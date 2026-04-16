from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx


@dataclass(frozen=True, slots=True)
class EvalCase:
    question: str
    acceptable_keyword_sets: tuple[tuple[str, ...], ...]
    should_refuse: bool = False


PDF_LINES = (
    "Project Phoenix revenue is 125 million dollars.",
    "The CEO is Alice Nguyen.",
    "The launch date is 2026-06-01.",
    "The support email is support@phoenix.example.",
)

EVAL_CASES = (
    EvalCase(
        question="What is the revenue of Project Phoenix?",
        acceptable_keyword_sets=(("125", "million"),),
    ),
    EvalCase(
        question="Who is the CEO?",
        acceptable_keyword_sets=(("Alice", "Nguyen"),),
    ),
    EvalCase(
        question="What is the launch date?",
        acceptable_keyword_sets=(("2026-06-01",), ("June", "1", "2026")),
    ),
    EvalCase(
        question="What is the office address?",
        acceptable_keyword_sets=(("office address",),),
        should_refuse=True,
    ),
    EvalCase(
        question="Summarize this document in 2 bullet points.",
        acceptable_keyword_sets=(("125", "Alice", "2026"),),
    ),
)


def _build_minimal_pdf(lines: tuple[str, ...]) -> bytes:
    text_commands = ["BT", "/F1 12 Tf", "72 720 Td"]
    for index, line in enumerate(lines):
        escaped_line = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if index > 0:
            text_commands.append("0 -20 Td")
        text_commands.append(f"({escaped_line}) Tj")
    text_commands.append("ET")
    content_bytes = "\n".join(text_commands).encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(content_bytes)).encode("ascii") + b" >>\nstream\n" + content_bytes + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))

    pdf.extend(
        (
            f"trailer\n<< /Root 1 0 R /Size {len(objects) + 1} >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)


def _write_sample_pdf(directory: Path) -> Path:
    run_marker = f"Evaluation run marker: {uuid4()}"
    pdf_path = directory / "llm_live_eval_sample.pdf"
    pdf_path.write_bytes(_build_minimal_pdf(PDF_LINES + (run_marker,)))
    return pdf_path


def _ensure_backend_ready(client: httpx.Client, base_url: str) -> None:
    response = client.get(f"{base_url}/health", timeout=10.0)
    response.raise_for_status()


def _upload_sample_document(client: httpx.Client, base_url: str, pdf_path: Path) -> dict[str, Any]:
    with pdf_path.open("rb") as file_handle:
        response = client.post(
            f"{base_url}/api/documents/upload",
            files={"file": (pdf_path.name, file_handle, "application/pdf")},
            timeout=120.0,
        )

    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "processed":
        raise RuntimeError(f"Uploaded document is not ready for RAG: {json.dumps(payload, indent=2)}")
    return payload


def _ask_question(
    client: httpx.Client,
    *,
    base_url: str,
    document_id: str,
    case: EvalCase,
) -> dict[str, Any]:
    started_at = time.perf_counter()
    response = client.post(
        f"{base_url}/api/rag/chat",
        json={
            "query": case.question,
            "document_id": document_id,
            "top_k": 5,
            "save_history": False,
        },
        timeout=120.0,
    )
    elapsed_ms = (time.perf_counter() - started_at) * 1000
    response.raise_for_status()
    payload = response.json()
    payload["_elapsed_ms"] = elapsed_ms
    return payload


def _contains_all(text: str, keywords: tuple[str, ...]) -> bool:
    normalized_text = text.casefold()
    return all(keyword.casefold() in normalized_text for keyword in keywords)


def _evaluate_response(case: EvalCase, payload: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    answer = str(payload.get("answer", ""))
    sources = payload.get("sources") or []

    if payload.get("used_fallback_generator"):
        problems.append("used fallback generator instead of the configured LLM")
    if payload.get("generator_provider") in {"extractive", None, ""}:
        problems.append(f"generator_provider is not a live LLM: {payload.get('generator_provider')!r}")
    if not sources:
        problems.append("no retrieval sources returned")
    if not any(_contains_all(answer, keywords) for keywords in case.acceptable_keyword_sets):
        problems.append(
            "answer is missing an acceptable keyword set: "
            + " OR ".join(", ".join(keyword_set) for keyword_set in case.acceptable_keyword_sets)
        )
    if case.should_refuse:
        refusal_markers = ("insufficient", "doesn't provide", "does not provide", "not provided", "not in the context")
        if not any(marker in answer.casefold() for marker in refusal_markers):
            problems.append("answer did not clearly refuse despite missing context")
        if "support@" in answer.casefold():
            problems.append("answer appears to hallucinate instead of refusing")
    return problems


def main() -> int:
    base_url = os.getenv("PDF_CHATBOT_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

    print(f"Base URL: {base_url}")
    print("Step 1/3: checking backend health...")

    with httpx.Client() as client:
        try:
            _ensure_backend_ready(client, base_url)
        except Exception as exc:
            print(f"Backend is not ready: {exc}")
            return 1

        with tempfile.TemporaryDirectory(prefix="pdf-chatbot-live-eval-") as temp_dir:
            pdf_path = _write_sample_pdf(Path(temp_dir))
            print(f"Step 2/3: uploading sample PDF {pdf_path.name}...")
            try:
                upload_payload = _upload_sample_document(client, base_url, pdf_path)
            except httpx.HTTPStatusError as exc:
                response_text = exc.response.text if exc.response is not None else str(exc)
                print("Upload failed:")
                print(response_text)
                return 1
            except Exception as exc:
                print(f"Upload failed: {exc}")
                return 1

        document_id = str(upload_payload["id"])
        print(f"Uploaded document_id: {document_id}")
        print("Step 3/3: running live RAG checks...")

        failures = 0
        for index, case in enumerate(EVAL_CASES, start=1):
            try:
                payload = _ask_question(
                    client,
                    base_url=base_url,
                    document_id=document_id,
                    case=case,
                )
            except httpx.HTTPStatusError as exc:
                failures += 1
                print(f"[{index}] FAIL {case.question}")
                print(f"  HTTP {exc.response.status_code}: {exc.response.text}")
                continue
            except Exception as exc:
                failures += 1
                print(f"[{index}] FAIL {case.question}")
                print(f"  Request error: {exc}")
                continue

            problems = _evaluate_response(case, payload)
            status = "PASS" if not problems else "FAIL"
            answer_preview = str(payload.get("answer", "")).replace("\n", " ").strip()
            if len(answer_preview) > 140:
                answer_preview = f"{answer_preview[:137]}..."

            print(f"[{index}] {status} {case.question}")
            print(
                "  "
                + f"provider={payload.get('generator_provider')} "
                + f"model={payload.get('generator_model_name')} "
                + f"fallback={payload.get('used_fallback_generator')} "
                + f"sources={len(payload.get('sources') or [])} "
                + f"elapsed_ms={payload.get('_elapsed_ms', 0):.0f}"
            )
            print(f"  answer={answer_preview}")
            if problems:
                failures += 1
                for problem in problems:
                    print(f"  problem={problem}")

        print()
        if failures:
            print(f"Live eval finished with {failures} failed case(s).")
            return 1

        print(f"Live eval finished successfully with {len(EVAL_CASES)} passing case(s).")
        return 0


if __name__ == "__main__":
    sys.exit(main())

from __future__ import annotations

import csv
import json
import os
import re
import sys
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, parse, request


REPO_ROOT = Path(__file__).resolve().parents[1]
EVALUATION_DIR = Path(__file__).resolve().parent
DEFAULT_QUESTIONS_FILE = EVALUATION_DIR / "evaluation_questions.csv"
DEFAULT_OUTPUT_DIR = EVALUATION_DIR
RESULT_COLUMNS = [
    "question_id",
    "document_name",
    "question",
    "answer",
    "expected_answer_keywords",
    "retrieved_sources",
    "top_1_relevant",
    "top_3_relevant_count",
    "top_5_relevant_count",
    "precision_at_1",
    "precision_at_3",
    "precision_at_5",
    "reciprocal_rank",
    "grounding_score",
    "functional_pass",
    "response_time_seconds",
    "error",
    "manual_review_note",
]


class EvaluationError(Exception):
    pass


class ApiRequestError(EvaluationError):
    def __init__(self, status_code: int | None, message: str) -> None:
        self.status_code = status_code
        super().__init__(message)


@dataclass(frozen=True)
class Config:
    api_base_url: str
    email: str
    password: str
    notebook_id: str | None
    output_dir: Path
    top_k: int
    questions_file: Path


def main() -> int:
    load_dotenv(REPO_ROOT / ".env")
    config = load_config()

    rows = read_question_rows(config.questions_file)
    if not rows:
        raise EvaluationError(f"No questions found in {config.questions_file}")

    token = login(config)
    notebooks = get_notebooks(config, token)
    documents = get_documents(config, token, notebooks)
    selected_documents = select_latest_documents(documents, count=3)
    document_by_question_name = build_document_lookup(selected_documents)

    results: list[dict[str, Any]] = []
    for row in rows:
        result = evaluate_question(config, token, row, document_by_question_name)
        results.append(result)
        print(
            f"{result['question_id']}: pass={result['functional_pass']} "
            f"p@1={result['precision_at_1']} rr={result['reciprocal_rank']} "
            f"time={result['response_time_seconds']}s"
        )

    config.output_dir.mkdir(parents=True, exist_ok=True)
    results_path = config.output_dir / "evaluation_results.csv"
    summary_path = config.output_dir / "evaluation_summary.json"
    write_results_csv(results_path, results)
    write_summary_json(summary_path, summarize(results))

    print(f"Wrote results to {results_path}")
    print(f"Wrote summary to {summary_path}")
    return 0


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_config() -> Config:
    email = os.environ.get("EVAL_EMAIL", "").strip()
    password = os.environ.get("EVAL_PASSWORD", "").strip()
    if not email or not password:
        raise EvaluationError("Set EVAL_EMAIL and EVAL_PASSWORD in .env before running evaluation.")

    top_k = int(os.environ.get("EVAL_TOP_K", "5"))
    if top_k < 1 or top_k > 20:
        raise EvaluationError("EVAL_TOP_K must be between 1 and 20.")

    output_dir = Path(os.environ.get("EVAL_OUTPUT_DIR", str(DEFAULT_OUTPUT_DIR)))
    questions_file = Path(os.environ.get("EVAL_QUESTIONS_FILE", str(DEFAULT_QUESTIONS_FILE)))

    return Config(
        api_base_url=os.environ.get("EVAL_API_BASE_URL", "http://localhost:8000").rstrip("/"),
        email=email,
        password=password,
        notebook_id=os.environ.get("EVAL_NOTEBOOK_ID") or None,
        output_dir=resolve_repo_path(output_dir),
        top_k=top_k,
        questions_file=resolve_repo_path(questions_file),
    )


def resolve_repo_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def read_question_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def login(config: Config) -> str:
    data = api_request(
        config,
        "POST",
        "/api/auth/login",
        payload={"email": config.email, "password": config.password},
    )
    token = data.get("access_token")
    if not token:
        raise EvaluationError("Login response did not include access_token.")
    return str(token)


def get_notebooks(config: Config, token: str) -> list[dict[str, Any]]:
    try:
        notebooks = api_request(config, "GET", "/api/notebooks/", token=token)
    except ApiRequestError as exc:
        print(f"Warning: could not list notebooks: {exc}", file=sys.stderr)
        return []
    return notebooks if isinstance(notebooks, list) else []


def get_documents(config: Config, token: str, notebooks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []

    if config.notebook_id:
        documents.extend(list_documents(config, token, config.notebook_id))
    else:
        documents.extend(list_documents(config, token, None))
        if len(processed_pdf_documents(documents)) < 3:
            seen_ids = {str(item.get("id")) for item in documents}
            for notebook in notebooks:
                notebook_id = str(notebook.get("id") or "")
                if not notebook_id:
                    continue
                for item in list_documents(config, token, notebook_id):
                    item_id = str(item.get("id"))
                    if item_id not in seen_ids:
                        documents.append(item)
                        seen_ids.add(item_id)

    processed = processed_pdf_documents(documents)
    if len(processed) < 3:
        raise EvaluationError("Need at least three processed PDF documents available to run this evaluation.")
    return processed


def list_documents(config: Config, token: str, notebook_id: str | None) -> list[dict[str, Any]]:
    query = {"notebook_id": notebook_id} if notebook_id else None
    data = api_request(config, "GET", "/api/documents/", token=token, query=query)
    return data if isinstance(data, list) else []


def processed_pdf_documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    filtered = [
        item
        for item in documents
        if str(item.get("status", "")).lower() == "processed"
        and str(item.get("mime_type", "")).lower() == "application/pdf"
    ]
    return sorted(filtered, key=lambda item: str(item.get("created_at", "")), reverse=True)


def select_latest_documents(documents: list[dict[str, Any]], *, count: int) -> list[dict[str, Any]]:
    return documents[:count]


def build_document_lookup(documents: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for index, document in enumerate(documents, start=1):
        name = str(document.get("original_file_name") or "")
        lookup[normalize_text(name)] = document
        lookup[normalize_text(Path(name).stem)] = document
        lookup[f"pdf {index}"] = document
        lookup[f"document {index}"] = document
    return lookup


def resolve_document_for_row(
    row: dict[str, str],
    document_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    requested_name = row.get("document_name", "")
    normalized_requested = normalize_text(requested_name)
    if normalized_requested in document_lookup:
        return document_lookup[normalized_requested]

    for candidate_name, document in document_lookup.items():
        if normalized_requested and (
            normalized_requested in candidate_name or candidate_name in normalized_requested
        ):
            return document

    available = ", ".join(sorted({str(doc.get("original_file_name")) for doc in document_lookup.values()}))
    raise EvaluationError(f"Could not match document_name '{requested_name}' to available documents: {available}")


def evaluate_question(
    config: Config,
    token: str,
    row: dict[str, str],
    document_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    question_id = row.get("question_id", "")
    question = row.get("question", "")
    expected_keywords = parse_terms(row.get("expected_answer_keywords", ""))
    source_hints = parse_terms(row.get("expected_source_hint", ""))
    started = time.perf_counter()
    answer = ""
    sources: list[dict[str, Any]] = []
    error_message = ""
    manual_review_note = ""

    try:
        document = resolve_document_for_row(row, document_lookup)
        payload = {
            "query": question,
            "top_k": config.top_k,
            "notebook_id": document.get("notebook_id"),
            "document_id": document.get("id"),
            "document_ids": [document.get("id")],
            "save_history": False,
        }
        response = api_request(config, "POST", "/api/chatbot/ask", token=token, payload=payload)
        answer = str(response.get("answer") or "")
        raw_sources = response.get("sources") or []
        sources = raw_sources if isinstance(raw_sources, list) else []
    except Exception as exc:
        error_message = str(exc)

    response_time = time.perf_counter() - started
    relevance = rank_relevant_sources(sources, expected_keywords, source_hints)
    top_1_relevant = bool(relevance[:1] and relevance[0])
    top_3_relevant_count = sum(1 for item in relevance[:3] if item)
    top_5_relevant_count = sum(1 for item in relevance[:5] if item)
    reciprocal_rank = reciprocal_rank_from_relevance(relevance)
    functional_pass = is_functional_pass(answer, error_message, expected_keywords)
    grounding_score, grounding_note = score_grounding(answer, sources, relevance, expected_keywords)
    if grounding_note:
        manual_review_note = grounding_note

    return {
        "question_id": question_id,
        "document_name": row.get("document_name", ""),
        "question": question,
        "answer": answer,
        "expected_answer_keywords": row.get("expected_answer_keywords", ""),
        "retrieved_sources": json.dumps(compact_sources(sources), ensure_ascii=False),
        "top_1_relevant": top_1_relevant,
        "top_3_relevant_count": top_3_relevant_count,
        "top_5_relevant_count": top_5_relevant_count,
        "precision_at_1": round(precision_at(relevance, 1), 4),
        "precision_at_3": round(precision_at(relevance, 3), 4),
        "precision_at_5": round(precision_at(relevance, 5), 4),
        "reciprocal_rank": round(reciprocal_rank, 4),
        "grounding_score": grounding_score,
        "functional_pass": functional_pass,
        "response_time_seconds": round(response_time, 4),
        "error": error_message,
        "manual_review_note": manual_review_note,
    }


def api_request(
    config: Config,
    method: str,
    path: str,
    *,
    token: str | None = None,
    payload: dict[str, Any] | None = None,
    query: dict[str, str | None] | None = None,
) -> Any:
    url = f"{config.api_base_url}{path}"
    if query:
        clean_query = {key: value for key, value in query.items() if value is not None}
        url = f"{url}?{parse.urlencode(clean_query)}"

    headers = {"Accept": "application/json"}
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = request.Request(url, data=body, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=120) as response:
            text = response.read().decode("utf-8")
            return json.loads(text) if text else {}
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise ApiRequestError(exc.code, extract_error_detail(details)) from exc
    except error.URLError as exc:
        raise ApiRequestError(None, f"Could not reach API at {config.api_base_url}: {exc.reason}") from exc


def extract_error_detail(details: str) -> str:
    try:
        parsed = json.loads(details)
    except json.JSONDecodeError:
        return details or "HTTP request failed."
    return str(parsed.get("detail") or parsed)


def parse_terms(raw_value: str) -> list[str]:
    terms = [item.strip() for item in raw_value.split(";")]
    return [item for item in terms if item]


def normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    ascii_value = ascii_value.lower()
    ascii_value = re.sub(r"[^a-z0-9]+", " ", ascii_value)
    return " ".join(ascii_value.split())


def source_text(source: dict[str, Any]) -> str:
    metadata = source.get("metadata") if isinstance(source.get("metadata"), dict) else {}
    parts = [
        source.get("document_name"),
        source.get("original_file_name"),
        source.get("content"),
        source.get("quoted_text"),
        json.dumps(metadata, ensure_ascii=False),
    ]
    return normalize_text(" ".join(str(part or "") for part in parts))


def rank_relevant_sources(
    sources: list[dict[str, Any]],
    expected_keywords: list[str],
    source_hints: list[str],
) -> list[bool]:
    terms = [normalize_text(term) for term in [*expected_keywords, *source_hints] if term]
    relevance: list[bool] = []
    for source in sources:
        text = source_text(source)
        relevance.append(any(term and term in text for term in terms))
    return relevance


def precision_at(relevance: list[bool], k: int) -> float:
    if k <= 0:
        return 0.0
    return sum(1 for item in relevance[:k] if item) / k


def reciprocal_rank_from_relevance(relevance: list[bool]) -> float:
    for index, relevant in enumerate(relevance, start=1):
        if relevant:
            return 1 / index
    return 0.0


def is_functional_pass(answer: str, error_message: str, expected_keywords: list[str]) -> bool:
    if error_message or not answer.strip():
        return False
    normalized_answer = normalize_text(answer)
    if not normalized_answer:
        return False
    if looks_like_failure_answer(normalized_answer):
        return False
    if expected_keywords:
        return any(normalize_text(keyword) in normalized_answer for keyword in expected_keywords)
    return True


def looks_like_failure_answer(normalized_answer: str) -> bool:
    failure_phrases = [
        "no relevant context was retrieved",
        "i do not know",
        "i don't know",
        "does not provide",
        "cannot answer",
        "could not answer",
    ]
    return any(phrase in normalized_answer for phrase in failure_phrases)


def score_grounding(
    answer: str,
    sources: list[dict[str, Any]],
    relevance: list[bool],
    expected_keywords: list[str],
) -> tuple[float, str]:
    if not answer.strip() or not sources:
        return 0.0, "No answer or no retrieved sources; manual review recommended."

    normalized_answer = normalize_text(answer)
    answer_has_keyword = any(normalize_text(keyword) in normalized_answer for keyword in expected_keywords)
    has_relevant_source = any(relevance)

    if answer_has_keyword and has_relevant_source:
        return 1.0, ""
    if answer_has_keyword or has_relevant_source:
        return 0.5, "Partial rule-based grounding; check manually if this question is important."
    return 0.0, "No expected keywords or relevant retrieved chunks detected; manual review recommended."


def compact_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compacted: list[dict[str, Any]] = []
    for rank, source in enumerate(sources, start=1):
        content = str(source.get("quoted_text") or source.get("content") or "")
        compacted.append(
            {
                "rank": rank,
                "document_name": source.get("document_name") or source.get("original_file_name"),
                "page": source.get("page_number") or source.get("page_from"),
                "chunk_index": source.get("chunk_index"),
                "score": source.get("score"),
                "excerpt": " ".join(content.split())[:300],
            }
        )
    return compacted


def write_results_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in RESULT_COLUMNS})


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    if total == 0:
        return {
            "total_questions": 0,
            "functional_pass_rate": 0,
            "precision_at_1": 0,
            "precision_at_3": 0,
            "precision_at_5": 0,
            "mean_reciprocal_rank": 0,
            "average_grounding_score": 0,
            "average_response_time_seconds": 0,
        }

    return {
        "total_questions": total,
        "functional_pass_rate": round(sum(bool_value(row["functional_pass"]) for row in rows) / total, 4),
        "precision_at_1": round(average_float(rows, "precision_at_1"), 4),
        "precision_at_3": round(average_float(rows, "precision_at_3"), 4),
        "precision_at_5": round(average_float(rows, "precision_at_5"), 4),
        "mean_reciprocal_rank": round(average_float(rows, "reciprocal_rank"), 4),
        "average_grounding_score": round(average_float(rows, "grounding_score"), 4),
        "average_response_time_seconds": round(average_float(rows, "response_time_seconds"), 4),
    }


def average_float(rows: list[dict[str, Any]], key: str) -> float:
    values = [float(row.get(key) or 0) for row in rows]
    return sum(values) / len(values) if values else 0.0


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes"}


def write_summary_json(path: Path, summary: dict[str, Any]) -> None:
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EvaluationError as exc:
        print(f"Evaluation failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

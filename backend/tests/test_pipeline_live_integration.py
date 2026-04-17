from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from pypdf import PdfReader, PdfWriter
from qdrant_client import QdrantClient
from sqlalchemy import select

from app.core.config import get_settings
from app.db.models import Document, DocumentChunk, DocumentContent
from app.db.models.shared import DocumentStatus
from app.db.session import SessionLocal

RUN_PDF_PIPELINE_INTEGRATION = os.getenv("RUN_PDF_PIPELINE_INTEGRATION") == "1"
BASE_URL = os.getenv("PDF_CHATBOT_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
REQUEST_TIMEOUT_SECONDS = float(os.getenv("PDF_CHATBOT_LIVE_TIMEOUT_SECONDS", "300"))
DATA_DIR = Path(__file__).resolve().parent / "data"
SOURCE_PDF_PATH = DATA_DIR / "test.pdf"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not RUN_PDF_PIPELINE_INTEGRATION,
        reason="Set RUN_PDF_PIPELINE_INTEGRATION=1 to run the live PDF pipeline integration test.",
    ),
]


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _clone_sample_pdf_with_unique_metadata(source_path: Path, target_path: Path) -> None:
    reader = PdfReader(str(source_path))
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    writer.add_metadata({"/PipelineRun": str(uuid4())})

    with target_path.open("wb") as file_handle:
        writer.write(file_handle)


def _upload_document(client: httpx.Client, pdf_path: Path) -> dict[str, object]:
    with pdf_path.open("rb") as file_handle:
        response = client.post(
            f"{BASE_URL}/api/documents/upload",
            files={"file": (pdf_path.name, file_handle, "application/pdf")},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

    assert response.status_code == 201, response.text
    return response.json()


def _load_document_state(document_id: UUID) -> tuple[Document, DocumentContent, list[DocumentChunk]]:
    with SessionLocal() as db:
        document = db.scalar(select(Document).where(Document.id == document_id))
        content = db.scalar(select(DocumentContent).where(DocumentContent.document_id == document_id))
        chunks = list(
            db.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == document_id)
                .order_by(DocumentChunk.chunk_index)
            )
        )

    assert document is not None, f"Document {document_id} was not found in PostgreSQL."
    assert content is not None, f"DocumentContent for {document_id} was not found in PostgreSQL."
    return document, content, chunks


def _assert_qdrant_points_exist(point_ids: list[str], *, collection_name: str, qdrant_url: str) -> None:
    qdrant_client = QdrantClient(url=qdrant_url)
    stored_points = qdrant_client.retrieve(
        collection_name=collection_name,
        ids=point_ids,
        with_payload=True,
        with_vectors=False,
    )

    assert len(stored_points) == len(point_ids), (
        f"Expected {len(point_ids)} Qdrant point(s), got {len(stored_points)}."
    )
    assert {str(point.id) for point in stored_points} == set(point_ids)


def test_pdf_pipeline_end_to_end_live() -> None:
    assert SOURCE_PDF_PATH.exists(), f"Sample PDF was not found at {SOURCE_PDF_PATH}"

    settings = get_settings()

    with httpx.Client() as client:
        health_response = client.get(f"{BASE_URL}/health", timeout=30.0)
        assert health_response.status_code == 200, health_response.text

        with tempfile.TemporaryDirectory(prefix="pdf-pipeline-live-") as temp_dir:
            upload_pdf_path = Path(temp_dir) / SOURCE_PDF_PATH.name
            _clone_sample_pdf_with_unique_metadata(SOURCE_PDF_PATH, upload_pdf_path)
            upload_payload = _upload_document(client, upload_pdf_path)

        document_id = UUID(str(upload_payload["id"]))
        document, content, chunks = _load_document_state(document_id)

        print()
        print(f"Uploaded document_id: {document_id}")
        print(f"Original filename: {document.original_file_name}")
        print(f"Pages: {document.total_pages}, chunks: {document.total_chunks}")

        assert document.status == DocumentStatus.processed
        assert document.total_chunks > 0
        assert document.total_chunks == len(chunks)

        normalized_raw_text = _normalize_text(content.raw_text)
        assert "COURSE: COMPUTER VISION".casefold() in normalized_raw_text.casefold()
        assert "LECTURER: PROF. NGUYEN DUC DUNG".casefold() in normalized_raw_text.casefold()
        assert "SROIE2019".casefold() in normalized_raw_text.casefold()

        point_ids = [chunk.qdrant_point_id for chunk in chunks if chunk.qdrant_point_id]
        assert point_ids, "No Qdrant point ids were saved for this document."
        assert len(point_ids) == len(chunks)
        assert all(chunk.embedding_model == settings.embedding_model_name for chunk in chunks)

        _assert_qdrant_points_exist(
            point_ids,
            collection_name=settings.qdrant_collection_name,
            qdrant_url=settings.qdrant_url,
        )

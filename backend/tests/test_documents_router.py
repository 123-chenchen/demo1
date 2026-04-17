from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.crud import document_crud
from app.db.models.shared import DocumentStatus
from app.services.document_ingest import document_ingest_service
from app.services.document_upload import (
    DocumentUploadConflictError,
    DocumentUploadStorageError,
    DocumentUploadValidationError,
    document_upload_service,
)


def _document_payload(
    *,
    document_id: UUID | None = None,
    original_file_name: str = "sample.pdf",
) -> dict[str, object]:
    now = datetime.now(timezone.utc)
    resolved_document_id = document_id or uuid4()
    return {
        "id": resolved_document_id,
        "storage_key": f"pdf-documents/documents/{resolved_document_id}.pdf",
        "original_file_name": original_file_name,
        "mime_type": "application/pdf",
        "file_size_bytes": 128,
        "total_pages": 1,
        "total_chunks": 2,
        "status": DocumentStatus.processed,
        "metadata": {"bucket_name": "pdf-documents"},
        "created_at": now,
        "updated_at": now,
    }


def test_upload_document_returns_created_record(client, override_db, monkeypatch) -> None:
    override_db()

    def fake_upload_pdf(db, *, upload_file, notebook_id=None):
        assert upload_file.filename == "sample.pdf"
        assert notebook_id is None
        return _document_payload(original_file_name=upload_file.filename)

    monkeypatch.setattr(document_upload_service, "upload_pdf", fake_upload_pdf)

    response = client.post(
        "/api/documents/upload",
        files={"file": ("sample.pdf", b"%PDF-1.4\ncontent\n%%EOF", "application/pdf")},
    )

    assert response.status_code == 201
    assert response.json()["original_file_name"] == "sample.pdf"
    assert response.json()["status"] == "processed"


def test_upload_document_maps_validation_errors_to_http_400(client, override_db, monkeypatch) -> None:
    override_db()

    def fake_upload_pdf(db, *, upload_file, notebook_id=None):
        raise DocumentUploadValidationError("Only .pdf files can be uploaded.")

    monkeypatch.setattr(document_upload_service, "upload_pdf", fake_upload_pdf)

    response = client.post(
        "/api/documents/upload",
        files={"file": ("sample.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only .pdf files can be uploaded."


def test_upload_document_maps_conflicts_to_http_409(client, override_db, monkeypatch) -> None:
    override_db()

    def fake_upload_pdf(db, *, upload_file, notebook_id=None):
        raise DocumentUploadConflictError("This PDF already exists in storage.")

    monkeypatch.setattr(document_upload_service, "upload_pdf", fake_upload_pdf)

    response = client.post(
        "/api/documents/upload",
        files={"file": ("sample.pdf", b"%PDF-1.4\ncontent\n%%EOF", "application/pdf")},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "This PDF already exists in storage."


def test_upload_document_maps_storage_failures_to_http_503(client, override_db, monkeypatch) -> None:
    override_db()

    def fake_upload_pdf(db, *, upload_file, notebook_id=None):
        raise DocumentUploadStorageError("Could not upload the PDF to MinIO.")

    monkeypatch.setattr(document_upload_service, "upload_pdf", fake_upload_pdf)

    response = client.post(
        "/api/documents/upload",
        files={"file": ("sample.pdf", b"%PDF-1.4\ncontent\n%%EOF", "application/pdf")},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Could not upload the PDF to MinIO."


def test_ingest_document_returns_processed_document(client, override_db, monkeypatch) -> None:
    override_db()
    document_id = uuid4()

    def fake_get_for_scope(db, *, obj_id, notebook_id):
        assert obj_id == document_id
        assert notebook_id is None
        return object()

    def fake_ingest_document(db, *, document):
        assert document is not None
        return _document_payload(document_id=document_id, original_file_name="ingested.pdf")

    monkeypatch.setattr(document_crud, "get_for_scope", fake_get_for_scope)
    monkeypatch.setattr(document_ingest_service, "ingest_document", fake_ingest_document)

    response = client.post(f"/api/documents/{document_id}/ingest")

    assert response.status_code == 200
    assert response.json()["id"] == str(document_id)
    assert response.json()["original_file_name"] == "ingested.pdf"


def test_ingest_document_returns_404_when_document_is_missing(client, override_db, monkeypatch) -> None:
    override_db()

    def fake_get_for_scope(db, *, obj_id, notebook_id):
        return None

    monkeypatch.setattr(document_crud, "get_for_scope", fake_get_for_scope)

    response = client.post(f"/api/documents/{uuid4()}/ingest")

    assert response.status_code == 404
    assert response.json()["detail"] == "document not found."

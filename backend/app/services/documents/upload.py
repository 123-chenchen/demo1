from __future__ import annotations 

import re 
import uuid 
from datetime import datetime, timezone 
from pathlib import Path
from typing import BinaryIO

from fastapi import UploadFile
from minio.error import S3Error
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Document
from app.db.models.shared import DocumentStatus
from app.services.retrieval.ingestion import document_ingest_service
from app.services.storage import StorageServiceError, ensure_bucket_exists, get_minio_client
from app.utils.pdf import PdfReadServiceError, extract_page_count, inspect_pdf

PDF_SIGNATURE = b"%PDF-"
READ_CHUNK_SIZE = 1024 * 1024


class DocumentUploadValidationError(Exception):
    pass


class DocumentUploadConflictError(Exception):
    pass


class DocumentUploadStorageError(Exception):
    pass

def _normalize_filename(filename: str | None) -> str:
    if not filename:
        return "document.pdf"

    safe_name = filename.replace("\\", "/").split("/")[-1].strip()
    return safe_name or "document.pdf"

def _build_object_name(original_file_name: str) -> str:
    stem = Path(original_file_name).stem or "document"
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip(".-_") or "document"
    date_prefix = datetime.now(timezone.utc).strftime("%Y/%m/%d")
    return f"documents/{date_prefix}/{uuid.uuid4()}-{safe_stem}.pdf"

def _inspect_pdf(file_obj: BinaryIO) -> int:
    try:
        return inspect_pdf(file_obj)
    except PdfReadServiceError as exc:
        raise DocumentUploadValidationError(str(exc)) from exc


def _extract_page_count(file_obj: BinaryIO) -> int | None:
    return extract_page_count(file_obj)


class DocumentUploadService:
    def upload_pdf(self, db: Session, *, upload_file: UploadFile, notebook_id=None) -> Document:
        original_file_name = _normalize_filename(upload_file.filename)
        if Path(original_file_name).suffix.lower() != ".pdf":
            raise DocumentUploadValidationError("Only .pdf files can be uploaded.")

        file_obj = upload_file.file
        file_size_bytes = _inspect_pdf(file_obj)
        total_pages = _extract_page_count(file_obj)

        settings = get_settings()
        object_name = _build_object_name(original_file_name)
        storage_key = f"{settings.minio_bucket}/{object_name}"

        try:
            ensure_bucket_exists(settings.minio_bucket)
            file_obj.seek(0)
            upload_result = get_minio_client().put_object(
                bucket_name=settings.minio_bucket,
                object_name=object_name,
                data=file_obj,
                length=file_size_bytes,
                content_type="application/pdf",
            )
        except (StorageServiceError, S3Error, OSError) as exc:
            raise DocumentUploadStorageError("Could not upload the PDF to MinIO.") from exc

        document = Document(
            notebook_id=notebook_id,
            storage_key=storage_key,
            original_file_name=original_file_name,
            mime_type="application/pdf",
            file_size_bytes=file_size_bytes,
            total_pages=total_pages,
            total_chunks=0,
            status=DocumentStatus.pending,
            extra_metadata={
                "storage_provider": "minio",
                "bucket_name": settings.minio_bucket,
                "object_name": object_name,
                "etag": upload_result.etag,
                "uploaded_content_type": upload_file.content_type,
            },
        )

        db.add(document)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            try:
                get_minio_client().remove_object(settings.minio_bucket, object_name)
            except S3Error:
                pass
            raise DocumentUploadConflictError("Could not save the uploaded PDF metadata.") from exc

        db.refresh(document)
        return document_ingest_service.ingest_document(db, document=document)


document_upload_service = DocumentUploadService()

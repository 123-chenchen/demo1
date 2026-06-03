from __future__ import annotations

import hashlib
import uuid

from pypdf.errors import PdfReadError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Document, DocumentChunk, DocumentContent
from app.db.models.shared import DocumentStatus
from app.services.retrieval.chunking import build_chunks, count_tokens
from app.services.retrieval.embedding import EmbeddingServiceError, get_embedding_dimension
from app.services.retrieval.vector_store import (
    VectorStoreError,
    delete_points,
    upsert_document_chunks,
)
from app.services.storage import StorageServiceError, get_object_buffer, parse_storage_key
from app.utils.pdf import PdfReadServiceError, extract_pdf_pages


class DocumentIngestError(Exception):
    pass


def _count_tokens(text: str) -> int | None:
    return count_tokens(text)


class DocumentIngestService:
    extractor_name = "pypdf"

    def ingest_document(self, db: Session, *, document: Document) -> Document:
        settings = get_settings()
        metadata = dict(document.extra_metadata or {})
        existing_point_ids = [
            point_id
            for point_id in db.scalars(
                select(DocumentChunk.qdrant_point_id).where(
                    DocumentChunk.document_id == document.id,
                    DocumentChunk.qdrant_point_id.is_not(None),
                )
            )
            if point_id
        ]
        new_point_ids: list[str] = []

        try:
            bucket_name, object_name = parse_storage_key(document.storage_key)
            file_buffer = get_object_buffer(bucket_name, object_name)
            page_entries = self._extract_pages(file_buffer)
            raw_text = "\n\n".join(entry["text"] for entry in page_entries).strip()
            if not raw_text:
                raise DocumentIngestError("No extractable text was found in the PDF.")

            chunks = self._build_chunks(page_entries)
            if not chunks:
                raise DocumentIngestError("Chunking produced no usable text chunks.")

            db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
            db.execute(delete(DocumentContent).where(DocumentContent.document_id == document.id))

            document_content = DocumentContent(
                document_id=document.id,
                raw_text=raw_text,
                character_count=len(raw_text),
                content_hash=hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
                extractor_name=self.extractor_name,
                extra_metadata={
                    "extracted_page_count": len(page_entries),
                },
            )

            db.add(document_content)

            chunk_rows: list[DocumentChunk] = []
            for chunk in chunks:
                chunk_id = uuid.uuid4()
                chunk_rows.append(
                    DocumentChunk(
                        id=chunk_id,
                        document_id=document.id,
                        chunk_index=chunk["chunk_index"],
                        page_from=chunk["page_from"],
                        page_to=chunk["page_to"],
                        content=chunk["content"],
                        token_count=chunk["token_count"],
                        character_count=chunk["character_count"],
                        qdrant_point_id=str(chunk_id),
                        embedding_model=settings.embedding_model_name,
                        extra_metadata=chunk["metadata"],
                    )
                )

            upsert_document_chunks(document=document, chunks=chunk_rows)
            new_point_ids = [chunk_row.qdrant_point_id for chunk_row in chunk_rows if chunk_row.qdrant_point_id]

            for chunk_row in chunk_rows:
                db.add(chunk_row)

            metadata.pop("ingest_error", None)
            metadata.update(
                {
                    "extractor_name": self.extractor_name,
                    "bucket_name": bucket_name,
                    "object_name": object_name,
                    "chunk_size": settings.document_chunk_size,
                    "chunk_overlap": settings.document_chunk_overlap,
                    "extracted_page_count": len(page_entries),
                    "embedding_model": settings.embedding_model_name,
                    "qdrant_collection": settings.qdrant_collection_name,
                    "vector_size": get_embedding_dimension(),
                    "embedded_chunk_count": len(chunk_rows),
                }
            )
            document.extra_metadata = metadata
            document.total_pages = len(page_entries)
            document.total_chunks = len(chunk_rows)
            document.status = DocumentStatus.processed

            db.add(document)
            db.commit()
        except (
            DocumentIngestError,
            StorageServiceError,
            VectorStoreError,
            EmbeddingServiceError,
            PdfReadServiceError,
            PdfReadError,
            ValueError,
            OSError,
        ) as exc:
            db.rollback()
            if new_point_ids:
                try:
                    delete_points(new_point_ids)
                except VectorStoreError:
                    pass
            return self._mark_failed(db, document=document, error_message=str(exc))

        if existing_point_ids:
            try:
                delete_points(existing_point_ids)
            except VectorStoreError:
                pass

        db.refresh(document)
        return document

    def _extract_pages(self, file_buffer) -> list[dict[str, int | str]]:
        try:
            return extract_pdf_pages(file_buffer)
        except PdfReadServiceError as exc:
            raise DocumentIngestError(str(exc)) from exc

    def _build_chunks(self, page_entries: list[dict[str, int | str]]) -> list[dict[str, object]]:
        return build_chunks(page_entries)

    def _mark_failed(self, db: Session, *, document: Document, error_message: str) -> Document:
        metadata = dict(document.extra_metadata or {})
        metadata["ingest_error"] = error_message
        document.extra_metadata = metadata
        document.status = DocumentStatus.failed
        document.total_chunks = 0
        db.add(document)
        db.commit()
        db.refresh(document)
        return document

    def ingest_document_by_id(self, db: Session, *, document_id) -> Document | None:
        document = db.scalar(select(Document).where(Document.id == document_id))
        if document is None:
            return None
        return self.ingest_document(db, document=document)


document_ingest_service = DocumentIngestService()

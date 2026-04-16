from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.db.models import Document, DocumentStatus
from app.services.vector_store import VectorStoreError, reset_collection, upsert_document_chunks


class RetrievalIndexerError(Exception):
    pass


class RetrievalIndexerService:
    def reindex_all(self, db: Session) -> dict[str, object]:
        settings = get_settings()

        try:
            reset_collection()

            documents = list(
                db.scalars(
                    select(Document)
                    .options(selectinload(Document.chunks))
                    .where(Document.status == DocumentStatus.processed)
                )
            )

            indexed_documents = 0
            indexed_chunks = 0

            for document in documents:
                chunk_rows = list(document.chunks)
                if not chunk_rows:
                    continue

                upsert_document_chunks(document=document, chunks=chunk_rows)
                for chunk_row in chunk_rows:
                    db.add(chunk_row)

                indexed_documents += 1
                indexed_chunks += len(chunk_rows)

            db.commit()
        except VectorStoreError as exc:
            db.rollback()
            raise RetrievalIndexerError(str(exc)) from exc
        except Exception as exc:
            db.rollback()
            raise RetrievalIndexerError("Could not reindex retrieval data into Qdrant.") from exc

        return {
            "reset_collection": True,
            "document_count": indexed_documents,
            "chunk_count": indexed_chunks,
            "collection_name": settings.qdrant_collection_name,
            "embedding_model": settings.embedding_model_name,
        }


retrieval_indexer_service = RetrievalIndexerService()

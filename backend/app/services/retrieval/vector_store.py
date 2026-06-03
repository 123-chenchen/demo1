from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache
from uuid import UUID

from langchain_core.documents import Document as LangChainDocument
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models

from app.config import get_settings
from app.db.models import Document, DocumentChunk
from app.services.retrieval.embedding import (
    EmbeddingServiceError,
    get_embedding_dimension,
    get_langchain_embeddings,
)

LANGCHAIN_CONTENT_KEY = "page_content"
LANGCHAIN_METADATA_KEY = "metadata"


class VectorStoreError(Exception):
    pass


@lru_cache
def get_qdrant_client() -> QdrantClient:
    settings = get_settings()
    return QdrantClient(url=settings.qdrant_url)


def ensure_collection() -> None:
    settings = get_settings()
    try:
        vector_size = get_embedding_dimension()
    except EmbeddingServiceError as exc:
        raise VectorStoreError(str(exc)) from exc
    client = get_qdrant_client()

    try:
        if client.collection_exists(settings.qdrant_collection_name):
            collection_info = client.get_collection(settings.qdrant_collection_name)
            vectors_config = collection_info.config.params.vectors
            if isinstance(vectors_config, dict):
                raise VectorStoreError(
                    "Existing Qdrant collection uses named vectors, but a single vector is required."
                )
            if vectors_config.size != vector_size:
                raise VectorStoreError(
                    "Existing Qdrant collection has a different vector size than the embedding model."
                )
            if vectors_config.distance != models.Distance.COSINE:
                raise VectorStoreError(
                    "Existing Qdrant collection must use cosine distance for this embedding pipeline."
                )
            return

        client.create_collection(
            collection_name=settings.qdrant_collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE,
            ),
        )
    except VectorStoreError:
        raise
    except Exception as exc:
        raise VectorStoreError("Could not initialize the Qdrant collection.") from exc


@lru_cache
def get_vector_store() -> QdrantVectorStore:
    settings = get_settings()
    ensure_collection()

    try:
        return QdrantVectorStore(
            client=get_qdrant_client(),
            collection_name=settings.qdrant_collection_name,
            embedding=get_langchain_embeddings(),
            content_payload_key=LANGCHAIN_CONTENT_KEY,
            metadata_payload_key=LANGCHAIN_METADATA_KEY,
        )
    except Exception as exc:
        raise VectorStoreError("Could not initialize LangChain Qdrant vector store.") from exc


def _build_payload_metadata(document: Document, chunk: DocumentChunk) -> dict[str, object]:
    return {
        "chunk_id": str(chunk.id),
        "document_id": str(document.id),
        "notebook_id": str(document.notebook_id) if document.notebook_id else None,
        "chunk_index": chunk.chunk_index,
        "page_from": chunk.page_from,
        "page_to": chunk.page_to,
        "storage_key": document.storage_key,
        "original_file_name": document.original_file_name,
        "token_count": chunk.token_count,
        "character_count": chunk.character_count,
        "embedding_model": get_settings().embedding_model_name,
    }


def upsert_document_chunks(*, document: Document, chunks: Sequence[DocumentChunk]) -> None:
    if not chunks:
        return

    settings = get_settings()
    ensure_collection()

    documents: list[LangChainDocument] = []
    point_ids: list[str] = []

    for chunk in chunks:
        point_id = chunk.qdrant_point_id or str(chunk.id)
        chunk.qdrant_point_id = point_id
        chunk.embedding_model = settings.embedding_model_name

        metadata = dict(chunk.extra_metadata or {})
        try:
            vector_size = get_embedding_dimension()
        except EmbeddingServiceError as exc:
            raise VectorStoreError(str(exc)) from exc

        metadata.update(
            {
                "embedding_model": settings.embedding_model_name,
                "qdrant_collection": settings.qdrant_collection_name,
                "vector_size": vector_size,
            }
        )
        chunk.extra_metadata = metadata

        documents.append(
            LangChainDocument(
                page_content=chunk.content,
                metadata=_build_payload_metadata(document, chunk),
            )
        )
        point_ids.append(point_id)

    try:
        get_vector_store().add_documents(documents=documents, ids=point_ids)
    except Exception as exc:
        raise VectorStoreError("Could not store document chunk vectors in Qdrant.") from exc


def build_document_filter(
    *,
    document_id: UUID | None,
    notebook_id: UUID | None = None,
    public_only: bool = False,
) -> models.Filter | None:
    must_conditions: list[object] = []

    if document_id is not None:
        must_conditions.append(
            models.FieldCondition(
                key=f"{LANGCHAIN_METADATA_KEY}.document_id",
                match=models.MatchValue(value=str(document_id)),
            )
        )

    if notebook_id is not None:
        must_conditions.append(
            models.FieldCondition(
                key=f"{LANGCHAIN_METADATA_KEY}.notebook_id",
                match=models.MatchValue(value=str(notebook_id)),
            )
        )

    if public_only:
        public_conditions = [
            models.IsNullCondition(
                is_null=models.PayloadField(key=f"{LANGCHAIN_METADATA_KEY}.notebook_id"),
            ),
            models.IsEmptyCondition(
                is_empty=models.PayloadField(key=f"{LANGCHAIN_METADATA_KEY}.notebook_id"),
            ),
        ]
        return models.Filter(
            must=must_conditions or None,
            min_should=models.MinShould(conditions=public_conditions, min_count=1),
        )

    if not must_conditions:
        return None

    return models.Filter(must=must_conditions)


def similarity_search(
    *,
    query: str,
    limit: int,
    document_id: UUID | None = None,
    notebook_id: UUID | None = None,
    public_only: bool = False,
) -> list[tuple[LangChainDocument, float]]:
    ensure_collection()

    try:
        return get_vector_store().similarity_search_with_score(
            query=query,
            k=limit,
            filter=build_document_filter(
                document_id=document_id,
                notebook_id=notebook_id,
                public_only=public_only,
            ),
        )
    except Exception as exc:
        raise VectorStoreError("Could not retrieve document chunks from Qdrant.") from exc


def delete_points(point_ids: Sequence[str]) -> None:
    normalized_point_ids = [point_id for point_id in point_ids if point_id]
    if not normalized_point_ids:
        return

    settings = get_settings()

    try:
        get_qdrant_client().delete(
            collection_name=settings.qdrant_collection_name,
            wait=True,
            points_selector=models.PointIdsList(points=normalized_point_ids),
        )
    except Exception as exc:
        raise VectorStoreError("Could not delete old document chunk vectors from Qdrant.") from exc


def reset_collection() -> None:
    settings = get_settings()
    client = get_qdrant_client()

    try:
        vector_size = get_embedding_dimension()
        if client.collection_exists(settings.qdrant_collection_name):
            client.delete_collection(settings.qdrant_collection_name)
        client.create_collection(
            collection_name=settings.qdrant_collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE,
            ),
        )
    except EmbeddingServiceError as exc:
        raise VectorStoreError(str(exc)) from exc
    except Exception as exc:
        raise VectorStoreError("Could not reset the Qdrant collection.") from exc

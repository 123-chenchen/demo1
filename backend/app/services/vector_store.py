from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache

from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings
from app.db.models import Document, DocumentChunk


class VectorStoreError(Exception):
    pass


@lru_cache
def get_qdrant_client() -> QdrantClient:
    settings = get_settings()
    return QdrantClient(url=settings.qdrant_url)


@lru_cache
def get_embedding_model() -> SentenceTransformer:
    settings = get_settings()
    try:
        return SentenceTransformer(settings.embedding_model_name)
    except Exception as exc:
        raise VectorStoreError(
            f"Could not load embedding model '{settings.embedding_model_name}'."
        ) from exc


@lru_cache
def get_embedding_dimension() -> int:
    try:
        model = get_embedding_model()
        if hasattr(model, "get_embedding_dimension"):
            vector_size = model.get_embedding_dimension()
        else:
            vector_size = model.get_sentence_embedding_dimension()
    except Exception as exc:
        raise VectorStoreError("Could not determine embedding vector size.") from exc

    if not vector_size:
        raise VectorStoreError("Embedding model returned an invalid vector size.")

    return int(vector_size)


def ensure_collection() -> None:
    settings = get_settings()
    vector_size = get_embedding_dimension()
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


def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    if not texts:
        return []

    settings = get_settings()

    try:
        vectors = get_embedding_model().encode(
            list(texts),
            batch_size=settings.embedding_batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
    except Exception as exc:
        raise VectorStoreError("Could not create embeddings for document chunks.") from exc

    return vectors.tolist()


def upsert_document_chunks(*, document: Document, chunks: Sequence[DocumentChunk]) -> None:
    if not chunks:
        return

    settings = get_settings()
    ensure_collection()
    vectors = embed_texts([chunk.content for chunk in chunks])

    points = []
    for chunk, vector in zip(chunks, vectors, strict=True):
        point_id = chunk.qdrant_point_id or str(chunk.id)
        chunk.qdrant_point_id = point_id
        chunk.embedding_model = settings.embedding_model_name

        metadata = dict(chunk.extra_metadata or {})
        metadata.update(
            {
                "embedding_model": settings.embedding_model_name,
                "qdrant_collection": settings.qdrant_collection_name,
                "vector_size": len(vector),
            }
        )
        chunk.extra_metadata = metadata

        points.append(
            models.PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "document_id": str(document.id),
                    "chunk_id": str(chunk.id),
                    "chunk_index": chunk.chunk_index,
                    "page_from": chunk.page_from,
                    "page_to": chunk.page_to,
                    "storage_key": document.storage_key,
                    "original_file_name": document.original_file_name,
                    "content": chunk.content,
                    "token_count": chunk.token_count,
                    "character_count": chunk.character_count,
                    "embedding_model": settings.embedding_model_name,
                },
            )
        )

    try:
        get_qdrant_client().upsert(
            collection_name=settings.qdrant_collection_name,
            wait=True,
            points=points,
        )
    except Exception as exc:
        raise VectorStoreError("Could not store document chunk vectors in Qdrant.") from exc


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

from __future__ import annotations

from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings
from sentence_transformers import SentenceTransformer

from app.config import get_settings


class EmbeddingServiceError(Exception):
    pass


@lru_cache
def get_embedding_model() -> SentenceTransformer:
    settings = get_settings()
    try:
        return SentenceTransformer(settings.embedding_model_name)
    except Exception as exc:
        raise EmbeddingServiceError(
            f"Could not load embedding model '{settings.embedding_model_name}'."
        ) from exc


@lru_cache
def get_langchain_embeddings() -> HuggingFaceEmbeddings:
    settings = get_settings()
    try:
        return HuggingFaceEmbeddings(
            model_name=settings.embedding_model_name,
            encode_kwargs={
                "batch_size": settings.embedding_batch_size,
                "normalize_embeddings": True,
            },
            show_progress=False,
        )
    except Exception as exc:
        raise EmbeddingServiceError(
            f"Could not initialize LangChain embeddings for '{settings.embedding_model_name}'."
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
        raise EmbeddingServiceError("Could not determine embedding vector size.") from exc

    if not vector_size:
        raise EmbeddingServiceError("Embedding model returned an invalid vector size.")

    return int(vector_size)

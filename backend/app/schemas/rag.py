from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.base import AppSchema


class RetrievalChunkRead(AppSchema):
    chunk_id: UUID
    document_id: UUID
    original_file_name: str
    storage_key: str
    content: str
    chunk_index: int
    page_from: int | None = None
    page_to: int | None = None
    token_count: int | None = None
    character_count: int | None = None
    score: float | None = None
    source: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatbotAskRequest(AppSchema):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    notebook_id: UUID | None = None
    document_id: UUID | None = None
    session_id: UUID | None = None
    save_history: bool = True


class ChatbotAskResponse(AppSchema):
    query: str
    answer: str
    notebook_id: UUID | None = None
    document_id: UUID | None = None
    session_id: UUID | None = None
    user_message_id: UUID | None = None
    assistant_message_id: UUID | None = None
    retriever: str
    embedding_model: str
    vector_store: str
    generator_provider: str
    generator_model_name: str | None = None
    used_fallback_generator: bool = False
    retrieval_latency_ms: float
    total_latency_ms: float
    sources: list[RetrievalChunkRead]


class ReindexResponse(AppSchema):
    reset_collection: bool
    document_count: int
    chunk_count: int
    collection_name: str
    embedding_model: str

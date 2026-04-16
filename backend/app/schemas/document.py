from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.db.models.shared import DocumentStatus
from app.schemas.base import AppSchema


class DocumentCreate(AppSchema):
    storage_key: str
    original_file_name: str
    mime_type: str = "application/pdf"
    file_size_bytes: int | None = None
    total_pages: int | None = None
    total_chunks: int = 0
    status: DocumentStatus = DocumentStatus.pending
    metadata: dict = Field(default_factory=dict)


class DocumentUpdate(AppSchema):
    storage_key: str | None = None
    original_file_name: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = None
    total_pages: int | None = None
    total_chunks: int | None = None
    status: DocumentStatus | None = None
    metadata: dict | None = None


class DocumentRead(AppSchema):
    id: UUID
    storage_key: str
    original_file_name: str
    mime_type: str
    file_size_bytes: int | None = None
    total_pages: int | None = None
    total_chunks: int
    status: DocumentStatus
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class DocumentContentCreate(AppSchema):
    document_id: UUID
    raw_text: str
    character_count: int | None = None
    content_hash: str | None = None
    extractor_name: str | None = None
    metadata: dict = Field(default_factory=dict)


class DocumentContentUpdate(AppSchema):
    raw_text: str | None = None
    character_count: int | None = None
    content_hash: str | None = None
    extractor_name: str | None = None
    metadata: dict | None = None


class DocumentContentRead(AppSchema):
    id: UUID
    document_id: UUID
    raw_text: str
    character_count: int | None = None
    content_hash: str | None = None
    extractor_name: str | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class DocumentChunkCreate(AppSchema):
    document_id: UUID
    chunk_index: int
    page_from: int | None = None
    page_to: int | None = None
    content: str
    token_count: int | None = None
    character_count: int | None = None
    qdrant_point_id: str | None = None
    embedding_model: str | None = None
    metadata: dict = Field(default_factory=dict)


class DocumentChunkUpdate(AppSchema):
    chunk_index: int | None = None
    page_from: int | None = None
    page_to: int | None = None
    content: str | None = None
    token_count: int | None = None
    character_count: int | None = None
    qdrant_point_id: str | None = None
    embedding_model: str | None = None
    metadata: dict | None = None


class DocumentChunkRead(AppSchema):
    id: UUID
    document_id: UUID
    chunk_index: int
    page_from: int | None = None
    page_to: int | None = None
    content: str
    token_count: int | None = None
    character_count: int | None = None
    qdrant_point_id: str | None = None
    embedding_model: str | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime

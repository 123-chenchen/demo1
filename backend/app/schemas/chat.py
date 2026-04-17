from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.db.models.shared import MessageRole
from app.schemas.base import AppSchema


class ChatSessionCreate(AppSchema):
    notebook_id: UUID | None = None
    title: str | None = None
    metadata: dict = Field(default_factory=dict)


class ChatSessionUpdate(AppSchema):
    title: str | None = None
    metadata: dict | None = None


class ChatSessionRead(AppSchema):
    id: UUID
    notebook_id: UUID | None = None
    title: str | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ChatMessageCreate(AppSchema):
    session_id: UUID
    reply_to_message_id: UUID | None = None
    role: MessageRole
    content: str
    model_name: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    metadata: dict = Field(default_factory=dict)


class ChatMessageUpdate(AppSchema):
    session_id: UUID | None = None
    reply_to_message_id: UUID | None = None
    role: MessageRole | None = None
    content: str | None = None
    model_name: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    metadata: dict | None = None


class ChatMessageRead(AppSchema):
    id: UUID
    session_id: UUID
    reply_to_message_id: UUID | None = None
    role: MessageRole
    content: str
    model_name: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime


class MessageSourceCreate(AppSchema):
    message_id: UUID
    chunk_id: UUID
    source_rank: int
    score: float | None = None
    snippet: str | None = None


class MessageSourceUpdate(AppSchema):
    message_id: UUID | None = None
    chunk_id: UUID | None = None
    source_rank: int | None = None
    score: float | None = None
    snippet: str | None = None


class MessageSourceRead(AppSchema):
    id: UUID
    message_id: UUID
    chunk_id: UUID
    source_rank: int
    score: float | None = None
    snippet: str | None = None
    created_at: datetime

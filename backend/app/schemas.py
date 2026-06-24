from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.db.models.shared import DocumentStatus, MessageRole

#
class AppSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra="forbid",
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_model_input(cls, value: Any) -> Any:
        if value is None:
            return value

        if isinstance(value, dict):
            data = dict(value)
        elif hasattr(value, "__dict__"):
            data = {
                key: val
                for key, val in vars(value).items()
                if not key.startswith("_")
            }
        else:
            return value

        normalized: dict[str, Any] = {}
        allowed_fields = set(cls.model_fields)

        for key, val in data.items():
            if key == "extra_metadata" and "metadata" in allowed_fields:
                normalized["metadata"] = val
            elif key in allowed_fields:
                normalized[key] = val

        return normalized

    def to_model_dict(self, *, exclude_unset: bool = False) -> dict[str, Any]:
        data = self.model_dump(exclude_unset=exclude_unset)
        if "metadata" in data:
            data["extra_metadata"] = data.pop("metadata")
        return data

# 
class UserCreate(AppSchema):
    email: str
    name: str | None = None
    full_name: str | None = None
    password: str = Field(min_length=8)
    is_verified: bool = False
    is_active: bool = True
    is_superuser: bool = False
    metadata: dict = Field(default_factory=dict)


class UserUpdate(AppSchema):
    email: str | None = None
    name: str | None = None
    full_name: str | None = None
    password: str | None = Field(default=None, min_length=8)
    is_verified: bool | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None
    last_login_at: datetime | None = None
    metadata: dict | None = None


class UserRead(AppSchema):
    email: str
    name: str
    full_name: str | None = None


class RefreshTokenCreate(AppSchema):
    user_id: UUID
    token_jti: str
    token_value: str = Field(min_length=16)
    expires_at: datetime
    revoked_at: datetime | None = None
    last_used_at: datetime | None = None
    user_agent: str | None = None
    ip_address: str | None = None


class RefreshTokenUpdate(AppSchema):
    token_jti: str | None = None
    token_value: str | None = Field(default=None, min_length=16)
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    last_used_at: datetime | None = None
    user_agent: str | None = None
    ip_address: str | None = None


class RefreshTokenRead(AppSchema):
    token_jti: str
    expires_at: datetime
    revoked_at: datetime | None = None
    last_used_at: datetime | None = None
    user_agent: str | None = None
    ip_address: str | None = None
    created_at: datetime


class RegisterRequest(AppSchema):
    email: str
    password: str = Field(min_length=8)
    confirm_password: str = Field(min_length=8)

    @model_validator(mode="after")
    def validate_matching_passwords(self) -> "RegisterRequest":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        return self


class RegisterVerifyRequest(AppSchema):
    email: str
    otp: str = Field(min_length=4, max_length=12)


class LoginRequest(AppSchema):
    email: str
    password: str = Field(min_length=8)


class ForgotPasswordRequest(AppSchema):
    email: str


class ForgotPasswordVerifyRequest(AppSchema):
    email: str
    otp: str = Field(min_length=4, max_length=12)
    new_password: str = Field(min_length=8)
    confirm_new_password: str = Field(min_length=8)

    @model_validator(mode="after")
    def validate_matching_passwords(self) -> "ForgotPasswordVerifyRequest":
        if self.new_password != self.confirm_new_password:
            raise ValueError("Passwords do not match.")
        return self


class UserSettingsRead(AppSchema):
    language: Literal["en"] = "en"
    theme: Literal["light", "dark"] = "light"


class UserSettingsUpdate(AppSchema):
    language: Literal["en"] | None = None
    theme: Literal["light", "dark"] | None = None


class ChangePasswordRequest(AppSchema):
    current_password: str = Field(min_length=8)
    new_password: str = Field(min_length=8)
    confirm_new_password: str = Field(min_length=8)

    @model_validator(mode="after")
    def validate_matching_passwords(self) -> "ChangePasswordRequest":
        if self.new_password != self.confirm_new_password:
            raise ValueError("Passwords do not match.")
        return self


class DeleteAccountRequest(AppSchema):
    current_password: str = Field(min_length=8)


class AuthUserRead(AppSchema):
    email: str
    name: str
    settings: UserSettingsRead = Field(default_factory=UserSettingsRead)


class AuthMeRead(AppSchema):
    email: str
    name: str
    settings: UserSettingsRead = Field(default_factory=UserSettingsRead)


class OTPDeliveryResponse(AppSchema):
    email: str
    purpose: str
    expires_at: datetime
    message: str


class RegisterVerifyResponse(AppSchema):
    user: AuthUserRead
    message: str


class LoginResponse(AppSchema):
    access_token: str
    access_token_expires_at: datetime
    refresh_token: str
    refresh_token_expires_at: datetime
    token_type: str = "bearer"
    user: AuthUserRead


class MessageResponse(AppSchema):
    message: str


class NotebookCreate(AppSchema):
    title: str | None = None
    metadata: dict = Field(default_factory=dict)


class NotebookUpdate(AppSchema):
    title: str | None = None
    metadata: dict | None = None


class NotebookRead(AppSchema):
    id: UUID
    title: str | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


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
    notebook_id: UUID | None = None
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


class ChatHistorySourceRead(AppSchema):
    chunk_id: UUID
    document_id: UUID
    document_name: str | None = None
    original_file_name: str
    storage_key: str
    content: str
    chunk_index: int
    page_number: int | None = None
    page_from: int | None = None
    page_to: int | None = None
    quoted_text: str | None = None
    bbox: list[float] | None = None
    page_width: float | None = None
    page_height: float | None = None
    score: float | None = None
    source: str = "history"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatHistoryMessageRead(ChatMessageRead):
    sources: list[ChatHistorySourceRead] = Field(default_factory=list)


class ChatSessionDetailRead(ChatSessionRead):
    messages: list[ChatHistoryMessageRead] = Field(default_factory=list)


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


class RetrievalChunkRead(AppSchema):
    chunk_id: UUID
    document_id: UUID
    document_name: str | None = None
    original_file_name: str
    storage_key: str
    content: str
    chunk_index: int
    page_number: int | None = None
    page_from: int | None = None
    page_to: int | None = None
    quoted_text: str | None = None
    bbox: list[float] | None = None
    page_width: float | None = None
    page_height: float | None = None
    token_count: int | None = None
    character_count: int | None = None
    score: float | None = None
    source: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class CitationRead(AppSchema):
    document_id: UUID
    document_name: str
    page_number: int | None = None
    chunk_id: UUID
    chunk_index: int
    text: str
    quoted_text: str
    bbox: list[float] | None = None
    page_width: float | None = None
    page_height: float | None = None


class ChatbotAskRequest(AppSchema):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    notebook_id: UUID | None = None
    document_id: UUID | None = None
    document_ids: list[UUID] = Field(default_factory=list)
    session_id: UUID | None = None
    save_history: bool = True
    language: Literal["en"] | None = None


class ChatbotAskResponse(AppSchema):
    query: str
    answer: str
    notebook_id: UUID | None = None
    document_id: UUID | None = None
    document_ids: list[UUID] = Field(default_factory=list)
    document_names: list[str] = Field(default_factory=list)
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


class ChatbotSuggestionsRequest(AppSchema):
    notebook_id: UUID | None = None
    document_id: UUID | None = None
    document_ids: list[UUID] = Field(default_factory=list)
    language: Literal["en"] = "en"


class ChatbotSuggestionsResponse(AppSchema):
    title: str
    topics: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)


class ReindexResponse(AppSchema):
    reset_collection: bool
    document_count: int
    chunk_count: int
    collection_name: str
    embedding_model: str

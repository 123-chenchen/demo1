from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import AppSchema


class UserCreate(AppSchema):
    email: str
    password: str = Field(min_length=8)
    username: str | None = None
    full_name: str | None = None
    is_active: bool = True
    is_superuser: bool = False
    metadata: dict = Field(default_factory=dict)


class UserUpdate(AppSchema):
    email: str | None = None
    password: str | None = Field(default=None, min_length=8)
    username: str | None = None
    full_name: str | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None
    last_login_at: datetime | None = None
    metadata: dict | None = None


class UserRead(AppSchema):
    id: UUID
    email: str
    username: str | None = None
    full_name: str | None = None
    is_active: bool
    is_superuser: bool
    last_login_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


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
    id: UUID
    user_id: UUID
    token_jti: str
    expires_at: datetime
    revoked_at: datetime | None = None
    last_used_at: datetime | None = None
    user_agent: str | None = None
    ip_address: str | None = None
    created_at: datetime

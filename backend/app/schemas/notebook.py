from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import AppSchema


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

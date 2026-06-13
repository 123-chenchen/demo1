from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ChatMessage


@dataclass(frozen=True, slots=True)
class ConversationContext:
    query: str
    resolved_document_id: object | None
    selected_document_name: str | None
    has_document_reference: bool
    recent_messages: list[ChatMessage]


class ConversationContextService:
    _document_reference_pattern = re.compile(
        r"\b(n[oó]|cai nay|cái này|tai lieu nay|tài liệu này|file nay|file này|pdf nay|pdf này|o day|ở đây|this|it|this document|this file)\b",
        re.IGNORECASE,
    )

    def resolve(
        self,
        db: Session,
        *,
        query: str,
        selected_document=None,
        session_id=None,
    ) -> ConversationContext:
        recent_messages = self._load_recent_messages(db, session_id=session_id)
        resolved_document_id = getattr(selected_document, "id", None)

        if resolved_document_id is None:
            resolved_document_id = self._last_document_id_from_history(recent_messages)

        return ConversationContext(
            query=query,
            resolved_document_id=resolved_document_id,
            selected_document_name=getattr(selected_document, "original_file_name", None),
            has_document_reference=bool(self._document_reference_pattern.search(query)),
            recent_messages=recent_messages,
        )

    def _load_recent_messages(self, db: Session, *, session_id) -> list[ChatMessage]:
        if session_id is None:
            return []
        statement = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(8)
        )
        return list(reversed(db.scalars(statement).all()))

    def _last_document_id_from_history(self, messages: list[ChatMessage]):
        for message in reversed(messages):
            metadata = dict(message.extra_metadata or {})
            document_id = metadata.get("document_id")
            if document_id:
                return document_id
        return None


conversation_context_service = ConversationContextService()

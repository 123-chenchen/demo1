from __future__ import annotations

from app.crud.base import CRUDBase
from app.db.models import ChatMessage, ChatSession, MessageSource
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageUpdate,
    ChatSessionCreate,
    ChatSessionUpdate,
    MessageSourceCreate,
    MessageSourceUpdate,
)

chat_session_crud = CRUDBase(ChatSession)
chat_message_crud = CRUDBase(ChatMessage)
message_source_crud = CRUDBase(MessageSource)

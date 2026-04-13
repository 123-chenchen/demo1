from app.api.crud_router import create_crud_router
from app.crud import chat_message_crud, chat_session_crud, message_source_crud
from app.schemas import (
    ChatMessageCreate,
    ChatMessageRead,
    ChatMessageUpdate,
    ChatSessionCreate,
    ChatSessionRead,
    ChatSessionUpdate,
    MessageSourceCreate,
    MessageSourceRead,
    MessageSourceUpdate,
)

chat_sessions_router = create_crud_router(
    crud=chat_session_crud,
    create_schema=ChatSessionCreate,
    read_schema=ChatSessionRead,
    update_schema=ChatSessionUpdate,
    prefix="/chat-sessions",
    tags=["chat-sessions"],
    entity_name="chat_session",
)

chat_messages_router = create_crud_router(
    crud=chat_message_crud,
    create_schema=ChatMessageCreate,
    read_schema=ChatMessageRead,
    update_schema=ChatMessageUpdate,
    prefix="/chat-messages",
    tags=["chat-messages"],
    entity_name="chat_message",
)

message_sources_router = create_crud_router(
    crud=message_source_crud,
    create_schema=MessageSourceCreate,
    read_schema=MessageSourceRead,
    update_schema=MessageSourceUpdate,
    prefix="/message-sources",
    tags=["message-sources"],
    entity_name="message_source",
)

from fastapi import APIRouter

from app.api.routers.auth import refresh_tokens_router, users_router
from app.api.routers.chats import chat_messages_router, chat_sessions_router, message_sources_router
from app.api.routers.documents import (
    document_chunks_router,
    document_contents_router,
    document_upload_router,
    documents_router,
)

api_router = APIRouter()
api_router.include_router(users_router)
api_router.include_router(refresh_tokens_router)
api_router.include_router(document_upload_router)
api_router.include_router(documents_router)
api_router.include_router(document_contents_router)
api_router.include_router(document_chunks_router)
api_router.include_router(chat_sessions_router)
api_router.include_router(chat_messages_router)
api_router.include_router(message_sources_router)

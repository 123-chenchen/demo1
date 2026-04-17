from fastapi import APIRouter

from app.api.routers.auth import auth_router
from app.api.routers.chats import chat_sessions_router
from app.api.routers.documents import (
    document_contents_router,
    document_upload_router,
    documents_router,
)
from app.api.routers.notebooks import notebooks_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(notebooks_router)
api_router.include_router(document_upload_router)
api_router.include_router(documents_router)
api_router.include_router(document_contents_router)
api_router.include_router(chat_sessions_router)

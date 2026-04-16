from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.rag import ChatbotAskRequest, ChatbotAskResponse, ReindexResponse
from app.services.chatbot import ChatbotServiceError, chatbot_service
from app.services.retrieval import RetrievalIndexerError, retrieval_indexer_service, retrieval_service
from app.services.vector_store import VectorStoreError

rag_router = APIRouter(prefix="/rag", tags=["rag"])


@rag_router.get("/config", response_model=dict[str, object], response_model_by_alias=False)
def get_rag_config() -> dict[str, object]:
    return retrieval_service.describe()


@rag_router.post("/chat", response_model=ChatbotAskResponse, response_model_by_alias=False)
def ask_chatbot(
    payload: ChatbotAskRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        return chatbot_service.ask(db, request=payload)
    except ChatbotServiceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (VectorStoreError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@rag_router.post("/reindex", response_model=ReindexResponse, response_model_by_alias=False)
def reindex_retrieval_data(
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        return retrieval_indexer_service.reindex_all(db)
    except RetrievalIndexerError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_optional, get_db
from app.db.models import User
from app.schemas.rag import ChatbotAskRequest, ChatbotAskResponse

chatbot_router = APIRouter(prefix="/chatbot", tags=["chatbot"])


@chatbot_router.post("/ask", response_model=ChatbotAskResponse, response_model_by_alias=False)
def ask_chatbot(
    payload: ChatbotAskRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict[str, object]:
    from app.services.chatbot.service import (
        ChatbotServiceError,
        ChatbotServicePermissionError,
        chatbot_service,
    )

    try:
        return chatbot_service.ask(db, request=payload, current_user=current_user)
    except ChatbotServicePermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ChatbotServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.crud import CrudConflictError, chat_session_crud
from app.db.models import User
from app.schemas import ChatSessionCreate, ChatSessionRead, ChatSessionUpdate
from app.services.auth import AuthNotFoundError, auth_service

chat_sessions_router = APIRouter(prefix="/chat-sessions", tags=["chat-sessions"])


@chat_sessions_router.get("/", response_model=list[ChatSessionRead], response_model_by_alias=False)
def list_chat_sessions(
    notebook_id: UUID | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[object]:
    try:
        selected_notebook = auth_service.resolve_user_notebook(
            db,
            user=current_user,
            notebook_id=notebook_id,
        )
    except AuthNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return chat_session_crud.list_for_user(
        db,
        user_id=current_user.id,
        notebook_id=selected_notebook.id,
        skip=skip,
        limit=limit,
    )


@chat_sessions_router.post(
    "/",
    response_model=ChatSessionRead,
    response_model_by_alias=False,
    status_code=status.HTTP_201_CREATED,
)
def create_chat_session(
    payload: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> object:
    try:
        selected_notebook = auth_service.resolve_user_notebook(
            db,
            user=current_user,
            notebook_id=payload.notebook_id,
        )
        return chat_session_crud.create_for_notebook(
            db,
            notebook_id=selected_notebook.id,
            obj_in=payload,
        )
    except AuthNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CrudConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@chat_sessions_router.get("/{item_id}", response_model=ChatSessionRead, response_model_by_alias=False)
def get_chat_session(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> object:
    db_obj = chat_session_crud.get_for_user(db, obj_id=item_id, user_id=current_user.id)
    if db_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="chat session not found.",
        )
    return db_obj


@chat_sessions_router.patch("/{item_id}", response_model=ChatSessionRead, response_model_by_alias=False)
def update_chat_session(
    item_id: UUID,
    payload: ChatSessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> object:
    db_obj = chat_session_crud.get_for_user(db, obj_id=item_id, user_id=current_user.id)
    if db_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="chat session not found.",
        )
    try:
        return chat_session_crud.update_for_notebook(
            db,
            db_obj=db_obj,
            obj_in=payload,
        )
    except CrudConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@chat_sessions_router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_session(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    db_obj = chat_session_crud.get_for_user(db, obj_id=item_id, user_id=current_user.id)
    if db_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="chat session not found.",
        )
    try:
        chat_session_crud.delete(db, obj_id=item_id)
    except CrudConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.crud import CrudConflictError, notebook_crud
from app.db.models import User
from app.schemas import NotebookCreate, NotebookRead, NotebookUpdate

notebooks_router = APIRouter(prefix="/notebooks", tags=["notebooks"])


@notebooks_router.get("/", response_model=list[NotebookRead], response_model_by_alias=False)
def list_notebooks(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[object]:
    return notebook_crud.list_for_user(
        db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )


@notebooks_router.post(
    "/",
    response_model=NotebookRead,
    response_model_by_alias=False,
    status_code=status.HTTP_201_CREATED,
)
def create_notebook(
    payload: NotebookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> object:
    try:
        return notebook_crud.create_for_user(
            db,
            user_id=current_user.id,
            obj_in=payload,
        )
    except CrudConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@notebooks_router.get("/{item_id}", response_model=NotebookRead, response_model_by_alias=False)
def get_notebook(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> object:
    notebook = notebook_crud.get_for_user(db, obj_id=item_id, user_id=current_user.id)
    if notebook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="notebook not found.")
    return notebook


@notebooks_router.patch("/{item_id}", response_model=NotebookRead, response_model_by_alias=False)
def update_notebook(
    item_id: UUID,
    payload: NotebookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> object:
    notebook = notebook_crud.get_for_user(db, obj_id=item_id, user_id=current_user.id)
    if notebook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="notebook not found.")
    try:
        return notebook_crud.update(db, db_obj=notebook, obj_in=payload)
    except CrudConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

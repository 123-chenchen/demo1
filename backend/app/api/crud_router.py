from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.crud.base import CRUDBase, CrudConflictError


def create_crud_router(
    *,
    crud: CRUDBase,
    create_schema: type[BaseModel],
    read_schema: type[BaseModel],
    update_schema: type[BaseModel],
    prefix: str,
    tags: list[str],
    entity_name: str,
) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=tags)
    entity_label = entity_name.replace("-", " ")

    @router.get("/", response_model=list[read_schema], response_model_by_alias=False)
    def list_items(
        skip: int = Query(default=0, ge=0),
        limit: int = Query(default=100, ge=1, le=200),
        db: Session = Depends(get_db),
    ) -> list[Any]:
        return crud.list(db, skip=skip, limit=limit)

    list_items.__name__ = f"list_{entity_name}"

    @router.post(
        "/",
        response_model=read_schema,
        response_model_by_alias=False,
        status_code=status.HTTP_201_CREATED,
    )
    def create_item(
        payload: create_schema,
        db: Session = Depends(get_db),
    ) -> Any:
        try:
            return crud.create(db, obj_in=payload)
        except CrudConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    create_item.__name__ = f"create_{entity_name}"

    @router.get("/{item_id}", response_model=read_schema, response_model_by_alias=False)
    def get_item(
        item_id: UUID,
        db: Session = Depends(get_db),
    ) -> Any:
        db_obj = crud.get(db, obj_id=item_id)
        if db_obj is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{entity_label} not found.",
            )
        return db_obj

    get_item.__name__ = f"get_{entity_name}"

    @router.patch("/{item_id}", response_model=read_schema, response_model_by_alias=False)
    def update_item(
        item_id: UUID,
        payload: update_schema,
        db: Session = Depends(get_db),
    ) -> Any:
        db_obj = crud.get(db, obj_id=item_id)
        if db_obj is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{entity_label} not found.",
            )
        try:
            return crud.update(db, db_obj=db_obj, obj_in=payload)
        except CrudConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    update_item.__name__ = f"update_{entity_name}"

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_item(
        item_id: UUID,
        db: Session = Depends(get_db),
    ) -> Response:
        try:
            db_obj = crud.delete(db, obj_id=item_id)
        except CrudConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        if db_obj is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{entity_label} not found.",
            )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    delete_item.__name__ = f"delete_{entity_name}"

    return router

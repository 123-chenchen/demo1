from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_current_user_optional, get_db
from app.crud import CrudConflictError, document_content_crud, document_crud
from app.db.models import User
from app.schemas import (
    DocumentContentRead,
    DocumentRead,
    DocumentUpdate,
)
from app.services.document_upload import (
    DocumentUploadConflictError,
    DocumentUploadStorageError,
    DocumentUploadValidationError,
    document_upload_service,
)
from app.services.document_ingest import document_ingest_service
from app.services.auth import AuthNotFoundError, auth_service

document_upload_router = APIRouter(prefix="/documents", tags=["documents"])
documents_router = APIRouter(prefix="/documents", tags=["documents"])
document_contents_router = APIRouter(prefix="/document-contents", tags=["document-contents"])


def _resolve_selected_notebook_id(
    db: Session,
    *,
    current_user: User | None,
    notebook_id: UUID | None,
) -> UUID | None:
    if current_user is None:
        return None
    try:
        notebook = auth_service.resolve_user_notebook(
            db,
            user=current_user,
            notebook_id=notebook_id,
        )
    except AuthNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return notebook.id


@documents_router.get("/", response_model=list[DocumentRead], response_model_by_alias=False)
def list_documents(
    notebook_id: UUID | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> list[object]:
    if current_user is None:
        return document_crud.list_for_scope(
            db,
            notebook_id=None,
            skip=skip,
            limit=limit,
        )

    return document_crud.list_for_user(
        db,
        user_id=current_user.id,
        notebook_id=_resolve_selected_notebook_id(
            db,
            current_user=current_user,
            notebook_id=notebook_id,
        ),
        skip=skip,
        limit=limit,
    )


@documents_router.get("/{item_id}", response_model=DocumentRead, response_model_by_alias=False)
def get_document(
    item_id: UUID,
    notebook_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> object:
    if current_user is None:
        document = document_crud.get_for_scope(
            db,
            obj_id=item_id,
            notebook_id=None,
        )
    else:
        document = document_crud.get_for_user(
            db,
            obj_id=item_id,
            user_id=current_user.id,
            notebook_id=notebook_id,
        )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document not found.")
    return document


@documents_router.patch("/{item_id}", response_model=DocumentRead, response_model_by_alias=False)
def update_document(
    item_id: UUID,
    payload: DocumentUpdate,
    notebook_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> object:
    document = document_crud.get_for_user(
        db,
        obj_id=item_id,
        user_id=current_user.id,
        notebook_id=notebook_id,
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document not found.")
    try:
        return document_crud.update(db, db_obj=document, obj_in=payload)
    except CrudConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@documents_router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    item_id: UUID,
    notebook_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    document = document_crud.get_for_user(
        db,
        obj_id=item_id,
        user_id=current_user.id,
        notebook_id=notebook_id,
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document not found.")
    try:
        db.delete(document)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not delete Document because of a database constraint.",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@document_upload_router.post(
    "/upload",
    response_model=DocumentRead,
    response_model_by_alias=False,
    status_code=status.HTTP_201_CREATED,
)
def upload_document_pdf(
    file: UploadFile = File(...),
    notebook_id: UUID | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> DocumentRead:
    try:
        resolved_notebook_id = _resolve_selected_notebook_id(
            db,
            current_user=current_user,
            notebook_id=notebook_id,
        )
        return document_upload_service.upload_pdf(
            db,
            upload_file=file,
            notebook_id=resolved_notebook_id,
        )
    except DocumentUploadValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except DocumentUploadConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except DocumentUploadStorageError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@document_upload_router.post(
    "/{document_id}/ingest",
    response_model=DocumentRead,
    response_model_by_alias=False,
)
def ingest_document(
    document_id: UUID,
    notebook_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> DocumentRead:
    if current_user is None:
        document = document_crud.get_for_scope(
            db,
            obj_id=document_id,
            notebook_id=None,
        )
    else:
        document = document_crud.get_for_user(
            db,
            obj_id=document_id,
            user_id=current_user.id,
            notebook_id=notebook_id,
        )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document not found.")
    return document_ingest_service.ingest_document(db, document=document)


@document_contents_router.get("/", response_model=list[DocumentContentRead], response_model_by_alias=False)
def list_document_contents(
    notebook_id: UUID | None = Query(default=None),
    document_id: UUID | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> list[object]:
    if current_user is None:
        return document_content_crud.list_for_scope(
            db,
            notebook_id=None,
            document_id=document_id,
            skip=skip,
            limit=limit,
        )

    return document_content_crud.list_for_user(
        db,
        user_id=current_user.id,
        notebook_id=_resolve_selected_notebook_id(
            db,
            current_user=current_user,
            notebook_id=notebook_id,
        ),
        document_id=document_id,
        skip=skip,
        limit=limit,
    )


@document_contents_router.get("/{item_id}", response_model=DocumentContentRead, response_model_by_alias=False)
def get_document_content(
    item_id: UUID,
    notebook_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> object:
    if current_user is None:
        content = document_content_crud.get_for_scope(
            db,
            obj_id=item_id,
            notebook_id=None,
        )
    else:
        content = document_content_crud.get_for_user(
            db,
            obj_id=item_id,
            user_id=current_user.id,
            notebook_id=notebook_id,
        )
    if content is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document content not found.")
    return content

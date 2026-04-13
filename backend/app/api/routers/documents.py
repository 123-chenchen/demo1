from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.crud_router import create_crud_router
from app.api.dependencies import get_db
from app.crud import document_chunk_crud, document_content_crud, document_crud
from app.schemas import (
    DocumentChunkCreate,
    DocumentChunkRead,
    DocumentChunkUpdate,
    DocumentContentCreate,
    DocumentContentRead,
    DocumentContentUpdate,
    DocumentCreate,
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

document_upload_router = APIRouter(prefix="/documents", tags=["documents"])

documents_router = create_crud_router(
    crud=document_crud,
    create_schema=DocumentCreate,
    read_schema=DocumentRead,
    update_schema=DocumentUpdate,
    prefix="/documents",
    tags=["documents"],
    entity_name="document",
)

document_contents_router = create_crud_router(
    crud=document_content_crud,
    create_schema=DocumentContentCreate,
    read_schema=DocumentContentRead,
    update_schema=DocumentContentUpdate,
    prefix="/document-contents",
    tags=["document-contents"],
    entity_name="document_content",
)

document_chunks_router = create_crud_router(
    crud=document_chunk_crud,
    create_schema=DocumentChunkCreate,
    read_schema=DocumentChunkRead,
    update_schema=DocumentChunkUpdate,
    prefix="/document-chunks",
    tags=["document-chunks"],
    entity_name="document_chunk",
)


@document_upload_router.post(
    "/upload",
    response_model=DocumentRead,
    response_model_by_alias=False,
    status_code=status.HTTP_201_CREATED,
)
def upload_document_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentRead:
    try:
        return document_upload_service.upload_pdf(db, upload_file=file)
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
    db: Session = Depends(get_db),
) -> DocumentRead:
    document = document_ingest_service.ingest_document_by_id(db, document_id=document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document not found.")
    return document

from app.api.crud_router import create_crud_router
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

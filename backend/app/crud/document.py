from __future__ import annotations

from app.crud.base import CRUDBase
from app.db.models import Document, DocumentChunk, DocumentContent
from app.schemas.document import (
    DocumentChunkCreate,
    DocumentChunkUpdate,
    DocumentContentCreate,
    DocumentContentUpdate,
    DocumentCreate,
    DocumentUpdate,
)

document_crud = CRUDBase(Document)
document_content_crud = CRUDBase(DocumentContent)
document_chunk_crud = CRUDBase(DocumentChunk)

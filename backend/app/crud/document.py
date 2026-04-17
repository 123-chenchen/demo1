from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.db.models import Document, DocumentChunk, DocumentContent, Notebook
from app.schemas.document import (
    DocumentChunkCreate,
    DocumentChunkUpdate,
    DocumentContentCreate,
    DocumentContentUpdate,
    DocumentCreate,
    DocumentUpdate,
)


def _apply_document_scope(statement, *, notebook_id):
    if notebook_id is None:
        return statement.where(Document.notebook_id.is_(None))
    return statement.where(Document.notebook_id == notebook_id)


def _apply_user_document_scope(statement, *, user_id, notebook_id=None):
    statement = statement.join(Notebook, Document.notebook_id == Notebook.id).where(Notebook.user_id == user_id)
    if notebook_id is not None:
        statement = statement.where(Document.notebook_id == notebook_id)
    return statement


class DocumentCRUD(CRUDBase[Document, DocumentCreate, DocumentUpdate]):
    def list_for_scope(
        self,
        db: Session,
        *,
        notebook_id,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Document]:
        statement = _apply_document_scope(select(Document), notebook_id=notebook_id).offset(skip).limit(limit)
        return list(db.scalars(statement).all())

    def get_for_scope(self, db: Session, *, obj_id, notebook_id) -> Document | None:
        statement = _apply_document_scope(
            select(Document).where(Document.id == obj_id),
            notebook_id=notebook_id,
        )
        return db.scalar(statement)

    def list_for_user(
        self,
        db: Session,
        *,
        user_id,
        notebook_id=None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Document]:
        statement = _apply_user_document_scope(select(Document), user_id=user_id, notebook_id=notebook_id)
        statement = statement.offset(skip).limit(limit)
        return list(db.scalars(statement).all())

    def get_for_user(self, db: Session, *, obj_id, user_id, notebook_id=None) -> Document | None:
        statement = _apply_user_document_scope(
            select(Document).where(Document.id == obj_id),
            user_id=user_id,
            notebook_id=notebook_id,
        )
        return db.scalar(statement)


class DocumentContentCRUD(CRUDBase[DocumentContent, DocumentContentCreate, DocumentContentUpdate]):
    def list_for_scope(
        self,
        db: Session,
        *,
        notebook_id,
        document_id=None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[DocumentContent]:
        statement = select(DocumentContent).join(Document)
        statement = _apply_document_scope(statement, notebook_id=notebook_id)
        if document_id is not None:
            statement = statement.where(DocumentContent.document_id == document_id)
        statement = statement.offset(skip).limit(limit)
        return list(db.scalars(statement).all())

    def get_for_scope(self, db: Session, *, obj_id, notebook_id) -> DocumentContent | None:
        statement = (
            select(DocumentContent)
            .join(Document)
            .where(DocumentContent.id == obj_id)
        )
        statement = _apply_document_scope(statement, notebook_id=notebook_id)
        return db.scalar(statement)

    def list_for_user(
        self,
        db: Session,
        *,
        user_id,
        notebook_id=None,
        document_id=None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[DocumentContent]:
        statement = select(DocumentContent).join(Document)
        statement = _apply_user_document_scope(statement, user_id=user_id, notebook_id=notebook_id)
        if document_id is not None:
            statement = statement.where(DocumentContent.document_id == document_id)
        statement = statement.offset(skip).limit(limit)
        return list(db.scalars(statement).all())

    def get_for_user(self, db: Session, *, obj_id, user_id, notebook_id=None) -> DocumentContent | None:
        statement = (
            select(DocumentContent)
            .join(Document)
            .where(DocumentContent.id == obj_id)
        )
        statement = _apply_user_document_scope(statement, user_id=user_id, notebook_id=notebook_id)
        return db.scalar(statement)


class DocumentChunkCRUD(CRUDBase[DocumentChunk, DocumentChunkCreate, DocumentChunkUpdate]):
    def list_for_scope(
        self,
        db: Session,
        *,
        notebook_id,
        document_id=None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[DocumentChunk]:
        statement = select(DocumentChunk).join(Document)
        statement = _apply_document_scope(statement, notebook_id=notebook_id)
        if document_id is not None:
            statement = statement.where(DocumentChunk.document_id == document_id)
        statement = statement.offset(skip).limit(limit)
        return list(db.scalars(statement).all())

    def get_for_scope(self, db: Session, *, obj_id, notebook_id) -> DocumentChunk | None:
        statement = (
            select(DocumentChunk)
            .join(Document)
            .where(DocumentChunk.id == obj_id)
        )
        statement = _apply_document_scope(statement, notebook_id=notebook_id)
        return db.scalar(statement)

    def list_for_user(
        self,
        db: Session,
        *,
        user_id,
        notebook_id=None,
        document_id=None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[DocumentChunk]:
        statement = select(DocumentChunk).join(Document)
        statement = _apply_user_document_scope(statement, user_id=user_id, notebook_id=notebook_id)
        if document_id is not None:
            statement = statement.where(DocumentChunk.document_id == document_id)
        statement = statement.offset(skip).limit(limit)
        return list(db.scalars(statement).all())

    def get_for_user(self, db: Session, *, obj_id, user_id, notebook_id=None) -> DocumentChunk | None:
        statement = (
            select(DocumentChunk)
            .join(Document)
            .where(DocumentChunk.id == obj_id)
        )
        statement = _apply_user_document_scope(statement, user_id=user_id, notebook_id=notebook_id)
        return db.scalar(statement)


document_crud = DocumentCRUD(Document)
document_content_crud = DocumentContentCRUD(DocumentContent)
document_chunk_crud = DocumentChunkCRUD(DocumentChunk)

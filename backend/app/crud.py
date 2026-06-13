from __future__ import annotations

import hashlib
from typing import Any, Generic, TypeVar

import bcrypt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import (
    ChatMessage,
    ChatSession,
    Document,
    DocumentChunk,
    DocumentContent,
    MessageSource,
    Notebook,
    RefreshToken,
    User,
)
from app.schemas import (
    ChatMessageCreate,
    ChatMessageUpdate,
    ChatSessionCreate,
    ChatSessionUpdate,
    DocumentChunkCreate,
    DocumentChunkUpdate,
    DocumentContentCreate,
    DocumentContentUpdate,
    DocumentCreate,
    DocumentUpdate,
    MessageSourceCreate,
    MessageSourceUpdate,
    NotebookCreate,
    NotebookUpdate,
    RefreshTokenCreate,
    RefreshTokenUpdate,
    UserCreate,
    UserUpdate,
)

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CrudConflictError(Exception):
    pass


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: type[ModelType]):
        self.model = model

    def list(self, db: Session, *, skip: int = 0, limit: int = 100) -> list[ModelType]:
        statement = select(self.model).offset(skip).limit(limit)
        return list(db.scalars(statement).all())

    def get(self, db: Session, *, obj_id: Any) -> ModelType | None:
        return db.get(self.model, obj_id)

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        data = self._schema_to_dict(obj_in)
        db_obj = self.model(**data)
        db.add(db_obj)
        self._commit(db, action="create")
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType,
    ) -> ModelType:
        data = self._schema_to_dict(obj_in, exclude_unset=True)
        for field, value in data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        self._commit(db, action="update")
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, *, obj_id: Any) -> ModelType | None:
        db_obj = self.get(db, obj_id=obj_id)
        if db_obj is None:
            return None
        db.delete(db_obj)
        self._commit(db, action="delete")
        return db_obj

    def _schema_to_dict(self, obj_in: BaseModel, *, exclude_unset: bool = False) -> dict[str, Any]:
        if hasattr(obj_in, "to_model_dict"):
            return obj_in.to_model_dict(exclude_unset=exclude_unset)
        return obj_in.model_dump(exclude_unset=exclude_unset)

    def _commit(self, db: Session, *, action: str) -> None:
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise CrudConflictError(
                f"Could not {action} {self.model.__name__} because of a database constraint."
            ) from exc


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def hash_token(token_value: str) -> str:
    return hashlib.sha256(token_value.encode("utf-8")).hexdigest()


class UserCRUD(CRUDBase[User, UserCreate, UserUpdate]):
    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        data = obj_in.to_model_dict()
        password = data.pop("password")
        data["password_hash"] = hash_password(password)
        db_obj = self.model(**data)
        db.add(db_obj)
        self._commit(db, action="create")
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: User, obj_in: UserUpdate) -> User:
        data = obj_in.to_model_dict(exclude_unset=True)
        password = data.pop("password", None)
        if password:
            data["password_hash"] = hash_password(password)
        for field, value in data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        self._commit(db, action="update")
        db.refresh(db_obj)
        return db_obj


class RefreshTokenCRUD(CRUDBase[RefreshToken, RefreshTokenCreate, RefreshTokenUpdate]):
    def create(self, db: Session, *, obj_in: RefreshTokenCreate) -> RefreshToken:
        data = obj_in.to_model_dict()
        token_value = data.pop("token_value")
        data["token_hash"] = hash_token(token_value)
        db_obj = self.model(**data)
        db.add(db_obj)
        self._commit(db, action="create")
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: RefreshToken,
        obj_in: RefreshTokenUpdate,
    ) -> RefreshToken:
        data = obj_in.to_model_dict(exclude_unset=True)
        token_value = data.pop("token_value", None)
        if token_value:
            data["token_hash"] = hash_token(token_value)
        for field, value in data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        self._commit(db, action="update")
        db.refresh(db_obj)
        return db_obj


class NotebookCRUD(CRUDBase[Notebook, NotebookCreate, NotebookUpdate]):
    def list_for_user(
        self,
        db: Session,
        *,
        user_id,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Notebook]:
        statement = (
            select(Notebook)
            .where(Notebook.user_id == user_id)
            .order_by(Notebook.created_at.asc(), Notebook.id.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(statement).all())

    def get_for_user(self, db: Session, *, obj_id, user_id) -> Notebook | None:
        statement = select(Notebook).where(
            Notebook.id == obj_id,
            Notebook.user_id == user_id,
        )
        return db.scalar(statement)

    def get_default_for_user(self, db: Session, *, user_id) -> Notebook | None:
        statement = (
            select(Notebook)
            .where(Notebook.user_id == user_id)
            .order_by(Notebook.created_at.asc(), Notebook.id.asc())
            .limit(1)
        )
        return db.scalar(statement)

    def create_for_user(self, db: Session, *, user_id, obj_in: NotebookCreate) -> Notebook:
        data = obj_in.to_model_dict()
        db_obj = self.model(user_id=user_id, **data)
        db.add(db_obj)
        self._commit(db, action="create")
        db.refresh(db_obj)
        return db_obj


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


class ChatSessionCRUD(CRUDBase[ChatSession, ChatSessionCreate, ChatSessionUpdate]):
    def list_for_user(
        self,
        db: Session,
        *,
        user_id,
        notebook_id=None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ChatSession]:
        statement = select(ChatSession).join(Notebook).where(Notebook.user_id == user_id)
        if notebook_id is not None:
            statement = statement.where(ChatSession.notebook_id == notebook_id)
        statement = statement.order_by(ChatSession.updated_at.desc(), ChatSession.created_at.desc())
        statement = statement.offset(skip).limit(limit)
        return list(db.scalars(statement).all())

    def get_for_user(self, db: Session, *, obj_id, user_id, notebook_id=None) -> ChatSession | None:
        statement = select(ChatSession).join(Notebook).where(
            ChatSession.id == obj_id,
            Notebook.user_id == user_id,
        )
        if notebook_id is not None:
            statement = statement.where(ChatSession.notebook_id == notebook_id)
        return db.scalar(statement)

    def create_for_notebook(self, db: Session, *, notebook_id, obj_in: ChatSessionCreate) -> ChatSession:
        data = obj_in.to_model_dict()
        data.pop("notebook_id", None)
        db_obj = self.model(notebook_id=notebook_id, **data)
        db.add(db_obj)
        self._commit(db, action="create")
        db.refresh(db_obj)
        return db_obj

    def update_for_notebook(
        self,
        db: Session,
        *,
        db_obj: ChatSession,
        obj_in: ChatSessionUpdate,
    ) -> ChatSession:
        data = obj_in.to_model_dict(exclude_unset=True)
        for field, value in data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        self._commit(db, action="update")
        db.refresh(db_obj)
        return db_obj


user_crud = UserCRUD(User)
refresh_token_crud = RefreshTokenCRUD(RefreshToken)
notebook_crud = NotebookCRUD(Notebook)
document_crud = DocumentCRUD(Document)
document_content_crud = DocumentContentCRUD(DocumentContent)
document_chunk_crud = DocumentChunkCRUD(DocumentChunk)
chat_session_crud = ChatSessionCRUD(ChatSession)
chat_message_crud = CRUDBase(ChatMessage)
message_source_crud = CRUDBase(MessageSource)

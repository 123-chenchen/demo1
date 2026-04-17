from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.db.models import ChatMessage, ChatSession, MessageSource, Notebook
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageUpdate,
    ChatSessionCreate,
    ChatSessionUpdate,
    MessageSourceCreate,
    MessageSourceUpdate,
)


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


chat_session_crud = ChatSessionCRUD(ChatSession)
chat_message_crud = CRUDBase(ChatMessage)
message_source_crud = CRUDBase(MessageSource)

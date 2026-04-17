from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.db.models import Notebook
from app.schemas.notebook import NotebookCreate, NotebookUpdate


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


notebook_crud = NotebookCRUD(Notebook)

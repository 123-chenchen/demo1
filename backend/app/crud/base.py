from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base

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

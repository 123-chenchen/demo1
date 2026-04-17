from __future__ import annotations

import hashlib

import bcrypt
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.db.models import RefreshToken, User
from app.schemas.auth import (
    RefreshTokenCreate,
    RefreshTokenUpdate,
    UserCreate,
    UserUpdate,
)


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


user_crud = UserCRUD(User)
refresh_token_crud = RefreshTokenCRUD(RefreshToken)

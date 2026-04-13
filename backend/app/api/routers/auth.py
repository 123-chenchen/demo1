from app.api.crud_router import create_crud_router
from app.crud import refresh_token_crud, user_crud
from app.schemas import (
    RefreshTokenCreate,
    RefreshTokenRead,
    RefreshTokenUpdate,
    UserCreate,
    UserRead,
    UserUpdate,
)

users_router = create_crud_router(
    crud=user_crud,
    create_schema=UserCreate,
    read_schema=UserRead,
    update_schema=UserUpdate,
    prefix="/users",
    tags=["users"],
    entity_name="user",
)

refresh_tokens_router = create_crud_router(
    crud=refresh_token_crud,
    create_schema=RefreshTokenCreate,
    read_schema=RefreshTokenRead,
    update_schema=RefreshTokenUpdate,
    prefix="/refresh-tokens",
    tags=["refresh-tokens"],
    entity_name="refresh_token",
)

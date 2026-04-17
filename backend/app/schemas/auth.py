from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field, model_validator

from app.schemas.base import AppSchema


class UserCreate(AppSchema):
    email: str
    password: str = Field(min_length=8)
    is_verified: bool = False
    is_active: bool = True
    is_superuser: bool = False
    metadata: dict = Field(default_factory=dict)


class UserUpdate(AppSchema):
    email: str | None = None
    password: str | None = Field(default=None, min_length=8)
    is_verified: bool | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None
    last_login_at: datetime | None = None
    metadata: dict | None = None


class UserRead(AppSchema):
    email: str
    name: str


class RefreshTokenCreate(AppSchema):
    user_id: UUID
    token_jti: str
    token_value: str = Field(min_length=16)
    expires_at: datetime
    revoked_at: datetime | None = None
    last_used_at: datetime | None = None
    user_agent: str | None = None
    ip_address: str | None = None


class RefreshTokenUpdate(AppSchema):
    token_jti: str | None = None
    token_value: str | None = Field(default=None, min_length=16)
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    last_used_at: datetime | None = None
    user_agent: str | None = None
    ip_address: str | None = None


class RefreshTokenRead(AppSchema):
    token_jti: str
    expires_at: datetime
    revoked_at: datetime | None = None
    last_used_at: datetime | None = None
    user_agent: str | None = None
    ip_address: str | None = None
    created_at: datetime


class RegisterRequest(AppSchema):
    email: str
    password: str = Field(min_length=8)
    confirm_password: str = Field(min_length=8)

    @model_validator(mode="after")
    def validate_matching_passwords(self) -> "RegisterRequest":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        return self


class RegisterVerifyRequest(AppSchema):
    email: str
    otp: str = Field(min_length=4, max_length=12)


class LoginRequest(AppSchema):
    email: str
    password: str = Field(min_length=8)


class ForgotPasswordRequest(AppSchema):
    email: str


class ForgotPasswordVerifyRequest(AppSchema):
    email: str
    otp: str = Field(min_length=4, max_length=12)
    new_password: str = Field(min_length=8)
    confirm_new_password: str = Field(min_length=8)

    @model_validator(mode="after")
    def validate_matching_passwords(self) -> "ForgotPasswordVerifyRequest":
        if self.new_password != self.confirm_new_password:
            raise ValueError("Passwords do not match.")
        return self


class AuthUserRead(AppSchema):
    email: str
    name: str


class AuthMeRead(AppSchema):
    email: str
    name: str


class OTPDeliveryResponse(AppSchema):
    email: str
    purpose: str
    expires_at: datetime
    message: str


class RegisterVerifyResponse(AppSchema):
    user: AuthUserRead
    message: str


class LoginResponse(AppSchema):
    access_token: str
    access_token_expires_at: datetime
    refresh_token: str
    refresh_token_expires_at: datetime
    token_type: str = "bearer"
    user: AuthUserRead


class MessageResponse(AppSchema):
    message: str

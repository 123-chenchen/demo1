from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services.auth import (
    AuthAuthenticationError,
    AuthConflictError,
    AuthForbiddenError,
    AuthNotFoundError,
    AuthValidationError,
    auth_service,
)


def _auth_user_payload() -> dict[str, object]:
    now = datetime.now(timezone.utc)
    return {
        "id": uuid4(),
        "email": "user@example.com",
        "name": "User",
        "is_verified": True,
        "created_at": now,
        "updated_at": now,
    }


def test_register_request_returns_otp_delivery_payload(client, override_db, monkeypatch) -> None:
    override_db()

    def fake_request_register(db, *, email, password):
        assert email == "user@example.com"
        assert password == "StrongPass1"
        return {
            "email": email,
            "purpose": "register",
            "expires_at": datetime.now(timezone.utc),
            "message": "OTP has been sent to your email.",
        }

    monkeypatch.setattr(auth_service, "request_register", fake_request_register)

    response = client.post(
        "/api/auth/register/request",
        json={
            "email": "user@example.com",
            "password": "StrongPass1",
            "confirm_password": "StrongPass1",
        },
    )

    assert response.status_code == 200
    assert response.json()["purpose"] == "register"


def test_register_request_maps_conflicts_to_http_409(client, override_db, monkeypatch) -> None:
    override_db()

    def fake_request_register(db, *, email, password):
        raise AuthConflictError("Email already exists.")

    monkeypatch.setattr(auth_service, "request_register", fake_request_register)

    response = client.post(
        "/api/auth/register/request",
        json={
            "email": "user@example.com",
            "password": "StrongPass1",
            "confirm_password": "StrongPass1",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Email already exists."


def test_register_verify_returns_created_user(client, override_db, monkeypatch) -> None:
    override_db()

    def fake_verify_register(db, *, email, otp):
        assert email == "user@example.com"
        assert otp == "123456"
        return {
            "user": _auth_user_payload(),
            "message": "Registration completed successfully.",
        }

    monkeypatch.setattr(auth_service, "verify_register", fake_verify_register)

    response = client.post(
        "/api/auth/register/verify",
        json={
            "email": "user@example.com",
            "otp": "123456",
        },
    )

    assert response.status_code == 201
    assert response.json()["user"]["email"] == "user@example.com"


def test_auth_me_returns_authenticated_user(client, override_db, monkeypatch) -> None:
    override_db()
    now = datetime.now(timezone.utc)

    def fake_get_current_user_from_access_token(db, *, token):
        assert token == "access-token"
        return SimpleNamespace(
            id=uuid4(),
            email="user@example.com",
            is_verified=True,
            created_at=now,
            updated_at=now,
        )

    monkeypatch.setattr(auth_service, "get_current_user_from_access_token", fake_get_current_user_from_access_token)

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"email": "user@example.com", "name": "User"}


def test_auth_me_requires_authentication(client, override_db) -> None:
    override_db()

    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_login_returns_tokens(client, override_db, monkeypatch) -> None:
    override_db()

    def fake_login(db, *, email, password, user_agent, ip_address):
        assert email == "user@example.com"
        assert password == "StrongPass1"
        assert user_agent == "pytest-agent"
        assert ip_address
        return {
            "access_token": "access-token",
            "access_token_expires_at": datetime.now(timezone.utc),
            "refresh_token": "refresh-token",
            "refresh_token_expires_at": datetime.now(timezone.utc),
            "token_type": "bearer",
            "user": _auth_user_payload(),
        }

    monkeypatch.setattr(auth_service, "login", fake_login)

    response = client.post(
        "/api/auth/login",
        json={
            "email": "user@example.com",
            "password": "StrongPass1",
        },
        headers={"User-Agent": "pytest-agent"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "access-token"
    assert response.json()["refresh_token"] == "refresh-token"


def test_login_maps_unverified_users_to_http_403(client, override_db, monkeypatch) -> None:
    override_db()

    def fake_login(db, *, email, password, user_agent, ip_address):
        raise AuthForbiddenError("Email has not been verified.")

    monkeypatch.setattr(auth_service, "login", fake_login)

    response = client.post(
        "/api/auth/login",
        json={
            "email": "user@example.com",
            "password": "StrongPass1",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Email has not been verified."


def test_login_maps_invalid_credentials_to_http_401(client, override_db, monkeypatch) -> None:
    override_db()

    def fake_login(db, *, email, password, user_agent, ip_address):
        raise AuthAuthenticationError("Invalid email or password.")

    monkeypatch.setattr(auth_service, "login", fake_login)

    response = client.post(
        "/api/auth/login",
        json={
            "email": "user@example.com",
            "password": "StrongPass1",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_forgot_password_request_maps_missing_users_to_http_404(client, override_db, monkeypatch) -> None:
    override_db()

    def fake_request_forgot_password(db, *, email):
        raise AuthNotFoundError("User not found.")

    monkeypatch.setattr(auth_service, "request_forgot_password", fake_request_forgot_password)

    response = client.post(
        "/api/auth/forgot-password/request",
        json={
            "email": "user@example.com",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found."


def test_forgot_password_verify_returns_success_message(client, override_db, monkeypatch) -> None:
    override_db()

    def fake_verify_forgot_password(db, *, email, otp, new_password):
        assert email == "user@example.com"
        assert otp == "654321"
        assert new_password == "NewStrongPass1"
        return {
            "message": "Password has been reset successfully.",
        }

    monkeypatch.setattr(auth_service, "verify_forgot_password", fake_verify_forgot_password)

    response = client.post(
        "/api/auth/forgot-password/verify",
        json={
            "email": "user@example.com",
            "otp": "654321",
            "new_password": "NewStrongPass1",
            "confirm_new_password": "NewStrongPass1",
        },
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Password has been reset successfully."


def test_forgot_password_verify_maps_invalid_otp_to_http_400(client, override_db, monkeypatch) -> None:
    override_db()

    def fake_verify_forgot_password(db, *, email, otp, new_password):
        raise AuthValidationError("OTP is invalid.")

    monkeypatch.setattr(auth_service, "verify_forgot_password", fake_verify_forgot_password)

    response = client.post(
        "/api/auth/forgot-password/verify",
        json={
            "email": "user@example.com",
            "otp": "654321",
            "new_password": "NewStrongPass1",
            "confirm_new_password": "NewStrongPass1",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "OTP is invalid."

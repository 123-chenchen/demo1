from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.crud import hash_password, verify_password
from app.services.auth import (
    AuthAuthenticationError,
    AuthValidationError,
    REGISTER_OTP_PURPOSE,
    _build_name_from_email,
    _build_otp_email_message,
    _generate_otp_code,
    _resolve_user_display_name,
    _smtp_password_for_login,
    _validate_email_format,
    _validate_password_strength,
    auth_service,
)


def test_validate_email_format_normalizes_case_and_whitespace() -> None:
    assert _validate_email_format("  USER@Example.COM ") == "user@example.com"


def test_validate_email_format_rejects_invalid_email() -> None:
    with pytest.raises(AuthValidationError, match="Email format is invalid."):
        _validate_email_format("not-an-email")


def test_validate_password_strength_accepts_upper_lower_and_digit() -> None:
    _validate_password_strength("StrongPass1")


def test_validate_password_strength_rejects_weak_password() -> None:
    with pytest.raises(AuthValidationError, match="Password must contain"):
        _validate_password_strength("weakpass")


def test_generate_otp_code_returns_requested_length_digits() -> None:
    otp_code = _generate_otp_code(6)

    assert len(otp_code) == 6
    assert otp_code.isdigit()


def test_build_name_from_email_uses_gmail_local_part() -> None:
    assert _build_name_from_email("nguyen.van.a+demo@gmail.com") == "Nguyen Van A"


def test_resolve_user_display_name_prefers_user_name() -> None:
    user = SimpleNamespace(
        email="fallback.name@gmail.com",
        name="Gmail Profile Name",
        full_name="Full Name",
        extra_metadata={"google_profile": {"name": "Google Metadata Name"}},
    )

    assert _resolve_user_display_name(user) == "Gmail Profile Name"


def test_resolve_user_display_name_uses_google_profile_before_email_prefix() -> None:
    user = SimpleNamespace(
        email="fallback.name+demo@gmail.com",
        name=None,
        full_name=None,
        extra_metadata={"google_profile": {"name": "Google Metadata Name"}},
    )

    assert _resolve_user_display_name(user) == "Google Metadata Name"


def test_resolve_user_display_name_falls_back_to_email_prefix() -> None:
    user = SimpleNamespace(
        email="fallback.name+demo@gmail.com",
        name=None,
        full_name=None,
        extra_metadata={},
    )

    assert _resolve_user_display_name(user) == "Fallback Name"


def test_resolve_user_display_name_ignores_non_dict_sqlalchemy_metadata() -> None:
    user = SimpleNamespace(
        email="fallback.name+demo@gmail.com",
        name=None,
        full_name=None,
        extra_metadata={},
        metadata=object(),
    )

    assert _resolve_user_display_name(user) == "Fallback Name"


def test_build_otp_email_message_contains_otp_and_purpose(monkeypatch) -> None:
    class FakeSettings:
        smtp_from_email = "noreply@example.com"
        smtp_username = "noreply@example.com"
        smtp_password = "secret"

    monkeypatch.setattr("app.services.auth.service.get_settings", lambda: FakeSettings())

    message = _build_otp_email_message(
        email="user@example.com",
        otp_code="123456",
        purpose=REGISTER_OTP_PURPOSE,
        expires_at=datetime(2026, 4, 16, 10, 0, tzinfo=timezone.utc),
    )

    assert message["To"] == "user@example.com"
    assert message["Subject"] == "Your OTP code for registration"
    assert "123456" in message.get_content()


def test_smtp_password_for_login_removes_gmail_app_password_spaces(monkeypatch) -> None:
    class FakeSettings:
        smtp_host = "smtp.gmail.com"
        smtp_password = "abcd efgh ijkl mnop"

    monkeypatch.setattr("app.services.auth.service.get_settings", lambda: FakeSettings())

    assert _smtp_password_for_login() == "abcdefghijklmnop"


def test_verify_password_matches_generated_hash() -> None:
    password_hash = hash_password("StrongPass1")

    assert verify_password("StrongPass1", password_hash) is True
    assert verify_password("WrongPass1", password_hash) is False


class _ScalarResult:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values


class _DeleteAccountDB:
    def __init__(self, scalar_batches):
        self._scalar_batches = list(scalar_batches)
        self.deleted = []
        self.flush_count = 0
        self.committed = False
        self.rolled_back = False

    def scalars(self, statement):
        del statement
        return _ScalarResult(self._scalar_batches.pop(0))

    def delete(self, value):
        self.deleted.append(value)

    def flush(self):
        self.flush_count += 1

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def test_delete_account_hard_deletes_owned_db_records_before_user() -> None:
    notebook_id = "notebook-id"
    chat_session = SimpleNamespace(id="chat-session")
    document = SimpleNamespace(id="document")
    notebook = SimpleNamespace(id=notebook_id)
    user = SimpleNamespace(
        id="user-id",
        email="delete.me@example.com",
        password_hash=hash_password("StrongPass1"),
    )
    db = _DeleteAccountDB([
        [notebook_id],
        [chat_session],
        [document],
        [notebook],
    ])

    result = auth_service.delete_account(db, user=user, current_password="StrongPass1")

    assert result["message"] == "Account has been deleted successfully."
    assert db.deleted == [chat_session, document, notebook, user]
    assert db.flush_count == 2
    assert db.committed is True
    assert db.rolled_back is False


def test_deleted_user_access_token_is_rejected() -> None:
    user = SimpleNamespace(id=uuid4(), email="deleted.user@example.com")
    access_token, _expires_at = auth_service.create_access_token(user)

    class DeletedUserDB:
        def scalar(self, statement):
            del statement
            return None

    with pytest.raises(AuthAuthenticationError, match="Authenticated user was not found."):
        auth_service.get_current_user_from_access_token(DeletedUserDB(), token=access_token)

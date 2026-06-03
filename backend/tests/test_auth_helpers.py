from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.crud import hash_password, verify_password
from app.services.auth import (
    AuthValidationError,
    REGISTER_OTP_PURPOSE,
    _build_name_from_email,
    _build_otp_email_message,
    _generate_otp_code,
    _smtp_password_for_login,
    _validate_email_format,
    _validate_password_strength,
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

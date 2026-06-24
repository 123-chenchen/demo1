from __future__ import annotations

import re
import secrets
import smtplib
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from uuid import UUID
from uuid import uuid4

import jwt
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.crud import hash_password, hash_token, verify_password
from app.db.models import ChatSession, Document, EmailOTP, Notebook, PendingRegistration, RefreshToken, User

REGISTER_OTP_PURPOSE = "register"
RESET_PASSWORD_OTP_PURPOSE = "reset_password"
EMAIL_REGEX = re.compile(r"^[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,63}$", re.IGNORECASE)


class AuthValidationError(Exception):
    pass


class AuthConflictError(Exception):
    pass


class AuthAuthenticationError(Exception):
    pass


class AuthForbiddenError(Exception):
    pass


class AuthNotFoundError(Exception):
    pass


class AuthDeliveryError(Exception):
    pass


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _validate_email_format(email: str) -> str:
    normalized_email = _normalize_email(email)
    if not normalized_email or not EMAIL_REGEX.fullmatch(normalized_email):
        raise AuthValidationError("Email format is invalid.")
    return normalized_email


def _validate_password_strength(password: str) -> None:
    checks = [
        (len(password) >= 8, "at least 8 characters"),
        (any(char.islower() for char in password), "one lowercase letter"),
        (any(char.isupper() for char in password), "one uppercase letter"),
        (any(char.isdigit() for char in password), "one digit"),
    ]
    missing_rules = [label for passed, label in checks if not passed]
    if missing_rules:
        raise AuthValidationError(
            "Password must contain " + ", ".join(missing_rules) + "."
        )


def _generate_otp_code(length: int) -> str:
    final_length = max(4, length)
    digits = "0123456789"
    return "".join(secrets.choice(digits) for _ in range(final_length))


def _truncate(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    return value[:max_length]


def _build_auth_user_payload(user: User) -> dict[str, object]:
    return {
        "id": user.id,
        "email": user.email,
        "name": _resolve_user_display_name(user),
        "settings": _settings_from_metadata(user.extra_metadata),
        "is_verified": user.is_verified,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


def _clean_display_name(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def _profile_display_name(profile: object) -> str | None:
    if not isinstance(profile, dict):
        return None

    for key in ("name", "full_name", "display_name"):
        resolved = _clean_display_name(profile.get(key))
        if resolved:
            return resolved

    joined_name = _clean_display_name(" ".join(
        part for part in (
            _clean_display_name(profile.get("given_name")),
            _clean_display_name(profile.get("family_name")),
        )
        if part
    ))
    return joined_name


def _metadata_dict(metadata: object) -> dict:
    if isinstance(metadata, Mapping):
        return dict(metadata)
    return {}


def _metadata_display_name(metadata: object) -> str | None:
    data = _metadata_dict(metadata)

    for key in ("name", "full_name", "display_name"):
        resolved = _clean_display_name(data.get(key))
        if resolved:
            return resolved

    for key in ("google_profile", "googleProfile", "google", "profile", "oauth_profile", "oauthProfile"):
        resolved = _profile_display_name(data.get(key))
        if resolved:
            return resolved

    return None


def _resolve_user_display_name(user: object) -> str:
    for key in ("name", "full_name"):
        resolved = _clean_display_name(getattr(user, key, None))
        if resolved:
            return resolved

    metadata = getattr(user, "extra_metadata", None)
    if metadata is None:
        metadata = getattr(user, "metadata", None)
    resolved = _metadata_display_name(metadata)
    if resolved:
        return resolved

    return _build_name_from_email(str(getattr(user, "email", "") or ""))


def _build_name_from_email(email: str) -> str:
    local_part = email.split("@", 1)[0].strip()
    alias_free_local_part = local_part.split("+", 1)[0].strip() or local_part
    tokens = [token for token in re.split(r"[._-]+", alias_free_local_part) if token]

    if not tokens:
        return email

    def _normalize_token(token: str) -> str:
        if token.isdigit():
            return token
        return token[:1].upper() + token[1:].lower()

    return " ".join(_normalize_token(token) for token in tokens)


def _build_default_notebook_title(email: str) -> str:
    display_name = _build_name_from_email(email).strip()
    if not display_name or display_name == email:
        return "My Notebook"
    return f"{display_name}'s notebook"


def _settings_from_metadata(metadata: object) -> dict[str, str]:
    raw_settings = _metadata_dict(metadata).get("settings") or {}
    if not isinstance(raw_settings, Mapping):
        raw_settings = {}
    raw_settings = dict(raw_settings)
    language = raw_settings.get("language")
    theme = raw_settings.get("theme")
    return {
        "language": "en",
        "theme": theme if theme in {"light", "dark"} else "light",
    }


def _build_otp_email_message(*, email: str, otp_code: str, purpose: str, expires_at: datetime) -> EmailMessage:
    settings = get_settings()
    sender_email = settings.smtp_from_email or settings.smtp_username
    if not sender_email or not settings.smtp_username or not settings.smtp_password:
        raise AuthDeliveryError("SMTP credentials are not configured.")

    purpose_label = "registration" if purpose == REGISTER_OTP_PURPOSE else "password reset"
    subject = f"Your OTP code for {purpose_label}"
    expires_label = expires_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    message = EmailMessage()
    message["From"] = sender_email
    message["To"] = email
    message["Subject"] = subject
    message.set_content(
        "\n".join(
            [
                f"Your OTP code for {purpose_label} is: {otp_code}",
                "",
                f"This code expires at {expires_label}.",
                "If you did not request this code, you can ignore this email.",
            ]
        )
    )
    return message


def _smtp_password_for_login() -> str:
    settings = get_settings()
    password = settings.smtp_password or ""
    if settings.smtp_host.lower() == "smtp.gmail.com":
        return "".join(password.split())
    return password


class OTPEmailSender:
    def send_otp(self, *, email: str, otp_code: str, purpose: str, expires_at: datetime) -> None:
        settings = get_settings()
        message = _build_otp_email_message(
            email=email,
            otp_code=otp_code,
            purpose=purpose,
            expires_at=expires_at,
        )

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
                server.ehlo()
                if settings.smtp_starttls:
                    server.starttls()
                    server.ehlo()
                server.login(settings.smtp_username, _smtp_password_for_login())
                server.send_message(message)
        except (AuthDeliveryError, OSError, smtplib.SMTPException) as exc:
            if isinstance(exc, AuthDeliveryError):
                raise
            raise AuthDeliveryError("Could not send OTP email.") from exc


class AuthService:
    def __init__(self) -> None:
        self.email_sender = OTPEmailSender()

    def build_name_from_email(self, email: str) -> str:
        return _build_name_from_email(email)

    def resolve_user_display_name(self, user: object) -> str:
        return _resolve_user_display_name(user)

    def request_register(self, db: Session, *, email: str, password: str) -> dict[str, object]:
        normalized_email = _validate_email_format(email)
        _validate_password_strength(password)
        if self._get_user_by_email(db, normalized_email) is not None:
            raise AuthConflictError("Email already exists.")

        expires_at = self._otp_expires_at()
        otp_code = _generate_otp_code(get_settings().otp_length)

        pending_registration = db.scalar(
            select(PendingRegistration).where(PendingRegistration.email == normalized_email)
        )
        if pending_registration is None:
            pending_registration = PendingRegistration(
                email=normalized_email,
                password_hash=hash_password(password),
                expires_at=expires_at,
            )
            db.add(pending_registration)
        else:
            pending_registration.password_hash = hash_password(password)
            pending_registration.expires_at = expires_at
            db.add(pending_registration)

        self._replace_active_otp(
            db,
            email=normalized_email,
            purpose=REGISTER_OTP_PURPOSE,
            otp_code=otp_code,
            expires_at=expires_at,
        )

        self._flush_send_and_commit(
            db,
            email=normalized_email,
            otp_code=otp_code,
            purpose=REGISTER_OTP_PURPOSE,
            expires_at=expires_at,
            conflict_message="Could not prepare the registration OTP.",
        )

        return {
            "email": normalized_email,
            "purpose": REGISTER_OTP_PURPOSE,
            "expires_at": expires_at,
            "message": "OTP has been sent to your email.",
        }

    def verify_register(self, db: Session, *, email: str, otp: str) -> dict[str, object]:
        normalized_email = _validate_email_format(email)
        if self._get_user_by_email(db, normalized_email) is not None:
            raise AuthConflictError("Email already exists.")

        pending_registration = db.scalar(
            select(PendingRegistration).where(PendingRegistration.email == normalized_email)
        )
        if pending_registration is None:
            raise AuthValidationError("Registration request was not found.")
        if pending_registration.expires_at < _now_utc():
            raise AuthValidationError("Registration request has expired.")

        otp_record = self._validate_otp(
            db,
            email=normalized_email,
            purpose=REGISTER_OTP_PURPOSE,
            otp=otp,
        )

        user = User(
            email=normalized_email,
            password_hash=pending_registration.password_hash,
            is_verified=True,
            is_active=True,
            is_superuser=False,
            extra_metadata={},
        )
        db.add(user)
        db.flush()
        self.ensure_user_default_notebook(db, user=user)
        otp_record.is_used = True
        db.add(otp_record)
        db.delete(pending_registration)

        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise AuthConflictError("Could not create the verified user.") from exc

        db.refresh(user)
        return {
            "user": _build_auth_user_payload(user),
            "message": "Registration completed successfully.",
        }

    def login(
        self,
        db: Session,
        *,
        email: str,
        password: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> dict[str, object]:
        normalized_email = _validate_email_format(email)
        user = self._get_user_by_email(db, normalized_email)
        if user is None or not verify_password(password, user.password_hash):
            raise AuthAuthenticationError("Invalid email or password.")
        if not user.is_verified:
            raise AuthForbiddenError("Email has not been verified.")

        access_token, access_token_expires_at = self.create_access_token(user)
        refresh_token_expires_at = _now_utc() + timedelta(days=get_settings().refresh_token_expire_days)
        refresh_token_value = secrets.token_urlsafe(48)

        refresh_token = RefreshToken(
            user_id=user.id,
            token_jti=str(uuid4()),
            token_hash=hash_token(refresh_token_value),
            expires_at=refresh_token_expires_at,
            user_agent=_truncate(user_agent, 512),
            ip_address=_truncate(ip_address, 64),
        )
        user.last_login_at = _now_utc()
        db.add(user)
        db.add(refresh_token)

        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise AuthConflictError("Could not create login tokens.") from exc

        db.refresh(user)
        return {
            "access_token": access_token,
            "access_token_expires_at": access_token_expires_at,
            "refresh_token": refresh_token_value,
            "refresh_token_expires_at": refresh_token_expires_at,
            "token_type": "bearer",
            "user": _build_auth_user_payload(user),
        }

    def create_access_token(self, user: User) -> tuple[str, datetime]:
        now = _now_utc()
        expires_at = now + timedelta(minutes=get_settings().access_token_expire_minutes)
        access_token = jwt.encode(
            {
                "sub": str(user.id),
                "email": user.email,
                "token_type": "access",
                "iat": now,
                "exp": expires_at,
            },
            get_settings().jwt_secret_key,
            algorithm=get_settings().jwt_algorithm,
        )
        return access_token, expires_at

    def get_current_user_from_access_token(self, db: Session, *, token: str) -> User:
        try:
            payload = jwt.decode(
                token,
                get_settings().jwt_secret_key,
                algorithms=[get_settings().jwt_algorithm],
            )
        except jwt.PyJWTError as exc:
            raise AuthAuthenticationError("Invalid access token.") from exc

        if payload.get("token_type") != "access":
            raise AuthAuthenticationError("Invalid access token.")

        subject = payload.get("sub")
        if not subject:
            raise AuthAuthenticationError("Invalid access token.")

        try:
            user_id = UUID(str(subject))
        except ValueError as exc:
            raise AuthAuthenticationError("Invalid access token.") from exc

        user = db.scalar(select(User).where(User.id == user_id))
        if user is None:
            raise AuthAuthenticationError("Authenticated user was not found.")
        if not user.is_active:
            raise AuthAuthenticationError("Authenticated user is inactive.")
        if self.get_default_user_notebook(db, user_id=user.id) is None:
            self.ensure_user_default_notebook(db, user=user)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                raise AuthAuthenticationError("Could not initialize the authenticated user notebook.")
            db.refresh(user)
        return user

    def request_forgot_password(self, db: Session, *, email: str) -> dict[str, object]:
        normalized_email = _validate_email_format(email)
        user = self._get_user_by_email(db, normalized_email)
        if user is None:
            raise AuthNotFoundError("User not found.")

        expires_at = self._otp_expires_at()
        otp_code = _generate_otp_code(get_settings().otp_length)
        self._replace_active_otp(
            db,
            email=normalized_email,
            purpose=RESET_PASSWORD_OTP_PURPOSE,
            otp_code=otp_code,
            expires_at=expires_at,
        )

        self._flush_send_and_commit(
            db,
            email=normalized_email,
            otp_code=otp_code,
            purpose=RESET_PASSWORD_OTP_PURPOSE,
            expires_at=expires_at,
            conflict_message="Could not prepare the reset password OTP.",
        )

        return {
            "email": normalized_email,
            "purpose": RESET_PASSWORD_OTP_PURPOSE,
            "expires_at": expires_at,
            "message": "OTP has been sent to your email.",
        }

    def verify_forgot_password(
        self,
        db: Session,
        *,
        email: str,
        otp: str,
        new_password: str,
    ) -> dict[str, object]:
        normalized_email = _validate_email_format(email)
        _validate_password_strength(new_password)

        user = self._get_user_by_email(db, normalized_email)
        if user is None:
            raise AuthNotFoundError("User not found.")

        otp_record = self._validate_otp(
            db,
            email=normalized_email,
            purpose=RESET_PASSWORD_OTP_PURPOSE,
            otp=otp,
        )

        user.password_hash = hash_password(new_password)
        otp_record.is_used = True
        db.add(user)
        db.add(otp_record)
        db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=_now_utc())
        )

        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise AuthConflictError("Could not reset the password.") from exc

        return {
            "message": "Password has been reset successfully.",
        }

    def get_user_settings(self, user: User) -> dict[str, str]:
        return _settings_from_metadata(getattr(user, "extra_metadata", None))

    def update_user_settings(
        self,
        db: Session,
        *,
        user: User,
        language: str | None = None,
        theme: str | None = None,
    ) -> dict[str, str]:
        next_settings = self.get_user_settings(user)
        if language is not None:
            next_settings["language"] = language
        if theme is not None:
            next_settings["theme"] = theme

        metadata = dict(user.extra_metadata or {})
        metadata["settings"] = next_settings
        user.extra_metadata = metadata
        db.add(user)

        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise AuthConflictError("Could not update user settings.") from exc

        db.refresh(user)
        return self.get_user_settings(user)

    def change_password(
        self,
        db: Session,
        *,
        user: User,
        current_password: str,
        new_password: str,
    ) -> dict[str, str]:
        if not verify_password(current_password, user.password_hash):
            raise AuthAuthenticationError("Current password is incorrect.")
        _validate_password_strength(new_password)

        user.password_hash = hash_password(new_password)
        db.add(user)
        db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=_now_utc())
        )

        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise AuthConflictError("Could not change the password.") from exc

        return {"message": "Password has been changed successfully."}

    def delete_account(
        self,
        db: Session,
        *,
        user: User,
        current_password: str,
    ) -> dict[str, str]:
        if not verify_password(current_password, user.password_hash):
            raise AuthAuthenticationError("Current password is incorrect.")

        try:
            self._delete_user_owned_data(db, user=user)
            db.delete(user)
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise AuthConflictError("Could not delete the account.") from exc

        return {"message": "Account has been deleted successfully."}

    def _delete_user_owned_data(self, db: Session, *, user: User) -> None:
        notebook_ids = list(db.scalars(select(Notebook.id).where(Notebook.user_id == user.id)).all())
        if not notebook_ids:
            return

        chat_sessions = list(
            db.scalars(
                select(ChatSession).where(ChatSession.notebook_id.in_(notebook_ids))
            ).all()
        )
        for session in chat_sessions:
            db.delete(session)
        db.flush()

        documents = list(
            db.scalars(
                select(Document).where(Document.notebook_id.in_(notebook_ids))
            ).all()
        )
        for document in documents:
            db.delete(document)
        db.flush()

        notebooks = list(db.scalars(select(Notebook).where(Notebook.id.in_(notebook_ids))).all())
        for notebook in notebooks:
            db.delete(notebook)

    def _get_user_by_email(self, db: Session, email: str) -> User | None:
        return db.scalar(select(User).where(User.email == email))

    def list_user_notebooks(self, db: Session, *, user_id, skip: int = 0, limit: int = 100) -> list[Notebook]:
        statement = (
            select(Notebook)
            .where(Notebook.user_id == user_id)
            .order_by(Notebook.created_at.asc(), Notebook.id.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(statement).all())

    def get_user_notebook(self, db: Session, *, user_id, notebook_id) -> Notebook | None:
        return db.scalar(
            select(Notebook).where(
                Notebook.id == notebook_id,
                Notebook.user_id == user_id,
            )
        )

    def get_default_user_notebook(self, db: Session, *, user_id) -> Notebook | None:
        return db.scalar(
            select(Notebook)
            .where(Notebook.user_id == user_id)
            .order_by(Notebook.created_at.asc(), Notebook.id.asc())
            .limit(1)
        )

    def resolve_user_notebook(
        self,
        db: Session,
        *,
        user: User,
        notebook_id=None,
    ) -> Notebook:
        if notebook_id is not None:
            notebook = self.get_user_notebook(db, user_id=user.id, notebook_id=notebook_id)
            if notebook is None:
                raise AuthNotFoundError("Notebook not found.")
            return notebook

        notebook = self.get_default_user_notebook(db, user_id=user.id)
        if notebook is None:
            notebook = self.ensure_user_default_notebook(db, user=user)
            db.commit()
            db.refresh(notebook)
        return notebook

    def ensure_user_default_notebook(self, db: Session, *, user: User) -> Notebook:
        notebook = self.get_default_user_notebook(db, user_id=user.id)
        if notebook is not None:
            return notebook

        notebook = Notebook(
            user_id=user.id,
            title=_build_default_notebook_title(user.email),
            extra_metadata={},
        )
        db.add(notebook)
        db.flush()
        return notebook

    def _replace_active_otp(
        self,
        db: Session,
        *,
        email: str,
        purpose: str,
        otp_code: str,
        expires_at: datetime,
    ) -> None:
        db.execute(
            update(EmailOTP)
            .where(
                EmailOTP.email == email,
                EmailOTP.purpose == purpose,
                EmailOTP.is_used.is_(False),
            )
            .values(is_used=True)
        )
        db.add(
            EmailOTP(
                email=email,
                otp_hash=hash_token(otp_code),
                purpose=purpose,
                expires_at=expires_at,
                is_used=False,
            )
        )

    def _validate_otp(self, db: Session, *, email: str, purpose: str, otp: str) -> EmailOTP:
        otp_record = db.scalar(
            select(EmailOTP)
            .where(
                EmailOTP.email == email,
                EmailOTP.purpose == purpose,
            )
            .order_by(EmailOTP.created_at.desc())
        )
        if otp_record is None:
            raise AuthValidationError("OTP is invalid.")
        if otp_record.is_used:
            raise AuthValidationError("OTP has already been used.")
        if otp_record.expires_at < _now_utc():
            raise AuthValidationError("OTP has expired.")
        if otp_record.otp_hash != hash_token(otp.strip()):
            raise AuthValidationError("OTP is invalid.")
        return otp_record

    def _otp_expires_at(self) -> datetime:
        return _now_utc() + timedelta(minutes=get_settings().otp_expire_minutes)

    def _flush_send_and_commit(
        self,
        db: Session,
        *,
        email: str,
        otp_code: str,
        purpose: str,
        expires_at: datetime,
        conflict_message: str,
    ) -> None:
        try:
            db.flush()
            self.email_sender.send_otp(
                email=email,
                otp_code=otp_code,
                purpose=purpose,
                expires_at=expires_at,
            )
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise AuthConflictError(conflict_message) from exc
        except AuthDeliveryError:
            db.rollback()
            raise


auth_service = AuthService()

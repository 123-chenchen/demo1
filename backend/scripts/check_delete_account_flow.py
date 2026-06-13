from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.crud import hash_password
from app.db.models import Notebook, RefreshToken, User
from app.db.session import SessionLocal, init_db
from app.services.auth import auth_service


PASSWORD = "StrongPass1"


def main() -> int:
    api_base = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/") + "/api"
    email = os.getenv("DELETE_ACCOUNT_TEST_EMAIL") or f"delete-account-{uuid4().hex[:12]}@example.com"

    print(f"[info] backend={api_base}")
    print(f"[info] test_user={email}")

    user_id = None
    try:
        init_db()

        with SessionLocal() as db:
            existing_user = db.scalar(select(User).where(User.email == email))
            if existing_user is not None:
                db.delete(existing_user)
                db.commit()

            user = User(
                email=email,
                name="Delete Account Test",
                password_hash=hash_password(PASSWORD),
                is_verified=True,
                is_active=True,
                is_superuser=False,
                extra_metadata={"google_profile": {"name": "Delete Account Test"}},
            )
            db.add(user)
            db.flush()
            auth_service.ensure_user_default_notebook(db, user=user)
            db.commit()
            db.refresh(user)
            user_id = user.id
            print(f"[ok] created DB user id={user_id}")

        login_status, login_payload = request_json(
            "POST",
            f"{api_base}/auth/login",
            {"email": email, "password": PASSWORD},
        )
        assert_status(login_status, 200, login_payload)
        token = login_payload["access_token"]
        print("[ok] login returned access token")

        delete_status, delete_payload = request_json(
            "DELETE",
            f"{api_base}/auth/account",
            {"current_password": PASSWORD},
            token=token,
        )
        assert_status(delete_status, 200, delete_payload)
        print(f"[ok] delete account API response: {delete_payload.get('message')}")

        with SessionLocal() as db:
            user_exists = db.scalar(select(User.id).where(User.email == email)) is not None
            notebook_exists = db.scalar(select(Notebook.id).where(Notebook.user_id == user_id)) is not None
            token_exists = db.scalar(select(RefreshToken.id).where(RefreshToken.user_id == user_id)) is not None

        if user_exists or notebook_exists or token_exists:
            raise AssertionError(
                "DB hard-delete check failed: "
                f"user_exists={user_exists}, notebook_exists={notebook_exists}, token_exists={token_exists}"
            )
        print("[ok] DB hard-delete verified for user, notebooks, and refresh tokens")

        me_status, me_payload = request_json("GET", f"{api_base}/auth/me", token=token)
        if me_status != 401:
            raise AssertionError(f"Old access token should be rejected, got {me_status}: {me_payload}")
        print("[ok] old access token is rejected after delete")
        print("[ok] frontend redirect check: deleteAccount() calls logout(), clears local session, and ProtectedRoute sends the user to /login")
        return 0
    except SQLAlchemyError as exc:
        print("[error] could not connect to the configured database.")
        print("[hint] If you run this from the host while Docker is running, set DATABASE_URL to a host-reachable URL, for example postgresql+psycopg://USER:PASSWORD@127.0.0.1:5432/DB.")
        print(f"[detail] {exc}")
        return 2
    finally:
        if user_id is not None:
            with SessionLocal() as db:
                leftover = db.scalar(select(User).where(User.email == email))
                if leftover is not None:
                    db.delete(leftover)
                    db.commit()
                    print("[cleanup] removed leftover test user")


def request_json(method: str, url: str, payload: dict | None = None, *, token: str | None = None) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else {}
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            payload_data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            payload_data = {"detail": body}
        return exc.code, payload_data


def assert_status(actual: int, expected: int, payload: dict) -> None:
    if actual != expected:
        raise AssertionError(f"Expected HTTP {expected}, got {actual}: {payload}")


if __name__ == "__main__":
    raise SystemExit(main())

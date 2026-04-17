from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.crud import notebook_crud
from app.services.auth import auth_service


def _current_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        email="user@example.com",
        is_verified=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _notebook_payload() -> dict[str, object]:
    now = datetime.now(timezone.utc)
    return {
        "id": uuid4(),
        "title": "Project Alpha",
        "metadata": {},
        "created_at": now,
        "updated_at": now,
    }


def test_list_notebooks_requires_authentication(client, override_db) -> None:
    override_db()

    response = client.get("/api/notebooks/")

    assert response.status_code == 401


def test_list_notebooks_returns_current_user_notebooks(client, override_db, monkeypatch) -> None:
    override_db()
    current_user = _current_user()

    def fake_get_current_user_from_access_token(db, *, token):
        return current_user

    def fake_list_for_user(db, *, user_id, skip, limit):
        assert user_id == current_user.id
        return [_notebook_payload()]

    monkeypatch.setattr(auth_service, "get_current_user_from_access_token", fake_get_current_user_from_access_token)
    monkeypatch.setattr(notebook_crud, "list_for_user", fake_list_for_user)

    response = client.get(
        "/api/notebooks/",
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 200
    assert response.json()[0]["title"] == "Project Alpha"


def test_create_notebook_uses_current_user(client, override_db, monkeypatch) -> None:
    override_db()
    current_user = _current_user()

    def fake_get_current_user_from_access_token(db, *, token):
        return current_user

    def fake_create_for_user(db, *, user_id, obj_in):
        assert user_id == current_user.id
        assert obj_in.title == "Project Alpha"
        return _notebook_payload()

    monkeypatch.setattr(auth_service, "get_current_user_from_access_token", fake_get_current_user_from_access_token)
    monkeypatch.setattr(notebook_crud, "create_for_user", fake_create_for_user)

    response = client.post(
        "/api/notebooks/",
        json={"title": "Project Alpha", "metadata": {}},
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Project Alpha"

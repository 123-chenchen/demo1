from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.crud import chat_session_crud
from app.services.auth import auth_service


def _current_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        email="user@example.com",
        is_verified=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _chat_session_payload() -> dict[str, object]:
    now = datetime.now(timezone.utc)
    return {
        "id": uuid4(),
        "title": "Session title",
        "metadata": {},
        "created_at": now,
        "updated_at": now,
    }


def test_list_chat_sessions_requires_authentication(client, override_db) -> None:
    override_db()

    response = client.get("/api/chat-sessions/")

    assert response.status_code == 401


def test_list_chat_sessions_returns_only_current_user_sessions(client, override_db, monkeypatch) -> None:
    override_db()
    current_user = _current_user()
    selected_notebook = SimpleNamespace(id=uuid4())

    def fake_get_current_user_from_access_token(db, *, token):
        return current_user

    def fake_resolve_user_notebook(db, *, user, notebook_id=None):
        assert user.id == current_user.id
        assert notebook_id is None
        return selected_notebook

    def fake_list_for_user(db, *, user_id, notebook_id, skip, limit):
        assert user_id == current_user.id
        assert notebook_id == selected_notebook.id
        return [_chat_session_payload()]

    monkeypatch.setattr(auth_service, "get_current_user_from_access_token", fake_get_current_user_from_access_token)
    monkeypatch.setattr(auth_service, "resolve_user_notebook", fake_resolve_user_notebook)
    monkeypatch.setattr(chat_session_crud, "list_for_user", fake_list_for_user)

    response = client.get(
        "/api/chat-sessions/",
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 200
    assert response.json()[0]["title"] == "Session title"


def test_create_chat_session_uses_current_user_from_token(client, override_db, monkeypatch) -> None:
    override_db()
    current_user = _current_user()
    selected_notebook = SimpleNamespace(id=uuid4())

    def fake_get_current_user_from_access_token(db, *, token):
        return current_user

    def fake_resolve_user_notebook(db, *, user, notebook_id=None):
        assert user.id == current_user.id
        assert notebook_id is None
        return selected_notebook

    def fake_create_for_notebook(db, *, notebook_id, obj_in):
        assert notebook_id == selected_notebook.id
        assert obj_in.title == "Session title"
        return _chat_session_payload()

    monkeypatch.setattr(auth_service, "get_current_user_from_access_token", fake_get_current_user_from_access_token)
    monkeypatch.setattr(auth_service, "resolve_user_notebook", fake_resolve_user_notebook)
    monkeypatch.setattr(chat_session_crud, "create_for_notebook", fake_create_for_notebook)

    response = client.post(
        "/api/chat-sessions/",
        json={
            "title": "Session title",
            "metadata": {},
        },
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Session title"


def test_get_chat_session_returns_404_for_non_owned_session(client, override_db, monkeypatch) -> None:
    override_db()

    def fake_get_current_user_from_access_token(db, *, token):
        return _current_user()

    def fake_get_for_user(db, *, obj_id, user_id):
        return None

    monkeypatch.setattr(auth_service, "get_current_user_from_access_token", fake_get_current_user_from_access_token)
    monkeypatch.setattr(chat_session_crud, "get_for_user", fake_get_for_user)

    response = client.get(
        f"/api/chat-sessions/{uuid4()}",
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "chat session not found."

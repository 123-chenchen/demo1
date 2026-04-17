from __future__ import annotations

from app.core.config import get_settings


def test_root_redirects_to_demo(client) -> None:
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/demo"


def test_demo_page_renders_expected_content(client) -> None:
    response = client.get("/demo")

    assert response.status_code == 200
    assert "PDF Chatbot Demo" in response.text
    assert "Upload Flow" in response.text
    assert "Chunk Summary" in response.text


def test_healthcheck_returns_status_ok(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app_name": get_settings().app_name,
    }


def test_openapi_does_not_expose_refresh_token_crud_routes(client) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/refresh-tokens/" not in paths
    assert "/api/refresh-tokens/{item_id}" not in paths


def test_openapi_does_not_expose_user_crud_routes(client) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/users/" not in paths
    assert "/api/users/{item_id}" not in paths


def test_openapi_does_not_expose_internal_chat_crud_routes(client) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/chat-messages/" not in paths
    assert "/api/chat-messages/{item_id}" not in paths
    assert "/api/message-sources/" not in paths
    assert "/api/message-sources/{item_id}" not in paths


def test_document_chunk_routes_are_not_registered(client) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/document-chunks/" not in paths
    assert "/api/document-chunks/{item_id}" not in paths

    route_response = client.get("/api/document-chunks/")
    assert route_response.status_code == 404


def test_rag_routes_are_not_registered(client) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/rag/config" not in paths
    assert "/api/rag/chat" not in paths
    assert "/api/rag/reindex" not in paths

    route_response = client.get("/api/rag/config")
    assert route_response.status_code == 404

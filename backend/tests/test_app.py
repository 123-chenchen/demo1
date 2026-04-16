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
    assert "Ask The PDF" in response.text


def test_healthcheck_returns_status_ok(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app_name": get_settings().app_name,
    }


def test_rag_config_reflects_runtime_settings(client) -> None:
    response = client.get("/api/rag/config")
    payload = response.json()
    settings = get_settings()

    assert response.status_code == 200
    assert payload["retriever"] == "langchain-qdrant"
    assert payload["vector_store"] == "qdrant"
    assert payload["collection_name"] == settings.qdrant_collection_name
    assert payload["embedding_model"] == settings.embedding_model_name
    assert payload["top_k"] == settings.retrieval_top_k

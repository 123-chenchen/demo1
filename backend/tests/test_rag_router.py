from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

from app.services.chatbot import ChatbotServiceError, chatbot_service
from app.services.retrieval import RetrievalIndexerError, retrieval_indexer_service
from app.services.vector_store import VectorStoreError
from app.services.auth import auth_service


def _chat_response(*, document_id: UUID) -> dict[str, object]:
    return {
        "query": "Summarize the PDF.",
        "answer": "A concise grounded answer [1].",
        "document_id": document_id,
        "session_id": uuid4(),
        "user_message_id": uuid4(),
        "assistant_message_id": uuid4(),
        "retriever": "langchain-qdrant",
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "vector_store": "qdrant",
        "generator_provider": "extractive",
        "generator_model_name": None,
        "used_fallback_generator": True,
        "retrieval_latency_ms": 12.5,
        "total_latency_ms": 18.2,
        "sources": [
            {
                "chunk_id": uuid4(),
                "document_id": document_id,
                "original_file_name": "sample.pdf",
                "storage_key": "pdf-documents/documents/sample.pdf",
                "content": "Relevant excerpt.",
                "chunk_index": 0,
                "page_from": 1,
                "page_to": 1,
                "token_count": 8,
                "character_count": 17,
                "score": 0.95,
                "source": "langchain-qdrant",
                "metadata": {"retrieval_rank": 1},
            }
        ],
    }


def test_chat_endpoint_returns_answer_payload(client, override_db, monkeypatch) -> None:
    override_db()
    document_id = uuid4()

    def fake_ask(db, *, request, current_user=None):
        assert request.query == "Summarize the PDF."
        assert request.document_id == document_id
        return _chat_response(document_id=document_id)

    monkeypatch.setattr(chatbot_service, "ask", fake_ask)

    response = client.post(
        "/api/rag/chat",
        json={
            "query": "Summarize the PDF.",
            "document_id": str(document_id),
            "top_k": 3,
            "save_history": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "A concise grounded answer [1]."
    assert payload["document_id"] == str(document_id)
    assert payload["generator_provider"] == "extractive"
    assert payload["sources"][0]["metadata"]["retrieval_rank"] == 1


def test_chat_endpoint_maps_chatbot_errors_to_http_404(client, override_db, monkeypatch) -> None:
    override_db()

    def fake_ask(db, *, request, current_user=None):
        raise ChatbotServiceError("chat session not found.")

    monkeypatch.setattr(chatbot_service, "ask", fake_ask)

    response = client.post(
        "/api/rag/chat",
        json={"query": "Summarize the PDF.", "top_k": 3, "save_history": False},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "chat session not found."


def test_chat_endpoint_maps_vector_store_errors_to_http_503(client, override_db, monkeypatch) -> None:
    override_db()

    def fake_ask(db, *, request, current_user=None):
        raise VectorStoreError("Could not retrieve document chunks from Qdrant.")

    monkeypatch.setattr(chatbot_service, "ask", fake_ask)

    response = client.post(
        "/api/rag/chat",
        json={"query": "Summarize the PDF.", "top_k": 3, "save_history": False},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Could not retrieve document chunks from Qdrant."


def test_chat_endpoint_passes_current_user_when_bearer_token_is_present(client, override_db, monkeypatch) -> None:
    override_db()
    document_id = uuid4()
    current_user_obj = SimpleNamespace(id=uuid4(), email="user@example.com")

    def fake_get_current_user_from_access_token(db, *, token):
        assert token == "access-token"
        return current_user_obj

    def fake_ask(db, *, request, current_user=None):
        assert current_user is not None
        assert current_user.id == current_user_obj.id
        return _chat_response(document_id=document_id)

    monkeypatch.setattr(auth_service, "get_current_user_from_access_token", fake_get_current_user_from_access_token)
    monkeypatch.setattr(chatbot_service, "ask", fake_ask)

    response = client.post(
        "/api/rag/chat",
        json={
            "query": "Summarize the PDF.",
            "document_id": str(document_id),
            "top_k": 3,
            "save_history": True,
        },
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 200


def test_reindex_endpoint_returns_summary(client, override_db, monkeypatch) -> None:
    override_db()

    def fake_reindex_all(db):
        return {
            "reset_collection": True,
            "document_count": 2,
            "chunk_count": 10,
            "collection_name": "document_chunks",
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        }

    monkeypatch.setattr(retrieval_indexer_service, "reindex_all", fake_reindex_all)

    response = client.post("/api/rag/reindex")

    assert response.status_code == 200
    assert response.json()["document_count"] == 2
    assert response.json()["chunk_count"] == 10


def test_reindex_endpoint_maps_indexer_errors_to_http_503(client, override_db, monkeypatch) -> None:
    override_db()

    def fake_reindex_all(db):
        raise RetrievalIndexerError("Could not reindex retrieval data into Qdrant.")

    monkeypatch.setattr(retrieval_indexer_service, "reindex_all", fake_reindex_all)

    response = client.post("/api/rag/reindex")

    assert response.status_code == 503
    assert response.json()["detail"] == "Could not reindex retrieval data into Qdrant."

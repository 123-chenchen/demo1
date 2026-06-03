from __future__ import annotations

from uuid import uuid4

from app.services.ai.generation import (
    _answer_language_for,
    _build_context_block,
    _clean_model_answer,
    generate_answer,
)
from app.services.chatbot.service import _build_session_title
from app.services.retrieval.models import ChunkCandidate


def test_build_session_title_keeps_short_query_intact() -> None:
    query = "Summarize the attached PDF."

    assert _build_session_title(query) == query


def test_build_session_title_truncates_long_query() -> None:
    title = _build_session_title("a" * 120)

    assert len(title) == 80
    assert title.endswith("...")


def test_build_context_block_formats_candidate_metadata() -> None:
    candidate = ChunkCandidate(
        chunk_id=uuid4(),
        document_id=uuid4(),
        original_file_name="report.pdf",
        storage_key="pdf-documents/documents/report.pdf",
        content="Line one.\nLine two.",
        chunk_index=7,
        page_from=2,
        page_to=3,
        token_count=42,
        character_count=18,
        score=0.91,
        source="langchain-qdrant",
    )

    context_block = _build_context_block([candidate])

    assert "[1] file=report.pdf page=2-3 chunk=7" in context_block
    assert "Line one. Line two." in context_block


def test_generate_answer_uses_extract_fallback_when_no_candidates() -> None:
    result = generate_answer(query="What is this document about?", candidates=[])

    assert result.provider == "extractive"
    assert result.used_fallback is True
    assert "No relevant context was retrieved" in result.answer


def test_answer_language_detects_vietnamese_query() -> None:
    assert _answer_language_for("Báo cáo nghiên cứu bài toán gì?") == "Vietnamese"


def test_clean_model_answer_removes_bilingual_parenthetical_note() -> None:
    answer = "Tài liệu không cung cấp thông tin này.\n\n(Vietnamese: The document does not provide this information.)"

    assert _clean_model_answer(answer) == "Tài liệu không cung cấp thông tin này."

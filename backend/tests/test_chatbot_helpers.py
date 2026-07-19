from __future__ import annotations

from uuid import uuid4

from app.services.ai.generation import (
    _answer_language_for,
    _build_context_block,
    _clean_model_answer,
    _extractive_synthesis,
    _has_language_mismatch,
    _is_low_information_answer,
    _required_answer_language,
    generate_answer,
    generate_no_relevant_document_answer,
)
from app.services.chatbot.retrieval_qa import RetrievalQAResult
from app.services.chatbot.service import ChatbotService, _build_session_title
from app.services.retrieval.models import ChunkCandidate, RetrievalTrace


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


def test_generate_answer_uses_english_fallback() -> None:
    result = generate_answer(query="show api", candidates=[], language="en")

    assert result.provider == "extractive"
    assert result.used_fallback is True
    assert "No relevant context was retrieved" in result.answer


def test_answer_language_is_always_english() -> None:
    assert _answer_language_for("Any question") == "English"
    assert _required_answer_language("What are the main ideas?", "en") == "English"


def test_low_information_answer_detects_keyword_only_response() -> None:
    assert _is_low_information_answer(query="show api", answer="API") is True
    assert _is_low_information_answer(query="show api", answer="API [1]") is True
    assert _is_low_information_answer(query="show api", answer="See [1]") is True
    assert _is_low_information_answer(query="show api", answer="The API is discussed in the implementation section [1].") is False


def test_language_mismatch_detects_non_ascii_answer_for_english_only_mode() -> None:
    assert _has_language_mismatch(answer="R\u00e9sum\u00e9 of the paper [1].", required_language="English") is True


def test_extractive_synthesis_summarizes_retrieved_passages() -> None:
    candidate = ChunkCandidate(
        chunk_id=uuid4(),
        document_id=uuid4(),
        original_file_name="report.pdf",
        storage_key="pdf-documents/documents/report.pdf",
        content=(
            "The API layer exposes endpoints for uploading documents and asking questions. "
            "It validates requests before sending them to the retrieval pipeline."
        ),
        chunk_index=3,
        page_from=8,
        page_to=8,
        token_count=20,
        character_count=120,
        score=0.8,
        source="test",
    )

    answer = _extractive_synthesis(query="show api", candidates=[candidate], language="en")

    assert answer.startswith("Summary from the relevant passages:")
    assert "API layer exposes endpoints" in answer
    assert "[1]" in answer


def test_clean_model_answer_removes_parenthetical_translation_note() -> None:
    answer = "The document does not provide this information.\n\n(Translation: redundant note.)"

    assert _clean_model_answer(answer) == "The document does not provide this information."


def test_generate_no_relevant_document_answer_is_a_clear_fallback() -> None:
    result = generate_no_relevant_document_answer()

    assert result.provider == "extractive"
    assert result.used_fallback is True
    assert "No related document found" in result.answer


def _low_score_candidate() -> ChunkCandidate:
    return ChunkCandidate(
        chunk_id=uuid4(),
        document_id=uuid4(),
        original_file_name="report.pdf",
        storage_key="pdf-documents/documents/report.pdf",
        content="Unrelated content that does not match the question.",
        chunk_index=0,
        page_from=1,
        page_to=1,
        token_count=10,
        character_count=52,
        score=0.05,
        source="langchain-qdrant",
    )


def test_enforce_relevance_replaces_low_score_candidates_with_no_document_answer() -> None:
    service = ChatbotService()
    candidate = _low_score_candidate()
    trace = RetrievalTrace(
        query="What is the weather today?",
        candidates=[candidate],
        retrieval_latency_ms=1.0,
        total_latency_ms=2.0,
        retriever="langchain-qdrant",
        embedding_model="test-model",
        vector_store="qdrant",
    )
    original_generation = generate_answer(query="What is the weather today?", candidates=[candidate])
    pipeline_result = RetrievalQAResult(trace=trace, generation=original_generation)

    enforced = service._enforce_relevance(pipeline_result)

    assert enforced.trace.candidates == []
    assert "No related document found" in enforced.generation.answer
    assert enforced.generation.used_fallback is True


def test_enforce_relevance_keeps_result_when_a_candidate_is_relevant() -> None:
    service = ChatbotService()
    relevant_candidate = _low_score_candidate()
    relevant_candidate.score = 0.8
    trace = RetrievalTrace(
        query="What does the report say?",
        candidates=[relevant_candidate],
        retrieval_latency_ms=1.0,
        total_latency_ms=2.0,
        retriever="langchain-qdrant",
        embedding_model="test-model",
        vector_store="qdrant",
    )
    generation = generate_answer(query="What does the report say?", candidates=[relevant_candidate])
    pipeline_result = RetrievalQAResult(trace=trace, generation=generation)

    enforced = service._enforce_relevance(pipeline_result)

    assert enforced is pipeline_result

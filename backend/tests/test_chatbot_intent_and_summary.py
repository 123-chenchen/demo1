from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.services.chatbot.document_summary import DocumentSummaryService
from app.services.chatbot.intent import ChatIntent, IntentDetectionService
from app.services.chatbot.service import ChatbotService


def test_detects_english_document_summary_intent() -> None:
    result = IntentDetectionService().detect("What is this paper about?")

    assert result.intent == ChatIntent.DOCUMENT_SUMMARY
    assert result.confidence > 0.8


def test_detects_vietnamese_document_summary_intent() -> None:
    result = IntentDetectionService().detect("Ý chính của tài liệu là gì?")

    assert result.intent == ChatIntent.DOCUMENT_SUMMARY
    assert result.confidence > 0.8


def test_keeps_specific_question_on_retrieval_qa_path() -> None:
    result = IntentDetectionService().detect("What embedding model is used?")

    assert result.intent == ChatIntent.RETRIEVAL_QA


def test_summary_selection_prefers_structural_sections() -> None:
    service = DocumentSummaryService()
    chunks = [
        _chunk(0, "Document title and front matter", 1),
        _chunk(1, "Abstract: This paper studies retrieval systems.", 1),
        _chunk(2, "Implementation details for a narrow subsystem.", 4),
        _chunk(3, "Conclusion: The system improves document question answering.", 9),
    ]

    selected, strategy = service._select_summary_chunks(chunks, max_chunks=6)

    assert strategy == "structural-sections"
    assert [chunk.chunk_index for chunk in selected] == [0, 1, 3]


def test_summary_selection_samples_entire_document_when_sections_missing() -> None:
    service = DocumentSummaryService()
    chunks = [_chunk(index, f"Chunk {index}", index + 1) for index in range(9)]

    selected, strategy = service._select_summary_chunks(chunks, max_chunks=5)

    assert strategy == "representative-document-sampling"
    assert selected[0].chunk_index == 0
    assert selected[-1].chunk_index == 8
    assert len(selected) == 5


def test_suggested_questions_use_content_topic_not_filename() -> None:
    service = ChatbotService()
    document_id = uuid4()
    document = SimpleNamespace(
        id=document_id,
        original_file_name="quarterly-plan.pdf",
        extra_metadata={},
    )
    chunks = [
        _chunk(0, "Risk management strategy\nThe plan describes mitigation owners and escalation paths.", 1),
    ]

    topics = service._suggestion_topics(
        documents=[document],
        chunks_by_document_id={document_id: chunks},
    )
    questions = service._build_suggestion_questions(
        topics=topics,
        document_count=1,
        language="en",
    )

    assert topics[0] == "Risk management strategy"
    assert all(".pdf" not in question.lower() for question in questions)
    assert any("Risk management strategy" in question for question in questions)


def _chunk(index: int, content: str, page: int):
    return SimpleNamespace(
        id=uuid4(),
        chunk_index=index,
        content=content,
        page_from=page,
        page_to=page,
        token_count=None,
        character_count=len(content),
        extra_metadata={},
    )

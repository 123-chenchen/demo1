from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum


class ChatIntent(str, Enum):
    DOCUMENT_SUMMARY = "document_summary"
    RETRIEVAL_QA = "retrieval_qa"


@dataclass(frozen=True, slots=True)
class IntentDetectionResult:
    intent: ChatIntent
    confidence: float
    matched_pattern: str | None = None


def _normalize(text: str) -> str:
    lowered = text.lower().strip()
    decomposed = unicodedata.normalize("NFD", lowered)
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", without_marks)


class IntentDetectionService:
    _summary_patterns = (
        r"\bsummar(y|ize|ise|ise this|ize this)\b",
        r"\bwhat (is|s) (this|the) (document|paper|pdf|file) (about|mainly about)\b",
        r"\bmain (idea|point|points|purpose|theme)\b",
        r"\boverview\b",
        r"\bbriefly describe (this|the) (document|paper|pdf|file)\b",
        r"\btom tat\b",
        r"\btom tat (tai lieu|file|pdf|van ban|no|cai nay)\b",
        r"\by chinh\b",
        r"\bnoi dung chinh\b",
        r"\btai lieu nay noi ve\b",
        r"\bfile nay noi ve\b",
        r"\bpdf nay noi ve\b",
        r"\bvan ban nay noi ve\b",
        r"\b(no|cai nay) noi ve gi\b",
        r"\b(y chinh|noi dung chinh) cua (tai lieu|file|pdf|van ban|no|cai nay)\b",
    )

    _specific_question_terms = (
        "what is ",
        "how does ",
        "how do ",
        "why does ",
        "where ",
        "when ",
        "which ",
        "ollama",
        "faiss",
        "embedding",
        "model",
        "api",
        "function",
        "class",
        "method",
    )

    def detect(self, query: str) -> IntentDetectionResult:
        normalized = _normalize(query)
        if not normalized:
            return IntentDetectionResult(ChatIntent.RETRIEVAL_QA, 0.0)

        for pattern in self._summary_patterns:
            if re.search(pattern, normalized):
                return IntentDetectionResult(ChatIntent.DOCUMENT_SUMMARY, 0.92, pattern)

        if any(term in normalized for term in self._specific_question_terms):
            return IntentDetectionResult(ChatIntent.RETRIEVAL_QA, 0.75)

        return IntentDetectionResult(ChatIntent.RETRIEVAL_QA, 0.55)


intent_detection_service = IntentDetectionService()

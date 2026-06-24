from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence
from uuid import UUID

from app.services.ai import AnswerGenerationResult, generate_answer
from app.services.retrieval.models import RetrievalTrace
from app.services.retrieval.service import retrieval_service


@dataclass(frozen=True, slots=True)
class RetrievalQAResult:
    trace: RetrievalTrace
    generation: AnswerGenerationResult


class RetrievalQAService:
    def answer(
        self,
        *,
        query: str,
        top_k: int | None,
        language: str | None = None,
        document_id=None,
        document_ids: Sequence[UUID] | None = None,
        notebook_id=None,
        public_only: bool = False,
    ) -> RetrievalQAResult:
        trace = retrieval_service.retrieve(
            query=query,
            top_k=top_k,
            document_id=document_id,
            document_ids=document_ids,
            notebook_id=notebook_id,
            public_only=public_only,
        )
        return RetrievalQAResult(
            trace=trace,
            generation=generate_answer(query=query, candidates=trace.candidates, language=language),
        )


retrieval_qa_service = RetrievalQAService()

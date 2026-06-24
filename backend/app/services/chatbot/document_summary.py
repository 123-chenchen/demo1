from __future__ import annotations

import re
from dataclasses import dataclass
from time import perf_counter
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Document, DocumentChunk
from app.services.ai import AnswerGenerationResult, generate_document_summary
from app.services.retrieval.models import ChunkCandidate, RetrievalTrace


@dataclass(frozen=True, slots=True)
class DocumentSummaryResult:
    trace: RetrievalTrace
    generation: AnswerGenerationResult
    source_strategy: str


class DocumentSummaryService:
    retriever_name = "document-summary"
    vector_store_name = "database"
    _section_patterns = {
        "title": re.compile(r"^\s*title\s*[:\n]", re.IGNORECASE),
        "abstract": re.compile(r"^\s*abstract\s*[:\n]", re.IGNORECASE),
        "introduction": re.compile(r"^\s*introduction\s*[:\n]", re.IGNORECASE),
        "conclusion": re.compile(r"^\s*(conclusion|summary|discussion)\s*[:\n]", re.IGNORECASE),
    }

    def summarize(
        self,
        db: Session,
        *,
        query: str,
        document: Document,
        language: str | None = None,
        max_chunks: int = 10,
    ) -> DocumentSummaryResult:
        settings = get_settings()
        total_started_at = perf_counter()
        retrieval_started_at = perf_counter()

        chunks = self._load_document_chunks(db, document_id=document.id)
        selected_chunks, strategy = self._select_summary_chunks(chunks, max_chunks=max_chunks)
        candidates = [self._to_candidate(document=document, chunk=chunk, rank=index) for index, chunk in enumerate(selected_chunks, start=1)]
        retrieval_latency_ms = (perf_counter() - retrieval_started_at) * 1000

        generation = generate_document_summary(
            query=query,
            candidates=candidates,
            document_title=document.original_file_name,
            language=language,
        )

        return DocumentSummaryResult(
            trace=RetrievalTrace(
                query=query,
                candidates=candidates,
                retrieval_latency_ms=retrieval_latency_ms,
                total_latency_ms=(perf_counter() - total_started_at) * 1000,
                retriever=self.retriever_name,
                embedding_model=settings.embedding_model_name,
                vector_store=self.vector_store_name,
            ),
            generation=generation,
            source_strategy=strategy,
        )

    def _load_document_chunks(self, db: Session, *, document_id: UUID) -> list[DocumentChunk]:
        statement = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        return list(db.scalars(statement).all())

    def _select_summary_chunks(
        self,
        chunks: list[DocumentChunk],
        *,
        max_chunks: int,
    ) -> tuple[list[DocumentChunk], str]:
        if not chunks:
            return [], "empty"

        selected: list[DocumentChunk] = []
        selected_ids: set[UUID] = set()

        def add(chunk: DocumentChunk) -> None:
            if chunk.id in selected_ids or len(selected) >= max_chunks:
                return
            selected.append(chunk)
            selected_ids.add(chunk.id)

        add(chunks[0])
        for chunk in chunks:
            content = chunk.content[:500]
            if any(pattern.search(content) for pattern in self._section_patterns.values()):
                add(chunk)

        if len(selected) >= 3:
            return sorted(selected, key=lambda item: item.chunk_index), "structural-sections"

        for chunk in self._representative_chunks(chunks, max_chunks=max_chunks):
            add(chunk)

        return sorted(selected, key=lambda item: item.chunk_index), "representative-document-sampling"

    def _representative_chunks(self, chunks: list[DocumentChunk], *, max_chunks: int) -> list[DocumentChunk]:
        if len(chunks) <= max_chunks:
            return chunks

        indexes = {0, len(chunks) - 1}
        slots = max(1, max_chunks - len(indexes))
        for slot in range(1, slots + 1):
            indexes.add(round(slot * (len(chunks) - 1) / (slots + 1)))

        return [chunks[index] for index in sorted(indexes)]

    def _to_candidate(self, *, document: Document, chunk: DocumentChunk, rank: int) -> ChunkCandidate:
        return ChunkCandidate(
            chunk_id=chunk.id,
            document_id=document.id,
            original_file_name=document.original_file_name,
            storage_key=document.storage_key,
            content=chunk.content,
            chunk_index=chunk.chunk_index,
            page_from=chunk.page_from,
            page_to=chunk.page_to,
            token_count=chunk.token_count,
            character_count=chunk.character_count,
            score=None,
            source=self.retriever_name,
            metadata={
                **dict(chunk.extra_metadata or {}),
                "retrieval_rank": rank,
                "summary_source": True,
                "summary_section": self._section_label(chunk),
            },
            document_name=document.original_file_name,
            page_number=chunk.page_from,
            quoted_text=str((chunk.extra_metadata or {}).get("quoted_text") or chunk.content),
            bbox=self._bbox(chunk),
            page_width=self._optional_float((chunk.extra_metadata or {}).get("page_width")),
            page_height=self._optional_float((chunk.extra_metadata or {}).get("page_height")),
        )

    def _section_label(self, chunk: DocumentChunk) -> str:
        if chunk.chunk_index == 0:
            return "title_or_front_matter"

        content = chunk.content[:500]
        for label, pattern in self._section_patterns.items():
            if pattern.search(content):
                return label

        return "representative_excerpt"

    def _bbox(self, chunk: DocumentChunk) -> list[float] | None:
        value = dict(chunk.extra_metadata or {}).get("bbox")
        if not isinstance(value, list) or len(value) != 4:
            return None
        return [float(item) for item in value]

    def _optional_float(self, value: object) -> float | None:
        if value is None:
            return None
        return float(value)


document_summary_service = DocumentSummaryService()

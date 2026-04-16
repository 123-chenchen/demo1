from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(slots=True)
class ChunkCandidate:
    chunk_id: UUID
    document_id: UUID
    original_file_name: str
    storage_key: str
    content: str
    chunk_index: int
    page_from: int | None
    page_to: int | None
    token_count: int | None
    character_count: int | None
    score: float | None
    source: str = ""
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class RetrievalTrace:
    query: str
    candidates: list[ChunkCandidate]
    retrieval_latency_ms: float
    total_latency_ms: float
    retriever: str
    embedding_model: str
    vector_store: str


def chunk_candidate_to_dict(candidate: ChunkCandidate) -> dict[str, object]:
    return {
        "chunk_id": candidate.chunk_id,
        "document_id": candidate.document_id,
        "original_file_name": candidate.original_file_name,
        "storage_key": candidate.storage_key,
        "content": candidate.content,
        "chunk_index": candidate.chunk_index,
        "page_from": candidate.page_from,
        "page_to": candidate.page_to,
        "token_count": candidate.token_count,
        "character_count": candidate.character_count,
        "score": candidate.score,
        "source": candidate.source,
        "metadata": candidate.metadata,
    }

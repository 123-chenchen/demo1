from __future__ import annotations

from time import perf_counter
from uuid import UUID

from app.config import get_settings
from app.services.retrieval.models import ChunkCandidate, RetrievalTrace
from app.services.retrieval.vector_store import similarity_search


class RetrievalService:
    retriever_name = "langchain-qdrant"
    vector_store_name = "qdrant"

    def describe(self) -> dict[str, object]:
        settings = get_settings()
        return {
            "retriever": self.retriever_name,
            "vector_store": self.vector_store_name,
            "collection_name": settings.qdrant_collection_name,
            "embedding_model": settings.embedding_model_name,
            "top_k": settings.retrieval_top_k,
        }

    def retrieve(
        self,
        *,
        query: str,
        top_k: int | None = None,
        document_id: UUID | None = None,
        notebook_id: UUID | None = None,
        public_only: bool = False,
    ) -> RetrievalTrace:
        settings = get_settings()
        final_top_k = max(1, top_k or settings.retrieval_top_k)
        total_started_at = perf_counter()

        retrieval_started_at = perf_counter()
        search_results = similarity_search(
            query=query,
            limit=final_top_k,
            document_id=document_id,
            notebook_id=notebook_id,
            public_only=public_only,
        )
        retrieval_latency_ms = (perf_counter() - retrieval_started_at) * 1000

        return RetrievalTrace(
            query=query,
            candidates=self._to_candidates(search_results),
            retrieval_latency_ms=retrieval_latency_ms,
            total_latency_ms=(perf_counter() - total_started_at) * 1000,
            retriever=self.retriever_name,
            embedding_model=settings.embedding_model_name,
            vector_store=self.vector_store_name,
        )

    def _to_candidates(self, search_results: list[tuple[object, float]]) -> list[ChunkCandidate]:
        candidates: list[ChunkCandidate] = []

        for rank, (document, score) in enumerate(search_results, start=1):
            metadata = dict(getattr(document, "metadata", {}) or {})
            chunk_id = metadata.get("chunk_id")
            document_id = metadata.get("document_id")
            if chunk_id is None or document_id is None:
                continue
            try:
                candidates.append(
                    ChunkCandidate(
                        chunk_id=UUID(str(chunk_id)),
                        document_id=UUID(str(document_id)),
                        original_file_name=str(metadata.get("original_file_name") or ""),
                        storage_key=str(metadata.get("storage_key") or ""),
                        content=str(getattr(document, "page_content", "") or ""),
                        chunk_index=int(metadata.get("chunk_index") or 0),
                        page_from=_optional_int(metadata.get("page_from")),
                        page_to=_optional_int(metadata.get("page_to")),
                        token_count=_optional_int(metadata.get("token_count")),
                        character_count=_optional_int(metadata.get("character_count")),
                        score=float(score) if score is not None else None,
                        source=self.retriever_name,
                        metadata={
                            **metadata,
                            "retrieval_rank": rank,
                        },
                    )
                )
            except (TypeError, ValueError):
                continue

        return candidates


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


retrieval_service = RetrievalService()

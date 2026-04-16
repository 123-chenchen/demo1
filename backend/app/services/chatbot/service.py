from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ChatMessage, ChatSession, MessageRole, MessageSource
from app.schemas.rag import ChatbotAskRequest
from app.services.chatbot.generation import generate_answer
from app.services.retrieval import chunk_candidate_to_dict, retrieval_service


class ChatbotServiceError(Exception):
    pass


def _build_session_title(query: str) -> str:
    normalized = " ".join(query.split())
    if len(normalized) <= 80:
        return normalized
    return f"{normalized[:77]}..."


class ChatbotService:
    def ask(self, db: Session, *, request: ChatbotAskRequest) -> dict[str, object]:
        trace = retrieval_service.retrieve(
            query=request.query,
            top_k=request.top_k,
            document_id=request.document_id,
        )
        generation = generate_answer(query=request.query, candidates=trace.candidates)

        session_id = request.session_id
        user_message_id = None
        assistant_message_id = None

        if request.save_history:
            session = self._resolve_or_create_session(
                db,
                session_id=request.session_id,
                query=request.query,
            )
            session_id = session.id

            user_message = ChatMessage(
                session_id=session.id,
                role=MessageRole.user,
                content=request.query,
                extra_metadata={
                    "top_k": request.top_k,
                    "document_id": str(request.document_id) if request.document_id else None,
                    "retriever": trace.retriever,
                    "embedding_model": trace.embedding_model,
                    "vector_store": trace.vector_store,
                },
            )
            db.add(user_message)
            db.flush()

            assistant_message = ChatMessage(
                session_id=session.id,
                role=MessageRole.assistant,
                reply_to_message_id=user_message.id,
                content=generation.answer,
                model_name=generation.model_name,
                extra_metadata={
                    "retriever": trace.retriever,
                    "embedding_model": trace.embedding_model,
                    "vector_store": trace.vector_store,
                    "generator_provider": generation.provider,
                    "used_fallback_generator": generation.used_fallback,
                    "retrieval_latency_ms": trace.retrieval_latency_ms,
                    "total_latency_ms": trace.total_latency_ms,
                    "document_id": str(request.document_id) if request.document_id else None,
                },
            )
            db.add(assistant_message)
            db.flush()

            for rank, candidate in enumerate(trace.candidates, start=1):
                db.add(
                    MessageSource(
                        message_id=assistant_message.id,
                        chunk_id=candidate.chunk_id,
                        source_rank=rank,
                        score=candidate.score,
                        snippet=candidate.content[:500],
                    )
                )

            db.commit()
            user_message_id = user_message.id
            assistant_message_id = assistant_message.id

        return {
            "query": request.query,
            "answer": generation.answer,
            "document_id": request.document_id,
            "session_id": session_id,
            "user_message_id": user_message_id,
            "assistant_message_id": assistant_message_id,
            "retriever": trace.retriever,
            "embedding_model": trace.embedding_model,
            "vector_store": trace.vector_store,
            "generator_provider": generation.provider,
            "generator_model_name": generation.model_name,
            "used_fallback_generator": generation.used_fallback,
            "retrieval_latency_ms": trace.retrieval_latency_ms,
            "total_latency_ms": trace.total_latency_ms,
            "sources": [chunk_candidate_to_dict(candidate) for candidate in trace.candidates],
        }

    def _resolve_or_create_session(
        self,
        db: Session,
        *,
        session_id,
        query: str,
    ) -> ChatSession:
        if session_id is not None:
            session = db.scalar(select(ChatSession).where(ChatSession.id == session_id))
            if session is None:
                raise ChatbotServiceError("chat session not found.")
            return session

        session = ChatSession(
            title=_build_session_title(query),
            extra_metadata={},
        )
        db.add(session)
        db.flush()
        return session


chatbot_service = ChatbotService()

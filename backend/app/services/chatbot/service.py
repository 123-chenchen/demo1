from __future__ import annotations

from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import ChatMessage, ChatSession, Document, DocumentStatus, MessageRole, MessageSource, User
from app.schemas import ChatbotAskRequest
from app.services.ai import generate_answer
from app.services.retrieval import chunk_candidate_to_dict, retrieval_service
from app.services.auth import AuthNotFoundError, auth_service
from app.services.retrieval.vector_store import VectorStoreError, upsert_document_chunks


class ChatbotServiceError(Exception):
    pass


class ChatbotServicePermissionError(Exception):
    pass


def _build_session_title(query: str) -> str:
    normalized = " ".join(query.split())
    if len(normalized) <= 80:
        return normalized
    return f"{normalized[:77]}..."


class ChatbotService:
    def ask(
        self,
        db: Session,
        *,
        request: ChatbotAskRequest,
        current_user: User | None = None,
    ) -> dict[str, object]:
        selected_notebook = self._resolve_requested_notebook(
            db,
            notebook_id=request.notebook_id,
            current_user=current_user,
            use_default=request.document_id is None and request.session_id is None,
        )
        accessible_document = self._resolve_accessible_document(
            db,
            document_id=request.document_id,
            current_user=current_user,
            selected_notebook=selected_notebook,
        )
        session_notebook = self._resolve_session_notebook(
            db,
            current_user=current_user,
            selected_notebook=selected_notebook,
            accessible_document=accessible_document,
            save_history=request.save_history,
        )
        if accessible_document is not None:
            retrieval_notebook_id = accessible_document.notebook_id
            public_only = accessible_document.notebook_id is None
        else:
            retrieval_notebook_id = selected_notebook.id if selected_notebook is not None else None
            public_only = current_user is None
        trace = retrieval_service.retrieve(
            query=request.query,
            top_k=request.top_k,
            document_id=request.document_id,
            notebook_id=retrieval_notebook_id,
            public_only=public_only,
        )
        if not trace.candidates and accessible_document is not None:
            if self._repair_document_index_if_needed(db, document=accessible_document):
                trace = retrieval_service.retrieve(
                    query=request.query,
                    top_k=request.top_k,
                    document_id=request.document_id,
                    notebook_id=retrieval_notebook_id,
                    public_only=public_only,
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
                current_user=current_user,
                selected_notebook=session_notebook,
            )
            session_id = session.id

            user_message = ChatMessage(
                session_id=session.id,
                role=MessageRole.user,
                content=request.query,
                extra_metadata={
                    "top_k": request.top_k,
                    "document_id": str(accessible_document.id) if accessible_document else None,
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
                    "document_id": str(accessible_document.id) if accessible_document else None,
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
            "notebook_id": (
                session.notebook_id
                if request.save_history and session_id is not None
                else (
                    selected_notebook.id
                    if selected_notebook is not None
                    else accessible_document.notebook_id if accessible_document is not None else None
                )
            ),
            "document_id": accessible_document.id if accessible_document else None,
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
        current_user: User | None = None,
        selected_notebook=None,
    ) -> ChatSession:
        if session_id is not None:
            session = db.scalar(select(ChatSession).where(ChatSession.id == session_id))
            if session is None:
                raise ChatbotServiceError("chat session not found.")
            if session.notebook_id is not None:
                if current_user is None:
                    raise ChatbotServicePermissionError("authentication is required for this chat session.")
                if auth_service.get_user_notebook(
                    db,
                    user_id=current_user.id,
                    notebook_id=session.notebook_id,
                ) is None:
                    raise ChatbotServicePermissionError("chat session does not belong to the current user.")
                if selected_notebook is not None and session.notebook_id != selected_notebook.id:
                    raise ChatbotServicePermissionError("chat session does not belong to the selected notebook.")
            elif selected_notebook is not None:
                session.notebook_id = selected_notebook.id
                db.add(session)
            return session

        session = ChatSession(
            notebook_id=selected_notebook.id if selected_notebook is not None else None,
            title=_build_session_title(query),
            extra_metadata={},
        )
        db.add(session)
        db.flush()
        return session

    def _resolve_accessible_document(
        self,
        db: Session,
        *,
        document_id,
        current_user: User | None = None,
        selected_notebook=None,
    ) -> Document | None:
        if document_id is None:
            return None

        document = db.scalar(select(Document).where(Document.id == document_id))
        if document is None:
            raise ChatbotServiceError("document not found.")

        if document.notebook_id is None:
            return document

        if current_user is None:
            raise ChatbotServicePermissionError("authentication is required for this document.")
        if auth_service.get_user_notebook(
            db,
            user_id=current_user.id,
            notebook_id=document.notebook_id,
        ) is None:
            raise ChatbotServicePermissionError("document does not belong to the current user.")
        if selected_notebook is not None and document.notebook_id != selected_notebook.id:
            raise ChatbotServicePermissionError("document does not belong to the selected notebook.")
        return document

    def _repair_document_index_if_needed(self, db: Session, *, document: Document) -> bool:
        if document.status != DocumentStatus.processed or document.total_chunks <= 0:
            return False

        indexed_document = db.scalar(
            select(Document)
            .options(selectinload(Document.chunks))
            .where(Document.id == document.id)
        )
        if indexed_document is None or not indexed_document.chunks:
            return False

        try:
            upsert_document_chunks(document=indexed_document, chunks=list(indexed_document.chunks))
            for chunk in indexed_document.chunks:
                db.add(chunk)
            db.commit()
            logger.warning(
                "Reindexed document {} after retrieval returned no candidates.",
                indexed_document.id,
            )
            return True
        except VectorStoreError as exc:
            db.rollback()
            logger.exception("Could not repair retrieval index for document {}: {}", document.id, exc)
        except Exception as exc:
            db.rollback()
            logger.exception("Unexpected retrieval index repair failure for document {}: {}", document.id, exc)
        return False

    def _resolve_requested_notebook(
        self,
        db: Session,
        *,
        notebook_id,
        current_user: User | None = None,
        use_default: bool = False,
    ):
        if current_user is None:
            if notebook_id is not None:
                raise ChatbotServicePermissionError("authentication is required for this notebook.")
            return None

        if notebook_id is None and not use_default:
            return None

        try:
            return auth_service.resolve_user_notebook(
                db,
                user=current_user,
                notebook_id=notebook_id,
            )
        except AuthNotFoundError as exc:
            raise ChatbotServiceError(str(exc)) from exc

    def _resolve_session_notebook(
        self,
        db: Session,
        *,
        current_user: User | None = None,
        selected_notebook=None,
        accessible_document: Document | None = None,
        save_history: bool = False,
    ):
        if selected_notebook is not None:
            return selected_notebook
        if current_user is None or not save_history:
            return None
        if accessible_document is not None and accessible_document.notebook_id is not None:
            return auth_service.get_user_notebook(
                db,
                user_id=current_user.id,
                notebook_id=accessible_document.notebook_id,
            )
        return auth_service.resolve_user_notebook(
            db,
            user=current_user,
            notebook_id=None,
        )


chatbot_service = ChatbotService()

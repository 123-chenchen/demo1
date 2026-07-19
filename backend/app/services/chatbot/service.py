from __future__ import annotations

import re
from collections import Counter, defaultdict
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import ChatMessage, ChatSession, Document, DocumentChunk, DocumentStatus, MessageRole, MessageSource, User
from app.schemas import ChatbotAskRequest, ChatbotSuggestionsRequest
from app.services.retrieval import chunk_candidate_to_dict
from app.services.auth import AuthNotFoundError, auth_service
from app.services.retrieval.vector_store import VectorStoreError, upsert_document_chunks
from app.services.chatbot.context import conversation_context_service
from app.services.chatbot.document_summary import document_summary_service
from app.services.chatbot.intent import ChatIntent, IntentDetectionResult, intent_detection_service
from app.services.chatbot.retrieval_qa import retrieval_qa_service

_GREETING_ANSWER = "Hello! How can I help you with your uploaded documents today?"


class ChatbotServiceError(Exception):
    pass


class ChatbotServicePermissionError(Exception):
    pass


def _build_session_title(query: str) -> str:
    normalized = " ".join(query.split())
    if len(normalized) <= 80:
        return normalized
    return f"{normalized[:77]}..."


_SUGGESTION_STOPWORDS = {
    "about",
    "across",
    "also",
    "and",
    "are",
    "because",
    "been",
    "between",
    "chapter",
    "data",
    "document",
    "documents",
    "example",
    "examples",
    "from",
    "have",
    "into",
    "material",
    "more",
    "page",
    "paper",
    "report",
    "section",
    "selected",
    "source",
    "sources",
    "that",
    "the",
    "their",
    "this",
    "with",
}


class ChatbotService:
    def ask(
        self,
        db: Session,
        *,
        request: ChatbotAskRequest,
        current_user: User | None = None,
    ) -> dict[str, object]:
        intent = intent_detection_service.detect(request.query)
        if intent.intent == ChatIntent.GREETING:
            return self._handle_greeting(db, request=request, current_user=current_user, intent=intent)

        requested_document_ids = self._requested_document_ids(request)
        selected_notebook = self._resolve_requested_notebook(
            db,
            notebook_id=request.notebook_id,
            current_user=current_user,
            use_default=not requested_document_ids and request.session_id is None,
        )
        accessible_documents = self._resolve_accessible_documents(
            db,
            document_ids=requested_document_ids,
            current_user=current_user,
            selected_notebook=selected_notebook,
        )
        accessible_document = accessible_documents[0] if len(accessible_documents) == 1 else None
        context = conversation_context_service.resolve(
            db,
            query=request.query,
            selected_document=accessible_document,
            session_id=request.session_id,
        )
        if not requested_document_ids and accessible_document is None and context.resolved_document_id is not None:
            accessible_document = self._resolve_accessible_document(
                db,
                document_id=context.resolved_document_id,
                current_user=current_user,
                selected_notebook=selected_notebook,
            )
            accessible_documents = [accessible_document]

        session_notebook = self._resolve_session_notebook(
            db,
            current_user=current_user,
            selected_notebook=selected_notebook,
            accessible_documents=accessible_documents,
            save_history=request.save_history,
        )
        if accessible_documents:
            retrieval_document_ids = [document.id for document in accessible_documents]
            retrieval_notebook_id = selected_notebook.id if selected_notebook is not None else self._common_notebook_id(accessible_documents)
            public_only = current_user is None and all(document.notebook_id is None for document in accessible_documents)
        else:
            retrieval_document_ids = []
            retrieval_notebook_id = selected_notebook.id if selected_notebook is not None else None
            public_only = current_user is None

        source_strategy = None
        if intent.intent == ChatIntent.DOCUMENT_SUMMARY and accessible_document is not None:
            pipeline_result = document_summary_service.summarize(
                db,
                query=request.query,
                document=accessible_document,
                language=request.language,
                max_chunks=min(max(request.top_k, 8), 12),
            )
            source_strategy = pipeline_result.source_strategy
        else:
            pipeline_result = retrieval_qa_service.answer(
                query=request.query,
                top_k=request.top_k,
                language=request.language,
                document_id=accessible_document.id if accessible_document is not None else None,
                document_ids=retrieval_document_ids if len(retrieval_document_ids) > 1 else None,
                notebook_id=retrieval_notebook_id,
                public_only=public_only,
            )
            if not pipeline_result.trace.candidates and accessible_document is not None:
                if self._repair_document_index_if_needed(db, document=accessible_document):
                    pipeline_result = retrieval_qa_service.answer(
                        query=request.query,
                        top_k=request.top_k,
                        language=request.language,
                        document_id=accessible_document.id,
                        document_ids=None,
                        notebook_id=retrieval_notebook_id,
                        public_only=public_only,
                    )

        trace = pipeline_result.trace
        generation = pipeline_result.generation

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
            document_history_metadata = self._document_history_metadata(accessible_documents)
            session.extra_metadata = {
                **dict(session.extra_metadata or {}),
                **document_history_metadata,
            }
            db.add(session)

            user_message = ChatMessage(
                session_id=session.id,
                role=MessageRole.user,
                content=request.query,
                extra_metadata={
                    "top_k": request.top_k,
                    "document_id": str(accessible_document.id) if accessible_document else None,
                    "document_ids": [str(document.id) for document in accessible_documents],
                    **document_history_metadata,
                    "resolved_document_id": str(context.resolved_document_id) if context.resolved_document_id else None,
                    "intent": intent.intent.value,
                    "intent_confidence": intent.confidence,
                    "intent_matched_pattern": intent.matched_pattern,
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
                    "intent": intent.intent.value,
                    "intent_confidence": intent.confidence,
                    "summary_source_strategy": source_strategy,
                    "retrieval_latency_ms": trace.retrieval_latency_ms,
                    "total_latency_ms": trace.total_latency_ms,
                    "document_id": str(accessible_document.id) if accessible_document else None,
                    "document_ids": [str(document.id) for document in accessible_documents],
                    **document_history_metadata,
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
            "document_ids": [document.id for document in accessible_documents],
            "document_names": [document.original_file_name for document in accessible_documents],
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

    def _handle_greeting(
        self,
        db: Session,
        *,
        request: ChatbotAskRequest,
        current_user: User | None = None,
        intent: IntentDetectionResult,
    ) -> dict[str, object]:
        answer = _GREETING_ANSWER
        session_id = request.session_id
        user_message_id = None
        assistant_message_id = None

        if request.save_history:
            session = self._resolve_or_create_session(
                db,
                session_id=request.session_id,
                query=request.query,
                current_user=current_user,
                selected_notebook=None,
            )
            session_id = session.id

            user_message = ChatMessage(
                session_id=session.id,
                role=MessageRole.user,
                content=request.query,
                extra_metadata={
                    "intent": intent.intent.value,
                    "intent_confidence": intent.confidence,
                    "intent_matched_pattern": intent.matched_pattern,
                },
            )
            db.add(user_message)
            db.flush()

            assistant_message = ChatMessage(
                session_id=session.id,
                role=MessageRole.assistant,
                reply_to_message_id=user_message.id,
                content=answer,
                model_name=None,
                extra_metadata={
                    "intent": intent.intent.value,
                    "generator_provider": "greeting",
                    "used_fallback_generator": False,
                },
            )
            db.add(assistant_message)
            db.flush()

            db.commit()
            user_message_id = user_message.id
            assistant_message_id = assistant_message.id

        return {
            "query": request.query,
            "answer": answer,
            "notebook_id": None,
            "document_id": None,
            "document_ids": [],
            "document_names": [],
            "session_id": session_id,
            "user_message_id": user_message_id,
            "assistant_message_id": assistant_message_id,
            "retriever": "none",
            "embedding_model": "none",
            "vector_store": "none",
            "generator_provider": "greeting",
            "generator_model_name": None,
            "used_fallback_generator": False,
            "retrieval_latency_ms": 0.0,
            "total_latency_ms": 0.0,
            "sources": [],
        }

    def suggest_questions(
        self,
        db: Session,
        *,
        request: ChatbotSuggestionsRequest,
        current_user: User | None = None,
    ) -> dict[str, object]:
        requested_document_ids = self._requested_document_ids(request)
        if not requested_document_ids:
            return self._empty_suggestions(language=request.language)

        selected_notebook = self._resolve_requested_notebook(
            db,
            notebook_id=request.notebook_id,
            current_user=current_user,
            use_default=False,
        )
        documents = self._resolve_accessible_documents(
            db,
            document_ids=requested_document_ids,
            current_user=current_user,
            selected_notebook=selected_notebook,
        )
        chunks_by_document_id = self._load_suggestion_chunks(db, documents=documents)
        topics = self._suggestion_topics(
            documents=documents,
            chunks_by_document_id=chunks_by_document_id,
        )
        questions = (
            self._build_suggestion_questions(
                topics=topics,
                document_count=len(documents),
                language=request.language,
            )
            if topics
            else []
        )
        return {
            "title": self._suggestion_title(documents=documents),
            "topics": topics,
            "questions": questions,
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

    def _resolve_accessible_documents(
        self,
        db: Session,
        *,
        document_ids,
        current_user: User | None = None,
        selected_notebook=None,
    ) -> list[Document]:
        documents: list[Document] = []
        for document_id in document_ids:
            documents.append(
                self._resolve_accessible_document(
                    db,
                    document_id=document_id,
                    current_user=current_user,
                    selected_notebook=selected_notebook,
                )
            )
        return documents

    def _requested_document_ids(self, request: ChatbotAskRequest | ChatbotSuggestionsRequest) -> list[object]:
        document_ids: list[object] = []
        seen: set[str] = set()
        for document_id in [request.document_id, *request.document_ids]:
            if document_id is None:
                continue
            normalized = str(document_id)
            if normalized in seen:
                continue
            seen.add(normalized)
            document_ids.append(document_id)
        return document_ids

    def _common_notebook_id(self, documents: list[Document]):
        notebook_ids = {document.notebook_id for document in documents}
        if len(notebook_ids) == 1:
            return next(iter(notebook_ids))
        return None

    def _load_suggestion_chunks(
        self,
        db: Session,
        *,
        documents: list[Document],
    ) -> dict[object, list[DocumentChunk]]:
        if not documents:
            return {}

        document_ids = [document.id for document in documents]
        statement = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id.in_(document_ids))
            .order_by(DocumentChunk.document_id.asc(), DocumentChunk.chunk_index.asc())
            .limit(max(12, min(60, len(document_ids) * 12)))
        )
        grouped_chunks: dict[object, list[DocumentChunk]] = defaultdict(list)
        for chunk in db.scalars(statement).all():
            grouped_chunks[chunk.document_id].append(chunk)
        return dict(grouped_chunks)

    def _suggestion_topics(
        self,
        *,
        documents: list[Document],
        chunks_by_document_id: dict[object, list[DocumentChunk]],
    ) -> list[str]:
        topics: list[str] = []
        for document in documents:
            topic = self._metadata_topic(document) or self._content_topic(chunks_by_document_id.get(document.id, []))
            if topic:
                topics.append(topic)

        if len(topics) < 5:
            combined_text = " ".join(
                chunk.content
                for chunks in chunks_by_document_id.values()
                for chunk in chunks[:6]
            )
            for keyword in self._keywords_from_text(combined_text):
                if keyword not in topics:
                    topics.append(keyword)
                if len(topics) >= 5:
                    break

        return [topic for topic in topics if topic][:5]

    def _metadata_topic(self, document: Document) -> str | None:
        metadata = dict(document.extra_metadata or {})
        for key in ("display_title", "title", "document_title", "pdf_title", "extracted_title", "subject", "topic", "summary_title"):
            value = metadata.get(key)
            if isinstance(value, str):
                normalized = self._clean_topic(value)
                if normalized:
                    return normalized
        return None

    def _content_topic(self, chunks: list[DocumentChunk]) -> str | None:
        for chunk in chunks[:4]:
            for line in chunk.content.splitlines():
                normalized = self._clean_topic(line)
                if normalized and 2 <= len(normalized.split()) <= 18:
                    return normalized
        keywords = self._keywords_from_text(" ".join(chunk.content for chunk in chunks[:8]))
        if keywords:
            return keywords[0]
        return None

    def _clean_topic(self, value: str) -> str | None:
        normalized = " ".join(value.replace("\x00", " ").split()).strip(" -:;,.")
        if not normalized:
            return None
        normalized = re.sub(r"^(title|topic|subject|abstract|summary)\s*[:\-]\s*", "", normalized, flags=re.IGNORECASE)
        if len(normalized) < 4 or len(normalized) > 120:
            return None
        if re.fullmatch(r"[\d.\-_vV]+", normalized):
            return None
        if ".pdf" in normalized.lower():
            return None
        if re.fullmatch(r"[\W_]+", normalized):
            return None
        return normalized[:1].upper() + normalized[1:]

    def _keywords_from_text(self, text: str) -> list[str]:
        words = [
            word.lower()
            for word in re.findall(r"[^\W\d_][\w\-]{3,}", text, flags=re.UNICODE)
            if word.lower() not in _SUGGESTION_STOPWORDS and ".pdf" not in word.lower()
        ]
        return [word for word, _count in Counter(words).most_common(8)]

    def _suggestion_title(self, *, documents: list[Document]) -> str:
        file_names = [document.original_file_name for document in documents if document.original_file_name]
        return " / ".join(file_names) if file_names else "Selected sources"

    def _document_history_metadata(self, documents: list[Document]) -> dict[str, object]:
        document_names = [document.original_file_name for document in documents if document.original_file_name]
        return {
            "document_names": document_names,
            "document_name": document_names[0] if len(document_names) == 1 else None,
        }

    def _empty_suggestions(self, *, language: str) -> dict[str, object]:
        return {
            "title": "No source selected",
            "topics": [],
            "questions": [],
        }

    def _build_suggestion_questions(
        self,
        *,
        topics: list[str],
        document_count: int,
        language: str,
    ) -> list[str]:
        primary = topics[0] if topics else "the selected material"

        if document_count > 1:
            questions = [
                "Compare the approaches discussed across the selected sources.",
                "What common themes appear in the selected documents?",
                "Summarize the key findings from all selected sources.",
                f"How are the selected documents related in their discussion of {primary}?",
                "Where do the sources complement, contradict, or leave gaps between each other?",
            ]
        else:
            questions = [
                "What are the main ideas presented in this paper?",
                "What problem or motivation does this report focus on?",
                "What approach, architecture, or method is described in this document?",
                "What evidence or examples are presented in this file?",
                "What challenges, limitations, or future work does this document discuss?",
            ]

        return questions[:5]
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
        accessible_documents: list[Document] | None = None,
        save_history: bool = False,
    ):
        if selected_notebook is not None:
            return selected_notebook
        if current_user is None or not save_history:
            return None
        accessible_documents = accessible_documents or []
        first_notebook_document = next(
            (document for document in accessible_documents if document.notebook_id is not None),
            None,
        )
        if first_notebook_document is not None:
            return auth_service.get_user_notebook(
                db,
                user_id=current_user.id,
                notebook_id=first_notebook_document.notebook_id,
            )
        return auth_service.resolve_user_notebook(
            db,
            user=current_user,
            notebook_id=None,
        )


chatbot_service = ChatbotService()

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import unicodedata

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger

from app.config import get_settings
from app.services.retrieval.models import ChunkCandidate


@dataclass(slots=True)
class AnswerGenerationResult:
    answer: str
    provider: str
    model_name: str | None
    used_fallback: bool


class AnswerGenerationError(Exception):
    pass


def _build_context_block(candidates: list[ChunkCandidate]) -> str:
    lines: list[str] = []
    for index, candidate in enumerate(candidates, start=1):
        page_label = "-"
        if candidate.page_from and candidate.page_to:
            if candidate.page_from == candidate.page_to:
                page_label = str(candidate.page_from)
            else:
                page_label = f"{candidate.page_from}-{candidate.page_to}"
        excerpt = " ".join(candidate.content.split())
        lines.append(
            f"[{index}] file={candidate.original_file_name or '-'} page={page_label} "
            f"chunk={candidate.chunk_index}\n{excerpt}"
        )
    return "\n\n".join(lines)


def _answer_language_for(query: str) -> str:
    normalized = query.lower()
    decomposed = unicodedata.normalize("NFD", normalized)
    if "đ" in normalized or any(unicodedata.combining(char) for char in decomposed):
        return "Vietnamese"
    return "the same language as the question"


def _clean_model_answer(answer: str) -> str:
    cleaned_lines = []
    for line in answer.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("(vietnamese:") and stripped.endswith(")"):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def _extractive_fallback(query: str, candidates: list[ChunkCandidate]) -> AnswerGenerationResult:
    if not candidates:
        return AnswerGenerationResult(
            answer=(
                "No relevant context was retrieved for this question. "
                "Upload or re-ingest documents before asking the chatbot."
            ),
            provider="extractive",
            model_name=None,
            used_fallback=True,
        )

    snippets = []
    for index, candidate in enumerate(candidates[:3], start=1):
        excerpt = " ".join(candidate.content.split())
        if len(excerpt) > 280:
            excerpt = f"{excerpt[:280]}..."
        snippets.append(f"[{index}] {excerpt}")

    return AnswerGenerationResult(
        answer=(
            "No external chat model is configured, so this is a retrieval-grounded fallback response.\n\n"
            + "\n".join(snippets)
        ),
        provider="extractive",
        model_name=None,
        used_fallback=True,
    )


@lru_cache
def _get_ollama_model():
    settings = get_settings()
    if not settings.ollama_model_name:
        raise AnswerGenerationError("OLLAMA_MODEL_NAME is not configured.")

    from langchain_ollama import ChatOllama

    return ChatOllama(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model_name,
        temperature=settings.chat_temperature,
    )


@lru_cache
def _get_google_model():
    settings = get_settings()
    if not settings.google_model_name or not settings.google_api_key:
        raise AnswerGenerationError("GOOGLE_MODEL_NAME or GOOGLE_API_KEY is not configured.")

    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=settings.google_model_name,
        google_api_key=settings.google_api_key,
        temperature=settings.chat_temperature,
    )


@lru_cache
def _get_prompt_template() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a careful document-grounded chatbot. "
                "Use only the supplied context; do not add outside knowledge. "
                "If the user asks for a summary, main idea, overview, or purpose of the document, "
                "summarize the entire document instead of answering from a small retrieved chunk. "
                "If the context does not contain enough evidence, say that the document does not provide enough information. "
                "If the answer cannot be determined from retrieved content, explicitly state that instead of hallucinating. "
                "Follow the required answer language exactly. "
                "If the required answer language is Vietnamese, every sentence must be Vietnamese and must not be English. "
                "Do not include translations, bilingual notes, or parenthetical restatements in another language. "
                "Write directly, without greetings or preambles. "
                "Synthesize the relevant facts into 2-5 concise sentences or short bullets. "
                "Cite every factual claim with supporting snippet numbers like [1], [2].",
            ),
            (
                "human",
                "Required answer language: {answer_language}\n\nQuestion:\n{question}\n\nContext:\n{context}",
            ),
        ]
    )


@lru_cache
def _get_summary_prompt_template() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a careful document-grounded summarization assistant. "
                "Use only the supplied document-level context; do not add outside knowledge. "
                "The user is asking for a summary, main idea, overview, or purpose of the document, "
                "so summarize the entire document represented by the supplied title, structural sections, "
                "and representative excerpts instead of focusing on one small passage. "
                "If the context does not contain enough evidence, explicitly say that the document content is insufficient. "
                "Follow the required answer language exactly. "
                "If the required answer language is Vietnamese, every sentence must be Vietnamese and must not be English. "
                "Write a concise summary followed by 3-6 key points. "
                "Cite every factual claim with supporting snippet numbers like [1], [2]. "
                "Prefer citing title/front matter, abstract, introduction, and conclusion snippets when available.",
            ),
            (
                "human",
                "Required answer language: {answer_language}\n\n"
                "Document title: {document_title}\n\n"
                "Question:\n{question}\n\n"
                "Document-level context:\n{context}",
            ),
        ]
    )


def _run_model_chain(*, model, query: str, candidates: list[ChunkCandidate]) -> str:
    chain = _get_prompt_template() | model | StrOutputParser()
    answer = chain.invoke(
        {
            "question": query,
            "answer_language": _answer_language_for(query),
            "context": _build_context_block(candidates),
        }
    )
    return _clean_model_answer(answer)


def _run_summary_chain(*, model, query: str, candidates: list[ChunkCandidate], document_title: str) -> str:
    chain = _get_summary_prompt_template() | model | StrOutputParser()
    answer = chain.invoke(
        {
            "question": query,
            "answer_language": _answer_language_for(query),
            "document_title": document_title,
            "context": _build_context_block(candidates),
        }
    )
    return _clean_model_answer(answer)


def generate_answer(*, query: str, candidates: list[ChunkCandidate]) -> AnswerGenerationResult:
    if not candidates:
        return _extractive_fallback(query, candidates)

    settings = get_settings()
    provider = (settings.chat_provider or "extractive").strip().lower()

    if provider == "extractive":
        return _extractive_fallback(query, candidates)

    try:
        if provider == "ollama":
            return AnswerGenerationResult(
                answer=_run_model_chain(model=_get_ollama_model(), query=query, candidates=candidates),
                provider="ollama",
                model_name=settings.ollama_model_name,
                used_fallback=False,
            )

        if provider == "google":
            return AnswerGenerationResult(
                answer=_run_model_chain(model=_get_google_model(), query=query, candidates=candidates),
                provider="google",
                model_name=settings.google_model_name,
                used_fallback=False,
            )

        if provider == "auto":
            if settings.google_model_name and settings.google_api_key:
                return AnswerGenerationResult(
                    answer=_run_model_chain(model=_get_google_model(), query=query, candidates=candidates),
                    provider="google",
                    model_name=settings.google_model_name,
                    used_fallback=False,
                )
            if settings.ollama_model_name:
                return AnswerGenerationResult(
                    answer=_run_model_chain(model=_get_ollama_model(), query=query, candidates=candidates),
                    provider="ollama",
                    model_name=settings.ollama_model_name,
                    used_fallback=False,
                )
    except Exception as exc:
        logger.exception(
            "Chat generation failed with provider={} model={}; falling back to extractive response: {}",
            provider,
            settings.ollama_model_name if provider == "ollama" else settings.google_model_name,
            exc,
        )
        return _extractive_fallback(query, candidates)

    return _extractive_fallback(query, candidates)


def generate_document_summary(
    *,
    query: str,
    candidates: list[ChunkCandidate],
    document_title: str,
) -> AnswerGenerationResult:
    if not candidates:
        return _extractive_fallback(query, candidates)

    settings = get_settings()
    provider = (settings.chat_provider or "extractive").strip().lower()

    if provider == "extractive":
        return _extractive_fallback(query, candidates)

    try:
        if provider == "ollama":
            return AnswerGenerationResult(
                answer=_run_summary_chain(
                    model=_get_ollama_model(),
                    query=query,
                    candidates=candidates,
                    document_title=document_title,
                ),
                provider="ollama",
                model_name=settings.ollama_model_name,
                used_fallback=False,
            )

        if provider == "google":
            return AnswerGenerationResult(
                answer=_run_summary_chain(
                    model=_get_google_model(),
                    query=query,
                    candidates=candidates,
                    document_title=document_title,
                ),
                provider="google",
                model_name=settings.google_model_name,
                used_fallback=False,
            )

        if provider == "auto":
            if settings.google_model_name and settings.google_api_key:
                return AnswerGenerationResult(
                    answer=_run_summary_chain(
                        model=_get_google_model(),
                        query=query,
                        candidates=candidates,
                        document_title=document_title,
                    ),
                    provider="google",
                    model_name=settings.google_model_name,
                    used_fallback=False,
                )
            if settings.ollama_model_name:
                return AnswerGenerationResult(
                    answer=_run_summary_chain(
                        model=_get_ollama_model(),
                        query=query,
                        candidates=candidates,
                        document_title=document_title,
                    ),
                    provider="ollama",
                    model_name=settings.ollama_model_name,
                    used_fallback=False,
                )
    except Exception as exc:
        logger.exception(
            "Document summary generation failed with provider={} model={}; falling back to extractive response: {}",
            provider,
            settings.ollama_model_name if provider == "ollama" else settings.google_model_name,
            exc,
        )
        return _extractive_fallback(query, candidates)

    return _extractive_fallback(query, candidates)

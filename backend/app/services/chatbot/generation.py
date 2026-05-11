from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import get_settings
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
                "You are a grounded retrieval chatbot. "
                "Answer only from the supplied context. "
                "If the context is insufficient, say so explicitly. "
                "Answer in the same language as the user's question. "
                "Keep the answer concise and cite supporting snippets as [1], [2], ...",
            ),
            (
                "human",
                "Question:\n{question}\n\nContext:\n{context}",
            ),
        ]
    )


def _run_model_chain(*, model, query: str, candidates: list[ChunkCandidate]) -> str:
    chain = _get_prompt_template() | model | StrOutputParser()
    return chain.invoke(
        {
            "question": query,
            "context": _build_context_block(candidates),
        }
    ).strip()


def generate_answer(*, query: str, candidates: list[ChunkCandidate]) -> AnswerGenerationResult:
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
    except Exception:
        return _extractive_fallback(query, candidates)

    return _extractive_fallback(query, candidates)

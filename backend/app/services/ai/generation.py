from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import re

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


def _required_answer_language(query: str, language: str | None = None) -> str:
    return "English"


def _answer_language_for(query: str) -> str:
    return "English"


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


def _clean_model_answer(answer: str) -> str:
    cleaned_lines = []
    for line in answer.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("(translation:") and stripped.endswith(")"):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def _is_low_information_answer(*, query: str, answer: str) -> bool:
    without_citations = re.sub(r"\[\d+\]", " ", answer)
    normalized_answer = " ".join(without_citations.strip().split()).strip(" .,:;!?\"'")
    if not normalized_answer:
        return True
    normalized_query = " ".join(query.strip().split()).strip(" .,:;!?\"'")
    if normalized_query and normalized_answer.lower() == normalized_query.lower():
        return True
    lower_answer = normalized_answer.lower()
    navigation_starts = ("see ", "refer to ", "look at ")
    if any(lower_answer.startswith(prefix) for prefix in navigation_starts):
        return True
    return len(normalized_answer.split()) <= 2


def _has_language_mismatch(*, answer: str, required_language: str) -> bool:
    if required_language != "English":
        return False
    answer_without_citations = re.sub(r"\[\d+\]", "", answer)
    return any(ord(char) > 127 for char in answer_without_citations)


def _is_unhelpful_insufficient_answer(answer: str) -> bool:
    lowered = answer.lower()
    markers = (
        "does not provide",
        "does not contain",
        "not enough information",
        "cannot be determined",
    )
    return any(marker in lowered for marker in markers)


def _insufficient_answer_for(language: str | None = None) -> str:
    return "The document does not provide enough information to answer this question."


def _sentence_candidates(text: str) -> list[str]:
    normalized = " ".join(text.replace("\x00", " ").split())
    if not normalized:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", normalized)
    useful = []
    for sentence in sentences:
        sentence = sentence.strip(" -\t\r\n")
        word_count = len(sentence.split())
        if 6 <= word_count <= 80:
            useful.append(sentence)
    if useful:
        return useful
    return [normalized[:320].strip()]


def _query_terms(query: str) -> set[str]:
    stopwords = {"show", "what", "where", "when", "how", "why", "the", "this", "that", "are", "is"}
    return {
        term.lower()
        for term in re.findall(r"[^\W\d_][\w\-]{2,}", query, flags=re.UNICODE)
        if term.lower() not in stopwords
    }


def _extractive_synthesis(
    *,
    query: str,
    candidates: list[ChunkCandidate],
    language: str | None = None,
    max_points: int = 3,
) -> str:
    if not candidates:
        return _insufficient_answer_for()

    terms = _query_terms(query)
    ranked: list[tuple[int, int, str]] = []
    for source_index, candidate in enumerate(candidates[:5], start=1):
        for sentence in _sentence_candidates(candidate.content)[:4]:
            score = sum(1 for term in terms if term in sentence.lower())
            ranked.append((score, source_index, sentence))

    ranked.sort(key=lambda item: item[0], reverse=True)
    selected: list[tuple[int, str]] = []
    seen: set[str] = set()
    for _score, source_index, sentence in ranked:
        normalized = sentence.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        selected.append((source_index, sentence))
        if len(selected) >= max_points:
            break

    if not selected:
        return _insufficient_answer_for()

    lines = ["Summary from the relevant passages:"]
    lines.extend(f"- {sentence} [{source_index}]" for source_index, sentence in selected)
    return "\n".join(lines)


def _extractive_fallback(
    query: str,
    candidates: list[ChunkCandidate],
    language: str | None = None,
) -> AnswerGenerationResult:
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

    synthesis = _extractive_synthesis(query=query, candidates=candidates)
    return AnswerGenerationResult(
        answer=(
            "No external chat model is configured, so this is a synthesized fallback from retrieved passages.\n\n"
            + synthesis
        ),
        provider="extractive",
        model_name=None,
        used_fallback=True,
    )


def generate_no_relevant_document_answer() -> AnswerGenerationResult:
    return AnswerGenerationResult(
        answer=(
            "No related document found. This question does not appear to be covered by the "
            "content of the uploaded documents."
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
                "Answer only in English using only the supplied context and no outside knowledge. "
                "Synthesize relevant evidence, especially any tools, techniques, workflows, UI, or database actions. "
                "Label indirect conclusions as inferences and do not overstate them. "
                "Do not claim insufficient information when relevant evidence exists. "
                "Only when there is truly not enough evidence, reply exactly: "
                "'The document does not provide enough information to answer this question.' "
                "Answer in 2-5 concise sentences or short bullets and support claims with citations such as [1], [2].",
            ),
            (
                "human",
                "Required answer language: English\n\nQuestion:\n{question}\n\nContext:\n{context}",
            ),
        ]
    )


@lru_cache
def _get_summary_prompt_template() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Answer only in English using only the supplied document context and no outside knowledge. "
                "Summarize the document as a whole from its title, sections, and representative excerpts. "
                "Clearly synthesize any tools, techniques, workflows, UI, or database actions mentioned. "
                "Label indirect conclusions as inferences and do not overstate them. "
                "Do not claim insufficient information when relevant evidence exists. "
                "Only when there is truly not enough evidence, reply exactly: "
                "'The document does not provide enough information to answer this question.' "
                "Answer in 2-5 concise sentences or short bullets and support claims with citations such as [1], [2].",
            ),
            (
                "human",
                "Required answer language: English\n\n"
                "Document title: {document_title}\n\n"
                "Question:\n{question}\n\n"
                "Document-level context:\n{context}",
            ),
        ]
    )


def _run_model_chain(*, model, query: str, candidates: list[ChunkCandidate], language: str | None = None) -> str:
    chain = _get_prompt_template() | model | StrOutputParser()
    answer = chain.invoke(
        {
            "question": query,
            "context": _build_context_block(candidates),
        }
    )
    cleaned = _clean_model_answer(answer)
    if (
        _is_low_information_answer(query=query, answer=cleaned)
        or _has_language_mismatch(answer=cleaned, required_language="English")
        or _is_unhelpful_insufficient_answer(cleaned)
    ):
        return _extractive_synthesis(query=query, candidates=candidates)
    return cleaned


def _run_summary_chain(
    *,
    model,
    query: str,
    candidates: list[ChunkCandidate],
    document_title: str,
    language: str | None = None,
) -> str:
    chain = _get_summary_prompt_template() | model | StrOutputParser()
    answer = chain.invoke(
        {
            "question": query,
            "document_title": document_title,
            "context": _build_context_block(candidates),
        }
    )
    cleaned = _clean_model_answer(answer)
    if (
        _is_low_information_answer(query=query, answer=cleaned)
        or _has_language_mismatch(answer=cleaned, required_language="English")
        or _is_unhelpful_insufficient_answer(cleaned)
    ):
        return _extractive_synthesis(query=query, candidates=candidates, max_points=5)
    return cleaned


def generate_answer(*, query: str, candidates: list[ChunkCandidate], language: str | None = None) -> AnswerGenerationResult:
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
    language: str | None = None,
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

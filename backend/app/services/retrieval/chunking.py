from __future__ import annotations

from functools import lru_cache

import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings


@lru_cache
def _get_tokenizer():
    return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int | None:
    try:
        return len(_get_tokenizer().encode(text))
    except Exception:
        return None


def build_chunks(page_entries: list[dict[str, int | str]]) -> list[dict[str, object]]:
    settings = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.document_chunk_size,
        chunk_overlap=settings.document_chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )

    chunks: list[dict[str, object]] = []
    chunk_index = 0

    for entry in page_entries:
        page_number = int(entry["page_number"])
        page_text = str(entry["text"])
        for piece in splitter.split_text(page_text):
            chunk_text = piece.strip()
            if not chunk_text:
                continue

            chunks.append(
                {
                    "chunk_index": chunk_index,
                    "page_from": page_number,
                    "page_to": page_number,
                    "content": chunk_text,
                    "token_count": count_tokens(chunk_text),
                    "character_count": len(chunk_text),
                    "metadata": {
                        "page_number": page_number,
                        "chunk_size": settings.document_chunk_size,
                        "chunk_overlap": settings.document_chunk_overlap,
                    },
                }
            )
            chunk_index += 1

    return chunks

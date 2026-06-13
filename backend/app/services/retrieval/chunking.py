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
        page_blocks = entry.get("blocks") if isinstance(entry, dict) else None
        if page_blocks:
            for chunk in _build_bbox_chunks_for_page(
                page_number=page_number,
                blocks=list(page_blocks),
                page_width=float(entry.get("width") or 0),
                page_height=float(entry.get("height") or 0),
                chunk_index_start=chunk_index,
                chunk_size=settings.document_chunk_size,
            ):
                chunks.append(chunk)
                chunk_index += 1
            continue

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


def _build_bbox_chunks_for_page(
    *,
    page_number: int,
    blocks: list[object],
    page_width: float,
    page_height: float,
    chunk_index_start: int,
    chunk_size: int,
) -> list[dict[str, object]]:
    chunks: list[dict[str, object]] = []
    current_texts: list[str] = []
    current_bboxes: list[list[float]] = []
    chunk_index = chunk_index_start

    def flush() -> None:
        nonlocal chunk_index, current_texts, current_bboxes
        chunk_text = "\n\n".join(current_texts).strip()
        if not chunk_text or not current_bboxes:
            current_texts = []
            current_bboxes = []
            return

        bbox = _union_bbox(current_bboxes)
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
                    "page_width": page_width,
                    "page_height": page_height,
                    "bbox": bbox,
                    "quoted_text": chunk_text,
                    "block_count": len(current_bboxes),
                },
            }
        )
        chunk_index += 1
        current_texts = []
        current_bboxes = []

    for block in blocks:
        if not isinstance(block, dict):
            continue
        text = " ".join(str(block.get("text") or "").split())
        bbox = block.get("bbox")
        if not text or not _is_bbox(bbox):
            continue
        current_length = sum(len(item) for item in current_texts)
        if current_texts and current_length + len(text) > chunk_size:
            flush()
        current_texts.append(text)
        current_bboxes.append([float(value) for value in bbox])

    flush()
    return chunks


def _is_bbox(value: object) -> bool:
    return isinstance(value, list) and len(value) == 4 and all(isinstance(item, (int, float)) for item in value)


def _union_bbox(bboxes: list[list[float]]) -> list[float]:
    return [
        min(bbox[0] for bbox in bboxes),
        min(bbox[1] for bbox in bboxes),
        max(bbox[2] for bbox in bboxes),
        max(bbox[3] for bbox in bboxes),
    ]

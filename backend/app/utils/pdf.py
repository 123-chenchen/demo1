from __future__ import annotations

from typing import BinaryIO

import fitz
from pypdf import PdfReader
from pypdf.errors import PdfReadError

PDF_SIGNATURE = b"%PDF-"
READ_CHUNK_SIZE = 1024 * 1024


class PdfReadServiceError(Exception):
    pass

# Hàm để kiểm tra xem tệp đã tải lên có phải là PDF hợp lệ bằng cách đọc các byte đầu tiên và so sánh với chữ ký PDF. Nếu tệp không phải là PDF hoặc có lỗi khi đọc, nó sẽ ném ra lỗi PdfReadServiceError với thông điệp chi tiết về lý do thất bại. Hàm này cũng sẽ trả về kích thước của tệp PDF nếu nó hợp lệ, điều này có thể hữu ích để xác thực thêm hoặc để lưu metadata của tài liệu trong cơ sở dữ liệu.
def inspect_pdf(file_obj: BinaryIO) -> int: 
    file_obj.seek(0)
    signature = file_obj.read(len(PDF_SIGNATURE))
    if signature != PDF_SIGNATURE:
        raise PdfReadServiceError("Only valid PDF files are supported.")

    file_obj.seek(0)
    file_size_bytes = 0

    while True:
        chunk = file_obj.read(READ_CHUNK_SIZE)
        if not chunk:
            break
        file_size_bytes += len(chunk)

    if file_size_bytes == 0:
        raise PdfReadServiceError("Uploaded PDF is empty.")

    file_obj.seek(0)
    return file_size_bytes


def extract_page_count(file_obj: BinaryIO) -> int | None:
    try:
        file_obj.seek(0)
        page_count = len(PdfReader(file_obj).pages)
    except (PdfReadError, ValueError, OSError):
        page_count = None
    finally:
        file_obj.seek(0)

    return page_count


def extract_pdf_metadata(file_obj: BinaryIO) -> dict[str, str]:
    metadata: dict[str, str] = {}

    try:
        file_obj.seek(0)
        pdf_bytes = file_obj.read()
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
        raw_metadata = document.metadata or {}
        title = _clean_metadata_value(raw_metadata.get("title"))
        if title:
            metadata["pdf_title"] = title
    except Exception:
        pass
    finally:
        try:
            document.close()
        except Exception:
            pass
        file_obj.seek(0)

    if metadata.get("pdf_title"):
        return metadata

    try:
        reader = PdfReader(file_obj)
        raw_title = getattr(reader.metadata, "title", None) if reader.metadata else None
        title = _clean_metadata_value(raw_title)
        if title:
            metadata["pdf_title"] = title
    except (PdfReadError, ValueError, OSError):
        pass
    finally:
        file_obj.seek(0)

    return metadata


def extract_pdf_pages(file_buffer: BinaryIO) -> list[dict[str, int | str]]:
    try:
        return extract_pdf_pages_with_bboxes(file_buffer)
    except PdfReadServiceError:
        raise
    except Exception:
        file_buffer.seek(0)

    try:
        reader = PdfReader(file_buffer)
    except PdfReadError as exc:
        raise PdfReadServiceError("Could not parse the uploaded PDF.") from exc

    page_entries: list[dict[str, int | str]] = []
    for page_number, page in enumerate(reader.pages, start=1):
        extracted_text = (page.extract_text() or "").strip()
        if not extracted_text:
            continue
        page_entries.append(
            {
                "page_number": page_number,
                "text": extracted_text,
            }
        )

    if not page_entries:
        raise PdfReadServiceError("No extractable text was found in the PDF.")

    return page_entries


def extract_pdf_pages_with_bboxes(file_buffer: BinaryIO) -> list[dict[str, object]]:
    try:
        file_buffer.seek(0)
        pdf_bytes = file_buffer.read()
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise PdfReadServiceError("Could not parse the uploaded PDF.") from exc
    finally:
        file_buffer.seek(0)

    page_entries: list[dict[str, object]] = []
    try:
        for page_index, page in enumerate(document, start=1):
            blocks: list[dict[str, object]] = []
            text_parts: list[str] = []
            for block in page.get_text("blocks"):
                if len(block) < 5:
                    continue
                x0, y0, x1, y1, text = block[:5]
                block_text = " ".join(str(text or "").split())
                if not block_text:
                    continue
                bbox = [float(x0), float(y0), float(x1), float(y1)]
                blocks.append({"text": block_text, "bbox": bbox})
                text_parts.append(block_text)

            page_text = "\n\n".join(text_parts).strip()
            if not page_text:
                continue

            rect = page.rect
            page_entries.append(
                {
                    "page_number": page_index,
                    "text": page_text,
                    "width": float(rect.width),
                    "height": float(rect.height),
                    "blocks": blocks,
                }
            )
    finally:
        document.close()

    if not page_entries:
        raise PdfReadServiceError("No extractable text was found in the PDF.")

    return page_entries


def _clean_metadata_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.replace("\x00", " ").split()).strip()
    if not normalized or normalized.lower() in {"untitled", "none"}:
        return None
    return normalized

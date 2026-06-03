from __future__ import annotations

from typing import BinaryIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

PDF_SIGNATURE = b"%PDF-"
READ_CHUNK_SIZE = 1024 * 1024


class PdfReadServiceError(Exception):
    pass


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


def extract_pdf_pages(file_buffer: BinaryIO) -> list[dict[str, int | str]]:
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

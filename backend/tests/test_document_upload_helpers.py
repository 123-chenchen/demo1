from __future__ import annotations

import io
import re

import pytest

from app.services.document_upload import (
    DocumentUploadValidationError,
    _build_object_name,
    _inspect_pdf,
    _normalize_filename,
)


@pytest.mark.parametrize(
    ("raw_name", "expected"),
    [
        (None, "document.pdf"),
        ("", "document.pdf"),
        ("folder/subdir/report.pdf", "report.pdf"),
        (r"C:\temp\report.pdf", "report.pdf"),
    ],
)
def test_normalize_filename_handles_missing_and_nested_paths(raw_name: str | None, expected: str) -> None:
    assert _normalize_filename(raw_name) == expected


def test_build_object_name_creates_minio_friendly_pdf_path() -> None:
    object_name = _build_object_name("Quarterly Report.pdf")

    assert re.match(
        r"^documents/\d{4}/\d{2}/\d{2}/[0-9a-f-]+-Quarterly-Report\.pdf$",
        object_name,
    )


def test_inspect_pdf_returns_file_size() -> None:
    payload = b"%PDF-1.4\nFake PDF content\n%%EOF"
    file_obj = io.BytesIO(payload)

    file_size_bytes = _inspect_pdf(file_obj)

    assert file_size_bytes == len(payload)


def test_inspect_pdf_rejects_invalid_signature() -> None:
    with pytest.raises(DocumentUploadValidationError, match="Only valid PDF files are supported."):
        _inspect_pdf(io.BytesIO(b"not-a-pdf"))

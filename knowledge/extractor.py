"""
AKI Knowledge Extractor.

Pulls page-anchored text out of supported documents:
    - PDF  (via pypdf — every page keeps its number)
    - TXT / Markdown (whole file becomes page 1)

Extraction is deliberately forgiving: broken encodings and odd
characters are normalized instead of raising, because real-world
cybersecurity PDFs are messy.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from knowledge.models import Book

_SUPPORTED_EXTENSIONS = frozenset({".pdf", ".txt", ".md"})

_WHITESPACE = re.compile(r"[ \t]+")
_BLANK_LINES = re.compile(r"\n{3,}")


class KnowledgeExtractionError(Exception):
    """Raised when a document cannot be extracted at all."""


def is_supported(path: str | Path) -> bool:
    """Return whether the file type can be ingested."""

    return Path(path).suffix.lower() in _SUPPORTED_EXTENSIONS


def extract_pages(path: str | Path) -> tuple[Book, list[tuple[int, str]]]:
    """
    Extract page-numbered text from one document.

    Args:
        path: Path to a PDF, TXT, or Markdown file.

    Returns:
        Tuple of (Book metadata, [(page_number, text), ...]).
        Page numbers start at 1.

    Raises:
        KnowledgeExtractionError: If the file is missing, unsupported,
            or yields no readable text at all.
    """

    file_path = Path(path)

    if not file_path.exists():
        raise KnowledgeExtractionError(
            f"File not found: {file_path}"
        )

    if not is_supported(file_path):
        raise KnowledgeExtractionError(
            f"Unsupported format '{file_path.suffix}'. "
            "Supported: PDF, TXT, MD."
        )

    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        pages = _extract_pdf(file_path)
    else:
        pages = _extract_text_file(file_path)

    pages = [
        (page, _normalize_text(text))
        for page, text in pages
        if text and text.strip()
    ]

    if not pages:
        raise KnowledgeExtractionError(
            f"No readable text found in '{file_path.name}'. "
            "Scanned/image-only PDFs are not supported yet."
        )

    book = Book(
        book_id=_make_book_id(file_path),
        title=file_path.stem,
        source_path=str(file_path),
        page_count=pages[-1][0],
    )

    return book, pages


def _extract_pdf(file_path: Path) -> list[tuple[int, str]]:
    """Extract text page-by-page so page numbers stay truthful."""

    try:
        from pypdf import PdfReader
    except ImportError as error:  # pragma: no cover
        raise KnowledgeExtractionError(
            "pypdf is not installed."
        ) from error

    try:
        reader = PdfReader(str(file_path))
    except Exception as error:
        raise KnowledgeExtractionError(
            f"PDF could not be opened: {error}"
        ) from error

    # Most real-world PDFs are AES-encrypted with an empty user
    # password (owner restrictions only) — decrypt automatically.
    if getattr(reader, "is_encrypted", False):
        try:
            reader.decrypt("")
        except Exception as error:
            raise KnowledgeExtractionError(
                "PDF password-protected hai. Bina password extract nahi "
                "ho sakti."
            ) from error

    pages: list[tuple[int, str]] = []

    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""

        pages.append((index, text))

    return pages


def _extract_text_file(file_path: Path) -> list[tuple[int, str]]:
    """Read a plain text file as a single page."""

    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as error:
        raise KnowledgeExtractionError(
            f"File could not be read: {error}"
        ) from error

    return [(1, text)]


def _normalize_text(text: str) -> str:
    """Clean extraction artifacts while preserving line structure."""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WHITESPACE.sub(" ", text)
    text = _BLANK_LINES.sub("\n\n", text)
    return text.strip()


def _make_book_id(file_path: Path) -> str:
    """
    Stable id from the file NAME only.

    Name-based identity gives replace-on-reingest semantics: updating
    a book's file and ingesting again refreshes its chunks instead of
    creating a duplicate library entry.
    """

    digest = hashlib.md5(  # noqa: S324 - non-crypto dedupe key only
        file_path.name.lower().encode("utf-8")
    ).hexdigest()[:12]

    return f"book_{digest}"


__all__ = [
    "KnowledgeExtractionError",
    "extract_pages",
    "is_supported",
]

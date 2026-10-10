"""
AKI Knowledge Models.

Data structures for the book/document intelligence subsystem.
Representation only — no extraction, storage, or search logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class Book:
    """
    One ingested document.

    Attributes:
        book_id: Stable identifier (content hash based).
        title: Display title (file name without extension).
        source_path: Original file location.
        page_count: Total pages extracted.
        ingested_at: ISO timestamp of ingestion.
    """

    book_id: str
    title: str
    source_path: str
    page_count: int
    ingested_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    topics: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class BookChunk:
    """
    A page-anchored piece of a book.

    Every chunk remembers exactly where it came from so AKI can
    answer "page 142 ki line 5" style questions and cite pages.
    """

    chunk_id: str
    book_id: str
    book_title: str
    page: int
    sequence: int
    text: str

    def __post_init__(self) -> None:
        """Validate the chunk."""

        if not self.text.strip():
            raise ValueError(
                "chunk text cannot be empty."
            )

        if self.page < 1:
            raise ValueError(
                "page numbers start at 1."
            )


@dataclass(frozen=True)
class KnowledgeMatch:
    """One search hit with its location for citations."""

    chunk: BookChunk
    score: float


__all__ = [
    "Book",
    "BookChunk",
    "KnowledgeMatch",
]

"""AKI Knowledge Subsystem — book/document intelligence."""

from knowledge.extractor import (
    KnowledgeExtractionError,
    extract_pages,
    is_supported,
)
from knowledge.models import Book, BookChunk, KnowledgeMatch
from knowledge.store import KnowledgeLibrary

__all__ = [
    "Book",
    "BookChunk",
    "KnowledgeExtractionError",
    "KnowledgeLibrary",
    "KnowledgeMatch",
    "extract_pages",
    "is_supported",
]

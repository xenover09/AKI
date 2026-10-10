"""
AKI Knowledge Library.

Ingests books into page-anchored chunks, persists them through the
DatabaseService, and answers lookups:

    - search(query)            Ranked chunks across all books.
    - lookup_page(book, page)  Exact page retrieval for
                               "page 142 kya likha hai" questions.
    - list_books()             Ingested library.

Ranking is deterministic (phrase + token overlap), matching the
memory subsystem's explainable approach — no external embeddings
required.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from database.database_service import DatabaseService
from knowledge.extractor import extract_pages
from knowledge.models import Book, BookChunk, KnowledgeMatch
from logs.logger import get_logger

logger = get_logger("knowledge.store")

_NAMESPACE = "knowledge"

_CHUNK_TARGET_CHARS = 1_800

_TOKENIZE = re.compile(r"\w{2,}")  # Unicode-aware: Urdu/Arabic script included

# Words that never describe a book's subject.
_TOPIC_STOPWORDS = frozenset(
    {
        "this", "that", "with", "from", "have", "has", "will", "your",
        "what", "when", "where", "which", "their", "them", "they",
        "been", "were", "are", "was", "into", "than", "then", "them",
        "these", "those", "there", "here", "other", "about", "also",
        "because", "should", "could", "would", "might", "shall", "must",
        "each", "such", "more", "most", "some", "any", "all", "one",
        "two", "can", "may", "not", "but", "and", "for", "the", "you",
        "his", "her", "its", "our", "out", "who", "how", "why", "use",
        "using", "used", "example", "examples", "chapter", "page",
        "figure", "table", "note", "notes", "http", "https", "www",
    }
)


def extract_topics(text: str, *, limit: int = 5) -> tuple[str, ...]:
    """
    Derive a book's subject areas from word frequency.

    Deterministic and instant — runs at ingest time so the library
    can answer "ye books kis related hain" without any AI call.
    """

    counts: dict[str, int] = {}

    for token in _TOKENIZE.findall(text.lower()):
        if len(token) < 4 or token in _TOPIC_STOPWORDS:
            continue

        counts[token] = counts.get(token, 0) + 1

    ranked = sorted(counts.items(), key=lambda item: -item[1])

    return tuple(token for token, _count in ranked[:limit])


class KnowledgeLibrary:
    """
    AKI's book brain.

    Responsibilities:
        - Ingest PDF/TXT/MD documents into page-anchored chunks.
        - Persist chunks and book metadata via DatabaseService.
        - Rank chunks for natural-language questions.
        - Retrieve exact pages on demand.
    """

    def __init__(
        self,
        database_service: DatabaseService,
    ) -> None:
        if not isinstance(database_service, DatabaseService):
            raise TypeError(
                "database_service must be a DatabaseService instance."
            )

        self._database = database_service

    # ============================================================
    # Ingestion
    # ============================================================

    def ingest(self, file_path: str) -> Book:
        """
        Extract, chunk, and persist one document.

        Re-ingesting the same file replaces its previous chunks.
        """

        book, pages = extract_pages(file_path)

        # Drop previous version of the same book (name-hash id).
        self._database.delete(_NAMESPACE, book.book_id)

        full_text = "\n".join(text for _page, text in pages)
        topics = extract_topics(full_text)

        chunks: list[BookChunk] = []
        sequence = 0

        for page_number, text in pages:
            for piece in _split_page_text(text):
                sequence += 1
                chunks.append(
                    BookChunk(
                        chunk_id=_chunk_id(book.book_id, sequence),
                        book_id=book.book_id,
                        book_title=book.title,
                        page=page_number,
                        sequence=sequence,
                        text=piece,
                    )
                )

        payload: dict[str, Any] = {
            "book": {
                "book_id": book.book_id,
                "title": book.title,
                "source_path": book.source_path,
                "page_count": book.page_count,
                "ingested_at": book.ingested_at,
                "topics": list(topics),
            },
            "chunks": [
                {
                    "chunk_id": chunk.chunk_id,
                    "page": chunk.page,
                    "sequence": chunk.sequence,
                    "text": chunk.text,
                }
                for chunk in chunks
            ],
        }

        import json

        self._database.save(
            _NAMESPACE,
            book.book_id,
            json.dumps(payload, ensure_ascii=False),
        )

        return book

    # ============================================================
    # Queries
    # ============================================================

    def list_books(self) -> tuple[Book, ...]:
        """Return every ingested book."""

        books: list[Book] = []

        for record in self._database.list(_NAMESPACE):
            try:
                import json

                payload = json.loads(record.value)
                meta = payload["book"]
                books.append(
                    Book(
                        book_id=str(meta["book_id"]),
                        title=str(meta["title"]),
                        source_path=str(meta["source_path"]),
                        page_count=int(meta["page_count"]),
                        ingested_at=str(meta.get("ingested_at", "")),
                        topics=tuple(meta.get("topics", ())),
                    )
                )
            except Exception:
                continue

        return tuple(books)

    def search(
        self,
        query: str,
        *,
        limit: int = 8,
    ) -> tuple[KnowledgeMatch, ...]:
        """
        Rank chunks against a natural-language question.

        Cross-language fallback: Roman-Urdu questions cannot
        keyword-match Urdu-script text, so when ranking finds nothing
        but the library has content, a deterministic spread of sample
        chunks is returned instead — enough for "koi hadees sunao"
        style requests where any passage works.
        """

        tokens = _tokenize(query)

        if not tokens:
            return ()

        matches: list[KnowledgeMatch] = []
        total_chunks = 0

        for chunk in self._iter_chunks():
            total_chunks += 1
            score = _score_chunk(tokens, query, chunk.text)

            if score > 0:
                matches.append(
                    KnowledgeMatch(chunk=chunk, score=score)
                )

        if matches:
            matches.sort(
                key=lambda match: (-match.score, match.chunk.sequence)
            )
            return tuple(matches[:limit])

        if total_chunks == 0:
            return ()

        # Sample fallback: evenly-spread chunks across the library.
        sampled = self._sample_chunks(limit)
        logger.info(
            "Knowledge search had no keyword hits; returning %d "
            "sample chunks.",
            len(sampled),
        )

        return tuple(
            KnowledgeMatch(chunk=chunk, score=0.1) for chunk in sampled
        )

    def _sample_chunks(self, limit: int) -> list[BookChunk]:
        """Deterministic even spread across all stored chunks."""

        all_chunks = list(self._iter_chunks())

        if not all_chunks:
            return []

        if len(all_chunks) <= limit:
            return all_chunks

        step = len(all_chunks) / limit

        return [
            all_chunks[int(index * step)]
            for index in range(limit)
        ]

    def lookup_page(
        self,
        book_title: str,
        page: int,
    ) -> tuple[BookChunk, ...]:
        """
        Return every chunk of one page — exact "page 42 kya hai" lookups.
        """

        if page < 1:
            raise ValueError(
                "page numbers start at 1."
            )

        wanted = book_title.strip().lower()
        hits: list[BookChunk] = []

        for chunk in self._iter_chunks():
            title_matches = (
                not wanted
                or wanted in chunk.book_title.lower()
            )

            if title_matches and chunk.page == page:
                hits.append(chunk)

        hits.sort(key=lambda chunk: chunk.sequence)
        return tuple(hits)

    # ============================================================
    # Internals
    # ============================================================

    def _iter_chunks(self):
        """Yield BookChunk objects from every stored book."""

        import json

        for record in self._database.list(_NAMESPACE):
            try:
                payload = json.loads(record.value)
                meta = payload["book"]
            except Exception:
                continue

            book_id = str(meta.get("book_id", record.key))
            title = str(meta.get("title", ""))

            for entry in payload.get("chunks", []):
                try:
                    yield BookChunk(
                        chunk_id=str(entry["chunk_id"]),
                        book_id=book_id,
                        book_title=title,
                        page=int(entry["page"]),
                        sequence=int(entry["sequence"]),
                        text=str(entry["text"]),
                    )
                except (KeyError, TypeError, ValueError):
                    continue


def _split_page_text(text: str) -> list[str]:
    """Split long pages into ~chunk-sized pieces on paragraph edges."""

    if len(text) <= _CHUNK_TARGET_CHARS:
        return [text]

    pieces: list[str] = []
    current: list[str] = []
    current_length = 0

    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()

        if not paragraph:
            continue

        if current_length + len(paragraph) > _CHUNK_TARGET_CHARS and current:
            pieces.append("\n\n".join(current))
            current = []
            current_length = 0

        current.append(paragraph)
        current_length += len(paragraph)

    if current:
        pieces.append("\n\n".join(current))

    return pieces or [text]


def _score_chunk(
    query_tokens: list[str],
    raw_query: str,
    chunk_text: str,
) -> float:
    """
    Deterministic relevance score.

    Phrase hit > token overlap; longer chunks are slightly
    normalized so big pages don't dominate.
    """

    lowered = chunk_text.lower()

    score = 0.0

    if raw_query.strip().lower() in lowered:
        score += 5.0

    chunk_tokens = set(_tokenize(lowered))

    if not chunk_tokens:
        return 0.0

    hits = sum(1 for token in set(query_tokens) if token in chunk_tokens)
    score += hits * 1.0

    if hits == 0 and score == 0:
        return 0.0

    # Mild length normalization.
    return score / (1.0 + len(lowered) / 10_000)


def _tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokens (2+ chars)."""

    return _TOKENIZE.findall(text.lower())


def _chunk_id(book_id: str, sequence: int) -> str:
    """Deterministic chunk id."""

    digest = hashlib.md5(  # noqa: S324 - non-crypto dedupe key only
        f"{book_id}:{sequence}".encode("utf-8")
    ).hexdigest()[:10]

    return f"chk_{digest}"


__all__ = [
    "KnowledgeLibrary",
]

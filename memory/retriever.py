"""
AKI Memory Retriever.

Provides retrieval operations for AKI memories.

The retriever is intentionally independent from:
    - AI models
    - databases
    - vector databases
    - operating-system actions

The initial implementation uses simple keyword matching.
A semantic/vector retrieval backend can be introduced later
without changing the public retrieval interface.
"""

from __future__ import annotations

import re
from typing import Iterable

from .models import Memory, MemoryMatch


class MemoryRetriever:
    """
    Retrieves relevant memories from a collection of Memory objects.

    The current implementation uses normalized keyword matching.
    """

    def __init__(
        self,
        memories: Iterable[Memory] | None = None,
    ) -> None:
        self._memories: dict[str, Memory] = {}

        if memories is not None:
            self.replace(memories)

    # ============================================================
    # Replace Collection
    # ============================================================

    def replace(
        self,
        memories: Iterable[Memory],
    ) -> None:
        """
        Replace the current retrieval collection.
        """

        self._memories.clear()

        for memory in memories:
            self.add(memory)

    # ============================================================
    # Add
    # ============================================================

    def add(
        self,
        memory: Memory,
    ) -> None:
        """
        Add or replace a memory in the retrieval collection.
        """

        if not isinstance(memory, Memory):
            raise TypeError(
                "memory must be a Memory instance."
            )

        self._memories[memory.memory_id] = memory

    # ============================================================
    # Remove
    # ============================================================

    def remove(
        self,
        memory_id: str,
    ) -> bool:
        """
        Remove a memory from the retrieval collection.

        Returns:
            True if the memory existed.
            False otherwise.
        """

        normalized_id = self._normalize_id(memory_id)

        return (
            self._memories.pop(
                normalized_id,
                None,
            )
            is not None
        )

    # ============================================================
    # Search
    # ============================================================

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
        minimum_score: float = 0.0,
    ) -> tuple[MemoryMatch, ...]:
        """
        Search memories using keyword relevance.

        Args:
            query:
                Search text.

            limit:
                Maximum number of results.

            minimum_score:
                Minimum relevance score between 0.0 and 1.0.

        Returns:
            Memories ranked by relevance.
        """

        normalized_query = self._normalize_text(query)

        if not normalized_query:
            return ()

        if limit <= 0:
            return ()

        if not 0.0 <= minimum_score <= 1.0:
            raise ValueError(
                "minimum_score must be between 0.0 and 1.0."
            )

        query_tokens = self._tokenize(
            normalized_query
        )

        if not query_tokens:
            return ()

        matches: list[MemoryMatch] = []

        for memory in self._memories.values():
            score = self._calculate_score(
                memory,
                query_tokens,
            )

            if score < minimum_score:
                continue

            if score <= 0.0:
                continue

            matches.append(
                MemoryMatch(
                    memory=memory,
                    score=score,
                )
            )

        matches.sort(
            key=lambda match: (
                -match.score,
                -match.memory.metadata.importance,
                match.memory.created_at,
            )
        )

        return tuple(matches[:limit])

    # ============================================================
    # Best Match
    # ============================================================

    def best_match(
        self,
        query: str,
    ) -> MemoryMatch | None:
        """
        Return the single most relevant memory.
        """

        results = self.search(
            query,
            limit=1,
        )

        if not results:
            return None

        return results[0]

    # ============================================================
    # Count
    # ============================================================

    def count(self) -> int:
        """Return the number of indexed memories."""

        return len(self._memories)

    # ============================================================
    # Clear
    # ============================================================

    def clear(self) -> None:
        """Remove all memories from the retrieval index."""

        self._memories.clear()

    # ============================================================
    # Scoring
    # ============================================================

    @classmethod
    def _calculate_score(
        cls,
        memory: Memory,
        query_tokens: set[str],
    ) -> float:
        """
        Calculate a simple keyword relevance score.

        Score is based on how many unique query tokens occur
        in the memory content or tags.
        """

        content_tokens = cls._tokenize(
            memory.content
        )

        tag_tokens = {
            tag.lower()
            for tag in memory.metadata.tags
        }

        searchable_tokens = (
            content_tokens | tag_tokens
        )

        if not searchable_tokens:
            return 0.0

        matched_tokens = (
            query_tokens & searchable_tokens
        )

        if not matched_tokens:
            return 0.0

        score = (
            len(matched_tokens)
            / len(query_tokens)
        )

        return min(
            max(score, 0.0),
            1.0,
        )

    # ============================================================
    # Tokenization
    # ============================================================

    @staticmethod
    def _tokenize(
        text: str,
    ) -> set[str]:
        """
        Convert text into normalized keyword tokens.
        """

        return {
            token
            for token in re.findall(
                r"[a-zA-Z0-9_]+",
                text.lower(),
            )
            if len(token) > 1
        }

    # ============================================================
    # Text Normalization
    # ============================================================

    @staticmethod
    def _normalize_text(
        text: str,
    ) -> str:
        """Normalize search text."""

        if not isinstance(text, str):
            raise TypeError(
                "query must be a string."
            )

        return " ".join(
            text.strip().lower().split()
        )

    # ============================================================
    # ID Normalization
    # ============================================================

    @staticmethod
    def _normalize_id(
        memory_id: str,
    ) -> str:
        """Normalize a memory identifier."""

        if not isinstance(memory_id, str):
            raise TypeError(
                "memory_id must be a string."
            )

        normalized = memory_id.strip()

        if not normalized:
            raise ValueError(
                "memory_id cannot be empty."
            )

        return normalized


__all__ = [
    "MemoryRetriever",
]
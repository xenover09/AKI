"""
AKI Memory Search.

Provides deterministic search and ranking over persisted AKI memories.

This layer intentionally remains independent from AI embeddings.
Semantic/vector retrieval will be added later in the Intelligence layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re

from database.database_service import DatabaseService
from memory.memory_service import MemoryService
from memory.models import Memory


@dataclass(frozen=True)
class MemorySearchResult:
    """One ranked memory returned by a search."""

    memory: Memory
    score: float


class MemorySearchService:
    """
    Searches and ranks persisted AKI memories.

    Ranking factors:

        1. Exact memory-id match
        2. Exact phrase match
        3. Query-token matches
        4. Tag matches
        5. Memory importance
        6. Memory confidence
        7. Recency

    The algorithm is deterministic and explainable.
    """

    def __init__(
        self,
        database_service: DatabaseService,
    ) -> None:
        if not isinstance(
            database_service,
            DatabaseService,
        ):
            raise TypeError(
                "database_service must be a DatabaseService instance."
            )

        self._database = database_service
        self._memory_service = MemoryService(
            database_service,
        )

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        memory_type: str | None = None,
        tag: str | None = None,
    ) -> list[MemorySearchResult]:
        """
        Search and rank persisted memories.

        Args:
            query:
                Natural-language search query.

            limit:
                Maximum number of results.

            memory_type:
                Optional memory-type filter.

            tag:
                Optional tag filter.

        Returns:
            Ranked memory search results.
        """

        query = self._normalize_query(query)

        if not isinstance(limit, int):
            raise TypeError(
                "limit must be an integer."
            )

        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero."
            )

        normalized_type = self._normalize_optional(
            memory_type,
            "memory_type",
        )

        normalized_tag = self._normalize_optional(
            tag,
            "tag",
        )

        query_tokens = self._tokenize(query)

        records = self._database.list(
            MemoryService.NAMESPACE,
        )

        results: list[MemorySearchResult] = []

        for record in records:
            memory = self._memory_service._deserialize(
                record.value,
            )

            if not self._matches_filters(
                memory,
                normalized_type,
                normalized_tag,
            ):
                continue

            score = self._score(
                memory,
                query,
                query_tokens,
            )

            if score <= 0:
                continue

            results.append(
                MemorySearchResult(
                    memory=memory,
                    score=score,
                )
            )

        results.sort(
            key=self._ranking_key,
            reverse=True,
        )

        return results[:limit]

    @staticmethod
    def _normalize_query(
        query: str,
    ) -> str:
        """Normalize and validate a search query."""

        if not isinstance(query, str):
            raise TypeError(
                "query must be a string."
            )

        normalized = " ".join(
            query.strip().lower().split()
        )

        if not normalized:
            raise ValueError(
                "query cannot be empty."
            )

        return normalized

    @staticmethod
    def _normalize_optional(
        value: str | None,
        field_name: str,
    ) -> str | None:
        """Normalize an optional filter value."""

        if value is None:
            return None

        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} must be a string or None."
            )

        normalized = value.strip().lower()

        if not normalized:
            raise ValueError(
                f"{field_name} cannot be empty."
            )

        return normalized

    @staticmethod
    def _tokenize(
        text: str,
    ) -> set[str]:
        """
        Convert text into normalized search tokens.
        """

        return {
            token
            for token in re.findall(
                r"[a-z0-9_'-]+",
                text.lower(),
            )
            if token
        }

    @staticmethod
    def _matches_filters(
        memory: Memory,
        memory_type: str | None,
        tag: str | None,
    ) -> bool:
        """Return whether a memory satisfies optional filters."""

        if memory_type is not None:
            current_type = (
                memory.metadata.memory_type.value.lower()
            )

            if current_type != memory_type:
                return False

        if tag is not None:
            memory_tags = {
                current_tag.lower()
                for current_tag in memory.metadata.tags
            }

            if tag not in memory_tags:
                return False

        return True

    @classmethod
    def _score(
        cls,
        memory: Memory,
        query: str,
        query_tokens: set[str],
    ) -> float:
        """
        Calculate a deterministic relevance score.

        Importance, confidence and recency are only ranking
        bonuses. They cannot make an unrelated memory appear
        in search results.
        """

        relevance_score = 0.0

        memory_id = memory.memory_id.lower()
        content = memory.content.lower()

        tags = {
            current_tag.lower()
            for current_tag in memory.metadata.tags
        }

        # --------------------------------------------------------
        # 1. Exact memory ID match
        # --------------------------------------------------------

        if query == memory_id:
            relevance_score += 100.0

        # --------------------------------------------------------
        # 2. Partial memory ID match
        # --------------------------------------------------------

        elif query in memory_id:
            relevance_score += 50.0

        # --------------------------------------------------------
        # 3. Exact phrase match
        # --------------------------------------------------------

        if query in content:
            relevance_score += 40.0

        # --------------------------------------------------------
        # 4. Token matching
        # --------------------------------------------------------

        content_tokens = cls._tokenize(
            content,
        )

        matching_tokens = (
            query_tokens & content_tokens
        )

        if query_tokens:
            token_ratio = (
                len(matching_tokens)
                / len(query_tokens)
            )

            relevance_score += (
                30.0 * token_ratio
            )

        # --------------------------------------------------------
        # 5. Tag matching
        # --------------------------------------------------------

        for token in query_tokens:
            if token in tags:
                relevance_score += 20.0

        # --------------------------------------------------------
        # Critical relevance gate
        #
        # If the memory has no actual relationship with the
        # query, it must never be returned merely because it
        # has high importance, confidence or recency.
        # --------------------------------------------------------

        if relevance_score <= 0.0:
            return 0.0

        # --------------------------------------------------------
        # 6. Importance bonus
        # --------------------------------------------------------

        relevance_score += (
            memory.metadata.importance
            * 10.0
        )

        # --------------------------------------------------------
        # 7. Confidence bonus
        # --------------------------------------------------------

        relevance_score += (
            memory.metadata.confidence
            * 5.0
        )

        # --------------------------------------------------------
        # 8. Recency bonus
        # --------------------------------------------------------

        relevance_score += cls._recency_score(
            memory.updated_at,
        )

        return relevance_score

    @staticmethod
    def _recency_score(
        updated_at: datetime,
    ) -> float:
        """
        Give recently updated memories a small ranking bonus.

        Relevance remains more important than recency.
        """

        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(
                tzinfo=timezone.utc,
            )

        now = datetime.now(
            timezone.utc,
        )

        age_seconds = max(
            0.0,
            (
                now - updated_at
            ).total_seconds(),
        )

        age_days = (
            age_seconds / 86400.0
        )

        if age_days <= 1:
            return 5.0

        if age_days <= 7:
            return 3.0

        if age_days <= 30:
            return 1.5

        return 0.0

    @staticmethod
    def _ranking_key(
        result: MemorySearchResult,
    ) -> tuple[
        float,
        float,
        float,
        datetime,
    ]:
        """
        Produce the final deterministic sorting key.
        """

        metadata = result.memory.metadata

        return (
            result.score,
            metadata.importance,
            metadata.confidence,
            result.memory.updated_at,
        )


__all__ = [
    "MemorySearchResult",
    "MemorySearchService",
]
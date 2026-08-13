"""
AKI Memory Models.

Defines the data structures used by AKI's memory subsystem.

This module contains data representation only.
It does not perform storage, retrieval, AI inference,
or operating-system actions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ================================================================
# Memory Type
# ================================================================


class MemoryType(str, Enum):
    """
    Categories of information AKI can remember.
    """

    FACT = "fact"
    PREFERENCE = "preference"
    CONTEXT = "context"
    CONVERSATION = "conversation"
    TASK = "task"
    SYSTEM = "system"


# ================================================================
# Memory Source
# ================================================================


class MemorySource(str, Enum):
    """
    Sources from which a memory may originate.
    """

    USER = "user"
    AI = "ai"
    SYSTEM = "system"
    IMPORTED = "imported"


# ================================================================
# Memory Metadata
# ================================================================


@dataclass(frozen=True)
class MemoryMetadata:
    """
    Additional information describing a memory.
    """

    memory_type: MemoryType = MemoryType.FACT
    source: MemorySource = MemorySource.USER
    tags: tuple[str, ...] = ()
    importance: float = 0.5
    confidence: float = 1.0

    def __post_init__(self) -> None:
        """
        Validate metadata values.
        """

        if not 0.0 <= self.importance <= 1.0:
            raise ValueError(
                "importance must be between 0.0 and 1.0."
            )

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "confidence must be between 0.0 and 1.0."
            )

        normalized_tags = tuple(
            tag.strip().lower()
            for tag in self.tags
            if isinstance(tag, str) and tag.strip()
        )

        object.__setattr__(
            self,
            "tags",
            normalized_tags,
        )


# ================================================================
# Memory Model
# ================================================================


@dataclass(frozen=True)
class Memory:
    """
    Complete representation of an AKI memory.

    Attributes:
        memory_id:
            Unique identifier.

        content:
            Information being remembered.

        metadata:
            Classification and additional memory information.

        created_at:
            UTC timestamp when the memory was created.

        updated_at:
            UTC timestamp when the memory was last modified.

        extra:
            Extensible metadata that does not belong to the
            core memory model.
    """

    memory_id: str
    content: str
    metadata: MemoryMetadata = field(
        default_factory=MemoryMetadata
    )
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    extra: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        """
        Validate and normalize the memory.
        """

        if not isinstance(self.memory_id, str):
            raise TypeError(
                "memory_id must be a string."
            )

        if not self.memory_id.strip():
            raise ValueError(
                "memory_id cannot be empty."
            )

        if not isinstance(self.content, str):
            raise TypeError(
                "content must be a string."
            )

        if not self.content.strip():
            raise ValueError(
                "content cannot be empty."
            )

        if self.updated_at < self.created_at:
            raise ValueError(
                "updated_at cannot be earlier than created_at."
            )

        object.__setattr__(
            self,
            "memory_id",
            self.memory_id.strip(),
        )

        object.__setattr__(
            self,
            "content",
            self.content.strip(),
        )

        object.__setattr__(
            self,
            "extra",
            dict(self.extra),
        )


# ================================================================
# Memory Match
# ================================================================


@dataclass(frozen=True)
class MemoryMatch:
    """
    Represents a memory returned from a retrieval operation.

    The score is intentionally generic.

    Later retrieval implementations may use:
        - keyword similarity
        - semantic similarity
        - embeddings
        - ranking algorithms
    """

    memory: Memory
    score: float

    def __post_init__(self) -> None:
        """
        Validate the retrieval score.
        """

        if not 0.0 <= self.score <= 1.0:
            raise ValueError(
                "score must be between 0.0 and 1.0."
            )


# ================================================================
# Public API
# ================================================================


__all__ = [
    "Memory",
    "MemoryMatch",
    "MemoryMetadata",
    "MemorySource",
    "MemoryType",
]
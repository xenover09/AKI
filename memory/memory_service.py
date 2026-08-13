"""
AKI Memory Service.

Application-facing service layer for AKI memory.

MemoryService coordinates the MemoryManager and MemoryRetriever
without exposing their internal implementation details to the
rest of the application.

This module does not execute operating-system actions.
"""

from __future__ import annotations

from typing import Any

from .memory_manager import MemoryManager
from .models import Memory
from .retriever import MemoryRetriever


class MemoryService:
    """
    High-level application service for AKI memory.

    Responsibilities:

    - Store memories.
    - Recall memories.
    - Search memories.
    - Forget memories.
    - Check whether a memory exists.
    - Provide memory statistics.

    The service acts as the application-facing boundary of
    the memory subsystem.
    """

    def __init__(
        self,
        manager: MemoryManager | None = None,
        retriever: MemoryRetriever | None = None,
    ) -> None:
        self._manager = manager or MemoryManager()

        self._retriever = (
            retriever
            or MemoryRetriever()
        )

        self._sync_retriever()

    # ============================================================
    # Remember
    # ============================================================

    def remember(
        self,
        key: str,
        memory: Memory,
    ) -> Memory:
        """
        Store a Memory object under a memory key.

        Args:
            key:
                Application-level memory key.

            memory:
                Memory object to store.

        Returns:
            The stored Memory object.
        """

        if not isinstance(memory, Memory):
            raise TypeError(
                "memory must be a Memory instance."
            )

        self._manager.remember(
            key,
            memory,
        )

        self._sync_retriever()

        return memory

    # ============================================================
    # Recall
    # ============================================================

    def recall(
        self,
        key: str,
    ) -> Any | None:
        """
        Retrieve the value associated with a memory key.
        """

        return self._manager.recall(key)

    # ============================================================
    # Recall Memory
    # ============================================================

    def recall_memory(
        self,
        key: str,
    ) -> Memory | None:
        """
        Retrieve a Memory object by its application key.

        Returns:
            Memory object if the stored value is a Memory,
            otherwise None.
        """

        value = self._manager.recall(key)

        if isinstance(value, Memory):
            return value

        return None

    # ============================================================
    # Search
    # ============================================================

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
        minimum_score: float = 0.0,
    ):
        """
        Search AKI's memories.

        The exact search result type is delegated to
        MemoryRetriever.
        """

        self._sync_retriever()

        return self._retriever.search(
            query,
            limit=limit,
            minimum_score=minimum_score,
        )

    # ============================================================
    # Best Match
    # ============================================================

    def best_match(
        self,
        query: str,
    ):
        """
        Return the strongest matching memory.
        """

        self._sync_retriever()

        return self._retriever.best_match(
            query
        )

    # ============================================================
    # Forget
    # ============================================================

    def forget(
        self,
        key: str,
    ) -> bool:
        """
        Remove a memory by application key.
        """

        removed = self._manager.forget(key)

        if removed:
            self._sync_retriever()

        return removed

    # ============================================================
    # Knows
    # ============================================================

    def knows(
        self,
        key: str,
    ) -> bool:
        """
        Check whether AKI knows a specific memory key.
        """

        return self._manager.knows(key)

    # ============================================================
    # All Memories
    # ============================================================

    def memories(self) -> tuple[Memory, ...]:
        """
        Return all stored Memory objects.

        Non-Memory values are ignored.
        """

        records = self._manager.memories()

        memories: list[Memory] = []

        for record in records:
            if isinstance(record.value, Memory):
                memories.append(record.value)

        return tuple(memories)

    # ============================================================
    # Count
    # ============================================================

    def count(self) -> int:
        """
        Return the number of stored memory records.
        """

        return self._manager.count()

    # ============================================================
    # Clear
    # ============================================================

    def clear(self) -> None:
        """
        Remove all memories.
        """

        self._manager.clear()
        self._retriever.clear()

    # ============================================================
    # Synchronization
    # ============================================================

    def _sync_retriever(self) -> None:
        """
        Synchronize the retriever with the MemoryManager.

        Only values that are actual Memory objects are exposed
        to the retrieval layer.
        """

        memories: list[Memory] = []

        for record in self._manager.memories():
            if isinstance(record.value, Memory):
                memories.append(record.value)

        self._retriever.replace(memories)


__all__ = [
    "MemoryService",
]
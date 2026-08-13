"""
AKI Memory Manager

High-level interface for AKI's memory system.

MemoryManager decides how AKI interacts with stored memories,
while MemoryStore remains responsible for the underlying storage.

This layer does not execute operating-system actions.
"""

from __future__ import annotations

from typing import Any

from .memory_store import MemoryRecord, MemoryStore


class MemoryManager:
    """
    High-level manager for AKI memory.

    Responsibilities:

    - Remember information.
    - Retrieve remembered information.
    - Forget information.
    - Check whether information exists.
    - Expose basic memory statistics.

    Storage implementation is delegated to MemoryStore.
    """

    def __init__(
        self,
        store: MemoryStore | None = None,
    ) -> None:
        self._store = store or MemoryStore()

    # ---------------------------------------------------------
    # Remember
    # ---------------------------------------------------------

    def remember(
        self,
        key: str,
        value: Any,
    ) -> MemoryRecord:
        """
        Store information in AKI's memory.

        Existing keys are updated.
        """

        return self._store.save(
            key=key,
            value=value,
        )

    # ---------------------------------------------------------
    # Recall
    # ---------------------------------------------------------

    def recall(
        self,
        key: str,
    ) -> Any | None:
        """
        Retrieve the value associated with a memory key.

        Returns:
            Stored value, or None if the memory does not exist.
        """

        record = self._store.get(key)

        if record is None:
            return None

        return record.value

    def recall_record(
        self,
        key: str,
    ) -> MemoryRecord | None:
        """
        Retrieve the complete memory record.
        """

        return self._store.get(key)

    # ---------------------------------------------------------
    # Forget
    # ---------------------------------------------------------

    def forget(
        self,
        key: str,
    ) -> bool:
        """
        Remove a memory.

        Returns:
            True if the memory existed and was removed.
        """

        return self._store.delete(key)

    # ---------------------------------------------------------
    # Existence
    # ---------------------------------------------------------

    def knows(
        self,
        key: str,
    ) -> bool:
        """
        Check whether AKI remembers a specific key.
        """

        return self._store.exists(key)

    # ---------------------------------------------------------
    # List Memories
    # ---------------------------------------------------------

    def memories(self) -> tuple[MemoryRecord, ...]:
        """
        Return all stored memories.
        """

        return self._store.all()

    # ---------------------------------------------------------
    # Statistics
    # ---------------------------------------------------------

    def count(self) -> int:
        """
        Return the number of stored memories.
        """

        return self._store.count()

    # ---------------------------------------------------------
    # Clear
    # ---------------------------------------------------------

    def clear(self) -> None:
        """
        Remove all memories.
        """

        self._store.clear()


__all__ = [
    "MemoryManager",
]
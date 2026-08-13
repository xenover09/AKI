"""
AKI Memory Repository.

Defines the storage contract used by AKI's memory subsystem.

The repository layer separates memory management from the actual
storage technology.

Future implementations may use:
    - in-memory storage
    - SQLite
    - PostgreSQL
    - another persistent backend

The rest of AKI should depend on this interface rather than on a
specific database implementation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from .models import Memory


class MemoryRepository(ABC):
    """
    Abstract repository contract for AKI memories.

    This class defines what a memory storage backend must provide.
    It does not define how the data is physically stored.
    """

    # ============================================================
    # Save
    # ============================================================

    @abstractmethod
    def save(
        self,
        memory: Memory,
    ) -> Memory:
        """
        Create or update a memory.

        Returns:
            The stored memory.
        """

        raise NotImplementedError

    # ============================================================
    # Get
    # ============================================================

    @abstractmethod
    def get(
        self,
        memory_id: str,
    ) -> Memory | None:
        """
        Retrieve a memory by its unique identifier.
        """

        raise NotImplementedError

    # ============================================================
    # Get All
    # ============================================================

    @abstractmethod
    def all(self) -> tuple[Memory, ...]:
        """
        Return all stored memories.
        """

        raise NotImplementedError

    # ============================================================
    # Delete
    # ============================================================

    @abstractmethod
    def delete(
        self,
        memory_id: str,
    ) -> bool:
        """
        Delete a memory by its identifier.

        Returns:
            True if the memory was deleted.
            False if it did not exist.
        """

        raise NotImplementedError

    # ============================================================
    # Exists
    # ============================================================

    @abstractmethod
    def exists(
        self,
        memory_id: str,
    ) -> bool:
        """
        Check whether a memory exists.
        """

        raise NotImplementedError

    # ============================================================
    # Count
    # ============================================================

    @abstractmethod
    def count(self) -> int:
        """
        Return the number of stored memories.
        """

        raise NotImplementedError

    # ============================================================
    # Clear
    # ============================================================

    @abstractmethod
    def clear(self) -> None:
        """
        Remove all stored memories.
        """

        raise NotImplementedError

    # ============================================================
    # Bulk Save
    # ============================================================

    def save_many(
        self,
        memories: Iterable[Memory],
    ) -> tuple[Memory, ...]:
        """
        Store multiple memories.

        The default implementation uses the repository's
        single-memory save() operation.

        Concrete repositories may override this with a more
        efficient transactional implementation.
        """

        stored: list[Memory] = []

        for memory in memories:
            stored.append(
                self.save(memory)
            )

        return tuple(stored)


__all__ = [
    "MemoryRepository",
]
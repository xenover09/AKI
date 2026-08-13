"""
AKI Memory Store

Provides the basic storage interface for AKI's memory system.

This module is responsible only for storing and retrieving memory
records. It does not make AI decisions and does not execute
operating-system actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class MemoryRecord:
    """
    Represents one piece of AKI memory.
    """

    memory_id: str
    key: str
    value: Any
    created_at: datetime
    updated_at: datetime


class MemoryStore:
    """
    Thread-safe in-memory storage for AKI.

    This is intentionally an abstraction.

    Later we can replace the internal storage with SQLite or another
    persistent database without changing the components that use
    MemoryStore.
    """

    def __init__(self) -> None:
        self._records: dict[str, MemoryRecord] = {}
        self._lock = RLock()

    # ---------------------------------------------------------
    # Create / Update
    # ---------------------------------------------------------

    def save(
        self,
        key: str,
        value: Any,
    ) -> MemoryRecord:
        """
        Create or update a memory record.

        If the key already exists, its value and updated timestamp
        are replaced.
        """

        normalized_key = self._normalize_key(key)
        now = datetime.now(timezone.utc)

        with self._lock:
            existing = self._records.get(normalized_key)

            if existing is None:
                record = MemoryRecord(
                    memory_id=str(uuid4()),
                    key=normalized_key,
                    value=value,
                    created_at=now,
                    updated_at=now,
                )
            else:
                record = MemoryRecord(
                    memory_id=existing.memory_id,
                    key=existing.key,
                    value=value,
                    created_at=existing.created_at,
                    updated_at=now,
                )

            self._records[normalized_key] = record

            return record

    # ---------------------------------------------------------
    # Read
    # ---------------------------------------------------------

    def get(
        self,
        key: str,
    ) -> MemoryRecord | None:
        """
        Retrieve a memory record by key.
        """

        normalized_key = self._normalize_key(key)

        with self._lock:
            return self._records.get(normalized_key)

    def exists(
        self,
        key: str,
    ) -> bool:
        """
        Check whether a memory key exists.
        """

        normalized_key = self._normalize_key(key)

        with self._lock:
            return normalized_key in self._records

    def all(self) -> tuple[MemoryRecord, ...]:
        """
        Return all stored memory records.
        """

        with self._lock:
            return tuple(self._records.values())

    # ---------------------------------------------------------
    # Delete
    # ---------------------------------------------------------

    def delete(
        self,
        key: str,
    ) -> bool:
        """
        Delete a memory record.

        Returns:
            True if a record was deleted.
            False if the key did not exist.
        """

        normalized_key = self._normalize_key(key)

        with self._lock:
            if normalized_key not in self._records:
                return False

            del self._records[normalized_key]

            return True

    # ---------------------------------------------------------
    # Clear
    # ---------------------------------------------------------

    def clear(self) -> None:
        """
        Remove all memory records.
        """

        with self._lock:
            self._records.clear()

    # ---------------------------------------------------------
    # Statistics
    # ---------------------------------------------------------

    def count(self) -> int:
        """
        Return the number of stored memory records.
        """

        with self._lock:
            return len(self._records)

    # ---------------------------------------------------------
    # Validation
    # ---------------------------------------------------------

    @staticmethod
    def _normalize_key(key: str) -> str:
        """
        Normalize and validate a memory key.
        """

        if not isinstance(key, str):
            raise TypeError("Memory key must be a string.")

        normalized = key.strip().lower()

        if not normalized:
            raise ValueError("Memory key cannot be empty.")

        return normalized


__all__ = [
    "MemoryRecord",
    "MemoryStore",
]
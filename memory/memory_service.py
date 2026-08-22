"""
AKI Memory Service.

Provides the application-level API for creating, retrieving,
checking, and deleting persistent AKI memories.

The service owns memory behavior.
Persistent storage is delegated to DatabaseService.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from database.database_service import DatabaseService
from memory.models import (
    Memory,
    MemoryMetadata,
    MemorySource,
    MemoryType,
)


class MemoryService:
    """
    Application service for AKI's memory subsystem.

    Responsibilities:
        - Validate Memory objects.
        - Persist memories through DatabaseService.
        - Restore Memory objects from persistent storage.
        - Check whether a memory exists.
        - Delete memories.
        - Keep storage details out of the rest of AKI.

    The database service is optional during construction so the
    existing AKI boot process remains compatible while the memory
    subsystem is being wired into persistent storage.
    """

    NAMESPACE = "memory"

    def __init__(
        self,
        database_service: DatabaseService | None = None,
    ) -> None:
        if database_service is not None and not isinstance(
            database_service,
            DatabaseService,
        ):
            raise TypeError(
                "database_service must be a DatabaseService instance "
                "or None."
            )

        self._database = database_service

    # ============================================================
    # Database Binding
    # ============================================================

    def bind_database(
        self,
        database_service: DatabaseService,
    ) -> None:
        """
        Attach the persistent database service.

        This is intentionally explicit so AKI's boot layer can
        initialize the database first and then connect memory to it.
        """

        if not isinstance(database_service, DatabaseService):
            raise TypeError(
                "database_service must be a DatabaseService instance."
            )

        self._database = database_service

    @property
    def is_persistent(self) -> bool:
        """Return whether persistent storage is currently available."""

        return self._database is not None

    # ============================================================
    # Public Memory API
    # ============================================================

    def remember(
        self,
        memory: Memory,
    ) -> Memory:
        """
        Persist a Memory object.

        Args:
            memory:
                Complete Memory instance to persist.

        Returns:
            The persisted Memory instance.
        """

        if not isinstance(memory, Memory):
            raise TypeError(
                "memory must be a Memory instance."
            )

        self._require_database()

        serialized = self._serialize(memory)

        self._database.save(
            self.NAMESPACE,
            memory.memory_id,
            serialized,
        )

        return memory

    def recall(
        self,
        memory_id: str,
    ) -> Memory | None:
        """
        Retrieve one memory by ID.

        Args:
            memory_id:
                Unique memory identifier.

        Returns:
            Memory instance if found, otherwise None.
        """

        memory_id = self._normalize_memory_id(memory_id)

        self._require_database()

        record = self._database.get(
            self.NAMESPACE,
            memory_id,
        )

        if record is None:
            return None

        return self._deserialize(record.value)

    def knows(
        self,
        memory_id: str,
    ) -> bool:
        """
        Check whether AKI knows a memory by its ID.
        """

        memory_id = self._normalize_memory_id(memory_id)

        self._require_database()

        return (
            self._database.get(
                self.NAMESPACE,
                memory_id,
            )
            is not None
        )

    def forget(
        self,
        memory_id: str,
    ) -> bool:
        """
        Delete one memory.

        Returns:
            True if a memory was deleted, otherwise False.
        """

        memory_id = self._normalize_memory_id(memory_id)

        self._require_database()

        return self._database.delete(
            self.NAMESPACE,
            memory_id,
        )

    def count(self) -> int:
        """
        Return the number of persisted memories.
        """

        self._require_database()

        return self._database.count(
            self.NAMESPACE,
        )

    def clear(self) -> int:
        """
        Delete all memories.

        Returns:
            Number of memories that existed before deletion.
        """

        self._require_database()

        total = self.count()

        self._database.clear(
            self.NAMESPACE,
        )

        return total

    # ============================================================
    # Serialization
    # ============================================================

    @staticmethod
    def _serialize(
        memory: Memory,
    ) -> str:
        """
        Convert a Memory object into JSON.

        JSON is used instead of Python pickle so the database remains
        inspectable, portable, and independent of Python internals.
        """

        payload: dict[str, Any] = {
            "memory_id": memory.memory_id,
            "content": memory.content,
            "metadata": {
                "memory_type": memory.metadata.memory_type.value,
                "source": memory.metadata.source.value,
                "tags": list(memory.metadata.tags),
                "importance": memory.metadata.importance,
                "confidence": memory.metadata.confidence,
            },
            "created_at": memory.created_at.isoformat(),
            "updated_at": memory.updated_at.isoformat(),
            "extra": memory.extra,
        }

        return json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    @staticmethod
    def _deserialize(
        value: str,
    ) -> Memory:
        """
        Convert stored JSON back into a Memory object.
        """

        try:
            payload = json.loads(value)
        except json.JSONDecodeError as error:
            raise ValueError(
                "Stored memory contains invalid JSON."
            ) from error

        if not isinstance(payload, dict):
            raise ValueError(
                "Stored memory payload must be a JSON object."
            )

        metadata_payload = payload.get(
            "metadata",
            {},
        )

        if not isinstance(metadata_payload, dict):
            raise ValueError(
                "Stored memory metadata must be a JSON object."
            )

        memory_type = MemoryType(
            metadata_payload.get(
                "memory_type",
                MemoryType.FACT.value,
            )
        )

        source = MemorySource(
            metadata_payload.get(
                "source",
                MemorySource.USER.value,
            )
        )

        tags_payload = metadata_payload.get(
            "tags",
            [],
        )

        if not isinstance(tags_payload, list):
            raise ValueError(
                "Stored memory tags must be a list."
            )

        metadata = MemoryMetadata(
            memory_type=memory_type,
            source=source,
            tags=tuple(
                str(tag)
                for tag in tags_payload
            ),
            importance=float(
                metadata_payload.get(
                    "importance",
                    0.5,
                )
            ),
            confidence=float(
                metadata_payload.get(
                    "confidence",
                    1.0,
                )
            ),
        )

        created_at = MemoryService._parse_datetime(
            payload["created_at"]
        )

        updated_at = MemoryService._parse_datetime(
            payload["updated_at"]
        )

        extra = payload.get(
            "extra",
            {},
        )

        if not isinstance(extra, dict):
            raise ValueError(
                "Stored memory extra data must be a JSON object."
            )

        return Memory(
            memory_id=str(
                payload["memory_id"]
            ),
            content=str(
                payload["content"]
            ),
            metadata=metadata,
            created_at=created_at,
            updated_at=updated_at,
            extra=dict(extra),
        )

    # ============================================================
    # Validation / Helpers
    # ============================================================

    def _require_database(self) -> DatabaseService:
        """
        Return the configured database or fail explicitly.
        """

        if self._database is None:
            raise RuntimeError(
                "Memory persistence is not configured. "
                "Bind a DatabaseService before using the "
                "persistent memory API."
            )

        return self._database

    @staticmethod
    def _normalize_memory_id(
        memory_id: str,
    ) -> str:
        """
        Normalize and validate a memory ID.
        """

        if not isinstance(memory_id, str):
            raise TypeError(
                "memory_id must be a string."
            )

        memory_id = memory_id.strip()

        if not memory_id:
            raise ValueError(
                "memory_id cannot be empty."
            )

        return memory_id

    @staticmethod
    def _parse_datetime(
        value: str,
    ) -> datetime:
        """
        Parse an ISO-8601 datetime.

        Naive timestamps are interpreted as UTC.
        """

        if not isinstance(value, str):
            raise ValueError(
                "Stored datetime must be a string."
            )

        parsed = datetime.fromisoformat(
            value,
        )

        if parsed.tzinfo is None:
            parsed = parsed.replace(
                tzinfo=timezone.utc,
            )

        return parsed


__all__ = [
    "MemoryService",
]
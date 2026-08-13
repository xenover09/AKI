"""
AKI Memory Serializer.

Converts AKI Memory objects to and from JSON-compatible dictionaries.

This module does not perform storage, retrieval, AI inference,
or operating-system actions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import (
    Memory,
    MemoryMetadata,
    MemorySource,
    MemoryType,
)


class MemorySerializer:
    """
    Serialize and deserialize AKI memory objects.
    """

    # ============================================================
    # Serialize
    # ============================================================

    @staticmethod
    def serialize(
        memory: Memory,
    ) -> dict[str, Any]:
        """
        Convert a Memory object into a JSON-compatible dictionary.
        """

        if not isinstance(memory, Memory):
            raise TypeError(
                "memory must be a Memory instance."
            )

        return {
            "memory_id": memory.memory_id,
            "content": memory.content,
            "metadata": {
                "memory_type": (
                    memory.metadata.memory_type.value
                ),
                "source": (
                    memory.metadata.source.value
                ),
                "tags": list(
                    memory.metadata.tags
                ),
                "importance": (
                    memory.metadata.importance
                ),
                "confidence": (
                    memory.metadata.confidence
                ),
            },
            "created_at": (
                memory.created_at.isoformat()
            ),
            "updated_at": (
                memory.updated_at.isoformat()
            ),
            "extra": dict(memory.extra),
        }

    # ============================================================
    # Deserialize
    # ============================================================

    @staticmethod
    def deserialize(
        data: dict[str, Any],
    ) -> Memory:
        """
        Reconstruct a Memory object from serialized data.
        """

        if not isinstance(data, dict):
            raise TypeError(
                "data must be a dictionary."
            )

        try:
            metadata_data = data["metadata"]

            metadata = MemoryMetadata(
                memory_type=MemoryType(
                    metadata_data["memory_type"]
                ),
                source=MemorySource(
                    metadata_data["source"]
                ),
                tags=tuple(
                    metadata_data.get(
                        "tags",
                        (),
                    )
                ),
                importance=float(
                    metadata_data.get(
                        "importance",
                        0.5,
                    )
                ),
                confidence=float(
                    metadata_data.get(
                        "confidence",
                        1.0,
                    )
                ),
            )

            return Memory(
                memory_id=str(
                    data["memory_id"]
                ),
                content=str(
                    data["content"]
                ),
                metadata=metadata,
                created_at=(
                    datetime.fromisoformat(
                        data["created_at"]
                    )
                ),
                updated_at=(
                    datetime.fromisoformat(
                        data["updated_at"]
                    )
                ),
                extra=dict(
                    data.get(
                        "extra",
                        {},
                    )
                ),
            )

        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(
                "Invalid serialized memory data."
            ) from error

    # ============================================================
    # Serialize Many
    # ============================================================

    @classmethod
    def serialize_many(
        cls,
        memories: tuple[Memory, ...],
    ) -> list[dict[str, Any]]:
        """
        Serialize multiple memories.
        """

        return [
            cls.serialize(memory)
            for memory in memories
        ]

    # ============================================================
    # Deserialize Many
    # ============================================================

    @classmethod
    def deserialize_many(
        cls,
        data: list[dict[str, Any]],
    ) -> tuple[Memory, ...]:
        """
        Deserialize multiple memory dictionaries.
        """

        if not isinstance(data, list):
            raise TypeError(
                "data must be a list."
            )

        return tuple(
            cls.deserialize(item)
            for item in data
        )


__all__ = [
    "MemorySerializer",
]
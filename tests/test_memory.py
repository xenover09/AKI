"""Unit tests for AKI's memory subsystem."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from database.database_service import DatabaseService
from memory.memory_service import MemoryService
from memory.models import Memory, MemoryMetadata, MemorySource, MemoryType


def make_memory(memory_id: str = "mem_1") -> Memory:
    """Build a fully-populated Memory for round-trip tests."""

    created = datetime(2026, 1, 15, 10, 30, tzinfo=timezone.utc)

    return Memory(
        memory_id=memory_id,
        content="User prefers dark mode",
        metadata=MemoryMetadata(
            memory_type=MemoryType.PREFERENCE,
            source=MemorySource.USER,
            tags=("ui", "theme"),
            importance=0.8,
            confidence=0.9,
        ),
        created_at=created,
        updated_at=created,
        extra={"origin": "settings-dialog"},
    )


class TestPersistenceRoundTrip:
    """remember / recall integrity."""

    def test_remember_then_recall_preserves_everything(
        self, memory_service: MemoryService
    ) -> None:
        original = make_memory()

        memory_service.remember(original)
        restored = memory_service.recall("mem_1")

        assert restored == original
        assert restored is not None
        assert restored.metadata.memory_type is MemoryType.PREFERENCE
        assert restored.metadata.tags == ("ui", "theme")
        assert restored.extra == {"origin": "settings-dialog"}

    def test_recall_unknown_id_returns_none(
        self, memory_service: MemoryService
    ) -> None:
        assert memory_service.recall("never-stored") is None

    def test_remember_same_id_overwrites(
        self, memory_service: MemoryService
    ) -> None:
        memory_service.remember(make_memory("dup"))
        memory_service.remember(make_memory("dup"))

        assert memory_service.count() == 1
        assert memory_service.recall("dup") is not None

    def test_memories_survive_service_restart(
        self, database_service: DatabaseService, tmp_path
    ) -> None:
        first = MemoryService(database_service)
        first.remember(make_memory("persistent"))

        second = MemoryService(database_service)

        assert second.knows("persistent") is True


class TestMemoryQueries:
    """knows / forget / count / clear."""

    def test_knows_reflects_storage(
        self, memory_service: MemoryService
    ) -> None:
        memory_service.remember(make_memory("known"))

        assert memory_service.knows("known") is True
        assert memory_service.knows("unknown") is False

    def test_forget_removes_and_reports(
        self, memory_service: MemoryService
    ) -> None:
        memory_service.remember(make_memory("doomed"))

        assert memory_service.forget("doomed") is True
        assert memory_service.forget("doomed") is False
        assert memory_service.knows("doomed") is False

    def test_clear_returns_previous_count(
        self, memory_service: MemoryService
    ) -> None:
        for index in range(3):
            memory_service.remember(make_memory(f"m{index}"))

        assert memory_service.clear() == 3
        assert memory_service.count() == 0


class TestValidation:
    """Explicit failure contracts."""

    def test_unbound_service_raises_runtime_error(self) -> None:
        service = MemoryService(database_service=None)

        with pytest.raises(RuntimeError):
            service.remember(make_memory())

    def test_remember_rejects_non_memory(
        self, memory_service: MemoryService
    ) -> None:
        with pytest.raises(TypeError):
            memory_service.remember("not a memory")  # type: ignore[arg-type]

    def test_empty_memory_id_is_rejected(
        self, memory_service: MemoryService
    ) -> None:
        with pytest.raises(ValueError):
            memory_service.recall("   ")

    def test_non_string_memory_id_is_rejected(
        self, memory_service: MemoryService
    ) -> None:
        with pytest.raises(TypeError):
            memory_service.knows(123)  # type: ignore[arg-type]

    def test_bind_database_rejects_wrong_type(
        self, memory_service: MemoryService
    ) -> None:
        with pytest.raises(TypeError):
            memory_service.bind_database("db")  # type: ignore[arg-type]

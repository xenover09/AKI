"""Unit tests for AKI's database subsystem."""

from __future__ import annotations

from pathlib import Path

import pytest

from database.database_service import DatabaseService


class TestDatabaseLifecycle:
    """Connection and schema lifecycle behavior."""

    def test_initialize_creates_database_file(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "fresh.db"

        service = DatabaseService(path)
        service.initialize()

        assert path.exists()

        service.close()

    def test_is_connected_after_construction(self, tmp_path: Path) -> None:
        # The repository eagerly prepares the schema, so a freshly
        # constructed service already owns an open connection.
        service = DatabaseService(tmp_path / "state.db")

        assert service.is_connected is True

        service.close()
        assert service.is_connected is False

    def test_database_path_property(self, tmp_path: Path) -> None:
        path = tmp_path / "path.db"
        service = DatabaseService(path)

        assert service.database_path == path


class TestRecordCrud:
    """Save / get / update round-trips."""

    def test_save_then_get_roundtrip(
        self, database_service: DatabaseService
    ) -> None:
        record = database_service.save("test", "greeting", "hello")

        fetched = database_service.get("test", "greeting")

        assert fetched is not None
        assert fetched.record_id == record.record_id
        assert fetched.value == "hello"

    def test_save_overwrites_existing_value(
        self, database_service: DatabaseService
    ) -> None:
        database_service.save("test", "key", "first")
        updated = database_service.save("test", "key", "second")

        fetched = database_service.get("test", "key")
        count = database_service.count("test")

        assert fetched.value == "second"
        assert count == 1

    def test_get_missing_record_returns_none(
        self, database_service: DatabaseService
    ) -> None:
        assert database_service.get("nope", "missing") is None

    def test_namespaces_are_isolated(
        self, database_service: DatabaseService
    ) -> None:
        database_service.save("alpha", "shared-key", "a")
        database_service.save("beta", "shared-key", "b")

        alpha = database_service.get("alpha", "shared-key")
        beta = database_service.get("beta", "shared-key")

        assert alpha.value == "a"
        assert beta.value == "b"


class TestRecordQueries:
    """Existence checks, listing, counting."""

    def test_exists_true_and_false(
        self, database_service: DatabaseService
    ) -> None:
        database_service.save("test", "known", "v")

        assert database_service.exists("test", "known") is True
        assert database_service.exists("test", "unknown") is False

    def test_list_filters_by_namespace(
        self, database_service: DatabaseService
    ) -> None:
        database_service.save("keep", "k1", "1")
        database_service.save("keep", "k2", "2")
        database_service.save("other", "k3", "3")

        keep = database_service.list("keep")
        everything = database_service.list()

        assert {r.key for r in keep} == {"k1", "k2"}
        assert len(everything) == 3


class TestRecordDeletion:
    """Delete and clear semantics."""

    def test_delete_returns_true_only_when_present(
        self, database_service: DatabaseService
    ) -> None:
        database_service.save("test", "gone", "v")

        assert database_service.delete("test", "gone") is True
        assert database_service.delete("test", "gone") is False

    def test_clear_scopes_to_namespace(
        self, database_service: DatabaseService
    ) -> None:
        # Clear is a void bulk operation; count-before-delete
        # semantics live in MemoryService, not here.
        database_service.save("wipe", "a", "1")
        database_service.save("wipe", "b", "2")
        database_service.save("survivor", "c", "3")

        removed = database_service.clear("wipe")

        assert removed is None
        assert database_service.count("wipe") == 0
        assert database_service.count("survivor") == 1

    def test_clear_without_namespace_removes_everything(
        self, database_service: DatabaseService
    ) -> None:
        database_service.save("one", "a", "1")
        database_service.save("two", "b", "2")

        database_service.clear()

        assert database_service.count() == 0


class TestValidation:
    """Constructor argument validation."""

    def test_rejects_non_path_argument(self) -> None:
        with pytest.raises(TypeError):
            DatabaseService("not-a-path")  # type: ignore[arg-type]

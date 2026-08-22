"""Unit tests for AKI's boot workspace layout."""

from __future__ import annotations

from pathlib import Path

from aki_core.boot import WorkspaceLayout


class TestWorkspaceLayout:
    """Path resolution and directory creation."""

    def test_resolve_computes_expected_subdirectories(
        self, tmp_path: Path
    ) -> None:
        layout = WorkspaceLayout.resolve(tmp_path)

        assert layout.workspace_dir == tmp_path / "workspace"
        assert layout.data_dir == tmp_path / "workspace" / "data"
        assert layout.cache_dir == tmp_path / "workspace" / "cache"
        assert (
            layout.database_dir == tmp_path / "workspace" / "database"
        )
        assert layout.memory_dir == tmp_path / "workspace" / "memory"

    def test_ensure_directories_creates_everything(
        self, tmp_path: Path
    ) -> None:
        layout = WorkspaceLayout.resolve(
            tmp_path / "nested" / "root"
        )

        layout.ensure_directories()

        for directory in (
            layout.workspace_dir,
            layout.data_dir,
            layout.cache_dir,
            layout.database_dir,
            layout.memory_dir,
        ):
            assert directory.is_dir()

    def test_ensure_directories_is_idempotent(
        self, tmp_path: Path
    ) -> None:
        layout = WorkspaceLayout.resolve(tmp_path)

        layout.ensure_directories()
        layout.ensure_directories()

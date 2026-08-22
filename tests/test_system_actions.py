"""Unit tests for AKI's built-in action system stack."""

from __future__ import annotations

import pytest

from aki_core.command_executor import ExecutionStatus
from aki_core.system_actions import build_action_system, resolve_application


@pytest.fixture(scope="module")
def actions():
    """Build one action system shared by the module's tests."""

    return build_action_system()


class TestStackAssembly:
    """The factory wires a complete, permission-checked stack."""

    def test_all_builtin_actions_registered(self, actions) -> None:
        names = {a.name for a in actions.registry.list_actions()}

        assert {
            "open_application",
            "open_website",
            "take_screenshot",
            "get_system_info",
            "search_files",
            "system_cleanup",
            "start_recording",
        } <= names

    def test_disabled_actions_report_disabled(self, actions) -> None:
        result = actions.run("system_cleanup")

        assert result.status is ExecutionStatus.DISABLED

    def test_unknown_action_not_found(self, actions) -> None:
        result = actions.run("format_hard_drive")

        assert result.status is ExecutionStatus.NOT_FOUND


class TestOpenWebsiteHandler:
    """Browser opening is monkeypatched for hermetic testing."""

    def test_known_site_opens(
        self, actions, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        opened = {}
        monkeypatch.setattr(
            "webbrowser.open",
            lambda url: opened.setdefault("url", url),
        )

        result = actions.run("open_website", site="youtube")

        assert result.status is ExecutionStatus.SUCCESS
        assert opened["url"] == "https://www.youtube.com"

    def test_unknown_site_fails_gracefully(self, actions) -> None:
        result = actions.run("open_website", site="not-a-site")

        assert result.status is ExecutionStatus.FAILED


class TestGetSystemInfoHandler:
    """Read-only telemetry executes without side effects."""

    def test_returns_live_snapshot(self, actions) -> None:
        result = actions.run("get_system_info")

        assert result.status is ExecutionStatus.SUCCESS
        assert 0 <= result.data["cpu_percent"] <= 100
        assert result.data["ram_total_gb"] > 0

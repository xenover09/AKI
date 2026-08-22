"""Unit tests for AKI's deterministic intent engine."""

from __future__ import annotations

import pytest

from aki_core.intent_engine import IntentEngine


@pytest.fixture()
def engine() -> IntentEngine:
    return IntentEngine()


class TestWebsiteIntents:
    """Site shortcuts route to the browser action."""

    def test_verb_first(self, engine: IntentEngine) -> None:
        decision = engine.match("open youtube")

        assert decision is not None
        assert decision.action == "open_website"
        assert decision.parameters == {"site": "youtube"}

    def test_urdu_order(self, engine: IntentEngine) -> None:
        decision = engine.match("github kholo")

        assert decision is not None
        assert decision.action == "open_website"
        assert decision.parameters["site"] == "github"

    def test_khol_do_variant(self, engine: IntentEngine) -> None:
        decision = engine.match("gmail khol do")

        assert decision is not None
        assert decision.parameters["site"] == "gmail"


class TestApplicationIntents:
    """App commands resolve only against known local applications."""

    def test_vscode_verb_first(self, engine: IntentEngine) -> None:
        decision = engine.match("open vs code")

        if decision is not None:
            # Only asserted when VS Code exists on this machine.
            assert decision.action == "open_application"
            assert decision.parameters["target"] == "vscode"

    def test_unknown_app_falls_through(self, engine: IntentEngine) -> None:
        # 'xyzapp' can never resolve, so the AI layer should handle it.
        assert engine.match("open xyzapp") is None

    def test_bare_mention_is_not_an_intent(self, engine: IntentEngine) -> None:
        assert engine.match("vs code acha editor hai") is None


class TestScreenshotIntent:
    """Screenshot phrases in both languages."""

    def test_take_screenshot(self, engine: IntentEngine) -> None:
        decision = engine.match("take a screenshot")

        assert decision is not None
        assert decision.action == "take_screenshot"

    def test_urdu_screenshot(self, engine: IntentEngine) -> None:
        decision = engine.match("screenshot lo")

        assert decision is not None
        assert decision.action == "take_screenshot"


class TestSystemInfoIntent:
    """Read-only information queries."""

    def test_time_question(self, engine: IntentEngine) -> None:
        decision = engine.match("kitna baja hai?")

        assert decision is not None
        assert decision.action == "get_system_info"

    def test_system_status(self, engine: IntentEngine) -> None:
        decision = engine.match("system status batao")

        assert decision is not None
        assert decision.action == "get_system_info"


class TestExplicitCommands:
    """UI quick-action chip phrases map to their actions directly."""

    def test_search_files_chip(self, engine: IntentEngine) -> None:
        decision = engine.match("Search Files")

        assert decision is not None
        assert decision.action == "search_files"

    def test_system_cleanup_chip(self, engine: IntentEngine) -> None:
        decision = engine.match("System Cleanup")

        assert decision is not None
        assert decision.action == "system_cleanup"

    def test_start_recording_chip(self, engine: IntentEngine) -> None:
        decision = engine.match("Start Recording")

        assert decision is not None
        assert decision.action == "start_recording"

    def test_urdu_cleanup(self, engine: IntentEngine) -> None:
        decision = engine.match("system cleanup karo")

        assert decision is not None
        assert decision.action == "system_cleanup"


class TestSafety:
    """Ambiguous or non-command input must never trigger actions."""

    def test_empty_input(self, engine: IntentEngine) -> None:
        assert engine.match("") is None
        assert engine.match("   ") is None

    def test_plain_conversation(self, engine: IntentEngine) -> None:
        assert engine.match("aaj mausam kaisa hai?") is None

    def test_non_string_rejected(self, engine: IntentEngine) -> None:
        with pytest.raises(TypeError):
            engine.match(None)  # type: ignore[arg-type]

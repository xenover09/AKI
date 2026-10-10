"""
Integration tests for the Settings panel wiring in AKIBridge.

QSettings is redirected to a temp INI location so persistence tests
never touch the real user registry.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from PySide6.QtCore import QCoreApplication, QSettings

from desktop.bridge import AKIBridge
from desktop.speech import SpeechService


@pytest.fixture(scope="module")
def qt_app():
    """One QCoreApplication for the module (QTimer/QSettings need it)."""

    app = QCoreApplication.instance()

    if app is None:
        app = QCoreApplication([])

    return app


@pytest.fixture()
def isolated_qsettings(tmp_path):
    """Redirect QSettings INI storage into the test's tmp directory."""

    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(tmp_path),
    )


@pytest.fixture()
def fake_settings() -> SimpleNamespace:
    """A stand-in matching config.settings.Settings' AI fields."""

    return SimpleNamespace(
        ai_provider="openai_compatible",
        ai_model="openai/gpt-oss-120b",
    )


def make_bridge(settings=None, speech=None) -> AKIBridge:
    return AKIBridge(
        speech_service=speech if speech is not None else SpeechService(),
        app_settings=settings,
    )


class TestSettingsInjection:
    """Test A — provider/model flow from the injected Settings object."""

    def test_provider_and_model_reported(
        self, qt_app, isolated_qsettings, fake_settings
    ) -> None:
        bridge = make_bridge(settings=fake_settings)

        snapshot = bridge.getSettings()

        assert snapshot["ai_provider"] == "openai_compatible"
        assert snapshot["ai_model"] == "openai/gpt-oss-120b"
        assert snapshot["ai_connected"] is False  # no AI service injected


class TestTtsVoicePersistence:
    """Test B — a selected voice survives service recreation."""

    def test_voice_restored_after_recreation(
        self, qt_app, isolated_qsettings
    ) -> None:
        first = make_bridge()
        assert first.setTtsVoice("ur-PK-UzmaNeural") is True

        # Simulated restart: a brand-new bridge reads persisted state.
        second = make_bridge()

        assert second.getSettings()["tts_voice"] == "ur-PK-UzmaNeural"


class TestMissingSettings:
    """Test C — absent settings must degrade, never crash."""

    def test_none_settings_report_unknown(
        self, qt_app, isolated_qsettings
    ) -> None:
        bridge = make_bridge(settings=None)

        snapshot = bridge.getSettings()

        assert snapshot["ai_provider"] == "unknown"
        assert snapshot["ai_model"] == ""
        assert snapshot["available_voices"]  # speech still functional


class TestInvalidVoice:
    """Test D — invalid selections are rejected without side effects."""

    def test_invalid_voice_rejected_and_not_persisted(
        self, qt_app, isolated_qsettings
    ) -> None:
        bridge = make_bridge()
        before = bridge.getSettings()["tts_voice"]

        assert bridge.setTtsVoice("definitely-not-a-voice") is False

        stored = QSettings("AKI", "DesktopOS").value("tts_voice", "")
        assert stored != "definitely-not-a-voice"
        assert bridge.getSettings()["tts_voice"] == before

    def test_non_string_voice_rejected(
        self, qt_app, isolated_qsettings
    ) -> None:
        bridge = make_bridge()

        assert bridge.setTtsVoice(123) is False  # type: ignore[arg-type]

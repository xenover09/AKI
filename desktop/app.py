"""AKI Desktop Application Entry Point.

Bootstraps the QApplication, applies the global Blue Glass theme,
shows the animated splash screen, and transitions into the
main frameless application window.
"""

from __future__ import annotations

import sys
from typing import Any, Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from desktop.main_window import MainWindow
from desktop.speech import SpeechService
from desktop.splash import SplashScreen
from desktop.themes.blue_theme import BlueTheme


class AKIApplication:
    """Owns the QApplication lifecycle and application bootstrap sequence."""

    def __init__(
        self,
        argv: list[str],
        runtime: Optional[Any] = None,
    ) -> None:
        """Initialize the AKI application.

        Args:
            argv: Command line arguments forwarded to QApplication.
            runtime: Optional ApplicationResult carrying the initialized
                core services (database, memory, conversation, AI).
        """
        self._app: QApplication = QApplication(argv)
        self._runtime = runtime
        self._theme: BlueTheme = BlueTheme()
        self._splash: SplashScreen | None = None
        self._main_window: MainWindow | None = None

        self._configure_application()

    def _configure_application(self) -> None:
        """Apply application-wide metadata and global stylesheet."""
        self._app.setApplicationName("AKI")
        self._app.setOrganizationName("AKI")
        self._app.setStyleSheet(self._theme.global_stylesheet())

    def run(self) -> int:
        """Start the AKI application event loop.

        Returns:
            The process exit code returned by the Qt event loop.
        """
        self._splash = SplashScreen()
        self._splash.show()

        QTimer.singleShot(2200, self._launch_main_window)

        return self._app.exec()

    def _launch_main_window(self) -> None:
        """Close the splash screen and reveal the main window."""
        self._main_window = self._build_main_window()
        self._main_window.show()

        if self._splash is not None:
            self._splash.close()
            self._splash = None

    def _build_main_window(self) -> MainWindow:
        """Construct the main window wired to core runtime services."""
        ai_service = getattr(self._runtime, "ai_service", None)
        conversation_service = getattr(self._runtime, "conversation_service", None)
        database_service = getattr(self._runtime, "database_service", None)
        action_system = getattr(self._runtime, "action_system", None)

        memory_service = None
        memory_search_service = None
        reminder_manager = None
        if database_service is not None:
            from automation.reminder_manager import ReminderManager
            from memory.memory_search import MemorySearchService
            from memory.memory_service import MemoryService

            memory_service = MemoryService(database_service)
            memory_search_service = MemorySearchService(database_service)
            reminder_manager = ReminderManager(database_service)

        return MainWindow(
            ai_service=ai_service,
            conversation_service=conversation_service,
            memory_search_service=memory_search_service,
            memory_service=memory_service,
            action_system=action_system,
            speech_transcriber=self._build_speech_transcriber(),
            speech_service=SpeechService(),
            reminder_manager=reminder_manager,
        )

    def _build_speech_transcriber(self):
        """Create the Groq Whisper transcriber when a real key exists."""
        boot = getattr(self._runtime, "boot", None)
        settings = getattr(boot, "settings", None)

        if settings is None or getattr(settings, "ai_provider", "") != "openai_compatible":
            return None

        if not getattr(settings, "ai_api_key", ""):
            return None

        from ai_engine.speech import SpeechTranscriber

        return SpeechTranscriber(
            base_url=settings.ai_base_url,
            api_key=settings.ai_api_key,
        )


def main() -> int:
    """Application entry point."""
    app = AKIApplication(sys.argv)
    return app.run()


if __name__ == "__main__":
    sys.exit(main())

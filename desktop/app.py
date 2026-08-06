"""AKI Desktop Application Entry Point.

Bootstraps the QApplication, applies the global Blue Glass theme,
shows the animated splash screen, and transitions into the
main frameless application window.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from desktop.main_window_old import MainWindow
from desktop.splash import SplashScreen
from desktop.themes.blue_theme import BlueTheme


class AKIApplication:
    """Owns the QApplication lifecycle and application bootstrap sequence."""

    def __init__(self, argv: list[str]) -> None:
        """Initialize the AKI application.

        Args:
            argv: Command line arguments forwarded to QApplication.
        """
        self._app: QApplication = QApplication(argv)
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
        self._main_window = MainWindow(theme=self._theme)
        self._main_window.show()

        if self._splash is not None:
            self._splash.finish(self._main_window)
            self._splash = None


def main() -> int:
    """Application entry point."""
    app = AKIApplication(sys.argv)
    return app.run()


if __name__ == "__main__":
    sys.exit(main())

"""
AKI System Tray Controller.

Owns the tray icon and its menu so closing the window keeps AKI
alive in the background, JARVIS-style.

Menu:
    - Show AKI
    - Start with Windows (checkable, HKCU Run key)
    - Quit AKI
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from logs.logger import get_logger

logger = get_logger("desktop.tray")

_AUTOSTART_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_AUTOSTART_VALUE_NAME = "AKI"


class TrayController(QObject):
    """
    Wraps the QSystemTrayIcon and its menu.

    Signals:
        show_requested: User clicked "Show AKI".
        quit_requested: User clicked "Quit AKI" — the app must really exit.
    """

    show_requested = Signal()
    quit_requested = Signal()

    def __init__(
        self,
        icon_path: str,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)

        self._tray = QSystemTrayIcon(QIcon(icon_path), self)
        self._tray.setToolTip("AKI — Personal AI Ecosystem")

        menu = QMenu()

        show_action = QAction("Show AKI", menu)
        show_action.triggered.connect(self.show_requested.emit)
        menu.addAction(show_action)

        menu.addSeparator()

        self._autostart_action = QAction("Start with Windows", menu)
        self._autostart_action.setCheckable(True)
        self._autostart_action.setChecked(self._is_autostart_enabled())
        self._autostart_action.toggled.connect(self._set_autostart_enabled)
        menu.addAction(self._autostart_action)

        menu.addSeparator()

        quit_action = QAction("Quit AKI", menu)
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.show()

        logger.info("System tray icon active.")

    # ============================================================
    # Public API
    # ============================================================

    def notify(self, title: str, message: str) -> None:
        """Show a tray balloon message."""

        self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 4000)

    @staticmethod
    def is_available() -> bool:
        """Return whether the platform supports a system tray."""

        return QSystemTrayIcon.isSystemTrayAvailable()

    # ============================================================
    # Autostart (HKCU Run key — per-user only)
    # ============================================================

    @staticmethod
    def _is_autostart_enabled() -> bool:
        """Check the Run key for the AKI entry."""

        if sys.platform != "win32":
            return False

        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                _AUTOSTART_RUN_KEY,
                0,
                winreg.KEY_READ,
            )
            value, _type = winreg.QueryValueEx(key, _AUTOSTART_VALUE_NAME)
            winreg.CloseKey(key)
            return bool(value)
        except FileNotFoundError:
            return False
        except OSError as error:
            logger.warning("Autostart lookup failed: %s", error)
            return False

    @staticmethod
    def _set_autostart_enabled(enabled: bool) -> None:
        """Create or remove the HKCU Run entry for AKI."""

        if sys.platform != "win32":
            return

        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                _AUTOSTART_RUN_KEY,
                0,
                winreg.KEY_SET_VALUE,
            )

            if enabled:
                executable = f'"{sys.executable}"'
                winreg.SetValueEx(
                    key, _AUTOSTART_VALUE_NAME, 0, winreg.REG_SZ, executable
                )
                logger.info("Autostart enabled | %s", executable)
            else:
                try:
                    winreg.DeleteValue(key, _AUTOSTART_VALUE_NAME)
                    logger.info("Autostart disabled.")
                except FileNotFoundError:
                    pass

            winreg.CloseKey(key)
        except OSError as error:
            logger.warning("Autostart toggle failed: %s", error)


__all__ = [
    "TrayController",
]

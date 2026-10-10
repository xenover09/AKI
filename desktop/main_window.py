"""Primary frameless application window for AKI desktop operating system.

Hosts the WebEngine view containing the 2035 Futuristic HTML/CSS/JS interface
within a translucent glass shell, providing native window control, manual edge resizing,
and window geometry persistence (position and size memory).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from PySide6.QtCore import QPoint, QRect, QSettings, QSize, Qt
from PySide6.QtGui import QCursor, QMouseEvent, QResizeEvent
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget

from desktop.themes.aki_theme import AkiTheme
from desktop.web_view import AKIWebView
from desktop.window_effects import WindowEffects
from logs.logger import get_logger
from services.telemetry_service import TelemetryService

logger: logging.Logger = get_logger("desktop.main_window")

_DEFAULT_WIDTH: int = 1280
_DEFAULT_HEIGHT: int = 800
_MIN_WIDTH: int = 1000
_MIN_HEIGHT: int = 650
_RESIZE_MARGIN: int = 8


class MainWindow(QMainWindow):
    """Frameless top-level window container hosting the AKI WebEngine interface."""

    def __init__(
        self,
        telemetry_service: Optional[TelemetryService] = None,
        ai_service: Optional[Any] = None,
        conversation_service: Optional[Any] = None,
        memory_search_service: Optional[Any] = None,
        memory_service: Optional[Any] = None,
        action_system: Optional[Any] = None,
        speech_transcriber: Optional[Any] = None,
        speech_service: Optional[Any] = None,
        reminder_manager: Optional[Any] = None,
        app_settings: Optional[Any] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the main window shell.

        Args:
            telemetry_service: Optional telemetry service instance.
            ai_service: Optional intelligence facade for real AI replies.
            conversation_service: Optional chat history persistence.
            memory_search_service: Optional ranked memory provider.
            memory_service: Optional persistent memory writer for auto-facts.
            action_system: Optional permission-checked action stack.
            speech_transcriber: Optional speech-to-text backend for the mic.
            speech_service: Optional text-to-speech service for spoken replies.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._telemetry_service = (
            telemetry_service if telemetry_service is not None else TelemetryService()
        )
        self._ai_service = ai_service
        self._conversation_service = conversation_service
        self._memory_search_service = memory_search_service
        self._memory_service = memory_service
        self._action_system = action_system
        self._speech_transcriber = speech_transcriber
        self._speech_service = speech_service
        self._reminder_manager = reminder_manager
        self._app_settings = app_settings
        self._settings = QSettings("AKI", "DesktopOS")
        self._drag_position: QPoint = QPoint()
        self._is_dragging: bool = False
        self._tray_controller = None
        self._tray_hint_shown: bool = False
        self._force_close: bool = False

        self._configure_window()
        self._build_ui()
        self._apply_effects()
        self._restore_window_geometry()

    def _configure_window(self) -> None:
        """Configure window flags, size, and background translucency."""
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowSystemMenuHint |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(_MIN_WIDTH, _MIN_HEIGHT)
        self.resize(_DEFAULT_WIDTH, _DEFAULT_HEIGHT)
        self.setMouseTracking(True)

    def _build_ui(self) -> None:
        """Construct the central widget and embed AKIWebView."""
        self._central_widget = QWidget(self)
        self._central_widget.setObjectName("centralContainer")
        # Use an almost-transparent background so Win32 catches mouse events instead of passing through to desktop
        self._central_widget.setStyleSheet(
            "QWidget#centralContainer { background: rgba(1, 1, 1, 1); }"
        )
        self._central_widget.setMouseTracking(True)
        self.setCentralWidget(self._central_widget)

        layout = QVBoxLayout(self._central_widget)
        # Add 6px margin so the MainWindow receives WM_NCHITTEST instead of QWebEngineView
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(0)

        # Create WebEngine View
        self._web_view = AKIWebView(
            telemetry_service=self._telemetry_service,
            ai_service=self._ai_service,
            conversation_service=self._conversation_service,
            memory_search_service=self._memory_search_service,
            memory_service=self._memory_service,
            action_system=self._action_system,
            speech_transcriber=self._speech_transcriber,
            speech_service=self._speech_service,
            reminder_manager=self._reminder_manager,
            app_settings=self._app_settings,
            parent=self,
        )
        self._web_view.bridge().set_window_reference(self)
        self._web_view.installEventFilter(self)
        if self._web_view.focusProxy() is not None:
            self._web_view.focusProxy().installEventFilter(self)
        layout.addWidget(self._web_view)

        # Dynamic Theme Linking
        from desktop.themes.theme_manager import ThemeManager
        tm = ThemeManager.get_instance()
        if tm:
            tm.themeChanged.connect(self._on_theme_changed)
            # initial web theme set when load finishes
            self._web_view.loadFinished.connect(
                lambda ok: self._web_view.set_web_theme(not tm.is_dark()) if ok else None
            )

    def _on_theme_changed(self, theme):
        """Re-skin webview when Qt theme changes dynamically."""
        from desktop.themes.theme_manager import ThemeManager
        tm = ThemeManager.get_instance()
        if tm and hasattr(self, "_web_view"):
            self._web_view.set_web_theme(not tm.is_dark())

    def changeEvent(self, event) -> None:
        """Track window state changes (e.g. Maximize/Restore) and notify bridge."""
        super().changeEvent(event)
        if event.type() == event.Type.WindowStateChange:
            if hasattr(self, "_web_view") and self._web_view is not None:
                state_str = "maximized" if self.isMaximized() else "normal"
                self._web_view.bridge().windowStateChanged.emit(state_str)

    def nativeEvent(self, event_type, message) -> tuple[bool, int]:
        """Intercept WM_NCHITTEST to enable native OS frameless window resizing."""
        if event_type == b"windows_generic_MSG" or event_type == "windows_generic_MSG":
            import sys
            if sys.platform == "win32":
                import ctypes
                from ctypes import wintypes
                
                class MSG(ctypes.Structure):
                    _fields_ = [("hwnd", wintypes.HWND),
                                ("message", wintypes.UINT),
                                ("wParam", wintypes.WPARAM),
                                ("lParam", wintypes.LPARAM),
                                ("time", wintypes.DWORD),
                                ("pt", wintypes.POINT)]
                
                msg = MSG.from_address(int(message))
                if msg.message == 0x0084: # WM_NCHITTEST
                    x = msg.lParam & 0xFFFF
                    if x >= 32768: x -= 65536
                    y = (msg.lParam >> 16) & 0xFFFF
                    if y >= 32768: y -= 65536
                    
                    local_pos = self.mapFromGlobal(QPoint(x, y))
                    edges = self._get_resize_edges(local_pos)
                    
                    if edges:
                        combined_edge = edges[0]
                        for edge in edges[1:]:
                            combined_edge = combined_edge | edge
                            
                        edge_map = {
                            Qt.Edge.LeftEdge: 10, # HTLEFT
                            Qt.Edge.RightEdge: 11, # HTRIGHT
                            Qt.Edge.TopEdge: 12, # HTTOP
                            Qt.Edge.TopEdge | Qt.Edge.LeftEdge: 13, # HTTOPLEFT
                            Qt.Edge.TopEdge | Qt.Edge.RightEdge: 14, # HTTOPRIGHT
                            Qt.Edge.BottomEdge: 15, # HTBOTTOM
                            Qt.Edge.BottomEdge | Qt.Edge.LeftEdge: 16, # HTBOTTOMLEFT
                            Qt.Edge.BottomEdge | Qt.Edge.RightEdge: 17, # HTBOTTOMRIGHT
                        }
                        ht_code = edge_map.get(combined_edge, 0)
                        if ht_code:
                            return True, ht_code
                            
        return super().nativeEvent(event_type, message)

    def _apply_effects(self) -> None:
        """Apply Windows acrylic blur effects if supported."""
        try:
            effects = WindowEffects(self, AkiTheme())
            # effects.enable_acrylic_blur() # Disabled for Dark Solid aesthetic
        except Exception as err:
            logger.debug("Platform window effect application notice: %s", err)

    def _restore_window_geometry(self) -> None:
        """Restore window position, size, and state from QSettings."""
        geometry = self._settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            # Default centering on screen
            screen = self.screen()
            if screen is not None:
                screen_geom = screen.availableGeometry()
                x = (screen_geom.width() - _DEFAULT_WIDTH) // 2
                y = (screen_geom.height() - _DEFAULT_HEIGHT) // 2
                self.move(x, y)

        if self._settings.value("is_maximized", False, type=bool):
            self.showMaximized()

    def _save_window_geometry(self) -> None:
        """Save current window geometry and state to QSettings."""
        if not self.isMaximized():
            self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("is_maximized", self.isMaximized())

    def closeEvent(self, event) -> None:
        """Save geometry; hide to tray instead of exiting when tray is active."""
        self._save_window_geometry()

        if self._tray_controller is not None and not self._force_close:
            event.ignore()
            self.hide()

            if not self._tray_hint_shown:
                self._tray_hint_shown = True
                self._tray_controller.notify(
                    "AKI is still running",
                    "AKI tray mein chal raha hai. Quit ke liye tray icon > Quit AKI use karein.",
                )
            return

        super().closeEvent(event)

    def set_tray_controller(self, tray_controller) -> None:
        """Enable close-to-tray behavior with the given controller."""

        self._tray_controller = tray_controller

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Save geometry on resize when not maximized."""
        super().resizeEvent(event)
        if not self.isMaximized():
            self._settings.setValue("geometry", self.saveGeometry())

    def _get_resize_edges(self, pos: QPoint) -> list[Qt.Edge]:
        """Determine which border edges are hit by mouse coordinate.

        Args:
            pos: Mouse position relative to window top-left.

        Returns:
            List of active border edges.
        """
        rect = self.rect()
        edges: list[Qt.Edge] = []

        if pos.x() <= _RESIZE_MARGIN:
            edges.append(Qt.Edge.LeftEdge)
        elif pos.x() >= rect.width() - _RESIZE_MARGIN:
            edges.append(Qt.Edge.RightEdge)

        if pos.y() <= _RESIZE_MARGIN:
            edges.append(Qt.Edge.TopEdge)
        elif pos.y() >= rect.height() - _RESIZE_MARGIN:
            edges.append(Qt.Edge.BottomEdge)

        return edges

    def _update_cursor_shape(self, edges: list[Qt.Edge]) -> None:
        """Update cursor shape depending on active window edge hit.

        Args:
            edges: Active border edges.
        """
        if self.isMaximized():
            self.unsetCursor()
            return

        if (Qt.Edge.LeftEdge in edges and Qt.Edge.TopEdge in edges) or (
            Qt.Edge.RightEdge in edges and Qt.Edge.BottomEdge in edges
        ):
            self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
        elif (Qt.Edge.RightEdge in edges and Qt.Edge.TopEdge in edges) or (
            Qt.Edge.LeftEdge in edges and Qt.Edge.BottomEdge in edges
        ):
            self.setCursor(QCursor(Qt.CursorShape.SizeBDiagCursor))
        elif Qt.Edge.LeftEdge in edges or Qt.Edge.RightEdge in edges:
            self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
        elif Qt.Edge.TopEdge in edges or Qt.Edge.BottomEdge in edges:
            self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
        else:
            self.unsetCursor()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Move window when dragged or update edge resize cursor."""
        if not self.isMaximized():
            edges = self._get_resize_edges(event.position().toPoint())
            self._update_cursor_shape(edges)

        if self._is_dragging and event.buttons() & Qt.MouseButton.LeftButton and not self.isMaximized():
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Release window drag tracking."""
        self._is_dragging = False
        event.accept()
        super().mouseReleaseEvent(event)

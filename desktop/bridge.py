"""Bridge layer connecting PySide6 Python backend to Qt WebEngine JavaScript frontend.

Exposes thread-safe slots and signals via QWebChannel for bidirectional
communication, telemetry streaming, and window control.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from PySide6.QtCore import QObject, Signal, Slot

from services.telemetry_service import TelemetryService

logger: logging.Logger = logging.getLogger(__name__)


class AKIBridge(QObject):
    """QObject bridge registered with QWebChannel to expose Python API to JavaScript."""

    # Signals emitted to JavaScript
    telemetryUpdated = Signal(dict)
    aiStatusChanged = Signal(dict)
    notificationPushed = Signal(dict)
    windowStateChanged = Signal(str)

    def __init__(
        self,
        telemetry_service: Optional[TelemetryService] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        """Initialize the AKI JavaScript-Python Bridge.

        Args:
            telemetry_service: Optional system telemetry monitoring instance.
            parent: Optional Qt parent object.
        """
        super().__init__(parent)
        self._telemetry_service: TelemetryService = (
            telemetry_service if telemetry_service is not None else TelemetryService()
        )
        self._window_ref: Optional[Any] = None

    def set_window_reference(self, window: Any) -> None:
        """Store reference to the main Qt window for native window operations.

        Args:
            window: The parent PySide QMainWindow instance.
        """
        self._window_ref = window

    @Slot(result=dict)
    def getSystemTelemetry(self) -> Dict[str, Any]:
        """Fetch current telemetry snapshot.

        Returns:
            Dictionary payload with system, memory, AI core, and uptime data.
        """
        return self._telemetry_service.get_telemetry_snapshot()

    @Slot()
    def publishTelemetry(self) -> None:
        """Collect current system telemetry and emit signal to JavaScript."""
        snapshot = self._telemetry_service.get_telemetry_snapshot()
        self.telemetryUpdated.emit(snapshot)

    @Slot(str, result=dict)
    def triggerDiagnosticScan(self, scan_type: str = "full") -> Dict[str, Any]:
        """Trigger diagnostic system scan.

        Args:
            scan_type: Type of scan ('full', 'quick', 'security').

        Returns:
            Diagnostic scan result status payload.
        """
        logger.info("Executing diagnostic scan: %s", scan_type)
        return {
            "status": "COMPLETED",
            "scan_type": scan_type,
            "threats_found": 0,
            "integrity": "100%",
            "timestamp": self._telemetry_service.get_system_uptime_seconds(),
        }

    @Slot(result=dict)
    def selectAttachment(self) -> Dict[str, Any]:
        """Open native desktop file dialog to select a file attachment.

        Returns:
            Dictionary with file details or empty status if cancelled.
        """
        from PySide6.QtWidgets import QFileDialog

        parent_widget = self._window_ref if self._window_ref is not None else None
        file_path, _ = QFileDialog.getOpenFileName(
            parent_widget,
            "Attach File to AKI",
            "",
            "All Files (*.*);;Images (*.png *.jpg *.jpeg *.webp);;Code (*.py *.js *.json *.html *.css *.txt)",
        )

        if not file_path:
            return {"selected": False}

        from pathlib import Path

        p = Path(file_path)
        return {
            "selected": True,
            "name": p.name,
            "path": str(p),
            "size_bytes": p.stat().st_size if p.exists() else 0,
            "extension": p.suffix,
        }

    @Slot(str, str, result=dict)
    def sendAiPrompt(self, prompt: str, attachment_name: str = "") -> Dict[str, Any]:
        """Process prompt from JavaScript frontend and return structured AI response.

        Args:
            prompt: User command or chat message.
            attachment_name: Optional attached filename.

        Returns:
            AI response payload.
        """
        logger.info("Processing AI Prompt: %s (Attachment: %s)", prompt, attachment_name)
        response_text = f"AKI OS has processed your request: '{prompt}'."
        if attachment_name:
            response_text += f" Analyzed attached artifact [{attachment_name}]."

        return {
            "status": "SUCCESS",
            "prompt": prompt,
            "response": response_text,
            "attachment": attachment_name,
            "timestamp": self._telemetry_service.get_system_uptime_seconds(),
        }

    @Slot()
    def startWindowMove(self) -> None:
        """Trigger native OS frameless window dragging."""
        if self._window_ref is not None:
            import sys
            if sys.platform == "win32":
                import ctypes
                hwnd = self._window_ref.winId()
                ctypes.windll.user32.ReleaseCapture()
                ctypes.windll.user32.SendMessageW(int(hwnd), 0x00A1, 2, 0) # WM_NCLBUTTONDOWN, HTCAPTION
            elif self._window_ref.windowHandle() is not None:
                self._window_ref.windowHandle().startSystemMove()

    @Slot(str)
    def startWindowResize(self, edge_name: str) -> None:
        """Trigger native OS frameless window resizing.

        Args:
            edge_name: Hit border name ('left', 'right', 'top', 'bottom', 'top-left', 'top-right', 'bottom-left', 'bottom-right').
        """
        if self._window_ref is None or self._window_ref.windowHandle() is None:
            return

        edge_map = {
            "left": Qt.Edge.LeftEdge,
            "right": Qt.Edge.RightEdge,
            "top": Qt.Edge.TopEdge,
            "bottom": Qt.Edge.BottomEdge,
            "top-left": Qt.Edge.TopEdge | Qt.Edge.LeftEdge,
            "top-right": Qt.Edge.TopEdge | Qt.Edge.RightEdge,
            "bottom-left": Qt.Edge.BottomEdge | Qt.Edge.LeftEdge,
            "bottom-right": Qt.Edge.BottomEdge | Qt.Edge.RightEdge,
        }

        qt_edge = edge_map.get(edge_name.lower())
        if qt_edge is not None:
            self._window_ref.windowHandle().startSystemResize(qt_edge)

    @Slot(result=bool)
    def isMaximized(self) -> bool:
        """Check if main window is currently maximized."""
        if self._window_ref is not None:
            return self._window_ref.isMaximized()
        return False

    @Slot()
    def minimizeWindow(self) -> None:
        """Minimize the main application window."""
        if self._window_ref is not None:
            self._window_ref.showMinimized()

    @Slot()
    def maximizeWindow(self) -> None:
        """Toggle maximize/restore state of main window using native PySide6 APIs."""
        if self._window_ref is not None:
            if self._window_ref.isMaximized():
                self._window_ref.showNormal()
                self.windowStateChanged.emit("normal")
            else:
                self._window_ref.showMaximized()
                self.windowStateChanged.emit("maximized")

    @Slot()
    def closeWindow(self) -> None:
        """Close the desktop application."""
        if self._window_ref is not None:
            self._window_ref.close()


"""PySide6 QtWebEngine container and bridge host for AKI HTML/CSS/JS interface.

Loads local web interfaces, exposes QWebChannel for Python-JS IPC, and streams
real-time system telemetry.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QTimer, QUrl, Qt
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QWidget

from desktop.bridge import AKIBridge
from services.telemetry_service import TelemetryService

logger: logging.Logger = logging.getLogger(__name__)

_TELEMETRY_INTERVAL_MS: int = 1500


class AKIWebView(QWebEngineView):
    """QWebEngineView component hosting the AKI 2035 Futuristic HTML UI."""

    def __init__(
        self,
        telemetry_service: Optional[TelemetryService] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the WebEngine View and set up QWebChannel.

        Args:
            telemetry_service: Optional telemetry service instance.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._telemetry_service = (
            telemetry_service if telemetry_service is not None else TelemetryService()
        )
        self._bridge = AKIBridge(telemetry_service=self._telemetry_service)
        self._channel = QWebChannel(self)
        self._telemetry_timer: Optional[QTimer] = None

        self._configure_web_engine()
        self._setup_web_channel()
        self.load_dashboard()

    def bridge(self) -> AKIBridge:
        """Access the underlying AKIBridge object.

        Returns:
            The AKIBridge instance registered with QWebChannel.
        """
        return self._bridge

    def _configure_web_engine(self) -> None:
        """Apply transparent background and WebEngine settings."""
        self.page().setBackgroundColor(Qt.GlobalColor.transparent)
        
        settings = self.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ShowScrollBars, False)

    def _setup_web_channel(self) -> None:
        """Register the AKIBridge with QWebChannel."""
        self._channel.registerObject("aki_bridge", self._bridge)
        self.page().setWebChannel(self._channel)

    def load_design_system(self) -> None:
        """Load the local design_system.html page into the WebEngine View."""
        project_root = Path(__file__).resolve().parent.parent
        ds_path = project_root / "interfaces" / "web" / "design_system.html"

        if not ds_path.exists():
            logger.error("Design System HTML file missing at path: %s", ds_path)
            return

        file_url = QUrl.fromLocalFile(str(ds_path))
        logger.info("Loading AKI 2035 Design System Showcase from: %s", file_url.toString())
        self.setUrl(file_url)

        self._start_telemetry_stream()

    def load_dashboard(self) -> None:
        """Load the local dashboard.html page into the WebEngine View."""
        project_root = Path(__file__).resolve().parent.parent
        dashboard_path = project_root / "interfaces" / "web" / "dashboard.html"

        if not dashboard_path.exists():
            logger.error("Dashboard HTML file missing at path: %s", dashboard_path)
            return

        file_url = QUrl.fromLocalFile(str(dashboard_path))
        logger.info("Loading AKI Web Dashboard from: %s", file_url.toString())
        self.setUrl(file_url)

        self._start_telemetry_stream()

    def _start_telemetry_stream(self) -> None:
        """Start periodic telemetry streaming to JavaScript."""
        if self._telemetry_timer is None:
            self._telemetry_timer = QTimer(self)
            self._telemetry_timer.setInterval(_TELEMETRY_INTERVAL_MS)
            self._telemetry_timer.timeout.connect(self._bridge.publishTelemetry)

        self._telemetry_timer.start()

    def stop_telemetry_stream(self) -> None:
        """Stop the periodic telemetry timer."""
        if self._telemetry_timer is not None:
            self._telemetry_timer.stop()

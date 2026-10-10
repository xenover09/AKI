"""PySide6 QtWebEngine container and bridge host for AKI HTML/CSS/JS interface.

Loads local web interfaces, exposes QWebChannel for Python-JS IPC, and streams
real-time system telemetry.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import QTimer, QUrl, Qt
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QWidget

from desktop.bridge import AKIBridge
from logs.logger import get_logger
from services.telemetry_service import TelemetryService

logger: logging.Logger = get_logger("desktop.web_view")

_TELEMETRY_INTERVAL_MS: int = 1500


class AKIWebView(QWebEngineView):
    """QWebEngineView component hosting the AKI 2035 Futuristic HTML UI."""

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
        knowledge_library: Optional[Any] = None,
        app_settings: Optional[Any] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the WebEngine View and set up QWebChannel.

        Args:
            telemetry_service: Optional system telemetry monitoring instance.
            ai_service: Optional intelligence facade for real AI replies.
            conversation_service: Optional chat history persistence.
            memory_search_service: Optional ranked memory provider.
            memory_service: Optional persistent memory writer for auto-facts.
            action_system: Optional permission-checked action stack.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._telemetry_service = (
            telemetry_service if telemetry_service is not None else TelemetryService()
        )
        self._bridge = AKIBridge(
            telemetry_service=self._telemetry_service,
            ai_service=ai_service,
            conversation_service=conversation_service,
            memory_search_service=memory_search_service,
            memory_service=memory_service,
            action_system=action_system,
            speech_transcriber=speech_transcriber,
            speech_service=speech_service,
            reminder_manager=reminder_manager,
            knowledge_library=knowledge_library,
            app_settings=app_settings,
        )
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

    def set_web_theme(self, is_light: bool) -> None:
        """Inject JS to toggle the web theme dynamically."""
        js = "document.body.classList.add('theme-light');" if is_light else "document.body.classList.remove('theme-light');"
        self.page().runJavaScript(js)

    def _configure_web_engine(self) -> None:
        """Apply transparent background and WebEngine settings."""
        self.page().setBackgroundColor(Qt.GlobalColor.transparent)

        settings = self.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ShowScrollBars, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)

        # Voice input: grant microphone access to our local UI origin.
        self.page().featurePermissionRequested.connect(
            self._grant_feature_permission
        )

    def _grant_feature_permission(self, origin, feature) -> None:
        """Auto-grant media permissions for AKI's own local interface."""

        from PySide6.QtWebEngineCore import QWebEnginePage

        if feature in (
            QWebEnginePage.Feature.MediaAudioCapture,
            QWebEnginePage.Feature.MediaAudioVideoCapture,
        ):
            self.page().setFeaturePermission(
                origin,
                feature,
                QWebEnginePage.PermissionPolicy.PermissionGrantedByUser,
            )
            logger.info("Microphone permission granted for %s", origin.toString())

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

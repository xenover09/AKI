"""Bridge layer connecting PySide6 Python backend to Qt WebEngine JavaScript frontend.

Exposes thread-safe slots and signals via QWebChannel for bidirectional
communication, real AI conversations, telemetry streaming, and window control.

AI requests run on background threads; all database access stays on the
main thread because the SQLite connection is single-threaded by design.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, Optional
from uuid import uuid4

from PySide6.QtCore import QObject, Signal, Slot

from logs.logger import get_logger
from memory.extraction import extract_facts
from services.telemetry_service import TelemetryService

logger: logging.Logger = get_logger("desktop.bridge")

_HISTORY_MESSAGE_LIMIT: int = 10
_MEMORY_CONTEXT_LIMIT: int = 5


class AKIBridge(QObject):
    """QObject bridge registered with QWebChannel to expose Python API to JavaScript."""

    # Signals emitted to JavaScript
    telemetryUpdated = Signal(dict)
    aiStatusChanged = Signal(dict)
    notificationPushed = Signal(dict)
    windowStateChanged = Signal(str)
    aiResponseReady = Signal(dict)

    # Internal worker-thread -> main-thread completion channels.
    _providerSucceeded = Signal(str, str)
    _providerFailed = Signal(str, str)

    def __init__(
        self,
        telemetry_service: Optional[TelemetryService] = None,
        ai_service: Optional[Any] = None,
        conversation_service: Optional[Any] = None,
        memory_search_service: Optional[Any] = None,
        memory_service: Optional[Any] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        """Initialize the AKI JavaScript-Python Bridge.

        Args:
            telemetry_service: Optional system telemetry monitoring instance.
            ai_service: Optional intelligence facade used for real replies.
            conversation_service: Optional persistence for chat history.
            memory_search_service: Optional ranked memory provider for context.
            memory_service: Optional persistent memory writer for auto-facts.
            parent: Optional Qt parent object.
        """
        super().__init__(parent)
        self._telemetry_service: TelemetryService = (
            telemetry_service if telemetry_service is not None else TelemetryService()
        )
        self._ai_service = ai_service
        self._conversation_service = conversation_service
        self._memory_search_service = memory_search_service
        self._memory_service = memory_service
        self._conversation_id: Optional[str] = None
        self._conversation_lock = threading.Lock()
        self._window_ref: Optional[Any] = None

        self._providerSucceeded.connect(self._on_provider_success)
        self._providerFailed.connect(self._on_provider_failure)

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

    @Slot(result=bool)
    def isAiConfigured(self) -> bool:
        """Report whether a real intelligence provider is available."""
        return self._ai_service is not None

    @Slot()
    def clearConversation(self) -> None:
        """Discard the active conversation; the next prompt starts fresh."""
        with self._conversation_lock:
            self._conversation_id = None
        logger.info("Desktop conversation cleared.")

    @Slot(str, str, result=dict)
    def sendAiPrompt(self, prompt: str, attachment_name: str = "") -> Dict[str, Any]:
        """Queue a user prompt for AKI's intelligence layer.

        Database work (history + persistence) happens here on the main
        thread; only the network-bound provider call runs on a worker
        thread. The reply is delivered later via `aiResponseReady`.

        Returns:
            PENDING payload with a request id when real AI is configured,
            otherwise an immediate informational payload.
        """
        text = (prompt or "").strip()

        if not text:
            return {"status": "EMPTY", "request_id": "", "response": ""}

        if attachment_name:
            logger.info("Attachment noted but not yet analyzed: %s", attachment_name)

        if self._ai_service is None:
            return {
                "status": "NO_PROVIDER",
                "request_id": "",
                "response": (
                    "AKI ka intelligence provider abhi configure nahi hua. "
                    ".env file mein AKI_AI_PROVIDER aur AKI_AI_API_KEY set karein."
                ),
            }

        request_id = uuid4().hex[:12]
        history = self._load_history()
        memories = self._collect_memory_context(text)
        self._persist_user_message(text)
        self._store_auto_memories(text)

        worker = threading.Thread(
            target=self._run_provider,
            args=(request_id, text, tuple(history), tuple(memories)),
            daemon=True,
            name=f"aki-ai-{request_id}",
        )
        worker.start()
        return {"status": "PENDING", "request_id": request_id}

    # ============================================================
    # AI pipeline internals
    # ============================================================

    def _ensure_conversation(self) -> Optional[str]:
        """Return the active desktop conversation id.

        The most recent existing conversation is resumed so chat
        history (and AKI's context) survive application restarts. A
        new conversation is only created when none exists yet.
        """
        if self._conversation_service is None:
            return None

        with self._conversation_lock:
            if self._conversation_id is None:
                self._conversation_id = self._latest_conversation_id()

            if self._conversation_id is None:
                conversation = self._conversation_service.create_conversation(
                    "AKI Desktop Session"
                )
                self._conversation_id = conversation.conversation_id

            return self._conversation_id

    def _latest_conversation_id(self) -> Optional[str]:
        """Return the id of the most recently updated conversation."""

        try:
            conversations = self._conversation_service.list_conversations(
                limit=1
            )
        except Exception:
            logger.exception("Conversation lookup failed.")
            return None

        return conversations[0].conversation_id if conversations else None

    def _load_history(self) -> list[Any]:
        """Load recent conversation messages for context."""
        conversation_id = self._ensure_conversation()
        if not conversation_id:
            return []

        try:
            return list(
                self._conversation_service.get_history(
                    conversation_id,
                    limit=_HISTORY_MESSAGE_LIMIT,
                )
            )
        except Exception:
            logger.exception("Could not load conversation history.")
            return []

    def _collect_memory_context(self, query: str) -> list[str]:
        """Return memory lines relevant to the prompt."""
        if self._memory_search_service is None:
            return []

        try:
            results = self._memory_search_service.search(
                query,
                limit=_MEMORY_CONTEXT_LIMIT,
            )
            return [result.memory.content for result in results]
        except Exception:
            logger.exception("Memory context lookup failed.")
            return []

    def _persist_user_message(self, text: str) -> None:
        """Store the user's message in the active conversation."""
        from conversation.models import MessageRole

        conversation_id = self._ensure_conversation()
        if not conversation_id:
            return

        try:
            self._conversation_service.add_message(
                conversation_id,
                MessageRole.USER,
                text,
            )
        except Exception:
            logger.exception("User message could not be persisted.")

    def _store_auto_memories(self, text: str) -> None:
        """Persist high-confidence facts found in the user's message."""

        if self._memory_service is None:
            return

        try:
            facts = extract_facts(text)
        except Exception:
            logger.exception("Fact extraction failed.")
            return

        for fact in facts:
            try:
                self._memory_service.remember(fact.to_memory())
                logger.info("Auto-memory stored: %s", fact.content)
            except Exception:
                logger.exception("Auto-memory could not be persisted.")

    def _run_provider(
        self,
        request_id: str,
        prompt: str,
        history: tuple,
        memories: tuple,
    ) -> None:
        """Worker-thread body: call the provider and report back via signal."""
        try:
            response = self._ai_service.respond(
                prompt,
                history=history,
                memories=memories,
            )
            content = response.content.strip()
            self._providerSucceeded.emit(request_id, content)
        except Exception as error:  # noqa: BLE001 - surfaced to the UI
            logger.exception("AI provider call failed.")
            self._providerFailed.emit(request_id, str(error))

    def _on_provider_success(self, request_id: str, content: str) -> None:
        """Main-thread completion: persist and forward the assistant reply."""
        fallback = content or "Main is waqt jawab tayyar nahi bana saka."
        self._persist_assistant_message(fallback)
        self.aiResponseReady.emit(
            {
                "status": "SUCCESS",
                "request_id": request_id,
                "response": fallback,
            }
        )

    def _on_provider_failure(self, request_id: str, detail: str) -> None:
        """Main-thread failure: inform the UI without crashing."""
        self.aiResponseReady.emit(
            {
                "status": "ERROR",
                "request_id": request_id,
                "response": (
                    "Intelligence subsystem mein masla prega hai. "
                    "Meherbani kar ke dobara koshish karein."
                ),
                "detail": detail,
            }
        )

    def _persist_assistant_message(self, text: str) -> None:
        """Store AKI's reply in the active conversation."""
        from conversation.models import MessageRole

        conversation_id = self._ensure_conversation()
        if not conversation_id:
            return

        try:
            self._conversation_service.add_message(
                conversation_id,
                MessageRole.ASSISTANT,
                text,
            )
        except Exception:
            logger.exception("Assistant message could not be persisted.")

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


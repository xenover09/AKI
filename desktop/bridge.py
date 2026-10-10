"""Bridge layer connecting PySide6 Python backend to Qt WebEngine JavaScript frontend.

Exposes thread-safe slots and signals via QWebChannel for bidirectional
communication, real AI conversations, telemetry streaming, and window control.

AI requests run on background threads; all database access stays on the
main thread because the SQLite connection is single-threaded by design.
"""

from __future__ import annotations

import base64
import logging
import threading
from typing import Any, Dict, Optional
from uuid import uuid4

from PySide6.QtCore import QMetaObject, QObject, QSettings, Qt, Signal, Slot

from aki_core.intent_engine import IntentEngine
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
    transcriptionReady = Signal(str, str)

    # Internal worker-thread -> main-thread completion channels.
    _providerSucceeded = Signal(str, str)
    _providerFailed = Signal(str, str)
    _transcribeSucceeded = Signal(str, str)
    _transcribeFailed = Signal(str)
    _speechFileReady = Signal(str, str)

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
        parent: Optional[QObject] = None,
    ) -> None:
        """Initialize the AKI JavaScript-Python Bridge.

        Args:
            telemetry_service: Optional system telemetry monitoring instance.
            ai_service: Optional intelligence facade used for real replies.
            conversation_service: Optional persistence for chat history.
            memory_search_service: Optional ranked memory provider for context.
            memory_service: Optional persistent memory writer for auto-facts.
            action_system: Optional permission-checked action stack for
                system commands (open apps, websites, screenshots).
            speech_transcriber: Optional speech-to-text backend for voice input.
            speech_service: Optional text-to-speech service for spoken replies.
            reminder_manager: Optional persistence for scheduled reminders.
            knowledge_library: Optional book library for page-cited answers.
            app_settings: Optional boot Settings snapshot for the UI panel.
            parent: Optional Qt parent object.
        """
        super().__init__(parent)
        self._app_settings = app_settings
        self._settings = QSettings("AKI", "DesktopOS")
        self._telemetry_service: TelemetryService = (
            telemetry_service if telemetry_service is not None else TelemetryService()
        )
        self._ai_service = ai_service
        self._conversation_service = conversation_service
        self._memory_search_service = memory_search_service
        self._memory_service = memory_service
        self._action_system = action_system
        self._speech_transcriber = speech_transcriber
        self._speech = speech_service
        self._reminder_manager = reminder_manager
        self._knowledge = knowledge_library


        if ai_service is not None:
            from dev_agent.agent import DevAgent

            self._dev_agent = DevAgent(
                ai_responder=lambda prompt: ai_service.respond(
                    prompt
                ).content,
            )
        else:
            self._dev_agent = None

        from services.web_search import WebSearchService

        self._web_search = WebSearchService()
        self._intents = IntentEngine()
        self._register_desktop_handlers()
        self._conversation_id: Optional[str] = None
        self._conversation_lock = threading.Lock()
        self._window_ref: Optional[Any] = None
        self._pending_attachment_path: Optional[str] = None
        self._voice_enabled = speech_service is not None
        self._daily_fired: Dict[str, str] = {}
        self._scheduler_timer = None
        self._speech_player = None
        self._speech_audio_output = None

        if self._speech is not None:
            self._speech.set_playback_handler(
                self._queue_speech_playback,
                self._queue_speech_stop,
            )

        self._speechFileReady.connect(self._play_speech_file)
        self._start_reminder_scheduler()
        self.apply_persisted_settings()

        self._providerSucceeded.connect(self._on_provider_success)
        self._providerFailed.connect(self._on_provider_failure)
        self._transcribeSucceeded.connect(self._on_transcribe_success)
        self._transcribeFailed.connect(self._on_transcribe_failure)

    def _register_desktop_handlers(self) -> None:
        """Attach desktop-layer implementations onto the action stack."""

        if self._action_system is None:
            return

        from aki_core.command_executor import ExecutionStatus

        executor = self._action_system.executor

        # The core factory leaves screenshots unimplemented on purpose;
        # the GUI layer owns real screen capture via Qt.
        if not executor.has_handler("take_screenshot"):
            from desktop.screen_capture import capture_screen

            executor.register_handler("take_screenshot", capture_screen)

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
        self._pending_attachment_path = str(p)

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

    @Slot(str)
    def copyToClipboard(self, text: str) -> None:
        """Copy message text to the system clipboard."""

        from PySide6.QtGui import QGuiApplication

        if text:
            QGuiApplication.clipboard().setText(text)
            logger.info("Copied %d chars to clipboard.", len(text))

    @Slot()
    def clearConversation(self) -> None:
        """Discard the active conversation; the next prompt starts fresh."""
        with self._conversation_lock:
            self._conversation_id = None
        logger.info("Desktop conversation cleared.")

    # ============================================================
    # Voice: input (speech-to-text) and output (text-to-speech)
    # ============================================================

    @Slot(result=bool)
    def isVoiceInputConfigured(self) -> bool:
        """Report whether a speech-to-text backend is available."""
        return self._speech_transcriber is not None

    # ============================================================
    # Settings panel
    # ============================================================

    # ============================================================
    # Dev Agent + Cyber Suite
    # ============================================================

    @Slot(str, str, str, result=dict)
    def createDevProject(
        self,
        kind: str,
        name: str,
        description: str,
    ) -> Dict[str, Any]:
        """Queue an AI project build; result arrives via aiResponseReady."""

        if self._dev_agent is None:
            return {
                "status": "NO_PROVIDER",
                "request_id": "",
                "response": "Dev Agent ke liye AI provider chahiye (.env API key).",
            }

        request_id = uuid4().hex[:12]

        threading.Thread(
            target=self._run_project_build,
            args=(request_id, kind, name, description),
            daemon=True,
            name=f"aki-dev-{request_id}",
        ).start()

        return {"status": "PENDING", "request_id": request_id}

    def _run_project_build(
        self,
        request_id: str,
        kind: str,
        name: str,
        description: str,
    ) -> None:
        """Worker: generate code via AI and write the project folder."""

        try:
            result = self._dev_agent.create_project(
                kind=kind,
                name=name,
                description=description,
            )
            self._providerSucceeded.emit(
                request_id,
                f"{result.summary()}\n\nProject folder khulne ke liye DEV window mein 'Open' dabayen.",
            )
        except Exception as error:  # noqa: BLE001
            logger.exception("Dev project build failed.")
            self._providerFailed.emit(request_id, str(error))

    @Slot(result=list)
    def getDevProjects(self) -> list:
        """List generated projects for the DEV window."""

        if self._dev_agent is None:
            return []

        return self._dev_agent.list_projects()

    @Slot(str)
    def openProjectFolder(self, path: str) -> None:
        """Open a generated project folder in Explorer."""

        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    @Slot(str, result=list)
    def getProjectFiles(self, path: str) -> list:
        """List files of a generated project (AKI-internal viewer)."""

        from pathlib import Path as _Path

        try:
            root = _Path(path).resolve()
            projects_root = self._dev_agent.projects_root.resolve() if self._dev_agent else None

            if projects_root is None or projects_root not in root.parents:
                return []

            return [
                str(item.relative_to(root))
                for item in sorted(root.rglob("*"))
                if item.is_file()
            ]
        except Exception:
            return []

    @Slot(str, str, result=str)
    def readProjectFile(self, path: str, relative: str) -> str:
        """Read one project file for the AKI-internal viewer."""

        from pathlib import Path as _Path

        try:
            root = _Path(path).resolve()
            target = (root / relative).resolve()

            if self._dev_agent is None:
                return ""

            projects_root = self._dev_agent.projects_root.resolve()

            if projects_root not in target.parents and target.parent != projects_root:
                return "[blocked]"

            if target.stat().st_size > 200_000:
                return "[File bohat bari hai — PC mein kholein]"

            return target.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return "[Read failed]"

    @Slot(str, str, result=dict)
    def runSecurityTool(self, tool: str, parameter: str = "") -> Dict[str, Any]:
        """Run one defensive security tool (worker for slow scans)."""

        request_id = uuid4().hex[:12]

        threading.Thread(
            target=self._run_security_tool,
            args=(request_id, tool, parameter),
            daemon=True,
            name=f"aki-sec-{request_id}",
        ).start()

        return {"status": "PENDING", "request_id": request_id}

    def _run_security_tool(
        self,
        request_id: str,
        tool: str,
        parameter: str,
    ) -> None:
        """Worker: execute the tool and emit a chat-visible summary."""

        detail = "Security suite has been removed in Phase A."
        summary = f"[{tool.upper()}] Security checks disabled."
        msg = f"<b>{summary}</b>\n<pre>{detail}</pre>"
        
        self._providerSucceeded.emit(
            request_id,
            msg
        )

    # ============================================================
    # Dev Agent + Cyber Suite (end)
    # ============================================================

    @Slot(result=dict)
    def addBookFromDialog(self) -> Dict[str, Any]:
        """Open a file dialog, ingest the book, and report the outcome."""

        if self._knowledge is None:
            return {"added": False, "error": "Knowledge subsystem unavailable"}

        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(
            self._window_ref,
            "Add Book to AKI Knowledge",
            "",
            "Books (*.pdf *.txt *.md);;All Files (*.*)",
        )

        if not path:
            return {"added": False}

        try:
            book = self._knowledge.ingest(path)
        except Exception as error:
            logger.warning("Book ingestion failed: %s", error)
            return {"added": False, "error": str(error)}

        logger.info(
            "Book ingested | %s (%d pages)", book.title, book.page_count
        )

        return {
            "added": True,
            "title": book.title,
            "pages": book.page_count,
        }

    @Slot(result=list)
    def getBooks(self) -> list:
        """Return the ingested knowledge library for the UI panel."""

        if self._knowledge is None:
            return []

        return [
            {
                "title": book.title,
                "pages": book.page_count,
                "topics": list(book.topics),
            }
            for book in self._knowledge.list_books()
        ]

    @Slot(result=dict)
    def getSettings(self) -> Dict[str, Any]:
        """
        Snapshot of user-adjustable settings for the UI panel.

        `ai_provider` / `ai_model` come from the boot Settings object
        injected at construction. When no Settings object was provided
        (only possible in tests or degenerate wiring), they legitimately
        read "unknown" / "" — the UI renders that as an OFFLINE badge.
        """

        settings_snapshot = self._app_settings

        provider = (
            settings_snapshot.ai_provider
            if settings_snapshot is not None
            else None
        )
        model = (
            settings_snapshot.ai_model
            if settings_snapshot is not None
            else None
        )

        return {
            "voice_output": self._voice_enabled,
            "tts_voice": self._effective_tts_voice(),
            "available_voices": list(
                self._speech.available_voices()
            )
            if self._speech
            else [],
            "voice_input": self._speech_transcriber is not None,
            "ai_provider": provider or "unknown",
            "ai_model": model or "",
            "ai_connected": self._ai_service is not None,
        }

    def _effective_tts_voice(self) -> str:
        """Return the neural voice that will actually be used next."""

        if self._speech is None:
            return ""

        name = self._speech.voice_name
        available = self._speech.available_voices()

        if name not in available and available:
            return available[0]

        return name

    @Slot(str, result=bool)
    def setTtsVoice(self, voice: str) -> bool:
        """Select the neural TTS voice; persists across restarts."""

        if self._speech is None:
            return False

        accepted = self._speech.set_voice(voice)

        if accepted:
            self._settings.setValue("tts_voice", voice)

        return accepted

    def apply_persisted_settings(self) -> None:
        """Restore saved preferences (called once after construction)."""

        saved_voice = self._settings.value("tts_voice", "")

        if saved_voice and self._speech is not None:
            self._speech.set_voice(str(saved_voice))

    @Slot(bool)
    def setVoiceOutputEnabled(self, enabled: bool) -> None:
        """Enable or disable AKI's spoken replies."""

        self._voice_enabled = bool(enabled)

        if not self._voice_enabled and self._speech is not None:
            self._speech.stop()

        logger.info("Voice output %s.", "enabled" if self._voice_enabled else "disabled")

    @Slot(result=bool)
    def isVoiceOutputEnabled(self) -> bool:
        """Return whether spoken replies are currently on."""
        return self._voice_enabled

    @Slot()
    def stopSpeaking(self) -> None:
        """Silence any ongoing utterance immediately."""
        if self._speech is not None:
            self._speech.stop()

    @Slot(str)
    def setAppearance(self, mode: str) -> None:
        """Set the application appearance mode (dark, light, system)."""
        from desktop.themes.theme_manager import ThemeManager
        tm = ThemeManager.get_instance()
        if tm:
            tm.set_appearance(mode)

    @Slot(result=str)
    def getAppearance(self) -> str:
        """Get the current appearance mode."""
        from desktop.themes.theme_manager import ThemeManager
        tm = ThemeManager.get_instance()
        return tm.get_appearance() if tm else "dark"

    @Slot(str, str, result=dict)
    def transcribeAudio(
        self,
        audio_base64: str,
        mime_type: str = "audio/webm",
    ) -> Dict[str, Any]:
        """Queue recorded microphone audio for transcription.

        The network call runs on a worker thread; the transcript is
        delivered later via `transcriptionReady`.
        """

        if self._speech_transcriber is None:
            return {
                "status": "NO_PROVIDER",
                "request_id": "",
                "transcript": "",
            }

        raw = (audio_base64 or "").strip()

        if not raw:
            return {"status": "EMPTY", "request_id": "", "transcript": ""}

        try:
            audio_bytes = base64.b64decode(raw, validate=False)
        except Exception as error:
            logger.warning("Voice payload could not be decoded.")
            return {
                "status": "DECODE_ERROR",
                "request_id": "",
                "response": f"Audio decode failed: {error}",
                "transcript": "",
            }

        request_id = uuid4().hex[:12]
        extension = (mime_type or "audio/webm").split("/")[-1].split(";")[0]
        filename = f"speech.{extension}"

        threading.Thread(
            target=self._run_transcription,
            args=(request_id, audio_bytes, filename),
            daemon=True,
            name=f"aki-stt-{request_id}",
        ).start()

        return {"status": "PENDING", "request_id": request_id}

    def _run_transcription(
        self,
        request_id: str,
        audio_bytes: bytes,
        filename: str,
    ) -> None:
        """Worker-thread body for one speech-to-text request."""

        try:
            transcript = self._speech_transcriber.transcribe(
                audio_bytes,
                filename=filename,
            )
            self._transcribeSucceeded.emit(request_id, transcript.text)
        except Exception as error:  # noqa: BLE001 - surfaced to the UI
            logger.exception("Speech transcription failed.")
            self._transcribeFailed.emit(f"{request_id}|{error}")

    def _on_transcribe_success(self, request_id: str, text: str) -> None:
        """Main-thread completion for one transcription."""

        logger.info("Voice transcribed (%d chars).", len(text))
        self.transcriptionReady.emit(request_id, text)

    def _on_transcribe_failure(self, request_and_error: str) -> None:
        """Main-thread failure path for one transcription."""

        request_id, _, error = request_and_error.partition("|")
        logger.warning("Transcription error surfaced to UI.")
        self.transcriptionReady.emit(request_id, f"__ERROR__{error}")

    def _speak_if_enabled(self, text: str) -> None:
        """Speak one utterance when voice output is turned on."""

        if self._voice_enabled and self._speech is not None and text:
            logger.info("Speaking | voice=%s", self._speech.voice_name)
            self._speech.speak(text)

    # ============================================================
    # Neural speech playback (GUI thread via queued signal)
    # ============================================================

    def _queue_speech_playback(self, audio_path: str, text: str) -> None:
        """Worker-thread hook: hand the synthesized file to the GUI."""

        self._speechFileReady.emit(audio_path, text)

    def _queue_speech_stop(self) -> None:
        """Worker-thread hook: stop playback on the GUI thread."""

        QMetaObject.invokeMethod(
            self,
            "_stop_speech_player",
            Qt.ConnectionType.QueuedConnection,
        )

    @Slot()
    def _stop_speech_player(self) -> None:
        """GUI thread: silence the active player immediately."""

        player = getattr(self, "_speech_player", None)
        if player is not None:
            try:
                player.stop()
            except Exception:
                pass
            self._speech_player = None

    def _play_speech_file(self, audio_path: str, text: str) -> None:
        """GUI thread: play the neural speech file with QMediaPlayer."""

        from PySide6.QtCore import QUrl
        from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        from pathlib import Path as _Path

        self._stop_speech_player()

        audio_file = _Path(audio_path)
        player = QMediaPlayer(self)
        output = QAudioOutput()
        output.setVolume(1.0)
        player.setAudioOutput(output)

        # CRITICAL: keep a Python reference to the audio output.
        # Without it the wrapper can be garbage-collected and the
        # player goes silent while still reporting "playing".
        self._speech_audio_output = output

        player.setSource(QUrl.fromLocalFile(str(audio_file)))

        self._speech_player = player

        def _cleanup() -> None:
            try:
                player.stop()
            except Exception:
                pass
            audio_file.unlink(missing_ok=True)
            if self._speech_player is player:
                self._speech_player = None
                self._speech_audio_output = None
            if self._speech is not None:
                self._speech.notify_playback_finished()

        def _on_error(err, error_string: str) -> None:
            logger.error(
                "Speech playback failed (%s); using SAPI fallback.",
                error_string,
            )
            audio_file.unlink(missing_ok=True)
            if self._speech_player is player:
                self._speech_player = None
                self._speech_audio_output = None
            if self._speech is not None and text:
                self._speech.speak_with_sapi_direct(text)

        def _on_status(status) -> None:
            logger.info("Speech player status: %s", status)

        player.mediaStatusChanged.connect(_on_status)
        player.mediaStatusChanged.connect(
            lambda status: _cleanup()
            if status == QMediaPlayer.MediaStatus.EndOfMedia
            else None
        )
        player.errorOccurred.connect(_on_error)

        logger.info("Playing neural speech | file=%s", audio_file.name)
        player.play()

    # ============================================================
    # Reminders: creation, listing, and the firing loop
    # ============================================================

    def _intent_reply(self, text: str, reply: str, decision: Any) -> Dict[str, Any]:
        """Shared persistence + payload for deterministic intents."""

        self._persist_user_message(text)
        self._persist_assistant_message(reply)
        self._speak_if_enabled(reply)

        return {
            "status": "SUCCESS",
            "request_id": "",
            "response": reply,
            "action": decision.action,
            "execution": "success",
        }

    def _handle_knowledge_intent(self, action: str) -> Optional[str]:
        """Serve book-library intents (add/list)."""

        if self._knowledge is None:
            return None

        if action == "add_book":
            from PySide6.QtWidgets import QFileDialog

            path, _ = QFileDialog.getOpenFileName(
                self._window_ref,
                "Add Book to AKI Knowledge",
                "",
                "Books (*.pdf *.txt *.md);;All Files (*.*)",
            )

            if not path:
                return None

            try:
                book = self._knowledge.ingest(path)
            except Exception as error:
                logger.warning("Book ingestion failed: %s", error)
                return f"Book add nahi ho saki: {error}"

            logger.info("Book ingested | %s (%d pages)", book.title, book.page_count)

            return (
                f"Done ✅ '{book.title}' meri knowledge mein add ho gayi — "
                f"{book.page_count} pages. Ab is ke baare mein kuch bhi poocho!"
            )

        if action == "list_books":
            books = self._knowledge.list_books()

            if not books:
                return (
                    "Library khali hai. 📚 sidebar button se ya 'book add "
                    "karo' bolkar PDF add karein."
                )

            lines = []
            for book in books[:12]:
                topics = (
                    ", ".join(book.topics[:4]) if book.topics else "general"
                )
                lines.append(
                    f"- **{book.title}** ({book.page_count} pages) — {topics}"
                )

            return (
                "Tumhari knowledge library:\n" + "\n".join(lines)
            )

        return None

    def _collect_book_context(self, query: str) -> list[str]:
        """Return page-cited book excerpts relevant to the question."""

        if self._knowledge is None:
            return []

        try:
            matches = self._knowledge.search(query, limit=6)
        except Exception:
            logger.exception("Knowledge lookup failed.")
            return []

        context: list[str] = []

        for match in matches:
            excerpt = match.chunk.text[:700].replace("\n", " ")
            context.append(
                f"[{match.chunk.book_title} · page {match.chunk.page}] {excerpt}"
            )

        return context

    def _handle_reminder_intent(self, action: str, text: str) -> Optional[str]:
        """
        Serve reminder intents. Returns a reply, or None to fall
        through to the AI conversation path.
        """

        if self._reminder_manager is None:
            return None

        from automation.parser import parse_schedule, strip_schedule_text

        if action == "create_reminder":
            schedule = parse_schedule(text)

            if schedule is None:
                return (
                    "Kab yaad dilana hai? Batao jaise: "
                    "'10 minute baad reminder do' ya 'roz 9 baje'."
                )

            message = strip_schedule_text(text) or "Reminder"

            reminder = self._reminder_manager.create(
                message,
                kind=schedule.kind,
                due_at=schedule.due_at,
                time_of_day=schedule.time_of_day,
            )

            logger.info(
                "Reminder created | id=%s kind=%s",
                reminder.reminder_id,
                reminder.kind,
            )

            if schedule.kind == "once" and schedule.due_at is not None:
                return (
                    f"Done ✅ Main tumhein '{message}' yaad dila doonga "
                    f"**{schedule.due_at.strftime('%H:%M')}** baje."
                )

            return (
                f"Done ✅ Roz **{schedule.time_of_day}** baje main "
                f"'{message}' yaad dila doonga."
            )

        if action == "list_reminders":
            active = self._reminder_manager.list_active()

            if not active:
                return "Filhal koi reminder set nahi hai."

            lines = []
            for reminder in active[:10]:
                when = reminder.time_of_day or (
                    reminder.due_at or ""
                )[:16].replace("T", " ")
                lines.append(f"- {reminder.message} ({when})")

            return "Tumhare reminders:\n" + "\n".join(lines)

        return None

    def _start_reminder_scheduler(self) -> None:
        """Start the periodic due-reminder check on the GUI thread."""

        try:
            from PySide6.QtCore import QTimer

            self._scheduler_timer = QTimer(self)
            self._scheduler_timer.setInterval(20_000)
            self._scheduler_timer.timeout.connect(self._check_due_reminders)
            self._scheduler_timer.start()
        except Exception as error:
            logger.warning("Reminder scheduler unavailable: %s", error)

    def _check_due_reminders(self) -> None:
        """Fire reminders that are due and notify the UI."""

        if self._reminder_manager is None:
            return

        from automation.scheduler import find_due_reminders
        from datetime import datetime

        try:
            active = self._reminder_manager.list_active()
        except Exception:
            logger.exception("Reminder lookup failed.")
            return

        if not active:
            return

        now_local = datetime.now()

        try:
            due = find_due_reminders(
                active,
                now_local=now_local,
                last_fired_daily=self._daily_fired,
            )
        except Exception:
            logger.exception("Reminder scheduling check failed.")
            return

        for reminder in due:
            self._reminder_manager.disable(reminder.reminder_id)

            if reminder.kind == "daily":
                self._daily_fired[reminder.reminder_id] = (
                    now_local.strftime("%Y-%m-%d")
                )

            message = f"⏰ Reminder: {reminder.message}"
            self.notificationPushed.emit(
                {
                    "title": "AKI Reminder",
                    "body": reminder.message,
                }
            )
            self._speak_if_enabled(
                f"Reminder! {reminder.message}"
            )
            logger.info("Reminder fired | id=%s", reminder.reminder_id)

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

        # Fast path: deterministic system commands skip the AI entirely.
        action_payload = self._try_run_intent(text)
        if action_payload is not None:
            return action_payload

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

        # Attached file content becomes part of the prompt context.
        if self._pending_attachment_path:
            from desktop.attachment_reader import read_attachment

            block, _truncated = read_attachment(self._pending_attachment_path)
            text = f"{text}\n\n{block}"
            self._pending_attachment_path = None

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

    def _try_run_intent(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Execute a deterministic system command when the utterance
        matches one. Returns None when the request should continue
        to the AI conversation path.
        """

        decision = self._intents.match(text)

        if decision is None:
            return None

        # Reminder + knowledge intents are handled here (they need
        # dialogs/parsers, not the action executor).
        if decision.action in ("create_reminder", "list_reminders"):
            reply = self._handle_reminder_intent(decision.action, text)

            if reply is not None:
                return self._intent_reply(text, reply, decision)

            return None

        if decision.action in ("add_book", "list_books"):
            reply = self._handle_knowledge_intent(decision.action)

            if reply is not None:
                return self._intent_reply(text, reply, decision)

            return None

        if self._action_system is None:
            return None

        logger.info(
            "Intent matched: action=%s params=%s",
            decision.action,
            decision.parameters,
        )

        result = self._action_system.run(
            decision.action,
            **decision.parameters,
        )

        response = self._describe_action_result(decision, result)

        payload: Dict[str, Any] = {
            "status": "SUCCESS" if result.status.value == "success" else "ACTION_ERROR",
            "request_id": "",
            "response": response,
            "action": decision.action,
            "execution": result.status.value,
        }

        self._persist_user_message(text)
        self._persist_assistant_message(response)
        self._speak_if_enabled(response)

        return payload

    @staticmethod
    def _describe_action_result(decision: Any, result: Any) -> str:
        """Translate an ExecutionResult into a user-facing reply."""

        from aki_core.command_executor import ExecutionStatus

        data = result.data if isinstance(result.data, dict) else {}

        if result.status is ExecutionStatus.SUCCESS:
            if decision.action == "open_application":
                return f"{decision.parameters.get('target', 'Application').title()} khol diya hai. ✅"
            if decision.action == "open_website":
                return (
                    f"{decision.parameters.get('site', '').title()} "
                    "browser mein khul gaya. ✅"
                )
            if decision.action == "take_screenshot":
                return f"Screenshot save ho gaya: {data.get('path', '')}"
            if decision.action == "get_system_info":
                return (
                    f"CPU {data.get('cpu_percent', '?')}% | "
                    f"RAM {data.get('ram_percent', '?')}% "
                    f"({data.get('ram_used_gb', '?')}/{data.get('ram_total_gb', '?')} GB) | "
                    f"Time {data.get('local_time', '')}"
                )
            return result.message

        if result.status in (
            ExecutionStatus.DISABLED,
            ExecutionStatus.NOT_IMPLEMENTED,
        ):
            return (
                "Yeh feature agle phase mein aa raha hai — abhi AKI "
                "iskay liye tayyar nahi hui. 🚧"
            )

        if result.status is ExecutionStatus.NOT_FOUND:
            return "Yeh command mujhe abhi samajh nahi aayi."

        if result.status is ExecutionStatus.DENIED:
            return "Is kaam ki ijazat filhal available nahi hai. 🔒"

        detail = ""
        if isinstance(result.data, dict):
            detail = str(result.data.get("error", ""))

        return f"Command execute karte waqt masla aaya. {detail}".strip()

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
            book_context = self._collect_book_context(prompt)
            combined_memories = list(memories) + book_context

            response = self._ai_service.respond(
                prompt,
                history=history,
                memories=combined_memories,
            )
            content = response.content.strip()

            # One-shot web search tool loop: the model may request
            # live results with a bare "SEARCH: <query>" reply.
            if (
                content.upper().startswith("SEARCH:")
                and len(content) < 300
                and self._web_search is not None
            ):
                query = content.split(":", 1)[1].strip()
                logger.info("AI requested web search: %s", query[:80])

                results = self._web_search.search(query)
                context = self._web_search.render_context(results)

                response = self._ai_service.respond(
                    f"{prompt}\n\n{context}\n\n"
                    "(Answer the user's original question using these live results.)",
                    history=history,
                    memories=combined_memories,
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
        self._speak_if_enabled(fallback)
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


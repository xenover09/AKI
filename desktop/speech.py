"""
AKI Text-to-Speech Service.

Speaks AKI's replies aloud with a natural Urdu/Hindi-accented neural
voice (Microsoft Edge TTS — free, no API key). When offline or when
the neural engine fails, AKI falls back to the Windows built-in SAPI
voice so speech never silently disappears.

Neural synthesis runs in a worker thread; playback happens through
Qt Multimedia on the GUI thread. The desktop UI never blocks while
AKI is talking.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Final

from logs.logger import get_logger

logger = get_logger("desktop.speech")

_MAX_SPEECH_CHARS: Final[int] = 600
_CREATION_NO_WINDOW: Final[int] = 0x08000000  # CREATE_NO_WINDOW
_SYNTH_RETRIES: Final[int] = 3
_SYNTH_RETRY_DELAY_SECONDS: Final[float] = 1.5

# Preferred neural voices, in priority order.
_NEURAL_VOICES: Final[tuple[str, ...]] = (
    "ur-PK-AsadNeural",      # Urdu (Pakistan) — male
    "ur-PK-UzmaNeural",      # Urdu (Pakistan) — female
    "ur-IN-GulNeural",       # Urdu (India) — male
    "hi-IN-MadhurNeural",    # Hindi — male
    "hi-IN-SwaraNeural",     # Hindi — female
)

# SAPI fallback voices for South-Asian accent, if installed.
_SAPI_VOICE_CANDIDATES: Final[tuple[str, ...]] = (
    "Microsoft Hemant Desktop",
    "Microsoft Kalpana Desktop",
    "Microsoft Hemant",
    "Microsoft Kalpana",
)

_VOICE_PREFERENCE_ENV: Final[str] = "AKI_TTS_VOICE"


class SpeechService:
    """
    Speaks text through the best available voice.

    Responsibilities:
        - Sanitize text before synthesis.
        - Prefer a neural Urdu/Hindi voice; fall back to SAPI.
        - Speak asynchronously so callers never block.
        - Track speaking state for UI effects (orb animation).
        - Stop an utterance mid-sentence when asked.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._speaking = False
        self._process: subprocess.Popen | None = None
        self._neural_voice: str | None = None

        # Set by the bridge: callback(path, text) that plays audio on
        # the GUI thread (via a queued Qt signal).
        self._playback_handler = None
        self._playback_stop_handler = None

    def notify_playback_finished(self) -> None:
        """Called by the bridge when Qt playback completes."""

        with self._lock:
            self._speaking = False
            self._process = None

        callback = self._on_playback_finished
        if callback:
            try:
                callback()
            except Exception:
                pass

    def speak_with_sapi_direct(self, text: str) -> None:
        """Force the offline SAPI voice (used when neural playback fails)."""

        self.stop()

        with self._lock:
            self._speaking = True

        logger.info("Speaking with fallback engine | engine=sapi")
        self._speak_with_sapi(self._sanitize(text))

    def set_playback_handler(self, handler, stop_handler=None) -> None:
        """Register callbacks: handler(path, text) plays audio; stop_handler() silences it."""

        self._playback_handler = handler
        self._playback_stop_handler = stop_handler

    def set_playback_finished_callback(self, callback) -> None:
        """Register a zero-argument callable invoked when playback ends."""

        self._on_playback_finished = callback

    def notify_playback_finished(self) -> None:
        """Called by the bridge when the player finishes; resets state."""

        with self._lock:
            self._speaking = False
            self._process = None

    @property
    def is_speaking(self) -> bool:
        """Return whether an utterance is currently being spoken."""

        with self._lock:
            return self._speaking

    @property
    def voice_name(self) -> str:
        """Return the active voice description."""

        if self._neural_voice:
            return self._neural_voice

        return "windows-sapi"

    def speak(self, text: str) -> None:
        """
        Speak one utterance asynchronously.

        Long text is truncated to keep replies snappy; markdown and
        shell-hostile characters are stripped.
        """

        clean = self._sanitize(text)

        if not clean:
            return

        self.stop()

        with self._lock:
            self._speaking = True

        threading.Thread(
            target=self._synthesize_and_play,
            args=(clean,),
            daemon=True,
            name="aki-tts",
        ).start()

    def stop(self) -> None:
        """Silence any ongoing utterance immediately."""

        if self._playback_stop_handler is not None:
            try:
                self._playback_stop_handler()
            except Exception:
                pass

        with self._lock:
            process = self._process
            self._process = None
            self._speaking = False

        if process is not None and process.poll() is None:
            try:
                process.kill()
            except Exception:
                logger.debug("SAPI process already gone.")

    # ============================================================
    # Neural engine (Edge TTS)
    # ============================================================

    def _synthesize_and_play(self, text: str) -> None:
        """Worker: synthesize with a neural voice, then hand to the player."""

        audio_file: Path | None = None
        last_error: Exception | None = None

        # Neural synthesis depends on the network; retry before
        # degrading to the robotic SAPI fallback.
        for attempt in range(1, _SYNTH_RETRIES + 1):
            if not self._speaking:
                return

            try:
                audio_file = self._synthesize_neural(text)
                break
            except Exception as error:
                last_error = error
                logger.warning(
                    "Neural synthesis attempt %d/%d failed: %s",
                    attempt,
                    _SYNTH_RETRIES,
                    error,
                )
                if attempt < _SYNTH_RETRIES:
                    threading.Event().wait(_SYNTH_RETRY_DELAY_SECONDS)

        if audio_file is not None and self._speaking:
            if self._playback_handler is not None:
                try:
                    self._playback_handler(str(audio_file), text)
                    return
                except Exception as error:
                    logger.warning("Playback hand-off failed: %s", error)

            _delete_quietly(audio_file)

        # Fallback: offline Windows voice.
        if self._speaking:
            logger.warning(
                "Neural TTS unavailable after retries (%s); using SAPI.",
                last_error,
            )
            logger.info("Speaking with fallback engine | engine=sapi")
            self._speak_with_sapi(text)

    def _synthesize_neural(self, text: str) -> Path:
        """Generate speech audio with an Edge neural voice."""

        import asyncio

        import edge_tts

        voice = self._preferred_voice()

        async def _generate() -> bytes:
            communicate = edge_tts.Communicate(text, voice)
            chunks: list[bytes] = []

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    chunks.append(chunk["data"])

            return b"".join(chunks)

        audio = asyncio.run(_generate())

        if not audio:
            raise RuntimeError("Neural synthesis returned no audio.")

        handle = tempfile.NamedTemporaryFile(
            prefix="aki_tts_",
            suffix=".mp3",
            delete=False,
        )
        handle.write(audio)
        handle.close()

        logger.info("Neural speech synthesized | voice=%s", voice)
        return Path(handle.name)

    def _preferred_voice(self) -> str:
        """Resolve the neural voice, honoring an optional env override."""

        if self._neural_voice:
            return self._neural_voice

        import os

        override = os.getenv(_VOICE_PREFERENCE_ENV, "").strip()

        if override:
            self._neural_voice = override
            return override

        for voice in _NEURAL_VOICES:
            self._neural_voice = voice
            return voice

        self._neural_voice = _NEURAL_VOICES[0]
        return self._neural_voice

    # ============================================================
    # Fallback engine (Windows SAPI)
    # ============================================================

    def _speak_with_sapi(self, text: str) -> None:
        """Offline fallback using the Windows built-in voice."""

        with self._lock:
            self._process = self._spawn_sapi(text)

        threading.Thread(
            target=self._wait_for_sapi_finish,
            daemon=True,
            name="aki-tts-sapi-wait",
        ).start()

    def _spawn_sapi(self, text: str) -> subprocess.Popen | None:
        """Start the detached PowerShell SAPI voice process."""

        voice_selector = "".join(
            f"try{{if(-not $selected){{try{{if($s.GetVoices() | Where-Object {{$_.Name -like '*{name}*'}}){{$s.SelectVoice('{name}');$selected=$true}}}}catch{{}}}}}}catch{{}};"
            for name in _SAPI_VOICE_CANDIDATES
        )

        script = (
            "Add-Type -AssemblyName System.Speech;"
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            "$selected=$false;"
            f"{voice_selector}"
            f"$s.Speak('{self._escape_ps(text)}')"
        )

        try:
            return subprocess.Popen(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    script,
                ],
                creationflags=_CREATION_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as error:
            logger.warning("SAPI speech unavailable: %s", error)
            with self._lock:
                self._speaking = False
            return None

    def _wait_for_sapi_finish(self) -> None:
        """Clear the speaking flag once the SAPI process exits."""

        with self._lock:
            process = self._process

        if process is not None:
            try:
                process.wait(timeout=120)
            except Exception:
                pass

        with self._lock:
            if self._process is process:
                self._process = None
                self._speaking = False

        callback = self._on_playback_finished
        if callback:
            try:
                callback()
            except Exception:
                pass

    # ============================================================
    # Text hygiene
    # ============================================================

    def _sanitize(self, text: str) -> str:
        """Strip markdown noise and cap length for natural speech."""

        clean = re.sub(r"[*_`#>]+", "", text or "")
        clean = re.sub(r"https?://\S+", "link", clean)
        clean = re.sub(r"\s+", " ", clean).strip()

        return clean[:_MAX_SPEECH_CHARS]

    @staticmethod
    def _escape_ps(text: str) -> str:
        """Escape single quotes for a PowerShell single-quoted string."""

        return text.replace("'", "''")


def _delete_quietly(path: Path) -> None:
    """Remove a temp file without raising."""

    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass


__all__ = [
    "SpeechService",
]

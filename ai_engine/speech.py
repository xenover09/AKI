"""
AKI Speech Transcription.

Speech-to-text through any OpenAI-compatible audio transcription
endpoint (Groq Whisper, OpenAI Whisper). Audio arrives as raw bytes
from the desktop layer; this module owns only the API contract.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from .provider import AIConfigurationError, AIProviderError


_DEFAULT_TIMEOUT_SECONDS = 30.0
_MAX_AUDIO_BYTES = 25 * 1024 * 1024  # Provider-side limit.


@dataclass(frozen=True)
class TranscriptResult:
    """Normalized transcription outcome."""

    text: str
    language: str | None = None
    duration_seconds: float | None = None


class SpeechTranscriber:
    """
    Turns recorded microphone audio into text.

    Responsibilities:
        - Validate incoming audio payloads before upload.
        - Post multipart audio to the transcription endpoint.
        - Normalize the reply into `TranscriptResult`.
        - Translate transport/API failures into AKI's error hierarchy.
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str = "whisper-large-v3-turbo",
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        client: httpx.Client | None = None,
    ) -> None:
        if not isinstance(base_url, str) or not base_url.strip():
            raise AIConfigurationError(
                "base_url must be a non-empty string."
            )

        if not isinstance(api_key, str) or not api_key.strip():
            raise AIConfigurationError(
                "api_key must be a non-empty string."
            )

        if not isinstance(model, str) or not model.strip():
            raise AIConfigurationError(
                "model must be a non-empty string."
            )

        self._base_url = base_url.strip().rstrip("/")
        self._api_key = api_key.strip()
        self._model = model.strip()
        self._timeout_seconds = float(timeout_seconds)
        self._client = client
        self._owns_client = client is None

    @property
    def model(self) -> str:
        """Return the configured transcription model."""

        return self._model

    def transcribe(
        self,
        audio_bytes: bytes,
        *,
        filename: str = "speech.webm",
        language: str | None = None,
    ) -> TranscriptResult:
        """
        Transcribe one recording.

        Args:
            audio_bytes: Raw audio file content (webm/ogg/wav/mp3).
            filename: Name describing the container format.
            language: Optional ISO-639-1 hint such as ``"ur"`` or ``"en"``.

        Returns:
            A normalized transcript.

        Raises:
            AIProviderError: On transport failure or non-2xx reply.
        """

        self._validate_audio(audio_bytes)

        try:
            response = self._http_client().post(
                f"{self._base_url}/audio/transcriptions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                files={"file": (filename, audio_bytes)},
                data=self._form_fields(language),
            )
        except httpx.HTTPError as error:
            raise AIProviderError(
                f"Could not reach speech endpoint: {error}"
            ) from error

        if response.status_code >= 400:
            raise AIProviderError(
                f"Speech endpoint returned {response.status_code}: "
                f"{self._error_detail(response)}",
                status_code=response.status_code,
            )

        body = response.json()

        return TranscriptResult(
            text=str(body.get("text", "")).strip(),
            language=body.get("language"),
            duration_seconds=body.get("duration"),
        )

    def close(self) -> None:
        """Close the HTTP client when this transcriber created it."""

        if self._owns_client and self._client is not None:
            self._client.close()

        self._client = None
        self._owns_client = True

    # ============================================================
    # Internals
    # ============================================================

    def _validate_audio(self, audio_bytes: bytes) -> None:
        """Reject empty or oversized uploads before hitting the wire."""

        if not isinstance(audio_bytes, bytes) or len(audio_bytes) == 0:
            raise AIProviderError(
                "Audio payload is empty; nothing to transcribe."
            )

        if len(audio_bytes) > _MAX_AUDIO_BYTES:
            raise AIProviderError(
                "Audio payload exceeds the 25 MB limit."
            )

    def _http_client(self) -> httpx.Client:
        """Return the injected test client, creating one on first use."""

        if self._client is None:
            self._client = httpx.Client(
                timeout=self._timeout_seconds,
            )

        return self._client

    def _form_fields(self, language: str | None) -> dict[str, str]:
        """Build the multipart form fields."""

        fields: dict[str, str] = {
            "model": self._model,
            "response_format": "verbose_json",
        }

        if language:
            fields["language"] = language

        return fields

    @staticmethod
    def _error_detail(response: httpx.Response) -> str:
        """Extract a short error message from a failed reply."""

        try:
            detail = response.json()["error"]["message"]
        except Exception:
            detail = response.text[:200]

        return detail


__all__ = [
    "SpeechTranscriber",
    "TranscriptResult",
]

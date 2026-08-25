"""Unit tests for AKI's speech transcription backend."""

from __future__ import annotations

import json

import httpx
import pytest

from ai_engine.provider import AIConfigurationError, AIProviderError
from ai_engine.speech import SpeechTranscriber


def make_transcriber(
    handler: httpx.MockTransport.HandlerType,
) -> SpeechTranscriber:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return SpeechTranscriber(
        base_url="http://testserver/v1",
        api_key="test-key",
        model="whisper-test",
        client=client,
    )


class TestConfiguration:
    """Constructor validation."""

    def test_rejects_missing_base_url(self) -> None:
        with pytest.raises(AIConfigurationError):
            SpeechTranscriber(base_url="", api_key="k")

    def test_rejects_missing_api_key(self) -> None:
        with pytest.raises(AIConfigurationError):
            SpeechTranscriber(base_url="http://x/v1", api_key="")


class TestTranscription:
    """Successful and failing API round-trips."""

    def test_success_returns_normalized_transcript(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            body = request.content

            assert b'name="model"' in body
            assert b"whisper-test" in body
            assert request.headers["Authorization"] == "Bearer test-key"
            assert request.url.path.endswith("/audio/transcriptions")

            return httpx.Response(
                200,
                json={
                    "text": "mera naam Aether hai",
                    "language": "ur",
                    "duration": 2.4,
                },
            )

        transcriber = make_transcriber(handler)
        result = transcriber.transcribe(b"fake-audio-bytes", filename="speech.webm")

        assert result.text == "mera naam Aether hai"
        assert result.language == "ur"
        assert result.duration_seconds == 2.4

    def test_language_hint_forwarded(self) -> None:
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = request.content.decode("utf-8", errors="ignore")
            return httpx.Response(200, json={"text": "hi"})

        make_transcriber(handler).transcribe(b"abc", language="en")

        assert 'name="language"' in captured["body"]
        # The multipart value line carries the bare ISO code.
        assert "\r\nen\r\n" in captured["body"]

    def test_empty_audio_rejected_before_network(self) -> None:
        called = {"hit": False}

        def handler(request: httpx.Request) -> httpx.Response:
            called["hit"] = True
            return httpx.Response(200, json={"text": ""})

        transcriber = make_transcriber(handler)

        with pytest.raises(AIProviderError):
            transcriber.transcribe(b"")

        assert called["hit"] is False

    def test_http_error_raises_provider_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                401,
                json={"error": {"message": "invalid key"}},
            )

        with pytest.raises(AIProviderError) as excinfo:
            make_transcriber(handler).transcribe(b"audio")

        assert excinfo.value.status_code == 401
        assert "invalid key" in str(excinfo.value)

    def test_transport_failure_raises_provider_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("offline")

        with pytest.raises(AIProviderError):
            make_transcriber(handler).transcribe(b"audio")

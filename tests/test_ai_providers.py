"""Unit tests for AKI's mock and OpenAI-compatible providers."""

from __future__ import annotations

import json

import httpx
import pytest

from ai_engine.models import ChatMessage, CompletionRequest
from ai_engine.providers.mock import MockProvider
from ai_engine.providers.openai_compatible import (
    OpenAICompatibleProvider,
)
from ai_engine.provider import (
    AIConfigurationError,
    AIProviderError,
)
from conversation.models import MessageRole


def make_request() -> CompletionRequest:
    """A minimal valid request used across provider tests."""

    return CompletionRequest(
        messages=(
            ChatMessage(MessageRole.SYSTEM, "be brief"),
            ChatMessage(MessageRole.USER, "hello AKI"),
        )
    )


class TestMockProvider:
    """Deterministic offline backend."""

    def test_reply_mentions_latest_user_message(self) -> None:
        response = MockProvider().complete(make_request())

        assert response.provider == "mock"
        assert 'hello AKI' in response.content

    def test_reply_is_deterministic(self) -> None:
        first = MockProvider().complete(make_request())
        second = MockProvider().complete(make_request())

        assert first.content == second.content


class TestOpenAICompatibleConfiguration:
    """Constructor validation."""

    def test_rejects_missing_base_url(self) -> None:
        with pytest.raises(AIConfigurationError):
            OpenAICompatibleProvider(
                base_url="", api_key="k", model="m"
            )

    def test_rejects_missing_api_key(self) -> None:
        with pytest.raises(AIConfigurationError):
            OpenAICompatibleProvider(
                base_url="http://x/v1", api_key="", model="m"
            )

    def test_rejects_missing_model(self) -> None:
        with pytest.raises(AIConfigurationError):
            OpenAICompatibleProvider(
                base_url="http://x/v1", api_key="k", model=" "
            )


class TestOpenAICompatibleCompletion:
    """HTTP behavior against injected mock transports."""

    def make_provider(
        self,
        handler: httpx.MockTransport.HandlerType,
    ) -> OpenAICompatibleProvider:
        client = httpx.Client(transport=httpx.MockTransport(handler))
        return OpenAICompatibleProvider(
            base_url="http://testserver/v1",
            api_key="test-key",
            model="test-model",
            client=client,
        )

    def test_success_returns_normalized_response(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)

            assert body["model"] == "test-model"
            assert request.headers["Authorization"] == "Bearer test-key"
            assert request.url.path.endswith("/chat/completions")

            return httpx.Response(
                200,
                json={
                    "model": "test-model",
                    "choices": [
                        {
                            "message": {"content": "Hi there!"},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 11,
                        "completion_tokens": 4,
                    },
                },
            )

        response = self.make_provider(handler).complete(make_request())

        assert response.content == "Hi there!"
        assert response.provider == "openai_compatible"
        assert response.prompt_tokens == 11
        assert response.completion_tokens == 4

    def test_http_error_raises_provider_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                401,
                json={
                    "error": {"message": "invalid api key"}
                },
            )

        with pytest.raises(AIProviderError) as excinfo:
            self.make_provider(handler).complete(make_request())

        assert excinfo.value.status_code == 401
        assert "invalid api key" in str(excinfo.value)

    def test_transport_failure_raises_provider_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        with pytest.raises(AIProviderError):
            self.make_provider(handler).complete(make_request())

    def test_unexpected_shape_raises_provider_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"unexpected": True})

        with pytest.raises(AIProviderError):
            self.make_provider(handler).complete(make_request())

    def test_close_does_not_close_injected_client(self) -> None:
        client = httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={})
            )
        )
        provider = OpenAICompatibleProvider(
            base_url="http://testserver/v1",
            api_key="k",
            model="m",
            client=client,
        )

        provider.close()

        assert not client.is_closed

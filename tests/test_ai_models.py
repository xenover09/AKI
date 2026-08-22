"""Unit tests for AKI's intelligence-layer models."""

from __future__ import annotations

import pytest

from ai_engine.models import (
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
)
from conversation.models import MessageRole


class TestChatMessage:
    """Validation of single provider messages."""

    def test_accepts_valid_message(self) -> None:
        message = ChatMessage(role=MessageRole.USER, content="hello")

        assert message.content == "hello"

    def test_rejects_raw_string_role(self) -> None:
        with pytest.raises(TypeError):
            ChatMessage(role="user", content="hello")  # type: ignore[arg-type]

    def test_rejects_non_string_content(self) -> None:
        with pytest.raises(TypeError):
            ChatMessage(role=MessageRole.USER, content=123)  # type: ignore[arg-type]


class TestCompletionRequest:
    """Validation of outgoing requests."""

    def test_requires_at_least_one_message(self) -> None:
        with pytest.raises(ValueError):
            CompletionRequest(messages=())

    def test_messages_must_be_tuple_of_chat_messages(self) -> None:
        with pytest.raises(TypeError):
            CompletionRequest(
                messages=[ChatMessage(MessageRole.USER, "hi")]  # type: ignore[arg-type]
            )

    def test_temperature_bounds(self) -> None:
        messages = (ChatMessage(MessageRole.USER, "hi"),)

        with pytest.raises(ValueError):
            CompletionRequest(messages=messages, temperature=-0.1)

        with pytest.raises(ValueError):
            CompletionRequest(messages=messages, temperature=2.1)

    def test_max_tokens_must_be_positive(self) -> None:
        messages = (ChatMessage(MessageRole.USER, "hi"),)

        with pytest.raises(ValueError):
            CompletionRequest(messages=messages, max_tokens=0)


class TestCompletionResponse:
    """Validation of normalized replies."""

    def test_accepts_valid_response(self) -> None:
        response = CompletionResponse(
            content="ok", model="m", provider="mock"
        )

        assert response.content == "ok"

    def test_model_and_provider_required(self) -> None:
        with pytest.raises(ValueError):
            CompletionResponse(content="ok", model=" ", provider="mock")

        with pytest.raises(ValueError):
            CompletionResponse(content="ok", model="m", provider="")

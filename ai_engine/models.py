"""
AKI AI Engine Models.

Defines the data structures exchanged inside the intelligence layer.

This module contains data representation only. It performs no
network I/O, prompt construction, or orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from conversation.models import MessageRole


@dataclass(frozen=True)
class ChatMessage:
    """
    One message sent to or received from an AI provider.

    Attributes:
        role: Speaker role (system, user, assistant, tool).
        content: Raw textual content of the message.
    """

    role: MessageRole
    content: str

    def __post_init__(self) -> None:
        """Validate the chat message."""

        if not isinstance(self.role, MessageRole):
            raise TypeError(
                "role must be a MessageRole instance."
            )

        if not isinstance(self.content, str):
            raise TypeError(
                "content must be a string."
            )


@dataclass(frozen=True)
class CompletionRequest:
    """
    A fully-prepared request handed to an AI provider.

    Attributes:
        messages: Ordered conversation so far (system first).
        model: Provider model identifier; ``None`` uses the
            provider's configured default.
        temperature: Sampling temperature between 0.0 and 2.0.
        max_tokens: Upper bound on generated tokens; ``None``
            lets the provider decide.
        extra: Provider-specific options passed through verbatim.
    """

    messages: tuple[ChatMessage, ...]
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate the completion request."""

        if not isinstance(self.messages, tuple):
            raise TypeError(
                "messages must be a tuple of ChatMessage instances."
            )

        if not self.messages:
            raise ValueError(
                "messages cannot be empty."
            )

        for message in self.messages:
            if not isinstance(message, ChatMessage):
                raise TypeError(
                    "messages must contain ChatMessage instances only."
                )

        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError(
                "temperature must be between 0.0 and 2.0."
            )

        if self.max_tokens is not None and (
            not isinstance(self.max_tokens, int) or self.max_tokens < 1
        ):
            raise ValueError(
                "max_tokens must be a positive integer when provided."
            )


@dataclass(frozen=True)
class CompletionResponse:
    """
    The normalized result of one provider completion call.

    Attributes:
        content: Generated text.
        model: Model identifier that produced the text.
        provider: Name of the provider implementation used.
        finish_reason: Provider-reported stop reason, if any.
        prompt_tokens: Prompt token usage reported by the provider.
        completion_tokens: Completion token usage reported by the provider.
    """

    content: str
    model: str
    provider: str
    finish_reason: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None

    def __post_init__(self) -> None:
        """Validate the completion response."""

        if not isinstance(self.content, str):
            raise TypeError(
                "content must be a string."
            )

        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError(
                "model must be a non-empty string."
            )

        if not isinstance(self.provider, str) or not self.provider.strip():
            raise ValueError(
                "provider must be a non-empty string."
            )


__all__ = [
    "ChatMessage",
    "CompletionRequest",
    "CompletionResponse",
]

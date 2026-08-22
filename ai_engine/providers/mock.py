"""
AKI Mock AI Provider.

A deterministic offline backend for development, demos, and tests.
It echoes structured information about the request instead of
calling any external service, so AKI remains fully functional
without an API key or network access.
"""

from __future__ import annotations

from ai_engine.models import (
    CompletionRequest,
    CompletionResponse,
    MessageRole,
)
from ai_engine.provider import AIProvider


class MockProvider(AIProvider):
    """
    Deterministic provider used when no real backend is configured.

    The generated reply is stable for a given input, which keeps
    manual runs predictable and unit tests assertion-friendly.
    """

    def __init__(
        self,
        *,
        model: str = "aki-mock",
    ) -> None:
        if not isinstance(model, str) or not model.strip():
            raise ValueError(
                "model must be a non-empty string."
            )

        self._model = model.strip()

    @property
    def name(self) -> str:
        """Return the provider identifier used in responses."""

        return "mock"

    def complete(
        self,
        request: CompletionRequest,
    ) -> CompletionResponse:
        """Produce a deterministic echo of the latest user message."""

        last_user_message = next(
            (
                message.content
                for message in reversed(request.messages)
                if message.role is MessageRole.USER
            ),
            "",
        )

        content = (
            "[AKI mock intelligence] "
            "No AI provider is configured yet. I received: "
            f"\"{last_user_message}\""
        )

        return CompletionResponse(
            content=content,
            model=self._model,
            provider=self.name,
            finish_reason="stop",
        )


__all__ = [
    "MockProvider",
]

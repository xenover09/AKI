"""
AKI AI Service.

The application-facing facade of the intelligence layer. It turns a
raw user utterance into a provider response by delegating prompt
assembly to `PromptManager` and generation to the configured
`AIProvider`.

The service never knows which backend is in use; providers are
injected at boot time and can be swapped without touching this code.
"""

from __future__ import annotations

from conversation.models import Message

from ai_engine.models import CompletionRequest, CompletionResponse
from ai_engine.prompt_manager import PromptManager
from ai_engine.provider import AIProvider


class AIService:
    """
    High-level entry point for AKI's intelligence subsystem.

    Responsibilities:
        - Validate raw user input before any work happens.
        - Ask the PromptManager for the final message sequence.
        - Forward that sequence to the configured provider.
        - Return the normalized completion to the caller.
    """

    def __init__(
        self,
        provider: AIProvider,
        prompt_manager: PromptManager | None = None,
    ) -> None:
        if not isinstance(provider, AIProvider):
            raise TypeError(
                "provider must be an AIProvider instance."
            )

        if prompt_manager is None:
            prompt_manager = PromptManager()

        self._provider = provider
        self._prompt_manager = prompt_manager

    @property
    def provider_name(self) -> str:
        """Return the identifier of the active provider."""

        return self._provider.name

    def close(self) -> None:
        """Release resources held by the underlying provider."""

        self._provider.close()

    def respond(
        self,
        user_input: str,
        *,
        history: tuple[Message, ...] | list[Message] = (),
        memories: tuple[str, ...] | list[str] = (),
    ) -> CompletionResponse:
        """
        Produce AKI's reply for one user turn.

        Args:
            user_input: The user's latest message.
            history: Recent conversation messages, chronological.
            memories: Memory lines relevant to this turn.

        Returns:
            The provider's normalized completion.
        """

        messages = self._prompt_manager.build_messages(
            user_input,
            history=history,
            memories=memories,
        )

        return self._provider.complete(
            CompletionRequest(messages=messages)
        )


__all__ = [
    "AIService",
]

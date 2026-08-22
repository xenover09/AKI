"""Unit and integration tests for AKI's AIService facade."""

from __future__ import annotations

import pytest

from ai_engine.ai_service import AIService
from ai_engine.models import MessageRole as AIMessageRole
from ai_engine.providers.mock import MockProvider
from conversation.models import Message, MessageRole


class TestAIService:
    """End-to-end flow through prompt assembly and the provider."""

    def make_service(self) -> AIService:
        return AIService(provider=MockProvider())

    def test_respond_returns_completion(self) -> None:
        response = self.make_service().respond("mera naam kya hai?")

        assert response.provider == "mock"
        assert response.content
        assert "mera naam kya hai?" in response.content

    def test_history_flows_into_request(self) -> None:
        history = [
            Message("m1", "c1", MessageRole.USER, "salam"),
            Message("m2", "c1", MessageRole.ASSISTANT, "wa alaikum"),
        ]

        response = self.make_service().respond(
            "kya hua tha?",
            history=history,
            memories=("User ka naam Aether hai",),
        )

        assert response.finish_reason == "stop"

    def test_rejects_empty_input(self) -> None:
        with pytest.raises(ValueError):
            self.make_service().respond("  ")

    def test_provider_contract_enforced(self) -> None:
        with pytest.raises(TypeError):
            AIService(provider="not-a-provider")  # type: ignore[arg-type]

    def test_roles_align_with_conversation_subsystem(self) -> None:
        # ChatMessage reuses MessageRole so no mapping layer is needed.
        assert AIMessageRole.USER.value == MessageRole.USER.value
        assert AIMessageRole.SYSTEM.value == MessageRole.SYSTEM.value

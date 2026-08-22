"""Unit tests for AKI's prompt assembly."""

from __future__ import annotations

import pytest

from ai_engine.prompt_manager import PromptManager
from conversation.models import Message, MessageRole


def make_history() -> list[Message]:
    """Two conversational turns plus one tool message."""

    return [
        Message("m1", "c1", MessageRole.USER, "hi"),
        Message("m2", "c1", MessageRole.ASSISTANT, "hello"),
        Message("m3", "c1", MessageRole.TOOL, "raw tool payload"),
    ]


class TestMessageOrdering:
    """System-first assembly with history and user input last."""

    def test_produces_system_first_user_last(self) -> None:
        manager = PromptManager()

        messages = manager.build_messages("what time is it?")

        assert messages[0].role is MessageRole.SYSTEM
        assert messages[-1].role is MessageRole.USER
        assert messages[-1].content == "what time is it?"
        assert len(messages) == 2

    def test_history_preserved_in_order_without_tool_messages(
        self,
    ) -> None:
        manager = PromptManager()

        messages = manager.build_messages(
            "again", history=make_history()
        )

        roles = [message.role for message in messages]

        assert roles == [
            MessageRole.SYSTEM,
            MessageRole.USER,
            MessageRole.ASSISTANT,
            MessageRole.USER,
        ]


class TestMemoryContext:
    """Relevant memories surface inside the system message."""

    def test_memories_rendered_as_bullet_context(self) -> None:
        manager = PromptManager()

        messages = manager.build_messages(
            "mera naam kya hai?",
            memories=("User ka naam Aether hai",),
        )

        system_content = messages[0].content

        assert "MEMORY CONTEXT:" in system_content
        assert "- User ka naam Aether hai" in system_content

    def test_blank_memory_lines_are_dropped(self) -> None:
        manager = PromptManager()

        messages = manager.build_messages(
            "hello", memories=("", "real memory", "   ")
        )

        assert "- real memory" in messages[0].content
        assert "\n- \n" not in messages[0].content


class TestValidation:
    """Explicit failure contracts."""

    def test_empty_user_input_rejected(self) -> None:
        manager = PromptManager()

        with pytest.raises(ValueError):
            manager.build_messages("   ")

    def test_non_string_input_rejected(self) -> None:
        manager = PromptManager()

        with pytest.raises(TypeError):
            manager.build_messages(42)  # type: ignore[arg-type]

    def test_directives_must_be_non_empty_strings(self) -> None:
        with pytest.raises(ValueError):
            PromptManager(system_directives=("ok", ""))

    def test_custom_directives_are_used(self) -> None:
        manager = PromptManager(system_directives=("Be brief.",))

        messages = manager.build_messages("hi")

        assert messages[0].content == "Be brief."

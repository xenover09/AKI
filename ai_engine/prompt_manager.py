"""
AKI Prompt Manager.

Builds the final message sequence handed to an AI provider by
combining, in a fixed order:

    1. System directives (who AKI is, how it behaves).
    2. Relevant memories supplied by the caller.
    3. Recent conversation history.
    4. The user's latest input.

The manager owns formatting only. It never talks to providers,
memory services, or the database directly; callers pass in exactly
the context they want included. This keeps prompt behavior
deterministic and unit-testable.
"""

from __future__ import annotations

from ai_engine.models import ChatMessage
from conversation.models import Message, MessageRole

_DEFAULT_SYSTEM_DIRECTIVES: tuple[str, ...] = (
    "You are AKI, a personal AI assistant running locally on the "
    "user's machine. You are NOT ChatGPT, GPT, or any other product — "
    "if asked who you are, you are always AKI.",
    "The user's name is SALAAR; address them by name when natural.",
    "ALWAYS reply in Roman script (Hinglish / Roman Urdu) — for "
    "example: 'Ji Aether, main samadh gaya.' NEVER use Hindi "
    "(Devanagari) or Urdu (Arabic) script in your replies, even if "
    "the user writes in those scripts. English words are fine when "
    "natural.",
    "Answer concisely and helpfully. Match the user's language and "
    "tone — they mostly write Roman Urdu/Hinglish.",
    "Use the provided MEMORY CONTEXT when it is relevant.",
    "BOOK CONTEXT entries look like [Book Title · page N] followed by "
    "an excerpt. When you use them, cite the book and page number in "
    "your answer, e.g. '(Cyber Handbook, page 42)'. If the user asks "
    "what is written on a specific page, quote from BOOK CONTEXT.",
    "You have one tool: live web search. If a question needs current "
    "information (news, prices, scores, weather, recent events), "
    "reply with exactly 'SEARCH: <search query>' and nothing else. "
    "Live results will be provided to you in the next turn. Never "
    "use SEARCH: for general knowledge you already know.",
    "When the user asks you to remember something or set a reminder, "
    "confirm briefly what you understood.",
)


class PromptManager:
    """
    Assembles provider-ready message sequences.

    Responsibilities:
        - Hold AKI's standing system directives.
        - Render memory context into an explicit system message.
        - Append history and the newest user input in order.
        - Keep every produced sequence non-empty and system-first.
    """

    def __init__(
        self,
        system_directives: tuple[str, ...] | None = None,
    ) -> None:
        if system_directives is None:
            system_directives = _DEFAULT_SYSTEM_DIRECTIVES

        if not isinstance(system_directives, tuple):
            raise TypeError(
                "system_directives must be a tuple of strings."
            )

        for directive in system_directives:
            if not isinstance(directive, str) or not directive.strip():
                raise ValueError(
                    "every system directive must be a non-empty string."
                )

        self._system_directives = system_directives

    @property
    def system_directives(self) -> tuple[str, ...]:
        """Return AKI's standing system directives."""

        return self._system_directives

    def build_messages(
        self,
        user_input: str,
        *,
        history: tuple[Message, ...] | list[Message] = (),
        memories: tuple[str, ...] | list[str] = (),
    ) -> tuple[ChatMessage, ...]:
        """
        Build the ordered message sequence for one AI turn.

        Args:
            user_input: The user's latest, non-empty message.
            history: Recent conversation messages in chronological
                order; tool messages are skipped because providers
                only accept conversational roles here.
            memories: Pre-formatted memory lines relevant to this turn.

        Returns:
            A system-first `ChatMessage` tuple ready for a provider.

        Raises:
            TypeError: If arguments have the wrong types.
            ValueError: If `user_input` is empty or whitespace.
        """

        if not isinstance(user_input, str):
            raise TypeError(
                "user_input must be a string."
            )

        user_input = user_input.strip()

        if not user_input:
            raise ValueError(
                "user_input cannot be empty."
            )

        if not isinstance(history, (tuple, list)):
            raise TypeError(
                "history must be a tuple or list of Message instances."
            )

        if not isinstance(memories, (tuple, list)):
            raise TypeError(
                "memories must be a tuple or list of strings."
            )

        messages: list[ChatMessage] = [
            ChatMessage(
                role=MessageRole.SYSTEM,
                content=self._render_system_prompt(memories),
            )
        ]

        for entry in history:
            if not isinstance(entry, Message):
                raise TypeError(
                    "history must contain Message instances only."
                )

            if entry.role is not MessageRole.TOOL:
                messages.append(
                    ChatMessage(
                        role=entry.role,
                        content=entry.content,
                    )
                )

        messages.append(
            ChatMessage(
                role=MessageRole.USER,
                content=user_input,
            )
        )

        return tuple(messages)

    # ============================================================
    # Internals
    # ============================================================

    def _render_system_prompt(
        self,
        memories: tuple[str, ...] | list[str],
    ) -> str:
        """Join directives and optional memory context."""

        sections = [directive for directive in self._system_directives]

        cleaned_memories = [
            str(memory).strip()
            for memory in memories
            if isinstance(memory, str) and memory.strip()
        ]

        if cleaned_memories:
            rendered = "\n".join(
                f"- {memory}"
                for memory in cleaned_memories
            )
            sections.append(
                f"MEMORY CONTEXT:\n{rendered}"
            )

        return "\n\n".join(sections)


__all__ = [
    "PromptManager",
]

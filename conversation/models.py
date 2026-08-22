"""
AKI Conversation Models.

Defines the data structures used by AKI's conversation subsystem.

This module contains data representation only.
It does not perform database operations, AI inference,
or operating-system actions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class MessageRole(str, Enum):
    """Role of a message inside a conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True)
class Message:
    """
    Represents one message in a conversation.
    """

    message_id: str
    conversation_id: str
    role: MessageRole
    content: str

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    extra: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        """Validate the message."""

        if not isinstance(self.message_id, str):
            raise TypeError(
                "message_id must be a string."
            )

        if not self.message_id.strip():
            raise ValueError(
                "message_id cannot be empty."
            )

        if not isinstance(self.conversation_id, str):
            raise TypeError(
                "conversation_id must be a string."
            )

        if not self.conversation_id.strip():
            raise ValueError(
                "conversation_id cannot be empty."
            )

        if not isinstance(self.role, MessageRole):
            raise TypeError(
                "role must be a MessageRole instance."
            )

        if not isinstance(self.content, str):
            raise TypeError(
                "content must be a string."
            )

        if not self.content.strip():
            raise ValueError(
                "content cannot be empty."
            )

        object.__setattr__(
            self,
            "message_id",
            self.message_id.strip(),
        )

        object.__setattr__(
            self,
            "conversation_id",
            self.conversation_id.strip(),
        )

        object.__setattr__(
            self,
            "content",
            self.content.strip(),
        )


@dataclass(frozen=True)
class Conversation:
    """
    Represents a complete AKI conversation.
    """

    conversation_id: str
    title: str = "New Conversation"

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    extra: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        """Validate the conversation."""

        if not isinstance(
            self.conversation_id,
            str,
        ):
            raise TypeError(
                "conversation_id must be a string."
            )

        if not self.conversation_id.strip():
            raise ValueError(
                "conversation_id cannot be empty."
            )

        if not isinstance(self.title, str):
            raise TypeError(
                "title must be a string."
            )

        if not self.title.strip():
            raise ValueError(
                "title cannot be empty."
            )

        if self.updated_at < self.created_at:
            raise ValueError(
                "updated_at cannot be earlier than created_at."
            )

        object.__setattr__(
            self,
            "conversation_id",
            self.conversation_id.strip(),
        )

        object.__setattr__(
            self,
            "title",
            self.title.strip(),
        )


__all__ = [
    "Conversation",
    "Message",
    "MessageRole",
]
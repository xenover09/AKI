"""
AKI Conversation Service.

Provides the business-level API for managing conversations
and messages.

This layer coordinates conversation models and persistence.
AI inference, UI logic, and external integrations do not
belong here.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from database.database_service import DatabaseService
from conversation.models import (
    Conversation,
    Message,
    MessageRole,
)
from conversation.repository import ConversationRepository


class ConversationService:
    """
    High-level service for AKI conversations.

    Responsibilities:
        - Create conversations.
        - Update conversations.
        - Add messages.
        - Retrieve conversations.
        - Retrieve conversation history.
        - Delete conversations.
        - Generate unique identifiers.

    AI inference is intentionally outside this layer.
    """

    def __init__(
        self,
        database_service: DatabaseService,
    ) -> None:
        if not isinstance(
            database_service,
            DatabaseService,
        ):
            raise TypeError(
                "database_service must be a DatabaseService instance."
            )

        self._repository = ConversationRepository(
            database_service,
        )

    # ============================================================
    # Conversation Management
    # ============================================================

    def create_conversation(
        self,
        title: str = "New Conversation",
    ) -> Conversation:
        """Create and persist a new conversation."""

        if not isinstance(
            title,
            str,
        ):
            raise TypeError(
                "title must be a string."
            )

        title = title.strip()

        if not title:
            raise ValueError(
                "title cannot be empty."
            )

        now = datetime.now(timezone.utc)

        conversation = Conversation(
            conversation_id=self._generate_id("conv"),
            title=title,
            created_at=now,
            updated_at=now,
        )

        return self._repository.create_conversation(
            conversation,
        )

    def get_conversation(
        self,
        conversation_id: str,
    ) -> Conversation | None:
        """Retrieve a conversation by ID."""

        return self._repository.get_conversation(
            conversation_id,
        )

    def list_conversations(
        self,
        *,
        limit: int = 100,
    ) -> list[Conversation]:
        """Return recent conversations."""

        return self._repository.list_conversations(
            limit=limit,
        )

    def update_conversation(
        self,
        conversation_id: str,
        *,
        title: str | None = None,
    ) -> Conversation | None:
        """Update conversation metadata."""

        return self._repository.update_conversation(
            conversation_id,
            title=title,
            updated_at=datetime.now(timezone.utc),
        )

    def delete_conversation(
        self,
        conversation_id: str,
    ) -> bool:
        """Delete a conversation and its messages."""

        return self._repository.delete_conversation(
            conversation_id,
        )

    # ============================================================
    # Message Management
    # ============================================================

    def add_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
    ) -> Message:
        """
        Add a message to an existing conversation.

        Adding a message also updates the conversation's
        updated_at timestamp.
        """

        if not isinstance(
            conversation_id,
            str,
        ):
            raise TypeError(
                "conversation_id must be a string."
            )

        conversation_id = conversation_id.strip()

        if not conversation_id:
            raise ValueError(
                "conversation_id cannot be empty."
            )

        if not isinstance(
            role,
            MessageRole,
        ):
            raise TypeError(
                "role must be a MessageRole instance."
            )

        if not isinstance(
            content,
            str,
        ):
            raise TypeError(
                "content must be a string."
            )

        content = content.strip()

        if not content:
            raise ValueError(
                "content cannot be empty."
            )

        conversation = self.get_conversation(
            conversation_id,
        )

        if conversation is None:
            raise ValueError(
                f"Conversation not found: {conversation_id}"
            )

        now = datetime.now(timezone.utc)

        message = Message(
            message_id=self._generate_id("msg"),
            conversation_id=conversation_id,
            role=role,
            content=content,
            created_at=now,
        )

        stored_message = self._repository.add_message(
            message,
        )

        self._touch_conversation(
            conversation_id,
            now,
        )

        return stored_message

    def get_message(
        self,
        message_id: str,
    ) -> Message | None:
        """Retrieve one message by ID."""

        return self._repository.get_message(
            message_id,
        )

    def get_history(
        self,
        conversation_id: str,
        *,
        limit: int = 1000,
    ) -> list[Message]:
        """Return conversation history chronologically."""

        return self._repository.list_messages(
            conversation_id,
            limit=limit,
        )

    def delete_message(
        self,
        message_id: str,
    ) -> bool:
        """Delete one message."""

        return self._repository.delete_message(
            message_id,
        )

    # ============================================================
    # Internal Helpers
    # ============================================================

    def _touch_conversation(
        self,
        conversation_id: str,
        updated_at: datetime,
    ) -> Conversation | None:
        """
        Update the conversation activity timestamp.
        """

        return self._repository.update_conversation(
            conversation_id,
            updated_at=updated_at,
        )

    @staticmethod
    def _generate_id(
        prefix: str,
    ) -> str:
        """Generate a unique identifier."""

        return f"{prefix}_{uuid4().hex}"


__all__ = [
    "ConversationService",
]
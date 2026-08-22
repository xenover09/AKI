"""
AKI Conversation Repository.

Handles persistence for conversations and messages.

This module performs database operations only.
Business logic belongs in ConversationService.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

from database.database_service import DatabaseService
from conversation.models import (
    Conversation,
    Message,
    MessageRole,
)


class ConversationRepository:
    """
    Persistence layer for AKI conversations.
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

        self._database = database_service

    # ============================================================
    # Conversations
    # ============================================================

    def create_conversation(
        self,
        conversation: Conversation,
    ) -> Conversation:
        """Persist a conversation."""

        if not isinstance(
            conversation,
            Conversation,
        ):
            raise TypeError(
                "conversation must be a Conversation instance."
            )

        with self._database._connection.connection() as connection:
            connection.execute(
                """
                INSERT INTO conversations (
                    conversation_id,
                    title,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    conversation.conversation_id,
                    conversation.title,
                    conversation.created_at.isoformat(),
                    conversation.updated_at.isoformat(),
                ),
            )

            connection.commit()

        return conversation

    def get_conversation(
        self,
        conversation_id: str,
    ) -> Conversation | None:
        """Retrieve one conversation by ID."""

        self._validate_id(
            conversation_id,
            "conversation_id",
        )

        with self._database._connection.connection() as connection:
            row = connection.execute(
                """
                SELECT
                    conversation_id,
                    title,
                    created_at,
                    updated_at
                FROM conversations
                WHERE conversation_id = ?
                """,
                (conversation_id,),
            ).fetchone()

        if row is None:
            return None

        return self._conversation_from_row(row)

    def list_conversations(
        self,
        *,
        limit: int = 100,
    ) -> list[Conversation]:
        """Return conversations ordered by most recent update."""

        self._validate_limit(limit)

        with self._database._connection.connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    conversation_id,
                    title,
                    created_at,
                    updated_at
                FROM conversations
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            self._conversation_from_row(row)
            for row in rows
        ]

    def update_conversation(
        self,
        conversation_id: str,
        *,
        title: str | None = None,
        updated_at: datetime | None = None,
    ) -> Conversation | None:
        """
        Update conversation metadata.

        Only supplied fields are changed.
        """

        self._validate_id(
            conversation_id,
            "conversation_id",
        )

        if title is not None:
            if not isinstance(title, str):
                raise TypeError(
                    "title must be a string."
                )

            title = title.strip()

            if not title:
                raise ValueError(
                    "title cannot be empty."
                )

        if updated_at is not None:
            if not isinstance(
                updated_at,
                datetime,
            ):
                raise TypeError(
                    "updated_at must be a datetime."
                )

        current = self.get_conversation(
            conversation_id
        )

        if current is None:
            return None

        new_title = (
            title
            if title is not None
            else current.title
        )

        new_updated_at = (
            updated_at
            if updated_at is not None
            else current.updated_at
        )

        with self._database._connection.connection() as connection:
            connection.execute(
                """
                UPDATE conversations
                SET
                    title = ?,
                    updated_at = ?
                WHERE conversation_id = ?
                """,
                (
                    new_title,
                    new_updated_at.isoformat(),
                    conversation_id,
                ),
            )

            connection.commit()

        return self.get_conversation(
            conversation_id
        )

    def delete_conversation(
        self,
        conversation_id: str,
    ) -> bool:
        """Delete a conversation and its messages."""

        self._validate_id(
            conversation_id,
            "conversation_id",
        )

        with self._database._connection.connection() as connection:
            cursor = connection.execute(
                """
                DELETE FROM conversations
                WHERE conversation_id = ?
                """,
                (conversation_id,),
            )

            connection.commit()

        return cursor.rowcount > 0

    # ============================================================
    # Messages
    # ============================================================

    def add_message(
        self,
        message: Message,
    ) -> Message:
        """Persist a message."""

        if not isinstance(
            message,
            Message,
        ):
            raise TypeError(
                "message must be a Message instance."
            )

        with self._database._connection.connection() as connection:
            connection.execute(
                """
                INSERT INTO messages (
                    message_id,
                    conversation_id,
                    role,
                    content,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    message.message_id,
                    message.conversation_id,
                    message.role.value,
                    message.content,
                    message.created_at.isoformat(),
                ),
            )

            connection.commit()

        return message

    def get_message(
        self,
        message_id: str,
    ) -> Message | None:
        """Retrieve one message by ID."""

        self._validate_id(
            message_id,
            "message_id",
        )

        with self._database._connection.connection() as connection:
            row = connection.execute(
                """
                SELECT
                    message_id,
                    conversation_id,
                    role,
                    content,
                    created_at
                FROM messages
                WHERE message_id = ?
                """,
                (message_id,),
            ).fetchone()

        if row is None:
            return None

        return self._message_from_row(row)

    def list_messages(
        self,
        conversation_id: str,
        *,
        limit: int = 1000,
    ) -> list[Message]:
        """Return conversation messages chronologically."""

        self._validate_id(
            conversation_id,
            "conversation_id",
        )

        self._validate_limit(limit)

        with self._database._connection.connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    message_id,
                    conversation_id,
                    role,
                    content,
                    created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (
                    conversation_id,
                    limit,
                ),
            ).fetchall()

        return [
            self._message_from_row(row)
            for row in rows
        ]

    def delete_message(
        self,
        message_id: str,
    ) -> bool:
        """Delete one message."""

        self._validate_id(
            message_id,
            "message_id",
        )

        with self._database._connection.connection() as connection:
            cursor = connection.execute(
                """
                DELETE FROM messages
                WHERE message_id = ?
                """,
                (message_id,),
            )

            connection.commit()

        return cursor.rowcount > 0

    # ============================================================
    # Conversion Helpers
    # ============================================================

    @staticmethod
    def _conversation_from_row(
        row: sqlite3.Row,
    ) -> Conversation:
        """Convert a database row into a Conversation."""

        return Conversation(
            conversation_id=row["conversation_id"],
            title=row["title"],
            created_at=datetime.fromisoformat(
                row["created_at"],
            ),
            updated_at=datetime.fromisoformat(
                row["updated_at"],
            ),
        )

    @staticmethod
    def _message_from_row(
        row: sqlite3.Row,
    ) -> Message:
        """Convert a database row into a Message."""

        return Message(
            message_id=row["message_id"],
            conversation_id=row["conversation_id"],
            role=MessageRole(row["role"]),
            content=row["content"],
            created_at=datetime.fromisoformat(
                row["created_at"],
            ),
        )

    # ============================================================
    # Validation Helpers
    # ============================================================

    @staticmethod
    def _validate_id(
        value: str,
        field_name: str,
    ) -> None:
        """Validate an identifier."""

        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} must be a string."
            )

        if not value.strip():
            raise ValueError(
                f"{field_name} cannot be empty."
            )

    @staticmethod
    def _validate_limit(
        limit: int,
    ) -> None:
        """Validate a query limit."""

        if not isinstance(limit, int):
            raise TypeError(
                "limit must be an integer."
            )

        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero."
            )


__all__ = [
    "ConversationRepository",
]
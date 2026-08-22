"""Unit tests for AKI's conversation subsystem."""

from __future__ import annotations

import pytest

from conversation.models import MessageRole
from conversation.service import ConversationService


class TestConversationLifecycle:
    """Create / read / update / delete conversations."""

    def test_create_with_default_title(
        self, conversation_service: ConversationService
    ) -> None:
        conversation = conversation_service.create_conversation()

        assert conversation.title == "New Conversation"
        assert conversation.conversation_id

    def test_create_then_get_roundtrip(
        self, conversation_service: ConversationService
    ) -> None:
        created = conversation_service.create_conversation("Project plan")
        fetched = conversation_service.get_conversation(
            created.conversation_id
        )

        assert fetched == created

    def test_get_unknown_returns_none(
        self, conversation_service: ConversationService
    ) -> None:
        assert conversation_service.get_conversation("missing") is None

    def test_list_conversations_returns_all(
        self, conversation_service: ConversationService
    ) -> None:
        first = conversation_service.create_conversation("A")
        second = conversation_service.create_conversation("B")

        ids = {
            c.conversation_id
            for c in conversation_service.list_conversations()
        }

        assert {first.conversation_id, second.conversation_id} <= ids

    def test_update_changes_title_only(
        self, conversation_service: ConversationService
    ) -> None:
        created = conversation_service.create_conversation("Old title")

        updated = conversation_service.update_conversation(
            created.conversation_id,
            title="Renamed",
        )

        assert updated is not None
        assert updated.title == "Renamed"
        assert updated.created_at == created.created_at

    def test_delete_removes_conversation(
        self, conversation_service: ConversationService
    ) -> None:
        created = conversation_service.create_conversation("Doomed")

        assert (
            conversation_service.delete_conversation(
                created.conversation_id
            )
            is True
        )
        assert (
            conversation_service.delete_conversation(
                created.conversation_id
            )
            is False
        )


class TestMessages:
    """Adding and reading messages inside a conversation."""

    def test_add_message_and_read_history(
        self, conversation_service: ConversationService
    ) -> None:
        conversation = conversation_service.create_conversation()
        cid = conversation.conversation_id

        conversation_service.add_message(cid, MessageRole.USER, "Hi AKI")
        conversation_service.add_message(
            cid, MessageRole.ASSISTANT, "Hello. How can I help?"
        )

        history = conversation_service.get_history(cid)

        assert [m.role for m in history] == [
            MessageRole.USER,
            MessageRole.ASSISTANT,
        ]
        assert history[0].content == "Hi AKI"

    def test_add_message_updates_conversation_timestamp(
        self, conversation_service: ConversationService
    ) -> None:
        conversation = conversation_service.create_conversation()

        conversation_service.add_message(
            conversation.conversation_id, MessageRole.USER, "ping"
        )

        refreshed = conversation_service.get_conversation(
            conversation.conversation_id
        )

        assert refreshed is not None
        assert refreshed.updated_at >= conversation.updated_at

    def test_messages_cascade_delete_with_conversation(
        self, conversation_service: ConversationService
    ) -> None:
        conversation = conversation_service.create_conversation()
        cid = conversation.conversation_id

        message = conversation_service.add_message(
            cid, MessageRole.USER, "temporary"
        )

        conversation_service.delete_conversation(cid)

        assert conversation_service.get_message(message.message_id) is None
        assert conversation_service.get_history(cid) == []

    def test_empty_content_is_rejected(
        self, conversation_service: ConversationService
    ) -> None:
        conversation = conversation_service.create_conversation()

        with pytest.raises(ValueError):
            conversation_service.add_message(
                conversation.conversation_id,
                MessageRole.USER,
                "   ",
            )

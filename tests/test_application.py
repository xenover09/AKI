"""Integration tests for AKI's application boot wiring.

These tests run the real BootManager sequence, so they touch
AKI's actual runtime workspace. They are marked ``integration``
and can be skipped with:

    pytest -m "not integration"
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aki_core.application import Application


@pytest.mark.integration
class TestApplicationBootWiring:
    """The composition root must expose exactly one of each service."""

    def test_initialize_adopts_boot_services(
        self, tmp_path: Path
    ) -> None:
        application = Application(Path(__file__).resolve().parents[1])

        try:
            result = application.initialize()

            assert result.database_service is application.database_service
            assert result.memory_service is application.memory_service
            assert (
                result.conversation_service
                is application.conversation_service
            )
        finally:
            application.close()

    def test_conversation_service_is_functional_after_boot(self) -> None:
        application = Application(Path(__file__).resolve().parents[1])

        try:
            application.initialize()

            conversation = application.conversation_service.create_conversation(
                "Boot wiring check"
            )
            fetched = application.conversation_service.get_conversation(
                conversation.conversation_id
            )

            assert fetched is not None
            assert fetched.title == "Boot wiring check"

            application.conversation_service.delete_conversation(
                conversation.conversation_id
            )
        finally:
            application.close()

    def test_properties_fail_before_initialization(self) -> None:
        application = Application(Path(__file__).resolve().parents[1])

        with pytest.raises(RuntimeError):
            _ = application.database_service

        with pytest.raises(RuntimeError):
            _ = application.memory_service

        with pytest.raises(RuntimeError):
            _ = application.conversation_service

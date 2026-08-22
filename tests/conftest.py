"""
Shared pytest fixtures for the AKI test suite.

All fixtures are hermetic: every test receives its own temporary
database file and service instances, so tests never touch AKI's
real workspace under the user's application-data directory.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from conversation.service import ConversationService
from database.database_service import DatabaseService
from memory.memory_service import MemoryService


@pytest.fixture()
def database_service(tmp_path: Path) -> Iterator[DatabaseService]:
    """Yield an initialized DatabaseService backed by a temp file."""

    service = DatabaseService(tmp_path / "test_aki.db")
    service.initialize()

    yield service

    service.close()


@pytest.fixture()
def memory_service(
    database_service: DatabaseService,
) -> MemoryService:
    """Return a MemoryService bound to the temp database."""

    return MemoryService(database_service)


@pytest.fixture()
def conversation_service(
    database_service: DatabaseService,
) -> ConversationService:
    """Return a ConversationService bound to the temp database."""

    return ConversationService(database_service)

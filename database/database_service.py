"""
AKI Database Service.

Application-facing service layer for AKI persistence.

DatabaseService hides repository and connection details from
the rest of the application.
"""

from __future__ import annotations

from pathlib import Path

from .connection import DatabaseConnection
from .repository import DatabaseRecord, DatabaseRepository


class DatabaseService:
    """
    High-level database service for AKI.

    Responsibilities:
        - Initialize the database.
        - Save records.
        - Retrieve records.
        - Check records.
        - Delete records.
        - List records.
        - Count records.
        - Clear records.
        - Manage database lifecycle.
    """

    def __init__(
        self,
        database_path: Path,
        *,
        connection: DatabaseConnection | None = None,
        repository: DatabaseRepository | None = None,
    ) -> None:
        self._connection = (
            connection
            or DatabaseConnection(database_path)
        )

        self._repository = (
            repository
            or DatabaseRepository(self._connection)
        )

    @property
    def database_path(self) -> Path:
        """Return the configured database path."""
        return self._connection.database_path

    # ============================================================
    # Save
    # ============================================================

    def save(
        self,
        namespace: str,
        key: str,
        value: str,
    ) -> DatabaseRecord:
        """Create or update a database record."""

        return self._repository.save(
            namespace,
            key,
            value,
        )

    # ============================================================
    # Get
    # ============================================================

    def get(
        self,
        namespace: str,
        key: str,
    ) -> DatabaseRecord | None:
        """Retrieve a database record."""

        return self._repository.get(
            namespace,
            key,
        )

    # ============================================================
    # Exists
    # ============================================================

    def exists(
        self,
        namespace: str,
        key: str,
    ) -> bool:
        """Check whether a record exists."""

        return self._repository.exists(
            namespace,
            key,
        )

    # ============================================================
    # List
    # ============================================================

    def list(
        self,
        namespace: str | None = None,
    ) -> tuple[DatabaseRecord, ...]:
        """Return database records."""

        return self._repository.list(
            namespace
        )

    # ============================================================
    # Delete
    # ============================================================

    def delete(
        self,
        namespace: str,
        key: str,
    ) -> bool:
        """Delete a database record."""

        return self._repository.delete(
            namespace,
            key,
        )

    # ============================================================
    # Clear
    # ============================================================

    def clear(
        self,
        namespace: str | None = None,
    ) -> None:
        """Clear database records."""

        self._repository.clear(
            namespace
        )

    # ============================================================
    # Count
    # ============================================================

    def count(
        self,
        namespace: str | None = None,
    ) -> int:
        """Return the number of database records."""

        return self._repository.count(
            namespace
        )

    # ============================================================
    # Lifecycle
    # ============================================================

    @property
    def is_connected(self) -> bool:
        """Return whether the database is currently connected."""

        return self._connection.is_connected

    def initialize(self) -> None:
        """Initialize the database schema."""
        self._connection.initialize()

    def close(self) -> None:
        """Close the database connection."""

        self._connection.close()

    def __enter__(self) -> "DatabaseService":
        """Enter a database service context."""

        self._connection.connect()

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        """Exit the database service context."""

        self.close()


__all__ = [
    "DatabaseService",
]
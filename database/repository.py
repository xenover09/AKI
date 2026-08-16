"""
AKI Database Repository

Application-facing persistence layer for AKI.

This module provides safe CRUD operations on the AKI SQLite
database without exposing raw SQL or connection handling
to the rest of the application.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .connection import DatabaseConnection


@dataclass(frozen=True, slots=True)
class DatabaseRecord:
    """Represents one persisted AKI record."""

    record_id: int
    namespace: str
    key: str
    value: str
    created_at: str
    updated_at: str


class DatabaseRepository:
    """
    High-level repository for AKI persistence.

    Responsibilities:

    - Create database schema.
    - Save records.
    - Retrieve records.
    - Check record existence.
    - Delete records.
    - List records.
    - Clear records.
    """

    def __init__(self, database: DatabaseConnection) -> None:
        self._database = database

        self._database.initialize()

    # ============================================================
    # Save
    # ============================================================

    def save(
        self,
        namespace: str,
        key: str,
        value: str,
    ) -> DatabaseRecord:
        """Create or update a persisted record."""

        namespace = self._normalize(namespace, "namespace")
        key = self._normalize(key, "key")

        if not isinstance(value, str):
            raise TypeError("value must be a string.")

        now = datetime.now(timezone.utc).isoformat()

        with self._database.connection() as connection:
            connection.execute(
                """
                INSERT INTO records (
                    namespace,
                    key,
                    value,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(namespace, key)
                DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (
                    namespace,
                    key,
                    value,
                    now,
                    now,
                ),
            )

            row = connection.execute(
                """
                SELECT
                    id,
                    namespace,
                    key,
                    value,
                    created_at,
                    updated_at
                FROM records
                WHERE namespace = ?
                  AND key = ?
                """,
                (
                    namespace,
                    key,
                ),
            ).fetchone()

        if row is None:
            raise RuntimeError(
                "Database record could not be retrieved after save."
            )

        return self._to_record(row)

    # ============================================================
    # Get
    # ============================================================

    def get(
        self,
        namespace: str,
        key: str,
    ) -> DatabaseRecord | None:
        """Retrieve one persisted record."""

        namespace = self._normalize(namespace, "namespace")
        key = self._normalize(key, "key")

        with self._database.connection() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    namespace,
                    key,
                    value,
                    created_at,
                    updated_at
                FROM records
                WHERE namespace = ?
                  AND key = ?
                """,
                (
                    namespace,
                    key,
                ),
            ).fetchone()

        if row is None:
            return None

        return self._to_record(row)

    # ============================================================
    # Exists
    # ============================================================

    def exists(
        self,
        namespace: str,
        key: str,
    ) -> bool:
        """Return True when a record exists."""

        namespace = self._normalize(namespace, "namespace")
        key = self._normalize(key, "key")

        with self._database.connection() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM records
                WHERE namespace = ?
                  AND key = ?
                LIMIT 1
                """,
                (
                    namespace,
                    key,
                ),
            ).fetchone()

        return row is not None

    # ============================================================
    # List
    # ============================================================

    def list(
        self,
        namespace: str | None = None,
    ) -> tuple[DatabaseRecord, ...]:
        """Return persisted records."""

        with self._database.connection() as connection:
            if namespace is None:
                rows = connection.execute(
                    """
                    SELECT
                        id,
                        namespace,
                        key,
                        value,
                        created_at,
                        updated_at
                    FROM records
                    ORDER BY id ASC
                    """
                ).fetchall()
            else:
                namespace = self._normalize(
                    namespace,
                    "namespace",
                )

                rows = connection.execute(
                    """
                    SELECT
                        id,
                        namespace,
                        key,
                        value,
                        created_at,
                        updated_at
                    FROM records
                    WHERE namespace = ?
                    ORDER BY id ASC
                    """,
                    (namespace,),
                ).fetchall()

        return tuple(
            self._to_record(row)
            for row in rows
        )

    # ============================================================
    # Delete
    # ============================================================

    def delete(
        self,
        namespace: str,
        key: str,
    ) -> bool:
        """Delete one persisted record."""

        namespace = self._normalize(namespace, "namespace")
        key = self._normalize(key, "key")

        with self._database.connection() as connection:
            cursor = connection.execute(
                """
                DELETE FROM records
                WHERE namespace = ?
                  AND key = ?
                """,
                (
                    namespace,
                    key,
                ),
            )

            return cursor.rowcount > 0

    # ============================================================
    # Clear
    # ============================================================

    def clear(
        self,
        namespace: str | None = None,
    ) -> None:
        """Delete all records, optionally within a namespace."""

        with self._database.connection() as connection:
            if namespace is None:
                connection.execute(
                    "DELETE FROM records"
                )
            else:
                namespace = self._normalize(
                    namespace,
                    "namespace",
                )

                connection.execute(
                    """
                    DELETE FROM records
                    WHERE namespace = ?
                    """,
                    (namespace,),
                )

    # ============================================================
    # Count
    # ============================================================

    def count(
        self,
        namespace: str | None = None,
    ) -> int:
        """Return the number of persisted records."""

        with self._database.connection() as connection:
            if namespace is None:
                row = connection.execute(
                    "SELECT COUNT(*) FROM records"
                ).fetchone()
            else:
                namespace = self._normalize(
                    namespace,
                    "namespace",
                )

                row = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM records
                    WHERE namespace = ?
                    """,
                    (namespace,),
                ).fetchone()

        return int(row[0])

    # ============================================================
    # Helpers
    # ============================================================

    @staticmethod
    def _normalize(
        value: str,
        field_name: str,
    ) -> str:
        """Validate and normalize repository identifiers."""

        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} must be a string."
            )

        normalized = value.strip().lower()

        if not normalized:
            raise ValueError(
                f"{field_name} cannot be empty."
            )

        return normalized

    @staticmethod
    def _to_record(row: Any) -> DatabaseRecord:
        """Convert a SQLite row into a DatabaseRecord."""

        return DatabaseRecord(
            record_id=int(row["id"]),
            namespace=str(row["namespace"]),
            key=str(row["key"]),
            value=str(row["value"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )


__all__ = [
    "DatabaseRecord",
    "DatabaseRepository",
]
"""
AKI Database Connection.

Owns the SQLite connection lifecycle for AKI.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .schema import SCHEMA_SQL


class DatabaseConnection:
    """
    Manages AKI's SQLite database.

    Responsibilities:
        - Create the database directory.
        - Open the SQLite connection.
        - Configure SQLite.
        - Initialize the schema.
        - Close the connection.
    """

    def __init__(self, database_path: Path) -> None:
        if not isinstance(database_path, Path):
            raise TypeError(
                "database_path must be a pathlib.Path."
            )

        self._database_path = database_path
        self._connection: sqlite3.Connection | None = None

    @property
    def database_path(self) -> Path:
        """Return the SQLite database path."""
        return self._database_path

    def connect(self) -> sqlite3.Connection:
        """Open and return the configured SQLite connection."""

        if self._connection is not None:
            return self._connection

        self._database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        connection = sqlite3.connect(
            self._database_path,
            timeout=30.0,
        )

        connection.row_factory = sqlite3.Row

        connection.execute(
            "PRAGMA foreign_keys = ON;"
        )

        connection.execute(
            "PRAGMA journal_mode = WAL;"
        )

        connection.execute(
            "PRAGMA synchronous = NORMAL;"
        )

        self._connection = connection

        return connection

    def connection(self) -> sqlite3.Connection:
        """Return the active SQLite connection."""
        return self.connect()

    def initialize(self) -> None:
        """Initialize the SQLite schema."""

        connection = self.connect()

        connection.executescript(
            SCHEMA_SQL
        )

        connection.commit()

    def close(self) -> None:
        """Close the active database connection."""

        if self._connection is None:
            return

        self._connection.close()
        self._connection = None

    @property
    def is_connected(self) -> bool:
        """Return whether a connection is currently active."""

        return self._connection is not None


__all__ = [
    "DatabaseConnection",
]
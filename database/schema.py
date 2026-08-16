"""
AKI Database Schema.

Defines the SQLite schema used by AKI's database subsystem.

This module contains schema definitions only.
It does not open connections or perform database operations.
"""

from __future__ import annotations


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    namespace TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    CONSTRAINT uq_records_namespace_key
        UNIQUE (namespace, key)
);

CREATE INDEX IF NOT EXISTS idx_records_namespace
    ON records(namespace);

CREATE INDEX IF NOT EXISTS idx_records_key
    ON records(key);

CREATE INDEX IF NOT EXISTS idx_records_created_at
    ON records(created_at);

CREATE INDEX IF NOT EXISTS idx_records_updated_at
    ON records(updated_at);
"""


__all__ = ["SCHEMA_SQL"]
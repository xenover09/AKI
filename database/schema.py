"""
AKI Database Schema.

Defines the SQLite schema used by AKI.

This module contains schema definitions only.
It does not open connections or perform database operations.
"""

from __future__ import annotations


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

-- ============================================================
-- Records
-- Generic key/value persistence used by subsystem services.
-- ============================================================

CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    namespace TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    UNIQUE (namespace, key)
);

CREATE INDEX IF NOT EXISTS idx_records_namespace
    ON records(namespace);

CREATE INDEX IF NOT EXISTS idx_records_updated_at
    ON records(updated_at);

-- ============================================================
-- Conversations
-- ============================================================

CREATE TABLE IF NOT EXISTS conversations (
    conversation_id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT 'New Conversation',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_conversations_created_at
    ON conversations(created_at);

CREATE INDEX IF NOT EXISTS idx_conversations_updated_at
    ON conversations(updated_at);


-- ============================================================
-- Messages
-- ============================================================

CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,

    FOREIGN KEY (
        conversation_id
    )
    REFERENCES conversations (
        conversation_id
    )
    ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
    ON messages(conversation_id);

CREATE INDEX IF NOT EXISTS idx_messages_created_at
    ON messages(created_at);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_created
    ON messages(conversation_id, created_at);
"""


__all__ = [
    "SCHEMA_SQL",
]
"""
AKI Reminder Manager.

Persists and queries reminders through the DatabaseService, keeping
storage details out of the scheduler and UI layers.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from database.database_service import DatabaseService

_NAMESPACE = "automation"


@dataclass(frozen=True)
class Reminder:
    """
    One schedulable AKI reminder.

    Attributes:
        reminder_id: Stable unique identifier.
        message: What AKI should say when the reminder fires.
        kind: "once" or "daily".
        due_at: ISO timestamp for one-shot reminders (None for daily).
        time_of_day: "HH:MM" for daily reminders (None for one-shot).
        created_at: ISO creation timestamp.
        enabled: Whether the reminder should still fire.
    """

    reminder_id: str
    message: str
    kind: str
    due_at: str | None
    time_of_day: str | None
    created_at: str
    enabled: bool = True

    def __post_init__(self) -> None:
        """Validate the reminder."""

        if not isinstance(self.reminder_id, str) or not self.reminder_id.strip():
            raise ValueError(
                "reminder_id must be a non-empty string."
            )

        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError(
                "message must be a non-empty string."
            )

        if self.kind not in ("once", "daily"):
            raise ValueError(
                "kind must be 'once' or 'daily'."
            )

        if self.kind == "once" and not self.due_at:
            raise ValueError(
                "once reminders require a due_at timestamp."
            )

        if self.kind == "daily" and not self.time_of_day:
            raise ValueError(
                "daily reminders require a time_of_day."
            )


class ReminderManager:
    """
    Persistence facade for reminders.

    Responsibilities:
        - Create reminders with generated ids.
        - List active reminders.
        - Disable reminders after they fire.
        - Delete reminders permanently.
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

    def create(
        self,
        message: str,
        *,
        kind: str,
        due_at: datetime | None = None,
        time_of_day: str | None = None,
    ) -> Reminder:
        """Persist and return a new reminder."""

        now_iso = datetime.now(timezone.utc).isoformat()

        reminder = Reminder(
            reminder_id=f"rem_{uuid4().hex[:10]}",
            message=message.strip(),
            kind=kind,
            due_at=due_at.isoformat() if due_at else None,
            time_of_day=time_of_day,
            created_at=now_iso,
        )

        self._database.save(
            _NAMESPACE,
            reminder.reminder_id,
            json.dumps(asdict(reminder), ensure_ascii=False),
        )

        return reminder

    def list_active(self) -> tuple[Reminder, ...]:
        """Return all enabled reminders."""

        active: list[Reminder] = []

        for record in self._database.list(_NAMESPACE):
            try:
                reminder = self._deserialize(record.value)
            except Exception:
                continue

            if reminder.enabled:
                active.append(reminder)

        return tuple(active)

    def disable(self, reminder_id: str) -> bool:
        """Mark a reminder as fired/disabled."""

        record = self._database.get(_NAMESPACE, reminder_id)

        if record is None:
            return False

        try:
            reminder = self._deserialize(record.value)
        except Exception:
            return False

        updated = replace(reminder, enabled=False)

        self._database.save(
            _NAMESPACE,
            reminder_id,
            json.dumps(asdict(updated), ensure_ascii=False),
        )

        return True

    def delete(self, reminder_id: str) -> bool:
        """Remove a reminder permanently."""

        return self._database.delete(_NAMESPACE, reminder_id)

    @staticmethod
    def _deserialize(value: str) -> Reminder:
        """Rebuild a Reminder from stored JSON."""

        payload = json.loads(value)

        return Reminder(
            reminder_id=str(payload["reminder_id"]),
            message=str(payload["message"]),
            kind=str(payload["kind"]),
            due_at=payload.get("due_at"),
            time_of_day=payload.get("time_of_day"),
            created_at=str(payload["created_at"]),
            enabled=bool(payload.get("enabled", True)),
        )


__all__ = [
    "Reminder",
    "ReminderManager",
]

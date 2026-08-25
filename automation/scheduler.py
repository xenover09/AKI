"""
AKI Reminder Scheduler.

Pure, deterministic logic that decides which reminders are due at a
given moment. No timers, no Qt, no I/O — the desktop layer drives it
from a periodic tick.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Final

from automation.reminder_manager import Reminder

_DAILY_GRACE_MINUTES: Final[int] = 1


def find_due_reminders(
    reminders: tuple[Reminder, ...] | list[Reminder],
    *,
    now_local: datetime,
    last_fired_daily: dict[str, str] | None = None,
) -> tuple[Reminder, ...]:
    """
    Return reminders that should fire right now.

    Args:
        reminders: All enabled reminders.
        now_local: Current local time (reminders fire in local time).
        last_fired_daily: Map of reminder_id -> "YYYY-MM-DD" for daily
            reminders already fired today, so they fire once per day.

    Returns:
        Reminders that are due, in the order given.
    """

    if not isinstance(now_local, datetime):
        raise TypeError(
            "now_local must be a datetime."
        )

    fired_today = last_fired_daily or {}
    due: list[Reminder] = []

    for reminder in reminders:
        if not reminder.enabled:
            continue

        if reminder.kind == "once":
            if reminder.due_at and _is_due_once(reminder.due_at, now_local):
                due.append(reminder)

        elif reminder.kind == "daily":
            if reminder.time_of_day and _is_due_daily(
                reminder.time_of_day,
                now_local,
                fired_today.get(reminder.reminder_id),
            ):
                due.append(reminder)

    return tuple(due)


def _is_due_once(due_at_iso: str, now_local: datetime) -> bool:
    """A one-shot reminder is due once its local time has passed."""

    try:
        due = datetime.fromisoformat(due_at_iso)
    except ValueError:
        return False

    if due.tzinfo is not None:
        due = due.astimezone().replace(tzinfo=None)

    return now_local >= due


def _is_due_daily(
    time_of_day: str,
    now_local: datetime,
    fired_date: str | None,
) -> bool:
    """
    A daily reminder is due when the clock has reached its time and
    it has not already fired today.
    """

    if fired_date == now_local.strftime("%Y-%m-%d"):
        return False

    try:
        hour_text, minute_text = time_of_day.split(":")
        target = now_local.replace(
            hour=int(hour_text),
            minute=int(minute_text),
            second=0,
            microsecond=0,
        )
    except (ValueError, TypeError):
        return False

    window_end = target + timedelta(minutes=_DAILY_GRACE_MINUTES)

    return target <= now_local <= window_end


__all__ = [
    "find_due_reminders",
]

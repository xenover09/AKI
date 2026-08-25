"""Unit tests for AKI's automation subsystem."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from automation.parser import parse_schedule, strip_schedule_text
from automation.reminder_manager import ReminderManager
from automation.scheduler import find_due_reminders
from database.database_service import DatabaseService


@pytest.fixture()
def reminder_manager(tmp_path) -> ReminderManager:
    service = DatabaseService(tmp_path / "reminders.db")
    service.initialize()
    return ReminderManager(service)


class TestRelativeParsing:
    """'X minute baad' style schedules."""

    def test_minutes_later(self) -> None:
        now = datetime(2026, 8, 22, 10, 0)
        schedule = parse_schedule("10 minute baad chai yaad dilana", now=now)

        assert schedule is not None
        assert schedule.kind == "once"
        assert schedule.due_at == now + timedelta(minutes=10)

    def test_word_number(self) -> None:
        now = datetime(2026, 8, 22, 10, 0)
        schedule = parse_schedule("do ghantay baad meeting", now=now)

        assert schedule.due_at == now + timedelta(hours=2)

    def test_english_variant(self) -> None:
        now = datetime(2026, 8, 22, 10, 0)
        schedule = parse_schedule("remind me in 5 minutes", now=now)

        assert schedule.due_at == now + timedelta(minutes=5)


class TestClockParsing:
    """'9 baje' style schedules."""

    def test_shaam_shifts_to_evening(self) -> None:
        now = datetime(2026, 8, 22, 10, 0)
        schedule = parse_schedule("shaam 6 baje call karna", now=now)

        assert schedule.due_at.hour == 18
        assert schedule.due_at.day == 22

    def test_past_time_moves_to_tomorrow(self) -> None:
        now = datetime(2026, 8, 22, 20, 0)
        schedule = parse_schedule("9 baje reminder do", now=now)

        assert schedule.due_at.day == 23
        assert schedule.due_at.hour == 9

    def test_explicit_pm(self) -> None:
        now = datetime(2026, 8, 22, 10, 0)
        schedule = parse_schedule("2:30 pm reminder", now=now)

        assert schedule.due_at.hour == 14
        assert schedule.due_at.minute == 30

    def test_daily_schedule(self) -> None:
        now = datetime(2026, 8, 22, 10, 0)
        schedule = parse_schedule("roz 9 baje gym reminder", now=now)

        assert schedule.kind == "daily"
        assert schedule.time_of_day == "09:00"
        assert schedule.due_at is None


class TestMessageCleanup:
    """Schedule words are stripped from the reminder message."""

    def test_message_remainder(self) -> None:
        cleaned = strip_schedule_text("10 minute baad chai yaad dilana mujhe")

        assert "chai" in cleaned
        assert "minute" not in cleaned
        assert "yaad dilana" not in cleaned


class TestScheduler:
    """Due-reminder selection logic."""

    def test_once_reminder_fires_when_past(self) -> None:
        now = datetime(2026, 8, 22, 10, 0)
        due_reminder = _make_reminder(
            due_at=(now - timedelta(minutes=1)).isoformat(),
        )
        future = _make_reminder(
            reminder_id="rem_future",
            due_at=(now + timedelta(hours=1)).isoformat(),
        )

        due = find_due_reminders((due_reminder, future), now_local=now)

        assert [r.reminder_id for r in due] == ["rem_1"]

    def test_daily_fires_once_per_day(self) -> None:
        now = datetime(2026, 8, 22, 9, 0, 30)
        daily = _make_reminder(kind="daily", time_of_day="09:00")

        first = find_due_reminders((daily,), now_local=now)
        second = find_due_reminders(
            (daily,),
            now_local=now,
            last_fired_daily={"rem_1": "2026-08-22"},
        )

        assert len(first) == 1
        assert second == ()


class TestReminderManager:
    """Persistence behavior."""

    def test_create_and_list(self, reminder_manager: ReminderManager) -> None:
        reminder_manager.create(
            "chai break",
            kind="once",
            due_at=datetime(2026, 8, 22, 12, 0),
        )

        active = reminder_manager.list_active()

        assert len(active) == 1
        assert active[0].message == "chai break"

    def test_disable_after_firing(self, reminder_manager: ReminderManager) -> None:
        reminder = reminder_manager.create(
            "one shot",
            kind="once",
            due_at=datetime(2026, 8, 22, 12, 0),
        )

        assert reminder_manager.disable(reminder.reminder_id) is True
        assert reminder_manager.list_active() == ()

    def test_validation_rejects_bad_kind(
        self, reminder_manager: ReminderManager
    ) -> None:
        with pytest.raises(ValueError):
            reminder_manager.create("x", kind="weekly")


def _make_reminder(
    *,
    reminder_id: str = "rem_1",
    due_at: str | None = None,
    kind: str = "once",
    time_of_day: str | None = None,
):
    from automation.reminder_manager import Reminder

    return Reminder(
        reminder_id=reminder_id,
        message="test reminder",
        kind=kind,
        due_at=due_at,
        time_of_day=time_of_day,
        created_at="2026-08-22T00:00:00+00:00",
    )

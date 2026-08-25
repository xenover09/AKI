"""
AKI Reminder Time Parser.

Extracts schedule information from natural-language commands in
English and Roman Urdu, e.g.:

    "10 minute baad chai yaad dilana"      -> in 10 minutes
    "roz 9 baje gym reminder"              -> daily at 09:00
    "kal shaam 6 baje call karna"          -> tomorrow 18:00
    "reminder 14:30 par meeting"           -> today 14:30

Only unambiguous patterns are accepted; anything uncertain yields
no schedule so the caller can ask the user for clarification
instead of setting a wrong alarm.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final


@dataclass(frozen=True)
class ParsedSchedule:
    """
    One extracted schedule.

    Attributes:
        kind: "once" or "daily".
        due_at: Exact fire time for "once" schedules.
        time_of_day: "HH:MM" for "daily" schedules.
        matched_text: The phrase that produced this schedule.
    """

    kind: str
    due_at: datetime | None
    time_of_day: str | None
    matched_text: str


_NUMBER_WORDS: Final[dict[str, int]] = {
    "ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4,
    "paanch": 5, "panch": 5, "che": 6, "chhe": 6, "saat": 7,
    "aath": 8, "nau": 9, "das": 10, "bees": 20, "tees": 30,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "fifteen": 15, "twenty": 20, "thirty": 30, "half": 30,
}

_PERIOD_WORDS: Final[dict[str, int]] = {
    "minute": 1, "minutes": 1, "min": 1, "mint": 1,
    "ghantay": 60, "ghanta": 60, "ghante": 60, "hour": 60, "hours": 60,
}

_DAY_PART_SHIFTS: Final[dict[str, int]] = {
    "subah": 0, "morning": 0,
    "dopahar": 0, "dopher": 0, "afternoon": 0,
    "shaam": 12, "evening": 12,
    "raat": 12, "night": 12,
}

_RELATIVE_PATTERN: Final[re.Pattern] = re.compile(
    r"\b(?P<count>\d{1,3}|"
    r"ek|do|teen|char|chaar|paanch|panch|che|chhe|saat|aath|nau|das|bees|tees|"
    r"one|two|three|four|five|six|seven|eight|nine|ten|fifteen|twenty|thirty)\s+"
    r"(?P<unit>minute|minutes|min|mints?|ghantay|ghanta|ghante|hour|hours)\s+"
    r"(?:baad|later|mein|me|main|in)\b",
    re.IGNORECASE,
)

# English pre-position form: "in 5 minutes".
_RELATIVE_EN_PATTERN: Final[re.Pattern] = re.compile(
    r"\bin\s+(?P<count>\d{1,3}|"
    r"one|two|three|four|five|six|seven|eight|nine|ten|fifteen|twenty|thirty)\s+"
    r"(?P<unit>minutes?|min|mints?|hours?|ghantay|ghante)\b",
    re.IGNORECASE,
)

# Two clock forms: "2:30 pm" (am/pm anchored) and "9 baje" (baje anchored).
_CLOCK_AMPM_PATTERN: Final[re.Pattern] = re.compile(
    r"\b(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<ampm>am|pm)\b",
    re.IGNORECASE,
)

_CLOCK_BAJE_PATTERN: Final[re.Pattern] = re.compile(
    r"\b(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*baje?\b",
    re.IGNORECASE,
)

_DAILY_PATTERN: Final[re.Pattern] = re.compile(
    r"\b(?:roz|daily|har\s+din|every\s*day)\b",
    re.IGNORECASE,
)

_TOMORROW_PATTERN: Final[re.Pattern] = re.compile(
    r"\b(?:kal|tomorrow)\b",
    re.IGNORECASE,
)

_DAY_PART_PATTERN: Final[re.Pattern] = re.compile(
    r"\b(subah|morning|dopahar|dopher|afternoon|shaam|evening|raat|night)\b",
    re.IGNORECASE,
)


def parse_schedule(text: str, *, now: datetime | None = None) -> ParsedSchedule | None:
    """
    Extract one schedule from a user message.

    Args:
        text: Raw user message.
        now: Reference time; defaults to the current UTC time.

    Returns:
        A `ParsedSchedule` on a confident match, otherwise None.
    """

    if not isinstance(text, str):
        raise TypeError(
            "text must be a string."
        )

    cleaned = text.strip()
    if not cleaned:
        return None

    reference = now or datetime.now()

    relative = _match_relative(cleaned, reference)
    if relative is not None:
        return relative

    clock = _match_clock(cleaned, reference)
    if clock is not None:
        return clock

    return None


def strip_schedule_text(text: str) -> str:
    """Remove schedule phrases so the remainder becomes the message."""

    cleaned = text

    for pattern in (
        _RELATIVE_PATTERN,
        re.compile(r"\b(?:reminder|remind(?:er)?\s+do|yaad\s+dila(?:na|do|de)?)\b", re.IGNORECASE),
        re.compile(r"\b(?:mujhe|mjhe|ko)\b", re.IGNORECASE),
        re.compile(r"\b(?:set|karo|kar\s*do|karden|please|plz)\b", re.IGNORECASE),
        re.compile(r"\b(?:a|an|the|at|on|par|pe|pr)\b", re.IGNORECASE),
    ):
        cleaned = pattern.sub(" ", cleaned)

    return re.sub(r"\s+", " ", cleaned).strip(" ,.-")


def _match_relative(text: str, reference: datetime) -> ParsedSchedule | None:
    """Match '10 minute baad' / 'in 5 minutes' style schedules."""

    found = _RELATIVE_PATTERN.search(text) or _RELATIVE_EN_PATTERN.search(text)

    if not found:
        return None

    count = _resolve_count(found.group("count"))
    unit_minutes = _PERIOD_WORDS.get(found.group("unit").lower(), 0)

    if count <= 0 or unit_minutes <= 0:
        return None

    return ParsedSchedule(
        kind="once",
        due_at=reference + timedelta(minutes=count * unit_minutes),
        time_of_day=None,
        matched_text=found.group(0),
    )


def _match_clock(text: str, reference: datetime) -> ParsedSchedule | None:
    """Match '9 baje' / 'roz 6:30 pm' / 'kal shaam 6 baje' schedules."""

    clock = _CLOCK_AMPM_PATTERN.search(text) or _CLOCK_BAJE_PATTERN.search(text)

    if not clock:
        return None

    groups = clock.groupdict()
    hour = int(groups.get("hour") or 0)
    minute = int(groups.get("minute") or 0)

    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        return None

    day_part = _DAY_PART_PATTERN.search(text)
    ampm = (groups.get("ampm") or "").lower()

    # Resolve 12-hour ambiguity from am/pm, then from day-part words.
    if ampm == "pm" and hour < 12:
        hour += 12
    elif ampm == "am" and hour == 12:
        hour = 0
    elif not ampm and day_part:
        shift = _DAY_PART_SHIFTS.get(day_part.group(1).lower(), 0)
        if 1 <= hour <= 11 and shift:
            hour += shift

    daily = bool(_DAILY_PATTERN.search(text))
    tomorrow = bool(_TOMORROW_PATTERN.search(text))

    due = reference.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )

    if not daily:
        if tomorrow or due <= reference:
            due += timedelta(days=1)

    return ParsedSchedule(
        kind="daily" if daily else "once",
        due_at=None if daily else due,
        time_of_day=f"{hour:02d}:{minute:02d}" if daily else None,
        matched_text=clock.group(0),
    )


def _resolve_count(raw: str) -> int:
    """Resolve a numeric or word count into an integer."""

    if raw.isdigit():
        return int(raw)

    return _NUMBER_WORDS.get(raw.lower(), 0)


__all__ = [
    "ParsedSchedule",
    "parse_schedule",
    "strip_schedule_text",
]

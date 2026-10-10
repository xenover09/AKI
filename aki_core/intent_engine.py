"""
AKI Intent Engine.

Maps natural-language commands (English + Roman Urdu) onto AKI's
registered actions using deterministic, high-confidence patterns.

Design rules:

    - A match requires an explicit action verb or command keyword;
      casual mentions never trigger actions.
    - Unknown application targets return no decision so the request
      falls through to normal conversation.
    - The engine performs no execution; it only decides.

Execution always flows through the permission-checked CommandExecutor.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Final

from .system_actions import resolve_application


@dataclass(frozen=True)
class IntentDecision:
    """
    One resolved user intent ready for the executor.

    Attributes:
        action: Registered action name.
        parameters: Keyword parameters forwarded to the handler.
        utterance: The original matched text.
    """

    action: str
    parameters: dict[str, str] = field(default_factory=dict)
    utterance: str = ""


_ACTION_VERB: Final[str] = (
    r"(?:open|khol(?:o|na)?|launch|start|run|chalao?|chala)"
)

_SITE_NAMES: Final[str] = r"youtube|google|github|gmail|whatsapp"

# Bare site mentions ("yt par jaker videos laya kar") — anyone typing
# a site alias wants that site opened; no verb required.
_BARE_SITE_PATTERN: Final[re.Pattern] = re.compile(
    r"\b(?:yt|youtube)\b",
    re.IGNORECASE,
)

_WEBSITE_PATTERNS: Final[tuple[re.Pattern, ...]] = (
    re.compile(
        rf"\b{_ACTION_VERB}\s+(?:the\s+)?(?P<site>{_SITE_NAMES})\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b(?P<site>{_SITE_NAMES})\s+(?:ko\s*)?{_ACTION_VERB}\b",
        re.IGNORECASE,
    ),
)

_APPLICATION_PATTERNS: Final[tuple[re.Pattern, ...]] = (
    re.compile(
        rf"\b{_ACTION_VERB}\s+(?:the\s+)?(?:app\s+)?"
        rf"(?P<target>[a-z][a-z0-9 ]{{1,30}}?)\s*(?:app)?\s*(?:please|zara)?\s*[.!]*\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b(?P<target>[a-z][a-z0-9 ]{{1,30}}?)\s*(?:ko\s*)?{_ACTION_VERB}\b",
        re.IGNORECASE,
    ),
)

_SCREENSHOT_PATTERN: Final[re.Pattern] = re.compile(
    r"\b(?:take\s+(?:a\s+)?screenshot|screenshot\s*(?:lo|le|lena|lijiye|lain)?)\b",
    re.IGNORECASE,
)

_SYSTEM_INFO_PATTERN: Final[re.Pattern] = re.compile(
    r"\b(?:system\s*(?:status|info(?:rmation)?|health)"
    r"|time\s*kya\s*(?:hua|hua hai)|kit(?:na|ne)\s*(?:baj(?:e|a)|hue)"
    r"|what(?:'s| is)\s+the\s+time)\b",
    re.IGNORECASE,
)

# --- PC control v2 -------------------------------------------------------

_VOLUME_PATTERN: Final[re.Pattern] = re.compile(
    r"\b(?:volume|awaaz|awaz|sound)\s*(?:full|100|max)?\s*"
    r"(?:up|barhao|barha|badhao|kam|karo|down|mute|kar(?:do|do))?|"
    r"\b(?:mute|unmute)\s*(?:karo|kar)?\b",
    re.IGNORECASE,
)

_MEDIA_PATTERN: Final[re.Pattern] = re.compile(
    r"\b(?:play|pause|play\/pause|next(?:\s*(?:song|track|gaana|gana))?|"
    r"previous(?:\s*(?:song|track|gaana|gana))?|agla(?:\s*gaana)?|"
    r"pichla(?:\s*gaana)?|gaana\s*(?:chala|lagao)|music\s*(?:chala|pause|rok))\b",
    re.IGNORECASE,
)

_PROCESSES_PATTERN: Final[re.Pattern] = re.compile(
    r"\b(?:processes?|apps?|programs?)\s*(?:batao?|dikhao|list)\b"
    r"|\bkaun(?:si|se)\s+(?:apps?|programs?|process)\s+chal",
    re.IGNORECASE,
)

_KILL_PATTERN: Final[re.Pattern] = re.compile(
    r"\b(?:kill|khatam)\s*(?:karo|kar)?\s+(?:process|app|program)?\s*(?P<target>[a-zA-Z0-9._ -]{2,40})\b"
    r"|\b(?P<target2>[a-zA-Z0-9._]{2,30})\s+(?:process|app)\s+(?:kill|band)\s*(?:karo|kar)?\b"
    r"|\b(?P<target3>[a-zA-Z0-9._]{2,30})\s+(?:kill|khatam)\b"
    r"|\b(?P<target4>[a-zA-Z0-9._]{2,30})\s+band\s*(?:karo|kar)?\b",
    re.IGNORECASE,
)

# Direct command phrases (UI quick-action chips and spoken equivalents).
# These may map to disabled actions so users get honest roadmap replies.
_EXPLICIT_ACTIONS: Final[tuple[tuple[re.Pattern, str], ...]] = (
    (
        re.compile(
            r"\b(?:search|find)\s+(?:my\s+)?files?\b|\bfiles?\s*(?:search|dhundo?|dhoondo)\b",
            re.IGNORECASE,
        ),
        "search_files",
    ),
    (
        re.compile(
            r"\bsystem\s+cleanup\b|\bcleanup\s*karo?\b|\bsafai\s*karo\b",
            re.IGNORECASE,
        ),
        "system_cleanup",
    ),
    (
        re.compile(
            r"\b(?:start\s+)?(?:screen\s+|audio\s+)?recording\s*(?:shuru|start|karo)?\b"
            r"|\brecord(?:ing)?\s*(?:shuru|karo)\b",
            re.IGNORECASE,
        ),
        "start_recording",
    ),
    (
        re.compile(
            r"\b(?:reminder|yaad)\s*(?:dila|dena|do|de|dilana|dilao)\b"
            r"|\b(?:set|lagao?|laga)\s+(?:a\s+)?(?:reminder|alarm)\b"
            r"|\balarm\s*(?:laga|lagao|do|bajao|dena)?\b"
            r"|\bremind\s+me\b"
            r"|\b(?:utha|bata)\s*dena\b"
            r"|\bnotify\s*(?:karo|karna|me)?\b"
            r"|\b\d{1,3}\s*(?:minute|minutes|min|mints?|ghantay|ghanta|ghante|hours?)\s*(?:baad|later)\b",
            re.IGNORECASE,
        ),
        "create_reminder",
    ),
    (
        re.compile(
            r"\b(?:mere\s+)?(?:reminders?|yaadein|yaadain)\s*(?:batao?|dikhao|kya|list)?\b",
            re.IGNORECASE,
        ),
        "list_reminders",
    ),
    (
        re.compile(
            r"\b(?:book|kitaab|pdf)\s*(?:add|lagao|laga|dao|do|dalo|import)\b"
            r"|\b(?:add|import)\s+(?:a\s+)?(?:book|pdf)\b",
            re.IGNORECASE,
        ),
        "add_book",
    ),
    (
        re.compile(
            r"\b(?:mere\s+)?(?:books?|kitaabein|library)\s+"
            r"(?:batao?|dikhao|list|kaunsi|kis|related|topics?)\b",
            re.IGNORECASE,
        ),
        "list_books",
    ),
)

_TARGET_FILLERS: Final[frozenset] = frozenset(
    {"do", "dena", "de", "please", "zara", "abhi", "jaldi", "na", "yaar"}
)


class IntentEngine:
    """
    Deterministic first-pass interpreter for user commands.

    The engine owns matching only. Callers feed decisions to the
    CommandExecutor, which enforces permissions and confirmation.
    """

    def match(self, text: str) -> IntentDecision | None:
        """
        Attempt to resolve one user utterance into an intent.

        Returns:
            An `IntentDecision` on a confident match, otherwise None.
        """

        if not isinstance(text, str):
            raise TypeError(
                "text must be a string."
            )

        cleaned = text.strip()
        if not cleaned:
            return None

        explicit = self._match_explicit(cleaned)
        if explicit is not None:
            return explicit

        website = self._match_website(cleaned)
        if website is not None:
            return website

        application = self._match_application(cleaned)
        if application is not None:
            return application

        if _SCREENSHOT_PATTERN.search(cleaned):
            return IntentDecision(
                action="take_screenshot",
                utterance=cleaned,
            )

        volume = self._match_volume(cleaned)
        if volume is not None:
            return volume

        media = self._match_media(cleaned)
        if media is not None:
            return media

        processes = self._match_processes(cleaned)
        if processes is not None:
            return processes

        kill = self._match_kill(cleaned)
        if kill is not None:
            return kill

        if _SYSTEM_INFO_PATTERN.search(cleaned):
            return IntentDecision(
                action="get_system_info",
                utterance=cleaned,
            )

        return None

    # ============================================================
    # Pattern strategies
    # ============================================================

    def _match_explicit(self, text: str) -> IntentDecision | None:
        """Match direct command phrases such as UI quick-action chips."""

        for pattern, action in _EXPLICIT_ACTIONS:
            if pattern.search(text):
                return IntentDecision(
                    action=action,
                    utterance=text,
                )

        return None

    def _match_volume(self, text: str) -> IntentDecision | None:
        """Match volume up/down/mute/full commands."""

        if not _VOLUME_PATTERN.search(text):
            return None

        lowered = text.lower()

        if "mute" in lowered:
            return IntentDecision(
                action="volume_step",
                parameters={"direction": "mute"},
                utterance=text,
            )

        if "full" in lowered or "100" in lowered or "max" in lowered:
            return IntentDecision(
                action="set_volume",
                parameters={"level": "100"},
                utterance=text,
            )

        direction = (
            "down"
            if any(word in lowered for word in ("kam", "down", "less"))
            else "up"
        )

        return IntentDecision(
            action="volume_step",
            parameters={"direction": direction},
            utterance=text,
        )

    def _match_media(self, text: str) -> IntentDecision | None:
        """Match play/pause/next/previous media commands."""

        found = _MEDIA_PATTERN.search(text)

        if not found:
            return None

        phrase = found.group(0).lower()

        if "next" in phrase or "agla" in phrase:
            action = "next"
        elif "previous" in phrase or "pichla" in phrase:
            action = "previous"
        elif "pause" in phrase or "rok" in phrase:
            action = "pause"
        else:
            action = "play"

        return IntentDecision(
            action="media_control",
            parameters={"action": action},
            utterance=text,
        )

    def _match_processes(self, text: str) -> IntentDecision | None:
        """Match 'processes batao' style read-only queries."""

        if _PROCESSES_PATTERN.search(text):
            return IntentDecision(
                action="list_processes",
                utterance=text,
            )

        return None

    def _match_kill(self, text: str) -> IntentDecision | None:
        """Match 'notepad kill karo' style requests (confirmation-gated)."""

        found = _KILL_PATTERN.search(text)

        if not found:
            return None

        groups = found.groupdict()
        target = next(
            (value for value in groups.values() if value),
            "",
        ).strip()

        # Avoid hijacking generic sentences with no real target.
        filler = {"karo", "kar", "process", "app", "program", "band", "kill"}

        if not target or target.lower() in filler:
            return None

        return IntentDecision(
            action="kill_process",
            parameters={"target": target},
            utterance=text,
        )

    def _match_website(self, text: str) -> IntentDecision | None:
        """Match 'open youtube' / 'youtube kholo' / bare 'yt ...' commands."""

        for pattern in _WEBSITE_PATTERNS:
            found = pattern.search(text)

            if found:
                site = (found.group("site") or "").lower()

                if site == "yt":
                    site = "youtube"

                if site:
                    return IntentDecision(
                        action="open_website",
                        parameters={"site": site},
                        utterance=text,
                    )

        # Bare alias: "yt" in any phrasing means "open YouTube".
        if _BARE_SITE_PATTERN.search(text):
            return IntentDecision(
                action="open_website",
                parameters={"site": "youtube"},
                utterance=text,
            )

        return None

    def _match_application(self, text: str) -> IntentDecision | None:
        """
        Match 'open vs code' / 'chrome kholo' style commands.

        The target must resolve to a known local application;
        otherwise the utterance falls through to conversation.
        """

        for pattern in _APPLICATION_PATTERNS:
            found = pattern.search(text)

            if not found:
                continue

            target = self._clean_target(found.group("target"))

            if not target:
                continue

            if resolve_application(target) is None:
                continue

            canonical = _canonical_app_name(target)

            return IntentDecision(
                action="open_application",
                parameters={"target": canonical},
                utterance=text,
            )

        return None

    @staticmethod
    def _clean_target(raw_target: str) -> str:
        """Strip filler words from an extracted target phrase."""

        words = [
            word
            for word in raw_target.lower().split()
            if word not in _TARGET_FILLERS
        ]

        return " ".join(words).strip()


def _canonical_app_name(target: str) -> str:
    """Return the friendliest alias for logging and replies."""

    normalized = target.strip().lower()

    aliases = {
        "code": "vscode",
        "vs code": "vscode",
        "google chrome": "chrome",
        "calc": "calculator",
        "files": "explorer",
        "file explorer": "explorer",
        "command prompt": "cmd",
    }

    return aliases.get(normalized, normalized)


__all__ = [
    "IntentDecision",
    "IntentEngine",
]

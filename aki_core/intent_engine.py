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

    def _match_website(self, text: str) -> IntentDecision | None:
        """Match 'open youtube' / 'youtube kholo' style commands."""

        for pattern in _WEBSITE_PATTERNS:
            found = pattern.search(text)

            if found:
                site = (found.group("site") or "").lower()

                if site:
                    return IntentDecision(
                        action="open_website",
                        parameters={"site": site},
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

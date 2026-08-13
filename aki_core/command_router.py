"""
AKI Command Router

Responsible only for:
- receiving raw user commands
- normalizing input
- identifying basic command intent
- returning a structured Command object

IMPORTANT:
This module does NOT execute commands.
It does NOT access the operating system.
It does NOT launch applications.
It does NOT modify files.

Execution will be handled by a separate, permission-controlled
executor layer later.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re


class CommandIntent(str, Enum):
    """Supported command intents."""

    OPEN_APPLICATION = "open_application"
    SYSTEM_INFORMATION = "system_information"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Command:
    """
    Structured representation of a user command.

    Attributes:
        raw_text: Original user input.
        normalized_text: Cleaned version of the input.
        intent: Detected command intent.
        target: Optional target associated with the intent.
        confidence: Basic router confidence from 0.0 to 1.0.
    """

    raw_text: str
    normalized_text: str
    intent: CommandIntent
    target: str | None = None
    confidence: float = 0.0


class CommandRouter:
    """
    Converts raw user text into structured commands.

    The router deliberately has NO execution capabilities.
    """

    _APPLICATION_ALIASES = {
        "vscode": "vscode",
        "vs code": "vscode",
        "visual studio code": "vscode",
        "code": "vscode",
    }

    _SYSTEM_TARGETS = {
        "cpu": "cpu",
        "processor": "cpu",
        "ram": "ram",
        "memory": "ram",
        "gpu": "gpu",
        "system": "system",
    }

    def route(self, text: str) -> Command:
        """
        Analyze a raw command and return a structured Command.

        No action is executed here.
        """

        raw_text = text if isinstance(text, str) else str(text)
        normalized = self._normalize(raw_text)

        if not normalized:
            return Command(
                raw_text=raw_text,
                normalized_text=normalized,
                intent=CommandIntent.UNKNOWN,
                confidence=1.0,
            )

        application = self._detect_application(normalized)

        if application is not None:
            return Command(
                raw_text=raw_text,
                normalized_text=normalized,
                intent=CommandIntent.OPEN_APPLICATION,
                target=application,
                confidence=0.95,
            )

        system_target = self._detect_system_information(normalized)

        if system_target is not None:
            return Command(
                raw_text=raw_text,
                normalized_text=normalized,
                intent=CommandIntent.SYSTEM_INFORMATION,
                target=system_target,
                confidence=0.90,
            )

        return Command(
            raw_text=raw_text,
            normalized_text=normalized,
            intent=CommandIntent.UNKNOWN,
            target=None,
            confidence=0.50,
        )

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize whitespace and casing without changing the original input."""

        text = text.strip().lower()
        text = re.sub(r"\s+", " ", text)

        return text

    def _detect_application(self, text: str) -> str | None:
        """Detect simple application-opening requests."""

        patterns = (
            r"^open\s+(.+)$",
            r"^launch\s+(.+)$",
            r"^start\s+(.+)$",
            r"^run\s+(.+)$",
        )

        for pattern in patterns:
            match = re.match(pattern, text)

            if not match:
                continue

            requested_app = match.group(1).strip()

            return self._APPLICATION_ALIASES.get(requested_app)

        return None

    def _detect_system_information(self, text: str) -> str | None:
        """Detect basic system-information requests."""

        information_patterns = (
            r"^(?:what is|what's|show|get|check)\s+(?:my\s+)?(.+?)\s*(?:usage|information|info|status)?$",
            r"^(?:check|show|get)\s+(?:system\s+)?(.+)$",
        )

        for pattern in information_patterns:
            match = re.match(pattern, text)

            if not match:
                continue

            requested_target = match.group(1).strip()

            target = self._SYSTEM_TARGETS.get(requested_target)

            if target is not None:
                return target

        return None


__all__ = [
    "Command",
    "CommandIntent",
    "CommandRouter",
]
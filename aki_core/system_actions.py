"""
AKI System Actions.

Assembles AKI's default action stack: the built-in action catalog,
its permission levels, and the executable handlers behind them.

Handlers here use only safe, explicit mechanisms:
    - Resolved application executables (never raw shell strings).
    - The standard library web browser opener for websites.
    - Read-only system information via psutil.

Destructive or sensitive actions are registered but intentionally
disabled until their phases are implemented.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import webbrowser
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

import psutil

from .action_registry import ActionCategory, ActionDefinition, ActionRegistry
from .command_executor import CommandExecutor, ExecutionResult
from .confirmation_manager import ConfirmationManager
from .permission_manager import PermissionLevel, PermissionManager


# ============================================================
# Built-in action catalog (metadata only)
# ============================================================

BUILTIN_ACTIONS: Final[tuple[ActionDefinition, ...]] = (
    ActionDefinition(
        name="open_application",
        description="Open a known desktop application by name.",
        category=ActionCategory.APPLICATION,
    ),
    ActionDefinition(
        name="open_website",
        description="Open a website in the default browser.",
        category=ActionCategory.BROWSER,
    ),
    ActionDefinition(
        name="take_screenshot",
        description="Capture the current screen.",
        category=ActionCategory.SYSTEM,
    ),
    ActionDefinition(
        name="get_system_info",
        description="Report live CPU, RAM, and uptime information.",
        category=ActionCategory.INFORMATION,
    ),
    ActionDefinition(
        name="search_files",
        description="Search files across the user's machine.",
        category=ActionCategory.FILE,
        enabled=False,
    ),
    ActionDefinition(
        name="system_cleanup",
        description="Clean temporary files and optimize the system.",
        category=ActionCategory.SYSTEM,
        requires_confirmation=True,
        enabled=False,
    ),
    ActionDefinition(
        name="start_recording",
        description="Start screen or audio recording.",
        category=ActionCategory.AUTOMATION,
        requires_confirmation=True,
        enabled=False,
    ),
)

_ACTION_PERMISSION_LEVELS: Final[dict[str, PermissionLevel]] = {
    "open_application": PermissionLevel.USER_ACTION,
    "open_website": PermissionLevel.USER_ACTION,
    "take_screenshot": PermissionLevel.READ_ONLY,
    "get_system_info": PermissionLevel.READ_ONLY,
}


# ============================================================
# Application resolution (Windows-first, PATH-aware)
# ============================================================

_APPLICATION_ALIASES: Final[dict[str, str]] = {
    "code": "vscode",
    "vs code": "vscode",
    "vscode": "vscode",
    "visual studio code": "vscode",
    "chrome": "chrome",
    "google chrome": "chrome",
    "notepad": "notepad",
    "calculator": "calculator",
    "calc": "calculator",
    "explorer": "explorer",
    "file explorer": "explorer",
    "files": "explorer",
    "cmd": "cmd",
    "command prompt": "cmd",
}

_APPLICATION_CANDIDATES: Final[dict[str, tuple[str, ...]]] = {
    "vscode": (
        r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
        r"%ProgramFiles%\Microsoft VS Code\Code.exe",
        "code",
    ),
    "chrome": (
        r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
        r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
        r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
        "chrome",
    ),
    "notepad": ("notepad",),
    "calculator": ("calc",),
    "explorer": ("explorer",),
    "cmd": ("cmd",),
}


def resolve_application(target: str) -> Path | None:
    """Resolve an application alias to an executable path."""

    if not isinstance(target, str) or not target.strip():
        return None

    normalized = target.strip().lower()
    canonical = _APPLICATION_ALIASES.get(normalized, normalized)

    candidates = _APPLICATION_CANDIDATES.get(canonical, ())
    if not candidates:
        return None

    for candidate in candidates:
        expanded = Path(os.path.expandvars(candidate))
        if expanded.exists():
            return expanded

        located = shutil.which(candidate)
        if located:
            return Path(located)

    return None


def _handle_open_application(*, target: str = "") -> dict[str, str]:
    """Launch a resolved desktop application."""

    resolved = resolve_application(target)

    if resolved is None:
        raise FileNotFoundError(
            f"'{target}' is not a known application on this machine."
        )

    subprocess.Popen([str(resolved)])  # noqa: S603 - fixed executable path
    return {"application": target, "executable": str(resolved)}


_KNOWN_SITES: Final[dict[str, str]] = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "whatsapp": "https://web.whatsapp.com",
}


def _handle_open_website(*, site: str = "") -> dict[str, str]:
    """Open a known website in the default browser."""

    key = site.strip().lower()
    url = _KNOWN_SITES.get(key, "")

    if not url:
        raise ValueError(f"'{site}' is not a known website shortcut.")

    webbrowser.open(url)
    return {"site": key, "url": url}


def _handle_get_system_info() -> dict[str, Any]:
    """Return a small read-only telemetry snapshot."""

    memory = psutil.virtual_memory()

    return {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "ram_percent": memory.percent,
        "ram_used_gb": round(memory.used / (1024 ** 3), 1),
        "ram_total_gb": round(memory.total / (1024 ** 3), 1),
        "local_time": datetime.now().strftime("%H:%M:%S"),
        "utc_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


# ============================================================
# Stack assembly
# ============================================================


@dataclass(frozen=True)
class ActionSystem:
    """The complete, wired action stack for one AKI process."""

    registry: ActionRegistry
    permissions: PermissionManager
    confirmations: ConfirmationManager
    executor: CommandExecutor

    def run(self, action_name: str, **parameters: Any) -> ExecutionResult:
        """Convenience passthrough to the executor."""
        return self.executor.execute(action_name, **parameters)


def build_action_system() -> ActionSystem:
    """
    Build and wire AKI's default action stack.
    """

    registry = ActionRegistry(BUILTIN_ACTIONS)

    permissions = PermissionManager(
        registry,
        default_level=PermissionLevel.READ_ONLY,
    )
    for action_name, level in _ACTION_PERMISSION_LEVELS.items():
        permissions.set_action_level(action_name, level)

    confirmations = ConfirmationManager()

    executor = CommandExecutor(registry, permissions, confirmations)
    executor.register_handler("open_application", _handle_open_application)
    executor.register_handler("open_website", _handle_open_website)
    # take_screenshot is intentionally unregistered here: the GUI layer
    # owns real screen capture and registers its own implementation.
    executor.register_handler("get_system_info", _handle_get_system_info)

    return ActionSystem(
        registry=registry,
        permissions=permissions,
        confirmations=confirmations,
        executor=executor,
    )


__all__ = [
    "ActionSystem",
    "BUILTIN_ACTIONS",
    "build_action_system",
    "resolve_application",
]

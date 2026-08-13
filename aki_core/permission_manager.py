"""
AKI Permission Manager

Controls whether an AKI action is allowed to proceed.

IMPORTANT:
This module does NOT execute actions.

It only evaluates permissions.

Execution must happen later through a separate,
controlled executor layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .action_registry import ActionDefinition, ActionRegistry


class PermissionLevel(str, Enum):
    """
    Permission levels available to AKI.

    Higher levels represent progressively more powerful
    system capabilities.
    """

    NONE = "none"
    READ_ONLY = "read_only"
    USER_ACTION = "user_action"
    SYSTEM_ACTION = "system_action"
    ADMIN_ACTION = "admin_action"


@dataclass(frozen=True)
class PermissionDecision:
    """
    Result of a permission check.
    """

    allowed: bool
    requires_confirmation: bool
    reason: str
    action: str
    level: PermissionLevel


class PermissionManager:
    """
    Evaluates whether an action is permitted.

    This class intentionally contains no execution logic.
    """

    def __init__(
        self,
        registry: ActionRegistry,
        default_level: PermissionLevel = PermissionLevel.READ_ONLY,
    ) -> None:
        self._registry = registry
        self._default_level = default_level

        self._action_levels: dict[str, PermissionLevel] = {}

    @property
    def default_level(self) -> PermissionLevel:
        """Return the default permission level."""

        return self._default_level

    def set_default_level(self, level: PermissionLevel) -> None:
        """Change the default permission level."""

        if not isinstance(level, PermissionLevel):
            raise TypeError(
                "level must be a PermissionLevel."
            )

        self._default_level = level

    def set_action_level(
        self,
        action_name: str,
        level: PermissionLevel,
    ) -> None:
        """
        Assign a specific permission level to an action.
        """

        if not isinstance(level, PermissionLevel):
            raise TypeError(
                "level must be a PermissionLevel."
            )

        action = self._registry.get(action_name)

        if action is None:
            raise ValueError(
                f"Unknown AKI action: {action_name}"
            )

        self._action_levels[action.name] = level

    def get_action_level(
        self,
        action_name: str,
    ) -> PermissionLevel:
        """Return the permission level assigned to an action."""

        normalized = self._normalize(action_name)

        return self._action_levels.get(
            normalized,
            self._default_level,
        )

    def check(
        self,
        action_name: str,
    ) -> PermissionDecision:
        """
        Evaluate whether an action is allowed.

        No action is executed.
        """

        action = self._registry.get(action_name)

        if action is None:
            return PermissionDecision(
                allowed=False,
                requires_confirmation=False,
                reason="Action is not registered.",
                action=self._normalize(action_name),
                level=PermissionLevel.NONE,
            )

        if not action.enabled:
            return PermissionDecision(
                allowed=False,
                requires_confirmation=False,
                reason="Action is currently disabled.",
                action=action.name,
                level=PermissionLevel.NONE,
            )

        level = self.get_action_level(action.name)

        if level == PermissionLevel.NONE:
            return PermissionDecision(
                allowed=False,
                requires_confirmation=False,
                reason="Permission level does not allow this action.",
                action=action.name,
                level=level,
            )

        return PermissionDecision(
            allowed=True,
            requires_confirmation=action.requires_confirmation,
            reason="Action is permitted.",
            action=action.name,
            level=level,
        )

    def revoke(self, action_name: str) -> None:
        """
        Completely revoke an action's permission.
        """

        normalized = self._normalize(action_name)

        self._action_levels[normalized] = PermissionLevel.NONE

    def reset_action(self, action_name: str) -> None:
        """
        Remove a custom permission and return the action
        to the default permission level.
        """

        normalized = self._normalize(action_name)

        self._action_levels.pop(normalized, None)

    @staticmethod
    def _normalize(action_name: str) -> str:
        """Normalize an action name."""

        if not isinstance(action_name, str):
            raise TypeError(
                "Action name must be a string."
            )

        return action_name.strip().lower()


__all__ = [
    "PermissionDecision",
    "PermissionLevel",
    "PermissionManager",
]
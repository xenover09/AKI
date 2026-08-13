"""
AKI Action Registry

The Action Registry defines the actions that AKI understands.

IMPORTANT:
This module does NOT execute actions.

It only:
- defines action metadata
- registers actions
- retrieves registered actions
- checks whether an action exists

Actual execution will be handled later by a separate,
permission-controlled Command Executor.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class ActionCategory(str, Enum):
    """High-level category of an AKI action."""

    APPLICATION = "application"
    SYSTEM = "system"
    FILE = "file"
    BROWSER = "browser"
    INFORMATION = "information"
    AUTOMATION = "automation"


@dataclass(frozen=True)
class ActionDefinition:
    """
    Describes an action available to AKI.

    This is metadata only. It does not contain executable code.
    """

    name: str
    description: str
    category: ActionCategory
    requires_confirmation: bool = False
    enabled: bool = True


class ActionRegistry:
    """
    Central registry for AKI actions.

    The registry deliberately contains no execution logic.
    """

    def __init__(
        self,
        actions: Iterable[ActionDefinition] | None = None,
    ) -> None:
        self._actions: dict[str, ActionDefinition] = {}

        if actions is not None:
            for action in actions:
                self.register(action)

    def register(self, action: ActionDefinition) -> None:
        """
        Register an action.

        Raises:
            TypeError: If the supplied value is not an ActionDefinition.
            ValueError: If the action name is invalid or already registered.
        """

        if not isinstance(action, ActionDefinition):
            raise TypeError(
                "action must be an ActionDefinition instance"
            )

        name = action.name.strip().lower()

        if not name:
            raise ValueError("Action name cannot be empty.")

        if name in self._actions:
            raise ValueError(
                f"Action '{name}' is already registered."
            )

        self._actions[name] = ActionDefinition(
            name=name,
            description=action.description.strip(),
            category=action.category,
            requires_confirmation=action.requires_confirmation,
            enabled=action.enabled,
        )

    def unregister(self, name: str) -> bool:
        """
        Remove an action from the registry.

        Returns:
            True if the action existed and was removed.
            False if it was not registered.
        """

        normalized_name = self._normalize_name(name)

        if normalized_name not in self._actions:
            return False

        del self._actions[normalized_name]
        return True

    def get(self, name: str) -> ActionDefinition | None:
        """Return an action definition by name."""

        return self._actions.get(self._normalize_name(name))

    def exists(self, name: str) -> bool:
        """Check whether an action is registered."""

        return self._normalize_name(name) in self._actions

    def is_enabled(self, name: str) -> bool:
        """Check whether an action exists and is currently enabled."""

        action = self.get(name)

        return action is not None and action.enabled

    def list_actions(self) -> tuple[ActionDefinition, ...]:
        """Return all registered actions as an immutable tuple."""

        return tuple(self._actions.values())

    def list_enabled_actions(self) -> tuple[ActionDefinition, ...]:
        """Return only enabled actions."""

        return tuple(
            action
            for action in self._actions.values()
            if action.enabled
        )

    def clear(self) -> None:
        """Remove all registered actions."""

        self._actions.clear()

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normalize an action name."""

        if not isinstance(name, str):
            raise TypeError("Action name must be a string.")

        return name.strip().lower()


__all__ = [
    "ActionCategory",
    "ActionDefinition",
    "ActionRegistry",
]
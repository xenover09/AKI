"""
AKI Command Executor

Executes only explicitly registered and supported actions.

IMPORTANT:
- No arbitrary shell commands.
- No direct user-provided command execution.
- No os.system().
- No unrestricted subprocess execution.
- Permission and confirmation checks happen before execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

from .action_registry import ActionRegistry
from .confirmation_manager import ConfirmationManager
from .permission_manager import PermissionManager


class ExecutionStatus(str, Enum):
    """Possible execution outcomes."""

    SUCCESS = "success"
    DENIED = "denied"
    CONFIRMATION_REQUIRED = "confirmation_required"
    NOT_FOUND = "not_found"
    DISABLED = "disabled"
    NOT_IMPLEMENTED = "not_implemented"
    FAILED = "failed"


@dataclass(frozen=True)
class ExecutionResult:
    """Structured result returned by the executor."""

    status: ExecutionStatus
    action: str
    message: str
    data: Any = None
    confirmation_id: str | None = None


ActionHandler = Callable[..., Any]


class CommandExecutor:
    """
    Controlled execution layer for AKI actions.

    Only handlers explicitly registered through register_handler()
    can ever be executed.
    """

    def __init__(
        self,
        registry: ActionRegistry,
        permission_manager: PermissionManager,
        confirmation_manager: ConfirmationManager,
    ) -> None:
        self._registry = registry
        self._permissions = permission_manager
        self._confirmations = confirmation_manager

        self._handlers: dict[str, ActionHandler] = {}

    def register_handler(
        self,
        action_name: str,
        handler: ActionHandler,
    ) -> None:
        """
        Register an implementation for an existing action.

        The action must already exist in ActionRegistry.
        """

        if not callable(handler):
            raise TypeError(
                "handler must be callable."
            )

        action = self._registry.get(action_name)

        if action is None:
            raise ValueError(
                f"Cannot register handler for unknown action: "
                f"{action_name}"
            )

        if action.name in self._handlers:
            raise ValueError(
                f"Handler already registered for: {action.name}"
            )

        self._handlers[action.name] = handler

    def unregister_handler(
        self,
        action_name: str,
    ) -> bool:
        """Remove an action handler."""

        name = self._normalize(action_name)

        if name not in self._handlers:
            return False

        del self._handlers[name]
        return True

    def has_handler(
        self,
        action_name: str,
    ) -> bool:
        """Check whether an executable handler exists."""

        return self._normalize(action_name) in self._handlers

    def execute(
        self,
        action_name: str,
        *,
        confirmation_id: str | None = None,
        **parameters: Any,
    ) -> ExecutionResult:
        """
        Execute a registered action after permission checks.

        No arbitrary command execution is supported.
        """

        name = self._normalize(action_name)

        action = self._registry.get(name)

        if action is None:
            return ExecutionResult(
                status=ExecutionStatus.NOT_FOUND,
                action=name,
                message=f"Unknown AKI action: {name}",
            )

        if not action.enabled:
            return ExecutionResult(
                status=ExecutionStatus.DISABLED,
                action=name,
                message=f"Action '{name}' is disabled.",
            )

        permission = self._permissions.check(name)

        if not permission.allowed:
            return ExecutionResult(
                status=ExecutionStatus.DENIED,
                action=name,
                message=permission.reason,
            )

        if permission.requires_confirmation:
            if confirmation_id is None:
                request = self._confirmations.create_request(
                    action=name,
                    reason=(
                        f"AKI requires your confirmation before "
                        f"executing '{name}'."
                    ),
                )

                return ExecutionResult(
                    status=ExecutionStatus.CONFIRMATION_REQUIRED,
                    action=name,
                    message=(
                        "User confirmation is required "
                        "before this action can execute."
                    ),
                    confirmation_id=request.request_id,
                )

            if not self._confirmations.is_approved(
                confirmation_id
            ):
                return ExecutionResult(
                    status=ExecutionStatus.DENIED,
                    action=name,
                    message=(
                        "The supplied confirmation has not "
                        "been approved."
                    ),
                    confirmation_id=confirmation_id,
                )

        handler = self._handlers.get(name)

        if handler is None:
            return ExecutionResult(
                status=ExecutionStatus.NOT_IMPLEMENTED,
                action=name,
                message=(
                    f"Action '{name}' is registered but "
                    "has no execution handler yet."
                ),
            )

        try:
            result = handler(**parameters)

        except Exception as exc:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                action=name,
                message=(
                    f"Action '{name}' failed during execution."
                ),
                data={
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
                confirmation_id=confirmation_id,
            )

        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            action=name,
            message=(
                f"Action '{name}' executed successfully."
            ),
            data=result,
            confirmation_id=confirmation_id,
        )

    @staticmethod
    def _normalize(action_name: str) -> str:
        """Normalize an action name."""

        if not isinstance(action_name, str):
            raise TypeError(
                "Action name must be a string."
            )

        return action_name.strip().lower()


__all__ = [
    "ActionHandler",
    "CommandExecutor",
    "ExecutionResult",
    "ExecutionStatus",
]
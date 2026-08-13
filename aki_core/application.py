"""
Application orchestration for AKI.

Application is the composition root for the core AKI runtime.

Responsibilities:
- Own the BootManager.
- Own the core command-system components.
- Initialize the application runtime.
- Expose the command router to higher-level presentation layers.
- Report boot status.

Important:
Application does NOT execute operating-system actions directly.
Actual execution remains behind the controlled CommandExecutor.
"""

from __future__ import annotations

import sys
from pathlib import Path

from aki_core.action_registry import ActionRegistry
from aki_core.boot import BootError, BootManager, BootResult
from aki_core.command_executor import CommandExecutor
from aki_core.command_router import CommandRouter
from aki_core.confirmation_manager import ConfirmationManager
from aki_core.permission_manager import PermissionManager


class Application:
    """
    Top-level orchestrator for AKI.

    Application acts as the composition root.

    It creates and connects AKI's core components but does not
    contain business logic or operating-system execution logic.
    """

    def __init__(self, project_root: Path) -> None:
        """
        Initialize the AKI application.

        Args:
            project_root:
                Absolute path to the AKI source root.
        """

        self._project_root = project_root

        # ---------------------------------------------------------
        # Boot
        # ---------------------------------------------------------

        self._boot_manager = BootManager(
            project_root=project_root
        )

        self._boot_result: BootResult | None = None

        # ---------------------------------------------------------
        # Command System
        # ---------------------------------------------------------

        self._action_registry = ActionRegistry()

        self._permission_manager = PermissionManager(
            registry=self._action_registry
        )

        self._confirmation_manager = ConfirmationManager()

        self._command_router = CommandRouter()

        self._command_executor = CommandExecutor(
            registry=self._action_registry,
            permission_manager=self._permission_manager,
            confirmation_manager=self._confirmation_manager,
        )

    # =============================================================
    # Boot
    # =============================================================

    def initialize(self) -> BootResult:
        """
        Run AKI's complete boot sequence.

        Returns:
            BootResult produced by BootManager.

        Raises:
            BootError:
                If a critical boot stage fails.
        """

        self._boot_result = self._boot_manager.boot()

        return self._boot_result

    # =============================================================
    # Command System Access
    # =============================================================

    @property
    def command_router(self) -> CommandRouter:
        """
        Return AKI's command router.

        Higher-level interfaces such as the desktop UI or
        future voice interface can submit commands through it.
        """

        return self._command_router

    @property
    def action_registry(self) -> ActionRegistry:
        """Return AKI's action registry."""

        return self._action_registry

    @property
    def permission_manager(self) -> PermissionManager:
        """Return AKI's permission manager."""

        return self._permission_manager

    @property
    def confirmation_manager(self) -> ConfirmationManager:
        """Return AKI's confirmation manager."""

        return self._confirmation_manager

    @property
    def command_executor(self) -> CommandExecutor:
        """
        Return the controlled command executor.

        No actions are executed merely by accessing this property.
        """

        return self._command_executor

    @property
    def boot_result(self) -> BootResult | None:
        """Return the latest boot result."""

        return self._boot_result

    # =============================================================
    # Application Runtime
    # =============================================================

    def run(self) -> int:
        """
        Run the application.

        Currently this ensures that the boot sequence completes.

        The desktop presentation layer will later take control
        after successful initialization.

        Returns:
            0:
                Successful startup.

            1:
                Boot failure.
        """

        try:
            if self._boot_result is None:
                self.initialize()

        except BootError as error:
            print(
                f"AKI failed to start: {error}",
                file=sys.stderr,
            )

            return 1

        return 0


__all__ = [
    "Application",
]
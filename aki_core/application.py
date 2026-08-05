"""
Application orchestration for AKI.

`Application` is the composition root's single entry point: it owns the
Boot Manager and reports whether AKI reached a ready state. All startup
logic lives in `BootManager` — `Application` never initializes a
subsystem itself, it only triggers and reports on the boot sequence.
"""

from __future__ import annotations

import sys
from pathlib import Path

from aki_core.boot import BootError, BootManager, BootResult


class Application:
    """
    Top-level orchestrator for AKI.

    `Application` delegates the entire startup sequence to the Boot
    Manager and exposes the resulting `BootResult` to whatever
    component takes over next. It does not yet own a GUI, domain
    services, or persistence — those are introduced as separate modules
    once the Boot Manager's foundation is approved.
    """

    def __init__(self, project_root: Path) -> None:
        """
        Initialize the Application.

        Args:
            project_root: Absolute path to the AKI source root, passed
                through to the Boot Manager.
        """
        self._project_root = project_root
        self._boot_manager = BootManager(project_root=project_root)
        self._boot_result: BootResult | None = None

    def initialize(self) -> BootResult:
        """
        Run AKI's full boot sequence via the Boot Manager.

        Returns:
            The `BootResult` produced by the Boot Manager.

        Raises:
            BootError: If a critical boot stage fails.
        """
        self._boot_result = self._boot_manager.boot()
        return self._boot_result

    def run(self) -> int:
        """
        Run the application.

        Ensures the boot sequence has completed, then returns a process
        exit code. Once presentation and domain modules exist, this
        method will hand control to them (e.g. starting the GUI event
        loop) after a successful boot.

        Returns:
            A process exit code: 0 on success, 1 if boot failed.
        """
        try:
            if self._boot_result is None:
                self.initialize()
        except BootError as error:
            print(f"AKI failed to start: {error}", file=sys.stderr)
            return 1

        return 0

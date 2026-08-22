"""
AKI Application.

Coordinates AKI's core runtime services.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai_engine import AIService
from aki_core.boot import BootResult
from conversation.service import ConversationService
from database.database_service import DatabaseService
from memory.memory_service import MemoryService


@dataclass(frozen=True)
class ApplicationResult:
    """
    Runtime services initialized by AKI.
    """

    boot: BootResult
    database_service: DatabaseService
    memory_service: MemoryService
    conversation_service: ConversationService
    ai_service: AIService | None


class Application:
    """
    Main application coordinator for AKI.

    The Application owns high-level services but does not
    contain their internal business logic.
    """

    def __init__(
        self,
        project_root: Path,
    ) -> None:
        if not isinstance(
            project_root,
            Path,
        ):
            raise TypeError(
                "project_root must be a pathlib.Path."
            )

        self._project_root = project_root
        self._database_service: DatabaseService | None = None
        self._memory_service: MemoryService | None = None
        self._conversation_service: ConversationService | None = None
        self._ai_service: AIService | None = None

    @property
    def project_root(self) -> Path:
        """Return the AKI project root."""

        return self._project_root

    @property
    def database_service(self) -> DatabaseService:
        """
        Return the initialized database service.
        """

        if self._database_service is None:
            raise RuntimeError(
                "Application has not been initialized."
            )

        return self._database_service

    @property
    def memory_service(self) -> MemoryService:
        """
        Return the initialized memory service.
        """

        if self._memory_service is None:
            raise RuntimeError(
                "Application has not been initialized."
            )

        return self._memory_service

    @property
    def conversation_service(self) -> ConversationService:
        """
        Return the initialized conversation service.
        """

        if self._conversation_service is None:
            raise RuntimeError(
                "Application has not been initialized."
            )

        return self._conversation_service

    @property
    def ai_service(self) -> AIService | None:
        """
        Return the initialized AI service, or None when the
        intelligence layer has no usable provider.
        """

        return self._ai_service

    def initialize(self) -> ApplicationResult:
        """
        Initialize AKI's runtime services.

        Service construction and initialization order are owned by
        the Boot Manager. This method runs the boot sequence and
        adopts the services it produced, so exactly one instance of
        each service exists per process.
        """

        boot = self._initialize_boot()

        self._database_service = boot.database_service
        self._memory_service = boot.memory_service
        self._conversation_service = boot.conversation_service
        self._ai_service = boot.ai_service

        return ApplicationResult(
            boot=boot,
            database_service=self._database_service,
            memory_service=self._memory_service,
            conversation_service=self._conversation_service,
            ai_service=self._ai_service,
        )

    def close(self) -> None:
        """
        Shut down initialized services cleanly.
        """

        if self._ai_service is not None:
            self._ai_service.close()

        if self._database_service is not None:
            self._database_service.close()

        self._conversation_service = None
        self._memory_service = None
        self._ai_service = None
        self._database_service = None

    def _initialize_boot(self) -> BootResult:
        """
        Initialize AKI's existing boot/runtime layer.

        This keeps the Application compatible with the
        existing AKI boot architecture.
        """

        from aki_core.boot import BootManager

        boot_manager = BootManager(
            self._project_root,
        )

        return boot_manager.boot()


__all__ = [
    "Application",
    "ApplicationResult",
]
"""
Boot orchestration for AKI.

The Boot Manager is the single startup controller for the entire
system. It runs a fixed, ordered sequence of boot stages and reports
the outcome of each one:

    1. Initialize Configuration Engine
    2. Initialize Logger
    3. Validate Runtime Environment
    4. Create Workspace Folders if Missing
    5. Initialize Database
    6. Initialize Memory
    7. Initialize Conversation
    8. Initialize Intelligence
    9. Display Boot Complete

No other module is permitted to reorder, skip, or duplicate this
sequence â€” every future subsystem AKI gains is wired in here, in the
order above, not scattered across `Application` or `main.py`.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from enum import Enum
from logging import Logger
from pathlib import Path

from ai_engine import AIService, MockProvider, OpenAICompatibleProvider
from config.constants import (
    AI_PROVIDER_MOCK,
    AI_PROVIDER_OPENAI_COMPATIBLE,
)
from config.manager import ConfigManager
from conversation.service import ConversationService
from database.database_service import DatabaseService
from memory.memory_service import MemoryService
from config.settings import Settings
from logs.logger import configure_logging

_MIN_PYTHON_VERSION: tuple[int, int] = (3, 12)


class BootStageStatus(str, Enum):
    """Outcome status of a single boot stage."""

    COMPLETED = "completed"
    PLACEHOLDER = "placeholder"


class BootError(Exception):
    """Raised when a critical boot stage fails and startup cannot continue."""


@dataclass(frozen=True, slots=True)
class BootStageResult:
    """
    Outcome of a single boot stage.

    Attributes:
        name: Human-readable name of the stage.
        status: Whether the stage completed normally or ran as a
            not-yet-implemented placeholder.
        detail: Optional human-readable detail about the outcome.
    """

    name: str
    status: BootStageStatus
    detail: str = ""


@dataclass(frozen=True, slots=True)
class WorkspaceLayout:
    """
    Filesystem layout for AKI's runtime workspace.

    Distinct from the Configuration Engine's `AppPaths`: `AppPaths`
    (see `config/paths.py`) stores *configuration*, `WorkspaceLayout`
    stores *runtime data* â€” the future database file, cached artifacts,
    and future subsystem state â€” rooted under that same
    platform-appropriate application directory.

    Attributes:
        workspace_dir: Root directory for all runtime workspace data.
        data_dir: General-purpose application data directory.
        cache_dir: Disposable cache directory.
        database_dir: Directory reserved for the future database engine.
        memory_dir: Directory reserved for the future memory subsystem.
    """

    workspace_dir: Path
    data_dir: Path
    cache_dir: Path
    database_dir: Path
    memory_dir: Path

    @classmethod
    def resolve(cls, root_dir: Path) -> "WorkspaceLayout":
        """
        Resolve the workspace layout beneath a given root directory.

        Args:
            root_dir: The application's root directory, as resolved by
                the Configuration Engine's `AppPaths`.

        Returns:
            A `WorkspaceLayout` with every subdirectory path computed.
        """
        workspace_dir = root_dir / "workspace"
        return cls(
            workspace_dir=workspace_dir,
            data_dir=workspace_dir / "data",
            cache_dir=workspace_dir / "cache",
            database_dir=workspace_dir / "database",
            memory_dir=workspace_dir / "memory",
        )

    def ensure_directories(self) -> None:
        """Create every workspace directory that does not yet exist."""
        for directory in (
            self.workspace_dir,
            self.data_dir,
            self.cache_dir,
            self.database_dir,
            self.memory_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True, slots=True)
class BootResult:
    """
    Full outcome of a completed boot sequence.

    Attributes:
        settings: Loaded infrastructure settings (environment, logging).
        config_manager: Initialized Configuration Engine.
        logger: Configured root logger for AKI.
        workspace: Resolved and created runtime workspace layout.
        stages: Ordered results of every boot stage that ran.
    """

    settings: Settings
    config_manager: ConfigManager
    logger: Logger
    workspace: WorkspaceLayout
    database_service: DatabaseService
    memory_service: MemoryService
    conversation_service: ConversationService
    ai_service: AIService | None
    stages: list[BootStageResult] = field(default_factory=list)


class BootManager:
    """
    Executes AKI's startup sequence in a fixed, well-defined order.

    The Boot Manager is the single startup controller for the entire
    system: nothing else in AKI is permitted to initialize the
    Configuration Engine, logger, workspace, or future subsystems
    independently.
    """

    def __init__(self, project_root: Path) -> None:
        """
        Initialize the Boot Manager.

        Args:
            project_root: Absolute path to the AKI source root. Used to
                resolve `.env` and other source-relative locations for
                `Settings`. This is distinct from the Configuration
                Engine's own data directory, which resolves to the
                platform's conventional application-data location.
        """
        self._project_root = project_root

    def boot(self) -> BootResult:
        """
        Run the full, fixed boot sequence.

        Returns:
            A `BootResult` describing every initialized subsystem and
            the outcome of each boot stage, in order.

        Raises:
            BootError: If a critical stage fails and startup cannot
                continue.
        """
        stages: list[BootStageResult] = []

        try:
            config_manager = self._init_configuration_engine()
            stages.append(
                BootStageResult("Configuration Engine", BootStageStatus.COMPLETED)
            )

            settings, logger = self._init_logger()
            stages.append(BootStageResult("Logger", BootStageStatus.COMPLETED))
        except Exception as error:
            # No logger exists yet if either stage above fails, so this
            # is the one place the Boot Manager reports failure without one.
            raise BootError(
                f"Failed to initialize configuration or logging: {error}"
            ) from error

        try:
            self._validate_runtime_environment(logger)
            stages.append(
                BootStageResult("Runtime Environment Validation", BootStageStatus.COMPLETED)
            )

            workspace = self._create_workspace_folders(config_manager, logger)
            stages.append(BootStageResult("Workspace Folders", BootStageStatus.COMPLETED))

            database_service, database_detail = self._init_database(workspace, logger)
            stages.append(
                BootStageResult("Database", BootStageStatus.COMPLETED, database_detail)
            )

            memory_service, memory_detail = self._init_memory(workspace, logger, database_service)
            stages.append(
                BootStageResult("Memory", BootStageStatus.COMPLETED, memory_detail)
            )

            conversation_service, conversation_detail = self._init_conversation(
                logger,
                database_service,
            )
            stages.append(
                BootStageResult(
                    "Conversation",
                    BootStageStatus.COMPLETED,
                    conversation_detail,
                )
            )

            ai_service, intelligence_detail, intelligence_status = (
                self._init_intelligence(settings, logger)
            )
            stages.append(
                BootStageResult(
                    "Intelligence",
                    intelligence_status,
                    intelligence_detail,
                )
            )
        except BootError:
            raise
        except Exception as error:
            logger.critical("Boot sequence failed: %s", error)
            raise BootError(str(error)) from error

        result = BootResult(
            settings=settings,
            config_manager=config_manager,
            logger=logger,
            workspace=workspace,
            database_service=database_service,
            memory_service=memory_service,
            conversation_service=conversation_service,
            ai_service=ai_service,
            stages=stages,
        )
        self._display_boot_complete(result)
        return result

    def _init_configuration_engine(self) -> ConfigManager:
        """
        Stage 1 â€” Initialize the Configuration Engine.

        Returns:
            An initialized `ConfigManager`. Its own constructor already
            guarantees required folders and `default.json` exist.
        """
        return ConfigManager()

    def _init_logger(self) -> tuple[Settings, Logger]:
        """
        Stage 2 â€” Load infrastructure settings and initialize the logger.

        Returns:
            A tuple of the loaded `Settings` and the configured root
            "AKI" logger.
        """
        settings = Settings.load(self._project_root)
        logger = configure_logging(settings)
        logger.info(
            "Logger initialized | level=%s | dir=%s", settings.log_level, settings.log_dir
        )
        return settings, logger

    def _validate_runtime_environment(self, logger: Logger) -> None:
        """
        Stage 3 â€” Validate that the runtime environment meets AKI's
        minimum requirements.

        Args:
            logger: The configured logger, used to report the outcome.

        Raises:
            BootError: If the running Python interpreter is older than
                AKI's minimum supported version.
        """
        if sys.version_info[:2] < _MIN_PYTHON_VERSION:
            required = f"{_MIN_PYTHON_VERSION[0]}.{_MIN_PYTHON_VERSION[1]}"
            found = f"{sys.version_info.major}.{sys.version_info.minor}"
            message = f"AKI requires Python {required}+ but found {found}."
            logger.critical(message)
            raise BootError(message)

        from scripts.check_dependencies import find_missing_dependencies, format_startup_error
        missing = find_missing_dependencies()
        if missing:
            err = format_startup_error(missing)
            logger.critical("Missing third-party dependencies during boot: %s", missing)
            raise BootError(err)

        logger.info(
            "Runtime environment validated | python=%s.%s.%s | platform=%s",
            sys.version_info.major,
            sys.version_info.minor,
            sys.version_info.micro,
            sys.platform,
        )

    def _create_workspace_folders(
        self, config_manager: ConfigManager, logger: Logger
    ) -> WorkspaceLayout:
        """
        Stage 4 â€” Create AKI's runtime workspace folders if missing.

        Args:
            config_manager: The initialized Configuration Engine, used
                to anchor the workspace beneath its resolved root
                directory.
            logger: The configured logger, used to report the outcome.

        Returns:
            The resolved `WorkspaceLayout`, with all directories present.
        """
        workspace = WorkspaceLayout.resolve(config_manager.paths.root_dir)
        workspace.ensure_directories()
        logger.info("Workspace folders ready | root=%s", workspace.workspace_dir)
        return workspace

    def _init_database(
        self,
        workspace: WorkspaceLayout,
        logger: Logger,
    ) -> tuple[DatabaseService, str]:
        """
        Stage 5 - Initialize AKI's SQLite database.
        """

        database_path = workspace.database_dir / "aki.db"

        database_service = DatabaseService(database_path)
        database_service.initialize()

        detail = (
            f"Database initialized | "
            f"path={database_path}"
        )

        logger.info(detail)

        return database_service, detail

    def _init_memory(
        self,
        workspace: WorkspaceLayout,
        logger: Logger,
        database_service: DatabaseService,
    ) -> tuple[MemoryService, str]:
        """
        Stage 6 - Initialize AKI's memory subsystem.
        """

        memory_service = MemoryService(database_service)

        detail = (
            f"Memory subsystem initialized | "
            f"workspace={workspace.memory_dir}"
        )

        logger.info(detail)

        return memory_service, detail

    def _init_conversation(
        self,
        logger: Logger,
        database_service: DatabaseService,
    ) -> tuple[ConversationService, str]:
        """
        Stage 7 - Initialize AKI's conversation subsystem.
        """

        conversation_service = ConversationService(database_service)

        detail = "Conversation subsystem initialized"

        logger.info(detail)

        return conversation_service, detail

    def _init_intelligence(
        self,
        settings: Settings,
        logger: Logger,
    ) -> tuple[AIService | None, str, BootStageStatus]:
        """
        Stage 8 - Initialize AKI's intelligence subsystem.

        Intelligence is optional at boot: without a usable provider
        the stage reports PLACEHOLDER and `ai_service` stays None so
        the rest of AKI keeps working offline.

        Returns:
            A tuple of (service or None, log detail, stage status).
        """

        if settings.ai_provider == AI_PROVIDER_MOCK:
            ai_service = AIService(MockProvider())
            detail = (
                "Intelligence initialized | "
                f"provider={AI_PROVIDER_MOCK}"
            )

            logger.info(detail)
            return ai_service, detail, BootStageStatus.COMPLETED

        if settings.ai_provider == AI_PROVIDER_OPENAI_COMPATIBLE:
            if not settings.ai_api_key:
                detail = (
                    "Intelligence not configured | "
                    f"provider={AI_PROVIDER_OPENAI_COMPATIBLE} | "
                    "set AKI_AI_API_KEY to enable"
                )
                logger.warning(detail)
                return None, detail, BootStageStatus.PLACEHOLDER

            provider = OpenAICompatibleProvider(
                base_url=settings.ai_base_url,
                api_key=settings.ai_api_key,
                model=settings.ai_model,
                timeout_seconds=settings.ai_timeout_seconds,
            )
            ai_service = AIService(provider)

            detail = (
                "Intelligence initialized | "
                f"provider={AI_PROVIDER_OPENAI_COMPATIBLE} | "
                f"model={settings.ai_model}"
            )

            logger.info(detail)
            return ai_service, detail, BootStageStatus.COMPLETED

        detail = (
            f"Unknown AI provider '{settings.ai_provider}' | "
            f"falling back to {AI_PROVIDER_MOCK}"
        )
        logger.warning(detail)

        ai_service = AIService(MockProvider())
        return (
            ai_service,
            f"{detail} | fallback active",
            BootStageStatus.COMPLETED,
        )

    def _display_boot_complete(self, result: BootResult) -> None:
        """
        Stage 7 â€” Display a summary confirming boot completion.

        Args:
            result: The full boot result, used to render a per-stage
                summary.
        """
        result.logger.info("=" * 48)
        result.logger.info("AKI Boot Complete")
        for stage in result.stages:
            result.logger.info(" - %-32s [%s]", stage.name, stage.status.value.upper())
        result.logger.info("=" * 48)


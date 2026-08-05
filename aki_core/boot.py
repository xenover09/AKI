"""
Boot orchestration for AKI.

The Boot Manager is the single startup controller for the entire
system. It runs a fixed, ordered sequence of boot stages and reports
the outcome of each one:

    1. Initialize Configuration Engine
    2. Initialize Logger
    3. Validate Runtime Environment
    4. Create Workspace Folders if Missing
    5. Initialize Database (placeholder only)
    6. Initialize Memory (placeholder only)
    7. Display Boot Complete

No other module is permitted to reorder, skip, or duplicate this
sequence — every future subsystem AKI gains is wired in here, in the
order above, not scattered across `Application` or `main.py`.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from enum import Enum
from logging import Logger
from pathlib import Path

from config.manager import ConfigManager
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
    stores *runtime data* — the future database file, cached artifacts,
    and future subsystem state — rooted under that same
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

            database_detail = self._init_database_placeholder(workspace, logger)
            stages.append(
                BootStageResult("Database", BootStageStatus.PLACEHOLDER, database_detail)
            )

            memory_detail = self._init_memory_placeholder(workspace, logger)
            stages.append(
                BootStageResult("Memory", BootStageStatus.PLACEHOLDER, memory_detail)
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
            stages=stages,
        )
        self._display_boot_complete(result)
        return result

    def _init_configuration_engine(self) -> ConfigManager:
        """
        Stage 1 — Initialize the Configuration Engine.

        Returns:
            An initialized `ConfigManager`. Its own constructor already
            guarantees required folders and `default.json` exist.
        """
        return ConfigManager()

    def _init_logger(self) -> tuple[Settings, Logger]:
        """
        Stage 2 — Load infrastructure settings and initialize the logger.

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
        Stage 3 — Validate that the runtime environment meets AKI's
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
        Stage 4 — Create AKI's runtime workspace folders if missing.

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

    def _init_database_placeholder(self, workspace: WorkspaceLayout, logger: Logger) -> str:
        """
        Stage 5 — Reserve the database location. No database engine is
        wired in yet; this stage exists so the boot sequence has a fixed
        slot for it when it is implemented.

        Args:
            workspace: The resolved workspace layout.
            logger: The configured logger, used to report the outcome.

        Returns:
            A human-readable detail string describing the placeholder.
        """
        detail = f"Reserved at {workspace.database_dir} — no database engine implemented yet."
        logger.info("Database initialization is a placeholder | %s", detail)
        return detail

    def _init_memory_placeholder(self, workspace: WorkspaceLayout, logger: Logger) -> str:
        """
        Stage 6 — Reserve the memory subsystem location. No memory
        subsystem is wired in yet; this stage exists so the boot
        sequence has a fixed slot for it when it is implemented.

        Args:
            workspace: The resolved workspace layout.
            logger: The configured logger, used to report the outcome.

        Returns:
            A human-readable detail string describing the placeholder.
        """
        detail = f"Reserved at {workspace.memory_dir} — no memory subsystem implemented yet."
        logger.info("Memory initialization is a placeholder | %s", detail)
        return detail

    def _display_boot_complete(self, result: BootResult) -> None:
        """
        Stage 7 — Display a summary confirming boot completion.

        Args:
            result: The full boot result, used to render a per-stage
                summary.
        """
        result.logger.info("=" * 48)
        result.logger.info("AKI Boot Complete")
        for stage in result.stages:
            result.logger.info(" - %-32s [%s]", stage.name, stage.status.value.upper())
        result.logger.info("=" * 48)

"""
Runtime configuration for AKI.

`Settings` is an immutable representation of every environment-dependent
value AKI needs at startup. It is loaded exactly once by the Boot
Manager and then passed explicitly to any component that needs it
(constructor injection). No part of the system other than this module
is permitted to read `os.environ` directly — this keeps configuration
centralized, testable, and mockable.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from config.constants import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_ENVIRONMENT,
    DEFAULT_LOG_DIR,
    DEFAULT_LOG_LEVEL,
    ENV_FILE_NAME,
)


@dataclass(frozen=True, slots=True)
class Settings:
    """
    Immutable snapshot of AKI's runtime configuration.

    Attributes:
        app_name: Human-readable application name.
        app_version: Semantic version of the running application.
        environment: Deployment environment ("development", "production", etc.).
        log_level: Minimum log severity to record (e.g. "DEBUG", "INFO").
        log_dir: Absolute directory where log files are written.
        debug: Whether AKI is running in debug mode.
    """

    app_name: str
    app_version: str
    environment: str
    log_level: str
    log_dir: Path
    debug: bool

    @classmethod
    def load(cls, project_root: Path) -> "Settings":
        """
        Build a `Settings` instance from environment variables and `.env`.

        Args:
            project_root: Absolute path to the AKI project root. Used to
                resolve the `.env` file location and any relative paths
                such as `log_dir`.

        Returns:
            A fully populated, immutable `Settings` instance.
        """
        env_file = project_root / ENV_FILE_NAME
        if env_file.exists():
            load_dotenv(dotenv_path=env_file)

        environment = os.getenv("AKI_ENVIRONMENT", DEFAULT_ENVIRONMENT)
        log_level = os.getenv("AKI_LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
        log_dir_value = os.getenv("AKI_LOG_DIR", DEFAULT_LOG_DIR)
        debug = os.getenv("AKI_DEBUG", "false").strip().lower() in {"1", "true", "yes"}

        log_dir = Path(log_dir_value)
        if not log_dir.is_absolute():
            log_dir = project_root / log_dir

        return cls(
            app_name=APP_NAME,
            app_version=APP_VERSION,
            environment=environment,
            log_level=log_level,
            log_dir=log_dir,
            debug=debug,
        )

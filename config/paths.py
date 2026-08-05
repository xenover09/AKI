"""
Centralized filesystem path resolution for AKI's Configuration Engine.

This module is the single source of truth for every path the
Configuration Engine touches on disk. It detects the host platform and
resolves an appropriate, conventional location for persisted
configuration data, then exposes those paths as one immutable object so
nothing else in the codebase has to compute or duplicate them.
"""

from __future__ import annotations

import os
import platform
import sys
from dataclasses import dataclass
from pathlib import Path


def is_windows() -> bool:
    """
    Determine whether AKI is currently running on Windows.

    Returns:
        True if the host operating system is Windows, False otherwise.
    """
    return sys.platform.startswith("win") or platform.system().lower() == "windows"


def is_macos() -> bool:
    """
    Determine whether AKI is currently running on macOS.

    Returns:
        True if the host operating system is macOS, False otherwise.
    """
    return platform.system().lower() == "darwin"


@dataclass(frozen=True, slots=True)
class AppPaths:
    """
    Immutable collection of every filesystem path used by the
    Configuration Engine.

    Attributes:
        root_dir: Root directory for all of AKI's persisted
            configuration (platform-specific).
        config_dir: Directory containing the Configuration Engine's data.
        profiles_dir: Directory containing named configuration profiles.
        default_config_file: Path to the default configuration profile
            ("default.json").
    """

    root_dir: Path
    config_dir: Path
    profiles_dir: Path
    default_config_file: Path

    @classmethod
    def resolve(cls, app_name: str, project_root: Path | None = None) -> "AppPaths":
        """
        Resolve platform-appropriate application paths.

        On Windows, configuration is stored under
        `%APPDATA%\\<app_name>`. On macOS, under
        `~/Library/Application Support/<app_name>`. On Linux and other
        platforms, under `~/.config/<app_name>` (respecting
        `$XDG_CONFIG_HOME` when it is set).

        Args:
            app_name: Application name, used as the root folder name.
            project_root: Optional override root directory. When
                provided, all paths are resolved beneath
                `project_root / app_name` instead of the platform
                default. Intended for tests and portable installs.

        Returns:
            A fully resolved, immutable `AppPaths` instance. No
            directories are created here — use `ensure_directories`.
        """
        if project_root is not None:
            root_dir = project_root / app_name
        elif is_windows():
            appdata = os.environ.get("APPDATA")
            base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
            root_dir = base / app_name
        elif is_macos():
            root_dir = Path.home() / "Library" / "Application Support" / app_name
        else:
            xdg_config = os.environ.get("XDG_CONFIG_HOME")
            base = Path(xdg_config) if xdg_config else Path.home() / ".config"
            root_dir = base / app_name

        config_dir = root_dir / "config"
        profiles_dir = config_dir / "profiles"
        default_config_file = profiles_dir / "default.json"

        return cls(
            root_dir=root_dir,
            config_dir=config_dir,
            profiles_dir=profiles_dir,
            default_config_file=default_config_file,
        )

    def ensure_directories(self) -> None:
        """
        Create every configuration directory that does not yet exist.

        Safe to call multiple times; existing directories are left
        untouched.
        """
        for directory in (self.root_dir, self.config_dir, self.profiles_dir):
            directory.mkdir(parents=True, exist_ok=True)

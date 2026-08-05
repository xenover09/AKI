"""
Configuration Engine manager for AKI.

`ConfigManager` is the single public entry point for reading and
writing AKI's persisted, JSON-backed configuration. It composes
`AppPaths`, `ProfileRepository`, and `ConfigValidator` so that no other
part of the system needs to know how or where configuration is stored
on disk. This is distinct from `config.settings.Settings`, which holds
boot-time infrastructure configuration (environment, logging) sourced
from environment variables — see the module-level note below.

Boundary with `config.settings.Settings`:
    `Settings` answers "how should this process start?" (environment,
    log level, log directory) and is loaded once from `.env` at boot.
    `ConfigManager` answers "what has the user/application configured?"
    (theme, window size, feature toggles) and is loaded from persisted
    JSON profiles that can be edited, switched, and saved at runtime.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from config.constants import APP_NAME
from config.paths import AppPaths
from config.profiles import ConfigProfile, ProfileRepository
from config.validator import ConfigValidator


class ConfigManager:
    """
    Manages AKI's persisted, JSON-backed application configuration.

    On construction, `ConfigManager` guarantees that every required
    configuration directory exists and that a valid "default" profile
    is available on disk, then loads that profile into memory.
    """

    def __init__(self, app_name: str = APP_NAME, project_root: Path | None = None) -> None:
        """
        Initialize the Configuration Engine.

        Args:
            app_name: Application name, used to resolve the platform
                configuration root directory. Defaults to AKI's
                canonical application name.
            project_root: Optional override root directory (primarily
                for tests or portable installs), passed through to
                `AppPaths.resolve`.
        """
        self._paths = AppPaths.resolve(app_name=app_name, project_root=project_root)
        self._paths.ensure_directories()

        self._repository = ProfileRepository(paths=self._paths)
        self._active_profile: ConfigProfile = self._repository.ensure_default_profile()

    @property
    def paths(self) -> AppPaths:
        """Return the resolved application paths used by this engine."""
        return self._paths

    @property
    def active_profile_name(self) -> str:
        """Return the name of the currently loaded configuration profile."""
        return self._active_profile.name

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a configuration value by dotted key path.

        Args:
            key: Dotted path into the configuration (e.g. "window.width").
            default: Value to return if the key is not present.

        Returns:
            The configuration value, or `default` if not found.
        """
        node: Any = self._active_profile.data
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value by dotted key path, in memory.

        The change is validated before being applied and is not
        persisted to disk until `save()` is called.

        Args:
            key: Dotted path into the configuration (e.g. "window.width").
            value: The new value to assign.

        Raises:
            ConfigValidationError: If applying the change would produce
                an invalid configuration.
        """
        parts = key.split(".")
        candidate = copy.deepcopy(self._active_profile.data)

        node = candidate
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value

        ConfigValidator.validate(candidate)
        self._active_profile.data = candidate

    def save(self) -> None:
        """Persist the active profile to disk."""
        self._repository.save(self._active_profile)

    def reload(self) -> None:
        """Discard in-memory changes and reload the active profile from disk."""
        self._active_profile = self._repository.load(self._active_profile.name)

    def switch_profile(self, name: str) -> None:
        """
        Load a different configuration profile as the active profile.

        Args:
            name: Name of the profile to load (without file extension).

        Raises:
            FileNotFoundError: If no profile with that name exists.
            ConfigValidationError: If the profile file is invalid.
        """
        self._active_profile = self._repository.load(name)

    def create_profile(self, name: str, data: dict[str, Any] | None = None) -> None:
        """
        Create a new configuration profile and set it as active.

        Args:
            name: Name of the new profile (without file extension).
            data: Optional initial configuration values. Defaults to
                AKI's standard default configuration when omitted.

        Raises:
            ConfigValidationError: If `data` fails validation.
        """
        self._active_profile = self._repository.create(name=name, data=data)

    def list_profiles(self) -> list[str]:
        """
        List the names of every configuration profile stored on disk.

        Returns:
            Profile names (without file extension), sorted alphabetically.
        """
        return self._repository.list_profiles()

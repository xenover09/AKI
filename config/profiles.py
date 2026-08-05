"""
Profile management for Project AKI.

This module is responsible for creating, loading,
saving and listing configuration profiles.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config.defaults import get_default_config
from config.paths import AppPaths
from config.validator import ConfigValidator


@dataclass
class ConfigProfile:
    """
    Represents a single AKI configuration profile.
    """

    name: str
    data: dict[str, Any]


class ProfileRepository:
    """
    Handles reading and writing profile files.
    """

    def __init__(self, paths: AppPaths) -> None:
        self._paths = paths

    def ensure_default_profile(self) -> ConfigProfile:
        """
        Create the default profile if it does not exist.
        """

        if not self._paths.default_config_file.exists():
            profile = ConfigProfile(
                name="default",
                data=get_default_config(),
            )

            self.save(profile)

            return profile

        return self.load("default")

    def load(self, name: str) -> ConfigProfile:
        """
        Load a profile from disk.
        """

        profile_path = self._paths.profiles_dir / f"{name}.json"

        if not profile_path.exists():
            raise FileNotFoundError(f"Profile '{name}' not found.")

        with profile_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        ConfigValidator.validate(data)

        return ConfigProfile(
            name=name,
            data=data,
        )

    def save(self, profile: ConfigProfile) -> None:
        """
        Save a profile to disk.
        """

        ConfigValidator.validate(profile.data)

        profile_path = self._paths.profiles_dir / f"{profile.name}.json"

        with profile_path.open("w", encoding="utf-8") as file:
            json.dump(
                profile.data,
                file,
                indent=4,
                ensure_ascii=False,
            )

    def create(
        self,
        name: str,
        data: dict[str, Any] | None = None,
    ) -> ConfigProfile:
        """
        Create a new profile.
        """

        if data is None:
            data = get_default_config()

        profile = ConfigProfile(
            name=name,
            data=data,
        )

        self.save(profile)

        return profile

    def list_profiles(self) -> list[str]:
        """
        Return all available profile names.
        """

        profiles: list[str] = []

        for file in self._paths.profiles_dir.glob("*.json"):
            profiles.append(file.stem)

        profiles.sort()

        return profiles
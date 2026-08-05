"""
Configuration validation for AKI's Configuration Engine.

`ConfigValidator` enforces the structural and value constraints of
AKI's persisted configuration schema before a configuration dictionary
is trusted anywhere else in the system. No other module decides whether
a configuration dictionary is valid.
"""

from __future__ import annotations

from typing import Any, Final

_ALLOWED_LOG_LEVELS: Final[frozenset[str]] = frozenset(
    {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
)
_ALLOWED_THEMES: Final[frozenset[str]] = frozenset({"blue_futuristic"})
_MIN_WINDOW_DIMENSION: Final[int] = 640


class ConfigValidationError(Exception):
    """
    Raised when a configuration dictionary fails validation.

    Attributes:
        errors: Every validation failure found, described in plain
            language, so a caller can report all problems at once
            instead of discovering them one at a time.
    """

    def __init__(self, errors: list[str]) -> None:
        """
        Initialize the exception with the full list of failures.

        Args:
            errors: One human-readable message per validation failure.
        """
        self.errors = errors
        super().__init__("; ".join(errors))


class ConfigValidator:
    """
    Validates configuration dictionaries against AKI's expected schema.
    """

    @staticmethod
    def validate(config: dict[str, Any]) -> None:
        """
        Validate a configuration dictionary.

        Args:
            config: The configuration dictionary to validate.

        Raises:
            ConfigValidationError: If one or more values are missing,
                the wrong type, or outside their allowed range.
        """
        errors: list[str] = []

        errors.extend(ConfigValidator._validate_schema_version(config))
        errors.extend(ConfigValidator._validate_profile_name(config))
        errors.extend(ConfigValidator._validate_theme(config))
        errors.extend(ConfigValidator._validate_language(config))
        errors.extend(ConfigValidator._validate_log_level(config))
        errors.extend(ConfigValidator._validate_window(config))
        errors.extend(ConfigValidator._validate_startup(config))

        if errors:
            raise ConfigValidationError(errors)

    @staticmethod
    def _validate_schema_version(config: dict[str, Any]) -> list[str]:
        """Validate the 'schema_version' field."""
        value = config.get("schema_version")
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            return ["'schema_version' must be a positive integer."]
        return []

    @staticmethod
    def _validate_profile_name(config: dict[str, Any]) -> list[str]:
        """Validate the 'profile_name' field."""
        value = config.get("profile_name")
        if not isinstance(value, str) or not value.strip():
            return ["'profile_name' must be a non-empty string."]
        return []

    @staticmethod
    def _validate_theme(config: dict[str, Any]) -> list[str]:
        """Validate the 'theme' field."""
        value = config.get("theme")
        if value not in _ALLOWED_THEMES:
            allowed = ", ".join(sorted(_ALLOWED_THEMES))
            return [f"'theme' must be one of: {allowed}."]
        return []

    @staticmethod
    def _validate_language(config: dict[str, Any]) -> list[str]:
        """Validate the 'language' field."""
        value = config.get("language")
        if not isinstance(value, str) or not value.strip():
            return ["'language' must be a non-empty string."]
        return []

    @staticmethod
    def _validate_log_level(config: dict[str, Any]) -> list[str]:
        """Validate the 'log_level' field."""
        value = config.get("log_level")
        if not isinstance(value, str) or value.upper() not in _ALLOWED_LOG_LEVELS:
            allowed = ", ".join(sorted(_ALLOWED_LOG_LEVELS))
            return [f"'log_level' must be one of: {allowed}."]
        return []

    @staticmethod
    def _validate_window(config: dict[str, Any]) -> list[str]:
        """Validate the 'window' section."""
        errors: list[str] = []
        window = config.get("window")
        if not isinstance(window, dict):
            return ["'window' must be an object."]

        for dimension in ("width", "height"):
            value = window.get(dimension)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < _MIN_WINDOW_DIMENSION
            ):
                errors.append(
                    f"'window.{dimension}' must be an integer >= {_MIN_WINDOW_DIMENSION}."
                )

        if not isinstance(window.get("start_maximized"), bool):
            errors.append("'window.start_maximized' must be a boolean.")

        return errors

    @staticmethod
    def _validate_startup(config: dict[str, Any]) -> list[str]:
        """Validate the 'startup' section."""
        startup = config.get("startup")
        if not isinstance(startup, dict):
            return ["'startup' must be an object."]
        if not isinstance(startup.get("check_for_updates"), bool):
            return ["'startup.check_for_updates' must be a boolean."]
        return []

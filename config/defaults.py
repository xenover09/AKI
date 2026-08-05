"""
Default configuration values for AKI's Configuration Engine.

This module owns the *shape* and *default values* of AKI's persisted,
JSON-backed configuration schema. It is used to create `default.json`
the first time the Configuration Engine runs, and as the seed for any
newly created profile.
"""

from __future__ import annotations

import copy
from typing import Any, Final

CONFIG_SCHEMA_VERSION: Final[int] = 1

DEFAULT_CONFIG: Final[dict[str, Any]] = {
    "schema_version": CONFIG_SCHEMA_VERSION,
    "profile_name": "default",
    "theme": "blue_futuristic",
    "language": "en",
    "log_level": "INFO",
    "window": {
        "width": 1280,
        "height": 800,
        "start_maximized": False,
    },
    "startup": {
        "check_for_updates": True,
    },
}


def get_default_config() -> dict[str, Any]:
    """
    Return a fresh, independent copy of AKI's default configuration.

    A new deep copy is returned on every call so callers can freely
    mutate the result without corrupting the module-level default.

    Returns:
        A deep copy of `DEFAULT_CONFIG`.
    """
    return copy.deepcopy(DEFAULT_CONFIG)

"""Dependency Validation Script for AKI System.

Validates that all required third-party Python packages are installed before
booting the AKI application engine.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from typing import List, Tuple

# Mapping of Python top-level import module names to PyPI package names
REQUIRED_DEPENDENCIES: dict[str, str] = {
    "dotenv": "python-dotenv",
    "psutil": "psutil",
    "PySide6": "PySide6",
    "qtawesome": "qtawesome",
    "requests": "requests",
    "pydantic": "pydantic",
}


def find_missing_dependencies() -> List[Tuple[str, str]]:
    """Scan runtime environment for missing required third-party dependencies.

    Returns:
        List of tuples containing (import_module_name, pypi_package_name) for
        any missing dependencies.
    """
    missing: List[Tuple[str, str]] = []
    for module_name, pypi_name in REQUIRED_DEPENDENCIES.items():
        try:
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                missing.append((module_name, pypi_name))
        except (ImportError, AttributeValueError, Exception):
            missing.append((module_name, pypi_name))
    return missing


def format_startup_error(missing: List[Tuple[str, str]]) -> str:
    """Format a clean, professional startup error message for missing packages.

    Args:
        missing: List of (import_name, pypi_name) tuples for missing modules.

    Returns:
        Formatted multi-line error string.
    """
    pkg_list = "\n".join(f"  - {pypi_name}" for _, pypi_name in missing)
    return (
        "------------------------------------------------\n"
        "AKI Startup Error\n\n"
        "Missing Dependency:\n"
        f"{pkg_list}\n\n"
        "Run:\n"
        "  pip install -r requirements.txt\n"
        "------------------------------------------------"
    )


def validate_dependencies_or_exit(debug_mode: bool = False) -> None:
    """Validate dependencies and exit with friendly message if any are missing.

    Args:
        debug_mode: If True, prints additional debug information.
    """
    missing = find_missing_dependencies()
    if missing:
        error_msg = format_startup_error(missing)
        print(error_msg, file=sys.stderr)
        sys.exit(1)


def main() -> int:
    """Standalone CLI entry point for checking dependencies.

    Returns:
        0 if all dependencies are satisfied, 1 if any are missing.
    """
    missing = find_missing_dependencies()
    if missing:
        print(format_startup_error(missing), file=sys.stderr)
        return 1
    
    print("[OK] All AKI third-party dependencies are installed and verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

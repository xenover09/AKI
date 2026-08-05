"""
AKI entry point.

Boot sequence (fully owned by the Boot Manager):
    main.py -> Application -> Boot Manager ->
        1. Configuration Engine
        2. Logger
        3. Runtime Environment Validation
        4. Workspace Folders
        5. Database (placeholder)
        6. Memory (placeholder)
        7. Boot Complete
"""

from __future__ import annotations

import sys
from pathlib import Path

from aki_core import Application


def main() -> int:
    """
    Compose and run AKI.

    Returns:
        The process exit code returned by `Application.run()`.
    """
    project_root = Path(__file__).resolve().parent
    application = Application(project_root=project_root)
    return application.run()


if __name__ == "__main__":
    sys.exit(main())

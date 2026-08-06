"""
AKI Entry Point.

Flow

Boot Manager
↓

Desktop Launcher
↓

Main Window
"""

from __future__ import annotations

import sys
from pathlib import Path

from aki_core import Application
from aki_core.boot import BootError

from desktop.app import AKIApplication


def main() -> int:

    project_root = Path(__file__).resolve().parent

    application = Application(project_root)

    try:

        application.initialize()

    except BootError as error:

        print(error)

        return 1

    desktop = AKIApplication(sys.argv)

    return desktop.run()


if __name__ == "__main__":

    sys.exit(main())
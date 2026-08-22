"""AKI Entry Point.

Boot Sequence Flow:
    Dependency Validation
    ↓
    Boot Manager & Runtime Environment
    ↓
    Desktop Launcher (PySide6 / WebEngine Container)
    ↓
    Main Window
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from scripts.check_dependencies import (
    find_missing_dependencies,
    format_startup_error,
)


def main() -> int:
    """Application entry point."""
    project_root = Path(__file__).resolve().parent

    # Step 0: Ensure execution uses project .venv (Python 3.12)
    venv_python = project_root / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        try:
            current_exe = Path(sys.executable).resolve()
            target_exe = venv_python.resolve()
            if current_exe != target_exe:
                os.execv(str(target_exe), [str(target_exe)] + sys.argv)
        except Exception:
            pass

    # Step 1: Pre-boot Dependency Validation
    missing_deps = find_missing_dependencies()
    if missing_deps:
        print(format_startup_error(missing_deps), file=sys.stderr)
        return 1

    debug_mode = "--debug" in sys.argv or os.environ.get("AKI_DEBUG") == "1"

    try:
        from aki_core import Application
        from aki_core.boot import BootError
        from desktop.app import AKIApplication

        application = Application(project_root)
        try:
            runtime = application.initialize()

            desktop = AKIApplication(sys.argv, runtime=runtime)
            return desktop.run()
        finally:
            application.close()

    except ModuleNotFoundError as error:
        # Catch any unexpected module import failures cleanly
        missing_module = getattr(error, "name", str(error))
        pypi_name = missing_module
        if missing_module == "dotenv":
            pypi_name = "python-dotenv"
            
        formatted_error = format_startup_error([(missing_module, pypi_name)])
        print(formatted_error, file=sys.stderr)
        
        if debug_mode:
            print("\n[DEBUG TRACEBACK]", file=sys.stderr)
            import traceback
            traceback.print_exc()
        return 1

    except Exception as error:
        if debug_mode:
            import traceback
            traceback.print_exc()
        else:
            print(f"------------------------------------------------\nAKI Startup Error\n\n{error}\n------------------------------------------------", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
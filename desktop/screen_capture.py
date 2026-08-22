"""Desktop screen capture for AKI's take_screenshot action."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

_ScreenshotDirectory = Path.home() / "Pictures" / "AKI"


def capture_screen() -> dict[str, Any]:
    """
    Capture the primary screen and save a timestamped PNG.

    Returns:
        Payload describing the saved screenshot.

    Raises:
        RuntimeError: When no screen exists or saving fails.
    """

    from PySide6.QtGui import QGuiApplication

    screen = QGuiApplication.primaryScreen()

    if screen is None:
        raise RuntimeError(
            "No screen is available for capture."
        )

    pixmap = screen.grabWindow(0)

    if pixmap.isNull():
        raise RuntimeError(
            "Screen capture produced an empty image."
        )

    _ScreenshotDirectory.mkdir(parents=True, exist_ok=True)
    path = _ScreenshotDirectory / (
        f"aki_screenshot_{datetime.now():%Y%m%d_%H%M%S}.png"
    )

    if not pixmap.save(str(path), "PNG"):
        raise RuntimeError(
            "Captured screenshot could not be saved."
        )

    return {
        "path": str(path),
        "width": pixmap.width(),
        "height": pixmap.height(),
    }


__all__ = [
    "capture_screen",
]

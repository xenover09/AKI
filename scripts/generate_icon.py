"""
Generate AKI's application icon.

Draws the AKI reactor mark (cyan ring + wordmark) programmatically so
no binary asset needs to be hand-maintained. Run once:

    python scripts/generate_icon.py
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPixmap,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_OUTPUT = _PROJECT_ROOT / "assets" / "aki_icon.png"

_SIZE = 256


def draw_icon() -> QPixmap:
    """Render the AKI mark onto a square pixmap."""

    pixmap = QPixmap(_SIZE, _SIZE)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Dark reactor base.
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#04121f"))
    painter.drawEllipse(8, 8, _SIZE - 16, _SIZE - 16)

    # Outer cyan ring.
    ring = QColor(0, 200, 255, 210)
    pen = painter.pen()
    pen.setColor(ring)
    pen.setWidth(7)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(24, 24, _SIZE - 48, _SIZE - 48)

    # Inner glow ring.
    pen.setWidth(3)
    pen.setColor(QColor(0, 240, 255, 130))
    painter.setPen(pen)
    painter.drawEllipse(44, 44, _SIZE - 88, _SIZE - 88)

    # Wordmark.
    font = QFont("Segoe UI", 64)
    font.setBold(True)
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.0)
    painter.setFont(font)
    painter.setPen(QColor("#eafaff"))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "AKI")

    # Status dot.
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#00ff96"))
    painter.drawEllipse(_SIZE - 58, 40, 18, 18)

    painter.end()
    return pixmap


def main() -> int:
    """Generate and save the icon; report the outcome."""

    _OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    pixmap = draw_icon()
    pixmap.save(str(_OUTPUT), "PNG")

    icon = QIcon(str(_OUTPUT))
    print(f"Icon written: {_OUTPUT}")
    print(f"Sizes embedded: {[f'{s.width()}x{s.height()}' for s in icon.availableSizes()]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

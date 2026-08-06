"""Circular avatar widget with initials fallback and status indicator."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPaintEvent, QPixmap
from PySide6.QtWidgets import QWidget

from desktop.themes.blue_theme import BlueTheme
from desktop.widgets.status_indicator import StatusState


class AvatarWidget(QWidget):
    """Renders a circular avatar from a pixmap or initials, with a status dot."""

    def __init__(
        self,
        theme: BlueTheme,
        initials: str = "",
        pixmap: Optional[QPixmap] = None,
        size: Optional[int] = None,
        status: Optional[StatusState] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the avatar widget.

        Args:
            theme: The active theme providing colors, fonts and sizes.
            initials: Fallback initials shown when no pixmap is provided.
            pixmap: Optional avatar image.
            size: Optional explicit diameter; defaults to theme medium avatar size.
            status: Optional status state rendered as a small badge.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._theme = theme
        self._initials = initials[:2].upper()
        self._pixmap = pixmap
        self._status = status
        diameter = size or theme.sizes.avatar_md
        self.setFixedSize(diameter, diameter)

    def set_status(self, status: Optional[StatusState]) -> None:
        """Update the status badge shown on the avatar.

        Args:
            status: The new status state, or ``None`` to hide the badge.
        """
        self._status = status
        self.update()

    def set_pixmap(self, pixmap: Optional[QPixmap]) -> None:
        """Update the avatar image.

        Args:
            pixmap: The new avatar image, or ``None`` to fall back to initials.
        """
        self._pixmap = pixmap
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 (Qt override naming)
        """Paint the circular avatar and optional status badge."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, self.width(), self.height())
        colors = self._theme.colors
        clip_rect = rect.adjusted(0, 0, -1, -1)
        painter.setPen(Qt.PenStyle.NoPen)

        if self._pixmap is not None:
            painter.save()
            painter.setClipRegion(self.rect())
            scaled = self._pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.drawPixmap(0, 0, scaled)
            painter.restore()
        else:
            painter.setBrush(QColor(colors.primary))
            painter.drawEllipse(clip_rect)
            painter.setPen(QColor(colors.text_primary))
            font = QFont(self._theme.fonts.family)
            font.setPointSize(max(self._theme.fonts.size_sm, self.height() // 3))
            font.setWeight(QFont.Weight(self._theme.fonts.weight_bold))
            painter.setFont(font)
            painter.drawText(clip_rect, Qt.AlignmentFlag.AlignCenter, self._initials)

        if self._status is not None:
            badge_diameter = max(self._theme.sizes.icon_sm // 2, self._theme.spacing.sm)
            badge_rect = QRectF(
                self.width() - badge_diameter,
                self.height() - badge_diameter,
                badge_diameter,
                badge_diameter,
            )
            status_colors = {
                StatusState.ONLINE: colors.success,
                StatusState.OFFLINE: colors.text_disabled,
                StatusState.BUSY: colors.error,
                StatusState.AWAY: colors.warning,
                StatusState.ERROR: colors.error,
            }
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(status_colors[self._status]))
            painter.drawEllipse(badge_rect)

        painter.end()

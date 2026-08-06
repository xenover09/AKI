"""Glassmorphism panel container widget."""

from __future__ import annotations

from typing import Optional

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QVBoxLayout, QWidget

from desktop.themes.blue_theme import BlueTheme


class GlassPanel(QFrame):
    """A translucent, blurred-glass styled container.

    Provides a themed background, rounded corners and a soft drop shadow.
    Intended as the base surface for cards, dialogs and popovers.
    """

    def __init__(
        self,
        theme: BlueTheme,
        parent: Optional[QWidget] = None,
        elevated: bool = True,
    ) -> None:
        """Initialize the glass panel.

        Args:
            theme: The active theme providing colors, radius and spacing.
            parent: Optional parent widget.
            elevated: Whether to apply a drop shadow effect.
        """
        super().__init__(parent)
        self._theme = theme
        self.setObjectName("glassPanel")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(
            theme.spacing.md, theme.spacing.md, theme.spacing.md, theme.spacing.md
        )
        self._layout.setSpacing(theme.spacing.sm)
        self._apply_style()
        if elevated:
            self._apply_shadow()

    @property
    def content_layout(self) -> QVBoxLayout:
        """Return the layout content widgets should be added to."""
        return self._layout

    def _apply_style(self) -> None:
        colors = self._theme.colors
        radius = self._theme.radius
        self.setStyleSheet(
            f"""
            QFrame#glassPanel {{
                background-color: {colors.glass_fill};
                border: 1px solid {colors.glass_border};
                border-radius: {radius.lg}px;
            }}
            """
        )

    def _apply_shadow(self) -> None:
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(self._theme.spacing.xl)
        shadow.setXOffset(0)
        shadow.setYOffset(self._theme.spacing.xs)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.setGraphicsEffect(shadow)

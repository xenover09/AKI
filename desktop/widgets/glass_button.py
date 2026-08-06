"""Glassmorphism styled push button with variants and hover animation."""

from __future__ import annotations

from enum import Enum, unique
from typing import Optional

from PySide6.QtCore import QEasingCurve, QEvent, QPropertyAnimation, Qt
from PySide6.QtGui import QEnterEvent
from PySide6.QtWidgets import QGraphicsOpacityEffect, QPushButton, QWidget

from desktop.themes.blue_theme import BlueTheme


@unique
class ButtonVariant(Enum):
    """Available visual variants for :class:`GlassButton`."""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    GHOST = "ghost"
    DANGER = "danger"


class GlassButton(QPushButton):
    """A themed push button with glass styling and a hover fade animation."""

    def __init__(
        self,
        text: str,
        theme: BlueTheme,
        variant: ButtonVariant = ButtonVariant.PRIMARY,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the glass button.

        Args:
            text: The button label.
            theme: The active theme providing colors, fonts and sizes.
            variant: The visual variant to render.
            parent: Optional parent widget.
        """
        super().__init__(text, parent)
        self._theme = theme
        self._variant = variant
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(theme.sizes.button_height)
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity_effect)
        self._hover_animation = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._hover_animation.setDuration(theme.animations.fast)
        self._hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._apply_style()

    def enterEvent(self, event: QEnterEvent) -> None:  # noqa: N802 (Qt override naming)
        """Animate opacity down slightly on hover to signal interactivity."""
        self._animate_opacity(0.85)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:  # noqa: N802 (Qt override naming)
        """Animate opacity back to full on hover exit."""
        self._animate_opacity(1.0)
        super().leaveEvent(event)

    def _animate_opacity(self, target: float) -> None:
        self._hover_animation.stop()
        self._hover_animation.setStartValue(self._opacity_effect.opacity())
        self._hover_animation.setEndValue(target)
        self._hover_animation.start()

    def _apply_style(self) -> None:
        colors = self._theme.colors
        fonts = self._theme.fonts
        radius = self._theme.radius
        spacing = self._theme.spacing
        palette = {
            ButtonVariant.PRIMARY: (colors.primary, colors.text_primary, colors.primary_hover),
            ButtonVariant.SECONDARY: (colors.surface, colors.text_primary, colors.surface_alt),
            ButtonVariant.GHOST: ("transparent", colors.text_secondary, colors.glass_fill),
            ButtonVariant.DANGER: (colors.error, colors.text_primary, colors.error),
        }
        background, text_color, hover_background = palette[self._variant]
        border = f"1px solid {colors.glass_border}" if self._variant != ButtonVariant.PRIMARY else "none"
        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {background};
                color: {text_color};
                border: {border};
                border-radius: {radius.md}px;
                padding: 0 {spacing.md}px;
                font-family: '{fonts.family}';
                font-size: {fonts.size_md}px;
                font-weight: {fonts.weight_medium};
            }}
            QPushButton:hover {{
                background-color: {hover_background};
            }}
            QPushButton:disabled {{
                background-color: {colors.surface};
                color: {colors.text_disabled};
            }}
            """
        )

"""Solid push button with variants and hover states."""

from __future__ import annotations

from enum import Enum, unique
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QWidget

from desktop.themes.aki_theme import AkiTheme


@unique
class ButtonVariant(Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    GHOST = "ghost"
    DANGER = "danger"


class GlassButton(QPushButton):
    """A solid flat push button."""

    def __init__(
        self,
        text: str,
        theme: AkiTheme,
        variant: ButtonVariant = ButtonVariant.PRIMARY,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(text, parent)
        self._theme = theme
        self._variant = variant
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(32)
        self._apply_style()

    def _apply_style(self) -> None:
        palette = {
            ButtonVariant.PRIMARY: (self._theme.SURFACE_CARD, self._theme.TEXT_PRIMARY, self._theme.PRIMARY),
            ButtonVariant.SECONDARY: (self._theme.SURFACE_BASE, self._theme.TEXT_PRIMARY, self._theme.PRIMARY),
            ButtonVariant.GHOST: ("transparent", self._theme.TEXT_SECONDARY, self._theme.PRIMARY),
            ButtonVariant.DANGER: (self._theme.SURFACE_CARD, self._theme.ERROR, self._theme.ERROR),
        }
        background, text_color, hover_background = palette[self._variant]
        border = f"1px solid {self._theme.BORDER_LIGHT}"
        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {background};
                color: {text_color};
                border: {border};
                border-radius: {self._theme.RADIUS_MD}px;
                padding: 0 {self._theme.SPACING_MD}px;
                font-family: '{self._theme.FONT_FAMILY_PRIMARY}';
                font-size: {self._theme.FONT_SIZE_BODY}px;
                font-weight: {self._theme.FONT_WEIGHT_MEDIUM};
            }}
            QPushButton:hover, QPushButton:pressed {{
                background-color: {hover_background};
                color: {self._theme.TEXT_PRIMARY};
                border: 1px solid {self._theme.PRIMARY};
            }}
            QPushButton:disabled {{
                background-color: {self._theme.SURFACE_BASE};
                color: {self._theme.TEXT_MUTED};
                border: 1px solid {self._theme.BORDER_LIGHT};
            }}
            """
        )

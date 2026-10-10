"""Solid panel container widget."""

from __future__ import annotations

from typing import Optional

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from desktop.themes.aki_theme import AkiTheme


class GlassPanel(QFrame):
    """A solid container panel."""

    def __init__(
        self,
        theme: AkiTheme,
        parent: Optional[QWidget] = None,
        elevated: bool = False,
    ) -> None:
        super().__init__(parent)
        self._theme = theme
        self.setObjectName("glassPanel")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(
            theme.SPACING_MD, theme.SPACING_MD, theme.SPACING_MD, theme.SPACING_MD
        )
        self._layout.setSpacing(theme.SPACING_SM)
        self._apply_style()

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._layout

    def _apply_style(self) -> None:
        self.setStyleSheet(
            f"""
            QFrame#glassPanel {{
                background-color: {self._theme.SURFACE_CARD};
                border: 1px solid {self._theme.BORDER_LIGHT};
                border-radius: {self._theme.RADIUS_LG}px;
            }}
            """
        )

    def _apply_shadow(self) -> None:
        pass

"""Solid card widget with optional title and content area."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from desktop.themes.aki_theme import AkiTheme
from desktop.widgets.glass_panel import GlassPanel


class GlassCard(GlassPanel):
    """A solid panel specialized for titled content cards."""

    def __init__(
        self,
        theme: AkiTheme,
        title: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(theme=theme, parent=parent, elevated=False)
        self._title_label: Optional[QLabel] = None
        if title:
            self.set_title(title)
        self._body_container = QWidget(self)
        self._body_layout = QVBoxLayout(self._body_container)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(theme.SPACING_SM)
        self.content_layout.addWidget(self._body_container)

    @property
    def body_layout(self) -> QVBoxLayout:
        return self._body_layout

    def set_title(self, title: str) -> None:
        if self._title_label is None:
            self._title_label = QLabel(self)
            self._title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.content_layout.insertWidget(0, self._title_label)
        self._title_label.setText(title)
        self._title_label.setStyleSheet(
            f"""
            color: {self._theme.TEXT_PRIMARY};
            font-family: '{self._theme.FONT_FAMILY_PRIMARY}';
            font-size: {self._theme.FONT_SIZE_TITLE}px;
            font-weight: {self._theme.FONT_WEIGHT_BOLD};
            """
        )

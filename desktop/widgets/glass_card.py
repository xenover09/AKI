"""Glassmorphism card widget with optional title and content area."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from desktop.themes.blue_theme import BlueTheme
from desktop.widgets.glass_panel import GlassPanel


class GlassCard(GlassPanel):
    """A glass panel specialized for titled content cards."""

    def __init__(
        self,
        theme: BlueTheme,
        title: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the glass card.

        Args:
            theme: The active theme providing fonts, colors and spacing.
            title: Optional title text shown at the top of the card.
            parent: Optional parent widget.
        """
        super().__init__(theme=theme, parent=parent, elevated=True)
        self._title_label: Optional[QLabel] = None
        if title:
            self.set_title(title)
        self._body_container = QWidget(self)
        self._body_layout = QVBoxLayout(self._body_container)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(theme.spacing.sm)
        self.content_layout.addWidget(self._body_container)

    @property
    def body_layout(self) -> QVBoxLayout:
        """Return the layout that card body widgets should be added to."""
        return self._body_layout

    def set_title(self, title: str) -> None:
        """Set or update the card title text.

        Args:
            title: The title text to display.
        """
        fonts = self._theme.fonts
        colors = self._theme.colors
        if self._title_label is None:
            self._title_label = QLabel(self)
            self._title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.content_layout.insertWidget(0, self._title_label)
        self._title_label.setText(title)
        self._title_label.setStyleSheet(
            f"""
            color: {colors.text_primary};
            font-family: '{fonts.family}';
            font-size: {fonts.size_lg}px;
            font-weight: {fonts.weight_bold};
            """
        )

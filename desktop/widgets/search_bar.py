"""Search input widget with debounced text-changed signal."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QToolButton, QWidget

from desktop.themes.blue_theme import BlueTheme


class SearchBar(QWidget):
    """A themed search input with a clear button and debounced search signal."""

    search_changed = Signal(str)

    def __init__(
        self,
        theme: BlueTheme,
        placeholder: str = "Search...",
        debounce_ms: int = 250,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the search bar.

        Args:
            theme: The active theme providing colors, fonts, radius and sizes.
            placeholder: Placeholder text shown when the field is empty.
            debounce_ms: Milliseconds to wait after typing stops before emitting.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._theme = theme

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.spacing.xs)

        self._input = QLineEdit(self)
        self._input.setPlaceholderText(placeholder)
        self._input.setFixedHeight(theme.sizes.input_height)
        layout.addWidget(self._input)

        self._clear_button = QToolButton(self)
        self._clear_button.setText("\u2715")
        self._clear_button.setVisible(False)
        self._clear_button.clicked.connect(self._input.clear)
        layout.addWidget(self._clear_button)

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(debounce_ms)
        self._debounce_timer.timeout.connect(self._emit_search_changed)

        self._input.textChanged.connect(self._on_text_changed)
        self._apply_style()

    def text(self) -> str:
        """Return the current search text."""
        return self._input.text()

    def set_text(self, text: str) -> None:
        """Set the search text programmatically.

        Args:
            text: The text to place in the field.
        """
        self._input.setText(text)

    def clear(self) -> None:
        """Clear the search text."""
        self._input.clear()

    def _on_text_changed(self, text: str) -> None:
        self._clear_button.setVisible(bool(text))
        self._debounce_timer.start()

    def _emit_search_changed(self) -> None:
        self.search_changed.emit(self._input.text())

    def _apply_style(self) -> None:
        colors = self._theme.colors
        fonts = self._theme.fonts
        radius = self._theme.radius
        spacing = self._theme.spacing
        self._input.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: {colors.surface};
                color: {colors.text_primary};
                border: 1px solid {colors.border};
                border-radius: {radius.md}px;
                padding: 0 {spacing.sm}px;
                font-family: '{fonts.family}';
                font-size: {fonts.size_md}px;
            }}
            QLineEdit:focus {{
                border: 1px solid {colors.primary};
            }}
            """
        )
        self._clear_button.setStyleSheet(
            f"""
            QToolButton {{
                background: transparent;
                color: {colors.text_secondary};
                border: none;
            }}
            QToolButton:hover {{
                color: {colors.text_primary};
            }}
            """
        )

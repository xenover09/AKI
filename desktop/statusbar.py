"""Application status bar showing connection state and contextual info."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from desktop.themes.aki_theme import AkiTheme
from desktop.widgets.status_indicator import StatusIndicator, StatusState


class StatusBar(QWidget):
    """A themed status bar with a status indicator, message and trailing info."""

    def __init__(self, theme: AkiTheme, parent: Optional[QWidget] = None) -> None:
        """Initialize the status bar.

        Args:
            theme: The active theme providing colors, fonts, spacing and sizes.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._theme = theme
        self.setFixedHeight(theme.sizes.statusbar_height)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(theme.spacing.md, 0, theme.spacing.md, 0)
        layout.setSpacing(theme.spacing.sm)

        self._status_indicator = StatusIndicator(theme=theme, state=StatusState.OFFLINE, parent=self)
        layout.addWidget(self._status_indicator)

        self._message_label = QLabel("", self)
        self._message_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._message_label, stretch=1)

        self._trailing_label = QLabel("", self)
        self._trailing_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._trailing_label)

        self._apply_style()

    def set_connection_state(self, state: StatusState) -> None:
        """Update the connection status indicator.

        Args:
            state: The new connection status state.
        """
        self._status_indicator.set_state(state)

    def set_message(self, message: str) -> None:
        """Update the primary status message.

        Args:
            message: The message text to display.
        """
        self._message_label.setText(message)

    def set_trailing_text(self, text: str) -> None:
        """Update the trailing (right-aligned) status text.

        Args:
            text: The text to display, e.g. a version string.
        """
        self._trailing_label.setText(text)

    def _apply_style(self) -> None:
        colors = self._theme.colors
        fonts = self._theme.fonts
        self.setStyleSheet(
            f"""
            StatusBar {{
                background-color: {colors.surface};
                border-top: 1px solid {colors.border};
            }}
            """
        )
        label_style = (
            f"color: {colors.text_secondary}; font-family: '{fonts.family}'; "
            f"font-size: {fonts.size_sm}px; background: transparent; border: none;"
        )
        self._message_label.setStyleSheet(label_style)
        self._trailing_label.setStyleSheet(label_style)

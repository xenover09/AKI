"""Small status indicator widget (dot + optional label)."""

from __future__ import annotations

from enum import Enum, unique
from typing import Optional

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from desktop.themes.blue_theme import BlueTheme


@unique
class StatusState(Enum):
    """Represents the visual state shown by :class:`StatusIndicator`."""

    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    AWAY = "away"
    ERROR = "error"


class StatusIndicator(QWidget):
    """Displays a colored dot representing a status, with an optional label."""

    def __init__(
        self,
        theme: BlueTheme,
        state: StatusState = StatusState.OFFLINE,
        label: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the status indicator.

        Args:
            theme: The active theme providing colors, fonts and spacing.
            state: The initial status state.
            label: Optional text label displayed next to the dot.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._theme = theme
        self._state = state

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.spacing.xs)

        dot_diameter = max(theme.sizes.icon_sm // 2, theme.spacing.sm)
        self._dot = QLabel(self)
        self._dot.setFixedSize(dot_diameter, dot_diameter)
        layout.addWidget(self._dot)

        self._label: Optional[QLabel] = None
        if label:
            self._label = QLabel(label, self)
            self._label.setStyleSheet(
                f"color: {theme.colors.text_secondary}; font-family: '{theme.fonts.family}'; "
                f"font-size: {theme.fonts.size_sm}px;"
            )
            layout.addWidget(self._label)
        layout.addStretch(1)

        self._apply_state_style()

    def set_state(self, state: StatusState) -> None:
        """Update the displayed status state.

        Args:
            state: The new status state.
        """
        self._state = state
        self._apply_state_style()

    def set_label(self, text: str) -> None:
        """Update the label text if a label is present.

        Args:
            text: The new label text.
        """
        if self._label is not None:
            self._label.setText(text)

    def _apply_state_style(self) -> None:
        colors = self._theme.colors
        color_map = {
            StatusState.ONLINE: colors.success,
            StatusState.OFFLINE: colors.text_disabled,
            StatusState.BUSY: colors.error,
            StatusState.AWAY: colors.warning,
            StatusState.ERROR: colors.error,
        }
        color = color_map[self._state]
        radius = self._dot.width() // 2
        self._dot.setStyleSheet(f"background-color: {color}; border-radius: {radius}px;")

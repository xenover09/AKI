"""Full-widget loading overlay with a centered spinner and message."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QResizeEvent
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from desktop.themes.aki_theme import AkiTheme
from desktop.widgets.animated_icon import AnimatedIcon


class LoadingOverlay(QWidget):
    """A translucent overlay shown above a parent widget while busy.

    The overlay covers its parent's geometry, dims the background and shows
    a spinning icon with an optional status message.
    """

    def __init__(
        self,
        theme: AkiTheme,
        parent: QWidget,
        spinner_icon: Optional[QIcon] = None,
    ) -> None:
        """Initialize the loading overlay.

        Args:
            theme: The active theme providing colors, fonts and spacing.
            parent: The widget this overlay covers.
            spinner_icon: Optional icon used for the spinner animation.
        """
        super().__init__(parent)
        self._theme = theme
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {theme.colors.background};")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(theme.spacing.sm)

        self._spinner = AnimatedIcon(theme=theme, icon=spinner_icon, size=theme.sizes.icon_lg, parent=self)
        layout.addWidget(self._spinner, alignment=Qt.AlignmentFlag.AlignCenter)

        self._message_label = QLabel("", self)
        self._message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message_label.setStyleSheet(
            f"color: {theme.colors.text_secondary}; "
            f"font-family: '{theme.fonts.family}'; "
            f"font-size: {theme.fonts.size_md}px;"
        )
        layout.addWidget(self._message_label)

        self.hide()

    def show_loading(self, message: str = "") -> None:
        """Show the overlay, covering the full parent widget.

        Args:
            message: Optional status message displayed under the spinner.
        """
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())
        self._message_label.setText(message)
        self._spinner.start_rotation()
        self.raise_()
        self.show()

    def hide_loading(self) -> None:
        """Hide the overlay and stop the spinner animation."""
        self._spinner.stop_rotation()
        self.hide()

    def set_message(self, message: str) -> None:
        """Update the status message shown below the spinner.

        Args:
            message: The new status message.
        """
        self._message_label.setText(message)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 (Qt override naming)
        """Keep the overlay covering the full parent widget on resize."""
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())
        super().resizeEvent(event)

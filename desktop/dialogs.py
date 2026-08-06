"""Reusable glass-styled dialog components."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget, QDialog

from desktop.themes.blue_theme import BlueTheme
from desktop.widgets.glass_button import ButtonVariant, GlassButton


class GlassDialog(QDialog):
    """Base themed dialog with a glass background and consistent layout."""

    def __init__(
        self,
        theme: BlueTheme,
        title: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the base glass dialog.

        Args:
            theme: The active theme providing colors, fonts, radius and spacing.
            title: The dialog window title.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._theme = theme
        self.setWindowTitle(title)
        self.setModal(True)

        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(
            theme.spacing.lg, theme.spacing.lg, theme.spacing.lg, theme.spacing.lg
        )
        self._root_layout.setSpacing(theme.spacing.md)

        self._title_label = QLabel(title, self)
        self._root_layout.addWidget(self._title_label)

        self._button_row = QHBoxLayout()
        self._button_row.addStretch(1)
        self._root_layout.addLayout(self._button_row)

        self._apply_style()

    @property
    def content_layout(self) -> QVBoxLayout:
        """Return the layout body content should be inserted into."""
        return self._root_layout

    def add_button(self, button: GlassButton) -> None:
        """Add a button to the dialog's bottom button row.

        Args:
            button: The button widget to add.
        """
        self._button_row.addWidget(button)

    def _apply_style(self) -> None:
        colors = self._theme.colors
        fonts = self._theme.fonts
        radius = self._theme.radius
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {colors.surface};
                border: 1px solid {colors.glass_border};
                border-radius: {radius.lg}px;
            }}
            QLabel {{
                color: {colors.text_primary};
                font-family: '{fonts.family}';
                font-size: {fonts.size_lg}px;
                font-weight: {fonts.weight_bold};
            }}
            """
        )


class ConfirmDialog(GlassDialog):
    """A dialog presenting a message with confirm and cancel actions."""

    def __init__(
        self,
        theme: BlueTheme,
        title: str,
        message: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the confirmation dialog.

        Args:
            theme: The active theme.
            title: The dialog title.
            message: The confirmation message body.
            parent: Optional parent widget.
        """
        super().__init__(theme=theme, title=title, parent=parent)
        message_label = QLabel(message, self)
        message_label.setWordWrap(True)
        message_label.setStyleSheet(
            f"color: {theme.colors.text_secondary}; font-weight: {theme.fonts.weight_regular};"
        )
        self.content_layout.insertWidget(1, message_label)

        cancel_button = GlassButton("Cancel", theme=theme, variant=ButtonVariant.GHOST, parent=self)
        cancel_button.clicked.connect(self.reject)
        confirm_button = GlassButton("Confirm", theme=theme, variant=ButtonVariant.PRIMARY, parent=self)
        confirm_button.clicked.connect(self.accept)
        self.add_button(cancel_button)
        self.add_button(confirm_button)


class AlertDialog(GlassDialog):
    """A dialog presenting a message with a single acknowledgement action."""

    def __init__(
        self,
        theme: BlueTheme,
        title: str,
        message: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the alert dialog.

        Args:
            theme: The active theme.
            title: The dialog title.
            message: The alert message body.
            parent: Optional parent widget.
        """
        super().__init__(theme=theme, title=title, parent=parent)
        message_label = QLabel(message, self)
        message_label.setWordWrap(True)
        message_label.setStyleSheet(
            f"color: {theme.colors.text_secondary}; font-weight: {theme.fonts.weight_regular};"
        )
        self.content_layout.insertWidget(1, message_label)

        ok_button = GlassButton("OK", theme=theme, variant=ButtonVariant.PRIMARY, parent=self)
        ok_button.clicked.connect(self.accept)
        self.add_button(ok_button)


class InputDialog(GlassDialog):
    """A dialog collecting a single line of text input from the user."""

    def __init__(
        self,
        theme: BlueTheme,
        title: str,
        label: str,
        default_text: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the input dialog.

        Args:
            theme: The active theme.
            title: The dialog title.
            label: The label describing the requested input.
            default_text: Pre-filled text for the input field.
            parent: Optional parent widget.
        """
        super().__init__(theme=theme, title=title, parent=parent)
        field_label = QLabel(label, self)
        field_label.setStyleSheet(
            f"color: {theme.colors.text_secondary}; font-weight: {theme.fonts.weight_regular};"
        )
        self.content_layout.insertWidget(1, field_label)

        self._input_field = QLineEdit(default_text, self)
        self._input_field.setFixedHeight(theme.sizes.input_height)
        self._input_field.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: {theme.colors.background};
                color: {theme.colors.text_primary};
                border: 1px solid {theme.colors.border};
                border-radius: {theme.radius.md}px;
                padding: 0 {theme.spacing.sm}px;
            }}
            """
        )
        self.content_layout.insertWidget(2, self._input_field)

        cancel_button = GlassButton("Cancel", theme=theme, variant=ButtonVariant.GHOST, parent=self)
        cancel_button.clicked.connect(self.reject)
        ok_button = GlassButton("OK", theme=theme, variant=ButtonVariant.PRIMARY, parent=self)
        ok_button.clicked.connect(self.accept)
        self.add_button(cancel_button)
        self.add_button(ok_button)

    def input_text(self) -> str:
        """Return the text currently entered in the input field."""
        return self._input_field.text()

"""Command palette dialog for quick keyboard-driven navigation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from desktop.themes.blue_theme import BlueTheme
from desktop.widgets.search_bar import SearchBar


@dataclass(frozen=True)
class CommandItem:
    """Represents a single entry displayed in the command palette."""

    command_id: str
    title: str
    subtitle: str = ""
    shortcut: str = ""


class CommandPalette(QDialog):
    """A modal, filterable list of commands invoked via a keyboard shortcut."""

    command_selected = Signal(str)

    def __init__(
        self,
        theme: BlueTheme,
        commands: Optional[List[CommandItem]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the command palette.

        Args:
            theme: The active theme providing colors, fonts, radius and sizes.
            commands: The initial list of available commands.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._theme = theme
        self._commands: List[CommandItem] = commands or []

        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setModal(True)
        self.setFixedWidth(theme.sizes.command_palette_width)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(theme.spacing.md, theme.spacing.md, theme.spacing.md, theme.spacing.md)
        layout.setSpacing(theme.spacing.sm)

        self._search_bar = SearchBar(theme=theme, placeholder="Type a command...", parent=self)
        self._search_bar.search_changed.connect(self._filter_commands)
        layout.addWidget(self._search_bar)

        self._list_widget = QListWidget(self)
        self._list_widget.itemActivated.connect(self._on_item_activated)
        layout.addWidget(self._list_widget)

        self._apply_style()
        self.set_commands(self._commands)

    def set_commands(self, commands: List[CommandItem]) -> None:
        """Replace the available command list and refresh the view.

        Args:
            commands: The full list of commands to make available.
        """
        self._commands = commands
        self._populate_list(self._commands)

    def _filter_commands(self, query: str) -> None:
        query_lower = query.strip().lower()
        if not query_lower:
            self._populate_list(self._commands)
            return
        filtered = [
            command
            for command in self._commands
            if query_lower in command.title.lower() or query_lower in command.subtitle.lower()
        ]
        self._populate_list(filtered)

    def _populate_list(self, commands: List[CommandItem]) -> None:
        self._list_widget.clear()
        for command in commands:
            label = command.title if not command.subtitle else f"{command.title}  \u2014  {command.subtitle}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, command.command_id)
            self._list_widget.addItem(item)

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        command_id = item.data(Qt.ItemDataRole.UserRole)
        self.command_selected.emit(command_id)
        self.accept()

    def _apply_style(self) -> None:
        colors = self._theme.colors
        fonts = self._theme.fonts
        radius = self._theme.radius
        spacing = self._theme.spacing
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {colors.surface};
                border: 1px solid {colors.glass_border};
                border-radius: {radius.lg}px;
            }}
            QListWidget {{
                background: transparent;
                color: {colors.text_primary};
                border: none;
                font-family: '{fonts.family}';
                font-size: {fonts.size_md}px;
            }}
            QListWidget::item {{
                padding: {spacing.sm}px;
                border-radius: {radius.sm}px;
            }}
            QListWidget::item:selected {{
                background-color: {colors.primary};
                color: {colors.text_primary};
            }}
            """
        )

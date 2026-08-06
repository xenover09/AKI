"""Notification center panel for transient and persistent messages."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, unique
from typing import Dict, Optional
from uuid import uuid4

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from desktop.themes.blue_theme import BlueTheme
from desktop.widgets.glass_button import ButtonVariant, GlassButton
from desktop.widgets.glass_card import GlassCard


@unique
class NotificationLevel(Enum):
    """Severity level of a notification, used for accent coloring."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class NotificationItem:
    """A single notification entry."""

    title: str
    message: str
    level: NotificationLevel = NotificationLevel.INFO
    notification_id: str = field(default_factory=lambda: uuid4().hex)
    created_at: datetime = field(default_factory=datetime.now)


class NotificationCenter(QWidget):
    """A scrollable panel that lists active notifications.

    Notifications are supplied by the caller; this widget performs no
    scheduling, persistence or business logic of its own.
    """

    notification_dismissed = Signal(str)
    cleared = Signal()

    def __init__(self, theme: BlueTheme, parent: Optional[QWidget] = None) -> None:
        """Initialize the notification center.

        Args:
            theme: The active theme providing colors, fonts and spacing.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._theme = theme
        self._notifications: Dict[str, NotificationItem] = {}
        self._cards: Dict[str, GlassCard] = {}

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        self._scroll_area = QScrollArea(self)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        outer_layout.addWidget(self._scroll_area)

        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(
            theme.spacing.sm, theme.spacing.sm, theme.spacing.sm, theme.spacing.sm
        )
        self._list_layout.setSpacing(theme.spacing.sm)
        self._list_layout.addStretch(1)
        self._scroll_area.setWidget(self._list_container)

    def add_notification(self, notification: NotificationItem) -> None:
        """Add a notification card to the top of the list.

        Args:
            notification: The notification to display.
        """
        self._notifications[notification.notification_id] = notification
        card = self._build_card(notification)
        self._cards[notification.notification_id] = card
        self._list_layout.insertWidget(0, card)

    def remove_notification(self, notification_id: str) -> None:
        """Remove a notification by identifier.

        Args:
            notification_id: The identifier of the notification to remove.
        """
        card = self._cards.pop(notification_id, None)
        self._notifications.pop(notification_id, None)
        if card is not None:
            card.setParent(None)
            card.deleteLater()

    def clear_all(self) -> None:
        """Remove all notifications from the panel."""
        for notification_id in list(self._notifications.keys()):
            self.remove_notification(notification_id)
        self.cleared.emit()

    def notification_count(self) -> int:
        """Return the number of currently displayed notifications."""
        return len(self._notifications)

    def _build_card(self, notification: NotificationItem) -> GlassCard:
        card = GlassCard(theme=self._theme, title=notification.title, parent=self._list_container)
        message_label = QLabel(notification.message, card)
        message_label.setWordWrap(True)
        message_label.setStyleSheet(
            f"color: {self._theme.colors.text_secondary}; "
            f"font-family: '{self._theme.fonts.family}'; "
            f"font-size: {self._theme.fonts.size_sm}px;"
        )
        card.body_layout.addWidget(message_label)

        dismiss_button = GlassButton("Dismiss", theme=self._theme, variant=ButtonVariant.GHOST, parent=card)
        notification_id = notification.notification_id
        dismiss_button.clicked.connect(lambda: self._on_dismiss_clicked(notification_id))
        card.body_layout.addWidget(dismiss_button)
        return card

    def _on_dismiss_clicked(self, notification_id: str) -> None:
        self.remove_notification(notification_id)
        self.notification_dismissed.emit(notification_id)

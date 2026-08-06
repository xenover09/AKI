"""Navigation primitives for the AKI desktop application.

This module defines the page identifiers and the navigation controller
used to broadcast navigation intent across the application without any
direct coupling between the requester and the page manager.
"""

from __future__ import annotations

from enum import Enum, unique
from typing import List, Optional

from PySide6.QtCore import QObject, Signal


@unique
class PageId(Enum):
    """Enumerates every navigable page in the application."""

    DASHBOARD = "dashboard"
    CHAT = "chat"
    VOICE = "voice"
    VISION = "vision"
    MEMORY = "memory"
    AUTOMATION = "automation"
    CYBER = "cyber"
    DEVELOPER = "developer"
    PLUGINS = "plugins"
    SETTINGS = "settings"


class NavigationController(QObject):
    """Publishes navigation events and maintains navigation history.

    The controller holds no references to widgets. It is injected into
    any component that needs to trigger or react to navigation, keeping
    the navigation source decoupled from the page rendering layer.
    """

    page_changed = Signal(PageId)
    history_changed = Signal(list)

    def __init__(
        self,
        initial_page: PageId = PageId.DASHBOARD,
        parent: Optional[QObject] = None,
    ) -> None:
        """Initialize the controller with an initial active page.

        Args:
            initial_page: The page considered active before any navigation.
            parent: Optional Qt parent object.
        """
        super().__init__(parent)
        self._current_page: PageId = initial_page
        self._history: List[PageId] = [initial_page]

    @property
    def current_page(self) -> PageId:
        """Return the currently active page identifier."""
        return self._current_page

    @property
    def history(self) -> List[PageId]:
        """Return a copy of the navigation history stack."""
        return list(self._history)

    def navigate_to(self, page_id: PageId) -> None:
        """Navigate to the given page and emit the relevant signals.

        Args:
            page_id: The destination page identifier.
        """
        if page_id == self._current_page:
            return
        self._current_page = page_id
        self._history.append(page_id)
        self.page_changed.emit(page_id)
        self.history_changed.emit(self.history)

    def go_back(self) -> Optional[PageId]:
        """Navigate to the previous page in history, if any.

        Returns:
            The page navigated to, or ``None`` if no previous page exists.
        """
        if len(self._history) < 2:
            return None
        self._history.pop()
        previous_page = self._history[-1]
        self._current_page = previous_page
        self.page_changed.emit(previous_page)
        self.history_changed.emit(self.history)
        return previous_page

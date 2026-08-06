"""Page registration and switching for the AKI desktop application."""

from __future__ import annotations

from typing import Dict, Optional

from PySide6.QtWidgets import QStackedWidget, QWidget

from desktop.navigation import NavigationController, PageId


class PageManager:
    """Registers page widgets and switches between them on navigation.

    The manager depends on an injected :class:`QStackedWidget` for display
    and an injected :class:`NavigationController` for routing signals. It
    holds no business logic; it only maps page identifiers to widgets.
    """

    def __init__(self, stacked_widget: QStackedWidget, navigation: NavigationController) -> None:
        """Initialize the page manager.

        Args:
            stacked_widget: The stacked widget used to display pages.
            navigation: The navigation controller to listen to.
        """
        self._stacked_widget = stacked_widget
        self._navigation = navigation
        self._pages: Dict[PageId, QWidget] = {}
        self._navigation.page_changed.connect(self.show_page)

    def register_page(self, page_id: PageId, widget: QWidget) -> None:
        """Register a page widget under a page identifier.

        Args:
            page_id: The identifier the widget should be shown for.
            widget: The widget instance representing the page.
        """
        if page_id in self._pages:
            return
        self._pages[page_id] = widget
        self._stacked_widget.addWidget(widget)

    def show_page(self, page_id: PageId) -> None:
        """Display the widget registered for the given page identifier.

        Args:
            page_id: The identifier of the page to display.
        """
        widget = self._pages.get(page_id)
        if widget is None:
            return
        self._stacked_widget.setCurrentWidget(widget)

    def widget_for(self, page_id: PageId) -> Optional[QWidget]:
        """Return the widget registered for a page identifier, if any.

        Args:
            page_id: The page identifier to look up.
        """
        return self._pages.get(page_id)

    def current_page_id(self) -> Optional[PageId]:
        """Return the identifier of the currently displayed page, if known."""
        current_widget = self._stacked_widget.currentWidget()
        for page_id, widget in self._pages.items():
            if widget is current_widget:
                return page_id
        return None

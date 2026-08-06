"""Main application window for the AKI Desktop Ecosystem.

This module defines :class:`MainWindow`, the frameless, resizable,
glass-effect shell of the application. It wires together the custom
:class:`~desktop.title_bar.TitleBar`, the :class:`~desktop.sidebar.Sidebar`,
and a :class:`QStackedWidget` that currently hosts only the
:class:`~desktop.pages.dashboard_page.DashboardPage` page. The stack is
architected so future pages can be registered and switched to via
``Sidebar.page_changed`` without further structural changes.

This module contains no business logic, AI logic, or networking code.
It is purely responsible for window chrome and layout. All colors are
sourced exclusively from :class:`desktop.themes.blue_theme.BlueTheme`.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from desktop.pages.dashboard_page import DashboardPage
from desktop.themes.blue_theme import BlueTheme
from desktop.sidebar import Sidebar
from desktop.title_bar import TitleBar


class MainWindow(QMainWindow):
    """Frameless glass-effect main window shell for the AKI ecosystem.

    The window has no native title bar or border. It provides its own
    :class:`TitleBar` for dragging/minimizing/closing, a :class:`Sidebar`
    for navigation, and a center :class:`QStackedWidget` that currently
    contains only the :class:`DashboardPage` page. The window supports
    manual resizing by dragging its edges and corners since frameless
    windows lose the operating system's native resize handles.

    Attributes:
        DASHBOARD_INDEX: Stack index reserved for the dashboard page.
    """

    DASHBOARD_INDEX: int = 0
    _RESIZE_MARGIN: int = 6
    _MIN_WIDTH: int = 960
    _MIN_HEIGHT: int = 600

    def __init__(
        self,
        theme: BlueTheme | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the main window shell.

        Args:
            theme: The active :class:`BlueTheme` instance used for all
                colors and metrics. A new default instance is created if
                one is not provided.
            parent: Optional parent widget. Typically ``None`` since this
                is the application's top-level window.
        """
        super().__init__(parent)

        self._theme: BlueTheme = theme if theme is not None else BlueTheme()
        self._resizing: bool = False
        self._resize_edges: dict[str, bool] = {}
        self._drag_start_pos: QPoint = QPoint()
        self._drag_start_geometry = self.geometry()

        self._configure_window()
        self._build_ui()
        self._apply_glass_style()
        self._connect_signals()

    def _configure_window(self) -> None:
        """Configure frameless, translucent, resizable window flags."""
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(self._MIN_WIDTH, self._MIN_HEIGHT)
        self.setMouseTracking(True)

    def _build_ui(self) -> None:
        """Assemble the title bar, sidebar, and center page stack."""
        self._central_widget = QWidget(self)
        self._central_widget.setObjectName("centralGlassContainer")
        self._central_widget.setMouseTracking(True)
        self.setCentralWidget(self._central_widget)

        outer_layout = QVBoxLayout(self._central_widget)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self._title_bar = TitleBar(parent=self, theme=self._theme)
        outer_layout.addWidget(self._title_bar)

        body_container = QWidget(self._central_widget)
        body_layout = QHBoxLayout(body_container)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self._sidebar = Sidebar(theme=self._theme, parent=body_container)
        body_layout.addWidget(self._sidebar)

        self._page_stack = QStackedWidget(body_container)
        self._page_stack.setObjectName("pageStack")

        self._dashboard = DashboardPage(self._page_stack)
        self._page_stack.insertWidget(self.DASHBOARD_INDEX, self._dashboard)
        self._page_stack.setCurrentIndex(self.DASHBOARD_INDEX)

        body_layout.addWidget(self._page_stack, stretch=1)
        outer_layout.addWidget(body_container, stretch=1)

    def _apply_glass_style(self) -> None:
        """Apply the rounded, glass-effect stylesheet using BlueTheme colors."""
        self._central_widget.setStyleSheet(
            f"""
            #centralGlassContainer {{
                background-color: {self._theme.SURFACE_GLASS};
                border: 1px solid {self._theme.BORDER_LIGHT};
                border-radius: 16px;
            }}
            #pageStack {{
                background-color: {self._theme.SURFACE_BASE};
                border: none;
            }}
            """
        )

    def _connect_signals(self) -> None:
        """Connect navigation and window-control signals."""
        self._sidebar.page_changed.connect(self._on_page_changed)
        self._title_bar.minimize_requested.connect(self.showMinimized)
        self._title_bar.close_requested.connect(self.close)
        self._title_bar.maximize_restore_requested.connect(
            self._toggle_maximize_restore
        )

    def _on_page_changed(self, page_index: int) -> None:
        """Switch the visible page in response to sidebar navigation.

        Only the dashboard page is currently registered. Future pages
        should be inserted into ``self._page_stack`` and will become
        reachable through this same handler without further changes.

        Args:
            page_index: The stack index requested by the sidebar.
        """
        if 0 <= page_index < self._page_stack.count():
            self._page_stack.setCurrentIndex(page_index)

    def _toggle_maximize_restore(self) -> None:
        """Toggle the window between maximized and normal geometry."""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Begin an edge-resize drag when pressing near the window border.

        Args:
            event: The mouse press event.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            edges = self._detect_resize_edges(event.position().toPoint())
            if edges:
                self._resizing = True
                self._resize_edges = edges
                self._drag_start_pos = event.globalPosition().toPoint()
                self._drag_start_geometry = self.geometry()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Resize the window while dragging, or update the resize cursor.

        Args:
            event: The mouse move event.
        """
        if self._resizing and event.buttons() & Qt.MouseButton.LeftButton:
            self._perform_resize(event.globalPosition().toPoint())
            event.accept()
            return

        edges = self._detect_resize_edges(event.position().toPoint())
        self._update_cursor_for_edges(edges)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """End an active edge-resize drag.

        Args:
            event: The mouse release event.
        """
        if event.button() == Qt.MouseButton.LeftButton and self._resizing:
            self._resizing = False
            self._resize_edges = {}
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _detect_resize_edges(self, local_pos: QPoint) -> dict[str, bool]:
        """Determine which window edges a local point is near.

        Args:
            local_pos: A point in the window's local coordinate space.

        Returns:
            A mapping with boolean flags for the "left", "right", "top",
            and "bottom" edges that the point is close enough to for a
            resize interaction. Empty if the point is not near any edge.
        """
        margin = self._RESIZE_MARGIN
        rect = self.rect()
        edges = {
            "left": local_pos.x() <= margin,
            "right": local_pos.x() >= rect.width() - margin,
            "top": local_pos.y() <= margin,
            "bottom": local_pos.y() >= rect.height() - margin,
        }
        return {name: value for name, value in edges.items() if value}

    def _update_cursor_for_edges(self, edges: dict[str, bool]) -> None:
        """Set an appropriate resize cursor for the given edges.

        Args:
            edges: The edges currently under the cursor, as produced by
                :meth:`_detect_resize_edges`.
        """
        horizontal = edges.get("left", False) or edges.get("right", False)
        vertical = edges.get("top", False) or edges.get("bottom", False)

        if horizontal and vertical:
            corner_is_backslash = edges.get("left", False) == edges.get(
                "top", False
            )
            cursor = (
                Qt.CursorShape.SizeFDiagCursor
                if corner_is_backslash
                else Qt.CursorShape.SizeBDiagCursor
            )
            self.setCursor(cursor)
        elif horizontal:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif vertical:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.unsetCursor()

    def _perform_resize(self, global_pos: QPoint) -> None:
        """Apply a new window geometry based on the active resize edges.

        Args:
            global_pos: The current global cursor position.
        """
        delta = global_pos - self._drag_start_pos
        geometry = self._drag_start_geometry
        left, top, right, bottom = (
            geometry.left(),
            geometry.top(),
            geometry.right(),
            geometry.bottom(),
        )

        if self._resize_edges.get("left"):
            left = geometry.left() + delta.x()
        if self._resize_edges.get("right"):
            right = geometry.right() + delta.x()
        if self._resize_edges.get("top"):
            top = geometry.top() + delta.y()
        if self._resize_edges.get("bottom"):
            bottom = geometry.bottom() + delta.y()

        new_width = right - left
        new_height = bottom - top
        if new_width < self._MIN_WIDTH:
            if self._resize_edges.get("left"):
                left = right - self._MIN_WIDTH
            else:
                right = left + self._MIN_WIDTH
        if new_height < self._MIN_HEIGHT:
            if self._resize_edges.get("top"):
                top = bottom - self._MIN_HEIGHT
            else:
                bottom = top + self._MIN_HEIGHT

        self.setGeometry(left, top, right - left, bottom - top)
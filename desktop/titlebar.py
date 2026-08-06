"""
Custom frameless title bar for the AKI desktop application.

Provides window dragging, double-click maximize/restore, and
minimize/maximize/close controls, fully styled through
:class:`desktop.themes.blue_theme.BlueTheme`.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QWidget,
)

from desktop.themes.blue_theme import BlueTheme


class TitleBar(QWidget):
    """Custom draggable title bar replacing the native window frame."""

    minimize_requested = Signal()
    maximize_restore_requested = Signal()
    close_requested = Signal()

    def __init__(self, theme: BlueTheme, parent: QWidget | None = None) -> None:
        """
        Initialize the title bar.

        Args:
            theme: Centralized theme providing colors, fonts, and spacing.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._theme: BlueTheme = theme
        self._drag_position: QPoint = QPoint()
        self._is_dragging: bool = False

        self.setObjectName("titleBar")
        self.setFixedHeight(52)
        self.setStyleSheet(self._theme.titlebar_stylesheet())

        self._build_ui()

    def _build_ui(self) -> None:
        """Construct and arrange all child widgets via layouts."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            self._theme.SPACING_MD, 0, self._theme.SPACING_SM, 0
        )
        layout.setSpacing(self._theme.SPACING_SM)

        layout.addWidget(self._build_logo_section())
        layout.addItem(
            QSpacerItem(
                0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
            )
        )
        layout.addLayout(self._build_window_controls())

    def _build_logo_section(self) -> QWidget:
        """
        Build the left-aligned logo, title, and status indicator group.

        Returns:
            A widget containing the branding and status section.
        """
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(self._theme.SPACING_SM)

        logo_label = QLabel("◈", container)
        logo_label.setObjectName("titleBarLogo")

        title_label = QLabel("AKI", container)
        title_label.setObjectName("titleBarLogo")

        self._status_dot = QLabel("●", container)
        self._status_dot.setStyleSheet(f"color: {self._theme.SUCCESS};")

        status_text = QLabel("ONLINE", container)
        status_text.setObjectName("titleBarStatus")

        layout.addWidget(logo_label)
        layout.addWidget(title_label)
        layout.addSpacing(self._theme.SPACING_MD)
        layout.addWidget(self._status_dot)
        layout.addWidget(status_text)

        return container

    def _build_window_controls(self) -> QHBoxLayout:
        """
        Build the minimize, maximize, and close control buttons.

        Returns:
            A layout containing the window control buttons.
        """
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(self._theme.SPACING_XS)

        self._minimize_button = self._make_control_button("—")
        self._minimize_button.clicked.connect(self.minimize_requested.emit)

        self._maximize_button = self._make_control_button("□")
        self._maximize_button.clicked.connect(
            self.maximize_restore_requested.emit
        )

        self._close_button = self._make_control_button("✕")
        self._close_button.setObjectName("titleBarCloseControl")
        self._close_button.clicked.connect(self.close_requested.emit)

        layout.addWidget(self._minimize_button)
        layout.addWidget(self._maximize_button)
        layout.addWidget(self._close_button)

        return layout

    def _make_control_button(self, symbol: str) -> QPushButton:
        """
        Create a single styled window control button.

        Args:
            symbol: The glyph displayed on the button.

        Returns:
            A configured QPushButton instance.
        """
        button = QPushButton(symbol, self)
        button.setObjectName("titleBarControl")
        button.setFixedSize(36, 32)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Begin window dragging when the left mouse button is pressed."""
        if event.button() == Qt.MouseButton.LeftButton:
            window = self.window()
            self._drag_position = (
                event.globalPosition().toPoint() - window.frameGeometry().topLeft()
            )
            self._is_dragging = True
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Move the parent window while dragging is active."""
        if self._is_dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """End window dragging on mouse release."""
        self._is_dragging = False
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Toggle maximize/restore on double click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.maximize_restore_requested.emit()
            event.accept()

    def set_online(self, is_online: bool) -> None:
        """
        Update the online status indicator color.

        Args:
            is_online: Whether AKI's backend connection is active.
        """
        color = self._theme.SUCCESS if is_online else self._theme.ERROR
        self._status_dot.setStyleSheet(f"color: {color};")

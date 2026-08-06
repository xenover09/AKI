"""Custom frameless title bar widget for the AKI desktop application.

This module defines :class:`TitleBar`, the glassmorphism-styled
replacement for the native OS window chrome. It renders the AKI brand
label alongside minimize, maximize/restore and close controls, and
supports dragging the window by its background as well as
double-click-to-maximize, mirroring standard OS title bar behavior.

Typical usage example:

    title_bar = TitleBar(parent=central_widget)
    title_bar.minimize_requested.connect(window.showMinimized)
    title_bar.maximize_restore_requested.connect(toggle_maximize)
    title_bar.close_requested.connect(window.close)
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget

from desktop.themes.blue_theme import BlueTheme


class TitleBar(QWidget):
    """Frameless, draggable title bar with window control buttons.

    The title bar owns no window-management logic itself; it only emits
    signals describing user intent (minimize, maximize/restore, close)
    and leaves the owning window responsible for acting on them. This
    keeps the widget reusable and independent of any particular
    :class:`QMainWindow` implementation.

    Attributes:
        minimize_requested: Emitted when the user activates the minimize
            button.
        maximize_restore_requested: Emitted when the user activates the
            maximize/restore button or double-clicks the title bar
            background.
        close_requested: Emitted when the user activates the close
            button.
    """

    minimize_requested: Signal = Signal()
    maximize_restore_requested: Signal = Signal()
    close_requested: Signal = Signal()

    _HEIGHT: int = 40
    _BUTTON_SIZE: int = 40
    _ICON_MINIMIZE: str = "\u2013"
    _ICON_MAXIMIZE: str = "\u25A1"
    _ICON_RESTORE: str = "\u25A2"
    _ICON_CLOSE: str = "\u2715"

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "AKI — Artificial Knowledge Intelligence",
        theme: Optional[BlueTheme] = None,
    ) -> None:
        """Initialize the title bar.

        Args:
            parent: Optional parent widget.
            title: Text displayed in the title bar label.
            theme: Theme instance supplying the stylesheet. A new
                :class:`BlueTheme` is created if not provided.
        """
        super().__init__(parent)
        self._theme = theme if theme is not None else BlueTheme()
        self._is_maximized: bool = False
        self._drag_offset: Optional[QPoint] = None

        self.setObjectName("mainWindowTitleBar")
        self.setFixedHeight(self._HEIGHT)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._title_label = self._build_title_label(title)
        self._minimize_button = self._build_control_button(
            object_name="titleBarMinimizeButton",
            icon_text=self._ICON_MINIMIZE,
            tooltip="Minimize",
        )
        self._maximize_button = self._build_control_button(
            object_name="titleBarMaximizeButton",
            icon_text=self._ICON_MAXIMIZE,
            tooltip="Maximize",
        )
        self._close_button = self._build_control_button(
            object_name="titleBarCloseButton",
            icon_text=self._ICON_CLOSE,
            tooltip="Close",
        )

        self._build_layout()
        self._connect_signals()
        self.setStyleSheet(self._theme.titlebar_stylesheet())

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    def _build_title_label(self, title: str) -> QLabel:
        """Create the brand/title label shown on the left of the bar.

        Args:
            title: Text displayed in the label.

        Returns:
            The constructed, unparented-to-layout label instance.
        """
        label = QLabel(title, self)
        label.setObjectName("titleBarLabel")
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        return label

    def _build_control_button(
        self, object_name: str, icon_text: str, tooltip: str
    ) -> QPushButton:
        """Create a single window-control button.

        Args:
            object_name: Unique object name used for QSS targeting.
            icon_text: Glyph rendered as the button's label.
            tooltip: Tooltip text shown on hover.

        Returns:
            The constructed, unparented-to-layout button instance.
        """
        button = QPushButton(icon_text, self)
        button.setObjectName(object_name)
        button.setFixedSize(self._BUTTON_SIZE, self._BUTTON_SIZE)
        button.setToolTip(tooltip)
        button.setCursor(Qt.CursorShape.ArrowCursor)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return button

    def _build_layout(self) -> None:
        """Assemble the title label and control buttons into the layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._title_label)
        layout.addWidget(self._minimize_button)
        layout.addWidget(self._maximize_button)
        layout.addWidget(self._close_button)

    def _connect_signals(self) -> None:
        """Wire button clicks to the title bar's public signals."""
        self._minimize_button.clicked.connect(self.minimize_requested.emit)
        self._maximize_button.clicked.connect(self.maximize_restore_requested.emit)
        self._close_button.clicked.connect(self.close_requested.emit)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_title(self, title: str) -> None:
        """Update the text displayed in the title label.

        Args:
            title: New title text to display.
        """
        self._title_label.setText(title)

    def set_maximized(self, is_maximized: bool) -> None:
        """Synchronize the maximize button icon/tooltip with window state.

        Args:
            is_maximized: ``True`` if the owning window is currently
                maximized, ``False`` otherwise.
        """
        self._is_maximized = is_maximized
        if is_maximized:
            self._maximize_button.setText(self._ICON_RESTORE)
            self._maximize_button.setToolTip("Restore")
        else:
            self._maximize_button.setText(self._ICON_MAXIMIZE)
            self._maximize_button.setToolTip("Maximize")

    def is_maximized(self) -> bool:
        """Return whether the title bar believes the window is maximized.

        Returns:
            ``True`` if the last call to :meth:`set_maximized` passed
            ``True``, ``False`` otherwise.
        """
        return self._is_maximized

    # ------------------------------------------------------------------
    # Drag-to-move and double-click-to-maximize handling
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        """Begin a window-drag gesture on left-button press.

        Args:
            event: The mouse press event.
        """
        if event.button() == Qt.MouseButton.LeftButton and not self._is_maximized:
            window = self.window()
            self._drag_offset = (
                event.globalPosition().toPoint() - window.frameGeometry().topLeft()
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        """Move the owning window while a drag gesture is in progress.

        Args:
            event: The mouse move event.
        """
        if (
            self._drag_offset is not None
            and event.buttons() & Qt.MouseButton.LeftButton
            and not self._is_maximized
        ):
            self.window().move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        """End the active window-drag gesture.

        Args:
            event: The mouse release event.
        """
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        """Emit ``maximize_restore_requested`` on a background double-click.

        Args:
            event: The mouse double-click event.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = None
            self.maximize_restore_requested.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

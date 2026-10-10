"""Platform window visual effects: blur, shadows and frameless drag support."""

from __future__ import annotations

import sys
from typing import Optional

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QMouseEvent
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget

from desktop.themes.aki_theme import AkiTheme


class WindowEffects:
    """Applies visual window effects to a target top-level widget.

    Encapsulates optional platform-specific blur/acrylic effects together
    with a drop shadow and frameless-window drag handling. All targets and
    theming are injected; no global state is kept.
    """

    def __init__(self, target: QWidget, theme: AkiTheme) -> None:
        """Initialize the window effects helper.

        Args:
            target: The top-level widget the effects apply to.
            theme: The active theme providing shadow and radius values.
        """
        self._target = target
        self._theme = theme
        self._drag_position: Optional[QPoint] = None

    def apply_drop_shadow(self) -> None:
        """Apply a soft drop shadow around the target widget."""
        shadow = QGraphicsDropShadowEffect(self._target)
        shadow.setBlurRadius(self._theme.spacing.xxl)
        shadow.setOffset(0, self._theme.spacing.xs)
        shadow.setColor(QColor(0, 0, 0, 160))
        self._target.setGraphicsEffect(shadow)

    def apply_translucent_background(self) -> None:
        """Enable a translucent background for glassmorphism blending."""
        self._target.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def enable_acrylic_blur(self) -> bool:
        """Attempt to enable native acrylic/blur behind the window.

        Returns:
            ``True`` if a platform-specific blur effect was applied,
            ``False`` if the current platform is unsupported.
        """
        if sys.platform == "win32":
            return self._enable_windows_blur()
        return False

    def _enable_windows_blur(self) -> bool:
        try:
            import ctypes

            hwnd = int(self._target.winId())
            accent_policy_type = ctypes.c_int * 4
            accent = accent_policy_type(3, 0, 0, 0)

            class WindowCompositionAttributeData(ctypes.Structure):
                _fields_ = [
                    ("Attribute", ctypes.c_int),
                    ("Data", ctypes.POINTER(ctypes.c_int)),
                    ("SizeOfData", ctypes.c_size_t),
                ]

            data = WindowCompositionAttributeData()
            data.Attribute = 19
            data.Data = ctypes.cast(accent, ctypes.POINTER(ctypes.c_int))
            data.SizeOfData = ctypes.sizeof(accent)

            set_window_composition_attribute = ctypes.windll.user32.SetWindowCompositionAttribute
            set_window_composition_attribute(hwnd, ctypes.byref(data))
            return True
        except (OSError, AttributeError, ImportError):
            return False

    def begin_drag(self, event: QMouseEvent) -> None:
        """Record the drag start position for a frameless window move.

        Args:
            event: The mouse press event initiating the drag.
        """
        self._drag_position = event.globalPosition().toPoint() - self._target.frameGeometry().topLeft()

    def perform_drag(self, event: QMouseEvent) -> None:
        """Move the target window based on an ongoing drag.

        Args:
            event: The mouse move event continuing the drag.
        """
        if self._drag_position is not None:
            self._target.move(event.globalPosition().toPoint() - self._drag_position)

    def end_drag(self) -> None:
        """Clear the recorded drag position, ending the drag operation."""
        self._drag_position = None

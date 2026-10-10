"""Icon label supporting rotate, pulse and fade animations."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QSize, Qt
from PySide6.QtGui import QIcon, QPixmap, QTransform
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget

from desktop.themes.aki_theme import AkiTheme


class AnimatedIcon(QLabel):
    """A themed icon widget with built-in rotate, pulse and fade helpers."""

    def __init__(
        self,
        theme: AkiTheme,
        icon: Optional[QIcon] = None,
        size: Optional[int] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the animated icon.

        Args:
            theme: The active theme providing sizes and animation durations.
            icon: The icon to render.
            size: Optional explicit icon size; defaults to theme medium icon size.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._theme = theme
        self._icon = icon
        self._size = size or theme.sizes.icon_md
        self._base_pixmap: Optional[QPixmap] = None
        self._rotation_angle = 0

        self.setFixedSize(self._size, self._size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._pulse_animation = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._pulse_animation.setDuration(theme.animations.slow)
        self._pulse_animation.setStartValue(1.0)
        self._pulse_animation.setEndValue(0.4)
        self._pulse_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._pulse_animation.setLoopCount(-1)

        self._rotation_animation = QPropertyAnimation(self, b"rotationAngle", self)
        self._rotation_animation.setDuration(theme.animations.slow * 2)
        self._rotation_animation.setStartValue(0)
        self._rotation_animation.setEndValue(360)
        self._rotation_animation.setLoopCount(-1)

        if icon is not None:
            self.set_icon(icon)

    def set_icon(self, icon: QIcon) -> None:
        """Set the icon rendered by this widget.

        Args:
            icon: The icon to render.
        """
        self._icon = icon
        self._base_pixmap = icon.pixmap(QSize(self._size, self._size))
        self.setPixmap(self._base_pixmap)

    def start_pulse(self) -> None:
        """Start a looping opacity pulse animation."""
        self._pulse_animation.start()

    def stop_pulse(self) -> None:
        """Stop the pulse animation and restore full opacity."""
        self._pulse_animation.stop()
        self._opacity_effect.setOpacity(1.0)

    def start_rotation(self) -> None:
        """Start a looping rotation animation, useful for loading spinners."""
        self._rotation_animation.start()

    def stop_rotation(self) -> None:
        """Stop the rotation animation and reset orientation."""
        self._rotation_animation.stop()
        self.set_rotation_angle(0)

    def get_rotation_angle(self) -> int:
        """Return the current rotation angle in degrees."""
        return self._rotation_angle

    def set_rotation_angle(self, angle: int) -> None:
        """Set the rotation angle and repaint the icon accordingly.

        Args:
            angle: The rotation angle in degrees.
        """
        self._rotation_angle = angle
        if self._base_pixmap is not None:
            transform = QTransform().rotate(angle)
            rotated = self._base_pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
            self.setPixmap(rotated)

    rotationAngle = Property(int, get_rotation_angle, set_rotation_angle)

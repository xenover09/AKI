"""Reusable animation helpers built on QPropertyAnimation."""

from __future__ import annotations

from enum import Enum, unique
from typing import Optional

from PySide6.QtCore import QEasingCurve, QObject, QPropertyAnimation, QRect
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget

from desktop.themes.aki_theme import AkiTheme


@unique
class SlideDirection(Enum):
    """Direction a widget slides in from."""

    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"


class AnimationController:
    """Builds themed fade, slide and pulse animations for widgets.

    All durations and easing curves are derived from the injected theme so
    that animation timing stays consistent across the application.
    """

    def __init__(self, theme: AkiTheme) -> None:
        """Initialize the animation controller.

        Args:
            theme: The active theme providing animation durations.
        """
        self._theme = theme

    def fade_in(self, widget: QWidget, parent: Optional[QObject] = None) -> QPropertyAnimation:
        """Create and start a fade-in animation for a widget.

        Args:
            widget: The widget to fade in.
            parent: Optional owner for the animation object.

        Returns:
            The running animation instance.
        """
        effect = self._ensure_opacity_effect(widget)
        animation = QPropertyAnimation(effect, b"opacity", parent or widget)
        animation.setDuration(self._theme.animations.normal)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        return animation

    def fade_out(self, widget: QWidget, parent: Optional[QObject] = None) -> QPropertyAnimation:
        """Create and start a fade-out animation for a widget.

        Args:
            widget: The widget to fade out.
            parent: Optional owner for the animation object.

        Returns:
            The running animation instance.
        """
        effect = self._ensure_opacity_effect(widget)
        animation = QPropertyAnimation(effect, b"opacity", parent or widget)
        animation.setDuration(self._theme.animations.normal)
        animation.setStartValue(1.0)
        animation.setEndValue(0.0)
        animation.setEasingCurve(QEasingCurve.Type.InCubic)
        animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        return animation

    def slide_in(
        self,
        widget: QWidget,
        direction: SlideDirection,
        distance: Optional[int] = None,
        parent: Optional[QObject] = None,
    ) -> QPropertyAnimation:
        """Create and start a slide-in animation for a widget.

        Args:
            widget: The widget to slide into place.
            direction: The direction the widget slides in from.
            distance: Optional slide distance in pixels; defaults to the
                widget's own extent along the slide axis.
            parent: Optional owner for the animation object.

        Returns:
            The running animation instance.
        """
        end_geometry = widget.geometry()
        offset = distance or (
            end_geometry.width()
            if direction in (SlideDirection.LEFT, SlideDirection.RIGHT)
            else end_geometry.height()
        )
        start_geometry = QRect(end_geometry)
        if direction == SlideDirection.LEFT:
            start_geometry.moveLeft(end_geometry.left() - offset)
        elif direction == SlideDirection.RIGHT:
            start_geometry.moveLeft(end_geometry.left() + offset)
        elif direction == SlideDirection.TOP:
            start_geometry.moveTop(end_geometry.top() - offset)
        else:
            start_geometry.moveTop(end_geometry.top() + offset)

        widget.setGeometry(start_geometry)
        animation = QPropertyAnimation(widget, b"geometry", parent or widget)
        animation.setDuration(self._theme.animations.normal)
        animation.setStartValue(start_geometry)
        animation.setEndValue(end_geometry)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        return animation

    def pulse(self, widget: QWidget, parent: Optional[QObject] = None) -> QPropertyAnimation:
        """Create and start a looping pulse (opacity) animation for a widget.

        Args:
            widget: The widget to pulse.
            parent: Optional owner for the animation object.

        Returns:
            The running, looping animation instance.
        """
        effect = self._ensure_opacity_effect(widget)
        animation = QPropertyAnimation(effect, b"opacity", parent or widget)
        animation.setDuration(self._theme.animations.slow)
        animation.setStartValue(1.0)
        animation.setKeyValueAt(0.5, 0.4)
        animation.setEndValue(1.0)
        animation.setLoopCount(-1)
        animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        animation.start()
        return animation

    @staticmethod
    def _ensure_opacity_effect(widget: QWidget) -> QGraphicsOpacityEffect:
        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
        return effect

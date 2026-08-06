"""
Animated glassmorphic sidebar navigation for the AKI desktop application.

Provides a reusable :class:`SidebarButton` with hover glow and active
state animation, and a :class:`Sidebar` container that emits
``page_changed`` when the user selects a navigation destination.
No page-switching logic lives inside this module.
"""

from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from desktop.themes.blue_theme import BlueTheme

_ANIMATION_DURATION_MS: int = 180
_GLOW_BLUR_IDLE: float = 0.0
_GLOW_BLUR_HOVER: float = 24.0


class SidebarButton(QPushButton):
    """A single animated, checkable navigation entry in the sidebar."""

    def __init__(
        self,
        page_id: str,
        icon_name: str,
        label: str,
        theme: BlueTheme,
        parent: QWidget | None = None,
    ) -> None:
        """
        Initialize a sidebar navigation button.

        Args:
            page_id: Stable identifier emitted via ``page_changed``.
            icon_name: QtAwesome icon glyph name (e.g. ``"fa5s.home"``).
            label: Human-readable navigation label.
            theme: Centralized theme providing colors, fonts, and spacing.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._page_id: str = page_id
        self._theme: BlueTheme = theme
        self._glow_blur: float = _GLOW_BLUR_IDLE

        self.setObjectName("sidebarItem")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(44)
        self.setText(f"   {label}")
        self.setIcon(qta.icon(icon_name, color=self._theme.TEXT_SECONDARY))
        self.setIconSize(self.iconSize() * 1)
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.setStyleSheet(self._theme.sidebar_stylesheet())

        self._glow_effect = QGraphicsDropShadowEffect(self)
        self._glow_effect.setColor(QColor(self._theme.ACCENT))
        self._glow_effect.setOffset(0, 0)
        self._glow_effect.setBlurRadius(_GLOW_BLUR_IDLE)
        self.setGraphicsEffect(self._glow_effect)

        self._glow_animation = QPropertyAnimation(self, b"glowBlur", self)
        self._glow_animation.setDuration(_ANIMATION_DURATION_MS)
        self._glow_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.toggled.connect(self._on_toggled)

    @property
    def page_id(self) -> str:
        """Return the stable page identifier for this button."""
        return self._page_id

    def _get_glow_blur(self) -> float:
        """Return the current glow blur radius."""
        return self._glow_blur

    def _set_glow_blur(self, value: float) -> None:
        """
        Apply a new glow blur radius to the drop shadow effect.

        Args:
            value: Blur radius in pixels.
        """
        self._glow_blur = value
        self._glow_effect.setBlurRadius(value)

    glowBlur = Property(float, _get_glow_blur, _set_glow_blur)

    def enterEvent(self, event) -> None:  # noqa: ANN001
        """Animate the glow in when the cursor enters the button."""
        self._animate_glow(_GLOW_BLUR_HOVER)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: ANN001
        """Animate the glow out when the cursor leaves the button."""
        if not self.isChecked():
            self._animate_glow(_GLOW_BLUR_IDLE)
        super().leaveEvent(event)

    def _on_toggled(self, checked: bool) -> None:
        """
        React to the active state changing.

        Args:
            checked: Whether this button is now the active navigation item.
        """
        target = _GLOW_BLUR_HOVER if checked else _GLOW_BLUR_IDLE
        icon_color = self._theme.ACCENT if checked else self._theme.TEXT_SECONDARY
        self.setIcon(qta.icon("fa5s.circle", color=icon_color))
        self._animate_glow(target)

    def _animate_glow(self, target_blur: float) -> None:
        """
        Smoothly transition the glow blur radius to a target value.

        Args:
            target_blur: The destination blur radius in pixels.
        """
        self._glow_animation.stop()
        self._glow_animation.setStartValue(self._glow_blur)
        self._glow_animation.setEndValue(target_blur)
        self._glow_animation.start()


class Sidebar(QWidget):
    """Animated glassmorphic navigation sidebar for the AKI shell."""

    page_changed = Signal(str)

    _NAV_ITEMS: tuple[tuple[str, str, str], ...] = (
        ("dashboard", "fa5s.home", "Dashboard"),
        ("chat", "fa5s.comments", "Chat"),
        ("voice", "fa5s.microphone", "Voice"),
        ("vision", "fa5s.eye", "Vision"),
        ("memory", "fa5s.brain", "Memory"),
        ("automation", "fa5s.cogs", "Automation"),
        ("cybersecurity", "fa5s.shield-alt", "Cyber Security"),
        ("developer", "fa5s.code", "Developer"),
        ("plugins", "fa5s.puzzle-piece", "Plugins"),
    )

    def __init__(self, theme: BlueTheme, parent: QWidget | None = None) -> None:
        """
        Initialize the sidebar.

        Args:
            theme: Centralized theme providing colors, fonts, and spacing.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._theme: BlueTheme = theme
        self._button_group: QButtonGroup = QButtonGroup(self)
        self._button_group.setExclusive(True)

        self.setObjectName("sidebar")
        self.setStyleSheet(self._theme.sidebar_stylesheet())
        self.setFixedWidth(220)

        self._build_ui()

    def _build_ui(self) -> None:
        """Construct and arrange the logo, navigation, and footer sections."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            self._theme.SPACING_SM,
            self._theme.SPACING_MD,
            self._theme.SPACING_SM,
            self._theme.SPACING_MD,
        )
        layout.setSpacing(self._theme.SPACING_SM)

        layout.addWidget(self._build_logo_section())
        layout.addSpacing(self._theme.SPACING_MD)
        layout.addLayout(self._build_navigation_section())
        layout.addItem(
            QSpacerItem(
                0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
            )
        )
        layout.addWidget(self._build_footer_section())

    def _build_logo_section(self) -> QWidget:
        """
        Build the top branding section of the sidebar.

        Returns:
            A widget displaying the AKI logo placeholder.
        """
        container = QFrame(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(
            self._theme.SPACING_SM, self._theme.SPACING_SM, self._theme.SPACING_SM, 0
        )
        layout.setSpacing(self._theme.SPACING_SM)

        icon_label = QLabel(container)
        icon_label.setPixmap(
            qta.icon("fa5s.satellite-dish", color=self._theme.ACCENT).pixmap(28, 28)
        )

        text_label = QLabel("AKI", container)
        text_label.setStyleSheet(
            f"color: {self._theme.ACCENT}; "
            f"font-size: {self._theme.FONT_SIZE_HEADER}px; font-weight: 800;"
        )

        layout.addWidget(icon_label)
        layout.addWidget(text_label)
        layout.addItem(
            QSpacerItem(
                0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
            )
        )

        return container

    def _build_navigation_section(self) -> QVBoxLayout:
        """
        Build the primary navigation button stack.

        Returns:
            A layout containing all sidebar navigation buttons.
        """
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(self._theme.SPACING_XS)

        for index, (page_id, icon_name, label) in enumerate(self._NAV_ITEMS):
            button = SidebarButton(page_id, icon_name, label, self._theme, self)
            button.clicked.connect(self._on_nav_button_clicked)
            self._button_group.addButton(button)
            layout.addWidget(button)

            if index == 0:
                button.setChecked(True)

        return layout

    def _build_footer_section(self) -> QWidget:
        """
        Build the bottom footer section containing settings and profile.

        Returns:
            A widget containing the settings and profile navigation buttons.
        """
        container = QFrame(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(self._theme.SPACING_XS)

        settings_button = SidebarButton(
            "settings", "fa5s.sliders-h", "Settings", self._theme, self
        )
        settings_button.clicked.connect(self._on_nav_button_clicked)
        self._button_group.addButton(settings_button)

        profile_button = SidebarButton(
            "profile", "fa5s.user", "Profile", self._theme, self
        )
        profile_button.clicked.connect(self._on_nav_button_clicked)
        self._button_group.addButton(profile_button)

        layout.addWidget(settings_button)
        layout.addWidget(profile_button)

        return container

    def _on_nav_button_clicked(self) -> None:
        """Emit ``page_changed`` for the button that triggered the click."""
        button = self.sender()
        if isinstance(button, SidebarButton) and button.isChecked():
            self.page_changed.emit(button.page_id)

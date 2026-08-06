"""
Central dashboard view for the AKI desktop application.

Displays a greeting, an overall status card, a grid of glass status
cards, and a grid of quick action cards. This module contains no
business logic, AI logic, or networking — it only renders UI and
exposes Qt signals for the host application to act upon.
"""

from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from desktop.themes.blue_theme import BlueTheme

_ANIMATION_DURATION_MS: int = 180
_GLOW_BLUR_IDLE: float = 0.0
_GLOW_BLUR_HOVER: float = 28.0


class GlassCard(QFrame):
    """A reusable rounded glassmorphic card with animated hover glow."""

    clicked = Signal(str)

    def __init__(
        self,
        card_id: str,
        icon_name: str,
        title: str,
        subtitle: str,
        theme: BlueTheme,
        clickable: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        """
        Initialize a glass card.

        Args:
            card_id: Stable identifier emitted on interaction.
            icon_name: QtAwesome icon glyph name.
            title: Primary label displayed on the card.
            subtitle: Secondary descriptive text displayed on the card.
            theme: Centralized theme providing colors, fonts, and spacing.
            clickable: Whether the card reacts to mouse clicks.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._card_id: str = card_id
        self._theme: BlueTheme = theme
        self._clickable: bool = clickable
        self._glow_blur: float = _GLOW_BLUR_IDLE

        self.setObjectName("card")
        self.setStyleSheet(self._theme.card_stylesheet())
        self.setMinimumHeight(120)
        self.setCursor(
            Qt.CursorShape.PointingHandCursor
            if clickable
            else Qt.CursorShape.ArrowCursor
        )

        self._glow_effect = QGraphicsDropShadowEffect(self)
        self._glow_effect.setColor(QColor(self._theme.SHADOW))
        self._glow_effect.setOffset(0, 0)
        self._glow_effect.setBlurRadius(_GLOW_BLUR_IDLE)
        self.setGraphicsEffect(self._glow_effect)

        self._glow_animation = QPropertyAnimation(self, b"glowBlur", self)
        self._glow_animation.setDuration(_ANIMATION_DURATION_MS)
        self._glow_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._build_ui(icon_name, title, subtitle)

    def _build_ui(self, icon_name: str, title: str, subtitle: str) -> None:
        """
        Construct and arrange the card's internal content.

        Args:
            icon_name: QtAwesome icon glyph name.
            title: Primary label displayed on the card.
            subtitle: Secondary descriptive text displayed on the card.
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            self._theme.SPACING_MD,
            self._theme.SPACING_MD,
            self._theme.SPACING_MD,
            self._theme.SPACING_MD,
        )
        layout.setSpacing(self._theme.SPACING_SM)

        icon_label = QLabel(self)
        icon_label.setPixmap(
            qta.icon(icon_name, color=self._theme.ACCENT).pixmap(26, 26)
        )

        self._title_label = QLabel(title, self)
        self._title_label.setObjectName("cardValue")

        self._subtitle_label = QLabel(subtitle, self)
        self._subtitle_label.setObjectName("cardSubtitle")
        self._subtitle_label.setWordWrap(True)

        layout.addWidget(icon_label)
        layout.addWidget(self._title_label)
        layout.addWidget(self._subtitle_label)
        layout.addItem(
            QSpacerItem(
                0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
            )
        )

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

    def set_subtitle(self, subtitle: str) -> None:
        """
        Update the card's subtitle text.

        Args:
            subtitle: New descriptive text to display.
        """
        self._subtitle_label.setText(subtitle)

    def set_title(self, title: str) -> None:
        """
        Update the card's title text.

        Args:
            title: New primary label to display.
        """
        self._title_label.setText(title)

    def enterEvent(self, event) -> None:  # noqa: ANN001
        """Animate the glow in when the cursor enters the card."""
        self._animate_glow(_GLOW_BLUR_HOVER)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: ANN001
        """Animate the glow out when the cursor leaves the card."""
        self._animate_glow(_GLOW_BLUR_IDLE)
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Emit ``clicked`` with this card's id when clickable and pressed."""
        if self._clickable and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._card_id)
        super().mousePressEvent(event)

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


class Dashboard(QWidget):
    """Main dashboard view composed of status and quick action cards."""

    quick_action_triggered = Signal(str)
    status_card_activated = Signal(str)

    _STATUS_ITEMS: tuple[tuple[str, str, str, str], ...] = (
        ("ai_status", "fa5s.robot", "AI Status", "Core systems nominal"),
        ("memory_status", "fa5s.brain", "Memory Status", "Synced and available"),
        ("voice_status", "fa5s.microphone", "Voice Status", "Listening disabled"),
        ("vision_status", "fa5s.eye", "Vision Status", "Standby"),
    )

    _QUICK_ACTIONS: tuple[tuple[str, str, str, str], ...] = (
        ("chat", "fa5s.comments", "Chat", "Open conversation"),
        ("voice", "fa5s.microphone", "Voice", "Start voice session"),
        ("vision", "fa5s.eye", "Vision", "Launch vision mode"),
        ("memory", "fa5s.brain", "Memory", "Browse memory"),
        ("automation", "fa5s.cogs", "Automation", "Manage automations"),
        ("cybersecurity", "fa5s.shield-alt", "Cyber Security", "View security"),
    )

    def __init__(self, theme: BlueTheme, parent: QWidget | None = None) -> None:
        """
        Initialize the dashboard.

        Args:
            theme: Centralized theme providing colors, fonts, and spacing.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._theme: BlueTheme = theme

        self._build_ui()

    def _build_ui(self) -> None:
        """Construct and arrange the greeting, status, and action sections."""
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("background: transparent; border: none;")

        content = QWidget(scroll_area)
        content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(
            self._theme.SPACING_XL,
            self._theme.SPACING_LG,
            self._theme.SPACING_XL,
            self._theme.SPACING_LG,
        )
        content_layout.setSpacing(self._theme.SPACING_LG)

        content_layout.addWidget(self._build_greeting_section())
        content_layout.addWidget(self._build_section_label("SYSTEM STATUS"))
        content_layout.addLayout(self._build_status_grid())
        content_layout.addWidget(self._build_section_label("QUICK ACTIONS"))
        content_layout.addLayout(self._build_quick_actions_grid())
        content_layout.addItem(
            QSpacerItem(
                0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
            )
        )

        scroll_area.setWidget(content)
        outer_layout.addWidget(scroll_area)

    def _build_greeting_section(self) -> QWidget:
        """
        Build the top greeting and overall status card section.

        Returns:
            A widget containing the greeting text and status summary card.
        """
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(self._theme.SPACING_LG)

        text_container = QWidget(container)
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(self._theme.SPACING_XS)

        greeting_label = QLabel("Welcome back, Aether", text_container)
        greeting_label.setStyleSheet(
            f"color: {self._theme.TEXT_PRIMARY}; "
            f"font-size: {self._theme.FONT_TITLE}px; font-weight: 700;"
        )

        subtitle_label = QLabel(
            "All systems are online and ready.", text_container
        )
        subtitle_label.setStyleSheet(
            f"color: {self._theme.TEXT_SECONDARY}; "
            f"font-size: {self._theme.FONT_BODY}px;"
        )

        text_layout.addWidget(greeting_label)
        text_layout.addWidget(subtitle_label)

        status_card = GlassCard(
            card_id="current_status",
            icon_name="fa5s.satellite-dish",
            title="Operational",
            subtitle="Current Status",
            theme=self._theme,
            clickable=True,
            parent=container,
        )
        status_card.setFixedWidth(220)
        status_card.clicked.connect(self.status_card_activated.emit)

        layout.addWidget(text_container, stretch=1)
        layout.addWidget(status_card)

        return container

    def _build_section_label(self, text: str) -> QLabel:
        """
        Build a small uppercase section header label.

        Args:
            text: The section heading text.

        Returns:
            A styled QLabel for use as a section divider.
        """
        label = QLabel(text, self)
        label.setStyleSheet(
            f"color: {self._theme.TEXT_SECONDARY}; "
            f"font-size: {self._theme.FONT_SMALL}px; "
            "font-weight: 700; letter-spacing: 2px;"
        )
        return label

    def _build_status_grid(self) -> QGridLayout:
        """
        Build the grid of read-only glass status cards.

        Returns:
            A grid layout containing AI, Memory, Voice, and Vision status
            cards.
        """
        grid = QGridLayout()
        grid.setSpacing(self._theme.SPACING_MD)

        columns = 4
        for index, (card_id, icon_name, title, subtitle) in enumerate(
            self._STATUS_ITEMS
        ):
            card = GlassCard(
                card_id=card_id,
                icon_name=icon_name,
                title=title,
                subtitle=subtitle,
                theme=self._theme,
                clickable=True,
                parent=self,
            )
            card.clicked.connect(self.status_card_activated.emit)
            grid.addWidget(card, index // columns, index % columns)

        for column in range(columns):
            grid.setColumnStretch(column, 1)

        return grid

    def _build_quick_actions_grid(self) -> QGridLayout:
        """
        Build the grid of clickable quick action cards.

        Returns:
            A grid layout containing the quick action cards.
        """
        grid = QGridLayout()
        grid.setSpacing(self._theme.SPACING_MD)

        columns = 3
        for index, (action_id, icon_name, title, subtitle) in enumerate(
            self._QUICK_ACTIONS
        ):
            card = GlassCard(
                card_id=action_id,
                icon_name=icon_name,
                title=title,
                subtitle=subtitle,
                theme=self._theme,
                clickable=True,
                parent=self,
            )
            card.clicked.connect(self.quick_action_triggered.emit)
            grid.addWidget(card, index // columns, index % columns)

        for column in range(columns):
            grid.setColumnStretch(column, 1)

        return grid

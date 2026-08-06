"""Cyber page for the AKI Desktop Ecosystem.

Provides the pure UI shell for security monitoring controls. This
module contains no business logic, AI logic, networking, or database
access -- it only renders a professional glass layout using BlueTheme
tokens exclusively.
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from desktop.themes.blue_theme import BlueTheme


class CyberPage(QWidget):
    """UI-only page presenting security monitoring and protection status.

    Displays a page title, subtitle, and a responsive grid of glass
    cards. Contains no scanning, detection, or networking logic --
    purely presentational scaffolding.
    """

    _TITLE: str = "Cyber"
    _SUBTITLE: str = "Security monitoring and protection status"
    _CARDS: tuple[tuple[str, str], ...] = (
        ("Threat Monitor", "Current status of active threat monitoring."),
        ("Firewall Status", "Overview of firewall configuration state."),
        ("Access Log", "Recent record of system access events."),
        ("Security Alerts", "Summary panel for outstanding security alerts."),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the cyber page.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._card_frames: list[QFrame] = []
        self._fade_effect: QGraphicsOpacityEffect | None = None
        self._fade_animation: QPropertyAnimation | None = None

        self._build_ui()
        self._apply_styles()
        self._setup_animations()

    def _build_ui(self) -> None:
        """Construct the page title, subtitle, and glass card grid."""
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(
            BlueTheme.SPACING_XL,
            BlueTheme.SPACING_XL,
            BlueTheme.SPACING_XL,
            BlueTheme.SPACING_XL,
        )
        root_layout.setSpacing(BlueTheme.SPACING_MD)

        self._title_label = QLabel(self._TITLE, self)
        self._title_label.setObjectName("pageTitle")

        self._subtitle_label = QLabel(self._SUBTITLE, self)
        self._subtitle_label.setObjectName("pageSubtitle")

        root_layout.addWidget(self._title_label)
        root_layout.addWidget(self._subtitle_label)
        root_layout.addSpacing(BlueTheme.SPACING_SM)

        self._scroll_area = QScrollArea(self)
        self._scroll_area.setObjectName("pageScrollArea")
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self._card_container = QWidget(self._scroll_area)
        self._card_container.setObjectName("cardContainer")

        self._grid_layout = QGridLayout(self._card_container)
        self._grid_layout.setSpacing(BlueTheme.SPACING_MD)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)

        for card_title, card_description in self._CARDS:
            card = self._create_glass_card(card_title, card_description)
            self._card_frames.append(card)

        self._scroll_area.setWidget(self._card_container)
        root_layout.addWidget(self._scroll_area, stretch=1)

        self._arrange_cards()

    def _create_glass_card(self, title: str, description: str) -> QFrame:
        """Build a single glass-styled card widget.

        Args:
            title: Card heading text.
            description: Card supporting text.

        Returns:
            A configured, unpositioned :class:`QFrame` card.
        """
        card = QFrame(self._card_container)
        card.setObjectName("glassCard")
        card.setMinimumSize(BlueTheme.CARD_MIN_WIDTH, BlueTheme.CARD_MIN_HEIGHT)
        card.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(
            BlueTheme.SPACING_MD,
            BlueTheme.SPACING_MD,
            BlueTheme.SPACING_MD,
            BlueTheme.SPACING_MD,
        )
        card_layout.setSpacing(BlueTheme.SPACING_XS)

        title_label = QLabel(title, card)
        title_label.setObjectName("cardTitle")
        title_label.setWordWrap(True)

        description_label = QLabel(description, card)
        description_label.setObjectName("cardDescription")
        description_label.setWordWrap(True)

        card_layout.addWidget(title_label)
        card_layout.addWidget(description_label)
        card_layout.addStretch(1)

        return card

    def _arrange_cards(self) -> None:
        """Place cards into the grid according to the current width."""
        column_count = self._resolve_column_count(self.width())
        for index, card in enumerate(self._card_frames):
            row, column = divmod(index, column_count)
            self._grid_layout.addWidget(card, row, column)

    def _resolve_column_count(self, available_width: int) -> int:
        """Determine how many grid columns fit the available width.

        Args:
            available_width: Current width of the page, in pixels.

        Returns:
            The number of columns to use for the card grid.
        """
        if available_width < BlueTheme.BREAKPOINT_COMPACT:
            return 1
        if available_width < BlueTheme.BREAKPOINT_WIDE:
            return 2
        return 3

    def _apply_styles(self) -> None:
        """Apply the glass stylesheet using BlueTheme tokens only."""
        self.setStyleSheet(
            f"""
            QWidget {{
                background-color: {BlueTheme.SURFACE_BASE};
            }}
            #pageTitle {{
                color: {BlueTheme.TEXT_PRIMARY};
                font-family: {BlueTheme.FONT_FAMILY_PRIMARY};
                font-size: {BlueTheme.FONT_SIZE_TITLE}px;
                font-weight: {BlueTheme.FONT_WEIGHT_BOLD};
                background: transparent;
                border: none;
            }}
            #pageSubtitle {{
                color: {BlueTheme.TEXT_SECONDARY};
                font-family: {BlueTheme.FONT_FAMILY_PRIMARY};
                font-size: {BlueTheme.FONT_SIZE_SUBTITLE}px;
                font-weight: {BlueTheme.FONT_WEIGHT_REGULAR};
                background: transparent;
                border: none;
            }}
            #pageScrollArea {{
                background: transparent;
                border: none;
            }}
            #cardContainer {{
                background: transparent;
            }}
            #glassCard {{
                background-color: {BlueTheme.SURFACE_GLASS};
                border: 1px solid {BlueTheme.BORDER_LIGHT};
                border-radius: {BlueTheme.RADIUS_LG}px;
            }}
            #cardTitle {{
                color: {BlueTheme.TEXT_PRIMARY};
                font-family: {BlueTheme.FONT_FAMILY_PRIMARY};
                font-size: {BlueTheme.FONT_SIZE_CARD_TITLE}px;
                font-weight: {BlueTheme.FONT_WEIGHT_MEDIUM};
                background: transparent;
                border: none;
            }}
            #cardDescription {{
                color: {BlueTheme.TEXT_SECONDARY};
                font-family: {BlueTheme.FONT_FAMILY_PRIMARY};
                font-size: {BlueTheme.FONT_SIZE_BODY}px;
                font-weight: {BlueTheme.FONT_WEIGHT_REGULAR};
                background: transparent;
                border: none;
            }}
            """
        )

    def _setup_animations(self) -> None:
        """Prepare a reusable fade-in opacity animation for this page."""
        self._fade_effect = QGraphicsOpacityEffect(self)
        self._fade_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._fade_effect)

        self._fade_animation = QPropertyAnimation(
            self._fade_effect, b"opacity", self
        )
        self._fade_animation.setDuration(BlueTheme.ANIMATION_DURATION_MEDIUM)
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Re-arrange the card grid whenever the page is resized.

        Args:
            event: The resize event supplied by Qt.
        """
        super().resizeEvent(event)
        self._arrange_cards()

    def initialize(self) -> None:
        """Prepare the page for display and play its entry animation."""
        if self._fade_effect is not None:
            self._fade_effect.setOpacity(0.0)
        if self._fade_animation is not None:
            self._fade_animation.stop()
            self._fade_animation.start()

    def refresh(self) -> None:
        """Recompute layout and re-apply styling for the page."""
        self._arrange_cards()
        self._apply_styles()

    def cleanup(self) -> None:
        """Release transient page resources such as running animations."""
        if self._fade_animation is not None:
            self._fade_animation.stop()

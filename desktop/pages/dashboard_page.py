"""Dashboard page for the AKI AI Operating System.

This module implements the primary landing view of the AKI desktop shell.
It presents a glassmorphism-styled overview of four core subsystems -
System Status, AI Core, Memory and Automation - using the shared
``AkiTheme`` design tokens for all colors, fonts, spacing and radii.

The page exposes an explicit lifecycle contract (``initialize``,
``refresh``, ``cleanup``) so that the hosting shell/router can manage its
resources deterministically instead of relying on Qt widget destruction
order.

Owner:
    Aether

Module:
    desktop.pages.dashboard_page
"""

from __future__ import annotations

import logging
from typing import Final

import psutil
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from desktop.themes.aki_theme import AkiTheme

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

_THEME: Final[AkiTheme] = AkiTheme()

# Timing.
_REFRESH_INTERVAL_MS: Final[int] = 2000

# Layout.
_PAGE_MARGIN_LEFT: Final[int] = _THEME.SPACING_LG
_PAGE_MARGIN_TOP: Final[int] = _THEME.SPACING_LG
_PAGE_MARGIN_RIGHT: Final[int] = _THEME.SPACING_LG
_PAGE_MARGIN_BOTTOM: Final[int] = _THEME.SPACING_LG
_HEADER_SPACING: Final[int] = _THEME.SPACING_SM
_SECTION_SPACING: Final[int] = _THEME.SPACING_LG
_CARD_GRID_SPACING: Final[int] = _THEME.SPACING_MD
_CARD_MIN_WIDTH: Final[int] = _THEME.CARD_MIN_WIDTH
_CARD_MIN_HEIGHT: Final[int] = _THEME.CARD_MIN_HEIGHT
_CARD_MAX_COLUMNS: Final[int] = 4
_CARD_MIN_COLUMNS: Final[int] = 1

# Responsive breakpoints (page width in pixels) mapped to column counts.
_RESPONSIVE_BREAKPOINTS: Final[tuple[tuple[int, int], ...]] = (
    (_THEME.BREAKPOINT_WIDE, 4),
    (_THEME.BREAKPOINT_COMPACT, 2),
    (0, 1),
)

# Card border width.
_CARD_BORDER_WIDTH: Final[int] = 1

# Byte conversion constant used for memory reporting.
_BYTES_PER_MEBIBYTE: Final[int] = 1024 * 1024


class _GlassCard(QFrame):
    """A single glassmorphism-styled status card.

    Renders a translucent, rounded panel containing a title, a primary
    value and a short descriptive line, styled entirely from
    ``AkiTheme`` tokens.

    Attributes:
        title: The card's static heading text.
    """

    def __init__(
        self,
        title: str,
        initial_value: str,
        initial_description: str,
        parent: QWidget | None = None,
    ) -> None:
        """Initializes the glass card.

        Args:
            title: The static heading displayed at the top of the card.
            initial_value: The initial primary value text.
            initial_description: The initial secondary description text.
            parent: The optional parent widget.
        """
        super().__init__(parent)
        self.title: str = title
        self._title_label: QLabel = QLabel(self)
        self._value_label: QLabel = QLabel(self)
        self._description_label: QLabel = QLabel(self)
        self._build_ui(initial_value, initial_description)
        self._apply_style()

    def _build_ui(self, initial_value: str, initial_description: str) -> None:
        """Builds and arranges the card's internal widgets.

        Args:
            initial_value: The initial primary value text.
            initial_description: The initial secondary description text.
        """
        self.setObjectName("glassCard")
        self.setMinimumSize(_CARD_MIN_WIDTH, _CARD_MIN_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            _THEME.SPACING_MD,
            _THEME.SPACING_MD,
            _THEME.SPACING_MD,
            _THEME.SPACING_MD,
        )
        layout.setSpacing(_THEME.SPACING_SM)

        self._title_label.setText(self.title.upper())
        self._title_label.setObjectName("dashboardGlassCardTitle")

        self._value_label.setText(initial_value)
        self._value_label.setObjectName("dashboardGlassCardValue")
        self._value_label.setWordWrap(True)

        self._description_label.setText(initial_description)
        self._description_label.setObjectName("dashboardGlassCardDescription")
        self._description_label.setWordWrap(True)

        layout.addWidget(self._title_label)
        layout.addStretch(1)
        layout.addWidget(self._value_label)
        layout.addWidget(self._description_label)

    def _apply_style(self) -> None:
        """Applies the AkiTheme glassmorphism stylesheet to the card."""
        self.setStyleSheet(
            f"""
            QFrame#glassCard {{
                background-color: {_THEME.SURFACE_GLASS};
                border: {_CARD_BORDER_WIDTH}px solid {_THEME.BORDER_LIGHT};
                border-radius: {_THEME.RADIUS_LG}px;
            }}
            QFrame#glassCard:hover {{
                border: {_CARD_BORDER_WIDTH}px solid {_THEME.BORDER_ACCENT};
            }}
            QLabel#dashboardGlassCardTitle {{
                color: {_THEME.TEXT_SECONDARY};
                font-family: {_THEME.FONT_FAMILY_PRIMARY};
                font-size: {_THEME.FONT_SIZE_CARD_TITLE}px;
                font-weight: {_THEME.FONT_WEIGHT_BOLD};
                letter-spacing: 1px;
                background: transparent;
                border: none;
            }}
            QLabel#dashboardGlassCardValue {{
                color: {_THEME.TEXT_PRIMARY};
                font-family: {_THEME.FONT_FAMILY_PRIMARY};
                font-size: {_THEME.FONT_SIZE_TITLE}px;
                font-weight: {_THEME.FONT_WEIGHT_BOLD};
                background: transparent;
                border: none;
            }}
            QLabel#dashboardGlassCardDescription {{
                color: {_THEME.TEXT_MUTED};
                font-family: {_THEME.FONT_FAMILY_PRIMARY};
                font-size: {_THEME.FONT_SIZE_SMALL}px;
                font-weight: {_THEME.FONT_WEIGHT_REGULAR};
                background: transparent;
                border: none;
            }}
            """
        )

    def set_value(self, value: str) -> None:
        """Updates the card's primary value text.

        Args:
            value: The new primary value text to display.
        """
        self._value_label.setText(value)

    def set_description(self, description: str) -> None:
        """Updates the card's secondary description text.

        Args:
            description: The new description text to display.
        """
        self._description_label.setText(description)


class DashboardPage(QWidget):
    """The primary dashboard view of the AKI desktop shell.

    Displays a welcome header and a responsive grid of four glass cards
    summarizing System Status, AI Core, Memory and Automation subsystem
    state. Dynamic values are refreshed on an internal timer while the
    page is active.

    Attributes:
        PAGE_TITLE: The static page title shown in the header.
        PAGE_SUBTITLE: The static page subtitle shown in the header.
    """

    PAGE_TITLE: Final[str] = "Dashboard"
    PAGE_SUBTITLE: Final[str] = "Welcome back, Aether."

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initializes the dashboard page and builds its static UI.

        Args:
            parent: The optional parent widget.
        """
        super().__init__(parent)
        self._refresh_timer: QTimer | None = None
        self._process: psutil.Process = psutil.Process()
        self._automation_task_count: int = 0
        self._ai_core_heartbeat: int = 0
        self._current_column_count: int = _CARD_MAX_COLUMNS

        self._grid_layout: QGridLayout = QGridLayout()
        self._status_card: _GlassCard = _GlassCard(
            "System Status", "--", "Awaiting first reading"
        )
        self._ai_core_card: _GlassCard = _GlassCard(
            "AI Core", "Standby", "Core not yet initialized"
        )
        self._memory_card: _GlassCard = _GlassCard(
            "Memory", "-- MB", "Awaiting first reading"
        )
        self._automation_card: _GlassCard = _GlassCard(
            "Automation", "0 Tasks", "No active automations"
        )
        self._cards: tuple[_GlassCard, ...] = (
            self._status_card,
            self._ai_core_card,
            self._memory_card,
            self._automation_card,
        )

        self._build_ui()

    def initialize(self) -> None:
        """Starts the dashboard's periodic refresh cycle.

        Performs an immediate refresh so the page never shows stale
        placeholder text, then starts the internal timer that keeps the
        cards up to date while the page remains active.
        """
        _LOGGER.debug("Initializing DashboardPage.")
        self.refresh()

        if self._refresh_timer is None:
            self._refresh_timer = QTimer(self)
            self._refresh_timer.setInterval(_REFRESH_INTERVAL_MS)
            self._refresh_timer.timeout.connect(self.refresh)

        self._refresh_timer.start()

    def refresh(self) -> None:
        """Recomputes and applies the latest values for every glass card."""
        cpu_value, cpu_description = self._collect_system_status()
        self._status_card.set_value(cpu_value)
        self._status_card.set_description(cpu_description)

        ai_value, ai_description = self._collect_ai_core_status()
        self._ai_core_card.set_value(ai_value)
        self._ai_core_card.set_description(ai_description)

        memory_value, memory_description = self._collect_memory_status()
        self._memory_card.set_value(memory_value)
        self._memory_card.set_description(memory_description)

        automation_value, automation_description = self._collect_automation_status()
        self._automation_card.set_value(automation_value)
        self._automation_card.set_description(automation_description)

    def cleanup(self) -> None:
        """Stops the refresh timer and releases dashboard resources."""
        _LOGGER.debug("Cleaning up DashboardPage.")
        if self._refresh_timer is not None:
            self._refresh_timer.stop()
            self._refresh_timer.timeout.disconnect(self.refresh)
            self._refresh_timer.deleteLater()
            self._refresh_timer = None

    def _build_ui(self) -> None:
        """Builds and arranges the full static layout of the page."""
        self.setObjectName("dashboardPage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            f"QWidget#dashboardPage {{ background-color: {_THEME.SURFACE_BASE}; }}"
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(
            _PAGE_MARGIN_LEFT,
            _PAGE_MARGIN_TOP,
            _PAGE_MARGIN_RIGHT,
            _PAGE_MARGIN_BOTTOM,
        )
        root_layout.setSpacing(_SECTION_SPACING)

        root_layout.addWidget(self._build_header())
        root_layout.addWidget(self._build_cards_container())
        root_layout.addStretch(1)

    def _build_header(self) -> QWidget:
        """Builds the header section containing the title and subtitle.

        Returns:
            A widget containing the stacked title and subtitle labels.
        """
        header_widget = QWidget(self)
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(_HEADER_SPACING)

        title_label = QLabel(self.PAGE_TITLE, header_widget)
        title_label.setObjectName("dashboardTitle")
        title_label.setStyleSheet(
            f"""
            QLabel#dashboardTitle {{
                color: {_THEME.TEXT_PRIMARY};
                font-family: {_THEME.FONT_FAMILY_PRIMARY};
                font-size: {_THEME.FONT_SIZE_HEADER}px;
                font-weight: {_THEME.FONT_WEIGHT_BOLD};
                background: transparent;
            }}
            """
        )

        subtitle_label = QLabel(self.PAGE_SUBTITLE, header_widget)
        subtitle_label.setObjectName("dashboardSubtitle")
        subtitle_label.setStyleSheet(
            f"""
            QLabel#dashboardSubtitle {{
                color: {_THEME.TEXT_SECONDARY};
                font-family: {_THEME.FONT_FAMILY_PRIMARY};
                font-size: {_THEME.FONT_SIZE_SUBTITLE}px;
                font-weight: {_THEME.FONT_WEIGHT_REGULAR};
                background: transparent;
            }}
            """
        )

        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        return header_widget

    def _build_cards_container(self) -> QWidget:
        """Builds the responsive grid container hosting the glass cards.

        Returns:
            A widget wrapping the grid layout that arranges the four
            glass cards.
        """
        container = QWidget(self)
        self._grid_layout.setParent(container)
        container.setLayout(self._grid_layout)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setHorizontalSpacing(_CARD_GRID_SPACING)
        self._grid_layout.setVerticalSpacing(_CARD_GRID_SPACING)

        self._reflow_grid(_CARD_MAX_COLUMNS)
        return container

    def _resolve_column_count(self, available_width: int) -> int:
        """Resolves the number of grid columns for a given page width.

        Args:
            available_width: The current width of the page in pixels.

        Returns:
            The number of columns the card grid should use, clamped
            between ``_CARD_MIN_COLUMNS`` and ``_CARD_MAX_COLUMNS``.
        """
        for breakpoint_width, column_count in _RESPONSIVE_BREAKPOINTS:
            if available_width >= breakpoint_width:
                return max(_CARD_MIN_COLUMNS, min(column_count, _CARD_MAX_COLUMNS))
        return _CARD_MIN_COLUMNS

    def _reflow_grid(self, column_count: int) -> None:
        """Repositions every glass card into a grid with the given columns.

        Args:
            column_count: The number of columns to arrange the cards into.
        """
        while self._grid_layout.count() > 0:
            self._grid_layout.takeAt(0)

        for index, card in enumerate(self._cards):
            row = index // column_count
            column = index % column_count
            self._grid_layout.addWidget(card, row, column)

        for column in range(column_count):
            self._grid_layout.setColumnStretch(column, 1)

        self._current_column_count = column_count

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Reflows the card grid whenever the page is resized.

        Args:
            event: The Qt resize event describing the new page size.
        """
        super().resizeEvent(event)
        target_column_count = self._resolve_column_count(event.size().width())
        if target_column_count != self._current_column_count:
            self._reflow_grid(target_column_count)

    def _collect_system_status(self) -> tuple[str, str]:
        """Collects current host CPU utilization for the System Status card.

        Returns:
            A tuple of ``(value_text, description_text)`` describing the
            current system CPU load.
        """
        cpu_percent = psutil.cpu_percent(interval=None)
        core_count = psutil.cpu_count(logical=True) or 1
        value_text = f"{cpu_percent:.0f}% CPU"
        description_text = f"{core_count} logical cores online"
        return value_text, description_text

    def _collect_ai_core_status(self) -> tuple[str, str]:
        """Collects a heartbeat-based status for the AI Core card.

        Returns:
            A tuple of ``(value_text, description_text)`` describing the
            AI Core's current operational state.
        """
        self._ai_core_heartbeat += 1
        value_text = "Online"
        description_text = f"Heartbeat #{self._ai_core_heartbeat}"
        return value_text, description_text

    def _collect_memory_status(self) -> tuple[str, str]:
        """Collects current process memory usage for the Memory card.

        Returns:
            A tuple of ``(value_text, description_text)`` describing the
            AKI process's resident memory footprint.
        """
        memory_info = self._process.memory_info()
        used_mebibytes = memory_info.rss / _BYTES_PER_MEBIBYTE
        system_memory = psutil.virtual_memory()
        system_used_percent = system_memory.percent
        value_text = f"{used_mebibytes:.0f} MB"
        description_text = f"System memory at {system_used_percent:.0f}%"
        return value_text, description_text

    def _collect_automation_status(self) -> tuple[str, str]:
        """Collects the current automation task count for the Automation card.

        Returns:
            A tuple of ``(value_text, description_text)`` describing the
            automation engine's current workload.
        """
        value_text = f"{self._automation_task_count} Tasks"
        if self._automation_task_count == 0:
            description_text = "No active automations"
        else:
            description_text = "Automations running"
        return value_text, description_text

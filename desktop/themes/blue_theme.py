"""Blue neon glassmorphism theme for the AKI desktop application.

This module defines :class:`BlueTheme`, the single source of truth for
every design token (colors, spacing, radii, typography, animation
timing, breakpoints) used across the AKI desktop shell, and the QSS
stylesheet builders derived from those tokens. Widgets never hard-code
colors or metrics directly; they pull everything from an instance of
this class so the entire application can be re-themed by swapping the
theme implementation.

Typical usage example:

    theme = BlueTheme()
    window.setStyleSheet(theme.global_stylesheet())
    sidebar.setStyleSheet(theme.sidebar_stylesheet())
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BlueTheme:
    """Design token catalog and QSS stylesheet factory for AKI.

    All tokens are declared as frozen dataclass fields with sensible
    defaults so the theme can be instantiated with zero arguments while
    still allowing a future ``ThemeManager`` to construct alternate
    palettes by overriding individual fields.

    Attributes:
        PRIMARY: Primary brand color, used for the main accent glow.
        SECONDARY: Secondary brand color, used for gradients and depth.
        ACCENT: High-emphasis accent color for active/selected states.
        SUCCESS: Semantic color for success/positive states.
        WARNING: Semantic color for warning/caution states.
        ERROR: Semantic color for error/destructive states.
        SURFACE_BASE: Base window background color.
        SURFACE_GLASS: Translucent glass panel background color.
        SURFACE_CARD: Opaque card background color.
        TEXT_PRIMARY: Primary, highest-emphasis text color.
        TEXT_SECONDARY: Secondary, medium-emphasis text color.
        TEXT_MUTED: Muted, low-emphasis text color.
        BORDER_LIGHT: Subtle hairline border color.
        BORDER_ACCENT: Accent-colored border used for focus/active states.
        RADIUS_SM: Small corner radius, in pixels.
        RADIUS_MD: Medium corner radius, in pixels.
        RADIUS_LG: Large corner radius, in pixels.
        RADIUS_XL: Extra-large corner radius, in pixels.
        SPACING_XS: Extra-small spacing unit, in pixels.
        SPACING_SM: Small spacing unit, in pixels.
        SPACING_MD: Medium spacing unit, in pixels.
        SPACING_LG: Large spacing unit, in pixels.
        SPACING_XL: Extra-large spacing unit, in pixels.
        FONT_FAMILY_PRIMARY: Primary font family stack.
        FONT_SIZE_SMALL: Small text font size, in pixels.
        FONT_SIZE_BODY: Body text font size, in pixels.
        FONT_SIZE_CARD_TITLE: Card title font size, in pixels.
        FONT_SIZE_SUBTITLE: Subtitle font size, in pixels.
        FONT_SIZE_TITLE: Title font size, in pixels.
        FONT_SIZE_HEADER: Header font size, in pixels.
        FONT_WEIGHT_REGULAR: Regular font weight value.
        FONT_WEIGHT_MEDIUM: Medium font weight value.
        FONT_WEIGHT_BOLD: Bold font weight value.
        WINDOW_MIN_WIDTH: Minimum application window width, in pixels.
        WINDOW_MIN_HEIGHT: Minimum application window height, in pixels.
        CARD_MIN_WIDTH: Minimum card widget width, in pixels.
        CARD_MIN_HEIGHT: Minimum card widget height, in pixels.
        BREAKPOINT_COMPACT: Max width, in pixels, considered "compact".
        BREAKPOINT_WIDE: Min width, in pixels, considered "wide".
        ANIMATION_DURATION_FAST: Fast animation duration, in milliseconds.
        ANIMATION_DURATION_MEDIUM: Medium animation duration, in
            milliseconds.
        ANIMATION_DURATION_SLOW: Slow animation duration, in milliseconds.
    """

    # ------------------------------------------------------------------
    # Colors
    # ------------------------------------------------------------------
    PRIMARY: str = "#2E7CFF"
    SECONDARY: str = "#7C4DFF"
    ACCENT: str = "#00E5FF"
    SUCCESS: str = "#2ED573"
    WARNING: str = "#FFB020"
    ERROR: str = "#FF4D4F"

    # ------------------------------------------------------------------
    # Backgrounds
    # ------------------------------------------------------------------
    SURFACE_BASE: str = "#0B0E17"
    SURFACE_GLASS: str = "rgba(24, 30, 48, 0.62)"
    SURFACE_CARD: str = "#141a29"

    # ------------------------------------------------------------------
    # Text
    # ------------------------------------------------------------------
    TEXT_PRIMARY: str = "#F5F7FF"
    TEXT_SECONDARY: str = "#A9B3D0"
    TEXT_MUTED: str = "#6B7591"

    # ------------------------------------------------------------------
    # Borders
    # ------------------------------------------------------------------
    BORDER_LIGHT: str = "rgba(255, 255, 255, 0.08)"
    BORDER_ACCENT: str = "rgba(46, 124, 255, 0.55)"

    # ------------------------------------------------------------------
    # Radius
    # ------------------------------------------------------------------
    RADIUS_SM: int = 6
    RADIUS_MD: int = 10
    RADIUS_LG: int = 16
    RADIUS_XL: int = 24

    # ------------------------------------------------------------------
    # Spacing
    # ------------------------------------------------------------------
    SPACING_XS: int = 4
    SPACING_SM: int = 8
    SPACING_MD: int = 16
    SPACING_LG: int = 24
    SPACING_XL: int = 32

    # ------------------------------------------------------------------
    # Fonts
    # ------------------------------------------------------------------
    FONT_FAMILY_PRIMARY: str = (
        "'Segoe UI', 'Inter', 'SF Pro Display', 'Helvetica Neue', Arial, "
        "sans-serif"
    )
    FONT_SIZE_SMALL: int = 11
    FONT_SIZE_BODY: int = 13
    FONT_SIZE_CARD_TITLE: int = 15
    FONT_SIZE_SUBTITLE: int = 17
    FONT_SIZE_TITLE: int = 22
    FONT_SIZE_HEADER: int = 28

    # ------------------------------------------------------------------
    # Weights
    # ------------------------------------------------------------------
    FONT_WEIGHT_REGULAR: int = 400
    FONT_WEIGHT_MEDIUM: int = 500
    FONT_WEIGHT_BOLD: int = 700

    # ------------------------------------------------------------------
    # Window
    # ------------------------------------------------------------------
    WINDOW_MIN_WIDTH: int = 1024
    WINDOW_MIN_HEIGHT: int = 640

    # ------------------------------------------------------------------
    # Cards
    # ------------------------------------------------------------------
    CARD_MIN_WIDTH: int = 220
    CARD_MIN_HEIGHT: int = 140

    # ------------------------------------------------------------------
    # Responsive
    # ------------------------------------------------------------------
    BREAKPOINT_COMPACT: int = 900
    BREAKPOINT_WIDE: int = 1440

    # ------------------------------------------------------------------
    # Animations
    # ------------------------------------------------------------------
    ANIMATION_DURATION_FAST: int = 120
    ANIMATION_DURATION_MEDIUM: int = 220
    ANIMATION_DURATION_SLOW: int = 360

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------

    def _rgba(self, hex_color: str, alpha: float) -> str:
        """Convert a ``#RRGGBB`` hex color into an ``rgba()`` QSS string.

        Args:
            hex_color: Color in ``#RRGGBB`` hex notation.
            alpha: Opacity in the ``[0.0, 1.0]`` range.

        Returns:
            The color formatted as a QSS ``rgba(r, g, b, a)`` string.

        Raises:
            ValueError: If ``hex_color`` is not a well-formed 6-digit hex
                color string.
        """
        normalized = hex_color.lstrip("#")
        if len(normalized) != 6:
            raise ValueError(f"Expected a 6-digit hex color, got '{hex_color}'.")
        red = int(normalized[0:2], 16)
        green = int(normalized[2:4], 16)
        blue = int(normalized[4:6], 16)
        return f"rgba({red}, {green}, {blue}, {alpha})"

    # ------------------------------------------------------------------
    # Stylesheet builders
    # ------------------------------------------------------------------

    def global_stylesheet(self) -> str:
        """Build the application-wide base stylesheet.

        Returns:
            The QSS stylesheet applied at the top-level application or
            main window scope, establishing base typography, palette and
            reset rules that every widget inherits from.
        """
        return f"""
        * {{
            font-family: {self.FONT_FAMILY_PRIMARY};
            font-size: {self.FONT_SIZE_BODY}px;
            font-weight: {self.FONT_WEIGHT_REGULAR};
            color: {self.TEXT_PRIMARY};
            outline: none;
        }}

        QWidget {{
            background-color: transparent;
        }}

        QWidget#mainWindowCentralWidget {{
            background-color: {self.SURFACE_BASE};
            border: 1px solid {self.BORDER_LIGHT};
            border-radius: {self.RADIUS_XL}px;
        }}

        QLabel {{
            background-color: transparent;
        }}

        QLabel#toastTitle {{
            font-size: {self.FONT_SIZE_CARD_TITLE}px;
            font-weight: {self.FONT_WEIGHT_BOLD};
            color: {self.TEXT_PRIMARY};
        }}

        QLabel#toastMessage {{
            font-size: {self.FONT_SIZE_SMALL}px;
            color: {self.TEXT_SECONDARY};
        }}

        QWidget#toastNotification {{
            background-color: {self.SURFACE_GLASS};
            border: 1px solid {self.BORDER_ACCENT};
            border-radius: {self.RADIUS_MD}px;
        }}

        QToolTip {{
            background-color: {self.SURFACE_CARD};
            color: {self.TEXT_PRIMARY};
            border: 1px solid {self.BORDER_LIGHT};
            border-radius: {self.RADIUS_SM}px;
            padding: {self.SPACING_XS}px {self.SPACING_SM}px;
        }}

        {self.scrollbar_stylesheet()}
        {self.button_stylesheet()}
        {self.input_stylesheet()}
        {self.menu_stylesheet()}
        """

    def sidebar_stylesheet(self) -> str:
        """Build the stylesheet for the navigation sidebar.

        Returns:
            The QSS stylesheet applied to
            :class:`~desktop.sidebar.Sidebar` and its navigation items.
        """
        return f"""
        QWidget#mainWindowSidebar {{
            background-color: {self.SURFACE_GLASS};
            border-right: 1px solid {self.BORDER_LIGHT};
        }}

        QWidget#mainWindowSidebar QPushButton {{
            text-align: left;
            padding: {self.SPACING_SM}px {self.SPACING_MD}px;
            margin: 2px {self.SPACING_SM}px;
            border: none;
            border-radius: {self.RADIUS_MD}px;
            background-color: transparent;
            color: {self.TEXT_SECONDARY};
            font-size: {self.FONT_SIZE_BODY}px;
            font-weight: {self.FONT_WEIGHT_MEDIUM};
        }}

        QWidget#mainWindowSidebar QPushButton:hover {{
            background-color: {self._rgba(self.PRIMARY, 0.14)};
            color: {self.TEXT_PRIMARY};
        }}

        QWidget#mainWindowSidebar QPushButton:checked {{
            background-color: {self._rgba(self.PRIMARY, 0.22)};
            color: {self.TEXT_PRIMARY};
            border-left: 3px solid {self.ACCENT};
            font-weight: {self.FONT_WEIGHT_BOLD};
        }}

        QWidget#mainWindowSidebar QLabel#sidebarBrand {{
            font-size: {self.FONT_SIZE_SUBTITLE}px;
            font-weight: {self.FONT_WEIGHT_BOLD};
            color: {self.TEXT_PRIMARY};
            padding: {self.SPACING_MD}px;
        }}

        QWidget#mainWindowSidebar QFrame#sidebarDivider {{
            background-color: {self.BORDER_LIGHT};
            max-height: 1px;
            min-height: 1px;
            margin: {self.SPACING_SM}px {self.SPACING_MD}px;
        }}
        """

    def titlebar_stylesheet(self) -> str:
        """Build the stylesheet for the custom frameless title bar.

        Returns:
            The QSS stylesheet applied to
            :class:`~desktop.title_bar.TitleBar` and its window control
            buttons.
        """
        return f"""
        QWidget#mainWindowTitleBar {{
            background-color: transparent;
            border-top-left-radius: {self.RADIUS_XL}px;
            border-top-right-radius: {self.RADIUS_XL}px;
            min-height: 40px;
            max-height: 40px;
        }}

        QWidget#mainWindowTitleBar QLabel#titleBarLabel {{
            color: {self.TEXT_SECONDARY};
            font-size: {self.FONT_SIZE_SMALL}px;
            font-weight: {self.FONT_WEIGHT_MEDIUM};
            padding-left: {self.SPACING_MD}px;
        }}

        QWidget#mainWindowTitleBar QPushButton {{
            background-color: transparent;
            border: none;
            border-radius: {self.RADIUS_SM}px;
            min-width: 40px;
            max-width: 40px;
            min-height: 32px;
            max-height: 32px;
            color: {self.TEXT_SECONDARY};
        }}

        QWidget#mainWindowTitleBar QPushButton:hover {{
            background-color: {self._rgba(self.PRIMARY, 0.18)};
            color: {self.TEXT_PRIMARY};
        }}

        QWidget#mainWindowTitleBar QPushButton#titleBarCloseButton:hover {{
            background-color: {self.ERROR};
            color: {self.TEXT_PRIMARY};
        }}
        """

    def glass_card_stylesheet(self) -> str:
        """Build the reusable glassmorphism card stylesheet.

        Returns:
            The QSS stylesheet applied to translucent glass card widgets
            used across dashboard, chat, memory and other pages.
        """
        return f"""
        QFrame#glassCard, QWidget#glassCard {{
            background-color: {self.SURFACE_GLASS};
            border: 1px solid {self.BORDER_LIGHT};
            border-radius: {self.RADIUS_LG}px;
            min-width: {self.CARD_MIN_WIDTH}px;
            min-height: {self.CARD_MIN_HEIGHT}px;
        }}

        QFrame#glassCard:hover, QWidget#glassCard:hover {{
            border: 1px solid {self.BORDER_ACCENT};
        }}

        QLabel#glassCardTitle {{
            font-size: {self.FONT_SIZE_CARD_TITLE}px;
            font-weight: {self.FONT_WEIGHT_BOLD};
            color: {self.TEXT_PRIMARY};
        }}

        QLabel#glassCardSubtitle {{
            font-size: {self.FONT_SIZE_SMALL}px;
            font-weight: {self.FONT_WEIGHT_REGULAR};
            color: {self.TEXT_MUTED};
        }}

        QFrame#glassCardAccentBar {{
            background-color: {self.ACCENT};
            border-radius: {self.RADIUS_SM}px;
            max-width: 4px;
            min-width: 4px;
        }}
        """

    def button_stylesheet(self) -> str:
        """Build the stylesheet for primary, secondary and icon buttons.

        Returns:
            The QSS stylesheet applied to :class:`QPushButton` variants
            distinguished by object name or dynamic property.
        """
        return f"""
        QPushButton {{
            background-color: {self.SURFACE_CARD};
            color: {self.TEXT_PRIMARY};
            border: 1px solid {self.BORDER_LIGHT};
            border-radius: {self.RADIUS_MD}px;
            padding: {self.SPACING_SM}px {self.SPACING_MD}px;
            font-size: {self.FONT_SIZE_BODY}px;
            font-weight: {self.FONT_WEIGHT_MEDIUM};
        }}

        QPushButton:hover {{
            border: 1px solid {self.BORDER_ACCENT};
        }}

        QPushButton:pressed {{
            background-color: {self._rgba(self.PRIMARY, 0.25)};
        }}

        QPushButton:disabled {{
            color: {self.TEXT_MUTED};
            border: 1px solid {self.BORDER_LIGHT};
            background-color: {self.SURFACE_BASE};
        }}

        QPushButton[variant="primary"] {{
            background-color: {self.PRIMARY};
            border: 1px solid {self.PRIMARY};
            color: {self.TEXT_PRIMARY};
            font-weight: {self.FONT_WEIGHT_BOLD};
        }}

        QPushButton[variant="primary"]:hover {{
            background-color: {self._rgba(self.PRIMARY, 0.85)};
        }}

        QPushButton[variant="danger"] {{
            background-color: {self.ERROR};
            border: 1px solid {self.ERROR};
            color: {self.TEXT_PRIMARY};
            font-weight: {self.FONT_WEIGHT_BOLD};
        }}

        QPushButton[variant="ghost"] {{
            background-color: transparent;
            border: 1px solid transparent;
            color: {self.TEXT_SECONDARY};
        }}

        QPushButton[variant="ghost"]:hover {{
            color: {self.TEXT_PRIMARY};
            border: 1px solid {self.BORDER_LIGHT};
        }}
        """

    def scrollbar_stylesheet(self) -> str:
        """Build the stylesheet for vertical and horizontal scrollbars.

        Returns:
            The QSS stylesheet applied to :class:`QScrollBar` instances
            throughout the application.
        """
        return f"""
        QScrollBar:vertical {{
            background: transparent;
            width: 10px;
            margin: {self.SPACING_XS}px 0px;
        }}

        QScrollBar::handle:vertical {{
            background: {self._rgba(self.PRIMARY, 0.45)};
            border-radius: {self.RADIUS_SM}px;
            min-height: 32px;
        }}

        QScrollBar::handle:vertical:hover {{
            background: {self._rgba(self.PRIMARY, 0.7)};
        }}

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
            background: transparent;
        }}

        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: transparent;
        }}

        QScrollBar:horizontal {{
            background: transparent;
            height: 10px;
            margin: 0px {self.SPACING_XS}px;
        }}

        QScrollBar::handle:horizontal {{
            background: {self._rgba(self.PRIMARY, 0.45)};
            border-radius: {self.RADIUS_SM}px;
            min-width: 32px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background: {self._rgba(self.PRIMARY, 0.7)};
        }}

        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
            background: transparent;
        }}

        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: transparent;
        }}
        """

    def input_stylesheet(self) -> str:
        """Build the stylesheet for text inputs and editable fields.

        Returns:
            The QSS stylesheet applied to :class:`QLineEdit`,
            :class:`QTextEdit` and :class:`QPlainTextEdit` widgets.
        """
        return f"""
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {self.SURFACE_CARD};
            color: {self.TEXT_PRIMARY};
            border: 1px solid {self.BORDER_LIGHT};
            border-radius: {self.RADIUS_MD}px;
            padding: {self.SPACING_SM}px;
            selection-background-color: {self._rgba(self.PRIMARY, 0.45)};
            selection-color: {self.TEXT_PRIMARY};
        }}

        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border: 1px solid {self.BORDER_ACCENT};
        }}

        QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
            color: {self.TEXT_MUTED};
            background-color: {self.SURFACE_BASE};
        }}

        QLineEdit#commandPaletteSearch {{
            font-size: {self.FONT_SIZE_SUBTITLE}px;
            font-weight: {self.FONT_WEIGHT_MEDIUM};
            padding: {self.SPACING_MD}px;
            border-radius: {self.RADIUS_LG}px;
        }}

        QComboBox {{
            background-color: {self.SURFACE_CARD};
            color: {self.TEXT_PRIMARY};
            border: 1px solid {self.BORDER_LIGHT};
            border-radius: {self.RADIUS_MD}px;
            padding: {self.SPACING_SM}px;
        }}

        QComboBox:hover {{
            border: 1px solid {self.BORDER_ACCENT};
        }}

        QComboBox QAbstractItemView {{
            background-color: {self.SURFACE_CARD};
            color: {self.TEXT_PRIMARY};
            border: 1px solid {self.BORDER_LIGHT};
            selection-background-color: {self._rgba(self.PRIMARY, 0.35)};
            outline: none;
        }}

        QCheckBox, QRadioButton {{
            color: {self.TEXT_SECONDARY};
            spacing: {self.SPACING_SM}px;
        }}

        QCheckBox::indicator, QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {self.BORDER_LIGHT};
            border-radius: {self.RADIUS_SM}px;
            background-color: {self.SURFACE_CARD};
        }}

        QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
            background-color: {self.PRIMARY};
            border: 1px solid {self.PRIMARY};
        }}
        """

    def menu_stylesheet(self) -> str:
        """Build the stylesheet for menus, list views and the command
        palette results list.

        Returns:
            The QSS stylesheet applied to :class:`QMenu`,
            :class:`QListWidget` and related popup surfaces.
        """
        return f"""
        QMenu {{
            background-color: {self.SURFACE_CARD};
            color: {self.TEXT_PRIMARY};
            border: 1px solid {self.BORDER_LIGHT};
            border-radius: {self.RADIUS_MD}px;
            padding: {self.SPACING_XS}px;
        }}

        QMenu::item {{
            padding: {self.SPACING_SM}px {self.SPACING_MD}px;
            border-radius: {self.RADIUS_SM}px;
        }}

        QMenu::item:selected {{
            background-color: {self._rgba(self.PRIMARY, 0.25)};
            color: {self.TEXT_PRIMARY};
        }}

        QMenu::separator {{
            height: 1px;
            background: {self.BORDER_LIGHT};
            margin: {self.SPACING_XS}px {self.SPACING_SM}px;
        }}

        QListWidget {{
            background-color: transparent;
            border: none;
            outline: none;
        }}

        QListWidget::item {{
            padding: {self.SPACING_SM}px {self.SPACING_MD}px;
            border-radius: {self.RADIUS_SM}px;
            color: {self.TEXT_SECONDARY};
        }}

        QListWidget::item:hover {{
            background-color: {self._rgba(self.PRIMARY, 0.14)};
            color: {self.TEXT_PRIMARY};
        }}

        QListWidget::item:selected {{
            background-color: {self._rgba(self.PRIMARY, 0.28)};
            color: {self.TEXT_PRIMARY};
        }}

        QWidget#commandPaletteOverlay {{
            background-color: {self._rgba(self.SURFACE_BASE, 0.85)};
        }}

        QWidget#commandPaletteOverlay QListWidget#commandPaletteResults {{
            background-color: {self.SURFACE_GLASS};
            border: 1px solid {self.BORDER_LIGHT};
            border-radius: {self.RADIUS_LG}px;
            padding: {self.SPACING_SM}px;
        }}
        """

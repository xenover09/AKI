"""
Centralized theme definition for the AKI desktop application.

This module is the single source of truth for every color, radius,
font, and spacing value used across the UI. No other module should
hardcode a color, font size, or spacing value — everything must be
sourced from :class:`BlueTheme`.

Style: Dark Futuristic / Glassmorphism / Cyber Blue / Neon Accent.
"""

from __future__ import annotations


class BlueTheme:
    """Centralized design system for AKI's Dark Blue Glass UI."""

    # ------------------------------------------------------------------
    # Colors
    # ------------------------------------------------------------------
    BACKGROUND: str = "#070B14"
    SURFACE: str = "#0D1420"
    CARD: str = "rgba(18, 27, 43, 0.72)"
    ACCENT: str = "#00D4FF"
    ACCENT_HOVER: str = "#33DFFF"
    TEXT_PRIMARY: str = "#E8F4FF"
    TEXT_SECONDARY: str = "#7C93B3"
    SUCCESS: str = "#2ED9A3"
    WARNING: str = "#FFB84D"
    ERROR: str = "#FF5C7A"
    BORDER: str = "rgba(0, 212, 255, 0.18)"
    SHADOW: str = "rgba(0, 212, 255, 0.25)"

    # ------------------------------------------------------------------
    # Radius
    # ------------------------------------------------------------------
    RADIUS_SMALL: int = 6
    RADIUS_MEDIUM: int = 12
    RADIUS_LARGE: int = 20

    # ------------------------------------------------------------------
    # Fonts
    # ------------------------------------------------------------------
    FONT_FAMILY: str = "Segoe UI"
    FONT_TITLE: int = 22
    FONT_HEADER: int = 16
    FONT_BODY: int = 12
    FONT_SMALL: int = 10

    # ------------------------------------------------------------------
    # Spacing
    # ------------------------------------------------------------------
    SPACING_XS: int = 4
    SPACING_SM: int = 8
    SPACING_MD: int = 16
    SPACING_LG: int = 24
    SPACING_XL: int = 32

    def global_stylesheet(self) -> str:
        """
        Build the application-wide base stylesheet.

        Returns:
            A Qt stylesheet string applied to the entire QApplication.
        """
        return f"""
            QWidget {{
                background-color: {self.BACKGROUND};
                color: {self.TEXT_PRIMARY};
                font-family: '{self.FONT_FAMILY}';
                font-size: {self.FONT_BODY}px;
            }}

            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 0px;
            }}

            QScrollBar::handle:vertical {{
                background: {self.ACCENT};
                border-radius: {self.RADIUS_SMALL}px;
                min-height: 24px;
            }}

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}

            QToolTip {{
                background-color: {self.SURFACE};
                color: {self.TEXT_PRIMARY};
                border: 1px solid {self.BORDER};
                border-radius: {self.RADIUS_SMALL}px;
                padding: {self.SPACING_XS}px {self.SPACING_SM}px;
            }}
        """

    def button_stylesheet(self) -> str:
        """
        Build the stylesheet applied to standard interactive buttons.

        Returns:
            A Qt stylesheet string targeting QPushButton widgets.
        """
        return f"""
            QPushButton {{
                background-color: rgba(0, 212, 255, 0.10);
                color: {self.TEXT_PRIMARY};
                border: 1px solid {self.BORDER};
                border-radius: {self.RADIUS_MEDIUM}px;
                padding: {self.SPACING_SM}px {self.SPACING_MD}px;
                font-size: {self.FONT_BODY}px;
                font-weight: 600;
            }}

            QPushButton:hover {{
                background-color: rgba(0, 212, 255, 0.22);
                border: 1px solid {self.ACCENT_HOVER};
                color: {self.ACCENT_HOVER};
            }}

            QPushButton:pressed {{
                background-color: rgba(0, 212, 255, 0.32);
                border: 1px solid {self.ACCENT};
            }}

            QPushButton:disabled {{
                background-color: rgba(124, 147, 179, 0.08);
                color: {self.TEXT_SECONDARY};
                border: 1px solid rgba(124, 147, 179, 0.15);
            }}
        """

    def card_stylesheet(self) -> str:
        """
        Build the stylesheet applied to glassmorphic dashboard cards.

        Returns:
            A Qt stylesheet string targeting card container widgets.
        """
        return f"""
            QFrame#card {{
                background-color: {self.CARD};
                border: 1px solid {self.BORDER};
                border-radius: {self.RADIUS_LARGE}px;
            }}

            QFrame#card:hover {{
                border: 1px solid {self.ACCENT};
            }}

            QLabel#cardTitle {{
                color: {self.TEXT_SECONDARY};
                font-size: {self.FONT_SMALL}px;
                font-weight: 600;
                letter-spacing: 1px;
            }}

            QLabel#cardValue {{
                color: {self.TEXT_PRIMARY};
                font-size: {self.FONT_HEADER}px;
                font-weight: 700;
            }}

            QLabel#cardSubtitle {{
                color: {self.TEXT_SECONDARY};
                font-size: {self.FONT_SMALL}px;
            }}
        """

    def sidebar_stylesheet(self) -> str:
        """
        Build the stylesheet applied to the animated navigation sidebar.

        Returns:
            A Qt stylesheet string targeting the sidebar container and
            its navigation buttons.
        """
        return f"""
            QFrame#sidebar {{
                background-color: {self.SURFACE};
                border: none;
                border-right: 1px solid {self.BORDER};
            }}

            QPushButton#sidebarItem {{
                background-color: transparent;
                color: {self.TEXT_SECONDARY};
                border: none;
                border-radius: {self.RADIUS_MEDIUM}px;
                text-align: left;
                padding: {self.SPACING_SM}px {self.SPACING_MD}px;
                font-size: {self.FONT_BODY}px;
                font-weight: 600;
            }}

            QPushButton#sidebarItem:hover {{
                background-color: rgba(0, 212, 255, 0.12);
                color: {self.ACCENT_HOVER};
            }}

            QPushButton#sidebarItem:checked {{
                background-color: rgba(0, 212, 255, 0.18);
                color: {self.ACCENT};
                border-left: 2px solid {self.ACCENT};
            }}

            QPushButton#sidebarToggle {{
                background-color: transparent;
                border: 1px solid {self.BORDER};
                border-radius: {self.RADIUS_SMALL}px;
                color: {self.TEXT_SECONDARY};
            }}

            QPushButton#sidebarToggle:hover {{
                color: {self.ACCENT};
                border: 1px solid {self.ACCENT};
            }}
        """

    def titlebar_stylesheet(self) -> str:
        """
        Build the stylesheet applied to the custom frameless title bar.

        Returns:
            A Qt stylesheet string targeting the title bar container and
            its window control buttons.
        """
        return f"""
            QFrame#titleBar {{
                background-color: {self.SURFACE};
                border: none;
                border-bottom: 1px solid {self.BORDER};
            }}

            QLabel#titleBarLogo {{
                color: {self.ACCENT};
                font-size: {self.FONT_HEADER}px;
                font-weight: 800;
                letter-spacing: 2px;
            }}

            QLabel#titleBarStatus {{
                color: {self.TEXT_SECONDARY};
                font-size: {self.FONT_SMALL}px;
            }}

            QPushButton#titleBarControl {{
                background-color: transparent;
                color: {self.TEXT_SECONDARY};
                border: none;
                border-radius: {self.RADIUS_SMALL}px;
            }}

            QPushButton#titleBarControl:hover {{
                background-color: rgba(0, 212, 255, 0.15);
                color: {self.ACCENT};
            }}

            QPushButton#titleBarCloseControl:hover {{
                background-color: {self.ERROR};
                color: {self.TEXT_PRIMARY};
            }}
        """

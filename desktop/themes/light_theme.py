from typing import Dict

class LightTheme:
    """Solid Professional Light Theme implementation."""

    # ---------------------------------------------------------
    # Core Colors
    # ---------------------------------------------------------
    BACKGROUND = "#F4F4F6"
    SURFACE_BASE = "#FFFFFF"
    SURFACE_CARD = "#FFFFFF"
    SURFACE_ELEVATED = "#F4F4F6"

    # ---------------------------------------------------------
    # State Colors
    # ---------------------------------------------------------
    HOVER = "#E2E2E8"
    PRESSED = "#D1D1D6"
    ACCENT = "#A259FF"
    ACCENT_HOVER = "#B875FF"

    # ---------------------------------------------------------
    # Status Colors
    # ---------------------------------------------------------
    SUCCESS = "#10B981"
    WARNING = "#F59E0B"
    ERROR = "#EF4444"
    INFO = "#3B82F6"

    # ---------------------------------------------------------
    # Typography
    # ---------------------------------------------------------
    TEXT_PRIMARY = "#1A1A20"
    TEXT_SECONDARY = "#6B6B76"
    TEXT_MUTED = "#6B6B76"
    TEXT_ACCENT = "#A259FF"

    # ---------------------------------------------------------
    # Borders
    # ---------------------------------------------------------
    BORDER_SUBTLE = "#E2E2E8"
    BORDER_LIGHT = "#E2E2E8"
    BORDER_ACCENT = "#A259FF"

    # ---------------------------------------------------------
    # Metrics
    # ---------------------------------------------------------
    RADIUS_SM = 4
    RADIUS_MD = 6
    RADIUS_LG = 8
    RADIUS_PILL = 9999

    # ---------------------------------------------------------
    # Global StyleSheet (No Glass)
    # ---------------------------------------------------------
    @classmethod
    def global_stylesheet(cls) -> str:
        return f"""
        QWidget {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            color: {cls.TEXT_PRIMARY};
            font-size: 13px;
        }}
        QMainWindow, QDialog {{
            background-color: {cls.BACKGROUND};
        }}
        QPushButton {{
            background-color: {cls.SURFACE_CARD};
            color: {cls.TEXT_PRIMARY};
            border: 1px solid {cls.BORDER_LIGHT};
            border-radius: {cls.RADIUS_MD}px;
            padding: 6px 12px;
        }}
        QPushButton:hover {{
            background-color: {cls.HOVER};
        }}
        QPushButton:pressed {{
            background-color: {cls.PRESSED};
        }}
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {cls.SURFACE_CARD};
            color: {cls.TEXT_PRIMARY};
            border: 1px solid {cls.BORDER_LIGHT};
            border-radius: {cls.RADIUS_MD}px;
            padding: 6px;
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border: 1px solid {cls.ACCENT};
        }}
        QScrollBar:vertical {{
            border: none;
            background: {cls.BACKGROUND};
            width: 8px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {cls.BORDER_LIGHT};
            min-height: 20px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {cls.TEXT_MUTED};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            border: none;
            background: none;
        }}
        QMenu {{
            background-color: {cls.SURFACE_ELEVATED};
            border: 1px solid {cls.BORDER_LIGHT};
            border-radius: {cls.RADIUS_MD}px;
        }}
        QMenu::item {{
            padding: 4px 24px 4px 8px;
        }}
        QMenu::item:selected {{
            background-color: {cls.HOVER};
        }}
        QToolTip {{
            background-color: {cls.SURFACE_ELEVATED};
            color: {cls.TEXT_PRIMARY};
            border: 1px solid {cls.BORDER_LIGHT};
            border-radius: {cls.RADIUS_SM}px;
        }}
        """

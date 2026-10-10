from PySide6.QtCore import QObject, Signal, QSettings, Qt
from PySide6.QtWidgets import QApplication
from desktop.themes.aki_theme import AkiTheme
from desktop.themes.light_theme import LightTheme

class ThemeManager(QObject):
    themeChanged = Signal(object)
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        return cls._instance
    
    def __init__(self, app: QApplication):
        super().__init__()
        ThemeManager._instance = self
        self._app = app
        self._settings = QSettings("AKI", "DesktopOS")
        self._current_appearance = self._settings.value("appearance", "dark")
        self._theme = AkiTheme()
        self.apply_theme()

    def is_dark(self) -> bool:
        if self._current_appearance == "light":
            return False
        if self._current_appearance == "system":
            style_hints = QApplication.styleHints()
            return style_hints.colorScheme() == Qt.ColorScheme.Dark
        return True

    def set_appearance(self, appearance: str):
        if appearance not in ["dark", "light", "system"]:
            appearance = "dark"
        self._current_appearance = appearance
        self._settings.setValue("appearance", appearance)
        self.apply_theme()

    def get_appearance(self) -> str:
        return self._current_appearance

    def apply_theme(self):
        if self.is_dark():
            self._theme = AkiTheme()
        else:
            self._theme = LightTheme()
        self._app.setStyleSheet(self._theme.global_stylesheet())
        self.themeChanged.emit(self._theme)

    @property
    def theme(self):
        return self._theme

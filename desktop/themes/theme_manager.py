from PySide6.QtCore import QObject, Signal, QSettings, Qt
from PySide6.QtWidgets import QApplication
from desktop.themes.aki_theme import AkiTheme

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
        self._current_appearance = "dark"
        self._theme = AkiTheme()
        self.apply_theme()

    def is_dark(self) -> bool:
        return True

    def set_appearance(self, appearance: str):
        pass

    def get_appearance(self) -> str:
        return "dark"

    def apply_theme(self):
        self._theme = AkiTheme()
        self._app.setStyleSheet(self._theme.global_stylesheet())
        self.themeChanged.emit(self._theme)

    @property
    def theme(self):
        return self._theme

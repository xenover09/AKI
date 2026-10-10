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
        
        self._app.styleHints().colorSchemeChanged.connect(self._on_system_scheme_changed)
        self.apply_theme()

    def is_dark(self) -> bool:
        if self._current_appearance == "system":
            return self._app.styleHints().colorScheme() == Qt.ColorScheme.Dark
        return self._current_appearance == "dark"

    def set_appearance(self, appearance: str):
        if appearance not in ["dark", "light", "system"]:
            return
        self._current_appearance = appearance
        self._settings.setValue("appearance", appearance)
        self.apply_theme()

    def get_appearance(self) -> str:
        return self._current_appearance

    def _on_system_scheme_changed(self, scheme):
        if self._current_appearance == "system":
            self.apply_theme()

    def apply_theme(self):
        self._theme = AkiTheme() if self.is_dark() else LightTheme()
        self._app.setStyleSheet(self._theme.global_stylesheet())
        self.themeChanged.emit(self._theme)

    @property
    def theme(self):
        return self._theme

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from desktop.app import AKIApplication
from desktop.themes.theme_manager import ThemeManager

class MockSettings:
    ai_provider = "openai_compatible"
    ai_api_key = "mock"
    ai_base_url = "mock"
    voice_output = False
    voice_input = False
    ai_connected = False
    ai_model = "mock"
    available_voices = []
    tts_voice = ""
    theme = "dark"

class MockBoot:
    settings = MockSettings()

class MockRuntime:
    boot = MockBoot()
    ai_service = None
    conversation_service = None
    database_service = None
    action_system = None

def main():
    app = AKIApplication(sys.argv, runtime=MockRuntime())
    
    def step1_dark():
        if not app._main_window:
            return
        win = app._main_window
        win.grab().save("dark_dashboard.png")
        
        # Switch to light
        tm = ThemeManager.get_instance()
        tm.set_appearance("light")
        QTimer.singleShot(1000, step2_light)

    def step2_light():
        win = app._main_window
        win.grab().save("light_dashboard.png")
        
        # Open settings
        win._web_view.page().runJavaScript("document.getElementById('btnOpenSettings').click();")
        QTimer.singleShot(1000, step3_settings_appearance)

    def step3_settings_appearance():
        win = app._main_window
        win.grab().save("settings_appearance.png")
        
        # Open profile or just scroll
        win._web_view.page().runJavaScript("document.querySelector('.os-settings-content').scrollTop = 0;")
        QTimer.singleShot(500, step4_settings_profile)

    def step4_settings_profile():
        win = app._main_window
        win.grab().save("settings_profile.png")
        
        # Close settings, clear greeting
        win._web_view.page().runJavaScript("document.getElementById('btnCloseSettings').click(); setTimeout(() => document.getElementById('akiGreeting').innerText = '', 100);")
        QTimer.singleShot(1000, step5_blank)

    def step5_blank():
        win = app._main_window
        win.grab().save("empty_dashboard.png")
        
        app._quit_application()

    QTimer.singleShot(4000, step1_dark)
    sys.exit(app.run())

if __name__ == "__main__":
    main()

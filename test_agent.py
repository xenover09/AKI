import sys
import json
import threading
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from ai_engine.agent import Agent
from desktop.agent_view import AgentView
from desktop.themes.aki_theme import AkiTheme

class MockAIService:
    def __init__(self):
        self.step = 0
        
    def generate(self, history):
        self.step += 1
        if self.step == 1:
            return json.dumps({
                "action": "goto",
                "params": {"url": "https://example.com"},
                "reasoning": "I need to visit example.com"
            })
        elif self.step == 2:
            return json.dumps({
                "action": "read_text",
                "reasoning": "I need to read the page content to find the title"
            })
        else:
            return json.dumps({
                "action": "report",
                "params": {"text": "Example Domain"},
                "reasoning": "I found the title"
            })

def run_test(view):
    ai = MockAIService()
    agent = Agent(ai, log_callback=lambda msg: print(f"AGENT: {msg}"))
    
    # We will hook the view's log signal to the agent's log
    agent.log_callback = lambda msg: view.log_signal.emit(msg)
    
    # Run the agent (this blocks the thread, which is fine)
    result = agent.run("go to example.com and tell me the page title")
    print("\nFINAL RESULT:", result)
    
    # Clean up browser
    agent.browser.close()
    
    # Exit app after a short delay
    QTimer.singleShot(2000, QApplication.instance().quit)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    theme = AkiTheme()
    view = AgentView(theme)
    view.resize(600, 400)
    view.show()
    
    # Auto-approve after 2 seconds when dialog shows up
    def auto_approve():
        if view.approval_container.isVisible():
            # Grab screenshot of the dialog for QA!
            view.grab().save("approval_dialog_qa.png")
            print("Auto-approving the dialog...")
            view.btn_approve.click()
    
    timer = QTimer()
    timer.timeout.connect(auto_approve)
    timer.start(1000)
    
    thread = threading.Thread(target=run_test, args=(view,), daemon=True)
    thread.start()
    
    sys.exit(app.exec())

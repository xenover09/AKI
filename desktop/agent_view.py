import threading
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QTextEdit, QLabel, QFrame)

from permissions import get_permission_helper

class AgentView(QFrame):
    """View to show live agent step logs and handle permission requests."""
    
    log_signal = Signal(str)
    
    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setObjectName("agentView")
        self._setup_ui()
        
        # Connect to the permission helper to handle incoming requests
        helper = get_permission_helper()
        helper.request_signal.connect(self.show_approval_request, Qt.ConnectionType.QueuedConnection)
        self.log_signal.connect(self.append_log, Qt.ConnectionType.QueuedConnection)
        
        self.current_event = None
        self._timeout_timer = QTimer(self)
        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.timeout.connect(self._auto_deny)

    def _setup_ui(self):
        self.setStyleSheet(f"""
            QFrame#agentView {{
                background-color: {self.theme.SURFACE_CARD};
                border: 1px solid {self.theme.BORDER_LIGHT};
                border-radius: {self.theme.RADIUS_LG}px;
            }}
            QTextEdit {{
                background-color: {self.theme.SURFACE_BASE};
                color: {self.theme.TEXT_PRIMARY};
                border: 1px solid {self.theme.BORDER_LIGHT};
                border-radius: 4px;
                font-family: 'Consolas', monospace;
            }}
        """)
        layout = QVBoxLayout(self)
        
        title = QLabel("Agent Live Feed")
        title.setStyleSheet(f"color: {self.theme.TEXT_PRIMARY}; font-weight: bold; font-size: 16px;")
        layout.addWidget(title)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)
        
        # Approval Area
        self.approval_container = QWidget()
        self.approval_container.setVisible(False)
        app_layout = QVBoxLayout(self.approval_container)
        
        self.request_label = QLabel("Permission Required")
        self.request_label.setStyleSheet(f"color: {self.theme.WARNING}; font-weight: bold;")
        app_layout.addWidget(self.request_label)
        
        btn_layout = QHBoxLayout()
        self.btn_approve = QPushButton("Approve")
        self.btn_approve.setStyleSheet(f"background-color: {self.theme.SUCCESS}; color: #000; border: none; padding: 6px; border-radius: 4px;")
        self.btn_approve.clicked.connect(self._on_approve)
        
        self.btn_deny = QPushButton("Deny")
        self.btn_deny.setStyleSheet(f"background-color: {self.theme.ERROR}; color: #000; border: none; padding: 6px; border-radius: 4px;")
        self.btn_deny.clicked.connect(self._on_deny)
        
        btn_layout.addWidget(self.btn_approve)
        btn_layout.addWidget(self.btn_deny)
        app_layout.addLayout(btn_layout)
        
        layout.addWidget(self.approval_container)

    @Slot(str)
    def append_log(self, text: str):
        self.log_area.append(text)

    @Slot(str, str, object)
    def show_approval_request(self, title: str, message: str, event: threading.Event):
        self.request_label.setText(f"{title}\n{message}")
        self.current_event = event
        self.approval_container.setVisible(True)
        self._timeout_timer.start(60000)
        self.append_log(f"[AUTH REQUIRED] {title}")

    def _on_approve(self):
        self.approval_container.setVisible(False)
        self._timeout_timer.stop()
        self.append_log("[AUTH] Request Approved.")
        if self.current_event:
            helper = get_permission_helper()
            helper.last_result = True
            self.current_event.set()
            self.current_event = None

    def _on_deny(self):
        self.approval_container.setVisible(False)
        self._timeout_timer.stop()
        self.append_log("[AUTH] Request Denied.")
        if self.current_event:
            helper = get_permission_helper()
            helper.last_result = False
            self.current_event.set()
            self.current_event = None

    def _auto_deny(self):
        if self.approval_container.isVisible():
            self._on_deny()

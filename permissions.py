import enum
import threading
from typing import Callable
from PySide6.QtCore import Qt, QObject, Signal, Slot, QTimer
from PySide6.QtWidgets import QMessageBox, QApplication

class PermissionTier(enum.Enum):
    SAFE = "SAFE"
    SENSITIVE = "SENSITIVE"
    DANGEROUS = "DANGEROUS"

class PermissionDialogHelper(QObject):
    request_signal = Signal(str, str, object)

    def __init__(self):
        super().__init__()
        self.request_signal.connect(self._show_dialog, Qt.ConnectionType.QueuedConnection)

    @Slot(str, str, object)
    def _show_dialog(self, title: str, message: str, event: threading.Event):
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        
        timer = QTimer(msg_box)
        timer.setSingleShot(True)
        timer.timeout.connect(msg_box.reject)
        timer.start(60000)
        
        res = msg_box.exec()
        self.last_result = (res == QMessageBox.StandardButton.Yes)
        event.set()

_helper = None

def get_permission_helper():
    global _helper
    if _helper is None:
        _helper = PermissionDialogHelper()
        app = QApplication.instance()
        if app:
            _helper.moveToThread(app.thread())
    return _helper

def check_permission(tier: PermissionTier, action_details: str) -> bool:
    if tier == PermissionTier.SAFE:
        return True
    if tier == PermissionTier.DANGEROUS:
        return False
        
    app = QApplication.instance()
    if not app:
        return False
        
    helper = get_permission_helper()
        
    event = threading.Event()
    helper.request_signal.emit(
        "Action Approval Required", 
        f"Do you allow the following action?\n\n{action_details}\n\nTimeout in 60s will auto-deny.",
        event
    )
    event.wait()
    return getattr(helper, "last_result", False)

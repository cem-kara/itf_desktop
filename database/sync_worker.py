from PySide6.QtCore import QThread, Signal
from database.sync_service import SyncService


class SyncWorker(QThread):
    finished = Signal()
    error = Signal(str)

    def run(self):
        try:
            sync = SyncService()
            sync.sync_personel()
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

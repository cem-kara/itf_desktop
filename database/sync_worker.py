from PySide6.QtCore import QThread, Signal
from core.logger import logger

from database.sqlite_manager import SQLiteManager
from database.repository_registry import RepositoryRegistry
from database.sync_service import SyncService


class SyncWorker(QThread):
    """
    Arka planda senkron işlemini yürüten QThread
    """

    finished = Signal()
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # 🔹 SQLite bağlantısı
        self.db = SQLiteManager()

        # 🔹 Repository registry (tüm tablolar)
        self.registry = RepositoryRegistry(self.db)

        # 🔹 Senkron servisi
        self.sync_service = SyncService(
            db=self.db,
            registry=self.registry
        )

        self._running = True

    # -----------------------------------------------------

    def run(self):
        logger.info("Otomatik senkron başlatılıyor")

        try:
            if not self._running:
                return

            # 🔁 TÜM TABLOLAR
            self.sync_service.sync_all()

            logger.info("Otomatik senkron tamamlandı")
            self.finished.emit()

        except Exception as e:
            logger.exception("Senkron sırasında hata oluştu")
            self.error.emit(str(e))

        finally:
            self.db.close()

    # -----------------------------------------------------

    def stop(self):
        """
        Thread güvenli şekilde durdurulur
        """
        self._running = False
        self.quit()
        self.wait()

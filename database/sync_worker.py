from PySide6.QtCore import QThread, Signal
from core.logger import logger

from database.sqlite_manager import SQLiteManager
from database.repository_registry import RepositoryRegistry
from database.sync_service import SyncService


class SyncWorker(QThread):
    """
    Arka planda senkron işlemini yürüten QThread

    ÖNEMLİ: SQLite nesneleri oluşturuldukları thread'de kullanılmalıdır.
    Bu yüzden db, registry ve sync_service run() içinde oluşturulur.
    """

    finished = Signal()
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True

    # -----------------------------------------------------

    def run(self):
        """
        Worker thread — tüm DB işlemleri burada başlar ve biter.
        """
        logger.info("Otomatik senkron başlatılıyor")

        db = None

        try:
            if not self._running:
                return

            # 🔹 Bağlantılar WORKER THREAD içinde oluşturulmalı
            db = SQLiteManager()
            registry = RepositoryRegistry(db)
            sync_service = SyncService(
                db=db,
                registry=registry
            )

            # 🔁 TÜM TABLOLAR
            sync_service.sync_all()

            logger.info("Otomatik senkron tamamlandı")
            self.finished.emit()

        except Exception as e:
            logger.exception("Senkron sırasında hata oluştu")
            self.error.emit(str(e))

        finally:
            if db:
                db.close()

    # -----------------------------------------------------

    def stop(self):
        """
        Thread güvenli şekilde durdurulur
        """
        self._running = False
        self.quit()
        self.wait()
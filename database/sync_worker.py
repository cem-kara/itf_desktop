from PySide6.QtCore import QThread, Signal
from PySide6.QtCore import QThread, Signal
from core.logger import logger, log_sync_error, get_user_friendly_error
from core.config import AppConfig

from database.sqlite_manager import SQLiteManager
from core.di import get_registry
from database.sync_service import SyncService, SyncBatchError


class SyncWorker(QThread):
    """
    Arka planda senkron işlemini yürüten QThread

    ÖNEMLİ: SQLite nesneleri oluşturuldukları thread'de kullanılmalıdır.
    Bu yüzden db, registry ve sync_service run() içinde oluşturulur.
    """

    finished = Signal()
    error = Signal(str, str)  # (short_message, detailed_message)
    progress = Signal(str, int, int)  # (table_name, current, total)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True

    # -----------------------------------------------------

    def run(self):
        """
        Worker thread — tüm DB işlemleri burada başlar ve biter.
        """
        if not AppConfig.is_online_mode():
            logger.info("Offline mod: SyncWorker atlandi")
            self.finished.emit()
            return

        logger.info("=" * 60)
        logger.info("SYNC İŞLEMİ BAŞLADI")
        logger.info("=" * 60)

        db = None

        try:
            if not self._running:
                return

            # 🔹 Bağlantılar WORKER THREAD içinde oluşturulmalı
            db = SQLiteManager()
            registry = get_registry(db)
            sync_service = SyncService(
                db=db,
                registry=registry
            )

            # 🔁 TÜM TABLOLAR - Hata takibi ile
            try:
                logger.info("Tüm tabloların senkronizasyonu başlıyor...")
                sync_service.sync_all()
                logger.info("✓ Tüm tablolar başarıyla senkronize edildi")

            except SyncBatchError as sync_error:
                short_msg, detail_msg = sync_error.to_ui_messages(max_tables=3)
                log_sync_error("GENEL", "sync_all", sync_error)
                self.error.emit(short_msg, detail_msg)
                return

            except Exception as sync_error:
                short_msg, detail_msg = get_user_friendly_error(sync_error)
                log_sync_error("GENEL", "sync_all", sync_error)
                self.error.emit(short_msg, detail_msg)
                return

            logger.info("=" * 60)
            logger.info("SYNC İŞLEMİ TAMAMLANDI")
            logger.info("=" * 60)
            self.finished.emit()

        except Exception as e:
            logger.error("=" * 60)
            logger.error("SYNC İŞLEMİ BAŞARISIZ")
            logger.error("=" * 60)
            logger.exception("Kritik senkron hatası")
            
            short_msg, detail_msg = get_user_friendly_error(e)
            self.error.emit(short_msg, detail_msg)

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




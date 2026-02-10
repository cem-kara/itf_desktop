from PySide6.QtCore import QThread, Signal
from core.logger import logger, log_sync_error, get_user_friendly_error

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
        logger.info("=" * 60)
        logger.info("SYNC İŞLEMİ BAŞLADI")
        logger.info("=" * 60)

        db = None
        failed_tables = []
        total_errors = []

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

            # 🔁 TÜM TABLOLAR - Hata takibi ile
            try:
                logger.info("Tüm tabloların senkronizasyonu başlıyor...")
                sync_service.sync_all()
                logger.info("✓ Tüm tablolar başarıyla senkronize edildi")
                
            except Exception as sync_error:
                # sync_all içinde hangi tablolarda hata olduğunu yakala
                error_msg = str(sync_error)
                
                # Hata mesajından tablo isimlerini çıkar
                if "tablolarda sync hatası:" in error_msg:
                    tables_part = error_msg.split("tablolarda sync hatası:")[-1]
                    failed_tables = [t.strip() for t in tables_part.split(",")]
                
                # Kullanıcı dostu mesaj oluştur
                short_msg, detail_msg = get_user_friendly_error(sync_error)
                
                if failed_tables:
                    short_msg = f"{len(failed_tables)} tabloda hata"
                    detail_msg = f"Başarısız tablolar: {', '.join(failed_tables[:3])}"
                    if len(failed_tables) > 3:
                        detail_msg += f" ve {len(failed_tables) - 3} tablo daha"
                
                log_sync_error("GENEL", "sync_all", sync_error)
                
                # Kısmi başarı durumunda da hatayı bildir
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
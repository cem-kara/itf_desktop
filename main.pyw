from database.sync_worker import SyncWorker
from core.logger import logger

sync_worker = None   # 🔴 GLOBAL REFERANS


def start_auto_sync():
    global sync_worker

    logger.info("Otomatik senkron başlatılıyor")

    # Çalışan thread varsa tekrar başlatma
    if sync_worker and sync_worker.isRunning():
        logger.info("Senkron zaten çalışıyor")
        return

    sync_worker = SyncWorker()
    sync_worker.finished.connect(lambda: logger.info("Senkron tamamlandı"))
    sync_worker.error.connect(lambda e: logger.error(f"Senkron hatası: {e}"))
    sync_worker.start()

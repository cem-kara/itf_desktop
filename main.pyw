import sys
import os

# Proje kök dizinini Python path'e ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from core.logger import logger
from core.paths import DB_PATH
from database.migrations import MigrationManager


def ensure_database():
    """Veritabanı şemasını kontrol et, yoksa oluştur."""
    import sqlite3

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='Personel'
    """)
    exists = cur.fetchone()

    if not exists:
        logger.info("Veritabanı bulunamadı — tablolar oluşturuluyor")
        MigrationManager(DB_PATH).reset_database()
    else:
        # Şema kontrolü
        cur.execute("PRAGMA table_info(Personel)")
        columns = [row[1] for row in cur.fetchall()]

        if "MezunOlunanFakulte" not in columns:
            logger.warning("Şema uyumsuz — veritabanı yeniden oluşturuluyor")
            MigrationManager(DB_PATH).reset_database()
        else:
            logger.info("Veritabanı şeması doğrulandı")

    conn.close()


def main():
    # High DPI desteği
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("ITF Desktop")

    # 1️⃣ Veritabanı kontrolü
    ensure_database()

    # 2️⃣ Ana pencere
    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()

    logger.info("Uygulama başlatıldı")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

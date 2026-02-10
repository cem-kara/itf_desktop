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
    """
    Veritabanı şemasını kontrol et ve gerekirse migration'ları çalıştır.
    
    Artık veri kaybı olmadan şema güncellemesi yapılıyor:
    - İlk kurulumda tüm tabloları oluşturur
    - Mevcut veritabanında sadece gerekli migration'ları uygular
    - Her migration öncesi otomatik yedekleme yapar
    - Veri korunarak şema güncellenir
    """
    import sqlite3
    from pathlib import Path

    # Veritabanı dosyası var mı kontrol et
    db_exists = Path(DB_PATH).exists()
    
    if not db_exists:
        logger.info("Veritabanı bulunamadı — ilk kurulum yapılıyor")
        migration_manager = MigrationManager(DB_PATH)
        migration_manager.run_migrations()
        return
    
    # Veritabanı var - migration kontrolü yap
    logger.info("Veritabanı bulundu — şema kontrolü yapılıyor")
    
    migration_manager = MigrationManager(DB_PATH)
    
    try:
        # Migration'ları çalıştır (gerekirse)
        migration_manager.run_migrations()
        logger.info("Veritabanı hazır ✓")
        
    except Exception as e:
        logger.error(f"Migration hatası: {e}")
        logger.error("Uygulamayı başlatmadan önce veritabanı sorununu çözün")
        raise


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
    window.showMaximized()

    logger.info("Uygulama başlatıldı")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

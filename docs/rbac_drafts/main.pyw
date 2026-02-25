import sys
import os
import shutil

# Proje kök dizinini Python path'e ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from core.logger import logger
from core.config import AppConfig
from core.log_manager import initialize_log_management
from core.paths import DB_PATH, TEMP_DIR
from database.migrations import MigrationManager
from database.sqlite_manager import SQLiteManager
from ui.theme_manager import ThemeManager

from core.auth.auth_service import AuthService
from core.auth.authorization_service import AuthorizationService
from core.auth.password_hasher import PasswordHasher
from core.auth.session_context import SessionContext
from ui.auth.login_dialog import LoginDialog


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
    app.setApplicationName(AppConfig.APP_NAME)
    ThemeManager.instance().apply_app_theme(app)
    app_icon_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "ui",
        "styles",
        "icons",
        "radyoloji_icon.ico",
    )
    if os.path.exists(app_icon_path):
        app.setWindowIcon(QIcon(app_icon_path))
    else:
        logger.warning(f"Uygulama ikonu bulunamadı: {app_icon_path}")

    # 1️⃣ Log yönetimi başlatma (cleanup, monitoring, statistics)
    initialize_log_management()

    # 2️⃣ Veritabanı kontrolü
    ensure_database()

    # 3️⃣ Auth hizmetleri
    db = SQLiteManager()
    session_context = SessionContext()
    hasher = PasswordHasher()
    auth_service = AuthService(db=db, hasher=hasher, session=session_context)

    login = LoginDialog(auth_service)
    if login.exec() != QDialog.Accepted:
        logger.info("Login iptal edildi, uygulama kapanıyor")
        return

    authorization_service = AuthorizationService(db)

    # 4️⃣ Ana pencere
    from ui.main_window import MainWindow
    window = MainWindow(
        db=db,
        session_context=session_context,
        authorization_service=authorization_service,
    )
    if os.path.exists(app_icon_path):
        window.setWindowIcon(QIcon(app_icon_path))
    window.showMaximized()

    logger.info("Uygulama başlatıldı")

    def _cleanup_temp():
        try:
            if os.path.isdir(TEMP_DIR):
                for name in os.listdir(TEMP_DIR):
                    path = os.path.join(TEMP_DIR, name)
                    try:
                        if os.path.isdir(path):
                            shutil.rmtree(path, ignore_errors=True)
                        else:
                            os.remove(path)
                    except Exception as item_err:
                        logger.warning(f"Temp temizlenemedi: {path} ({item_err})")
            logger.info("Temp klasoru temizlendi")
        except Exception as e:
            logger.warning(f"Temp temizleme hatasi: {e}")

    app.aboutToQuit.connect(_cleanup_temp)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

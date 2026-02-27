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
from core.di import get_auth_services
from ui.auth.login_dialog import LoginDialog
from ui.auth.change_password_dialog import ChangePasswordDialog
from ui.theme_manager import ThemeManager


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

    # 3 Login gate
    db = SQLiteManager()
    auth_service, authorization_service, session_context = get_auth_services(db)

    login_dialog = LoginDialog(auth_service)
    if os.path.exists(app_icon_path):
        login_dialog.setWindowIcon(QIcon(app_icon_path))
    if login_dialog.exec() != QDialog.Accepted:
        db.close()
        logger.info("Login iptal edildi - uygulama kapatiliyor")
        sys.exit(0)

    # 3.1 Ilk giris sifre degistirme zorunlulugu
    session_user = session_context.get_user()
    if session_user and session_user.must_change_password:
        pwd_dialog = ChangePasswordDialog(auth_service, session_user, parent=None)
        if pwd_dialog.exec() != QDialog.Accepted:
            auth_service.logout()
            db.close()
            logger.info("Sifre degistirme iptal edildi - uygulama kapatiliyor")
            sys.exit(0)

    # 4 Ana pencere
    from ui.main_window import MainWindow
    window = MainWindow(db=db, authorization_service=authorization_service, session_context=session_context)
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


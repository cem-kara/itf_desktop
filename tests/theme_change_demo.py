"""
Tema Değiştirme Demo — Runtime Light/Dark Tema Değişimi Testi

Kullanım:
    python -m pytest tests/theme_change_demo.py -v -s
"""
import sys
from pathlib import Path

# Proje root'u path'e ekle
root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from ui.theme_manager import ThemeManager
from core.logger import logger


class ThemeTestWindow(QMainWindow):
    """Tema değiştirme test penceresi."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tema Değiştirme Test")
        self.setMinimumSize(400, 300)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Başlık
        title = QLabel("Tema Değiştirme Test")
        title.setProperty("color-role", "primary")
        layout.addWidget(title)
        
        # Bilgi
        info = QLabel(
            "Aşağıdaki butonlarla tema değiştiremeyi test edin.\n"
            "Değişiklikler anında uygulanır."
        )
        info.setProperty("color-role", "primary")
        layout.addWidget(info)
        
        # Dark Tema Butonu
        btn_dark = QPushButton("Dark Tema'ya Geç")
        btn_dark.clicked.connect(self._switch_dark)
        layout.addWidget(btn_dark)
        
        # Light Tema Butonu
        btn_light = QPushButton("Light Tema'ya Geç")
        btn_light.clicked.connect(self._switch_light)
        layout.addWidget(btn_light)
        
        # Bilgi Label
        self.lbl_current = QLabel("Mevcut Tema: Dark")
        self.lbl_current.setProperty("color-role", "primary")
        layout.addWidget(self.lbl_current)
        
        layout.addStretch()
    
    def _switch_dark(self):
        """Dark tema'ya geç."""
        app = QApplication.instance()
        if not isinstance(app, QApplication):
            logger.error("QApplication örneği bulunamadı")
            return
        
        theme_manager = ThemeManager.instance()
        success = theme_manager.set_theme(app, "dark")
        if success:
            self.lbl_current.setText("Mevcut Tema: Dark ✓")
            logger.info("Dark temaya başarıyla geçildi")
        else:
            self.lbl_current.setText("Tema değişikliği başarısız!")
            logger.error("Dark temaya geçiş başarısız")
    
    def _switch_light(self):
        """Light tema'ya geç."""
        app = QApplication.instance()
        if not isinstance(app, QApplication):
            logger.error("QApplication örneği bulunamadı")
            return
        
        theme_manager = ThemeManager.instance()
        success = theme_manager.set_theme(app, "light")
        if success:
            self.lbl_current.setText("Mevcut Tema: Light ✓")
            logger.info("Light temaya başarıyla geçildi")
        else:
            self.lbl_current.setText("Tema değişikliği başarısız!")
            logger.error("Light temaya geçiş başarısız")


def test_theme_switching():
    """Tema değiştirme fonksiyonalitesi test."""
    app_instance = QApplication.instance() or QApplication(sys.argv)
    
    # İlk tema uyguı
    theme_manager = ThemeManager.instance()
    if isinstance(app_instance, QApplication):
        theme_manager.apply_app_theme(app_instance)
    
    # Test penceresini aç
    window = ThemeTestWindow()
    window.show()
    
    logger.info("Tema değiştirme test penceresi açılmıştır")
    logger.info("Butonları kullanarak Dark/Light tema değişimi test edin")
    
    # Test sonuçları (pytest için)
    assert theme_manager is not None, "ThemeManager örneği oluşturulamadı"
    assert app is not None, "QApplication örneği oluşturulamadı"
    
    return True


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Tema yöneticisini başlat
    theme_manager = ThemeManager.instance()
    theme_manager.apply_app_theme(app)
    
    # Test penceresini aç
    window = ThemeTestWindow()
    window.show()
    
    logger.info("Tema değiştirme test penceresi başlatılmıştır")
    
    sys.exit(app.exec())

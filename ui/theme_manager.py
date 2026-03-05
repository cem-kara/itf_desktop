# ui/theme_manager.py  ─  REPYS v3.1 · Merkezi Tema Yöneticisi
# ═══════════════════════════════════════════════════════════════
#
#  Tek sorumluluk: QApplication'a QSS + QPalette uygula,
#  tercihi ayarlar.json'a kaydet.
#
#  Kullanım:
#     ThemeManager.instance().apply_app_theme(app)   # başlangıçta
#     ThemeManager.instance().set_theme(app, "light")  # değişiklikte
#
# ═══════════════════════════════════════════════════════════════

from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication

from core import settings
from core.logger import logger
from ui.styles.themes import get_tokens

_QSS_PATH = Path(__file__).parent / "theme_template.qss"


class ThemeManager(QObject):
    """
    Tema uygulama ve değiştirme yöneticisi.

    Sinyaller:
        theme_changed(str) — "dark" veya "light"
    """

    theme_changed = Signal(str)
    _instance: "ThemeManager | None" = None
    
    # Signal: Tema değiştiğinde gönderilir
    theme_changed = Signal(str)  # tema adı (str)

    # ── Singleton ────────────────────────────────────────────
    @classmethod
    def instance(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        super().__init__()
        self._current = settings.get("theme", "dark")

    # ── Public API ───────────────────────────────────────────
    def apply_app_theme(self, app: QApplication) -> None:
        """Başlangıçta çağrılır — ayarlar.json'daki temayı uygular."""
        app.setStyle("Fusion")
        self._apply(app, self._current)
        logger.debug(f"Başlangıç teması uygulandı: {self._current}")

    def set_theme(self, app: QApplication, name: str) -> bool:
        """
        Runtime tema değişimi.

        Args:
            app:  QApplication örneği
            name: "dark" veya "light"

        Returns:
            True (başarılı) | False (hata)
        """
        name = name.lower()
        if name not in ("dark", "light"):
            logger.error(f"Geçersiz tema adı: {name}")
            return False

        try:
            self._apply(app, name)
            self._current = name
            settings.set("theme", name)
            self.theme_changed.emit(name)
            logger.info(f"Tema değiştirildi: {name}")
            return True
        except Exception as e:
            logger.error(f"Tema değişikliği hatası: {e}", exc_info=True)
            return False

    def current_theme(self) -> str:
        """Aktif tema adını döndür."""
        return self._current

    # ── İç implementasyon ────────────────────────────────────
    def _apply(self, app: QApplication, name: str) -> None:
        """QSS ve QPalette'i uygula."""
        tokens = get_tokens(name)

        # QSS
        try:
            template = _QSS_PATH.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.error(f"theme_template.qss bulunamadı: {_QSS_PATH}")
            template = ""

        qss = template
        for key, val in tokens.items():
            qss = qss.replace(f"{{{key}}}", val)
        app.setStyleSheet(qss)

        # QPalette
        p = QPalette()
        p.setColor(QPalette.Window,          QColor(tokens["BG_PRIMARY"]))
        p.setColor(QPalette.WindowText,      QColor(tokens["TEXT_PRIMARY"]))
        p.setColor(QPalette.Base,            QColor(tokens["BG_TERTIARY"]))
        p.setColor(QPalette.AlternateBase,   QColor(tokens["BG_SECONDARY"]))
        p.setColor(QPalette.Text,            QColor(tokens["TEXT_PRIMARY"]))
        p.setColor(QPalette.Button,          QColor(tokens["BG_SECONDARY"]))
        p.setColor(QPalette.ButtonText,      QColor(tokens["TEXT_PRIMARY"]))
        p.setColor(QPalette.ToolTipBase,     QColor(tokens["BG_ELEVATED"]))
        p.setColor(QPalette.ToolTipText,     QColor(tokens["TEXT_PRIMARY"]))
        p.setColor(QPalette.Highlight,       QColor(tokens["ACCENT"]))
        p.setColor(QPalette.HighlightedText,
                   QColor("#ffffff" if name == "light" else tokens["BG_DARK"]))
        p.setColor(QPalette.Link,            QColor(tokens["ACCENT2"]))
        p.setColor(QPalette.PlaceholderText, QColor(tokens["TEXT_MUTED"]))
        p.setColor(QPalette.Mid,             QColor(tokens["BG_ELEVATED"]))
        p.setColor(QPalette.Dark,
                   QColor(tokens["BORDER_PRIMARY"] if name == "light" else tokens["BG_DARK"]))
        p.setColor(QPalette.Light,           QColor(tokens["BG_TERTIARY"]))
        app.setPalette(p)

    # ── Geriye dönük uyumluluk ────────────────────────────────
    def load_stylesheet(self, theme_class=None) -> str:
        """
        Eski kodlar için — load_stylesheet() çağrıları bozulmasın.
        theme_class verilmese aktif temayı kullanır.
        """
        name = self._current
        if theme_class is not None:
            from ui.styles.light_theme import LightTheme
            name = "light" if theme_class is LightTheme else "dark"
        tokens = get_tokens(name)
        try:
            template = _QSS_PATH.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ""
        for key, val in tokens.items():
            template = template.replace(f"{{{key}}}", val)
        return template

    def refresh_theme(self, app: QApplication | None = None) -> None:
        """Mevcut temayı yeniden uygula (cache sıfırlama)."""
        if app is None:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
        if app:
            self._apply(app, self._current)

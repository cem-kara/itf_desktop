# ui/theme_manager.py  ─  REPYS v3 · Merkezi Tema Yöneticisi
from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QWidget, QDateEdit
from PySide6.QtGui import QColor, QPalette

from core.logger import logger
from ui.styles import Colors, DarkTheme, STYLES
from ui.styles.components import STYLES, ComponentStyles


class ThemeManager(QObject):
    """
    Merkezi Tema Yöneticisi — Singleton.

    Kullanım:
        ThemeManager.instance().apply_app_theme(app)
        ThemeManager.instance().set_theme(ThemeType.LIGHT)
    """

    _instance: "ThemeManager | None" = None
    
    # Signal: Tema değiştiğinde gönderilir
    theme_changed = Signal(str)  # tema adı (str)

    def __init__(self) -> None:
        super().__init__()
        self._theme_template_path = Path(__file__).with_name("theme_template.qss")
        self._stylesheet_cache: str | None = None
        self._current_theme_type = None  # Mevcut tema tipi
        
        # Tema registry
        from ui.styles.theme_registry import ThemeRegistry, ThemeType
        self._registry = ThemeRegistry.instance()
        self._current_theme_type = ThemeType.DARK

    @classmethod
    def instance(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_color_map(self, theme_class=None) -> dict[str, str]:
        """
        QSS şablonundaki {PLACEHOLDER} değişkenlerini tema
        token'larıyla eşleştirir.

        Eğer theme_class verilmemişse, mevcut tema kullanılır.

        ⚠  theme_template.qss'e yeni placeholder eklenirse
           bu haritaya da eklenmesi gerekir.
        """
        if theme_class is None:
            theme_class = DarkTheme
        
        return {
            # Zemin katmanları
            "BG_PRIMARY":     theme_class.BG_PRIMARY,
            "BG_SECONDARY":   theme_class.BG_SECONDARY,
            "BG_TERTIARY":    theme_class.BG_TERTIARY,
            "BG_ELEVATED":    theme_class.BG_ELEVATED,
            "BG_DARK":        getattr(theme_class, "BG_DARK", Colors.NAVY_950),
            # Kenarlıklar
            "BORDER_PRIMARY":   theme_class.BORDER_PRIMARY,
            "BORDER_SECONDARY": theme_class.BORDER_SECONDARY,
            "BORDER_STRONG":    theme_class.BORDER_STRONG,
            # Input
            "INPUT_BG":           theme_class.INPUT_BG,
            # Metin
            "TEXT_PRIMARY":   theme_class.TEXT_PRIMARY,
            "TEXT_SECONDARY": theme_class.TEXT_SECONDARY,
            "TEXT_MUTED":     theme_class.TEXT_MUTED,
            "TEXT_DISABLED":  theme_class.TEXT_DISABLED,
            # Vurgu
            "ACCENT":         theme_class.ACCENT,
            "ACCENT2":        theme_class.ACCENT2,
            "ACCENT_BG":      getattr(theme_class, "ACCENT_BG", "rgba(61,142,245,0.12)"),
            # Tablo
            "TEXT_TABLE_HEADER": getattr(theme_class, "TEXT_TABLE_HEADER", theme_class.TEXT_PRIMARY),
        }

    def load_stylesheet(self, theme_class=None) -> str:
        """
        Şablon QSS dosyasını yükler ve renk haritasıyla doldurur.
        Sonuç önbelleğe alınır (tema değiştiğinde sıfırlanır).
        
        Args:
            theme_class: Tema sınıfı (DarkTheme, LightTheme, vs.)
                        None ise DarkTheme kullanılır
        """
        if theme_class is None:
            theme_class = DarkTheme

        try:
            template = self._theme_template_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.warning("Tema şablonu bulunamadı: %s", self._theme_template_path)
            return ""

        stylesheet = template
        for placeholder, color in self._get_color_map(theme_class).items():
            stylesheet = stylesheet.replace(f"{{{placeholder}}}", color)

        return stylesheet

    def _load_saved_theme_name(self) -> str:
        """ayarlar.json'dan kayıtlı tema adını oku. Kayıt yoksa 'dark' döndür."""
        try:
            from core.config import AppConfig
            import json, os
            if os.path.exists(AppConfig.SETTINGS_PATH):
                with open(AppConfig.SETTINGS_PATH, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                saved = str(settings.get("theme", "dark")).lower()
                if saved in ("dark", "light"):
                    return saved
        except Exception as e:
            logger.warning(f"Tema tercihi okunamadı, varsayılan kullanılıyor: {e}")
        return "dark"

    def apply_app_theme(self, app: QApplication) -> None:
        """Başlangıçta ayarlar.json'dan kaydedilmiş temayı uygular."""
        saved_theme = self._load_saved_theme_name()
        logger.debug(f"Başlangıç teması: {saved_theme}")
        app.setStyle("Fusion")
        # set_theme içindeki tüm palette + QSS mantığını tekrar kullanır
        self.set_theme(app, saved_theme)

    def set_theme(self, app: QApplication, theme_name: str) -> bool:
        """
        Runtime'da tema değiştir.
        
        Args:
            app: QApplication örneği
            theme_name: Tema adı ("dark", "light")
            
        Returns:
            Başarılıysa True, hata varsa False
        """
        from ui.styles.theme_registry import ThemeRegistry, ThemeType
        
        try:
            logger.info(f"Tema değişimi başlanıyor: {theme_name}")
            
            # Tema tipini belirle
            if theme_name.lower() == "dark":
                logger.debug("Dark tema seçildi")
                theme_type = ThemeType.DARK
                theme_class = DarkTheme
            elif theme_name.lower() == "light":
                logger.debug("Light tema seçildi, LightTheme import ediliyor...")
                from ui.styles.light_theme import LightTheme
                logger.debug(f"LightTheme sınıfı başarıyla import edildi: {LightTheme}")
                theme_type = ThemeType.LIGHT
                theme_class = LightTheme
            else:
                logger.error(f"Bilinmeyen tema: {theme_name}")
                return False
            
            logger.info(f"Tema sınıfı: {theme_class}")
            
            # Registry'i güncelle
            logger.debug("Registry güncelleniyor...")
            self._registry.set_active_theme(theme_type)
            self._current_theme_type = theme_type
            
            # Palette'i güncelle — tema'ya göre uygun renkler kullan
            logger.debug("QPalette güncelleniyor...")
            p = app.palette()
            p.setColor(QPalette.Window,          QColor(theme_class.BG_PRIMARY))
            p.setColor(QPalette.WindowText,      QColor(theme_class.TEXT_PRIMARY))
            p.setColor(QPalette.Base,            QColor(theme_class.BG_TERTIARY))
            p.setColor(QPalette.AlternateBase,   QColor(theme_class.BG_SECONDARY))
            p.setColor(QPalette.Text,            QColor(theme_class.TEXT_PRIMARY))
            p.setColor(QPalette.Button,          QColor(theme_class.BG_SECONDARY))
            p.setColor(QPalette.ButtonText,      QColor(theme_class.TEXT_PRIMARY))
            p.setColor(QPalette.ToolTipBase,     QColor(theme_class.BG_ELEVATED))
            p.setColor(QPalette.ToolTipText,     QColor(theme_class.TEXT_PRIMARY))
            p.setColor(QPalette.Highlight,       QColor(theme_class.ACCENT))
            
            # HighlightedText: Light tema'da beyaz, Dark tema'da çok koyu
            highlighted_text_color = "#ffffff" if theme_type == ThemeType.LIGHT else Colors.NAVY_950
            p.setColor(QPalette.HighlightedText, QColor(highlighted_text_color))
            
            p.setColor(QPalette.Link,            QColor(theme_class.ACCENT2))
            p.setColor(QPalette.PlaceholderText, QColor(theme_class.TEXT_MUTED))
            p.setColor(QPalette.Mid,             QColor(theme_class.BG_ELEVATED))
            
            # Dark: Light tema'da açık gri, Dark tema'da çok koyu
            dark_color = "#cbd5e1" if theme_type == ThemeType.LIGHT else Colors.NAVY_950
            p.setColor(QPalette.Dark,            QColor(dark_color))
            
            p.setColor(QPalette.Light,           QColor(theme_class.BG_TERTIARY))
            app.setPalette(p)
            logger.debug("QPalette başarıyla ayarlandı")
            
            # Stylesheet'i güncelle
            logger.debug("Stylesheet yükleniyor...")
            stylesheet = self.load_stylesheet(theme_class)
            logger.debug(f"Stylesheet boyutu: {len(stylesheet)} byte")
            app.setStyleSheet(stylesheet)
            logger.debug("Stylesheet uygulandı")
            
            # Tüm widget'ları yenile — tema değişikliğini görünür hale getir
            logger.info("Tüm widget'lar yenileniyor...")
            
            # Adım 1: App'in style'ını yeniden set et
            from PySide6.QtWidgets import QStyle
            current_style = app.style()
            if current_style:
                app.setStyle(current_style.__class__.__name__)
                logger.debug(f"Style yeniden ayarlandı: {current_style.__class__.__name__}")
            
            # Adım 2: Tüm widget'ları recursive olarak güncelle
            def update_widget_recursive(widget: QWidget) -> int:
                """Widget ve tüm child'larını recursive güncelle"""
                count = 0
                try:
                    # Widget'ın kendisi
                    widget.style().unpolish(widget)
                    widget.style().polish(widget)
                    widget.update()
                    widget.repaint()
                    count += 1
                    
                    # Tüm child widget'lar
                    for child in widget.findChildren(QWidget):
                        child.style().unpolish(child)
                        child.style().polish(child)
                        child.update()
                        count += 1
                except Exception as e:
                    logger.debug(f"Widget update hatası: {widget.__class__.__name__}: {e}")
                
                return count
            
            # Tüm top-level widget'lara recursive update uygula
            total_updated = 0
            for widget in app.topLevelWidgets():
                total_updated += update_widget_recursive(widget)
                logger.debug(f"Top-level widget güncellendi: {widget.__class__.__name__} ({update_widget_recursive(widget)} alt widget)")
            
            logger.debug(f"Toplam {total_updated} widget güncellendi")
            
            # Adım 3: QGroupBox'ları ekspilisit olarak güncelle
            logger.debug("QGroupBox'lar güncelleniyor...")
            from PySide6.QtWidgets import QGroupBox
            for groupbox in app.findChildren(QGroupBox):
                groupbox.style().unpolish(groupbox)
                groupbox.style().polish(groupbox)
                groupbox.update()
                groupbox.repaint()
            logger.debug("QGroupBox'lar başarıyla güncellendi")
            
            # Adım 4: Event loop'u çalıştır (CSS refresh)
            for i in range(10):
                app.processEvents()
            
            logger.info("Widget'lar başarıyla yenilendi")
            

            # ── Tema sonrası yenileme ──────────────────────────────────
            # STYLES cache'ini sıfırla
            try:
                from ui.styles.components import refresh_styles
                refresh_styles()
                logger.debug("STYLES cache sıfırlandı")
            except Exception as _e:
                logger.warning(f"refresh_styles hatası: {_e}")

            # refresh_theme() metoduna sahip tüm widget'ları bilgilendir
            _refreshed = 0
            for _w in app.allWidgets():
                if hasattr(_w, 'refresh_theme') and callable(_w.refresh_theme):
                    try:
                        _w.refresh_theme()
                        _refreshed += 1
                    except Exception as _e:
                        logger.debug(f"refresh_theme [{_w.__class__.__name__}]: {_e}")
            logger.info(f"{_refreshed} widget refresh_theme() ile güncellendi")
            # ──────────────────────────────────────────────────────────

            # Signal gönder
            logger.debug(f"theme_changed sinyali gönderiliyor: {theme_name}")
            self.theme_changed.emit(theme_name.lower())

            # Tercihi diske kaydet — bir sonraki açılışta hatırlanır
            try:
                from core.config import AppConfig
                import json as _json, os as _os
                _settings = {}
                if _os.path.exists(AppConfig.SETTINGS_PATH):
                    try:
                        with open(AppConfig.SETTINGS_PATH, "r", encoding="utf-8") as _f:
                            _settings = _json.load(_f)
                    except Exception:
                        _settings = {}
                _settings["theme"] = theme_name.lower()
                with open(AppConfig.SETTINGS_PATH, "w", encoding="utf-8") as _f:
                    _json.dump(_settings, _f, ensure_ascii=False, indent=2)
                logger.debug(f"Tema tercihi kaydedildi: {theme_name}")
            except Exception as _e:
                logger.warning(f"Tema tercihi kaydedilemedi: {_e}")

            logger.info(f"Tema başarıyla değiştirildi: {theme_name.capitalize()}")
            return True
            
        except ImportError as e:
            logger.error(f"Import hatası (tema dosyası bulunamadı): {e}", exc_info=True)
            return False
        except AttributeError as e:
            logger.error(f"Attribute hatası (tema rengi bulunamadı): {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Tema değişikliği hatası: {e}", exc_info=True)
            return False

    # ── Statik yardımcılar (mevcut API korundu) ──────────────────

    @staticmethod
    def get_component_styles(component_name: str) -> str:
        """STYLES dict'ten bileşen stili döndürür."""
        return STYLES.get(component_name, "")

    @staticmethod
    def get_all_component_styles() -> dict:
        return STYLES.copy()

    @staticmethod
    def get_color(color_name: str) -> str:
        """Colors sınıfından renk döndürür."""
        return getattr(Colors, color_name, "#ffffff")

    @staticmethod
    def get_dark_theme_color(color_name: str) -> str:
        """DarkTheme sınıfından token değeri döndürür."""
        return getattr(DarkTheme, color_name, "#ffffff")

    @staticmethod
    def get_status_color(status: str) -> QColor:
        r, g, b, a = ComponentStyles.get_status_color(status)
        return QColor(r, g, b, a)

    @staticmethod
    def get_status_text_color(status: str) -> str:
        return ComponentStyles.get_status_text_color(status)

    @staticmethod
    def set_variant(widget: QWidget, variant: str) -> None:
        """QSS property-based variant uygular (polish/unpolish)."""
        widget.setProperty("variant", variant)
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    @staticmethod
    def setup_calendar_popup(date_edit: QDateEdit) -> None:
        """QDateEdit popup takvimini tema renkleriyle stillendirir."""
        cal = date_edit.calendarWidget()
        cal.setMinimumWidth(300)
        cal.setMinimumHeight(200)
        cal.setStyleSheet(STYLES["calendar"])
        cal.setVerticalHeaderFormat(cal.VerticalHeaderFormat.NoVerticalHeader)

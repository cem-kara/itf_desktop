from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtGui import QColor

from core.logger import logger
from ui.styles import Colors, DarkTheme, ComponentStyles
from ui.styles.components import STYLES


class ThemeManager(QObject):
    """
    Merkezi Tema Yöneticisi
    
    Tüm UI stillerinin yönetildiği tek nokta.
    - Ana stylesheet (theme.qss) yüklemesi
    - Bileşen stilleri (ComponentStyles)
    - Renk paletleri (Colors, DarkTheme)
    """

    _instance: "ThemeManager | None" = None

    def __init__(self) -> None:
        super().__init__()
        self._theme_path = Path(__file__).with_name("theme.qss")
        self._stylesheet_cache: str | None = None

    @classmethod
    def instance(cls) -> "ThemeManager":
        """ThemeManager singleton döner."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load_stylesheet(self) -> str:
        """Ana theme.qss dosyasını yükle ve cache'le."""
        if self._stylesheet_cache is not None:
            return self._stylesheet_cache

        try:
            self._stylesheet_cache = self._theme_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.warning("Tema dosyası bulunamadı: %s", self._theme_path)
            self._stylesheet_cache = ""

        return self._stylesheet_cache

    def apply_app_theme(self, app: QApplication) -> None:
        """Ana uygulamaya theme.qss uygula."""
        app.setStyleSheet(self.load_stylesheet())

    # ══════════════════════════════════════════════════════════════
    # MERKEZİ STİL KAYNAĞINDAN ALMAK İÇİN HELPER METODLARİ
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def get_component_styles(component_name: str) -> str:
        """
        Belirli bir bileşen stilini döner.
        
        Args:
            component_name: "filter_panel", "table", "search", vb.
        
        Returns:
            QSS string
        """
        return STYLES.get(component_name, "")

    @staticmethod
    def get_all_component_styles() -> dict:
        """Tüm bileşen stillerini dict olarak döner."""
        return STYLES.copy()

    @staticmethod
    def get_color(color_name: str) -> str:
        """
        Renk paletinden hex renk döner.
        
        Args:
            color_name: "BLUE_700", "GREEN_600", "RED_500", vb.
        
        Returns:
            Hex color string (ör. "#1d75fe")
        """
        return getattr(Colors, color_name, "#ffffff")

    @staticmethod
    def get_dark_theme_color(color_name: str) -> str:
        """
        Dark tema rengini döner.
        
        Args:
            color_name: "BG_PRIMARY", "TEXT_PRIMARY", "BTN_DANGER_BG", vb.
        
        Returns:
            Hex renk veya rgba string
        """
        return getattr(DarkTheme, color_name, "#ffffff")

    @staticmethod
    def get_status_color(status: str) -> QColor:
        """
        Durum adına göre QColor döner (tablo hücresi vb. için).
        
        Args:
            status: "Aktif", "Pasif", "İzinli", vb.
        
        Returns:
            QColor (RGBA ile transparency)
        """
        r, g, b, a = ComponentStyles.get_status_color(status)
        return QColor(r, g, b, a)

    @staticmethod
    def get_status_text_color(status: str) -> str:
        """
        Durum adına göre metin rengi (hex) döner.
        
        Args:
            status: "Aktif", "Pasif", "İzinli", vb.
        
        Returns:
            Hex renk string
        """
        return ComponentStyles.get_status_text_color(status)

    @staticmethod
    def set_variant(widget: QWidget, variant: str) -> None:
        """Widget'a variant property'si setler ve redraw yapar."""
        widget.setProperty("variant", variant)
        widget.style().unpolish(widget)
        widget.style().polish(widget)


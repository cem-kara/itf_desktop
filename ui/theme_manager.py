# ui/theme_manager.py  ─  REPYS v3 · Medikal Dark-Blue Tema
from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication, QWidget, QDateEdit
from PySide6.QtGui import QColor, QPalette

from core.logger import logger
from ui.styles import Colors, DarkTheme, ComponentStyles
from ui.styles.components import STYLES


class ThemeManager(QObject):
    """Merkezi Tema Yöneticisi — Medikal Dark-Blue (v3)."""

    _instance: "ThemeManager | None" = None

    def __init__(self) -> None:
        super().__init__()
        self._theme_template_path = Path(__file__).with_name("theme_template.qss")
        self._stylesheet_cache: str | None = None

    @classmethod
    def instance(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_color_map(self) -> dict[str, str]:
        """Tema placeholder'larını gerçek renklerle eşleştirir."""
        return {
            "BG_PRIMARY":     DarkTheme.BG_PRIMARY,
            "BG_SECONDARY":   DarkTheme.BG_SECONDARY,
            "BG_TERTIARY":    DarkTheme.BG_TERTIARY,
            "BG_ELEVATED":    DarkTheme.BG_ELEVATED,
            "BG_DARK":        Colors.NAVY_950,
            "BORDER_PRIMARY": DarkTheme.BORDER_PRIMARY,
            "TEXT_PRIMARY":   DarkTheme.TEXT_PRIMARY,
            "TEXT_SECONDARY": DarkTheme.TEXT_SECONDARY,
            "TEXT_MUTED":     DarkTheme.TEXT_MUTED,
            "TEXT_DISABLED":  DarkTheme.TEXT_DISABLED,
            "ACCENT":         DarkTheme.ACCENT,
            "ACCENT2":        DarkTheme.ACCENT2,
        }

    def load_stylesheet(self) -> str:
        """
        Şablon dosyasını yükler ve renklerle dinamik olarak doldurur.
        
        Şablon syntax: {PLACEHOLDER_NAME}
        Örnek: color: {TEXT_PRIMARY};
        """
        if self._stylesheet_cache is not None:
            return self._stylesheet_cache

        try:
            template_content = self._theme_template_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.warning("Tema şablonu bulunamadı: %s", self._theme_template_path)
            self._stylesheet_cache = ""
            return self._stylesheet_cache

        # Renk haritasını al
        color_map = self._get_color_map()

        # Placeholder'ları değiştir
        stylesheet = template_content
        for placeholder, color in color_map.items():
            stylesheet = stylesheet.replace(f"{{{placeholder}}}", color)

        self._stylesheet_cache = stylesheet
        return self._stylesheet_cache

    def apply_app_theme(self, app: QApplication) -> None:
        """Uygulamaya medikal dark-blue tema uygular."""
        app.setStyle("Fusion")

        p = app.palette()
        p.setColor(QPalette.Window,          QColor(DarkTheme.BG_PRIMARY))
        p.setColor(QPalette.WindowText,      QColor(DarkTheme.TEXT_PRIMARY))
        p.setColor(QPalette.Base,            QColor(DarkTheme.BG_TERTIARY))
        p.setColor(QPalette.AlternateBase,   QColor(DarkTheme.BG_SECONDARY))
        p.setColor(QPalette.Text,            QColor(DarkTheme.TEXT_PRIMARY))
        p.setColor(QPalette.Button,          QColor(DarkTheme.BG_SECONDARY))
        p.setColor(QPalette.ButtonText,      QColor(DarkTheme.TEXT_PRIMARY))
        p.setColor(QPalette.ToolTipBase,     QColor(DarkTheme.BG_ELEVATED))
        p.setColor(QPalette.ToolTipText,     QColor(DarkTheme.TEXT_PRIMARY))
        p.setColor(QPalette.Highlight,       QColor(DarkTheme.ACCENT))
        p.setColor(QPalette.HighlightedText, QColor(Colors.NAVY_950))
        p.setColor(QPalette.Link,            QColor(DarkTheme.ACCENT2))
        p.setColor(QPalette.PlaceholderText, QColor(DarkTheme.TEXT_MUTED))
        p.setColor(QPalette.Mid,             QColor(DarkTheme.BG_ELEVATED))
        p.setColor(QPalette.Dark,            QColor(Colors.NAVY_950))
        p.setColor(QPalette.Light,           QColor(DarkTheme.BG_TERTIARY))
        app.setPalette(p)

        app.setStyleSheet(self.load_stylesheet())

    # ── Yardımcı metodlar (mevcut API korundu) ──────────────────
    @staticmethod
    def get_component_styles(component_name: str) -> str:
        return STYLES.get(component_name, "")

    @staticmethod
    def get_all_component_styles() -> dict:
        return STYLES.copy()

    @staticmethod
    def get_color(color_name: str) -> str:
        return getattr(Colors, color_name, "#ffffff")

    @staticmethod
    def get_dark_theme_color(color_name: str) -> str:
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
        widget.setProperty("variant", variant)
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    @staticmethod
    def setup_calendar_popup(date_edit: QDateEdit) -> None:
        cal = date_edit.calendarWidget()
        cal.setMinimumWidth(300)
        cal.setMinimumHeight(200)
        from ui.styles.components import ComponentStyles
        cal.setStyleSheet(ComponentStyles.CALENDAR)
        cal.setVerticalHeaderFormat(cal.VerticalHeaderFormat.NoVerticalHeader)

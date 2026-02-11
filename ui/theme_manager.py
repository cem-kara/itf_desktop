from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication, QWidget

from core.logger import logger


class ThemeManager(QObject):
    """Uygulama temasını tek noktadan yöneten yardımcı sınıf."""

    _instance: "ThemeManager | None" = None

    def __init__(self) -> None:
        super().__init__()
        self._theme_path = Path(__file__).with_name("theme.qss")
        self._stylesheet_cache: str | None = None

    @classmethod
    def instance(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load_stylesheet(self) -> str:
        if self._stylesheet_cache is not None:
            return self._stylesheet_cache

        try:
            self._stylesheet_cache = self._theme_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.warning("Tema dosyası bulunamadı: %s", self._theme_path)
            self._stylesheet_cache = ""

        return self._stylesheet_cache

    def apply_app_theme(self, app: QApplication) -> None:
        app.setStyleSheet(self.load_stylesheet())

    @staticmethod
    def set_variant(widget: QWidget, variant: str) -> None:
        widget.setProperty("variant", variant)
        widget.style().unpolish(widget)
        widget.style().polish(widget)

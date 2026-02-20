# ui/styles/theme_registry.py  ─  REPYS v3 · Tema Yönetim Sistemi
# ═══════════════════════════════════════════════════════════════
#  Runtime tema değiştirme altyapısı.
#  Tema tanımları ve yönetimi merkezi noktada.
# ═══════════════════════════════════════════════════════════════

from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from core.logger import logger

if TYPE_CHECKING:
    from ui.styles import Colors, DarkTheme, LightTheme


class ThemeType(Enum):
    """Desteklenen Tema Tipleri."""
    DARK = "dark"
    LIGHT = "light"


class ThemeDefinition:
    """Tema tanımı ve kaynaklarını tutar."""

    def __init__(
        self,
        name: ThemeType,
        theme_class,  # Colors | DarkTheme | LightTheme
        qss_template_file: str,
        display_name: str = "",
    ) -> None:
        self.name = name
        self.type = name
        self.theme_class = theme_class
        self.qss_template_file = qss_template_file
        self.display_name = display_name or name.value.capitalize()
        self.template_path = Path(__file__).parent.parent / qss_template_file

    def __repr__(self) -> str:
        return f"<ThemeDefinition: {self.display_name}>"


class ThemeRegistry:
    """
    Tema kayıt ve yönetim sistemi.
    
    Kullanım:
        registry = ThemeRegistry.instance()
        theme = registry.get_theme(ThemeType.DARK)
        registry.set_active_theme(ThemeType.LIGHT)
    """

    _instance: "ThemeRegistry | None" = None
    _themes: dict[ThemeType, ThemeDefinition] = {}

    def __init__(self) -> None:
        """Initialize registy ve tema tanımlarını yükle."""
        self._active_theme = ThemeType.DARK
        self._initialize_themes()

    def _initialize_themes(self) -> None:
        """Tema tanımlarını kaydet."""
        # Dark tema
        from ui.styles import DarkTheme

        self._themes[ThemeType.DARK] = ThemeDefinition(
            name=ThemeType.DARK,
            theme_class=DarkTheme,
            qss_template_file="theme_template.qss",
            display_name="Koyu Mavi (Dark Blue)",
        )

        # Light tema
        from ui.styles.light_theme import LightTheme

        self._themes[ThemeType.LIGHT] = ThemeDefinition(
            name=ThemeType.LIGHT,
            theme_class=LightTheme,
            qss_template_file="theme_light_template.qss",
            display_name="Açık Mavi (Light Blue)",
        )

        logger.debug(f"Tema registry başlatıldı. {len(self._themes)} tema yüklendi.")

    @classmethod
    def instance(cls) -> "ThemeRegistry":
        """Singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_theme(self, theme_type: ThemeType) -> ThemeDefinition | None:
        """
        Tema tanımını getir.
        
        Args:
            theme_type: ThemeType.DARK veya ThemeType.LIGHT
            
        Returns:
            ThemeDefinition veya None (bulunamadıysa)
        """
        return self._themes.get(theme_type)

    def get_active_theme(self) -> ThemeDefinition:
        """Aktif temayı getir."""
        return self._themes[self._active_theme]

    def get_active_theme_type(self) -> ThemeType:
        """Aktif tema tipini getir."""
        return self._active_theme

    def set_active_theme(self, theme_type: ThemeType) -> bool:
        """
        Aktif temayı değiştir. (Henüz ThemeManager entegrasyonu yapılmamıştır.)
        
        Args:
            theme_type: Yeni tema tipi
            
        Returns:
            Başarılıysa True, hata varsa False
        """
        if theme_type not in self._themes:
            logger.error(f"Tema bulunamadı: {theme_type}")
            return False

        self._active_theme = theme_type
        logger.info(f"Aktif tema değiştirildi: {self._themes[theme_type].display_name}")
        return True

    def get_all_themes(self) -> list[ThemeDefinition]:
        """Tüm kayıtlı temalar."""
        return list(self._themes.values())

    def get_theme_by_name(self, name: str) -> ThemeDefinition | None:
        """
        Tema adına göre ara.
        
        Args:
            name: Tema adı ("dark", "light", vs)
            
        Returns:
            ThemeDefinition veya None
        """
        try:
            theme_type = ThemeType(name.lower())
            return self.get_theme(theme_type)
        except ValueError:
            logger.warning(f"Tema adı Geçersiz: {name}")
            return None

    def is_theme_available(self, theme_type: ThemeType) -> bool:
        """Tema mevcut mu?"""
        return theme_type in self._themes

    def get_theme_template_content(self, theme_type: ThemeType) -> str:
        """
        Tema QSS şablon içeriğini getir.
        
        Args:
            theme_type: Tema tipi
            
        Returns:
            QSS şablon içeriği
        """
        theme = self.get_theme(theme_type)
        if not theme:
            logger.error(f"Tema bulunamadı: {theme_type}")
            return ""

        try:
            return theme.template_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.error(f"Tema şablonu bulunamadı: {theme.template_path}")
            return ""

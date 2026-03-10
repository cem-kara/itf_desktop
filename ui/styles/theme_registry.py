# ui/styles/theme_registry.py  ─  REPYS v3.1
# ═══════════════════════════════════════════════════════════════
#
#  Geriye dönük uyumluluk için korunuyor.
#  v3.1: İç implementasyon themes.py'e taşındı.
#
#  Import'lar değişmedi:
#     from ui.styles.theme_registry import ThemeRegistry, ThemeType
#
# ═══════════════════════════════════════════════════════════════

from enum import Enum
from core.logger import logger
from core.settings import get as _settings_get, set as _settings_set


class ThemeType(Enum):
    """Desteklenen tema tipleri."""
    DARK  = "dark"
    LIGHT = "light"


class ThemeDefinition:
    """Tema meta bilgisi — geriye dönük uyumluluk."""

    def __init__(self, name: ThemeType, theme_class, display_name: str = ""):
        self.name         = name
        self.type         = name
        self.theme_class  = theme_class
        self.display_name = display_name or name.value.capitalize()

    def __repr__(self):
        return f"<ThemeDefinition: {self.display_name}>"


class ThemeRegistry:
    """
    Tema kayıt sistemi — singleton.

    v3.1: Aktif tema bilgisi artık core/settings üzerinden
    ayarlar.json'dan okunuyor. ThemeRegistry sadece ince bir
    sarmalayıcı olarak kalıyor.
    """

    _instance: "ThemeRegistry | None" = None

    def __init__(self):
        self._themes: dict[ThemeType, ThemeDefinition] = {}
        self._initialize_themes()

    def _initialize_themes(self):
        from ui.styles.colors import DarkTheme
        from ui.styles.light_theme import LightTheme

        self._themes[ThemeType.DARK] = ThemeDefinition(
            ThemeType.DARK, DarkTheme, "Koyu Mavi (Dark Blue)"
        )
        self._themes[ThemeType.LIGHT] = ThemeDefinition(
            ThemeType.LIGHT, LightTheme, "Açık Mavi (Light Blue)"
        )
        logger.debug(f"ThemeRegistry başlatıldı: {len(self._themes)} tema")

    @classmethod
    def instance(cls) -> "ThemeRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Aktif tema ────────────────────────────────────────────
    def get_active_theme(self) -> ThemeDefinition:
        name = _settings_get("theme", "dark")
        try:
            theme_type = ThemeType(name)
        except ValueError:
            theme_type = ThemeType.DARK
        return self._themes[theme_type]

    def get_active_theme_type(self) -> ThemeType:
        name = _settings_get("theme", "dark")
        try:
            return ThemeType(name)
        except ValueError:
            return ThemeType.DARK

    def set_active_theme(self, theme_type: ThemeType) -> bool:
        if theme_type not in self._themes:
            logger.error(f"Tema bulunamadı: {theme_type}")
            return False
        _settings_set("theme", theme_type.value)
        logger.info(f"Aktif tema: {self._themes[theme_type].display_name}")
        return True

    # ── Sorgular ─────────────────────────────────────────────
    def get_theme(self, theme_type: ThemeType) -> ThemeDefinition | None:
        return self._themes.get(theme_type)

    def get_theme_by_name(self, name: str) -> ThemeDefinition | None:
        try:
            return self.get_theme(ThemeType(name.lower()))
        except ValueError:
            return None

    def get_all_themes(self) -> list[ThemeDefinition]:
        return list(self._themes.values())

    def is_theme_available(self, theme_type: ThemeType) -> bool:
        return theme_type in self._themes

    # ── QSS şablonu ──────────────────────────────────────────
    def get_theme_template_content(self, theme_type: ThemeType) -> str:
        """QSS şablon içeriğini döndür (geriye dönük uyumluluk)."""
        from pathlib import Path
        from ui.styles.icons import Icons
        from ui.styles.themes import get_tokens
        try:
            qss_path = Path(__file__).parent.parent / "theme_template.qss"
            template = qss_path.read_text(encoding="utf-8")
            tokens = get_tokens(theme_type.value)
            tokens["ICON_CHEVRON_UP"] = Icons.qss_url("chevron_up", tokens["TEXT_SECONDARY"], 12)
            tokens["ICON_CHEVRON_DOWN"] = Icons.qss_url("chevron_down", tokens["TEXT_SECONDARY"], 12)
            for k, v in tokens.items():
                template = template.replace(f"{{{k}}}", v)
            return template
        except Exception as e:
            logger.error(f"QSS şablon hatası: {e}")
            return ""

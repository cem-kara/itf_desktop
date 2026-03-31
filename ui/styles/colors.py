# ui/styles/colors.py  ─  REPYS v3 · Tema Renk Sistemi
# ═══════════════════════════════════════════════════════════════
#
#  Dışarıdan import arayüzü (değişmedi):
#     from ui.styles.colors import DarkTheme as C
#     from ui.styles.colors import DarkTheme, ThemeProxy, Colors
#
#  Nasıl çalışır (v3.1):
#     "page"  →  _LiveThemeMeta devreye girer
#                            →  ayarlar.json'dan aktif temayı okur
#                            →  ui/styles/themes.py'den rengi döndürür
#
#  Artık ThemeRegistry bağımlılığı yok — döngüsel import riski ortadan kalktı.
# ═══════════════════════════════════════════════════════════════


class Colors:
    """
    Ham renk paleti — uygulama genelinde yeniden kullanılabilir
    referans değerleri. DarkTheme ve LightTheme bu değerlerden türetilir.
    """

    WHITE = "#ffffff"
    BLACK = "#000000"

    # ── Mavi / Lacivert skalası ──────────────────────────────────
    NAVY_950 = "#060d1a"
    NAVY_900 = "#0b1628"
    NAVY_850 = "#0e1e35"
    NAVY_800 = "#112240"
    NAVY_750 = "#152b4f"
    NAVY_700 = "#1a3560"
    NAVY_600 = "#1e4080"
    NAVY_500 = "#1e5fa0"
    NAVY_400 = "#2478c8"
    NAVY_300 = "#4a9be0"
    NAVY_200 = "#7ab8f0"
    NAVY_100 = "#b8d8f8"
    NAVY_50  = "#e8f2fc"

    # ── Vurgu — Elektrik Mavi ───────────────────────────────────
    CYAN_500 = "#00b4d8"
    CYAN_400 = "#22d3ee"
    CYAN_300 = "#67e8f9"
    CYAN_BG  = "rgba(0,180,216,0.10)"

    # ── Gri (nötr) ───────────────────────────────────────────────
    GRAY_900 = "#111827"
    GRAY_800 = "#1f2937"
    GRAY_700 = "#374151"
    GRAY_600 = "#4b5563"
    GRAY_400 = "#9ca3af"
    GRAY_300 = "#d1d5db"
    GRAY_100 = "#f3f4f6"

    # ── Durum renkleri ───────────────────────────────────────────
    GREEN_600  = "#059669"
    GREEN_500  = "#10b981"
    GREEN_400  = "#34d399"
    GREEN_BG   = "rgba(16,185,129,0.10)"

    RED_600    = "#dc2626"
    RED_500    = "#ef4444"
    RED_400    = "#f87171"
    RED_BG     = "rgba(239,68,68,0.10)"

    YELLOW_500 = "#f59e0b"
    YELLOW_400 = "#fbbf24"
    YELLOW_BG  = "rgba(245,158,11,0.10)"

    ORANGE_500 = "#f97316"
    ORANGE_400 = "#fb923c"

    PURPLE_500 = "#a855f7"
    PURPLE_400 = "#c084fc"
    PURPLE_BG  = "rgba(168,85,247,0.10)"

    # ── Menü renkleri ────────────────────────────────────────────
    MENU_ACTIVE = "#00b4d8"
    MENU_ITEM   = "#8aa8c8"


# ══════════════════════════════════════════════════════════════
#  _LiveThemeMeta — DarkTheme.ATTR erişimini aktif temaya yönlendirir
#
#  v3.1 değişikliği: ThemeRegistry yerine core/settings + themes.py
#  kullanır. Döngüsel import riski ortadan kalktı.
# ══════════════════════════════════════════════════════════════
class _LiveThemeMeta(type):
    def __getattribute__(cls, name: str):
        # Dunder / private isimler → normal sınıf davranışı
        if name.startswith("_"):
            return type.__getattribute__(cls, name)
        try:
            from core.settings import get as _settings_get
            from ui.styles.themes import get_tokens
            theme_value = _settings_get("theme", "dark")
            theme_name = theme_value if isinstance(theme_value, str) and theme_value else "dark"
            tokens = get_tokens(theme_name)
            if name in tokens:
                return tokens[name]

            # Geriye donuk token adlari
            legacy_alias = {
                "PANEL": "BG_ELEVATED",
                "SURFACE": "BG_SECONDARY",
                "SUCCESS": "STATUS_SUCCESS",
                "WARNING": "STATUS_WARNING",
                "DANGER": "STATUS_ERROR",
                "ERROR": "STATUS_ERROR",
                "INFO": "STATUS_INFO",
            }
            if name in legacy_alias and legacy_alias[name] in tokens:
                return tokens[legacy_alias[name]]
        except Exception:
            pass
        # Fallback: sınıf üzerindeki gerçek değer (varsa)
        return type.__getattribute__(cls, name)


def _safe_theme_name() -> str:
    from core.settings import get as _settings_get
    value = _settings_get("theme", "dark")
    return value if isinstance(value, str) and value else "dark"


class DarkTheme(metaclass=_LiveThemeMeta):
    """
    Tema token'larına dinamik erişim sağlar.
    Aktif tema dark ise DARK dict, light ise LIGHT dict döner.

    Tüm attribute erişimleri _LiveThemeMeta üzerinden geçer —
    bu sınıfın kendi body'sini değiştirmeye gerek yok.

    Geriye dönük uyumluluk için STATE_* tuple'ları burada:
    """
    # Badge RGBA tuple'ları — QSS'te kullanılamaz, Python kodu için
    STATE_ACTIVE  = (16,  185, 129, 35)
    STATE_PASSIVE = (239, 68,  68,  35)
    STATE_LEAVE   = (245, 158, 11,  35)


# ══════════════════════════════════════════════════════════════
#  ThemeProxy — DarkTheme ile aynı, geriye dönük uyumluluk için
# ══════════════════════════════════════════════════════════════
class _ThemeProxyMeta(type):
    def __getattr__(cls, name: str):
        return getattr(DarkTheme, name)


class ThemeProxy(metaclass=_ThemeProxyMeta):
    """
    DarkTheme için alias. Eski kod bozulmasın diye korunuyor.
    Yeni kodda DarkTheme kullanın.
    """


def get_current_theme():
    """
    Geriye dönük uyumluluk.
    Aktif temanın token dict'ini nesne olarak döndürür.
    """
    from ui.styles.themes import get_tokens
    tokens = get_tokens(_safe_theme_name())
    return type("_ActiveTheme", (), tokens)()


def get_current_theme_name() -> str:
    """Aktif tema adını döndür: 'dark' veya 'light'."""
    return _safe_theme_name()


# ══════════════════════════════════════════════════════════════
#  _C dict — eski bakim_form.py vb. için geriye dönük uyumluluk
#  Yeni kodda kullanmayın, STYLES veya setProperty tercih edin.
# ══════════════════════════════════════════════════════════════
class _CDictProxy(dict):
    """_C['muted'] gibi eski erişimleri aktif temaya yönlendirir."""
    _KEY_MAP = {
        "red":     "STATUS_ERROR",
        "amber":   "STATUS_WARNING",
        "green":   "STATUS_SUCCESS",
        "accent":  "ACCENT",
        "muted":   "TEXT_MUTED",
        "surface": "BG_SECONDARY",
        "panel":   "BG_ELEVATED",
        "border":  "BORDER_PRIMARY",
        "text":    "TEXT_PRIMARY",
    }

    def __getitem__(self, key):
        key_text = str(key)
        token = self._KEY_MAP.get(key_text, key_text.upper())
        return getattr(DarkTheme, token, super().__getitem__(key))

    def get(self, key, default=None):
        try:
            return self[key]
        except (KeyError, AttributeError):
            return default


C = _CDictProxy({
    "red":     "#e85555",
    "amber":   "#e8a030",
    "green":   "#2ec98e",
    "accent":  "#3d8ef5",
    "muted":   "#4d6070",
    "surface": "#121820",
    "panel":   "#1a2030",
    "border":  "#1e2d3d",
    "text":    "#e8edf5",
})

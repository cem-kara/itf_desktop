# ui/styles/__init__.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
#  Merkezi Stil Yönetimi  ─  REPYS v3
#
#  Hızlı kullanım:
#
#    from ui.styles import DarkTheme
#    from ui.styles.components import STYLES as S
#
#    widget.setStyleSheet(S["btn_action"])
#    color = DarkTheme.STATUS_SUCCESS
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ui/styles/__init__.py
from ui.styles.colors import Colors, DarkTheme, ThemeProxy, get_current_theme
from ui.styles.light_theme import LightTheme
from ui.styles.theme_registry import ThemeRegistry, ThemeType, ThemeDefinition
from ui.styles.components import STYLES, refresh_styles

# Geriye dönük uyumluluk — ComponentStyles'ı import edenler için
from ui.styles.components import ComponentStyles

__all__ = [
    "Colors", "DarkTheme", "LightTheme",
    "ThemeProxy", "get_current_theme",
    "STYLES", "ComponentStyles", "refresh_styles",
    "ThemeRegistry", "ThemeType", "ThemeDefinition",
]

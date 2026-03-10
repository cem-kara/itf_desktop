# ui/styles/__init__.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
#  Merkezi Stil Yönetimi  ─  REPYS v3.4
#
#  KULLANIM:
#    widget.setProperty("style-role", "action")   # buton
#    widget.setProperty("color-role", "muted")    # renk tonu
#    widget.setProperty("bg-role", "panel")       # arka plan
#
#  YASAK:
#    ❌  from ui.styles.components import STYLES as S
#    ❌  widget.setStyleSheet(S["..."])
#    ❌  widget.setStyleSheet(f"QWidget{{ ... }}")
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from ui.styles.colors import Colors, DarkTheme, ThemeProxy, get_current_theme
from ui.styles.light_theme import LightTheme
from ui.styles.theme_registry import ThemeRegistry, ThemeType, ThemeDefinition

__all__ = [
    "Colors", "DarkTheme", "LightTheme",
    "ThemeProxy", "get_current_theme",
    "ThemeRegistry", "ThemeType", "ThemeDefinition",
]

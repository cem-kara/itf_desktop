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

from ui.styles.colors import Colors, DarkTheme
from ui.styles.components import ComponentStyles
from ui.styles.light_theme import LightTheme
from ui.styles.theme_registry import ThemeRegistry, ThemeType, ThemeDefinition

__all__ = [
    "Colors",
    "DarkTheme",
    "LightTheme",
    "ComponentStyles",
    "ThemeRegistry",
    "ThemeType",
    "ThemeDefinition",
]

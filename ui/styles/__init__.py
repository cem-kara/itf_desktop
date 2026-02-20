# ui/styles/__init__.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Merkezi Stil Yönetimi (Theme Management)
#
# Tüm UI stillerinin merkezi yönetimi —
# Burada tanımlanan renkler ve stilleri tüm sayfalar ve bileşenler kullanır.
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


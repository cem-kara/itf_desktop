# ui/styles/components.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
#  ⛔  BU DOSYA KULLANIM DIŞIDIR — v3.4 (Mart 2026)
#
#  Önceki kullanım:  widget.setStyleSheet(S["btn_action"])
#  Yeni kullanım:    widget.setProperty("style-role", "action")
#
#  Tüm stiller ui/theme_template.qss içindedir.
#  Python koduna asla renk veya QSS string'i yazılmaz.
#
#  Bkz: copilot-instructions.md → "TEMA SİSTEMİ — KESİN KURALLAR"
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import warnings as _w

class _Forbidden(dict):
    """Bu sınıfa erişim hata verir — geliştirici yanlış yöntemi kullanıyor."""
    def __getitem__(self, key):
        _w.warn(
            f"YASAK: STYLES['{key}'] kullanıldı. "
            "widget.setProperty(\"style-role\", \"ROL\") kullanın. "
            "Bkz: copilot-instructions.md",
            DeprecationWarning, stacklevel=2
        )
        return ""
    def get(self, key, default=""):
        _w.warn(
            f"YASAK: STYLES.get('{key}') kullanıldı. "
            "widget.setProperty(\"style-role\", \"ROL\") kullanın. "
            "Bkz: copilot-instructions.md",
            DeprecationWarning, stacklevel=2
        )
        return default

STYLES = _Forbidden()

def refresh_styles():
    """Artık gerekmiyor — stil ThemeManager tarafından yönetilir."""

class ComponentStyles:
    """Artık gerekmiyor — setProperty() kullanın."""

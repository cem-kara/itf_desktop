# ui/styles/themes.py  ─  REPYS v3 · Tema Renk Sözlüğü
# ═══════════════════════════════════════════════════════════════
#
#  Tüm tema renkleri burada, sade Python dict olarak.
#  Sınıf yok, metaclass yok, registry yok.
#
#  Diğer modüller buradan okur:
#     from ui.styles.themes import get_tokens
#     tokens = get_tokens("dark")   → dict
#     tokens["BG_PRIMARY"]          → "#0d1117"
#
#  Yeni tema eklemek:
#     1. THEMES dict'ine yeni key ekle
#     2. get_tokens() otomatik bulur
#
# ═══════════════════════════════════════════════════════════════

# ── Koyu Tema ──────────────────────────────────────────────────
DARK: dict[str, str] = {
    # Zemin katmanları
    "BG_PRIMARY":    "#0d1117",
    "BG_SECONDARY":  "#121820",
    "BG_TERTIARY":   "#0d1117",
    "BG_ELEVATED":   "#1a2030",
    "BG_DARK":       "#060d1a",
    "BG_HOVER":      "rgba(61,142,245,0.06)",
    "BG_SELECTED":   "rgba(61,142,245,0.14)",

    # Kenarlıklar
    "BORDER_PRIMARY":   "#1e2d3d",
    "BORDER_SECONDARY": "#253545",
    "BORDER_STRONG":    "#253545",
    "BORDER_FOCUS":     "#3d8ef5",

    # Metin
    "TEXT_PRIMARY":       "#e8edf5",
    "TEXT_SECONDARY":     "#8fa3b8",
    "TEXT_MUTED":         "#4d6070",
    "TEXT_DISABLED":      "#263850",
    "TEXT_TABLE_HEADER":  "#c7dcf1",

    # Input
    "INPUT_BG":            "#1a2030",
    "INPUT_BORDER":        "#1e2d3d",
    "INPUT_BORDER_FOCUS":  "#3d8ef5",

    # Vurgu
    "ACCENT":    "#3d8ef5",
    "ACCENT2":   "#20c0d8",
    "ACCENT_BG": "rgba(61,142,245,0.12)",

    # Butonlar
    "BTN_PRIMARY_BG":       "#3d8ef5",
    "BTN_PRIMARY_TEXT":     "#060d1a",
    "BTN_PRIMARY_HOVER":    "#20c0d8",
    "BTN_PRIMARY_BORDER":   "#3d8ef5",
    "BTN_SECONDARY_BG":     "#1a2030",
    "BTN_SECONDARY_TEXT":   "#8fa3b8",
    "BTN_SECONDARY_BORDER": "#1e2d3d",
    "BTN_SECONDARY_HOVER":  "#253545",
    "BTN_DANGER_BG":        "rgba(232,85,85,0.15)",
    "BTN_DANGER_TEXT":      "#e85555",
    "BTN_DANGER_BORDER":    "rgba(232,85,85,0.30)",
    "BTN_DANGER_HOVER":     "rgba(232,85,85,0.25)",
    "BTN_SUCCESS_BG":       "rgba(46,201,142,0.15)",
    "BTN_SUCCESS_TEXT":     "#2ec98e",
    "BTN_SUCCESS_BORDER":   "rgba(46,201,142,0.30)",
    "BTN_SUCCESS_HOVER":    "rgba(46,201,142,0.25)",

    # Durum
    "STATUS_SUCCESS": "#2ec98e",
    "STATUS_WARNING": "#e8a030",
    "STATUS_ERROR":   "#e85555",
    "STATUS_INFO":    "#3d8ef5",

    # Diğer
    "MONOSPACE": "\"JetBrains Mono\", \"Consolas\", monospace",
    "RKE_PURP":  "#a855f7",

    # QSS şablon için placeholder değerleri
    "PLACEHOLDER": "#4d6070",
}

# ── Açık Tema ──────────────────────────────────────────────────
LIGHT: dict[str, str] = {
    # Zemin katmanları
    "BG_PRIMARY":    "#f0f4f8",
    "BG_SECONDARY":  "#ffffff",
    "BG_TERTIARY":   "#e8f0fe",
    "BG_ELEVATED":   "#f8fafc",
    "BG_DARK":       "#1e293b",
    "BG_HOVER":      "#e8f0fe",
    "BG_SELECTED":   "rgba(37,99,235,0.10)",

    # Kenarlıklar
    "BORDER_PRIMARY":   "#d1dce8",
    "BORDER_SECONDARY": "#b8c8d9",
    "BORDER_STRONG":    "#b8c8d9",
    "BORDER_FOCUS":     "#2563eb",

    # Metin
    "TEXT_PRIMARY":       "#0f172a",
    "TEXT_SECONDARY":     "#475569",
    "TEXT_MUTED":         "#94a3b8",
    "TEXT_DISABLED":      "#cbd5e1",
    "TEXT_TABLE_HEADER":  "#1e293b",

    # Input
    "INPUT_BG":            "#ffffff",
    "INPUT_BORDER":        "#d1dce8",
    "INPUT_BORDER_FOCUS":  "#2563eb",

    # Vurgu
    "ACCENT":    "#2563eb",
    "ACCENT2":   "#0891b2",
    "ACCENT_BG": "rgba(37,99,235,0.08)",

    # Butonlar
    "BTN_PRIMARY_BG":       "#2563eb",
    "BTN_PRIMARY_TEXT":     "#ffffff",
    "BTN_PRIMARY_HOVER":    "#0891b2",
    "BTN_PRIMARY_BORDER":   "#2563eb",
    "BTN_SECONDARY_BG":     "transparent",
    "BTN_SECONDARY_TEXT":   "#475569",
    "BTN_SECONDARY_BORDER": "#d1dce8",
    "BTN_SECONDARY_HOVER":  "#e8f0fe",
    "BTN_DANGER_BG":        "rgba(220,38,38,0.10)",
    "BTN_DANGER_TEXT":      "#dc2626",
    "BTN_DANGER_BORDER":    "rgba(220,38,38,0.25)",
    "BTN_DANGER_HOVER":     "rgba(220,38,38,0.18)",
    "BTN_SUCCESS_BG":       "rgba(22,163,74,0.10)",
    "BTN_SUCCESS_TEXT":     "#16a34a",
    "BTN_SUCCESS_BORDER":   "rgba(22,163,74,0.25)",
    "BTN_SUCCESS_HOVER":    "rgba(22,163,74,0.18)",

    # Durum
    "STATUS_SUCCESS": "#16a34a",
    "STATUS_WARNING": "#d97706",
    "STATUS_ERROR":   "#dc2626",
    "STATUS_INFO":    "#2563eb",

    # Diğer
    "MONOSPACE": "\"JetBrains Mono\", \"Consolas\", monospace",
    "RKE_PURP":  "#7c3aed",

    # QSS şablon için placeholder değerleri
    "PLACEHOLDER": "#94a3b8",
}

# ── Ana sözlük ─────────────────────────────────────────────────
THEMES: dict[str, dict] = {
    "dark":  DARK,
    "light": LIGHT,
}


def get_tokens(name: str) -> dict[str, str]:
    """
    Tema adına göre token dict'ini döndür.
    Bilinmeyen tema adında DARK döner (güvenli fallback).

    Örnek:
        tokens = get_tokens("light")
        tokens["ACCENT"]   → "#2563eb"
    """
    return THEMES.get(name.lower(), DARK)


def available_themes() -> list[str]:
    """Tanımlı tema adlarını döndür."""
    return list(THEMES.keys())

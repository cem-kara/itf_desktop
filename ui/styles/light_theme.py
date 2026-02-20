# ui/styles/light_theme.py  ─  REPYS v3 · Medikal Light Tema
# ═══════════════════════════════════════════════════════════════
#  Açık mavi palette (medical-grade).
#  DarkTheme ile aynı attribute yapısı — runtime tema değiştirme için.
# ═══════════════════════════════════════════════════════════════


class LightTheme:
    """
    Medikal açık mavi light tema.
    DarkTheme ile aynı attribute isimleri — tema değiştirmede uyumlu.
    """
    # ── Zemin Katmanları ─────────────────────────────────────────
    BG_PRIMARY   = "#f8fafc"    # Ana zemin — çok açık gri-mavi
    BG_SECONDARY = "#f1f5f9"    # Panel / kart
    BG_TERTIARY  = "#e2e8f0"    # İçe gömülü alan, zebra satır
    BG_ELEVATED  = "#cbd5e1"    # Yükseltilmiş panel, popup
    BG_HOVER     = "rgba(15,23,42,0.04)"
    BG_SELECTED  = "rgba(15,23,42,0.08)"

    # ── Kenarlıklar ──────────────────────────────────────────────
    BORDER_PRIMARY   = "rgba(15,23,42,0.12)"
    BORDER_SECONDARY = "rgba(15,23,42,0.06)"
    BORDER_FOCUS     = "#0284c7"
    BORDER_STRONG    = "rgba(15,23,42,0.20)"

    # ── Metin ────────────────────────────────────────────────────
    TEXT_PRIMARY   = "#0f172a"   # Çok koyu — siyaha yakın
    TEXT_SECONDARY = "#475569"   # Gri
    TEXT_MUTED     = "#94a3b8"   # Açık gri
    TEXT_DISABLED  = "#cbd5e1"   # Devre dışı

    # ── Input ────────────────────────────────────────────────────
    INPUT_BG           = "#ffffff"
    INPUT_BORDER       = "rgba(15,23,42,0.10)"
    INPUT_BORDER_FOCUS = "#0284c7"

    # ── Vurgu (Mavi/Cyan) ────────────────────────────────────────
    ACCENT    = "#0284c7"        # Sky Blue
    ACCENT2   = "#0ea5e9"        # Lighter Sky Blue
    ACCENT_BG = "rgba(2,132,199,0.08)"

    # ── Butonlar ─────────────────────────────────────────────────
    BTN_PRIMARY_BG     = "#0284c7"
    BTN_PRIMARY_TEXT   = "#ffffff"
    BTN_PRIMARY_HOVER  = "#0ea5e9"

    # ── Durum Renkleri ───────────────────────────────────────────
    SUCCESS_BG   = "rgba(34,197,94,0.08)"
    WARNING_BG   = "rgba(245,158,11,0.08)"
    ERROR_BG     = "rgba(239,68,68,0.08)"
    INFO_BG      = "rgba(168,85,247,0.08)"

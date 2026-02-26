# ui/styles/light_theme.py  ─  REPYS v3 · Medikal Light Tema
# ═══════════════════════════════════════════════════════════════
#
#  DarkTheme ile birebir aynı attribute isimleri —
#  runtime tema değişimi için zorunludur.
#
#  ⚠  Yeni attribute eklendiğinde DarkTheme'de de aynı isimle
#     tanımlanmalıdır (ve tersi).
# ═══════════════════════════════════════════════════════════════


class LightTheme:
    """
    Medikal açık mavi light tema.

    DarkTheme ile birebir aynı attribute sözleşmesi —
    theme_registry üzerinden runtime'da değiştirilebilir.
    """

    # ── Yazı tipi ────────────────────────────────────────────────
    MONOSPACE = "JetBrains Mono"

    # ── Zemin katmanları ─────────────────────────────────────────
    BG_PRIMARY   = "#f8fafc"
    BG_SECONDARY = "#f1f5f9"
    BG_TERTIARY  = "#e2e8f0"
    BG_ELEVATED  = "#cbd5e1"
    BG_HOVER     = "rgba(15,23,42,0.04)"
    BG_SELECTED  = "rgba(15,23,42,0.08)"

    # ── Kenarlıklar ──────────────────────────────────────────────
    BORDER_PRIMARY   = "rgba(15,23,42,0.12)"
    BORDER_SECONDARY = "rgba(15,23,42,0.06)"
    BORDER_STRONG    = "rgba(15,23,42,0.20)"
    BORDER_FOCUS     = "#0284c7"

    # ── Metin ────────────────────────────────────────────────────
    TEXT_PRIMARY   = "#0f172a"
    TEXT_SECONDARY = "#475569"
    TEXT_MUTED     = "#94a3b8"
    TEXT_DISABLED  = "#cbd5e1"

    # ── Input alanları ───────────────────────────────────────────
    INPUT_BG           = "#ffffff"
    INPUT_BORDER       = "rgba(15,23,42,0.10)"
    INPUT_BORDER_FOCUS = "#0284c7"

    # ── Vurgu (Accent) ───────────────────────────────────────────
    ACCENT    = "#0284c7"
    ACCENT2   = "#0ea5e9"
    ACCENT_BG = "rgba(2,132,199,0.08)"

    # ── Butonlar ─────────────────────────────────────────────────
    BTN_PRIMARY_BG     = "#0284c7"
    BTN_PRIMARY_TEXT   = "#ffffff"
    BTN_PRIMARY_HOVER  = "#0ea5e9"
    BTN_PRIMARY_BORDER = "#0284c7"

    BTN_SECONDARY_BG     = "#f1f5f9"
    BTN_SECONDARY_TEXT   = "#475569"
    BTN_SECONDARY_BORDER = "rgba(15,23,42,0.15)"
    BTN_SECONDARY_HOVER  = "#e2e8f0"

    BTN_DANGER_BG     = "rgba(239,68,68,0.08)"
    BTN_DANGER_TEXT   = "#dc2626"
    BTN_DANGER_BORDER = "rgba(239,68,68,0.25)"
    BTN_DANGER_HOVER  = "rgba(239,68,68,0.15)"

    BTN_SUCCESS_BG     = "rgba(16,185,129,0.08)"
    BTN_SUCCESS_TEXT   = "#059669"
    BTN_SUCCESS_BORDER = "rgba(16,185,129,0.25)"
    BTN_SUCCESS_HOVER  = "rgba(16,185,129,0.15)"

    # ── Durum token'ları ─────────────────────────────────────────
    STATUS_SUCCESS = "#059669"
    STATUS_WARNING = "#d97706"
    STATUS_ERROR   = "#dc2626"
    STATUS_INFO    = "#0284c7"

    # ── Badge RGBA (r, g, b, alpha) ──────────────────────────────
    STATE_ACTIVE  = (5,   150, 105, 30)
    STATE_PASSIVE = (220, 38,  38,  30)
    STATE_LEAVE   = (217, 119, 6,   30)

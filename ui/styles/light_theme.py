# ui/styles/light_theme.py  ─  REPYS v3 · Medikal Light Tema
# ═══════════════════════════════════════════════════════════════
#
#  DarkTheme ile birebir aynı attribute isimleri —
#  runtime tema değişimi için zorunludur.
#
#  Renkler HTML Tema Editörü LIGHT_PRESET ile birebir eşleşir.
#
#  ⚠  Yeni attribute eklendiğinde DarkTheme'de de aynı isimle
#     tanımlanmalıdır (ve tersi).
# ═══════════════════════════════════════════════════════════════


class LightTheme:
    """
    Medikal açık mavi light tema.
    DarkTheme ile birebir aynı attribute sözleşmesi.
    """

    # ── Yazı tipi ────────────────────────────────────────────────
    MONOSPACE = "JetBrains Mono"

    # ── Zemin katmanları ─────────────────────────────────────────
    BG_PRIMARY   = "#f0f4f8"   # Ana pencere zemini
    BG_SECONDARY = "#ffffff"   # Panel / kart zemini
    BG_TERTIARY  = "#e8f0fe"   # Hover efekti zemini
    BG_ELEVATED  = "#f8fafc"   # Input / popup zemini
    BG_HOVER     = "#e8f0fe"
    BG_SELECTED  = "rgba(37,99,235,0.10)"

    # ── Kenarlıklar ──────────────────────────────────────────────
    BORDER_PRIMARY   = "#d1dce8"
    BORDER_SECONDARY = "#b8c8d9"
    BORDER_STRONG    = "#b8c8d9"
    BORDER_FOCUS     = "#2563eb"

    # ── Metin ────────────────────────────────────────────────────
    TEXT_PRIMARY      = "#0f172a"
    TEXT_SECONDARY    = "#475569"
    TEXT_MUTED        = "#94a3b8"
    TEXT_DISABLED     = "#cbd5e1"
    TEXT_TABLE_HEADER = "#1e293b"

    # ── Input alanları ───────────────────────────────────────────
    INPUT_BG           = "#ffffff"
    INPUT_BORDER       = "#d1dce8"
    INPUT_BORDER_FOCUS = "#2563eb"

    # ── Vurgu (Accent) ───────────────────────────────────────────
    ACCENT    = "#2563eb"
    ACCENT2   = "#0891b2"
    ACCENT_BG = "rgba(37,99,235,0.08)"

    # ── Butonlar ─────────────────────────────────────────────────
    BTN_PRIMARY_BG     = "#2563eb"
    BTN_PRIMARY_TEXT   = "#ffffff"
    BTN_PRIMARY_HOVER  = "#0891b2"
    BTN_PRIMARY_BORDER = "#2563eb"

    BTN_SECONDARY_BG     = "transparent"
    BTN_SECONDARY_TEXT   = "#475569"
    BTN_SECONDARY_BORDER = "#b8c8d9"
    BTN_SECONDARY_HOVER  = "#f8fafc"

    BTN_DANGER_BG     = "rgba(220,38,38,0.08)"
    BTN_DANGER_TEXT   = "#dc2626"
    BTN_DANGER_BORDER = "rgba(220,38,38,0.30)"
    BTN_DANGER_HOVER  = "rgba(220,38,38,0.15)"

    BTN_SUCCESS_BG     = "rgba(5,150,105,0.08)"
    BTN_SUCCESS_TEXT   = "#059669"
    BTN_SUCCESS_BORDER = "rgba(5,150,105,0.30)"
    BTN_SUCCESS_HOVER  = "rgba(5,150,105,0.15)"

    # ── Durum token'ları ─────────────────────────────────────────
    STATUS_SUCCESS = "#059669"
    STATUS_WARNING = "#d97706"
    STATUS_ERROR   = "#dc2626"
    STATUS_INFO    = "#2563eb"

    # ── Badge RGBA (r, g, b, alpha) ──────────────────────────────
    STATE_ACTIVE  = (5,   150, 105, 30)
    STATE_PASSIVE = (220, 38,  38,  30)
    STATE_LEAVE   = (217, 119, 6,   30)

    RKE_PURP = "#7c3aed"

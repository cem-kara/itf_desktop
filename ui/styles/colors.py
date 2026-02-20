# ui/styles/colors.py  ─  REPYS v3 · Medikal Dark-Blue Tema
# ═══════════════════════════════════════════════════════════════
#  Koyu mavi (medical-grade) palette.
#  DarkTheme attribute isimleri KORUNDU — başka dosyada değişiklik yok.
# ═══════════════════════════════════════════════════════════════

class Colors:
    WHITE   = "#ffffff"
    BLACK   = "#000000"

    # Mavi/Lacivert Skalası
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

    # Vurgu — Elektrik Mavi (accent)
    CYAN_500  = "#00b4d8"
    CYAN_400  = "#22d3ee"
    CYAN_300  = "#67e8f9"
    CYAN_BG   = "rgba(0,180,216,0.10)"

    # Gri (nötr)
    GRAY_900 = "#111827"
    GRAY_800 = "#1f2937"
    GRAY_700 = "#374151"
    GRAY_600 = "#4b5563"
    GRAY_400 = "#9ca3af"
    GRAY_300 = "#d1d5db"
    GRAY_100 = "#f3f4f6"

    # Durum
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
    PURPLE_500 = "#a855f7"
    PURPLE_BG  = "rgba(168,85,247,0.10)"

    # Menu renkleri
    MENU_ACTIVE = "#00b4d8"
    MENU_ITEM   = "#8aa8c8"

    SUCCESS = "#10b981"


class DarkTheme:
    """
    Medikal koyu mavi dark tema.
    Tüm attribute isimleri önceki versiyonla birebir aynı.
    """
    # ── Zemin Katmanları ─────────────────────────────────────────
    BG_PRIMARY   = "#0b1628"   # Ana zemin — derin lacivert
    BG_SECONDARY = "#0e1e35"   # Panel / kart
    BG_TERTIARY  = "#112240"   # İçe gömülü alan, zebra satır
    BG_ELEVATED  = "#152b4f"   # Yükseltilmiş panel, popup
    BG_HOVER     = "rgba(0,180,216,0.06)"
    BG_SELECTED  = "rgba(0,180,216,0.14)"

    # ── Kenarlıklar ──────────────────────────────────────────────
    BORDER_PRIMARY   = "rgba(255,255,255,0.07)"
    BORDER_SECONDARY = "rgba(255,255,255,0.04)"
    BORDER_FOCUS     = "#00b4d8"
    BORDER_STRONG    = "rgba(255,255,255,0.12)"

    # ── Metin ────────────────────────────────────────────────────
    TEXT_PRIMARY   = "#e2eaf4"   # Beyaza yakın, parlak
    TEXT_SECONDARY = "#8aa8c8"   # Soluk mavi-gri
    TEXT_MUTED     = "#4e6888"   # Placeholder
    TEXT_DISABLED  = "#263850"   # Devre dışı

    # ── Input ────────────────────────────────────────────────────
    INPUT_BG           = "#112240"
    INPUT_BORDER       = "rgba(255,255,255,0.08)"
    INPUT_BORDER_FOCUS = "#00b4d8"

    # ── Vurgu (Cyan) ─────────────────────────────────────────────
    ACCENT    = "#00b4d8"
    ACCENT2   = "#22d3ee"
    ACCENT_BG = "rgba(0,180,216,0.10)"

    # ── Butonlar ─────────────────────────────────────────────────
    BTN_PRIMARY_BG     = "#00b4d8"
    BTN_PRIMARY_TEXT   = "#060d1a"
    BTN_PRIMARY_HOVER  = "#22d3ee"
    BTN_PRIMARY_BORDER = "#00b4d8"

    BTN_SECONDARY_BG     = "rgba(255,255,255,0.05)"
    BTN_SECONDARY_TEXT   = "#8aa8c8"
    BTN_SECONDARY_BORDER = "rgba(255,255,255,0.10)"
    BTN_SECONDARY_HOVER  = "rgba(255,255,255,0.09)"

    BTN_DANGER_BG     = "rgba(239,68,68,0.10)"
    BTN_DANGER_TEXT   = "#f87171"
    BTN_DANGER_BORDER = "rgba(239,68,68,0.25)"
    BTN_DANGER_HOVER  = "rgba(239,68,68,0.18)"

    BTN_SUCCESS_BG     = "rgba(16,185,129,0.10)"
    BTN_SUCCESS_TEXT   = "#34d399"
    BTN_SUCCESS_BORDER = "rgba(16,185,129,0.25)"
    BTN_SUCCESS_HOVER  = "rgba(16,185,129,0.18)"

    # ── Durum ────────────────────────────────────────────────────
    STATUS_SUCCESS = "#10b981"
    STATUS_WARNING = "#f59e0b"
    STATUS_ERROR   = "#ef4444"
    STATUS_INFO    = "#00b4d8"

    # ── Badge RGBA (r,g,b,alpha) ──────────────────────────────────
    STATE_ACTIVE  = (16,  185, 129, 35)
    STATE_PASSIVE = (239, 68,  68,  35)
    STATE_LEAVE   = (245, 158, 11,  35)

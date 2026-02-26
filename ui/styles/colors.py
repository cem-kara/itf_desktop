# ui/styles/colors.py  ─  REPYS v3 · Medikal Dark-Blue Tema
# ═══════════════════════════════════════════════════════════════
#
#  İKİ KATMANLI PALET SİSTEMİ
#  ┌─ Colors     ─ Ham hex değerleri, global renk paleti
#  └─ DarkTheme  ─ Anlamsal (semantic) tasarım token'ları
#
#  Kullanım:
#     from ui.styles.colors import Colors, DarkTheme
#
#  ⚠  Sayfa/bileşen kodunda doğrudan Colors kullanmayın.
#     Her zaman DarkTheme token'larını tercih edin.
# ═══════════════════════════════════════════════════════════════


class Colors:
    """
    Ham renk paleti — uygulama genelinde yeniden kullanılabilir
    referans değerleri. Doğrudan UI bileşenlerinde kullanılmaz;
    DarkTheme ve LightTheme bu değerlerden token üretir.
    """

    WHITE = "#ffffff"
    BLACK = "#000000"

    # ── Mavi / Lacivert skalası ──────────────────────────────────
    NAVY_950 = "#060d1a"   # En koyu zemin
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

    # ── Vurgu — Elektrik Mavi (accent) ──────────────────────────
    CYAN_500 = "#00b4d8"
    CYAN_400 = "#22d3ee"
    CYAN_300 = "#67e8f9"
    CYAN_BG  = "rgba(0,180,216,0.10)"

    # ── Gri (nötr) ───────────────────────────────────────────────
    GRAY_900 = "#111827"
    GRAY_800 = "#1f2937"
    GRAY_700 = "#374151"
    GRAY_600 = "#4b5563"
    GRAY_400 = "#9ca3af"
    GRAY_300 = "#d1d5db"
    GRAY_100 = "#f3f4f6"

    # ── Durum renkleri ───────────────────────────────────────────
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
    ORANGE_400 = "#fb923c"

    PURPLE_500 = "#a855f7"
    PURPLE_400 = "#c084fc"
    PURPLE_BG  = "rgba(168,85,247,0.10)"

    # ── Menü renkleri ────────────────────────────────────────────
    MENU_ACTIVE = "#00b4d8"
    MENU_ITEM   = "#8aa8c8"


class DarkTheme:
    """
    Medikal koyu mavi dark tema — anlamsal tasarım token'ları.

    Bu sınıfın attribute isimleri uygulama genelinde kullanılan
    sözleşmedir (contract). İsim değişikliği tüm sayfaları etkiler.

    Hiyerarşi (koyu → açık):
        BG_PRIMARY → BG_SECONDARY → BG_TERTIARY → BG_ELEVATED
    """

    # ── Yazı tipi ────────────────────────────────────────────────
    MONOSPACE = "JetBrains Mono"   # Tablolar, input'lar, KPI değerleri

    # ── Zemin katmanları ─────────────────────────────────────────
    #    BG_PRIMARY  : Ana pencere zemini
    #    BG_SECONDARY: Panel / kart zemini
    #    BG_TERTIARY : Zebra satır, gömülü alan (= BG_PRIMARY, bilerek)
    #    BG_ELEVATED : Popup, tooltip, yükseltilmiş bileşen
    BG_PRIMARY   = "#0d1117"
    BG_SECONDARY = "#121820"
    BG_TERTIARY  = "#0d1117"   # ← BG_PRIMARY ile aynı (tablo zebra zemin)
    BG_ELEVATED  = "#1a2030"
    BG_HOVER     = "rgba(61,142,245,0.06)"
    BG_SELECTED  = "rgba(61,142,245,0.14)"

    # ── Kenarlıklar ──────────────────────────────────────────────
    #    BORDER_PRIMARY  : Varsayılan kenarlık
    #    BORDER_SECONDARY: Çok ince / iç kenarlık
    #    BORDER_STRONG   : Belirgin kenarlık, hover'da kullanılır
    #    BORDER_FOCUS    : Odak halkası rengi (mavi)
    BORDER_PRIMARY   = "#1e2d3d"
    BORDER_SECONDARY = "#253545"
    BORDER_STRONG    = "#253545"   # BORDER_SECONDARY ile aynı — bağımsız güncelleme için ayrı tutuldu
    BORDER_FOCUS     = "#3d8ef5"

    # ── Metin ────────────────────────────────────────────────────
    TEXT_PRIMARY   = "#e8edf5"   # Birincil metin — parlak beyaza yakın
    TEXT_SECONDARY = "#8fa3b8"   # İkincil metin — mavi-gri
    TEXT_MUTED     = "#4d6070"   # Açıklama, yardımcı metin
    TEXT_DISABLED  = "#263850"   # Devre dışı bileşen metni

    # ── Input alanları ───────────────────────────────────────────
    INPUT_BG           = "#1a2030"   # = BG_ELEVATED
    INPUT_BORDER       = "#1e2d3d"   # = BORDER_PRIMARY
    INPUT_BORDER_FOCUS = "#3d8ef5"   # = BORDER_FOCUS

    # ── Vurgu (Accent) ───────────────────────────────────────────
    ACCENT    = "#3d8ef5"              # Ana vurgu rengi — mavi
    ACCENT2   = "#20c0d8"              # İkincil vurgu — cyan
    ACCENT_BG = "rgba(61,142,245,0.12)"

    # ── Butonlar ─────────────────────────────────────────────────
    BTN_PRIMARY_BG     = "#3d8ef5"
    BTN_PRIMARY_TEXT   = "#060d1a"
    BTN_PRIMARY_HOVER  = "#20c0d8"
    BTN_PRIMARY_BORDER = "#3d8ef5"

    BTN_SECONDARY_BG     = "#1a2030"
    BTN_SECONDARY_TEXT   = "#8fa3b8"
    BTN_SECONDARY_BORDER = "#1e2d3d"
    BTN_SECONDARY_HOVER  = "#253545"

    BTN_DANGER_BG     = "rgba(232,85,85,0.15)"
    BTN_DANGER_TEXT   = "#e85555"
    BTN_DANGER_BORDER = "rgba(232,85,85,0.30)"
    BTN_DANGER_HOVER  = "rgba(232,85,85,0.25)"

    BTN_SUCCESS_BG     = "rgba(46,201,142,0.15)"
    BTN_SUCCESS_TEXT   = "#2ec98e"
    BTN_SUCCESS_BORDER = "rgba(46,201,142,0.30)"
    BTN_SUCCESS_HOVER  = "rgba(46,201,142,0.25)"

    # ── Durum token'ları ─────────────────────────────────────────
    STATUS_SUCCESS = "#2ec98e"
    STATUS_WARNING = "#e8a030"
    STATUS_ERROR   = "#e85555"
    STATUS_INFO    = "#3d8ef5"

    # ── Badge RGBA (r, g, b, alpha) ──────────────────────────────
    STATE_ACTIVE  = (16,  185, 129, 35)   # Yeşil — aktif
    STATE_PASSIVE = (239, 68,  68,  35)   # Kırmızı — pasif / arıza
    STATE_LEAVE   = (245, 158, 11,  35)   # Sarı — izinli

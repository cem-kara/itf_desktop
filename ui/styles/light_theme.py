# ui/styles/light_theme.py  ─  REPYS v3 · Açık Tema
# ═══════════════════════════════════════════════════════════════
#
#  v3.1: Renkler artık ui/styles/themes.py LIGHT dict'inden geliyor.
#  DarkTheme ile birebir aynı attribute isimleri korundu.
#
# ═══════════════════════════════════════════════════════════════

from ui.styles.themes import LIGHT as _L


class LightTheme:
    """
    Medikal açık mavi light tema.
    DarkTheme ile birebir aynı attribute sözleşmesi.
    Tüm değerler ui/styles/themes.py LIGHT dict'inden gelir.
    """

    # Zemin
    BG_PRIMARY    = _L["BG_PRIMARY"]
    BG_SECONDARY  = _L["BG_SECONDARY"]
    BG_TERTIARY   = _L["BG_TERTIARY"]
    BG_ELEVATED   = _L["BG_ELEVATED"]
    BG_DARK       = _L["BG_DARK"]
    BG_HOVER      = _L["BG_HOVER"]
    BG_SELECTED   = _L["BG_SELECTED"]

    # Kenarlıklar
    BORDER_PRIMARY    = _L["BORDER_PRIMARY"]
    BORDER_SECONDARY  = _L["BORDER_SECONDARY"]
    BORDER_STRONG     = _L["BORDER_STRONG"]
    BORDER_FOCUS      = _L["BORDER_FOCUS"]

    # Metin
    TEXT_PRIMARY       = _L["TEXT_PRIMARY"]
    TEXT_SECONDARY     = _L["TEXT_SECONDARY"]
    TEXT_MUTED         = _L["TEXT_MUTED"]
    TEXT_DISABLED      = _L["TEXT_DISABLED"]
    TEXT_TABLE_HEADER  = _L["TEXT_TABLE_HEADER"]

    # Input
    INPUT_BG            = _L["INPUT_BG"]
    INPUT_BORDER        = _L["INPUT_BORDER"]
    INPUT_BORDER_FOCUS  = _L["INPUT_BORDER_FOCUS"]

    # Vurgu
    ACCENT    = _L["ACCENT"]
    ACCENT2   = _L["ACCENT2"]
    ACCENT_BG = _L["ACCENT_BG"]

    # Butonlar
    BTN_PRIMARY_BG       = _L["BTN_PRIMARY_BG"]
    BTN_PRIMARY_TEXT     = _L["BTN_PRIMARY_TEXT"]
    BTN_PRIMARY_HOVER    = _L["BTN_PRIMARY_HOVER"]
    BTN_PRIMARY_BORDER   = _L["BTN_PRIMARY_BORDER"]
    BTN_SECONDARY_BG     = _L["BTN_SECONDARY_BG"]
    BTN_SECONDARY_TEXT   = _L["BTN_SECONDARY_TEXT"]
    BTN_SECONDARY_BORDER = _L["BTN_SECONDARY_BORDER"]
    BTN_SECONDARY_HOVER  = _L["BTN_SECONDARY_HOVER"]
    BTN_DANGER_BG        = _L["BTN_DANGER_BG"]
    BTN_DANGER_TEXT      = _L["BTN_DANGER_TEXT"]
    BTN_DANGER_BORDER    = _L["BTN_DANGER_BORDER"]
    BTN_DANGER_HOVER     = _L["BTN_DANGER_HOVER"]
    BTN_SUCCESS_BG       = _L["BTN_SUCCESS_BG"]
    BTN_SUCCESS_TEXT     = _L["BTN_SUCCESS_TEXT"]
    BTN_SUCCESS_BORDER   = _L["BTN_SUCCESS_BORDER"]
    BTN_SUCCESS_HOVER    = _L["BTN_SUCCESS_HOVER"]

    # Durum
    STATUS_SUCCESS = _L["STATUS_SUCCESS"]
    STATUS_WARNING = _L["STATUS_WARNING"]
    STATUS_ERROR   = _L["STATUS_ERROR"]
    STATUS_INFO    = _L["STATUS_INFO"]

    # Diğer
    MONOSPACE = _L["MONOSPACE"]
    RKE_PURP  = _L["RKE_PURP"]

    # Badge RGBA tuple'ları (DarkTheme ile aynı)
    STATE_ACTIVE  = (16,  185, 129, 35)
    STATE_PASSIVE = (239, 68,  68,  35)
    STATE_LEAVE   = (245, 158, 11,  35)

# ui/styles/colors.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Merkezi Renk Paletleri
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Colors:
    """Temel renk paletleri."""
    
    # Siyah-Beyaz
    WHITE = "#ffffff"
    BLACK = "#000000"
    
    # Gri tonları
    GRAY_900 = "#0f1020"
    GRAY_800 = "#1e202c"
    GRAY_700 = "#2d2e40"
    GRAY_600 = "#475569"
    GRAY_500 = "#64748b"
    GRAY_400 = "#94a3b8"
    GRAY_300 = "#cbd5e1"
    GRAY_200 = "#e2e8f0"
    GRAY_100 = "#f1f5f9"
    GRAY_50 = "#f8fafc"
    
    # Mavi (Primary)
    BLUE_900 = "#0c2f78"
    BLUE_700 = "#1d75fe"
    BLUE_600 = "#2563eb"
    BLUE_500 = "#3b82f6"
    BLUE_400 = "#60a5fa"
    BLUE_300 = "#93c5fd"
    BLUE_200 = "#bfdbfe"
    BLUE_100 = "#dbeafe"
    BLUE_50 = "#eff6ff"
    
    # Yeşil (Success)
    GREEN_700 = "#15803d"
    GREEN_600 = "#16a34a"
    GREEN_500 = "#22c55e"
    GREEN_400 = "#4ade80"
    GREEN_50 = "#f0fdf4"
    
    # Kırmızı (Danger)
    RED_700 = "#b91c1c"
    RED_600 = "#dc2626"
    RED_500 = "#ef4444"
    RED_400 = "#f87171"
    RED_50 = "#fef2f2"
    
    # Sarı (Warning)
    YELLOW_700 = "#a16207"
    YELLOW_600 = "#ca8a04"
    YELLOW_500 = "#eab308"
    YELLOW_400 = "#facc15"
    YELLOW_50 = "#fefce8"
    
    # Turuncu (Info)
    ORANGE_600 = "#ea580c"
    ORANGE_500 = "#f97316"
    ORANGE_400 = "#fb923c"
    

class DarkTheme:
    """Dark tema renkleri (W11 Glass stili)."""
    
    # Arka planlar
    BG_PRIMARY = "#16172b"
    BG_SECONDARY = "#1e202c"
    BG_TERTIARY = "#292b41"
    BG_HOVER = "rgba(255, 255, 255, 0.04)"
    BG_SELECTED = "rgba(29, 117, 254, 0.45)"
    
    # Kenarlıklar
    BORDER_PRIMARY = "rgba(255, 255, 255, 0.08)"
    BORDER_SECONDARY = "rgba(255, 255, 255, 0.04)"
    BORDER_FOCUS = "rgba(29, 117, 254, 0.5)"
    
    # Metin
    TEXT_PRIMARY = "#e0e2ea"
    TEXT_SECONDARY = "#c8cad0"
    TEXT_MUTED = "#8b8fa3"
    TEXT_DISABLED = "#5a5d6e"
    
    # Componentler
    INPUT_BG = "#1e202c"
    INPUT_BORDER = "#292b41"
    INPUT_BORDER_FOCUS = "#1d75fe"
    
    # Button renkler
    BTN_PRIMARY_BG = "rgba(29, 117, 254, 0.25)"
    BTN_PRIMARY_TEXT = "#6bd3ff"
    BTN_PRIMARY_BORDER = "rgba(29, 117, 254, 0.4)"
    BTN_PRIMARY_HOVER = "rgba(29, 117, 254, 0.4)"
    
    BTN_SECONDARY_BG = "rgba(255, 255, 255, 0.06)"
    BTN_SECONDARY_TEXT = "#8b8fa3"
    BTN_SECONDARY_BORDER = "rgba(255, 255, 255, 0.06)"
    
    BTN_DANGER_BG = "rgba(239, 68, 68, 0.15)"
    BTN_DANGER_TEXT = "#f87171"
    BTN_DANGER_BORDER = "rgba(239, 68, 68, 0.25)"
    BTN_DANGER_HOVER = "rgba(239, 68, 68, 0.35)"
    
    BTN_SUCCESS_BG = "rgba(5, 150, 105, 0.25)"
    BTN_SUCCESS_TEXT = "#6ee7b7"
    BTN_SUCCESS_BORDER = "rgba(5, 150, 105, 0.4)"
    BTN_SUCCESS_HOVER = "rgba(5, 150, 105, 0.4)"
    
    # Status renkler
    STATUS_SUCCESS = "#22c55e"
    STATUS_WARNING = "#f59e0b"
    STATUS_ERROR = "#ef4444"
    STATUS_INFO = "#3b82f6"
    
    # Durum Hücre Renkleri (transparency ile)
    STATE_ACTIVE = (34, 197, 94, 40)      # Yeşil
    STATE_PASSIVE = (239, 68, 68, 40)     # Kırmızı
    STATE_LEAVE = (234, 179, 8, 40)       # Sarı

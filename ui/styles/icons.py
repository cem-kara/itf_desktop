# ui/styles/icons.py
#
# SVG ikonlar Lucide Icons projesinden esinlenilerek hazırlanmıştır.
# Lucide Icons — MIT Lisansı — https://lucide.dev
# Copyright (c) 2020 Lucide Contributors
#
# Tabler Icons — MIT Lisansı — https://tabler.io/icons  
# Copyright (c) 2020 Paweł Kuna
# -------------------------------------------------------------
# Profesyonel SVG İkon Kütüphanesi  PySide6 Uyumlu
#
# Kullanm:
#   from ui.styles.icons import Icons, IconRenderer

#
#   # QIcon olarak al (QPushButton, QAction iin):
#   btn.setIcon(Icons.get("users"))
#
#   # QPixmap olarak al (QLabel iin):
#   label.setPixmap(Icons.pixmap("users", size=20, color="#6bd3ff"))
#
#   # kon + Metin buton:
#   IconRenderer.set_button_icon(btn, "users", color="#6bd3ff", size=16)
#
# -------------------------------------------------------------


from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtCore import Qt, QSize, QByteArray
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QPushButton, QLabel

# ================================================================
# ROL → RENK HEX MAP (QSS ile uyumlu)
# ================================================================
ROLE_COLOR_MAP = {
    "primary":   "#e0e2ea",   # TEXT_PRIMARY
    "secondary": "#8b8fa3",   # TEXT_SECONDARY
    "muted":     "#5a5d6e",   # TEXT_MUTED
    "disabled":  "#3a3c47",   # TEXT_DISABLED
    "accent":    "#6bd3ff",   # ACCENT
    "accent2":   "#60a5fa",   # ACCENT2
    "ok":        "#4ade80",   # STATUS_SUCCESS
    "warn":      "#facc15",   # STATUS_WARNING
    "err":       "#f87171",   # STATUS_ERROR
    "info":      "#60a5fa",   # STATUS_INFO
}

def resolve_icon_color(color: str) -> str:
    """
    Eğer color bir rol ismi ise hex koda çevirir.
    Değilse olduğu gibi döner.
    """
    if not color:
        return Icons.DEFAULT_COLOR
    return ROLE_COLOR_MAP.get(color, color)


# ================================================================
# SVG TANIMI  Tm ikonlar inline SVG olarak tanml
# Stroke tabanl, temiz izgi ikonlar (Lucide/Tabler stili)
# viewBox: 0 0 24 24, stroke-width: 1.75
# ================================================================

_SVG_PATHS: dict[str, str] = {

    #  TILDE ~
    "tilde": """
        <path d="M4 15c1.5-2 4.5-2 6 0s4.5 2 6 0" stroke-linecap="round"/>
    """,

    #  PERSONEL 
    "users": """
        <circle cx="9" cy="7" r="3.5"/>
        <path d="M2 20c0-3.866 3.134-7 7-7s7 3.134 7 7"/>
        <path d="M17 11c1.657 0 3 1.343 3 3" stroke-linecap="round"/>
        <path d="M19.5 20H22c0-2.761-1.791-5-4-5.5"/>
    """,

    "user_add": """
        <circle cx="10" cy="7" r="3.5"/>
        <path d="M2 20c0-3.866 3.134-7 8-7 1.5 0 2.9.37 4.1 1.02"/>
        <line x1="18" y1="14" x2="18" y2="22"/>
        <line x1="14" y1="18" x2="22" y2="18"/>
    """,

    "user": """
        <circle cx="12" cy="8" r="4"/>
        <path d="M4 20c0-4.418 3.582-8 8-8s8 3.582 8 8"/>
    """,

    "id_card": """
        <rect x="2" y="5" width="20" height="14" rx="2"/>
        <circle cx="8" cy="12" r="2.5"/>
        <path d="M14 10h4M14 14h3" stroke-linecap="round"/>
    """,

    #  DEVAM / ZN 
    "calendar": """
        <rect x="3" y="4" width="18" height="17" rx="2"/>
        <path d="M3 9h18" stroke-linecap="round"/>
        <path d="M8 2v4M16 2v4" stroke-linecap="round"/>
        <circle cx="8" cy="14" r="1" fill="currentColor" stroke="none"/>
        <circle cx="12" cy="14" r="1" fill="currentColor" stroke="none"/>
        <circle cx="16" cy="14" r="1" fill="currentColor" stroke="none"/>
    """,

    "calendar_check": """
        <rect x="3" y="4" width="18" height="17" rx="2"/>
        <path d="M3 9h18" stroke-linecap="round"/>
        <path d="M8 2v4M16 2v4" stroke-linecap="round"/>
        <path d="M8.5 14.5l2 2 4-4" stroke-linecap="round" stroke-linejoin="round"/>
    """,

    "calendar_off": """
        <rect x="3" y="4" width="18" height="17" rx="2"/>
        <path d="M3 9h18" stroke-linecap="round"/>
        <path d="M8 2v4M16 2v4" stroke-linecap="round"/>
        <path d="M9 14l6 4M15 14l-6 4" stroke-linecap="round"/>
    """,

    #  FHSZ / RAPOR 
    "bar_chart": """
        <rect x="3" y="12" width="4" height="9" rx="1"/>
        <rect x="10" y="7" width="4" height="14" rx="1"/>
        <rect x="17" y="4" width="4" height="17" rx="1"/>
        <path d="M3 3v18h18" stroke-linecap="round"/>
    """,

    "pie_chart": """
        <path d="M12 2a10 10 0 1 0 10 10H12V2z"/>
        <path d="M12 2v10l7.07-7.07A10 10 0 0 0 12 2z"/>
    """,

    "clipboard": """
        <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/>
        <rect x="9" y="3" width="6" height="4" rx="1.5"/>
        <path d="M9 12h6M9 16h4" stroke-linecap="round"/>
    """,

    "clipboard_list": """
        <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/>
        <rect x="9" y="3" width="6" height="4" rx="1.5"/>
        <path d="M9 12h6M9 16h6" stroke-linecap="round"/>
        <circle cx="7.5" cy="12" r="0.75" fill="currentColor" stroke="none"/>
        <circle cx="7.5" cy="16" r="0.75" fill="currentColor" stroke="none"/>
    """,

    #  SALIK 
    "activity": """
        <polyline points="22,12 18,12 15,20 9,4 6,12 2,12"
                  stroke-linecap="round" stroke-linejoin="round"/>
    """,

    "heart_pulse": """
        <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>
        <path d="M9 9h1l1 3 2-6 1 3h1" stroke-linecap="round" stroke-linejoin="round"/>
    """,

    "stethoscope": """
        <path d="M4.8 2.3A.3.3 0 1 0 5 2H4a2 2 0 0 0-2 2v5a6 6 0 0 0 6 6v0a6 6 0 0 0 6-6V4a2 2 0 0 0-2-2h-1a.2.2 0 1 0 .3.3"/>
        <path d="M8 15v1a6 6 0 0 0 6 6v0a6 6 0 0 0 6-6v-4"/>
        <circle cx="20" cy="10" r="2"/>
    """,

    #  CHAZ 
    "microscope": """
        <path d="M6 18h8M3 22h18M14 22a7 7 0 1 0-7-7"/>
        <path d="M9 4h2v2H9zM11 4h2v6h-2z"/>
        <path d="M9 7H7l-2 2v2h8V9l-2-2z"/>
    """,

    "device_add": """
        <rect x="2" y="6" width="14" height="12" rx="2"/>
        <path d="M16 10h4a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-4"/>
        <path d="M18 12v4" stroke-linecap="round"/>
        <path d="M16 14h4" stroke-linecap="round"/>
        <circle cx="9" cy="12" r="2"/>
    """,

    "cpu": """
        <rect x="7" y="7" width="10" height="10" rx="1"/>
        <path d="M9 3v4M15 3v4M9 17v4M15 17v4M3 9h4M3 15h4M17 9h4M17 15h4"
              stroke-linecap="round"/>
    """,

    "circuit_board": """
        <rect x="3" y="3" width="18" height="18" rx="2"/>
        <path d="M9 9h6v6H9z"/>
        <path d="M9 3v6M15 3v6M9 15v6M15 15v6M3 9h6M3 15h6M15 9h6M15 15h6"
              stroke-linecap="round"/>
    """,

    #  ARIZA / BAKIM 
    "alert_triangle": """
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
        <line x1="12" y1="9" x2="12" y2="13" stroke-linecap="round"/>
        <circle cx="12" cy="17" r="0.5" fill="currentColor" stroke="none"/>
    """,

    "alert_list": """
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
        <path d="M9 13h6M10 16h4" stroke-linecap="round"/>
        <circle cx="12" cy="10" r="0.5" fill="currentColor" stroke="none"/>
    """,

    "wrench": """
        <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
    """,

    "wrench_list": """
        <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0L21 4.5a6 6 0 0 1-7.94 7.94l-4.91 4.91a2.12 2.12 0 0 1-3-3l4.91-4.91A6 6 0 0 1 17.5 3l-2.8 3.3z"/>
        <path d="M2 20h8M2 16h6" stroke-linecap="round"/>
    """,

    "tools": """
        <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
        <path d="M2 12l3-3 2 2-3 3-2-2z" stroke-linejoin="round"/>
    """,

    #  KALBRASYON 
    "target": """
        <circle cx="12" cy="12" r="9"/>
        <circle cx="12" cy="12" r="5"/>
        <circle cx="12" cy="12" r="1" fill="currentColor" stroke="none"/>
        <path d="M12 3v3M12 18v3M3 12h3M18 12h3" stroke-linecap="round"/>
    """,

    "crosshair": """
        <circle cx="12" cy="12" r="8"/>
        <path d="M22 12h-4M6 12H2M12 6V2M12 22v-4" stroke-linecap="round"/>
        <circle cx="12" cy="12" r="1.5" fill="currentColor" stroke="none"/>
    """,

    #  RKE / GVENLK 
    "shield": """
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    """,

    "shield_check": """
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
        <path d="M9 12l2 2 4-4" stroke-linecap="round" stroke-linejoin="round"/>
    """,

    "shield_alert": """
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
        <path d="M12 8v4" stroke-linecap="round"/>
        <circle cx="12" cy="15" r="0.5" fill="currentColor" stroke="none"/>
    """,

    "shield_cog": """
        <path d="m10.929 14.467-.383.924"/>
        <path d="M10.929 8.923 10.546 8"/>
        <path d="M13.225 8.923 13.608 8"/>
        <path d="m13.607 15.391-.382-.924"/>
        <path d="m14.849 10.547.923-.383"/>
        <path d="m14.849 12.843.923.383"/>
        <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>
        <path d="m9.305 10.547-.923-.383"/>
        <path d="m9.305 12.843-.923.383"/>
        <circle cx="12.077" cy="11.695" r="3"/>
    """,

    "radiation": """
        <path d="M12 12h.01"/>
        <path d="M14 15.4641a4 4 0 0 1-4 0L7.52786 19.74597 A 1 1 0 0 0 7.99303 21.16211 10 10 0 0 0 16.00697 21.16211 1 1 0 0 0 16.47214 19.74597z"/>
        <path d="M16 12a4 4 0 0 0-2-3.464l2.472-4.282a1 1 0 0 1 1.46-.305 10 10 0 0 1 4.006 6.94A1 1 0 0 1 21 12z"/>
        <path d="M8 12a4 4 0 0 1 2-3.464L7.528 4.254a1 1 0 0 0-1.46-.305 10 10 0 0 0-4.006 6.94A1 1 0 0 0 3 12z"/>
    """,

    "lock": """
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
        <path d="M7 11V7a5 5 0 0 1 10 0v4" stroke-linecap="round"/>
        <circle cx="12" cy="16" r="1" fill="currentColor" stroke="none"/>
    """,

    "check_in": """
        <path d="M9 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-4"/>
        <polyline points="14,9 9,14 6.5,11.5" stroke-linecap="round" stroke-linejoin="round"/>
        <polyline points="16,3 22,3 22,9" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="15" y1="10" x2="22" y2="3" stroke-linecap="round"/>
    """,

    #  RAPORLAMA 
    "file_text": """
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14,2 14,8 20,8"/>
        <path d="M16 13H8M16 17H8M10 9H8" stroke-linecap="round"/>
    """,

    "file_chart": """
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14,2 14,8 20,8"/>
        <rect x="8" y="16" width="2" height="3"/>
        <rect x="11" y="13" width="2" height="6"/>
        <rect x="14" y="14" width="2" height="5"/>
    """,

    #  YIL SONU 
    "calendar_year": """
        <rect x="3" y="4" width="18" height="17" rx="2"/>
        <path d="M3 9h18" stroke-linecap="round"/>
        <path d="M8 2v4M16 2v4" stroke-linecap="round"/>
        <path d="M8 14l2 2 4-4" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M8 17h8" stroke-linecap="round"/>
    """,

    #  AYARLAR / YNETM 
    "settings": """
        <circle cx="12" cy="12" r="3"/>
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
    """,

    "settings_sliders": """
        <line x1="4" y1="6" x2="20" y2="6" stroke-linecap="round"/>
        <line x1="4" y1="12" x2="20" y2="12" stroke-linecap="round"/>
        <line x1="4" y1="18" x2="20" y2="18" stroke-linecap="round"/>
        <circle cx="8" cy="6" r="2" fill="none"/>
        <circle cx="16" cy="12" r="2" fill="none"/>
        <circle cx="10" cy="18" r="2" fill="none"/>
    """,

    #  GENELGEEKL KONLAR 
    "plus": """
        <line x1="12" y1="5" x2="12" y2="19" stroke-linecap="round"/>
        <line x1="5" y1="12" x2="19" y2="12" stroke-linecap="round"/>
    """,

    "plus_circle": """
        <circle cx="12" cy="12" r="9"/>
        <line x1="12" y1="8" x2="12" y2="16" stroke-linecap="round"/>
        <line x1="8" y1="12" x2="16" y2="12" stroke-linecap="round"/>
    """,

    "check_square": """
        <rect x="3" y="3" width="18" height="18" rx="2"/>
        <path d="M8 12l3 3 5-5" stroke-linecap="round" stroke-linejoin="round"/>
    """,

    "clock": """
        <circle cx="12" cy="12" r="9"/>
        <path d="M12 7v5l3 2" stroke-linecap="round" stroke-linejoin="round"/>
    """,

    "bolt": """
        <path d="M13 2L4 14h6l-1 8 9-12h-6l1-8z" stroke-linejoin="round"/>
    """,

    "refresh": """
        <polyline points="23,4 23,10 17,10" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" stroke-linecap="round"/>
    """,

    "search": """
        <circle cx="11" cy="11" r="7"/>
        <line x1="21" y1="21" x2="16.65" y2="16.65" stroke-linecap="round"/>
    """,

    "filter": """
        <polygon points="22,3 2,3 10,12.46 10,19 14,21 14,12.46"/>
    """,

    "download": """
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="7,10 12,15 17,10" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="12" y1="15" x2="12" y2="3" stroke-linecap="round"/>
    """,

    "upload": """
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="17,8 12,3 7,8" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="12" y1="3" x2="12" y2="15" stroke-linecap="round"/>
    """,

    "edit": """
        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
    """,

    "trash": """
        <polyline points="3,6 5,6 21,6" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
    """,

    "eye": """
        <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z"/>
        <circle cx="12" cy="12" r="3"/>
    """,

    "check": """
        <polyline points="20,6 9,17 4,12" stroke-linecap="round" stroke-linejoin="round"/>
    """,

    "check_circle": """
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
        <polyline points="22,4 12,14.01 9,11.01" stroke-linecap="round" stroke-linejoin="round"/>
    """,

    "x": """
        <line x1="18" y1="6" x2="6" y2="18" stroke-linecap="round"/>
        <line x1="6" y1="6" x2="18" y2="18" stroke-linecap="round"/>
    """,

    "x_circle": """
        <circle cx="12" cy="12" r="9"/>
        <line x1="15" y1="9" x2="9" y2="15" stroke-linecap="round"/>
        <line x1="9" y1="9" x2="15" y2="15" stroke-linecap="round"/>
    """,

    "info": """
        <circle cx="12" cy="12" r="9"/>
        <line x1="12" y1="8" x2="12" y2="12" stroke-linecap="round"/>
        <circle cx="12" cy="16" r="0.5" fill="currentColor" stroke="none"/>
    """,

    "bell": """
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
        <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
    """,

    "bell_dot": """
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
        <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
        <circle cx="19" cy="5" r="2.5" fill="#ef4444" stroke="#ef4444"/>
    """,

    "log_out": """
        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
        <polyline points="16,17 21,12 16,7" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="21" y1="12" x2="9" y2="12" stroke-linecap="round"/>
    """,

    "home": """
        <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"
              stroke-linejoin="round"/>
        <polyline points="9,22 9,12 15,12 15,22" stroke-linejoin="round"/>
    """,

    "layers": """
        <polygon points="12,2 2,7 12,12 22,7"/>
        <polyline points="2,17 12,22 22,17"/>
        <polyline points="2,12 12,17 22,12"/>
    """,

    "list": """
        <line x1="8" y1="6" x2="21" y2="6" stroke-linecap="round"/>
        <line x1="8" y1="12" x2="21" y2="12" stroke-linecap="round"/>
        <line x1="8" y1="18" x2="21" y2="18" stroke-linecap="round"/>
        <circle cx="4" cy="6" r="1" fill="currentColor" stroke="none"/>
        <circle cx="4" cy="12" r="1" fill="currentColor" stroke="none"/>
        <circle cx="4" cy="18" r="1" fill="currentColor" stroke="none"/>
    """,

    "database": """
        <ellipse cx="12" cy="5" rx="9" ry="3"/>
        <path d="M21 12c0 1.66-4.03 3-9 3S3 13.66 3 12"/>
        <path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5"/>
    """,

    "save": """
        <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
        <polyline points="17,21 17,13 7,13 7,21"/>
        <polyline points="7,3 7,8 15,8"/>
    """,

    "print": """
        <polyline points="6,9 6,2 18,2 18,9"/>
        <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>
        <rect x="6" y="14" width="12" height="8"/>
    """,

    "mail": """
        <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
        <polyline points="22,6 12,13 2,6"/>
    """,

    "arrow_left": """
        <line x1="19" y1="12" x2="5" y2="12" stroke-linecap="round"/>
        <polyline points="12,19 5,12 12,5" stroke-linecap="round" stroke-linejoin="round"/>
    """,

    "arrow_right": """
        <line x1="5" y1="12" x2="19" y2="12" stroke-linecap="round"/>
        <polyline points="12,5 19,12 12,19" stroke-linecap="round" stroke-linejoin="round"/>
    """,

    "chevron_down": """
        <polyline points="6,9 12,15 18,9" stroke-linecap="round" stroke-linejoin="round"/>
    """,

    "chevron_up": """
        <polyline points="6,15 12,9 18,15" stroke-linecap="round" stroke-linejoin="round"/>
    """,

    "chevron_left": """
        <polyline points="15,18 9,12 15,6" stroke-linecap="round" stroke-linejoin="round"/>
    """,

    "chevron_right": """
        <polyline points="9,18 15,12 9,6" stroke-linecap="round" stroke-linejoin="round"/>
    """,

    "menu": """
        <line x1="3" y1="12" x2="21" y2="12" stroke-linecap="round"/>
        <line x1="3" y1="6" x2="21" y2="6" stroke-linecap="round"/>
        <line x1="3" y1="18" x2="21" y2="18" stroke-linecap="round"/>
    """,

    #  DURUM KONLARI 
    "status_active": """
        <circle cx="12" cy="12" r="9"/>
        <path d="M8 12l3 3 5-5" stroke-linecap="round" stroke-linejoin="round"/>
    """,

    "status_passive": """
        <circle cx="12" cy="12" r="9"/>
        <line x1="15" y1="9" x2="9" y2="15" stroke-linecap="round"/>
        <line x1="9" y1="9" x2="15" y2="15" stroke-linecap="round"/>
    """,

    "status_leave": """
        <circle cx="12" cy="12" r="9"/>
        <line x1="12" y1="8" x2="12" y2="12" stroke-linecap="round"/>
        <circle cx="12" cy="16" r="0.5" fill="currentColor" stroke="none"/>
    """,

    #  HASTANE / LOGO 
    "hospital": """
        <path d="M12 6V2H8v4H4a2 2 0 0 0-2 2v14h20V8a2 2 0 0 0-2-2h-4V2h-4v4z"/>
        <path d="M10 14v-3h4v3"/>
        <path d="M12 11v3"/>
        <path d="M10 11h4" stroke-linecap="round"/>
    """,

    "building": """
        <rect x="3" y="2" width="18" height="20" rx="1"/>
        <path d="M9 22v-4h6v4"/>
        <path d="M8 6h.01M16 6h.01M8 10h.01M16 10h.01M8 14h.01M16 14h.01"
              stroke-linecap="round" stroke-width="2.5"/>
    """,

    #  EXCEL / PDF BUTONLARI 
    "file_excel": """
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14,2 14,8 20,8"/>
        <path d="M9 13l2 3 2-3M9 16l2-3 2 3" stroke-linecap="round" stroke-linejoin="round"/>
    """,

    "file_pdf": """
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14,2 14,8 20,8"/>
        <path d="M9 13h1.5a1 1 0 0 1 0 2H9v-4h1.5a1 1 0 0 1 0 2"/>
        <path d="M14 11h1a2 2 0 0 1 2 2v1a2 2 0 0 1-2 2h-1v-5z"/>
    """,

    "sync": """
        <polyline points="1,4 1,10 7,10" stroke-linecap="round" stroke-linejoin="round"/>
        <polyline points="23,20 23,14 17,14" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10M23 14l-4.64 4.36A9 9 0 0 1 3.51 15"
              stroke-linecap="round"/>
    """,

    "cloud_sync": """
        <polyline points="16,16 12,12 8,16" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="12" y1="12" x2="12" y2="21" stroke-linecap="round"/>
        <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/>
    """,

    "package": """
        <line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/>
        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
        <polyline points="3.27,6.96 12,12.01 20.73,6.96"/>
        <line x1="12" y1="22.08" x2="12" y2="12"/>
    """,
}


# ================================================================
# MENU IKON HARITALAMASI
# sidebar.py'deki MENU_ICONS'u emojiden SVG key'e tasiyin
# ================================================================

MENU_ICON_MAP: dict[str, str] = {
    "Personel Listesi":  "users",
    "Personel Ekle":     "user_add",
    "İzin Takip":        "calendar_check",
    "İzin Takip ve FHSZ Yönetim":      "bar_chart",
    "Puantaj Rapor":     "clipboard_list",
    "Sağlık Takip":      "activity",
    "Personel Verileri": "file_chart",
    "Cihaz Listesi":     "microscope",
    "Cihaz Ekle":        "device_add",
    "Arıza Kayıt":       "alert_triangle",
    "Arıza Listesi":     "wrench_list",
    "Teknik Hizmetler":   "tools",
    "Kalibrasyon Takip": "crosshair",
    "RKE Envanter":      "shield_check",
    "RKE Muayene":       "check_in",
    "RKE Raporlama":     "file_text",
    "Yıl Sonu İzin":     "calendar_year",
    "Ayarlar":           "settings",
    "Dozimetre Takip":      "radiation",
    "Diğer Rad. Gör. FHSZ Yön.": "shield_alert",
    "Yönetici İşlemleri": "settings_sliders",
    "Nöbet Planı": "calendar_check",
    "Fazla Mesai": "clock",
    "Nöbetçi Listesi": "users",
}

GROUP_ICON_MAP: dict[str, str] = {
    "PERSONEL":           "user",
    "CİHAZ":              "microscope",
    "RKE":                "shield",
    "YÖNETİCİ İŞLEMLERİ": "settings_sliders",
    "NÖBET":              "calendar_check",
}


# ================================================================
# SVG RENDER MOTORu
# ================================================================

def _build_svg(paths: str, color: str, size: int) -> str:
    """Ham path verisinden tam SVG belgesi oluturur."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg"
     width="{size}" height="{size}" viewBox="0 0 24 24"
     fill="none"
     stroke="{color}"
     stroke-width="1.75"
     stroke-linecap="round"
     stroke-linejoin="round">
     {paths}
</svg>"""


def _render_svg(svg_str: str, size: int) -> QPixmap:
    """SVG string'i QPixmap'e dntrr."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(QByteArray(svg_str.encode("utf-8")))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()
    return pixmap


# ================================================================
# ANA API  Icons snf
# ================================================================

class Icons:
    """
    Merkezi SVG ikon eriim noktas.

    rnekler
    --------
    # Varsaylan renk ve boyutla QIcon al:
    icon = Icons.get("users")

    # zel renk ve boyut:
    icon = Icons.get("settings", color="#6bd3ff", size=20)

    # QPixmap olarak (QLabel iin):
    pm = Icons.pixmap("bell", size=24, color="#ffca28")

    # Mevcut tm ikon isimlerini listele:
    Icons.available()
    """

    # Varsaylan deerler (DarkTheme uyumlu)
    DEFAULT_COLOR: str = "#8b8fa3"    # TEXT_MUTED benzeri ntr gri
    DEFAULT_SIZE:  int = 16

    #  nbellek  ayn (name, color, size) ls iin tekrar render etme
    _cache: dict[tuple, QPixmap] = {}

    @classmethod
    def pixmap(
        cls,
        name: str,
        size:  int = DEFAULT_SIZE,
        color: str = DEFAULT_COLOR,
    ) -> QPixmap:
        """İkon adından QPixmap döndürür. Bulunamazsa boş pixmap."""
        hex_color = resolve_icon_color(color)
        key = (name, size, hex_color)
        if key in cls._cache:
            return cls._cache[key]

        paths = _SVG_PATHS.get(name)
        if paths is None:
            # Bilinmeyen ikon için soru işareti benzeri minimal placeholder
            paths = '<circle cx="12" cy="12" r="8"/><text x="12" y="17" text-anchor="middle" font-size="12" fill="{c}" stroke="none">?</text>'.replace("{c}", hex_color)

        svg = _build_svg(paths, hex_color, size)
        pm = _render_svg(svg, size)
        cls._cache[key] = pm
        return pm

    @classmethod
    def get(
        cls,
        name: str,
        size:  int = DEFAULT_SIZE,
        color: str = DEFAULT_COLOR,
    ) -> QIcon:
        """İkon adından QIcon döndürür (QPushButton.setIcon için)."""
        return QIcon(cls.pixmap(name, size, color))

    @classmethod
    def menu_icon(cls, menu_title: str, size: int = 16) -> QIcon | None:
        """
        Men balndan QIcon dndrr.
        MENU_ICON_MAP zerinden alr.
        """
        key = MENU_ICON_MAP.get(menu_title)
        if key:
            return cls.get(key, size=size, color="#8b8fa3")
        return None

    @classmethod
    def group_icon(cls, group_name: str, size: int = 16) -> QIcon | None:
        """Grup balndan QIcon dndrr."""
        key = GROUP_ICON_MAP.get(group_name)
        if key:
            return cls.get(key, size=size, color="#6bd3ff")
        return None

    @classmethod
    def available(cls) -> list[str]:
        """Kaytl tm ikon isimlerini dndrr."""
        return sorted(_SVG_PATHS.keys())

    # SVG dosya önbelleği — diske yazılan dosya yolları
    _qss_file_cache: dict[tuple, str] = {}

    @classmethod
    def qss_url(
        cls,
        name:  str,
        color: str = DEFAULT_COLOR,
        size:  int = 12,
    ) -> str:
        """
        QSS içinde  image: url(...)  olarak kullanılmak üzere
        SVG içeriğini diske yazar ve dosya yolunu döndürür.

        Qt QSS motoru data: URI'yi desteklemez; gerçek dosya
        yolu gerektirir. SVG'ler geçici klasöre yazılır ve
        uygulama boyunca önbellekte tutulur.

        Kullanım — components.py içinde f-string içinde çağrılır:
            QComboBox::down-arrow {{
                image: url("{Icons.qss_url("chevron_down", C.TEXT_SECONDARY, 12)}");
                width: 12px; height: 12px;
            }}
        """
        import pathlib, tempfile
        key = (name, color, size)
        if key in cls._qss_file_cache:
            cached = cls._qss_file_cache[key]
            if pathlib.Path(cached).exists():
                return cached
            # Dosya silinmişse cache'i temizle ve yeniden oluştur
            del cls._qss_file_cache[key]

        # 1. Önce ui/styles/icons klasörüne bak (projenin kendi SVG ikonları)
        #    Bu klasör varsa temp'e yazmaya gerek yok — kalıcı ve güvenli.
        try:
            from core.paths import BASE_DIR as _BASE_DIR
            static_dir = pathlib.Path(_BASE_DIR) / "ui" / "styles" / "icons"
            static_file = static_dir / f"{name}.svg"
            if static_file.exists():
                url = static_file.as_posix()
                cls._qss_file_cache[key] = url
                return url
        except Exception:
            pass

        # 2. Klasörde yoksa (renk/boyut varyantı gerekiyor) — kalıcı app temp'e yaz
        try:
            from core.paths import TEMP_DIR as _TEMP_DIR
            icon_dir = pathlib.Path(_TEMP_DIR) / "qss_icons"
        except ImportError:
            icon_dir = pathlib.Path(tempfile.gettempdir()) / "repys_qss_icons"

        icon_dir.mkdir(parents=True, exist_ok=True)

        safe_color = color.lstrip("#")
        fname      = f"{name}_{safe_color}_{size}.svg"
        fpath      = icon_dir / fname

        if not fpath.exists():
            paths = _SVG_PATHS.get(name, '<circle cx="12" cy="12" r="8"/>')
            svg   = _build_svg(paths, color, size)
            try:
                fpath.write_text(svg, encoding="utf-8")
            except OSError as e:
                import warnings
                warnings.warn(f"SVG ikon yazılamadı ({fpath}): {e}")
                return fpath.as_posix()

        url = fpath.as_posix()
        cls._qss_file_cache[key] = url
        return url

    @classmethod
    def clear_cache(cls) -> None:
        """Render nbelleini temizler."""
        cls._cache.clear()


# ================================================================
# YARDIMCI  IconRenderer (widget entegrasyonu)
# ================================================================

class IconRenderer:
    """
    Widget'lara pratik ikon atama yardmclar.

    rnekler
    --------
    IconRenderer.set_button_icon(btn, "users", color="#6bd3ff", size=16)
    IconRenderer.set_label_icon(label, "bell", size=24, color="#ffca28")
    """

    @staticmethod
    def set_button_icon(
        btn:   "QPushButton",
        name:  str,
        color: str = Icons.DEFAULT_COLOR,
        size:  int = Icons.DEFAULT_SIZE,
    ) -> None:
        """QPushButton'a ikon ata."""
        icon = Icons.get(name, size=size, color=color)
        btn.setIcon(icon)
        btn.setIconSize(QSize(size, size))

    @staticmethod
    def set_label_icon(
        label: "QLabel",
        name:  str,
        size:  int = Icons.DEFAULT_SIZE,
        color: str = Icons.DEFAULT_COLOR,
    ) -> None:
        """QLabel'a ikon pixmap ata."""
        pm = Icons.pixmap(name, size=size, color=color)
        label.setPixmap(pm)
        label.setFixedSize(size, size)

    @staticmethod
    def status_icon(status: str, size: int = 14) -> QIcon:
        """
        Personel durumuna gre renkli durum ikonu dndrr.

        Parametreler
        ------------
        status : "Aktif" | "Pasif" | "İzinli"
        """
        _map = {
            "Aktif":   ("status_active",  "#22c55e"),
            "Pasif":   ("status_passive", "#ef4444"),
            "İzinli":  ("status_leave",   "#eab308"),
        }
        icon_name, color = _map.get(status, ("info", "#8b8fa3"))
        return Icons.get(icon_name, size=size, color=color)


# ================================================================
# HAZIR RENK SABTLER (DarkTheme ile uyumlu)
# Sk kullanlan ikon renklerini merkezi tutar
# ================================================================

class IconColors:
    """Uygulamada tutarl ikon renkleri iin sabitler."""

    # Sidebar menu item (pasif)
    MENU_ITEM      = "#8b8fa3"
    # Sidebar menu item (aktif / hover)
    MENU_ACTIVE    = "#ffffff"
    # Sidebar grup bal
    GROUP_HEADER   = "#6bd3ff"
    # Primary aksiyon butonlar
    PRIMARY        = "#6bd3ff"
    # Tehlike / silme
    DANGER         = "#f87171"
    # Baar / aktif durum
    SUCCESS        = "#4ade80"
    # Uyar / izin
    WARNING        = "#facc15"
    # Bilgi
    INFO           = "#60a5fa"
    # Pasif / muted
    MUTED          = "#5a5d6e"
    # Genel metin
    TEXT           = "#e0e2ea"
    # Bildirim butonu
    NOTIFICATION   = "#ffca28"
    # Excel butonu
    EXCEL          = "#6ee7b7"
    # PDF butonu
    PDF            = "#fca5a5"
    # Sync butonu
    SYNC           = "#6bd3ff"


# ================================================================
# RENKLI İKON SİSTEMİ — Emoji tarzı badge ikonlar
#
# Kullanım:
#   # Badge tarzı (dolu zemin + beyaz ikon):
#   btn.setIcon(Icons.badge("users", "#22d3ee"))          # cyan badge
#   label.setPixmap(Icons.badge_pixmap("save", "#4ade80")) # yeşil badge
#
#   # Menü öğesi rengi ile otomatik badge:
#   btn.setIcon(Icons.menu_badge("Personel Listesi"))
#
#   # :Özel arka plan + ikon rengi
#   Icons.badge("settings", bg="#1e3a5f", icon_color="#22d3ee")
# ================================================================

# ── Menü öğesi → badge renk tanımları ──────────────────────────
MENU_BADGE_COLORS: dict[str, str] = {
    # PERSONEL  —  cyan ailesi
    "Personel Listesi":              "#22d3ee",
    "Personel Ekle":                 "#06b6d4",
    "Sağlık Takip":                  "#4ade80",
    "Dozimetre Takip":               "#a78bfa",
    "İzin Takip ve FHSZ Yönetim":   "#38bdf8",
    "Diğer Rad. Gör. FHSZ Yön.":    "#7dd3fc",

    #Nöbet 
    "Nöbet Planı":                   "#1c55f1",
    "Nöbetçi Listesi":                "#a325d4",
    "Fazla Mesai":                   "#5371f7",

    # CİHAZ  —  mavi ailesi
    "Cihaz Listesi":                 "#4080e0",
    "Cihaz Ekle":                    "#60a5fa",
    "Teknik Hizmetler":              "#818cf8",

    # RKE  —  mor ailesi
    "RKE Envanter":                  "#a855f7",
    "RKE Muayene":                   "#c084fc",
    "RKE Raporlama":                 "#e879f9",

    # YÖNETİCİ  —  turuncu ailesi
    "Admin Panel":                   "#f59e0b",
    "Doküman Yönetimi":              "#fb923c",

    # AYARLAR  —  gri-mavi ailesi
    "Ayarlar":                       "#64748b",
    "İmportlar":                     "#475569",
}

# ── Grup → badge renk tanımları ────────────────────────────────
GROUP_BADGE_COLORS: dict[str, str] = {
    "PERSONEL":            "#22d3ee",
    "CİHAZ":               "#4080e0",
    "RKE":                 "#a855f7",
    "YÖNETİCİ İŞLEMLERİ": "#f59e0b",
    "AYARLAR":             "#64748b",
    "NÖBET":              "#1c55f1",
}


def _build_badge_svg(paths: str, bg_color: str, icon_color: str, size: int) -> str:
    """
    Emoji tarzı badge SVG oluşturur:
    - Dolu renkli yuvarlak köşeli kare arka plan
    - Üzerinde beyaz/açık renkli ikon
    """
    # Arka plan: yuvarlak köşeli dikdörtgen, %85 büyüklüğünde
    corner = size * 0.22
    pad    = size * 0.10
    s      = size - pad * 2
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg"'
        f' width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
        # Gradient arka plan — tek renkten %70'ine
        f'<defs>'
        f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0%" stop-color="{bg_color}" stop-opacity="1"/>'
        f'<stop offset="100%" stop-color="{bg_color}" stop-opacity="0.70"/>'
        f'</linearGradient>'
        f'</defs>'
        # Arka plan kutusu
        f'<rect x="{pad}" y="{pad}" width="{s}" height="{s}"'
        f' rx="{corner}" ry="{corner}" fill="url(#bg)"/>'
        # İkon — 0 0 24 24 koordinatlarını size'a scale et
        f'<g transform="translate({pad},{pad}) scale({s/24})"'
        f' fill="none"'
        f' stroke="{icon_color}"'
        f' stroke-width="1.9"'
        f' stroke-linecap="round"'
        f' stroke-linejoin="round">'
        f'{paths}'
        f'</g>'
        f'</svg>'
    )


class _BadgeIconCache:
    """Badge ikon önbelleği — aynı parametreler için yeniden render etme."""
    _cache: dict[tuple, QPixmap] = {}

    @classmethod
    def get(cls, name: str, bg_color: str, icon_color: str, size: int) -> QPixmap:
        key = (name, bg_color, icon_color, size)
        if key in cls._cache:
            return cls._cache[key]
        paths = _SVG_PATHS.get(name, '<circle cx="12" cy="12" r="6"/>')
        svg   = _build_badge_svg(paths, bg_color, icon_color, size)
        pm    = _render_svg(svg, size)
        cls._cache[key] = pm
        return pm


# ── Icons sınıfına badge metodları ekle ────────────────────────
def _icons_badge_pixmap(
    cls,
    name:       str,
    bg_color:   str = "#22d3ee",
    icon_color: str = "#ffffff",
    size:       int = 20,
) -> "QPixmap":
    """
    Emoji tarzı badge QPixmap döndürür.

    Parametreler
    ------------
    name       : İkon adı (_SVG_PATHS içindeki)
    bg_color   : Arka plan rengi (badge zemin)
    icon_color : İkon çizgi rengi (genellikle beyaz)
    size       : Piksel boyutu
    """
    return _BadgeIconCache.get(name, bg_color, icon_color, size)


def _icons_badge(
    cls,
    name:       str,
    bg_color:   str = "#22d3ee",
    icon_color: str = "#ffffff",
    size:       int = 20,
) -> "QIcon":
    """Badge tarzı QIcon döndürür."""
    return QIcon(_BadgeIconCache.get(name, bg_color, icon_color, size))


def _icons_menu_badge(
    cls,
    menu_title: str,
    size:       int = 20,
    icon_color: str = "#ffffff",
) -> "QIcon | None":
    """
    Menü başlığından otomatik renkli badge QIcon döndürür.
    MENU_BADGE_COLORS ve MENU_ICON_MAP kullanır.
    """
    icon_key = MENU_ICON_MAP.get(menu_title)
    bg_color = MENU_BADGE_COLORS.get(menu_title)
    if not icon_key or not bg_color:
        return None
    return QIcon(_BadgeIconCache.get(icon_key, bg_color, icon_color, size))


def _icons_group_badge(
    cls,
    group_name: str,
    size:       int = 18,
    icon_color: str = "#ffffff",
) -> "QIcon | None":
    """Grup başlığından otomatik renkli badge QIcon döndürür."""
    icon_key = GROUP_ICON_MAP.get(group_name)
    bg_color = GROUP_BADGE_COLORS.get(group_name)
    if not icon_key or not bg_color:
        return None
    return QIcon(_BadgeIconCache.get(icon_key, bg_color, icon_color, size))


# Metodları Icons sınıfına doğrudan bağla
Icons.badge_pixmap = classmethod(lambda cls, name, bg_color="#22d3ee", icon_color="#ffffff", size=20: _BadgeIconCache.get(name, bg_color, icon_color, size))  # type: ignore
Icons.badge        = classmethod(lambda cls, name, bg_color="#22d3ee", icon_color="#ffffff", size=20: QIcon(_BadgeIconCache.get(name, bg_color, icon_color, size)))  # type: ignore
Icons.menu_badge   = classmethod(lambda cls, menu_title, size=20, icon_color="#ffffff": QIcon(_BadgeIconCache.get(MENU_ICON_MAP[menu_title], MENU_BADGE_COLORS[menu_title], icon_color, size)) if (MENU_ICON_MAP.get(menu_title) and MENU_BADGE_COLORS.get(menu_title)) else None)  # type: ignore
Icons.group_badge  = classmethod(lambda cls, group_name, size=18, icon_color="#ffffff": QIcon(_BadgeIconCache.get(GROUP_ICON_MAP[group_name], GROUP_BADGE_COLORS[group_name], icon_color, size)) if (GROUP_ICON_MAP.get(group_name) and GROUP_BADGE_COLORS.get(group_name)) else None)  # type: ignore


# ================================================================
# YARDIMCI  IconRenderer — badge metodları doğrudan eklendi
# ================================================================

def _ir_set_button_badge(btn, name, bg_color="#22d3ee", icon_color="#ffffff", size=20):
    """QPushButton'a emoji tarzı badge ikon ata."""
    icon = QIcon(_BadgeIconCache.get(name, bg_color, icon_color, size))
    btn.setIcon(icon)
    btn.setIconSize(QSize(size, size))

def _ir_set_menu_badge(btn, menu_title, size=20):
    """Menü butonuna otomatik renkli badge ikon ata."""
    icon_key = MENU_ICON_MAP.get(menu_title)
    bg_color = MENU_BADGE_COLORS.get(menu_title)
    if icon_key and bg_color:
        btn.setIcon(QIcon(_BadgeIconCache.get(icon_key, bg_color, "#ffffff", size)))
        btn.setIconSize(QSize(size, size))

def _ir_set_label_badge(label, name, bg_color="#22d3ee", icon_color="#ffffff", size=20):
    """QLabel'a emoji tarzı badge pixmap ata."""
    pm = _BadgeIconCache.get(name, bg_color, icon_color, size)
    label.setPixmap(pm)
    label.setFixedSize(size, size)

# IconRenderer'a yeni static metodları bağla
IconRenderer.set_button_badge = staticmethod(_ir_set_button_badge)  # type: ignore
IconRenderer.set_menu_badge   = staticmethod(_ir_set_menu_badge)    # type: ignore
IconRenderer.set_label_badge  = staticmethod(_ir_set_label_badge)   # type: ignore

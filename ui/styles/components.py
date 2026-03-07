# ui/styles/components.py  ─  REPYS v3 · Medikal Dark-Blue
# ═══════════════════════════════════════════════════════════════
#
#  Bileşen QSS string'leri.  Tüm renkler aktif tema üzerinden
#  dinamik olarak üretilir — ham hex veya sabit DarkTheme ref
#  kullanılmaz.
#
#  STYLES dict → _DynamicStyles proxy'si üzerinden erişilir.
#  Her STYLES["key"] çağrısı o anki aktif temayı kullanır.
#
#  Kullanım (değişmedi):
#     from ui.styles.components import STYLES as S
#     widget.setStyleSheet(S["btn_action"])   # ← aktif tema
#
#  Tema değişikliği sonrası mevcut widget'ları güncellemek için:
#     from ui.styles.components import refresh_styles
#     refresh_styles()   # STYLES cache'ini sıfırlar
#
# ═══════════════════════════════════════════════════════════════

from typing import Any, cast

from ui.styles.colors import Colors, DarkTheme, get_current_theme
from ui.styles.icons  import Icons


def _build_component_styles(C: Any = None):
    """
    Aktif tema token'larıyla tüm QSS string'lerini üretir.
    Her tema değişikliğinde taze çağrılır — renkleri baked-in etmez.
    C parametresi geriye dönük uyumluluk için korundu (artık kullanılmıyor).
    """
    # Aktif temayı themes.py'den al — f-string'ler C.ATTR olarak erişir
    from core.settings import get as _settings_get
    from ui.styles.themes import get_tokens
    theme_value = _settings_get("theme", "dark")
    theme_name = theme_value if isinstance(theme_value, str) and theme_value else "dark"
    _tokens = get_tokens(theme_name)
    C = cast(Any, type("_C", (), _tokens)())  # dict → attribute erişimine çevir
    class ComponentStyles:

        # ── Sayfa / Çerçeve ──────────────────────────────────────────
        PAGE = f"QWidget {{ background-color: {C.BG_PRIMARY}; }}"

        FILTER_PANEL = f"""
            QFrame {{
                background-color: {C.BG_SECONDARY};
                border: 1px solid {C.BORDER_PRIMARY};
                border-radius: 10px;
            }}
        """

        SEPARATOR = f"""
            QFrame {{
                background-color: {C.BORDER_SECONDARY};
                height: 1px;
            }}
        """

        SPLITTER = f"""
            QSplitter {{ background-color: transparent; }}
            QSplitter::handle {{ background-color: {C.BORDER_SECONDARY}; }}
            QSplitter::handle:hover {{ background-color: {C.BORDER_STRONG}; }}
        """

        # ── Butonlar ─────────────────────────────────────────────────
        #
        #  Temel buton ailesi:
        #    BTN_ACTION    → Birincil eylem (mavi dolgu)
        #    BTN_SECONDARY → Şeffaf arka plan, ince kenarlık
        #    BTN_SUCCESS   → Yeşil çerçeveli, hover'da doldu
        #    BTN_DANGER    → Kırmızı çerçeveli, hover'da doldu
        #    BTN_REFRESH   → Küçük / ikon butonlar
        #    BTN_FILTER    → Toggle filtre butonları
        #
        BTN_ACTION = f"""
            QPushButton {{
                background-color: {C.BTN_PRIMARY_BG};
                color: {C.BTN_PRIMARY_TEXT};
                border: none;
                border-radius: 4px;
                padding: 4px 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{ background-color: {C.BTN_PRIMARY_HOVER}; }}
            QPushButton:pressed {{ opacity: 0.8; }}
            QPushButton:disabled {{
                background-color: {C.BORDER_PRIMARY};
                color: {C.TEXT_MUTED};
            }}
        """

        BTN_SECONDARY = f"""
            QPushButton {{
                background-color: transparent;
                color: {C.TEXT_SECONDARY};
                border: 1px solid {C.BORDER_SECONDARY};
                border-radius: 4px;
                padding: 4px 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {C.BG_ELEVATED};
                color: {C.TEXT_PRIMARY};
                border-color: {C.INPUT_BORDER_FOCUS};
            }}
            QPushButton:disabled {{
                color: {C.TEXT_MUTED};
                border-color: {C.BORDER_PRIMARY};
            }}
        """

        BTN_SUCCESS = f"""
            QPushButton {{
                background-color: transparent;
                color: {C.TEXT_SECONDARY};
                border: 1px solid {C.BORDER_SECONDARY};
                border-radius: 4px;
                padding: 4px 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {C.BTN_SUCCESS_BG};
                color: {C.BTN_SUCCESS_TEXT};
                border-color: {C.BTN_SUCCESS_BORDER};
            }}
        """

        BTN_DANGER = f"""
            QPushButton {{
                background-color: transparent;
                color: {C.TEXT_SECONDARY};
                border: 1px solid {C.BORDER_SECONDARY};
                border-radius: 4px;
                padding: 4px 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {C.BTN_DANGER_BG};
                color: {C.BTN_DANGER_TEXT};
                border-color: {C.BTN_DANGER_BORDER};
            }}
        """

        BTN_REFRESH = f"""
            QPushButton {{
                background-color: transparent;
                color: {C.TEXT_SECONDARY};
                border: 1px solid {C.BORDER_SECONDARY};
                border-radius: 4px;
                padding: 4px 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {C.BG_ELEVATED};
                color: {C.TEXT_PRIMARY};
                border-color: {C.INPUT_BORDER_FOCUS};
            }}
        """

        BTN_FILTER = f"""
            QPushButton {{
                background-color: transparent;
                color: {C.TEXT_SECONDARY};
                border: 1px solid {C.BORDER_SECONDARY};
                border-radius: 4px;
                padding: 4px 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {C.BG_ELEVATED};
                color: {C.TEXT_PRIMARY};
            }}
            QPushButton:checked {{
                background-color: {C.ACCENT_BG};
                color: {C.ACCENT2};
                border-color: {C.ACCENT};
                font-weight: 700;
            }}
        """

        BTN_FILTER_ALL = f"""
            QPushButton {{
                background-color: transparent;
                color: {C.TEXT_SECONDARY};
                border: 1px solid {C.BORDER_STRONG};
                border-radius: 20px;
                padding: 4px 13px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {C.BG_TERTIARY};
                color: {C.TEXT_PRIMARY};
            }}
            QPushButton:checked {{
                background-color: {C.BG_ELEVATED};
                color: {C.TEXT_PRIMARY};
                border-color: {C.BORDER_STRONG};
                font-weight: 600;
            }}
        """

        PHOTO_BTN = f"""
            QPushButton {{
                background-color: {C.ACCENT};
                color: {C.BTN_PRIMARY_TEXT};
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover  {{ background-color: {C.BTN_PRIMARY_HOVER}; }}
            QPushButton:pressed {{ opacity: 0.85; }}
        """

        # ── Input alanları ───────────────────────────────────────────
        INPUT_SEARCH = f"""
            QLineEdit {{
                background-color: {C.INPUT_BG};
                border: 1px solid {C.BORDER_SECONDARY};
                border-radius: 4px;
                padding: 5px 10px 5px 32px;
                min-height: 22px;
                color: {C.TEXT_PRIMARY};
                font-family: {C.MONOSPACE};
            }}
            QLineEdit:focus {{ border-color: {C.INPUT_BORDER_FOCUS}; }}
            QLineEdit::placeholder {{ color: {C.TEXT_MUTED}; }}
        """

        INPUT_FIELD = f"""
            QLineEdit {{
                background-color: {C.INPUT_BG};
                border: 1px solid {C.BORDER_SECONDARY};
                border-radius: 4px;
                padding: 5px 9px;
                min-height: 22px;
                color: {C.TEXT_PRIMARY};
                font-family: {C.MONOSPACE};
            }}
            QLineEdit:focus {{ border-color: {C.INPUT_BORDER_FOCUS}; }}
            QLineEdit:read-only {{
                background-color: {C.BG_SECONDARY};
                color: {C.TEXT_SECONDARY};
            }}
            QLineEdit::placeholder {{ color: {C.TEXT_MUTED}; }}
        """

        INPUT_COMBO = f"""
            QComboBox {{
                background-color: {C.INPUT_BG};
                border: 1px solid {C.BORDER_SECONDARY};
                border-radius: 4px;
                padding: 5px 32px 5px 9px;
                min-height: 22px;
                color: {C.TEXT_PRIMARY};
                font-family: {C.MONOSPACE};
            }}
            QComboBox:focus  {{ border-color: {C.INPUT_BORDER_FOCUS}; }}
            QComboBox:hover  {{ border-color: {C.BORDER_STRONG}; }}
            QComboBox::drop-down {{
                subcontrol-origin:          padding;
                subcontrol-position:        right center;
                width:                      28px;
                border-left:                1px solid {C.BORDER_PRIMARY};
                border-top-right-radius:    3px;
                border-bottom-right-radius: 3px;
                background:                 {C.BG_ELEVATED};
            }}
            QComboBox::drop-down:hover {{ background: {C.ACCENT_BG}; }}
            QComboBox::down-arrow {{
                image:  url("{Icons.qss_url("chevron_down", C.TEXT_SECONDARY, 12)}");
                width:  12px;
                height: 12px;
            }}
            QComboBox::down-arrow:on {{
                image:  "none";
            }}
            QComboBox QAbstractItemView {{
                background-color:           {C.BG_ELEVATED};
                border:                     1px solid {C.BORDER_SECONDARY};
                color:                      {C.TEXT_PRIMARY};
                selection-background-color: {C.ACCENT_BG};
                selection-color:            {C.TEXT_PRIMARY};
                padding:                    4px;
                outline:                    0;
            }}
            QComboBox QAbstractItemView::item {{
                min-height: 26px;
                padding:    3px 8px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {C.ACCENT_BG};
                color:            {C.ACCENT2};
            }}
        """

        INPUT_DATE = f"""
            QDateEdit {{
                background-color: {C.INPUT_BG};
                border: 1px solid {C.BORDER_SECONDARY};
                border-radius: 4px;
                padding: 5px 32px 5px 9px;
                min-height: 22px;
                color: {C.TEXT_PRIMARY};
                font-family: {C.MONOSPACE};
            }}
            QDateEdit:focus  {{ border-color: {C.INPUT_BORDER_FOCUS}; }}
            QDateEdit:hover  {{ border-color: {C.BORDER_STRONG}; }}
            QDateEdit::drop-down {{
                subcontrol-origin:          padding;
                subcontrol-position:        right center;
                width:                      28px;
                border-left:                1px solid {C.BORDER_PRIMARY};
                border-top-right-radius:    3px;
                border-bottom-right-radius: 3px;
                background:                 {C.BG_ELEVATED};
            }}
            QDateEdit::drop-down:hover {{ background: {C.ACCENT_BG}; }}
            QDateEdit::down-arrow {{
                image:  url("{Icons.qss_url("chevron_down", C.TEXT_SECONDARY, 12)}");
                width:  12px;
                height: 12px;
            }}
            QDateEdit::down-arrow:on {{
                image:  "none";
            }}
        """

        INPUT_TEXT = f"""
            QTextEdit {{
                background-color: {C.INPUT_BG};
                border: 1px solid {C.BORDER_SECONDARY};
                border-radius: 4px;
                padding: 5px 9px;
                color: {C.TEXT_PRIMARY};
                font-family: {C.MONOSPACE};
            }}
            QTextEdit:focus {{ border-color: {C.INPUT_BORDER_FOCUS}; }}
        """

        SPIN = f"""
            QSpinBox, QDoubleSpinBox {{
                background-color: {C.INPUT_BG};
                border: 1px solid {C.BORDER_SECONDARY};
                border-radius: 4px;
                padding: 5px 9px;
                min-height: 22px;
                color: {C.TEXT_PRIMARY};
                font-family: {C.MONOSPACE};
            }}
            QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {C.INPUT_BORDER_FOCUS}; }}
            QSpinBox::up-button, QSpinBox::down-button,
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                background: transparent;
                border: none;
                width: 18px;
            }}
        """

        # ── Onay kutusu & Radyo butonu ────────────────────────────────
        #    Global QSS'te de tanımlı — bu stil setStyleSheet() ile
        #    uygulandığında global'i ezer ve tutarlı görünüm sağlar.
        CHECKBOX = f"""
            QCheckBox {{
                color: {C.TEXT_SECONDARY};
                spacing: 7px;
                font-size: 13px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {C.BORDER_STRONG};
                border-radius: 3px;
                background-color: {C.INPUT_BG};
            }}
            QCheckBox::indicator:hover    {{ border-color: {C.ACCENT}; }}
            QCheckBox::indicator:checked  {{
                background-color: {C.ACCENT};
                border-color: {C.ACCENT};
            }}
            QCheckBox::indicator:disabled {{
                background-color: {C.BG_SECONDARY};
                border-color: {C.BORDER_PRIMARY};
            }}
            QCheckBox:disabled {{ color: {C.TEXT_DISABLED}; }}
        """

        RADIOBUTTON = f"""
            QRadioButton {{
                color: {C.TEXT_SECONDARY};
                spacing: 7px;
                font-size: 13px;
                background: transparent;
            }}
            QRadioButton::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {C.BORDER_STRONG};
                border-radius: 8px;
                background-color: {C.INPUT_BG};
            }}
            QRadioButton::indicator:hover   {{ border-color: {C.ACCENT}; }}
            QRadioButton::indicator:checked {{
                background-color: {C.ACCENT};
                border-color: {C.ACCENT};
            }}
            QRadioButton:disabled {{ color: {C.TEXT_DISABLED}; }}
        """

        CALENDAR = f"""
            QCalendarWidget {{
                background-color: {C.BG_SECONDARY};
                color: {C.TEXT_PRIMARY};
                border: 1px solid {C.BORDER_PRIMARY};
            }}
            QCalendarWidget QToolButton {{
                background-color: transparent;
                color: {C.TEXT_PRIMARY};
                border: none;
                padding: 4px 8px;
            }}
            QCalendarWidget QMenu {{
                background-color: {C.BG_SECONDARY};
                color: {C.TEXT_PRIMARY};
                border: 1px solid {C.BORDER_PRIMARY};
            }}
            QCalendarWidget QAbstractItemView {{
                background-color: {C.BG_SECONDARY};
                color: {C.TEXT_SECONDARY};
                selection-background-color: {C.ACCENT_BG};
                selection-color: {C.ACCENT2};
                outline: none;
            }}
        """

        # ── Tablo ─────────────────────────────────────────────────────
        # NOT: QHeaderView::section stilleri global QSS'de tanımlı (theme_template.qss).
        # Manuel override yerine global stillerin kullanılmasına izin verilir.
        TABLE = f"""
            QTableView, QTableWidget {{
                background-color: {C.BG_SECONDARY};
                border: 1px solid {C.BORDER_PRIMARY};
                gridline-color: transparent;
                color: {C.TEXT_PRIMARY};
                selection-background-color: {C.ACCENT_BG};
                selection-color: {C.ACCENT2};
                outline: 0;
            }}
            QTableView::item {{ padding: 4px 10px; color: {C.TEXT_SECONDARY}; }}
            QTableView::item:selected {{
                background-color: {C.ACCENT_BG};
                color: {C.TEXT_PRIMARY};
            }}
            QTableView::item:hover {{ background-color: {C.BG_HOVER}; }}
        """

        # ── GroupBox ──────────────────────────────────────────────────
        GROUP_BOX = f"""
            QGroupBox {{
                background-color: {C.BG_SECONDARY};
                border: 1px solid {C.BORDER_PRIMARY};
                margin-top: 12px;
                padding-top: 8px;
                color: {C.TEXT_PRIMARY};
                font-weight: 600;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
                color: {C.TEXT_PRIMARY};
                font-weight: 600;
            }}
        """

        # ── Sekme ─────────────────────────────────────────────────────
        TAB = f"""
            QTabWidget::pane {{
                background-color: {C.BG_SECONDARY};
                border: 1px solid {C.BORDER_PRIMARY};
            }}
            QTabBar::tab {{
                background-color: transparent;
                color: {C.TEXT_SECONDARY};
                border: none;
                border-bottom: 2px solid transparent;
                padding: 6px 12px;
                font-weight: 500;
            }}
            QTabBar::tab:hover {{ color: {C.TEXT_PRIMARY}; }}
            QTabBar::tab:selected {{
                color: {C.ACCENT2};
                border-bottom-color: {C.INPUT_BORDER_FOCUS};
                font-weight: 700;
            }}
        """

        # ── Kaydırma çubuğu ───────────────────────────────────────────
        SCROLLBAR = f"""
            QScrollBar:vertical {{
                background: transparent; width: 5px; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {C.BORDER_SECONDARY};
                border-radius: 2px; min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{ background: {C.TEXT_MUTED}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar:horizontal {{
                background: transparent; height: 5px; margin: 0;
            }}
            QScrollBar::handle:horizontal {{
                background: {C.BORDER_SECONDARY};
                border-radius: 2px; min-width: 20px;
            }}
            QScrollBar::handle:horizontal:hover {{ background: {C.TEXT_MUTED}; }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
        """

        # ── İlerleme çubuğu ──────────────────────────────────────────
        PROGRESS = f"""
            QProgressBar {{
                background-color: {C.BORDER_SECONDARY};
                border: none;
                border-radius: 1px;
                height: 3px;
                margin: 0px; padding: 0px;
            }}
            QProgressBar::chunk {{
                background-color: {C.INPUT_BORDER_FOCUS};
                border-radius: 1px;
            }}
        """

        # ── Bağlam menüsü ─────────────────────────────────────────────
        CONTEXT_MENU = f"""
            QMenu {{
                background-color: {C.BG_SECONDARY};
                color: {C.TEXT_PRIMARY};
                border: 1px solid {C.BORDER_PRIMARY};
                border-radius: 8px;
                padding: 4px 0;
            }}
            QMenu::item {{ padding: 6px 16px; background: transparent; }}
            QMenu::item:selected {{
                background-color: {C.BG_HOVER};
                color: {C.ACCENT2};
            }}
            QMenu::item:pressed {{ background-color: {C.BG_SELECTED}; }}
            QMenu::separator {{
                height: 1px;
                background-color: {C.BORDER_SECONDARY};
                margin: 4px 0;
            }}
        """

        # ── Etiketler ─────────────────────────────────────────────────
        LABEL_FORM = f"""
            QLabel {{
                color: {C.TEXT_SECONDARY};
                font-size: 11px;
                font-weight: 700;
                background: transparent;
                letter-spacing: 0.04em;
            }}
        """

        LABEL_TITLE = f"""
            QLabel {{
                color: {C.TEXT_PRIMARY};
                font-size: 15px;
                font-weight: 700;
                background: transparent;
            }}
        """

        SECTION_LABEL = f"""
            QLabel {{
                color: {C.TEXT_PRIMARY};
                font-size: 13px;
                font-weight: 700;
                background: transparent;
                letter-spacing: 0.02em;
            }}
        """

        SECTION_TITLE = f"""
            QLabel {{
                color: {C.TEXT_PRIMARY};
                font-size: 14px;
                font-weight: 700;
                background: transparent;
                padding: 6px 0;
            }}
        """

        INFO_LABEL = f"""
            QLabel {{
                color: {C.TEXT_SECONDARY};
                font-size: 12px;
                font-weight: 500;
                background: transparent;
            }}
        """

        FOOTER_LABEL = f"""
            QLabel {{
                color: {C.TEXT_MUTED};
                font-size: 10px;
                font-weight: 400;
                background: transparent;
            }}
        """

        HEADER_NAME = f"""
            QLabel {{
                color: {C.TEXT_PRIMARY};
                font-size: 14px;
                font-weight: 700;
                background: transparent;
                letter-spacing: 0.01em;
            }}
        """

        REQUIRED_LABEL = f"""
            QLabel {{
                color: {C.TEXT_SECONDARY};
                font-size: 11px;
                font-weight: 700;
                background: transparent;
                letter-spacing: 0.04em;
            }}
        """

        MAX_LABEL = f"""
            QLabel {{
                color: {Colors.YELLOW_400};
                font-size: 11px;
                font-style: italic;
                background: transparent;
            }}
        """

        DONEM_LABEL = f"""
            QLabel {{
                color: {C.ACCENT};
                font-size: 13px;
                font-weight: 600;
                background: transparent;
                padding: 4px 8px;
            }}
        """

        # ── İstatistik etiketleri ─────────────────────────────────────
        STAT_LABEL = f"""
            QLabel {{
                color: {C.TEXT_MUTED};
                font-size: 12px;
                font-weight: 500;
                background: transparent;
            }}
        """

        STAT_VALUE = f"""
            QLabel {{
                color: {C.TEXT_PRIMARY};
                font-size: 16px;
                font-weight: 600;
                background: transparent;
            }}
        """

        STAT_RED = f"""
            QLabel {{
                color: {Colors.RED_400};
                font-size: 16px;
                font-weight: 600;
                background: transparent;
            }}
        """

        STAT_GREEN = f"""
            QLabel {{
                color: {Colors.GREEN_400};
                font-size: 16px;
                font-weight: 600;
                background: transparent;
            }}
        """

        STAT_HIGHLIGHT = f"""
            QLabel {{
                color: {C.ACCENT};
                font-size: 16px;
                font-weight: 700;
                background: transparent;
            }}
        """

        VALUE = f"""
            QLabel {{
                color: {C.TEXT_PRIMARY};
                font-size: 13px;
                font-weight: 500;
                background: transparent;
            }}
        """

        # ── Durum badge'leri ──────────────────────────────────────────
        HEADER_DURUM_AKTIF = f"""
            QLabel {{
                background-color: {Colors.GREEN_BG};
                color: {Colors.GREEN_400};
                border: 1px solid rgba(16,185,129,0.30);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.04em;
            }}
        """

        HEADER_DURUM_PASIF = f"""
            QLabel {{
                background-color: {Colors.RED_BG};
                color: {Colors.RED_400};
                border: 1px solid rgba(239,68,68,0.30);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.04em;
            }}
        """

        HEADER_DURUM_IZINLI = f"""
            QLabel {{
                background-color: {Colors.YELLOW_BG};
                color: {Colors.YELLOW_400};
                border: 1px solid rgba(245,158,11,0.30);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.04em;
            }}
        """

        # ── Fotoğraf alanı ────────────────────────────────────────────
        PHOTO_AREA = f"""
            QLabel {{
                background-color: {C.BG_TERTIARY};
                border: 2px dashed {C.BORDER_STRONG};
                border-radius: 8px;
                color: {C.TEXT_MUTED};
                font-size: 12px;
            }}
        """

        # ── Durum rengi yardımcıları ──────────────────────────────────
        @staticmethod
        def get_status_color(status: str) -> tuple:
            """Durum string'ine göre RGBA tuple döndürür (badge arka planı)."""
            _MAP = {
                "Aktif":             (16,  185, 129, 30),
                "Pasif":             (239, 68,  68,  30),
                "İzinli":            (245, 158, 11,  30),
                "Arızalı":           (239, 68,  68,  30),
                "Bakımda":           (245, 158, 11,  30),
                "Kapalı (Çözüldü)": (16,  185, 129, 30),
                "Açık":              (239, 68,  68,  30),
                "İşlemde":           (249, 115, 22,  30),
                "Planlandı":         (245, 158, 11,  30),
                "Tamamlandı":        (16,  185, 129, 30),
                "Onaylandı":         (16,  185, 129, 30),
                "Beklemede":         (245, 158, 11,  30),
                "İptal":             (100, 116, 139, 25),
                "Kalibrasyonda":     (168, 85,  247, 30),
                "Parça Bekliyor":    (251, 191, 36,  30),
                "Dış Serviste":      (168, 85,  247, 30),
            }
            return _MAP.get(status, (78, 104, 136, 25))

        @staticmethod
        def get_status_text_color(status: str) -> str:
            """Durum string'ine göre metin rengi döndürür."""
            _MAP = {
                "Aktif":             Colors.GREEN_500,
                "Pasif":             Colors.RED_400,
                "İzinli":            Colors.YELLOW_500,
                "Arızalı":           Colors.RED_400,
                "Bakımda":           Colors.YELLOW_500,
                "Kapalı (Çözüldü)":  Colors.GREEN_500,
                "Açık":              Colors.RED_400,
                "İşlemde":           Colors.ORANGE_400,
                "Planlandı":         Colors.YELLOW_500,
                "Tamamlandı":        Colors.GREEN_500,
                "Onaylandı":         Colors.GREEN_500,
                "Beklemede":         Colors.YELLOW_500,
                "İptal":             C.TEXT_MUTED,
                "Kalibrasyonda":     Colors.PURPLE_500,
                "Parça Bekliyor":    Colors.YELLOW_400,
                "Dış Serviste":      Colors.PURPLE_500,
            }
            return _MAP.get(status, C.TEXT_SECONDARY)


    # ═══════════════════════════════════════════════════════════════
    #  STYLES dict  ─  Merkezi erişim noktası
    #
    #  ── Canonical key'ler ──────────────────────────────────────────
    #  Her bileşen stili tek bir canonical key ile tanımlanmıştır.
    #  Kullanımda her zaman canonical key'i tercih edin.
    #
    #  ── Geriye dönük alias key'ler ─────────────────────────────────
    #  Mevcut sayfa kodu değiştirilmeden çalışmaya devam etsin diye
    #  eski key adları korunmuştur. Yeni kodda kullanmayın.
    #
    return ComponentStyles


# ══════════════════════════════════════════════════════════════════════════════
#  Dinamik STYLES proxy — tema değişikliğinde taze renkler
# ══════════════════════════════════════════════════════════════════════════════

class _DynamicStyles:
    """
    STYLES["key"] erişiminde aktif temayı kullanır.
    Tema değişikliği sonrası ek işlem gerekmez — otomatik güncellenir.
    """
    _cache: dict = {}
    _cached_theme = None

    def _get_cache(self) -> dict:
        current_theme = get_current_theme()
        if current_theme is not self.__class__._cached_theme:
            cs = _build_component_styles(current_theme)
            self.__class__._cached_theme = current_theme
            self.__class__._cache = {
                # Sayfa
                "page": cs.PAGE, "filter_panel": cs.FILTER_PANEL,
                "separator": cs.SEPARATOR, "splitter": cs.SPLITTER,
                # Butonlar
                "btn_action": cs.BTN_ACTION, "btn_secondary": cs.BTN_SECONDARY,
                "btn_success": cs.BTN_SUCCESS, "btn_danger": cs.BTN_DANGER,
                "btn_refresh": cs.BTN_REFRESH, "btn_filter": cs.BTN_FILTER,
                "btn_filter_all": cs.BTN_FILTER_ALL, "photo_btn": cs.PHOTO_BTN,
                # Input
                "input_search": cs.INPUT_SEARCH, "input_field": cs.INPUT_FIELD,
                "input_combo": cs.INPUT_COMBO, "input_date": cs.INPUT_DATE,
                "input_text": cs.INPUT_TEXT, "spin": cs.SPIN, "double_spin": cs.SPIN,
                "checkbox": cs.CHECKBOX, "radiobutton": cs.RADIOBUTTON,
                "calendar": cs.CALENDAR,
                # Tablo vb.
                "table": cs.TABLE, "group_box": cs.GROUP_BOX, "tab": cs.TAB,
                "scrollbar": cs.SCROLLBAR, "progress": cs.PROGRESS,
                "context_menu": cs.CONTEXT_MENU,
                # Etiketler
                "label_form": cs.LABEL_FORM, "label_title": cs.LABEL_TITLE,
                "section_label": cs.SECTION_LABEL, "section_title": cs.SECTION_TITLE,
                "info_label": cs.INFO_LABEL, "footer_label": cs.FOOTER_LABEL,
                "header_name": cs.HEADER_NAME, "required_label": cs.REQUIRED_LABEL,
                "max_label": cs.MAX_LABEL, "donem_label": cs.DONEM_LABEL,
                # İstatistik
                "stat_label": cs.STAT_LABEL, "stat_value": cs.STAT_VALUE,
                "stat_red": cs.STAT_RED, "stat_green": cs.STAT_GREEN,
                "stat_highlight": cs.STAT_HIGHLIGHT, "value": cs.VALUE,
                # Durum
                "header_durum_aktif": cs.HEADER_DURUM_AKTIF,
                "header_durum_pasif": cs.HEADER_DURUM_PASIF,
                "header_durum_izinli": cs.HEADER_DURUM_IZINLI,
                "photo_area": cs.PHOTO_AREA, "file_btn": cs.PHOTO_BTN,
                # Geriye dönük alias
                "save_btn": cs.BTN_SUCCESS, "cancel_btn": cs.BTN_SECONDARY,
                "edit_btn": cs.BTN_SECONDARY, "danger_btn": cs.BTN_DANGER,
                "report_btn": cs.BTN_SECONDARY, "pdf_btn": cs.BTN_SECONDARY,
                "back_btn": cs.BTN_SECONDARY, "calc_btn": cs.BTN_SECONDARY,
                "action_btn": cs.BTN_ACTION, "refresh_btn": cs.BTN_REFRESH,
                "close_btn": cs.BTN_DANGER, "excel_btn": cs.BTN_SUCCESS,
                "btn_close": cs.BTN_DANGER, "btn_excel": cs.BTN_SUCCESS,
                "input": cs.INPUT_FIELD, "search": cs.INPUT_SEARCH,
                "combo": cs.INPUT_COMBO, "combo_filter": cs.INPUT_COMBO,
                "date": cs.INPUT_DATE, "group": cs.GROUP_BOX,
                "label": cs.LABEL_FORM, "scroll": cs.SCROLLBAR,
            }
        return self.__class__._cache

    def __getitem__(self, key: str) -> str:
        return self._get_cache()[key]

    def get(self, key: str, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def invalidate(self):
        """Cache'i sıfırla — ThemeManager.set_theme() çağırır."""
        self.__class__._cache = {}
        self.__class__._cached_theme = None


STYLES: "_DynamicStyles" = _DynamicStyles()


def refresh_styles() -> None:
    """
    Tema değişikliği sonrası STYLES cache'ini sıfırla.
    ThemeManager.set_theme() içinden çağrılmalıdır.
    """
    STYLES.invalidate()

# Geriye dönük uyumluluk
ComponentStyles = _build_component_styles(DarkTheme)
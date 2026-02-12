# ui/styles/components.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Bileşen Stilleri (QSS) — Merkezi Yönetim
#
# Tüm sayfa ve form bileşenleri bu stillerden kullanır.
# Inline QSS yerine merkezi tanımlar.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from ui.styles.colors import DarkTheme as Colors


class ComponentStyles:
    """Tüm UI bileşenlerinin stillerini sağlar."""

    # ══════════════════════════════════════════
    # PANEL / FRAME STİLLERİ
    # ══════════════════════════════════════════

    FILTER_PANEL = f"""
        QFrame {{
            background-color: rgba(30, 32, 44, 0.85);
            border: 1px solid {Colors.BORDER_PRIMARY};
            border-radius: 10px;
        }}
    """

    # ══════════════════════════════════════════
    # BUTTON STİLLERİ
    # ══════════════════════════════════════════

    BTN_FILTER = f"""
        QPushButton {{
            background-color: {Colors.BTN_SECONDARY_BG};
            color: {Colors.BTN_SECONDARY_TEXT};
            border: 1px solid {Colors.BTN_SECONDARY_BORDER};
            border-radius: 6px;
            padding: 6px 14px;
            font-size: 12px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: rgba(255, 255, 255, 0.10);
            color: {Colors.TEXT_SECONDARY};
        }}
        QPushButton:checked {{
            background-color: rgba(29, 117, 254, 0.35);
            color: {Colors.TEXT_PRIMARY};
            border: 1px solid {Colors.BTN_PRIMARY_BORDER};
        }}
    """

    BTN_FILTER_ALL = f"""
        QPushButton {{
            background-color: {Colors.BTN_SECONDARY_BG};
            color: {Colors.BTN_SECONDARY_TEXT};
            border: 1px solid {Colors.BTN_SECONDARY_BORDER};
            border-radius: 6px;
            padding: 6px 14px;
            font-size: 12px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: rgba(255, 255, 255, 0.10);
            color: {Colors.TEXT_SECONDARY};
        }}
        QPushButton:checked {{
            background-color: rgba(255, 255, 255, 0.12);
            color: {Colors.TEXT_PRIMARY};
            border: 1px solid rgba(255, 255, 255, 0.15);
        }}
    """

    BTN_ACTION = f"""
        QPushButton {{
            background-color: {Colors.BTN_PRIMARY_BG};
            color: {Colors.BTN_PRIMARY_TEXT};
            border: 1px solid {Colors.BTN_PRIMARY_BORDER};
            border-radius: 6px;
            padding: 7px 16px;
            font-size: 12px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: {Colors.BTN_PRIMARY_HOVER};
            color: {Colors.TEXT_PRIMARY};
        }}
    """

    BTN_REFRESH = f"""
        QPushButton {{
            background-color: rgba(255, 255, 255, 0.05);
            color: {Colors.BTN_SECONDARY_TEXT};
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 6px;
            padding: 7px 12px;
            font-size: 12px;
        }}
        QPushButton:hover {{
            background-color: rgba(255, 255, 255, 0.10);
            color: {Colors.TEXT_SECONDARY};
        }}
    """

    BTN_CLOSE = f"""
        QPushButton {{
            background-color: {Colors.BTN_DANGER_BG};
            color: {Colors.BTN_DANGER_TEXT};
            border: 1px solid {Colors.BTN_DANGER_BORDER};
            border-radius: 6px;
            font-size: 14px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {Colors.BTN_DANGER_HOVER};
            color: {Colors.TEXT_PRIMARY};
        }}
    """

    BTN_EXCEL = f"""
        QPushButton {{
            background-color: {Colors.BTN_SUCCESS_BG};
            color: {Colors.BTN_SUCCESS_TEXT};
            border: 1px solid {Colors.BTN_SUCCESS_BORDER};
            border-radius: 6px;
            padding: 6px 14px;
            font-size: 12px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: {Colors.BTN_SUCCESS_HOVER};
            color: {Colors.TEXT_PRIMARY};
        }}
    """

    # ══════════════════════════════════════════
    # INPUT STİLLERİ (QLineEdit, QComboBox)
    # ══════════════════════════════════════════

    INPUT_SEARCH = f"""
        QLineEdit {{
            background-color: #1e202c;
            border: 1px solid {Colors.INPUT_BORDER};
            border-bottom: 2px solid #9dcbe3;
            border-radius: 8px;
            padding: 7px 12px;
            font-size: 13px;
            color: {Colors.TEXT_PRIMARY};
        }}
        QLineEdit:focus {{
            border: 1px solid rgba(29, 117, 254, 0.5);
            border-bottom: 2px solid {Colors.INPUT_BORDER_FOCUS};
        }}
        QLineEdit::placeholder {{
            color: {Colors.TEXT_MUTED};
        }}
    """

    INPUT_COMBO = f"""
        QComboBox {{
            background-color: #1e202c;
            border: 1px solid {Colors.INPUT_BORDER};
            border-bottom: 2px solid #9dcbe3;
            border-radius: 6px;
            padding: 5px 10px;
            font-size: 12px;
            color: {Colors.TEXT_PRIMARY};
            min-height: 22px;
        }}
        QComboBox:focus {{
            border-bottom: 2px solid {Colors.INPUT_BORDER_FOCUS};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        QComboBox QAbstractItemView {{
            background-color: #1e202c;
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: {Colors.TEXT_SECONDARY};
            selection-background-color: rgba(29, 117, 254, 0.3);
            selection-color: {Colors.TEXT_PRIMARY};
        }}
    """

    # ══════════════════════════════════════════
    # TABLO STİLLERİ
    # ══════════════════════════════════════════

    TABLE = f"""
        QTableView {{
            background-color: rgba(30, 32, 44, 0.7);
            alternate-background-color: rgba(255, 255, 255, 0.02);
            border: 1px solid {Colors.BORDER_PRIMARY};
            border-radius: 8px;
            gridline-color: rgba(255, 255, 255, 0.04);
            selection-background-color: {Colors.BG_SELECTED};
            selection-color: {Colors.TEXT_PRIMARY};
            color: {Colors.TEXT_SECONDARY};
            font-size: 13px;
        }}
        QTableView::item {{
            padding: 6px 8px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.02);
        }}
        QTableView::item:selected {{
            background-color: {Colors.BG_SELECTED};
            color: {Colors.TEXT_PRIMARY};
        }}
        QTableView::item:hover:!selected {{
            background-color: {Colors.BG_HOVER};
        }}
        QHeaderView::section {{
            background-color: rgba(255, 255, 255, 0.05);
            color: {Colors.TEXT_MUTED};
            font-weight: 600;
            font-size: 12px;
            padding: 8px;
            border: none;
            border-bottom: 1px solid rgba(29, 117, 254, 0.3);
            border-right: 1px solid rgba(255, 255, 255, 0.03);
        }}
    """

    # ══════════════════════════════════════════
    # LABEL / TEKSİT STİLLERİ
    # ══════════════════════════════════════════

    LABEL_FOOTER = f"color: {Colors.TEXT_DISABLED}; font-size: 12px; background: transparent;"

    LABEL_SECTION = f"color: {Colors.TEXT_DISABLED}; font-size: 11px; font-weight: bold; background: transparent;"

    # ══════════════════════════════════════════
    # MENU / CONTEXT STİLLERİ
    # ══════════════════════════════════════════

    CONTEXT_MENU = f"""
        QMenu {{
            background-color: #1e202c;
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 8px;
            padding: 4px;
            color: {Colors.TEXT_SECONDARY};
            font-size: 13px;
        }}
        QMenu::item {{
            padding: 8px 24px 8px 12px;
            border-radius: 4px;
            margin: 2px;
        }}
        QMenu::item:selected {{
            background-color: rgba(29, 117, 254, 0.35);
            color: {Colors.TEXT_PRIMARY};
        }}
        QMenu::separator {{
            height: 1px;
            background: rgba(255, 255, 255, 0.08);
            margin: 4px 8px;
        }}
    """

    # ══════════════════════════════════════════
    # PROGRESS BAR
    # ══════════════════════════════════════════

    PROGRESS_BAR = f"""
        QProgressBar {{
            background-color: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 4px;
            color: {Colors.TEXT_MUTED};
            font-size: 11px;
        }}
        QProgressBar::chunk {{
            background-color: rgba(29, 117, 254, 0.6);
            border-radius: 3px;
        }}
    """

    # ══════════════════════════════════════════
    # SAYFA STİLLERİ (Personel Detay, Ekle vb.)
    # ══════════════════════════════════════════

    PAGE = f"""
        QWidget {{
            background-color: {Colors.BG_PRIMARY};
        }}
    """

    HEADER_NAME = f"""
        color: {Colors.TEXT_PRIMARY};
        font-size: 18px;
        font-weight: 600;
        background: transparent;
    """

    SAVE_BTN = f"""
        QPushButton {{
            background-color: {Colors.BTN_SUCCESS_BG};
            color: {Colors.BTN_SUCCESS_TEXT};
            border: 1px solid {Colors.BTN_SUCCESS_BORDER};
            border-radius: 6px;
            padding: 7px 16px;
            font-size: 12px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: {Colors.BTN_SUCCESS_HOVER};
            color: {Colors.TEXT_PRIMARY};
        }}
        QPushButton:pressed {{
            background-color: rgba(74, 222, 128, 0.4);
        }}
    """

    EDIT_BTN = f"""
        QPushButton {{
            background-color: {Colors.BTN_PRIMARY_BG};
            color: {Colors.BTN_PRIMARY_TEXT};
            border: 1px solid {Colors.BTN_PRIMARY_BORDER};
            border-radius: 6px;
            padding: 7px 16px;
            font-size: 12px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: {Colors.BTN_PRIMARY_HOVER};
            color: {Colors.TEXT_PRIMARY};
        }}
        QPushButton:pressed {{
            background-color: rgba(29, 117, 254, 0.6);
        }}
    """

    CANCEL_BTN = f"""
        QPushButton {{
            background-color: rgba(255, 255, 255, 0.05);
            color: {Colors.TEXT_SECONDARY};
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 6px;
            padding: 7px 16px;
            font-size: 12px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: rgba(255, 255, 255, 0.10);
            color: {Colors.TEXT_PRIMARY};
        }}
        QPushButton:pressed {{
            background-color: rgba(255, 255, 255, 0.15);
        }}
    """

    DANGER_BTN = f"""
        QPushButton {{
            background-color: {Colors.BTN_DANGER_BG};
            color: {Colors.BTN_DANGER_TEXT};
            border: 1px solid {Colors.BTN_DANGER_BORDER};
            border-radius: 6px;
            padding: 7px 16px;
            font-size: 12px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: {Colors.BTN_DANGER_HOVER};
            color: {Colors.TEXT_PRIMARY};
        }}
        QPushButton:pressed {{
            background-color: rgba(248, 113, 113, 0.6);
        }}
    """

    TAB = f"""
        QTabWidget {{
            background-color: transparent;
            border: none;
        }}
        QTabWidget::pane {{
            border: none;
            background-color: transparent;
        }}
        QTabBar {{
            background-color: transparent;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }}
        QTabBar::tab {{
            background-color: transparent;
            color: {Colors.TEXT_SECONDARY};
            padding: 8px 24px;
            border-bottom: 2px solid transparent;
            font-size: 12px;
            font-weight: 600;
        }}
        QTabBar::tab:hover {{
            color: {Colors.TEXT_PRIMARY};
        }}
        QTabBar::tab:selected {{
            color: {Colors.TEXT_PRIMARY};
            border-bottom: 2px solid rgba(29, 117, 254, 0.8);
        }}
    """

    SCROLL = f"""
        QScrollArea {{
            background-color: transparent;
            border: none;
        }}
        QScrollBar:vertical {{
            background-color: transparent;
            width: 8px;
            border: none;
        }}
        QScrollBar::handle:vertical {{
            background-color: rgba(255, 255, 255, 0.2);
            border-radius: 4px;
            min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: rgba(255, 255, 255, 0.3);
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            border: none;
            background: none;
        }}
    """

    GROUP = f"""
        QGroupBox {{
            color: {Colors.TEXT_SECONDARY};
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding-top: 16px;
            padding-left: 12px;
            padding-right: 12px;
            font-size: 12px;
            font-weight: 600;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 2px 6px;
            color: {Colors.TEXT_PRIMARY};
        }}
    """

    PHOTO_AREA = f"""
        background-color: rgba(255, 255, 255, 0.03);
        border: 2px dashed rgba(255, 255, 255, 0.15);
        border-radius: 8px;
        color: {Colors.TEXT_MUTED};
        font-size: 12px;
    """

    PHOTO_BTN = f"""
        QPushButton {{
            background-color: {Colors.BTN_PRIMARY_BG};
            color: {Colors.BTN_PRIMARY_TEXT};
            border: 1px solid {Colors.BTN_PRIMARY_BORDER};
            border-radius: 6px;
            padding: 6px 14px;
            font-size: 12px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: {Colors.BTN_PRIMARY_HOVER};
            color: {Colors.TEXT_PRIMARY};
        }}
        QPushButton:pressed {{
            background-color: rgba(29, 117, 254, 0.6);
        }}
    """

    # ══════════════════════════════════════════
    # FORM ELEMENTLERI
    # ══════════════════════════════════════════

    LABEL = f"""
        color: {Colors.TEXT_SECONDARY};
        font-size: 12px;
        font-weight: 600;
        background: transparent;
    """

    VALUE = f"""
        color: {Colors.TEXT_PRIMARY};
        font-size: 13px;
        background: transparent;
    """

    REQUIRED_LABEL = f"""
        color: {Colors.TEXT_PRIMARY};
        font-size: 12px;
        font-weight: 600;
        background: transparent;
    """

    INPUT = f"""
        QLineEdit {{
            background-color: rgba(255, 255, 255, 0.03);
            border: 1px solid {Colors.INPUT_BORDER};
            border-radius: 6px;
            padding: 7px 10px;
            font-size: 12px;
            color: {Colors.TEXT_PRIMARY};
        }}
        QLineEdit:focus {{
            border: 1px solid {Colors.INPUT_BORDER_FOCUS};
            background-color: rgba(255, 255, 255, 0.05);
        }}
        QLineEdit::placeholder {{
            color: {Colors.TEXT_MUTED};
        }}
    """

    DATE = f"""
        QDateEdit {{
            background-color: rgba(255, 255, 255, 0.03);
            border: 1px solid {Colors.INPUT_BORDER};
            border-radius: 6px;
            padding: 7px 10px;
            font-size: 12px;
            color: {Colors.TEXT_PRIMARY};
        }}
        QDateEdit:focus {{
            border: 1px solid {Colors.INPUT_BORDER_FOCUS};
            background-color: rgba(255, 255, 255, 0.05);
        }}
        QDateEdit::down-arrow {{
            image: none;
            width: 0px;
        }}
    """

    COMBO_FILTER = f"""
        QComboBox {{
            background-color: rgba(255, 255, 255, 0.03);
            border: 1px solid {Colors.INPUT_BORDER};
            border-radius: 6px;
            padding: 5px 8px;
            font-size: 11px;
            color: {Colors.TEXT_SECONDARY};
            min-height: 20px;
        }}
        QComboBox:focus {{
            border: 1px solid {Colors.INPUT_BORDER_FOCUS};
            background-color: rgba(255, 255, 255, 0.05);
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QComboBox QAbstractItemView {{
            background-color: #1e202c;
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: {Colors.TEXT_SECONDARY};
            selection-background-color: rgba(29, 117, 254, 0.3);
            selection-color: {Colors.TEXT_PRIMARY};
        }}
    """

    FILE_BTN = f"""
        QPushButton {{
            background-color: rgba(255, 255, 255, 0.08);
            color: {Colors.TEXT_SECONDARY};
            border: 1px dashed rgba(255, 255, 255, 0.2);
            border-radius: 6px;
            padding: 6px 12px;
            font-size: 11px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: rgba(255, 255, 255, 0.12);
            color: {Colors.TEXT_PRIMARY};
        }}
        QPushButton:pressed {{
            background-color: rgba(255, 255, 255, 0.15);
        }}
    """

    SEPARATOR = f"""
        background-color: rgba(255, 255, 255, 0.08);
    """

    STAT_LABEL = f"""
        color: {Colors.TEXT_MUTED};
        font-size: 11px;
        background: transparent;
    """

    STAT_VALUE = f"""
        color: {Colors.TEXT_PRIMARY};
        font-size: 14px;
        font-weight: 600;
        background: transparent;
    """

    STAT_HIGHLIGHT = f"""
        color: {Colors.TEXT_PRIMARY};
        font-size: 16px;
        font-weight: 700;
        background: rgba(29, 117, 254, 0.12);
        padding: 6px 10px;
        border-radius: 6px;
    """

    SPIN = f"""
        QSpinBox, QDoubleSpinBox {{
            background-color: rgba(255, 255, 255, 0.03);
            border: 1px solid {Colors.INPUT_BORDER};
            border-radius: 6px;
            padding: 4px 8px;
            color: {Colors.TEXT_PRIMARY};
            min-height: 26px;
        }}
        QSpinBox::up-button, QSpinBox::down-button {{
            width: 18px;
        }}
    """

    CALC_BTN = f"""
        QPushButton {{
            background-color: rgba(29, 117, 254, 0.3);
            color: {Colors.TEXT_PRIMARY};
            border: 1px solid rgba(29, 117, 254, 0.6);
            border-radius: 6px;
            padding: 7px 14px;
            font-size: 12px;
            font-weight: 700;
        }}
        QPushButton:hover {{
            background-color: rgba(29, 117, 254, 0.4);
        }}
    """

    STAT_RED = f"""
        color: #f87171;
        font-size: 14px;
        font-weight: 600;
        background: transparent;
    """

    STAT_GREEN = f"""
        color: #4ade80;
        font-size: 14px;
        font-weight: 600;
        background: transparent;
    """

    SECTION_TITLE = f"""
        color: {Colors.TEXT_PRIMARY};
        font-size: 13px;
        font-weight: 700;
        background: transparent;
    """

    MAX_LABEL = f"""
        color: {Colors.TEXT_SECONDARY};
        font-size: 12px;
        font-weight: 600;
        background: transparent;
    """
    BACK_BTN = f"""
        QPushButton {{
            background-color: rgba(255, 255, 255, 0.05);
            color: {Colors.TEXT_SECONDARY};
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 6px;
            padding: 7px 14px;
            font-size: 12px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: rgba(255, 255, 255, 0.10);
            color: {Colors.TEXT_PRIMARY};
        }}
        QPushButton:pressed {{
            background-color: rgba(255, 255, 255, 0.15);
        }}
    """

    SPLITTER = f"""
        QSplitter::handle {{
            background-color: rgba(255, 255, 255, 0.08);
        }}
        QSplitter::handle:hover {{
            background-color: rgba(255, 255, 255, 0.12);
        }}
    """

    DONEM_LABEL = f"""
        color: {Colors.TEXT_PRIMARY};
        font-size: 13px;
        font-weight: 600;
        background: transparent;
    """

    HEADER_DURUM_AKTIF = f"""
        color: #4ade80;
        font-size: 13px;
        font-weight: 600;
        background: rgba(74, 222, 128, 0.15);
        padding: 2px 8px;
        border-radius: 4px;
    """

    HEADER_DURUM_PASIF = f"""
        color: #f87171;
        font-size: 13px;
        font-weight: 600;
        background: rgba(248, 113, 113, 0.15);
        padding: 2px 8px;
        border-radius: 4px;
    """

    HEADER_DURUM_IZINLI = f"""
        color: #facc15;
        font-size: 13px;
        font-weight: 600;
        background: rgba(250, 204, 21, 0.15);
        padding: 2px 8px;
        border-radius: 4px;
    """

    REPORT_BTN = f"""
        QPushButton {{
            background-color: rgba(29, 117, 254, 0.25);
            color: {Colors.TEXT_PRIMARY};
            border: 1px solid rgba(29, 117, 254, 0.5);
            border-radius: 6px;
            padding: 7px 16px;
            font-size: 12px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: rgba(29, 117, 254, 0.35);
            color: {Colors.TEXT_PRIMARY};
        }}
        QPushButton:pressed {{
            background-color: rgba(29, 117, 254, 0.5);
        }}
    """

    INFO_LABEL = f"""
        color: {Colors.TEXT_MUTED};
        font-size: 11px;
        background: transparent;
    """

    PDF_BTN = f"""
        QPushButton {{
            background-color: rgba(239, 68, 68, 0.25);
            color: #fca5a5;
            border: 1px solid rgba(239, 68, 68, 0.5);
            border-radius: 6px;
            padding: 6px 14px;
            font-size: 12px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: rgba(239, 68, 68, 0.35);
            color: #ffffff;
        }}
        QPushButton:pressed {{
            background-color: rgba(239, 68, 68, 0.5);
        }}
    """

    # ══════════════════════════════════════════
    # DURUM HÜCRE RENKLERİ (QColor, değil QSS)
    # ══════════════════════════════════════════

    @staticmethod
    def get_status_color(status: str):
        """
        Durum adına göre renk döner (QColor tuple).
        
        Args:
            status: "Aktif", "Pasif", "İzinli" vb.
        
        Returns:
            (R, G, B, Alpha) tuple (QColor uyumlu)
        """
        status_colors = {
            "Aktif": Colors.STATE_ACTIVE,      # Yeşil
            "Pasif": Colors.STATE_PASSIVE,     # Kırmızı
            "İzinli": Colors.STATE_LEAVE,      # Sarı
        }
        return status_colors.get(status, (100, 100, 100, 40))

    @staticmethod
    def get_status_text_color(status: str):
        """
        Durum adına göre metin rengi döner (hex string).
        """
        status_text_colors = {
            "Aktif": "#4ade80",      # Yeşil
            "Pasif": "#f87171",      # Kırmızı
            "İzinli": "#facc15",     # Sarı
        }
        return status_text_colors.get(status, "#8b8fa3")


# ════════════════════════════════════════════════════════════════
# KOLAYLIK: Tüm stilleri dict olarak dönen helper
# ════════════════════════════════════════════════════════════════

STYLES = {
    "page": ComponentStyles.PAGE,
    "header_name": ComponentStyles.HEADER_NAME,
    "save_btn": ComponentStyles.SAVE_BTN,
    "edit_btn": ComponentStyles.EDIT_BTN,
    "cancel_btn": ComponentStyles.CANCEL_BTN,
    "danger_btn": ComponentStyles.DANGER_BTN,
    "tab": ComponentStyles.TAB,
    "scroll": ComponentStyles.SCROLL,
    "group": ComponentStyles.GROUP,
    "photo_area": ComponentStyles.PHOTO_AREA,
    "photo_btn": ComponentStyles.PHOTO_BTN,
    "label": ComponentStyles.LABEL,
    "value": ComponentStyles.VALUE,
    "required_label": ComponentStyles.REQUIRED_LABEL,
    "input": ComponentStyles.INPUT,
    "date": ComponentStyles.DATE,
    "combo_filter": ComponentStyles.COMBO_FILTER,
    "file_btn": ComponentStyles.FILE_BTN,
    "separator": ComponentStyles.SEPARATOR,
    "stat_label": ComponentStyles.STAT_LABEL,
    "stat_value": ComponentStyles.STAT_VALUE,
    "stat_highlight": ComponentStyles.STAT_HIGHLIGHT,
    "spin": ComponentStyles.SPIN,
    "calc_btn": ComponentStyles.CALC_BTN,
    "stat_red": ComponentStyles.STAT_RED,
    "stat_green": ComponentStyles.STAT_GREEN,
    "section_title": ComponentStyles.SECTION_TITLE,
    "max_label": ComponentStyles.MAX_LABEL,
    "back_btn": ComponentStyles.BACK_BTN,
    "splitter": ComponentStyles.SPLITTER,
    "donem_label": ComponentStyles.DONEM_LABEL,
    "header_durum_aktif": ComponentStyles.HEADER_DURUM_AKTIF,
    "header_durum_pasif": ComponentStyles.HEADER_DURUM_PASIF,
    "header_durum_izinli": ComponentStyles.HEADER_DURUM_IZINLI,
    "report_btn": ComponentStyles.REPORT_BTN,
    "info_label": ComponentStyles.INFO_LABEL,
    "pdf_btn": ComponentStyles.PDF_BTN,
    "filter_panel": ComponentStyles.FILTER_PANEL,
    "filter_btn": ComponentStyles.BTN_FILTER,
    "filter_btn_all": ComponentStyles.BTN_FILTER_ALL,
    "action_btn": ComponentStyles.BTN_ACTION,
    "refresh_btn": ComponentStyles.BTN_REFRESH,
    "close_btn": ComponentStyles.BTN_CLOSE,
    "excel_btn": ComponentStyles.BTN_EXCEL,
    "search": ComponentStyles.INPUT_SEARCH,
    "combo": ComponentStyles.INPUT_COMBO,
    "table": ComponentStyles.TABLE,
    "footer_label": ComponentStyles.LABEL_FOOTER,
    "section_label": ComponentStyles.LABEL_SECTION,
    "context_menu": ComponentStyles.CONTEXT_MENU,
    "progress": ComponentStyles.PROGRESS_BAR,
}

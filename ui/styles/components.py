# ui/styles/components.py  ─  REPYS v3 · Medikal Dark-Blue
from ui.styles.colors import DarkTheme as C


class ComponentStyles:

    PAGE = f"QWidget {{ background-color: {C.BG_PRIMARY}; }}"

    FILTER_PANEL = f"""
        QFrame {{
            background-color: {C.BG_SECONDARY};
            border: 1px solid {C.BORDER_PRIMARY};
            border-radius: 10px;
        }}
    """

    # ── Butonlar ─────────────────────────────────────────────────
    BTN_ACTION = f"""
        QPushButton {{
            background-color: {C.BTN_PRIMARY_BG};
            color: {C.BTN_PRIMARY_TEXT};
            border: none;
            border-radius: 7px;
            padding: 6px 16px;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.02em;
        }}
        QPushButton:hover  {{ background-color: {C.BTN_PRIMARY_HOVER}; }}
        QPushButton:pressed {{ background-color: #0090b0; }}
        QPushButton:disabled {{
            background-color: rgba(0,180,216,0.20);
            color: rgba(6,13,26,0.5);
        }}
    """

    BTN_REFRESH = f"""
        QPushButton {{
            background-color: {C.BTN_SECONDARY_BG};
            color: {C.TEXT_SECONDARY};
            border: 1px solid {C.BORDER_STRONG};
            border-radius: 7px;
            padding: 6px 12px;
            font-size: 12px;
        }}
        QPushButton:hover  {{
            background-color: {C.BG_TERTIARY};
            color: {C.TEXT_PRIMARY};
            border-color: {C.ACCENT};
        }}
        QPushButton:pressed {{ background-color: {C.BG_ELEVATED}; }}
    """

    BTN_FILTER = f"""
        QPushButton {{
            background-color: transparent;
            color: {C.TEXT_SECONDARY};
            border: 1px solid {C.BORDER_STRONG};
            border-radius: 20px;
            padding: 4px 13px;
            font-size: 12px;
            font-weight: 500;
        }}
        QPushButton:hover  {{
            background-color: {C.BG_TERTIARY};
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
        QPushButton:hover  {{
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

    BTN_CLOSE = f"""
        QPushButton {{
            background-color: {C.BTN_DANGER_BG};
            color: {C.BTN_DANGER_TEXT};
            border: 1px solid {C.BTN_DANGER_BORDER};
            border-radius: 7px;
            padding: 6px 14px;
            font-size: 12px;
            font-weight: 600;
        }}
        QPushButton:hover {{ background-color: {C.BTN_DANGER_HOVER}; }}
    """

    BTN_EXCEL = f"""
        QPushButton {{
            background-color: {C.BTN_SUCCESS_BG};
            color: {C.BTN_SUCCESS_TEXT};
            border: 1px solid {C.BTN_SUCCESS_BORDER};
            border-radius: 7px;
            padding: 6px 14px;
            font-size: 12px;
            font-weight: 600;
        }}
        QPushButton:hover {{ background-color: {C.BTN_SUCCESS_HOVER}; }}
    """

    SAVE_BTN   = BTN_EXCEL
    CANCEL_BTN = BTN_REFRESH
    EDIT_BTN   = BTN_REFRESH
    DANGER_BTN = BTN_CLOSE
    REPORT_BTN = BTN_REFRESH
    PDF_BTN    = BTN_REFRESH
    BACK_BTN   = BTN_REFRESH
    CALC_BTN   = BTN_REFRESH

    # ── Input Alanları ───────────────────────────────────────────
    INPUT_SEARCH = f"""
        QLineEdit {{
            background-color: {C.INPUT_BG};
            border: 1.5px solid {C.INPUT_BORDER};
            border-radius: 8px;
            padding: 6px 10px 6px 30px;
            font-size: 13px;
            color: {C.TEXT_PRIMARY};
        }}
        QLineEdit:focus {{
            border-color: {C.INPUT_BORDER_FOCUS};
            background-color: {C.BG_ELEVATED};
        }}
        QLineEdit::placeholder {{ color: {C.TEXT_MUTED}; }}
    """

    INPUT_COMBO = f"""
        QComboBox {{
            background-color: {C.INPUT_BG};
            border: 1.5px solid {C.INPUT_BORDER};
            border-radius: 8px;
            padding: 6px 10px;
            color: {C.TEXT_PRIMARY};
            font-size: 13px;
        }}
        QComboBox:focus {{ border-color: {C.INPUT_BORDER_FOCUS}; }}
        QComboBox:hover {{ border-color: {C.BORDER_STRONG}; }}
        QComboBox::drop-down {{ border: none; width: 20px; }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid {C.TEXT_MUTED};
            width: 0; height: 0;
        }}
        QComboBox QAbstractItemView {{
            background-color: {C.BG_ELEVATED};
            border: 1px solid {C.BORDER_STRONG};
            border-radius: 8px;
            color: {C.TEXT_SECONDARY};
            selection-background-color: {C.BG_SELECTED};
            selection-color: {C.ACCENT2};
            outline: 0;
            padding: 4px;
        }}
        QComboBox QAbstractItemView::item {{
            padding: 6px 10px;
            border-radius: 5px;
            min-height: 26px;
        }}
        QComboBox QAbstractItemView::item:hover {{
            background-color: {C.BG_HOVER};
            color: {C.ACCENT2};
        }}
    """

    INPUT_FIELD = f"""
        QLineEdit {{
            background-color: {C.INPUT_BG};
            border: 1.5px solid {C.INPUT_BORDER};
            border-radius: 8px;
            padding: 6px 10px;
            font-size: 13px;
            color: {C.TEXT_PRIMARY};
        }}
        QLineEdit:focus {{
            border-color: {C.INPUT_BORDER_FOCUS};
            background-color: {C.BG_ELEVATED};
        }}
        QLineEdit:read-only {{
            background-color: {C.BG_SECONDARY};
            color: {C.TEXT_SECONDARY};
        }}
        QLineEdit::placeholder {{ color: {C.TEXT_MUTED}; }}
    """

    INPUT_DATE = f"""
        QDateEdit {{
            background-color: {C.INPUT_BG};
            border: 1.5px solid {C.INPUT_BORDER};
            border-radius: 8px;
            padding: 6px 10px;
            font-size: 13px;
            color: {C.TEXT_PRIMARY};
        }}
        QDateEdit:focus {{ border-color: {C.INPUT_BORDER_FOCUS}; }}
        QDateEdit::drop-down {{ border: none; width: 20px; }}
    """

    CALENDAR = f"""
        QCalendarWidget {{
            background-color: {C.BG_SECONDARY};
            color: {C.TEXT_PRIMARY};
            border: 1px solid {C.BORDER_PRIMARY};
            border-radius: 10px;
        }}
        QCalendarWidget QToolButton {{
            background-color: transparent;
            color: {C.TEXT_PRIMARY};
            border: none;
            padding: 6px 12px;
            font-size: 13px; font-weight: 600;
        }}
        QCalendarWidget QToolButton:hover {{
            background-color: rgba(0,180,216,0.12);
            border-radius: 6px;
            color: {C.ACCENT2};
        }}
        QCalendarWidget QMenu {{
            background-color: {C.BG_ELEVATED};
            color: {C.TEXT_PRIMARY};
            border: 1px solid rgba(0,180,216,0.20);
            border-radius: 8px;
        }}
        QCalendarWidget QSpinBox {{
            background-color: {C.INPUT_BG};
            color: {C.TEXT_PRIMARY};
            border: 1.5px solid rgba(255,255,255,0.10);
            padding: 4px 8px;
            font-size: 13px;
            border-radius: 6px;
        }}
        QCalendarWidget QAbstractItemView {{
            background-color: {C.BG_SECONDARY};
            color: {C.TEXT_MUTED};
            selection-background-color: rgba(0,180,216,0.18);
            selection-color: {C.ACCENT2};
            font-size: 13px;
            outline: none;
        }}
        QCalendarWidget QAbstractItemView:disabled {{ color: #263850; }}
        QCalendarWidget #qt_calendar_navigationbar {{
            background-color: {C.BG_TERTIARY};
            border-bottom: 1px solid rgba(255,255,255,0.07);
            padding: 4px;
        }}
    """

    INPUT_TEXT = f"""
        QTextEdit {{
            background-color: {C.INPUT_BG};
            border: 1.5px solid {C.INPUT_BORDER};
            border-radius: 8px;
            padding: 8px 10px;
            font-size: 13px;
            color: {C.TEXT_PRIMARY};
        }}
        QTextEdit:focus {{ border-color: {C.INPUT_BORDER_FOCUS}; }}
    """

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

    # ── Tablo ────────────────────────────────────────────────────
    TABLE = f"""
        QTableView, QTableWidget {{
            background-color: {C.BG_SECONDARY};
            border: 1px solid {C.BORDER_PRIMARY};
            border-radius: 10px;
            gridline-color: {C.BORDER_SECONDARY};
            color: {C.TEXT_PRIMARY};
            selection-background-color: {C.BG_SELECTED};
            selection-color: {C.ACCENT2};
            alternate-background-color: {C.BG_TERTIARY};
            outline: 0;
        }}
        QHeaderView::section {{
            background-color: {C.BG_TERTIARY};
            color: {C.TEXT_SECONDARY};
            border: none;
            border-bottom: 1px solid {C.BORDER_STRONG};
            border-right: 1px solid {C.BORDER_SECONDARY};
            padding: 7px 10px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.06em;
        }}
        QHeaderView::section:last {{ border-right: none; }}
        QHeaderView::section:hover {{
            background-color: {C.BG_ELEVATED};
            color: {C.ACCENT2};
        }}
        QTableView::item {{ padding: 5px 10px; min-height: 34px; }}
        QTableView::item:hover {{ background-color: {C.BG_HOVER}; }}
        QTableView::item:selected {{
            background-color: {C.BG_SELECTED};
            color: {C.ACCENT2};
        }}
    """

    # ── GroupBox ─────────────────────────────────────────────────
    GROUP_BOX = f"""
        QGroupBox {{
            background-color: {C.BG_SECONDARY};
            border: 1px solid {C.BORDER_PRIMARY};
            border-radius: 10px;
            margin-top: 14px;
            padding-top: 10px;
            font-size: 12px;
            font-weight: 700;
            color: {C.TEXT_PRIMARY};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 2px 10px;
            background-color: {C.BG_SECONDARY};
            border: 1px solid {C.BORDER_PRIMARY};
            border-radius: 6px;
            color: {C.TEXT_SECONDARY};
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.05em;
        }}
    """

    SCROLLBAR = f"""
        QScrollBar:vertical {{
            background: transparent; width: 7px; margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {C.BORDER_STRONG};
            border-radius: 3px; min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{ background: {C.TEXT_MUTED}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QScrollBar:horizontal {{
            background: transparent; height: 7px; margin: 0;
        }}
        QScrollBar::handle:horizontal {{
            background: {C.BORDER_STRONG};
            border-radius: 3px; min-width: 30px;
        }}
        QScrollBar::handle:horizontal:hover {{ background: {C.TEXT_MUTED}; }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
    """

    TAB = f"""
        QTabWidget::pane {{
            background-color: {C.BG_SECONDARY};
            border: 1px solid {C.BORDER_PRIMARY};
            border-radius: 10px;
            top: -1px;
        }}
        QTabBar::tab {{
            background-color: transparent;
            color: {C.TEXT_SECONDARY};
            border: none;
            border-bottom: 2px solid transparent;
            padding: 8px 16px;
            font-size: 12px;
            font-weight: 500;
            margin-right: 2px;
        }}
        QTabBar::tab:hover {{
            color: {C.TEXT_PRIMARY};
            border-bottom-color: {C.BORDER_STRONG};
        }}
        QTabBar::tab:selected {{
            color: {C.ACCENT2};
            border-bottom-color: {C.ACCENT};
            font-weight: 700;
        }}
    """

    @staticmethod
    def get_status_color(status: str) -> tuple:
        _MAP = {
            "Aktif":              (16,  185, 129, 30),
            "Pasif":              (239, 68,  68,  30),
            "İzinli":             (245, 158, 11,  30),
            "Arızalı":            (239, 68,  68,  30),
            "Bakımda":            (245, 158, 11,  30),
            "Kapalı (Çözüldü)":  (16,  185, 129, 30),
            "Açık":               (239, 68,  68,  30),
            "İşlemde":            (249, 115, 22,  30),
            "Planlandı":          (245, 158, 11,  30),
            "Tamamlandı":         (16,  185, 129, 30),
            "Onaylandı":          (16,  185, 129, 30),
            "Beklemede":          (245, 158, 11,  30),
            "İptal":              (100, 116, 139, 25),
            "Kalibrasyonda":      (168, 85,  247, 30),
            "Parça Bekliyor":     (251, 191, 36,  30),
            "Dış Serviste":       (168, 85,  247, 30),
        }
        return _MAP.get(status, (78, 104, 136, 25))

    @staticmethod
    def get_status_text_color(status: str) -> str:
        _MAP = {
            "Aktif":              "#10b981",
            "Pasif":              "#f87171",
            "İzinli":             "#f59e0b",
            "Arızalı":            "#f87171",
            "Bakımda":            "#f59e0b",
            "Kapalı (Çözüldü)":  "#10b981",
            "Açık":               "#f87171",
            "İşlemde":            "#fb923c",
            "Planlandı":          "#f59e0b",
            "Tamamlandı":         "#10b981",
            "Onaylandı":          "#10b981",
            "Beklemede":          "#f59e0b",
            "İptal":              "#4e6888",
            "Kalibrasyonda":      "#a855f7",
            "Parça Bekliyor":     "#fbbf24",
            "Dış Serviste":       "#a855f7",
        }
        return _MAP.get(status, "#8aa8c8")

    FOOTER_LABEL = f"""
        QLabel {{
            color: {C.TEXT_MUTED};
            font-size: 10px;
            font-weight: 400;
            background: transparent;
        }}
    """

    PROGRESS = f"""
        QProgressBar {{
            background-color: {C.BG_TERTIARY};
            border: 1px solid {C.BORDER_SECONDARY};
            border-radius: 2px;
            height: 4px;
            margin: 0px;
            padding: 0px;
            text-align: center;
        }}
        QProgressBar::chunk {{
            background-color: {C.ACCENT};
            border-radius: 2px;
        }}
    """

    CONTEXT_MENU = f"""
        QMenu {{
            background-color: {C.BG_SECONDARY};
            color: {C.TEXT_PRIMARY};
            border: 1px solid {C.BORDER_PRIMARY};
            border-radius: 8px;
            padding: 4px 0;
            spacing: 0;
        }}
        QMenu::item {{
            padding: 6px 16px;
            background: transparent;
            border-radius: 0;
        }}
        QMenu::item:selected {{
            background-color: {C.BG_HOVER};
            color: {C.ACCENT2};
        }}
        QMenu::item:pressed {{
            background-color: {C.BG_SELECTED};
        }}
        QMenu::separator {{
            height: 1px;
            background-color: {C.BORDER_SECONDARY};
            margin: 4px 0;
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

    SECTION_LABEL = f"""
        QLabel {{
            color: {C.TEXT_PRIMARY};
            font-size: 13px;
            font-weight: 700;
            background: transparent;
            letter-spacing: 0.02em;
        }}
    """

    # ── Ek Stiller (Personel Modülü) ──────────────────────────────
    LABEL = LABEL_FORM  # Generic etiket

    INPUT = INPUT_FIELD  # Generic input

    SEPARATOR = f"""
        QFrame {{
            background-color: {C.BORDER_SECONDARY};
            height: 1px;
        }}
    """

    SPLITTER = f"""
        QSplitter {{
            background-color: transparent;
        }}
        QSplitter::handle {{
            background-color: {C.BORDER_SECONDARY};
        }}
        QSplitter::handle:hover {{
            background-color: {C.BORDER_STRONG};
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

    PHOTO_AREA = f"""
        QLabel {{
            background-color: {C.BG_TERTIARY};
            border: 2px dashed {C.BORDER_STRONG};
            border-radius: 8px;
            color: {C.TEXT_MUTED};
            font-size: 12px;
        }}
    """

    PHOTO_BTN = f"""
        QPushButton {{
            background-color: {C.ACCENT};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 6px 14px;
            font-size: 11px;
            font-weight: 600;
        }}
        QPushButton:hover {{ background-color: #00a8d8; }}
        QPushButton:pressed {{ background-color: #0090b0; }}
    """

    FILE_BTN = PHOTO_BTN

    REQUIRED_LABEL = f"""
        QLabel {{
            color: {C.TEXT_SECONDARY};
            font-size: 11px;
            font-weight: 700;
            background: transparent;
            letter-spacing: 0.04em;
        }}
        QLabel::before {{
            content: "* ";
            color: #ef4444;
        }}
    """

    DATE = INPUT_DATE


# ThemeManager için STYLES dict
STYLES = {
    "page":           ComponentStyles.PAGE,
    "filter_panel":   ComponentStyles.FILTER_PANEL,
    "btn_action":     ComponentStyles.BTN_ACTION,
    "btn_refresh":    ComponentStyles.BTN_REFRESH,
    "btn_filter":     ComponentStyles.BTN_FILTER,
    "btn_filter_all": ComponentStyles.BTN_FILTER_ALL,
    "btn_close":      ComponentStyles.BTN_CLOSE,
    "btn_excel":      ComponentStyles.BTN_EXCEL,
    "save_btn":       ComponentStyles.SAVE_BTN,
    "cancel_btn":     ComponentStyles.CANCEL_BTN,
    "edit_btn":       ComponentStyles.EDIT_BTN,
    "danger_btn":     ComponentStyles.DANGER_BTN,
    "report_btn":     ComponentStyles.REPORT_BTN,
    "pdf_btn":        ComponentStyles.PDF_BTN,
    "back_btn":       ComponentStyles.BACK_BTN,
    "calc_btn":       ComponentStyles.CALC_BTN,
    "input_search":   ComponentStyles.INPUT_SEARCH,
    "input_combo":    ComponentStyles.INPUT_COMBO,
    "input_field":    ComponentStyles.INPUT_FIELD,
    "input_date":     ComponentStyles.INPUT_DATE,
    "input_text":     ComponentStyles.INPUT_TEXT,
    "label_form":     ComponentStyles.LABEL_FORM,
    "label_title":    ComponentStyles.LABEL_TITLE,
    "table":          ComponentStyles.TABLE,
    "group_box":      ComponentStyles.GROUP_BOX,
    "scrollbar":      ComponentStyles.SCROLLBAR,
    "tab":            ComponentStyles.TAB,
    "footer_label":   ComponentStyles.FOOTER_LABEL,
    "progress":       ComponentStyles.PROGRESS,
    "context_menu":   ComponentStyles.CONTEXT_MENU,
    "info_label":     ComponentStyles.INFO_LABEL,
    "section_label":  ComponentStyles.SECTION_LABEL,
    "label":          ComponentStyles.LABEL,
    "input":          ComponentStyles.INPUT,
    "separator":      ComponentStyles.SEPARATOR,
    "splitter":       ComponentStyles.SPLITTER,
    "header_name":    ComponentStyles.HEADER_NAME,
    "photo_area":     ComponentStyles.PHOTO_AREA,
    "photo_btn":      ComponentStyles.PHOTO_BTN,
    "file_btn":       ComponentStyles.FILE_BTN,
    "required_label": ComponentStyles.REQUIRED_LABEL,
    "date":           ComponentStyles.DATE,
    "group":          ComponentStyles.GROUP_BOX,
    # Geriye dönük uyumluluk takma adları
    "refresh_btn":    ComponentStyles.BTN_REFRESH,
    "close_btn":      ComponentStyles.BTN_CLOSE,
    "action_btn":     ComponentStyles.BTN_ACTION,
    "combo":          ComponentStyles.INPUT_COMBO,
    "excel_btn":      ComponentStyles.BTN_EXCEL,
    "search":         ComponentStyles.INPUT_SEARCH,
    "scroll":         ComponentStyles.SCROLLBAR,

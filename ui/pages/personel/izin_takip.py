# -*- coding: utf-8 -*-
"""
İzin Takip Sayfası (Sidebar menüden erişilir)
- Sol: Personel seçimi (HizmetSınıfı filtreli) + Yeni izin girişi + Bakiye
- Sağ: İzin kayıtları tablosu (Ay/Yıl filtreli + seçili personel filtreli)

🔧 GÜNCELLEMELER:
- ✅ Tarih çakışma kontrolü eklendi
- ✅ Bakiye kontrolü ve otomatik düşme eklendi
- ✅ Güncelleme sırasında da kontroller aktif
"""
import uuid
from datetime import datetime, date, timedelta
from PySide6.QtCore import (
    Qt, QDate, QSortFilterProxyModel, QModelIndex, QAbstractTableModel
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDateEdit, QSpinBox, QFrame, QGroupBox,
    QGridLayout, QSplitter, QTableView, QHeaderView,
    QAbstractSpinBox, QMessageBox, QMenu
)
from PySide6.QtGui import QColor, QCursor

from core.logger import logger


# ─── Tarih Parse (çoklu format desteği) ───
_DATE_FMTS = ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y")

def _parse_date(val):
    """Çoklu format desteğiyle tarih string → date objesi."""
    val = str(val).strip()
    if not val:
        return None
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None

def _format_date_display(val):
    """Tarih string → dd.MM.yyyy gösterim."""
    d = _parse_date(val)
    return d.strftime("%d.%m.%Y") if d else str(val)


# ─── W11 Dark Glass Stiller ───
S = {
    "page": "background-color: transparent;",
    "filter_panel": """
        QFrame {
            background-color: rgba(30, 32, 44, 0.85);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 10px;
        }
    """,
    "group": """
        QGroupBox {
            background-color: rgba(30, 32, 44, 0.85);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 10px;
            margin-top: 14px; padding: 16px 12px 12px 12px;
            font-size: 13px; font-weight: bold; color: #8b8fa3;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            padding: 0 8px; color: #6bd3ff;
        }
    """,
    "label": "color: #8b8fa3; font-size: 12px; background: transparent;",
    "combo": """
        QComboBox {
            background-color: #1e202c;
            border: 1px solid #292b41; border-bottom: 2px solid #9dcbe3;
            border-radius: 6px; padding: 5px 10px; font-size: 13px;
            color: #e0e2ea; min-height: 24px;
        }
        QComboBox:focus { border-bottom: 2px solid #1d75fe; }
        QComboBox::drop-down { border: none; width: 24px; }
        QComboBox QAbstractItemView {
            background-color: #1e202c; border: 1px solid rgba(255,255,255,0.1);
            color: #c8cad0; selection-background-color: rgba(29,117,254,0.3);
            selection-color: #ffffff;
        }
    """,
    "combo_filter": """
        QComboBox {
            background-color: #1e202c;
            border: 1px solid #292b41; border-bottom: 2px solid #9dcbe3;
            border-radius: 6px; padding: 4px 8px; font-size: 12px;
            color: #e0e2ea; min-height: 22px;
        }
        QComboBox:focus { border-bottom: 2px solid #1d75fe; }
        QComboBox::drop-down { border: none; width: 22px; }
        QComboBox QAbstractItemView {
            background-color: #1e202c; border: 1px solid rgba(255,255,255,0.1);
            color: #c8cad0; selection-background-color: rgba(29,117,254,0.3);
            selection-color: #ffffff;
        }
    """,
    "date": """
        QDateEdit {
            background-color: #1e202c;
            border: 1px solid #292b41; border-bottom: 2px solid #9dcbe3;
            border-radius: 6px; padding: 5px 10px; font-size: 13px;
            color: #e0e2ea; min-height: 24px;
        }
        QDateEdit:focus { border-bottom: 2px solid #1d75fe; }
        QDateEdit::drop-down { border: none; width: 24px; }
        QDateEdit:read-only {
            background-color: rgba(30, 32, 44, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.04);
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
        }
    """,
    "spin": """
        QSpinBox {
            background-color: #1e202c;
            border: 1px solid #292b41; border-bottom: 2px solid #9dcbe3;
            border-radius: 6px; padding: 5px 10px; font-size: 13px;
            color: #e0e2ea; min-height: 24px;
        }
        QSpinBox:focus { border-bottom: 2px solid #1d75fe; }
    """,
    "save_btn": """
        QPushButton {
            background-color: rgba(29, 117, 254, 0.3); color: #6bd3ff;
            border: 1px solid rgba(29, 117, 254, 0.5); border-radius: 8px;
            padding: 10px 24px; font-size: 14px; font-weight: bold;
        }
        QPushButton:hover { background-color: rgba(29, 117, 254, 0.45); color: #ffffff; }
        QPushButton:disabled {
            background-color: rgba(255,255,255,0.05); color: #5a5d6e;
            border: 1px solid rgba(255,255,255,0.05);
        }
    """,
    "refresh_btn": """
        QPushButton {
            background-color: rgba(255,255,255,0.05); color: #8b8fa3;
            border: 1px solid rgba(255,255,255,0.08); border-radius: 6px;
            padding: 5px 10px; font-size: 12px;
        }
        QPushButton:hover { background-color: rgba(255,255,255,0.10); color: #c8cad0; }
    """,
    "close_btn": """
        QPushButton {
            background-color: rgba(239, 68, 68, 0.15); color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.25); border-radius: 6px;
            font-size: 14px; font-weight: bold;
        }
        QPushButton:hover { background-color: rgba(239, 68, 68, 0.35); color: #ffffff; }
    """,
    "table": """
        QTableView {
            background-color: rgba(30, 32, 44, 0.7);
            alternate-background-color: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            gridline-color: rgba(255, 255, 255, 0.04);
            selection-background-color: rgba(29, 117, 254, 0.45);
            selection-color: #ffffff;
            color: #c8cad0; font-size: 13px;
        }
        QTableView::item {
            padding: 6px 8px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.02);
        }
        QTableView::item:selected {
            background-color: rgba(29, 117, 254, 0.45); color: #ffffff;
        }
        QTableView::item:hover:!selected {
            background-color: rgba(255, 255, 255, 0.04);
        }
        QHeaderView::section {
            background-color: rgba(255, 255, 255, 0.05);
            color: #8b8fa3; font-weight: 600; font-size: 12px;
            padding: 8px; border: none;
            border-bottom: 1px solid rgba(29, 117, 254, 0.3);
            border-right: 1px solid rgba(255, 255, 255, 0.03);
        }
    """,
    "splitter": """
        QSplitter::handle {
            background-color: rgba(255, 255, 255, 0.06);
            width: 2px; margin: 8px 4px;
        }
    """,
    "context_menu": """
        QMenu {
            background-color: #1e202c;
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 8px; padding: 4px;
            color: #c8cad0; font-size: 13px;
        }
        QMenu::item {
            padding: 8px 24px 8px 12px; border-radius: 4px; margin: 2px;
        }
        QMenu::item:selected {
            background-color: rgba(29,117,254,0.35); color: #ffffff;
        }
        QMenu::separator {
            height: 1px; background: rgba(255,255,255,0.08); margin: 4px 8px;
        }
    """,
    "separator": "QFrame { background-color: rgba(255, 255, 255, 0.06); }",
    "stat_label": "color: #8b8fa3; font-size: 12px; background: transparent;",
    "stat_value": "color: #e0e2ea; font-size: 14px; font-weight: bold; background: transparent;",
    "stat_green": "color: #4ade80; font-size: 16px; font-weight: bold; background: transparent;",
    "stat_red": "color: #f87171; font-size: 14px; font-weight: bold; background: transparent;",
    "section_title": "color: #6bd3ff; font-size: 12px; font-weight: bold; background: transparent;",
    "footer_label": "color: #5a5d6e; font-size: 12px; background: transparent;",
    "max_label": "color: #facc15; font-size: 11px; font-style: italic; background: transparent;",
}


# ═══════════════════════════════════════════════
#  TABLE MODEL (Performans İçin)
# ═══════════════════════════════════════════════

class IzinTableModel(QAbstractTableModel):
    """QTableWidget yerine performanslı model."""

    HEADERS = ["TC", "Ad Soyad", "Başlama", "Gün", "Bitiş", "İzin Tipi", "Durum"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return None

        row_data = self._data[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:
                return str(row_data.get("Personelid", ""))
            elif col == 1:
                return str(row_data.get("AdSoyad", ""))
            elif col == 2:
                return _format_date_display(row_data.get("BaslamaTarihi", ""))
            elif col == 3:
                return str(row_data.get("Gun", ""))
            elif col == 4:
                return _format_date_display(row_data.get("BitisTarihi", ""))
            elif col == 5:
                return str(row_data.get("IzinTipi", ""))
            elif col == 6:
                return str(row_data.get("Durum", ""))

        elif role == Qt.ForegroundRole:
            if col == 6:
                durum = str(row_data.get("Durum", "")).strip()
                if durum == "İptal":
                    return QColor("#f87171")
                elif durum == "Onaylandı":
                    return QColor("#4ade80")
                elif durum == "Beklemede":
                    return QColor("#facc15")

        elif role == Qt.TextAlignmentRole:
            if col in (3,):
                return Qt.AlignCenter

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return None

    def set_data(self, data_list):
        self.beginResetModel()
        self._data = data_list
        self.endResetModel()

    def get_row(self, row_idx):
        if 0 <= row_idx < len(self._data):
            return self._data[row_idx]
        return None


# ═══════════════════════════════════════════════
#  ANA SAYFA
# ═══════════════════════════════════════════════

class IzinTakipPage(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self._db = db

        self._all_personel = []
        self._all_izin = []
        self._tatiller = set()
        self._izin_max_gun = {}

        # 🔧 Düzenleme modu kontrolü
        self._edit_mode = False
        self._edit_izin_id = None

        self.setStyleSheet(S["page"])
        self._build_ui()
        self.load_data()

    # ═══════════════════════════════════════════
    #  UI
    # ═══════════════════════════════════════════

    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(S["splitter"])
        splitter.setHandleWidth(3)

        left = self._build_left_panel()
        right = self._build_right_panel()

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([400, 800])

        main_layout.addWidget(splitter)

    def _build_left_panel(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # ─── FİLTRE ───
        grp_filter = QGroupBox("🔍 Personel Filtresi")
        grp_filter.setStyleSheet(S["group"])
        fl = QVBoxLayout(grp_filter)
        fl.setSpacing(8)

        lbl_sinif = QLabel("Hizmet Sınıfı:")
        lbl_sinif.setStyleSheet(S["label"])
        self.cmb_sinif = QComboBox()
        self.cmb_sinif.setStyleSheet(S["combo_filter"])
        self.cmb_sinif.currentIndexChanged.connect(self._filter_personel)
        fl.addWidget(lbl_sinif)
        fl.addWidget(self.cmb_sinif)

        lbl_p = QLabel("Personel:")
        lbl_p.setStyleSheet(S["label"])
        self.cmb_personel = QComboBox()
        self.cmb_personel.setStyleSheet(S["combo"])
        self.cmb_personel.setEditable(True)
        self.cmb_personel.currentIndexChanged.connect(self._on_personel_changed)
        fl.addWidget(lbl_p)
        fl.addWidget(self.cmb_personel)

        layout.addWidget(grp_filter)

        # ─── YENİ İZİN GİRİŞİ ───
        grp_form = QGroupBox("📝 Yeni İzin Girişi")
        grp_form.setStyleSheet(S["group"])
        gl = QGridLayout(grp_form)
        gl.setSpacing(10)
        gl.setColumnStretch(1, 1)

        row = 0

        # İzin Tipi
        lbl_tip = QLabel("İzin Tipi:")
        lbl_tip.setStyleSheet(S["label"])
        self.cmb_izin_tipi = QComboBox()
        self.cmb_izin_tipi.setStyleSheet(S["combo"])
        gl.addWidget(lbl_tip, row, 0)
        gl.addWidget(self.cmb_izin_tipi, row, 1)
        row += 1

        # Başlama Tarihi
        lbl_bas = QLabel("Başlama Tarihi:")
        lbl_bas.setStyleSheet(S["label"])
        self.dt_baslama = QDateEdit(QDate.currentDate())
        self.dt_baslama.setStyleSheet(S["date"])
        self.dt_baslama.setCalendarPopup(True)
        self.dt_baslama.setDisplayFormat("dd.MM.yyyy")
        self.dt_baslama.dateChanged.connect(self._calculate_bitis)
        gl.addWidget(lbl_bas, row, 0)
        gl.addWidget(self.dt_baslama, row, 1)
        row += 1

        # Gün Sayısı
        lbl_gun = QLabel("Gün Sayısı:")
        lbl_gun.setStyleSheet(S["label"])
        self.spn_gun = QSpinBox()
        self.spn_gun.setStyleSheet(S["spin"])
        self.spn_gun.setRange(1, 365)
        self.spn_gun.setValue(1)
        self.spn_gun.setButtonSymbols(QAbstractSpinBox.PlusMinus)
        self.spn_gun.valueChanged.connect(self._calculate_bitis)
        gl.addWidget(lbl_gun, row, 0)
        gl.addWidget(self.spn_gun, row, 1)
        row += 1

        # Bitiş Tarihi (read-only)
        lbl_bit = QLabel("İşe Dönüş:")
        lbl_bit.setStyleSheet(S["label"])
        self.dt_bitis = QDateEdit(QDate.currentDate())
        self.dt_bitis.setStyleSheet(S["date"])
        self.dt_bitis.setReadOnly(True)
        self.dt_bitis.setDisplayFormat("dd.MM.yyyy")
        gl.addWidget(lbl_bit, row, 0)
        gl.addWidget(self.dt_bitis, row, 1)
        row += 1

        # Max gün uyarısı
        self.lbl_max_gun = QLabel("")
        self.lbl_max_gun.setStyleSheet(S["max_label"])
        gl.addWidget(self.lbl_max_gun, row, 0, 1, 2)
        row += 1

        # Kaydet Butonu
        self.btn_kaydet = QPushButton("💾 KAYDET")
        self.btn_kaydet.setStyleSheet(S["save_btn"])
        self.btn_kaydet.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kaydet.clicked.connect(self._on_save)
        gl.addWidget(self.btn_kaydet, row, 0, 1, 2)
        row += 1

        # 🔧 Düzenleme İptal Butonu
        self.btn_iptal = QPushButton("🔄 İptal (Yeni Kayda Dön)")
        self.btn_iptal.setStyleSheet(S["refresh_btn"])
        self.btn_iptal.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_iptal.clicked.connect(self._clear_form)
        self.btn_iptal.setVisible(False)
        gl.addWidget(self.btn_iptal, row, 0, 1, 2)
        row += 1

        layout.addWidget(grp_form)

        # ─── BAKİYE BİLGİSİ ───
        grp_bakiye = QGroupBox("💰 Bakiye Bilgisi")
        grp_bakiye.setStyleSheet(S["group"])
        bl = QVBoxLayout(grp_bakiye)
        bl.setSpacing(6)

        # Yıllık İzin
        lbl_yil_title = QLabel("📅 YILLIK İZİN")
        lbl_yil_title.setStyleSheet(S["section_title"])
        bl.addWidget(lbl_yil_title)

        def add_stat(label_text, value_style=S["stat_value"]):
            hbox = QHBoxLayout()
            hbox.setSpacing(8)
            lbl = QLabel(label_text)
            lbl.setStyleSheet(S["stat_label"])
            val = QLabel("—")
            val.setStyleSheet(value_style)
            hbox.addWidget(lbl)
            hbox.addStretch()
            hbox.addWidget(val)
            bl.addLayout(hbox)
            return val

        self.lbl_y_devir = add_stat("Devir:")
        self.lbl_y_hak = add_stat("Hakediş:")
        self.lbl_y_kul = add_stat("Kullanılan:", S["stat_red"])
        self.lbl_y_kal = add_stat("Kalan:", S["stat_green"])

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setStyleSheet(S["separator"])
        bl.addWidget(sep1)

        # Şua İzni
        lbl_sua_title = QLabel("⏰ ŞUA İZNİ")
        lbl_sua_title.setStyleSheet(S["section_title"])
        bl.addWidget(lbl_sua_title)

        self.lbl_s_hak = add_stat("Hakediş:")
        self.lbl_s_kul = add_stat("Kullanılan:", S["stat_red"])
        self.lbl_s_kal = add_stat("Kalan:", S["stat_green"])

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet(S["separator"])
        bl.addWidget(sep2)

        # Diğer
        lbl_diger_title = QLabel("📋 DİĞER")
        lbl_diger_title.setStyleSheet(S["section_title"])
        bl.addWidget(lbl_diger_title)

        self.lbl_diger = add_stat("Rapor / Mazeret:")

        bl.addStretch()

        layout.addWidget(grp_bakiye)
        layout.addStretch()

        return widget

    def _build_right_panel(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # ─── FİLTRE ───
        filter_frame = QFrame()
        filter_frame.setStyleSheet(S["filter_panel"])
        fl = QHBoxLayout(filter_frame)
        fl.setContentsMargins(12, 10, 12, 10)
        fl.setSpacing(10)

        lbl_yil = QLabel("Yıl:")
        lbl_yil.setStyleSheet(S["label"])
        self.cmb_yil = QComboBox()
        self.cmb_yil.setStyleSheet(S["combo_filter"])
        self.cmb_yil.currentIndexChanged.connect(self._apply_filters)
        fl.addWidget(lbl_yil)
        fl.addWidget(self.cmb_yil)

        lbl_ay = QLabel("Ay:")
        lbl_ay.setStyleSheet(S["label"])
        self.cmb_ay = QComboBox()
        self.cmb_ay.setStyleSheet(S["combo_filter"])
        self.cmb_ay.currentIndexChanged.connect(self._apply_filters)
        fl.addWidget(lbl_ay)
        fl.addWidget(self.cmb_ay)

        fl.addStretch()

        btn_refresh = QPushButton("🔄 Yenile")
        btn_refresh.setStyleSheet(S["refresh_btn"])
        btn_refresh.setCursor(QCursor(Qt.PointingHandCursor))
        btn_refresh.clicked.connect(self.load_data)
        fl.addWidget(btn_refresh)

        layout.addWidget(filter_frame)

        # ─── TABLO ───
        self._model = IzinTableModel(self)
        self._proxy = QSortFilterProxyModel(self)
        self._proxy.setSourceModel(self._model)

        self.table = QTableView()
        self.table.setStyleSheet(S["table"])
        self.table.setModel(self._proxy)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.setSortingEnabled(True)

        # Header resize
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)

        # 🔧 Satıra çift tıklanınca düzenle
        self.table.doubleClicked.connect(self._on_table_double_click)

        layout.addWidget(self.table)

        # ─── FOOTER ───
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(16)

        self.lbl_count = QLabel("0 / 0 kayıt")
        self.lbl_count.setStyleSheet(S["footer_label"])
        footer_layout.addWidget(self.lbl_count)

        footer_layout.addStretch()

        # Kapat butonu
        self.btn_kapat = QPushButton("✕ Kapat")
        self.btn_kapat.setStyleSheet(S["close_btn"])
        self.btn_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kapat.setFixedWidth(120)
        footer_layout.addWidget(self.btn_kapat)

        layout.addLayout(footer_layout)

        return widget

    # ═══════════════════════════════════════════
    #  VERİ YÜKLEME
    # ═══════════════════════════════════════════

    def load_data(self):
        """Tüm verileri yükle: personel, izinler, sabitler, tatiller."""
        try:
            from database.repository_registry import RepositoryRegistry
            registry = RepositoryRegistry(self._db)

            # Personel
            all_p = registry.get("Personel").get_all()
            self._all_personel = [
                {
                    "KimlikNo": p.get("KimlikNo"),
                    "AdSoyad": p.get("AdSoyad"),
                    "HizmetSinifi": p.get("HizmetSinifi"),
                }
                for p in all_p if p.get("AdSoyad")
            ]

            # Hizmet Sınıfları (Sabitler)
            sabits = registry.get("Sabitler").get_all()
            siniflar = sorted(set(
                s.get("Aciklama", "")
                for s in sabits if s.get("Kod") == "Hizmet_Sinifi"
            ))
            siniflar = [x for x in siniflar if x]

            self.cmb_sinif.clear()
            self.cmb_sinif.addItem("Tümü", "")
            for sinif in siniflar:
                self.cmb_sinif.addItem(sinif, sinif)

            # İzin Tipleri
            izin_tipleri = sorted(set(
                s.get("Aciklama", "")
                for s in sabits if s.get("Kod") == "Izin_Tipi"
            ))
            izin_tipleri = [x for x in izin_tipleri if x]

            self.cmb_izin_tipi.clear()
            for tip in izin_tipleri:
                self.cmb_izin_tipi.addItem(tip)

            # İzin Tipi Max Gün
            self._izin_max_gun = {}
            for s in sabits:
                if s.get("Kod") == "Izin_Tipi":
                    tip = s.get("Aciklama", "").strip()
                    try:
                        max_val = int(s.get("Deger", 0))
                        if max_val > 0:
                            self._izin_max_gun[tip] = max_val
                    except (ValueError, TypeError):
                        pass

            self.cmb_izin_tipi.currentIndexChanged.connect(self._update_max_gun_label)
            self._update_max_gun_label()

            # Tatiller
            tatil_kayitlari = registry.get("Tatiller").get_all()
            self._tatiller = set()
            for t in tatil_kayitlari:
                d = _parse_date(t.get("Tarih", ""))
                if d:
                    self._tatiller.add(d.isoformat())

            # İzin Kayıtları
            self._all_izin = registry.get("Izin_Giris").get_all()

            # Yıl filtresi
            yillar = set()
            for r in self._all_izin:
                d = _parse_date(r.get("BaslamaTarihi", ""))
                if d:
                    yillar.add(d.year)
            yillar = sorted(yillar, reverse=True)

            self.cmb_yil.clear()
            self.cmb_yil.addItem("Tümü", 0)
            for y in yillar:
                self.cmb_yil.addItem(str(y), y)

            # Ay filtresi
            aylar = ["Tümü", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
                     "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
            self.cmb_ay.clear()
            for i, ay in enumerate(aylar):
                self.cmb_ay.addItem(ay, i)

            self._filter_personel()
            self._apply_filters()

            logger.info(
                f"İzin takip verileri yüklendi: {len(self._all_personel)} personel, "
                f"{len(self._all_izin)} izin kaydı"
            )

        except Exception as e:
            logger.error(f"İzin takip veri yükleme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Veri yüklenemedi:\n{e}")

    def _filter_personel(self):
        """HizmetSınıfı filtresine göre personel listesini doldur."""
        selected_sinif = self.cmb_sinif.currentData()

        self.cmb_personel.clear()
        self.cmb_personel.addItem("Seçiniz...", "")

        filtered = self._all_personel
        if selected_sinif:
            filtered = [p for p in self._all_personel
                        if p.get("HizmetSinifi") == selected_sinif]

        filtered = sorted(filtered, key=lambda x: x.get("AdSoyad", ""))

        for p in filtered:
            ad = p.get("AdSoyad", "")
            tc = p.get("KimlikNo", "")
            self.cmb_personel.addItem(ad, tc)

    def _on_personel_changed(self):
        """Personel seçildiğinde bakiye bilgisi yükle + filtreyi uygula."""
        tc = self.cmb_personel.currentData()
        self._load_bakiye(tc)
        self._apply_filters()

    def _update_max_gun_label(self):
        """İzin tipine göre max gün uyarısını göster."""
        izin_tipi = self.cmb_izin_tipi.currentText().strip()
        max_gun = self._izin_max_gun.get(izin_tipi, 0)
        if max_gun:
            self.lbl_max_gun.setText(f"⚠️ Maksimum {max_gun} gün girilebilir")
        else:
            self.lbl_max_gun.setText("")

    def _load_bakiye(self, tc):
        """Seçili personelin bakiye bilgisini göster."""
        if not tc:
            self._clear_bakiye()
            return
        try:
            from database.repository_registry import RepositoryRegistry
            registry = RepositoryRegistry(self._db)
            izin = registry.get("Izin_Bilgi").get_by_id(tc)
            if izin:
                self.lbl_y_devir.setText(str(izin.get("YillikDevir", "0")))
                self.lbl_y_hak.setText(str(izin.get("YillikHakedis", "0")))
                self.lbl_y_kul.setText(str(izin.get("YillikKullanilan", "0")))
                self.lbl_y_kal.setText(str(izin.get("YillikKalan", "0")))
                self.lbl_s_hak.setText(str(izin.get("SuaKullanilabilirHak", "0")))
                self.lbl_s_kul.setText(str(izin.get("SuaKullanilan", "0")))
                self.lbl_s_kal.setText(str(izin.get("SuaKalan", "0")))
                self.lbl_diger.setText(str(izin.get("RaporMazeretTop", "0")))
            else:
                self._clear_bakiye()
        except Exception as e:
            logger.error(f"Bakiye yükleme hatası: {e}")
            self._clear_bakiye()

    def _clear_bakiye(self):
        for lbl in [self.lbl_y_devir, self.lbl_y_hak, self.lbl_y_kul, self.lbl_y_kal,
                     self.lbl_s_hak, self.lbl_s_kul, self.lbl_s_kal, self.lbl_diger]:
            lbl.setText("—")

    # ═══════════════════════════════════════════
    #  FİLTRELEME  (Ay + Yıl + Seçili Personel)
    # ═══════════════════════════════════════════

    def _apply_filters(self):
        """Ay/Yıl + seçili personel filtresi, yeniden eskiye sırala."""
        filtered = list(self._all_izin)

        ay = self.cmb_ay.currentData()     # int: 0=Tümü, 1-12
        yil = self.cmb_yil.currentData()   # int: 0=Tümü, 2026 ...
        selected_tc = self.cmb_personel.currentData()  # "" veya TC

        # Ay / Yıl filtresi (çoklu tarih formatı)
        if ay or yil:
            result = []
            for r in filtered:
                d = _parse_date(r.get("BaslamaTarihi", ""))
                if not d:
                    continue
                if yil and d.year != yil:
                    continue
                if ay and d.month != ay:
                    continue
                result.append(r)
            filtered = result

        # Personel filtresi
        if selected_tc:
            filtered = [r for r in filtered
                        if str(r.get("Personelid", "")).strip() == selected_tc]

        # Sıralama: yeniden eskiye
        filtered.sort(
            key=lambda r: _parse_date(r.get("BaslamaTarihi", "")) or date.min,
            reverse=True
        )

        self._model.set_data(filtered)

        # Varsayılan sıralama: Başlama sütunu (index 2) descending
        self.table.sortByColumn(2, Qt.DescendingOrder)

        total_gun = sum(int(r.get("Gun", 0)) for r in filtered
                        if str(r.get("Gun", "")).isdigit())
        self.lbl_count.setText(
            f"{len(filtered)} / {len(self._all_izin)} kayıt  —  Toplam {total_gun} gün"
        )

    # ═══════════════════════════════════════════
    #  BİTİŞ TARİHİ HESAPLA
    # ═══════════════════════════════════════════

    def _calculate_bitis(self):
        baslama = self.dt_baslama.date().toPython()
        gun = self.spn_gun.value()

        kalan = gun
        current = baslama
        while kalan > 0:
            current += timedelta(days=1)
            if current.weekday() in (5, 6):
                continue
            if current.isoformat() in self._tatiller:
                continue
            kalan -= 1

        self.dt_bitis.setDate(QDate(current.year, current.month, current.day))

    # ═══════════════════════════════════════════
    #  🔧 KAYDET (ÇAKIŞMA + BAKİYE KONTROLÜ)
    # ═══════════════════════════════════════════

    def _on_save(self):
        """İzin kaydet — çakışma kontrolü + bakiye kontrolü."""
        print("\n" + "="*60)
        print("🔴 KAYDET FONKSİYONU ÇAĞRILDI - YENİ SÜRÜM ÇALIŞIYOR!")
        print("="*60 + "\n")
        logger.info("🔴 KAYDET fonksiyonu çağrıldı")
        
        tc = self.cmb_personel.currentData()
        if not tc:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir personel seçin.")
            return

        p = next((p for p in self._all_personel
                  if p.get("KimlikNo") == tc), {})
        ad = p.get("AdSoyad", "")
        sinif = p.get("HizmetSinifi", "")
        izin_tipi = self.cmb_izin_tipi.currentText().strip()

        if not izin_tipi:
            QMessageBox.warning(self, "Eksik", "İzin tipi seçilmeli.")
            return

        baslama = self.dt_baslama.date().toString("yyyy-MM-dd")
        bitis = self.dt_bitis.date().toString("yyyy-MM-dd")
        gun = self.spn_gun.value()

        # Max gün kontrolü
        max_gun = self._izin_max_gun.get(izin_tipi, 0)
        if max_gun and gun > max_gun:
            QMessageBox.warning(self, "Limit Aşımı",
                f"{izin_tipi} için maksimum {max_gun} gün girilebilir.")
            return

        # 🔧 TARİH ÇAKIŞMA KONTROLÜ
        yeni_bas = _parse_date(baslama)
        yeni_bit = _parse_date(bitis)

        print(f"\n{'='*70}")
        print(f"🔍 ÇAKIŞMA KONTROLÜ BAŞLADI")
        print(f"{'='*70}")
        print(f"TC: {tc} | Ad: {ad}")
        print(f"Yeni izin: {yeni_bas} - {yeni_bit}")
        print(f"Toplam kayıt sayısı: {len(self._all_izin)}")
        print(f"{'='*70}\n")

        if not yeni_bas or not yeni_bit:
            print("❌ HATA: Tarih formatı hatalı!")
            QMessageBox.critical(self, "Hata", "Tarih formatı hatalı.")
            return

        logger.info(f"Çakışma kontrolü başladı: {tc} için {yeni_bas} - {yeni_bit}")
        logger.info(f"Kontrol edilecek izin sayısı: {len(self._all_izin)}")

        ayni_personel_sayisi = 0
        for kayit in self._all_izin:
            # İptal edilen kayıtları atla
            durum = str(kayit.get("Durum", "")).strip()
            if durum == "İptal":
                continue

            # Başka personel ise atla
            vt_tc = str(kayit.get("Personelid", "")).strip()
            if vt_tc != tc:
                continue

            ayni_personel_sayisi += 1
            print(f"[{ayni_personel_sayisi}] Aynı TC bulundu: {kayit.get('Izinid')}")

            # Düzenleme modunda aynı kaydı atla
            vt_id = str(kayit.get("Izinid", "")).strip()
            if self._edit_mode and vt_id == self._edit_izin_id:
                print(f"    ⏩ Atlandı (düzenleme modu)")
                continue

            # Tarih çakışması kontrolü
            vt_bas = _parse_date(kayit.get("BaslamaTarihi", ""))
            vt_bit = _parse_date(kayit.get("BitisTarihi", ""))

            if vt_bas and vt_bit:
                print(f"    📅 Tarihler: {vt_bas} - {vt_bit}")
                cond1 = yeni_bas <= vt_bit
                cond2 = yeni_bit >= vt_bas
                print(f"    📊 yeni_bas ({yeni_bas}) <= vt_bit ({vt_bit}) = {cond1}")
                print(f"    📊 yeni_bit ({yeni_bit}) >= vt_bas ({vt_bas}) = {cond2}")
                
                logger.debug(f"Kontrol ediliyor: {vt_bas} - {vt_bit} vs {yeni_bas} - {yeni_bit}")
                
                # Çakışma formülü: (yeni_bas <= vt_bit) AND (yeni_bit >= vt_bas)
                if (yeni_bas <= vt_bit) and (yeni_bit >= vt_bas):
                    print(f"\n{'='*70}")
                    print(f"❌❌❌ ÇAKIŞMA BULUNDU! ❌❌❌")
                    print(f"Mevcut: {vt_bas.strftime('%d.%m.%Y')} - {vt_bit.strftime('%d.%m.%Y')}")
                    print(f"Yeni  : {yeni_bas.strftime('%d.%m.%Y')} - {yeni_bit.strftime('%d.%m.%Y')}")
                    print(f"İzin Tipi: {kayit.get('IzinTipi', '')}")
                    print(f"{'='*70}\n")
                    
                    logger.warning(f"ÇAKIŞMA BULUNDU! {vt_bas} - {vt_bit}")
                    QMessageBox.warning(
                        self, "❌ Çakışma Var!",
                        f"{ad} personeli {vt_bas.strftime('%d.%m.%Y')} - "
                        f"{vt_bit.strftime('%d.%m.%Y')} tarihlerinde zaten izinli!\n\n"
                        f"İzin Tipi: {kayit.get('IzinTipi', '')}\n"
                        f"Durum: {durum}\n\n"
                        f"Lütfen farklı bir tarih seçiniz."
                    )
                    return
                else:
                    print(f"    ✅ Çakışma yok")

        print(f"\n{'='*70}")
        print(f"✅ Çakışma kontrolü tamamlandı")
        print(f"Aynı personele ait {ayni_personel_sayisi} kayıt kontrol edildi")
        print(f"Çakışma bulunamadı - kayıt devam ediyor...")
        print(f"{'='*70}\n")
        
        logger.info("Çakışma kontrolü tamamlandı - çakışma yok")

        # 🔧 BAKİYE KONTROLÜ (Yıllık İzin ve Şua için)
        if izin_tipi in ["Yıllık İzin", "Şua İzni"]:
            try:
                from database.repository_registry import RepositoryRegistry
                registry = RepositoryRegistry(self._db)
                izin_bilgi = registry.get("Izin_Bilgi").get_by_id(tc)

                if izin_bilgi:
                    if izin_tipi == "Yıllık İzin":
                        kalan = float(izin_bilgi.get("YillikKalan", 0))
                        if gun > kalan:
                            cevap = QMessageBox.question(
                                self, "Bakiye Yetersiz",
                                f"⚠️ {ad} personelinin yıllık izin bakiyesi: {kalan} gün\n"
                                f"Girilen gün sayısı: {gun} gün\n\n"
                                f"Eksik: {gun - kalan} gün\n\n"
                                f"Yine de kaydetmek istiyor musunuz?",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                            )
                            if cevap != QMessageBox.Yes:
                                return

                    elif izin_tipi == "Şua İzni":
                        kalan = float(izin_bilgi.get("SuaKalan", 0))
                        if gun > kalan:
                            cevap = QMessageBox.question(
                                self, "Bakiye Yetersiz",
                                f"⚠️ {ad} personelinin şua izin bakiyesi: {kalan} gün\n"
                                f"Girilen gün sayısı: {gun} gün\n\n"
                                f"Eksik: {gun - kalan} gün\n\n"
                                f"Yine de kaydetmek istiyor musunuz?",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                            )
                            if cevap != QMessageBox.Yes:
                                return
            except Exception as e:
                logger.error(f"Bakiye kontrolü hatası: {e}")

        # Kayıt oluştur
        if self._edit_mode:
            izin_id = self._edit_izin_id
        else:
            izin_id = str(uuid.uuid4())[:8].upper()

        kayit = {
            "Izinid": izin_id,
            "HizmetSinifi": sinif,
            "Personelid": tc,
            "AdSoyad": ad,
            "IzinTipi": izin_tipi,
            "BaslamaTarihi": baslama,
            "Gun": gun,
            "BitisTarihi": bitis,
            "Durum": "Onaylandı",
        }

        try:
            from database.repository_registry import RepositoryRegistry
            registry = RepositoryRegistry(self._db)

            if self._edit_mode:
                # Güncelleme
                registry.get("Izin_Giris").update(izin_id, kayit)
                logger.info(f"İzin güncellendi: {izin_id} — {ad} — {izin_tipi} — {gun} gün")
                msg = "Güncellendi"
            else:
                # Yeni kayıt
                registry.get("Izin_Giris").insert(kayit)
                logger.info(f"İzin kaydedildi: {izin_id} — {ad} — {izin_tipi} — {gun} gün")

                # 🔧 BAKİYE DÜŞME
                self._bakiye_dus(registry, tc, izin_tipi, gun)
                msg = "Kaydedildi"

            QMessageBox.information(
                self, "Başarılı",
                f"✅ {ad} için {gun} gün {izin_tipi} {msg}.\n"
                f"Başlama: {self.dt_baslama.date().toString('dd.MM.yyyy')}\n"
                f"İşe Dönüş: {self.dt_bitis.date().toString('dd.MM.yyyy')}"
            )

            self._clear_form()
            self.load_data()

        except Exception as e:
            logger.error(f"İzin kaydetme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"İzin kaydedilemedi:\n{e}")

    def _bakiye_dus(self, registry, tc, izin_tipi, gun):
        """Bakiyeden düş (Yıllık İzin / Şua İzni)."""
        try:
            izin_bilgi = registry.get("Izin_Bilgi").get_by_id(tc)
            if not izin_bilgi:
                return

            if izin_tipi == "Yıllık İzin":
                mevcut = float(izin_bilgi.get("YillikKullanilan", 0))
                yeni = mevcut + gun
                kalan_eski = float(izin_bilgi.get("YillikKalan", 0))
                kalan_yeni = kalan_eski - gun

                registry.get("Izin_Bilgi").update(tc, {
                    "YillikKullanilan": yeni,
                    "YillikKalan": kalan_yeni
                })
                logger.info(f"Yıllık izin bakiye düştü: {tc} → {gun} gün")

            elif izin_tipi == "Şua İzni":
                mevcut = float(izin_bilgi.get("SuaKullanilan", 0))
                yeni = mevcut + gun
                kalan_eski = float(izin_bilgi.get("SuaKalan", 0))
                kalan_yeni = kalan_eski - gun

                registry.get("Izin_Bilgi").update(tc, {
                    "SuaKullanilan": yeni,
                    "SuaKalan": kalan_yeni
                })
                logger.info(f"Şua izin bakiye düştü: {tc} → {gun} gün")

            elif izin_tipi in ["Rapor", "Mazeret İzni"]:
                mevcut = float(izin_bilgi.get("RaporMazeretTop", 0))
                yeni = mevcut + gun
                registry.get("Izin_Bilgi").update(tc, {
                    "RaporMazeretTop": yeni
                })
                logger.info(f"Rapor/Mazeret toplam arttı: {tc} → {gun} gün")

        except Exception as e:
            logger.error(f"Bakiye düşme hatası: {e}")

    # ═══════════════════════════════════════════
    #  🔧 DÜZENLEME MODU
    # ═══════════════════════════════════════════

    def _on_table_double_click(self, index):
        """Tabloda satıra çift tıklanınca düzenleme moduna geç."""
        source_idx = self._proxy.mapToSource(index)
        row_data = self._model.get_row(source_idx.row())
        if not row_data:
            return

        durum = str(row_data.get("Durum", "")).strip()
        if durum == "İptal":
            QMessageBox.warning(self, "Uyarı", "İptal edilmiş kayıtlar düzenlenemez.")
            return

        # Düzenleme moduna geç
        self._edit_mode = True
        self._edit_izin_id = str(row_data.get("Izinid", ""))

        # Formu doldur
        tc = str(row_data.get("Personelid", ""))
        idx = self.cmb_personel.findData(tc)
        if idx >= 0:
            self.cmb_personel.setCurrentIndex(idx)

        self.cmb_izin_tipi.setCurrentText(str(row_data.get("IzinTipi", "")))

        bas = _parse_date(row_data.get("BaslamaTarihi", ""))
        if bas:
            self.dt_baslama.setDate(QDate(bas.year, bas.month, bas.day))

        self.spn_gun.setValue(int(row_data.get("Gun", 1)))

        # UI değişiklikleri
        self.btn_kaydet.setText("✏️ GÜNCELLE")
        self.btn_kaydet.setStyleSheet("""
            QPushButton {
                background-color: rgba(245, 158, 11, 0.3); color: #fbbf24;
                border: 1px solid rgba(245, 158, 11, 0.5); border-radius: 8px;
                padding: 10px 24px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background-color: rgba(245, 158, 11, 0.45); color: #ffffff; }
        """)
        self.btn_iptal.setVisible(True)

        logger.info(f"Düzenleme modu: {self._edit_izin_id}")

    def _clear_form(self):
        """Formu temizle ve yeni kayıt moduna dön."""
        self._edit_mode = False
        self._edit_izin_id = None

        self.cmb_personel.setCurrentIndex(0)
        self.cmb_izin_tipi.setCurrentIndex(0)
        self.spn_gun.setValue(1)
        self.dt_baslama.setDate(QDate.currentDate())

        self.btn_kaydet.setText("💾 KAYDET")
        self.btn_kaydet.setStyleSheet(S["save_btn"])
        self.btn_iptal.setVisible(False)

        logger.info("Form temizlendi — yeni kayıt modu")

    # ═══════════════════════════════════════════
    #  SAĞ TIKLAMA MENÜSÜ
    # ═══════════════════════════════════════════

    def _show_context_menu(self, pos):
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        source_idx = self._proxy.mapToSource(index)
        row_data = self._model.get_row(source_idx.row())
        if not row_data:
            return

        ad = row_data.get("AdSoyad", "")
        izin_id = row_data.get("Izinid", "")
        durum = str(row_data.get("Durum", "")).strip()

        menu = QMenu(self)
        menu.setStyleSheet(S["context_menu"])

        if durum != "İptal":
            act_iptal = menu.addAction("❌ İzni İptal Et")
            act_iptal.triggered.connect(lambda: self._iptal_izin(izin_id, ad))

        if durum == "Beklemede":
            act_onayla = menu.addAction("✅ Onayla")
            act_onayla.triggered.connect(lambda: self._durum_degistir(izin_id, ad, "Onaylandı"))

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _iptal_izin(self, izin_id, ad):
        cevap = QMessageBox.question(
            self, "İzin İptal",
            f"{ad} personelinin bu izni iptal edilsin mi?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if cevap == QMessageBox.Yes:
            self._durum_degistir(izin_id, ad, "İptal")

    def _durum_degistir(self, izin_id, ad, yeni_durum):
        try:
            from database.repository_registry import RepositoryRegistry
            registry = RepositoryRegistry(self._db)
            registry.get("Izin_Giris").update(izin_id, {"Durum": yeni_durum})
            logger.info(f"İzin durum değişti: {izin_id} → {yeni_durum}")
            self.load_data()
        except Exception as e:
            logger.error(f"İzin durum hatası: {e}")
            QMessageBox.critical(self, "Hata", f"İşlem hatası:\n{e}")

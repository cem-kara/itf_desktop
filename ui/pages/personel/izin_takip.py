# -*- coding: utf-8 -*-
"""
İzin Takip Sayfası (Sidebar menüden erişilir)
- Sol: Personel seçimi (HizmetSınıfı filtreli) + Yeni izin girişi + Bakiye
- Sağ: İzin kayıtları tablosu (Ay/Yıl filtreli + seçili personel filtreli)
"""
import uuid
from datetime import date, timedelta
from PySide6.QtCore import (
    Qt, QDate, QSortFilterProxyModel,
    QPropertyAnimation, QEasingCurve
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDateEdit, QSpinBox, QFrame, QGroupBox,
    QGridLayout, QTableView, QHeaderView, QScrollArea,
    QAbstractSpinBox, QMessageBox, QMenu, QSizePolicy
)
from PySide6.QtGui import QColor, QCursor

from core.logger import logger
from core.date_utils import parse_date
from core.di import get_personel_service, get_izin_service
from ui.components.base_table_model import BaseTableModel
from ui.styles import DarkTheme
from ui.styles.components import STYLES as S
from ui.styles.icons import IconRenderer


AY_ISIMLERI = [
    "", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]


# ═══════════════════════════════════════════════
#  TABLO MODELİ
# ═══════════════════════════════════════════════

IZIN_COLUMNS = [
    ("AdSoyad",        "Ad Soyad",     3),
    ("IzinTipi",       "İzin Tipi",    2),
    ("BaslamaTarihi",  "Başlama",      2),
    ("BitisTarihi",    "Bitiş",        2),
    ("Gun",            "Gün",          1),
    ("Durum",          "Durum",        1),
]

DURUM_COLORS_BG = {
    "Onaylandı": QColor(34, 197, 94, 40),
    "Beklemede":  QColor(234, 179, 8, 40),
    "İptal":      QColor(239, 68, 68, 40),
}
DURUM_COLORS_FG = {
    "Onaylandı": QColor(DarkTheme.STATUS_SUCCESS),
    "Beklemede":  QColor(DarkTheme.STATUS_WARNING),
    "İptal":      QColor(DarkTheme.STATUS_ERROR),
}


class IzinTableModel(BaseTableModel):
    DATE_KEYS = frozenset({"BaslamaTarihi", "BitisTarihi"})
    def __init__(self, data=None, parent=None):
        super().__init__(IZIN_COLUMNS, data, parent)

    def _display(self, key, row):
        val = str(row.get(key, ""))
        if key in ("BaslamaTarihi", "BitisTarihi") and val:
            return self._fmt_date(val)
        return val

    def _bg(self, key, row):
        if key == "Durum":
            return DURUM_COLORS_BG.get(str(row.get("Durum", "")))
        return None

    def _fg(self, key, row):
        if key == "Durum":
            return self._status_fg(row.get("Durum", ""))
        return None

    def _align(self, key):
        if key in ("Gun", "Durum"):
            return Qt.AlignmentFlag.AlignCenter
        return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.UserRole:
            if not index.isValid():
                return None
            row = self.get_row(index.row()) or {}
            col_key = self._keys[index.column()]
            if col_key in ("BaslamaTarihi", "BitisTarihi"):
                d = parse_date(row.get(col_key, ""))
                return d.isoformat() if d else ""
            return str(row.get(col_key, ""))
        return super().data(index, role)


# ═══════════════════════════════════════════════
#  İZİN TAKİP SAYFASI
# ═══════════════════════════════════════════════

class IzinTakipPage(QWidget):

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(S["page"])
        self._db = db
        self._svc = get_izin_service(db) if db else None
        self._all_izin = []
        self._all_personel = []
        self._tatiller = []
        self._izin_tipleri = []           # [tip_adi, ...]
        self._izin_max_gun = {}           # {"Yıllık İzin": 20, ...}
        self._drawer = None
        self._drawer_width = 900
        self._drawer_ratio = 0.55
        self._drawer_min_width = 720
        self._drawer_max_width = 980

        self._setup_ui()
        self._connect_signals()

    # ═══════════════════════════════════════════
    #  UI
    # ═══════════════════════════════════════════

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 12, 20, 12)
        main.setSpacing(12)

        # ── FILTER BAR: Sadece Ay + Yıl ──
        filter_frame = QFrame()
        filter_frame.setStyleSheet(S["filter_panel"])
        fp = QHBoxLayout(filter_frame)
        fp.setContentsMargins(12, 8, 12, 8)
        fp.setSpacing(8)

        lbl_title = QLabel("Izin Takip")
        lbl_title.setStyleSheet(S.get("section_title") or "")
        fp.addWidget(lbl_title)

        self._add_sep(fp)

        lbl_ay = QLabel("Ay:")
        lbl_ay.setProperty("color-role", "muted")
        lbl_ay.setStyleSheet("font-size: 12px; background: transparent;")
        lbl_ay.style().unpolish(lbl_ay)
        lbl_ay.style().polish(lbl_ay)
        fp.addWidget(lbl_ay)

        self.cmb_ay = QComboBox()
        self.cmb_ay.setStyleSheet(S["combo_filter"])
        self.cmb_ay.setFixedWidth(110)
        self.cmb_ay.addItem("Tümü", 0)
        for i in range(1, 13):
            self.cmb_ay.addItem(AY_ISIMLERI[i], i)
        # Mevcut ayı seç
        self.cmb_ay.setCurrentIndex(date.today().month)
        fp.addWidget(self.cmb_ay)

        lbl_yil = QLabel("Yıl:")
        lbl_yil.setProperty("color-role", "muted")
        lbl_yil.setStyleSheet("font-size: 12px; background: transparent;")
        lbl_yil.style().unpolish(lbl_yil)
        lbl_yil.style().polish(lbl_yil)
        fp.addWidget(lbl_yil)

        self.cmb_yil = QComboBox()
        self.cmb_yil.setStyleSheet(S["combo_filter"])
        self.cmb_yil.setFixedWidth(80)
        current_year = date.today().year
        self.cmb_yil.addItem("Tümü", 0)
        for y in range(current_year, current_year - 6, -1):
            self.cmb_yil.addItem(str(y), y)
        # Mevcut yılı seç (index 1)
        self.cmb_yil.setCurrentIndex(1)
        fp.addWidget(self.cmb_yil)

        fp.addStretch()

        self.btn_yeni = QPushButton("Yeni Izin")
        self.btn_yeni.setStyleSheet(S["save_btn"])
        self.btn_yeni.setToolTip("Yeni İzin")
        self.btn_yeni.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_yeni, "plus", color=DarkTheme.TEXT_PRIMARY, size=14)
        fp.addWidget(self.btn_yeni)

        self.btn_yenile = QPushButton("Yenile")
        self.btn_yenile.setStyleSheet(S["refresh_btn"])
        self.btn_yenile.setToolTip("Yenile")
        self.btn_yenile.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_yenile, "sync", color=DarkTheme.TEXT_PRIMARY, size=14)
        fp.addWidget(self.btn_yenile)

        main.addWidget(filter_frame)

        # ── CONTENT ──
        content = QHBoxLayout()
        content.setSpacing(12)

        # ── TABLO PANELİ ──
        right = QWidget()
        right.setStyleSheet("background: transparent;")
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.setSpacing(8)

        grp_tablo = QGroupBox("Izin Kayitlari")
        grp_tablo.setStyleSheet(S["group"])
        tl = QVBoxLayout(grp_tablo)
        tl.setContentsMargins(8, 8, 8, 8)
        tl.setSpacing(6)

        self._model = IzinTableModel()
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setSortRole(Qt.ItemDataRole.UserRole)

        self.table = QTableView()
        self.table.setModel(self._proxy)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setStyleSheet(S["table"])
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        for i in range(len(IZIN_COLUMNS)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Gün
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Durum

        tl.addWidget(self.table, 1)

        # Footer
        foot = QHBoxLayout()
        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet(S["footer_label"])
        foot.addWidget(self.lbl_count)
        foot.addStretch()
        tl.addLayout(foot)

        right_l.addWidget(grp_tablo, 1)
        content.addWidget(right, 1)

        # ── DRAWER: İzin Giriş Paneli ──
        self._drawer = QFrame()
        self._drawer.setStyleSheet(
            f"background-color: {DarkTheme.BG_SECONDARY}; border-left: 1px solid {DarkTheme.BORDER_PRIMARY};"
        )
        self._drawer.setMaximumWidth(0)
        self._drawer.setMinimumWidth(0)

        drawer_lay = QVBoxLayout(self._drawer)
        drawer_lay.setContentsMargins(0, 0, 0, 0)
        drawer_lay.setSpacing(0)

        drawer_header = QFrame()
        drawer_header.setStyleSheet(
            f"background-color: {DarkTheme.BG_PRIMARY}; border-bottom: 1px solid {DarkTheme.BORDER_PRIMARY};"
        )
        header_lay = QHBoxLayout(drawer_header)
        header_lay.setContentsMargins(12, 12, 12, 12)

        lbl_drawer = QLabel("Izin Girisi")
        lbl_drawer.setProperty("color-role", "primary")
        lbl_drawer.setStyleSheet("font-size: 14px; font-weight: 600;")
        lbl_drawer.style().unpolish(lbl_drawer)
        lbl_drawer.style().polish(lbl_drawer)
        header_lay.addWidget(lbl_drawer)
        header_lay.addStretch()

        btn_drawer_close = QPushButton()
        btn_drawer_close.setFixedSize(32, 32)
        btn_drawer_close.setStyleSheet(S["close_btn"])
        btn_drawer_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(btn_drawer_close, "x", color=DarkTheme.TEXT_PRIMARY, size=16)
        btn_drawer_close.clicked.connect(self._close_drawer)
        header_lay.addWidget(btn_drawer_close)
        drawer_lay.addWidget(drawer_header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(S.get("scroll") or "")

        left = QWidget()
        left.setStyleSheet("background: transparent;")
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(12, 12, 12, 12)
        left_l.setSpacing(12)

        # ─ Personel Seçimi ─
        grp_personel = QGroupBox("Personel Secimi")
        grp_personel.setStyleSheet(S["group"])
        grp_personel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        pg = QGridLayout(grp_personel)
        pg.setSpacing(8)
        pg.setContentsMargins(12, 12, 12, 12)
        pg.setColumnStretch(0, 0)
        pg.setColumnStretch(1, 1)

        lbl_sinif = QLabel("Hizmet Sınıfı")
        lbl_sinif.setStyleSheet(S["label"])
        lbl_sinif.setFixedWidth(120)
        pg.addWidget(lbl_sinif, 0, 0)
        self.cmb_hizmet_sinifi = QComboBox()
        self.cmb_hizmet_sinifi.setStyleSheet(S["combo"])
        self.cmb_hizmet_sinifi.setMinimumWidth(200)
        self.cmb_hizmet_sinifi.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        pg.addWidget(self.cmb_hizmet_sinifi, 0, 1)

        lbl_p = QLabel("Personel")
        lbl_p.setStyleSheet(S["label"])
        lbl_p.setFixedWidth(120)
        pg.addWidget(lbl_p, 1, 0)
        self.cmb_personel = QComboBox()
        self.cmb_personel.setEditable(True)
        self.cmb_personel.setStyleSheet(S["combo"])
        self.cmb_personel.lineEdit().setPlaceholderText("İsim yazarak ara...")
        self.cmb_personel.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.cmb_personel.setMinimumWidth(200)
        self.cmb_personel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        pg.addWidget(self.cmb_personel, 1, 1)

        self.lbl_personel_info = QLabel("")
        self.lbl_personel_info.setStyleSheet(
            f"color: {DarkTheme.TEXT_SECONDARY}; font-size: 11px; background: transparent;"
        )
        pg.addWidget(self.lbl_personel_info, 2, 0, 1, 2)
        left_l.addWidget(grp_personel)

        # ─ İzin Giriş Formu ─
        grp_giris = QGroupBox("Yeni Izin Girisi")
        grp_giris.setStyleSheet(S["group"])
        grp_giris.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        fg = QGridLayout(grp_giris)
        fg.setSpacing(10)
        fg.setContentsMargins(12, 12, 12, 12)
        fg.setColumnStretch(0, 0)
        fg.setColumnStretch(1, 1)

        lbl_tip = QLabel("İzin Tipi")
        lbl_tip.setStyleSheet(S["label"])
        lbl_tip.setFixedWidth(120)
        fg.addWidget(lbl_tip, 0, 0)
        self.cmb_izin_tipi = QComboBox()
        self.cmb_izin_tipi.setStyleSheet(S["combo"])
        self.cmb_izin_tipi.setMinimumWidth(200)
        self.cmb_izin_tipi.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        fg.addWidget(self.cmb_izin_tipi, 0, 1)

        # Max gün uyarı etiketi
        self.lbl_max_gun = QLabel("")
        self.lbl_max_gun.setStyleSheet(S["max_label"])
        fg.addWidget(self.lbl_max_gun, 1, 0, 1, 2)

        lbl_bas = QLabel("Başlama / Süre")
        lbl_bas.setStyleSheet(S["label"])
        lbl_bas.setFixedWidth(120)
        fg.addWidget(lbl_bas, 2, 0)

        h_tarih = QHBoxLayout()
        h_tarih.setSpacing(8)
        self.dt_baslama = QDateEdit(QDate.currentDate())
        self.dt_baslama.setCalendarPopup(True)
        self.dt_baslama.setDisplayFormat("dd.MM.yyyy")
        self.dt_baslama.setStyleSheet(S["date"])
        self.dt_baslama.setMinimumWidth(160)
        self.dt_baslama.setMaximumWidth(240)
        self.dt_baslama.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._setup_calendar(self.dt_baslama)
        h_tarih.addWidget(self.dt_baslama, 2)

        lbl_gun = QLabel("Gün:")
        lbl_gun.setStyleSheet(S["label"])
        h_tarih.addWidget(lbl_gun)
        self.spn_gun = QSpinBox()
        self.spn_gun.setRange(1, 365)
        self.spn_gun.setValue(1)
        self.spn_gun.setStyleSheet(S["spin"])
        self.spn_gun.setFixedWidth(70)
        h_tarih.addWidget(self.spn_gun)
        h_tarih.addStretch()
        fg.addLayout(h_tarih, 2, 1)

        lbl_bit = QLabel("Bitiş (İşe Dönüş)")
        lbl_bit.setStyleSheet(S["label"])
        lbl_bit.setFixedWidth(120)
        fg.addWidget(lbl_bit, 3, 0)
        self.dt_bitis = QDateEdit()
        self.dt_bitis.setReadOnly(True)
        self.dt_bitis.setDisplayFormat("dd.MM.yyyy")
        self.dt_bitis.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.dt_bitis.setStyleSheet(S["date"])
        self.dt_bitis.setMinimumWidth(160)
        self.dt_bitis.setMaximumWidth(240)
        self.dt_bitis.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        fg.addWidget(self.dt_bitis, 3, 1)

        self.btn_kaydet = QPushButton("IZIN KAYDET")
        self.btn_kaydet.setStyleSheet(S["save_btn"])
        self.btn_kaydet.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_kaydet.setEnabled(False)
        IconRenderer.set_button_icon(self.btn_kaydet, "save", color=DarkTheme.TEXT_PRIMARY, size=14)
        fg.addWidget(self.btn_kaydet, 4, 0, 1, 2)
        left_l.addWidget(grp_giris)

        # ─ Bakiye Panosu ─
        grp_bakiye = QGroupBox("Izin Bakiyesi")
        grp_bakiye.setStyleSheet(S["group"])
        grp_bakiye.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        bg = QGridLayout(grp_bakiye)
        bg.setSpacing(4)
        bg.setContentsMargins(12, 12, 12, 12)
        bg.setColumnStretch(0, 0)
        bg.setColumnStretch(1, 1)

        lbl_y = QLabel("YILLIK İZİN")
        lbl_y.setStyleSheet(S["section_title"])
        bg.addWidget(lbl_y, 0, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)

        self.lbl_y_devir = self._add_stat(bg, 1, "Devir", "stat_value")
        self.lbl_y_hak = self._add_stat(bg, 2, "Hakediş", "stat_value")
        self.lbl_y_kul = self._add_stat(bg, 3, "Kullanılan", "stat_red")
        self.lbl_y_kal = self._add_stat(bg, 4, "KALAN", "stat_green")

        sep3 = QFrame(); sep3.setFixedHeight(1); sep3.setStyleSheet(S["separator"])
        bg.addWidget(sep3, 5, 0, 1, 2)

        lbl_s = QLabel("ŞUA İZNİ")
        lbl_s.setStyleSheet(S["section_title"])
        bg.addWidget(lbl_s, 6, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)

        self.lbl_s_hak = self._add_stat(bg, 7, "Hakediş", "stat_value")
        self.lbl_s_kul = self._add_stat(bg, 8, "Kullanılan", "stat_red")
        self.lbl_s_kal = self._add_stat(bg, 9, "KALAN", "stat_green")

        sep4 = QFrame(); sep4.setFixedHeight(1); sep4.setStyleSheet(S["separator"])
        bg.addWidget(sep4, 10, 0, 1, 2)

        self.lbl_diger = self._add_stat(bg, 11, "Rapor / Mazeret", "stat_value")
        bg.setRowStretch(12, 1)
        left_l.addWidget(grp_bakiye)
        left_l.addStretch()

        scroll.setWidget(left)
        drawer_lay.addWidget(scroll, 1)

        content.addWidget(self._drawer)
        main.addLayout(content, 1)

        # İlk bitiş hesapla
        self._calculate_bitis()

    def _calc_drawer_width(self) -> int:
        base = int(self.width() * self._drawer_ratio)
        return max(self._drawer_min_width, min(self._drawer_max_width, base))

    def _update_drawer_width(self, animated=False):
        self._drawer_width = self._calc_drawer_width()
        if not self._drawer:
            return
        if self._drawer.maximumWidth() <= 0:
            return
        if animated:
            anim = QPropertyAnimation(self._drawer, b"maximumWidth", self)
            anim.setDuration(180)
            anim.setStartValue(self._drawer.maximumWidth())
            anim.setEndValue(self._drawer_width)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.start(QPropertyAnimation.DeleteWhenStopped)
        else:
            self._drawer.setMaximumWidth(self._drawer_width)

    def _open_drawer(self):
        if not self._drawer:
            return
        target_width = self._calc_drawer_width()
        if self._drawer.maximumWidth() == target_width:
            return
        anim = QPropertyAnimation(self._drawer, b"maximumWidth", self)
        anim.setDuration(240)
        anim.setStartValue(0)
        anim.setEndValue(target_width)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)

    def _close_drawer(self):
        if not self._drawer or self._drawer.maximumWidth() == 0:
            return
        anim = QPropertyAnimation(self._drawer, b"maximumWidth", self)
        anim.setDuration(200)
        anim.setStartValue(self._drawer.maximumWidth())
        anim.setEndValue(0)
        anim.setEasingCurve(QEasingCurve.InCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_drawer_width(animated=False)

    def _open_new_form(self):
        self.spn_gun.setValue(1)
        self.dt_baslama.setDate(QDate.currentDate())
        self._calculate_bitis()
        self._open_drawer()

    # ── Yardımcı UI ──

    def _add_sep(self, layout):
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setFixedHeight(20)
        sep.setProperty("bg-role", "separator")
        sep.style().unpolish(sep)
        sep.style().polish(sep)
        layout.addWidget(sep)

    def _setup_calendar(self, date_edit):
        pass

    def _add_stat(self, grid, row, text, style_key):
        lbl = QLabel(text)
        lbl.setStyleSheet(S["stat_label"])
        grid.addWidget(lbl, row, 0)
        val = QLabel("—")
        val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        val.setStyleSheet(S[style_key])
        grid.addWidget(val, row, 1)
        return val

    # ═══════════════════════════════════════════
    #  SİNYALLER
    # ═══════════════════════════════════════════

    def _connect_signals(self):
        self.cmb_hizmet_sinifi.currentTextChanged.connect(self._on_sinif_changed)
        self.cmb_personel.currentIndexChanged.connect(self._on_personel_changed)
        self.cmb_izin_tipi.currentTextChanged.connect(self._on_izin_tipi_changed)
        self.dt_baslama.dateChanged.connect(self._calculate_bitis)
        self.spn_gun.valueChanged.connect(self._calculate_bitis)
        self.btn_kaydet.clicked.connect(self._on_save)
        self.btn_yeni.clicked.connect(self._open_new_form)
        self.btn_yenile.clicked.connect(self.load_data)
        self.cmb_ay.currentIndexChanged.connect(self._apply_filters)
        self.cmb_yil.currentIndexChanged.connect(self._apply_filters)

    # ═══════════════════════════════════════════
    #  VERİ YÜKLEME
    # ═══════════════════════════════════════════

    def load_data(self):
        if not self._db:
            return
        try:
            personel_svc = get_personel_service(self._db)
            izin_svc = get_izin_service(self._db)

            # ── Personeller ──
            self._all_personel = personel_svc.get_all()
            aktif = [p for p in self._all_personel
                     if str(p.get("Durum", "")).strip() == "Aktif"]
            aktif.sort(key=lambda p: str(p.get("AdSoyad", "")))

            # Hizmet sınıfı listesi
            siniflar = sorted(set(
                str(p.get("HizmetSinifi") or "").strip()
                for p in aktif if str(p.get("HizmetSinifi") or "").strip()
            ))
            current_sinif = self.cmb_hizmet_sinifi.currentText()
            self.cmb_hizmet_sinifi.blockSignals(True)
            self.cmb_hizmet_sinifi.clear()
            self.cmb_hizmet_sinifi.addItem("Tümü")
            self.cmb_hizmet_sinifi.addItems(siniflar)
            if current_sinif:
                idx = self.cmb_hizmet_sinifi.findText(current_sinif)
                if idx >= 0:
                    self.cmb_hizmet_sinifi.setCurrentIndex(idx)
            self.cmb_hizmet_sinifi.blockSignals(False)

            # Personel combo (sınıf filtresine göre)
            self._fill_personel_combo(aktif)

            # ── İzin Tipleri: Sabitler → Kod = "İzin_Tipi" ──
            sabitler = registry.get("Sabitler").get_all()
            self._izin_max_gun = {}
            tip_adlari = []

            for r in sabitler:
                if str(r.get("Kod", "")).strip() != "İzin_Tipi":
                    continue
                tip_adi = str(r.get("MenuEleman", "")).strip()
                if not tip_adi:
                    continue
                tip_adlari.append(tip_adi)
                # Aciklama sütununda max gün sayısı
                aciklama = str(r.get("Aciklama", "")).strip()
                if aciklama:
                    try:
                        self._izin_max_gun[tip_adi] = int(aciklama)
                    except ValueError:
                        pass

            tip_adlari.sort()
            if not tip_adlari:
                tip_adlari = [
                    "Yıllık İzin", "Şua İzni", "Mazeret İzni", "Sağlık Raporu",
                    "Ücretsiz İzin", "Doğum İzni", "Babalık İzni",
                    "Evlilik İzni", "Ölüm İzni", "Diğer",
                ]

            self._izin_tipleri = tip_adlari
            self.cmb_izin_tipi.blockSignals(True)
            self.cmb_izin_tipi.clear()
            self.cmb_izin_tipi.addItems(tip_adlari)
            self.cmb_izin_tipi.blockSignals(False)
            self._on_izin_tipi_changed(self.cmb_izin_tipi.currentText())

            # ── Tatiller ──
            try:
                tatiller = registry.get("Tatiller").get_all()
                self._tatiller = []
                for r in tatiller:
                    t = str(r.get("Tarih", "")).strip()
                    d = parse_date(t)
                    if d:
                        self._tatiller.append(d.isoformat())
            except Exception:
                self._tatiller = []

            # ── İzin Kayıtları ──
            self._all_izin = registry.get("Izin_Giris").get_all()

            # Yeniden eskiye sırala (çoklu tarih formatı)
            self._all_izin.sort(
                key=lambda r: parse_date(r.get("BaslamaTarihi", "")) or date.min,
                reverse=True
            )

            self._apply_filters()

            logger.info(f"İzin takip yüklendi: {len(self._all_izin)} kayıt, "
                        f"{len(aktif)} aktif personel, "
                        f"{len(tip_adlari)} izin tipi, "
                        f"{len(self._izin_max_gun)} max gün tanımlı")

        except Exception as e:
            logger.error(f"İzin takip yükleme hatası: {e}")

    # ═══════════════════════════════════════════
    #  PERSONEL COMBO (HİZMET SINIFI FİLTRELİ)
    # ═══════════════════════════════════════════

    def _fill_personel_combo(self, aktif=None):
        """Hizmet sınıfı filtresine göre personel comboyu doldur."""
        if aktif is None:
            aktif = [p for p in self._all_personel
                     if str(p.get("Durum", "")).strip() == "Aktif"]
            aktif.sort(key=lambda p: str(p.get("AdSoyad", "")))

        sinif_filtre = self.cmb_hizmet_sinifi.currentText()
        if sinif_filtre and sinif_filtre != "Tümü":
            aktif = [p for p in aktif
                     if str(p.get("HizmetSinifi") or "").strip() == sinif_filtre]

        current_tc = self.cmb_personel.currentData()
        self.cmb_personel.blockSignals(True)
        self.cmb_personel.clear()
        self.cmb_personel.addItem("— Tüm Personel —", "")
        for p in aktif:
            ad = p.get("AdSoyad", "")
            tc = p.get("KimlikNo", "")
            sinif = p.get("HizmetSinifi", "")
            self.cmb_personel.addItem(f"{ad}  ({sinif})", tc)

        if current_tc:
            idx = self.cmb_personel.findData(current_tc)
            if idx >= 0:
                self.cmb_personel.setCurrentIndex(idx)
        self.cmb_personel.blockSignals(False)

    def _on_sinif_changed(self, text):
        """Hizmet sınıfı değiştiğinde personel combosunu yeniden doldur."""
        self._fill_personel_combo()
        self._on_personel_changed(self.cmb_personel.currentIndex())

    def _on_personel_changed(self, idx):
        """Personel değiştiğinde: bakiye güncelle + tablo filtrele."""
        tc = self.cmb_personel.currentData()
        self.btn_kaydet.setEnabled(bool(tc))

        if not tc:
            self.lbl_personel_info.setText("")
            self._clear_bakiye()
        else:
            p = next((p for p in self._all_personel
                      if p.get("KimlikNo") == tc), None)
            if p:
                gorev = p.get("GorevYeri", "")
                sinif = p.get("HizmetSinifi", "")
                self.lbl_personel_info.setText(f"TC: {tc}  |  {sinif}  |  {gorev}")
            self._load_bakiye(tc)

        # Tablo filtresi de yenile (personel seçimi dahil)
        self._apply_filters()

    # ═══════════════════════════════════════════
    #  İZİN TİPİ DEĞİŞİNCE → MAX GÜN
    # ═══════════════════════════════════════════

    def _on_izin_tipi_changed(self, tip_text):
        """Seçili izin tipinin max gün sınırını uygula."""
        tip_text = str(tip_text).strip()
        max_gun = self._izin_max_gun.get(tip_text, 0)

        if max_gun and max_gun > 0:
            self.spn_gun.setMaximum(max_gun)
            if self.spn_gun.value() > max_gun:
                self.spn_gun.setValue(max_gun)
            self.lbl_max_gun.setText(f"Bu izin tipi maks. {max_gun} gun")
        else:
            self.spn_gun.setMaximum(365)
            self.lbl_max_gun.setText("")

    # ═══════════════════════════════════════════
    #  BAKİYE
    # ═══════════════════════════════════════════

    def _load_bakiye(self, tc):
        if not self._db or not tc:
            self._clear_bakiye()
            return
        try:
            izin_svc = get_izin_service(self._db)
            izin = izin_svc.get_izin_bilgi_repo().get_by_id(tc)
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
                d = parse_date(r.get("BaslamaTarihi", ""))
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
            key=lambda r: parse_date(r.get("BaslamaTarihi", "")) or date.min,
            reverse=True
        )

        self._model.set_data(filtered)

        # Varsayılan sıralama: Başlama sütunu (index 2) descending
        self.table.sortByColumn(2, Qt.SortOrder.DescendingOrder)

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

    def _should_set_pasif(self, izin_tipi: str, gun: int) -> bool:
        tip = str(izin_tipi or "").strip().lower()
        return gun > 30 or "aylıksız" in tip or "ucretsiz" in tip or "ücretsiz" in tip

    def _set_personel_pasif(self, registry, tc: str, izin_tipi: str, gun: int) -> None:
        if not tc or not self._should_set_pasif(izin_tipi, gun):
            return
        try:
            registry.get("Personel").update(tc, {"Durum": "Pasif"})
            logger.info(f"Personel pasif yapıldı: {tc} — {izin_tipi} — {gun} gün")
        except Exception as e:
            logger.error(f"Personel durum güncelleme hatası: {e}")

    # ═══════════════════════════════════════════
    #  KAYDET
    # ═══════════════════════════════════════════

    def _on_save(self):
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

        # ═══════════════════════════════════════════════
        # 🔧 TARİH ÇAKIŞMA KONTROLÜ
        # ═══════════════════════════════════════════════
        yeni_bas = parse_date(baslama)
        yeni_bit = parse_date(bitis)

        if not yeni_bas or not yeni_bit:
            QMessageBox.critical(self, "Hata", "Tarih formatı hatalı.")
            return

        # Aynı personelin mevcut izinlerini kontrol et
        for kayit in self._all_izin:
            # İptal edilen kayıtları atla
            durum = str(kayit.get("Durum", "")).strip()
            if durum == "İptal":
                continue

            # Başka personel ise atla
            vt_tc = str(kayit.get("Personelid", "")).strip()
            if vt_tc != tc:
                continue

            # Tarih çakışması kontrolü
            vt_bas = parse_date(kayit.get("BaslamaTarihi", ""))
            vt_bit = parse_date(kayit.get("BitisTarihi", ""))

            if vt_bas and vt_bit:
                # Çakışma formülü: (yeni_bas <= vt_bit) AND (yeni_bit >= vt_bas)
                if (yeni_bas <= vt_bit) and (yeni_bit >= vt_bas):
                    QMessageBox.warning(
                        self, "Cakisma Var!",
                        f"{ad} personeli {vt_bas.strftime('%d.%m.%Y')} - "
                        f"{vt_bit.strftime('%d.%m.%Y')} tarihlerinde zaten izinli!\n\n"
                        f"İzin Tipi: {kayit.get('IzinTipi', '')}\n"
                        f"Durum: {durum}\n\n"
                        f"Lütfen farklı bir tarih seçiniz."
                    )
                    return

        # ═══════════════════════════════════════════════
        # 🔧 BAKİYE KONTROLÜ (Yıllık İzin ve Şua için)
        # ═══════════════════════════════════════════════
        if izin_tipi in ["Yıllık İzin", "Şua İzni"]:
            try:
                izin_repo = izin_svc.get_izin_bilgi_repo()
                izin_bilgi = izin_repo.get_by_id(tc) if izin_repo else None

                if izin_bilgi:
                    if izin_tipi == "Yıllık İzin":
                        kalan = float(izin_bilgi.get("YillikKalan", 0))
                        if gun > kalan:
                            cevap = QMessageBox.question(
                                self, "Bakiye Yetersiz",
                                f"{ad} personelinin yıllık izin bakiyesi: {kalan} gün\n"
                                f"Girilen gün sayısı: {gun} gün\n\n"
                                f"Eksik: {gun - kalan} gün\n\n"
                                f"Yine de kaydetmek istiyor musunuz?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
                            )
                            if cevap != QMessageBox.StandardButton.Yes:
                                return

                    elif izin_tipi == "Şua İzni":
                        kalan = float(izin_bilgi.get("SuaKalan", 0))
                        if gun > kalan:
                            cevap = QMessageBox.question(
                                self, "Bakiye Yetersiz",
                                f"{ad} personelinin şua izin bakiyesi: {kalan} gün\n"
                                f"Girilen gün sayısı: {gun} gün\n\n"
                                f"Eksik: {gun - kalan} gün\n\n"
                                f"Yine de kaydetmek istiyor musunuz?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
                            )
                            if cevap != QMessageBox.StandardButton.Yes:
                                return
            except Exception as e:
                logger.error(f"Bakiye kontrolü hatası: {e}")

        # ═══════════════════════════════════════════════
        # KAYDET
        # ═══════════════════════════════════════════════
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
            from core.di import get_registry
            registry = get_registry(self._db)
            registry.get("Izin_Giris").insert(kayit)
            logger.info(f"İzin kaydedildi: {izin_id} — {ad} — {izin_tipi} — {gun} gün")

            # ═══════════════════════════════════════════════
            # 🔧 BAKİYE DÜŞME (Otomatik)
            # ═══════════════════════════════════════════════
            self._bakiye_dus(registry, tc, izin_tipi, gun)

            # ═══════════════════════════════════════════════
            # 🔧 UZUN / AYLIKSIZ İZİN → PERSONEL PASİF
            # ═══════════════════════════════════════════════
            self._set_personel_pasif(registry, tc, izin_tipi, gun)

            QMessageBox.information(
                self, "Başarılı",
                f"{ad} için {gun} gün {izin_tipi} kaydedildi.\n"
                f"Başlama: {self.dt_baslama.date().toString('dd.MM.yyyy')}\n"
                f"İşe Dönüş: {self.dt_bitis.date().toString('dd.MM.yyyy')}"
            )

            self.load_data()
            self.spn_gun.setValue(1)
            self.dt_baslama.setDate(QDate.currentDate())

        except Exception as e:
            logger.error(f"İzin kaydetme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"İzin kaydedilemedi:\n{e}")

    def _bakiye_dus(self, registry, tc, izin_tipi, gun):
        """Bakiyeden otomatik düş (Yıllık İzin / Şua İzni / Rapor-Mazeret)."""
        try:
            izin_bilgi = registry.get("Izin_Bilgi").get_by_id(tc)
            if not izin_bilgi:
                return

            if izin_tipi == "Yıllık İzin":
                mevcut_kul = float(izin_bilgi.get("YillikKullanilan", 0))
                yeni_kul = mevcut_kul + gun
                mevcut_kal = float(izin_bilgi.get("YillikKalan", 0))
                yeni_kal = mevcut_kal - gun

                registry.get("Izin_Bilgi").update(tc, {
                    "YillikKullanilan": yeni_kul,
                    "YillikKalan": yeni_kal
                })
                logger.info(f"Yıllık izin bakiye düştü: {tc} → {gun} gün (Kalan: {yeni_kal})")

            elif izin_tipi == "Şua İzni":
                mevcut_kul = float(izin_bilgi.get("SuaKullanilan", 0))
                yeni_kul = mevcut_kul + gun
                mevcut_kal = float(izin_bilgi.get("SuaKalan", 0))
                yeni_kal = mevcut_kal - gun

                registry.get("Izin_Bilgi").update(tc, {
                    "SuaKullanilan": yeni_kul,
                    "SuaKalan": yeni_kal
                })
                logger.info(f"Şua izin bakiye düştü: {tc} → {gun} gün (Kalan: {yeni_kal})")

            elif izin_tipi in ["Rapor", "Mazeret İzni"]:
                mevcut_top = float(izin_bilgi.get("RaporMazeretTop", 0))
                yeni_top = mevcut_top + gun
                registry.get("Izin_Bilgi").update(tc, {
                    "RaporMazeretTop": yeni_top
                })
                logger.info(f"Rapor/Mazeret toplam arttı: {tc} → +{gun} gün (Toplam: {yeni_top})")

        except Exception as e:
            logger.error(f"Bakiye düşme hatası: {e}")

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
            act_iptal = menu.addAction("Izni Iptal Et")
            act_iptal.triggered.connect(lambda: self._iptal_izin(izin_id, ad))

        if durum == "Beklemede":
            act_onayla = menu.addAction("Onayla")
            act_onayla.triggered.connect(lambda: self._durum_degistir(izin_id, ad, "Onaylandı"))

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _iptal_izin(self, izin_id, ad):
        cevap = QMessageBox.question(
            self, "İzin İptal",
            f"{ad} personelinin bu izni iptal edilsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        )
        if cevap == QMessageBox.StandardButton.Yes:
            self._durum_degistir(izin_id, ad, "İptal")

    def _durum_degistir(self, izin_id, ad, yeni_durum):
        try:
            from core.di import get_registry
            registry = get_registry(self._db)
            registry.get("Izin_Giris").update(izin_id, {"Durum": yeni_durum})
            logger.info(f"İzin durum değişti: {izin_id} → {yeni_durum}")
            self.load_data()
        except Exception as e:
            logger.error(f"İzin durum hatası: {e}")
            QMessageBox.critical(self, "Hata", f"İşlem hatası:\n{e}")





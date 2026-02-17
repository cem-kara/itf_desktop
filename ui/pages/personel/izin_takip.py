# -*- coding: utf-8 -*-
"""
İzin Takip Sayfası (Sidebar menüden erişilir)
- Sol: Personel seçimi (HizmetSınıfı filtreli) + Yeni izin girişi + Bakiye
- Sağ: İzin kayıtları tablosu (Ay/Yıl filtreli + seçili personel filtreli)
"""
import uuid
from datetime import datetime, date, timedelta
from PySide6.QtCore import (
    Qt, QDate, QSortFilterProxyModel, QModelIndex, QAbstractTableModel
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDateEdit, QSpinBox, QFrame, QGroupBox,
    QGridLayout, QTableView, QHeaderView,
    QAbstractSpinBox, QMessageBox, QMenu
)
from PySide6.QtGui import QColor, QCursor

from core.logger import logger
from core.date_utils import parse_date as parse_any_date, to_ui_date
from ui.theme_manager import ThemeManager

def _parse_date(val):
    """Merkezi date_utils üzerinden tarih parse eder."""
    return parse_any_date(val)

def _format_date_display(val):
    """Tarih string → dd.MM.yyyy gösterim."""
    return to_ui_date(val)


# ─── W11 Dark Glass Stiller (MERKEZİ KAYNAKTAN) ───
S = ThemeManager.get_all_component_styles()

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
    "Onaylandı": QColor("#4ade80"),
    "Beklemede":  QColor("#facc15"),
    "İptal":      QColor("#f87171"),
}


class IzinTableModel(QAbstractTableModel):
    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self._data = data or []
        self._keys = [c[0] for c in IZIN_COLUMNS]
        self._headers = [c[1] for c in IZIN_COLUMNS]

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(IZIN_COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._data[index.row()]
        col_key = self._keys[index.column()]

        if role == Qt.DisplayRole:
            val = str(row.get(col_key, ""))
            if col_key in ("BaslamaTarihi", "BitisTarihi") and val:
                return _format_date_display(val)
            return val

        if role == Qt.BackgroundRole and col_key == "Durum":
            return DURUM_COLORS_BG.get(str(row.get("Durum", "")))

        if role == Qt.ForegroundRole and col_key == "Durum":
            return DURUM_COLORS_FG.get(str(row.get("Durum", "")), QColor("#8b8fa3"))

        if role == Qt.TextAlignmentRole:
            if col_key in ("Gun", "Durum"):
                return Qt.AlignCenter
            return Qt.AlignVCenter | Qt.AlignLeft

        # Sıralama için ham ISO değer
        if role == Qt.UserRole:
            if col_key in ("BaslamaTarihi", "BitisTarihi"):
                d = _parse_date(row.get(col_key, ""))
                return d.isoformat() if d else ""
            return str(row.get(col_key, ""))

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None

    def set_data(self, data):
        self.beginResetModel()
        self._data = data or []
        self.endResetModel()

    def get_row(self, row_idx):
        if 0 <= row_idx < len(self._data):
            return self._data[row_idx]
        return None


# ═══════════════════════════════════════════════
#  İZİN TAKİP SAYFASI
# ═══════════════════════════════════════════════

class IzinTakipPage(QWidget):

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(S["page"])
        self._db = db
        self._all_izin = []
        self._all_personel = []
        self._tatiller = []
        self._izin_tipleri = []           # [tip_adi, ...]
        self._izin_max_gun = {}           # {"Yıllık İzin": 20, ...}

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

        lbl_title = QLabel("📅 İzin Takip")
        lbl_title.setStyleSheet("color: #6bd3ff; font-size: 14px; font-weight: bold; background: transparent;")
        fp.addWidget(lbl_title)

        self._add_sep(fp)

        lbl_ay = QLabel("Ay:")
        lbl_ay.setStyleSheet("color: #8b8fa3; font-size: 12px; background: transparent;")
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
        lbl_yil.setStyleSheet("color: #8b8fa3; font-size: 12px; background: transparent;")
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

        self.btn_yenile = QPushButton("⟳ Yenile")
        self.btn_yenile.setStyleSheet(S["refresh_btn"])
        self.btn_yenile.setToolTip("Yenile")
        self.btn_yenile.setCursor(QCursor(Qt.PointingHandCursor))
        fp.addWidget(self.btn_yenile)

        self._add_sep(fp)

        self.btn_kapat = QPushButton("✕ Kapat")
        self.btn_kapat.setToolTip("Kapat")
        self.btn_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kapat.setStyleSheet(S["close_btn"])
        fp.addWidget(self.btn_kapat)

        main.addWidget(filter_frame)

        # ── SPLITTER ──
        content = QHBoxLayout()
        content.setSpacing(12)

        # ── SOL PANEL ──
        left = QWidget()
        left.setStyleSheet("background: transparent;")
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(0, 0, 0, 0)
        left_l.setSpacing(12)

        # ─ Personel Seçimi ─
        grp_personel = QGroupBox("👤  Personel Seçimi")
        grp_personel.setStyleSheet(S["group"])
        pg = QGridLayout(grp_personel)
        pg.setSpacing(8)
        pg.setContentsMargins(12, 12, 12, 12)

        lbl_sinif = QLabel("Hizmet Sınıfı")
        lbl_sinif.setStyleSheet(S["label"])
        pg.addWidget(lbl_sinif, 0, 0)
        self.cmb_hizmet_sinifi = QComboBox()
        self.cmb_hizmet_sinifi.setStyleSheet(S["combo"])
        pg.addWidget(self.cmb_hizmet_sinifi, 0, 1)

        lbl_p = QLabel("Personel")
        lbl_p.setStyleSheet(S["label"])
        pg.addWidget(lbl_p, 1, 0)
        self.cmb_personel = QComboBox()
        self.cmb_personel.setEditable(True)
        self.cmb_personel.setStyleSheet(S["combo"])
        self.cmb_personel.lineEdit().setPlaceholderText("İsim yazarak ara...")
        self.cmb_personel.setInsertPolicy(QComboBox.NoInsert)
        pg.addWidget(self.cmb_personel, 1, 1)

        self.lbl_personel_info = QLabel("")
        self.lbl_personel_info.setStyleSheet("color: #6bd3ff; font-size: 11px; background: transparent;")
        pg.addWidget(self.lbl_personel_info, 2, 0, 1, 2)

        left_l.addWidget(grp_personel)

        # ─ İzin Giriş Formu ─
        grp_giris = QGroupBox("📝  Yeni İzin Girişi")
        grp_giris.setStyleSheet(S["group"])
        fg = QGridLayout(grp_giris)
        fg.setSpacing(10)
        fg.setContentsMargins(12, 12, 12, 12)

        lbl_tip = QLabel("İzin Tipi")
        lbl_tip.setStyleSheet(S["label"])
        fg.addWidget(lbl_tip, 0, 0)
        self.cmb_izin_tipi = QComboBox()
        self.cmb_izin_tipi.setStyleSheet(S["combo"])
        fg.addWidget(self.cmb_izin_tipi, 0, 1)

        # Max gün uyarı etiketi
        self.lbl_max_gun = QLabel("")
        self.lbl_max_gun.setStyleSheet(S["max_label"])
        fg.addWidget(self.lbl_max_gun, 1, 0, 1, 2)

        lbl_bas = QLabel("Başlama / Süre")
        lbl_bas.setStyleSheet(S["label"])
        fg.addWidget(lbl_bas, 2, 0)

        h_tarih = QHBoxLayout()
        h_tarih.setSpacing(8)
        self.dt_baslama = QDateEdit(QDate.currentDate())
        self.dt_baslama.setCalendarPopup(True)
        self.dt_baslama.setDisplayFormat("dd.MM.yyyy")
        self.dt_baslama.setStyleSheet(S["date"])
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
        fg.addLayout(h_tarih, 2, 1)

        lbl_bit = QLabel("Bitiş (İşe Dönüş)")
        lbl_bit.setStyleSheet(S["label"])
        fg.addWidget(lbl_bit, 3, 0)
        self.dt_bitis = QDateEdit()
        self.dt_bitis.setReadOnly(True)
        self.dt_bitis.setDisplayFormat("dd.MM.yyyy")
        self.dt_bitis.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.dt_bitis.setStyleSheet(S["date"])
        fg.addWidget(self.dt_bitis, 3, 1)

        self.btn_kaydet = QPushButton("✓  İZİN KAYDET")
        self.btn_kaydet.setStyleSheet(S["save_btn"])
        self.btn_kaydet.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kaydet.setEnabled(False)
        fg.addWidget(self.btn_kaydet, 4, 0, 1, 2)

        left_l.addWidget(grp_giris)

        # ─ Bakiye Panosu ─
        grp_bakiye = QGroupBox("📊  İzin Bakiyesi")
        grp_bakiye.setStyleSheet(S["group"])
        bg = QGridLayout(grp_bakiye)
        bg.setSpacing(4)
        bg.setContentsMargins(12, 12, 12, 12)

        lbl_y = QLabel("YILLIK İZİN")
        lbl_y.setStyleSheet(S["section_title"])
        bg.addWidget(lbl_y, 0, 0, 1, 2, Qt.AlignCenter)

        self.lbl_y_devir = self._add_stat(bg, 1, "Devir", "stat_value")
        self.lbl_y_hak = self._add_stat(bg, 2, "Hakediş", "stat_value")
        self.lbl_y_kul = self._add_stat(bg, 3, "Kullanılan", "stat_red")
        self.lbl_y_kal = self._add_stat(bg, 4, "KALAN", "stat_green")

        sep3 = QFrame(); sep3.setFixedHeight(1); sep3.setStyleSheet(S["separator"])
        bg.addWidget(sep3, 5, 0, 1, 2)

        lbl_s = QLabel("ŞUA İZNİ")
        lbl_s.setStyleSheet(S["section_title"])
        bg.addWidget(lbl_s, 6, 0, 1, 2, Qt.AlignCenter)

        self.lbl_s_hak = self._add_stat(bg, 7, "Hakediş", "stat_value")
        self.lbl_s_kul = self._add_stat(bg, 8, "Kullanılan", "stat_red")
        self.lbl_s_kal = self._add_stat(bg, 9, "KALAN", "stat_green")

        sep4 = QFrame(); sep4.setFixedHeight(1); sep4.setStyleSheet(S["separator"])
        bg.addWidget(sep4, 10, 0, 1, 2)

        self.lbl_diger = self._add_stat(bg, 11, "Rapor / Mazeret", "stat_value")
        bg.setRowStretch(12, 1)
        left_l.addWidget(grp_bakiye)
        left_l.addStretch()

        # ── SAĞ PANEL: Tablo ──
        right = QWidget()
        right.setStyleSheet("background: transparent;")
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.setSpacing(8)

        grp_tablo = QGroupBox("📋  İzin Kayıtları")
        grp_tablo.setStyleSheet(S["group"])
        tl = QVBoxLayout(grp_tablo)
        tl.setContentsMargins(8, 8, 8, 8)
        tl.setSpacing(6)

        self._model = IzinTableModel()
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setSortRole(Qt.UserRole)

        self.table = QTableView()
        self.table.setModel(self._proxy)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setStyleSheet(S["table"])
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        for i in range(len(IZIN_COLUMNS)):
            header.setSectionResizeMode(i, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Gün
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Durum

        tl.addWidget(self.table, 1)

        # Footer
        foot = QHBoxLayout()
        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet(S["footer_label"])
        foot.addWidget(self.lbl_count)
        foot.addStretch()
        tl.addLayout(foot)

        right_l.addWidget(grp_tablo, 1)

        # Splitter oranları
        left.setFixedWidth(430)
        content.addWidget(left)
        content.addWidget(right, 1)
        main.addLayout(content, 1)

        # İlk bitiş hesapla
        self._calculate_bitis()

    # ── Yardımcı UI ──

    def _add_sep(self, layout):
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setFixedHeight(20)
        sep.setStyleSheet("background-color: rgba(255,255,255,0.08);")
        layout.addWidget(sep)

    def _setup_calendar(self, date_edit):
        ThemeManager.setup_calendar_popup(date_edit)

    def _add_stat(self, grid, row, text, style_key):
        lbl = QLabel(text)
        lbl.setStyleSheet(S["stat_label"])
        grid.addWidget(lbl, row, 0)
        val = QLabel("—")
        val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
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
            from core.di import get_registry
            registry = get_registry(self._db)

            # ── Personeller ──
            self._all_personel = registry.get("Personel").get_all()
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
                    d = _parse_date(t)
                    if d:
                        self._tatiller.append(d.isoformat())
            except Exception:
                self._tatiller = []

            # ── İzin Kayıtları ──
            self._all_izin = registry.get("Izin_Giris").get_all()

            # Yeniden eskiye sırala (çoklu tarih formatı)
            self._all_izin.sort(
                key=lambda r: _parse_date(r.get("BaslamaTarihi", "")) or date.min,
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
            self.lbl_max_gun.setText(f"⚠ Bu izin tipi maks. {max_gun} gün")
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
            from core.di import get_registry
            registry = get_registry(self._db)
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
        yeni_bas = _parse_date(baslama)
        yeni_bit = _parse_date(bitis)

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
            vt_bas = _parse_date(kayit.get("BaslamaTarihi", ""))
            vt_bit = _parse_date(kayit.get("BitisTarihi", ""))

            if vt_bas and vt_bit:
                # Çakışma formülü: (yeni_bas <= vt_bit) AND (yeni_bit >= vt_bas)
                if (yeni_bas <= vt_bit) and (yeni_bit >= vt_bas):
                    QMessageBox.warning(
                        self, "❌ Çakışma Var!",
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
                from core.di import get_registry
                registry = get_registry(self._db)
                izin_bilgi = registry.get("Izin_Bilgi").get_by_id(tc)

                if izin_bilgi:
                    if izin_tipi == "Yıllık İzin":
                        kalan = float(izin_bilgi.get("YillikKalan", 0))
                        if gun > kalan:
                            cevap = QMessageBox.question(
                                self, "⚠️ Bakiye Yetersiz",
                                f"{ad} personelinin yıllık izin bakiyesi: {kalan} gün\n"
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
                                self, "⚠️ Bakiye Yetersiz",
                                f"{ad} personelinin şua izin bakiyesi: {kalan} gün\n"
                                f"Girilen gün sayısı: {gun} gün\n\n"
                                f"Eksik: {gun - kalan} gün\n\n"
                                f"Yine de kaydetmek istiyor musunuz?",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                            )
                            if cevap != QMessageBox.Yes:
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
            from core.di import get_registry
            registry = get_registry(self._db)
            registry.get("Izin_Giris").update(izin_id, {"Durum": yeni_durum})
            logger.info(f"İzin durum değişti: {izin_id} → {yeni_durum}")
            self.load_data()
        except Exception as e:
            logger.error(f"İzin durum hatası: {e}")
            QMessageBox.critical(self, "Hata", f"İşlem hatası:\n{e}")



"""
İzin Takip Ana Sayfası - Sprint 3.1 Refactored
==============================================

Sorumluluklar:
- UI layout (tablo + drawer)
- Event handling (combo seçimi, tarih değişimi, form kaydetme)
- Signal'lar (detay/iptal/kaydet işlemleri)

İş Mantığı: IzinCalculator, Repository, Service'te
"""

import uuid
from datetime import date, QDate, timedelta
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QGridLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QPushButton,
    QComboBox, QDateEdit, QSpinBox, QScrollArea, QFrame, QAbstractSpinBox,
    QMessageBox, QMenu, QPropertyAnimation, QEasingCurve
)
from PySide6.QtCore import (
    Qt, Signal, QDate as QtQDate, QRect, pyqtSignal, pyqtSlot
)
from PySide6.QtGui import QCursor, QColor
from PySide6.QtCharts import QChart

from core.log_manager import get_logger
from ui.styles import DarkTheme, IconRenderer
from ui.styles.components import STYLES as S

from .models.izin_model import IzinTableModel
from .services.izin_calculator import IzinCalculator

logger = get_logger(__name__)


class IzinTakipPage(QWidget):
    """
    İzin Takip Sayfası

    Layout:
    ┌─────────────────────────────────────────────┐
    │ [Filtreler: Ay, Yıl] [Yeni] [Yenile]      │
    ├─────────────────────────────────────────────┤
    │                                             │
    │  [Tablo]            │  [Drawer: Yeni İzin] │
    │                     │                       │
    │                     │ • Personel Seçimi     │
    │                     │ • İzin Formu          │
    │                     │ • Bakiye Panosu       │
    │                     │                       │
    └─────────────────────────────────────────────┘
    """

    # Signaller
    kaydet_requested = pyqtSignal(dict)  # İzin verileri
    iptal_requested = pyqtSignal(str, str)  # Izin ID, Ad Soyad

    # Drawer ayarları
    _drawer_ratio = 0.4
    _drawer_min_width = 280
    _drawer_max_width = 480

    def __init__(self, db_path: str = "", parent=None):
        super().__init__(parent)
        self._db = db_path
        self._drawer = None
        self._drawer_width = 350
        self._model = IzinTableModel()
        self._calculator = IzinCalculator()

        # Veri
        self._all_izin = []
        self._all_personel = []
        self._izin_tipleri = []
        self._izin_max_gun = {}
        self._tatiller = []

        # Ay/Yıl sabitleri
        self.AY_ISIMLERI = [
            "—", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
            "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
        ]

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """UI yapısını oluştur."""
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # TOOLBAR: Filtreler + Butonlar
        toolbar = QFrame()
        toolbar.setStyleSheet(
            f"background-color: {DarkTheme.BG_PRIMARY}; "
            f"border-bottom: 1px solid {DarkTheme.BORDER_PRIMARY};"
        )
        toolbar.setFixedHeight(50)
        tbl = QHBoxLayout(toolbar)
        tbl.setContentsMargins(12, 6, 12, 6)
        tbl.setSpacing(8)

        # Ay filtresi
        lbl_ay = QLabel("Ay:")
        lbl_ay.setStyleSheet(S["label"])
        tbl.addWidget(lbl_ay)
        self.cmb_ay = QComboBox()
        self.cmb_ay.setStyleSheet(S["combo"])
        self.cmb_ay.setMaximumWidth(120)
        # Ay listesi: (display, data) → display="—", data=0 vb.
        self.cmb_ay.addItem("Tümü", 0)
        for i in range(1, 13):
            self.cmb_ay.addItem(self.AY_ISIMLERI[i], i)
        tbl.addWidget(self.cmb_ay)

        # Yıl filtresi
        lbl_yil = QLabel("Yıl:")
        lbl_yil.setStyleSheet(S["label"])
        tbl.addWidget(lbl_yil)
        self.cmb_yil = QComboBox()
        self.cmb_yil.setStyleSheet(S["combo"])
        self.cmb_yil.setMaximumWidth(100)
        self.cmb_yil.addItem("Tümü", 0)
        for y in range(2020, 2035):
            self.cmb_yil.addItem(str(y), y)
        tbl.addWidget(self.cmb_yil)

        tbl.addStretch()

        # Butonlar
        self.btn_yeni = QPushButton("YENİ İZİN")
        self.btn_yeni.setStyleSheet(S["primary_btn"])
        self.btn_yeni.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_yeni, "plus", color=DarkTheme.TEXT_PRIMARY, size=14)
        tbl.addWidget(self.btn_yeni)

        self.btn_yenile = QPushButton("YENİLE")
        self.btn_yenile.setStyleSheet(S["secondary_btn"])
        self.btn_yenile.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_yenile, "refresh-cw", color=DarkTheme.TEXT_PRIMARY, size=14)
        tbl.addWidget(self.btn_yenile)

        main.addWidget(toolbar)

        # CONTENT: Tablo + Drawer
        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)

        # ── SOL: TABLO ──
        right = QWidget()
        right.setStyleSheet("background: transparent;")
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.setSpacing(0)

        grp_tablo = QGroupBox("İzin Kayıtları")
        grp_tablo.setStyleSheet(S["group"])
        tl = QVBoxLayout(grp_tablo)
        tl.setContentsMargins(12, 12, 12, 12)
        tl.setSpacing(8)

        # Tablo widget'ı
        self.table = QTableWidget()
        self.table.setModel(self._model)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setStyleSheet(S.get("table", ""))
        self.table.setColumnCount(len(IzinTableModel.COLUMNS))
        self.table.setHorizontalHeaderLabels(IzinTableModel.COLUMNS)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        header = self.table.horizontalHeader()
        for i in range(len(IzinTableModel.COLUMNS)):
            header.setSectionResizeMode(i, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Gün

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

        # ── SAĞ: DRAWER (İzin Girişi) ──
        self._drawer = QFrame()
        self._drawer.setStyleSheet(
            f"background-color: {DarkTheme.BG_SECONDARY}; "
            f"border-left: 1px solid {DarkTheme.BORDER_PRIMARY};"
        )
        self._drawer.setMaximumWidth(0)
        self._drawer.setMinimumWidth(0)

        drawer_lay = QVBoxLayout(self._drawer)
        drawer_lay.setContentsMargins(0, 0, 0, 0)
        drawer_lay.setSpacing(0)

        # Drawer başlık
        drawer_header = QFrame()
        drawer_header.setStyleSheet(
            f"background-color: {DarkTheme.BG_PRIMARY}; "
            f"border-bottom: 1px solid {DarkTheme.BORDER_PRIMARY};"
        )
        header_lay = QHBoxLayout(drawer_header)
        header_lay.setContentsMargins(12, 12, 12, 12)

        lbl_drawer = QLabel("İzin Girişi")
        lbl_drawer.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {DarkTheme.TEXT_PRIMARY};")
        header_lay.addWidget(lbl_drawer)
        header_lay.addStretch()

        btn_drawer_close = QPushButton()
        btn_drawer_close.setFixedSize(32, 32)
        btn_drawer_close.setStyleSheet(S["close_btn"])
        btn_drawer_close.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(btn_drawer_close, "x", color=DarkTheme.TEXT_PRIMARY, size=16)
        btn_drawer_close.clicked.connect(self._close_drawer)
        header_lay.addWidget(btn_drawer_close)
        drawer_lay.addWidget(drawer_header)

        # Drawer scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(S.get("scroll", ""))

        left = QWidget()
        left.setStyleSheet("background: transparent;")
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(12, 12, 12, 12)
        left_l.setSpacing(12)

        # ─ PERSONEL SEÇİMİ ─
        grp_personel = QGroupBox("Personel Seçimi")
        grp_personel.setStyleSheet(S["group"])
        pg = QGridLayout(grp_personel)
        pg.setSpacing(8)
        pg.setContentsMargins(12, 12, 12, 12)

        lbl_sinif = QLabel("Hizmet Sınıfı")
        lbl_sinif.setStyleSheet(S["label"])
        lbl_sinif.setFixedWidth(100)
        pg.addWidget(lbl_sinif, 0, 0)
        self.cmb_hizmet_sinifi = QComboBox()
        self.cmb_hizmet_sinifi.setStyleSheet(S["combo"])
        pg.addWidget(self.cmb_hizmet_sinifi, 0, 1)

        lbl_p = QLabel("Personel")
        lbl_p.setStyleSheet(S["label"])
        lbl_p.setFixedWidth(100)
        pg.addWidget(lbl_p, 1, 0)
        self.cmb_personel = QComboBox()
        self.cmb_personel.setEditable(True)
        self.cmb_personel.setStyleSheet(S["combo"])
        self.cmb_personel.lineEdit().setPlaceholderText("İsim ara...")
        pg.addWidget(self.cmb_personel, 1, 1)

        self.lbl_personel_info = QLabel("")
        self.lbl_personel_info.setStyleSheet(S["help_text"])
        pg.addWidget(self.lbl_personel_info, 2, 0, 1, 2)
        left_l.addWidget(grp_personel)

        # ─ İZİN FORMU ─
        grp_giris = QGroupBox("Yeni İzin Girişi")
        grp_giris.setStyleSheet(S["group"])
        fg = QGridLayout(grp_giris)
        fg.setSpacing(10)
        fg.setContentsMargins(12, 12, 12, 12)

        lbl_tip = QLabel("İzin Tipi")
        lbl_tip.setStyleSheet(S["label"])
        lbl_tip.setFixedWidth(100)
        fg.addWidget(lbl_tip, 0, 0)
        self.cmb_izin_tipi = QComboBox()
        self.cmb_izin_tipi.setStyleSheet(S["combo"])
        fg.addWidget(self.cmb_izin_tipi, 0, 1)

        # Max gün uyarısı
        self.lbl_max_gun = QLabel("")
        self.lbl_max_gun.setStyleSheet(S.get("warning_label", "color: #FFC107;"))
        fg.addWidget(self.lbl_max_gun, 1, 0, 1, 2)

        lbl_bas = QLabel("Başlama")
        lbl_bas.setStyleSheet(S["label"])
        lbl_bas.setFixedWidth(100)
        fg.addWidget(lbl_bas, 2, 0)
        self.dt_baslama = QDateEdit(QtQDate.currentDate())
        self.dt_baslama.setCalendarPopup(True)
        self.dt_baslama.setDisplayFormat("dd.MM.yyyy")
        self.dt_baslama.setStyleSheet(S["date"])
        fg.addWidget(self.dt_baslama, 2, 1)

        lbl_gun = QLabel("Gün")
        lbl_gun.setStyleSheet(S["label"])
        lbl_gun.setFixedWidth(100)
        fg.addWidget(lbl_gun, 3, 0)
        self.spn_gun = QSpinBox()
        self.spn_gun.setRange(1, 365)
        self.spn_gun.setValue(1)
        self.spn_gun.setStyleSheet(S["spin"])
        fg.addWidget(self.spn_gun, 3, 1)

        lbl_bit = QLabel("Bitiş (İşe Dönüş)")
        lbl_bit.setStyleSheet(S["label"])
        lbl_bit.setFixedWidth(100)
        fg.addWidget(lbl_bit, 4, 0)
        self.dt_bitis = QDateEdit()
        self.dt_bitis.setReadOnly(True)
        self.dt_bitis.setDisplayFormat("dd.MM.yyyy")
        self.dt_bitis.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.dt_bitis.setStyleSheet(S["date"])
        fg.addWidget(self.dt_bitis, 4, 1)

        self.btn_kaydet = QPushButton("KAYDET")
        self.btn_kaydet.setStyleSheet(S["save_btn"])
        self.btn_kaydet.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kaydet.setEnabled(False)
        fg.addWidget(self.btn_kaydet, 5, 0, 1, 2)
        left_l.addWidget(grp_giris)

        # ─ BAKİYE PANOSu ─
        grp_bakiye = QGroupBox("İzin Bakiyesi")
        grp_bakiye.setStyleSheet(S["group"])
        bg = QGridLayout(grp_bakiye)
        bg.setSpacing(4)
        bg.setContentsMargins(12, 12, 12, 12)

        lbl_y = QLabel("YILLIK İZİN")
        lbl_y.setStyleSheet(S.get("section_title", "font-weight: 600; color: #fff;"))
        bg.addWidget(lbl_y, 0, 0, 1, 2, Qt.AlignCenter)

        self.lbl_y_devir = self._add_stat(bg, 1, "Devir")
        self.lbl_y_hak = self._add_stat(bg, 2, "Hakediş")
        self.lbl_y_kul = self._add_stat(bg, 3, "Kullanılan")
        self.lbl_y_kal = self._add_stat(bg, 4, "KALAN")

        sep1 = QFrame()
        sep1.setFixedHeight(1)
        sep1.setStyleSheet(S.get("separator", f"background-color: {DarkTheme.BORDER_PRIMARY};"))
        bg.addWidget(sep1, 5, 0, 1, 2)

        lbl_s = QLabel("ŞUA İZNİ")
        lbl_s.setStyleSheet(S.get("section_title", "font-weight: 600; color: #fff;"))
        bg.addWidget(lbl_s, 6, 0, 1, 2, Qt.AlignCenter)

        self.lbl_s_hak = self._add_stat(bg, 7, "Hakediş")
        self.lbl_s_kul = self._add_stat(bg, 8, "Kullanılan")
        self.lbl_s_kal = self._add_stat(bg, 9, "KALAN")

        sep2 = QFrame()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet(S.get("separator", f"background-color: {DarkTheme.BORDER_PRIMARY};"))
        bg.addWidget(sep2, 10, 0, 1, 2)

        self.lbl_diger = self._add_stat(bg, 11, "Rapor/Mazeret")
        bg.setRowStretch(12, 1)
        left_l.addWidget(grp_bakiye)
        left_l.addStretch()

        scroll.setWidget(left)
        drawer_lay.addWidget(scroll, 1)
        content.addWidget(self._drawer)

        main.addLayout(content, 1)

    def _add_stat(self, grid: QGridLayout, row: int, text: str) -> QLabel:
        """Bakiye panosu satırı ekle."""
        lbl = QLabel(text)
        lbl.setStyleSheet(S.get("stat_label", ""))
        grid.addWidget(lbl, row, 0)
        val = QLabel("—")
        val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        val.setStyleSheet(S.get("stat_value", ""))
        grid.addWidget(val, row, 1)
        return val

    def _connect_signals(self):
        """Tüm signalleri bağla."""
        self.cmb_hizmet_sinifi.currentTextChanged.connect(self._on_sinif_changed)
        self.cmb_personel.currentIndexChanged.connect(self._on_personel_changed)
        self.cmb_izin_tipi.currentTextChanged.connect(self._on_izin_tipi_changed)
        self.dt_baslama.dateChanged.connect(self._on_baslama_changed)
        self.spn_gun.valueChanged.connect(self._on_baslama_changed)
        self.btn_kaydet.clicked.connect(self._on_save)
        self.btn_yeni.clicked.connect(self._open_new_form)
        self.btn_yenile.clicked.connect(self.load_data)
        self.cmb_ay.currentIndexChanged.connect(self._apply_filters)
        self.cmb_yil.currentIndexChanged.connect(self._apply_filters)

    # ═══════════════════════════════════════════
    #  VERİ YÜKLEME
    # ═══════════════════════════════════════════

    def load_data(self):
        """İzin verilerini yükle (personel, izin tipleri, tatiller, mevcut izinler)."""
        if not self._db:
            logger.warning("Database path not set")
            return

        try:
            from core.di import get_registry
            registry = get_registry(self._db)

            # ── PERSONEL ──
            self._all_personel = registry.get("Personel").get_all()
            aktif = [p for p in self._all_personel
                     if str(p.get("Durum", "")).strip() == "Aktif"]
            aktif.sort(key=lambda p: str(p.get("AdSoyad", "")))

            # Hizmet sınıfları
            siniflar = sorted(set(
                str(p.get("HizmetSinifi") or "").strip()
                for p in aktif if str(p.get("HizmetSinifi") or "").strip()
            ))
            self.cmb_hizmet_sinifi.blockSignals(True)
            self.cmb_hizmet_sinifi.clear()
            self.cmb_hizmet_sinifi.addItem("Tümü")
            self.cmb_hizmet_sinifi.addItems(siniflar)
            self.cmb_hizmet_sinifi.blockSignals(False)

            # Personel combo
            self._fill_personel_combo(aktif)

            # ── İZİN TİPLERİ ──
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

            # ── TATİLLER ──
            try:
                tatiller = registry.get("Tatiller").get_all()
                tatil_listesi = []
                for r in tatiller:
                    t = str(r.get("Tarih", "")).strip()
                    if t:
                        tatil_listesi.append(t)
                self._tatiller = tatil_listesi
                self._calculator.add_tatiller(tatil_listesi)
            except Exception:
                self._tatiller = []

            # ── İZİN KAYITLARI ──
            self._all_izin = registry.get("Izin_Giris").get_all()
            self._all_izin.sort(
                key=lambda r: self._parse_date(r.get("BaslamaTarihi", "")) or date.min,
                reverse=True
            )

            self._apply_filters()
            logger.info(
                f"İzin yükleme tamamlandı: {len(self._all_izin)} kayıt, "
                f"{len(aktif)} aktif personel, {len(tip_adlari)} izin tipi"
            )

        except Exception as e:
            logger.error(f"İzin yükleme hatası: {e}")

    def _fill_personel_combo(self, aktif: list):
        """Personel combosu doldur."""
        sinif_filtre = self.cmb_hizmet_sinifi.currentText()
        if sinif_filtre and sinif_filtre != "Tümü":
            aktif = [p for p in aktif
                     if str(p.get("HizmetSinifi") or "").strip() == sinif_filtre]

        self.cmb_personel.blockSignals(True)
        self.cmb_personel.clear()
        self.cmb_personel.addItem("— Tüm Personel —", "")
        for p in aktif:
            ad = p.get("AdSoyad", "")
            tc = p.get("KimlikNo", "")
            sinif = p.get("HizmetSinifi", "")
            self.cmb_personel.addItem(f"{ad}  ({sinif})", tc)
        self.cmb_personel.blockSignals(False)

    # ═══════════════════════════════════════════
    #  SİGNAL HANDLERS
    # ═══════════════════════════════════════════

    def _on_sinif_changed(self, text: str):
        """Hizmet sınıfı değişince personel combosunu yenile."""
        self._fill_personel_combo([p for p in self._all_personel
                                   if str(p.get("Durum", "")).strip() == "Aktif"])
        self._on_personel_changed(0)

    def _on_personel_changed(self, idx: int):
        """Personel değişince bakiye yükle ve tablo filtrele."""
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

        self._apply_filters()

    def _on_izin_tipi_changed(self, tip_text: str):
        """İzin tipi değişince max gün sınırını uygula."""
        tip_text = str(tip_text).strip()
        max_gun = self._izin_max_gun.get(tip_text, 0)

        if max_gun and max_gun > 0:
            self.spn_gun.setMaximum(max_gun)
            if self.spn_gun.value() > max_gun:
                self.spn_gun.setValue(max_gun)
            self.lbl_max_gun.setText(f"Max. {max_gun} gün")
        else:
            self.spn_gun.setMaximum(365)
            self.lbl_max_gun.setText("")

    def _on_baslama_changed(self):
        """Başlama tarihi veya gün değişince bitiş tarihi hesapla."""
        self._calculate_bitis()

    # ═══════════════════════════════════════════
    #  HESAPLAMALAR
    # ═══════════════════════════════════════════

    def _calculate_bitis(self):
        """Bitiş tarihini hesapla (IzinCalculator kullan)."""
        baslama = self.dt_baslama.date().toPython()
        gun = self.spn_gun.value()

        bitis = self._calculator.calculate_bitis_tarihi(baslama, gun)
        if bitis:
            self.dt_bitis.setDate(QtQDate(bitis.year, bitis.month, bitis.day))

    def _load_bakiye(self, tc: str):
        """Personel bakiyesini yükle."""
        if not self._db or not tc:
            self._clear_bakiye()
            return

        try:
            from core.di import get_registry
            registry = get_registry(self._db)
            izin_bilgi = registry.get("Izin_Bilgi").get_by_id(tc)
            if izin_bilgi:
                self.lbl_y_devir.setText(str(izin_bilgi.get("YillikDevir", "0")))
                self.lbl_y_hak.setText(str(izin_bilgi.get("YillikHakedis", "0")))
                self.lbl_y_kul.setText(str(izin_bilgi.get("YillikKullanilan", "0")))
                self.lbl_y_kal.setText(str(izin_bilgi.get("YillikKalan", "0")))
                self.lbl_s_hak.setText(str(izin_bilgi.get("SuaKullanilabilirHak", "0")))
                self.lbl_s_kul.setText(str(izin_bilgi.get("SuaKullanilan", "0")))
                self.lbl_s_kal.setText(str(izin_bilgi.get("SuaKalan", "0")))
                self.lbl_diger.setText(str(izin_bilgi.get("RaporMazeretTop", "0")))
            else:
                self._clear_bakiye()
        except Exception as e:
            logger.error(f"Bakiye yüksüz: {e}")
            self._clear_bakiye()

    def _clear_bakiye(self):
        """Bakiye etiketlerini temizle."""
        for lbl in [self.lbl_y_devir, self.lbl_y_hak, self.lbl_y_kul, self.lbl_y_kal,
                    self.lbl_s_hak, self.lbl_s_kul, self.lbl_s_kal, self.lbl_diger]:
            lbl.setText("—")

    # ═══════════════════════════════════════════
    #  FİLTRELEME
    # ═══════════════════════════════════════════

    def _apply_filters(self):
        """Ay/Yıl + seçili personel filtrelemesi uygula."""
        filtered = list(self._all_izin)

        ay = self.cmb_ay.currentData() or 0
        yil = self.cmb_yil.currentData() or 0
        selected_tc = self.cmb_personel.currentData() or ""

        # Ay/Yıl filtresi
        if ay or yil:
            result = []
            for r in filtered:
                d = self._parse_date(r.get("BaslamaTarihi", ""))
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
            key=lambda r: self._parse_date(r.get("BaslamaTarihi", "")) or date.min,
            reverse=True
        )

        self._model.set_data(filtered)

        # Sayı
        total_gun = sum(int(r.get("Gun", 0)) for r in filtered
                        if str(r.get("Gun", "")).isdigit())
        self.lbl_count.setText(
            f"{len(filtered)} / {len(self._all_izin)} kayıt — Toplam {total_gun} gün"
        )

    # ═══════════════════════════════════════════
    #  DRAWER
    # ═══════════════════════════════════════════

    def _open_new_form(self):
        """Yeni izin formunu aç."""
        self.spn_gun.setValue(1)
        self.dt_baslama.setDate(QtQDate.currentDate())
        self._calculate_bitis()
        self._open_drawer()

    def _open_drawer(self):
        """Draweri aç (animasyonlu)."""
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
        """Draweri kapat."""
        if not self._drawer or self._drawer.maximumWidth() == 0:
            return
        anim = QPropertyAnimation(self._drawer, b"maximumWidth", self)
        anim.setDuration(200)
        anim.setStartValue(self._drawer.maximumWidth())
        anim.setEndValue(0)
        anim.setEasingCurve(QEasingCurve.InCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)

    def _calc_drawer_width(self) -> int:
        """Drawer genişliği hesapla."""
        base = int(self.width() * self._drawer_ratio)
        return max(self._drawer_min_width, min(self._drawer_max_width, base))

    def resizeEvent(self, event):
        """Pencere boyutu değişince drawer genişliğini güncelle."""
        super().resizeEvent(event)
        if self._drawer:
            self._drawer.setMaximumWidth(self._calc_drawer_width())

    # ═══════════════════════════════════════════
    #  KAYDET
    # ═══════════════════════════════════════════

    def _on_save(self):
        """İzin kaydet."""
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

        # Tarih parse
        yeni_bas = self._parse_date(baslama)
        yeni_bit = self._parse_date(bitis)
        if not yeni_bas or not yeni_bit:
            QMessageBox.critical(self, "Hata", "Tarih formatı hatalı.")
            return

        # Çakışma kontrolü
        has_conflict, conflict = self._calculator.check_tarih_cakismasi(
            yeni_bas, yeni_bit, self._all_izin
        )
        if has_conflict:
            QMessageBox.warning(self, "Çakışma Var!",
                f"{ad} personeli {conflict['BaslamaTarihi']} - "
                f"{conflict['BitisTarihi']} tarihlerinde zaten izinli!\n\n"
                f"İzin Tipi: {conflict['IzinTipi']}\n"
                f"Durum: {conflict['Durum']}")
            return

        # Bakiye kontrolü
        try:
            from core.di import get_registry
            registry = get_registry(self._db)
            izin_bilgi = registry.get("Izin_Bilgi").get_by_id(tc)

            if izin_bilgi:
                is_valid, msg = self._calculator.validate_balance(
                    izin_tipi, gun, izin_bilgi
                )
                if not is_valid:
                    cevap = QMessageBox.question(
                        self, "Bakiye Yetersiz",
                        f"{msg}\n\nYine de kaydetmek istiyor musunuz?",
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                    )
                    if cevap != QMessageBox.Yes:
                        return

            # Kaydet
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

            registry.get("Izin_Giris").insert(kayit)
            logger.info(f"İzin kaydedildi: {izin_id}")

            # Otomatik bakiye düşümü
            field_name, should_deduct = self._calculator.get_balance_deduction(izin_tipi)
            if should_deduct and field_name:
                try:
                    izin_bilgi = registry.get("Izin_Bilgi").get_by_id(tc)
                    if izin_bilgi:
                        if should_deduct and "Kalan" in field_name:
                            mevcut = float(izin_bilgi.get(field_name, 0))
                            yeni = mevcut - gun
                            registry.get("Izin_Bilgi").update(tc, {field_name: yeni})
                except Exception as e:
                    logger.error(f"Bakiye düşmesi başarısız: {e}")

            # Pasif yapılması gerekli mi?
            if self._calculator.should_set_pasif(izin_tipi, gun):
                try:
                    registry.get("Personel").update(tc, {"Durum": "Pasif"})
                    logger.info(f"Personel pasif yapıldı: {tc}")
                except Exception as e:
                    logger.error(f"Personel pasif durumu güncelleme hatası: {e}")

            QMessageBox.information(self, "Başarılı",
                f"{ad} için {gun} gün {izin_tipi} kaydedildi.\n"
                f"Başlama: {self.dt_baslama.date().toString('dd.MM.yyyy')}\n"
                f"İşe Dönüş: {self.dt_bitis.date().toString('dd.MM.yyyy')}")

            self.load_data()
            self._close_drawer()

        except Exception as e:
            logger.error(f"İzin kaydetme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"İzin kaydedilemedi:\n{e}")

    # ═══════════════════════════════════════════
    #  CONTEXT MENU (İptal / Onayla)
    # ═══════════════════════════════════════════

    def _show_context_menu(self, pos):
        """Tablo sağ tıklaması için context menu göster."""
        index_model = self.table.indexAt(pos)
        if not index_model.isValid():
            return

        row = index_model.row()
        row_data = self._model.get_row(row)
        if not row_data:
            return

        ad = row_data.get("AdSoyad", "")
        izin_id = row_data.get("Izinid", "")
        durum = str(row_data.get("Durum", "")).strip()

        menu = QMenu(self)
        menu.setStyleSheet(S.get("context_menu", ""))

        if durum != "İptal":
            act_iptal = menu.addAction("İzni İptal Et")
            act_iptal.triggered.connect(lambda: self._iptal_izin(izin_id, ad))

        if durum == "Beklemede":
            act_onayla = menu.addAction("Onayla")
            act_onayla.triggered.connect(lambda: self._durum_degistir(izin_id, ad, "Onaylandı"))

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _iptal_izin(self, izin_id: str, ad: str):
        """İzni iptal et."""
        cevap = QMessageBox.question(
            self, "İzin İptal",
            f"{ad} personelinin bu izni iptal edilsin mi?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if cevap == QMessageBox.Yes:
            self._durum_degistir(izin_id, ad, "İptal")

    def _durum_degistir(self, izin_id: str, ad: str, yeni_durum: str):
        """İzin durumunu değiştir."""
        try:
            from core.di import get_registry
            registry = get_registry(self._db)
            registry.get("Izin_Giris").update(izin_id, {"Durum": yeni_durum})
            logger.info(f"İzin durum değişti: {izin_id} → {yeni_durum}")
            self.load_data()
        except Exception as e:
            logger.error(f"Durum değişim hatası: {e}")
            QMessageBox.critical(self, "Hata", f"İşlem hatası:\n{e}")

    # ═══════════════════════════════════════════
    #  YARDIMCI METODLAR
    # ═══════════════════════════════════════════

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[date]:
        """Tarih string'ini parse et."""
        if not date_str:
            return None
        date_str = str(date_str).strip()
        # ISO
        if len(date_str) == 10 and date_str[4] == "-":
            try:
                return date(int(date_str[:4]), int(date_str[5:7]), int(date_str[8:10]))
            except ValueError:
                pass
        # TR
        if len(date_str) == 10 and date_str[2] == ".":
            try:
                parts = date_str.split(".")
                return date(int(parts[2]), int(parts[1]), int(parts[0]))
            except (ValueError, IndexError):
                pass
        return None

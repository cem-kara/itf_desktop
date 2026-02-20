 # -*- coding: utf-8 -*-
"""
İzin Giriş & Takip Sayfası
- Sol: Yeni izin girişi + bakiye panosu
- Sağ: İzin geçmişi tablosu
"""
import uuid
from datetime import datetime, timedelta
from PySide6.QtCore import Qt, QDate, QSortFilterProxyModel, QModelIndex, QAbstractTableModel
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDateEdit, QSpinBox, QFrame, QGroupBox,
    QGridLayout, QSplitter, QTableView, QHeaderView,
    QAbstractSpinBox, QProgressBar, QMessageBox
)
from PySide6.QtGui import QColor, QCursor

from core.logger import logger
from core.date_utils import parse_date as parse_any_date, to_ui_date
from ui.styles import DarkTheme
from ui.styles.components import STYLES as S
from ui.styles.icons import IconRenderer


# ─── İzin Tipleri (varsayılan) ───
IZIN_TIPLERI = [
    "Yıllık İzin",
    "Şua İzni",
    "Mazeret İzni",
    "Sağlık Raporu",
    "Ücretsiz İzin",
    "Doğum İzni",
    "Babalık İzni",
    "Evlilik İzni",
    "Ölüm İzni",
    "Diğer",
]


# ═══════════════════════════════════════════════
#  İZİN GEÇMİŞİ TABLO MODELİ
# ═══════════════════════════════════════════════

IZIN_COLUMNS = [
    ("IzinTipi",       "İzin Tipi",    3),
    ("BaslamaTarihi",  "Başlama",      2),
    ("BitisTarihi",    "Bitiş",        2),
    ("Gun",            "Gün",          1),
    ("Durum",          "Durum",        1),
]

DURUM_COLORS = {
    "Onaylandı":  QColor(34, 197, 94, 40),
    "Beklemede":   QColor(234, 179, 8, 40),
    "İptal":       QColor(239, 68, 68, 40),
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
            # Tarih formatla
            if col_key in ("BaslamaTarihi", "BitisTarihi") and val:
                return to_ui_date(val)
            return val

        if role == Qt.BackgroundRole and col_key == "Durum":
            return DURUM_COLORS.get(str(row.get("Durum", "")))

        if role == Qt.ForegroundRole and col_key == "Durum":
            durum = str(row.get("Durum", ""))
            colors = {
                "Onaylandı": QColor(DarkTheme.STATUS_SUCCESS),
                "Beklemede": QColor(DarkTheme.STATUS_WARNING),
                "İptal": QColor(DarkTheme.STATUS_ERROR),
            }
            return colors.get(durum, QColor(DarkTheme.TEXT_MUTED))

        if role == Qt.TextAlignmentRole:
            if col_key in ("Gun", "Durum"):
                return Qt.AlignCenter
            return Qt.AlignVCenter | Qt.AlignLeft

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
#  İZİN GİRİŞ SAYFASI
# ═══════════════════════════════════════════════

class IzinGirisPage(QWidget):
    """
    İzin Giriş & Takip sayfası.
    db: SQLiteManager
    personel_data: dict → personel bilgileri
    on_back: callback → geri dönüş
    """

    def __init__(self, db=None, personel_data=None, on_back=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(S["page"])
        self._db = db
        self._personel = personel_data or {}
        self._on_back = on_back
        self._tatiller = []
        self.ui = {}

        self._setup_ui()
        self._load_sabitler()
        self._load_izin_bakiye()
        self._load_izin_gecmisi()

    # ═══════════════════════════════════════════
    #  UI
    # ═══════════════════════════════════════════

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 12, 20, 12)
        main.setSpacing(12)

        # ── HEADER ──
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 32, 44, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }
        """)
        hdr = QHBoxLayout(header_frame)
        hdr.setContentsMargins(16, 10, 16, 10)
        hdr.setSpacing(12)

        btn_back = QPushButton("← Geri")
        btn_back.setStyleSheet(S["back_btn"])
        btn_back.setCursor(QCursor(Qt.PointingHandCursor))
        btn_back.clicked.connect(self._go_back)
        hdr.addWidget(btn_back)

        ad = self._personel.get("AdSoyad", "")
        tc = self._personel.get("KimlikNo", "")
        self.lbl_header = QLabel(f"{ad} - Izin Takip")
        self.lbl_header.setStyleSheet(S["header_name"])
        hdr.addWidget(self.lbl_header)
        hdr.addStretch()

        main.addWidget(header_frame)

        # ── SPLITTER ──
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(S["splitter"])

        # ── SOL: Giriş + Bakiye ──
        left = QWidget()
        left.setStyleSheet("background: transparent;")
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(0, 0, 0, 0)
        left_l.setSpacing(12)

        # Giriş Kutusu
        grp_giris = QGroupBox("Yeni Izin Girisi")
        grp_giris.setStyleSheet(S["group"])
        form = QGridLayout(grp_giris)
        form.setSpacing(10)
        form.setContentsMargins(12, 12, 12, 12)

        # İzin Tipi
        lbl_tip = QLabel("İzin Tipi")
        lbl_tip.setStyleSheet(S["label"])
        form.addWidget(lbl_tip, 0, 0)
        self.ui["izin_tipi"] = QComboBox()
        self.ui["izin_tipi"].setStyleSheet(S["combo"])
        form.addWidget(self.ui["izin_tipi"], 0, 1)

        # Başlama Tarihi
        lbl_bas = QLabel("Başlama Tarihi")
        lbl_bas.setStyleSheet(S["label"])
        form.addWidget(lbl_bas, 1, 0)

        h_tarih = QHBoxLayout()
        h_tarih.setSpacing(8)
        self.ui["baslama"] = QDateEdit(QDate.currentDate())
        self.ui["baslama"].setCalendarPopup(True)
        self.ui["baslama"].setDisplayFormat("dd.MM.yyyy")
        self.ui["baslama"].setStyleSheet(S["date"])
        self._setup_calendar(self.ui["baslama"])
        h_tarih.addWidget(self.ui["baslama"], 2)

        lbl_gun = QLabel("Gün:")
        lbl_gun.setStyleSheet(S["label"])
        h_tarih.addWidget(lbl_gun)

        self.ui["gun"] = QSpinBox()
        self.ui["gun"].setRange(1, 365)
        self.ui["gun"].setValue(1)
        self.ui["gun"].setStyleSheet(S["spin"])
        self.ui["gun"].setFixedWidth(70)
        h_tarih.addWidget(self.ui["gun"])
        form.addLayout(h_tarih, 1, 1)

        # Bitiş Tarihi (otomatik)
        lbl_bit = QLabel("Bitiş (İşe Başlama)")
        lbl_bit.setStyleSheet(S["label"])
        form.addWidget(lbl_bit, 2, 0)
        self.ui["bitis"] = QDateEdit()
        self.ui["bitis"].setReadOnly(True)
        self.ui["bitis"].setDisplayFormat("dd.MM.yyyy")
        self.ui["bitis"].setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.ui["bitis"].setStyleSheet(S["date"])
        form.addWidget(self.ui["bitis"], 2, 1)

        # Kaydet butonu
        self.btn_kaydet = QPushButton("IZIN KAYDET")
        self.btn_kaydet.setStyleSheet(S["save_btn"])
        self.btn_kaydet.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kaydet.clicked.connect(self._on_save)
        IconRenderer.set_button_icon(self.btn_kaydet, "save", color=DarkTheme.TEXT_PRIMARY, size=14)
        form.addWidget(self.btn_kaydet, 3, 0, 1, 2)

        # Sinyaller
        self.ui["baslama"].dateChanged.connect(self._calculate_bitis)
        self.ui["gun"].valueChanged.connect(self._calculate_bitis)

        left_l.addWidget(grp_giris)

        # Bakiye Panosu
        grp_bakiye = QGroupBox("Izin Bakiyesi")
        grp_bakiye.setStyleSheet(S["group"])
        bg = QGridLayout(grp_bakiye)
        bg.setSpacing(4)
        bg.setContentsMargins(12, 12, 12, 12)

        # Yıllık
        lbl_y = QLabel("YILLIK İZİN")
        lbl_y.setStyleSheet(S["section_title"])
        bg.addWidget(lbl_y, 0, 0, 1, 2, Qt.AlignCenter)

        self.lbl_y_devir = self._add_stat(bg, 1, "Devir", "stat_value")
        self.lbl_y_hak = self._add_stat(bg, 2, "Hakediş", "stat_value")
        self.lbl_y_kul = self._add_stat(bg, 3, "Kullanılan", "stat_red")
        self.lbl_y_kal = self._add_stat(bg, 4, "KALAN", "stat_green")

        sep1 = QFrame(); sep1.setFixedHeight(1); sep1.setStyleSheet(S["separator"])
        bg.addWidget(sep1, 5, 0, 1, 2)

        # Şua
        lbl_s = QLabel("ŞUA İZNİ")
        lbl_s.setStyleSheet(S["section_title"])
        bg.addWidget(lbl_s, 6, 0, 1, 2, Qt.AlignCenter)

        self.lbl_s_hak = self._add_stat(bg, 7, "Hakediş", "stat_value")
        self.lbl_s_kul = self._add_stat(bg, 8, "Kullanılan", "stat_red")
        self.lbl_s_kal = self._add_stat(bg, 9, "KALAN", "stat_green")

        sep2 = QFrame(); sep2.setFixedHeight(1); sep2.setStyleSheet(S["separator"])
        bg.addWidget(sep2, 10, 0, 1, 2)

        # Diğer
        self.lbl_diger = self._add_stat(bg, 11, "Rapor / Mazeret", "stat_value")

        bg.setRowStretch(12, 1)
        left_l.addWidget(grp_bakiye)
        left_l.addStretch()

        # ── SAĞ: İzin Geçmişi ──
        right = QWidget()
        right.setStyleSheet("background: transparent;")
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.setSpacing(8)

        grp_gecmis = QGroupBox("Izin Gecmisi")
        grp_gecmis.setStyleSheet(S["group"])
        gecmis_l = QVBoxLayout(grp_gecmis)
        gecmis_l.setContentsMargins(8, 8, 8, 8)

        self._izin_model = IzinTableModel()
        self._izin_proxy = QSortFilterProxyModel()
        self._izin_proxy.setSourceModel(self._izin_model)

        self.table = QTableView()
        self.table.setModel(self._izin_proxy)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setStyleSheet(S["table"])
        self.table.setStyleSheet(S["table"] + S["scroll"])

        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        for i, (_, _, stretch) in enumerate(IZIN_COLUMNS):
            header.setSectionResizeMode(i, QHeaderView.Stretch)

        gecmis_l.addWidget(self.table)

        # Toplam satırı
        footer_h = QHBoxLayout()
        self.lbl_toplam = QLabel("")
        self.lbl_toplam.setStyleSheet(f"color: {DarkTheme.TEXT_MUTED}; font-size: 12px; background: transparent;")
        footer_h.addWidget(self.lbl_toplam)
        footer_h.addStretch()
        gecmis_l.addLayout(footer_h)

        right_l.addWidget(grp_gecmis, 1)

        # Splitter
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        main.addWidget(splitter, 1)

        # İlk bitiş hesapla
        self._calculate_bitis()

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
    #  YENİ EKLENEN: BAKİYE DÜŞME METODU
    # ═══════════════════════════════════════════
    def _bakiye_dus(self, registry, tc, izin_tipi, gun):
        """Bakiyeden otomatik düş (Yıllık İzin / Şua İzni / Rapor-Mazeret)."""
        try:
            izin_bilgi = registry.get("Izin_Bilgi").get_by_id(tc)
            if not izin_bilgi:
                return

            if izin_tipi == "Yıllık İzin":
                mevcut_kul = float(izin_bilgi.get("YillikKullanilan", 0))
                mevcut_kal = float(izin_bilgi.get("YillikKalan", 0))
                registry.get("Izin_Bilgi").update(tc, {
                    "YillikKullanilan": mevcut_kul + gun,
                    "YillikKalan": mevcut_kal - gun
                })
            elif izin_tipi == "Şua İzni":
                mevcut_kul = float(izin_bilgi.get("SuaKullanilan", 0))
                mevcut_kal = float(izin_bilgi.get("SuaKalan", 0))
                registry.get("Izin_Bilgi").update(tc, {
                    "SuaKullanilan": mevcut_kul + gun,
                    "SuaKalan": mevcut_kal - gun
                })
            elif izin_tipi in ["Sağlık Raporu", "Mazeret İzni"]:
                mevcut_top = float(izin_bilgi.get("RaporMazeretTop", 0))
                registry.get("Izin_Bilgi").update(tc, {
                    "RaporMazeretTop": mevcut_top + gun
                })
            logger.info(f"Bakiye güncellendi: {tc} - {izin_tipi}")
        except Exception as e:
            logger.error(f"Bakiye düşme hatası: {e}")

    # ═══════════════════════════════════════════
    #  VERİ YÜKLEME
    # ═══════════════════════════════════════════

    def _load_sabitler(self):
        """İzin tiplerini ve tatilleri Sabitler tablosundan dinamik olarak yükler."""
        try:
            if not self._db:
                return

            from core.di import get_registry
            registry = get_registry(self._db)
            
            # 1. İzin Tiplerini Yükle (Sabitler -> Kod: 'Izin_Tipi')
            sabitler_repo = registry.get("Sabitler")
            all_sabit = sabitler_repo.get_all()

            izin_tipleri = sorted([
                str(r.get("MenuEleman", "")).strip()
                for r in all_sabit
                if r.get("Kod") == "İzin_Tipi" and r.get("MenuEleman", "").strip()
            ])

            # Eğer veritabanı boşsa varsayılanları koru
            if not izin_tipleri:
                izin_tipleri = ["Yıllık İzin", "Şua İzni", "Mazeret İzni", "Sağlık Raporu"]

            self.ui["izin_tipi"].clear()
            self.ui["izin_tipi"].addItems(izin_tipleri)

            # 2. Tatilleri Yükle (Bitiş tarihi hesaplaması için)
            tatiller_repo = registry.get("Tatiller")
            tatiller = tatiller_repo.get_all()
            self._tatiller = [
                str(r.get("Tarih", "")).strip()
                for r in tatiller
                if r.get("Tarih", "").strip()
            ]
            
            logger.info(f"Sabitler ve {len(self._tatiller)} adet tatil günü yüklendi.")

        except Exception as e:
            logger.error(f"Veritabanı sabitleri yükleme hatası: {e}")

    def _load_izin_bakiye(self):
        """İzin_Bilgi tablosundan bakiye verilerini yükler."""
        tc = self._personel.get("KimlikNo", "")
        if not self._db or not tc:
            return

        try:
            from core.di import get_registry
            registry = get_registry(self._db)
            repo = registry.get("Izin_Bilgi")
            izin = repo.get_by_id(tc)

            if izin:
                self.lbl_y_devir.setText(str(izin.get("YillikDevir", "0")))
                self.lbl_y_hak.setText(str(izin.get("YillikHakedis", "0")))
                self.lbl_y_kul.setText(str(izin.get("YillikKullanilan", "0")))
                self.lbl_y_kal.setText(str(izin.get("YillikKalan", "0")))
                self.lbl_s_hak.setText(str(izin.get("SuaKullanilabilirHak", "0")))
                self.lbl_s_kul.setText(str(izin.get("SuaKullanilan", "0")))
                self.lbl_s_kal.setText(str(izin.get("SuaKalan", "0")))
                self.lbl_diger.setText(str(izin.get("RaporMazeretTop", "0")))
        except Exception as e:
            logger.error(f"İzin bakiye yükleme hatası: {e}")

    def _load_izin_gecmisi(self):
        """Izin_Giris tablosundan personelin izin kayıtlarını yükler."""
        tc = self._personel.get("KimlikNo", "")
        if not self._db or not tc:
            return

        try:
            from core.di import get_registry
            registry = get_registry(self._db)
            repo = registry.get("Izin_Giris")
            all_izin = repo.get_all()

            # Bu personelin izinlerini filtrele (Personelid = TC)
            personel_izin = [
                r for r in all_izin
                if str(r.get("Personelid", "")).strip() == tc
            ]
            # Tarihe göre sırala (yeni önce)
            personel_izin.sort(
                key=lambda r: str(r.get("BaslamaTarihi", "")),
                reverse=True
            )

            self._izin_model.set_data(personel_izin)

            # Toplam gün hesapla
            toplam_gun = sum(
                int(r.get("Gun", 0)) for r in personel_izin
                if str(r.get("Gun", "")).isdigit()
            )
            self.lbl_toplam.setText(
                f"{len(personel_izin)} izin kaydı — Toplam {toplam_gun} gün"
            )

        except Exception as e:
            logger.error(f"İzin geçmişi yükleme hatası: {e}")

    # ═══════════════════════════════════════════
    #  BİTİŞ TARİHİ HESAPLAMA
    # ═══════════════════════════════════════════

    def _calculate_bitis(self):
        """Başlama + gün + tatiller/hafta sonu = bitiş tarihi hesapla."""
        baslama = self.ui["baslama"].date().toPython()
        gun = self.ui["gun"].value()

        # İş günü hesapla (hafta sonu ve tatilleri atla)
        kalan = gun
        current = baslama
        while kalan > 0:
            current += timedelta(days=1)
            # Hafta sonu kontrolü (5=Cumartesi, 6=Pazar)
            if current.weekday() in (5, 6):
                continue
            # Tatil kontrolü
            if current.strftime("%Y-%m-%d") in self._tatiller:
                continue
            kalan -= 1

        # Bitiş = işe başlama günü (izin bitişinin ertesi iş günü)
        self.ui["bitis"].setDate(QDate(current.year, current.month, current.day))

    
    # ═══════════════════════════════════════════
    #  GÜNCELLENEN: KAYDET METODU
    # ═══════════════════════════════════════════
    def _on_save(self):
        """Yeni izin kaydını kontrollerle birlikte DB'ye yazar."""
        tc = self._personel.get("KimlikNo", "")
        ad = self._personel.get("AdSoyad", "")
        sinif = self._personel.get("HizmetSinifi", "")
        izin_tipi = self.ui["izin_tipi"].currentText().strip()

        if not izin_tipi:
            QMessageBox.warning(self, "Eksik", "İzin tipi seçilmeli.")
            return

        baslama_str = self.ui["baslama"].date().toString("yyyy-MM-dd")
        bitis_str = self.ui["bitis"].date().toString("yyyy-MM-dd")
        gun = self.ui["gun"].value()

        yeni_bas = _parse_date(baslama_str)
        yeni_bit = _parse_date(bitis_str)

        try:
            from core.di import get_registry
            registry = get_registry(self._db)
            
            # 1. TARİH ÇAKIŞMA KONTROLÜ
            all_izin = registry.get("Izin_Giris").get_all()
            for kayit in all_izin:
                if str(kayit.get("Durum", "")) == "İptal": continue
                if str(kayit.get("Personelid", "")) != tc: continue

                vt_bas = _parse_date(kayit.get("BaslamaTarihi", ""))
                vt_bit = _parse_date(kayit.get("BitisTarihi", ""))

                if vt_bas and vt_bit:
                    if (yeni_bas <= vt_bit) and (yeni_bit >= vt_bas):
                        QMessageBox.warning(
                            self, "Tarih Cakismasi",
                            f"Bu tarihlerde zaten bir kayıt mevcut!\n"
                            f"Mevcut İzin: {vt_bas.strftime('%d.%m.%Y')} - {vt_bit.strftime('%d.%m.%Y')}"
                        )
                        return

            # 2. BAKİYE KONTROLÜ
            if izin_tipi in ["Yıllık İzin", "Şua İzni"]:
                izin_bilgi = registry.get("Izin_Bilgi").get_by_id(tc)
                if izin_bilgi:
                    alan = "YillikKalan" if izin_tipi == "Yıllık İzin" else "SuaKalan"
                    kalan = float(izin_bilgi.get(alan, 0))
                    if gun > kalan:
                        cevap = QMessageBox.question(
                            self, "Yetersiz Bakiye",
                            f"Kalan bakiye: {kalan} gün. Girilen: {gun} gün.\nDevam edilsin mi?",
                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                        )
                        if cevap != QMessageBox.Yes: return

            # 3. KAYDETME İŞLEMİ
            izin_id = str(uuid.uuid4())[:8].upper()
            yeni_kayit = {
                "Izinid": izin_id, "HizmetSinifi": sinif, "Personelid": tc,
                "AdSoyad": ad, "IzinTipi": izin_tipi, "BaslamaTarihi": baslama_str,
                "Gun": gun, "BitisTarihi": bitis_str, "Durum": "Onaylandı",
            }
            
            registry.get("Izin_Giris").insert(yeni_kayit)
            
            # 4. OTOMATİK BAKİYE DÜŞME
            self._bakiye_dus(registry, tc, izin_tipi, gun)

            QMessageBox.information(self, "Başarılı", f"İzin başarıyla kaydedildi.")
            
            self._load_izin_gecmisi()
            self._load_izin_bakiye()
            self.ui["gun"].setValue(1)

        except Exception as e:
            logger.error(f"Kaydetme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"İşlem başarısız: {e}")

    # ═══════════════════════════════════════════
    #  GERİ
    # ═══════════════════════════════════════════

    def _go_back(self):
        if self._on_back:
            self._on_back()



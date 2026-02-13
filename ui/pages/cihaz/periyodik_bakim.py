# -*- coding: utf-8 -*-
"""
Periyodik Bakım Yönetimi Sayfası
──────────────────────────────────
• Sol panel : bakım planlama formu + durum / aksiyon girişi
• Sağ panel : bakım takvimi tablosu (ay filtrelidir)
• Çift tıklama satıra → formu düzenleme moduna alır
• DB tablosu : Periyodik_Bakim
  Kolonlar   : Planid, Cihazid, BakimPeriyodu, BakimSirasi,
               PlanlananTarih, Bakim, Durum, BakimTarihi,
               BakimTipi, YapilanIslemler, Aciklama, Teknisyen, Rapor
"""
import time
import calendar
import datetime
import os

from dateutil.relativedelta import relativedelta

from PySide6.QtCore import Qt, QDate, QThread, Signal, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QComboBox, QDateEdit, QTextEdit, QFileDialog, QProgressBar,
    QCompleter, QAbstractItemView, QGroupBox, QSizePolicy, QMessageBox,
    QGraphicsDropShadowEffect, QDialog, QDialogButtonBox, QSpinBox,
    QCheckBox, QScrollArea, QFrame, QSplitter
)

from core.logger import logger
from ui.theme_manager import ThemeManager


S = ThemeManager.get_all_component_styles()

BAKIM_PERIYOTLARI = ["3 Ay", "6 Ay", "1 Yıl", "Tek Seferlik"]
DURUM_SECENEKLERI = ["Planlandı", "Yapıldı", "Gecikti", "İptal"]

DURUM_RENK = {
    "Yapıldı":   "#4caf50",
    "Gecikti":   "#f44336",
    "Planlandı": "#ffeb3b",
    "İptal":     "#9ca3af",
}


def _ay_ekle(kaynak_tarih, ay_sayisi: int):
    return kaynak_tarih + relativedelta(months=ay_sayisi)


# ═══════════════════════════════════════════════
#  THREAD SINIFLARI
# ═══════════════════════════════════════════════

class VeriYukleyici(QThread):
    veri_hazir  = Signal(list, dict, list)
    hata_olustu = Signal(str)

    def run(self):
        from database.sqlite_manager import SQLiteManager
        db = None
        try:
            db = SQLiteManager()
            from database.repository_registry import RepositoryRegistry
            registry = RepositoryRegistry(db)

            cihaz_combo = []
            cihaz_dict  = {}
            for c in registry.get("Cihazlar").get_all():
                c_id = str(c.get("Cihazid", "")).strip()
                if not c_id:
                    continue
                marka = str(c.get("Marka", ""))
                model = str(c.get("Model", ""))
                cihaz_combo.append(f"{c_id} | {marka} {model}".strip())
                cihaz_dict[c_id] = f"{marka} {model}".strip()

            bakimlar = registry.get("Periyodik_Bakim").get_all()
            bakimlar.sort(key=lambda x: x.get("PlanlananTarih", ""), reverse=True)

            self.veri_hazir.emit(sorted(cihaz_combo), cihaz_dict, bakimlar)
        except Exception as e:
            logger.error(f"Periyodik Bakım veri yükleme hatası: {e}")
            self.hata_olustu.emit(str(e))
        finally:
            if db:
                db.close()


class IslemKaydedici(QThread):
    islem_tamam = Signal()
    hata_olustu = Signal(str)

    def __init__(self, islem_tipi: str, veri, parent=None):
        super().__init__(parent)
        self._tip  = islem_tipi
        self._veri = veri

    def run(self):
        from database.sqlite_manager import SQLiteManager
        db = None
        try:
            db = SQLiteManager()
            from database.repository_registry import RepositoryRegistry
            repo = RepositoryRegistry(db).get("Periyodik_Bakim")

            if self._tip == "INSERT":
                for satir in self._veri:
                    repo.insert(satir)
            elif self._tip == "UPDATE":
                planid, yeni_degerler = self._veri
                repo.update(planid, yeni_degerler)

            self.islem_tamam.emit()
        except Exception as e:
            logger.error(f"Periyodik Bakım kayıt hatası: {e}")
            self.hata_olustu.emit(str(e))
        finally:
            if db:
                db.close()


class DosyaYukleyici(QThread):
    yuklendi = Signal(str)

    def __init__(self, yerel_yol: str, parent=None):
        super().__init__(parent)
        self._yol = yerel_yol

    def run(self):
        try:
            from database.google import GoogleDriveService
            link = GoogleDriveService().upload_file(self._yol)
            self.yuklendi.emit(link if link else "-")
        except Exception as e:
            logger.warning(f"Drive yükleme başarısız (devam ediliyor): {e}")
            self.yuklendi.emit("-")


# ═══════════════════════════════════════════════
#  AKILLI TAKVİM BANDI
# ═══════════════════════════════════════════════

class AkilliTakvimBandi(QWidget):
    """
    Sağ panelin üstünde sabit duran; ACIL / YAKIN / TOPLAM sayaçlarını
    ve opsiyonel bir kısa yol butonunu gösteren özet şerit.
    """
    filtre_istendi = Signal(str)   # "acil" | "yakin" | "tumu"

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(10)

        self._kartlar = {}
        tanim = [
            ("acil",  "🔴 ACIL",  "#f44336"),
            ("yakin", "🟡 YAKIN", "#ff9800"),
            ("normal","🔵 NORMAL","#4dabf7"),
        ]
        for key, metin, renk in tanim:
            btn = QPushButton(f"{metin}: 0")
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #2d2d2d;
                    border: 1px solid {renk};
                    border-radius: 6px;
                    color: {renk};
                    font-weight: bold;
                    font-size: 12px;
                    padding: 4px 14px;
                }}
                QPushButton:hover {{ background-color: #383838; }}
            """)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.clicked.connect(lambda _, k=key: self.filtre_istendi.emit(k))
            lay.addWidget(btn)
            self._kartlar[key] = btn

        lay.addStretch()

    def guncelle(self, bakimlar: list):
        """_tum_bakimlar listesini tarayarak sayaçları günceller."""
        bugun = datetime.date.today()
        acil = yakin = normal = 0
        for b in bakimlar:
            if str(b.get("Durum", "")) != "Planlandı":
                continue
            t_str = str(b.get("PlanlananTarih", ""))
            try:
                t = datetime.datetime.strptime(t_str, "%Y-%m-%d").date()
            except ValueError:
                continue
            delta = (t - bugun).days
            if delta < 0:
                acil += 1
            elif delta <= 7:
                yakin += 1
            else:
                normal += 1

        self._kartlar["acil"].setText(f"🔴 ACIL: {acil}")
        self._kartlar["yakin"].setText(f"🟡 YAKIN: {yakin}")
        self._kartlar["normal"].setText(f"🔵 NORMAL: {normal}")


# ═══════════════════════════════════════════════
#  TOPLU PLANLAMA DİALOGU
# ═══════════════════════════════════════════════

class TopluPlanlamaDialog(QDialog):
    """
    Öneriler 1 + 2: Birden fazla cihazı seçip tek seferde periyodik
    bakım planlaması yapılmasını sağlar.

    Adımlar:
      1) Cihaz listesini filtrele / seç (checkbox'lı tablo)
      2) Plan parametrelerini gir  (periyot, başlangıç, dönem sayısı)
      3) Önizleme → Oluştur
    """

    def __init__(self, cihaz_combo: list, cihaz_dict: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Toplu Bakım Planı Oluştur")
        self.setMinimumSize(720, 560)
        self.setStyleSheet("background:#1e1e1e; color:#e0e2ea;")

        self._cihaz_combo   = cihaz_combo   # ["ID | Marka Model", ...]
        self._cihaz_dict    = cihaz_dict    # {id: "Marka Model"}
        self._secilen_satirlar: list = []   # Oluşturulacak kayıtlar

        self._setup_ui()

    # ── UI ──────────────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Başlık
        lbl_baslik = QLabel("📋  Toplu Bakım Planı Oluştur")
        lbl_baslik.setStyleSheet("font-size:15px; font-weight:bold; color:#4dabf7;")
        root.addWidget(lbl_baslik)

        # ── ADIM 1: CİHAZ SEÇİMİ ──
        grp_cihaz = QGroupBox("1️⃣  Cihaz Seçimi")
        grp_cihaz.setStyleSheet("QGroupBox {color:#4CAF50; font-weight:bold; "
                                "border:1px solid #444; border-radius:6px; margin-top:16px;}"
                                "QGroupBox::title {subcontrol-origin:margin; left:10px; padding:0 8px;}")
        g_lay = QVBoxLayout(grp_cihaz)

        # Arama satırı
        h_ara = QHBoxLayout()
        self._ara_input = QLineEdit()
        self._ara_input.setPlaceholderText("Cihaz adı / ID ile filtrele...")
        self._ara_input.setStyleSheet("background:#2d2d2d; color:#e0e2ea; border:1px solid #555;"
                                       "border-radius:4px; padding:4px 8px; min-height:30px;")
        self._ara_input.textChanged.connect(self._tabloyu_filtrele)

        btn_hepsini_sec = QPushButton("☑ Tümünü Seç")
        btn_hepsini_sec.setStyleSheet("background:#2d2d2d; color:#4dabf7; border:1px solid #4dabf7;"
                                       "border-radius:4px; padding:4px 10px;")
        btn_hepsini_sec.clicked.connect(lambda: self._toplu_sec(True))

        btn_hepsini_kaldir = QPushButton("☐ Temizle")
        btn_hepsini_kaldir.setStyleSheet("background:#2d2d2d; color:#aaa; border:1px solid #555;"
                                          "border-radius:4px; padding:4px 10px;")
        btn_hepsini_kaldir.clicked.connect(lambda: self._toplu_sec(False))

        h_ara.addWidget(self._ara_input, 1)
        h_ara.addWidget(btn_hepsini_sec)
        h_ara.addWidget(btn_hepsini_kaldir)
        g_lay.addLayout(h_ara)

        # Cihaz tablosu
        self._cihaz_tablo = QTableWidget()
        self._cihaz_tablo.setColumnCount(3)
        self._cihaz_tablo.setHorizontalHeaderLabels(["", "Cihaz ID", "Cihaz Adı"])
        hdr = self._cihaz_tablo.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        self._cihaz_tablo.verticalHeader().setVisible(False)
        self._cihaz_tablo.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._cihaz_tablo.setSelectionMode(QAbstractItemView.NoSelection)
        self._cihaz_tablo.setStyleSheet(
            "QTableWidget {background:#1a1a1a; color:#e0e2ea; gridline-color:#333;}"
            "QHeaderView::section {background:#2d2d2d; color:#aaa; border:none; padding:4px;}"
        )
        self._cihaz_tablo.setMaximumHeight(200)
        self._cihaz_tablo.itemChanged.connect(self._secim_degisti)
        g_lay.addWidget(self._cihaz_tablo)

        self._lbl_secim_sayisi = QLabel("Seçilen: 0 cihaz")
        self._lbl_secim_sayisi.setStyleSheet("color:#aaa; font-size:11px;")
        g_lay.addWidget(self._lbl_secim_sayisi)

        root.addWidget(grp_cihaz)

        # ── ADIM 2: PLAN PARAMETRELERİ ──
        grp_param = QGroupBox("2️⃣  Plan Parametreleri")
        grp_param.setStyleSheet("QGroupBox {color:#FF9800; font-weight:bold; "
                                "border:1px solid #444; border-radius:6px; margin-top:16px;}"
                                "QGroupBox::title {subcontrol-origin:margin; left:10px; padding:0 8px;}")
        p_lay = QHBoxLayout(grp_param)

        combo_style = ("background:#2d2d2d; color:#e0e2ea; border:1px solid #555;"
                       "border-radius:4px; padding:4px; min-height:30px;")
        date_style  = ("background:#2d2d2d; color:#e0e2ea; border:1px solid #555;"
                       "border-radius:4px; padding:4px; min-height:30px;")
        spin_style  = ("background:#2d2d2d; color:#e0e2ea; border:1px solid #555;"
                       "border-radius:4px; padding:4px; min-height:30px;")

        # Periyot
        col1 = QVBoxLayout()
        col1.addWidget(QLabel("Bakım Periyodu:"))
        self._cmb_periyot = QComboBox()
        self._cmb_periyot.addItems(BAKIM_PERIYOTLARI)
        self._cmb_periyot.setStyleSheet(combo_style)
        self._cmb_periyot.currentIndexChanged.connect(self._onizleme_guncelle)
        col1.addWidget(self._cmb_periyot)

        # Başlangıç tarihi
        col2 = QVBoxLayout()
        col2.addWidget(QLabel("Başlangıç Tarihi:"))
        self._tarih = QDateEdit(QDate.currentDate())
        self._tarih.setCalendarPopup(True)
        self._tarih.setDisplayFormat("yyyy-MM-dd")
        self._tarih.setStyleSheet(date_style)
        self._tarih.dateChanged.connect(self._onizleme_guncelle)
        col2.addWidget(self._tarih)

        # Dönem sayısı
        col3 = QVBoxLayout()
        col3.addWidget(QLabel("Dönem Sayısı:"))
        self._spin_donem = QSpinBox()
        self._spin_donem.setRange(1, 12)
        self._spin_donem.setValue(4)
        self._spin_donem.setStyleSheet(spin_style)
        self._spin_donem.valueChanged.connect(self._onizleme_guncelle)
        col3.addWidget(self._spin_donem)

        # Teknisyen
        col4 = QVBoxLayout()
        col4.addWidget(QLabel("Teknisyen:"))
        self._teknisyen = QLineEdit()
        self._teknisyen.setStyleSheet("background:#2d2d2d; color:#e0e2ea; border:1px solid #555;"
                                       "border-radius:4px; padding:4px; min-height:30px;")
        col4.addWidget(self._teknisyen)

        for col in (col1, col2, col3, col4):
            lbl = col.itemAt(0).widget()
            lbl.setStyleSheet("color:#b0b0b0; font-size:11px; font-weight:bold;")
            p_lay.addLayout(col)

        root.addWidget(grp_param)

        # ── ADIM 3: ÖNİZLEME ──
        grp_onizleme = QGroupBox("3️⃣  Önizleme")
        grp_onizleme.setStyleSheet("QGroupBox {color:#4dabf7; font-weight:bold; "
                                   "border:1px solid #444; border-radius:6px; margin-top:16px;}"
                                   "QGroupBox::title {subcontrol-origin:margin; left:10px; padding:0 8px;}")
        o_lay = QVBoxLayout(grp_onizleme)
        self._lbl_onizleme = QLabel("— Henüz cihaz seçilmedi —")
        self._lbl_onizleme.setStyleSheet("color:#aaa; padding:6px;")
        self._lbl_onizleme.setWordWrap(True)
        o_lay.addWidget(self._lbl_onizleme)
        root.addWidget(grp_onizleme)

        # ── BUTONLAR ──
        self._btn_olustur = QPushButton("✓  PLANLA")
        self._btn_olustur.setMinimumHeight(42)
        self._btn_olustur.setEnabled(False)
        self._btn_olustur.setStyleSheet(
            "QPushButton {background:#4CAF50; color:white; font-weight:bold; "
            "border-radius:6px; font-size:13px;}"
            "QPushButton:disabled {background:#555; color:#888;}"
            "QPushButton:hover:!disabled {background:#45a049;}"
        )
        self._btn_olustur.clicked.connect(self._planlari_olustur)

        btn_iptal = QPushButton("İptal")
        btn_iptal.setMinimumHeight(42)
        btn_iptal.setStyleSheet(
            "QPushButton {background:#2d2d2d; color:#aaa; border:1px solid #555;"
            "border-radius:6px; font-size:13px;}"
            "QPushButton:hover {background:#383838;}"
        )
        btn_iptal.clicked.connect(self.reject)

        h_btn = QHBoxLayout()
        h_btn.addStretch()
        h_btn.addWidget(btn_iptal)
        h_btn.addWidget(self._btn_olustur)
        root.addLayout(h_btn)

        # Cihaz tablosunu doldur
        self._tabloyu_doldur(self._cihaz_combo)

    # ── Tablo ──────────────────────────────────────────────────

    def _tabloyu_doldur(self, combo_list: list):
        self._cihaz_tablo.setRowCount(0)
        self._cihaz_tablo.blockSignals(True)
        for entry in combo_list:
            parts = entry.split("|", 1)
            c_id  = parts[0].strip()
            c_ad  = parts[1].strip() if len(parts) > 1 else ""
            r = self._cihaz_tablo.rowCount()
            self._cihaz_tablo.insertRow(r)

            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk.setCheckState(Qt.Unchecked)
            self._cihaz_tablo.setItem(r, 0, chk)
            self._cihaz_tablo.setItem(r, 1, QTableWidgetItem(c_id))
            self._cihaz_tablo.setItem(r, 2, QTableWidgetItem(c_ad))
        self._cihaz_tablo.blockSignals(False)
        self._secim_degisti()

    def _tabloyu_filtrele(self, metin: str):
        metin = metin.lower()
        for r in range(self._cihaz_tablo.rowCount()):
            goster = (not metin
                      or metin in self._cihaz_tablo.item(r, 1).text().lower()
                      or metin in self._cihaz_tablo.item(r, 2).text().lower())
            self._cihaz_tablo.setRowHidden(r, not goster)

    def _toplu_sec(self, sec: bool):
        self._cihaz_tablo.blockSignals(True)
        durum = Qt.Checked if sec else Qt.Unchecked
        for r in range(self._cihaz_tablo.rowCount()):
            if not self._cihaz_tablo.isRowHidden(r):
                self._cihaz_tablo.item(r, 0).setCheckState(durum)
        self._cihaz_tablo.blockSignals(False)
        self._secim_degisti()

    def _secim_degisti(self):
        sayi = sum(
            1 for r in range(self._cihaz_tablo.rowCount())
            if self._cihaz_tablo.item(r, 0)
            and self._cihaz_tablo.item(r, 0).checkState() == Qt.Checked
        )
        self._lbl_secim_sayisi.setText(f"Seçilen: {sayi} cihaz")
        self._onizleme_guncelle()

    # ── Önizleme ───────────────────────────────────────────────

    def _onizleme_guncelle(self):
        secilen_cihazlar = [
            self._cihaz_tablo.item(r, 1).text()
            for r in range(self._cihaz_tablo.rowCount())
            if self._cihaz_tablo.item(r, 0)
            and self._cihaz_tablo.item(r, 0).checkState() == Qt.Checked
        ]
        cihaz_sayisi = len(secilen_cihazlar)
        donem_sayisi = self._spin_donem.value()
        toplam       = cihaz_sayisi * donem_sayisi

        if cihaz_sayisi == 0:
            self._lbl_onizleme.setText("— Henüz cihaz seçilmedi —")
            self._btn_olustur.setEnabled(False)
            return

        periyot = self._cmb_periyot.currentText()
        bas_t   = self._tarih.date().toPython()
        ay_adim = 3 if "3 Ay" in periyot else 6 if "6 Ay" in periyot else 12

        tarihler = []
        for i in range(donem_sayisi):
            t = _ay_ekle(bas_t, i * ay_adim)
            tarihler.append(t.strftime("%d.%m.%Y"))

        tarih_satirlari = "\n   • ".join(tarihler)
        metin = (
            f"<b>{toplam} bakım kaydı</b> oluşturulacak "
            f"({cihaz_sayisi} cihaz × {donem_sayisi} dönem)\n\n"
            f"Periyot: <b>{periyot}</b>   |   Dönem tarihleri:\n"
            f"   • {tarih_satirlari}"
        )
        self._lbl_onizleme.setText(metin)
        self._btn_olustur.setEnabled(True)
        self._btn_olustur.setText(f"✓  PLANLA  ({toplam} kayıt)")

    # ── Oluştur ────────────────────────────────────────────────

    def _planlari_olustur(self):
        secilen_ids = [
            self._cihaz_tablo.item(r, 1).text()
            for r in range(self._cihaz_tablo.rowCount())
            if self._cihaz_tablo.item(r, 0)
            and self._cihaz_tablo.item(r, 0).checkState() == Qt.Checked
        ]
        if not secilen_ids:
            return

        periyot    = self._cmb_periyot.currentText()
        bas_tarih  = self._tarih.date().toPython()
        donem      = self._spin_donem.value()
        teknisyen  = self._teknisyen.text().strip()
        ay_adim    = 3 if "3 Ay" in periyot else 6 if "6 Ay" in periyot else 12

        base_id = int(time.time())
        self._secilen_satirlar = []
        idx = 0
        for cihaz_id in secilen_ids:
            for i in range(donem):
                yeni_tarih = _ay_ekle(bas_tarih, i * ay_adim)
                self._secilen_satirlar.append({
                    "Planid":          f"P-{base_id + idx}",
                    "Cihazid":         cihaz_id,
                    "BakimPeriyodu":   periyot,
                    "BakimSirasi":     f"{i + 1}. Bakım",
                    "PlanlananTarih":  yeni_tarih.strftime("%Y-%m-%d"),
                    "Bakim":           "Periyodik",
                    "Durum":           "Planlandı",
                    "BakimTarihi":     "",
                    "BakimTipi":       "Periyodik",
                    "YapilanIslemler": "",
                    "Aciklama":        "",
                    "Teknisyen":       teknisyen,
                    "Rapor":           "",
                })
                idx += 1

        self.accept()

    def get_satirlar(self) -> list:
        """Dialog accept() sonrası oluşturulan kayıt listesini döner."""
        return self._secilen_satirlar


# ═══════════════════════════════════════════════
#  ANA SAYFA
# ═══════════════════════════════════════════════

class PeriyodikBakimPage(QWidget):

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(S["page"])
        self._db           = db

        self.inputs           = {}
        self._cihaz_sozlugu   = {}
        self._tum_bakimlar    = []
        self._secilen_plan_id = None
        self._secilen_dosya   = None
        self._mevcut_link     = None
        self._pending_cihaz_id = None # Yarış durumu için bekleyen cihaz ID'si

        self._setup_ui()
        self._verileri_yukle()

    # ─── UI ───────────────────────────────────────────────────

    def set_cihaz(self, cihaz_id: str):
        """
        Dışarıdan bir cihaz seçimi ayarlar.
        Veri yüklenmemişse, ID'yi beklemeye alır.
        """
        if not cihaz_id:
            return
        
        # Veri zaten yüklüyse, combobox'ı hemen ayarla
        if self._cihaz_sozlugu:
            self._set_combo_to_cihaz(cihaz_id)
        # Değilse, ID'yi daha sonra kullanmak üzere sakla
        else:
            self._pending_cihaz_id = cihaz_id
            logger.info(f"Veri yüklenmedi, cihaz ID'si ({cihaz_id}) beklemeye alındı.")

    def _set_combo_to_cihaz(self, cihaz_id: str):
        """Combobox'ı verilen cihaz ID'sine göre ayarlar."""
        if not cihaz_id:
            return

        # Formu temizle ki yeni bir planlama yapılabilsin
        self._formu_temizle()

        # Combobox'ta cihazı bul ve seç
        combo = self.inputs.get("Cihazid")
        if combo:
            for i in range(combo.count()):
                item_text = combo.itemText(i)
                if item_text.startswith(cihaz_id):
                    combo.setCurrentIndex(i)
                    self.inputs["BakimPeriyodu"].setEnabled(True)
                    self.inputs["PlanlananTarih"].setEnabled(True)
                    logger.info(f"Periyodik bakım formu, cihaz '{cihaz_id}' için ayarlandı.")
                    break
            else:
                logger.warning(f"Combobox'ta cihaz '{cihaz_id}' bulunamadı.")

    def _setup_ui(self):
        main = QHBoxLayout(self)
        main.setContentsMargins(15, 15, 15, 15)
        main.setSpacing(20)

        # ── SOL PANEL ──────────────────────────────────────────
        sol = QVBoxLayout()
        sol.setSpacing(12)

        # Kart 1: Planlama
        card_plan = QGroupBox("Bakım Planlama")
        card_plan.setStyleSheet(S["group"] + "QGroupBox { color: #4CAF50; }")
        card_plan_layout = QVBoxLayout(card_plan)
        card_plan_layout.setContentsMargins(15, 22, 15, 15)
        card_plan_layout.setSpacing(10)

        self.inputs["Cihazid"] = QComboBox()
        self.inputs["Cihazid"].setEditable(True)
        self.inputs["Cihazid"].setInsertPolicy(QComboBox.NoInsert)
        self.inputs["Cihazid"].setPlaceholderText("ID veya Marka ile arayın...")
        self.inputs["Cihazid"].setStyleSheet(S["combo"])
        comp = self.inputs["Cihazid"].completer()
        comp.setCompletionMode(QCompleter.PopupCompletion)
        comp.setFilterMode(Qt.MatchContains)
        lbl_cihaz = QLabel("Cihaz Seçimi:"); lbl_cihaz.setStyleSheet(S["label"])
        card_plan_layout.addWidget(lbl_cihaz)
        card_plan_layout.addWidget(self.inputs["Cihazid"])

        h_periyot = QHBoxLayout()
        h_periyot.setSpacing(10)
        self.inputs["BakimPeriyodu"] = QComboBox()
        self.inputs["BakimPeriyodu"].addItems(BAKIM_PERIYOTLARI)
        self.inputs["BakimPeriyodu"].setStyleSheet(S["combo"])
        self.inputs["PlanlananTarih"] = QDateEdit(QDate.currentDate())
        self.inputs["PlanlananTarih"].setCalendarPopup(True)
        self.inputs["PlanlananTarih"].setDisplayFormat("yyyy-MM-dd")
        self.inputs["PlanlananTarih"].setStyleSheet(S["date"])

        v_periyot = QVBoxLayout(); v_periyot.setSpacing(3)
        lbl_periyot = QLabel("Bakım Periyodu:"); lbl_periyot.setStyleSheet(S["label"])
        v_periyot.addWidget(lbl_periyot); v_periyot.addWidget(self.inputs["BakimPeriyodu"])
        h_periyot.addLayout(v_periyot)

        v_tarih = QVBoxLayout(); v_tarih.setSpacing(3)
        lbl_tarih = QLabel("Planlanan Tarih:"); lbl_tarih.setStyleSheet(S["label"])
        v_tarih.addWidget(lbl_tarih); v_tarih.addWidget(self.inputs["PlanlananTarih"])
        h_periyot.addLayout(v_tarih)

        card_plan_layout.addLayout(h_periyot)
        sol.addWidget(card_plan)

        # Kart 2: Aksiyon / Durum
        card_islem = QGroupBox("Aksiyon / Durum")
        card_islem.setStyleSheet(S["group"] + "QGroupBox { color: #FF9800; }")
        card_islem_layout = QVBoxLayout(card_islem)
        card_islem_layout.setContentsMargins(15, 22, 15, 15)
        card_islem_layout.setSpacing(10)

        h_durum = QHBoxLayout()
        h_durum.setSpacing(10)
        self.inputs["Durum"] = QComboBox()
        self.inputs["Durum"].addItems(DURUM_SECENEKLERI)
        self.inputs["Durum"].setStyleSheet(S["combo"])
        self.inputs["Durum"].currentTextChanged.connect(self._durum_kontrol)
        self.inputs["BakimTarihi"] = QDateEdit(QDate.currentDate())
        self.inputs["BakimTarihi"].setCalendarPopup(True)
        self.inputs["BakimTarihi"].setDisplayFormat("yyyy-MM-dd")
        self.inputs["BakimTarihi"].setStyleSheet(S["date"])

        v_durum = QVBoxLayout(); v_durum.setSpacing(3)
        lbl_durum = QLabel("Bakım Durumu:"); lbl_durum.setStyleSheet(S["label"])
        v_durum.addWidget(lbl_durum); v_durum.addWidget(self.inputs["Durum"])
        h_durum.addLayout(v_durum)

        v_yapilma = QVBoxLayout(); v_yapilma.setSpacing(3)
        lbl_yapilma = QLabel("Yapılma Tarihi:"); lbl_yapilma.setStyleSheet(S["label"])
        v_yapilma.addWidget(lbl_yapilma); v_yapilma.addWidget(self.inputs["BakimTarihi"])
        h_durum.addLayout(v_yapilma)

        card_islem_layout.addLayout(h_durum)

        self.inputs["Teknisyen"] = QLineEdit()
        self.inputs["Teknisyen"].setStyleSheet(S["input"])
        lbl_teknisyen = QLabel("Teknisyen:"); lbl_teknisyen.setStyleSheet(S["label"])
        card_islem_layout.addWidget(lbl_teknisyen)
        card_islem_layout.addWidget(self.inputs["Teknisyen"])

        lbl_yap = QLabel("Yapılan İşlemler:")
        lbl_yap.setStyleSheet(S["label"])
        self.inputs["YapilanIslemler"] = QTextEdit()
        self.inputs["YapilanIslemler"].setStyleSheet(S["input"])
        self.inputs["YapilanIslemler"].setMaximumHeight(65)
        card_islem_layout.addWidget(lbl_yap)
        card_islem_layout.addWidget(self.inputs["YapilanIslemler"])

        lbl_not = QLabel("Not / Açıklama:")
        lbl_not.setStyleSheet(S["label"])
        self.inputs["Aciklama"] = QTextEdit()
        self.inputs["Aciklama"].setStyleSheet(S["input"])
        self.inputs["Aciklama"].setMaximumHeight(55)
        card_islem_layout.addWidget(lbl_not)
        card_islem_layout.addWidget(self.inputs["Aciklama"])

        lbl_rapor = QLabel("Rapor Dosyası:")
        lbl_rapor.setStyleSheet(S["label"])
        h_rapor = QHBoxLayout()
        self.lbl_dosya = QLabel("Rapor Yok")
        self.lbl_dosya.setStyleSheet("color:#666; font-style:italic;")
        self.btn_dosya_ac = QPushButton("📄 Aç")
        self.btn_dosya_ac.setFixedSize(58, 32)
        self.btn_dosya_ac.setStyleSheet(S["action_btn"])
        self.btn_dosya_ac.setVisible(False)
        self.btn_dosya_ac.clicked.connect(self._dosyayi_ac)
        btn_yukle = QPushButton("📂 Yükle")
        btn_yukle.setFixedSize(68, 32)
        btn_yukle.setStyleSheet(S["file_btn"])
        btn_yukle.setCursor(QCursor(Qt.PointingHandCursor))
        btn_yukle.clicked.connect(self._dosya_sec)
        h_rapor.addWidget(self.lbl_dosya)
        h_rapor.addStretch()
        h_rapor.addWidget(self.btn_dosya_ac)
        h_rapor.addWidget(btn_yukle)
        card_islem_layout.addWidget(lbl_rapor)
        card_islem_layout.addLayout(h_rapor)
        sol.addWidget(card_islem)

        self.btn_yeni = QPushButton("Temizle / Yeni Plan")
        self.btn_yeni.setStyleSheet(S["cancel_btn"])
        self.btn_yeni.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_yeni.clicked.connect(self._formu_temizle)
        sol.addWidget(self.btn_yeni)

        # ── Toplu Planlama ──────────────────────────────────────
        self.btn_toplu = QPushButton("📋  Toplu Planlama (Çoklu Cihaz)")
        self.btn_toplu.setMinimumHeight(40)
        self.btn_toplu.setStyleSheet(
            "QPushButton {background:#1a3a5c; color:#4dabf7; border:1px solid #4dabf7;"
            "border-radius:6px; font-weight:bold; font-size:12px;}"
            "QPushButton:hover {background:#234870;}"
        )
        self.btn_toplu.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_toplu.clicked.connect(self._toplu_planla)
        sol.addWidget(self.btn_toplu)

        self.btn_kaydet = QPushButton("🗓️  Planı Oluştur")
        self.btn_kaydet.setMinimumHeight(48)
        self.btn_kaydet.setStyleSheet(S["save_btn"])
        self.btn_kaydet.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kaydet.clicked.connect(self._kaydet_baslat)
        sol.addWidget(self.btn_kaydet)
        sol.addStretch()

        sol_widget = QWidget()
        sol_widget.setLayout(sol)
        sol_widget.setFixedWidth(430)
        main.addWidget(sol_widget)

        # ── SAĞ PANEL ──────────────────────────────────────────
        sag = QVBoxLayout()

        grp_filtre = QGroupBox("Bakım Takvimi")
        grp_filtre.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        grp_filtre.setStyleSheet(
            "QGroupBox { font-size:14px; font-weight:bold; "
            "color:#4dabf7; margin-top:10px; }"
        )
        filter_lay = QHBoxLayout(grp_filtre)
        lbl_ay = QLabel("Ay Filtresi:")
        lbl_ay.setStyleSheet("color:#aaa;")
        self.cmb_filtre_ay = QComboBox()
        self.cmb_filtre_ay.addItems(["Tüm Aylar"] + list(calendar.month_name)[1:])
        self.cmb_filtre_ay.setFixedWidth(155)
        self.cmb_filtre_ay.setStyleSheet(S["combo"])
        self.cmb_filtre_ay.currentIndexChanged.connect(self._tabloyu_guncelle)
        btn_yenile = QPushButton("⟳")
        btn_yenile.setFixedSize(36, 36)
        btn_yenile.setStyleSheet(S["refresh_btn"])
        btn_yenile.setCursor(QCursor(Qt.PointingHandCursor))
        btn_yenile.clicked.connect(self._verileri_yukle)

        self.btn_kapat = QPushButton("✕ Kapat")
        self.btn_kapat.setToolTip("Kapat")
        self.btn_kapat.setFixedSize(36, 36)
        self.btn_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kapat.setStyleSheet(S["close_btn"])

        filter_lay.addStretch()
        filter_lay.addWidget(lbl_ay)
        filter_lay.addWidget(self.cmb_filtre_ay)
        filter_lay.addWidget(btn_yenile)
        filter_lay.addWidget(self.btn_kapat)
        sag.addWidget(grp_filtre)

        # ── Akıllı Takvim Bandı ──────────────────────────────────
        self._akilli_band = AkilliTakvimBandi()
        self._akilli_band.filtre_istendi.connect(self._akilli_filtre_uygula)
        sag.addWidget(self._akilli_band)

        self.tablo = QTableWidget()
        self.tablo.setColumnCount(7)
        self.tablo.setHorizontalHeaderLabels([
            "Plan ID", "Cihaz", "Planlanan Tarih",
            "Periyot", "Sıra", "Durum", "Teknisyen"
        ])
        hdr = self.tablo.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        for col in (0, 3, 4, 5):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.tablo.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tablo.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tablo.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.setAlternatingRowColors(True)
        self.tablo.setStyleSheet(S["table"])
        self.tablo.cellDoubleClicked.connect(self._satir_tiklandi)
        sag.addWidget(self.tablo, 1)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(S.get("progress", ""))
        sag.addWidget(self.progress)

        self.lbl_count = QLabel("Toplam: 0 kayıt")
        self.lbl_count.setStyleSheet(S["footer_label"])
        sag.addWidget(self.lbl_count)

        main.addLayout(sag, 1)

    # ─── Veri Yükleme ─────────────────────────────────────────

    def _verileri_yukle(self):
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self._loader = VeriYukleyici(self)
        self._loader.veri_hazir.connect(self._veriler_geldi)
        self._loader.hata_olustu.connect(self._hata_goster)
        self._loader.start()

    def _veriler_geldi(self, cihaz_combo: list, cihaz_dict: dict, bakimlar: list):
        self.progress.setVisible(False)
        self._cihaz_sozlugu = cihaz_dict
        self._tum_bakimlar  = bakimlar

        self.inputs["Cihazid"].clear()
        self.inputs["Cihazid"].addItem("")
        self.inputs["Cihazid"].addItems(cihaz_combo)
        self.inputs["Cihazid"].setEnabled(True)

        # Akıllı takvim bandını güncelle
        self._akilli_band.guncelle(bakimlar)

        self._tabloyu_guncelle()

        # Bekleyen bir cihaz ID'si varsa şimdi ayarla
        if self._pending_cihaz_id:
            self._set_combo_to_cihaz(self._pending_cihaz_id)
            self._pending_cihaz_id = None # Temizle

    # ─── Tablo ────────────────────────────────────────────────

    def _tabloyu_guncelle(self):
        self.tablo.setRowCount(0)
        ay_idx    = self.cmb_filtre_ay.currentIndex()
        gosterilen = 0
        bugun     = datetime.date.today()

        for row in self._tum_bakimlar:
            tarih = str(row.get("PlanlananTarih", ""))

            if ay_idx > 0:
                try:
                    dt = datetime.datetime.strptime(tarih, "%Y-%m-%d")
                    if dt.month != ay_idx:
                        continue
                except ValueError:
                    continue

            r = self.tablo.rowCount()
            self.tablo.insertRow(r)

            plan_id   = str(row.get("Planid", ""))
            cihaz_id  = str(row.get("Cihazid", ""))
            cihaz_ad  = self._cihaz_sozlugu.get(cihaz_id, cihaz_id)
            periyot   = str(row.get("BakimPeriyodu", ""))
            sira      = str(row.get("BakimSirasi", ""))
            durum     = str(row.get("Durum", ""))
            teknisyen = str(row.get("Teknisyen", ""))

            self.tablo.setItem(r, 0, QTableWidgetItem(plan_id))
            self.tablo.setItem(r, 1, QTableWidgetItem(cihaz_ad))

            # Tarih hücresi — Planlandı ise akıllı renk uygula
            item_tarih = QTableWidgetItem(tarih)
            if durum == "Planlandı" and tarih:
                try:
                    plan_t = datetime.datetime.strptime(tarih, "%Y-%m-%d").date()
                    delta  = (plan_t - bugun).days
                    if delta < 0:
                        item_tarih.setForeground(QColor("#f44336"))   # ACIL - kırmızı
                        item_tarih.setToolTip(f"⚠️ {abs(delta)} gün gecikti!")
                    elif delta <= 7:
                        item_tarih.setForeground(QColor("#ff9800"))   # YAKIN - turuncu
                        item_tarih.setToolTip(f"⏰ {delta} gün kaldı")
                except ValueError:
                    pass
            self.tablo.setItem(r, 2, item_tarih)

            self.tablo.setItem(r, 3, QTableWidgetItem(periyot))
            self.tablo.setItem(r, 4, QTableWidgetItem(sira))

            item_durum = QTableWidgetItem(durum)
            item_durum.setForeground(QColor(DURUM_RENK.get(durum, "#e0e2ea")))
            self.tablo.setItem(r, 5, item_durum)
            self.tablo.setItem(r, 6, QTableWidgetItem(teknisyen))

            self.tablo.item(r, 0).setData(Qt.UserRole, row)
            gosterilen += 1

        self.lbl_count.setText(f"Toplam: {gosterilen} kayıt")

    # ─── Akıllı Filtre ────────────────────────────────────────

    def _akilli_filtre_uygula(self, filtre: str):
        """
        AkilliTakvimBandi'ndan gelen filtre sinyaline göre tabloyu
        sadece ACIL / YAKIN / tüm 'Planlandı' kayıtlarını gösterecek şekilde günceller.
        """
        self.tablo.setRowCount(0)
        bugun     = datetime.date.today()
        gosterilen = 0

        for row in self._tum_bakimlar:
            durum = str(row.get("Durum", ""))
            if durum != "Planlandı":
                continue

            tarih_str = str(row.get("PlanlananTarih", ""))
            try:
                t     = datetime.datetime.strptime(tarih_str, "%Y-%m-%d").date()
                delta = (t - bugun).days
            except ValueError:
                continue

            if   filtre == "acil"  and delta >= 0:
                continue
            elif filtre == "yakin" and not (0 <= delta <= 7):
                continue
            # "tumu" → hepsini göster

            r = self.tablo.rowCount()
            self.tablo.insertRow(r)

            cihaz_id  = str(row.get("Cihazid", ""))
            cihaz_ad  = self._cihaz_sozlugu.get(cihaz_id, cihaz_id)
            periyot   = str(row.get("BakimPeriyodu", ""))
            sira      = str(row.get("BakimSirasi", ""))
            teknisyen = str(row.get("Teknisyen", ""))

            self.tablo.setItem(r, 0, QTableWidgetItem(str(row.get("Planid", ""))))
            self.tablo.setItem(r, 1, QTableWidgetItem(cihaz_ad))

            item_t = QTableWidgetItem(tarih_str)
            if delta < 0:
                item_t.setForeground(QColor("#f44336"))
                item_t.setToolTip(f"⚠️ {abs(delta)} gün gecikti!")
            elif delta <= 7:
                item_t.setForeground(QColor("#ff9800"))
                item_t.setToolTip(f"⏰ {delta} gün kaldı")
            self.tablo.setItem(r, 2, item_t)
            self.tablo.setItem(r, 3, QTableWidgetItem(periyot))
            self.tablo.setItem(r, 4, QTableWidgetItem(sira))

            item_d = QTableWidgetItem(durum)
            item_d.setForeground(QColor(DURUM_RENK.get(durum, "#e0e2ea")))
            self.tablo.setItem(r, 5, item_d)
            self.tablo.setItem(r, 6, QTableWidgetItem(teknisyen))
            self.tablo.item(r, 0).setData(Qt.UserRole, row)
            gosterilen += 1

        etiketler = {"acil": "🔴 ACIL", "yakin": "🟡 YAKIN", "tumu": "Tümü"}
        self.lbl_count.setText(
            f"{etiketler.get(filtre, filtre)}: {gosterilen} kayıt gösteriliyor"
        )

    # ─── Toplu Planlama ───────────────────────────────────────

    def _toplu_planla(self):
        """Toplu Planlama dialogunu açar; onaylanırsa kayıtları veritabanına yazar."""
        if not self._cihaz_sozlugu:
            QMessageBox.warning(self, "Uyarı", "Henüz cihaz verisi yüklenmedi.")
            return

        # Cihaz listesini combobox verisiyle oluştur
        combo_list = []
        for i in range(1, self.inputs["Cihazid"].count()):
            combo_list.append(self.inputs["Cihazid"].itemText(i))

        dlg = TopluPlanlamaDialog(
            cihaz_combo    = combo_list,
            cihaz_dict     = self._cihaz_sozlugu,
            parent         = self,
        )

        if dlg.exec() != QDialog.Accepted:
            return

        satirlar = dlg.get_satirlar()
        if not satirlar:
            return

        self.btn_toplu.setEnabled(False)
        self.btn_toplu.setText("⏳  Kaydediliyor...")
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)

        self._saver = IslemKaydedici("INSERT", satirlar, self)
        self._saver.islem_tamam.connect(self._toplu_islem_bitti)
        self._saver.hata_olustu.connect(self._hata_goster)
        self._saver.start()

    def _toplu_islem_bitti(self):
        self.progress.setVisible(False)
        self.btn_toplu.setEnabled(True)
        self.btn_toplu.setText("📋  Toplu Planlama (Çoklu Cihaz)")
        QMessageBox.information(self, "Başarılı", "Toplu bakım planları oluşturuldu.")
        self._verileri_yukle()

    # ─── Satır Seçimi ─────────────────────────────────────────

    def _satir_tiklandi(self, row: int, _col: int):
        item = self.tablo.item(row, 0)
        if not item:
            return
        row_data = item.data(Qt.UserRole)
        if not row_data:
            return

        self._secilen_plan_id = str(row_data.get("Planid", ""))
        self.btn_kaydet.setText("💾  Değişiklikleri Kaydet")
        self.btn_kaydet.setStyleSheet(S["save_btn"])

        self.inputs["Cihazid"].setEnabled(False)
        self.inputs["BakimPeriyodu"].setEnabled(False)
        self.inputs["PlanlananTarih"].setEnabled(False)

        cihaz_id = str(row_data.get("Cihazid", ""))
        idx = self.inputs["Cihazid"].findText(cihaz_id, Qt.MatchContains)
        if idx >= 0:
            self.inputs["Cihazid"].setCurrentIndex(idx)

        self.inputs["BakimPeriyodu"].setCurrentText(str(row_data.get("BakimPeriyodu", "")))

        t = str(row_data.get("PlanlananTarih", ""))
        if t:
            self.inputs["PlanlananTarih"].setDate(QDate.fromString(t, "yyyy-MM-dd"))

        bt = str(row_data.get("BakimTarihi", ""))
        self.inputs["BakimTarihi"].setDate(
            QDate.fromString(bt, "yyyy-MM-dd") if bt else QDate.currentDate()
        )

        self.inputs["Durum"].setCurrentText(str(row_data.get("Durum", "")))
        self.inputs["YapilanIslemler"].setPlainText(str(row_data.get("YapilanIslemler", "")))
        self.inputs["Aciklama"].setPlainText(str(row_data.get("Aciklama", "")))
        self.inputs["Teknisyen"].setText(str(row_data.get("Teknisyen", "")))

        link = str(row_data.get("Rapor", ""))
        if link.startswith("http"):
            self._mevcut_link = link
            self.btn_dosya_ac.setVisible(True)
            self.lbl_dosya.setText("✅  Rapor Mevcut")
            self.lbl_dosya.setStyleSheet("color:#4caf50; font-weight:bold;")
        else:
            self._mevcut_link = None
            self.btn_dosya_ac.setVisible(False)
            self.lbl_dosya.setText("Rapor Yok")
            self.lbl_dosya.setStyleSheet("color:#666; font-style:italic;")

        self._kilit_yonet(str(row_data.get("Durum", "")) == "Yapıldı")

    # ─── Form ─────────────────────────────────────────────────

    def _durum_kontrol(self):
        durum = self.inputs["Durum"].currentText()
        if durum == "Yapıldı":
            self.lbl_dosya.setText("Rapor Yükleyiniz")
            self.lbl_dosya.setStyleSheet("color:#ff9800; font-weight:bold;")
            self.inputs["Aciklama"].setPlaceholderText("Mutlaka giriniz")
        else:
            if not self._mevcut_link and not self._secilen_dosya:
                self.lbl_dosya.setText("Rapor Gerekmiyor")
                self.lbl_dosya.setStyleSheet("color:#666; font-style:italic;")

    def _kilit_yonet(self, tamamlandi_mi: bool):
        self.inputs["Durum"].setEnabled(not tamamlandi_mi)
        self.inputs["Teknisyen"].setReadOnly(tamamlandi_mi)
        self.inputs["BakimTarihi"].setEnabled(True)
        self.inputs["Aciklama"].setReadOnly(False)
        self.inputs["YapilanIslemler"].setReadOnly(False)
        self.btn_dosya_ac.setEnabled(True)
        self.btn_kaydet.setText(
            "💾  Notları / Dosyayı Güncelle" if tamamlandi_mi
            else "💾  Değişiklikleri Kaydet"
        )

    def _formu_temizle(self):
        self._secilen_plan_id = None
        self._secilen_dosya   = None
        self._mevcut_link     = None

        self.inputs["Cihazid"].setCurrentIndex(0)
        self.inputs["Cihazid"].setEnabled(True)
        self.inputs["BakimPeriyodu"].setCurrentIndex(0)
        self.inputs["BakimPeriyodu"].setEnabled(True)
        self.inputs["PlanlananTarih"].setDate(QDate.currentDate())
        self.inputs["PlanlananTarih"].setEnabled(True)
        self.inputs["BakimTarihi"].setDate(QDate.currentDate())
        self.inputs["Durum"].setCurrentIndex(0)
        self.inputs["Durum"].setEnabled(True)
        self.inputs["YapilanIslemler"].clear()
        self.inputs["Aciklama"].clear()
        self.inputs["Teknisyen"].setReadOnly(False)
        self.inputs["Teknisyen"].clear()

        self.lbl_dosya.setText("Rapor Yok")
        self.lbl_dosya.setStyleSheet("color:#666; font-style:italic;")
        self.btn_dosya_ac.setVisible(False)

        self.btn_kaydet.setText("🗓️  Planı Oluştur")
        self.btn_kaydet.setStyleSheet(S["save_btn"])
        self.btn_kaydet.setEnabled(True)

    # ─── Dosya ────────────────────────────────────────────────

    def _dosya_sec(self):
        yol, _ = QFileDialog.getOpenFileName(
            self, "Rapor Seç", "",
            "PDF ve Resim (*.pdf *.jpg *.jpeg *.png)"
        )
        if yol:
            self._secilen_dosya = yol
            self.lbl_dosya.setText(f"📎  {os.path.basename(yol)}")
            self.lbl_dosya.setStyleSheet("color:#ff9800; font-weight:bold;")

    def _dosyayi_ac(self):
        if self._mevcut_link:
            QDesktopServices.openUrl(QUrl(self._mevcut_link))

    # ─── Kayıt ────────────────────────────────────────────────

    def _kaydet_baslat(self):
        cihaz_text = self.inputs["Cihazid"].currentText().strip()
        if not cihaz_text:
            QMessageBox.warning(self, "Eksik Alan", "Cihaz seçmelisiniz.")
            return

        self.btn_kaydet.setText("İşleniyor...")
        self.btn_kaydet.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)

        cihaz_id = cihaz_text.split("|")[0].strip()

        if self._secilen_dosya:
            self._uploader = DosyaYukleyici(self._secilen_dosya, self)
            self._uploader.yuklendi.connect(
                lambda link: self._kaydet_devam(link, cihaz_id)
            )
            self._uploader.start()
        else:
            self._kaydet_devam("-", cihaz_id)

    def _kaydet_devam(self, dosya_link: str, cihaz_id: str):
        if dosya_link == "-" and self._mevcut_link:
            dosya_link = self._mevcut_link

        periyot   = self.inputs["BakimPeriyodu"].currentText()
        tarih     = self.inputs["PlanlananTarih"].date().toPython()
        tarih_str = tarih.strftime("%Y-%m-%d")
        durum     = self.inputs["Durum"].currentText()
        yapilan   = self.inputs["YapilanIslemler"].toPlainText().strip()
        aciklama  = self.inputs["Aciklama"].toPlainText().strip()
        teknisyen = self.inputs["Teknisyen"].text().strip()
        bakim_t   = self.inputs["BakimTarihi"].date().toString("yyyy-MM-dd") if durum == "Yapıldı" else ""

        if self._secilen_plan_id:
            yeni = {
                "Cihazid":         cihaz_id,
                "BakimPeriyodu":   periyot,
                "PlanlananTarih":  tarih_str,
                "Durum":           durum,
                "BakimTarihi":     bakim_t,
                "YapilanIslemler": yapilan,
                "Aciklama":        aciklama,
                "Teknisyen":       teknisyen,
                "Rapor":           dosya_link,
            }
            self._saver = IslemKaydedici("UPDATE", (self._secilen_plan_id, yeni), self)
        else:
            tekrar  = 1
            ay_adim = 0
            if "3 Ay"  in periyot: tekrar, ay_adim = 4,  3
            elif "6 Ay"  in periyot: tekrar, ay_adim = 2,  6
            elif "1 Yıl" in periyot: tekrar, ay_adim = 1, 12

            base_id  = int(time.time())
            satirlar = []
            for i in range(tekrar):
                yeni_tarih = _ay_ekle(tarih, i * ay_adim)
                ilk        = (i == 0)
                s_durum    = durum if ilk else "Planlandı"
                s_bakim_t  = bakim_t if (ilk and s_durum == "Yapıldı") else ""
                satirlar.append({
                    "Planid":          f"P-{base_id + i}",
                    "Cihazid":         cihaz_id,
                    "BakimPeriyodu":   periyot,
                    "BakimSirasi":     f"{i + 1}. Bakım",
                    "PlanlananTarih":  yeni_tarih.strftime("%Y-%m-%d"),
                    "Bakim":           "Periyodik",
                    "Durum":           s_durum,
                    "BakimTarihi":     s_bakim_t,
                    "BakimTipi":       "Periyodik",
                    "YapilanIslemler": yapilan   if ilk else "",
                    "Aciklama":        aciklama  if ilk else "",
                    "Teknisyen":       teknisyen if ilk else "",
                    "Rapor":           dosya_link if ilk else "",
                })
            self._saver = IslemKaydedici("INSERT", satirlar, self)

        self._saver.islem_tamam.connect(self._islem_bitti)
        self._saver.hata_olustu.connect(self._hata_goster)
        self._saver.start()

    def _islem_bitti(self):
        self.progress.setVisible(False)
        logger.info("Periyodik bakım kaydedildi.")
        QMessageBox.information(self, "Başarılı", "İşlem kaydedildi.")
        self._formu_temizle()
        self._verileri_yukle()

    def _hata_goster(self, mesaj: str):
        self.progress.setVisible(False)
        self.btn_kaydet.setEnabled(True)
        self.btn_kaydet.setText("🗓️  Planı Oluştur")
        QMessageBox.critical(self, "Hata", mesaj)

    def closeEvent(self, event):
        for attr in ("_loader", "_saver", "_uploader"):
            w = getattr(self, attr, None)
            if w and w.isRunning():
                w.quit()
                w.wait(500)
        event.accept()
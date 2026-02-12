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
    QGraphicsDropShadowEffect
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
#  YARDIMCI BİLEŞENLER
# ═══════════════════════════════════════════════

class _LabeledWidget(QWidget):
    def __init__(self, label_text: str, widget: QWidget, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(3)
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color:#b0b0b0; font-size:11px; font-weight:bold;")
        widget.setMinimumHeight(35)
        lay.addWidget(lbl)
        lay.addWidget(widget)


class _InfoCard(QGroupBox):
    def __init__(self, title: str, color: str = "#4dabf7", parent=None):
        super().__init__(title, parent)
        self.setStyleSheet(f"""
            QGroupBox {{
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 8px;
                margin-top: 20px;
                font-weight: bold;
                color: {color};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                left: 10px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 100))
        self.setGraphicsEffect(shadow)

        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(15, 22, 15, 15)
        self._lay.setSpacing(10)

    def add(self, item):
        if isinstance(item, QWidget):
            self._lay.addWidget(item)
        else:
            self._lay.addLayout(item)


# ═══════════════════════════════════════════════
#  ANA SAYFA
# ═══════════════════════════════════════════════

class PeriyodikBakimPage(QWidget):

    def __init__(self, db=None, yetki: str = "viewer",
                 kullanici_adi=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(S["page"])
        self._db           = db
        self.yetki         = yetki
        self.kullanici_adi = kullanici_adi

        self.inputs           = {}
        self._cihaz_sozlugu   = {}
        self._tum_bakimlar    = []
        self._secilen_plan_id = None
        self._secilen_dosya   = None
        self._mevcut_link     = None

        self._setup_ui()
        self._verileri_yukle()

    # ─── UI ───────────────────────────────────────────────────

    def _setup_ui(self):
        main = QHBoxLayout(self)
        main.setContentsMargins(15, 15, 15, 15)
        main.setSpacing(20)

        # ── SOL PANEL ──────────────────────────────────────────
        sol = QVBoxLayout()
        sol.setSpacing(12)

        # Kart 1: Planlama
        card_plan = _InfoCard("Bakım Planlama", color="#4CAF50")

        self.inputs["Cihazid"] = QComboBox()
        self.inputs["Cihazid"].setEditable(True)
        self.inputs["Cihazid"].setInsertPolicy(QComboBox.NoInsert)
        self.inputs["Cihazid"].setPlaceholderText("ID veya Marka ile arayın...")
        self.inputs["Cihazid"].setStyleSheet(S["combo"])
        comp = self.inputs["Cihazid"].completer()
        comp.setCompletionMode(QCompleter.PopupCompletion)
        comp.setFilterMode(Qt.MatchContains)
        card_plan.add(_LabeledWidget("Cihaz Seçimi:", self.inputs["Cihazid"]))

        h_periyot = QHBoxLayout()
        h_periyot.setSpacing(10)
        self.inputs["BakimPeriyodu"] = QComboBox()
        self.inputs["BakimPeriyodu"].addItems(BAKIM_PERIYOTLARI)
        self.inputs["BakimPeriyodu"].setStyleSheet(S["combo"])
        self.inputs["PlanlananTarih"] = QDateEdit(QDate.currentDate())
        self.inputs["PlanlananTarih"].setCalendarPopup(True)
        self.inputs["PlanlananTarih"].setDisplayFormat("yyyy-MM-dd")
        self.inputs["PlanlananTarih"].setStyleSheet(S["date"])
        h_periyot.addWidget(_LabeledWidget("Bakım Periyodu:", self.inputs["BakimPeriyodu"]))
        h_periyot.addWidget(_LabeledWidget("Planlanan Tarih:", self.inputs["PlanlananTarih"]))
        card_plan.add(h_periyot)
        sol.addWidget(card_plan)

        # Kart 2: Aksiyon / Durum
        card_islem = _InfoCard("Aksiyon / Durum", color="#FF9800")

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
        h_durum.addWidget(_LabeledWidget("Bakım Durumu:", self.inputs["Durum"]))
        h_durum.addWidget(_LabeledWidget("Yapılma Tarihi:", self.inputs["BakimTarihi"]))
        card_islem.add(h_durum)

        self.inputs["Teknisyen"] = QLineEdit()
        self.inputs["Teknisyen"].setStyleSheet(S["input"])
        if self.kullanici_adi:
            self.inputs["Teknisyen"].setText(str(self.kullanici_adi))
        card_islem.add(_LabeledWidget("Teknisyen:", self.inputs["Teknisyen"]))

        lbl_yap = QLabel("Yapılan İşlemler:")
        lbl_yap.setStyleSheet("color:#b0b0b0; font-size:11px; font-weight:bold;")
        self.inputs["YapilanIslemler"] = QTextEdit()
        self.inputs["YapilanIslemler"].setStyleSheet(S["input"])
        self.inputs["YapilanIslemler"].setMaximumHeight(65)
        card_islem.add(lbl_yap)
        card_islem.add(self.inputs["YapilanIslemler"])

        lbl_not = QLabel("Not / Açıklama:")
        lbl_not.setStyleSheet("color:#b0b0b0; font-size:11px; font-weight:bold;")
        self.inputs["Aciklama"] = QTextEdit()
        self.inputs["Aciklama"].setStyleSheet(S["input"])
        self.inputs["Aciklama"].setMaximumHeight(55)
        card_islem.add(lbl_not)
        card_islem.add(self.inputs["Aciklama"])

        lbl_rapor = QLabel("Rapor Dosyası:")
        lbl_rapor.setStyleSheet("color:#b0b0b0; font-size:11px; font-weight:bold;")
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
        card_islem.add(lbl_rapor)
        card_islem.add(h_rapor)
        sol.addWidget(card_islem)

        self.btn_yeni = QPushButton("Temizle / Yeni Plan")
        self.btn_yeni.setStyleSheet(S["cancel_btn"])
        self.btn_yeni.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_yeni.clicked.connect(self._formu_temizle)
        sol.addWidget(self.btn_yeni)

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

        self.btn_kapat = QPushButton("✕")
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

        self._tabloyu_guncelle()

    # ─── Tablo ────────────────────────────────────────────────

    def _tabloyu_guncelle(self):
        self.tablo.setRowCount(0)
        ay_idx    = self.cmb_filtre_ay.currentIndex()
        gosterilen = 0

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
            self.tablo.setItem(r, 2, QTableWidgetItem(tarih))
            self.tablo.setItem(r, 3, QTableWidgetItem(periyot))
            self.tablo.setItem(r, 4, QTableWidgetItem(sira))

            item_durum = QTableWidgetItem(durum)
            item_durum.setForeground(QColor(DURUM_RENK.get(durum, "#e0e2ea")))
            self.tablo.setItem(r, 5, item_durum)
            self.tablo.setItem(r, 6, QTableWidgetItem(teknisyen))

            self.tablo.item(r, 0).setData(Qt.UserRole, row)
            gosterilen += 1

        self.lbl_count.setText(f"Toplam: {gosterilen} kayıt")

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
        if self.kullanici_adi:
            self.inputs["Teknisyen"].setText(str(self.kullanici_adi))

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
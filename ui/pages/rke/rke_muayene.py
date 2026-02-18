# -*- coding: utf-8 -*-
"""
RKE Muayene Girişi Sayfası
────────────────────────────
• Sol: Tekli / toplu muayene formu + geçmiş
• Sağ: RKE listesi (QAbstractTableModel)
• itf_desktop mimarisine uygun (get_registry(db), core.logger, GoogleDriveService)
"""
import os
import time

from PySide6.QtCore import (
    Qt, QDate, QThread, Signal, QTimer,
    QAbstractTableModel, QModelIndex, QSortFilterProxyModel
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QProgressBar, QFrame, QComboBox, QLineEdit,
    QDateEdit, QGroupBox, QMessageBox, QTableView, QHeaderView,
    QAbstractItemView, QDialog, QListWidget, QFileDialog
)
from PySide6.QtGui import QColor, QCursor, QPalette, QStandardItemModel, QStandardItem

from core.logger import logger
from core.hata_yonetici import exc_logla
from ui.theme_manager import ThemeManager
from ui.styles import DarkTheme
from ui.styles.icons import IconRenderer

# ─── Merkezi Stiller ───
S = ThemeManager.get_all_component_styles()

# ─── RKE Listesi Tablo sütunları ───
RKE_COLUMNS = [
    ("EkipmanNo",     "Ekipman No",    120),
    ("AnaBilimDali",  "ABD",           140),
    ("Birim",         "Birim",         130),
    ("KoruyucuCinsi", "Cinsi",         130),
    ("KontrolTarihi", "Son Kontrol",   110),
    ("Durum",         "Durum",          90),
]

DURUM_RENK = {
    "Kullanıma Uygun":       QColor(DarkTheme.STATUS_SUCCESS),
    "Kullanıma Uygun Değil": QColor(DarkTheme.STATUS_ERROR),
    "Hurda":                  QColor(DarkTheme.STATUS_ERROR),
}


# ═══════════════════════════════════════════════
#  ÖZEL BİLEŞENLER
# ═══════════════════════════════════════════════

class CheckableComboBox(QComboBox):
    """Çoklu seçim yapılabilen ComboBox."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view().pressed.connect(self._handle_pressed)
        self.setModel(QStandardItemModel(self))
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        p = self.lineEdit().palette()
        p.setColor(QPalette.Base, QColor(DarkTheme.INPUT_BG))
        p.setColor(QPalette.Text, QColor(DarkTheme.TEXT_PRIMARY))
        self.lineEdit().setPalette(p)

    def _handle_pressed(self, index):
        item = self.model().itemFromIndex(index)
        item.setCheckState(Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked)
        QTimer.singleShot(10, self._update_text)

    def _update_text(self):
        checked = [
            self.model().item(i).text()
            for i in range(self.count())
            if self.model().item(i).checkState() == Qt.Checked
        ]
        self.lineEdit().setText(", ".join(checked))

    def set_checked_items(self, text_list):
        if isinstance(text_list, str):
            text_list = [x.strip() for x in text_list.split(",") if x.strip()] if text_list else []
        text_list = text_list or []
        for i in range(self.count()):
            item = self.model().item(i)
            item.setCheckState(Qt.Checked if item.text() in text_list else Qt.Unchecked)
        self._update_text()

    def get_checked_items(self):
        return self.lineEdit().text()

    def addItem(self, text, data=None):
        item = QStandardItem(text)
        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        item.setData(Qt.Unchecked, Qt.CheckStateRole)
        self.model().appendRow(item)

    def addItems(self, texts):
        for t in texts:
            self.addItem(t)


# ═══════════════════════════════════════════════
#  TABLO MODELİ (RKE Listesi)
# ═══════════════════════════════════════════════

class RKEListTableModel(QAbstractTableModel):

    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self._data    = data or []
        self._keys    = [c[0] for c in RKE_COLUMNS]
        self._headers = [c[1] for c in RKE_COLUMNS]

    def rowCount(self, parent=QModelIndex()):    return len(self._data)
    def columnCount(self, parent=QModelIndex()): return len(RKE_COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        row = self._data[index.row()]
        col = self._keys[index.column()]
        if role == Qt.DisplayRole:
            return str(row.get(col, ""))
        if role == Qt.ForegroundRole and col == "Durum":
            return DURUM_RENK.get(str(row.get(col, "")), QColor(DarkTheme.TEXT_MUTED))
        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter if col in ("KontrolTarihi", "Durum") else Qt.AlignVCenter | Qt.AlignLeft
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None

    def get_row(self, row_idx):
        return self._data[row_idx] if 0 <= row_idx < len(self._data) else None

    def set_data(self, data):
        self.beginResetModel()
        self._data = data or []
        self.endResetModel()


# ═══════════════════════════════════════════════
#  WORKER THREAD'LER
# ═══════════════════════════════════════════════

class VeriYukleyiciThread(QThread):
    """Tüm sayfa verilerini arka planda yükler."""
    # rke_data, teknik_acik, kontrol_edenler, birim_sorumlulari, tum_muayene
    veri_hazir  = Signal(list, list, list, list, list)
    hata_olustu = Signal(str)

    def run(self):
        from database.sqlite_manager import SQLiteManager
        from core.di import get_registry
        db = None
        try:
            db       = SQLiteManager()
            registry = get_registry(db)

            rke_data = registry.get("RKE_List").get_all()

            all_sabit = registry.get("Sabitler").get_all()
            teknik    = [
                str(x.get("MenuEleman", "")).strip()
                for x in all_sabit
                if x.get("Kod") == "RKE_Teknik" and x.get("MenuEleman", "").strip()
            ]

            tum_muayene = registry.get("RKE_Muayene").get_all()

            # Kontrol Eden ve Birim Sorumlusu: RKE_Muayene tablosundan benzersiz değerler
            kontrol_edenler = sorted(set(
                str(r.get("KontrolEdenUnvani", "")).strip()
                for r in tum_muayene
                if str(r.get("KontrolEdenUnvani", "")).strip()
            ))
            birim_sorumlulari = sorted(set(
                str(r.get("BirimSorumlusuUnvani", "")).strip()
                for r in tum_muayene
                if str(r.get("BirimSorumlusuUnvani", "")).strip()
            ))

            self.veri_hazir.emit(rke_data, teknik, kontrol_edenler, birim_sorumlulari, tum_muayene)
        except Exception as e:
            exc_logla("RKEMuayene.Worker", e)
            self.hata_olustu.emit(str(e))
        finally:
            if db:
                db.close()


class KayitWorkerThread(QThread):
    """Tek ekipman muayene kaydı."""
    kayit_tamam = Signal(str)
    hata_olustu = Signal(str)

    def __init__(self, veri_dict, dosya_yolu=None):
        super().__init__()
        self._veri       = veri_dict
        self._dosya_yolu = dosya_yolu

    def run(self):
        from database.sqlite_manager import SQLiteManager
        from core.di import get_registry
        db = None
        try:
            db       = SQLiteManager()
            registry = get_registry(db)

            # Drive yükleme
            if self._dosya_yolu:
                from core.di import get_cloud_adapter
                from database.google.utils import resolve_storage_target
                cloud = get_cloud_adapter()
                all_sabit = registry.get("Sabitler").get_all()
                storage_target = resolve_storage_target(all_sabit, "RKE_Raporlar")
                link = cloud.upload_file(
                    self._dosya_yolu,
                    parent_folder_id=storage_target["drive_folder_id"],
                    offline_folder_name=storage_target["offline_folder_name"]
                )
                if link:
                    self._veri["Rapor"] = link
                else:
                    logger.info("RKE Muayene: rapor yukleme atlandi/basarisiz (offline olabilir)")

            registry.get("RKE_Muayene").insert(self._veri)

            # RKE_List durum güncelle
            ekipman_no = self._veri.get("EkipmanNo")
            if ekipman_no:
                yeni_durum = (
                    "Kullanıma Uygun Değil"
                    if "Değil" in self._veri.get("FizikselDurum", "") or
                       "Değil" in self._veri.get("SkopiDurum", "")
                    else "Kullanıma Uygun"
                )
                repo_list = registry.get("RKE_List")
                target    = next(
                    (x for x in repo_list.get_all() if str(x.get("EkipmanNo")) == str(ekipman_no)),
                    None
                )
                if target and target.get("KayitNo"):
                    repo_list.update(target["KayitNo"], {
                        "Durum":         yeni_durum,
                        "KontrolTarihi": self._veri.get("FMuayeneTarihi")
                    })

            self.kayit_tamam.emit("Kayıt Başarılı")
        except Exception as e:
            exc_logla("RKEMuayene.Worker", e)
            self.hata_olustu.emit(str(e))
        finally:
            if db:
                db.close()


class TopluKayitWorkerThread(QThread):
    """Birden fazla ekipman için toplu muayene kaydı."""
    kayit_tamam = Signal(str)
    hata_olustu = Signal(str)

    def __init__(self, ekipman_listesi, ortak_veri, dosya_yolu=None):
        super().__init__()
        self._ekipmanlar = ekipman_listesi
        self._ortak_veri = ortak_veri
        self._dosya_yolu = dosya_yolu

    def run(self):
        from database.sqlite_manager import SQLiteManager
        from core.di import get_registry
        db = None
        try:
            db       = SQLiteManager()
            registry = get_registry(db)

            repo_muayene = registry.get("RKE_Muayene")
            repo_list    = registry.get("RKE_List")
            all_rke      = repo_list.get_all()

            dosya_link = ""
            if self._dosya_yolu:
                from core.di import get_cloud_adapter
                from database.google.utils import resolve_storage_target
                cloud        = get_cloud_adapter()
                all_sabit    = registry.get("Sabitler").get_all()
                storage_target = resolve_storage_target(all_sabit, "RKE_Raporlar")
                dosya_link = cloud.upload_file(
                    self._dosya_yolu,
                    parent_folder_id=storage_target["drive_folder_id"],
                    offline_folder_name=storage_target["offline_folder_name"]
                ) or ""

            for ekipman_no in self._ekipmanlar:
                item = self._ortak_veri.copy()
                item["EkipmanNo"] = ekipman_no
                item["KayitNo"]   = f"M-{int(time.time())}-{ekipman_no}"
                if dosya_link:
                    item["Rapor"] = dosya_link

                repo_muayene.insert(item)

                yeni_durum = (
                    "Kullanıma Uygun Değil"
                    if "Değil" in item.get("FizikselDurum", "") or
                       "Değil" in item.get("SkopiDurum", "")
                    else "Kullanıma Uygun"
                )
                target = next(
                    (x for x in all_rke if str(x.get("EkipmanNo")) == str(ekipman_no)),
                    None
                )
                if target and target.get("KayitNo"):
                    repo_list.update(target["KayitNo"], {
                        "Durum":         yeni_durum,
                        "KontrolTarihi": item.get("FMuayeneTarihi")
                    })

            self.kayit_tamam.emit("Toplu Kayıt Başarılı")
        except Exception as e:
            exc_logla("RKEMuayene.Worker", e)
            self.hata_olustu.emit(str(e))
        finally:
            if db:
                db.close()


# ═══════════════════════════════════════════════
#  TOPLU MUAYENE DİALOG
# ═══════════════════════════════════════════════

class TopluMuayeneDialog(QDialog):
    """Seçili ekipmanlara aynı anda muayene kaydı ekler."""

    def __init__(self, secilen_ekipmanlar, teknik_aciklamalar,
                 kontrol_listesi, sorumlu_listesi, kullanici_adi=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Toplu Muayene — {len(secilen_ekipmanlar)} Ekipman")
        self.resize(680, 640)
        self._ekipmanlar         = secilen_ekipmanlar
        self._teknik_aciklamalar = teknik_aciklamalar
        self._kontrol_listesi    = kontrol_listesi
        self._sorumlu_listesi    = sorumlu_listesi
        self._kullanici_adi      = kullanici_adi
        self._dosya_yolu         = None

        self._setup_ui()

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setSpacing(12)

        # Ekipman listesi
        grp_list = QGroupBox(f"Ekipmanlar ({len(self._ekipmanlar)})")
        grp_list.setStyleSheet(S.get("group", ""))
        v_list = QVBoxLayout(grp_list)
        lst = QListWidget()
        lst.addItems(self._ekipmanlar)
        lst.setFixedHeight(80)
        v_list.addWidget(lst)
        main.addWidget(grp_list)

        # Fiziksel
        self._grp_fiz = QGroupBox("Fiziksel Muayene")
        self._grp_fiz.setCheckable(True)
        self._grp_fiz.setChecked(True)
        self._grp_fiz.setStyleSheet(S.get("group", ""))
        h_fiz = QHBoxLayout(self._grp_fiz)
        self._dt_fiz  = self._make_date("Tarih")
        self._cmb_fiz = self._make_combo("Durum", ["Kullanıma Uygun", "Kullanıma Uygun Değil"])
        h_fiz.addWidget(self._dt_fiz["widget"])
        h_fiz.addWidget(self._cmb_fiz["widget"])
        main.addWidget(self._grp_fiz)

        # Skopi
        self._grp_sko = QGroupBox("Skopi Muayene")
        self._grp_sko.setCheckable(True)
        self._grp_sko.setChecked(False)
        self._grp_sko.setStyleSheet(S.get("group", ""))
        h_sko = QHBoxLayout(self._grp_sko)
        self._dt_sko  = self._make_date("Tarih")
        self._cmb_sko = self._make_combo("Durum", ["Kullanıma Uygun", "Kullanıma Uygun Değil", "Yapılmadı"])
        h_sko.addWidget(self._dt_sko["widget"])
        h_sko.addWidget(self._cmb_sko["widget"])
        main.addWidget(self._grp_sko)

        # Ortak bilgiler
        grp_ortak = QGroupBox("Ortak Bilgiler")
        grp_ortak.setStyleSheet(S.get("group", ""))
        v_ortak = QVBoxLayout(grp_ortak)

        h_pers = QHBoxLayout()
        self._cmb_kontrol = QComboBox()
        self._cmb_kontrol.setEditable(True)
        self._cmb_kontrol.setStyleSheet(S.get("combo", ""))
        self._cmb_kontrol.addItems(self._kontrol_listesi)
        if self._kullanici_adi:
            self._cmb_kontrol.setCurrentText(self._kullanici_adi)
        h_pers.addWidget(self._labeled("Kontrol Eden", self._cmb_kontrol))

        self._cmb_sorumlu = QComboBox()
        self._cmb_sorumlu.setEditable(True)
        self._cmb_sorumlu.setStyleSheet(S.get("combo", ""))
        self._cmb_sorumlu.addItems(self._sorumlu_listesi)
        h_pers.addWidget(self._labeled("Birim Sorumlusu", self._cmb_sorumlu))
        v_ortak.addLayout(h_pers)

        self._cmb_aciklama = CheckableComboBox()
        self._cmb_aciklama.setStyleSheet(S.get("combo", ""))
        self._cmb_aciklama.addItems(self._teknik_aciklamalar)
        v_ortak.addWidget(self._labeled("Teknik Açıklama (Çoklu Seçim)", self._cmb_aciklama))

        h_dosya = QHBoxLayout()
        self._lbl_dosya = QLabel("Dosya seçilmedi")
        self._lbl_dosya.setStyleSheet("color:#8b8fa3; font-size:11px;")
        btn_dosya = QPushButton("Ortak Rapor Sec")
        btn_dosya.setStyleSheet(S.get("file_btn", ""))
        btn_dosya.clicked.connect(self._sec_dosya)
        IconRenderer.set_button_icon(btn_dosya, "upload", color=DarkTheme.TEXT_PRIMARY, size=14)
        h_dosya.addWidget(self._lbl_dosya)
        h_dosya.addWidget(btn_dosya)
        v_ortak.addLayout(h_dosya)

        main.addWidget(grp_ortak)

        # Progress + Butonlar
        self._pbar = QProgressBar()
        self._pbar.setFixedHeight(4)
        self._pbar.setTextVisible(False)
        self._pbar.setVisible(False)
        main.addWidget(self._pbar)

        h_btn = QHBoxLayout()
        h_btn.addStretch()
        btn_iptal = QPushButton("Iptal")
        btn_iptal.setStyleSheet(S.get("cancel_btn", ""))
        btn_iptal.clicked.connect(self.reject)
        self._btn_baslat = QPushButton("Baslat")
        self._btn_baslat.setStyleSheet(S.get("save_btn", ""))
        self._btn_baslat.clicked.connect(self._on_save)
        IconRenderer.set_button_icon(btn_iptal, "x", color=DarkTheme.TEXT_PRIMARY, size=14)
        IconRenderer.set_button_icon(self._btn_baslat, "save", color=DarkTheme.TEXT_PRIMARY, size=14)
        h_btn.addWidget(btn_iptal)
        h_btn.addWidget(self._btn_baslat)
        main.addLayout(h_btn)

    def _labeled(self, label_text, widget):
        """Label + Widget sarmalayan container döndürür."""
        c = QWidget()
        c.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(c)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl = QLabel(label_text)
        lbl.setStyleSheet(S.get("label", ""))
        lay.addWidget(lbl)
        lay.addWidget(widget)
        return c

    def _make_date(self, label):
        c = QWidget()
        c.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(c)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl = QLabel(label)
        lbl.setStyleSheet(S.get("label", ""))
        de = QDateEdit(QDate.currentDate())
        de.setCalendarPopup(True)
        de.setDisplayFormat("yyyy-MM-dd")
        de.setStyleSheet(S.get("date", ""))
        self._setup_calendar(de)
        lay.addWidget(lbl)
        lay.addWidget(de)
        return {"widget": c, "date": de}

    def _make_combo(self, label, items):
        c = QWidget()
        c.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(c)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl = QLabel(label)
        lbl.setStyleSheet(S.get("label", ""))
        cmb = QComboBox()
        cmb.setStyleSheet(S.get("combo", ""))
        cmb.addItems(items)
        lay.addWidget(lbl)
        lay.addWidget(cmb)
        return {"widget": c, "combo": cmb}

    def _setup_calendar(self, date_edit):
        ThemeManager.setup_calendar_popup(date_edit)

    def _sec_dosya(self):
        yol, _ = QFileDialog.getOpenFileName(self, "Rapor Seç", "", "PDF / Resim (*.pdf *.jpg *.jpeg *.png)")
        if yol:
            self._dosya_yolu = yol
            self._lbl_dosya.setText(os.path.basename(yol))

    def _on_save(self):
        ortak_veri = {
            "FMuayeneTarihi": self._dt_fiz["date"].date().toString("yyyy-MM-dd") if self._grp_fiz.isChecked() else "",
            "FizikselDurum":  self._cmb_fiz["combo"].currentText()               if self._grp_fiz.isChecked() else "",
            "SMuayeneTarihi": self._dt_sko["date"].date().toString("yyyy-MM-dd") if self._grp_sko.isChecked() else "",
            "SkopiDurum":     self._cmb_sko["combo"].currentText()               if self._grp_sko.isChecked() else "",
            "Aciklamalar":    self._cmb_aciklama.get_checked_items(),
            "KontrolEden":    self._cmb_kontrol.currentText(),
            "BirimSorumlusu": self._cmb_sorumlu.currentText(),
            "Notlar":         "Toplu Kayıt",
        }
        self._btn_baslat.setEnabled(False)
        self._pbar.setVisible(True)
        self._pbar.setRange(0, 0)

        self._worker = TopluKayitWorkerThread(self._ekipmanlar, ortak_veri, self._dosya_yolu)
        self._worker.kayit_tamam.connect(lambda _: self.accept())
        self._worker.hata_olustu.connect(lambda e: QMessageBox.critical(self, "Hata", e))
        self._worker.start()


# ═══════════════════════════════════════════════
#  ANA SAYFA
# ═══════════════════════════════════════════════

class RKEMuayenePage(QWidget):
    """
    RKE Muayene Girişi sayfası.
    db: SQLiteManager instance
    """

    def __init__(self, db=None, kullanici_adi=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(S.get("page", "background-color: transparent;"))
        self._db             = db
        self._kullanici_adi  = kullanici_adi
        self._rke_data        = []
        self._tum_muayeneler  = []
        self._teknik_acik     = []
        self._kontrol_list    = []   # RKE_Muayene.KontrolEdenUnvani benzersiz değerleri
        self._sorumlu_list    = []   # RKE_Muayene.BirimSorumlusuUnvani benzersiz değerleri
        self._secilen_dosya   = None

        self._setup_ui()
        self._connect_signals()
        self.load_data()

    # ═══════════════════════════════════════════
    #  UI
    # ═══════════════════════════════════════════

    def _setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # ── SOL: FORM ──
        sol_widget = QWidget()
        sol_lay = QVBoxLayout(sol_widget)
        sol_lay.setContentsMargins(0, 0, 0, 0)
        sol_lay.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(S.get("scroll", ""))

        form_inner = QWidget()
        form_inner.setStyleSheet("background: transparent;")
        form_lay = QVBoxLayout(form_inner)
        form_lay.setContentsMargins(0, 0, 8, 0)
        form_lay.setSpacing(12)

        # 1. Ekipman Seçimi
        grp_ekipman = QGroupBox("Ekipman Secimi")
        grp_ekipman.setStyleSheet(S.get("group", ""))
        v_ekip = QVBoxLayout(grp_ekipman)
        self._cmb_rke = QComboBox()
        self._cmb_rke.setEditable(True)
        self._cmb_rke.setPlaceholderText("Ekipman Ara...")
        self._cmb_rke.setStyleSheet(S.get("combo", ""))
        v_ekip.addWidget(self._labeled("Ekipman No | Cinsi", self._cmb_rke))
        form_lay.addWidget(grp_ekipman)

        # 2. Muayene Detayları
        grp_detay = QGroupBox("Muayene Detaylari")
        grp_detay.setStyleSheet(S.get("group", ""))
        v_detay = QVBoxLayout(grp_detay)

        h_fiz = QHBoxLayout()
        self._dt_fiziksel = self._make_date_widget("Fiziksel Muayene Tarihi", h_fiz)
        self._cmb_fiziksel = self._make_combo_widget("Fiziksel Durum",
            ["Kullanıma Uygun", "Kullanıma Uygun Değil"], h_fiz)
        v_detay.addLayout(h_fiz)

        h_sko = QHBoxLayout()
        self._dt_skopi = self._make_date_widget("Skopi Muayene Tarihi", h_sko)
        self._cmb_skopi = self._make_combo_widget("Skopi Durumu",
            ["Kullanıma Uygun", "Kullanıma Uygun Değil", "Yapılmadı"], h_sko)
        v_detay.addLayout(h_sko)

        form_lay.addWidget(grp_detay)

        # 3. Sonuç ve Raporlama
        grp_sonuc = QGroupBox("Sonuc ve Raporlama")
        grp_sonuc.setStyleSheet(S.get("group", ""))
        v_sonuc = QVBoxLayout(grp_sonuc)

        h_pers = QHBoxLayout()
        self._cmb_kontrol = QComboBox()
        self._cmb_kontrol.setEditable(True)
        self._cmb_kontrol.setStyleSheet(S.get("combo", ""))
        h_pers.addWidget(self._labeled("Kontrol Eden", self._cmb_kontrol))

        self._cmb_sorumlu = QComboBox()
        self._cmb_sorumlu.setEditable(True)
        self._cmb_sorumlu.setStyleSheet(S.get("combo", ""))
        h_pers.addWidget(self._labeled("Birim Sorumlusu", self._cmb_sorumlu))
        v_sonuc.addLayout(h_pers)

        self._cmb_aciklama = CheckableComboBox()
        self._cmb_aciklama.setStyleSheet(S.get("combo", ""))
        v_sonuc.addWidget(self._labeled("Teknik Açıklama (Çoklu Seçim)", self._cmb_aciklama))

        h_dosya = QHBoxLayout()
        self._lbl_dosya = QLabel("Rapor seçilmedi")
        self._lbl_dosya.setStyleSheet(f"color:{DarkTheme.TEXT_MUTED}; font-size:11px; font-style:italic;")
        btn_dosya = QPushButton("Rapor Sec")
        btn_dosya.setStyleSheet(S.get("file_btn", ""))
        btn_dosya.setCursor(QCursor(Qt.PointingHandCursor))
        btn_dosya.clicked.connect(self._sec_dosya)
        IconRenderer.set_button_icon(btn_dosya, "upload", color=DarkTheme.TEXT_PRIMARY, size=14)
        h_dosya.addWidget(self._lbl_dosya)
        h_dosya.addWidget(btn_dosya)
        v_sonuc.addWidget(self._labeled("Varsa Rapor", QWidget()))  # placeholder
        v_sonuc.addLayout(h_dosya)

        form_lay.addWidget(grp_sonuc)

        # 4. Geçmiş Muayeneler
        grp_gecmis = QGroupBox("Gecmis Muayeneler")
        grp_gecmis.setStyleSheet(S.get("group", ""))
        v_gec = QVBoxLayout(grp_gecmis)

        self._gecmis_model = _GecmisMuayeneModel()
        self._gecmis_view  = QTableView()
        self._gecmis_view.setModel(self._gecmis_model)
        self._gecmis_view.setStyleSheet(S.get("table", ""))
        self._gecmis_view.verticalHeader().setVisible(False)
        self._gecmis_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._gecmis_view.setFixedHeight(140)
        hdr = self._gecmis_view.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        v_gec.addWidget(self._gecmis_view)
        form_lay.addWidget(grp_gecmis)

        form_lay.addStretch()

        scroll.setWidget(form_inner)
        sol_lay.addWidget(scroll, 1)

        # Progress
        self._pbar = QProgressBar()
        self._pbar.setFixedHeight(4)
        self._pbar.setTextVisible(False)
        self._pbar.setStyleSheet(S.get("progress", ""))
        self._pbar.setVisible(False)
        sol_lay.addWidget(self._pbar)

        # Butonlar
        h_btn = QHBoxLayout()
        h_btn.setSpacing(8)
        self._btn_temizle = QPushButton("TEMIZLE")
        self._btn_temizle.setStyleSheet(S.get("cancel_btn", ""))
        self._btn_temizle.setCursor(QCursor(Qt.PointingHandCursor))
        self._btn_kaydet = QPushButton("KAYDET")
        self._btn_kaydet.setStyleSheet(S.get("save_btn", ""))
        self._btn_kaydet.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self._btn_temizle, "x", color=DarkTheme.TEXT_PRIMARY, size=14)
        IconRenderer.set_button_icon(self._btn_kaydet, "save", color=DarkTheme.TEXT_PRIMARY, size=14)
        h_btn.addWidget(self._btn_temizle)
        h_btn.addWidget(self._btn_kaydet)
        sol_lay.addLayout(h_btn)

        root.addWidget(sol_widget, 35)

        # Dikey ayraç
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(S.get("separator", ""))
        root.addWidget(sep)

        # ── SAĞ: LİSTE ──
        sag_widget = QWidget()
        sag_lay = QVBoxLayout(sag_widget)
        sag_lay.setContentsMargins(0, 0, 0, 0)
        sag_lay.setSpacing(8)

        # Filtre paneli
        filter_frame = QFrame()
        filter_frame.setStyleSheet(S.get("filter_panel", ""))
        fl = QHBoxLayout(filter_frame)
        fl.setContentsMargins(12, 8, 12, 8)
        fl.setSpacing(8)

        self._cmb_filtre_abd = QComboBox()
        self._cmb_filtre_abd.addItem("Tüm Bölümler")
        self._cmb_filtre_abd.setStyleSheet(S.get("combo", ""))
        fl.addWidget(self._cmb_filtre_abd)

        self._txt_ara = QLineEdit()
        self._txt_ara.setPlaceholderText("Ekipman ara...")
        self._txt_ara.setClearButtonEnabled(True)
        self._txt_ara.setStyleSheet(S.get("search", ""))
        fl.addWidget(self._txt_ara)

        fl.addStretch()

        self._btn_yenile = QPushButton("Yenile")
        self._btn_yenile.setToolTip("Yenile")
        self._btn_yenile.setStyleSheet(S.get("refresh_btn", ""))
        self._btn_yenile.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self._btn_yenile, "sync", color=DarkTheme.TEXT_PRIMARY, size=14)
        fl.addWidget(self._btn_yenile)

        _sep_k = QFrame()
        _sep_k.setFrameShape(QFrame.VLine)
        _sep_k.setFixedHeight(20)
        _sep_k.setStyleSheet(S.get("separator", ""))
        fl.addWidget(_sep_k)

        self.btn_kapat = QPushButton("Kapat")
        self.btn_kapat.setToolTip("Pencereyi Kapat")
        self.btn_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kapat.setStyleSheet(S.get("close_btn", ""))
        IconRenderer.set_button_icon(self.btn_kapat, "x", color=DarkTheme.TEXT_PRIMARY, size=14)
        fl.addWidget(self.btn_kapat)

        sag_lay.addWidget(filter_frame)

        # Tablo
        self._list_model = RKEListTableModel()
        self._list_proxy = QSortFilterProxyModel()
        self._list_proxy.setSourceModel(self._list_model)
        self._list_proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self._list_proxy.setFilterKeyColumn(-1)

        self._list_view = QTableView()
        self._list_view.setModel(self._list_proxy)
        self._list_view.setStyleSheet(S.get("table", ""))
        self._list_view.verticalHeader().setVisible(False)
        self._list_view.setAlternatingRowColors(True)
        self._list_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._list_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._list_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._list_view.setSortingEnabled(True)
        hdr2 = self._list_view.horizontalHeader()
        hdr2.setSectionResizeMode(QHeaderView.Stretch)
        hdr2.setSectionResizeMode(len(RKE_COLUMNS) - 1, QHeaderView.ResizeToContents)

        sag_lay.addWidget(self._list_view, 1)

        # Toplu İşlem Butonu + Footer
        self._btn_toplu = QPushButton("Secili Ekipmanlara Toplu Muayene Ekle")
        self._btn_toplu.setStyleSheet(S.get("action_btn", ""))
        self._btn_toplu.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self._btn_toplu, "clipboard", color=DarkTheme.TEXT_PRIMARY, size=14)
        sag_lay.addWidget(self._btn_toplu)

        footer = QHBoxLayout()
        self._lbl_sayi = QLabel("0 kayıt")
        self._lbl_sayi.setStyleSheet(S.get("footer_label", f"color:{DarkTheme.TEXT_MUTED}; font-size:11px;"))
        footer.addStretch()
        footer.addWidget(self._lbl_sayi)
        sag_lay.addLayout(footer)

        root.addWidget(sag_widget, 65)

    def _labeled(self, text, widget):
        c = QWidget()
        c.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(c)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl = QLabel(text)
        lbl.setStyleSheet(S.get("label", ""))
        lay.addWidget(lbl)
        lay.addWidget(widget)
        return c

    def _make_date_widget(self, label_text, parent_layout):
        c = QWidget()
        c.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(c)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl = QLabel(label_text)
        lbl.setStyleSheet(S.get("label", ""))
        de = QDateEdit(QDate.currentDate())
        de.setCalendarPopup(True)
        de.setDisplayFormat("yyyy-MM-dd")
        de.setStyleSheet(S.get("date", ""))
        self._setup_calendar(de)
        lay.addWidget(lbl)
        lay.addWidget(de)
        parent_layout.addWidget(c)
        return de

    def _make_combo_widget(self, label_text, items, parent_layout):
        c = QWidget()
        c.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(c)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl = QLabel(label_text)
        lbl.setStyleSheet(S.get("label", ""))
        cmb = QComboBox()
        cmb.setStyleSheet(S.get("combo", ""))
        cmb.addItems(items)
        lay.addWidget(lbl)
        lay.addWidget(cmb)
        parent_layout.addWidget(c)
        return cmb

    def _setup_calendar(self, date_edit):
        ThemeManager.setup_calendar_popup(date_edit)

    # ═══════════════════════════════════════════
    #  SİNYALLER
    # ═══════════════════════════════════════════

    def _connect_signals(self):
        self._btn_kaydet.clicked.connect(self._on_save)
        self._btn_temizle.clicked.connect(self._on_clear)
        self._btn_yenile.clicked.connect(self.load_data)
        self._btn_toplu.clicked.connect(self._ac_toplu_dialog)
        self._txt_ara.textChanged.connect(self._list_proxy.setFilterFixedString)
        self._cmb_filtre_abd.currentTextChanged.connect(self._apply_filter)
        self._cmb_rke.currentIndexChanged.connect(self._on_ekipman_secildi)
        self._list_view.selectionModel().selectionChanged.connect(self._on_list_selection)

    # ═══════════════════════════════════════════
    #  VERİ
    # ═══════════════════════════════════════════

    def load_data(self):
        # Önceki thread hâlâ çalışıyorsa yeni başlatma
        if hasattr(self, "_loader") and self._loader.isRunning():
            return
        self._pbar.setVisible(True)
        self._pbar.setRange(0, 0)
        # self._loader referansı tutularak Python GC'nin thread'i erken silmesi engellenir.
        # deleteLater KULLANILMIYOR — kullanılırsa C++ nesnesi silinince sonraki
        # isRunning() çağrısı RuntimeError fırlatır ve load_data sessizce çıkar.
        self._loader = VeriYukleyiciThread()
        self._loader.veri_hazir.connect(self._on_data_ready)
        self._loader.hata_olustu.connect(self._on_error)
        self._loader.finished.connect(lambda: self._pbar.setVisible(False))
        self._loader.start()

    def _on_data_ready(self, rke_data, teknik, kontrol_listesi, sorumlu_listesi, tum_muayene):
        self._rke_data       = rke_data
        self._teknik_acik    = teknik
        self._kontrol_list   = kontrol_listesi
        self._sorumlu_list   = sorumlu_listesi
        self._tum_muayeneler = tum_muayene

        # Ekipman combosu
        self._cmb_rke.blockSignals(True)
        self._cmb_rke.clear()
        items = sorted([
            f"{str(r.get('EkipmanNo', '')).strip()} | {str(r.get('KoruyucuCinsi', '')).strip()}"
            for r in rke_data if r.get("EkipmanNo")
        ])
        self._cmb_rke.addItems(items)
        self._cmb_rke.setCurrentIndex(-1)
        self._cmb_rke.blockSignals(False)

        # Teknik açıklama
        self._cmb_aciklama.clear()
        self._cmb_aciklama.addItems(teknik)

        # Kontrol Eden — RKE_Muayene.KontrolEdenUnvani'dan benzersiz değerler
        self._cmb_kontrol.blockSignals(True)
        mevcut_kontrol = self._cmb_kontrol.currentText()
        self._cmb_kontrol.clear()
        self._cmb_kontrol.addItems(kontrol_listesi)
        # Önceki değeri koru veya kullanıcı adını yaz
        if self._kullanici_adi:
            self._cmb_kontrol.setCurrentText(self._kullanici_adi)
        elif mevcut_kontrol:
            self._cmb_kontrol.setCurrentText(mevcut_kontrol)
        self._cmb_kontrol.blockSignals(False)

        # Birim Sorumlusu — RKE_Muayene.BirimSorumlusuUnvani'dan benzersiz değerler
        self._cmb_sorumlu.blockSignals(True)
        mevcut_sorumlu = self._cmb_sorumlu.currentText()
        self._cmb_sorumlu.clear()
        self._cmb_sorumlu.addItems(sorumlu_listesi)
        if mevcut_sorumlu:
            self._cmb_sorumlu.setCurrentText(mevcut_sorumlu)
        self._cmb_sorumlu.blockSignals(False)

        # ABD filtre
        abd_set = set(str(r.get("AnaBilimDali", "")).strip() for r in rke_data if r.get("AnaBilimDali"))
        self._cmb_filtre_abd.blockSignals(True)
        self._cmb_filtre_abd.clear()
        self._cmb_filtre_abd.addItem("Tüm Bölümler")
        self._cmb_filtre_abd.addItems(sorted(abd_set))
        self._cmb_filtre_abd.blockSignals(False)

        self._apply_filter()

    def _apply_filter(self):
        f_abd = self._cmb_filtre_abd.currentText()
        filtered = [
            r for r in self._rke_data
            if f_abd == "Tüm Bölümler" or str(r.get("AnaBilimDali", "")).strip() == f_abd
        ]
        self._list_model.set_data(filtered)
        self._lbl_sayi.setText(f"{len(filtered)} Ekipman")

    def _on_list_selection(self):
        """Tabloda satır seçilince sol formdaki combo'yu güncelle."""
        indexes = self._list_view.selectionModel().selectedRows()
        if len(indexes) != 1:
            return
        src_idx  = self._list_proxy.mapToSource(indexes[0])
        row_data = self._list_model.get_row(src_idx.row())
        if not row_data:
            return
        ekipman_no = str(row_data.get("EkipmanNo", "")).strip()
        idx = self._cmb_rke.findText(ekipman_no, Qt.MatchContains)
        if idx >= 0:
            self._cmb_rke.blockSignals(True)
            self._cmb_rke.setCurrentIndex(idx)
            self._cmb_rke.blockSignals(False)
        self._goster_gecmis(ekipman_no)

    def _on_ekipman_secildi(self):
        txt = self._cmb_rke.currentText()
        if not txt:
            return
        ekipman_no = txt.split("|")[0].strip()
        self._goster_gecmis(ekipman_no)

    def _goster_gecmis(self, ekipman_no):
        gecmis = [
            m for m in self._tum_muayeneler
            if str(m.get("EkipmanNo", "")).strip() == ekipman_no
        ]
        self._gecmis_model.set_data(gecmis)

    # ═══════════════════════════════════════════
    #  DOSYA
    # ═══════════════════════════════════════════

    def _sec_dosya(self):
        yol, _ = QFileDialog.getOpenFileName(self, "Rapor Seç", "", "PDF / Resim (*.pdf *.jpg *.jpeg *.png)")
        if yol:
            self._secilen_dosya = yol
            self._lbl_dosya.setText(os.path.basename(yol))
            logger.info(f"RKE rapor dosyası seçildi: {yol}")

    # ═══════════════════════════════════════════
    #  KAYDET
    # ═══════════════════════════════════════════

    def _on_save(self):
        txt = self._cmb_rke.currentText()
        if not txt:
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen bir ekipman seçin.")
            return

        ekipman_no = txt.split("|")[0].strip()
        veri = {
            "KayitNo":              f"M-{int(time.time())}",
            "EkipmanNo":            ekipman_no,
            "FMuayeneTarihi":       self._dt_fiziksel.date().toString("yyyy-MM-dd"),
            "FizikselDurum":        self._cmb_fiziksel.currentText(),
            "SMuayeneTarihi":       self._dt_skopi.date().toString("yyyy-MM-dd"),
            "SkopiDurum":           self._cmb_skopi.currentText(),
            "Aciklamalar":          self._cmb_aciklama.get_checked_items(),
            "KontrolEdenUnvani":    self._cmb_kontrol.currentText(),
            "BirimSorumlusuUnvani": self._cmb_sorumlu.currentText(),
            "Notlar":               "",
        }

        self._pbar.setVisible(True)
        self._pbar.setRange(0, 0)
        self._btn_kaydet.setEnabled(False)

        self._saver = KayitWorkerThread(veri, self._secilen_dosya)
        self._saver.kayit_tamam.connect(self._on_save_success)
        self._saver.hata_olustu.connect(self._on_error)
        self._saver.start()

    def _on_save_success(self, msg):
        self._pbar.setVisible(False)
        self._btn_kaydet.setEnabled(True)
        QMessageBox.information(self, "Başarılı", msg)
        self._on_clear()
        self.load_data()

    def _on_clear(self):
        self._cmb_rke.setCurrentIndex(-1)
        self._dt_fiziksel.setDate(QDate.currentDate())
        self._dt_skopi.setDate(QDate.currentDate())
        self._cmb_fiziksel.setCurrentIndex(0)
        self._cmb_skopi.setCurrentIndex(0)
        self._cmb_aciklama.set_checked_items([])
        # Kontrol Eden: varsa kullanıcı adını koru, yoksa boş bırak
        if self._kullanici_adi:
            self._cmb_kontrol.setCurrentText(self._kullanici_adi)
        else:
            self._cmb_kontrol.clearEditText()
        self._cmb_sorumlu.clearEditText()
        self._lbl_dosya.setText("Rapor seçilmedi")
        self._secilen_dosya = None
        self._gecmis_model.set_data([])

    def _on_error(self, msg):
        self._pbar.setVisible(False)
        self._btn_kaydet.setEnabled(True)
        logger.error(f"RKEMuayene hatası: {msg}")
        QMessageBox.critical(self, "Hata", msg)

    # ═══════════════════════════════════════════
    #  TOPLU MUAYENE
    # ═══════════════════════════════════════════

    def _ac_toplu_dialog(self):
        indexes = self._list_view.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.warning(self, "Uyarı", "Listeden en az bir ekipman seçin (Ctrl/Shift ile çoklu seçim).")
            return

        ekipmanlar = sorted(set(
            str(self._list_model.get_row(self._list_proxy.mapToSource(idx).row()).get("EkipmanNo", "")).strip()
            for idx in indexes
        ))

        dlg = TopluMuayeneDialog(
            ekipmanlar,
            self._teknik_acik,
            self._kontrol_list,
            self._sorumlu_list,
            self._kullanici_adi,
            self
        )
        if dlg.exec() == QDialog.Accepted:
            QMessageBox.information(self, "Bilgi", "Toplu kayıt tamamlandı.")
            self.load_data()


# ═══════════════════════════════════════════════
#  GEÇMIŞ MUAYENE TABLO MODELİ
# ═══════════════════════════════════════════════

_GECMIS_COLS = [
    ("FMuayeneTarihi",  "Fiz. Tarih"),
    ("SMuayeneTarihi",  "Skopi Tarih"),
    ("Aciklamalar",     "Açıklama"),
    ("FizikselDurum",   "Sonuç"),
]

class _GecmisMuayeneModel(QAbstractTableModel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data    = []
        self._keys    = [c[0] for c in _GECMIS_COLS]
        self._headers = [c[1] for c in _GECMIS_COLS]

    def rowCount(self, parent=QModelIndex()):    return len(self._data)
    def columnCount(self, parent=QModelIndex()): return len(_GECMIS_COLS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        row = self._data[index.row()]
        col = self._keys[index.column()]
        if role == Qt.DisplayRole:
            return str(row.get(col, ""))
        if role == Qt.ForegroundRole and col == "FizikselDurum":
            return QColor(DarkTheme.STATUS_ERROR) if "Değil" in str(row.get(col, "")) else QColor(DarkTheme.STATUS_SUCCESS)
        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter if col in ("FMuayeneTarihi", "SMuayeneTarihi", "FizikselDurum") else Qt.AlignVCenter | Qt.AlignLeft
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None

    def set_data(self, data):
        self.beginResetModel()
        self._data = data or []
        self.endResetModel()

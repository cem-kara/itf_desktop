# -*- coding: utf-8 -*-
"""RKE Muayene Girisi - rke_yonetim tasarimiyla uyumlu."""
import sys
import os
import datetime
import uuid
from typing import List, Dict, Optional

from PySide6.QtCore import (Qt, QDate, QThread, Signal, QAbstractTableModel,
                             QModelIndex, QTimer, QUrl)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QAbstractItemView,
    QTableView, QHeaderView, QLabel, QPushButton, QComboBox,
    QDateEdit, QLineEdit, QTextEdit, QProgressBar, QScrollArea,
    QFrame, QGroupBox, QGridLayout, QFileDialog,
    QDialog, QListWidget, QCheckBox, QApplication,
)
from PySide6.QtGui import QColor, QCursor, QDesktopServices, QStandardItemModel, QStandardItem, QPalette

from ui.styles.colors import C as _C
from ui.styles.icons import IconRenderer
from ui.components.base_table_model import BaseTableModel
from ui.pages.rke.components.toplu_muayene_dialog import TopluMuayeneDialog
from core.paths import DB_PATH
from core.hata_yonetici import hata_goster, bilgi_goster, uyari_goster
from core.storage.storage_service import StorageService

# --- YOL AYARLARI ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir  = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from core.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger("RKEMuayene")

try:
    from database.google import GoogleDriveService  # type: ignore
except ImportError:  # type: ignore
    class GoogleDriveService:  # type: ignore
        def upload_file(self, a, b): return None

try:
    from dateutil.relativedelta import relativedelta  # type: ignore
except ImportError:  # type: ignore
    class relativedelta:  # type: ignore
        def __init__(self, **kw): self.years = kw.get("years", 0)
        def __radd__(self, dt): return dt.replace(year=dt.year + self.years)

try:
    from core.auth.authorization_service import YetkiYoneticisi  # type: ignore
except (ImportError, ModuleNotFoundError):  # type: ignore
    class YetkiYoneticisi:  # type: ignore
        @staticmethod
        def uygula(w, key): pass

from ui.styles.colors import DarkTheme


# RKE envanter tablo kolonlari
_RKE_COLS = [
    ("EkipmanNo",        "EKIPMAN NO",  120),
    ("KoruyucuNumarasi", "KORUYUCU NO", 140),
    ("AnaBilimDali",     "ABD",         110),
    ("Birim",            "BIRIM",       110),
    ("KoruyucuCinsi",    "CINS",        110),
    ("KursunEsdegeri",   "Pb",           70),
    ("HizmetYili",       "YIL",          60),
    ("Bedeni",           "BEDEN",        70),
    ("KontrolTarihi",    "KONTROL T.",  100),
    ("Durum",            "DURUM",       120),
]
_RKE_KEYS = [c[0] for c in _RKE_COLS]
_RKE_HEADERS = [c[1] for c in _RKE_COLS]
_RKE_WIDTHS = [c[2] for c in _RKE_COLS]


# ==================================================================
#  FieldGroup - mockup'in fgroup bileseni
# ==================================================================
class FieldGroup(QGroupBox):
    """
    QGroupBox tabanlı grup kutusu — tema sistemiyle uyumlu.
    color parametresi başlık aksan rengini belirler.
    Arka plan ve kenarlık tema QSS tarafından otomatik uygulanır.
    """
    def __init__(self, title: str, color: str = "", parent=None):
        super().__init__(title, parent)
        # Başlık rengini sadece color özelliğiyle override et
        if color:
            self.setStyleSheet(f"QGroupBox::title {{ color: {color}; }}")
        self._bl = QVBoxLayout(self)
        self._bl.setContentsMargins(10, 10, 10, 12)
        self._bl.setSpacing(8)

    def add_widget(self, w): self._bl.addWidget(w)
    def add_layout(self, l): self._bl.addLayout(l)
    def body_layout(self) -> QVBoxLayout: return self._bl



# ----------------------------------------------------------------
# YARDIMCI FONKSIYONLAR
# ----------------------------------------------------------------

def envanter_durumunu_belirle(fiziksel: str, skopi: str) -> str:
    fiz_ok = (fiziksel == "Kullanima Uygun")
    sko_ok = (skopi in ("Kullanima Uygun", "Yapilmadi"))
    return "Kullanima Uygun" if fiz_ok and sko_ok else "Kullanima Uygun Degil"


# ----------------------------------------------------------------
# CHECKABLE COMBOBOX (degismedi)
# ----------------------------------------------------------------

class CheckableComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view().pressed.connect(self.handleItemPressed)
        self.setModel(QStandardItemModel(self))
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)  # type: ignore

    def handleItemPressed(self, index):
        item = self.model().itemFromIndex(index)  # type: ignore
        item.setCheckState(Qt.CheckState.Unchecked if item.checkState() == Qt.CheckState.Checked else Qt.CheckState.Checked)
        QTimer.singleShot(10, self.updateText)

    def updateText(self):
        items = [self.model().item(i).text()  # type: ignore
                 for i in range(self.count())
                 if self.model().item(i).checkState() == Qt.CheckState.Checked]  # type: ignore
        self.lineEdit().setText(", ".join(items))  # type: ignore

    def setCheckedItems(self, text_list):
        if isinstance(text_list, str):
            text_list = [x.strip() for x in text_list.split(',')] if text_list else []
        elif not text_list:
            text_list = []
        for i in range(self.count()):
            item = self.model().item(i)  # type: ignore
            item.setCheckState(Qt.CheckState.Checked if item.text() in text_list else Qt.CheckState.Unchecked)
        self.updateText()

    def getCheckedItems(self): return self.lineEdit().text()  # type: ignore

    def addItem(self, text, *, userData=None):  # type: ignore
        item = QStandardItem(text)
        item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)  # type: ignore
        item.setData(Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
        self.model().appendRow(item)  # type: ignore

    def addItems(self, texts):
        for t in texts: self.addItem(t)


# ==========================================================================================================================
#  WORKER THREADS (degismedi)
# ==========================================================================================================================

class VeriYukleyici(QThread):
    veri_hazir  = Signal(list, list, dict, list, list, list, list, list)
    hata_olustu = Signal(str)

    def __init__(self, db_path=None):
        super().__init__()
        self._db_path = db_path or DB_PATH

    @staticmethod
    def _repo_muayene_to_table(rows: List[Dict]):
        if not rows:
            return [], []
        headers = [
            "KayitNo", "EkipmanNo", "FMuayeneTarihi", "FizikselDurum",
            "SMuayeneTarihi", "SkopiDurum", "Aciklamalar",
            "KontrolEden/Unvani", "BirimSorumlusu/Unvani", "Not", "Rapor"
        ]
        data = []
        for r in rows:
            data.append([
                r.get("KayitNo", ""),
                r.get("EkipmanNo", ""),
                r.get("FMuayeneTarihi", ""),
                r.get("FizikselDurum", ""),
                r.get("SMuayeneTarihi", ""),
                r.get("SkopiDurum", ""),
                r.get("Aciklamalar", ""),
                r.get("KontrolEdenUnvani", ""),
                r.get("BirimSorumlusuUnvani", ""),
                r.get("Notlar", ""),
                r.get("Rapor", ""),
            ])
        return headers, data

    @staticmethod
    def _find_header_index(headers: List[str], *candidates: str) -> int:
        for name in candidates:
            if name in headers:
                return headers.index(name)
        return -1

    def run(self):
        try:
            rke_data, rke_combo, rke_dict = [], [], {}
            muayene_listesi, headers = [], []
            teknik_aciklamalar = []
            kontrol_edenler, birim_sorumlulari = set(), set()

            from database.sqlite_manager import SQLiteManager
            from core.di import get_rke_service
            db = SQLiteManager(db_path=self._db_path, check_same_thread=True)
            rke_svc = get_rke_service(db)
            rke_repo = rke_svc.get_rke_repo()
            muayene_repo = rke_svc.get_muayene_repo()

            rke_data = rke_repo.get_all()

            for row in rke_data:
                ekipman_no = str(row.get('EkipmanNo', '')).strip()
                cins       = str(row.get('KoruyucuCinsi', '')).strip()
                if ekipman_no:
                    display = f"{ekipman_no} | {cins}"
                    rke_combo.append(display)
                    rke_dict[display] = ekipman_no

            headers, muayene_listesi = self._repo_muayene_to_table(muayene_repo.get_all())

            if headers and muayene_listesi:
                idx_k = self._find_header_index(headers, "KontrolEden/Unvani", "KontrolEden")
                idx_s = self._find_header_index(headers, "BirimSorumlusu/Unvani", "BirimSorumlusu")
                for row in muayene_listesi:
                    if idx_k != -1 and len(row) > idx_k:
                        val = str(row[idx_k]).strip()
                        if val: kontrol_edenler.add(val)
                    if idx_s != -1 and len(row) > idx_s:
                        val = str(row[idx_s]).strip()
                        if val: birim_sorumlulari.add(val)

            try:
                sabitler_rke = rke_svc._r.get("Sabitler").get_by_kod("RKE_Teknik")
                for s in sabitler_rke:
                    eleman = str(s.get("MenuEleman", "")).strip()
                    if eleman:
                        teknik_aciklamalar.append(eleman)
            except Exception:
                pass

            if not teknik_aciklamalar:
                teknik_aciklamalar = ["Yirtik Yok", "Kursun Butunlugu Tam", "Askilar Saglam", "Temiz"]

            self.veri_hazir.emit(
                rke_data, sorted(rke_combo), rke_dict,
                muayene_listesi, headers, sorted(teknik_aciklamalar),
                sorted(kontrol_edenler), sorted(birim_sorumlulari)
            )
            if db:
                db.close()
        except Exception as e:
            self.hata_olustu.emit(str(e))


class KayitWorker(QThread):
    finished = Signal(str)
    error    = Signal(str)

    def __init__(self, veri_dict, dosya_yolu, db_path=None):
        super().__init__()
        self.veri       = veri_dict
        self.dosya_yolu = dosya_yolu
        self._db_path   = db_path or DB_PATH

    def run(self):
        try:
            drive_link = "-"
            upload_result = {"mode": "none", "drive_link": "", "local_path": "", "error": ""}

            # Local DB (Dokumanlar için) her zaman açılır
            from database.sqlite_manager import SQLiteManager
            from core.di import get_rke_service, get_dokuman_service
            db = SQLiteManager(db_path=self._db_path, check_same_thread=True)
            rke_svc = get_rke_service(db)

            if self.dosya_yolu and os.path.exists(self.dosya_yolu):
                storage = StorageService(db)
                upload_result = storage.upload(
                    file_path=self.dosya_yolu,
                    folder_name="RKE_Rapor",
                    custom_name=os.path.basename(self.dosya_yolu)
                )
                drive_link = upload_result.get("drive_link") or upload_result.get("local_path") or "-"

                # Dokumanlar tablosuna kaydet
                if upload_result.get("mode") != "none":
                    try:
                        repo_doc = rke_svc.get_dokuman_repo()
                        repo_doc.insert({  # type: ignore
                            "EntityType": "rke",
                            "EntityId": str(self.veri.get("EkipmanNo", "")),
                            "BelgeTuru": "Rapor",
                            "Belge": os.path.basename(self.dosya_yolu),
                            "DocType": "RKE_Rapor",
                            "DisplayName": os.path.basename(self.dosya_yolu),
                            "LocalPath": upload_result.get("local_path") or "",
                            "DrivePath": upload_result.get("drive_link") or "",
                            "BelgeAciklama": "",
                            "YuklenmeTarihi": datetime.datetime.now().isoformat(),
                            "IliskiliBelgeID": self.veri.get("KayitNo"),
                            "IliskiliBelgeTipi": "RKE_Muayene",
                        })
                    except Exception as e:
                        logger.warning(f"Dokumanlar kaydi eklenemedi: {e}")

            rke_repo    = rke_svc.get_rke_repo()
            muayene_repo = rke_svc.get_muayene_repo()

            muayene_data = {
                "KayitNo":              self.veri.get("KayitNo"),
                "EkipmanNo":            self.veri.get("EkipmanNo"),
                "FMuayeneTarihi":       self.veri.get("FMuayeneTarihi"),
                "FizikselDurum":        self.veri.get("FizikselDurum"),
                "SMuayeneTarihi":       self.veri.get("SMuayeneTarihi"),
                "SkopiDurum":           self.veri.get("SkopiDurum"),
                "Aciklamalar":          self.veri.get("Aciklamalar"),
                "KontrolEdenUnvani":    self.veri.get("KontrolEden"),
                "BirimSorumlusuUnvani": self.veri.get("BirimSorumlusu"),
                "Notlar":               self.veri.get("Not"),
                "Rapor":                drive_link,
            }
            muayene_repo.insert(muayene_data)

            yeni_durum = envanter_durumunu_belirle(
                self.veri['FizikselDurum'], self.veri['SkopiDurum'])
            gelecek = ""
            skopi_str = self.veri.get('SMuayeneTarihi', '')
            if skopi_str:
                try:
                    dt_obj = datetime.datetime.strptime(skopi_str, "%Y-%m-%d")
                    gelecek = (dt_obj + relativedelta(years=1)).strftime("%Y-%m-%d")
                except Exception:
                    gelecek = skopi_str
            update_data = {"Durum": yeni_durum, "Aciklama": self.veri.get("Aciklamalar", "")}
            if gelecek:
                update_data["KontrolTarihi"] = gelecek
            rke_repo.update(self.veri["EkipmanNo"], update_data)

            self.finished.emit("Kayit ve guncelleme basarili.")
            if db:
                db.close()
        except Exception as e:
            self.error.emit(str(e))

class TopluKayitWorker(QThread):
    progress = Signal(int, int)
    finished = Signal()
    error    = Signal(str)

    def __init__(self, ekipman_listesi, ortak_veri, dosya_yolu, fiziksel_aktif, skopi_aktif, db_path=None):
        super().__init__()
        self.ekipman_listesi = ekipman_listesi
        self.ortak_veri      = ortak_veri
        self.dosya_yolu      = dosya_yolu
        self.fiziksel_aktif  = fiziksel_aktif
        self.skopi_aktif     = skopi_aktif
        self._db_path        = db_path or DB_PATH

    def run(self):
        try:
            drive_link = "-"
            upload_result = {"mode": "none", "drive_link": "", "local_path": "", "error": ""}

            from database.sqlite_manager import SQLiteManager
            from core.di import get_rke_service
            db = SQLiteManager(db_path=self._db_path, check_same_thread=True)
            rke_svc = get_rke_service(db)

            if self.dosya_yolu and os.path.exists(self.dosya_yolu):
                storage = StorageService(db)
                upload_result = storage.upload(
                    file_path=self.dosya_yolu,
                    folder_name="RKE_Rapor",
                    custom_name=os.path.basename(self.dosya_yolu)
                )
                drive_link = upload_result.get("drive_link") or upload_result.get("local_path") or "-"

            rke_repo     = rke_svc.get_rke_repo()
            muayene_repo = rke_svc.get_muayene_repo()

            for idx, ekipman_no in enumerate(self.ekipman_listesi):
                unique_id = uuid.uuid4().hex[:12].upper()
                f_tarih = self.ortak_veri["FMuayeneTarihi"] if self.fiziksel_aktif else ""
                f_durum = self.ortak_veri["FizikselDurum"]  if self.fiziksel_aktif else ""
                s_tarih = self.ortak_veri["SMuayeneTarihi"] if self.skopi_aktif    else ""
                s_durum = self.ortak_veri["SkopiDurum"]     if self.skopi_aktif    else ""

                muayene_data = {
                    "KayitNo":              unique_id,
                    "EkipmanNo":            ekipman_no,
                    "FMuayeneTarihi":       f_tarih,
                    "FizikselDurum":        f_durum,
                    "SMuayeneTarihi":       s_tarih,
                    "SkopiDurum":           s_durum,
                    "Aciklamalar":          self.ortak_veri["Aciklamalar"],
                    "KontrolEdenUnvani":    self.ortak_veri["KontrolEden"],
                    "BirimSorumlusuUnvani": self.ortak_veri["BirimSorumlusu"],
                    "Notlar":               self.ortak_veri["Not"],
                    "Rapor":                drive_link,
                }
                muayene_repo.insert(muayene_data)

                yeni_genel = envanter_durumunu_belirle(f_durum, s_durum)
                gelecek = ""
                if s_tarih:
                    try:
                        dt_obj = datetime.datetime.strptime(s_tarih, "%Y-%m-%d")
                        gelecek = (dt_obj + relativedelta(years=1)).strftime("%Y-%m-%d")
                    except Exception:
                        gelecek = s_tarih
                update_data = {"Durum": yeni_genel, "Aciklama": self.ortak_veri.get("Aciklamalar", "")}
                if gelecek:
                    update_data["KontrolTarihi"] = gelecek
                rke_repo.update(ekipman_no, update_data)

                if upload_result.get("mode") != "none":
                    try:
                        repo_doc = rke_svc.get_dokuman_repo()
                        repo_doc.insert({  # type: ignore
                            "EntityType":         "rke",
                            "EntityId":           str(ekipman_no),
                            "BelgeTuru":          "Rapor",
                            "Belge":              os.path.basename(self.dosya_yolu),
                            "DocType":            "RKE_Rapor",
                            "DisplayName":        os.path.basename(self.dosya_yolu),
                            "LocalPath":          upload_result.get("local_path") or "",
                            "DrivePath":          upload_result.get("drive_link") or "",
                            "BelgeAciklama":      "",
                            "YuklenmeTarihi":     datetime.datetime.now().isoformat(),
                            "IliskiliBelgeID":    unique_id,
                            "IliskiliBelgeTipi":  "RKE_Muayene",
                        })
                    except Exception as e:
                        logger.warning(f"Dokumanlar kaydi eklenemedi: {e}")

                self.progress.emit(idx + 1, len(self.ekipman_listesi))

            self.finished.emit()
            if db:
                db.close()
        except Exception as e:
            self.error.emit(str(e))

class RKEEnvanterModel(BaseTableModel):
    def __init__(self, rows=None, parent=None):
        super().__init__(_RKE_COLS, rows, parent)

    def _display(self, key, row):
        return str(row.get(key, ""))

    def _fg(self, key, row):
        if key == "Durum":
            v = row.get(key, "")
            if "Degil" in v or "Hurda" in v:
                return QColor(_C["red"])
            if "Uygun" in v:
                return QColor(_C["green"])
        return None

    def _bg(self, key, row):
        """
        Satır arka planı KontrolTarihi'ne göre:
          • Geçmiş  (süresi dolmuş) → kırmızı tonu
          • ≤ 30 gün kalan         → sarı/turuncu tonu
          • > 30 gün kalan         → normal
        """
        kt = str(row.get("KontrolTarihi", "")).strip()
        if not kt or len(kt) < 10:
            return None
        try:
            dt_obj = datetime.datetime.strptime(kt[:10], "%Y-%m-%d").date()
            today  = datetime.date.today()
            delta  = (dt_obj - today).days
            if delta < 0:
                return QColor(_C.get("red", "#e85555") + "28")   # kırmızı, %16 opaklık
            if delta <= 30:
                return QColor(_C.get("amber", "#e8a030") + "28") # turuncu, %16 opaklık
        except Exception:
            pass
        return None

    def _align(self, key):
        if key in ("KontrolTarihi", "Durum"):
            return Qt.AlignmentFlag.AlignCenter
        return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft

    def set_rows(self, rows):
        self.set_data(rows)

    def get_row(self, idx):
        return self._data[idx] if 0 <= idx < len(self._data) else None


_GECMIS_COLS = [
    ("FMuayeneTarihi", "Fiz. Tarih"),
    ("SMuayeneTarihi", "Skopi Tarih"),
    ("Aciklamalar",     "Aciklama"),
    ("Rapor",           "Rapor"),
]

class GecmisModel(BaseTableModel):
    def __init__(self, parent=None):
        super().__init__(_GECMIS_COLS, [], parent)

    def _display(self, key, row):
        val = str(row.get(key, ""))
        if key == "Rapor":
            return "Link" if "http" in val else "-"
        return val

    def _fg(self, key, row):
        if key == "Rapor" and "http" in str(row.get(key, "")):
            return QColor(_C["accent"])
        return None

    def set_rows(self, rows):
        self.set_data(rows)

    def get_row(self, idx):
        return self._data[idx] if 0 <= idx < len(self._data) else None


# ----------------------------------------------------------------
# TOPLU MUAYENE DIALOG
# ----------------------------------------------------------------

class RKEMuayenePage(QWidget):
    def __init__(self, db=None, action_guard=None, parent=None, yetki="viewer", kullanici_adi=None):
        super().__init__(parent)
        self._db = db
        self._action_guard = action_guard
        self._db_path = DB_PATH
        self.yetki         = yetki
        self.kullanici_adi = kullanici_adi
        self.setWindowTitle("RKE Muayene Girisi")
        self.resize(1200, 820)
        # setStyleSheet kaldırıldı (_S_PAGE) — global QSS

        self.rke_data: List[Dict]   = []
        self.rke_dict: Dict         = {}
        self.tum_muayeneler         = []
        self.teknik_aciklamalar     = []
        self.kontrol_listesi        = []
        self.sorumlu_listesi        = []
        self.secilen_dosya          = None
        self.header_map: Dict       = {}
        self._kpi_labels: Dict[str, QLabel] = {}
        self.btn_kapat = None  # Kapiyi kapat dugmesi icin yer tutucu


        self._setup_ui()
        # YetkiYoneticisi.uygula(self, "rke_muayene")  # TODO: Yetki sistemi entegrasyonu

    # ==================================================================
    #  UI KURULUM
    # ==================================================================

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_kpi_bar())
        root.addWidget(self._build_body(), 1)

    def _build_kpi_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(68)
        bar.setProperty("bg-role", "page")
        hl = QHBoxLayout(bar)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(1)
        
        specs = [
            ("toplam",  "TOPLAM EKIPMAN",  "0", DarkTheme.ACCENT),
            ("uygun",   "KULLANIMA UYGUN", "0", DarkTheme.STATUS_SUCCESS),
            ("uygun_d", "UYGUN DEGIL",     "0", DarkTheme.STATUS_ERROR),
            ("bekleyen","KONTROL BEKLEYEN","0", DarkTheme.STATUS_WARNING),
        ]
        for key, title, val, color in specs:
            hl.addWidget(self._mk_kpi_card(key, title, val, color), 1)
        return bar
    
    def _mk_kpi_card(self, key, title, val, color) -> QWidget:
        w = QWidget()
        w.setProperty("bg-role", "page")
        hl = QHBoxLayout(w)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)

        accent = QFrame()
        accent.setFixedWidth(3)
        accent.setStyleSheet("border: none;")
        hl.addWidget(accent)

        content = QWidget()
        content.setProperty("bg-role", "page")
        vl = QVBoxLayout(content)
        vl.setContentsMargins(14, 8, 14, 8)
        vl.setSpacing(2)

        lt = QLabel(title)
        lt.setProperty("color-role", "muted")
        lv = QLabel(val)
        lv.setStyleSheet(f"color:{color};background:transparent;font-size:20px;font-weight:700;")
        vl.addWidget(lt)
        vl.addWidget(lv)
        hl.addWidget(content, 1)
        self._kpi_labels[key] = lv
        return w

    def _build_body(self) -> QWidget:
        body = QWidget()
        body.setProperty("bg-role", "page")
        hl = QHBoxLayout(body)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)

        self._form_panel = self._build_form_panel()
        self._form_panel.setFixedWidth(390)
        hl.addWidget(self._form_panel)

        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setProperty("bg-role", "separator")
        hl.addWidget(sep)

        hl.addWidget(self._build_list_panel(), 1)
        return body

    def _build_form_panel(self) -> QWidget:
        panel = QWidget()
        panel.setProperty("bg-role", "page")
        vl = QVBoxLayout(panel)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        # Panel baslik
        hdr = QWidget()
        hdr.setFixedHeight(36)
        hdr.setProperty("bg-role", "page")
        hh = QHBoxLayout(hdr)
        hh.setContentsMargins(14, 0, 14, 0)
        t1 = QLabel("MUAYENE FORMU")
        t1.setProperty("color-role", "muted")
        t1.setProperty("color-role", "muted")  # monospace font tema QSS ile belirlenir
        hh.addWidget(t1)
        hh.addStretch()
        vl.addWidget(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        # setStyleSheet kaldırıldı (_S_SCROLL) — global QSS

        inner = QWidget()
        inner.setStyleSheet("background:transparent;")
        il = QVBoxLayout(inner)
        il.setContentsMargins(12, 12, 12, 16)
        il.setSpacing(10)

        # 1. Ekipman Secimi
        grp_ekipman = FieldGroup("Ekipman Secimi", DarkTheme.STATUS_WARNING)
        g = QGridLayout()
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(6)
        g.addWidget(self._lbl("EKIPMAN NO"), 0, 0, 1, 2)
        self.cmb_rke = QComboBox()
        self.cmb_rke.setEditable(True)
        # setStyleSheet kaldırıldı (_S_COMBO) — global QSS
        self.cmb_rke.setFixedHeight(28)
        self.cmb_rke.setPlaceholderText("Ara veya secin...")
        self.cmb_rke.currentIndexChanged.connect(self.ekipman_secildi)
        g.addWidget(self.cmb_rke, 1, 0, 1, 2)
        grp_ekipman.add_layout(g)
        il.addWidget(grp_ekipman)

        # 2. Fiziksel Muayene
        grp_fiz = FieldGroup("Fiziksel Muayene", DarkTheme.STATUS_SUCCESS)
        gf = QGridLayout()
        gf.setContentsMargins(0, 0, 0, 0)
        gf.setHorizontalSpacing(10)
        gf.setVerticalSpacing(6)
        gf.addWidget(self._lbl("MUAYENE TARIHI"), 0, 0)
        gf.addWidget(self._lbl("DURUM"), 0, 1)
        self.dt_fiziksel = QDateEdit(QDate.currentDate())
        self.dt_fiziksel.setCalendarPopup(True)
        # setStyleSheet kaldırıldı (_S_DATE) — global QSS
        self.dt_fiziksel.setFixedHeight(28)
        self.cmb_fiziksel = QComboBox()
        # setStyleSheet kaldırıldı (_S_COMBO) — global QSS
        self.cmb_fiziksel.setFixedHeight(28)
        self.cmb_fiziksel.addItems(["Kullanima Uygun", "Kullanima Uygun Degil"])
        gf.addWidget(self.dt_fiziksel, 1, 0)
        gf.addWidget(self.cmb_fiziksel, 1, 1)
        grp_fiz.add_layout(gf)
        il.addWidget(grp_fiz)

        # 3. Skopi Muayene
        grp_sko = FieldGroup("Skopi Muayene", DarkTheme.ACCENT2)
        gs = QGridLayout()
        gs.setContentsMargins(0, 0, 0, 0)
        gs.setHorizontalSpacing(10)
        gs.setVerticalSpacing(6)
        gs.addWidget(self._lbl("MUAYENE TARIHI"), 0, 0)
        gs.addWidget(self._lbl("DURUM"), 0, 1)
        self.dt_skopi = QDateEdit(QDate.currentDate())
        self.dt_skopi.setCalendarPopup(True)
        # setStyleSheet kaldırıldı (_S_DATE) — global QSS
        self.dt_skopi.setFixedHeight(28)
        self.cmb_skopi = QComboBox()
        # setStyleSheet kaldırıldı (_S_COMBO) — global QSS
        self.cmb_skopi.setFixedHeight(28)
        self.cmb_skopi.addItems(["Kullanima Uygun", "Kullanima Uygun Degil", "Yapilmadi"])
        gs.addWidget(self.dt_skopi, 1, 0)
        gs.addWidget(self.cmb_skopi, 1, 1)
        grp_sko.add_layout(gs)
        il.addWidget(grp_sko)

        # 4. Sonuc ve Raporlama
        grp_sonuc = FieldGroup("Sonuc ve Raporlama", DarkTheme.ACCENT)
        go = QGridLayout()
        go.setContentsMargins(0, 0, 0, 0)
        go.setHorizontalSpacing(10)
        go.setVerticalSpacing(6)
        go.addWidget(self._lbl("KONTROL EDEN"), 0, 0)
        go.addWidget(self._lbl("BIRIM SORUMLUSU"), 0, 1)
        self.cmb_kontrol = QComboBox()
        self.cmb_kontrol.setEditable(True)
        # setStyleSheet kaldırıldı (_S_COMBO) — global QSS
        self.cmb_kontrol.setFixedHeight(28)
        if self.kullanici_adi:
            self.cmb_kontrol.setCurrentText(str(self.kullanici_adi))
        self.cmb_sorumlu = QComboBox()
        self.cmb_sorumlu.setEditable(True)
        # setStyleSheet kaldırıldı (_S_COMBO) — global QSS
        self.cmb_sorumlu.setFixedHeight(28)
        go.addWidget(self.cmb_kontrol, 1, 0)
        go.addWidget(self.cmb_sorumlu, 1, 1)
        go.addWidget(self._lbl("TEKNIK ACIKLAMA (Çoklu Seçim)"), 2, 0, 1, 2)
        self.cmb_aciklama = CheckableComboBox()
        # setStyleSheet kaldırıldı (_S_COMBO) — global QSS
        self.cmb_aciklama.setFixedHeight(28)
        go.addWidget(self.cmb_aciklama, 3, 0, 1, 2)

        # Dosya satiri
        file_row = QHBoxLayout()
        self.lbl_dosya = QLabel("Rapor secilmedi")
        self.lbl_dosya.setProperty("color-role", "muted")
        self.lbl_dosya.setStyleSheet("font-size: 10px;")
        btn_dosya = QPushButton("Rapor Yukle")
        btn_dosya.setProperty("style-role", "upload")
        btn_dosya.setFixedHeight(28)
        btn_dosya.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(btn_dosya, "upload", color=DarkTheme.TEXT_SECONDARY, size=14)
        btn_dosya.clicked.connect(self.dosya_sec)
        file_row.addWidget(self.lbl_dosya, 1)
        file_row.addWidget(btn_dosya)
        go.addLayout(file_row, 4, 0, 1, 2)
        grp_sonuc.add_layout(go)
        il.addWidget(grp_sonuc)

        # 5. Gecmis
        grp_gecmis = FieldGroup("Secili Ekipmanin Gecmisi", DarkTheme.RKE_PURP)
        self._gecmis_model = GecmisModel()
        self.tbl_gecmis = QTableView()
        self.tbl_gecmis.setModel(self._gecmis_model)
        # setStyleSheet kaldırıldı (_S_TABLE) — global QSS
        self.tbl_gecmis.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_gecmis.setEditTriggers(QAbstractItemView.EditTriggers.NoEditTriggers)  # type: ignore
        self.tbl_gecmis.verticalHeader().setVisible(False)
        self.tbl_gecmis.setShowGrid(False)
        self.tbl_gecmis.setAlternatingRowColors(True)
        self.tbl_gecmis.setFixedHeight(140)
        self.tbl_gecmis.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_gecmis.doubleClicked.connect(self._gecmis_satir_tiklandi)
        grp_gecmis.add_widget(self.tbl_gecmis)
        il.addWidget(grp_gecmis)

        il.addStretch()
        scroll.setWidget(inner)
        vl.addWidget(scroll, 1)

        # Progress
        self.pbar = QProgressBar()
        self.pbar.setVisible(False)
        self.pbar.setFixedHeight(3)
        # setStyleSheet kaldırıldı (_S_PBAR) — global QSS
        vl.addWidget(self.pbar)

        # Butonlar
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(12, 8, 12, 12)
        btn_row.setSpacing(8)
        self.btn_temizle = QPushButton("TEMIZLE")
        self.btn_temizle.setFixedHeight(34)
        self.btn_temizle.setProperty("style-role", "secondary")
        self.btn_temizle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_temizle, "x", color=DarkTheme.TEXT_MUTED, size=14)
        self.btn_temizle.clicked.connect(self.temizle)
        self.btn_kaydet = QPushButton("KAYDET")
        self.btn_kaydet.setFixedHeight(34)
        self.btn_kaydet.setProperty("style-role", "success-filled")
        self.btn_kaydet.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_kaydet, "save", color="#051a10", size=14)
        self.btn_kaydet.clicked.connect(self.kaydet)
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self.btn_kaydet, "cihaz.write")
        btn_row.addWidget(self.btn_temizle)
        btn_row.addWidget(self.btn_kaydet)
        vl.addLayout(btn_row)
        return panel

    def _build_list_panel(self) -> QWidget:
        panel = QWidget()
        panel.setProperty("bg-role", "page")
        vl = QVBoxLayout(panel)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        # Filtre cubugu — iki satır
        fbar = QWidget()
        fbar.setProperty("bg-role", "page")
        fbar_vl = QVBoxLayout(fbar)
        fbar_vl.setContentsMargins(12, 8, 12, 8)
        fbar_vl.setSpacing(6)

        # ── Üst satır: ABD + Durum + Arama ──────────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        self.cmb_filtre_abd = QComboBox()
        self.cmb_filtre_abd.setFixedHeight(28)
        self.cmb_filtre_abd.setMinimumWidth(160)
        self.cmb_filtre_abd.addItem("Tüm ABD")
        self.cmb_filtre_abd.currentIndexChanged.connect(self.tabloyu_filtrele)

        self.cmb_filtre_durum = QComboBox()
        self.cmb_filtre_durum.setFixedHeight(28)
        self.cmb_filtre_durum.setMinimumWidth(170)
        for label in ["Tüm Durumlar", "Kullanıma Uygun", "Kullanıma Uygun Değil", "Hurda"]:
            self.cmb_filtre_durum.addItem(label)
        self.cmb_filtre_durum.currentIndexChanged.connect(self.tabloyu_filtrele)

        self.txt_ara = QLineEdit()
        self.txt_ara.setFixedHeight(28)
        self.txt_ara.setPlaceholderText("Ekipman no, birim, cins ara...")
        self.txt_ara.textChanged.connect(self.tabloyu_filtrele)

        row1.addWidget(self.cmb_filtre_abd)
        row1.addWidget(self.cmb_filtre_durum)
        row1.addWidget(self.txt_ara, 1)

        # ── Alt satır: Tarih filtresi + butonlar ─────────────────
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        # Tarih filtresi: gecikmiş / 30 gün / hepsi
        lbl_tarih = QLabel("Kontrol tarihi:")
        lbl_tarih.setProperty("color-role", "muted")
        lbl_tarih.setStyleSheet("font-size:11px;")

        self.cmb_filtre_tarih = QComboBox()
        self.cmb_filtre_tarih.setFixedHeight(28)
        self.cmb_filtre_tarih.setMinimumWidth(180)
        self.cmb_filtre_tarih.addItems([
            "Tüm Tarihler",
            "Tarihi Geçmiş",
            "30 Gün İçinde",
            "60 Gün İçinde",
        ])
        self.cmb_filtre_tarih.currentIndexChanged.connect(self.tabloyu_filtrele)

        # Renk açıklaması
        def _badge(renk: str, metin: str) -> QLabel:
            lbl = QLabel(f"● {metin}")
            lbl.setStyleSheet(f"color:{renk}; font-size:11px;")
            return lbl

        row2.addWidget(lbl_tarih)
        row2.addWidget(self.cmb_filtre_tarih)
        row2.addSpacing(8)
        row2.addWidget(_badge(_C.get("red",   "#e85555"), "Geçmiş"))
        row2.addWidget(_badge(_C.get("amber", "#e8a030"), "≤30 gün"))
        row2.addWidget(_badge(_C.get("green", "#2ec98e"), "Uygun"))
        row2.addStretch()

        btn_yenile = QPushButton("")
        btn_yenile.setFixedSize(28, 28)
        btn_yenile.setProperty("style-role", "refresh")
        btn_yenile.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(btn_yenile, "refresh", color=DarkTheme.TEXT_SECONDARY, size=14)
        btn_yenile.clicked.connect(self.verileri_yukle)

        btn_toplu = QPushButton("Toplu Muayene")
        btn_toplu.setFixedHeight(28)
        btn_toplu.setProperty("style-role", "action")
        btn_toplu.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(btn_toplu, "clipboard_list", color="#0a1420", size=14)
        btn_toplu.clicked.connect(self.ac_toplu_dialog)

        row2.addWidget(btn_yenile)
        row2.addWidget(btn_toplu)

        fbar_vl.addLayout(row1)
        fbar_vl.addLayout(row2)

        # Tablo
        self._model = RKEEnvanterModel()
        self.tablo = QTableView()
        self.tablo.setModel(self._model)
        # setStyleSheet kaldırıldı (_S_TABLE) — global QSS
        self.tablo.setAlternatingRowColors(True)
        self.tablo.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tablo.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)  # type: ignore
        self.tablo.setEditTriggers(QAbstractItemView.EditTriggers.NoEditTriggers)  # type: ignore
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.setShowGrid(False)
        hdr = self.tablo.horizontalHeader()
        for i, w in enumerate(_RKE_WIDTHS):
            if i == len(_RKE_COLS) - 1:
                hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            else:
                hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                hdr.resizeSection(i, w)
        self.tablo.clicked.connect(self._sag_tablo_tiklandi)
        vl.addWidget(self.tablo, 1)

        # Footer
        footer = QWidget()
        footer.setFixedHeight(44)
        footer.setProperty("bg-role", "panel")
        footer.setProperty("border-role", "top")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(12, 8, 12, 8)
        fl.setSpacing(8)
        
        self.lbl_sayi = QLabel("0 kayit")
        self.lbl_sayi.setProperty("color-role", "muted")
        fl.addStretch()
        fl.addWidget(self.lbl_sayi)
        vl.addWidget(footer)
        return panel

    # ==================================================================
    #  YARDIMCI UI
    # ==================================================================

    @staticmethod
    def _lbl(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setProperty("color-role", "muted")
        return lbl

    # ==================================================================
    #  KPI
    # ==================================================================

    def _update_kpi(self, rows: List[Dict]):
        toplam, uygun, uygun_d, bekleyen = len(rows), 0, 0, 0
        today = datetime.date.today()
        for r in rows:
            d = str(r.get("Durum", ""))
            if "Degil" in d: uygun_d += 1
            elif "Uygun" in d: uygun  += 1
            kt = str(r.get("KontrolTarihi", ""))
            if kt and len(kt) >= 10:
                try:
                    dt_obj = datetime.datetime.strptime(kt[:10], "%Y-%m-%d").date()
                    if dt_obj <= today: bekleyen += 1
                except: pass
        for k, v in [("toplam", toplam), ("uygun", uygun),
                     ("uygun_d", uygun_d), ("bekleyen", bekleyen)]:
            if k in self._kpi_labels:
                self._kpi_labels[k].setText(str(v))

    # ==================================================================
    #  MANTIK
    # ==================================================================

    def dosya_sec(self):
        yol, _ = QFileDialog.getOpenFileName(self, "Rapor", "", "PDF/Resim (*.pdf *.jpg)")
        if yol:
            self.secilen_dosya = yol
            self.lbl_dosya.setText(os.path.basename(yol))

    def verileri_yukle(self):
        self.pbar.setVisible(True)
        self.pbar.setRange(0, 0)
        self.loader = VeriYukleyici(self._db_path)
        self.loader.veri_hazir.connect(self.veriler_geldi)
        self.loader.hata_olustu.connect(lambda e: hata_goster(self, e))
        self.loader.finished.connect(lambda: self.pbar.setVisible(False))
        self.loader.start()

    def veriler_geldi(self, rke_data, rke_combo, rke_dict, muayene_list,
                      headers, teknik_aciklamalar, kontrol_edenler, birim_sorumlulari):
        self.rke_data           = rke_data
        self.rke_dict           = rke_dict
        self.tum_muayeneler     = muayene_list
        self.header_map         = {h.strip(): i for i, h in enumerate(headers)}
        self.teknik_aciklamalar = teknik_aciklamalar
        self.kontrol_listesi    = kontrol_edenler
        self.sorumlu_listesi    = birim_sorumlulari

        self.cmb_rke.blockSignals(True)
        self.cmb_rke.clear()
        self.cmb_rke.addItems(rke_combo)
        self.cmb_rke.blockSignals(False)

        self.cmb_aciklama.clear()
        self.cmb_aciklama.addItems(teknik_aciklamalar)

        self.cmb_kontrol.clear()
        self.cmb_kontrol.addItems(kontrol_edenler)
        if self.kullanici_adi: self.cmb_kontrol.setCurrentText(str(self.kullanici_adi))

        self.cmb_sorumlu.clear()
        self.cmb_sorumlu.addItems(birim_sorumlulari)

        abd = sorted({str(r.get("AnaBilimDali", "")).strip() for r in rke_data
                      if str(r.get("AnaBilimDali", "")).strip()})
        self.cmb_filtre_abd.blockSignals(True)
        self.cmb_filtre_abd.clear()
        self.cmb_filtre_abd.addItem("Tüm ABD")
        self.cmb_filtre_abd.addItems(abd)
        self.cmb_filtre_abd.blockSignals(False)

        self.tabloyu_filtrele()

    def tabloyu_filtrele(self):
        secilen_abd   = self.cmb_filtre_abd.currentText()
        secilen_durum = self.cmb_filtre_durum.currentText()
        secilen_tarih = self.cmb_filtre_tarih.currentText()
        ara           = self.txt_ara.text().lower()
        today         = datetime.date.today()
        filtered      = []

        for row in self.rke_data:
            # ABD filtresi
            abd = str(row.get("AnaBilimDali", "")).strip()
            if secilen_abd not in ("Tüm ABD", "Tum ABD") and abd != secilen_abd:
                continue

            # Durum filtresi
            durum = str(row.get("Durum", ""))
            if secilen_durum == "Kullanıma Uygun" and "Uygun" not in durum:
                continue
            if secilen_durum == "Kullanıma Uygun Değil" and "Degil" not in durum:
                continue
            if secilen_durum == "Hurda" and "Hurda" not in durum:
                continue

            # Kontrol tarihi filtresi
            if secilen_tarih != "Tüm Tarihler":
                kt = str(row.get("KontrolTarihi", "")).strip()
                if not kt or len(kt) < 10:
                    continue
                try:
                    dt_obj = datetime.datetime.strptime(kt[:10], "%Y-%m-%d").date()
                    delta  = (dt_obj - today).days
                    if secilen_tarih == "Tarihi Geçmiş"  and delta >= 0:
                        continue
                    if secilen_tarih == "30 Gün İçinde"  and not (0 <= delta <= 30):
                        continue
                    if secilen_tarih == "60 Gün İçinde"  and not (0 <= delta <= 60):
                        continue
                except Exception:
                    continue

            # Metin araması
            if ara and ara not in " ".join([str(v) for v in row.values()]).lower():
                continue

            filtered.append(row)

        self._model.set_rows(filtered)
        self.lbl_sayi.setText(f"{len(filtered)} / {len(self.rke_data)} kayıt")
        self._update_kpi(filtered)

    def _sag_tablo_tiklandi(self, index: QModelIndex):
        row_data = self._model.get_row(index.row())
        if not row_data: return
        ekipman_no = str(row_data.get("EkipmanNo", ""))
        idx = self.cmb_rke.findText(ekipman_no, Qt.MatchFlag.MatchContains)  # type: ignore
        if idx >= 0: self.cmb_rke.setCurrentIndex(idx)

    def ekipman_secildi(self):
        secilen_text = self.cmb_rke.currentText()
        if not secilen_text: return
        ekipman_no = self.rke_dict.get(secilen_text, secilen_text.split('|')[0].strip())
        rows = []
        idx_ekipman = self.header_map.get("EkipmanNo", -1)
        if idx_ekipman == -1: return
        for row in self.tum_muayeneler:
            if len(row) > idx_ekipman and row[idx_ekipman] == ekipman_no:
                def get_v(key):
                    i = self.header_map.get(key, -1)
                    return row[i] if i != -1 and len(row) > i else ""
                rows.append({
                    "FMuayeneTarihi": get_v("FMuayeneTarihi"),
                    "SMuayeneTarihi": get_v("SMuayeneTarihi"),
                    "Aciklamalar":     get_v("Aciklamalar"),
                    "Rapor":           get_v("Rapor"),
                })
        self._gecmis_model.set_rows(rows)

    def _gecmis_satir_tiklandi(self, index: QModelIndex):
        if index.column() == 3:
            row_data = self._gecmis_model.get_row(index.row())
            if row_data:
                link = str(row_data.get("Rapor", ""))
                if "http" in link:
                    QDesktopServices.openUrl(QUrl(link))

    def temizle(self):
        self.cmb_rke.setCurrentIndex(-1)
        self.dt_fiziksel.setDate(QDate.currentDate())
        self.dt_skopi.setDate(QDate.currentDate())
        self.cmb_kontrol.setCurrentText(str(self.kullanici_adi) if self.kullanici_adi else "")
        self.cmb_sorumlu.setCurrentText("")
        self.cmb_fiziksel.setCurrentIndex(0)
        self.cmb_skopi.setCurrentIndex(0)
        self.cmb_aciklama.setCheckedItems([])
        self.lbl_dosya.setText("Rapor secilmedi")
        self.secilen_dosya = None
        self._gecmis_model.set_rows([])

    def kaydet(self):
        if self._action_guard and not self._action_guard.check_and_warn(
            self, "cihaz.write", "RKE Muayene Kaydetme"
        ):
            return
        rke_text = self.cmb_rke.currentText()
        if not rke_text:
            uyari_goster(self, "Ekipman seçin."); return
        ekipman_no = self.rke_dict.get(rke_text, rke_text.split('|')[0].strip())
        unique_id = uuid.uuid4().hex[:12].upper()
        veri = {
            'KayitNo':          unique_id,
            'EkipmanNo':        ekipman_no,
            'FMuayeneTarihi':  self.dt_fiziksel.date().toString("yyyy-MM-dd"),
            'FizikselDurum':    self.cmb_fiziksel.currentText(),
            'SMuayeneTarihi':  self.dt_skopi.date().toString("yyyy-MM-dd"),
            'SkopiDurum':       self.cmb_skopi.currentText(),
            'Aciklamalar':      self.cmb_aciklama.getCheckedItems(),
            'KontrolEden':      self.cmb_kontrol.currentText(),
            'BirimSorumlusu':   self.cmb_sorumlu.currentText(),
            'Not':              "",
        }
        self.pbar.setVisible(True)
        self.pbar.setRange(0, 0)
        self.btn_kaydet.setEnabled(False)
        self.saver = KayitWorker(veri, self.secilen_dosya, db_path=self._db_path)
        self.saver.finished.connect(self.islem_basarili)
        self.saver.error.connect(lambda e: hata_goster(self, e))
        self.saver.start()

    def islem_basarili(self, msg: str):
        self.pbar.setVisible(False)
        self.btn_kaydet.setEnabled(True)
        bilgi_goster(self, msg)
        self.temizle()
        self.verileri_yukle()

    def ac_toplu_dialog(self):
        secili = self.tablo.selectionModel().selectedRows()
        if not secili:
            uyari_goster(self, "Tabloda satır seçin."); return
        ekipmanlar = sorted({
            str(self._model.get_row(i.row()).get("EkipmanNo", ""))  # type: ignore
            for i in secili
            if self._model.get_row(i.row())
        })
        dlg = TopluMuayeneDialog(
            ekipmanlar,
            self.teknik_aciklamalar,
            self.kontrol_listesi,
            self.sorumlu_listesi,
            self.kullanici_adi,
            self,
            db_path=self._db_path,
            checkable_combo_cls=CheckableComboBox,
            worker_cls=TopluKayitWorker,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            bilgi_goster(self, "Toplu kayıt başarılı.")
            self.verileri_yukle()

    def load_data(self):
        """main_window.py'den cagrilan yukleme metodu."""
        self.verileri_yukle()

    def closeEvent(self, event):
        for attr in ("loader", "saver"):
            t = getattr(self, attr, None)
            if t and t.isRunning(): t.quit(); t.wait(500)
        event.accept()







# -*- coding: utf-8 -*-
"""
RKE Raporlama Sayfası
──────────────────────
• Filtre paneli: ABD / Birim / Tarih + rapor türü (Genel / Hurda / Personel Bazlı)
• QAbstractTableModel tablosu
• PDF oluşturma ve Google Drive'a yükleme
• itf_desktop mimarisine uygun (get_registry(db), core.logger, GoogleDriveService)
"""
import os
import datetime

from PySide6.QtCore import (
    Qt, QThread, Signal,
    QAbstractTableModel, QModelIndex, QSortFilterProxyModel
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QComboBox, QLineEdit,
    QGroupBox, QMessageBox, QTableView, QHeaderView,
    QAbstractItemView, QRadioButton, QButtonGroup, QSizePolicy,
    QFileDialog
)
from PySide6.QtGui import (
    QColor, QCursor
)

from core.logger import logger
from core.hata_yonetici import exc_logla
from ui.theme_manager import ThemeManager
from ui.styles import DarkTheme
from ui.styles.icons import IconRenderer
from core.rapor_servisi import RaporServisi

# ─── Merkezi Stiller ───
S = ThemeManager.get_all_component_styles()

# ─── Tablo sütun tanımları ───
COLUMNS = [
    ("EkipmanNo",  "Ekipman No",   110),
    ("Cins",       "Cins",         120),
    ("Pb",         "Pb (mm)",       80),
    ("Birim",      "Birim",        130),
    ("Tarih",      "Tarih",         90),
    ("Sonuc",      "Sonuç",        140),
    ("Aciklama",   "Açıklama",     200),
    ("KontrolEden","Kontrol Eden", 140),
]

# Rapor Türleri
RAPOR_TIPLERI = {
    1: "Genel Kontrol Raporu",
    2: "Hurda (HEK) Raporu",
    3: "Ana Bilim Dalı Envanter Listesi",
    4: "Ana Bilim Dalı + Birim Envanter Listesi",
}

SONUC_RENK = {
    "Kullanıma Uygun":       QColor(DarkTheme.STATUS_SUCCESS),
    "Kullanıma Uygun Değil": QColor(DarkTheme.STATUS_ERROR),
}


# ═══════════════════════════════════════════════
#  TABLO MODELİ
# ═══════════════════════════════════════════════

class RaporTableModel(QAbstractTableModel):

    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self._data    = data or []
        self._keys    = [c[0] for c in COLUMNS]
        self._headers = [c[1] for c in COLUMNS]

    def rowCount(self, parent=QModelIndex()):    return len(self._data)
    def columnCount(self, parent=QModelIndex()): return len(COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        row = self._data[index.row()]
        col = self._keys[index.column()]
        if role == Qt.DisplayRole:
            return str(row.get(col, ""))
        if role == Qt.ForegroundRole and col == "Sonuc":
            return SONUC_RENK.get(str(row.get(col, "")), QColor(DarkTheme.TEXT_MUTED))
        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter if col in ("Tarih", "Pb", "Sonuc") else Qt.AlignVCenter | Qt.AlignLeft
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
    """RKE_List + RKE_Muayene birleştirerek rapor verisi hazırlar."""
    veri_hazir  = Signal(list, list, list, list, list)   # muayene, envanter, abd, birim, tarih
    hata_olustu = Signal(str)

    def run(self):
        from database.sqlite_manager import SQLiteManager
        from core.di import get_registry
        db = None
        try:
            db       = SQLiteManager()
            registry = get_registry(db)

            # 1. Envanter Listesi ve Map Hazırlığı
            envanter_listesi = []
            envanter_map = {}
            abd_set   = set()
            birim_set = set()

            for row in registry.get("RKE_List").get_all():
                eno = str(row.get("EkipmanNo", "")).strip()
                if not eno: continue

                abd   = str(row.get("AnaBilimDali",    "")).strip()
                birim = str(row.get("Birim",           "")).strip()
                cins  = str(row.get("KoruyucuCinsi",   "")).strip()
                pb    = str(row.get("KursunEsdegeri",  "")).strip()

                envanter_map[eno] = {
                    "ABD": abd, "Birim": birim, "Cins": cins, "Pb": pb
                }
                
                abd_set.add(abd)
                birim_set.add(birim)

                envanter_listesi.append({
                    "EkipmanNo":   eno,
                    "Cins":        cins,
                    "Pb":          pb,
                    "Birim":       birim,
                    "ABD":         abd,
                    "Tarih":       str(row.get("KontrolTarihi", "")).strip(),
                    "Sonuc":       str(row.get("Durum",         "")).strip(),
                    "Aciklama":    str(row.get("Aciklama",      "")).strip(),
                    "HizmetYili":  str(row.get("HizmetYili",    "")).strip(),
                    "KontrolEden": "", 
                })

            # 2. Muayene Listesi Hazırlığı
            muayene_listesi = []
            tarih_set = set()

            for row in registry.get("RKE_Muayene").get_all():
                eno    = str(row.get("EkipmanNo",      "")).strip()
                tarih  = str(row.get("FMuayeneTarihi", "")).strip()
                fiz    = str(row.get("FizikselDurum",  "")).strip()
                sko    = str(row.get("SkopiDurum",     "")).strip()
                env    = envanter_map.get(eno, {})

                if tarih:
                    tarih_set.add(tarih)

                sonuc = (
                    "Kullanıma Uygun Değil"
                    if "Değil" in fiz or "Değil" in sko
                    else "Kullanıma Uygun"
                )

                muayene_listesi.append({
                    "EkipmanNo":   eno,
                    "Cins":        env.get("Cins",  ""),
                    "Pb":          env.get("Pb",    ""),
                    "Birim":       env.get("Birim", ""),
                    "ABD":         env.get("ABD",   ""),
                    "Tarih":       tarih,
                    "Fiziksel":    fiz,
                    "Skopi":       sko,
                    "Sonuc":       sonuc,
                    "KontrolEden": str(row.get("KontrolEdenUnvani", "")).strip(),
                    "Aciklama":    str(row.get("Aciklamalar",       "")).strip(),
                })

            def parse_date(s):
                for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
                    try:
                        return datetime.datetime.strptime(s, fmt).date()
                    except Exception:
                        continue
                return datetime.date.min

            sirali_tarih = sorted(tarih_set, key=parse_date, reverse=True)

            self.veri_hazir.emit(
                muayene_listesi,
                envanter_listesi,
                sorted(abd_set   - {""}),
                sorted(birim_set - {""}),
                sirali_tarih
            )
        except Exception as e:
            exc_logla("RKERapor.Worker", e)
            self.hata_olustu.emit(str(e))
        finally:
            if db:
                db.close()


class RaporOlusturucuThread(QThread):
    """PDF oluşturur ve Drive'a yükler."""
    log_mesaji  = Signal(str)
    islem_bitti = Signal()

    def __init__(self, mod, veriler, ozet, filtre_info=None):
        super().__init__()
        self._mod    = mod     # 1: Genel, 2: Hurda, 3: ABD Envanter, 4: ABD+Birim Envanter
        self._veriler = veriler
        self._ozet   = ozet
        self._filtre_info = filtre_info or {"abd": "", "birim": "", "tarih": ""}

    def run(self):
        gecici_dosyalar = []
        try:
            rapor_tarihi = datetime.datetime.now().strftime("%d.%m.%Y")
            zaman = datetime.datetime.now().strftime("%d%m%Y")
            
            # Filtre bilgilerinden dosya adı bileşenleri oluştur
            abd = self._filtre_info.get("abd", "").replace(" ", "_").replace("/", "_") or "Tum_Bolumler"
            birim = self._filtre_info.get("birim", "").replace(" ", "_").replace("/", "_") or "Tum_Birimler"
            
            # Tarih formatını DD MM YYYY olarak düzenle
            tarih_raw = self._filtre_info.get("tarih", "")
            if tarih_raw:
                try:
                    # Çeşitli tarih formatlarını try et
                    for fmt in ("%Y%m%d", "%d%m%Y", "%Y-%m-%d", "%d.%m.%Y"):
                        try:
                            dt = datetime.datetime.strptime(tarih_raw, fmt).date()
                            tarih = dt.strftime("%d%m%Y")
                            break
                        except ValueError:
                            continue
                    else:
                        tarih = zaman
                except Exception:
                    tarih = zaman
            else:
                tarih = zaman

            if self._mod == 1:
                # A. Genel Kontrol Raporu: RKE_Muayene_{ABD}_{Birim}_{Tarih}.pdf
                if not self._veriler:
                    self.log_mesaji.emit("UYARI: Rapor oluşturmak için veri bulunamadı.")
                    return
                dosya_adi = f"RKE_Muayene_{abd}_{birim}_{tarih}.pdf"
                if RaporServisi.pdf(
                    sablon="rke_genel",
                    context={"filtre": self._ozet, "rapor_tarihi": rapor_tarihi},
                    tablo=self._veriler,
                    kayit_yolu=dosya_adi
                ):
                    gecici_dosyalar.append(dosya_adi)
                    self._yukle_drive(dosya_adi)
                else:
                    self.log_mesaji.emit("HATA: PDF oluşturulamadı.")

            elif self._mod == 2:
                # B. Hurda Raporu: RKE_Hurda_{ABD}_{Birim}_{Tarih}.pdf
                # Liste zaten filtrelendiği için self._veriler kullanılabilir
                hurda = self._veriler
                if not hurda:
                    self.log_mesaji.emit("UYARI: Hurda adayı kayıt bulunamadı.")
                    return
                dosya_adi = f"RKE_Hurda_{abd}_{birim}_{tarih}.pdf"
                if RaporServisi.pdf(
                    sablon="rke_hurda",
                    context={"rapor_tarihi": rapor_tarihi},
                    tablo=hurda,
                    kayit_yolu=dosya_adi
                ):
                    gecici_dosyalar.append(dosya_adi)
                    self._yukle_drive(dosya_adi)
                else:
                    self.log_mesaji.emit("HATA: Hurda PDF oluşturulamadı.")

            elif self._mod == 3:
                # C. Ana Bilim Dalı Envanter: RKE_Envanter_{ABD}_{Tarih}.pdf
                if not self._veriler:
                    self.log_mesaji.emit("UYARI: Rapor oluşturmak için veri bulunamadı.")
                    return
                dosya_adi = f"RKE_Envanter_{abd}_{tarih}.pdf"
                if RaporServisi.pdf(
                    sablon="rke_envanter_abd",
                    context={"bolum": self._ozet, "rapor_tarihi": rapor_tarihi},
                    tablo=self._veriler,
                    kayit_yolu=dosya_adi
                ):
                    gecici_dosyalar.append(dosya_adi)
                    self._yukle_drive(dosya_adi)
                else:
                    self.log_mesaji.emit("HATA: ABD Envanter PDF oluşturulamadı.")

            elif self._mod == 4:
                # D. Ana Bilim Dalı + Birim Envanter: RKE_Envanteri_{ABD}_{Birim}_{Tarih}.pdf
                if not self._veriler:
                    self.log_mesaji.emit("UYARI: Rapor oluşturmak için veri bulunamadı.")
                    return
                dosya_adi = f"RKE_Envanteri_{abd}_{birim}_{tarih}.pdf"
                if RaporServisi.pdf(
                    sablon="rke_envanter_detayli",
                    context={"filtre": self._ozet, "rapor_tarihi": rapor_tarihi},
                    tablo=self._veriler,
                    kayit_yolu=dosya_adi
                ):
                    gecici_dosyalar.append(dosya_adi)
                    self._yukle_drive(dosya_adi)
                else:
                    self.log_mesaji.emit("HATA: ABD+Birim Envanter PDF oluşturulamadı.")

        except Exception as e:
            self.log_mesaji.emit(f"HATA: {e}")
            logger.error(f"RaporOlusturucu hatası: {e}")
        finally:
            for f in gecici_dosyalar:
                try:
                    if os.path.exists(f):
                        os.remove(f)
                except Exception as _e:
                    logger.warning(f"Geçici dosya silinemedi: {f} — {_e}")
            self.islem_bitti.emit()

    def _yukle_drive(self, dosya_adi: str):
        db = None
        try:
            from database.sqlite_manager import SQLiteManager
            from core.di import get_registry, get_cloud_adapter
            from database.google.utils import resolve_storage_target

            db       = SQLiteManager()
            registry = get_registry(db)
            all_sabit = registry.get("Sabitler").get_all()
            storage_target = resolve_storage_target(all_sabit, "RKE_Raporlar")
            cloud = get_cloud_adapter()
            link  = cloud.upload_file(
                dosya_adi,
                parent_folder_id=storage_target["drive_folder_id"],
                offline_folder_name=storage_target["offline_folder_name"]
            )
            if link:
                if str(link).startswith("http"):
                    self.log_mesaji.emit("BASARILI: Drive'a yüklendi.")
                else:
                    self.log_mesaji.emit(f"BASARILI: Yerel klasöre kaydedildi ({os.path.basename(str(link))}).")
            else:
                self.log_mesaji.emit("UYARI: Yükleme yapılamadı (Offline modda hedef klasör tanımlı olmayabilir).")
        except Exception as e:
            self.log_mesaji.emit(f"UYARI: Drive hatasi: {e}")
            logger.warning(f"Drive yükleme hatası: {e}")
        finally:
            if db:
                db.close()


# ═══════════════════════════════════════════════
#  ANA SAYFA
# ═══════════════════════════════════════════════

class RKERaporPage(QWidget):
    """
    RKE Raporlama ve Analiz sayfası.
    db: SQLiteManager instance
    """

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(S.get("page", "background-color: transparent;"))
        self._db               = db
        self._muayene_verileri = []
        self._envanter_verileri= []
        self._filtreli_veri    = []

        self._setup_ui()
        self._connect_signals()
        self.load_data()

    # ═══════════════════════════════════════════
    #  UI
    # ═══════════════════════════════════════════

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(16, 12, 16, 12)
        main.setSpacing(12)

        # ── KONTROL PANELİ ──
        panel = QGroupBox("Rapor Ayarlari ve Filtreler")
        panel.setStyleSheet(S.get("group", ""))
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        h_panel = QHBoxLayout(panel)
        h_panel.setSpacing(20)

        # Sol: Rapor Türü
        v_left = QVBoxLayout()
        v_left.setSpacing(8)
        lbl_tur = QLabel("RAPOR TÜRÜ")
        lbl_tur.setStyleSheet(S.get("section_title", ""))
        v_left.addWidget(lbl_tur)

        radio_ss = f"""
            QRadioButton {{ color:{DarkTheme.TEXT_SECONDARY}; font-size:13px; padding:4px; background:transparent; }}
            QRadioButton::indicator {{ width:16px; height:16px; border-radius:9px; border:2px solid {DarkTheme.BORDER_PRIMARY}; background:{DarkTheme.BG_SECONDARY}; }}
            QRadioButton::indicator:checked {{ background-color:{DarkTheme.INPUT_BORDER_FOCUS}; border-color:{DarkTheme.INPUT_BORDER_FOCUS}; }}
            QRadioButton:hover {{ color:{DarkTheme.TEXT_PRIMARY}; }}
        """
        self._rb_genel = QRadioButton("A.  Kontrol Raporu (Genel)")
        self._rb_genel.setChecked(True)
        self._rb_genel.setStyleSheet(radio_ss)
        self._rb_hurda = QRadioButton("B.  Hurda (HEK) Raporu")
        self._rb_hurda.setStyleSheet(radio_ss)
        self._rb_abd_env = QRadioButton("C.  Ana Bilim Dalı Envanteri")
        self._rb_abd_env.setStyleSheet(radio_ss)
        self._rb_abd_birim_env = QRadioButton("D.  Ana Bilim Dalı + Birim Envanteri")
        self._rb_abd_birim_env.setStyleSheet(radio_ss)

        self._btn_group = QButtonGroup(self)
        for rb in (self._rb_genel, self._rb_hurda, self._rb_abd_env, self._rb_abd_birim_env):
            v_left.addWidget(rb)
            self._btn_group.addButton(rb)
        v_left.addStretch()
        h_panel.addLayout(v_left)

        # Dikey ayraç
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(S.get("separator", ""))
        h_panel.addWidget(sep)

        # Sağ: Filtreler + Butonlar
        v_right = QVBoxLayout()
        v_right.setSpacing(12)

        # Filtre comboları
        h_filters = QHBoxLayout()
        h_filters.setSpacing(12)

        self._cmb_abd   = self._make_labeled_combo("Ana Bilim Dalı",  "Tüm Bölümler")
        self._cmb_birim = self._make_labeled_combo("Birim",           "Tüm Birimler")
        self._cmb_tarih = self._make_labeled_combo("İşlem Tarihi",    "Tüm Tarihler")

        for w in (self._cmb_abd, self._cmb_birim, self._cmb_tarih):
            h_filters.addWidget(w["container"])

        # Arama
        txt_wrap = QWidget()
        txt_wrap.setStyleSheet("background: transparent;")
        tw = QVBoxLayout(txt_wrap)
        tw.setContentsMargins(0, 0, 0, 0)
        tw.setSpacing(4)
        tw.addWidget(QLabel("Ara"))
        self._txt_ara = QLineEdit()
        self._txt_ara.setPlaceholderText("Ekipman / Cins / Birim...")
        self._txt_ara.setClearButtonEnabled(True)
        self._txt_ara.setStyleSheet(S.get("search", ""))
        tw.addWidget(self._txt_ara)
        h_filters.addWidget(txt_wrap)

        v_right.addLayout(h_filters)

        # Butonlar
        h_btn = QHBoxLayout()
        h_btn.setSpacing(10)

        self._btn_yenile = QPushButton("VERILERI YENILE")
        self._btn_yenile.setStyleSheet(S.get("refresh_btn", ""))
        self._btn_yenile.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self._btn_yenile, "sync", color=DarkTheme.TEXT_PRIMARY, size=14)

        self._btn_olustur = QPushButton("PDF RAPOR OLUSTUR")
        self._btn_olustur.setStyleSheet(S.get("pdf_btn", ""))
        self._btn_olustur.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self._btn_olustur, "save", color=DarkTheme.TEXT_PRIMARY, size=14)

        h_btn.addWidget(self._btn_yenile)
        h_btn.addWidget(self._btn_olustur)
        h_btn.addStretch()

        _sep_k = QFrame()
        _sep_k.setFrameShape(QFrame.VLine)
        _sep_k.setFixedHeight(28)
        _sep_k.setStyleSheet(S.get("separator", ""))
        h_btn.addWidget(_sep_k)

        self.btn_kapat = QPushButton("KAPAT")
        self.btn_kapat.setToolTip("Pencereyi Kapat")
        self.btn_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kapat.setStyleSheet(S.get("close_btn", ""))
        IconRenderer.set_button_icon(self.btn_kapat, "x", color=DarkTheme.TEXT_PRIMARY, size=14)
        h_btn.addWidget(self.btn_kapat)

        v_right.addLayout(h_btn)
        v_right.addStretch()

        h_panel.addLayout(v_right)
        main.addWidget(panel)

        # ── PROGRESS ──
        self._pbar = QProgressBar()
        self._pbar.setFixedHeight(4)
        self._pbar.setTextVisible(False)
        self._pbar.setStyleSheet(S.get("progress", ""))
        self._pbar.setVisible(False)
        main.addWidget(self._pbar)

        # ── TABLO ──
        self._model = RaporTableModel()
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self._proxy.setFilterKeyColumn(-1)

        self._table = QTableView()
        self._table.setModel(self._proxy)
        self._table.setStyleSheet(S.get("table", ""))
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSortingEnabled(True)

        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Tarih
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Pb

        main.addWidget(self._table, 1)

        # ── FOOTER ──
        footer = QHBoxLayout()
        self._lbl_sayi = QLabel("0 kayıt")
        self._lbl_sayi.setStyleSheet(S.get("footer_label", f"color:{DarkTheme.TEXT_MUTED}; font-size:11px;"))
        footer.addWidget(self._lbl_sayi)
        footer.addStretch()
        main.addLayout(footer)

    def _make_labeled_combo(self, label_text, default_item):
        c = QWidget()
        c.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(c)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl = QLabel(label_text)
        lbl.setStyleSheet(S.get("label", ""))
        cmb = QComboBox()
        cmb.setStyleSheet(S.get("combo", ""))
        cmb.setMinimumWidth(160)
        cmb.addItem(default_item)
        lay.addWidget(lbl)
        lay.addWidget(cmb)
        return {"container": c, "combo": cmb}

    # ═══════════════════════════════════════════
    #  SİNYALLER
    # ═══════════════════════════════════════════

    def _connect_signals(self):
        self._btn_yenile.clicked.connect(self.load_data)
        self._btn_olustur.clicked.connect(self._on_rapor_olustur)
        self._txt_ara.textChanged.connect(self._proxy.setFilterFixedString)
        self._cmb_abd["combo"].currentTextChanged.connect(self._on_abd_birim_degisti)
        self._cmb_birim["combo"].currentTextChanged.connect(self._on_abd_birim_degisti)
        self._cmb_tarih["combo"].currentTextChanged.connect(self._filtrele)
        self._btn_group.buttonClicked.connect(lambda _: self._on_abd_birim_degisti())

    # ═══════════════════════════════════════════
    #  VERİ
    # ═══════════════════════════════════════════

    def load_data(self):
        # Önceki thread hâlâ çalışıyorsa yeni başlatma
        if hasattr(self, "_loader") and self._loader.isRunning():
            return
        self._pbar.setVisible(True)
        self._pbar.setRange(0, 0)
        self._btn_olustur.setEnabled(False)
        self._btn_yenile.setText("Yükleniyor…")

        self._loader = VeriYukleyiciThread()
        self._loader.veri_hazir.connect(self._on_data_ready)
        self._loader.hata_olustu.connect(self._on_error)
        self._loader.finished.connect(self._on_loader_finished)
        self._loader.start()

    def _on_loader_finished(self):
        self._pbar.setVisible(False)
        self._btn_olustur.setEnabled(True)
        self._btn_yenile.setText("VERILERI YENILE")

    def _on_data_ready(self, muayene, envanter, abd_listesi, birim_listesi, tarih_listesi):
        self._muayene_verileri = muayene
        self._envanter_verileri = envanter

        def fill(widget_dict, items, default):
            cmb = widget_dict["combo"]
            cmb.blockSignals(True)
            curr = cmb.currentText()
            cmb.clear()
            cmb.addItem(default)
            cmb.addItems(items)
            idx = cmb.findText(curr)
            cmb.setCurrentIndex(idx if idx >= 0 else 0)
            cmb.blockSignals(False)

        fill(self._cmb_abd,   abd_listesi,  "Tüm Bölümler")
        fill(self._cmb_birim, birim_listesi, "Tüm Birimler")
        fill(self._cmb_tarih, tarih_listesi, "Tüm Tarihler")

        self._on_abd_birim_degisti()

    def _get_aktif_veri(self):
        """Seçili rapor türüne göre kullanılacak veri setini döndürür."""
        if self._rb_abd_env.isChecked() or self._rb_abd_birim_env.isChecked():
            return self._envanter_verileri
        return self._muayene_verileri

    def _on_abd_birim_degisti(self):
        """ABD veya Birim değişince Tarih combosu yeniden hesaplanır."""
        f_abd   = self._cmb_abd["combo"].currentText()
        f_birim = self._cmb_birim["combo"].currentText()
        aktif_veri = self._get_aktif_veri()

        mevcut_tarihler = set()
        for row in aktif_veri:
            if "Tüm" not in f_abd   and row.get("ABD",   "") != f_abd:   continue
            if "Tüm" not in f_birim and row.get("Birim", "") != f_birim: continue
            if row.get("Tarih"):
                mevcut_tarihler.add(row["Tarih"])

        def parse(s):
            for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
                try:
                    return datetime.datetime.strptime(s, fmt).date()
                except Exception:
                    pass
            return datetime.date.min

        sirali = sorted(mevcut_tarihler, key=parse, reverse=True)

        cmb = self._cmb_tarih["combo"]
        cmb.blockSignals(True)
        cmb.clear()
        cmb.addItem("Tüm Tarihler")
        cmb.addItems(sirali)

        # Envanter raporları seçiliyse tarih filtresini sıfırla ve devre dışı bırak
        is_envanter = self._rb_abd_env.isChecked() or self._rb_abd_birim_env.isChecked()
        if is_envanter:
            cmb.setCurrentIndex(0)
            cmb.setEnabled(False)
        else:
            cmb.setEnabled(True)

        cmb.blockSignals(False)

        self._filtrele()

    def _filtrele(self):
        f_abd   = self._cmb_abd["combo"].currentText()
        f_birim = self._cmb_birim["combo"].currentText()
        f_tarih = self._cmb_tarih["combo"].currentText()
        aktif_veri = self._get_aktif_veri()

        filtered = []
        for row in aktif_veri:
            if "Tüm" not in f_abd   and row.get("ABD",   "") != f_abd:   continue
            if "Tüm" not in f_birim and row.get("Birim", "") != f_birim: continue
            if "Tüm" not in f_tarih and row.get("Tarih", "") != f_tarih: continue
            if self._rb_hurda.isChecked() and "Değil" not in row.get("Sonuc", ""):
                continue
            filtered.append(row)

        self._filtreli_veri = filtered
        self._model.set_data(filtered)
        self._lbl_sayi.setText(f"{len(filtered)} kayıt")
        
        # Veri boşsa rapor oluştur butonunu devre dışı bırak
        self._btn_olustur.setEnabled(len(filtered) > 0)

    # ═══════════════════════════════════════════
    #  RAPOR OLUŞTURMA
    # ═══════════════════════════════════════════

    def _on_rapor_olustur(self):
        # Filtre kontrolü: 3'ü de "Tüm" ise uyarı ver
        f_abd   = self._cmb_abd["combo"].currentText()
        f_birim = self._cmb_birim["combo"].currentText()
        f_tarih = self._cmb_tarih["combo"].currentText()
        
        if f_abd == "Tüm Bölümler" and f_birim == "Tüm Birimler" and f_tarih == "Tüm Tarihler":
            QMessageBox.warning(self, "Uyarı", "Lütfen en az bir filtre seçiniz.")
            return
        
        if not self._filtreli_veri:
            QMessageBox.warning(self, "Uyarı", "Rapor oluşturmak için tabloda veri olmalıdır.")
            return

        mod = 1
        if self._rb_hurda.isChecked():
            mod = 2
        elif self._rb_abd_env.isChecked():
            mod = 3
        elif self._rb_abd_birim_env.isChecked():
            mod = 4

        # Dosya adı için filtre bilgilerini hazırla
        abd_kisa   = f_abd.replace("Tüm Bölümler", "").strip()
        birim_kisa = f_birim.replace("Tüm Birimler", "").strip()
        
        # Tarih formatını DD MM YYYY (DDMMYYYY) olarak düzenle
        tarih_raw = f_tarih.replace("Tüm Tarihler", "").strip()
        if tarih_raw:
            try:
                # Çeşitli formatı detect et ve DD MM YYYY formatına çevir
                if "." in tarih_raw:
                    # DD.MM.YYYY formatı
                    dt = datetime.datetime.strptime(tarih_raw, "%d.%m.%Y").date()
                elif "-" in tarih_raw:
                    # YYYY-MM-DD formatı
                    dt = datetime.datetime.strptime(tarih_raw, "%Y-%m-%d").date()
                else:
                    # YYYYMMDD veya DDMMYYYY fallback
                    dt = None
                
                if dt:
                    tarih_kisa = dt.strftime("%d%m%Y")
                else:
                    tarih_kisa = ""
            except Exception:
                tarih_kisa = ""
        else:
            tarih_kisa = ""
        
        filtre_info = {
            "abd": abd_kisa,
            "birim": birim_kisa,
            "tarih": tarih_kisa
        }

        ozet = f"{f_abd} — {f_birim}"

        # Önceki rapor işlemi hâlâ sürüyorsa yeni başlatma
        if hasattr(self, "_worker") and self._worker.isRunning():
            QMessageBox.warning(self, "Uyarı", "Önceki rapor işlemi henüz tamamlanmadı.")
            return

        self._btn_olustur.setEnabled(False)
        self._btn_olustur.setText("İşleniyor…")
        self._pbar.setVisible(True)
        self._pbar.setRange(0, 0)

        self._worker = RaporOlusturucuThread(mod, self._filtreli_veri, ozet, filtre_info)
        self._worker.log_mesaji.connect(self._on_log)
        self._worker.islem_bitti.connect(self._on_rapor_bitti)
        self._worker.start()

    def _on_rapor_bitti(self):
        self._pbar.setVisible(False)
        self._btn_olustur.setEnabled(True)
        self._btn_olustur.setText("PDF RAPOR OLUSTUR")
        QMessageBox.information(
            self, "Tamamlandı",
            "Rapor işlemi tamamlandı. PDF oluşturulduysa Drive'a yüklenmiştir."
        )

    def _on_log(self, msg):
        logger.info(f"[RKERapor] {msg}")
        if "HATA" in msg:
            QMessageBox.warning(self, "Uyarı", msg)

    def _on_error(self, msg):
        self._pbar.setVisible(False)
        self._btn_olustur.setEnabled(True)
        self._btn_yenile.setText("VERILERI YENILE")
        logger.error(f"RKERapor hatası: {msg}")
        QMessageBox.critical(self, "Hata", msg)

# -*- coding: utf-8 -*-
"""
RKE Raporlama Sayfası
──────────────────────
• Filtre paneli: ABD / Birim / Tarih + rapor türü (Genel / Hurda / Personel Bazlı)
• QAbstractTableModel tablosu
• PDF oluşturma ve Google Drive'a yükleme
• itf_desktop mimarisine uygun (RepositoryRegistry(db), core.logger, GoogleDriveService)
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
    QColor, QCursor,
    QTextDocument, QPdfWriter, QPageSize, QPageLayout, QFont
)
from PySide6.QtCore import QMarginsF

from core.logger import logger
from core.hata_yonetici import exc_logla
from ui.theme_manager import ThemeManager

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

SONUC_RENK = {
    "Kullanıma Uygun":       QColor("#4ade80"),
    "Kullanıma Uygun Değil": QColor("#f87171"),
}


# ═══════════════════════════════════════════════
#  PDF ŞABLONLARI
# ═══════════════════════════════════════════════

def _base_css():
    return """
        body { font-family: 'Times New Roman', serif; font-size: 11pt; color: #000; }
        h1 { text-align: center; font-size: 14pt; font-weight: bold; margin-bottom: 5px; }
        h2 { font-size: 12pt; font-weight: bold; margin-top: 15px; text-decoration: underline; }
        .center { text-align: center; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 10pt; }
        th, td { border: 1px solid #000; padding: 4px; text-align: center; vertical-align: middle; }
        th { background-color: #f0f0f0; font-weight: bold; }
        .left { text-align: left; }
        .sig-table { width: 100%; border: none; margin-top: 40px; }
        .sig-table td { border: none; text-align: center; vertical-align: top; padding: 20px; }
        .line { border-top: 1px solid #000; width: 80%; margin: 30px auto 0; }
        .legal { text-align: justify; margin: 5px 0; line-height: 1.4; }
    """


def html_genel_rapor(veriler, filtre_ozeti):
    tarih = datetime.datetime.now().strftime("%d.%m.%Y")
    rows  = "".join(
        f"<tr><td>{r['Cins']}</td><td>{r['EkipmanNo']}</td><td>{r['Pb']}</td>"
        f"<td>{r['Tarih']}<br>{r['Sonuc']}</td>"
        f"<td class='left'>{r['Aciklama']}</td></tr>"
        for r in veriler
    )
    return f"""
    <html><head><style>{_base_css()}</style></head><body>
    <h1>RADYASYON KORUYUCU EKİPMAN (RKE) KONTROL RAPORU</h1>
    <div class="center">Filtre: {filtre_ozeti} | Tarih: {tarih}</div>
    <table>
      <thead>
        <tr>
          <th>Koruyucu Cinsi</th><th>Ekipman No</th><th>Pb (mm)</th>
          <th>Kontrol (Tarih – Sonuç)</th><th>Açıklama</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
    <p style="font-size:9pt; font-style:italic; margin-top:8px;">
      * Bu form toplu kontroller için üretilmiştir.
    </p>
    <table class="sig-table">
      <tr>
        <td><b>Kontrol Eden</b><div class="line">İmza</div></td>
        <td><b>Birim Sorumlusu</b><div class="line">İmza</div></td>
        <td><b>Radyasyon Koruma Sorumlusu</b><div class="line">İmza</div></td>
      </tr>
    </table>
    </body></html>
    """


def html_hurda_rapor(veriler):
    tarih = datetime.datetime.now().strftime("%d.%m.%Y")
    rows  = ""
    for i, r in enumerate(veriler, 1):
        sorunlar = []
        if "Değil" in r.get("Sonuc", ""):
            sorunlar.append(f"Muayene: {r['Sonuc']}")
        if r.get("Aciklama"):
            sorunlar.append(r["Aciklama"])
        rows += (
            f"<tr><td>{i}</td><td>{r['Cins']}</td><td>{r['EkipmanNo']}</td>"
            f"<td>{r.get('ABD','')}</td><td>{r['Pb']}</td>"
            f"<td class='left'>{' | '.join(sorunlar)}</td></tr>"
        )
    return f"""
    <html><head><style>{_base_css()}</style></head><body>
    <h1>HURDA (HEK) EKİPMAN TEKNİK RAPORU</h1>
    <div class="center">Tarih: {tarih}</div>
    <h2>A. İmha Edilecek Ekipman Listesi</h2>
    <table>
      <thead>
        <tr>
          <th>Sıra</th><th>Cinsi</th><th>Ekipman No</th>
          <th>Bölüm</th><th>Pb (mm)</th><th>Uygunsuzluk</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
    <h2>B. Teknik Rapor ve Talep</h2>
    <p class="legal">
      Yukarıda bilgileri belirtilen ekipmanların fiziksel veya radyolojik bütünlüklerini
      yitirdikleri tespit edilmiştir. Hizmet dışı bırakılarak (HEK) demirbaş kayıtlarından
      düşülmesi arz olunur.
    </p>
    <table class="sig-table">
      <tr>
        <td><b>Kontrol Eden</b><div class="line">İmza</div></td>
        <td><b>Birim Sorumlusu</b><div class="line">İmza</div></td>
        <td><b>RKS</b><div class="line">İmza</div></td>
      </tr>
    </table>
    </body></html>
    """


def pdf_olustur(html_content: str, dosya_yolu: str) -> bool:
    """HTML içeriğini A4 PDF olarak kaydeder."""
    try:
        doc = QTextDocument()
        doc.setHtml(html_content)
        writer = QPdfWriter(dosya_yolu)
        writer.setPageSize(QPageSize(QPageSize.A4))
        writer.setResolution(300)
        layout = QPageLayout()
        layout.setPageSize(QPageSize(QPageSize.A4))
        layout.setOrientation(QPageLayout.Portrait)
        layout.setMargins(QMarginsF(15, 15, 15, 15))
        writer.setPageLayout(layout)
        doc.print_(writer)
        return True
    except Exception as e:
        logger.error(f"PDF oluşturma hatası: {e}")
        return False


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
            return SONUC_RENK.get(str(row.get(col, "")), QColor("#8b8fa3"))
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
    veri_hazir  = Signal(list, list, list, list)   # data, abd_listesi, birim_listesi, tarih_listesi
    hata_olustu = Signal(str)

    def run(self):
        from database.sqlite_manager import SQLiteManager
        from database.repository_registry import RepositoryRegistry
        db = None
        try:
            db       = SQLiteManager()
            registry = RepositoryRegistry(db)

            envanter_map = {}
            for row in registry.get("RKE_List").get_all():
                eno = str(row.get("EkipmanNo", "")).strip()
                if eno:
                    envanter_map[eno] = {
                        "ABD":   str(row.get("AnaBilimDali",    "")).strip(),
                        "Birim": str(row.get("Birim",           "")).strip(),
                        "Cins":  str(row.get("KoruyucuCinsi",   "")).strip(),
                        "Pb":    str(row.get("KursunEsdegeri",  "")).strip(),
                    }

            birlesik = []
            abd_set   = set()
            birim_set = set()
            tarih_set = set()

            for row in registry.get("RKE_Muayene").get_all():
                eno    = str(row.get("EkipmanNo",      "")).strip()
                tarih  = str(row.get("FMuayeneTarihi", "")).strip()
                fiz    = str(row.get("FizikselDurum",  "")).strip()
                sko    = str(row.get("SkopiDurum",     "")).strip()
                env    = envanter_map.get(eno, {})

                abd_set.add(env.get("ABD",   ""))
                birim_set.add(env.get("Birim", ""))
                if tarih:
                    tarih_set.add(tarih)

                sonuc = (
                    "Kullanıma Uygun Değil"
                    if "Değil" in fiz or "Değil" in sko
                    else "Kullanıma Uygun"
                )

                birlesik.append({
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
                birlesik,
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

    def __init__(self, mod, veriler, ozet):
        super().__init__()
        self._mod    = mod     # 1: Genel, 2: Hurda, 3: Personel Bazlı
        self._veriler = veriler
        self._ozet   = ozet

    def run(self):
        gecici_dosyalar = []
        try:
            zaman = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

            if self._mod == 1:
                # Genel Kontrol Raporu
                if not self._veriler:
                    self.log_mesaji.emit("⚠️ Rapor için veri bulunamadı.")
                    return
                dosya_adi = f"RKE_Genel_{zaman}.pdf"
                html = html_genel_rapor(self._veriler, self._ozet)
                if pdf_olustur(html, dosya_adi):
                    gecici_dosyalar.append(dosya_adi)
                    self._yukle_drive(dosya_adi)
                else:
                    self.log_mesaji.emit("❌ PDF oluşturulamadı.")

            elif self._mod == 2:
                # Hurda Raporu
                hurda = [v for v in self._veriler if "Değil" in v.get("Sonuc", "")]
                if not hurda:
                    self.log_mesaji.emit("⚠️ Hurda adayı kayıt bulunamadı.")
                    return
                dosya_adi = f"RKE_Hurda_{zaman}.pdf"
                html = html_hurda_rapor(hurda)
                if pdf_olustur(html, dosya_adi):
                    gecici_dosyalar.append(dosya_adi)
                    self._yukle_drive(dosya_adi)
                else:
                    self.log_mesaji.emit("❌ Hurda PDF oluşturulamadı.")

            elif self._mod == 3:
                # Personel Bazlı (kişi × tarih grupları)
                gruplar: dict = {}
                for item in self._veriler:
                    key = (item.get("KontrolEden", ""), item.get("Tarih", ""))
                    gruplar.setdefault(key, []).append(item)

                self.log_mesaji.emit(f"ℹ️ {len(gruplar)} farklı rapor hazırlanıyor...")
                for (kisi, tarih), liste in gruplar.items():
                    ad       = f"Rapor_{kisi}_{tarih}".replace(" ", "_")
                    dosya_adi = f"{ad}_{zaman}.pdf"
                    html = html_genel_rapor(liste, f"Kontrolör: {kisi} — {tarih}")
                    if pdf_olustur(html, dosya_adi):
                        gecici_dosyalar.append(dosya_adi)
                        self._yukle_drive(dosya_adi)
                        self.log_mesaji.emit(f"✅ {dosya_adi} yüklendi.")

        except Exception as e:
            self.log_mesaji.emit(f"❌ Hata: {e}")
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
        try:
            from database.sqlite_manager import SQLiteManager
            from database.repository_registry import RepositoryRegistry
            from database.google import GoogleDriveService

            db       = SQLiteManager()
            registry = RepositoryRegistry(db)
            all_sabit = registry.get("Sabitler").get_all()
            folder_id = next(
                (str(r.get("Aciklama", "")).strip()
                 for r in all_sabit
                 if r.get("Kod") == "Sistem_DriveID" and r.get("MenuEleman") == "RKE_Raporlar"),
                ""
            )
            db.close()

            drive = GoogleDriveService()
            link  = drive.upload_file(dosya_adi, parent_folder_id=folder_id)
            if link:
                self.log_mesaji.emit(f"✅ Drive'a yüklendi.")
            else:
                self.log_mesaji.emit("⚠️ Drive yükleme başarısız.")
        except Exception as e:
            self.log_mesaji.emit(f"⚠️ Drive hatası: {e}")
            logger.warning(f"Drive yükleme hatası: {e}")


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
        self._db             = db
        self._ham_veriler    = []
        self._filtreli_veri  = []

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
        panel = QGroupBox("📊  Rapor Ayarları ve Filtreler")
        panel.setStyleSheet(S.get("group", ""))
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        h_panel = QHBoxLayout(panel)
        h_panel.setSpacing(20)

        # Sol: Rapor Türü
        v_left = QVBoxLayout()
        v_left.setSpacing(8)
        lbl_tur = QLabel("RAPOR TÜRÜ")
        lbl_tur.setStyleSheet("color:#8b8fa3; font-size:11px; font-weight:bold; letter-spacing:1px;")
        v_left.addWidget(lbl_tur)

        radio_ss = """
            QRadioButton { color:#c8cad0; font-size:13px; padding:4px; background:transparent; }
            QRadioButton::indicator { width:16px; height:16px; border-radius:9px; border:2px solid #444; background:#222; }
            QRadioButton::indicator:checked { background-color:#ab47bc; border-color:#ab47bc; }
            QRadioButton:hover { color:#ffffff; }
        """
        self._rb_genel = QRadioButton("A.  Kontrol Raporu (Genel)")
        self._rb_genel.setChecked(True)
        self._rb_genel.setStyleSheet(radio_ss)
        self._rb_hurda = QRadioButton("B.  Hurda (HEK) Raporu")
        self._rb_hurda.setStyleSheet(radio_ss)
        self._rb_kisi  = QRadioButton("C.  Personel Bazlı Raporlar")
        self._rb_kisi.setStyleSheet(radio_ss)

        self._btn_group = QButtonGroup(self)
        for rb in (self._rb_genel, self._rb_hurda, self._rb_kisi):
            v_left.addWidget(rb)
            self._btn_group.addButton(rb)
        v_left.addStretch()
        h_panel.addLayout(v_left)

        # Dikey ayraç
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("background-color: rgba(255,255,255,0.08);")
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
        self._txt_ara.setPlaceholderText("🔍 Ekipman / Cins / Birim...")
        self._txt_ara.setClearButtonEnabled(True)
        self._txt_ara.setStyleSheet(S.get("search", ""))
        tw.addWidget(self._txt_ara)
        h_filters.addWidget(txt_wrap)

        v_right.addLayout(h_filters)

        # Butonlar
        h_btn = QHBoxLayout()
        h_btn.setSpacing(10)

        self._btn_yenile = QPushButton("⟳ VERİLERİ YENİLE")
        self._btn_yenile.setFixedHeight(40)
        self._btn_yenile.setStyleSheet(S.get("refresh_btn", ""))
        self._btn_yenile.setCursor(QCursor(Qt.PointingHandCursor))

        self._btn_olustur = QPushButton("📄  PDF RAPOR OLUŞTUR")
        self._btn_olustur.setFixedHeight(40)
        self._btn_olustur.setStyleSheet(
            "QPushButton { background-color:#c62828; color:white; font-weight:bold; "
            "font-size:13px; border-radius:6px; border:none; padding:0 16px; } "
            "QPushButton:hover { background-color:#b71c1c; } "
            "QPushButton:disabled { background-color:#333; color:#555; }"
        )
        self._btn_olustur.setCursor(QCursor(Qt.PointingHandCursor))

        h_btn.addWidget(self._btn_yenile)
        h_btn.addWidget(self._btn_olustur)
        h_btn.addStretch()

        _sep_k = QFrame()
        _sep_k.setFrameShape(QFrame.VLine)
        _sep_k.setFixedHeight(28)
        _sep_k.setStyleSheet("background-color: rgba(255,255,255,0.08);")
        h_btn.addWidget(_sep_k)

        self.btn_kapat = QPushButton("✕  KAPAT")
        self.btn_kapat.setFixedHeight(40)
        self.btn_kapat.setToolTip("Pencereyi Kapat")
        self.btn_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kapat.setStyleSheet(S.get("close_btn", ""))
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
        self._lbl_sayi.setStyleSheet(S.get("footer_label", "color:#8b8fa3; font-size:11px;"))
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
        self._btn_group.buttonClicked.connect(lambda _: self._filtrele())

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
        self._btn_yenile.setText("⟳ Yenile  VERİLERİ YENİLE")

    def _on_data_ready(self, data, abd_listesi, birim_listesi, tarih_listesi):
        self._ham_veriler = data

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

    def _on_abd_birim_degisti(self):
        """ABD veya Birim değişince Tarih combosu yeniden hesaplanır."""
        f_abd   = self._cmb_abd["combo"].currentText()
        f_birim = self._cmb_birim["combo"].currentText()

        mevcut_tarihler = set()
        for row in self._ham_veriler:
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
        cmb.blockSignals(False)

        self._filtrele()

    def _filtrele(self):
        f_abd   = self._cmb_abd["combo"].currentText()
        f_birim = self._cmb_birim["combo"].currentText()
        f_tarih = self._cmb_tarih["combo"].currentText()

        filtered = []
        for row in self._ham_veriler:
            if "Tüm" not in f_abd   and row.get("ABD",   "") != f_abd:   continue
            if "Tüm" not in f_birim and row.get("Birim", "") != f_birim: continue
            if "Tüm" not in f_tarih and row.get("Tarih", "") != f_tarih: continue
            if self._rb_hurda.isChecked() and "Değil" not in row.get("Sonuc", ""):
                continue
            filtered.append(row)

        self._filtreli_veri = filtered
        self._model.set_data(filtered)
        self._lbl_sayi.setText(f"{len(filtered)} kayıt")

    # ═══════════════════════════════════════════
    #  RAPOR OLUŞTURMA
    # ═══════════════════════════════════════════

    def _on_rapor_olustur(self):
        if not self._filtreli_veri:
            QMessageBox.warning(self, "Uyarı", "Rapor oluşturmak için tabloda veri olmalıdır.")
            return

        mod = 1
        if self._rb_hurda.isChecked():
            mod = 2
        elif self._rb_kisi.isChecked():
            mod = 3

        ozet = (
            f"{self._cmb_abd['combo'].currentText()} — "
            f"{self._cmb_birim['combo'].currentText()}"
        )

        # Önceki rapor işlemi hâlâ sürüyorsa yeni başlatma
        if hasattr(self, "_worker") and self._worker.isRunning():
            QMessageBox.warning(self, "Uyarı", "Önceki rapor işlemi henüz tamamlanmadı.")
            return

        self._btn_olustur.setEnabled(False)
        self._btn_olustur.setText("İşleniyor…")
        self._pbar.setVisible(True)
        self._pbar.setRange(0, 0)

        self._worker = RaporOlusturucuThread(mod, self._filtreli_veri, ozet)
        self._worker.log_mesaji.connect(self._on_log)
        self._worker.islem_bitti.connect(self._on_rapor_bitti)
        self._worker.start()

    def _on_rapor_bitti(self):
        self._pbar.setVisible(False)
        self._btn_olustur.setEnabled(True)
        self._btn_olustur.setText("📄  PDF RAPOR OLUŞTUR")
        QMessageBox.information(
            self, "Tamamlandı",
            "Rapor işlemi tamamlandı. PDF oluşturulduysa Drive'a yüklenmiştir."
        )

    def _on_log(self, msg):
        logger.info(f"[RKERapor] {msg}")
        if "HATA" in msg or "❌" in msg:
            QMessageBox.warning(self, "Uyarı", msg)

    def _on_error(self, msg):
        self._pbar.setVisible(False)
        self._btn_olustur.setEnabled(True)
        self._btn_yenile.setText("⟳ Yenile  VERİLERİ YENİLE")
        logger.error(f"RKERapor hatası: {msg}")
        QMessageBox.critical(self, "Hata", msg)

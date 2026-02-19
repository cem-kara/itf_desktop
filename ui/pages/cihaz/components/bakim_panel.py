# -*- coding: utf-8 -*-
"""
BakimPanel — Cihaz 360° Merkez için Periyodik Bakım Sekmesi
────────────────────────────────────────────────────────────
• Seçili cihaza ait bakım planlarını tablo ile gösterir
• Üst bant: Acil / Yakın / Planlandı sayaçları
• Sağda inline form: yeni plan oluştur veya mevcut kaydı düzenle
• PeriyodikBakimPage'in mevcut thread / iş mantığı aynen kullanılır
"""
import time
import datetime
import os

from dateutil.relativedelta import relativedelta

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QProgressBar, QMessageBox,
    QComboBox, QDateEdit, QLineEdit, QTextEdit, QScrollArea, QFileDialog,
)
from PySide6.QtCore import Qt, Signal, QDate, QThread, QUrl
from PySide6.QtGui import QColor, QCursor, QDesktopServices

from core.logger import logger
from ui.theme_manager import ThemeManager
from ui.styles import DarkTheme
from ui.styles.icons import IconRenderer

C      = DarkTheme
STYLES = ThemeManager.get_all_component_styles()

BAKIM_PERIYOTLARI  = ["3 Ay", "6 Ay", "1 Yıl", "Tek Seferlik"]
DURUM_SECENEKLERI  = ["Planlandı", "Yapıldı", "Gecikti", "İptal"]
DURUM_RENK = {
    "Yapıldı":   C.STATUS_SUCCESS,
    "Gecikti":   C.STATUS_ERROR,
    "Planlandı": C.STATUS_WARNING,
    "İptal":     C.TEXT_MUTED,
}

SUTUNLAR = [
    ("Planid",          "Plan ID",          90),
    ("Cihazid",         "Cihaz",           110),
    ("PlanlananTarih",  "Planlanan Tarih", 110),
    ("BakimPeriyodu",   "Periyot",          90),
    ("BakimSirasi",     "Sıra",             70),
    ("Durum",           "Durum",            90),
    ("Teknisyen",       "Teknisyen",       130),
]


def _ay_ekle(kaynak: datetime.date, ay: int) -> datetime.date:
    return kaynak + relativedelta(months=ay)


class BakimKaydedici(QThread):
    islem_tamam = Signal()
    hata_olustu = Signal(str)

    def __init__(self, tip: str, veri, parent=None):
        super().__init__(parent)
        self._tip  = tip   # "INSERT" | "UPDATE"
        self._veri = veri  # list[dict] | (plan_id, dict)

    def run(self):
        from database.sqlite_manager import SQLiteManager
        db = None
        try:
            db = SQLiteManager()
            from core.di import get_registry
            repo = get_registry(db).get("Periyodik_Bakim")
            if self._tip == "INSERT":
                for row in self._veri:
                    repo.insert(row)
            else:
                plan_id, update = self._veri
                repo.update(plan_id, update)
            self.islem_tamam.emit()
        except Exception as e:
            self.hata_olustu.emit(str(e))
        finally:
            if db: db.close()


class BakimPanel(QWidget):
    """Cihaza özgü periyodik bakım yönetim paneli."""

    kayit_eklendi = Signal()

    def __init__(self, cihaz_id: str, db=None, parent=None):
        super().__init__(parent)
        self._cihaz_id        = cihaz_id
        self._db              = db
        self._all_data        = []
        self._cihaz_map       = {}   # cihaz_id → "Marka Model"
        self._secilen_plan_id = None
        self._secilen_dosya   = None
        self._mevcut_link     = None
        self._setup_ui()
        self.load_data()

    # ═══════════════════════════════════════════
    #  UI
    # ═══════════════════════════════════════════

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_toolbar())
        root.addWidget(self._build_ozet_band())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # Sol: tablo
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(16, 12, 16, 12)
        ll.setSpacing(6)
        ll.addWidget(self._build_table(), 1)

        self.tbl_progress = QProgressBar()
        self.tbl_progress.setFixedHeight(4)
        self.tbl_progress.setTextVisible(False)
        self.tbl_progress.setVisible(False)
        self.tbl_progress.setStyleSheet(STYLES.get("progress",""))
        ll.addWidget(self.tbl_progress)

        self.lbl_count = QLabel("0 kayıt")
        self.lbl_count.setStyleSheet(STYLES["footer_label"])
        ll.addWidget(self.lbl_count)
        body.addWidget(left, 1)

        # Sağ: form (gizli başlar)
        self.form_panel = self._build_form_panel()
        self.form_panel.setVisible(False)
        body.addWidget(self.form_panel)

        body_w = QWidget()
        body_w.setLayout(body)
        root.addWidget(body_w, 1)

    def _build_toolbar(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(40)
        frame.setStyleSheet(
            f"QFrame{{background:{C.BG_SECONDARY};border-bottom:1px solid {C.BORDER_PRIMARY};}}"
        )
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(8)

        self.lbl_cihaz = QLabel(f"Periyodik Bakım — {self._cihaz_id}" if self._cihaz_id else "Periyodik Bakım — Tüm Cihazlar")
        self.lbl_cihaz.setStyleSheet(f"color:{C.TEXT_MUTED}; font-size:12px; background:transparent;")
        lay.addWidget(self.lbl_cihaz); lay.addStretch()

        btn = QPushButton("⟳")
        btn.setStyleSheet(STYLES["refresh_btn"])
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.clicked.connect(self.load_data)
        lay.addWidget(btn)

        self.btn_yeni = QPushButton("+ Yeni Bakım Planı")
        self.btn_yeni.setStyleSheet(STYLES["action_btn"])
        self.btn_yeni.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_yeni.clicked.connect(self._toggle_form)
        lay.addWidget(self.btn_yeni)
        return frame

    def _build_ozet_band(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(36)
        frame.setStyleSheet(
            f"QFrame{{background:{C.BG_TERTIARY};border-bottom:1px solid {C.BORDER_PRIMARY};}}"
        )
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(20)

        self._sayac_lbls = {}
        for key, label, color in [
            ("acil",   "Acil",   C.STATUS_ERROR),
            ("yakin",  "Yakın",  C.STATUS_WARNING),
            ("normal", "Normal", C.STATUS_INFO),
        ]:
            lbl = QLabel(f"{label}: 0")
            lbl.setStyleSheet(f"color:{color}; font-size:12px; font-weight:600; background:transparent;")
            self._sayac_lbls[key] = lbl
            lay.addWidget(lbl)
        lay.addStretch()
        return frame

    def _build_table(self) -> QTableWidget:
        tbl = QTableWidget()
        tbl.setColumnCount(len(SUTUNLAR))
        tbl.setHorizontalHeaderLabels([s[1] for s in SUTUNLAR])
        tbl.verticalHeader().setVisible(False)
        tbl.setAlternatingRowColors(True)
        tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tbl.setStyleSheet(STYLES["table"])

        hdr = tbl.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        for i, (_, __, w) in enumerate(SUTUNLAR):
            if w < 120:
                hdr.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        tbl.cellDoubleClicked.connect(self._on_double_click)
        self.table = tbl
        return tbl

    def _build_form_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet(
            f"background:{C.BG_SECONDARY};border-left:1px solid {C.BORDER_PRIMARY};"
        )
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(0, 0, 0, 0)

        # Başlık
        hdr = QFrame()
        hdr.setFixedHeight(32)
        hdr.setStyleSheet(f"background:{C.BG_TERTIARY};border-bottom:1px solid {C.BORDER_PRIMARY};")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(12, 0, 12, 0)
        self.lbl_form_title = QLabel("YENİ BAKIM PLANI")
        self.lbl_form_title.setStyleSheet(
            f"color:{C.TEXT_MUTED}; font-size:11px; font-weight:600; background:transparent;")
        hl.addWidget(self.lbl_form_title); hl.addStretch()
        btn_sifirla = QPushButton("Temizle")
        btn_sifirla.setStyleSheet(STYLES["cancel_btn"])
        btn_sifirla.clicked.connect(self._formu_temizle)
        hl.addWidget(btn_sifirla)
        btn_kapat = QPushButton("✕")
        btn_kapat.setFixedSize(22, 22)
        btn_kapat.setStyleSheet("background:transparent; border:none; color:#888;")
        btn_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        btn_kapat.clicked.connect(self._hide_form)
        hl.addWidget(btn_kapat)
        pl.addWidget(hdr)

        # Scroll form içeriği
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(STYLES["scroll"])

        fw = QWidget(); fw.setStyleSheet("background:transparent;")
        fl = QVBoxLayout(fw)
        fl.setContentsMargins(14, 12, 14, 12)
        fl.setSpacing(10)

        self.inp = {}

        # Periyot + Planlanan tarih
        h1 = QHBoxLayout()
        self._col(h1, "Bakım Periyodu",   "BakimPeriyodu",  "combo_fixed", items=BAKIM_PERIYOTLARI)
        self._col(h1, "Planlanan Tarih",  "PlanlananTarih", "date")
        fl.addLayout(h1)

        # Durum + Yapılma tarihi
        h2 = QHBoxLayout()
        self._col(h2, "Durum",            "Durum",          "combo_fixed", items=DURUM_SECENEKLERI)
        self._col(h2, "Yapılma Tarihi",   "BakimTarihi",    "date")
        fl.addLayout(h2)

        self._row(fl, "Teknisyen",        "Teknisyen",      "input")
        self._row(fl, "Yapılan İşlemler", "YapilanIslemler","textarea")
        self._row(fl, "Açıklama / Not",   "Aciklama",       "textarea")

        # Rapor dosyası
        lbl_r = QLabel("Rapor Dosyası"); lbl_r.setStyleSheet(STYLES["label"])
        fl.addWidget(lbl_r)
        hr = QHBoxLayout()
        self.lbl_dosya = QLabel("Rapor Yok")
        self.lbl_dosya.setStyleSheet(f"color:{C.TEXT_DISABLED}; font-style:italic;")
        self.btn_dosya_ac = QPushButton("Aç")
        self.btn_dosya_ac.setStyleSheet(STYLES["action_btn"])
        self.btn_dosya_ac.setVisible(False)
        self.btn_dosya_ac.clicked.connect(self._dosyayi_ac)
        btn_yukle = QPushButton("Yükle")
        btn_yukle.setFixedSize(60, 26)
        btn_yukle.setStyleSheet(STYLES["file_btn"])
        btn_yukle.clicked.connect(self._dosya_sec)
        hr.addWidget(self.lbl_dosya); hr.addStretch()
        hr.addWidget(self.btn_dosya_ac); hr.addWidget(btn_yukle)
        fl.addLayout(hr)

        fl.addStretch()
        scroll.setWidget(fw)
        pl.addWidget(scroll, 1)

        # Progress + Kaydet
        self.form_progress = QProgressBar()
        self.form_progress.setFixedHeight(4)
        self.form_progress.setTextVisible(False)
        self.form_progress.setVisible(False)
        self.form_progress.setStyleSheet(STYLES.get("progress",""))
        pl.addWidget(self.form_progress)

        self.btn_kaydet = QPushButton("Planı Oluştur")
        self.btn_kaydet.setFixedHeight(36)
        self.btn_kaydet.setStyleSheet(STYLES["save_btn"])
        self.btn_kaydet.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kaydet.clicked.connect(self._kaydet)
        pl.addWidget(self.btn_kaydet)
        return panel

    # ── Form Yardımcıları ────────────────────────────────────

    def _row(self, parent_layout, label, key, tip, items=None):
        lbl = QLabel(label); lbl.setStyleSheet(STYLES["label"])
        parent_layout.addWidget(lbl)
        w = self._mk_inp(tip, items)
        parent_layout.addWidget(w)
        self.inp[key] = w

    def _col(self, hbox, label, key, tip, items=None):
        col = QWidget(); col.setStyleSheet("background:transparent;")
        cl  = QVBoxLayout(col); cl.setContentsMargins(0,0,0,0); cl.setSpacing(4)
        cl.addWidget(QLabel(label, styleSheet=STYLES["label"]))
        w = self._mk_inp(tip, items)
        cl.addWidget(w)
        hbox.addWidget(col)
        self.inp[key] = w

    def _mk_inp(self, tip, items=None):
        if tip == "input":
            w = QLineEdit(); w.setStyleSheet(STYLES["input"]); return w
        elif tip == "date":
            w = QDateEdit(QDate.currentDate()); w.setCalendarPopup(True)
            w.setDisplayFormat("yyyy-MM-dd"); w.setStyleSheet(STYLES["date"])
            ThemeManager.setup_calendar_popup(w); return w
        elif tip == "combo_fixed":
            w = QComboBox(); w.setStyleSheet(STYLES["combo"])
            if items: w.addItems(items)
            return w
        elif tip == "textarea":
            w = QTextEdit(); w.setStyleSheet(STYLES["input"]); w.setMaximumHeight(65); return w
        return QLabel()

    # ═══════════════════════════════════════════
    #  VERİ
    # ═══════════════════════════════════════════

    def set_cihaz(self, cihaz_id: str):
        """Filtre cihazını değiştir ve yenile. Boş string = tüm cihazlar."""
        self._cihaz_id = cihaz_id.strip()
        lbl = getattr(self, "lbl_cihaz", None)
        if lbl:
            lbl.setText(f"Periyodik Bakım — {self._cihaz_id}" if self._cihaz_id else "Periyodik Bakım — Tüm Cihazlar")
        self.load_data()

    def load_data(self):
        if not self._db:
            return
        try:
            from core.di import get_registry
            reg = get_registry(self._db)
            tum = reg.get("Periyodik_Bakim").get_all()
            cihaz_list = reg.get("Cihazlar").get_all()
            self._cihaz_map = {
                str(r.get("Cihazid","")): f"{r.get('Marka','')} {r.get('Model','')}".strip()
                for r in cihaz_list
            }
            if self._cihaz_id:
                self._all_data = [r for r in tum
                                  if str(r.get("Cihazid","")).strip() == self._cihaz_id]
            else:
                self._all_data = list(tum)
            self._all_data.sort(key=lambda x: x.get("PlanlananTarih",""), reverse=True)
            self._populate()
        except Exception as e:
            logger.error(f"BakimPanel veri yükleme: {e}")

    def _populate(self):
        self.table.setRowCount(0)
        self.table.setRowCount(len(self._all_data))
        bugun = datetime.date.today()
        acil  = yakin = normal = 0

        for r, row in enumerate(self._all_data):
            durum      = str(row.get("Durum",""))
            tarih_str  = str(row.get("PlanlananTarih",""))

            # Sayaç
            if durum == "Planlandı" and tarih_str:
                try:
                    t     = datetime.datetime.strptime(tarih_str, "%Y-%m-%d").date()
                    delta = (t - bugun).days
                    if delta < 0:   acil  += 1
                    elif delta <= 7: yakin += 1
                    else:           normal += 1
                except ValueError:
                    pass

            for c, (key, _, __) in enumerate(SUTUNLAR):
                if key == "Cihazid":
                    cid = str(row.get("Cihazid",""))
                    cihaz_map = getattr(self, "_cihaz_map", {})
                    ad = cihaz_map.get(cid, "")
                    val = f"{ad} ({cid})" if ad else cid
                else:
                    val = str(row.get(key,"") or "")
                item = QTableWidgetItem(val)

                if key == "Durum":
                    item.setForeground(QColor(DURUM_RENK.get(val, C.TEXT_SECONDARY)))
                elif key == "PlanlananTarih" and durum == "Planlandı" and val:
                    try:
                        t     = datetime.datetime.strptime(val, "%Y-%m-%d").date()
                        delta = (t - bugun).days
                        if delta < 0:   item.setForeground(QColor(C.STATUS_ERROR))
                        elif delta <= 7: item.setForeground(QColor(C.STATUS_WARNING))
                    except ValueError:
                        pass

                item.setData(Qt.UserRole, row)
                self.table.setItem(r, c, item)

        self._sayac_lbls["acil"].setText(f"Acil: {acil}")
        self._sayac_lbls["yakin"].setText(f"Yakın: {yakin}")
        self._sayac_lbls["normal"].setText(f"Normal: {normal}")
        self.lbl_count.setText(f"{len(self._all_data)} kayıt")

    # ═══════════════════════════════════════════
    #  AKSİYONLAR
    # ═══════════════════════════════════════════

    def _toggle_form(self):
        if self.form_panel.isVisible():
            self._hide_form()
        else:
            self._formu_temizle()
            self.form_panel.setVisible(True)

    def _hide_form(self):
        self.form_panel.setVisible(False)

    def _on_double_click(self, row: int, _col: int):
        item = self.table.item(row, 0)
        if not item: return
        data = item.data(Qt.UserRole)
        if not data: return

        self._secilen_plan_id = str(data.get("Planid",""))
        self.lbl_form_title.setText("BAKIM GÜNCELLE")
        self.btn_kaydet.setText("Değişiklikleri Kaydet")
        self.form_panel.setVisible(True)

        for key, w in self.inp.items():
            val = data.get(key,"") or ""
            if isinstance(w, QLineEdit):   w.setText(str(val))
            elif isinstance(w, QComboBox): w.setCurrentText(str(val))
            elif isinstance(w, QDateEdit):
                d = QDate.fromString(str(val), "yyyy-MM-dd")
                if d.isValid(): w.setDate(d)
            elif isinstance(w, QTextEdit): w.setPlainText(str(val))

        link = str(data.get("Rapor",""))
        if link.startswith("http"):
            self._mevcut_link = link
            self.btn_dosya_ac.setVisible(True)
            self.lbl_dosya.setText("✅ Rapor Mevcut")
            self.lbl_dosya.setStyleSheet(f"color:{C.STATUS_SUCCESS}; font-weight:bold;")
        else:
            self._mevcut_link = None
            self.btn_dosya_ac.setVisible(False)
            self.lbl_dosya.setText("Rapor Yok")
            self.lbl_dosya.setStyleSheet(f"color:{C.TEXT_DISABLED}; font-style:italic;")

    def _dosya_sec(self):
        yol, _ = QFileDialog.getOpenFileName(
            self, "Rapor Seç", "", "PDF ve Resim (*.pdf *.jpg *.png)")
        if yol:
            self._secilen_dosya = yol
            self.lbl_dosya.setText(os.path.basename(yol))
            self.lbl_dosya.setStyleSheet(f"color:{C.STATUS_WARNING}; font-weight:bold;")

    def _dosyayi_ac(self):
        if self._mevcut_link:
            QDesktopServices.openUrl(QUrl(self._mevcut_link))

    def _formu_temizle(self):
        self._secilen_plan_id = None
        self._secilen_dosya   = None
        self._mevcut_link     = None
        self.lbl_form_title.setText("YENİ BAKIM PLANI")
        self.btn_kaydet.setText("Planı Oluştur")

        for key, w in self.inp.items():
            if isinstance(w, QLineEdit):   w.clear()
            elif isinstance(w, QComboBox): w.setCurrentIndex(0)
            elif isinstance(w, QDateEdit): w.setDate(QDate.currentDate())
            elif isinstance(w, QTextEdit): w.clear()

        self.lbl_dosya.setText("Rapor Yok")
        self.lbl_dosya.setStyleSheet(f"color:{C.TEXT_DISABLED}; font-style:italic;")
        self.btn_dosya_ac.setVisible(False)

    def _kaydet(self):
        periyot    = self.inp["BakimPeriyodu"].currentText()
        tarih      = self.inp["PlanlananTarih"].date().toPython()
        tarih_str  = tarih.strftime("%Y-%m-%d")
        durum      = self.inp["Durum"].currentText()
        yapilan    = self.inp["YapilanIslemler"].toPlainText().strip()
        aciklama   = self.inp["Aciklama"].toPlainText().strip()
        teknisyen  = self.inp["Teknisyen"].text().strip()
        bakim_t    = (self.inp["BakimTarihi"].date().toString("yyyy-MM-dd")
                      if durum == "Yapıldı" else "")
        dosya_link = self._mevcut_link or "-"

        self.btn_kaydet.setEnabled(False)
        self.form_progress.setVisible(True)
        self.form_progress.setRange(0, 0)

        if self._secilen_plan_id:
            # Güncelle
            update = {
                "Cihazid":         self._cihaz_id,
                "BakimPeriyodu":   periyot,
                "PlanlananTarih":  tarih_str,
                "Durum":           durum,
                "BakimTarihi":     bakim_t,
                "YapilanIslemler": yapilan,
                "Aciklama":        aciklama,
                "Teknisyen":       teknisyen,
                "Rapor":           dosya_link,
            }
            veri = (self._secilen_plan_id, update)
            tip  = "UPDATE"
        else:
            # Yeni plan(lar) — periyodik
            ay_adim  = 3 if "3 Ay" in periyot else 6 if "6 Ay" in periyot else 12 if "1 Yıl" in periyot else 0
            tekrar   = 4 if ay_adim == 3 else 2 if ay_adim == 6 else 1 if ay_adim == 12 else 1
            base_id  = int(time.time())
            satirlar = []
            for i in range(tekrar):
                yeni_tarih = _ay_ekle(tarih, i * ay_adim)
                ilk        = (i == 0)
                satirlar.append({
                    "Planid":          f"P-{base_id + i}",
                    "Cihazid":         self._cihaz_id,
                    "BakimPeriyodu":   periyot,
                    "BakimSirasi":     f"{i+1}. Bakım",
                    "PlanlananTarih":  yeni_tarih.strftime("%Y-%m-%d"),
                    "Bakim":           "Periyodik",
                    "Durum":           durum if ilk else "Planlandı",
                    "BakimTarihi":     bakim_t if ilk else "",
                    "BakimTipi":       "Periyodik",
                    "YapilanIslemler": yapilan   if ilk else "",
                    "Aciklama":        aciklama  if ilk else "",
                    "Teknisyen":       teknisyen if ilk else "",
                    "Rapor":           dosya_link if ilk else "",
                })
            veri = satirlar
            tip  = "INSERT"

        self._saver = BakimKaydedici(tip, veri, self)
        self._saver.islem_tamam.connect(self._kayit_tamam)
        self._saver.hata_olustu.connect(self._kayit_hata)
        self._saver.start()

    def _kayit_tamam(self):
        self.form_progress.setVisible(False)
        self.btn_kaydet.setEnabled(True)
        self._formu_temizle()
        self._hide_form()
        self.load_data()
        self.kayit_eklendi.emit()

    def _kayit_hata(self, msg: str):
        self.form_progress.setVisible(False)
        self.btn_kaydet.setEnabled(True)
        QMessageBox.critical(self, "Hata", f"Kayıt başarısız:\n{msg}")

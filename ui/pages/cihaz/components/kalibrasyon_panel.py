# -*- coding: utf-8 -*-
"""
KalibrasyonPanel — Cihaz 360° Merkez için Kalibrasyon Sekmesi
───────────────────────────────────────────────────────────────
• Seçili cihaza ait kalibrasyon kayıtlarını gösterir
• Üst durum bandı: Son kalibrasyon tarihi, sonraki tarih, kalan gün
• Yeni kalibrasyon formu sağda inline (KalibrasyonTakipPage'den form kısmı)
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox,
    QComboBox, QDateEdit, QLineEdit, QTextEdit, QProgressBar, QFileDialog,
    QGroupBox, QScrollArea,
)
from PySide6.QtCore import Qt, Signal, QDate, QThread, QUrl
from PySide6.QtGui import QColor, QCursor, QDesktopServices
from datetime import date

from core.logger import logger
from ui.theme_manager import ThemeManager
from ui.styles import DarkTheme
from ui.styles.icons import IconRenderer

C      = DarkTheme
STYLES = ThemeManager.get_all_component_styles()

SUTUNLAR = [
    ("Kalibrasyon_ID",   "ID",               90),
    ("Cihazid",          "Cihaz",           110),
    ("YapilanTarih",     "Yapılan Tarih",   110),
    ("GecerlilikBitis",  "Geçerlilik Bitiş",110),
    ("KalibrasyonFirmasi","Firma",          150),
    ("Sertifika",        "Sertifika",       120),
    ("Sonuc",            "Sonuç",           100),
    ("Aciklama",         "Açıklama",        200),
]


class KalibrasyonKaydedici(QThread):
    islem_tamam = Signal()
    hata_olustu = Signal(str)

    def __init__(self, veri: dict, mod="yeni", kayit_id=None, parent=None):
        super().__init__(parent)
        self._veri     = veri
        self._mod      = mod
        self._kayit_id = kayit_id

    def run(self):
        from database.sqlite_manager import SQLiteManager
        db = None
        try:
            db = SQLiteManager()
            from core.di import get_registry
            repo = get_registry(db).get("Kalibrasyon")
            if self._mod == "yeni":
                repo.insert(self._veri)
            else:
                repo.update(self._kayit_id, self._veri)
            self.islem_tamam.emit()
        except Exception as e:
            self.hata_olustu.emit(str(e))
        finally:
            if db: db.close()


class KalibrasyonPanel(QWidget):
    """Cihaza özgü kalibrasyon paneli."""

    kayit_eklendi = Signal()

    def __init__(self, cihaz_id: str, db=None, parent=None):
        super().__init__(parent)
        self._cihaz_id    = cihaz_id
        self._db          = db
        self._all_data    = []
        self._cihaz_map   = {}   # cihaz_id → "Marka Model"
        self._firmalar    = []
        self._edit_id     = None
        self._secilen_dosya = None
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
        root.addWidget(self._build_durum_bandi())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # Sol: tablo
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(16, 12, 16, 12)
        ll.setSpacing(6)
        ll.addWidget(self._build_table(), 1)

        self.progress = QProgressBar()
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        self.progress.setStyleSheet(STYLES.get("progress",""))
        ll.addWidget(self.progress)
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

        self.lbl_cihaz = QLabel(f"Kalibrasyon Kayıtları — {self._cihaz_id}" if self._cihaz_id else "Kalibrasyon — Tüm Cihazlar")
        self.lbl_cihaz.setStyleSheet(f"color:{C.TEXT_MUTED}; font-size:12px; background:transparent;")
        lay.addWidget(self.lbl_cihaz); lay.addStretch()

        btn = QPushButton("⟳")
        btn.setFixedSize(30, 26)
        btn.setStyleSheet(STYLES["refresh_btn"])
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.clicked.connect(self.load_data)
        lay.addWidget(btn)

        self.btn_yeni = QPushButton("+ Yeni Kalibrasyon")
        self.btn_yeni.setFixedHeight(26)
        self.btn_yeni.setStyleSheet(STYLES["action_btn"])
        self.btn_yeni.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_yeni.clicked.connect(self._toggle_form)
        lay.addWidget(self.btn_yeni)
        return frame

    def _build_durum_bandi(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(42)
        frame.setStyleSheet(
            f"QFrame{{background:{C.BG_TERTIARY};border-bottom:1px solid {C.BORDER_PRIMARY};}}"
        )
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(24)

        self.lbl_son     = QLabel("Son Kalibrasyon: —")
        self.lbl_bitis   = QLabel("Geçerlilik Bitiş: —")
        self.lbl_kalan   = QLabel("Kalan: —")
        for l in (self.lbl_son, self.lbl_bitis, self.lbl_kalan):
            l.setStyleSheet(f"color:{C.TEXT_SECONDARY}; font-size:12px; background:transparent;")
            lay.addWidget(l)
        lay.addStretch()

        self.lbl_toplam = QLabel("0 kayıt")
        self.lbl_toplam.setStyleSheet(STYLES["footer_label"])
        lay.addWidget(self.lbl_toplam)
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
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)

        tbl.doubleClicked.connect(self._on_double_click)
        self.table = tbl
        return tbl

    def _build_form_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet(f"background:{C.BG_SECONDARY};border-left:1px solid {C.BORDER_PRIMARY};")

        pl = QVBoxLayout(panel)
        pl.setContentsMargins(0, 0, 0, 0)

        # Başlık
        hdr = QFrame()
        hdr.setFixedHeight(32)
        hdr.setStyleSheet(f"background:{C.BG_TERTIARY};border-bottom:1px solid {C.BORDER_PRIMARY};")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(12, 0, 12, 0)
        self.lbl_form_title = QLabel("YENİ KALİBRASYON")
        self.lbl_form_title.setStyleSheet(
            f"color:{C.TEXT_MUTED}; font-size:11px; font-weight:600; background:transparent;")
        hl.addWidget(self.lbl_form_title); hl.addStretch()
        btn_temizle = QPushButton("Temizle")
        btn_temizle.setFixedHeight(22)
        btn_temizle.setStyleSheet(STYLES["cancel_btn"])
        btn_temizle.clicked.connect(self._formu_temizle)
        hl.addWidget(btn_temizle)
        btn_kapat = QPushButton("✕")
        btn_kapat.setFixedSize(22, 22)
        btn_kapat.setStyleSheet("background:transparent; border:none; color:#888;")
        btn_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        btn_kapat.clicked.connect(self._hide_form)
        hl.addWidget(btn_kapat)
        pl.addWidget(hdr)

        # Form içeriği (scroll)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(STYLES["scroll"])

        fw = QWidget(); fw.setStyleSheet("background:transparent;")
        fl = QVBoxLayout(fw)
        fl.setContentsMargins(14, 12, 14, 12)
        fl.setSpacing(10)

        self.inp = {}
        self._row(fl, "Cihaz ID", "Cihazid", "input", readonly=True)
        self.inp["Cihazid"].setText(self._cihaz_id)

        h1 = QHBoxLayout()
        self._col(h1, "Yapılan Tarih",      "YapilanTarih",     "date")
        self._col(h1, "Geçerlilik Bitiş",   "GecerlilikBitis",  "date")
        fl.addLayout(h1)

        self._row(fl, "Kalibrasyon Firması", "KalibrasyonFirmasi", "combo")
        self._row(fl, "Sertifika No",        "Sertifika",         "input")

        h2 = QHBoxLayout()
        self._col(h2, "Sonuç", "Sonuc", "combo_fixed", items=["Uygun","Uygun Değil","Koşullu Uygun"])
        fl.addLayout(h2)

        self._row(fl, "Açıklama", "Aciklama", "textarea")

        # Sertifika dosyası
        lbl_dos = QLabel("Sertifika Dosyası")
        lbl_dos.setStyleSheet(STYLES["label"])
        fl.addWidget(lbl_dos)
        dos_row = QHBoxLayout()
        self.lbl_dosya = QLabel("Dosya seçilmedi")
        self.lbl_dosya.setStyleSheet(f"color:{C.TEXT_DISABLED}; font-style:italic;")
        btn_dos = QPushButton("Seç")
        btn_dos.setFixedHeight(26)
        btn_dos.setStyleSheet(STYLES["file_btn"])
        btn_dos.clicked.connect(self._dosya_sec)
        dos_row.addWidget(self.lbl_dosya, 1)
        dos_row.addWidget(btn_dos)
        fl.addLayout(dos_row)

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

        self.btn_kaydet = QPushButton("Kaydı Oluştur")
        self.btn_kaydet.setFixedHeight(36)
        self.btn_kaydet.setStyleSheet(STYLES["save_btn"])
        self.btn_kaydet.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kaydet.clicked.connect(self._kaydet)
        pl.addWidget(self.btn_kaydet)

        return panel

    # ── Form Yardımcıları ────────────────────────────────────

    def _row(self, parent_layout, label, key, tip, readonly=False, items=None):
        lbl = QLabel(label); lbl.setStyleSheet(STYLES["label"])
        parent_layout.addWidget(lbl)
        w = self._mk_inp(tip, key, readonly=readonly, items=items)
        parent_layout.addWidget(w)
        self.inp[key] = w

    def _col(self, hbox, label, key, tip, readonly=False, items=None):
        col = QWidget(); col.setStyleSheet("background:transparent;")
        cl  = QVBoxLayout(col); cl.setContentsMargins(0,0,0,0); cl.setSpacing(4)
        cl.addWidget(QLabel(label, styleSheet=STYLES["label"]))
        w = self._mk_inp(tip, key, readonly=readonly, items=items)
        cl.addWidget(w)
        hbox.addWidget(col)
        self.inp[key] = w

    def _mk_inp(self, tip, key, readonly=False, items=None):
        if tip == "input":
            w = QLineEdit(); w.setStyleSheet(STYLES["input"]); w.setReadOnly(readonly); return w
        elif tip == "date":
            w = QDateEdit(QDate.currentDate())
            w.setCalendarPopup(True); w.setDisplayFormat("yyyy-MM-dd")
            w.setStyleSheet(STYLES["date"]); ThemeManager.setup_calendar_popup(w); return w
        elif tip in ("combo", "combo_fixed"):
            w = QComboBox(); w.setStyleSheet(STYLES["combo"])
            if tip == "combo_fixed" and items:
                w.addItems(items)
            return w
        elif tip == "textarea":
            w = QTextEdit(); w.setStyleSheet(STYLES["input"]); w.setMaximumHeight(70); return w
        return QLabel()

    # ═══════════════════════════════════════════
    #  VERİ
    # ═══════════════════════════════════════════

    def set_cihaz(self, cihaz_id: str):
        """Filtre cihazını değiştir ve yenile. Boş string = tüm cihazlar."""
        self._cihaz_id = cihaz_id.strip()
        lbl = getattr(self, "lbl_cihaz", None)
        if lbl:
            lbl.setText(f"Kalibrasyon — {self._cihaz_id}" if self._cihaz_id else "Kalibrasyon — Tüm Cihazlar")
        if "Cihazid" in self.inp:
            self.inp["Cihazid"].setText(self._cihaz_id)
        self.load_data()

    def load_data(self):
        if not self._db:
            return
        try:
            from core.di import get_registry
            reg  = get_registry(self._db)
            tum  = reg.get("Kalibrasyon").get_all()
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
            self._all_data.sort(key=lambda x: x.get("YapilanTarih",""), reverse=True)

            # Firmalar
            sabitler = reg.get("Sabitler").get_all()
            self._firmalar = [s.get("MenuEleman","") for s in sabitler if s.get("Kod") == "firmalar"]
            cmb = self.inp.get("KalibrasyonFirmasi")
            if isinstance(cmb, QComboBox):
                cur = cmb.currentText()
                cmb.blockSignals(True); cmb.clear(); cmb.addItem("")
                cmb.addItems(sorted(self._firmalar)); cmb.setCurrentText(cur); cmb.blockSignals(False)

            self._populate()
        except Exception as e:
            logger.error(f"KalibrasyonPanel veri yükleme: {e}")

    def _populate(self):
        self.table.setRowCount(0)
        self.table.setRowCount(len(self._all_data))
        bugun = date.today()

        for r, row in enumerate(self._all_data):
            for c, (key, _, __) in enumerate(SUTUNLAR):
                if key == "Cihazid":
                    cid = str(row.get("Cihazid",""))
                    cihaz_map = getattr(self, "_cihaz_map", {})
                    ad = cihaz_map.get(cid, "")
                    val = f"{ad} ({cid})" if ad else cid
                else:
                    val = str(row.get(key,"") or "")
                item = QTableWidgetItem(val)
                if key == "Sertifika" and val.startswith("http"):
                    item.setForeground(QColor(C.INPUT_BORDER_FOCUS))
                    item.setToolTip("Çift tıkla: sertifikayı aç")
                elif key == "GecerlilikBitis" and val:
                    try:
                        from core.date_utils import parse_date as pd
                        son = pd(val)
                        if son:
                            delta = (son - bugun).days
                            item.setForeground(QColor(
                                C.STATUS_ERROR if delta < 0 else
                                C.STATUS_WARNING if delta <= 30 else
                                C.STATUS_SUCCESS
                            ))
                    except Exception:
                        pass
                item.setData(Qt.UserRole, row)
                self.table.setItem(r, c, item)

        # Durum bandı
        if self._all_data:
            son = self._all_data[0]
            self.lbl_son.setText(f"Son: {son.get('YapilanTarih','—')}")
            bitis = son.get("GecerlilikBitis","")
            self.lbl_bitis.setText(f"Bitiş: {bitis or '—'}")
            if bitis:
                try:
                    from core.date_utils import parse_date as pd
                    s = pd(bitis)
                    if s:
                        delta = (s - bugun).days
                        clr   = C.STATUS_ERROR if delta < 0 else C.STATUS_WARNING if delta <= 30 else C.STATUS_SUCCESS
                        self.lbl_kalan.setText(f"{'Geçti' if delta < 0 else 'Kalan'}: {abs(delta)} gün")
                        self.lbl_kalan.setStyleSheet(f"color:{clr}; font-size:12px; font-weight:600; background:transparent;")
                except Exception:
                    pass
        self.lbl_toplam.setText(f"{len(self._all_data)} kayıt")

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

    def _on_double_click(self, index):
        item = self.table.item(index.row(), 0)
        if not item: return
        data = item.data(Qt.UserRole)
        if not data: return

        # Sertifika sütununa çift tıkladıysa linki aç
        col_key = SUTUNLAR[index.column()][0]
        if col_key == "Sertifika":
            link = str(data.get("Sertifika",""))
            if link.startswith("http"):
                QDesktopServices.openUrl(QUrl(link)); return

        # Formu düzenleme modunda aç
        self._edit_id = str(data.get("Kalibrasyon_ID","") or "")
        self.lbl_form_title.setText("KALİBRASYON GÜNCELLE")
        self.form_panel.setVisible(True)
        for key, widget in self.inp.items():
            val = data.get(key, "") or ""
            if isinstance(widget, QLineEdit): widget.setText(str(val))
            elif isinstance(widget, QComboBox): widget.setCurrentText(str(val))
            elif isinstance(widget, QDateEdit):
                d = QDate.fromString(str(val), "yyyy-MM-dd")
                if d.isValid(): widget.setDate(d)
            elif isinstance(widget, QTextEdit): widget.setPlainText(str(val))
        self.btn_kaydet.setText("Güncelle")

    def _dosya_sec(self):
        yol, _ = QFileDialog.getOpenFileName(self, "Sertifika Seç", "", "PDF ve Resim (*.pdf *.jpg *.png)")
        if yol:
            self._secilen_dosya = yol
            import os
            self.lbl_dosya.setText(os.path.basename(yol))
            self.lbl_dosya.setStyleSheet(f"color:{C.STATUS_WARNING}; font-weight:bold;")

    def _formu_temizle(self):
        self._edit_id = None
        self._secilen_dosya = None
        self.lbl_form_title.setText("YENİ KALİBRASYON")
        self.btn_kaydet.setText("Kaydı Oluştur")
        for key, w in self.inp.items():
            if isinstance(w, QLineEdit): w.setText("" if key != "Cihazid" else self._cihaz_id)
            elif isinstance(w, QComboBox): w.setCurrentIndex(0)
            elif isinstance(w, QDateEdit): w.setDate(QDate.currentDate())
            elif isinstance(w, QTextEdit): w.clear()
        self.lbl_dosya.setText("Dosya seçilmedi")
        self.lbl_dosya.setStyleSheet(f"color:{C.TEXT_DISABLED}; font-style:italic;")

    def _kaydet(self):
        veri = {"Cihazid": self._cihaz_id}
        for key, w in self.inp.items():
            if key == "Cihazid": continue
            if isinstance(w, QLineEdit):   veri[key] = w.text().strip()
            elif isinstance(w, QComboBox): veri[key] = w.currentText().strip()
            elif isinstance(w, QDateEdit): veri[key] = w.date().toString("yyyy-MM-dd")
            elif isinstance(w, QTextEdit): veri[key] = w.toPlainText().strip()

        if not veri.get("YapilanTarih"):
            QMessageBox.warning(self, "Eksik", "Yapılan tarih zorunludur."); return

        self.btn_kaydet.setEnabled(False)
        self.form_progress.setVisible(True); self.form_progress.setRange(0, 0)

        import time
        if not self._edit_id:
            veri["Kalibrasyon_ID"] = f"KAL-{int(time.time())}"

        self._saver = KalibrasyonKaydedici(
            veri, "guncelle" if self._edit_id else "yeni", self._edit_id, self)
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

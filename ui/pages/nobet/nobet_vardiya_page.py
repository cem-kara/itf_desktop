"""
nobet_vardiya_page.py — Birim Vardiya Grubu & Vardiya Yönetimi

Yerleşim:
  Sol  — Birim listesi (NB_Birim)
  Orta — Seçili birimin vardiya grupları
  Sağ  — Seçili grubun vardiyaları
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QDialog, QLineEdit, QComboBox, QSpinBox, QCheckBox,
    QMessageBox, QHeaderView, QScrollArea, QSplitter,
    QAbstractItemView,
)

from core.logger import logger


# ══════════════════════════════════════════════════════════════════
#  DİALOGLAR
# ══════════════════════════════════════════════════════════════════

class _GrupDialog(QDialog):
    """Vardiya grubu ekle / düzenle."""

    TURLER = ["zorunlu", "ihtiyari"]

    def __init__(self, kayit: dict = None, parent=None):
        super().__init__(parent)
        self._kayit = kayit or {}
        self.setWindowTitle("Yeni Grup" if not kayit else "Grubu Düzenle")
        self.setModal(True)
        self.setMinimumWidth(380)
        self.setProperty("bg-role", "page")
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 20, 20, 20)

        def _row(lbl, widget):
            h = QHBoxLayout()
            l = QLabel(lbl)
            l.setFixedWidth(100)
            h.addWidget(l)
            h.addWidget(widget)
            lay.addLayout(h)
            return widget

        self._inp_adi = _row("Grup Adı *",
            QLineEdit(self._kayit.get("GrupAdi", "")))
        self._inp_adi.setPlaceholderText("ör: 24 Saat Nöbet")

        self._cmb_tur = QComboBox()
        for t in self.TURLER:
            self._cmb_tur.addItem(t)
        idx = self._cmb_tur.findText(self._kayit.get("GrupTuru", "zorunlu"))
        if idx >= 0:
            self._cmb_tur.setCurrentIndex(idx)
        _row("Tür", self._cmb_tur)

        self._spn_sira = QSpinBox()
        self._spn_sira.setRange(1, 99)
        self._spn_sira.setValue(int(self._kayit.get("Sira", 1)))
        _row("Sıra", self._spn_sira)

        lay.addSpacing(8)
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        iptal = QPushButton("İptal")
        iptal.setProperty("style-role", "secondary")
        iptal.setFixedWidth(80)
        iptal.clicked.connect(self.reject)
        btn_row.addWidget(iptal)

        kaydet = QPushButton("Kaydet")
        kaydet.setProperty("style-role", "action")
        kaydet.setFixedWidth(80)
        kaydet.clicked.connect(self._kaydet)
        btn_row.addWidget(kaydet)
        lay.addLayout(btn_row)

    def _kaydet(self):
        if not self._inp_adi.text().strip():
            QMessageBox.warning(self, "Uyarı", "Grup adı boş olamaz.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "GrupAdi":  self._inp_adi.text().strip(),
            "GrupTuru": self._cmb_tur.currentText(),
            "Sira":     self._spn_sira.value(),
        }


class _VardiyaDialog(QDialog):
    """Vardiya ekle / düzenle."""

    ROLLER = ["ana", "yardimci"]

    def __init__(self, kayit: dict = None, parent=None):
        super().__init__(parent)
        self._kayit = kayit or {}
        self.setWindowTitle("Yeni Vardiya" if not kayit else "Vardiya Düzenle")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setProperty("bg-role", "page")
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 20, 20, 20)

        def _row(lbl, widget):
            h = QHBoxLayout()
            l = QLabel(lbl)
            l.setFixedWidth(110)
            h.addWidget(l)
            h.addWidget(widget)
            lay.addLayout(h)
            return widget

        self._inp_adi = _row("Vardiya Adı *",
            QLineEdit(self._kayit.get("VardiyaAdi", "")))
        self._inp_adi.setPlaceholderText("ör: Gündüz, Gece")

        self._inp_bas = _row("Başlangıç *",
            QLineEdit(self._kayit.get("BasSaat", "08:00")))
        self._inp_bas.setPlaceholderText("08:00")
        self._inp_bas.setInputMask("99:99")

        self._inp_bit = _row("Bitiş *",
            QLineEdit(self._kayit.get("BitSaat", "20:00")))
        self._inp_bit.setPlaceholderText("20:00")
        self._inp_bit.setInputMask("99:99")

        self._lbl_sure = QLabel("—")
        self._lbl_sure.setProperty("color-role", "muted")
        _row("Süre (otomatik)", self._lbl_sure)
        self._inp_bas.textChanged.connect(self._sure_guncelle)
        self._inp_bit.textChanged.connect(self._sure_guncelle)

        self._cmb_rol = QComboBox()
        for r in self.ROLLER:
            self._cmb_rol.addItem(r)
        idx = self._cmb_rol.findText(self._kayit.get("Rol", "ana"))
        if idx >= 0:
            self._cmb_rol.setCurrentIndex(idx)
        _row("Rol", self._cmb_rol)

        self._spn_min = QSpinBox()
        self._spn_min.setRange(0, 99)
        self._spn_min.setValue(int(self._kayit.get("MinPersonel", 1)))
        _row("Min. Personel", self._spn_min)

        self._spn_sira = QSpinBox()
        self._spn_sira.setRange(1, 99)
        self._spn_sira.setValue(int(self._kayit.get("Sira", 1)))
        _row("Sıra", self._spn_sira)

        # Rol açıklaması
        acik = QLabel(
            "ana: Algoritma bu vardiyayı doldurur.\n"
            "yardimci: Sadece manuel veya slot bölününce.")
        acik.setProperty("color-role", "muted")
        acik.setStyleSheet("font-size: 11px;")
        lay.addWidget(acik)

        lay.addSpacing(6)
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        iptal = QPushButton("İptal")
        iptal.setProperty("style-role", "secondary")
        iptal.setFixedWidth(80)
        iptal.clicked.connect(self.reject)
        btn_row.addWidget(iptal)

        kaydet = QPushButton("Kaydet")
        kaydet.setProperty("style-role", "action")
        kaydet.setFixedWidth(80)
        kaydet.clicked.connect(self._kaydet)
        btn_row.addWidget(kaydet)
        lay.addLayout(btn_row)

        self._sure_guncelle()

    def _sure_hesapla(self) -> int:
        try:
            bh, bm = map(int, self._inp_bas.text().split(":"))
            eh, em = map(int, self._inp_bit.text().split(":"))
            dk = (eh * 60 + em) - (bh * 60 + bm)
            if dk <= 0:
                dk += 24 * 60
            return dk
        except Exception:
            return 0

    def _sure_guncelle(self):
        dk = self._sure_hesapla()
        if dk > 0:
            self._lbl_sure.setText(f"{dk // 60}s {dk % 60:02d}dk ({dk} dk)")
        else:
            self._lbl_sure.setText("—")

    def _kaydet(self):
        adi = self._inp_adi.text().strip()
        if not adi:
            QMessageBox.warning(self, "Uyarı", "Vardiya adı boş olamaz.")
            return
        if self._sure_hesapla() <= 0:
            QMessageBox.warning(self, "Uyarı",
                "Geçersiz saat aralığı. Başlangıç ve bitiş saatini kontrol edin.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "VardiyaAdi": self._inp_adi.text().strip(),
            "BasSaat":    self._inp_bas.text(),
            "BitSaat":    self._inp_bit.text(),
            "Rol":        self._cmb_rol.currentText(),
            "MinPersonel": self._spn_min.value(),
            "Sira":       self._spn_sira.value(),
        }


class _PersonelAtaDialog(QDialog):
    """Birime personel atama formu."""

    ROLLER = ["teknisyen", "uzman", "sorumlu", "asistan"]

    def __init__(self, db=None, birim_id: str = "", parent=None):
        super().__init__(parent)
        self._db       = db
        self._birim_id = birim_id
        self.setWindowTitle("Personel Ata")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setProperty("bg-role", "page")
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 20, 20, 20)

        def _row(lbl, widget):
            h = QHBoxLayout()
            l = QLabel(lbl)
            l.setFixedWidth(110)
            h.addWidget(l)
            h.addWidget(widget)
            lay.addLayout(h)
            return widget

        # Personel seçimi
        self._cmb_personel = QComboBox()
        self._cmb_personel.setMinimumWidth(220)
        _row("Personel *", self._cmb_personel)
        self._personelleri_yukle()

        # Rol
        self._cmb_rol = QComboBox()
        for r in self.ROLLER:
            self._cmb_rol.addItem(r)
        _row("Rol", self._cmb_rol)

        # Ana birim mi?
        self._chk_ana = QCheckBox("Ana birim (birincil görev yeri)")
        self._chk_ana.setChecked(True)
        lay.addWidget(self._chk_ana)

        # Görev başlangıç
        from PySide6.QtWidgets import QDateEdit
        from PySide6.QtCore import QDate
        self._inp_bas = QDateEdit()
        self._inp_bas.setDate(QDate.currentDate())
        self._inp_bas.setDisplayFormat("dd.MM.yyyy")
        self._inp_bas.setCalendarPopup(True)
        _row("Görev Başl.", self._inp_bas)

        # Notlar
        self._inp_notlar = QLineEdit()
        self._inp_notlar.setPlaceholderText("İsteğe bağlı")
        _row("Notlar", self._inp_notlar)

        lay.addSpacing(8)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        iptal = QPushButton("İptal")
        iptal.setProperty("style-role", "secondary")
        iptal.setFixedWidth(80)
        iptal.clicked.connect(self.reject)
        btn_row.addWidget(iptal)
        kaydet = QPushButton("Ata")
        kaydet.setProperty("style-role", "action")
        kaydet.setFixedWidth(80)
        kaydet.clicked.connect(self._kaydet)
        btn_row.addWidget(kaydet)
        lay.addLayout(btn_row)

    def _personelleri_yukle(self):
        """Atanmamış personeli listele."""
        try:
            from core.di import get_nb_birim_personel_service, get_registry
            svc     = get_nb_birim_personel_service(self._db)
            atanmis = set(svc.personel_pid_listesi(self._birim_id))
            reg     = get_registry(self._db)
            p_rows  = reg.get("Personel").get_all() or []
            for p in sorted(p_rows, key=lambda x: x.get("AdSoyad","")):
                pid = str(p["KimlikNo"])
                if pid in atanmis:
                    continue
                ad  = p.get("AdSoyad","")
                if not ad:
                    continue
                self._cmb_personel.addItem(ad, userData=pid)
        except Exception as e:
            logger.error(f"Personel listesi: {e}")

    def _kaydet(self):
        if self._cmb_personel.currentIndex() < 0:
            QMessageBox.warning(self, "Uyarı", "Personel seçin.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "PersonelID":     self._cmb_personel.currentData(),
            "Rol":            self._cmb_rol.currentText(),
            "AnabirimMi":     self._chk_ana.isChecked(),
            "GorevBaslangic": self._inp_bas.date().toString("yyyy-MM-dd"),
            "Notlar":         self._inp_notlar.text().strip(),
        }


class _AtamaDuzenleDialog(QDialog):
    """Mevcut atama kaydını düzenleme."""

    ROLLER = ["teknisyen", "uzman", "sorumlu", "asistan"]

    def __init__(self, kayit: dict = None, parent=None):
        super().__init__(parent)
        self._kayit = kayit or {}
        self.setWindowTitle("Atama Düzenle")
        self.setModal(True)
        self.setMinimumWidth(380)
        self.setProperty("bg-role", "page")
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 20, 20, 20)

        def _row(lbl, widget):
            h = QHBoxLayout()
            l = QLabel(lbl)
            l.setFixedWidth(110)
            h.addWidget(l)
            h.addWidget(widget)
            lay.addLayout(h)
            return widget

        self._cmb_rol = QComboBox()
        for r in self.ROLLER:
            self._cmb_rol.addItem(r)
        idx = self._cmb_rol.findText(self._kayit.get("Rol","teknisyen"))
        if idx >= 0:
            self._cmb_rol.setCurrentIndex(idx)
        _row("Rol", self._cmb_rol)

        self._chk_ana = QCheckBox("Ana birim")
        self._chk_ana.setChecked(bool(int(self._kayit.get("AnabirimMi", 1))))
        lay.addWidget(self._chk_ana)

        self._inp_notlar = QLineEdit(self._kayit.get("Notlar",""))
        _row("Notlar", self._inp_notlar)

        lay.addSpacing(8)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        iptal = QPushButton("İptal")
        iptal.setProperty("style-role", "secondary")
        iptal.setFixedWidth(80)
        iptal.clicked.connect(self.reject)
        btn_row.addWidget(iptal)
        kaydet = QPushButton("Kaydet")
        kaydet.setProperty("style-role", "action")
        kaydet.setFixedWidth(80)
        kaydet.clicked.connect(self.accept)
        btn_row.addWidget(kaydet)
        lay.addLayout(btn_row)

    def get_data(self) -> dict:
        return {
            "Rol":       self._cmb_rol.currentText(),
            "AnabirimMi": self._chk_ana.isChecked(),
            "Notlar":    self._inp_notlar.text().strip(),
        }


class _SablonDialog(QDialog):
    """Hazır şablon seçimi."""

    SABLONLAR = {
        "tam_gun_24h":        "7/24 Nöbet  —  Gündüz(08-20) + Gece(20-08)",
        "sadece_gunduz_12h":  "Sadece Gündüz  —  08:00 - 20:00",
        "uzatilmis_gunduz":   "Uzatılmış Gündüz  —  Gündüz(08-20) + Akşam/Gece(20-00)",
        "uc_vardiya_8h":      "3 Vardiya  —  Sabah(08-16) + Akşam(16-00) + Gece(00-08)",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hazır Şablon Seç")
        self.setModal(True)
        self.setMinimumWidth(440)
        self.setProperty("bg-role", "page")
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(10)

        lay.addWidget(QLabel("Uygulanacak şablonu seçin:"))

        self._cmb = QComboBox()
        for key, adi in self.SABLONLAR.items():
            self._cmb.addItem(adi, userData=key)
        lay.addWidget(self._cmb)

        lay.addSpacing(8)
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        iptal = QPushButton("İptal")
        iptal.setProperty("style-role", "secondary")
        iptal.clicked.connect(self.reject)
        btn_row.addWidget(iptal)

        uygula = QPushButton("Uygula")
        uygula.setProperty("style-role", "action")
        uygula.clicked.connect(self.accept)
        btn_row.addWidget(uygula)
        lay.addLayout(btn_row)

    def get_sablon(self) -> str:
        return self._cmb.currentData()


# ══════════════════════════════════════════════════════════════════
#  ANA SAYFA
# ══════════════════════════════════════════════════════════════════

class NobetVardiyaPage(QWidget):
    """Birim → [Vardiyalar | Personel] iki sekmeli yönetim sayfası."""

    def __init__(self, db=None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db           = db
        self._action_guard = action_guard
        self._secili_birim_id = ""
        self._secili_grup_id  = ""
        self.setProperty("bg-role", "page")
        self._build()
        self._birimleri_yukle()

    # ─── UI ───────────────────────────────────────────────────

    def _build(self):
        from PySide6.QtWidgets import QTabWidget
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Başlık
        hdr = QFrame()
        hdr.setProperty("bg-role", "panel")
        hdr.setFixedHeight(44)
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(16, 0, 16, 0)
        lbl = QLabel("Birim & Vardiya Tanımları")
        lbl.setProperty("style-role", "section-title")
        hl.addWidget(lbl)
        hl.addStretch()
        lay.addWidget(hdr)

        # Ana splitter: sol birim listesi + sağ sekmeler
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.addWidget(self._build_birim_panel())

        # Sağ taraf: sekmeli
        self._tabs = QTabWidget()
        # Sekme 1: Vardiyalar (grup + vardiya)
        vardiya_w = QWidget()
        v_lay = QVBoxLayout(vardiya_w)
        v_lay.setContentsMargins(0, 0, 0, 0)
        v_lay.setSpacing(0)
        inner = QSplitter(Qt.Orientation.Horizontal)
        inner.setHandleWidth(1)
        inner.addWidget(self._build_grup_panel())
        inner.addWidget(self._build_vardiya_panel())
        inner.setSizes([280, 420])
        v_lay.addWidget(inner)
        self._tabs.addTab(vardiya_w, "Vardiyalar")

        # Sekme 2: Personel
        self._tabs.addTab(self._build_personel_panel(), "Personel")

        splitter.addWidget(self._tabs)
        splitter.setSizes([220, 700])
        lay.addWidget(splitter, 1)

    def _panel(self, baslik: str) -> tuple[QWidget, QVBoxLayout]:
        w   = QWidget()
        w.setProperty("bg-role", "page")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        hdr = QFrame()
        hdr.setProperty("bg-role", "elevated")
        hdr.setFixedHeight(36)
        hl  = QHBoxLayout(hdr)
        hl.setContentsMargins(12, 0, 12, 0)
        lbl = QLabel(baslik)
        lbl.setProperty("style-role", "stat-label")
        hl.addWidget(lbl)
        lay.addWidget(hdr)

        return w, lay

    # ── Sol Panel: Birimler ────────────────────────────────────

    def _build_birim_panel(self) -> QWidget:
        w, lay = self._panel("Birimler")

        self._tbl_birim = QTableWidget(0, 1)
        self._tbl_birim.horizontalHeader().setVisible(False)
        self._tbl_birim.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self._tbl_birim.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl_birim.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl_birim.verticalHeader().setVisible(False)
        self._tbl_birim.setShowGrid(False)
        self._tbl_birim.setAlternatingRowColors(True)
        self._tbl_birim.selectionModel().selectionChanged.connect(
            self._on_birim_sec)
        lay.addWidget(self._tbl_birim, 1)

        self._lbl_birim_durum = QLabel("")
        self._lbl_birim_durum.setProperty("color-role", "muted")
        self._lbl_birim_durum.setStyleSheet(
            "font-size: 10px; padding: 4px 8px;")
        lay.addWidget(self._lbl_birim_durum)
        return w

    # ── Orta Panel: Gruplar ────────────────────────────────────

    def _build_grup_panel(self) -> QWidget:
        w, lay = self._panel("Vardiya Grupları")

        # Araç çubuğu
        tb = QFrame()
        tb.setProperty("bg-role", "panel")
        tbl = QHBoxLayout(tb)
        tbl.setContentsMargins(8, 4, 8, 4)
        tbl.setSpacing(4)

        self._btn_grup_yeni = QPushButton("+ Grup")
        self._btn_grup_yeni.setProperty("style-role", "action")
        self._btn_grup_yeni.setFixedHeight(28)
        self._btn_grup_yeni.setEnabled(False)
        self._btn_grup_yeni.clicked.connect(self._grup_yeni)
        tbl.addWidget(self._btn_grup_yeni)

        self._btn_sablon = QPushButton("⚡ Şablon")
        self._btn_sablon.setProperty("style-role", "secondary")
        self._btn_sablon.setFixedHeight(28)
        self._btn_sablon.setEnabled(False)
        self._btn_sablon.clicked.connect(self._sablon_uygula)
        tbl.addWidget(self._btn_sablon)

        tbl.addStretch()
        lay.addWidget(tb)

        self._tbl_grup = QTableWidget(0, 3)
        self._tbl_grup.setHorizontalHeaderLabels(["Grup Adı", "Tür", "Sıra"])
        self._tbl_grup.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self._tbl_grup.setColumnWidth(1, 80)
        self._tbl_grup.setColumnWidth(2, 50)
        self._tbl_grup.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl_grup.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl_grup.verticalHeader().setVisible(False)
        self._tbl_grup.setShowGrid(False)
        self._tbl_grup.setAlternatingRowColors(True)
        self._tbl_grup.doubleClicked.connect(self._grup_duzenle)
        self._tbl_grup.selectionModel().selectionChanged.connect(
            self._on_grup_sec)
        lay.addWidget(self._tbl_grup, 1)

        # Alt butonlar
        alt = QHBoxLayout()
        alt.setContentsMargins(8, 4, 8, 4)
        self._btn_grup_duzenle = QPushButton("✎")
        self._btn_grup_duzenle.setToolTip("Düzenle")
        self._btn_grup_duzenle.setProperty("style-role", "secondary")
        self._btn_grup_duzenle.setFixedSize(32, 28)
        self._btn_grup_duzenle.setEnabled(False)
        self._btn_grup_duzenle.clicked.connect(self._grup_duzenle)
        alt.addWidget(self._btn_grup_duzenle)

        self._btn_grup_sil = QPushButton("✕")
        self._btn_grup_sil.setToolTip("Sil")
        self._btn_grup_sil.setProperty("style-role", "danger")
        self._btn_grup_sil.setFixedSize(32, 28)
        self._btn_grup_sil.setEnabled(False)
        self._btn_grup_sil.clicked.connect(self._grup_sil)
        alt.addWidget(self._btn_grup_sil)
        alt.addStretch()
        lay.addLayout(alt)
        return w

    # ── Sağ Panel: Vardiyalar ──────────────────────────────────

    def _build_vardiya_panel(self) -> QWidget:
        w, lay = self._panel("Vardiyalar")

        tb = QFrame()
        tb.setProperty("bg-role", "panel")
        tbl = QHBoxLayout(tb)
        tbl.setContentsMargins(8, 4, 8, 4)
        tbl.setSpacing(4)

        self._btn_v_yeni = QPushButton("+ Vardiya")
        self._btn_v_yeni.setProperty("style-role", "action")
        self._btn_v_yeni.setFixedHeight(28)
        self._btn_v_yeni.setEnabled(False)
        self._btn_v_yeni.clicked.connect(self._vardiya_yeni)
        tbl.addWidget(self._btn_v_yeni)

        self._lbl_v_grup = QLabel("—")
        self._lbl_v_grup.setProperty("color-role", "muted")
        self._lbl_v_grup.setStyleSheet("font-size: 11px;")
        tbl.addWidget(self._lbl_v_grup)
        tbl.addStretch()
        lay.addWidget(tb)

        self._tbl_v = QTableWidget(0, 6)
        self._tbl_v.setHorizontalHeaderLabels(
            ["Vardiya Adı", "Başlangıç", "Bitiş", "Süre", "Rol", "Min"])
        self._tbl_v.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self._tbl_v.setColumnWidth(1, 70)
        self._tbl_v.setColumnWidth(2, 70)
        self._tbl_v.setColumnWidth(3, 80)
        self._tbl_v.setColumnWidth(4, 70)
        self._tbl_v.setColumnWidth(5, 40)
        self._tbl_v.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl_v.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl_v.verticalHeader().setVisible(False)
        self._tbl_v.setShowGrid(False)
        self._tbl_v.setAlternatingRowColors(True)
        self._tbl_v.doubleClicked.connect(self._vardiya_duzenle)
        self._tbl_v.selectionModel().selectionChanged.connect(
            self._on_v_sec)
        lay.addWidget(self._tbl_v, 1)

        alt = QHBoxLayout()
        alt.setContentsMargins(8, 4, 8, 4)
        self._btn_v_duzenle = QPushButton("✎")
        self._btn_v_duzenle.setToolTip("Düzenle")
        self._btn_v_duzenle.setProperty("style-role", "secondary")
        self._btn_v_duzenle.setFixedSize(32, 28)
        self._btn_v_duzenle.setEnabled(False)
        self._btn_v_duzenle.clicked.connect(self._vardiya_duzenle)
        alt.addWidget(self._btn_v_duzenle)

        self._btn_v_pasif = QPushButton("⏸")
        self._btn_v_pasif.setToolTip("Pasife Al")
        self._btn_v_pasif.setProperty("style-role", "secondary")
        self._btn_v_pasif.setFixedSize(32, 28)
        self._btn_v_pasif.setEnabled(False)
        self._btn_v_pasif.clicked.connect(self._vardiya_pasif)
        alt.addWidget(self._btn_v_pasif)
        alt.addStretch()

        self._lbl_v_ozet = QLabel("")
        self._lbl_v_ozet.setProperty("color-role", "muted")
        self._lbl_v_ozet.setStyleSheet("font-size: 10px;")
        alt.addWidget(self._lbl_v_ozet)
        lay.addLayout(alt)
        return w

    # ── Sağ Panel: Personel ───────────────────────────────────

    def _build_personel_panel(self) -> QWidget:
        w, lay = self._panel("Birim Personeli")

        # Araç çubuğu
        tb  = QFrame()
        tb.setProperty("bg-role", "panel")
        tbl = QHBoxLayout(tb)
        tbl.setContentsMargins(8, 4, 8, 4)
        tbl.setSpacing(4)

        self._btn_p_ata = QPushButton("+ Personel Ata")
        self._btn_p_ata.setProperty("style-role", "action")
        self._btn_p_ata.setFixedHeight(28)
        self._btn_p_ata.setEnabled(False)
        self._btn_p_ata.clicked.connect(self._personel_ata)
        tbl.addWidget(self._btn_p_ata)

        self._btn_p_migrate = QPushButton("⟳ GorevYeri'nden Aktar")
        self._btn_p_migrate.setProperty("style-role", "secondary")
        self._btn_p_migrate.setFixedHeight(28)
        self._btn_p_migrate.setEnabled(False)
        self._btn_p_migrate.setToolTip(
            "Personel.GorevYeri eşleşen tüm personeli bu birime aktar.\n"
            "GorevYeri alanı değiştirilmez (FHSZ kapsamında korunur).")
        self._btn_p_migrate.clicked.connect(self._personel_migrate)
        tbl.addWidget(self._btn_p_migrate)

        tbl.addStretch()
        lay.addWidget(tb)

        # Tablo
        self._tbl_p = QTableWidget(0, 5)
        self._tbl_p.setHorizontalHeaderLabels(
            ["Ad Soyad", "Rol", "Ana Birim", "Görev Başl.", "Durum"])
        self._tbl_p.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self._tbl_p.setColumnWidth(1, 90)
        self._tbl_p.setColumnWidth(2, 80)
        self._tbl_p.setColumnWidth(3, 100)
        self._tbl_p.setColumnWidth(4, 70)
        self._tbl_p.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl_p.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl_p.verticalHeader().setVisible(False)
        self._tbl_p.setShowGrid(False)
        self._tbl_p.setAlternatingRowColors(True)
        self._tbl_p.doubleClicked.connect(self._personel_duzenle)
        self._tbl_p.selectionModel().selectionChanged.connect(
            self._on_p_sec)
        lay.addWidget(self._tbl_p, 1)

        # Alt butonlar
        alt = QHBoxLayout()
        alt.setContentsMargins(8, 4, 8, 4)

        self._btn_p_duzenle = QPushButton("✎  Düzenle")
        self._btn_p_duzenle.setProperty("style-role", "secondary")
        self._btn_p_duzenle.setFixedHeight(28)
        self._btn_p_duzenle.setEnabled(False)
        self._btn_p_duzenle.clicked.connect(self._personel_duzenle)
        alt.addWidget(self._btn_p_duzenle)

        self._btn_p_cikar = QPushButton("✕  Görevden Al")
        self._btn_p_cikar.setProperty("style-role", "danger")
        self._btn_p_cikar.setFixedHeight(28)
        self._btn_p_cikar.setEnabled(False)
        self._btn_p_cikar.clicked.connect(self._personel_cikar)
        alt.addWidget(self._btn_p_cikar)

        alt.addStretch()

        self._lbl_p_ozet = QLabel("")
        self._lbl_p_ozet.setProperty("color-role", "muted")
        self._lbl_p_ozet.setStyleSheet("font-size: 10px;")
        alt.addWidget(self._lbl_p_ozet)
        lay.addLayout(alt)

        return w

    # ─── Servisler ────────────────────────────────────────────

    def _birim_svc(self):
        from core.di import get_nb_birim_service
        return get_nb_birim_service(self._db)

    def _vardiya_svc(self):
        from core.di import get_nb_vardiya_service
        return get_nb_vardiya_service(self._db)

    def _bp_svc(self):
        from core.di import get_nb_birim_personel_service
        return get_nb_birim_personel_service(self._db)

    # ─── Veri Yükleme ─────────────────────────────────────────

    def _birimleri_yukle(self):
        try:
            sonuc    = self._birim_svc().get_birimler()
            birimler = sonuc.veri or [] if sonuc.basarili else []
            self._tbl_birim.setRowCount(0)
            for b in birimler:
                ri  = self._tbl_birim.rowCount()
                bid = b.get("BirimID", "")
                self._tbl_birim.insertRow(ri)
                itm = QTableWidgetItem(b.get("BirimAdi", ""))
                itm.setData(Qt.ItemDataRole.UserRole, bid)
                self._tbl_birim.setItem(ri, 0, itm)
            self._lbl_birim_durum.setText(f"{len(birimler)} birim")
        except Exception as e:
            logger.error(f"Birim yükleme: {e}")

    def _gruplari_yukle(self, birim_id: str):
        self._secili_grup_id = ""
        self._tbl_grup.setRowCount(0)
        self._tbl_v.setRowCount(0)
        self._lbl_v_grup.setText("—")
        self._lbl_v_ozet.setText("")
        if not birim_id:
            return
        try:
            sonuc  = self._vardiya_svc().get_gruplar(birim_id)
            gruplar = sonuc.veri or [] if sonuc.basarili else []
            for g in gruplar:
                ri  = self._tbl_grup.rowCount()
                gid = g.get("GrupID", "")
                self._tbl_grup.insertRow(ri)

                def _i(text, user=gid):
                    it = QTableWidgetItem(str(text))
                    it.setData(Qt.ItemDataRole.UserRole, user)
                    return it

                self._tbl_grup.setItem(ri, 0, _i(g.get("GrupAdi", "")))
                tur_i = _i(g.get("GrupTuru", "zorunlu"))
                if g.get("GrupTuru") == "ihtiyari":
                    tur_i.setForeground(QColor("#e8a030"))
                self._tbl_grup.setItem(ri, 1, tur_i)
                self._tbl_grup.setItem(ri, 2, _i(g.get("Sira", 1)))
        except Exception as e:
            logger.error(f"Grup yükleme: {e}")

    def _vardiyas_yukle(self, grup_id: str):
        self._tbl_v.setRowCount(0)
        self._lbl_v_ozet.setText("")
        if not grup_id:
            return
        try:
            v_rows = self._vardiya_svc()._r.get("NB_Vardiya").get_all() or []
            vardiyalar = sorted(
                [v for v in v_rows
                 if str(v.get("GrupID", "")) == grup_id
                 and int(v.get("Aktif", 1))],
                key=lambda v: int(v.get("Sira", 1))
            )
            toplam_dk = 0
            for v in vardiyalar:
                ri  = self._tbl_v.rowCount()
                vid = v.get("VardiyaID", "")
                dk  = int(v.get("SureDakika", 0))
                self._tbl_v.insertRow(ri)

                def _i(text, user=vid):
                    it = QTableWidgetItem(str(text))
                    it.setData(Qt.ItemDataRole.UserRole, user)
                    return it

                self._tbl_v.setItem(ri, 0, _i(v.get("VardiyaAdi", "")))
                self._tbl_v.setItem(ri, 1, _i(v.get("BasSaat", "")))
                self._tbl_v.setItem(ri, 2, _i(v.get("BitSaat", "")))
                self._tbl_v.setItem(ri, 3, _i(
                    f"{dk//60}s {dk%60:02d}dk" if dk else "—"))

                rol = v.get("Rol", "ana")
                rol_i = _i(rol)
                if rol == "yardimci":
                    rol_i.setForeground(QColor("#e8a030"))
                self._tbl_v.setItem(ri, 4, rol_i)
                self._tbl_v.setItem(ri, 5, _i(v.get("MinPersonel", 1)))

                if rol == "ana":
                    toplam_dk += dk

            ana_sayi = sum(1 for v in vardiyalar if v.get("Rol","ana")=="ana")
            self._lbl_v_ozet.setText(
                f"{len(vardiyalar)} vardiya  |  "
                f"{ana_sayi} ana  |  "
                f"Toplam: {toplam_dk//60}s {toplam_dk%60:02d}dk")
        except Exception as e:
            logger.error(f"Vardiya yükleme: {e}")

    # ─── Seçim Sinyalleri ─────────────────────────────────────

    def _on_birim_sec(self):
        row = self._tbl_birim.currentRow()
        if row < 0:
            self._secili_birim_id = ""
            self._btn_grup_yeni.setEnabled(False)
            self._btn_sablon.setEnabled(False)
            self._btn_p_ata.setEnabled(False)
            self._btn_p_migrate.setEnabled(False)
            return
        itm = self._tbl_birim.item(row, 0)
        bid = itm.data(Qt.ItemDataRole.UserRole) if itm else ""
        self._secili_birim_id = bid
        aktif = bool(bid)
        self._btn_grup_yeni.setEnabled(aktif)
        self._btn_sablon.setEnabled(aktif)
        self._btn_p_ata.setEnabled(aktif)
        self._btn_p_migrate.setEnabled(aktif)
        self._gruplari_yukle(bid)
        self._personelleri_yukle(bid)

    def _on_grup_sec(self):
        row = self._tbl_grup.currentRow()
        var = row >= 0
        self._btn_grup_duzenle.setEnabled(var)
        self._btn_grup_sil.setEnabled(var)
        self._btn_v_yeni.setEnabled(var)
        if not var:
            self._secili_grup_id = ""
            self._lbl_v_grup.setText("—")
            self._tbl_v.setRowCount(0)
            return
        itm = self._tbl_grup.item(row, 0)
        gid = itm.data(Qt.ItemDataRole.UserRole) if itm else ""
        adi = itm.text() if itm else ""
        self._secili_grup_id = gid
        self._lbl_v_grup.setText(adi)
        self._vardiyas_yukle(gid)

    def _on_v_sec(self):
        var = self._tbl_v.currentRow() >= 0
        self._btn_v_duzenle.setEnabled(var)
        self._btn_v_pasif.setEnabled(var)

    # ─── Grup Aksiyonları ─────────────────────────────────────

    def _grup_yeni(self):
        if not self._secili_birim_id:
            return
        dialog = _GrupDialog(parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        veri  = dialog.get_data()
        sonuc = self._vardiya_svc().grup_ekle(
            birim_id = self._secili_birim_id,
            grup_adi = veri["GrupAdi"],
            grup_turu= veri["GrupTuru"],
            sira     = veri["Sira"],
        )
        if sonuc.basarili:
            self._gruplari_yukle(self._secili_birim_id)
        else:
            QMessageBox.critical(self, "Hata", str(sonuc.hata))

    def _grup_duzenle(self):
        gid = self._secili_grup_id
        if not gid:
            return
        try:
            g_rows = self._vardiya_svc()._r.get("NB_VardiyaGrubu").get_all() or []
            kayit  = next((dict(r) for r in g_rows
                           if r.get("GrupID") == gid), None)
        except Exception:
            kayit = None
        dialog = _GrupDialog(kayit=kayit, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        veri  = dialog.get_data()
        sonuc = self._vardiya_svc().grup_guncelle(
            grup_id  = gid,
            grup_adi = veri["GrupAdi"],
            sira     = veri["Sira"],
        )
        if sonuc.basarili:
            self._gruplari_yukle(self._secili_birim_id)
        else:
            QMessageBox.critical(self, "Hata", str(sonuc.hata))

    def _grup_sil(self):
        gid = self._secili_grup_id
        if not gid:
            return
        row = self._tbl_grup.currentRow()
        adi = self._tbl_grup.item(row, 0).text() if row >= 0 else ""
        cevap = QMessageBox.question(
            self, "Onay",
            f"'{adi}' grubu ve tüm vardiyaları pasife alınsın mı?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if cevap != QMessageBox.StandardButton.Yes:
            return
        sonuc = self._vardiya_svc().grup_sil(gid)
        if sonuc.basarili:
            self._gruplari_yukle(self._secili_birim_id)
        else:
            QMessageBox.critical(self, "Hata", str(sonuc.hata))

    def _sablon_uygula(self):
        if not self._secili_birim_id:
            return
        dialog = _SablonDialog(parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        sablon = dialog.get_sablon()
        sonuc  = self._vardiya_svc().sablon_yukle(
            self._secili_birim_id, sablon)
        if sonuc.basarili:
            QMessageBox.information(self, "Başarılı", sonuc.mesaj)
            self._gruplari_yukle(self._secili_birim_id)
        else:
            QMessageBox.critical(self, "Hata", str(sonuc.hata))

    # ─── Vardiya Aksiyonları ──────────────────────────────────

    def _vardiya_yeni(self):
        gid = self._secili_grup_id
        if not gid:
            return
        dialog = _VardiyaDialog(parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        veri  = dialog.get_data()
        sonuc = self._vardiya_svc().vardiya_ekle(
            grup_id     = gid,
            birim_id    = self._secili_birim_id,
            vardiya_adi = veri["VardiyaAdi"],
            bas_saat    = veri["BasSaat"],
            bit_saat    = veri["BitSaat"],
            rol         = veri["Rol"],
            min_personel= veri["MinPersonel"],
            sira        = veri["Sira"],
        )
        if sonuc.basarili:
            self._vardiyas_yukle(gid)
        else:
            QMessageBox.critical(self, "Hata", str(sonuc.hata))

    def _vardiya_duzenle(self):
        row = self._tbl_v.currentRow()
        if row < 0:
            return
        itm = self._tbl_v.item(row, 0)
        vid = itm.data(Qt.ItemDataRole.UserRole) if itm else ""
        if not vid:
            return
        kayit = self._vardiya_svc().get_vardiya(vid)
        dialog = _VardiyaDialog(kayit=kayit, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        veri  = dialog.get_data()
        sonuc = self._vardiya_svc().vardiya_guncelle(
            vardiya_id  = vid,
            vardiya_adi = veri["VardiyaAdi"],
            bas_saat    = veri["BasSaat"],
            bit_saat    = veri["BitSaat"],
            rol         = veri["Rol"],
            min_personel= veri["MinPersonel"],
            sira        = veri["Sira"],
        )
        if sonuc.basarili:
            self._vardiyas_yukle(self._secili_grup_id)
        else:
            QMessageBox.critical(self, "Hata", str(sonuc.hata))

    def _vardiya_pasif(self):
        row = self._tbl_v.currentRow()
        if row < 0:
            return
        itm = self._tbl_v.item(row, 0)
        vid = itm.data(Qt.ItemDataRole.UserRole) if itm else ""
        if not vid:
            return
        adi = itm.text()
        cevap = QMessageBox.question(
            self, "Onay",
            f"'{adi}' vardiyası pasife alınsın mı?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if cevap != QMessageBox.StandardButton.Yes:
            return
        sonuc = self._vardiya_svc().vardiya_pasif_al(vid)
        if sonuc.basarili:
            self._vardiyas_yukle(self._secili_grup_id)
        else:
            QMessageBox.critical(self, "Hata", str(sonuc.hata))

    def _personelleri_yukle(self, birim_id: str):
        self._tbl_p.setRowCount(0)
        self._lbl_p_ozet.setText("")
        if not birim_id:
            return
        try:
            sonuc = self._bp_svc().birim_personelleri(birim_id, sadece_aktif=False)
            personeller = sonuc.veri or [] if sonuc.basarili else []

            for p in personeller:
                ri  = self._tbl_p.rowCount()
                aid = p.get("ID", "")
                self._tbl_p.insertRow(ri)

                def _i(text, user=aid):
                    it = QTableWidgetItem(str(text))
                    it.setData(Qt.ItemDataRole.UserRole, user)
                    return it

                self._tbl_p.setItem(ri, 0, _i(p.get("AdSoyad", "")))

                rol_i = _i(p.get("Rol", "teknisyen"))
                if p.get("Rol") == "sorumlu":
                    rol_i.setForeground(QColor("#4d9ee8"))
                self._tbl_p.setItem(ri, 1, rol_i)

                ana_i = _i("✔" if int(p.get("AnabirimMi", 1)) else "◌")
                if not int(p.get("AnabirimMi", 1)):
                    ana_i.setForeground(QColor("#888"))
                self._tbl_p.setItem(ri, 2, ana_i)

                self._tbl_p.setItem(ri, 3, _i(
                    p.get("GorevBaslangic", "")[:10]))

                aktif  = int(p.get("Aktif", 1))
                bitis  = p.get("GorevBitis", "")
                if not aktif or bitis:
                    durum_i = _i("Pasif")
                    durum_i.setForeground(QColor("#e85555"))
                else:
                    durum_i = _i("Aktif")
                    durum_i.setForeground(QColor("#2ec98e"))
                self._tbl_p.setItem(ri, 4, durum_i)

            aktif_sayi = sum(
                1 for p in personeller
                if int(p.get("Aktif", 1)) and not p.get("GorevBitis")
            )
            self._lbl_p_ozet.setText(
                f"{aktif_sayi} aktif  /  {len(personeller)} toplam")
        except Exception as e:
            logger.error(f"Personel yükleme: {e}")

    def _on_p_sec(self):
        var = self._tbl_p.currentRow() >= 0
        self._btn_p_duzenle.setEnabled(var)
        self._btn_p_cikar.setEnabled(var)

    def _secili_atama_id(self) -> str:
        row = self._tbl_p.currentRow()
        if row < 0:
            return ""
        itm = self._tbl_p.item(row, 0)
        return itm.data(Qt.ItemDataRole.UserRole) if itm else ""

    def _personel_ata(self):
        if not self._secili_birim_id:
            return
        dialog = _PersonelAtaDialog(
            db=self._db,
            birim_id=self._secili_birim_id,
            parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        veri  = dialog.get_data()
        sonuc = self._bp_svc().personel_ata(
            birim_id        = self._secili_birim_id,
            personel_id     = veri["PersonelID"],
            rol             = veri["Rol"],
            ana_birim       = veri["AnabirimMi"],
            gorev_baslangic = veri["GorevBaslangic"],
            notlar          = veri["Notlar"],
        )
        if sonuc.basarili:
            self._personelleri_yukle(self._secili_birim_id)
        else:
            QMessageBox.critical(self, "Hata", str(sonuc.hata))

    def _personel_duzenle(self):
        aid = self._secili_atama_id()
        if not aid:
            return
        try:
            bp_rows = self._bp_svc()._r.get("NB_BirimPersonel").get_all() or []
            kayit   = next((dict(r) for r in bp_rows
                            if r.get("ID") == aid), None)
        except Exception:
            kayit = None
        if not kayit:
            return
        dialog = _AtamaDuzenleDialog(kayit=kayit, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        veri  = dialog.get_data()
        sonuc = self._bp_svc().atama_guncelle(
            atama_id = aid,
            rol      = veri.get("Rol"),
            ana_birim= veri.get("AnabirimMi"),
            notlar   = veri.get("Notlar"),
        )
        if sonuc.basarili:
            self._personelleri_yukle(self._secili_birim_id)
        else:
            QMessageBox.critical(self, "Hata", str(sonuc.hata))

    def _personel_cikar(self):
        aid = self._secili_atama_id()
        if not aid:
            return
        row = self._tbl_p.currentRow()
        ad  = self._tbl_p.item(row, 0).text() if row >= 0 else ""
        cevap = QMessageBox.question(
            self, "Onay",
            f"'{ad}' bu birimden görevden alınsın mı?\n\n"
            "Kayıt silinmez, GorevBitis tarihi set edilir.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if cevap != QMessageBox.StandardButton.Yes:
            return

        # BirimID + PersonelID bul
        try:
            bp_rows = self._bp_svc()._r.get("NB_BirimPersonel").get_all() or []
            kayit   = next((r for r in bp_rows if r.get("ID") == aid), None)
        except Exception:
            kayit = None
        if not kayit:
            return
        sonuc = self._bp_svc().gorevden_al(
            birim_id    = str(kayit.get("BirimID","")),
            personel_id = str(kayit.get("PersonelID","")),
        )
        if sonuc.basarili:
            self._personelleri_yukle(self._secili_birim_id)
        else:
            QMessageBox.critical(self, "Hata", str(sonuc.hata))

    def _personel_migrate(self):
        if not self._secili_birim_id:
            return
        row = self._tbl_birim.currentRow()
        birim_adi = self._tbl_birim.item(row, 0).text() if row >= 0 else "?"
        cevap = QMessageBox.question(
            self, "GorevYeri'nden Aktar",
            f"'{birim_adi}' birimine GorevYeri eşleşen tüm personel\n"
            f"NB_BirimPersonel tablosuna aktarılsın mı?\n\n"
            f"GorevYeri alanı değiştirilmez (FHSZ kapsamında korunur).\n"
            f"Zaten atanmış personel atlanır.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if cevap != QMessageBox.StandardButton.Yes:
            return
        sonuc = self._bp_svc().toplu_gorev_yeri_migrate(self._secili_birim_id)
        if sonuc.basarili:
            QMessageBox.information(self, "Tamamlandı", sonuc.mesaj)
            self._personelleri_yukle(self._secili_birim_id)
        else:
            QMessageBox.critical(self, "Hata", str(sonuc.hata))

    def load_data(self):
        """Dış çağrı için — sayfa gösterildiğinde yenile."""
        self._birimleri_yukle()

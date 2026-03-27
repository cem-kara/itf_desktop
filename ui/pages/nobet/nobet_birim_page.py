# -*- coding: utf-8 -*-
"""Nöbet Birim & Vardiya Tanımları Sayfası."""
from typing import Optional

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QLineEdit, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView,
    QStackedWidget, QFormLayout, QScrollArea, QGroupBox,
    QDoubleSpinBox, QSpinBox,
)

from core.di import get_nobet_service
from core.logger import logger
from core.hata_yonetici import bilgi_goster, hata_goster, soru_sor
from ui.styles.icons import IconRenderer, IconColors

_PANEL_W = 360


class NobetBirimPage(QWidget):

    def __init__(self, db=None, action_guard=None, parent=None):
        super().__init__(parent)
        self.setProperty("bg-role", "page")
        self._db = db
        self._action_guard = action_guard
        self._secili_birim: Optional[dict] = None
        self._anim: list = []
        self._setup_ui()
        if db:
            self.load_data()

    # ─── UI ──────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_toolbar())

        icerik = QHBoxLayout()
        icerik.setContentsMargins(0, 0, 0, 0)
        icerik.setSpacing(0)

        # Sol: birim listesi
        sol = QWidget()
        sl = QVBoxLayout(sol)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(0)
        sl.addWidget(self._build_birim_tablo(), 1)
        sl.addWidget(self._build_footer())
        icerik.addWidget(sol, 1)

        # Sağ: birim formu
        self._birim_panel = self._build_birim_panel()
        icerik.addWidget(self._birim_panel)

        wrap = QWidget()
        wrap.setLayout(icerik)
        root.addWidget(wrap, 1)

    def _build_toolbar(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(52)
        frame.setProperty("bg-role", "panel")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(8)

        lbl = QLabel("Birimler")
        lbl.setProperty("style-role", "title")
        lbl.setProperty("color-role", "primary")
        lay.addWidget(lbl)
        lay.addStretch()

        self.btn_yenile = QPushButton()
        self.btn_yenile.setFixedSize(32, 28)
        self.btn_yenile.setProperty("style-role", "refresh")
        self.btn_yenile.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_yenile, "refresh",
                                     color=IconColors.MUTED, size=16)
        self.btn_yenile.clicked.connect(self.load_data)
        lay.addWidget(self.btn_yenile)

        self.btn_yeni = QPushButton(" Yeni Birim")
        self.btn_yeni.setProperty("style-role", "action")
        self.btn_yeni.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_yeni, "plus",
                                     color=IconColors.PRIMARY, size=14)
        self.btn_yeni.clicked.connect(self._on_yeni_birim)
        lay.addWidget(self.btn_yeni)
        return frame

    def _build_birim_tablo(self) -> QTableWidget:
        self.tbl_birim = QTableWidget(0, 3)
        self.tbl_birim.setHorizontalHeaderLabels(
            ["Birim Adı", "Vardiya Sayısı", "Durum"]
        )
        self.tbl_birim.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_birim.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_birim.setAlternatingRowColors(True)
        self.tbl_birim.verticalHeader().setVisible(False)
        self.tbl_birim.setShowGrid(False)
        hdr = self.tbl_birim.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_birim.doubleClicked.connect(self._on_birim_sec)
        return self.tbl_birim

    def _build_footer(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(36)
        frame.setProperty("bg-role", "panel")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 0, 16, 0)
        self.lbl_sayi = QLabel("0 birim")
        self.lbl_sayi.setProperty("style-role", "footer")
        lay.addWidget(self.lbl_sayi)
        lay.addStretch()
        return frame

    def _build_birim_panel(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("bg-role", "panel")
        panel.setMinimumWidth(0)
        panel.setMaximumWidth(0)
        root = QVBoxLayout(panel)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Başlık
        hdr = QFrame()
        hdr.setFixedHeight(48)
        hdr.setProperty("bg-role", "elevated")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(16, 0, 8, 0)
        self.lbl_panel_baslik = QLabel("Yeni Birim")
        self.lbl_panel_baslik.setProperty("style-role", "section-title")
        self.lbl_panel_baslik.setProperty("color-role", "primary")
        hl.addWidget(self.lbl_panel_baslik)
        hl.addStretch()
        btn_kapat = QPushButton()
        btn_kapat.setFixedSize(28, 28)
        btn_kapat.setProperty("style-role", "close")
        btn_kapat.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(btn_kapat, "x", color=IconColors.MUTED, size=14)
        btn_kapat.clicked.connect(self._panel_kapat)
        hl.addWidget(btn_kapat)
        root.addWidget(hdr)

        # QStackedWidget: 0=birim form, 1=vardiya listesi
        self._panel_stack = QStackedWidget()
        self._panel_stack.addWidget(self._build_birim_form())
        self._panel_stack.addWidget(self._build_vardiya_panel())
        root.addWidget(self._panel_stack, 1)
        return panel

    def _build_birim_form(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        icerik = QWidget()
        form = QFormLayout(icerik)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight |
                               Qt.AlignmentFlag.AlignVCenter)

        def _lbl(t, z=False):
            l = QLabel(("* " if z else "") + t)
            l.setProperty("color-role", "muted")
            return l

        self.inp_birim_adi = QLineEdit()
        self.inp_birim_adi.setPlaceholderText("Örn: MRI, Acil, Tomografi")
        form.addRow(_lbl("Birim Adı", True), self.inp_birim_adi)

        self.inp_aciklama = QLineEdit()
        self.inp_aciklama.setPlaceholderText("Opsiyonel not...")
        form.addRow(_lbl("Açıklama"), self.inp_aciklama)

        lbl_bilgi = QLabel("Birimi kaydettikten sonra vardiyaları düzenleyebilirsiniz.")
        lbl_bilgi.setProperty("color-role", "muted")
        lbl_bilgi.setWordWrap(True)
        form.addRow("", lbl_bilgi)

        scroll.setWidget(icerik)

        # Alt butonlar
        self._birim_alt = QFrame()
        self._birim_alt.setFixedHeight(56)
        self._birim_alt.setProperty("bg-role", "elevated")
        alay = QHBoxLayout(self._birim_alt)
        alay.setContentsMargins(16, 8, 16, 8)
        alay.setSpacing(8)

        # Sabitler read-only — sil/kaydet butonu yok
        alay.addStretch()

        self.btn_vardiya_duzenle = QPushButton(" Vardiyaları Düzenle")
        self.btn_vardiya_duzenle.setProperty("style-role", "secondary")
        self.btn_vardiya_duzenle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_vardiya_duzenle.setVisible(False)
        IconRenderer.set_button_icon(self.btn_vardiya_duzenle, "clock",
                                     color=IconColors.MUTED, size=14)
        self.btn_vardiya_duzenle.clicked.connect(self._on_vardiya_duzenle)
        alay.addWidget(self.btn_vardiya_duzenle)

        alay.addStretch()

        self.btn_birim_kaydet = QPushButton("Tamam")
        self.btn_birim_kaydet.setProperty("style-role", "action")
        self.btn_birim_kaydet.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_birim_kaydet, "check",
                                     color=IconColors.PRIMARY, size=14)
        self.btn_birim_kaydet.clicked.connect(self._panel_kapat)
        alay.addWidget(self.btn_birim_kaydet)

        # Wrap form + alt
        wrap = QWidget()
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(0)
        wl.addWidget(scroll, 1)
        wl.addWidget(self._birim_alt)
        return wrap

    def _build_vardiya_panel(self) -> QWidget:
        """Seçili birimin vardiyalarını listele ve düzenle."""
        wrap = QWidget()
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(0)

        # Geri butonu
        geri_bar = QFrame()
        geri_bar.setFixedHeight(36)
        geri_bar.setProperty("bg-role", "elevated")
        gl = QHBoxLayout(geri_bar)
        gl.setContentsMargins(8, 0, 8, 0)
        btn_geri = QPushButton(" Birim Bilgilerine Dön")
        btn_geri.setProperty("style-role", "secondary")
        btn_geri.setFixedHeight(26)
        btn_geri.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(btn_geri, "arrow_left",
                                     color=IconColors.MUTED, size=12)
        btn_geri.clicked.connect(lambda: self._panel_stack.setCurrentIndex(0))
        gl.addWidget(btn_geri)
        gl.addStretch()
        btn_v_ekle = QPushButton(" Vardiya Ekle")
        btn_v_ekle.setProperty("style-role", "action")
        btn_v_ekle.setFixedHeight(26)
        btn_v_ekle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(btn_v_ekle, "plus",
                                     color=IconColors.PRIMARY, size=12)
        btn_v_ekle.clicked.connect(self._on_vardiya_ekle_dialog)
        gl.addWidget(btn_v_ekle)
        wl.addWidget(geri_bar)

        # Vardiya tablosu
        self.tbl_vardiya = QTableWidget(0, 4)
        self.tbl_vardiya.setHorizontalHeaderLabels(
            ["Vardiya Adı", "Başlangıç", "Bitiş", "Min Personel"])
        self.tbl_vardiya.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_vardiya.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_vardiya.setAlternatingRowColors(True)
        self.tbl_vardiya.verticalHeader().setVisible(False)
        self.tbl_vardiya.setShowGrid(False)
        hdr = self.tbl_vardiya.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in (1, 2, 3):
            hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_vardiya.doubleClicked.connect(self._on_vardiya_duzenle_satir)
        wl.addWidget(self.tbl_vardiya, 1)
        return wrap

    # ─── Animasyon ───────────────────────────────────────

    def _panel_ac(self):
        self._animate(_PANEL_W)

    def _panel_kapat(self):
        self._animate(0)
        self._secili_birim = None

    def _animate(self, hedef: int):
        self._anim.clear()
        cur = self._birim_panel.width()
        for prop in (b"minimumWidth", b"maximumWidth"):
            a = QPropertyAnimation(self._birim_panel, prop)
            a.setDuration(220)
            a.setStartValue(cur)
            a.setEndValue(hedef)
            a.setEasingCurve(QEasingCurve.Type.OutCubic)
            a.start()
            self._anim.append(a)

    # ─── Veri ────────────────────────────────────────────

    def load_data(self):
        if not self._db:
            return
        try:
            svc = get_nobet_service(self._db)
            sonuc = svc.get_birimler()
            birimler = sonuc.veri or [] if sonuc.basarili else []
            self._doldur_birim_tablo(birimler)
        except Exception as e:
            logger.error(f"Birim yükleme: {e}")

    def _doldur_birim_tablo(self, birimler: list[str]):
        """birimler: Sabitler'den gelen birim adları listesi (string)."""
        self.tbl_birim.setRowCount(0)
        self.tbl_birim.setProperty("_data", birimler)

        try:
            svc    = get_nobet_service(self._db)
            v_sonuc = svc.get_vardiyalar()
            v_rows  = v_sonuc.veri or [] if v_sonuc.basarili else []
        except Exception:
            v_rows = []

        v_sayac: dict[str, int] = {}
        for v in v_rows:
            bid = v.get("BirimAdi", "")
            v_sayac[bid] = v_sayac.get(bid, 0) + 1

        for birim_adi in birimler:
            r = self.tbl_birim.rowCount()
            self.tbl_birim.insertRow(r)
            self.tbl_birim.setItem(r, 0, QTableWidgetItem(birim_adi))
            self.tbl_birim.setItem(r, 1, QTableWidgetItem(
                str(v_sayac.get(birim_adi, 0))))
            self.tbl_birim.setItem(r, 2, QTableWidgetItem("Aktif"))

        self.lbl_sayi.setText(f"{len(birimler)} birim")

    # ─── Panel işlemleri ─────────────────────────────────

    def _on_yeni_birim(self):
        from core.hata_yonetici import bilgi_goster
        bilgi_goster(self,
            "Birimler Sabitler tablosundan okunmaktadır.\n"
            "Yeni birim eklemek için Sabitler tablosuna\n"
            "Kod='Birim' ile kayıt ekleyin."
        )

    def _on_birim_sec(self, idx):
        data = self.tbl_birim.property("_data") or []
        row_no = idx.row()
        if row_no >= len(data):
            return
        birim_adi = data[row_no]   # artık string
        self._secili_birim = {"BirimAdi": birim_adi}
        self.lbl_panel_baslik.setText(f"Vardiyalar — {birim_adi}")
        self.btn_vardiya_duzenle.setVisible(True)
        self.inp_birim_adi.setText(birim_adi)
        self.inp_birim_adi.setReadOnly(True)        # Sabitler'den geliyor
        self.inp_aciklama.clear()
        self._panel_stack.setCurrentIndex(0)
        self._panel_ac()

    def _on_vardiya_duzenle(self):
        if not self._secili_birim:
            return
        self._vardiya_tablo_doldur(self._secili_birim["BirimAdi"])
        self._panel_stack.setCurrentIndex(1)

    def _vardiya_tablo_doldur(self, birim_adi: str):
        try:
            svc   = get_nobet_service(self._db)
            sonuc = svc.get_vardiyalar(birim_adi)
            rows  = sonuc.veri or [] if sonuc.basarili else []
            self.tbl_vardiya.setRowCount(0)
            self.tbl_vardiya.setProperty("_v_data", rows)
            for v in rows:
                r = self.tbl_vardiya.rowCount()
                self.tbl_vardiya.insertRow(r)
                self.tbl_vardiya.setItem(r, 0, QTableWidgetItem(str(v.get("VardiyaAdi", ""))))
                self.tbl_vardiya.setItem(r, 1, QTableWidgetItem(str(v.get("BasSaat", ""))))
                self.tbl_vardiya.setItem(r, 2, QTableWidgetItem(str(v.get("BitSaat", ""))))
                self.tbl_vardiya.setItem(r, 3, QTableWidgetItem(str(v.get("MinPersonel", 1))))
        except Exception as e:
            logger.error(f"Vardiya tablo: {e}")

    def _on_vardiya_ekle_dialog(self):
        if not self._secili_birim:
            return
        from ui.pages.nobet.nobet_vardiya_dialog import NobetVardiyaDialog
        dlg = NobetVardiyaDialog(
            birim_adi=self._secili_birim["BirimAdi"],
            db=self._db,
            parent=self,
        )
        if dlg.exec():
            self._vardiya_tablo_doldur(self._secili_birim["BirimAdi"])

    def _on_vardiya_duzenle_satir(self, idx):
        data = self.tbl_vardiya.property("_v_data") or []
        v = data[idx.row()] if idx.row() < len(data) else None
        if not v:
            return
        from ui.pages.nobet.nobet_vardiya_dialog import NobetVardiyaDialog
        dlg = NobetVardiyaDialog(
            birim_adi=self._secili_birim["BirimAdi"],
            db=self._db,
            mevcut=v,
            parent=self,
        )
        if dlg.exec():
            self._vardiya_tablo_doldur(self._secili_birim["BirimAdi"])

    # ─── Yardımcı ────────────────────────────────────────
    # (Sabitler read-only — birim CRUD yok)

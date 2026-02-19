# -*- coding: utf-8 -*-
"""
CihazGenelPanel — Cihaz Genel Bilgi Sekmesi
─────────────────────────────────────────────
PersonelOverviewPanel deseninde: read-only görünüm, grup bazlı düzenleme.

Gruplar:
  kimlik     → Marka, Model, Cihaz Tipi, Seri No, Demirbaş No
  lokasyon   → Ana Bilim Dalı, Birim, Bulunduğu Bina
  lisans     → NDK Lisans No, NDK Seri No, Lisans Durumu, Bitiş
  teknik     → Sorumlu, RKS, Hizmete Giriş, Durum, Kaynak
  garanti    → Garanti Durumu, Bitiş, Bakım Anlaşması, Kalibrasyon Gerekli
"""
import os
from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
    QGroupBox, QScrollArea, QPushButton, QLineEdit, QComboBox,
    QDateEdit, QMessageBox, QFileDialog,
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QCursor, QPixmap

from core.logger import logger
from ui.theme_manager import ThemeManager
from ui.styles import DarkTheme
from ui.styles.icons import IconRenderer

C      = DarkTheme
STYLES = ThemeManager.get_all_component_styles()

# DB alanı → (grup_id, tip)
FIELDS = {
    # --- kimlik ---
    "Marka":          ("kimlik",  "combo",   "Marka"),
    "Model":          ("kimlik",  "input",   "Model"),
    "CihazTipi":      ("kimlik",  "combo",   "CihazTipi"),
    "SeriNo":         ("kimlik",  "input",   "Seri No"),
    "DemirbasNo":     ("kimlik",  "input",   "Demirbaş No"),
    # --- lokasyon ---
    "AnaBilimDali":   ("lokasyon","combo",   "Ana Bilim Dalı"),
    "Birim":          ("lokasyon","combo",   "Birim"),
    "BulunduguBina":  ("lokasyon","input",   "Bulunduğu Bina"),
    # --- lisans ---
    "NDKLisansNo":    ("lisans",  "input",   "NDK Lisans No"),
    "NDKSeriNo":      ("lisans",  "input",   "NDK Seri No"),
    "LisansDurum":    ("lisans",  "combo",   "Lisans Durumu"),
    "BitisTarihi":    ("lisans",  "date",    "Lisans Bitiş"),
    # --- teknik ---
    "Sorumlusu":      ("teknik",  "input",   "Sorumlu Kişi"),
    "RKS":            ("teknik",  "input",   "Radyasyon Kor. Sor."),
    "HizmeteGirisTarihi": ("teknik","date",  "Hizmete Giriş"),
    "Durum":          ("teknik",  "combo",   "Genel Durum"),
    "Kaynak":         ("teknik",  "combo",   "Edinim Kaynağı"),
    # --- garanti ---
    "GarantiDurumu":  ("garanti", "combo",   "Garanti Durumu"),
    "GarantiBitisTarihi": ("garanti","date", "Garanti Bitiş"),
    "BakimDurum":     ("garanti", "combo",   "Bakım Anlaşması"),
    "KalibrasyonGereklimi": ("garanti","combo","Kalibrasyon Gerekli"),
}

GRUP_META = {
    "kimlik":   ("KİMLİK BİLGİLERİ",   2),
    "lokasyon": ("LOKASYON",            1),
    "lisans":   ("LİSANS",             2),
    "teknik":   ("TEKNİK BİLGİLER",   2),
    "garanti":  ("GARANTİ & BAKIM",    2),
}


class CihazGenelPanel(QWidget):
    """
    Cihaz 360° Merkez ekranının 'Genel Bilgi' sekmesi.
    Cihaz verilerini gruplar halinde gösterir; her grup kendi Düzenle/Kaydet döngüsüne sahip.
    """
    veri_guncellendi = Signal()   # Kayıt başarılıysa emit et

    def __init__(self, cihaz_data: dict, db=None, parent=None):
        super().__init__(parent)
        self.db          = db
        self._cihaz      = cihaz_data or {}
        self._cihaz_id   = str(self._cihaz.get("Cihazid", ""))
        self._widgets    = {}   # db_key → widget
        self._groups     = {}   # grup_id → meta dict
        self._sabit_opts = {}   # db_kod → [değerler]
        self._setup_ui()
        self._populate_sabit_combos()

    # ═══════════════════════════════════════════
    #  UI
    # ═══════════════════════════════════════════

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(STYLES["scroll"])

        content = QWidget()
        content.setStyleSheet("background:transparent;")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(20, 20, 20, 20)
        cl.setSpacing(16)

        # ── Header: cihaz kimliği + fotoğraf ──────────────────
        cl.addWidget(self._build_header())

        # ── Gruplar ───────────────────────────────────────────
        # Yan yana gruplar
        row1 = QHBoxLayout(); row1.setSpacing(16)
        row1.addWidget(self._build_group("kimlik"))
        row1.addWidget(self._build_group("lokasyon"))
        cl.addLayout(row1)

        row2 = QHBoxLayout(); row2.setSpacing(16)
        row2.addWidget(self._build_group("lisans"))
        row2.addWidget(self._build_group("teknik"))
        cl.addLayout(row2)

        cl.addWidget(self._build_group("garanti"))
        cl.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)

    def _build_header(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            f"background:{C.BG_SECONDARY}; border-radius:8px;"
            f"border:1px solid {C.BORDER_PRIMARY};"
        )
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(20)

        # Cihaz görseli
        self.lbl_resim = QLabel("Görsel\nYok")
        self.lbl_resim.setFixedSize(90, 90)
        self.lbl_resim.setAlignment(Qt.AlignCenter)
        self.lbl_resim.setStyleSheet(
            f"border:1px solid {C.BORDER_PRIMARY}; border-radius:6px;"
            f"background:{C.BG_TERTIARY}; color:{C.TEXT_DISABLED}; font-size:11px;"
        )
        self._set_photo(self._cihaz.get("Img", ""))

        photo_col = QVBoxLayout()
        photo_col.addWidget(self.lbl_resim, alignment=Qt.AlignHCenter)
        btn_resim = QPushButton("Görsel Güncelle")
        btn_resim.setFixedHeight(24)
        btn_resim.setStyleSheet(STYLES["file_btn"])
        btn_resim.setCursor(QCursor(Qt.PointingHandCursor))
        btn_resim.clicked.connect(self._select_photo)
        photo_col.addWidget(btn_resim, alignment=Qt.AlignHCenter)
        lay.addLayout(photo_col)

        # Kimlik bilgileri (read-only)
        info = QGridLayout()
        info.setSpacing(14)
        for i, (label, key) in enumerate([
            ("Cihaz ID",     "Cihazid"),
            ("Marka / Model","_marka_model"),
            ("Cihaz Tipi",   "CihazTipi"),
            ("Birim",        "Birim"),
        ]):
            r, c = divmod(i, 2)
            self._add_ro(info, r, c, label,
                         f"{self._cihaz.get('Marka','')} {self._cihaz.get('Model','')}".strip()
                         if key == "_marka_model" else self._cihaz.get(key, ""))
        lay.addLayout(info, 1)
        return frame

    def _build_group(self, grup_id: str) -> QGroupBox:
        baslik, cols = GRUP_META[grup_id]
        grp = QGroupBox()
        grp.setStyleSheet(
            f"QGroupBox{{background:{C.BG_SECONDARY}; border:1px solid {C.BORDER_PRIMARY};"
            "border-radius:8px; margin-top:0; padding:10px;}}"
        )
        vbox = QVBoxLayout(grp)
        vbox.setContentsMargins(10, 10, 10, 10)
        vbox.setSpacing(8)

        # Başlık + butonlar
        hdr = QHBoxLayout()
        lbl = QLabel(baslik)
        lbl.setStyleSheet(
            f"color:{C.INPUT_BORDER_FOCUS}; font-weight:700; font-size:11px; background:transparent;"
        )
        hdr.addWidget(lbl); hdr.addStretch()

        btn_edit   = self._mk_icon_btn("edit",  "Düzenle",  lambda _=False, gid=grup_id: self._toggle(gid, True))
        btn_save   = self._mk_icon_btn("save",  "Kaydet",   lambda _=False, gid=grup_id: self._save(gid), vis=False)
        btn_cancel = self._mk_icon_btn("x",     "İptal",    lambda _=False, gid=grup_id: self._toggle(gid, False), vis=False)
        for b in (btn_edit, btn_save, btn_cancel):
            hdr.addWidget(b)
        vbox.addLayout(hdr)

        # İçerik grid
        content_w = QWidget(); content_w.setStyleSheet("background:transparent;")
        grid = QGridLayout(content_w)
        grid.setSpacing(10)

        fields_in_group = [(k, t, lbl) for k, (g, t, lbl) in FIELDS.items() if g == grup_id]
        for idx, (db_key, tip, label) in enumerate(fields_in_group):
            r, c = divmod(idx, cols)
            widget = self._mk_widget(tip, db_key)
            self._widgets[db_key] = widget

            col_w = QWidget(); col_w.setStyleSheet("background:transparent;")
            col_l = QVBoxLayout(col_w)
            col_l.setContentsMargins(0, 0, 0, 0)
            col_l.setSpacing(3)
            col_l.addWidget(QLabel(label, styleSheet=f"color:{C.TEXT_MUTED}; font-size:11px; background:transparent;"))
            col_l.addWidget(widget)
            grid.addWidget(col_w, r, c)

        vbox.addWidget(content_w)

        self._groups[grup_id] = {
            "content": content_w,
            "btn_edit": btn_edit, "btn_save": btn_save, "btn_cancel": btn_cancel,
            "fields": [k for k, (g, _, __) in FIELDS.items() if g == grup_id],
        }
        return grp

    # ═══════════════════════════════════════════
    #  WIDGET FABRİKASI
    # ═══════════════════════════════════════════

    def _mk_widget(self, tip: str, db_key: str) -> QWidget:
        val = self._cihaz.get(db_key, "") or ""
        if tip == "input":
            w = QLineEdit(str(val))
            w.setReadOnly(True)
            w.setStyleSheet(self._ro_style())
            return w
        elif tip == "combo":
            w = QComboBox()
            w.setEditable(True)
            w.addItem(str(val))
            w.setCurrentText(str(val))
            w.setEnabled(False)
            w.setStyleSheet(self._ro_style())
            return w
        elif tip == "date":
            w = QDateEdit()
            w.setCalendarPopup(True)
            w.setDisplayFormat("dd.MM.yyyy")
            d = QDate.fromString(str(val), "yyyy-MM-dd")
            w.setDate(d if d.isValid() else QDate.currentDate())
            w.setEnabled(False)
            w.setStyleSheet(self._ro_style())
            ThemeManager.setup_calendar_popup(w)
            return w
        return QLabel(str(val))

    # ═══════════════════════════════════════════
    #  DÜZENLEME DÖNGÜSÜ
    # ═══════════════════════════════════════════

    def _toggle(self, grup_id: str, edit_mode: bool):
        grp = self._groups[grup_id]
        grp["btn_edit"].setVisible(not edit_mode)
        grp["btn_save"].setVisible(edit_mode)
        grp["btn_cancel"].setVisible(edit_mode)

        for db_key in grp["fields"]:
            w = self._widgets.get(db_key)
            if w is None:
                continue
            if edit_mode:
                if isinstance(w, QLineEdit):
                    w.setReadOnly(False); w.setStyleSheet(STYLES["input"])
                elif isinstance(w, QComboBox):
                    w.setEnabled(True);  w.setStyleSheet(STYLES["combo"])
                elif isinstance(w, QDateEdit):
                    w.setEnabled(True);  w.setStyleSheet(STYLES["date"])
            else:
                # İptal: eski değere dön
                val = self._cihaz.get(db_key, "") or ""
                if isinstance(w, QLineEdit):
                    w.setText(str(val)); w.setReadOnly(True); w.setStyleSheet(self._ro_style())
                elif isinstance(w, QComboBox):
                    w.setCurrentText(str(val)); w.setEnabled(False); w.setStyleSheet(self._ro_style())
                elif isinstance(w, QDateEdit):
                    d = QDate.fromString(str(val), "yyyy-MM-dd")
                    w.setDate(d if d.isValid() else QDate.currentDate())
                    w.setEnabled(False); w.setStyleSheet(self._ro_style())

    def _save(self, grup_id: str):
        if not self.db or not self._cihaz_id:
            QMessageBox.warning(self, "Hata", "Veritabanı bağlantısı yok.")
            return

        grp = self._groups[grup_id]
        update = {}
        for db_key in grp["fields"]:
            w = self._widgets.get(db_key)
            if isinstance(w, QLineEdit):
                update[db_key] = w.text().strip()
            elif isinstance(w, QComboBox):
                update[db_key] = w.currentText().strip()
            elif isinstance(w, QDateEdit):
                update[db_key] = w.date().toString("yyyy-MM-dd")

        try:
            from core.di import get_registry
            get_registry(self.db).get("Cihazlar").update(self._cihaz_id, update)
            self._cihaz.update(update)
            self._toggle(grup_id, False)
            logger.info(f"Cihaz güncellendi ({grup_id}): {self._cihaz_id}")
            self.veri_guncellendi.emit()
        except Exception as e:
            logger.error(f"Cihaz kayıt hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Güncelleme başarısız:\n{e}")

    # ═══════════════════════════════════════════
    #  FOTOĞRAF
    # ═══════════════════════════════════════════

    def _set_photo(self, ref: str):
        ref = str(ref or "").strip()
        if not ref:
            self.lbl_resim.setText("Görsel\nYok")
            return
        if os.path.exists(ref):
            px = QPixmap(ref)
            if not px.isNull():
                self.lbl_resim.setText("")
                self.lbl_resim.setPixmap(
                    px.scaled(self.lbl_resim.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                return
        if ref.startswith("http"):
            self.lbl_resim.setText("☁ Drive")
            return
        self.lbl_resim.setText("Görsel\nYüklenemedi")

    def _select_photo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Görsel Seç", "",
            "Görsel Dosyaları (*.jpg *.jpeg *.png *.bmp)")
        if not path:
            return
        self._set_photo(path)
        self._cihaz["Img"] = path

    # ═══════════════════════════════════════════
    #  SABİTLER (combo seçenekleri)
    # ═══════════════════════════════════════════

    def _populate_sabit_combos(self):
        if not self.db:
            return
        try:
            from core.di import get_registry
            sabitler = get_registry(self.db).get("Sabitler").get_all()
            for item in sabitler:
                kod     = item.get("Kod", "")
                eleman  = item.get("MenuEleman", "")
                if kod and eleman:
                    self._sabit_opts.setdefault(kod, []).append(eleman)

            # DB_KOD → combo widget key eşlemeleri
            mapping = {
                "Marka":         "Marka",
                "Cihaz_Tipi":    "CihazTipi",
                "AnaBilimDali":  "AnaBilimDali",
                "Birim":         "Birim",
                "Kaynak":        "Kaynak",
                "Lisans_Durum":  "LisansDurum",
                "Cihaz_Durum":   "Durum",
                "Garanti_Durum": "GarantiDurumu",
                "Bakim_Durum":   "BakimDurum",
                "Kalibrasyon_Durum": "KalibrasyonGereklimi",
            }
            for sabit_kod, widget_key in mapping.items():
                items = sorted(self._sabit_opts.get(sabit_kod, []))
                cmb   = self._widgets.get(widget_key)
                if not isinstance(cmb, QComboBox) or not items:
                    continue
                cur = cmb.currentText()
                cmb.blockSignals(True)
                cmb.clear(); cmb.addItem(""); cmb.addItems(items)
                cmb.setCurrentText(cur)
                cmb.blockSignals(False)
        except Exception as e:
            logger.error(f"CihazGenelPanel sabit combo: {e}")

    # ═══════════════════════════════════════════
    #  YARDIMCILAR
    # ═══════════════════════════════════════════

    @staticmethod
    def _ro_style() -> str:
        return (
            f"background:transparent; border:none;"
            f"color:{C.TEXT_PRIMARY}; font-size:13px; font-weight:500; padding:4px;"
        )

    def _mk_icon_btn(self, icon: str, tip: str, cb, vis=True) -> QPushButton:
        btn = QPushButton()
        btn.setToolTip(tip)
        btn.setFixedSize(28, 24)
        btn.setVisible(vis)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.setStyleSheet(
            "QPushButton{background:rgba(255,255,255,.08);border:none;border-radius:4px;}"
            "QPushButton:hover{background:rgba(255,255,255,.18);}"
        )
        try:
            IconRenderer.set_button_icon(btn, icon, color=C.TEXT_SECONDARY, size=13)
        except Exception:
            btn.setText(icon[:1])
        btn.clicked.connect(cb)
        return btn

    @staticmethod
    def _add_ro(layout, row, col, label, value):
        w = QWidget(); w.setStyleSheet("background:transparent;")
        l = QVBoxLayout(w); l.setContentsMargins(0,0,0,0); l.setSpacing(2)
        l.addWidget(QLabel(label, styleSheet=f"color:{C.TEXT_MUTED}; font-size:11px;"))
        l.addWidget(QLabel(str(value or "—"), styleSheet=f"color:{C.TEXT_PRIMARY}; font-size:13px; font-weight:500;"))
        layout.addWidget(w, row, col)

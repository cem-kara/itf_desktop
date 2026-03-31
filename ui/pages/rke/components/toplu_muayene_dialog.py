# -*- coding: utf-8 -*-
"""RKE Toplu Muayene Dialog — seçili ekipmanlara tek seferde muayene kaydı."""
import uuid
from typing import Optional

from PySide6.QtCore import Qt, QDate, QThread, Signal as _Signal
from PySide6.QtGui import QCursor, QStandardItemModel, QStandardItem
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QGridLayout,
    QLabel, QComboBox, QDateEdit, QPushButton, QListWidget,
    QProgressBar,
)

from core.logger import logger
from core.di import get_rke_service
from core.hata_yonetici import hata_goster, uyari_goster


# ─── CheckableComboBox ─────────────────────────────────────

class CheckableComboBox(QComboBox):
    """Çoklu seçim destekli combo."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModel(QStandardItemModel(self))
        self.setEditable(True)
        if le := self.lineEdit():
            le.setReadOnly(True)
        self.view().pressed.connect(self._toggle)

    def _toggle(self, index):
        item = self.model().itemFromIndex(index)  # type: ignore
        if item:
            checked = item.checkState() == Qt.CheckState.Checked
            item.setCheckState(
                Qt.CheckState.Unchecked if checked else Qt.CheckState.Checked
            )
            self._sync_text()

    def _sync_text(self):
        items = [
            self.model().item(i).text()  # type: ignore
            for i in range(self.count())
            if self.model().item(i).checkState() == Qt.CheckState.Checked  # type: ignore
        ]
        if le := self.lineEdit():
            le.setText(", ".join(items))

    def addItem(self, text: str, userData=None):  # type: ignore
        item = QStandardItem(text)
        item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        item.setData(Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
        self.model().appendRow(item)  # type: ignore

    def addItems(self, texts):  # type: ignore
        for t in texts:
            self.addItem(t)

    def checked_items(self) -> str:
        return self.lineEdit().text() if self.lineEdit() else ""

    def clear_checks(self):
        for i in range(self.count()):
            item = self.model().item(i)  # type: ignore
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)
        if le := self.lineEdit():
            le.clear()


# ─── Worker ────────────────────────────────────────────────

class _TopluWorker(QThread):
    progress = _Signal(int, int)
    finished = _Signal(int)
    error    = _Signal(str)

    def __init__(self, db, ekipmanlar: list[str], ortak: dict,
                 fiz_aktif: bool, sko_aktif: bool):
        super().__init__()
        self._db         = db
        self._ekipmanlar = ekipmanlar
        self._ortak      = ortak
        self._fiz        = fiz_aktif
        self._sko        = sko_aktif

    def run(self):
        try:
            svc = get_rke_service(self._db)
            ok  = 0
            n   = len(self._ekipmanlar)

            for idx, ekipman_no in enumerate(self._ekipmanlar, 1):
                veri = {
                    "KayitNo":              f"M-{uuid.uuid4().hex[:10].upper()}",
                    "EkipmanNo":            ekipman_no,
                    "FMuayeneTarihi":       self._ortak["FMuayeneTarihi"] if self._fiz else "",
                    "FizikselDurum":        self._ortak["FizikselDurum"]  if self._fiz else "",
                    "SMuayeneTarihi":       self._ortak["SMuayeneTarihi"] if self._sko else "",
                    "SkopiDurum":           self._ortak["SkopiDurum"]     if self._sko else "",
                    "Aciklamalar":          self._ortak.get("Aciklamalar", ""),
                    "KontrolEdenUnvani":    self._ortak.get("KontrolEden", ""),
                    "BirimSorumlusuUnvani": "",
                    "Notlar":               "Toplu Kayıt",
                    "Rapor":                "",
                }
                sonuc = svc.muayene_ekle(veri)
                if sonuc.basarili:
                    ok += 1
                self.progress.emit(idx, n)

            self.finished.emit(ok)

        except Exception as e:
            logger.error(f"Toplu muayene worker: {e}")
            self.error.emit(str(e))


# ═══════════════════════════════════════════════════════════
#  DIALOG
# ═══════════════════════════════════════════════════════════

class TopluMuayeneDialog(QDialog):
    """
    Seçili ekipmanlar için toplu muayene kaydı.

        dlg = TopluMuayeneDialog(
            db=self._db,
            ekipmanlar=["RKE-ON-1", "RKE-ON-2"],
            kontrol_listesi=[...],
            aciklama_listesi=[...],
            kullanici_adi="Dr. Ali",
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_data()
    """

    def __init__(self, db=None,
                 ekipmanlar: Optional[list[str]] = None,
                 kontrol_listesi: Optional[list[str]] = None,
                 aciklama_listesi: Optional[list[str]] = None,
                 kullanici_adi: Optional[str] = None,
                 parent=None,
                 # Eski API uyumluluğu (görmezden gelinir)
                 secilen_ekipmanlar=None,
                 teknik_aciklamalar=None,
                 sorumlu_listesi=None,
                 db_path=None,
                 checkable_combo_cls=None,
                 worker_cls=None,
                 use_sheets=False):
        super().__init__(parent)
        # Eski API fallback
        if ekipmanlar is None and secilen_ekipmanlar is not None:
            ekipmanlar = secilen_ekipmanlar
        if aciklama_listesi is None and teknik_aciklamalar is not None:
            aciklama_listesi = teknik_aciklamalar

        self._db               = db
        self._ekipmanlar       = ekipmanlar or []
        self._kontrol_listesi  = kontrol_listesi or []
        self._aciklama_listesi = aciklama_listesi or []
        self._kullanici_adi    = kullanici_adi
        self._worker: Optional[_TopluWorker] = None

        self.setWindowTitle(f"Toplu Muayene — {len(self._ekipmanlar)} Ekipman")
        self.setModal(True)
        self.resize(560, 520)
        self._build_ui()

    # ─── UI ──────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # Ekipman listesi
        grp_list = QGroupBox(f"Seçili Ekipmanlar ({len(self._ekipmanlar)})")
        gl = QVBoxLayout(grp_list)
        lst = QListWidget()
        lst.setFixedHeight(80)
        lst.addItems(self._ekipmanlar)
        gl.addWidget(lst)
        root.addWidget(grp_list)

        # Fiziksel Muayene
        self.grp_fiz = QGroupBox("Fiziksel Muayene")
        self.grp_fiz.setCheckable(True)
        self.grp_fiz.setChecked(True)
        hf = QHBoxLayout(self.grp_fiz)
        hf.setSpacing(10)
        lbl_ft = QLabel("Tarih:"); lbl_ft.setProperty("color-role", "muted")
        self.dt_fiz = QDateEdit(QDate.currentDate())
        self.dt_fiz.setCalendarPopup(True)
        self.dt_fiz.setDisplayFormat("dd.MM.yyyy")
        lbl_fd = QLabel("Durum:"); lbl_fd.setProperty("color-role", "muted")
        self.cmb_fiz = QComboBox()
        self.cmb_fiz.addItems(["Kullanıma Uygun", "Kullanıma Uygun Değil"])
        hf.addWidget(lbl_ft); hf.addWidget(self.dt_fiz)
        hf.addWidget(lbl_fd); hf.addWidget(self.cmb_fiz)
        root.addWidget(self.grp_fiz)

        # Skopi Muayene
        self.grp_sko = QGroupBox("Skopi Muayene")
        self.grp_sko.setCheckable(True)
        self.grp_sko.setChecked(False)
        hs = QHBoxLayout(self.grp_sko)
        hs.setSpacing(10)
        lbl_st = QLabel("Tarih:"); lbl_st.setProperty("color-role", "muted")
        self.dt_sko = QDateEdit(QDate.currentDate())
        self.dt_sko.setCalendarPopup(True)
        self.dt_sko.setDisplayFormat("dd.MM.yyyy")
        lbl_sd = QLabel("Durum:"); lbl_sd.setProperty("color-role", "muted")
        self.cmb_sko = QComboBox()
        self.cmb_sko.addItems(["Kullanıma Uygun", "Kullanıma Uygun Değil", "Yapılmadı"])
        hs.addWidget(lbl_st); hs.addWidget(self.dt_sko)
        hs.addWidget(lbl_sd); hs.addWidget(self.cmb_sko)
        root.addWidget(self.grp_sko)

        # Ortak Bilgiler
        grp_ortak = QGroupBox("Ortak Bilgiler")
        og = QGridLayout(grp_ortak)
        og.setSpacing(8)

        lbl_ke = QLabel("Kontrol Eden:"); lbl_ke.setProperty("color-role", "muted")
        self.cmb_kontrol = QComboBox()
        self.cmb_kontrol.setEditable(True)
        self.cmb_kontrol.addItems(self._kontrol_listesi)
        if self._kullanici_adi:
            self.cmb_kontrol.setCurrentText(self._kullanici_adi)
        og.addWidget(lbl_ke, 0, 0)
        og.addWidget(self.cmb_kontrol, 0, 1, 1, 3)

        lbl_acik = QLabel("Teknik Açıklama:"); lbl_acik.setProperty("color-role", "muted")
        self.cmb_aciklama = CheckableComboBox()
        self.cmb_aciklama.addItems(self._aciklama_listesi)
        og.addWidget(lbl_acik, 1, 0)
        og.addWidget(self.cmb_aciklama, 1, 1, 1, 3)
        root.addWidget(grp_ortak)

        # Progress + durum
        self.pbar = QProgressBar()
        self.pbar.setVisible(False)
        self.pbar.setFixedHeight(4)
        root.addWidget(self.pbar)

        self.lbl_durum = QLabel("")
        self.lbl_durum.setProperty("color-role", "muted")
        self.lbl_durum.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.lbl_durum)

        # Butonlar
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_iptal = QPushButton("İptal")
        btn_iptal.setProperty("style-role", "secondary")
        btn_iptal.setFixedHeight(36)
        btn_iptal.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_iptal.clicked.connect(self.reject)
        btn_row.addWidget(btn_iptal)

        self.btn_baslat = QPushButton("▶  Başlat")
        self.btn_baslat.setProperty("style-role", "success-filled")
        self.btn_baslat.setFixedHeight(36)
        self.btn_baslat.setFixedWidth(120)
        self.btn_baslat.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_baslat.clicked.connect(self._baslat)
        btn_row.addWidget(self.btn_baslat)
        root.addLayout(btn_row)

    # ─── İşlem ───────────────────────────────────────────

    def _baslat(self):
        if not self.grp_fiz.isChecked() and not self.grp_sko.isChecked():
            uyari_goster(self, "En az bir muayene türü seçin.")
            return
        if not self._ekipmanlar:
            uyari_goster(self, "Ekipman listesi boş.")
            return
        if not self._db:
            hata_goster(self, "Veritabanı bağlantısı yok.")
            return

        ortak = {
            "FMuayeneTarihi": self.dt_fiz.date().toString("yyyy-MM-dd"),
            "FizikselDurum":  self.cmb_fiz.currentText(),
            "SMuayeneTarihi": self.dt_sko.date().toString("yyyy-MM-dd"),
            "SkopiDurum":     self.cmb_sko.currentText(),
            "Aciklamalar":    self.cmb_aciklama.checked_items(),
            "KontrolEden":    self.cmb_kontrol.currentText().strip(),
        }

        self.btn_baslat.setEnabled(False)
        self.pbar.setRange(0, len(self._ekipmanlar))
        self.pbar.setValue(0)
        self.pbar.setVisible(True)
        self.lbl_durum.setText(f"0 / {len(self._ekipmanlar)} işleniyor…")

        self._worker = _TopluWorker(
            self._db, self._ekipmanlar, ortak,
            self.grp_fiz.isChecked(),
            self.grp_sko.isChecked(),
        )
        self._worker.progress.connect(
            lambda cur, tot: (
                self.pbar.setValue(cur),
                self.lbl_durum.setText(f"{cur} / {tot} işlendi…"),
            )
        )
        self._worker.finished.connect(self._bitti)
        self._worker.error.connect(self._hata)
        self._worker.start()

    def _bitti(self, ok: int):
        self.pbar.setVisible(False)
        self.lbl_durum.setText(f"✔  {ok} / {len(self._ekipmanlar)} kayıt eklendi.")
        self.btn_baslat.setEnabled(True)
        self.accept()

    def _hata(self, msg: str):
        self.pbar.setVisible(False)
        self.btn_baslat.setEnabled(True)
        self.lbl_durum.setText("")
        hata_goster(self, msg)

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(500)
        event.accept()

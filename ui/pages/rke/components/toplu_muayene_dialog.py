# -*- coding: utf-8 -*-
import os

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QHBoxLayout, QDateEdit, QComboBox,
    QLabel, QGridLayout, QListWidget, QProgressBar, QPushButton,
    QFileDialog, QMessageBox,
)
from PySide6.QtGui import QCursor

from ui.styles.colors import DarkTheme


# _S_PAGE kaldırıldı — global QSS kuralı geçerli
# _S_DATE kaldırıldı — global QSS kuralı geçerli
# _S_COMBO kaldırıldı — global QSS kuralı geçerli
# _S_TABLE kaldırıldı — global QSS kuralı geçerli
# _S_PBAR kaldırıldı — global QSS kuralı geçerli


class TopluMuayeneDialog(QDialog):
    def __init__(
        self,
        secilen_ekipmanlar,
        teknik_aciklamalar,
        kontrol_listesi,
        sorumlu_listesi,
        kullanici_adi=None,
        parent=None,
        db_path=None,
        use_sheets=True,
        checkable_combo_cls=None,
        worker_cls=None,
    ):
        super().__init__(parent)
        self._db_path = db_path
        self._use_sheets = use_sheets
        self._worker_cls = worker_cls
        self._checkable_combo_cls = checkable_combo_cls

        self.ekipmanlar = secilen_ekipmanlar
        self.teknik_aciklamalar = teknik_aciklamalar
        self.kontrol_listesi = kontrol_listesi
        self.sorumlu_listesi = sorumlu_listesi
        self.kullanici_adi = kullanici_adi
        self.dosya_yolu = None

        self.setWindowTitle(f"Toplu Muayene - {len(self.ekipmanlar)} Ekipman")
        self.resize(640, 600)
        # setStyleSheet kaldırıldı (_S_PAGE) — global QSS
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        grp_list = QGroupBox(f"Seçili Ekipmanlar ({len(self.ekipmanlar)})")
        # tema otomatik — grp_list
        gl = QVBoxLayout(grp_list)
        lst = QListWidget()
        # setStyleSheet kaldırıldı (_S_TABLE) — global QSS
        lst.setFixedHeight(90)
        lst.addItems(self.ekipmanlar)
        gl.addWidget(lst)
        root.addWidget(grp_list)

        self.grp_fiz = QGroupBox("Fiziksel Muayene")
        self.grp_fiz.setCheckable(True)
        self.grp_fiz.setChecked(True)
        # tema otomatik — self.grp_fiz
        hf = QHBoxLayout(self.grp_fiz)
        hf.setSpacing(12)
        self.dt_fiz = QDateEdit(QDate.currentDate())
        self.dt_fiz.setCalendarPopup(True)
        # setStyleSheet kaldırıldı (_S_DATE) — global QSS
        self.dt_fiz.setFixedHeight(28)
        self.cmb_fiz = QComboBox()
        # setStyleSheet kaldırıldı (_S_COMBO) — global QSS
        self.cmb_fiz.setFixedHeight(28)
        self.cmb_fiz.addItems(["Kullanıma Uygun", "Kullanıma Uygun Değil"])
        lbl_t = QLabel("Tarih:")
        lbl_t.setProperty("color-role", "muted")
        lbl_t.setProperty("color-role", "muted")
        lbl_t.style().unpolish(lbl_t)
        lbl_t.style().polish(lbl_t)
        lbl_d = QLabel("Durum:")
        lbl_d.setProperty("color-role", "muted")
        lbl_d.setProperty("color-role", "muted")
        lbl_d.style().unpolish(lbl_d)
        lbl_d.style().polish(lbl_d)
        hf.addWidget(lbl_t)
        hf.addWidget(self.dt_fiz)
        hf.addWidget(lbl_d)
        hf.addWidget(self.cmb_fiz)
        root.addWidget(self.grp_fiz)
        self.chk_fiz = self.grp_fiz

        self.grp_sko = QGroupBox("Skopi Muayene")
        self.grp_sko.setCheckable(True)
        self.grp_sko.setChecked(False)
        # tema otomatik — self.grp_sko
        hs = QHBoxLayout(self.grp_sko)
        hs.setSpacing(12)
        self.dt_sko = QDateEdit(QDate.currentDate())
        self.dt_sko.setCalendarPopup(True)
        # setStyleSheet kaldırıldı (_S_DATE) — global QSS
        self.dt_sko.setFixedHeight(28)
        self.cmb_sko = QComboBox()
        # setStyleSheet kaldırıldı (_S_COMBO) — global QSS
        self.cmb_sko.setFixedHeight(28)
        self.cmb_sko.addItems(["Kullanıma Uygun", "Kullanıma Uygun Değil", "Yapılmadı"])
        lbl_t2 = QLabel("Tarih:")
        lbl_t2.setProperty("color-role", "muted")
        lbl_t2.setProperty("color-role", "muted")
        lbl_t2.style().unpolish(lbl_t2)
        lbl_t2.style().polish(lbl_t2)
        lbl_d2 = QLabel("Durum:")
        lbl_d2.setProperty("color-role", "muted")
        lbl_d2.setProperty("color-role", "muted")
        lbl_d2.style().unpolish(lbl_d2)
        lbl_d2.style().polish(lbl_d2)
        hs.addWidget(lbl_t2)
        hs.addWidget(self.dt_sko)
        hs.addWidget(lbl_d2)
        hs.addWidget(self.cmb_sko)
        root.addWidget(self.grp_sko)
        self.chk_sko = self.grp_sko

        grp_ortak = QGroupBox("Ortak Bilgiler")
        # tema otomatik — grp_ortak
        og = QGridLayout(grp_ortak)
        og.setContentsMargins(8, 8, 8, 8)
        og.setSpacing(8)

        lbl_ke = QLabel("Kontrol Eden:")
        lbl_ke.setProperty("color-role", "muted")
        lbl_ke.setProperty("color-role", "muted")
        lbl_ke.style().unpolish(lbl_ke)
        lbl_ke.style().polish(lbl_ke)
        self.cmb_kontrol = QComboBox()
        self.cmb_kontrol.setEditable(True)
        # setStyleSheet kaldırıldı (_S_COMBO) — global QSS
        self.cmb_kontrol.setFixedHeight(28)
        self.cmb_kontrol.addItems(self.kontrol_listesi)
        if self.kullanici_adi:
            self.cmb_kontrol.setCurrentText(self.kullanici_adi)

        lbl_bs = QLabel("Birim Sorumlusu:")
        lbl_bs.setProperty("color-role", "muted")
        lbl_bs.setProperty("color-role", "muted")
        lbl_bs.style().unpolish(lbl_bs)
        lbl_bs.style().polish(lbl_bs)
        self.cmb_sorumlu = QComboBox()
        self.cmb_sorumlu.setEditable(True)
        # setStyleSheet kaldırıldı (_S_COMBO) — global QSS
        self.cmb_sorumlu.setFixedHeight(28)
        self.cmb_sorumlu.addItems(self.sorumlu_listesi)

        og.addWidget(lbl_ke, 0, 0)
        og.addWidget(self.cmb_kontrol, 0, 1)
        og.addWidget(lbl_bs, 0, 2)
        og.addWidget(self.cmb_sorumlu, 0, 3)

        lbl_acik = QLabel("Teknik Açıklama:")
        lbl_acik.setProperty("color-role", "muted")
        lbl_acik.setProperty("color-role", "muted")
        lbl_acik.style().unpolish(lbl_acik)
        lbl_acik.style().polish(lbl_acik)

        if not self._checkable_combo_cls:
            QMessageBox.critical(self, "Hata", "CheckableComboBox sınıfı bulunamadı.")
            self.reject()
            return

        self.cmb_aciklama = self._checkable_combo_cls()
        # setStyleSheet kaldırıldı (_S_COMBO) — global QSS
        self.cmb_aciklama.setFixedHeight(28)
        self.cmb_aciklama.addItems(self.teknik_aciklamalar)
        og.addWidget(lbl_acik, 1, 0, 1, 1)
        og.addWidget(self.cmb_aciklama, 1, 1, 1, 3)

        file_row = QHBoxLayout()
        self.lbl_file = QLabel("Dosya seçilmedi")
        self.lbl_file.setProperty("color-role", "muted")
        self.lbl_file.setProperty("color-role", "muted")
        self.lbl_file.style().unpolish(self.lbl_file)
        self.lbl_file.style().polish(self.lbl_file)
        btn_file = QPushButton("Ortak Rapor")
        btn_file.setProperty("style-role", "upload")
        btn_file.setFixedHeight(28)
        btn_file.clicked.connect(self._dosya_sec)
        file_row.addWidget(self.lbl_file, 1)
        file_row.addWidget(btn_file)
        og.addLayout(file_row, 2, 0, 1, 4)
        root.addWidget(grp_ortak)

        self.pbar = QProgressBar()
        self.pbar.setVisible(False)
        self.pbar.setFixedHeight(3)
        # setStyleSheet kaldırıldı (_S_PBAR) — global QSS
        root.addWidget(self.pbar)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_iptal = QPushButton("İptal")
        btn_iptal.setProperty("style-role", "secondary")
        btn_iptal.setFixedHeight(36)
        btn_iptal.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_iptal.clicked.connect(self.reject)

        self.btn_kaydet = QPushButton("▶ Başlat")
        self.btn_kaydet.setProperty("style-role", "success-filled")
        self.btn_kaydet.setFixedHeight(36)
        self.btn_kaydet.setFixedWidth(120)
        self.btn_kaydet.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_kaydet.clicked.connect(self.kaydet)

        btn_row.addWidget(btn_iptal)
        btn_row.addWidget(self.btn_kaydet)
        root.addLayout(btn_row)

    def _dosya_sec(self):
        yol, _ = QFileDialog.getOpenFileName(self, "Rapor", "", "PDF/Resim (*.pdf *.jpg)")
        if yol:
            self.dosya_yolu = yol
            self.lbl_file.setText(os.path.basename(yol))

    def kaydet(self):
        if not self.chk_fiz.isChecked() and not self.chk_sko.isChecked():
            QMessageBox.warning(self, "Uyarı", "En az bir muayene türü seçin.")
            return

        if not self._worker_cls:
            QMessageBox.critical(self, "Hata", "Toplu kayıt worker sınıfı bulunamadı.")
            return

        ortak_veri = {
            "F_MuayeneTarihi": self.dt_fiz.date().toString("yyyy-MM-dd"),
            "FizikselDurum": self.cmb_fiz.currentText(),
            "S_MuayeneTarihi": self.dt_sko.date().toString("yyyy-MM-dd"),
            "SkopiDurum": self.cmb_sko.currentText(),
            "Aciklamalar": self.cmb_aciklama.getCheckedItems(),
            "KontrolEden": self.cmb_kontrol.currentText(),
            "BirimSorumlusu": self.cmb_sorumlu.currentText(),
            "Not": "Toplu Kayıt",
        }

        self.btn_kaydet.setEnabled(False)
        self.pbar.setVisible(True)
        self.pbar.setRange(0, len(self.ekipmanlar))

        self.worker = self._worker_cls(
            self.ekipmanlar,
            ortak_veri,
            self.dosya_yolu,
            self.chk_fiz.isChecked(),
            self.chk_sko.isChecked(),
            db_path=self._db_path,
            use_sheets=self._use_sheets,
        )
        self.worker.progress.connect(self.pbar.setValue)
        self.worker.finished.connect(self.accept)
        self.worker.error.connect(lambda e: QMessageBox.critical(self, "Hata", e))
        self.worker.start()

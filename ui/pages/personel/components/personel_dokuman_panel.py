# -*- coding: utf-8 -*-
"""
Personel Dokuman Panel

Personel ile ilgili belgeleri yönetir.
Belge türü | Belge adı | Açıklama | Tarih
"""
import os
import subprocess
import platform
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QComboBox, QLineEdit,
    QMessageBox, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QCursor, QColor

from ui.styles import DarkTheme
from ui.styles.components import STYLES as S
from core.logger import logger
from core.storage.storage_service import StorageService
from database.repository_registry import RepositoryRegistry

C = DarkTheme
_ACCENT = getattr(C, "ACCENT", "#4d9de0")
_TEXT_SEC = getattr(C, "TEXT_SECONDARY", "#7a93ad")


class PersonelDokumanPanel(QWidget):
    saved = Signal()

    def __init__(self, personel_id, db=None, sabitler_cache=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.personel_id = str(personel_id) if personel_id else ""
        self.sabitler_cache = sabitler_cache
        self.dokumanlari = []
        self.belge_turleri = []
        self._storage = StorageService(self.db, sabitler_cache=self.sabitler_cache)

        self._setup_ui()
        self._load_belge_turleri()
        self._load_dokumanlari()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(S.get("scroll", ""))

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        root = QVBoxLayout(content)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # Upload panel
        upload_frame = QFrame()
        upload_frame.setStyleSheet(
            f"background: rgba(255,255,255,0.03);"
            f"border: 1px solid rgba(255,255,255,0.07);"
            f"border-radius: 8px;"
        )
        upload_layout = QVBoxLayout(upload_frame)
        upload_layout.setContentsMargins(14, 12, 14, 12)
        upload_layout.setSpacing(10)

        title = QLabel("📎  Belge Yükle")
        title.setStyleSheet(f"color: {_ACCENT}; font-size: 13px; font-weight: 700;")
        upload_layout.addWidget(title)

        # Belge türü
        row1 = QHBoxLayout()
        row1.setSpacing(10)
        lbl_type = QLabel("Belge Türü:")
        lbl_type.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 11px; font-weight: 600;")
        lbl_type.setMinimumWidth(90)
        self.combo_type = QComboBox()
        self.combo_type.setStyleSheet(S.get("input_combo", ""))
        self.combo_type.setMinimumHeight(30)
        row1.addWidget(lbl_type)
        row1.addWidget(self.combo_type, 1)
        upload_layout.addLayout(row1)

        # Dosya seçme
        row2 = QHBoxLayout()
        row2.setSpacing(10)
        self.lbl_file = QLineEdit()
        self.lbl_file.setPlaceholderText("Dosya seçilmedi...")
        self.lbl_file.setReadOnly(True)
        self.lbl_file.setStyleSheet(S.get("input_field", ""))
        self.lbl_file.setMinimumHeight(30)
        btn_browse = QPushButton("📁 Dosya Seç")
        btn_browse.setStyleSheet(S.get("btn_action", ""))
        btn_browse.setMinimumHeight(30)
        btn_browse.setMinimumWidth(100)
        btn_browse.clicked.connect(self._browse_file)
        row2.addWidget(self.lbl_file, 1)
        row2.addWidget(btn_browse)
        upload_layout.addLayout(row2)

        # Açıklama
        row3 = QHBoxLayout()
        row3.setSpacing(10)
        lbl_desc = QLabel("Açıklama:")
        lbl_desc.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 11px; font-weight: 600;")
        lbl_desc.setMinimumWidth(90)
        self.inp_desc = QLineEdit()
        self.inp_desc.setPlaceholderText("Belge hakkında notlar...")
        self.inp_desc.setStyleSheet(S.get("input_field", ""))
        self.inp_desc.setMinimumHeight(30)
        row3.addWidget(lbl_desc)
        row3.addWidget(self.inp_desc, 1)
        upload_layout.addLayout(row3)

        # Yükle butonu
        row4 = QHBoxLayout()
        row4.setSpacing(10)
        self.btn_upload = QPushButton("✓ Belgeyi Yükle")
        self.btn_upload.setStyleSheet(S.get("save_btn", ""))
        self.btn_upload.setMinimumHeight(34)
        self.btn_upload.clicked.connect(self._upload_dokuman)
        row4.addStretch()
        row4.addWidget(self.btn_upload)
        upload_layout.addLayout(row4)

        root.addWidget(upload_frame)

        # Liste
        list_title = QLabel("Yüklü Belgeler")
        list_title.setStyleSheet(
            f"color: {_ACCENT}; font-size: 12px; font-weight: 700; "
            f"padding: 8px 0px;"
        )
        root.addWidget(list_title)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ["Belge Türü", "Dosya Adı", "Açıklama", "Yüklenme Tarihi"]
        )
        self.table.setStyleSheet(S.get("table", ""))
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(200)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.doubleClicked.connect(self._open_dokuman)
        self.table.setToolTip("Dosyayı açmak için çift tıklayın")
        root.addWidget(self.table)

        root.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _load_belge_turleri(self):
        """Sabitlerden belge türlerini yükler. Yoksa default set."""
        try:
            if not self.db:
                self._disable_upload("Veritabanı bağlantısı yok.")
                return
            repo = RepositoryRegistry(self.db).get("Sabitler")
            turleri = repo.get_where({"Kod": "Personel_Belge_Tur"})
            if turleri:
                self.belge_turleri = [t.get("MenuEleman", "") for t in turleri if t.get("MenuEleman")]
                self.combo_type.addItems(self.belge_turleri)
                if "Diğer belge" not in self.belge_turleri:
                    self.combo_type.addItem("Diğer belge")
            else:
                self._disable_upload("Sabitler'de Personel_Belge_Tur bulunamadı.")
        except Exception as e:
            logger.warning(f"Personel belge türleri yüklenemedi: {e}")
            self._disable_upload("Belge türleri yüklenemedi.")

    def _disable_upload(self, reason: str):
        self.combo_type.clear()
        self.combo_type.addItem("Belge türü yok")
        self.combo_type.setEnabled(False)
        if hasattr(self, "btn_upload"):
            self.btn_upload.setEnabled(False)
        QMessageBox.warning(self, "Belge Türü", reason)

    def _browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Belge Seç",
            "",
            "Belgeler (*.pdf *.doc *.docx *.xlsx *.xls *.jpg *.png *.txt);;Tüm Dosyalar (*.*)"
        )
        if file_path:
            self.lbl_file.setText(file_path)

    def _upload_dokuman(self):
        file_path = self.lbl_file.text().strip()
        belge_tur = self.combo_type.currentText()
        aciklama = self.inp_desc.text().strip()

        if not file_path:
            QMessageBox.warning(self, "Hata", "Lütfen bir dosya seçin.")
            return
        if not belge_tur or belge_tur == "Belge türü yok":
            QMessageBox.warning(self, "Hata", "Lütfen belge türü seçin.")
            return
        if belge_tur == "Diğer belge" and not aciklama:
            QMessageBox.warning(self, "Hata", "Diğer belge için açıklama zorunludur.")
            return

        try:
            _, ext = os.path.splitext(file_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_tur = belge_tur.replace(" ", "_")
            dst_name = f"{self.personel_id}_{safe_tur}_{timestamp}{ext}"

            upload_result = self._storage.upload(
                file_path=file_path,
                folder_name="Personel_Belge",
                custom_name=dst_name
            )
            if upload_result.get("mode") == "none":
                QMessageBox.critical(self, "Hata", f"Yükleme başarısız: {upload_result.get('error')}")
                return

            repo = RepositoryRegistry(self.db).get("Dokumanlar")
            data = {
                "EntityType": "personel",
                "EntityId": self.personel_id,
                "BelgeTuru": belge_tur,
                "Belge": dst_name,
                "DocType": "Personel_Belge",
                "DisplayName": os.path.basename(file_path),
                "LocalPath": upload_result.get("local_path") or "",
                "DrivePath": upload_result.get("drive_link") or "",
                "BelgeAciklama": aciklama,
                "YuklenmeTarihi": datetime.now().isoformat(),
                "IliskiliBelgeID": None,
                "IliskiliBelgeTipi": None,
            }
            repo.insert(data)

            self.lbl_file.clear()
            self.inp_desc.clear()
            self._load_dokumanlari()

            QMessageBox.information(self, "Başarılı", f"Belge yüklendi: {belge_tur}")
            self.saved.emit()

        except Exception as e:
            logger.error(f"Belge yükleme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Yükleme başarısız:\n{e}")

    def _load_dokumanlari(self):
        try:
            if not self.db or not self.personel_id:
                self.table.setRowCount(0)
                return

            repo = RepositoryRegistry(self.db).get("Dokumanlar")
            self.dokumanlari = repo.get_where({
                "EntityType": "personel",
                "EntityId": self.personel_id
            })

            self.table.setRowCount(len(self.dokumanlari))

            for row, doc in enumerate(self.dokumanlari):
                belge_tur = doc.get("BelgeTuru", "")
                belge_dosya = doc.get("DisplayName") or doc.get("Belge", "")
                aciklama = doc.get("BelgeAciklama", "")
                yuklenme_tarihi = doc.get("YuklenmeTarihi", "")

                if yuklenme_tarihi:
                    try:
                        dt = datetime.fromisoformat(yuklenme_tarihi)
                        tarih_str = dt.strftime("%d.%m.%Y %H:%M")
                    except:
                        tarih_str = yuklenme_tarihi[:16] if len(yuklenme_tarihi) > 16 else yuklenme_tarihi
                else:
                    tarih_str = "-"

                item_tur = QTableWidgetItem(belge_tur)
                item_dosya = QTableWidgetItem(belge_dosya)
                item_dosya.setToolTip("Çift tıklayarak dosyayı aç")
                item_dosya.setForeground(QColor(_ACCENT))
                item_aciklama = QTableWidgetItem(aciklama or "-")
                item_tarih = QTableWidgetItem(tarih_str)

                self.table.setItem(row, 0, item_tur)
                self.table.setItem(row, 1, item_dosya)
                self.table.setItem(row, 2, item_aciklama)
                self.table.setItem(row, 3, item_tarih)

        except Exception as e:
            logger.error(f"Belgeler yüklenemedi: {e}")

    def _open_dokuman(self, index):
        if index.column() != 1:
            return
        row = index.row()
        if row >= len(self.dokumanlari):
            return

        doc = self.dokumanlari[row]
        belge_dosya = doc.get("Belge", "")
        drive_link = doc.get("DrivePath", "")
        local_path = doc.get("LocalPath", "")
        if not belge_dosya:
            return

        try:
            if drive_link:
                QDesktopServices.openUrl(QUrl(drive_link))
                return

            if not local_path or not os.path.exists(local_path):
                QMessageBox.warning(
                    self, "Dosya Bulunamadı",
                    f"Dosya bulunamadı:\n{local_path}\n\nDosya silinmiş veya taşınmış olabilir."
                )
                return

            if platform.system() == 'Windows':
                os.startfile(str(local_path))
            elif platform.system() == 'Darwin':
                subprocess.run(['open', str(local_path)])
            else:
                subprocess.run(['xdg-open', str(local_path)])
        except Exception as e:
            logger.error(f"Belge açma hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Dosya açılamadı:\n{e}")

    def load_data(self):
        self._load_dokumanlari()

# -*- coding: utf-8 -*-
"""
Cihaz Dokuman Panel
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Cihaz ile ilgili belgeleri yÃ¶netir.
Belge tÃ¼rÃ¼ | Belge adÄ± | AÃ§Ä±klama | Tarih | Ä°ÅŸlemler
"""
import os
import subprocess
import platform
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QSizePolicy, QComboBox, QLineEdit,
    QMessageBox, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QIcon, QDesktopServices, QCursor, QColor

from ui.styles import DarkTheme
from ui.styles.components import STYLES as S
from core.logger import logger
from database.repository_registry import RepositoryRegistry
from core.storage.storage_service import StorageService

C = DarkTheme

_ACCENT    = getattr(C, "ACCENT",         "#4d9de0")
_TEXT_PRI  = getattr(C, "TEXT_PRIMARY",   "#dce8f5")
_TEXT_SEC  = getattr(C, "TEXT_SECONDARY", "#7a93ad")
_SUCCESS   = "#4caf6e"
_ERROR     = "#e05c5c"


class CihazDokumanPanel(QWidget):
    """
    Cihaz Teknik Belgeler sekmesi.
    Belgeleri yÃ¶netir, yÃ¼kler, listeler, siler.
    """
    saved = Signal()  # Belge iÅŸlemi tamamlandÄ±ÄŸÄ±nda emit et

    def __init__(self, cihaz_id, db=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.cihaz_id = str(cihaz_id) if cihaz_id else ""
        self.dokumanlari = []
        self.belge_turleri = []
        
        # Hibrit storage servisi
        self._storage = StorageService(self.db)
        self._setup_ui()
        self._load_belge_turleri()
        self._load_dokumanlari()

    def _setup_ui(self):
        """UI oluÅŸtur."""
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

        # â”€â”€ 0. Cihaz ID Durumu â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if not self.cihaz_id:
            info_label = QLabel("âš ï¸  LÃ¼tfen Ã¶nce ana formda cihazÄ± kaydedin")
            info_label.setStyleSheet(
                f"color: {_ERROR}; font-size: 12px; "
                f"background: rgba(224, 92, 92, 0.1); "
                f"border: 1px solid rgba(224, 92, 92, 0.3); "
                f"border-radius: 6px; padding: 10px;"
            )
            root.addWidget(info_label)

        # â”€â”€ 1. Belge YÃ¼kleme Paneli â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        upload_frame = QFrame()
        upload_frame.setStyleSheet(
            f"background: rgba(255,255,255,0.03);"
            f"border: 1px solid rgba(255,255,255,0.07);"
            f"border-radius: 8px;"
        )
        upload_layout = QVBoxLayout(upload_frame)
        upload_layout.setContentsMargins(14, 12, 14, 12)
        upload_layout.setSpacing(10)

        title = QLabel("ğŸ“„  Belge YÃ¼kle")
        title.setStyleSheet(f"color: {_ACCENT}; font-size: 13px; font-weight: 700;")
        upload_layout.addWidget(title)

        # Belge tÃ¼rÃ¼
        row1 = QHBoxLayout()
        row1.setSpacing(10)
        lbl_type = QLabel("Belge TÃ¼rÃ¼:")
        lbl_type.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 11px; font-weight: 600;")
        lbl_type.setMinimumWidth(80)
        self.combo_type = QComboBox()
        self.combo_type.setStyleSheet(S.get("input_combo", ""))
        self.combo_type.setMinimumHeight(30)
        row1.addWidget(lbl_type)
        row1.addWidget(self.combo_type, 1)
        upload_layout.addLayout(row1)

        # Dosya seÃ§me
        row2 = QHBoxLayout()
        row2.setSpacing(10)
        self.lbl_file = QLineEdit()
        self.lbl_file.setPlaceholderText("Dosya seÃ§ilmedi...")
        self.lbl_file.setReadOnly(True)
        self.lbl_file.setStyleSheet(S.get("input_field", ""))
        self.lbl_file.setMinimumHeight(30)
        btn_browse = QPushButton("ğŸ“ Dosya SeÃ§")
        btn_browse.setStyleSheet(S.get("btn_action", ""))
        btn_browse.setMinimumHeight(30)
        btn_browse.setMinimumWidth(100)
        btn_browse.clicked.connect(self._browse_file)
        row2.addWidget(self.lbl_file, 1)
        row2.addWidget(btn_browse)
        upload_layout.addLayout(row2)

        # AÃ§Ä±klama
        row3 = QHBoxLayout()
        row3.setSpacing(10)
        lbl_desc = QLabel("AÃ§Ä±klama:")
        lbl_desc.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 11px; font-weight: 600;")
        lbl_desc.setMinimumWidth(80)
        self.inp_desc = QLineEdit()
        self.inp_desc.setPlaceholderText("Belge hakkÄ±nda notlar...")
        self.inp_desc.setStyleSheet(S.get("input_field", ""))
        self.inp_desc.setMinimumHeight(30)
        row3.addWidget(lbl_desc)
        row3.addWidget(self.inp_desc, 1)
        upload_layout.addLayout(row3)

        # YÃ¼kle butonlarÄ±
        row4 = QHBoxLayout()
        row4.setSpacing(10)
        btn_upload = QPushButton("âœ“ Belgeyi YÃ¼kle")
        btn_upload.setStyleSheet(S.get("save_btn", ""))
        btn_upload.setMinimumHeight(34)
        btn_upload.clicked.connect(self._upload_dokuman)
        row4.addStretch()
        row4.addWidget(btn_upload)
        upload_layout.addLayout(row4)

        # Upload frame'i disable et (cihaz_id boÅŸ ise)
        if not self.cihaz_id:
            for widget in upload_frame.findChildren(QWidget):
                widget.setEnabled(False)

        root.addWidget(upload_frame)

        # â”€â”€ 2. Belgeler Listesi â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        list_title = QLabel("YÃ¼klÃ¼ Belgeler")
        list_title.setStyleSheet(
            f"color: {_ACCENT}; font-size: 12px; font-weight: 700; "
            f"padding: 8px 0px;"
        )
        root.addWidget(list_title)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ["Belge TÃ¼rÃ¼", "Dosya AdÄ±", "AÃ§Ä±klama", "YÃ¼klenme Tarihi"]
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
        self.table.setToolTip("DosyayÄ± aÃ§mak iÃ§in Ã§ift tÄ±klayÄ±n")
        root.addWidget(self.table)

        root.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _load_belge_turleri(self):
        """Sabitler tablosundan belge tÃ¼rlerini yÃ¼kle."""
        try:
            if not self.db:
                logger.warning("DB baÄŸlantÄ±sÄ± yok, default belge tÃ¼rleri kullanÄ±lÄ±yor")
                self.combo_type.addItems([
                    "NDK LisansÄ±", "RKS Belgesi", "Sorumlu DiplomasÄ±",
                    "KullanÄ±m Klavuzu", "Cihaz SertifikasÄ±", "Teknik Veri SayfasÄ±", 
                    "Garanti Belgesi"
                ])
                return
            
            repo = RepositoryRegistry(self.db).get("Sabitler")
            turleri = repo.get_where({"Kod": "Cihaz_Belge_Tur"})
            
            if turleri:
                self.belge_turleri = [t.get("MenuEleman", "") for t in turleri]
                self.combo_type.addItems(self.belge_turleri)
                logger.info(f"âœ“ {len(self.belge_turleri)} belge tÃ¼rÃ¼ yÃ¼klendi")
            else:
                logger.warning("Sabitler'de 'Cihaz_Belge_Tur' bulunamadÄ±, default kullanÄ±lÄ±yor")
                self.combo_type.addItems([
                    "NDK LisansÄ±", "RKS Belgesi", "Sorumlu DiplomasÄ±",
                    "KullanÄ±m Klavuzu", "Cihaz SertifikasÄ±", "Teknik Veri SayfasÄ±", 
                    "Garanti Belgesi"
                ])
        except Exception as e:
            logger.warning(f"Belge tÃ¼rleri yÃ¼klenemedi: {e}")
            self.combo_type.addItems([
                "NDK LisansÄ±", "RKS Belgesi", "Sorumlu DiplomasÄ±",
                "KullanÄ±m Klavuzu", "Cihaz SertifikasÄ±", "Teknik Veri SayfasÄ±", 
                "Garanti Belgesi"
            ])

    def _browse_file(self):
        """Dosya seÃ§ dialog."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Belge SeÃ§",
            "",
            "Belgeler (*.pdf *.doc *.docx *.xlsx *.xls *.jpg *.png *.txt);;TÃ¼m Dosyalar (*.*)"
        )
        if file_path:
            self.lbl_file.setText(file_path)

    def _upload_dokuman(self):
        """Belgeyi yükle ve DB'ye kaydet."""
        file_path = self.lbl_file.text().strip()
        belge_tur = self.combo_type.currentText()
        aciklama = self.inp_desc.text().strip()

        if not file_path:
            QMessageBox.warning(self, "Hata", "Lütfen bir dosya seçin.")
            return

        if not belge_tur:
            QMessageBox.warning(self, "Hata", "Lütfen belge türü seçin.")
            return

        try:
            # Dosya adını oluştur: CihazID_BelgeTuru_Tarih.ext
            _, ext = os.path.splitext(file_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_tur = belge_tur.replace(" ", "_")
            dst_name = f"{self.cihaz_id}_{safe_tur}_{timestamp}{ext}"

            # Hibrit yükleme (Drive varsa Drive, yoksa local)
            upload_result = self._storage.upload(
                file_path=file_path,
                folder_name="Cihaz_Belgeler",
                custom_name=dst_name
            )

            if upload_result.get("mode") == "none":
                QMessageBox.critical(self, "Hata", f"Yükleme başarısız: {upload_result.get('error')}")
                return

            # DB'ye kaydet (Dokumanlar)
            repo = RepositoryRegistry(self.db).get("Dokumanlar")
            data = {
                "EntityType": "cihaz",
                "EntityId": self.cihaz_id,
                "BelgeTuru": belge_tur,
                "Belge": dst_name,
                "DocType": "Cihaz_Belge",
                "DisplayName": os.path.basename(file_path),
                "LocalPath": upload_result.get("local_path") or "",
                "DrivePath": upload_result.get("drive_link") or "",
                "BelgeAciklama": aciklama,
                "YuklenmeTarihi": datetime.now().isoformat(),
                "IliskiliBelgeID": None,
                "IliskiliBelgeTipi": None,
            }
            repo.insert(data)

            logger.info(f"Belge DB'ye kaydedildi: {data}")

            # UI güncelle
            self.lbl_file.clear()
            self.inp_desc.clear()
            self._load_dokumanlari()

            QMessageBox.information(
                self, "Başarılı", f"Belge yüklendi: {belge_tur}"
            )
            self.saved.emit()

        except Exception as e:
            logger.error(f"Belge yükleme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Yükleme başarısız:\n{e}")
    def _load_dokumanlari(self):
        """DB'den belgeleri yükle ve tabloya doldur."""
        try:
            if not self.db or not self.cihaz_id:
                self.table.setRowCount(0)
                return

            repo = RepositoryRegistry(self.db).get("Dokumanlar")
            self.dokumanlari = repo.get_where({
                "EntityType": "cihaz",
                "EntityId": self.cihaz_id
            })

            self.table.setRowCount(len(self.dokumanlari))

            for row, doc in enumerate(self.dokumanlari):
                belge_tur = doc.get("BelgeTuru", "")
                belge_dosya = doc.get("DisplayName") or doc.get("Belge", "")
                aciklama = doc.get("BelgeAciklama", "")
                yuklenme_tarihi = doc.get("YuklenmeTarihi", "")

                # Tarih formatını düzenle
                if yuklenme_tarihi:
                    try:
                        dt = datetime.fromisoformat(yuklenme_tarihi)
                        tarih_str = dt.strftime("%d.%m.%Y %H:%M")
                    except:
                        tarih_str = yuklenme_tarihi[:16] if len(yuklenme_tarihi) > 16 else yuklenme_tarihi
                else:
                    tarih_str = "-"

                # Tabloya ekle
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
        """Tabloda çift tıklanan dosyayı aç."""
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
                logger.info(f"Belge Drive linki ile açıldı: {belge_dosya}")
                return

            if not local_path or not os.path.exists(local_path):
                QMessageBox.warning(
                    self,
                    "Dosya Bulunamadı",
                    f"Dosya bulunamadı:\n{local_path}\n\nDosya silinmiş veya taşınmış olabilir."
                )
                return

            # Dosyayı varsayılan uygulamayla aç
            if platform.system() == 'Windows':
                os.startfile(str(local_path))
            elif platform.system() == 'Darwin':
                subprocess.run(['open', str(local_path)])
            else:
                subprocess.run(['xdg-open', str(local_path)])

            logger.info(f"Belge açıldı: {belge_dosya}")
        except Exception as e:
            logger.error(f"Belge açma hatası: {e}")
            QMessageBox.critical(
                self,
                "Hata",
                f"Dosya açılamadı:\n{e}"
            )

    def set_cihaz_id(self, cihaz_id: str):
        """Cihaz ID'sini set et ve UI'Ä± enable et."""
        self.cihaz_id = str(cihaz_id) if cihaz_id else ""
        
        # Upload frame'Ã¼ enable et
        if self.cihaz_id:
            # TÃ¼m widget'larÄ± enable et
            for widget in self.findChildren(QWidget):
                widget.setEnabled(True)
            self._load_dokumanlari()
            logger.info(f"Belgeler paneli aktif: {self.cihaz_id}")
        else:
            # Cihaz ID yoksa tabloyu temizle
            self.table.setRowCount(0)

    def load_data(self):
        """Belgeleri yeniden yÃ¼kle."""
        self._load_dokumanlari()

    def set_embedded_mode(self, embedded: bool):
        """Embedded mode flag."""
        pass





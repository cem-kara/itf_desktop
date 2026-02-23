# -*- coding: utf-8 -*-
"""
Cihaz Dokuman Panel
─────────────────────────────────────
Cihaz ile ilgili belgeleri yönetir.
Belge türü | Belge adı | Açıklama | Tarih | İşlemler
"""
from pathlib import Path
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
from core.paths import DATA_DIR
from database.repository_registry import RepositoryRegistry

C = DarkTheme

_ACCENT    = getattr(C, "ACCENT",         "#4d9de0")
_TEXT_PRI  = getattr(C, "TEXT_PRIMARY",   "#dce8f5")
_TEXT_SEC  = getattr(C, "TEXT_SECONDARY", "#7a93ad")
_SUCCESS   = "#4caf6e"
_ERROR     = "#e05c5c"


class CihazDokumanPanel(QWidget):
    """
    Cihaz Teknik Belgeler sekmesi.
    Belgeleri yönetir, yükler, listeler, siler.
    """
    saved = Signal()  # Belge işlemi tamamlandığında emit et

    def __init__(self, cihaz_id, db=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.cihaz_id = str(cihaz_id) if cihaz_id else ""
        self.dokumanlari = []
        self.belge_turleri = []
        
        # Base belgeler dizini
        self._base_docs_dir = Path(DATA_DIR) / "offline_uploads" / "cihazlar" / "belgeler"
        self._base_docs_dir.mkdir(parents=True, exist_ok=True)
        
        # Cihaz ID varsa, cihaza özel klasör oluştur
        if self.cihaz_id:
            self._docs_dir = self._base_docs_dir / self.cihaz_id
            self._docs_dir.mkdir(parents=True, exist_ok=True)
        else:
            self._docs_dir = self._base_docs_dir
        
        self._setup_ui()
        self._load_belge_turleri()
        self._load_dokumanlari()

    def _setup_ui(self):
        """UI oluştur."""
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

        # ── 0. Cihaz ID Durumu ────────────────────────────────────────────
        if not self.cihaz_id:
            info_label = QLabel("⚠️  Lütfen önce ana formda cihazı kaydedin")
            info_label.setStyleSheet(
                f"color: {_ERROR}; font-size: 12px; "
                f"background: rgba(224, 92, 92, 0.1); "
                f"border: 1px solid rgba(224, 92, 92, 0.3); "
                f"border-radius: 6px; padding: 10px;"
            )
            root.addWidget(info_label)

        # ── 1. Belge Yükleme Paneli ────────────────────────────────────────
        upload_frame = QFrame()
        upload_frame.setStyleSheet(
            f"background: rgba(255,255,255,0.03);"
            f"border: 1px solid rgba(255,255,255,0.07);"
            f"border-radius: 8px;"
        )
        upload_layout = QVBoxLayout(upload_frame)
        upload_layout.setContentsMargins(14, 12, 14, 12)
        upload_layout.setSpacing(10)

        title = QLabel("📄  Belge Yükle")
        title.setStyleSheet(f"color: {_ACCENT}; font-size: 13px; font-weight: 700;")
        upload_layout.addWidget(title)

        # Belge türü
        row1 = QHBoxLayout()
        row1.setSpacing(10)
        lbl_type = QLabel("Belge Türü:")
        lbl_type.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 11px; font-weight: 600;")
        lbl_type.setMinimumWidth(80)
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
        lbl_desc.setMinimumWidth(80)
        self.inp_desc = QLineEdit()
        self.inp_desc.setPlaceholderText("Belge hakkında notlar...")
        self.inp_desc.setStyleSheet(S.get("input_field", ""))
        self.inp_desc.setMinimumHeight(30)
        row3.addWidget(lbl_desc)
        row3.addWidget(self.inp_desc, 1)
        upload_layout.addLayout(row3)

        # Yükle butonları
        row4 = QHBoxLayout()
        row4.setSpacing(10)
        btn_upload = QPushButton("✓ Belgeyi Yükle")
        btn_upload.setStyleSheet(S.get("save_btn", ""))
        btn_upload.setMinimumHeight(34)
        btn_upload.clicked.connect(self._upload_dokuman)
        row4.addStretch()
        row4.addWidget(btn_upload)
        upload_layout.addLayout(row4)

        # Upload frame'i disable et (cihaz_id boş ise)
        if not self.cihaz_id:
            for widget in upload_frame.findChildren(QWidget):
                widget.setEnabled(False)

        root.addWidget(upload_frame)

        # ── 2. Belgeler Listesi ────────────────────────────────────────────
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
        """Sabitler tablosundan belge türlerini yükle."""
        try:
            if not self.db:
                logger.warning("DB bağlantısı yok, default belge türleri kullanılıyor")
                self.combo_type.addItems([
                    "NDK Lisansı", "RKS Belgesi", "Sorumlu Diploması",
                    "Kullanım Klavuzu", "Cihaz Sertifikası", "Teknik Veri Sayfası", 
                    "Garanti Belgesi"
                ])
                return
            
            repo = RepositoryRegistry(self.db).get("Sabitler")
            turleri = repo.get_where({"Kod": "Cihaz_Belge_Tur"})
            
            if turleri:
                self.belge_turleri = [t.get("MenuEleman", "") for t in turleri]
                self.combo_type.addItems(self.belge_turleri)
                logger.info(f"✓ {len(self.belge_turleri)} belge türü yüklendi")
            else:
                logger.warning("Sabitler'de 'Cihaz_Belge_Tur' bulunamadı, default kullanılıyor")
                self.combo_type.addItems([
                    "NDK Lisansı", "RKS Belgesi", "Sorumlu Diploması",
                    "Kullanım Klavuzu", "Cihaz Sertifikası", "Teknik Veri Sayfası", 
                    "Garanti Belgesi"
                ])
        except Exception as e:
            logger.warning(f"Belge türleri yüklenemedi: {e}")
            self.combo_type.addItems([
                "NDK Lisansı", "RKS Belgesi", "Sorumlu Diploması",
                "Kullanım Klavuzu", "Cihaz Sertifikası", "Teknik Veri Sayfası", 
                "Garanti Belgesi"
            ])

    def _browse_file(self):
        """Dosya seç dialog."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Belge Seç",
            "",
            "Belgeler (*.pdf *.doc *.docx *.xlsx *.xls *.jpg *.png *.txt);;Tüm Dosyalar (*.*)"
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
            # Dosyayı lokal dizine kopyala
            src = Path(file_path)
            if not src.exists():
                QMessageBox.critical(self, "Hata", "Dosya bulunamadı.")
                return

            # Dosya adını oluştur: CihazID_BelgeTuru_Tarih.ext
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = src.suffix
            dst_name = f"{self.cihaz_id}_{belge_tur.replace(' ', '_')}_{timestamp}{ext}"
            dst = self._docs_dir / dst_name

            # Dosyayı kopyala
            dst.write_bytes(src.read_bytes())
            logger.info(f"Belge kopyalandı: {dst}")

            # DB'ye kaydet (Cihaz_Belgeler)
            repo = RepositoryRegistry(self.db).get("Cihaz_Belgeler")
            data = {
                "Cihazid": self.cihaz_id,
                "BelgeTuru": belge_tur,
                "Belge": dst_name,
                "BelgeAciklama": aciklama,
                "YuklenmeTarihi": datetime.now().isoformat(),
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

            repo = RepositoryRegistry(self.db).get("Cihaz_Belgeler")
            self.dokumanlari = repo.get_where({"Cihazid": self.cihaz_id})

            self.table.setRowCount(len(self.dokumanlari))

            for row, doc in enumerate(self.dokumanlari):
                belge_tur = doc.get("BelgeTuru", "")
                belge_dosya = doc.get("Belge", "")
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
                item_dosya.setForeground(QColor(_ACCENT))  # Tıklanabilir görünüm
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
        if index.column() != 1:  # Sadece dosya adı kolonunda
            return
        
        row = index.row()
        if row >= len(self.dokumanlari):
            return
        
        doc = self.dokumanlari[row]
        belge_dosya = doc.get("Belge", "")
        
        if not belge_dosya:
            return
        
        # Dosya yolu: belgeler/cihaz_id/dosya_adi
        file_path = self._base_docs_dir / self.cihaz_id / belge_dosya
        
        if not file_path.exists():
            QMessageBox.warning(
                self, 
                "Dosya Bulunamadı", 
                f"Dosya bulunamadı:\n{file_path}\n\nDosya silinmiş veya taşınmış olabilir."
            )
            return
        
        try:
            # Dosyayı varsayılan uygulamayla aç
            if platform.system() == 'Windows':
                os.startfile(str(file_path))
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', str(file_path)])
            else:  # Linux
                subprocess.run(['xdg-open', str(file_path)])
            
            logger.info(f"Belge açıldı: {belge_dosya}")
        except Exception as e:
            logger.error(f"Belge açma hatası: {e}")
            QMessageBox.critical(
                self, 
                "Hata", 
                f"Dosya açılamadı:\n{e}"
            )

    def set_cihaz_id(self, cihaz_id: str):
        """Cihaz ID'sini set et ve UI'ı enable et."""
        self.cihaz_id = str(cihaz_id) if cihaz_id else ""
        
        # Upload frame'ü enable et
        if self.cihaz_id:
            # Cihaz klasörünü oluştur
            self._docs_dir = self._base_docs_dir / self.cihaz_id
            self._docs_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Cihaz belgeler klasörü oluşturuldu: {self._docs_dir}")
            
            # Tüm widget'ları enable et
            for widget in self.findChildren(QWidget):
                widget.setEnabled(True)
            self._load_dokumanlari()
            logger.info(f"Belgeler paneli aktif: {self.cihaz_id}")
        else:
            # Cihaz ID yoksa tabloyu temizle
            self.table.setRowCount(0)

    def load_data(self):
        """Belgeleri yeniden yükle."""
        self._load_dokumanlari()

    def set_embedded_mode(self, embedded: bool):
        """Embedded mode flag."""
        pass

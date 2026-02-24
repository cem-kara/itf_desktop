# -*- coding: utf-8 -*-
"""Ariza Islem — ariza üzerinde yapılan işlemleri kaydetme ve görüntüleme."""
from typing import List, Dict, Any, Optional
from pathlib import Path

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QTableView,
    QHeaderView, QLabel, QGridLayout, QTextEdit, QLineEdit,
    QComboBox, QDateEdit, QPushButton, QMenu, QFileDialog, QMessageBox
)
from PySide6.QtGui import QCursor

from core.date_utils import to_ui_date
from core.logger import logger
from core.paths import DATA_DIR
from database.repository_registry import RepositoryRegistry
from ui.styles.components import STYLES as S
from ui.styles.icons import IconRenderer
from ui.styles import DarkTheme
from datetime import datetime


ISLEM_COLUMNS = [
    ("Tarih", "Tarih", 90),
    ("Saat", "Saat", 60),
    ("IslemYapan", "İşlem Yapan", 110),
    ("IslemTuru", "İşlem Türü", 110),
    ("YeniDurum", "Yeni Durum", 80),
]


class ArizaIslemTableModel(QAbstractTableModel):
    def __init__(self, rows: Optional[List[Dict[str, Any]]] = None, parent=None):
        super().__init__(parent)
        self._rows = rows or []
        self._keys = [c[0] for c in ISLEM_COLUMNS]
        self._headers = [c[1] for c in ISLEM_COLUMNS]

    def rowCount(self, parent=QModelIndex()):
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return len(ISLEM_COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        key = self._keys[index.column()]

        if role == Qt.DisplayRole:
            value = row.get(key, "")
            if key == "Tarih":
                return to_ui_date(value, "")
            return str(value)

        if role == Qt.TextAlignmentRole:
            if key in ("Tarih", "Saat", "YeniDurum"):
                return Qt.AlignCenter
            return Qt.AlignVCenter | Qt.AlignLeft

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None

    def set_rows(self, rows: List[Dict[str, Any]]):
        self.beginResetModel()
        self._rows = rows or []
        self.endResetModel()

    def get_row(self, row_idx: int) -> Optional[Dict[str, Any]]:
        if 0 <= row_idx < len(self._rows):
            return self._rows[row_idx]
        return None


class ArizaIslemForm(QWidget):
    saved = Signal()

    def __init__(self, db=None, ariza_id: Optional[str] = None, parent=None):
        super().__init__(parent)
        self._db = db
        self._ariza_id = ariza_id
        self._rapor_belge_path = None  # Seçilen belge yolu
        
        # Belgeler için dizin (cihaz_dokuman_panel ile aynı yapı)
        self._base_docs_dir = Path(DATA_DIR) / "offline_uploads" / "cihazlar" / "belgeler"
        self._base_docs_dir.mkdir(parents=True, exist_ok=True)
        
        # Arıza ID'den cihaz ID'yi çıkar
        if self._ariza_id and "-" in self._ariza_id:
            self._cihaz_id = self._ariza_id.split("-")[0]
            self._docs_dir = self._base_docs_dir / self._cihaz_id
            self._docs_dir.mkdir(parents=True, exist_ok=True)
        else:
            self._cihaz_id = None
            self._docs_dir = self._base_docs_dir
        
        self._setup_ui()

    def set_ariza_id(self, ariza_id: Optional[str]):
        self._ariza_id = ariza_id

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        form = QGroupBox("Ariza İşlemi Kaydi")
        form.setStyleSheet(S["group"])
        grid = QGridLayout(form)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(8)

        self.dt_tarih = QDateEdit()
        self.dt_tarih.setDate(QDate.currentDate())
        self.dt_tarih.setStyleSheet(S["input"])
        self._add_row(grid, 0, "Tarih", self.dt_tarih)

        self.txt_saat = QLineEdit()
        self.txt_saat.setStyleSheet(S["input"])
        self.txt_saat.setPlaceholderText("HH:MM")
        self._add_row(grid, 1, "Saat", self.txt_saat)

        self.txt_islem_yapan = QLineEdit()
        self.txt_islem_yapan.setStyleSheet(S["input"])
        self._add_row(grid, 2, "İşlem Yapan", self.txt_islem_yapan)

        self.cmb_islem_turu = QComboBox()
        self.cmb_islem_turu.setEditable(True)
        self.cmb_islem_turu.setStyleSheet(S["combo"])
        self.cmb_islem_turu.addItems([
            "Elektrik Onarımı",
            "Mekanik Onarımı",
            "Yazılım Güncellemesi",
            "Temizlik",
            "Test",
            "Bakım",
            "Diğer"
        ])
        self._add_row(grid, 3, "İşlem Türü", self.cmb_islem_turu)

        self.txt_yapilan_islem = QTextEdit()
        self.txt_yapilan_islem.setStyleSheet(S["input_text"])
        self.txt_yapilan_islem.setFixedHeight(80)
        self._add_row(grid, 4, "Yapılan İşlem", self.txt_yapilan_islem)

        self.cmb_yeni_durum = QComboBox()
        self.cmb_yeni_durum.setStyleSheet(S["combo"])
        self.cmb_yeni_durum.addItems(["Açık", "Yakında Kapanacak", "Kapalı"])
        self._add_row(grid, 5, "Yeni Durum", self.cmb_yeni_durum)

        self.txt_rapor = QTextEdit()
        self.txt_rapor.setStyleSheet(S["input_text"])
        self.txt_rapor.setFixedHeight(70)
        self._add_row(grid, 6, "Rapor (Metin)", self.txt_rapor)
        
        # Rapor Belgesi Yükleme
        belge_container = QWidget()
        belge_lay = QHBoxLayout(belge_container)
        belge_lay.setContentsMargins(0, 0, 0, 0)
        belge_lay.setSpacing(8)
        
        self.lbl_rapor_belge = QLabel("Belge seçilmedi")
        self.lbl_rapor_belge.setStyleSheet(S.get("info_label", f"color: {DarkTheme.TEXT_MUTED}; font-size: 11px;"))
        belge_lay.addWidget(self.lbl_rapor_belge, 1)
        
        self.btn_belge_sec = QPushButton("Belge Seç")
        self.btn_belge_sec.setStyleSheet(S.get("btn_refresh", ""))
        self.btn_belge_sec.setFixedWidth(100)
        self.btn_belge_sec.clicked.connect(self._select_rapor_belge)
        belge_lay.addWidget(self.btn_belge_sec)
        
        self.btn_belge_temizle = QPushButton("✕")
        self.btn_belge_temizle.setStyleSheet(S.get("btn_refresh", ""))
        self.btn_belge_temizle.setFixedWidth(30)
        self.btn_belge_temizle.clicked.connect(self._clear_rapor_belge)
        belge_lay.addWidget(self.btn_belge_temizle)
        
        self._add_row(grid, 7, "Rapor Belgesi", belge_container)

        root.addWidget(form)

        # Butonlar
        btn_lay = QHBoxLayout()
        btn_lay.setSpacing(8)

        btn_kaydet = QPushButton("Kaydet")
        btn_kaydet.setStyleSheet(S["success_btn"] if "success_btn" in S else S["refresh_btn"])
        btn_kaydet.clicked.connect(self._save)
        btn_lay.addWidget(btn_kaydet)

        btn_temizle = QPushButton("Temizle")
        btn_temizle.setStyleSheet(S["cancel_btn"] if "cancel_btn" in S else "")
        btn_temizle.clicked.connect(self._clear)
        btn_lay.addWidget(btn_temizle)

        root.addLayout(btn_lay)

    def _add_row(self, grid, row, label, widget):
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label"])
        grid.addWidget(lbl, row, 0)
        grid.addWidget(widget, row, 1)

    def _select_rapor_belge(self):
        """Rapor belgesi seçme."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Rapor Belgesi Seç",
            "",
            "Belgeler (*.pdf *.doc *.docx *.jpg *.jpeg *.png *.txt);;Tüm Dosyalar (*.*)"
        )
        if file_path:
            self._rapor_belge_path = file_path
            self.lbl_rapor_belge.setText(Path(file_path).name)
            self.lbl_rapor_belge.setStyleSheet(S.get("info_label", f"color: {DarkTheme.ACCENT}; font-size: 11px;"))
    
    def _clear_rapor_belge(self):
        """Seçilen belgeyi temizle."""
        self._rapor_belge_path = None
        self.lbl_rapor_belge.setText("Belge seçilmedi")
        self.lbl_rapor_belge.setStyleSheet(S.get("info_label", f"color: {DarkTheme.TEXT_MUTED}; font-size: 11px;"))

    def _save(self):
        if not self._db or not self._ariza_id:
            return

        tarih = self.dt_tarih.date().toString("yyyy-MM-dd")
        saat = self.txt_saat.text().strip()
        islem_yapan = self.txt_islem_yapan.text().strip()
        islem_turu = self.cmb_islem_turu.currentText().strip()
        yapilan_islem = self.txt_yapilan_islem.toPlainText().strip()
        yeni_durum = self.cmb_yeni_durum.currentText().strip()
        rapor = self.txt_rapor.toPlainText().strip()

        if not saat or not islem_yapan or not yapilan_islem:
            return

        islem_id = f"{self._ariza_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Önce işlem kaydını yap
        data = {
            "Islemid": islem_id,
            "Arizaid": self._ariza_id,
            "Tarih": tarih,
            "Saat": saat,
            "IslemYapan": islem_yapan,
            "IslemTuru": islem_turu,
            "YapilanIslem": yapilan_islem,
            "YeniDurum": yeni_durum,
            "Rapor": rapor,
        }

        try:
            repo_islem = RepositoryRegistry(self._db).get("Ariza_Islem")
            repo_islem.insert(data)
            
            # Rapor belgesi varsa Cihaz_Belgeler tablosuna kaydet
            if self._rapor_belge_path and self._cihaz_id:
                try:
                    src = Path(self._rapor_belge_path)
                    if src.exists():
                        # Dosya adı: CihazID_ArizaIslemRaporu_timestamp.ext
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        ext = src.suffix
                        belge_name = f"{self._cihaz_id}_ArizaIslemRaporu_{timestamp}{ext}"
                        dst = self._docs_dir / belge_name
                        
                        # Dosyayı kopyala
                        dst.write_bytes(src.read_bytes())
                        logger.info(f"Arıza işlem rapor belgesi kopyalandı: {dst}")
                        
                        # Cihaz_Belgeler tablosuna kaydet
                        repo_belge = RepositoryRegistry(self._db).get("Cihaz_Belgeler")
                        belge_data = {
                            "Cihazid": self._cihaz_id,
                            "BelgeTuru": "Arıza İşlem Raporu",
                            "Belge": belge_name,
                            "BelgeAciklama": f"İşlem: {islem_turu} ({islem_id})",
                            "YuklenmeTarihi": datetime.now().isoformat(),
                        }
                        repo_belge.insert(belge_data)
                        logger.info(f"Arıza işlem raporu Cihaz_Belgeler tablosuna kaydedildi")
                        
                except Exception as e:
                    logger.error(f"Rapor belgesi kaydetme hatası: {e}")
                    QMessageBox.warning(self, "Uyarı", f"Belge kaydedilemedi: {e}")
            
            self.saved.emit()
            self._clear()
        except Exception as e:
            logger.error(f"Ariza islemi kaydedilemedi: {e}")
            QMessageBox.critical(self, "Hata", f"Kayıt başarısız: {e}")

    def _clear(self):
        self.dt_tarih.setDate(QDate.currentDate())
        self.txt_saat.clear()
        self.txt_islem_yapan.clear()
        self.cmb_islem_turu.setCurrentIndex(0)
        self.txt_yapilan_islem.clear()
        self.cmb_yeni_durum.setCurrentIndex(0)
        self.txt_rapor.clear()
        self._clear_rapor_belge()


class ArizaIslemPenceresi(QWidget):
    """Seçili arıza için işlemleri listeleyen widget (sadece tablo)."""
    
    islem_secildi = Signal(dict)  # Seçili işlem detayı emit et

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._ariza_id = None
        self._model = None
        self._setup_ui()

    def set_ariza_id(self, ariza_id: Optional[str]):
        """Görüntülenecek arızayı değiştir ve işlemleri yükle."""
        self._ariza_id = ariza_id
        self.load_data()
        # İlk işlemi seç
        if self._model.rowCount() > 0:
            self.table.selectRow(0)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # Tablo grubu (kompakt)
        grp_table = QGroupBox("Ariza İşlemleri")
        grp_table.setStyleSheet(S["group"])
        tl = QVBoxLayout(grp_table)
        tl.setContentsMargins(10, 10, 10, 10)
        tl.setSpacing(6)

        self._model = ArizaIslemTableModel()
        self.table = QTableView()
        self.table.setModel(self._model)
        self.table.setStyleSheet(S["table"])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSortingEnabled(False)
        self.table.setMaximumHeight(180)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        for i, (_, _, w) in enumerate(ISLEM_COLUMNS):
            if i == len(ISLEM_COLUMNS) - 1:
                header.setSectionResizeMode(i, QHeaderView.Stretch)
            else:
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
            header.resizeSection(i, w)

        self.table.selectionModel().currentChanged.connect(self._on_row_selected)

        tl.addWidget(self.table)

        self.lbl_count = QLabel("0 kayit")
        self.lbl_count.setStyleSheet(S["footer_label"])
        tl.addWidget(self.lbl_count)

        root.addWidget(grp_table)

    def _on_row_selected(self, current: QModelIndex, previous: QModelIndex):
        """Tablo satırı seçildiğinde detayları emit et."""
        if not current.isValid():
            return

        row_data = self._model.get_row(current.row())
        if row_data:
            self.islem_secildi.emit(row_data)

    def load_data(self):
        """Seçili arızanın işlemlerini yükle."""
        if not self._db or not self._ariza_id:
            self._model.set_rows([])
            self.lbl_count.setText("0 kayit")
            return

        try:
            repo = RepositoryRegistry(self._db).get("Ariza_Islem")
            rows = repo.get_by_kod(self._ariza_id, "Arizaid")
            # En yeni işlemler altta olacak şekilde ters sırala
            rows.sort(key=lambda r: (r.get("Tarih", "") or "", r.get("Saat", "") or ""), reverse=True)
            self._model.set_rows(rows)

            count = len(rows)
            self.lbl_count.setText(f"{count} kayit")
            logger.info(f"Ariza islemi yüklendi: {count} kayit")

        except Exception as e:
            logger.error(f"Ariza islemi yüklenirken hata: {e}")
            self._model.set_rows([])
            self.lbl_count.setText("0 kayit")

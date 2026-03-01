"""
Veritabanı Yedekleme ve Geri Yükleme Sayfası

Özellikler:
- Manuel yedek oluşturma (DB ve/veya dosyalar)
- Yedek listesi görüntüleme
- Yedek geri yükleme
- Yedek silme
- Disk alanı bilgisi
- Otomatik temizleme
"""
from __future__ import annotations

import os

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTableView,
    QHeaderView,
    QMessageBox,
    QGroupBox,
    QLineEdit,
    QSpinBox,
    QFrame,
    QCheckBox,
    QScrollArea,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from core.logger import logger
from core.services.backup_service import BackupService
from core.paths import DATA_DIR, LOG_DIR
from ui.components.base_table_model import BaseTableModel
from ui.styles.icons import Icons, IconRenderer


# Sütun tanımları
BACKUP_COLUMNS = [
    ("filename", "Dosya Adı", 250),
    ("size_mb", "Boyut (MB)", 100),
    ("created", "Oluşturma Tarihi", 150),
    ("description", "Açıklama", 300),
]


class BackupTableModel(BaseTableModel):
    """Yedek listesi için tablo modeli"""

    def __init__(self, rows=None, parent=None):
        super().__init__(BACKUP_COLUMNS, rows, parent)

    def _display(self, key, row):
        val = row.get(key, "")
        if key == "size_mb":
            return f"{val:.2f}" if val else "0.00"
        return str(val) if val else ""

    def _align(self, key):
        if key in ("size_mb",):
            return Qt.AlignmentFlag.AlignCenter
        if key == "created":
            return Qt.AlignmentFlag.AlignCenter
        return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft


class BackupPage(QWidget):
    """Veritabanı yedekleme sayfası"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._service = BackupService()
        self._setup_ui()
        self._load_backups()
        self._update_stats()

    def _setup_ui(self):
        """UI bileşenlerini oluştur"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Başlık
        title_layout = QHBoxLayout()
        title_label = QLabel("Veritabanı Yedekleme")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        title_icon = QLabel()
        title_icon.setPixmap(Icons.pixmap("database", size=24))
        title_layout.addWidget(title_icon)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # İstatistikler grubu
        stats_group = QGroupBox("İstatistikler")
        stats_layout = QHBoxLayout()
        stats_group.setLayout(stats_layout)
        
        self._lbl_backup_count = QLabel("Yedek Sayısı: -")
        self._lbl_total_size = QLabel("Toplam Boyut: -")
        self._lbl_disk_free = QLabel("Disk Alanı: -")
        
        stats_layout.addWidget(self._lbl_backup_count)
        stats_layout.addWidget(self._create_separator())
        stats_layout.addWidget(self._lbl_total_size)
        stats_layout.addWidget(self._create_separator())
        stats_layout.addWidget(self._lbl_disk_free)
        stats_layout.addStretch()
        
        layout.addWidget(stats_group)

        # Yeni yedek oluşturma grubu
        create_group = QGroupBox("Yeni Yedek Oluştur")
        create_layout = QHBoxLayout()
        create_group.setLayout(create_layout)
        
        self._btn_create_backup = QPushButton("Yedek Oluştur")
        IconRenderer.set_button_icon(self._btn_create_backup, "save", size=14)
        self._btn_create_backup.clicked.connect(self._create_backup)
        self._btn_create_backup.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        create_layout.addWidget(self._btn_create_backup)
        create_layout.addStretch()

        # Tam yedek (Veritabanı + Dosyalar) grubu
        full_backup_group = QGroupBox("Tam Yedek Oluştur (Veritabanı + Dosyalar)")
        full_backup_layout = QVBoxLayout()
        full_backup_group.setLayout(full_backup_layout)
        
        # Klasör seçimleri
        folders_layout = QHBoxLayout()
        folders_layout.addWidget(QLabel("Dahil Edilecek Klasörler:"))
        
        self._chk_offline_uploads = QCheckBox("offline_uploads")
        self._chk_offline_uploads.setChecked(True)
        self._chk_offline_uploads.setToolTip("Offline modda yüklenen dosyaları ekle")
        folders_layout.addWidget(self._chk_offline_uploads)
        
        self._chk_logs = QCheckBox("logs")
        self._chk_logs.setToolTip("Uygulama loglarını ekle")
        folders_layout.addWidget(self._chk_logs)
        
        self._chk_templates = QCheckBox("templates")
        self._chk_templates.setToolTip("Rapor şablonlarını ekle")
        folders_layout.addWidget(self._chk_templates)
        
        folders_layout.addStretch()
        full_backup_layout.addLayout(folders_layout)
        
        self._btn_create_full_backup = QPushButton("Tam Yedek Oluştur")
        IconRenderer.set_button_icon(self._btn_create_full_backup, "package", size=14)
        self._btn_create_full_backup.clicked.connect(self._create_full_backup)
        self._btn_create_full_backup.setStyleSheet("""
            QPushButton {
                background-color: #107c10;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0d6e07;
            }
        """)
        full_backup_layout.addWidget(self._btn_create_full_backup)
        
        # İki grubu yan yana al
        backup_groups_layout = QHBoxLayout()
        backup_groups_layout.addWidget(create_group, 1)
        backup_groups_layout.addWidget(full_backup_group, 1)
        layout.addLayout(backup_groups_layout)
        
        # İşlem butonları
        btn_layout = QHBoxLayout()
        
        self._btn_refresh = QPushButton("Yenile")
        IconRenderer.set_button_icon(self._btn_refresh, "refresh", size=14)
        self._btn_refresh.clicked.connect(self._load_backups)
        btn_layout.addWidget(self._btn_refresh)
        
        self._btn_restore = QPushButton("Geri Yükle")
        IconRenderer.set_button_icon(self._btn_restore, "upload", size=14)
        self._btn_restore.clicked.connect(self._restore_backup)
        self._btn_restore.setEnabled(False)
        btn_layout.addWidget(self._btn_restore)
        
        self._btn_delete = QPushButton("Sil")
        IconRenderer.set_button_icon(self._btn_delete, "trash", size=14)
        self._btn_delete.clicked.connect(self._delete_backup)
        self._btn_delete.setEnabled(False)
        self._btn_delete.setStyleSheet("""
            QPushButton {
                background-color: #d13438;
                color: white;
            }
            QPushButton:hover {
                background-color: #a82a2d;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        btn_layout.addWidget(self._btn_delete)
        
        btn_layout.addSpacing(20)
        
        # Temizleme
        btn_layout.addWidget(QLabel("Sadece son"))
        self._spin_keep_count = QSpinBox()
        self._spin_keep_count.setRange(1, 100)
        self._spin_keep_count.setValue(10)
        self._spin_keep_count.setSuffix(" yedek tut")
        btn_layout.addWidget(self._spin_keep_count)
        
        self._btn_cleanup = QPushButton("Eski Yedekleri Temizle")
        IconRenderer.set_button_icon(self._btn_cleanup, "trash", size=14)
        self._btn_cleanup.clicked.connect(self._cleanup_old_backups)
        btn_layout.addWidget(self._btn_cleanup)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Tablo
        self._table = QTableView()
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self._table.setSortingEnabled(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        
        self._model = BackupTableModel()
        self._table.setModel(self._model)
        
        # Sütun genişlikleri
        for i, (_, _, width) in enumerate(BACKUP_COLUMNS):
            self._table.setColumnWidth(i, width)
        
        # Seçim değiştiğinde butonları aktifleştir
        self._table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        
        layout.addWidget(self._table)

    def _create_separator(self):
        """Dikey ayırıcı çizgi"""
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        return line

    def _load_backups(self):
        """Yedekleri yükle"""
        try:
            backups = self._service.get_backups()
            self._model.set_data(backups)
            self._update_stats()
            logger.info(f"{len(backups)} yedek yüklendi")
        except Exception as e:
            logger.error(f"Yedek yükleme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Yedekler yüklenemedi:\n{str(e)}")

    def _update_stats(self):
        """İstatistikleri güncelle"""
        try:
            # Yedek istatistikleri
            stats = self._service.get_backup_stats()
            self._lbl_backup_count.setText(f"Yedek Sayısı: {stats['backup_count']}")
            self._lbl_total_size.setText(f"Toplam Boyut: {stats['total_size_mb']:.2f} MB")
            
            # Disk bilgisi
            disk = self._service.get_disk_space_info()
            if disk["total_mb"] > 0:
                free_gb = disk["free_mb"] / 1024
                self._lbl_disk_free.setText(
                    f"Disk Alanı: {free_gb:.2f} GB boş ({disk['percent_used']:.1f}% kullanılıyor)"
                )
            else:
                self._lbl_disk_free.setText("Disk Alanı: Bilgi alınamadı")
                
        except Exception as e:
            logger.error(f"İstatistik güncelleme hatası: {e}")

    def _create_backup(self):
        """Yeni yedek oluştur"""
        reply = QMessageBox.question(
            self,
            "Yedek Oluştur",
            "Yeni yedek oluşturmak istediğinizden emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            self._btn_create_backup.setEnabled(False)
            self._btn_create_backup.setText("Oluşturuluyor...")
            
            result = self._service.create_backup(description="")
            
            if result["success"]:
                QMessageBox.information(
                    self,
                    "Başarılı",
                    f"{result['message']}\n\nBoyut: {result['size_mb']:.2f} MB"
                )
                self._load_backups()
            else:
                QMessageBox.critical(self, "Hata", result["message"])
                
        except Exception as e:
            logger.error(f"Yedek oluşturma hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Yedek oluşturulamadı:\n{str(e)}")
        finally:
            self._btn_create_backup.setEnabled(True)
            self._btn_create_backup.setText("Yedek Oluştur")

    def _create_full_backup(self):
        """Veritabanı + dosyalarla tam yedek oluştur"""
        # Dahil edilecek klasörleri topla (mutlak yollarla)
        include_folders = []
        
        try:
            # Widget varlığı kontrolü
            if not hasattr(self, '_chk_offline_uploads') or not self._chk_offline_uploads:
                return
            
            if self._chk_offline_uploads.isChecked():
                offline_path = os.path.join(DATA_DIR, "offline_uploads")
                if os.path.exists(offline_path):
                    include_folders.append(offline_path)
            if self._chk_logs.isChecked():
                if os.path.exists(LOG_DIR):
                    include_folders.append(LOG_DIR)
            if self._chk_templates.isChecked():
                templates_path = os.path.join(DATA_DIR, "templates")
                if os.path.exists(templates_path):
                    include_folders.append(templates_path)
            
            description = ""
        except (RuntimeError, AttributeError):
            # Tab kapatılırken callback çalıştıysa widget silinmiş olabilir
            return
        
        msg = "Tam yedek oluşturmak istediğinizden emin misiniz?\n\n"
        msg += "Veritabanı ve aşağıdaki klasörler eklenecek:\n"
        if include_folders:
            folder_names = [os.path.basename(f) for f in include_folders]
            msg += "• " + "\n• ".join(folder_names)
        else:
            msg += "• Sadece veritabanı"
        
        reply = QMessageBox.question(
            self,
            "Tam Yedek Oluştur",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            self._btn_create_full_backup.setEnabled(False)
            self._btn_create_full_backup.setText("Oluşturuluyor...")
            
            result = self._service.create_backup_with_files(
                description="",
                include_folders=include_folders if include_folders else None
            )
            
            if result["success"]:
                QMessageBox.information(
                    self,
                    "Başarılı",
                    f"{result['message']}\n\n"
                    f"İçerik: Veritabanı + {len(include_folders) if include_folders else 0} klasör"
                )
                self._load_backups()
            else:
                QMessageBox.critical(self, "Hata", result["message"])
                
        except Exception as e:
            logger.error(f"Tam yedek oluşturma hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Tam yedek oluşturulamadı:\n{str(e)}")
        finally:
            self._btn_create_full_backup.setEnabled(True)
            self._btn_create_full_backup.setText("Tam Yedek Oluştur")

    def _restore_backup(self):
        """Seçili yedeği geri yükle"""
        selected = self._table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "Uyarı", "Lütfen geri yüklenecek yedeği seçin.")
            return
        
        row_index = selected[0].row()
        backup = self._model.get_row(row_index)
        
        if not backup:
            return
        
        backup_path = backup['path']
        is_zip = backup_path.endswith('.zip')
        
        reply = QMessageBox.warning(
            self,
            "DİKKAT",
            f"Yedeği geri yüklemek istediğinizden emin misiniz?\n\n"
            f"Dosya: {backup['filename']}\n"
            f"Tarih: {backup['created']}\n"
            f"Türü: {'ZIP (Veritabanı + Dosyalar)' if is_zip else 'Veritabanı'}\n\n"
            f"MEVCUT VERİTABANI YEDEĞİ ALINACAK VE\n"
            f"SEÇİLİ YEDEK GERİ YÜKLENECEKTİR!\n\n"
            f"Bu işlem sonrası uygulama yeniden başlatılmalıdır.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            # ZIP veya normal yedek?
            if is_zip:
                result = self._service.restore_backup_with_files(backup_path)
            else:
                result = self._service.restore_backup(backup_path)
            
            if result["success"]:
                QMessageBox.information(self, "Başarılı", result["message"])
            else:
                QMessageBox.critical(self, "Hata", result["message"])
                
        except Exception as e:
            logger.error(f"Yedek geri yükleme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Yedek geri yüklenemedi:\n{str(e)}")

    def _delete_backup(self):
        """Seçili yedeği sil"""
        selected = self._table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "Uyarı", "Lütfen silinecek yedeği seçin.")
            return
        
        row_index = selected[0].row()
        backup = self._model.get_row(row_index)
        
        if not backup:
            return
        
        reply = QMessageBox.question(
            self,
            "Yedeği Sil",
            f"Bu yedeği silmek istediğinizden emin misiniz?\n\n"
            f"Dosya: {backup['filename']}\n"
            f"Tarih: {backup['created']}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            result = self._service.delete_backup(backup["path"])
            
            if result["success"]:
                QMessageBox.information(self, "Başarılı", result["message"])
                self._load_backups()
            else:
                QMessageBox.critical(self, "Hata", result["message"])
                
        except Exception as e:
            logger.error(f"Yedek silme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Yedek silinemedi:\n{str(e)}")

    def _cleanup_old_backups(self):
        """Eski yedekleri temizle"""
        keep_count = self._spin_keep_count.value()
        
        reply = QMessageBox.question(
            self,
            "Eski Yedekleri Temizle",
            f"En yeni {keep_count} yedek hariç diğerleri silinecek.\n\n"
            f"Devam etmek istiyor musunuz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            result = self._service.cleanup_old_backups(keep_count)
            
            if result["success"]:
                if result["deleted_count"] > 0:
                    QMessageBox.information(
                        self,
                        "Başarılı",
                        f"{result['deleted_count']} yedek silindi.\n"
                        f"{result['freed_mb']:.2f} MB disk alanı boşaltıldı."
                    )
                else:
                    QMessageBox.information(self, "Bilgi", result["message"])
                self._load_backups()
            else:
                QMessageBox.critical(self, "Hata", result["message"])
                
        except Exception as e:
            logger.error(f"Yedek temizleme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Yedekler temizlenemedi:\n{str(e)}")

    def _on_selection_changed(self):
        """Seçim değiştiğinde butonları aktifleştir"""
        has_selection = bool(self._table.selectionModel().selectedRows())
        self._btn_restore.setEnabled(has_selection)
        self._btn_delete.setEnabled(has_selection)

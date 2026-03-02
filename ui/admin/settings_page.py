"""
Ayarlar Sayfası — Sabitler ve Tatiller Yönetimi

Özellikler:
- Sabitler tarafından veri eklemek, düzenlemek, silmek
- Tatiller tarafından veri eklemek, düzenlemek, silmek
- Tarih picker ile tatil tarihi seçimi
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QPushButton,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QLineEdit,
    QDateEdit,
    QMessageBox,
    QDialog,
    QTabWidget,
    QListWidget,
    QListWidgetItem,
    QSplitter,
)
from PySide6.QtCore import Qt, QDate

from core.logger import logger
from core.services.settings_service import SettingsService
from core.validators import validate_not_empty
from ui.components.formatted_widgets import (
    apply_title_case_formatting,
    apply_combo_title_case_formatting,
)
from ui.styles.colors import DarkTheme as C
from ui.styles.components import STYLES
from ui.styles.icons import Icons, IconRenderer


class SabitEditDialog(QDialog):
    """Sabit Düzenleme Dialogu"""
    
    def __init__(self, kod: str = "", menu_eleman: str = "", aciklama: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sabit Düzenleme")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Kod
        layout.addWidget(QLabel("Kod:"))
        self._txt_kod = QLineEdit()
        self._txt_kod.setStyleSheet(STYLES["input_field"])
        self._txt_kod.setText(kod)
        self._txt_kod.setPlaceholderText("Örn: PARAM_001")
        layout.addWidget(self._txt_kod)
        
        # Menü Elemanı
        layout.addWidget(QLabel("Menü Elemanı (Seçenek):"))
        self._txt_menu_eleman = QLineEdit()
        self._txt_menu_eleman.setStyleSheet(STYLES["input_field"])
        self._txt_menu_eleman.setText(menu_eleman)
        self._txt_menu_eleman.setPlaceholderText("Örn: Tıp, Mühendislik, Fen Bilgisi")
        apply_title_case_formatting(self._txt_menu_eleman)
        layout.addWidget(self._txt_menu_eleman)
        
        # Açıklama
        layout.addWidget(QLabel("Açıklama:"))
        self._txt_aciklama = QLineEdit()
        self._txt_aciklama.setStyleSheet(STYLES["input_field"])
        self._txt_aciklama.setText(aciklama)
        self._txt_aciklama.setPlaceholderText("Seçeneğin açıklaması (opsiyonel)")
        layout.addWidget(self._txt_aciklama)
        
        # Butonlar
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Tamam")
        IconRenderer.set_button_icon(btn_ok, "check", size=14)
        btn_ok.clicked.connect(self._on_accept)
        btn_cancel = QPushButton("İptal")
        IconRenderer.set_button_icon(btn_cancel, "x", size=14)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
    
    def _on_accept(self):
        """Validate before accepting"""
        if self.validate():
            self.accept()
    
    def get_data(self) -> tuple[str, str, str]:
        """Giriş verilerini döndür"""
        return (
            self._txt_kod.text().strip(),
            self._txt_menu_eleman.text().strip(),
            self._txt_aciklama.text().strip()
        )
    
    def validate(self) -> bool:
        """Form doğrulaması — Rehber Bölüm 8.5.4"""
        kod = self._txt_kod.text().strip()
        menu_eleman = self._txt_menu_eleman.text().strip()
        
        if not validate_not_empty(kod):
            QMessageBox.warning(self, "Uyarı", "Kod alanı boş olamaz!")
            self._txt_kod.setFocus()
            return False
        
        if not validate_not_empty(menu_eleman):
            QMessageBox.warning(self, "Uyarı", "Menü Elemanı alanı boş olamaz!")
            self._txt_menu_eleman.setFocus()
            return False
        
        return True


class TatilEditDialog(QDialog):
    """Tatil Düzenleme Dialogu"""
    
    def __init__(
        self,
        tarih: str = "",
        resmi_tatil: str = "",
        tatil_adlari: list[str] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Tatil Düzenleme")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Tarih
        layout.addWidget(QLabel("Tarih:"))
        self._date_edit = QDateEdit()
        self._date_edit.setCalendarPopup(True)
        self._date_edit.setDate(QDate.fromString(tarih, "yyyy-MM-dd") if tarih else QDate.currentDate())
        self._date_edit.setDateRange(QDate(2020, 1, 1), QDate(2050, 12, 31))
        self._date_edit.setStyleSheet(STYLES["input_date"])
        layout.addWidget(self._date_edit)
        
        # Tatil Adı
        layout.addWidget(QLabel("Tatil Adı:"))
        self._cmb_resmi_tatil = QComboBox()
        self._cmb_resmi_tatil.setEditable(True)
        self._cmb_resmi_tatil.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._cmb_resmi_tatil.setStyleSheet(STYLES["input_combo"])
        self._cmb_resmi_tatil.lineEdit().setPlaceholderText("Örn: Yeni Yıl")

        unique_adlar = sorted({(ad or "").strip() for ad in (tatil_adlari or []) if (ad or "").strip()})
        self._cmb_resmi_tatil.addItems(unique_adlar)

        if resmi_tatil and resmi_tatil.strip() and resmi_tatil.strip() not in unique_adlar:
            self._cmb_resmi_tatil.addItem(resmi_tatil.strip())

        self._cmb_resmi_tatil.setCurrentText(resmi_tatil)
        apply_combo_title_case_formatting(self._cmb_resmi_tatil)
        layout.addWidget(self._cmb_resmi_tatil)
        
        # Butonlar
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Tamam")
        IconRenderer.set_button_icon(btn_ok, "check", size=14)
        btn_ok.clicked.connect(self._on_accept)
        btn_cancel = QPushButton("İptal")
        IconRenderer.set_button_icon(btn_cancel, "x", size=14)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
    
    def _on_accept(self):
        """Validate before accepting"""
        if self.validate():
            self.accept()
    
    def get_data(self) -> tuple[str, str]:
        """Giriş verilerini döndür"""
        return (
            self._date_edit.date().toString("yyyy-MM-dd"),
            self._cmb_resmi_tatil.currentText().strip()
        )
    
    def validate(self) -> bool:
        """Form doğrulaması — Rehber Bölüm 8.5.4"""
        resmi_tatil = self._cmb_resmi_tatil.currentText().strip()
        
        if not validate_not_empty(resmi_tatil):
            QMessageBox.warning(self, "Uyarı", "Tatil Adı boş olamaz!")
            self._cmb_resmi_tatil.setFocus()
            return False
        
        return True


class SettingsPage(QWidget):
    """Ayarlar sayfası — Rehber Bölüm 1.3 uyumlu"""
    
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db
        
        # Service bağlantısı — di.py kullan (Rehber Bölüm 1.3)
        if db:
            from core.di import get_registry
            from database.repository_registry import RepositoryRegistry
            # SettingsService henüz registry kullanmıyor, direkt SQLiteManager kullanıyor
            # Bu yüzden şimdilik direkt instance oluşturuyoruz
            self._service = SettingsService()
        else:
            self._service = SettingsService()
        
        self._setup_ui()
        self._load_data()
    
    def _setup_ui(self):
        """UI bileşenlerini oluştur"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Tab widget
        tabs = QTabWidget()
        
        # ======== SABİTLER TAB ========
        sabitler_widget = QWidget()
        sabitler_layout = QVBoxLayout(sabitler_widget)
        
        # Ana layout: Sol (Kod) + Sağ (MenuEleman)
        content_layout = QHBoxLayout()
        
        # SOL: Kod Listesi
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("Ana Kategoriler (Kod):"))
        self._list_kod = QListWidget()
        self._list_kod.itemSelectionChanged.connect(self._on_kod_selected)
        left_panel.addWidget(self._list_kod)
        
        # Yeni Kategori butonu
        btn_new_kod = QPushButton("Yeni Kategori")
        IconRenderer.set_button_icon(btn_new_kod, "plus", size=14)
        btn_new_kod.clicked.connect(self._add_kod)
        left_panel.addWidget(btn_new_kod)
        
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        
        # SAĞ: MenuEleman Tablosu
        right_panel = QVBoxLayout()
        right_panel.addWidget(QLabel("Seçenekler (MenuEleman) ve Açıklamalar:"))
        
        self._table_menu_elemanlari = QTableWidget()
        self._table_menu_elemanlari.setColumnCount(2)
        self._table_menu_elemanlari.setHorizontalHeaderLabels(["Seçenek (MenuEleman)", "Açıklama"])
        self._table_menu_elemanlari.setColumnWidth(0, 350)  # MenuEleman sütununu genişlet
        self._table_menu_elemanlari.horizontalHeader().setStretchLastSection(True)
        self._table_menu_elemanlari.setSelectionBehavior(QTableWidget.SelectRows)
        self._table_menu_elemanlari.setSelectionMode(QTableWidget.SingleSelection)
        self._table_menu_elemanlari.setAlternatingRowColors(True)
        right_panel.addWidget(self._table_menu_elemanlari)
        
        # Butonlar (MenuEleman işlemleri)
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("Yeni Seçenek")
        IconRenderer.set_button_icon(btn_add, "plus", size=14)
        btn_add.clicked.connect(self._add_menu_eleman)
        btn_edit = QPushButton("Düzenle")
        IconRenderer.set_button_icon(btn_edit, "edit", size=14)
        btn_edit.clicked.connect(self._edit_menu_eleman)
        btn_delete = QPushButton("Sil")
        IconRenderer.set_button_icon(btn_delete, "trash", size=14)
        btn_delete.clicked.connect(self._delete_menu_eleman)
        
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_edit)
        btn_layout.addWidget(btn_delete)
        btn_layout.addStretch()
        right_panel.addLayout(btn_layout)
        
        right_widget = QWidget()
        right_widget.setLayout(right_panel)
        
        # Splitter ile sol-sağ bölme
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([300, 500])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        
        content_layout.addWidget(splitter)
        sabitler_layout.addLayout(content_layout)
        
        tabs.addTab(sabitler_widget, "Sabitler")
        tabs.setTabIcon(0, Icons.get("settings_sliders"))
        
        # ======== TATİLLER TAB ========
        tatiller_widget = QWidget()
        tatiller_layout = QVBoxLayout(tatiller_widget)

        # Yıl filtresi
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Yıl:"))
        self._cmb_tatil_yil = QComboBox()
        self._cmb_tatil_yil.setStyleSheet(STYLES["input_combo"])
        self._cmb_tatil_yil.currentIndexChanged.connect(self._load_tatiller)
        filter_layout.addWidget(self._cmb_tatil_yil)
        filter_layout.addStretch()
        tatiller_layout.addLayout(filter_layout)
        
        # Tablo
        self._table_tatiller = QTableWidget()
        self._table_tatiller.setColumnCount(2)
        self._table_tatiller.setHorizontalHeaderLabels(["Tarih", "Tatil Adı"])
        self._table_tatiller.horizontalHeader().setStretchLastSection(True)
        self._table_tatiller.setSelectionBehavior(QTableWidget.SelectRows)
        self._table_tatiller.setSelectionMode(QTableWidget.SingleSelection)
        self._table_tatiller.setAlternatingRowColors(True)
        tatiller_layout.addWidget(self._table_tatiller)
        
        # Butonlar
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("Yeni Tatil")
        IconRenderer.set_button_icon(btn_add, "plus", size=14)
        btn_add.clicked.connect(self._add_tatil)
        btn_edit = QPushButton("Düzenle")
        IconRenderer.set_button_icon(btn_edit, "edit", size=14)
        btn_edit.clicked.connect(self._edit_tatil)
        btn_delete = QPushButton("Sil")
        IconRenderer.set_button_icon(btn_delete, "trash", size=14)
        btn_delete.clicked.connect(self._delete_tatil)
        
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_edit)
        btn_layout.addWidget(btn_delete)
        btn_layout.addStretch()
        tatiller_layout.addLayout(btn_layout)
        
        tabs.addTab(tatiller_widget, "Tatiller")
        tabs.setTabIcon(1, Icons.get("calendar"))
        
        layout.addWidget(tabs)
    
    def _load_data(self):
        """Verileri yükle"""
        self._load_sabitler()
        self._load_tatiller()
    
    def _load_sabitler(self):
        """Sabitleri yükle — Sol tarafta unique Kod'lar listele"""
        try:
            sabitler = self._service.get_sabitler()
            
            # Benzersiz Kod'ları bul
            unique_kodlar = {}
            for sabit in sabitler:
                kod = sabit.get("Kod", "")
                if kod and kod not in unique_kodlar:
                    unique_kodlar[kod] = sabit
            
            # Sol tarafta listele
            self._list_kod.clear()
            for kod in sorted(unique_kodlar.keys()):
                item = QListWidgetItem(kod)
                item.setData(Qt.ItemDataRole.UserRole, kod)  # Kod'u saklı tut
                self._list_kod.addItem(item)
            
            logger.info(f"{len(unique_kodlar)} benzersiz kod yüklendi")
            
            # İlk Kod'u seç varsa
            if self._list_kod.count() > 0:
                self._list_kod.setCurrentRow(0)
            else:
                self._load_menu_elemanlari(None)
            
        except Exception as e:
            logger.error(f"Sabitler yükleme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Sabitler yüklenemedi:\n{str(e)}")
    
    def _on_kod_selected(self):
        """Kod seçildiğinde sağ tarafı güncelle"""
        current_item = self._list_kod.currentItem()
        if current_item:
            kod = current_item.data(Qt.ItemDataRole.UserRole)
            self._load_menu_elemanlari(kod)
        else:
            self._load_menu_elemanlari(None)
    
    def _add_kod(self):
        """Yeni Ana Kategori (Kod) ekle"""
        dialog = SabitEditDialog(parent=self)
        dialog.setWindowTitle("Yeni Kategori Ekle")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            kod, menu_eleman, aciklama = dialog.get_data()
            
            if not kod or not menu_eleman:
                QMessageBox.warning(self, "Uyarı", "Kod ve Seçenek (MenuEleman) zorunludur")
                return
            
            result = self._service.add_sabit(kod, menu_eleman, aciklama)
            if result["success"]:
                QMessageBox.information(self, "Başarılı", f"'{kod}' kategorisi oluşturuldu")
                self._load_sabitler()
            else:
                QMessageBox.critical(self, "Hata", result["message"])
    
    def _load_menu_elemanlari(self, kod: str = None):
        """Seçilen Kod'un MenuElemanlarını sağ tarafta göster"""
        try:
            self._table_menu_elemanlari.setRowCount(0)
            
            if not kod:
                return
            
            sabitler = self._service.get_sabitler()
            
            # Seçili Kod'a ait MenuElemanları göster
            for sabit in sabitler:
                if sabit.get("Kod", "") == kod:
                    row = self._table_menu_elemanlari.rowCount()
                    self._table_menu_elemanlari.insertRow(row)
                    
                    # Rowid ve Kod'u saklı tut
                    item_menu = QTableWidgetItem(sabit.get("MenuEleman", ""))
                    item_menu.setData(Qt.ItemDataRole.UserRole, sabit.get("Rowid", ""))  # Rowid
                    item_menu.setData(Qt.ItemDataRole.UserRole + 1, kod)  # Kod
                    self._table_menu_elemanlari.setItem(row, 0, item_menu)
                    
                    # Açıklama
                    self._table_menu_elemanlari.setItem(row, 1, QTableWidgetItem(sabit.get("Aciklama", "")))
            
            logger.info(f"'{kod}' için {self._table_menu_elemanlari.rowCount()} menü elemanı yüklendi")
            
        except Exception as e:
            logger.error(f"MenuEleman yükleme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Menü elemanları yüklenemedi:\n{str(e)}")
    
    def _load_tatiller(self):
        """Tatilleri yükle"""
        try:
            tatiller = self._service.get_tatiller()

            # Yıl filtresi seçeneklerini güncelle
            selected_year = self._cmb_tatil_yil.currentData() if hasattr(self, "_cmb_tatil_yil") else None
            years = sorted(
                {
                    t.get("Tarih", "")[:4]
                    for t in tatiller
                    if t.get("Tarih", "") and t.get("Tarih", "")[:4].isdigit()
                },
                reverse=True,
            )

            self._cmb_tatil_yil.blockSignals(True)
            self._cmb_tatil_yil.clear()
            self._cmb_tatil_yil.addItem("Tüm Yıllar", None)
            for year in years:
                self._cmb_tatil_yil.addItem(year, year)

            if selected_year in years:
                self._cmb_tatil_yil.setCurrentText(selected_year)
            else:
                self._cmb_tatil_yil.setCurrentIndex(0)
            self._cmb_tatil_yil.blockSignals(False)

            active_year = self._cmb_tatil_yil.currentData()
            filtered_tatiller = [
                tatil
                for tatil in tatiller
                if not active_year or tatil.get("Tarih", "").startswith(f"{active_year}-")
            ]

            self._table_tatiller.setRowCount(0)
            
            for tatil in filtered_tatiller:
                row = self._table_tatiller.rowCount()
                self._table_tatiller.insertRow(row)
                
                # Tarih
                self._table_tatiller.setItem(row, 0, QTableWidgetItem(tatil.get("Tarih", "")))
                
                # Tatil Adı
                self._table_tatiller.setItem(row, 1, QTableWidgetItem(tatil.get("ResmiTatil", "")))
            
            year_text = active_year if active_year else "Tüm Yıllar"
            logger.info(f"{len(filtered_tatiller)} tatil yüklendi (Yıl: {year_text})")
            
        except Exception as e:
            logger.error(f"Tatiller yükleme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Tatiller yüklenemedi:\n{str(e)}")

    def _get_unique_tatil_adlari(self) -> list[str]:
        """Tatiller tablosundaki benzersiz tatil adlarını döndür."""
        try:
            tatiller = self._service.get_tatiller()
            return sorted(
                {
                    (t.get("ResmiTatil", "") or "").strip()
                    for t in tatiller
                    if (t.get("ResmiTatil", "") or "").strip()
                }
            )
        except Exception as e:
            logger.warning(f"Tatil adı listesi alınamadı: {e}")
            return []
    
    def _add_menu_eleman(self):
        """Seçili Kod'a yeni MenuEleman ekle"""
        current_item = self._list_kod.currentItem()
        
        # Eğer Kod seçili değilse, yeni Kod'u seç
        if not current_item:
            dialog = SabitEditDialog(parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                kod, menu_eleman, aciklama = dialog.get_data()
                
                if not kod or not menu_eleman:
                    QMessageBox.warning(self, "Uyarı", "Kod ve Seçenek (MenuEleman) zorunludur")
                    return
                
                result = self._service.add_sabit(kod, menu_eleman, aciklama)
                if result["success"]:
                    QMessageBox.information(self, "Başarılı", f"'{kod}' kategorisi oluşturuldu ve '{menu_eleman}' seçeneği eklendi")
                    self._load_sabitler()
                else:
                    QMessageBox.critical(self, "Hata", result["message"])
            return
        
        # Kod seçili ise, yeni MenuEleman ekle
        kod = current_item.data(Qt.ItemDataRole.UserRole)
        
        dialog = SabitEditDialog(kod=kod, parent=self)
        # Kod alanını devre dışı bırak (zaten seçili)
        dialog._txt_kod.setReadOnly(True)
        dialog._txt_kod.setStyleSheet(f"background-color: {C.INPUT_BG};")
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            _, menu_eleman, aciklama = dialog.get_data()
            
            if not menu_eleman:
                QMessageBox.warning(self, "Uyarı", "Seçenek (MenuEleman) zorunludur")
                return
            
            result = self._service.add_sabit(kod, menu_eleman, aciklama)
            if result["success"]:
                QMessageBox.information(self, "Başarılı", f"'{menu_eleman}' seçeneği eklendi")
                self._on_kod_selected()  # Sağ tarafı yenile
            else:
                QMessageBox.critical(self, "Hata", result["message"])
    
    def _edit_menu_eleman(self):
        """Seçili MenuEleman'ı düzenle"""
        row = self._table_menu_elemanlari.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen düzenlemek için bir seçenek seçin")
            return
        
        rowid = self._table_menu_elemanlari.item(row, 0).data(Qt.ItemDataRole.UserRole)
        kod = self._table_menu_elemanlari.item(row, 0).data(Qt.ItemDataRole.UserRole + 1)
        menu_eleman = self._table_menu_elemanlari.item(row, 0).text()
        aciklama = self._table_menu_elemanlari.item(row, 1).text()
        
        dialog = SabitEditDialog(kod, menu_eleman, aciklama, parent=self)
        # Kod alanını devre dışı bırak
        dialog._txt_kod.setReadOnly(True)
        dialog._txt_kod.setStyleSheet(f"background-color: {C.INPUT_BG};")
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            _, menu_eleman, aciklama = dialog.get_data()
            
            if not menu_eleman:
                QMessageBox.warning(self, "Uyarı", "Seçenek (MenuEleman) zorunludur")
                return
            
            result = self._service.update_sabit(rowid, kod, menu_eleman, aciklama)
            if result["success"]:
                QMessageBox.information(self, "Başarılı", "Seçenek güncellendi")
                self._on_kod_selected()  # Sağ tarafı yenile
            else:
                QMessageBox.critical(self, "Hata", result["message"])
    
    def _delete_menu_eleman(self):
        """Seçili MenuEleman'ı sil"""
        row = self._table_menu_elemanlari.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen silinecek seçeneği seçin")
            return
        
        rowid = self._table_menu_elemanlari.item(row, 0).data(Qt.ItemDataRole.UserRole)
        menu_eleman = self._table_menu_elemanlari.item(row, 0).text()
        aciklama = self._table_menu_elemanlari.item(row, 1).text()
        
        reply = QMessageBox.question(
            self,
            "Seçenek Sil",
            f"'{menu_eleman}' seçeneğini silmek istediğinizden emin misiniz?\n\n({aciklama})",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            result = self._service.delete_sabit(rowid)
            if result["success"]:
                QMessageBox.information(self, "Başarılı", "Seçenek silindi")
                self._on_kod_selected()  # Sağ tarafı yenile
            else:
                QMessageBox.critical(self, "Hata", result["message"])
    
    def _add_tatil(self):
        """Yeni tatil ekle"""
        dialog = TatilEditDialog(
            tatil_adlari=self._get_unique_tatil_adlari(),
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            tarih, resmi_tatil = dialog.get_data()
            
            if not tarih or not resmi_tatil:
                QMessageBox.warning(self, "Uyarı", "Tarih ve Tatil Adı zorunludur")
                return
            
            result = self._service.add_tatil(tarih, resmi_tatil)
            if result["success"]:
                QMessageBox.information(self, "Başarılı", result["message"])
                self._load_tatiller()
            else:
                QMessageBox.critical(self, "Hata", result["message"])
    
    def _edit_tatil(self):
        """Tatili düzenle"""
        row = self._table_tatiller.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen düzenlemek için bir tatil seçin")
            return
        
        tarih = self._table_tatiller.item(row, 0).text()
        resmi_tatil = self._table_tatiller.item(row, 1).text()
        
        dialog = TatilEditDialog(
            tarih=tarih,
            resmi_tatil=resmi_tatil,
            tatil_adlari=self._get_unique_tatil_adlari(),
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_tarih, resmi_tatil = dialog.get_data()
            
            if not new_tarih or not resmi_tatil:
                QMessageBox.warning(self, "Uyarı", "Tarih ve Tatil Adı zorunludur")
                return
            
            # Tarih değişiyorsa: eski sil, yeni ekle
            if new_tarih != tarih:
                self._service.delete_tatil(tarih)
                result = self._service.add_tatil(new_tarih, resmi_tatil)
            else:
                result = self._service.update_tatil(tarih, resmi_tatil)
            
            if result["success"]:
                QMessageBox.information(self, "Başarılı", result["message"])
                self._load_tatiller()
            else:
                QMessageBox.critical(self, "Hata", result["message"])
    
    def _delete_tatil(self):
        """Tatili sil"""
        row = self._table_tatiller.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen silinecek tatili seçin")
            return
        
        tarih = self._table_tatiller.item(row, 0).text()
        resmi_tatil = self._table_tatiller.item(row, 1).text()
        
        reply = QMessageBox.question(
            self,
            "Tatil Sil",
            f"'{resmi_tatil}' ({tarih}) tatilini silmek istediğinizden emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            result = self._service.delete_tatil(tarih)
            if result["success"]:
                QMessageBox.information(self, "Başarılı", result["message"])
                self._load_tatiller()
            else:
                QMessageBox.critical(self, "Hata", result["message"])

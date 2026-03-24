"""
Ayarlar Sayfası — Sabitler, Tatiller, Tema ve Online/Offline Yönetimi

Özellikler:
- Sabitler tarafından veri eklemek, düzenlemek, silmek
- Tatiller tarafından veri eklemek, düzenlemek, silmek
- Tarih picker ile tatil tarihi seçimi
- Tema seçimi (Dark/Light)
- Sistemin online/offline durumu kontrol etme
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
    QCheckBox,
    QRadioButton,
    QGroupBox,
)
from PySide6.QtCore import Qt, QDate

from core.logger import logger
from core.config import AppConfig
from core.services.settings_service import SettingsService
from core.validators import validate_not_empty
from ui.components.formatted_widgets import (
    apply_title_case_formatting,
    apply_combo_title_case_formatting,
)
from ui.styles.colors import DarkTheme, get_current_theme
from ui.styles.components import STYLES, refresh_styles
from ui.styles.icons import Icons, IconRenderer


class SabitEditDialog(QDialog):
    """Sabit Düzenleme Dialogu"""
    
    def __init__(self, kod: str = "", menu_eleman: str = "", aciklama: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sabit Düzenleme")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setProperty("bg-role", "page")
        self.style().unpolish(self)
        self.style().polish(self)
        
        layout = QVBoxLayout(self)
        
        # Kod
        lbl_kod = QLabel("Kod:")
        lbl_kod.setProperty("color-role", "primary")
        lbl_kod.setStyleSheet("font-weight: 500;")
        lbl_kod.style().unpolish(lbl_kod)
        lbl_kod.style().polish(lbl_kod)
        layout.addWidget(lbl_kod)
        self._txt_kod = QLineEdit()
        # setStyleSheet kaldırıldı: input_field — global QSS kuralı geçerli
        self._txt_kod.setText(kod)
        self._txt_kod.setPlaceholderText("Örn: PARAM_001")
        layout.addWidget(self._txt_kod)
        
        # Menü Elemanı
        lbl_menu = QLabel("Menü Elemanı (Seçenek):")
        lbl_menu.setProperty("color-role", "primary")
        lbl_menu.setStyleSheet("font-weight: 500;")
        lbl_menu.style().unpolish(lbl_menu)
        lbl_menu.style().polish(lbl_menu)
        layout.addWidget(lbl_menu)
        self._txt_menu_eleman = QLineEdit()
        # setStyleSheet kaldırıldı: input_field — global QSS kuralı geçerli
        self._txt_menu_eleman.setText(menu_eleman)
        self._txt_menu_eleman.setPlaceholderText("Örn: Tıp, Mühendislik, Fen Bilgisi")
        apply_title_case_formatting(self._txt_menu_eleman)
        layout.addWidget(self._txt_menu_eleman)
        
        # Açıklama
        lbl_aciklama = QLabel("Açıklama:")
        lbl_aciklama.setProperty("color-role", "primary")
        lbl_aciklama.setStyleSheet("font-weight: 500;")
        lbl_aciklama.style().unpolish(lbl_aciklama)
        lbl_aciklama.style().polish(lbl_aciklama)
        layout.addWidget(lbl_aciklama)
        self._txt_aciklama = QLineEdit()
        # setStyleSheet kaldırıldı: input_field — global QSS kuralı geçerli
        self._txt_aciklama.setText(aciklama)
        self._txt_aciklama.setPlaceholderText("Seçeneğin açıklaması (opsiyonel)")
        layout.addWidget(self._txt_aciklama)
        
        # Butonlar
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Tamam")
        btn_ok.setProperty("style-role", "action")
        btn_ok.style().unpolish(btn_ok)
        btn_ok.style().polish(btn_ok)
        IconRenderer.set_button_icon(btn_ok, "check", size=14)
        btn_ok.clicked.connect(self._on_accept)
        btn_cancel = QPushButton("İptal")
        btn_cancel.setProperty("style-role", "secondary")
        btn_cancel.style().unpolish(btn_cancel)
        btn_cancel.style().polish(btn_cancel)
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
        self.setProperty("bg-role", "page"); self.style().unpolish(self); self.style().polish(self)
        
        layout = QVBoxLayout(self)
        
        # Tarih
        lbl_tarih = QLabel("Tarih:")
        lbl_tarih.setProperty("color-role", "primary")
        lbl_tarih.setStyleSheet("font-weight: 500;")
        lbl_tarih.style().unpolish(lbl_tarih)
        lbl_tarih.style().polish(lbl_tarih)
        layout.addWidget(lbl_tarih)
        self._date_edit = QDateEdit()
        self._date_edit.setCalendarPopup(True)
        self._date_edit.setDate(QDate.fromString(tarih, "yyyy-MM-dd") if tarih else QDate.currentDate())
        self._date_edit.setDateRange(QDate(2020, 1, 1), QDate(2050, 12, 31))
        # setStyleSheet kaldırıldı: input_date — global QSS kuralı geçerli
        layout.addWidget(self._date_edit)
        
        # Tatil Adı
        lbl_tatil_adi = QLabel("Tatil Adı:")
        lbl_tatil_adi.setProperty("color-role", "primary")
        lbl_tatil_adi.setStyleSheet("font-weight: 500;")
        lbl_tatil_adi.style().unpolish(lbl_tatil_adi)
        lbl_tatil_adi.style().polish(lbl_tatil_adi)
        layout.addWidget(lbl_tatil_adi)
        self._cmb_resmi_tatil = QComboBox()
        self._cmb_resmi_tatil.setEditable(True)
        self._cmb_resmi_tatil.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        # setStyleSheet kaldırıldı: input_combo — global QSS kuralı geçerli
        # Placeholder text ayarla
        line_edit = self._cmb_resmi_tatil.lineEdit()
        if line_edit:
            line_edit.setPlaceholderText("Örn: Yeni Yıl")

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
        btn_ok.setProperty("style-role", "action")
        btn_ok.style().unpolish(btn_ok)
        btn_ok.style().polish(btn_ok)
        IconRenderer.set_button_icon(btn_ok, "check", size=14)
        btn_ok.clicked.connect(self._on_accept)
        btn_cancel = QPushButton("İptal")
        btn_cancel.setProperty("style-role", "secondary")
        btn_cancel.style().unpolish(btn_cancel)
        btn_cancel.style().polish(btn_cancel)
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

        # SettingsService doğrudan db nesnesi bekler.
        self._service = SettingsService(self._db)
        
        self._setup_ui()
        self._load_data()
    
    def _setup_ui(self):
        """UI bileşenlerini oluştur"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Ana sayfa background
        self.setProperty("bg-role", "page")
        self.style().unpolish(self)
        self.style().polish(self)
        
        # Tab widget
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {{
                border: 1px solid {};
                background-color: {};
            }}
            QTabBar::tab {{
                background-color: {};
                color: {};
                padding: 8px 20px;
                border: 1px solid {};
                border-bottom: none;
            }}
            QTabBar::tab:selected {{
                background-color: {};
                color: {};
                border-bottom: 1px solid {};
            }}
        """.format(
            DarkTheme.BORDER_PRIMARY, DarkTheme.BG_PRIMARY,
            DarkTheme.BG_SECONDARY, DarkTheme.TEXT_SECONDARY,
            DarkTheme.BORDER_PRIMARY, DarkTheme.BG_PRIMARY,
            DarkTheme.TEXT_PRIMARY, DarkTheme.BG_PRIMARY
        ))
        
        # ======== SABİTLER TAB ========
        sabitler_widget = QWidget()
        sabitler_layout = QVBoxLayout(sabitler_widget)
        
        # Ana layout: Sol (Kod) + Sağ (MenuEleman)
        content_layout = QHBoxLayout()
        
        # SOL: Kod Listesi
        left_panel = QVBoxLayout()
        lbl_ana_kat = QLabel("Ana Kategoriler (Kod):")
        lbl_ana_kat.setProperty("color-role", "primary")
        lbl_ana_kat.setStyleSheet("font-weight: 600;")
        lbl_ana_kat.style().unpolish(lbl_ana_kat)
        lbl_ana_kat.style().polish(lbl_ana_kat)
        left_panel.addWidget(lbl_ana_kat)
        self._list_kod = QListWidget()
        # setStyleSheet kaldırıldı: table — global QSS
        self._list_kod.itemSelectionChanged.connect(self._on_kod_selected)
        left_panel.addWidget(self._list_kod)
        
        # Yeni Kategori butonu
        btn_new_kod = QPushButton("Yeni Kategori")
        btn_new_kod.setProperty("style-role", "secondary")
        btn_new_kod.style().unpolish(btn_new_kod)
        btn_new_kod.style().polish(btn_new_kod)
        IconRenderer.set_button_icon(btn_new_kod, "plus", size=14)
        btn_new_kod.clicked.connect(self._add_kod)
        left_panel.addWidget(btn_new_kod)
        
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        
        # SAĞ: MenuEleman Tablosu
        right_panel = QVBoxLayout()
        lbl_secenekler = QLabel("Seçenekler (MenuEleman) ve Açıklamalar:")
        lbl_secenekler.setProperty("color-role", "primary")
        lbl_secenekler.setStyleSheet("font-weight: 600;")
        lbl_secenekler.style().unpolish(lbl_secenekler)
        lbl_secenekler.style().polish(lbl_secenekler)
        right_panel.addWidget(lbl_secenekler)
        
        self._table_menu_elemanlari = QTableWidget()
        self._table_menu_elemanlari.setColumnCount(2)
        self._table_menu_elemanlari.setHorizontalHeaderLabels(["Seçenek (MenuEleman)", "Açıklama"])
        self._table_menu_elemanlari.setColumnWidth(0, 350)  # MenuEleman sütununu genişlet
        self._table_menu_elemanlari.horizontalHeader().setStretchLastSection(True)
        self._table_menu_elemanlari.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table_menu_elemanlari.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table_menu_elemanlari.setAlternatingRowColors(True)
        # setStyleSheet kaldırıldı: table — global QSS kuralı geçerli
        right_panel.addWidget(self._table_menu_elemanlari)
        
        # Butonlar (MenuEleman işlemleri)
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("Yeni Seçenek")
        btn_add.setProperty("style-role", "secondary")
        btn_add.style().unpolish(btn_add)
        btn_add.style().polish(btn_add)
        IconRenderer.set_button_icon(btn_add, "plus", size=14)
        btn_add.clicked.connect(self._add_menu_eleman)
        btn_edit = QPushButton("Düzenle")
        btn_edit.setProperty("style-role", "secondary")
        btn_edit.style().unpolish(btn_edit)
        btn_edit.style().polish(btn_edit)
        IconRenderer.set_button_icon(btn_edit, "edit", size=14)
        btn_edit.clicked.connect(self._edit_menu_eleman)
        btn_delete = QPushButton("Sil")
        btn_delete.setProperty("style-role", "secondary")
        btn_delete.style().unpolish(btn_delete)
        btn_delete.style().polish(btn_delete)
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
        # setStyleSheet kaldırıldı: splitter — global QSS kuralı geçerli
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
        lbl_yil = QLabel("Yıl:")
        lbl_yil.setProperty("color-role", "primary")
        lbl_yil.setStyleSheet("font-weight: 500;")
        lbl_yil.style().unpolish(lbl_yil)
        lbl_yil.style().polish(lbl_yil)
        filter_layout.addWidget(lbl_yil)
        self._cmb_tatil_yil = QComboBox()
        # setStyleSheet kaldırıldı: input_combo — global QSS kuralı geçerli
        self._cmb_tatil_yil.currentIndexChanged.connect(self._load_tatiller)
        filter_layout.addWidget(self._cmb_tatil_yil)
        filter_layout.addStretch()
        tatiller_layout.addLayout(filter_layout)
        
        # Tablo
        self._table_tatiller = QTableWidget()
        self._table_tatiller.setColumnCount(2)
        self._table_tatiller.setHorizontalHeaderLabels(["Tarih", "Tatil Adı"])
        self._table_tatiller.horizontalHeader().setStretchLastSection(True)
        self._table_tatiller.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table_tatiller.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table_tatiller.setAlternatingRowColors(True)
        # setStyleSheet kaldırıldı: table — global QSS kuralı geçerli
        tatiller_layout.addWidget(self._table_tatiller)
        
        # Butonlar
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("Yeni Tatil")
        btn_add.setProperty("style-role", "secondary")
        btn_add.style().unpolish(btn_add)
        btn_add.style().polish(btn_add)
        IconRenderer.set_button_icon(btn_add, "plus", size=14)
        btn_add.clicked.connect(self._add_tatil)
        btn_edit = QPushButton("Düzenle")
        btn_edit.setProperty("style-role", "secondary")
        btn_edit.style().unpolish(btn_edit)
        btn_edit.style().polish(btn_edit)
        IconRenderer.set_button_icon(btn_edit, "edit", size=14)
        btn_edit.clicked.connect(self._edit_tatil)
        btn_delete = QPushButton("Sil")
        btn_delete.setProperty("style-role", "secondary")
        btn_delete.style().unpolish(btn_delete)
        btn_delete.style().polish(btn_delete)
        IconRenderer.set_button_icon(btn_delete, "trash", size=14)
        btn_delete.clicked.connect(self._delete_tatil)
        
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_edit)
        btn_layout.addWidget(btn_delete)
        btn_layout.addStretch()
        tatiller_layout.addLayout(btn_layout)
        
        tabs.addTab(tatiller_widget, "Tatiller")
        tabs.setTabIcon(1, Icons.get("calendar"))
        
        # ======== TEMA TAB ========
        tema_widget = QWidget()
        tema_layout = QVBoxLayout(tema_widget)
        
        lbl_tema_baslik = QLabel("Tema Seçimi")
        lbl_tema_baslik.setProperty("color-role", "primary")
        lbl_tema_baslik.setStyleSheet("font-weight: 700; font-size: 14px;")
        lbl_tema_baslik.style().unpolish(lbl_tema_baslik)
        lbl_tema_baslik.style().polish(lbl_tema_baslik)
        tema_layout.addWidget(lbl_tema_baslik)
        
        tema_info = QLabel("Uygulamanın görünüş temasını seçin")
        tema_info.setProperty("color-role", "secondary")
        tema_info.setStyleSheet("font-size: 12px;")
        tema_info.style().unpolish(tema_info)
        tema_info.style().polish(tema_info)
        tema_layout.addWidget(tema_info)
        
        tema_layout.addSpacing(20)
        
        # Dark tema seçeneği
        self._radio_dark = QRadioButton("Koyu Tema (Dark)")
        self._radio_dark.setProperty("color-role", "primary")
        self._radio_dark.setStyleSheet("font-size: 12px;")
        self._radio_dark.style().unpolish(self._radio_dark)
        self._radio_dark.style().polish(self._radio_dark)
        self._radio_dark.setChecked(True)
        tema_layout.addWidget(self._radio_dark)
        
        dark_desc = QLabel("Dimli, göz arkadaşı renkler")
        dark_desc.setProperty("color-role", "secondary")
        dark_desc.setStyleSheet("font-size: 11px; margin-left: 25px;")
        dark_desc.style().unpolish(dark_desc)
        dark_desc.style().polish(dark_desc)
        tema_layout.addWidget(dark_desc)
        
        tema_layout.addSpacing(15)
        
        # Light tema seçeneği
        self._radio_light = QRadioButton("Açık Tema (Light)")
        self._radio_light.setProperty("color-role", "primary")
        self._radio_light.setStyleSheet("font-size: 12px;")
        self._radio_light.style().unpolish(self._radio_light)
        self._radio_light.style().polish(self._radio_light)
        tema_layout.addWidget(self._radio_light)
        
        light_desc = QLabel("Aydınlık, açık renkler")
        light_desc.setProperty("color-role", "secondary")
        light_desc.setStyleSheet("font-size: 11px; margin-left: 25px;")
        light_desc.style().unpolish(light_desc)
        light_desc.style().polish(light_desc)
        tema_layout.addWidget(light_desc)
        
        tema_layout.addSpacing(20)
        
        # Kaydet butonu
        btn_tema_kaydet = QPushButton("Tema Değişikliğini Uygula")
        btn_tema_kaydet.setProperty("style-role", "action")
        btn_tema_kaydet.style().unpolish(btn_tema_kaydet)
        btn_tema_kaydet.style().polish(btn_tema_kaydet)
        IconRenderer.set_button_icon(btn_tema_kaydet, "palette", size=14)
        btn_tema_kaydet.clicked.connect(self._apply_theme)
        tema_layout.addWidget(btn_tema_kaydet)
        
        tema_layout.addStretch()
        
        tabs.addTab(tema_widget, "Tema")
        tabs.setTabIcon(2, Icons.get("palette"))
        
        # ======== ONLINE/OFFLINE TAB ========
        sistem_widget = QWidget()
        sistem_layout = QVBoxLayout(sistem_widget)
        
        lbl_sistem_baslik = QLabel("Sistem Durumu")
        lbl_sistem_baslik.setProperty("color-role", "primary")
        lbl_sistem_baslik.setStyleSheet("font-weight: 700; font-size: 14px;")
        lbl_sistem_baslik.style().unpolish(lbl_sistem_baslik)
        lbl_sistem_baslik.style().polish(lbl_sistem_baslik)
        sistem_layout.addWidget(lbl_sistem_baslik)
        
        durum_info = QLabel("Sistemin çalışma modunu belirleyin")
        durum_info.setProperty("color-role", "secondary")
        durum_info.setStyleSheet("font-size: 12px;")
        durum_info.style().unpolish(durum_info)
        durum_info.style().polish(durum_info)
        sistem_layout.addWidget(durum_info)
        
        sistem_layout.addSpacing(20)
        
        # Online mod checkbox
        self._chk_online_mod = QCheckBox("Online Mod Etkin")
        self._chk_online_mod.setProperty("color-role", "primary")
        self._chk_online_mod.setStyleSheet("font-size: 12px; font-weight: 500;")
        self._chk_online_mod.style().unpolish(self._chk_online_mod)
        self._chk_online_mod.style().polish(self._chk_online_mod)
        self._chk_online_mod.setChecked(AppConfig.is_online_mode())
        self._chk_online_mod.stateChanged.connect(self._on_online_mode_changed)
        sistem_layout.addWidget(self._chk_online_mod)
        
        online_desc = QLabel("✓ Online: Bulut senkronizasyonu, canlı veri\n✗ Offline: Yerel veri, manuel senkronizasyon")
        online_desc.setProperty("color-role", "secondary")
        online_desc.setStyleSheet("font-size: 11px; margin-left: 25px;")
        online_desc.style().unpolish(online_desc)
        online_desc.style().polish(online_desc)
        sistem_layout.addWidget(online_desc)
        
        sistem_layout.addSpacing(20)
        
        # Otomatik senkronizasyon
        self._chk_auto_sync = QCheckBox("Otomatik Senkronizasyon")
        self._chk_auto_sync.setProperty("color-role", "primary")
        self._chk_auto_sync.setStyleSheet("font-size: 12px; font-weight: 500;")
        self._chk_auto_sync.style().unpolish(self._chk_auto_sync)
        self._chk_auto_sync.style().polish(self._chk_auto_sync)
        self._chk_auto_sync.setChecked(AppConfig.get_auto_sync())
        self._chk_auto_sync.setEnabled(True)
        sistem_layout.addWidget(self._chk_auto_sync)
        
        sync_desc = QLabel("Değişiklikleri arka planda otomatik senkronize et")
        sync_desc.setProperty("color-role", "secondary")
        sync_desc.setStyleSheet("font-size: 11px; margin-left: 25px;")
        sync_desc.style().unpolish(sync_desc)
        sync_desc.style().polish(sync_desc)
        sistem_layout.addWidget(sync_desc)
        
        sistem_layout.addSpacing(20)
        
        # Senkronizasyon bilgisi
        lbl_sync_info = QLabel("Son Senkronizasyon: Şimdi")
        lbl_sync_info.setProperty("color-role", "ok")
        lbl_sync_info.setStyleSheet("font-size: 11px; font-weight: 500;")
        lbl_sync_info.style().unpolish(lbl_sync_info)
        lbl_sync_info.style().polish(lbl_sync_info)
        sistem_layout.addWidget(lbl_sync_info)
        
        sistem_layout.addSpacing(20)
        
        # Kaydet butonu
        btn_sistem_kaydet = QPushButton("Sistem Ayarlarını Kaydet")
        btn_sistem_kaydet.setProperty("style-role", "action")
        btn_sistem_kaydet.style().unpolish(btn_sistem_kaydet)
        btn_sistem_kaydet.style().polish(btn_sistem_kaydet)
        IconRenderer.set_button_icon(btn_sistem_kaydet, "save", size=14)
        btn_sistem_kaydet.clicked.connect(self._save_system_settings)
        sistem_layout.addWidget(btn_sistem_kaydet)
        
        sistem_layout.addStretch()
        
        tabs.addTab(sistem_widget, "Online/Offline")
        tabs.setTabIcon(3, Icons.get("wifi"))

        layout.addWidget(tabs)
    
    def _load_data(self):
        """Verileri yükle"""
        self._load_sabitler()
        self._load_tatiller()
    
    def _load_sabitler(self):
        """Sabitleri yükle — Sol tarafta unique Kod'lar listele"""
        try:
            sonuc = self._service.get_sabitler()
            if sonuc.basarisiz:
                raise ValueError(sonuc.mesaj or "Sabitler alınamadı")
            sabitler = sonuc.veri or []
            
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
            if result.basarili:
                QMessageBox.information(self, "Başarılı", f"'{kod}' kategorisi oluşturuldu")
                self._load_sabitler()
            else:
                QMessageBox.critical(self, "Hata", result.mesaj)
    
    def _load_menu_elemanlari(self, kod: str | None = None):
        """Seçilen Kod'un MenuElemanlarını sağ tarafta göster"""
        try:
            self._table_menu_elemanlari.setRowCount(0)
            
            if not kod:
                return
            
            sonuc = self._service.get_sabitler()
            if sonuc.basarisiz:
                raise ValueError(sonuc.mesaj or "Menü elemanları alınamadı")
            sabitler = sonuc.veri or []
            
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
            sonuc = self._service.get_tatiller()
            if sonuc.basarisiz:
                raise ValueError(sonuc.mesaj or "Tatiller alınamadı")
            tatiller = sonuc.veri or []

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
                self._cmb_tatil_yil.setCurrentText(str(selected_year))
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
            sonuc = self._service.get_tatiller()
            if sonuc.basarisiz:
                return []
            tatiller = sonuc.veri or []
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
                if result.basarili:
                    QMessageBox.information(self, "Başarılı", f"'{kod}' kategorisi oluşturuldu ve '{menu_eleman}' seçeneği eklendi")
                    self._load_sabitler()
                else:
                    QMessageBox.critical(self, "Hata", result.mesaj)
            return
        
        # Kod seçili ise, yeni MenuEleman ekle
        kod = current_item.data(Qt.ItemDataRole.UserRole)
        
        dialog = SabitEditDialog(kod=kod, parent=self)
        # Kod alanını devre dışı bırak (zaten seçili)
        dialog._txt_kod.setReadOnly(True)
        dialog._txt_kod.setProperty("bg-role", "input")
        dialog._txt_kod.style().unpolish(dialog._txt_kod)
        dialog._txt_kod.style().polish(dialog._txt_kod)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            _, menu_eleman, aciklama = dialog.get_data()
            
            if not menu_eleman:
                QMessageBox.warning(self, "Uyarı", "Seçenek (MenuEleman) zorunludur")
                return
            
            result = self._service.add_sabit(kod, menu_eleman, aciklama)
            if result.basarili:
                QMessageBox.information(self, "Başarılı", f"'{menu_eleman}' seçeneği eklendi")
                self._on_kod_selected()  # Sağ tarafı yenile
            else:
                QMessageBox.critical(self, "Hata", result.mesaj)
    
    def _edit_menu_eleman(self):
        """Seçili MenuEleman'ı düzenle"""
        row = self._table_menu_elemanlari.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen düzenlemek için bir seçenek seçin")
            return
        
        item_0 = self._table_menu_elemanlari.item(row, 0)
        item_1 = self._table_menu_elemanlari.item(row, 1)
        if not item_0 or not item_1:
            return
        
        rowid = item_0.data(Qt.ItemDataRole.UserRole)
        kod = item_0.data(Qt.ItemDataRole.UserRole + 1)
        menu_eleman = item_0.text()
        aciklama = item_1.text()
        
        dialog = SabitEditDialog(kod, menu_eleman, aciklama, parent=self)
        # Kod alanını devre dışı bırak
        dialog._txt_kod.setReadOnly(True)
        dialog._txt_kod.setProperty("bg-role", "input")
        dialog._txt_kod.style().unpolish(dialog._txt_kod)
        dialog._txt_kod.style().polish(dialog._txt_kod)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            _, menu_eleman, aciklama = dialog.get_data()
            
            if not menu_eleman:
                QMessageBox.warning(self, "Uyarı", "Seçenek (MenuEleman) zorunludur")
                return
            
            result = self._service.update_sabit(rowid, kod, menu_eleman, aciklama)
            if result.basarili:
                QMessageBox.information(self, "Başarılı", "Seçenek güncellendi")
                self._on_kod_selected()  # Sağ tarafı yenile
            else:
                QMessageBox.critical(self, "Hata", result.mesaj)
    
    def _delete_menu_eleman(self):
        """Seçili MenuEleman'ı sil"""
        row = self._table_menu_elemanlari.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen silinecek seçeneği seçin")
            return
        
        item_0 = self._table_menu_elemanlari.item(row, 0)
        item_1 = self._table_menu_elemanlari.item(row, 1)
        if not item_0 or not item_1:
            return
        
        rowid = item_0.data(Qt.ItemDataRole.UserRole)
        menu_eleman = item_0.text()
        aciklama = item_1.text()
        
        reply = QMessageBox.question(
            self,
            "Seçenek Sil",
            f"'{menu_eleman}' seçeneğini silmek istediğinizden emin misiniz?\n\n({aciklama})",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            result = self._service.delete_sabit(rowid)
            if result.basarili:
                QMessageBox.information(self, "Başarılı", "Seçenek silindi")
                self._on_kod_selected()  # Sağ tarafı yenile
            else:
                QMessageBox.critical(self, "Hata", result.mesaj)
    
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
            if result.basarili:
                QMessageBox.information(self, "Başarılı", result.mesaj)
                self._load_tatiller()
            else:
                QMessageBox.critical(self, "Hata", result.mesaj)
    
    def _edit_tatil(self):
        """Tatili düzenle"""
        row = self._table_tatiller.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen düzenlemek için bir tatil seçin")
            return
        
        item_0 = self._table_tatiller.item(row, 0)
        item_1 = self._table_tatiller.item(row, 1)
        if not item_0 or not item_1:
            return
        
        tarih = item_0.text()
        resmi_tatil = item_1.text()
        
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
            
            if result.basarili:
                QMessageBox.information(self, "Başarılı", result.mesaj)
                self._load_tatiller()
            else:
                QMessageBox.critical(self, "Hata", result.mesaj)
    
    def _delete_tatil(self):
        """Tatili sil"""
        row = self._table_tatiller.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen silinecek tatili seçin")
            return
        
        item_0 = self._table_tatiller.item(row, 0)
        item_1 = self._table_tatiller.item(row, 1)
        if not item_0 or not item_1:
            return
        
        tarih = item_0.text()
        resmi_tatil = item_1.text()
        
        reply = QMessageBox.question(
            self,
            "Tatil Sil",
            f"'{resmi_tatil}' ({tarih}) tatilini silmek istediğinizden emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            result = self._service.delete_tatil(tarih)
            if result.basarili:
                QMessageBox.information(self, "Başarılı", result.mesaj)
                self._load_tatiller()
            else:
                QMessageBox.critical(self, "Hata", result.mesaj)

    def _apply_theme(self):
        """Tema değişikliğini uygula"""
        try:
            from PySide6.QtWidgets import QApplication
            from ui.theme_manager import ThemeManager
            
            if self._radio_dark.isChecked():
                tema = "dark"
                tema_adi = "Koyu Tema"
            else:
                tema = "light"
                tema_adi = "Açık Tema"
            
            logger.info(f"Tema değişimi başlatılıyor: {tema}")
            
            # QApplication örneğini al
            app = QApplication.instance()
            if not app:
                logger.error("QApplication örneği bulunamadı")
                QMessageBox.critical(self, "Hata", "Uygulama başlatılmamış")
                return
            
            # ThemeManager ile tema değiştir
            from typing import cast
            theme_manager = ThemeManager.instance()
            success = theme_manager.set_theme(cast(QApplication, app), tema)
            logger.info(f"Tema değişimi sonucu: {success}")
            
            if success:
                # STYLES cache'ini sıfırla (kalan STYLES kullanımları için)
                refresh_styles()
                logger.info(f"Tema başarıyla değiştirildi: {tema}")
                QMessageBox.information(
                    self,
                    "Başarılı",
                    f"Tema '{tema_adi}' olarak değiştirilmiştir.\n"
                    f"Değişiklikler anında uygulanmıştır."
                )
            else:
                logger.error("ThemeManager.set_theme False dönüştü")
                QMessageBox.critical(self, "Hata", "Tema değişikliği başarısız oldu")
                
        except Exception as e:
            logger.error(f"Tema değişikliği hatası: {e}", exc_info=True)
            QMessageBox.critical(self, "Hata", f"Tema değişikliği başarısız:\n{str(e)}")

    def refresh_theme(self):
        """
        Tema değişikliği sonrası bu sayfanın tüm inline stillerini yenile.
        ThemeManager, açık tüm sayfalarda bu metodu çağırmalıdır.
        """
        C = DarkTheme
        
        # Ana widget arkaplan
        self.setProperty("bg-role", "page"); self.style().unpolish(self); self.style().polish(self)
        
        # Tab widget
        tabs_widget = getattr(self, '_tabs', None)
        if tabs_widget:
            from typing import cast
            tabs_cast = cast(QTabWidget, tabs_widget)
            tabs_cast.setStyleSheet("""
                QTabWidget::pane {{
                    border: 1px solid {};
                    background-color: {};
                }}
                QTabBar::tab {{
                    background-color: {};
                    color: {};
                    padding: 8px 20px;
                    border: 1px solid {};
                    border-bottom: none;
                }}
                QTabBar::tab:selected {{
                    background-color: {};
                    color: {};
                    border-bottom: 1px solid {};
                }}
            """.format(
                C.BORDER_PRIMARY, C.BG_PRIMARY,
                C.BG_SECONDARY, C.TEXT_SECONDARY,
                C.BORDER_PRIMARY, C.BG_PRIMARY,
                C.TEXT_PRIMARY, C.BG_PRIMARY
            ))
        
        # RadioButton'lar
        if hasattr(self, '_radio_dark'):
            self._radio_dark.setProperty("color-role", "primary")
            self._radio_dark.setStyleSheet("font-size: 12px;")
            self._radio_dark.style().unpolish(self._radio_dark)
            self._radio_dark.style().polish(self._radio_dark)
        if hasattr(self, '_radio_light'):
            self._radio_light.setProperty("color-role", "primary")
            self._radio_light.setStyleSheet("font-size: 12px;")
            self._radio_light.style().unpolish(self._radio_light)
            self._radio_light.style().polish(self._radio_light)
        
        # Checkbox'lar
        if hasattr(self, '_chk_online_mod'):
            self._chk_online_mod.setProperty("color-role", "primary")
            self._chk_online_mod.setStyleSheet("font-size: 12px; font-weight: 500;")
            self._chk_online_mod.style().unpolish(self._chk_online_mod)
            self._chk_online_mod.style().polish(self._chk_online_mod)
        if hasattr(self, '_chk_auto_sync'):
            self._chk_auto_sync.setProperty("color-role", "primary")
            self._chk_auto_sync.setStyleSheet("font-size: 12px; font-weight: 500;")
            self._chk_auto_sync.style().unpolish(self._chk_auto_sync)
            self._chk_auto_sync.style().polish(self._chk_auto_sync)
        
        # Tablo ve liste stiller — global QSS kuralları geçerli, ek setStyleSheet gerekmez
        pass
        
        logger.debug("SettingsPage tema stilleri yenilendi")
    
    def _on_online_mode_changed(self):
        """Online mod değiştiğinde otomatik senkronizasyon seçeneğini güncelle"""
        is_online = self._chk_online_mod.isChecked()
        self._chk_auto_sync.setEnabled(is_online)
        
        if not is_online:
            self._chk_auto_sync.setChecked(False)
            logger.info("Offline moda geçildi, otomatik senkronizasyon devre dışı bırakıldı")
        else:
            logger.info("Online moda geçildi, otomatik senkronizasyon etkin kılınması önerilir")
    
    def _save_system_settings(self):
        """Sistem ayarlarını kaydet"""
        try:
            is_online = self._chk_online_mod.isChecked()
            auto_sync = self._chk_auto_sync.isChecked()
            
            # Doğrulama ve bilgi mesajı oluştur
            if is_online and auto_sync:
                mod_text = "Online (Otomatik Senkronizasyon)"
            elif is_online:
                mod_text = "Online (Manuel Senkronizasyon)"
            else:
                mod_text = "Offline (Yerel Veri)"
            
            # Sistem ayarlarını log'a yaz (later: config dosyasına kaydedilecek)
            logger.info(f"Sistem ayarları güncellendi - Mod: {mod_text}")
            logger.info(f"Online Mod: {is_online}, Otomatik Senkronizasyon: {auto_sync}")
            
            # AppConfig üzerinden kaydet (settings.json'a yazar)
            mode = AppConfig.MODE_ONLINE if is_online else AppConfig.MODE_OFFLINE
            AppConfig.set_app_mode(mode, persist=True)
            AppConfig.set_auto_sync(auto_sync, persist=True)

            QMessageBox.information(
                self,
                "Başarılı",
                f"Sistem ayarları kaydedilmiştir.\n\n"
                f"Mevcut Mod: {mod_text}\n"
                f"Yeniden başlatmada geçerli olacaktır."
            )
        except Exception as e:
            logger.error(f"Sistem ayarları kaydetme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Ayarlar kaydedilemedi:\n{str(e)}")


# -*- coding: utf-8 -*-
import os
from PySide6.QtCore import Qt, QDate, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QProgressBar, QFrame, QComboBox, QLineEdit,
    QDateEdit, QGroupBox, QMessageBox, QFileDialog
)
from PySide6.QtGui import QCursor, QPixmap

from core.logger import logger
from core.hata_yonetici import exc_logla
from ui.theme_manager import ThemeManager
from ui.styles import DarkTheme
from ui.styles.icons import IconRenderer


# ─── Drive Yükleme Worker (UI donmasın) ───
class DriveUploadWorker(QThread):
    finished = Signal(str, str)   # (alan_adi, webViewLink)
    error = Signal(str, str)      # (alan_adi, hata_mesaji)

    def __init__(self, file_path, folder_id, custom_name, alan_adi, offline_folder_name=None):
        super().__init__()
        self._file_path = file_path
        self._folder_id = folder_id
        self._custom_name = custom_name
        self._alan_adi = alan_adi
        self._offline_folder_name = offline_folder_name

    def run(self):
        try:
            from core.di import get_cloud_adapter
            cloud = get_cloud_adapter()
            link = cloud.upload_file(
                self._file_path,
                parent_folder_id=self._folder_id,
                custom_name=self._custom_name,
                offline_folder_name=self._offline_folder_name
            )
            if link:
                self.finished.emit(self._alan_adi, str(link))
            else:
                self.error.emit(self._alan_adi, "Yükleme başarısız (Offline modda hedef klasör tanımlı olmayabilir)")
        except Exception as e:
            exc_logla("CihazEkle.DosyaYukleyici", e)
            self.error.emit(self._alan_adi, str(e))


# ─── W11 Dark Glass Stiller (MERKEZİ KAYNAKTAN) ───
S = ThemeManager.get_all_component_styles()

# DB alan → form widget eşlemesi
FIELD_MAP = {
    "Marka": "marka",
    "Model": "model",
    "CihazTipi": "cihaz_tipi",
    "SeriNo": "seri_no",
    "Amac": "amac",
    "Kaynak": "kaynak",
    "AnaBilimDali": "ana_bilim_dali",
    "Birim": "birim",
    "BulunduguBina": "bina",
    "DemirbasNo": "demirbas_no",
    "NDKLisansNo": "ndk_lisans_no",
    "NDKSeriNo": "ndk_seri_no",
    "LisansDurum": "lisans_durum",
    "BitisTarihi": "lisans_bitis",
    "Sorumlusu": "sorumlu",
    "RKS": "rks",
    "HizmeteGirisTarihi": "hizmet_giris",
    "Durum": "durum",
    "GarantiDurumu": "garanti_durum",
    "GarantiBitisTarihi": "garanti_bitis",
    "BakimDurum": "bakim_durum",
    "KalibrasyonGereklimi": "kalibrasyon_gerekli",
}


class CihazEklePage(QWidget):
    """
    Cihaz Ekle / Düzenle sayfası.
    db: SQLiteManager instance
    edit_data: dict → düzenleme modunda mevcut veri
    on_saved: callback → kayıt sonrası çağrılır
    """

    def __init__(self, db=None, edit_data=None, on_saved=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(S["page"])
        self._db = db
        self._edit_data = edit_data
        self._on_saved = on_saved
        self._is_edit = edit_data is not None
        self.ui = {}
        self._file_paths = {}          # {"Img": path, "NDKLisansBelgesi": path}
        self._drive_links = {}         # {"Img": link, "NDKLisansBelgesi": link}
        self._drive_folders = {}       # {"Cihaz_Resim": folder_id, ...}
        self._upload_workers = []
        self._sabit_maps = {}
        self._all_sabit = []
        self._next_cihaz_sira = 1

        self._setup_ui()
        self._populate_combos()

        if self._is_edit:
            self._fill_form(edit_data)

    # ═══════════════════════════════════════════
    #  UI
    # ═══════════════════════════════════════════

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 12, 20, 12)
        main.setSpacing(12)

        # Scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(S["scroll"])

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content_layout = QHBoxLayout(content)
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # ── SOL SÜTUN ──
        left = QWidget()
        left_l = QVBoxLayout(left)
        left_l.setSpacing(12)
        left_l.setContentsMargins(0, 0, 0, 0)

        # Cihaz Görseli
        photo_grp = QGroupBox("Cihaz Gorseli")
        photo_grp.setStyleSheet(S["group"])
        photo_lay = QVBoxLayout(photo_grp)
        photo_lay.setAlignment(Qt.AlignCenter)

        self.lbl_resim = QLabel("Görsel\nYüklenmedi")
        self.lbl_resim.setFixedSize(200, 200)
        self.lbl_resim.setAlignment(Qt.AlignCenter)
        self.lbl_resim.setStyleSheet(S["photo_area"])
        photo_lay.addWidget(self.lbl_resim, alignment=Qt.AlignCenter)

        btn_resim = QPushButton("Gorsel Sec")
        btn_resim.setStyleSheet(S["photo_btn"])
        btn_resim.setCursor(QCursor(Qt.PointingHandCursor))
        btn_resim.clicked.connect(lambda: self._select_file("Img"))
        IconRenderer.set_button_icon(btn_resim, "upload", color=DarkTheme.TEXT_PRIMARY, size=14)
        photo_lay.addWidget(btn_resim, alignment=Qt.AlignCenter)
        left_l.addWidget(photo_grp)

        # Temel Bilgiler
        basic_grp = QGroupBox("Temel Bilgiler")
        basic_grp.setStyleSheet(S["group"])
        basic_lay = QHBoxLayout(basic_grp)
        basic_lay.setSpacing(10)

        # Cihaz ID (Otomatik)
        self.ui["cihaz_id"] = self._make_input("Cihaz ID (Otomatik)", basic_lay)
        self.ui["cihaz_id"].setReadOnly(True)
        self.ui["cihaz_id"].setStyleSheet(S["input"] + """
            QLineEdit {
                background-color: rgba(255,255,255,0.02);
                color: {DarkTheme.TEXT_MUTED};
            }
        """)

        # Demirbaş No
        self.ui["demirbas_no"] = self._make_input("Demirbaş No", basic_lay)

        left_l.addWidget(basic_grp)

        # Kimlik Bilgileri
        identity_grp = QGroupBox("Cihaz Kimlik Bilgileri")
        identity_grp.setStyleSheet(S["group"])
        identity_lay = QVBoxLayout(identity_grp)
        identity_lay.setSpacing(10)

        row1 = QHBoxLayout()
        self.ui["marka"] = self._make_combo("Marka *", row1, required=True)
        self.ui["marka"].setProperty("db_kod", "Marka")
        self.ui["model"] = self._make_input("Model *", row1, required=True)
        identity_lay.addLayout(row1)

        row2 = QHBoxLayout()
        self.ui["cihaz_tipi"] = self._make_combo("Cihaz Tipi *", row2, required=True)
        self.ui["cihaz_tipi"].setProperty("db_kod", "Cihaz_Tipi")
        self.ui["seri_no"] = self._make_input("Seri No *", row2, required=True)
        identity_lay.addLayout(row2)

        row3 = QHBoxLayout()
        self.ui["amac"] = self._make_combo("Kullanım Amacı", row3)
        self.ui["amac"].setProperty("db_kod", "Amac")
        self.ui["kaynak"] = self._make_combo("Edinim Kaynağı", row3)
        self.ui["kaynak"].setProperty("db_kod", "Kaynak")
        identity_lay.addLayout(row3)
        left_l.addWidget(identity_grp)
        left_l.addStretch()

        # ── SAĞ SÜTUN ──
        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setSpacing(12)
        right_l.setContentsMargins(0, 0, 0, 0)

        # Lokasyon Bilgileri
        location_grp = QGroupBox("Lokasyon Bilgileri")
        location_grp.setStyleSheet(S["group"])
        location_lay = QVBoxLayout(location_grp)
        location_lay.setSpacing(10)

        self.ui["ana_bilim_dali"] = self._make_combo_v("Ana Bilim Dalı", location_lay)
        self.ui["ana_bilim_dali"].setProperty("db_kod", "AnaBilimDali")

        row_loc = QHBoxLayout()
        self.ui["birim"] = self._make_combo("Birim", row_loc)
        self.ui["birim"].setProperty("db_kod", "Birim")
        self.ui["bina"] = self._make_input("Bulunduğu Bina", row_loc)
        location_lay.addLayout(row_loc)

        right_l.addWidget(location_grp)

        # Lisans Bilgileri
        license_grp = QGroupBox("Lisans Bilgileri")
        license_grp.setStyleSheet(S["group"])
        license_lay = QVBoxLayout(license_grp)
        license_lay.setSpacing(10)

        row_l1 = QHBoxLayout()
        self.ui["ndk_lisans_no"] = self._make_input("NDK Lisans No", row_l1)
        self.ui["ndk_seri_no"] = self._make_input("NDK Seri No", row_l1)
        license_lay.addLayout(row_l1)

        row_l2 = QHBoxLayout()
        self.ui["lisans_durum"] = self._make_combo("Lisans Durumu", row_l2)
        self.ui["lisans_durum"].setProperty("db_kod", "Lisans_Durum")
        self.ui["lisans_bitis"] = self._make_date("Lisans Bitiş Tarihi", row_l2)
        license_lay.addLayout(row_l2)

        btn_lisans = QPushButton("Lisans Belgesi Sec")
        btn_lisans.setStyleSheet(S["file_btn"])
        btn_lisans.setCursor(QCursor(Qt.PointingHandCursor))
        btn_lisans.clicked.connect(lambda: self._select_file("NDKLisansBelgesi"))
        IconRenderer.set_button_icon(btn_lisans, "upload", color=DarkTheme.TEXT_PRIMARY, size=14)
        license_lay.addWidget(btn_lisans)

        lbl_lisans_file = QLabel("")
        lbl_lisans_file.setStyleSheet(
            f"color: {DarkTheme.STATUS_SUCCESS}; font-size: 11px; background: transparent;"
        )
        license_lay.addWidget(lbl_lisans_file)
        self.ui["lisans_file_lbl"] = lbl_lisans_file
        right_l.addWidget(license_grp)

        # Teknik Bilgiler
        tech_info_grp = QGroupBox("Teknik Bilgiler")
        tech_info_grp.setStyleSheet(S["group"])
        tech_info_lay = QVBoxLayout(tech_info_grp)
        tech_info_lay.setSpacing(10)

        row_t1 = QHBoxLayout()
        self.ui["sorumlu"] = self._make_input("Sorumlu Kişi", row_t1)
        self.ui["rks"] = self._make_input("Radyasyon Kor. Sor.", row_t1)
        tech_info_lay.addLayout(row_t1)

        row_t2 = QHBoxLayout()
        self.ui["hizmet_giris"] = self._make_date("Hizmete Giriş Tarihi", row_t2)
        self.ui["durum"] = self._make_combo("Genel Durum", row_t2)
        self.ui["durum"].setProperty("db_kod", "Cihaz_Durum")
        tech_info_lay.addLayout(row_t2)

        right_l.addWidget(tech_info_grp)

        # Garanti ve Bakım
        maint_grp = QGroupBox("Garanti ve Bakim Durumu")
        maint_grp.setStyleSheet(S["group"])
        maint_lay = QVBoxLayout(maint_grp)
        maint_lay.setSpacing(10)

        row_m1 = QHBoxLayout()
        self.ui["garanti_durum"] = self._make_combo("Garanti Durumu", row_m1)
        self.ui["garanti_durum"].setProperty("db_kod", "Garanti_Durum")
        self.ui["garanti_bitis"] = self._make_date("Garanti Bitiş Tarihi", row_m1)
        maint_lay.addLayout(row_m1)

        row_m2 = QHBoxLayout()
        self.ui["bakim_durum"] = self._make_combo("Bakım Anlaşması", row_m2)
        self.ui["bakim_durum"].setProperty("db_kod", "Bakim_Durum")
        self.ui["kalibrasyon_gerekli"] = self._make_combo("Kalibrasyon Gerekli mi?", row_m2)
        self.ui["kalibrasyon_gerekli"].setProperty("db_kod", "Kalibrasyon_Durum")
        maint_lay.addLayout(row_m2)

        right_l.addWidget(maint_grp)
        right_l.addStretch()

        content_layout.addWidget(left, stretch=1)
        content_layout.addWidget(right, stretch=1)
        scroll.setWidget(content)
        main.addWidget(scroll, 1)

        # ── FOOTER ──
        footer = QHBoxLayout()
        footer.setSpacing(12)

        self.progress = QProgressBar()
        self.progress.setFixedWidth(150)
        self.progress.setFixedHeight(16)
        self.progress.setVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 4px; color: %s; font-size: 11px;
            }
            QProgressBar::chunk {
                background-color: %s;
                border-radius: 3px;
            }
        """ % (DarkTheme.TEXT_MUTED, DarkTheme.BTN_PRIMARY_HOVER))
        footer.addWidget(self.progress)
        footer.addStretch()

        btn_iptal = QPushButton("IPTAL")
        btn_iptal.setStyleSheet(S["cancel_btn"])
        btn_iptal.setCursor(QCursor(Qt.PointingHandCursor))
        btn_iptal.clicked.connect(self._on_cancel)
        IconRenderer.set_button_icon(btn_iptal, "x", color=DarkTheme.TEXT_PRIMARY, size=14)
        footer.addWidget(btn_iptal)

        title = "GÜNCELLE" if self._is_edit else "KAYDET"
        self.btn_kaydet = QPushButton(f"CIHAZI {title}")
        self.btn_kaydet.setStyleSheet(S["save_btn"])
        self.btn_kaydet.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kaydet.clicked.connect(self._on_save)
        IconRenderer.set_button_icon(self.btn_kaydet, "save", color=DarkTheme.TEXT_PRIMARY, size=14)
        footer.addWidget(self.btn_kaydet)

        main.addLayout(footer)

    # ═══════════════════════════════════════════
    #  YARDIMCI WIDGET FABRİKALARI
    # ═══════════════════════════════════════════

    def _make_input(self, label, parent_layout, required=False, placeholder=""):
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl = QLabel(label)
        lbl.setStyleSheet(S["required_label"] if required else S["label"])
        lay.addWidget(lbl)
        inp = QLineEdit()
        inp.setStyleSheet(S["input"])
        if placeholder:
            inp.setPlaceholderText(placeholder)
        lay.addWidget(inp)
        parent_layout.addWidget(container)
        return inp

    def _make_combo(self, label, parent_layout, required=False, editable=False):
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl = QLabel(label)
        lbl.setStyleSheet(S["required_label"] if required else S["label"])
        lay.addWidget(lbl)
        cmb = QComboBox()
        cmb.setStyleSheet(S["combo"])
        cmb.setEditable(editable)
        lay.addWidget(cmb)
        parent_layout.addWidget(container)
        return cmb

    def _make_date(self, label, parent_layout, required=False):
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl = QLabel(label)
        lbl.setStyleSheet(S["required_label"] if required else S["label"])
        lay.addWidget(lbl)
        de = QDateEdit()
        de.setStyleSheet(S["date"])
        de.setCalendarPopup(True)
        de.setDate(QDate.currentDate())
        de.setDisplayFormat("dd.MM.yyyy")

        ThemeManager.setup_calendar_popup(de)

        lay.addWidget(de)
        parent_layout.addWidget(container)
        return de

    # Dikey versiyon
    def _make_input_v(self, label, parent_layout, placeholder=""):
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label"])
        parent_layout.addWidget(lbl)
        inp = QLineEdit()
        inp.setStyleSheet(S["input"])
        if placeholder:
            inp.setPlaceholderText(placeholder)
        parent_layout.addWidget(inp)
        return inp

    def _make_combo_v(self, label, parent_layout, editable=False):
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label"])
        parent_layout.addWidget(lbl)
        cmb = QComboBox()
        cmb.setStyleSheet(S["combo"])
        cmb.setEditable(editable)
        parent_layout.addWidget(cmb)
        return cmb

    def _make_date_v(self, label, parent_layout):
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label"])
        parent_layout.addWidget(lbl)
        de = QDateEdit()
        de.setStyleSheet(S["date"])
        de.setCalendarPopup(True)
        de.setDate(QDate.currentDate())
        de.setDisplayFormat("dd.MM.yyyy")
        ThemeManager.setup_calendar_popup(de)
        parent_layout.addWidget(de)
        return de

    # ═══════════════════════════════════════════
    #  COMBOBOX POPULATE
    # ═══════════════════════════════════════════

    def _populate_combos(self):
        """ComboBox'ları Sabitler tablosundan doldurur"""
        if not self._db:
            return

        try:
            from core.di import get_registry
            registry = get_registry(self._db)
            sabitler_repo = registry.get("Sabitler")
            all_sabit = sabitler_repo.get_all()
            self._all_sabit = all_sabit

            sabitler_map = {}
            self._sabit_maps = {"AnaBilimDali": {}, "Cihaz_Tipi": {}, "Kaynak": {}}

            for item in all_sabit:
                kod = item.get("Kod")
                eleman = item.get("MenuEleman")
                if not (kod and eleman):
                    continue

                if kod not in sabitler_map:
                    sabitler_map[kod] = []
                sabitler_map[kod].append(eleman)

                if kod in self._sabit_maps:
                    kisaltma = str(item.get("Aciklama", "")).strip()
                    if kisaltma:
                        self._sabit_maps[kod][eleman] = kisaltma

            for widget in self.ui.values():
                if isinstance(widget, QComboBox):
                    db_kod = widget.property("db_kod")
                    if db_kod in sabitler_map:
                        widget.addItems([""] + sorted(sabitler_map[db_kod]))

            # Cihaz ID için sıradaki no
            cihaz_repo = registry.get("Cihazlar")
            max_id = 0
            for cihaz in cihaz_repo.get_all():
                val = str(cihaz.get("Cihazid", "")).strip()
                if val and '-' in val:
                    try:
                        num = int(val.split('-')[-1])
                        if num > max_id and num < 9000:
                            max_id = num
                    except (ValueError, IndexError):
                        pass
            self._next_cihaz_sira = max_id + 1

            # Sinyalleri bağla
            for key in ["ana_bilim_dali", "cihaz_tipi", "kaynak"]:
                if key in self.ui:
                    self.ui[key].currentTextChanged.connect(self._update_cihaz_id)
            self._update_cihaz_id()

            # Drive klasör ID'leri
            self._drive_folders = {
                str(r.get("MenuEleman", "")).strip(): str(r.get("Aciklama", "")).strip()
                for r in all_sabit if r.get("Kod") == "Sistem_DriveID"
            }

        except Exception as e:
            logger.error(f"Combo populate hatası: {e}")

    def _update_cihaz_id(self):
        """Cihaz ID'yi otomatik oluşturur"""
        try:
            abd = self.ui["ana_bilim_dali"].currentText().strip()
            tip = self.ui["cihaz_tipi"].currentText().strip()
            kaynak = self.ui["kaynak"].currentText().strip()

            abd_short = self._sabit_maps.get("AnaBilimDali", {}).get(abd, "")
            tip_short = self._sabit_maps.get("Cihaz_Tipi", {}).get(tip, "")
            kaynak_short = self._sabit_maps.get("Kaynak", {}).get(kaynak, "")

            if abd_short and tip_short and kaynak_short:
                cihaz_id = f"{abd_short}-{tip_short}-{kaynak_short}-{self._next_cihaz_sira:04d}"
                self.ui["cihaz_id"].setText(cihaz_id)
            else:
                self.ui["cihaz_id"].setText("")
        except Exception as e:
            logger.error(f"Cihaz ID güncelleme hatası: {e}")

    # ═══════════════════════════════════════════
    #  DOSYA SEÇİMİ
    # ═══════════════════════════════════════════

    def _select_file(self, alan_adi):
        """Dosya seçici dialog"""
        if alan_adi == "Img":
            file_filter = "Görsel Dosyaları (*.jpg *.jpeg *.png *.bmp *.gif)"
        else:
            file_filter = "Belgeler (*.pdf *.jpg *.jpeg *.png)"

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"{alan_adi} Seç",
            "",
            file_filter
        )

        if file_path:
            self._file_paths[alan_adi] = file_path
            logger.info(f"{alan_adi} seçildi: {file_path}")

            if alan_adi == "Img":
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    self.lbl_resim.setPixmap(
                        pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    )
                    self.lbl_resim.setScaledContents(False)
            elif alan_adi == "NDKLisansBelgesi":
                file_name = os.path.basename(file_path)
                self.ui["lisans_file_lbl"].setText(file_name)

    # ═══════════════════════════════════════════
    #  FORM İŞLEMLERİ
    # ═══════════════════════════════════════════

    def _fill_form(self, data):
        """Formu mevcut veri ile doldurur (düzenleme modu)"""
        for db_field, widget_key in FIELD_MAP.items():
            if widget_key in self.ui:
                widget = self.ui[widget_key]
                value = data.get(db_field, "")

                if isinstance(widget, QLineEdit):
                    widget.setText(str(value))
                elif isinstance(widget, QComboBox):
                    idx = widget.findText(str(value))
                    if idx >= 0:
                        widget.setCurrentIndex(idx)
                elif isinstance(widget, QDateEdit):
                    if value:
                        try:
                            date = QDate.fromString(str(value), "yyyy-MM-dd")
                            if date.isValid():
                                widget.setDate(date)
                        except:
                            pass

        # Cihaz ID
        self.ui["cihaz_id"].setText(data.get("Cihazid", ""))

        # Görsel
        img_link = data.get("Img", "")
        if img_link:
            self._drive_links["Img"] = img_link
            # TODO: Drive'dan görsel indirip göster

    def _on_save(self):
        """Kaydet butonu"""
        # Zorunlu alanları kontrol et
        required_fields = {
            "marka": "Marka",
            "model": "Model",
            "cihaz_tipi": "Cihaz Tipi",
            "seri_no": "Seri No"
        }

        for key, name in required_fields.items():
            if key in self.ui:
                widget = self.ui[key]
                value = ""
                if isinstance(widget, QLineEdit):
                    value = widget.text().strip()
                elif isinstance(widget, QComboBox):
                    value = widget.currentText().strip()

                if not value:
                    QMessageBox.warning(self, "Eksik Bilgi", f"Lütfen {name} alanını doldurun!")
                    widget.setFocus()
                    return

        # Veriyi topla
        data = {}
        for db_field, widget_key in FIELD_MAP.items():
            if widget_key in self.ui:
                widget = self.ui[widget_key]
                if isinstance(widget, QLineEdit):
                    data[db_field] = widget.text().strip()
                elif isinstance(widget, QComboBox):
                    data[db_field] = widget.currentText().strip()
                elif isinstance(widget, QDateEdit):
                    data[db_field] = widget.date().toString("yyyy-MM-dd")

        data["Cihazid"] = self.ui["cihaz_id"].text().strip()

        # Drive yüklemeleri
        if self._file_paths:
            self.btn_kaydet.setEnabled(False)
            self.progress.setVisible(True)
            self._upload_to_drive(data)
        else:
            self._save_to_db(data)

    def _upload_to_drive(self, data):
        """Dosyaları Drive'a yükle"""
        from database.google.utils import resolve_storage_target

        for alan_adi, file_path in self._file_paths.items():
            target = resolve_storage_target(self._all_sabit, f"Cihaz_{alan_adi}")
            folder_id = target.get("drive_folder_id")
            offline_folder_name = target.get("offline_folder_name")
            
            custom_name = f"{data['Cihazid']}_{alan_adi}{os.path.splitext(file_path)[1]}"

            worker = DriveUploadWorker(file_path, folder_id, custom_name, alan_adi, offline_folder_name)
            worker.finished.connect(lambda a, l: self._on_upload_finished(a, l, data))
            worker.error.connect(self._on_upload_error)
            worker.start()
            self._upload_workers.append(worker)

    def _on_upload_finished(self, alan_adi, link, data):
        """Drive yükleme tamamlandı"""
        self._drive_links[alan_adi] = link
        logger.info(f"{alan_adi} yüklendi: {link}")

        # Tüm yüklemeler tamamlandı mı?
        if len(self._drive_links) == len(self._file_paths):
            self._save_to_db(data)

    def _on_upload_error(self, alan_adi, error_msg):
        """Drive yükleme hatası"""
        logger.error(f"{alan_adi} yükleme hatası: {error_msg}")
        QMessageBox.warning(self, "Yükleme Hatası", f"{alan_adi} yüklenemedi: {error_msg}")
        self.btn_kaydet.setEnabled(True)
        self.progress.setVisible(False)

    def _save_to_db(self, data):
        """Veritabanına kaydet"""
        try:
            # Drive linklerini ekle
            for alan_adi, link in self._drive_links.items():
                data[alan_adi] = link

            from core.di import get_registry
            registry = get_registry(self._db)
            cihaz_repo = registry.get("Cihazlar")

            if self._is_edit:
                pk = self._edit_data.get("Cihazid")
                cihaz_repo.update(pk, data)
                QMessageBox.information(self, "Başarılı", "Cihaz güncellendi!")
            else:
                cihaz_repo.insert(data)
                QMessageBox.information(self, "Başarılı", "Cihaz kaydedildi!")

            if self._on_saved:
                self._on_saved()

        except Exception as e:
            logger.error(f"Kayıt hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Kayıt başarısız: {e}")
        finally:
            self.btn_kaydet.setEnabled(True)
            self.progress.setVisible(False)

    def _on_cancel(self):
        """İptal butonu"""
        reply = QMessageBox.question(
            self,
            "İptal",
            "Değişiklikler kaydedilmeyecek. Devam edilsin mi?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if self._on_saved:
                self._on_saved()

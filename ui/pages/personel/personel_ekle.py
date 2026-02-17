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
from core.date_utils import parse_date
from ui.theme_manager import ThemeManager
from ui.styles import DarkTheme
from ui.styles.icons import IconRenderer


# ─── Drive Yükleme Worker (UI donmasın) ───
class DriveUploadWorker(QThread):
    finished = Signal(str, str)   # (alan_adi, webViewLink)
    error = Signal(str, str)      # (alan_adi, hata_mesaji)

    def __init__(self, file_path, folder_id, custom_name, alan_adi):
        super().__init__()
        self._file_path = file_path
        self._folder_id = folder_id
        self._custom_name = custom_name
        self._alan_adi = alan_adi

    def run(self):
        try:
            from database.google import GoogleDriveService
            drive = GoogleDriveService()
            link = drive.upload_file(
                self._file_path,
                parent_folder_id=self._folder_id,
                custom_name=self._custom_name
            )
            if link:
                self.finished.emit(self._alan_adi, link)
            else:
                self.error.emit(self._alan_adi, "Yükleme başarısız")
        except Exception as e:
            exc_logla("PersonelEkle.DosyaYukleyici", e)
            self.error.emit(self._alan_adi, str(e))

# ─── W11 Dark Glass Stiller (MERKEZİ KAYNAKTAN) ───
S = ThemeManager.get_all_component_styles()

# DB alan → form widget eşlemesi
FIELD_MAP = {
    "KimlikNo": "tc",
    "AdSoyad": "ad_soyad",
    "DogumYeri": "dogum_yeri",
    "DogumTarihi": "dogum_tarihi",
    "HizmetSinifi": "hizmet_sinifi",
    "KadroUnvani": "kadro_unvani",
    "GorevYeri": "gorev_yeri",
    "KurumSicilNo": "sicil_no",
    "MemuriyeteBaslamaTarihi": "baslama_tarihi",
    "CepTelefonu": "cep_tel",
    "Eposta": "eposta",
    "MezunOlunanOkul": "okul1",
    "MezunOlunanFakulte": "fakulte1",
    "MezuniyetTarihi": "mezun_tarihi1",
    "DiplomaNo": "diploma_no1",
    "MezunOlunanOkul2": "okul2",
    "MezunOlunanFakulte2": "fakulte2",
    "MezuniyetTarihi2": "mezun_tarihi2",
    "DiplomaNo2": "diploma_no2",
}


class PersonelEklePage(QWidget):
    """
    Personel Ekle / Düzenle sayfası.
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
        self._file_paths = {}          # {"Resim": path, "Diploma1": path, ...}
        self._drive_links = {}         # {"Resim": link, "Diploma1": link, ...}
        self._drive_folders = {}       # {"Personel_Resim": folder_id, ...}
        self._upload_workers = []

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

        # Fotoğraf
        photo_grp = QGroupBox("Fotograf")
        photo_grp.setStyleSheet(S["group"])
        photo_lay = QVBoxLayout(photo_grp)
        photo_lay.setAlignment(Qt.AlignCenter)

        self.lbl_resim = QLabel("Fotoğraf\nYüklenmedi")
        self.lbl_resim.setFixedSize(160, 200)
        self.lbl_resim.setAlignment(Qt.AlignCenter)
        self.lbl_resim.setStyleSheet(S["photo_area"])
        photo_lay.addWidget(self.lbl_resim, alignment=Qt.AlignCenter)

        btn_resim = QPushButton("Fotograf Sec")
        btn_resim.setStyleSheet(S["photo_btn"])
        btn_resim.setCursor(QCursor(Qt.PointingHandCursor))
        btn_resim.clicked.connect(self._select_photo)
        IconRenderer.set_button_icon(btn_resim, "upload", color=DarkTheme.TEXT_PRIMARY, size=14)
        photo_lay.addWidget(btn_resim, alignment=Qt.AlignCenter)
        left_l.addWidget(photo_grp)

        # Kimlik Bilgileri
        id_grp = QGroupBox("Kimlik Bilgileri")
        id_grp.setStyleSheet(S["group"])
        id_lay = QVBoxLayout(id_grp)
        id_lay.setSpacing(10)

        row1 = QHBoxLayout()
        self.ui["tc"] = self._make_input("TC Kimlik No *", row1, required=True)
        self.ui["tc"].setMaxLength(11)
        from PySide6.QtCore import QRegularExpression
        from PySide6.QtGui import QRegularExpressionValidator
        self.ui["tc"].setValidator(QRegularExpressionValidator(QRegularExpression(r"^\d{0,11}$")))
        self.ui["ad_soyad"] = self._make_input("Ad Soyad *", row1, required=True)
        id_lay.addLayout(row1)

        row2 = QHBoxLayout()
        self.ui["dogum_yeri"] = self._make_combo("Doğum Yeri", row2, editable=True)
        self.ui["dogum_tarihi"] = self._make_date("Doğum Tarihi", row2)
        id_lay.addLayout(row2)

        left_l.addWidget(id_grp)

        # İletişim
        contact_grp = QGroupBox("Iletisim Bilgileri")
        contact_grp.setStyleSheet(S["group"])
        contact_lay = QVBoxLayout(contact_grp)

        row_c = QHBoxLayout()
        self.ui["cep_tel"] = self._make_input("Cep Telefonu", row_c, placeholder="05XX XXX XX XX")
        self.ui["eposta"] = self._make_input("E-posta Adresi", row_c, placeholder="ornek@email.com")
        contact_lay.addLayout(row_c)

        left_l.addWidget(contact_grp)

        left_l.addStretch()

        # ── SAĞ SÜTUN ──
        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setSpacing(12)
        right_l.setContentsMargins(0, 0, 0, 0)

        # Kurumsal
        corp_grp = QGroupBox("Kadro ve Kurumsal Bilgiler")
        corp_grp.setStyleSheet(S["group"])
        corp_lay = QVBoxLayout(corp_grp)
        corp_lay.setSpacing(10)

        row_k1 = QHBoxLayout()
        self.ui["hizmet_sinifi"] = self._make_combo("Hizmet Sınıfı *", row_k1, required=True)
        self.ui["kadro_unvani"] = self._make_combo("Kadro Ünvanı *", row_k1, required=True)
        corp_lay.addLayout(row_k1)

        row_k2 = QHBoxLayout()
        self.ui["gorev_yeri"] = self._make_combo("Görev Yeri", row_k2)
        self.ui["sicil_no"] = self._make_input("Kurum Sicil No", row_k2)
        corp_lay.addLayout(row_k2)

        row_k3 = QHBoxLayout()
        self.ui["baslama_tarihi"] = self._make_date("Memuriyete Başlama Tarihi", row_k3)
        row_k3.addStretch()
        corp_lay.addLayout(row_k3)

        right_l.addWidget(corp_grp)

        # Eğitim
        edu_grp = QGroupBox("Egitim Bilgileri")
        edu_grp.setStyleSheet(S["group"])
        edu_main = QHBoxLayout(edu_grp)
        edu_main.setSpacing(16)

        for i in ["1", "2"]:
            col = QVBoxLayout()
            col.setSpacing(8)

            header = QLabel(f"{'Lise / Önlisans / Lisans' if i == '1' else 'Lisans / Yüksek Lisans / Lisans Tamamlama'}")
            header.setStyleSheet(S.get("section_title", ""))
            col.addWidget(header)

            self.ui[f"okul{i}"] = self._make_combo_v(f"Okul Adı", col, editable=True)
            self.ui[f"fakulte{i}"] = self._make_combo_v(f"Bölüm / Fakülte", col, editable=True)
            self.ui[f"mezun_tarihi{i}"] = self._make_input_v(f"Mezuniyet Tarihi", col)
            self.ui[f"diploma_no{i}"] = self._make_input_v(f"Diploma No", col)

            btn_dip = QPushButton(f"Diploma {i} Sec")
            btn_dip.setStyleSheet(S["file_btn"])
            btn_dip.setCursor(QCursor(Qt.PointingHandCursor))
            btn_dip.clicked.connect(lambda checked, idx=i: self._select_diploma(idx))
            IconRenderer.set_button_icon(btn_dip, "upload", color=DarkTheme.TEXT_PRIMARY, size=14)
            col.addWidget(btn_dip)

            # Seçili dosya etiketi
            lbl_file = QLabel("")
            lbl_file.setStyleSheet(
                f"color: {DarkTheme.STATUS_SUCCESS}; font-size: 11px; background: transparent;"
            )
            col.addWidget(lbl_file)
            self.ui[f"diploma_file_lbl{i}"] = lbl_file

            edu_main.addLayout(col)

            if i == "1":
                sep = QFrame()
                sep.setFrameShape(QFrame.VLine)
                sep.setFixedWidth(1)
                sep.setStyleSheet(S["separator"])
                edu_main.addWidget(sep)

        right_l.addWidget(edu_grp)
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
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 4px; color: {DarkTheme.TEXT_MUTED}; font-size: 11px;
            }}
            QProgressBar::chunk {{
                background-color: rgba(29, 117, 254, 0.6);
                border-radius: 3px;
            }}
        """)
        footer.addWidget(self.progress)
        footer.addStretch()

        btn_iptal = QPushButton("IPTAL")
        btn_iptal.setStyleSheet(S["cancel_btn"])
        btn_iptal.setCursor(QCursor(Qt.PointingHandCursor))
        btn_iptal.clicked.connect(self._on_cancel)
        IconRenderer.set_button_icon(btn_iptal, "x", color=DarkTheme.TEXT_PRIMARY, size=14)
        footer.addWidget(btn_iptal)

        title = "GÜNCELLE" if self._is_edit else "KAYDET"
        self.btn_kaydet = QPushButton(f"PERSONELI {title}")
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

    # Dikey versiyon (eğitim bölümü için)
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

    # ═══════════════════════════════════════════
    #  COMBO DOLDURMA
    # ═══════════════════════════════════════════

    def _populate_combos(self):
        """Combobox'ları Sabitler + Personel tablosundan doldurur."""
        if not self._db:
            return

        try:
            from core.di import get_registry
            registry = get_registry(self._db)

            # ── Sabitler'den ──
            sabitler = registry.get("Sabitler")
            all_sabit = sabitler.get_all()

            def get_sabit(kod):
                return sorted([
                    str(r.get("MenuEleman", "")).strip()
                    for r in all_sabit
                    if r.get("Kod") == kod and r.get("MenuEleman", "").strip()
                ])

            # Hizmet Sınıfı
            self.ui["hizmet_sinifi"].clear()
            self.ui["hizmet_sinifi"].addItem("")
            self.ui["hizmet_sinifi"].addItems(get_sabit("Hizmet_Sinifi"))

            # Kadro Ünvanı
            self.ui["kadro_unvani"].clear()
            self.ui["kadro_unvani"].addItem("")
            self.ui["kadro_unvani"].addItems(get_sabit("Kadro_Unvani"))

            # Görev Yeri
            self.ui["gorev_yeri"].clear()
            self.ui["gorev_yeri"].addItem("")
            self.ui["gorev_yeri"].addItems(get_sabit("Gorev_Yeri"))

            # ── Personel'den benzersiz Doğum Yeri ──
            personeller = registry.get("Personel")
            all_personel = personeller.get_all()

            dogum_yerleri = sorted(set(
                str(r.get("DogumYeri", "")).strip()
                for r in all_personel
                if r.get("DogumYeri", "").strip()
            ))
            self.ui["dogum_yeri"].clear()
            self.ui["dogum_yeri"].addItem("")
            self.ui["dogum_yeri"].addItems(dogum_yerleri)

            okullar = sorted(set(
                s for r in all_personel
                for col in ("MezunOlunanOkul", "MezunOlunanOkul2")
                if (s := str(r.get(col, "")).strip())
            ))
            for k in ["okul1", "okul2"]:
                self.ui[k].clear()
                self.ui[k].addItem("")
                self.ui[k].addItems(okullar)

            # ── Personel'den benzersiz Fakülteler ──
            fakulteler = sorted(set(
                s for r in all_personel
                for col in ("MezunOlunanFakulte", "MezunOlunanFakulte2")
                if (s := str(r.get(col, "")).strip())
            ))
            for k in ["fakulte1", "fakulte2"]:
                self.ui[k].clear()
                self.ui[k].addItem("")
                self.ui[k].addItems(fakulteler)

            # ── Drive klasör ID'leri ──
            self._drive_folders = {
                str(r.get("MenuEleman", "")).strip(): str(r.get("Aciklama", "")).strip()
                for r in all_sabit
                if r.get("Kod") == "Sistem_DriveID" and r.get("Aciklama", "").strip()
            }
            logger.info(f"Drive klasörleri: {list(self._drive_folders.keys())}")

        except Exception as e:
            logger.error(f"Combo doldurma hatası: {e}")

    # ═══════════════════════════════════════════
    #  FORM → VERİ
    # ═══════════════════════════════════════════

    def _get_widget_value(self, key):
        """Widget'tan değer alır."""
        w = self.ui.get(key)
        if w is None:
            return ""
        if isinstance(w, QLineEdit):
            return w.text().strip()
        if isinstance(w, QComboBox):
            return w.currentText().strip()
        if isinstance(w, QDateEdit):
            return w.date().toString("yyyy-MM-dd")
        return ""

    def _set_widget_value(self, key, value):
        """Widget'a değer set eder."""
        w = self.ui.get(key)
        if w is None:
            return
        value = str(value).strip() if value else ""
        if isinstance(w, QLineEdit):
            w.setText(value)
        elif isinstance(w, QComboBox):
            idx = w.findText(value)
            if idx >= 0:
                w.setCurrentIndex(idx)
            elif w.isEditable():
                w.setEditText(value)
            else:
                w.addItem(value)
                w.setCurrentText(value)
        elif isinstance(w, QDateEdit):
            if value:
                try:
                    parsed = parse_date(value)
                    d = QDate(parsed.year, parsed.month, parsed.day) if parsed else QDate.fromString(value, "yyyy-MM-dd")
                    if d.isValid():
                        w.setDate(d)
                except Exception:
                    pass

    def _collect_data(self):
        data = {}
        for db_col, ui_key in FIELD_MAP.items():
            data[db_col] = self._get_widget_value(ui_key)
        data["Durum"] = "Aktif"
        return data
    

    def _fill_form(self, row_data):
        """Mevcut veriyi forma doldurur (düzenleme modu)."""
        for db_col, ui_key in FIELD_MAP.items():
            value = row_data.get(db_col, "")
            self._set_widget_value(ui_key, value)

    # ═══════════════════════════════════════════
    #  DOSYA SEÇME & DRIVE YÜKLEME
    # ═══════════════════════════════════════════

    def _select_photo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Fotoğraf Seç", "",
            "Resim Dosyaları (*.jpg *.jpeg *.png *.bmp);;Tüm Dosyalar (*)"
        )
        if path:
            self._file_paths["Resim"] = path
            # Önizleme göster
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                self.lbl_resim.setPixmap(
                    pixmap.scaled(160, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
            self.lbl_resim.setToolTip(os.path.basename(path))
            logger.info(f"Fotoğraf seçildi: {path}")

    def _select_diploma(self, idx):
        path, _ = QFileDialog.getOpenFileName(
            self, f"Diploma {idx} Seç", "",
            "Dosyalar (*.pdf *.jpg *.jpeg *.png);;Tüm Dosyalar (*)"
        )
        if path:
            key = f"Diploma{idx}"
            self._file_paths[key] = path
            lbl = self.ui.get(f"diploma_file_lbl{idx}")
            if lbl:
                lbl.setText(os.path.basename(path))
            logger.info(f"Diploma {idx} seçildi: {path}")

    def _get_drive_folder_id(self, folder_name):
        """Sabitler'den Drive klasör ID'sini döndürür."""
        return self._drive_folders.get(folder_name, "")

    def _upload_files_to_drive(self, tc_no, callback):
        """Seçili dosyaları Drive'a yükler, bitince callback çağırır."""
        # Yüklenecek dosya yoksa direkt callback
        if not self._file_paths:
            callback()
            return

        upload_map = {
            "Resim":    ("Personel_Resim",   "Resim"),
            "Diploma1": ("Personel_Diploma",  "Diploma1"),
            "Diploma2": ("Personel_Diploma",  "Diploma2"),
        }

        self._pending_uploads = 0
        self._upload_errors = []

        for file_key, file_path in self._file_paths.items():
            if file_key not in upload_map:
                continue
            folder_name, db_field = upload_map[file_key]
            folder_id = self._get_drive_folder_id(folder_name)
            if not folder_id:
                logger.warning(f"Drive klasör bulunamadı: {folder_name}")
                continue

            # Dosya adı: TC_alan.uzantı
            ext = os.path.splitext(file_path)[1]
            custom_name = f"{tc_no}_{db_field}{ext}"

            self._pending_uploads += 1
            worker = DriveUploadWorker(file_path, folder_id, custom_name, db_field)
            worker.finished.connect(self._on_upload_finished)
            worker.error.connect(self._on_upload_error)
            self._upload_workers.append(worker)
            worker.start()

        if self._pending_uploads == 0:
            callback()
        else:
            self._upload_callback = callback
            self.progress.setVisible(True)
            self.progress.setRange(0, 0)  # indeterminate
            self.btn_kaydet.setEnabled(False)

    def _on_upload_finished(self, alan_adi, link):
        """Tek dosya yükleme tamamlandı."""
        self._drive_links[alan_adi] = link
        logger.info(f"Drive yükleme OK: {alan_adi} → {link}")
        self._pending_uploads -= 1
        if self._pending_uploads <= 0:
            self._finalize_uploads()

    def _on_upload_error(self, alan_adi, hata):
        """Tek dosya yükleme hatası."""
        self._upload_errors.append(f"{alan_adi}: {hata}")
        logger.error(f"Drive yükleme HATA: {alan_adi} → {hata}")
        self._pending_uploads -= 1
        if self._pending_uploads <= 0:
            self._finalize_uploads()

    def _finalize_uploads(self):
        """Tüm yüklemeler bitti."""
        self.progress.setVisible(False)
        self.btn_kaydet.setEnabled(True)
        self._upload_workers.clear()

        if self._upload_errors:
            QMessageBox.warning(
                self, "Drive Yükleme Uyarısı",
                "Bazı dosyalar yüklenemedi:\n" + "\n".join(self._upload_errors)
            )

        if hasattr(self, "_upload_callback"):
            self._upload_callback()

    # ═══════════════════════════════════════════
    #  KAYDET / İPTAL
    # ═══════════════════════════════════════════

    def _validate(self):
        """Zorunlu alan kontrolü."""
        errors = []
        tc = self._get_widget_value("tc")
        if not tc:
            errors.append("TC Kimlik No boş olamaz")
        elif len(tc) != 11 or not tc.isdigit():
            errors.append("TC Kimlik No 11 haneli rakam olmalı")

        if not self._get_widget_value("ad_soyad"):
            errors.append("Ad Soyad boş olamaz")
        if not self._get_widget_value("hizmet_sinifi"):
            errors.append("Hizmet Sınıfı seçilmeli")
        if not self._get_widget_value("kadro_unvani"):
            errors.append("Kadro Ünvanı seçilmeli")

        return errors

    def _on_save(self):
        """Kaydet: validasyon → Drive yükleme → DB kayıt."""
        errors = self._validate()
        if errors:
            QMessageBox.warning(
                self, "Eksik Bilgi",
                "\n".join(f"• {e}" for e in errors)
            )
            return

        data = self._collect_data()
        tc_no = data["KimlikNo"]
        
        # Elle girilen metin alanlarını Title Case yap
        title_fields = [
            "AdSoyad", "DogumYeri",
            "MezunOlunanOkul", "MezunOlunanFakulte",
            "MezunOlunanOkul2", "MezunOlunanFakulte2",
        ]
        for field in title_fields:
            if data.get(field):
                data[field] = data[field].title()
        # Düzenleme değilse aynı TC kontrolü
        if not self._is_edit:
            try:
                from core.di import get_registry
                registry = get_registry(self._db)
                repo = registry.get("Personel")
                existing = repo.get_by_id(tc_no)
                if existing:
                    QMessageBox.warning(
                        self, "Kayıt Mevcut",
                        f"TC {tc_no} ile kayıtlı personel zaten var."
                    )
                    return
            except Exception as e:
                logger.error(f"TC kontrol hatası: {e}")

        # Dosya varsa önce Drive'a yükle, sonra kaydet
        self._pending_data = data
        self._upload_files_to_drive(tc_no, self._save_to_db)

    def _save_to_db(self):
        """Drive yüklemesi bittikten sonra DB'ye kaydet."""
        data = self._pending_data

        # Drive linklerini data'ya ekle
        link_map = {
            "Resim": "Resim",
            "Diploma1": "Diploma1",
            "Diploma2": "Diploma2",
        }
        for drive_key, db_col in link_map.items():
            link = self._drive_links.get(drive_key, "")
            if link:
                data[db_col] = link

        try:
            from core.di import get_registry
            registry = get_registry(self._db)
            repo = registry.get("Personel")

            if self._is_edit:
                repo.update(data["KimlikNo"], data)
                logger.info(f"Personel güncellendi: {data['KimlikNo']}")
            else:
                repo.insert(data)
                logger.info(f"Yeni personel eklendi: {data['KimlikNo']}")

                # Yeni personel için Izin_Bilgi kaydı oluştur
                try:
                    repo_izin = registry.get("Izin_Bilgi")
                    izin_data = {
                        "Personelid": data["KimlikNo"],
                        "AdSoyad": data["AdSoyad"]
                    }
                    repo_izin.insert(izin_data)
                    logger.info(f"Izin_Bilgi kaydı oluşturuldu: {data['KimlikNo']}")
                except Exception as e_izin:
                    logger.error(f"Izin_Bilgi oluşturma hatası: {e_izin}")

            QMessageBox.information(
                self, "Başarılı",
                "Personel kaydı başarıyla " + ("güncellendi" if self._is_edit else "eklendi") + "."
            )

            if self._on_saved:
                self._on_saved()

        except Exception as e:
            logger.error(f"Kaydetme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Kaydetme sırasında hata:\n{e}")

    def _on_cancel(self):
        """İptal — listeye geri dön."""
        if self._on_saved:
            self._on_saved()



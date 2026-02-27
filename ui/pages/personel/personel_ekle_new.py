"""
Personel Ekle / Duzenle Sayfasi - Refactored (Sprint 3.2)
========================================================

Sorumluluklar:
- UI layout
- Event handling
- Form validasyonu
- Kaydetme islemi (upload + DB)
"""

import os
from datetime import datetime

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QProgressBar, QFrame, QComboBox, QLineEdit,
    QDateEdit, QGroupBox, QMessageBox, QFileDialog
)
from PySide6.QtGui import QCursor, QPixmap

from core.logger import logger
from core.date_utils import parse_date
from core.auth.password_hasher import PasswordHasher
from database.repository_registry import RepositoryRegistry
from database.auth_repository import AuthRepository
from ui.styles import DarkTheme
from ui.styles.components import STYLES as S
from ui.styles.icons import IconRenderer
from ui.theme_manager import ThemeManager

from .services.personel_validators import (
    validate_tc_kimlik_no,
    validate_email,
    generate_username_from_name,
)
from .services.personel_upload_service import PersonelUploadManager


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
    """Personel ekle/duzenle sayfasi."""

    def __init__(self, db=None, edit_data=None, on_saved=None, action_guard=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(S["page"])
        self._db = db
        self._edit_data = edit_data
        self._on_saved = on_saved
        self._action_guard = action_guard
        self._is_edit = edit_data is not None

        self.ui = {}
        self._file_paths = {}
        self._drive_links = {}
        self._all_sabit = []
        self._upload_manager = None
        self._pending_data = None

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

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(S["scroll"])

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content_layout = QHBoxLayout(content)
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # ── SOL ──
        left = QWidget()
        left_l = QVBoxLayout(left)
        left_l.setSpacing(12)
        left_l.setContentsMargins(0, 0, 0, 0)

        # Foto
        photo_grp = QGroupBox("Fotograf")
        photo_grp.setStyleSheet(S["group"])
        photo_lay = QVBoxLayout(photo_grp)
        photo_lay.setAlignment(Qt.AlignCenter)

        self.lbl_resim = QLabel("Fotograf\nYuklenmedi")
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

        tc_container = QWidget()
        tc_container.setStyleSheet("background: transparent;")
        tc_lay = QVBoxLayout(tc_container)
        tc_lay.setContentsMargins(0, 0, 0, 0)
        tc_lay.setSpacing(4)
        tc_lbl = QLabel("TC Kimlik No *")
        tc_lbl.setStyleSheet(S["required_label"])
        tc_lay.addWidget(tc_lbl)
        tc_row = QHBoxLayout()
        tc_row.setSpacing(4)

        self.ui["tc"] = QLineEdit()
        self.ui["tc"].setMaxLength(11)
        self.ui["tc"].setStyleSheet(S["input"])
        self.ui["tc"].setPlaceholderText("11 haneli rakam")
        self.ui["tc"].textChanged.connect(self._validate_tc_on_change)
        tc_row.addWidget(self.ui["tc"])
        self._tc_status = QLabel("")
        self._tc_status.setFixedWidth(20)
        tc_row.addWidget(self._tc_status)
        tc_lay.addLayout(tc_row)

        row1 = QHBoxLayout()
        row1.addWidget(tc_container)
        self.ui["ad_soyad"] = self._make_input("Ad Soyad *", row1, required=True)
        id_lay.addLayout(row1)

        row2 = QHBoxLayout()
        self.ui["dogum_yeri"] = self._make_combo("Dogum Yeri", row2, editable=True)
        self.ui["dogum_tarihi"] = self._make_date("Dogum Tarihi", row2)
        id_lay.addLayout(row2)

        left_l.addWidget(id_grp)

        # Iletisim
        contact_grp = QGroupBox("Iletisim Bilgileri")
        contact_grp.setStyleSheet(S["group"])
        contact_lay = QVBoxLayout(contact_grp)

        row_c = QHBoxLayout()
        self.ui["cep_tel"] = self._make_input("Cep Telefonu", row_c, placeholder="05XX XXX XX XX")

        email_container = QWidget()
        email_container.setStyleSheet("background: transparent;")
        email_lay = QVBoxLayout(email_container)
        email_lay.setContentsMargins(0, 0, 0, 0)
        email_lay.setSpacing(4)
        email_lbl = QLabel("E-posta Adresi")
        email_lbl.setStyleSheet(S["label"])
        email_lay.addWidget(email_lbl)
        email_row = QHBoxLayout()
        email_row.setSpacing(4)
        self.ui["eposta"] = QLineEdit()
        self.ui["eposta"].setStyleSheet(S["input"])
        self.ui["eposta"].setPlaceholderText("ornek@email.com")
        self.ui["eposta"].textChanged.connect(self._validate_email_on_change)
        email_row.addWidget(self.ui["eposta"])
        self._email_status = QLabel("")
        self._email_status.setFixedWidth(20)
        email_row.addWidget(self._email_status)
        email_lay.addLayout(email_row)

        row_c.addWidget(email_container)
        contact_lay.addLayout(row_c)
        left_l.addWidget(contact_grp)
        left_l.addStretch()

        # ── SAG ──
        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setSpacing(12)
        right_l.setContentsMargins(0, 0, 0, 0)

        corp_grp = QGroupBox("Kadro ve Kurumsal Bilgiler")
        corp_grp.setStyleSheet(S["group"])
        corp_lay = QVBoxLayout(corp_grp)
        corp_lay.setSpacing(10)

        row_k1 = QHBoxLayout()
        self.ui["hizmet_sinifi"] = self._make_combo("Hizmet Sinifi *", row_k1, required=True)
        self.ui["kadro_unvani"] = self._make_combo("Kadro Unvani *", row_k1, required=True)
        corp_lay.addLayout(row_k1)

        row_k2 = QHBoxLayout()
        self.ui["gorev_yeri"] = self._make_combo("Gorev Yeri", row_k2)
        self.ui["sicil_no"] = self._make_input("Kurum Sicil No", row_k2)
        corp_lay.addLayout(row_k2)

        row_k3 = QHBoxLayout()
        self.ui["baslama_tarihi"] = self._make_date("Memuriyete Baslama Tarihi", row_k3)
        row_k3.addStretch()
        corp_lay.addLayout(row_k3)

        right_l.addWidget(corp_grp)

        edu_grp = QGroupBox("Egitim Bilgileri")
        edu_grp.setStyleSheet(S["group"])
        edu_main = QHBoxLayout(edu_grp)
        edu_main.setSpacing(16)

        for i in ["1", "2"]:
            col = QVBoxLayout()
            col.setSpacing(8)

            header = QLabel(
                "Lise / Onlisans / Lisans" if i == "1" else "Lisans / Yuksek Lisans / Lisans Tamamlama"
            )
            header.setStyleSheet(S.get("section_title", ""))
            col.addWidget(header)

            self.ui[f"okul{i}"] = self._make_combo_v("Okul Adi", col, editable=True)
            self.ui[f"fakulte{i}"] = self._make_combo_v("Bolum / Fakulte", col, editable=True)
            self.ui[f"mezun_tarihi{i}"] = self._make_input_v("Mezuniyet Tarihi", col)
            self.ui[f"diploma_no{i}"] = self._make_input_v("Diploma No", col)

            btn_dip = QPushButton(f"Diploma {i} Sec")
            btn_dip.setStyleSheet(S["file_btn"])
            btn_dip.setCursor(QCursor(Qt.PointingHandCursor))
            btn_dip.clicked.connect(lambda checked, idx=i: self._select_diploma(idx))
            IconRenderer.set_button_icon(btn_dip, "upload", color=DarkTheme.TEXT_PRIMARY, size=14)
            col.addWidget(btn_dip)

            lbl_file = QLabel("")
            lbl_file.setStyleSheet(f"color: {DarkTheme.STATUS_SUCCESS}; font-size: 11px; background: transparent;")
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

        # Footer
        footer = QHBoxLayout()
        footer.setSpacing(12)

        self.progress = QProgressBar()
        self.progress.setFixedWidth(150)
        self.progress.setFixedHeight(16)
        self.progress.setVisible(False)
        self.progress.setStyleSheet(
            f"QProgressBar {{ background-color: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08);"
            f" border-radius: 4px; color: {DarkTheme.TEXT_MUTED}; font-size: 11px; }}"
            f"QProgressBar::chunk {{ background-color: rgba(29, 117, 254, 0.6); border-radius: 3px; }}"
        )
        footer.addWidget(self.progress)
        footer.addStretch()

        btn_iptal = QPushButton("IPTAL")
        btn_iptal.setStyleSheet(S["cancel_btn"])
        btn_iptal.setCursor(QCursor(Qt.PointingHandCursor))
        btn_iptal.clicked.connect(self._on_cancel)
        IconRenderer.set_button_icon(btn_iptal, "x", color=DarkTheme.TEXT_PRIMARY, size=14)
        footer.addWidget(btn_iptal)

        title = "GUNCELLE" if self._is_edit else "KAYDET"
        self.btn_kaydet = QPushButton(f"PERSONELI {title}")
        self.btn_kaydet.setStyleSheet(S["save_btn"])
        self.btn_kaydet.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kaydet.clicked.connect(self._on_save)
        IconRenderer.set_button_icon(self.btn_kaydet, "save", color=DarkTheme.TEXT_PRIMARY, size=14)
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self.btn_kaydet, "personel.write")
        footer.addWidget(self.btn_kaydet)

        main.addLayout(footer)

    # ═══════════════════════════════════════════
    #  YARDIMCI WIDGETLAR
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
        if not self._db:
            return

        try:
            registry = RepositoryRegistry(self._db)
            sabitler = registry.get("Sabitler")
            all_sabit = sabitler.get_all()
            self._all_sabit = all_sabit

            def get_sabit(kod):
                return sorted([
                    str(r.get("MenuEleman", "")).strip()
                    for r in all_sabit
                    if r.get("Kod") == kod and r.get("MenuEleman", "").strip()
                ])

            self.ui["hizmet_sinifi"].clear()
            self.ui["hizmet_sinifi"].addItem("")
            self.ui["hizmet_sinifi"].addItems(get_sabit("Hizmet_Sinifi"))

            self.ui["kadro_unvani"].clear()
            self.ui["kadro_unvani"].addItem("")
            self.ui["kadro_unvani"].addItems(get_sabit("Kadro_Unvani"))

            self.ui["gorev_yeri"].clear()
            self.ui["gorev_yeri"].addItem("")
            self.ui["gorev_yeri"].addItems(get_sabit("Gorev_Yeri"))

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

            fakulteler = sorted(set(
                s for r in all_personel
                for col in ("MezunOlunanFakulte", "MezunOlunanFakulte2")
                if (s := str(r.get(col, "")).strip())
            ))
            for k in ["fakulte1", "fakulte2"]:
                self.ui[k].clear()
                self.ui[k].addItem("")
                self.ui[k].addItems(fakulteler)

        except Exception as e:
            logger.error(f"Combo doldurma hatasi: {e}")

    # ═══════════════════════════════════════════
    #  FORM VERI
    # ═══════════════════════════════════════════

    def _get_widget_value(self, key):
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
        for db_col, ui_key in FIELD_MAP.items():
            value = row_data.get(db_col, "")
            self._set_widget_value(ui_key, value)

    # ═══════════════════════════════════════════
    #  DOSYA SECIMI
    # ═══════════════════════════════════════════

    def _select_photo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Fotograf Sec", "",
            "Resim Dosyalari (*.jpg *.jpeg *.png *.bmp);;Tum Dosyalar (*)"
        )
        if path:
            self._file_paths["Resim"] = path
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                self.lbl_resim.setPixmap(
                    pixmap.scaled(160, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
            self.lbl_resim.setToolTip(os.path.basename(path))

    def _select_diploma(self, idx):
        path, _ = QFileDialog.getOpenFileName(
            self, f"Diploma {idx} Sec", "",
            "Dosyalar (*.pdf *.jpg *.jpeg *.png);;Tum Dosyalar (*)"
        )
        if path:
            key = f"Diploma{idx}"
            self._file_paths[key] = path
            lbl = self.ui.get(f"diploma_file_lbl{idx}")
            if lbl:
                lbl.setText(os.path.basename(path))

    # ═══════════════════════════════════════════
    #  VALIDASYON
    # ═══════════════════════════════════════════

    def _validate_tc_on_change(self):
        tc_text = self.ui["tc"].text().strip()
        if not tc_text:
            self._tc_status.setText("!")
            self._tc_status.setStyleSheet(f"color: {DarkTheme.TEXT_MUTED}; font-size: 16px;")
        elif len(tc_text) == 11 and tc_text.isdigit():
            self._tc_status.setText("✓")
            self._tc_status.setStyleSheet(f"color: {DarkTheme.STATUS_SUCCESS}; font-size: 16px;")
        else:
            self._tc_status.setText("x")
            self._tc_status.setStyleSheet(f"color: {DarkTheme.STATUS_ERROR}; font-size: 16px;")

    def _validate_email_on_change(self):
        email_text = self.ui["eposta"].text().strip()
        if not email_text:
            self._email_status.setText("!")
            self._email_status.setStyleSheet(f"color: {DarkTheme.TEXT_MUTED}; font-size: 16px;")
        elif validate_email(email_text):
            self._email_status.setText("✓")
            self._email_status.setStyleSheet(f"color: {DarkTheme.STATUS_SUCCESS}; font-size: 16px;")
        else:
            self._email_status.setText("x")
            self._email_status.setStyleSheet(f"color: {DarkTheme.STATUS_ERROR}; font-size: 16px;")

    def _validate(self):
        errors = []
        tc = self._get_widget_value("tc")
        if not tc:
            errors.append("TC Kimlik No bos olamaz")
        elif len(tc) != 11 or not tc.isdigit():
            errors.append("TC Kimlik No 11 haneli rakam olmali")
        elif not validate_tc_kimlik_no(tc):
            errors.append("TC Kimlik No gecersiz")

        if not self._get_widget_value("ad_soyad"):
            errors.append("Ad Soyad bos olamaz")

        email = self._get_widget_value("eposta")
        if email and not validate_email(email):
            errors.append("E-posta adresi gecersiz")

        if not self._get_widget_value("hizmet_sinifi"):
            errors.append("Hizmet Sinifi secilmeli")
        if not self._get_widget_value("kadro_unvani"):
            errors.append("Kadro Unvani secilmeli")

        return errors

    # ═══════════════════════════════════════════
    #  KAYDET
    # ═══════════════════════════════════════════

    def _on_save(self):
        if self._action_guard and not self._action_guard.check_and_warn(
            self, "personel.write", "Personel Kaydetme"
        ):
            return

        errors = self._validate()
        if errors:
            QMessageBox.warning(self, "Eksik Bilgi", "\n".join(f"• {e}" for e in errors))
            return

        data = self._collect_data()
        tc_no = data["KimlikNo"]

        for field in [
            "AdSoyad", "DogumYeri",
            "MezunOlunanOkul", "MezunOlunanFakulte",
            "MezunOlunanOkul2", "MezunOlunanFakulte2",
        ]:
            if data.get(field):
                data[field] = data[field].title()

        if not self._is_edit:
            try:
                registry = RepositoryRegistry(self._db)
                repo = registry.get("Personel")
                existing = repo.get_by_id(tc_no)
                if existing:
                    QMessageBox.warning(self, "Kayit Mevcut", f"TC {tc_no} ile kayitli personel var.")
                    return
            except Exception as e:
                logger.error(f"TC kontrol hatasi: {e}")

        # Upload -> DB
        self._pending_data = data
        self._start_uploads(tc_no)

    def _start_uploads(self, tc_no: str):
        if not self._file_paths:
            self._save_to_db({})
            return

        self._upload_manager = PersonelUploadManager(self._db, self._all_sabit)
        self._upload_manager.progress.connect(self._on_upload_progress)
        self._upload_manager.finished.connect(self._on_upload_finished)

        self.progress.setVisible(True)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.btn_kaydet.setEnabled(False)

        self._upload_manager.start_uploads(self._file_paths, tc_no)

    def _on_upload_progress(self, percent: int):
        self.progress.setValue(percent)

    def _on_upload_finished(self, drive_links: dict, errors: list):
        self.progress.setVisible(False)
        self.btn_kaydet.setEnabled(True)
        self._drive_links = drive_links or {}

        if errors:
            QMessageBox.warning(self, "Drive Yukleme Uyarisi", "\n".join(errors))

        self._save_to_db(self._drive_links)

    def _save_to_db(self, drive_links: dict):
        data = self._pending_data or {}
        link_map = {
            "Resim": "Resim",
            "Diploma1": "Diploma1",
            "Diploma2": "Diploma2",
        }
        for drive_key, db_col in link_map.items():
            link = drive_links.get(drive_key, "")
            if link:
                data[db_col] = link

        try:
            registry = RepositoryRegistry(self._db)
            repo = registry.get("Personel")

            if self._is_edit:
                repo.update(data["KimlikNo"], data)
                logger.info(f"Personel guncellendi: {data['KimlikNo']}")
            else:
                repo.insert(data)
                logger.info(f"Yeni personel eklendi: {data['KimlikNo']}")

                try:
                    repo_izin = registry.get("Izin_Bilgi")
                    izin_data = {"TCKimlik": data["KimlikNo"], "AdSoyad": data["AdSoyad"]}
                    repo_izin.insert(izin_data)
                except Exception as e_izin:
                    logger.error(f"Izin_Bilgi olusturma hatasi: {e_izin}")

                try:
                    ad_soyad = data.get("AdSoyad", "")
                    username = generate_username_from_name(ad_soyad)
                    if username:
                        password = f"{username}123"
                        hasher = PasswordHasher()
                        password_hash = hasher.hash(password)
                        auth_repo = AuthRepository(self._db)
                        auth_repo.create_user(
                            username=username,
                            password_hash=password_hash,
                            is_active=True,
                            must_change_password=True
                        )
                except Exception as e_user:
                    logger.error(f"Kullanici olusturma hatasi: {e_user}")

            QMessageBox.information(
                self, "Basarili",
                "Personel kaydi basariyla " + ("guncellendi" if self._is_edit else "eklendi") + "."
            )

            if self._on_saved:
                self._on_saved()

        except Exception as e:
            logger.error(f"Kaydetme hatasi: {e}")
            QMessageBox.critical(self, "Hata", f"Kaydetme sirasinda hata:\n{e}")

    def _on_cancel(self):
        if self._on_saved:
            self._on_saved()

# -*- coding: utf-8 -*-
import os
import re
from datetime import datetime
from PySide6.QtCore import Qt, QDate, QTimer, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QProgressBar, QFrame, QComboBox, QLineEdit,
    QDateEdit, QGroupBox, QMessageBox, QFileDialog
)
from PySide6.QtGui import QCursor, QPixmap

from core.logger import logger
from core.date_utils import parse_date
from core.paths import DB_PATH
from core.auth.password_hasher import PasswordHasher
from core.di import get_registry
from core.services.dokuman_service import DokumanService
from core.services.personel_service import PersonelService
from core.validators import validate_tc_kimlik_no, validate_email
from core.text_utils import turkish_title_case
from database.auth_repository import AuthRepository
from ui.styles import DarkTheme
from ui.styles.components import STYLES as S
from ui.styles.icons import IconRenderer
from ui.theme_manager import ThemeManager
from ui.components.formatted_widgets import apply_title_case_formatting


class DokumanUploadWorker(QThread):
    """Tek bir dosya için DokumanService upload worker'ı."""
    upload_finished = Signal(str, dict)
    upload_error = Signal(str, str)

    def __init__(self, db_path: str, job: dict, parent=None):
        super().__init__(parent)
        self._db_path = db_path
        self._job = job

    def run(self):
        try:
            # Her thread kendi DB connection'ını oluşturur (SQLite thread güvenliği için)
            from database.sqlite_manager import SQLiteManager
            db = SQLiteManager(self._db_path, check_same_thread=False)
            svc = DokumanService(db)
            sonuc = svc.upload_and_save(
                file_path=self._job["file_path"],
                entity_type="personel",
                entity_id=str(self._job["tc_no"]),
                belge_turu=self._job["belge_turu"],
                folder_name=self._job["folder_name"],
                doc_type=self._job["doc_type"],
                custom_name=self._job["custom_name"],
            )
            if sonuc.get("ok"):
                self.upload_finished.emit(self._job["db_field"], sonuc)
            else:
                self.upload_error.emit(
                    self._job["db_field"],
                    sonuc.get("error", "Bilinmeyen yükleme hatası")
                )
        except Exception as e:
            self.upload_error.emit(self._job.get("db_field", ""), str(e))


def generate_username_from_name(ad_soyad: str) -> str:
    """
    Adından kullanıcı adı oluştur.
    Örnek: "Cem Kara" → "CKara", "Ahmet Cem Kara" → "ACKara"
    
    Kural:
    - Soyadı (son kelime) tamamen yaz
    - Diğer kelimelerin ilk harfini yaz
    - Büyük harf yap
    """
    if not ad_soyad or not ad_soyad.strip():
        return ""
    
    parts = ad_soyad.strip().split()
    if len(parts) == 0:
        return ""
    
    # Son kelime soyadı (tamamen)
    surname = parts[-1]
    
    # Diğer kelimelerin ilk harfleri
    initials = "".join([p[0] for p in parts[:-1]])
    
    # Birleştir ve büyük harf yap
    username = (initials + surname).upper()
    return username

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
    # Sinyal: form kapanması istendiğinde emitir (kaydet veya iptal)
    form_closed = Signal()

    def __init__(self, db=None, edit_data=None, on_saved=None, action_guard=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(S["page"])
        self._db = db
        self._edit_data = edit_data
        self._on_saved = on_saved
        self._action_guard = action_guard
        self._is_edit = edit_data is not None
        self.ui = {}
        self._file_paths = {}          # {"Resim": path, "Diploma1": path, ...}
        self._drive_links = {}         # {"Resim": link, "Diploma1": link, ...}
        self._drive_folders = {}       # {"Personel_Resim": folder_id, ...}
        self._upload_workers = []
        self._all_sabit = []
        self._pending_uploads = 0
        self._completed_uploads = 0
        self._upload_errors = []
        self._upload_meta = {}         # alan_adi -> metadata
        
        # Service layer
        if db:
            self._registry = get_registry(db)
            self._svc = PersonelService(self._registry)
        else:
            self._registry = None
            self._svc = None

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
        scroll.setFrameShape(QFrame.Shape.NoFrame)
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
        photo_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_resim = QLabel("Fotoğraf\nYüklenmedi")
        self.lbl_resim.setFixedSize(160, 200)
        self.lbl_resim.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_resim.setStyleSheet(S["photo_area"])
        photo_lay.addWidget(self.lbl_resim, alignment=Qt.AlignmentFlag.AlignCenter)

        btn_resim = QPushButton("Fotograf Sec")
        btn_resim.setStyleSheet(S["photo_btn"])
        btn_resim.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_resim.clicked.connect(self._select_photo)
        IconRenderer.set_button_icon(btn_resim, "upload", color=DarkTheme.TEXT_PRIMARY, size=14)
        photo_lay.addWidget(btn_resim, alignment=Qt.AlignmentFlag.AlignCenter)
        left_l.addWidget(photo_grp)

        # Kimlik Bilgileri
        id_grp = QGroupBox("Kimlik Bilgileri")
        id_grp.setStyleSheet(S["group"])
        id_lay = QVBoxLayout(id_grp)
        id_lay.setSpacing(10)

        # TC Kimlik No ile validation status
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
        self.ui["dogum_yeri"] = self._make_combo("Doğum Yeri", row2, editable=True)
        self.ui["dogum_tarihi"] = self._make_date("Doğum Tarihi", row2)
        id_lay.addLayout(row2)

        left_l.addWidget(id_grp)

        # İletişim
        contact_grp = QGroupBox("Iletisim Bilgileri")
        contact_grp.setStyleSheet(S["group"])
        contact_lay = QVBoxLayout(contact_grp)

        row_c = QHBoxLayout()
        self.ui["cep_tel"] = self._make_input("Cep Telefonu", row_c, placeholder="05XX XXX XX XX", auto_format=False)
        
        # Email ile validation status
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
        self.ui["gorev_yeri"] = self._make_combo("Görev Yeri", row_k2, stretch=1)
        self.ui["sicil_no"] = self._make_input("Kurum Sicil No", row_k2, stretch=1, auto_format=False)
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
            self.ui[f"mezun_tarihi{i}"] = self._make_input_v(f"Mezuniyet Tarihi", col, auto_format=False)
            self.ui[f"diploma_no{i}"] = self._make_input_v(f"Diploma No", col, auto_format=False)

            btn_dip = QPushButton(f"Diploma {i} Sec")
            btn_dip.setStyleSheet(S["file_btn"])
            btn_dip.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
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
                sep.setFrameShape(QFrame.Shape.VLine)
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
        btn_iptal.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_iptal.clicked.connect(self._on_cancel)
        IconRenderer.set_button_icon(btn_iptal, "x", color=DarkTheme.TEXT_PRIMARY, size=14)
        footer.addWidget(btn_iptal)

        title = "GÜNCELLE" if self._is_edit else "KAYDET"
        self.btn_kaydet = QPushButton(f"PERSONELI {title}")
        self.btn_kaydet.setStyleSheet(S["save_btn"])
        self.btn_kaydet.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_kaydet.clicked.connect(self._on_save)
        IconRenderer.set_button_icon(self.btn_kaydet, "save", color=DarkTheme.TEXT_PRIMARY, size=14)
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self.btn_kaydet, "personel.write")
        footer.addWidget(self.btn_kaydet)

        main.addLayout(footer)

    # ═══════════════════════════════════════════
    #  YARDIMCI WIDGET FABRİKALARI
    # ═══════════════════════════════════════════

    def _make_input(self, label, parent_layout, required=False, placeholder="", stretch=0, auto_format=True):
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
        parent_layout.addWidget(container, stretch)
        
        # Otomatik formatting uygula (özel alanlar hariç)
        if auto_format:
            apply_title_case_formatting(inp)
        
        return inp

    def _make_combo(self, label, parent_layout, required=False, editable=False, stretch=0, auto_format=True):
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
        parent_layout.addWidget(container, stretch)
        
        # Editable combo'lara otomatik formatting ekle
        if editable and auto_format:
            line_edit = cmb.lineEdit()
            if line_edit:
                apply_title_case_formatting(line_edit)
        
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
    def _make_input_v(self, label, parent_layout, placeholder="", auto_format=True):
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label"])
        parent_layout.addWidget(lbl)
        inp = QLineEdit()
        inp.setStyleSheet(S["input"])
        if placeholder:
            inp.setPlaceholderText(placeholder)
        parent_layout.addWidget(inp)
        
        # Otomatik formatting uygula (özel alanlar hariç)
        if auto_format:
            apply_title_case_formatting(inp)
        
        return inp

    def _make_combo_v(self, label, parent_layout, editable=False, auto_format=True):
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label"])
        parent_layout.addWidget(lbl)
        cmb = QComboBox()
        cmb.setStyleSheet(S["combo"])
        cmb.setEditable(editable)
        parent_layout.addWidget(cmb)
        
        # Editable combo'lara otomatik formatting ekle
        if editable and auto_format:
            line_edit = cmb.lineEdit()
            if line_edit:
                apply_title_case_formatting(line_edit)
        
        return cmb

    # ═══════════════════════════════════════════
    #  COMBO DOLDURMA
    # ═══════════════════════════════════════════

    def _populate_combos(self):
        """Combobox'ları Sabitler + Personel tablosundan doldurur."""
        if not self._registry:
            return

        try:
            registry = self._registry

            # ── Sabitler'den ──
            sabitler = registry.get("Sabitler")
            all_sabit = sabitler.get_all()
            self._all_sabit = all_sabit

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
                    pixmap.scaled(160, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
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
        """Seçili dosyaları DokumanService ile yükler, bitince callback çağırır."""
        # Yüklenecek dosya yoksa direkt callback
        if not self._file_paths:
            callback()
            return

        upload_map = {
            "Resim": {
                "folder_name": "Personel_Resim",
                "doc_type": "Personel_Resim",
                "db_field": "Resim",
                "belge_turu": "Resim",
            },
            "Diploma1": {
                "folder_name": "Personel_Diploma",
                "doc_type": "Personel_Diploma",
                "db_field": "Diploma1",
                "belge_turu": "Diploma1",
            },
            "Diploma2": {
                "folder_name": "Personel_Diploma",
                "doc_type": "Personel_Diploma",
                "db_field": "Diploma2",
                "belge_turu": "Diploma2",
            },
        }

        self._pending_uploads = 0
        self._completed_uploads = 0
        self._upload_errors = []

        for file_key, file_path in self._file_paths.items():
            if file_key not in upload_map:
                continue
            map_info = upload_map[file_key]
            ext = os.path.splitext(file_path)[1]

            # Diploma dosya adı formatı: TCKimlik_Diploma_Tarih
            # Örn: 12345678901_Diploma_20260301.pdf
            if file_key in ("Diploma1", "Diploma2"):
                tarih = datetime.now().strftime("%Y%m%d")
                custom_name = f"{tc_no}_Diploma_{tarih}{ext}"
                if file_key == "Diploma2":
                    custom_name = f"{tc_no}_Diploma_{tarih}_2{ext}"
            else:
                custom_name = f"{tc_no}_{map_info['db_field']}{ext}"

            self._upload_meta[map_info["db_field"]] = {
                "tc_no": tc_no,
                "file_path": file_path,
                "custom_name": custom_name,
                "folder_name": map_info["folder_name"],
                "belge_turu": map_info["belge_turu"],
                "doc_type": map_info["doc_type"],
            }

            job = {
                "tc_no": tc_no,
                "file_path": file_path,
                "custom_name": custom_name,
                "folder_name": map_info["folder_name"],
                "doc_type": map_info["doc_type"],
                "db_field": map_info["db_field"],
                "belge_turu": map_info["belge_turu"],
            }
            self._pending_uploads += 1
            worker = DokumanUploadWorker(DB_PATH, job)
            worker.upload_finished.connect(self._on_upload_finished)
            worker.upload_error.connect(self._on_upload_error)
            self._upload_workers.append(worker)
            worker.start()

        if self._pending_uploads == 0:
            callback()
        else:
            self._upload_callback = callback
            self.progress.setVisible(True)
            self.progress.setRange(0, 100)  # percentage
            self.progress.setValue(0)
            self.btn_kaydet.setEnabled(False)

    def _on_upload_finished(self, alan_adi, sonuc):
        """Tek dosya yükleme tamamlandı."""
        kayit_linki = sonuc.get("drive_link") or sonuc.get("local_path") or ""
        self._drive_links[alan_adi] = kayit_linki
        logger.info(f"Dosya yükleme OK: {alan_adi} → {kayit_linki}")
        self._completed_uploads += 1
        # Progress bar'ı güncelle
        percent = int((self._completed_uploads / self._pending_uploads) * 100)
        self.progress.setValue(percent)
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
    #  REAL-TIME FORM VALIDASYON
    # ═══════════════════════════════════════════

    def _validate_tc_on_change(self):
        """TC Kimlik No real-time validasyonu."""
        tc_text = self.ui["tc"].text().strip()
        if not tc_text:
            self._tc_status.setText("⚠")
            self._tc_status.setStyleSheet(f"color: {DarkTheme.TEXT_MUTED}; font-size: 16px;")
        elif len(tc_text) == 11 and tc_text.isdigit():
            # Format doğru, status göster
            self._tc_status.setText("✓")
            self._tc_status.setStyleSheet(f"color: {DarkTheme.STATUS_SUCCESS}; font-size: 16px;")
        else:
            # Format yanlış
            self._tc_status.setText("✗")
            self._tc_status.setStyleSheet(f"color: {DarkTheme.STATUS_ERROR}; font-size: 16px;")

    def _validate_email_on_change(self):
        """E-posta real-time validasyonu."""
        email_text = self.ui["eposta"].text().strip()
        if not email_text:
            self._email_status.setText("⚠")
            self._email_status.setStyleSheet(f"color: {DarkTheme.TEXT_MUTED}; font-size: 16px;")
        elif validate_email(email_text):
            self._email_status.setText("✓")
            self._email_status.setStyleSheet(f"color: {DarkTheme.STATUS_SUCCESS}; font-size: 16px;")
        else:
            self._email_status.setText("✗")
            self._email_status.setStyleSheet(f"color: {DarkTheme.STATUS_ERROR}; font-size: 16px;")

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
        elif not validate_tc_kimlik_no(tc):
            errors.append("TC Kimlik No geçersiz (kontrol hanesi yanlış)")

        if not self._get_widget_value("ad_soyad"):
            errors.append("Ad Soyad boş olamaz")
        
        email = self._get_widget_value("eposta")
        if email and not validate_email(email):
            errors.append("E-posta adresi geçersiz")

        if not self._get_widget_value("hizmet_sinifi"):
            errors.append("Hizmet Sınıfı seçilmeli")
        if not self._get_widget_value("kadro_unvani"):
            errors.append("Kadro Ünvanı seçilmeli")

        return errors

    def _on_save(self):
        """Kaydet: validasyon → Drive yükleme → DB kayıt."""
        if self._action_guard and not self._action_guard.check_and_warn(
            self, "personel.write", "Personel Kaydetme"
        ):
            return
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
                if not self._registry:
                    return
                repo = self._registry.get("Personel")
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
            if not self._registry:
                QMessageBox.critical(self, "Hata", "Veritabanı bağlantısı bulunamadı.")
                return
            registry = self._registry
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
                        "TCKimlik": data["KimlikNo"],
                        "AdSoyad": data["AdSoyad"]
                    }
                    repo_izin.insert(izin_data)
                    logger.info(f"Izin_Bilgi kaydı oluşturuldu: {data['KimlikNo']}")
                except Exception as e_izin:
                    logger.error(f"Izin_Bilgi oluşturma hatası: {e_izin}")
                
                # Yeni personel için kullanıcı hesabı oluştur
                try:
                    ad_soyad = data.get("AdSoyad", "")
                    username = generate_username_from_name(ad_soyad)

                    if username:
                        # Şifre: kullanıcı adı + "123" (örn: "CKara123")
                        password = f"{username}123"

                        # Şifreyi hash'le
                        hasher = PasswordHasher()
                        password_hash = hasher.hash(password)

                        # Kullanıcı oluştur (must_change_password=True → ilk girişte değiştirmesi istenir)
                        auth_repo = AuthRepository(self._db)
                        user_id = auth_repo.create_user(
                            username=username,
                            password_hash=password_hash,
                            is_active=True,
                            must_change_password=True
                        )

                        # Varsayılan rol: operator
                        try:
                            roles = auth_repo.get_roles() or []
                            operator_role = next(
                                (r for r in roles if str(r.get("name", "")).strip().lower() == "operator"),
                                None,
                            )
                            if operator_role and operator_role.get("id"):
                                auth_repo.assign_role(user_id=user_id, role_id=int(operator_role["id"]))
                                logger.info(f"Kullanıcıya operator rolü atandı: {username} (ID: {user_id})")
                            else:
                                logger.warning("'operator' rolü bulunamadı, kullanıcı rol ataması yapılmadı")
                        except Exception as e_role:
                            logger.error(f"Operator rol atama hatası: {e_role}")

                        logger.info(f"Kullanıcı hesabı oluşturuldu: {username} (ID: {user_id})")
                    else:
                        logger.warning(f"Personel adından kullanıcı adı oluşturulamadı: {ad_soyad}")
                except Exception as e_user:
                    logger.error(f"Kullanıcı hesabı oluşturma hatası: {e_user}")

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
        """İptal — form kapanış sinyali emitir."""
        self.form_closed.emit()

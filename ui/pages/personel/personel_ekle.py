# -*- coding: utf-8 -*-
import os
import re
from datetime import datetime
from PySide6.QtCore import Qt, QDate, QTimer, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QScrollArea, QProgressBar, QFrame, QComboBox, QLineEdit,
    QDateEdit, QGroupBox, QMessageBox, QFileDialog
)
from PySide6.QtGui import QCursor, QPixmap

from core.logger import logger
from core.date_utils import parse_date
from core.paths import DB_PATH
from core.auth.password_hasher import PasswordHasher
from core.di import get_personel_service, get_izin_service, get_dokuman_service
from core.validators import validate_tc_kimlik_no, validate_email, validate_phone_number
from core.text_utils import turkish_title_case
from core.services.dokuman_service import DokumanService
from database.auth_repository import AuthRepository
from ui.styles import DarkTheme
from ui.styles.components import STYLES as S
from ui.styles.icons import IconRenderer
from ui.theme_manager import ThemeManager
from ui.components.formatted_widgets import apply_title_case_formatting, apply_combo_title_case_formatting
from ui.pages.personel.components.personel_dokuman_panel import PersonelDokumanPanel
from ui.styles.colors import get_current_theme
from ui.dialogs.mesaj_kutusu import MesajKutusu

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
        self._dokuman_panel = None     # PersonelDokumanPanel instance
        self.lbl_baslik: QLabel | None = None
        
        # Service layer
        self._personel_svc = get_personel_service(db)
        self._izin_svc = get_izin_service(db) if db else None
        self._dokuman_svc = get_dokuman_service(db) if db else None

        self._setup_ui()
        self._populate_combos()

        if self._is_edit:
            self._fill_form(edit_data)
            # Düzenleme modunda form doldurulduktan sonra panel ayarla
            self._update_dokuman_panel()
        else:
            # Yeni ekleme modunda da ilk panel oluştur
            self._update_dokuman_panel()

    # ═══════════════════════════════════════════
    #  UI
    # ═══════════════════════════════════════════

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(16, 12, 16, 12)
        main.setSpacing(12)

        title_text = "Personel Düzenle" if self._is_edit else "Personel Ekle"
        self.lbl_baslik = QLabel(title_text)
        self.lbl_baslik.setProperty("style-role", "title")
        self.lbl_baslik.style().unpolish(self.lbl_baslik)
        self.lbl_baslik.style().polish(self.lbl_baslik)
        main.addWidget(self.lbl_baslik)

        # Scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(S["scroll"])

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content_layout = QHBoxLayout(content)
        content_layout.setSpacing(16)
        content_layout.setContentsMargins(0, 8, 0, 8)

        # ══════════════════════════════════════════════════════
        # SOL KART — Fotoğraf ve Kimlik
        # ══════════════════════════════════════════════════════
        left_grp = QGroupBox("Fotograf ve Kimlik Bilgileri")
        left_grp.setStyleSheet(S["group"])
        left_grp.setFixedWidth(270)
        left_l = QVBoxLayout(left_grp)
        left_l.setSpacing(0)
        left_l.setContentsMargins(12, 12, 12, 16)

        # Fotoğraf
        self.lbl_resim = QLabel()
        self.lbl_resim.setFixedSize(160, 180)
        self.lbl_resim.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_resim.setProperty("bg-role", "panel")
        self.lbl_resim.setStyleSheet(
            "border: 2px solid rgba(61,142,245,0.25); border-radius: 8px;"
        )
        self.lbl_resim.setText("Fotoğraf")
        self.lbl_resim.setProperty("color-role", "muted")
        left_l.addWidget(self.lbl_resim, alignment=Qt.AlignmentFlag.AlignCenter)
        left_l.addSpacing(8)

        btn_resim = QPushButton("Fotoğraf Seç")
        btn_resim.setProperty("style-role", "upload")
        btn_resim.setFixedHeight(28)
        btn_resim.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_resim.clicked.connect(self._select_photo)
        IconRenderer.set_button_icon(btn_resim, "upload", color=DarkTheme.TEXT_PRIMARY, size=13)
        left_l.addWidget(btn_resim, alignment=Qt.AlignmentFlag.AlignCenter)
        left_l.addSpacing(10)

        # Ayırıcı
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setProperty("bg-role", "separator")
        sep.style().unpolish(sep); sep.style().polish(sep)
        left_l.addWidget(sep)
        left_l.addSpacing(8)

        # ── Kimlik grid: etiket | input yan yana ──
        kimlik_grid = QGridLayout()
        kimlik_grid.setHorizontalSpacing(8)
        kimlik_grid.setVerticalSpacing(6)
        kimlik_grid.setColumnStretch(1, 1)

        def _field_row(grid, row, label_txt, widget, required=False):
            """Etiket sol | Widget sağ şeklinde hizalar."""
            lbl = QLabel(label_txt)
            if required:
                lbl.setStyleSheet(S.get("required_label", "font-size:10px; color:#e85555;"))
            else:
                lbl.setProperty("color-role", "muted")
                lbl.setStyleSheet("font-size: 10px;")
                lbl.style().unpolish(lbl); lbl.style().polish(lbl)
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(lbl, row, 0)
            grid.addWidget(widget, row, 1)

        # TC alanı (doğrulama göstergesiyle birlikte)
        tc_container = QWidget()
        tc_container.setStyleSheet("background: transparent;")
        tc_h = QHBoxLayout(tc_container)
        tc_h.setContentsMargins(0, 0, 0, 0)
        tc_h.setSpacing(4)
        self.ui["tc"] = QLineEdit()
        self.ui["tc"].setMaxLength(11)
        self.ui["tc"].setStyleSheet(S["input"])
        self.ui["tc"].setPlaceholderText("11 haneli")
        self.ui["tc"].textChanged.connect(self._validate_tc_on_change)
        self.ui["tc"].textChanged.connect(self._update_dokuman_panel)
        tc_h.addWidget(self.ui["tc"], 1)
        self._tc_status = QLabel("")
        self._tc_status.setFixedWidth(18)
        tc_h.addWidget(self._tc_status)
        _field_row(kimlik_grid, 0, "TC Kimlik No ✱", tc_container, required=True)

        self.ui["ad_soyad"] = QLineEdit()
        self.ui["ad_soyad"].setStyleSheet(S["input"])
        self.ui["ad_soyad"].setPlaceholderText("Ad Soyad")
        apply_title_case_formatting(self.ui["ad_soyad"])
        _field_row(kimlik_grid, 1, "Ad Soyad ✱", self.ui["ad_soyad"], required=True)

        self.ui["dogum_yeri"] = QComboBox()
        self.ui["dogum_yeri"].setEditable(True)
        self.ui["dogum_yeri"].setStyleSheet(S["input_combo"])
        apply_combo_title_case_formatting(self.ui["dogum_yeri"])
        _field_row(kimlik_grid, 2, "Doğum Yeri", self.ui["dogum_yeri"])

        self.ui["dogum_tarihi"] = QDateEdit()
        self.ui["dogum_tarihi"].setCalendarPopup(True)
        self.ui["dogum_tarihi"].setDate(QDate.currentDate().addYears(-30))
        self.ui["dogum_tarihi"].setStyleSheet(S["date"])
        _field_row(kimlik_grid, 3, "Doğum Tarihi", self.ui["dogum_tarihi"])

        left_l.addLayout(kimlik_grid)
        left_l.addStretch()

        # ══════════════════════════════════════════════════════
        # SAĞ SÜTUN
        # ══════════════════════════════════════════════════════
        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setSpacing(12)
        right_l.setContentsMargins(0, 0, 0, 0)

        # ── İletişim Bilgileri ──
        contact_grp = QGroupBox("İletişim Bilgileri")
        contact_grp.setStyleSheet(S["group"])
        contact_grid = QGridLayout(contact_grp)
        contact_grid.setSpacing(12)
        contact_grid.setContentsMargins(12, 8, 12, 12)
        contact_grid.setColumnStretch(0, 1)
        contact_grid.setColumnStretch(1, 1)

        def _contact_col(grid, col, label_txt, widget, status_lbl=None):
            lbl = QLabel(label_txt)
            lbl.setProperty("color-role", "muted")
            lbl.setStyleSheet("font-size: 11px;")
            lbl.style().unpolish(lbl); lbl.style().polish(lbl)
            grid.addWidget(lbl, 0, col)
            if status_lbl:
                row_w = QWidget()
                row_w.setStyleSheet("background: transparent;")
                rh = QHBoxLayout(row_w)
                rh.setContentsMargins(0, 0, 0, 0)
                rh.setSpacing(4)
                rh.addWidget(widget, 1)
                rh.addWidget(status_lbl)
                grid.addWidget(row_w, 1, col)
            else:
                grid.addWidget(widget, 1, col)

        self.ui["cep_tel"] = QLineEdit()
        self.ui["cep_tel"].setStyleSheet(S["input"])
        self.ui["cep_tel"].setPlaceholderText("05XX XXX XX XX")
        self.ui["cep_tel"].textChanged.connect(self._validate_phone_on_change)
        self._phone_status = QLabel("")
        self._phone_status.setFixedWidth(18)
        _contact_col(contact_grid, 0, "Cep Telefonu", self.ui["cep_tel"], self._phone_status)

        self.ui["eposta"] = QLineEdit()
        self.ui["eposta"].setStyleSheet(S["input"])
        self.ui["eposta"].setPlaceholderText("ornek@email.com")
        self.ui["eposta"].textChanged.connect(self._validate_email_on_change)
        self._email_status = QLabel("")
        self._email_status.setFixedWidth(18)
        _contact_col(contact_grid, 1, "E-posta", self.ui["eposta"], self._email_status)

        right_l.addWidget(contact_grp)

        # ── Kurumsal Bilgiler ──
        corp_grp = QGroupBox("Kurumsal Bilgiler")
        corp_grp.setStyleSheet(S["group"])
        corp_grid = QGridLayout(corp_grp)
        corp_grid.setSpacing(12)
        corp_grid.setContentsMargins(12, 8, 12, 12)
        corp_grid.setColumnStretch(0, 1)
        corp_grid.setColumnStretch(1, 1)
        corp_grid.setColumnStretch(2, 1)

        def _corp_field(grid, row_lbl, row_inp, col, label_txt, widget, required=False):
            lbl = QLabel(label_txt)
            if required:
                lbl.setStyleSheet(S.get("required_label", "font-size:11px; color:#e85555;"))
            else:
                lbl.setProperty("color-role", "muted")
                lbl.setStyleSheet("font-size: 11px;")
                lbl.style().unpolish(lbl); lbl.style().polish(lbl)
            grid.addWidget(lbl, row_lbl, col)
            grid.addWidget(widget, row_inp, col)

        self.ui["hizmet_sinifi"] = QComboBox()
        self.ui["hizmet_sinifi"].setStyleSheet(S["input_combo"])
        apply_combo_title_case_formatting(self.ui["hizmet_sinifi"])
        _corp_field(corp_grid, 0, 1, 0, "Hizmet Sınıfı ✱", self.ui["hizmet_sinifi"], required=True)

        self.ui["kadro_unvani"] = QComboBox()
        self.ui["kadro_unvani"].setStyleSheet(S["input_combo"])
        apply_combo_title_case_formatting(self.ui["kadro_unvani"])
        _corp_field(corp_grid, 0, 1, 1, "Kadro Ünvanı ✱", self.ui["kadro_unvani"], required=True)

        self.ui["gorev_yeri"] = QComboBox()
        self.ui["gorev_yeri"].setStyleSheet(S["input_combo"])
        apply_combo_title_case_formatting(self.ui["gorev_yeri"])
        _corp_field(corp_grid, 0, 1, 2, "Görev Yeri", self.ui["gorev_yeri"])

        self.ui["baslama_tarihi"] = QDateEdit()
        self.ui["baslama_tarihi"].setCalendarPopup(True)
        self.ui["baslama_tarihi"].setDate(QDate.currentDate())
        self.ui["baslama_tarihi"].setStyleSheet(S["date"])
        _corp_field(corp_grid, 2, 3, 0, "Başlama Tarihi", self.ui["baslama_tarihi"])

        self.ui["sicil_no"] = QLineEdit()
        self.ui["sicil_no"].setStyleSheet(S["input"])
        self.ui["sicil_no"].setPlaceholderText("Kurum Sicil No")
        _corp_field(corp_grid, 2, 3, 1, "Kurum Sicil No", self.ui["sicil_no"])

        right_l.addWidget(corp_grp)

        # ── Eğitim Bilgileri ──
        edu_grp = QGroupBox("Eğitim Bilgileri")
        edu_grp.setStyleSheet(S["group"])
        edu_lay = QVBoxLayout(edu_grp)
        edu_lay.setSpacing(6)
        edu_lay.setContentsMargins(12, 8, 12, 12)

        # Sütun başlıkları
        def _edu_col_headers(layout):
            hdr = QHBoxLayout()
            hdr.setSpacing(8)
            hdr.setContentsMargins(0, 0, 0, 2)
            for txt, stretch in [("Okul Adı", 3), ("Bölüm / Fakülte", 3),
                                  ("Mezuniyet Tarihi", 2), ("Diploma No", 2)]:
                lbl = QLabel(txt)
                lbl.setProperty("color-role", "muted")
                lbl.setStyleSheet("font-size: 11px; font-weight: 600;")
                lbl.style().unpolish(lbl); lbl.style().polish(lbl)
                hdr.addWidget(lbl, stretch)
            layout.addLayout(hdr)

        # ── 1. Eğitim ──
        edu1_label = QLabel("Lise / Önlisans / Lisans")
        edu1_label.setProperty("color-role", "accent")
        edu1_label.setStyleSheet("font-weight: 600; font-size: 11px; background: transparent;")
        edu1_label.style().unpolish(edu1_label); edu1_label.style().polish(edu1_label)
        edu_lay.addWidget(edu1_label)
        _edu_col_headers(edu_lay)

        edu_grid1 = QGridLayout()
        edu_grid1.setHorizontalSpacing(8)
        edu_grid1.setVerticalSpacing(0)
        edu_grid1.setContentsMargins(0, 0, 0, 0)
        edu_grid1.setColumnStretch(0, 3); edu_grid1.setColumnStretch(1, 3)
        edu_grid1.setColumnStretch(2, 2); edu_grid1.setColumnStretch(3, 2)

        self.ui["okul1"] = QComboBox()
        self.ui["okul1"].setEditable(True)
        self.ui["okul1"].setStyleSheet(S["input_combo"])
        self.ui["okul1"].setPlaceholderText("Okul")
        apply_combo_title_case_formatting(self.ui["okul1"])
        edu_grid1.addWidget(self.ui["okul1"], 0, 0)

        self.ui["fakulte1"] = QComboBox()
        self.ui["fakulte1"].setEditable(True)
        self.ui["fakulte1"].setStyleSheet(S["input_combo"])
        self.ui["fakulte1"].setPlaceholderText("Bölüm")
        apply_combo_title_case_formatting(self.ui["fakulte1"])
        edu_grid1.addWidget(self.ui["fakulte1"], 0, 1)

        self.ui["mezun_tarihi1"] = QDateEdit()
        self.ui["mezun_tarihi1"].setStyleSheet(S["date"])
        self.ui["mezun_tarihi1"].setCalendarPopup(True)
        self.ui["mezun_tarihi1"].setDisplayFormat("dd.MM.yyyy")
        self.ui["mezun_tarihi1"].setToolTip("Mezuniyet tarihi (Gün.Ay.Yıl)")
        if _le := self.ui["mezun_tarihi1"].lineEdit():
            _le.setPlaceholderText("gg.aa.yyyy")
        edu_grid1.addWidget(self.ui["mezun_tarihi1"], 0, 2)

        self.ui["diploma_no1"] = QLineEdit()
        self.ui["diploma_no1"].setStyleSheet(S["input"])
        self.ui["diploma_no1"].setPlaceholderText("Diploma No")
        edu_grid1.addWidget(self.ui["diploma_no1"], 0, 3)
        edu_lay.addLayout(edu_grid1)

        # Ayırıcı
        sep_edu = QFrame()
        sep_edu.setFixedHeight(1)
        sep_edu.setProperty("bg-role", "separator")
        sep_edu.style().unpolish(sep_edu); sep_edu.style().polish(sep_edu)
        edu_lay.addWidget(sep_edu)

        # ── 2. Eğitim ──
        edu2_label = QLabel("Önlisans / Lisans / Yüksek Lisans / Doktora")
        edu2_label.setProperty("color-role", "accent")
        edu2_label.setStyleSheet("font-weight: 600; font-size: 11px; background: transparent;")
        edu2_label.style().unpolish(edu2_label); edu2_label.style().polish(edu2_label)
        edu_lay.addWidget(edu2_label)
        _edu_col_headers(edu_lay)

        edu_grid2 = QGridLayout()
        edu_grid2.setHorizontalSpacing(8)
        edu_grid2.setVerticalSpacing(0)
        edu_grid2.setContentsMargins(0, 0, 0, 0)
        edu_grid2.setColumnStretch(0, 3); edu_grid2.setColumnStretch(1, 3)
        edu_grid2.setColumnStretch(2, 2); edu_grid2.setColumnStretch(3, 2)

        self.ui["okul2"] = QComboBox()
        self.ui["okul2"].setEditable(True)
        self.ui["okul2"].setStyleSheet(S["input_combo"])
        self.ui["okul2"].setPlaceholderText("Okul")
        apply_combo_title_case_formatting(self.ui["okul2"])
        edu_grid2.addWidget(self.ui["okul2"], 0, 0)

        self.ui["fakulte2"] = QComboBox()
        self.ui["fakulte2"].setEditable(True)
        self.ui["fakulte2"].setStyleSheet(S["input_combo"])
        self.ui["fakulte2"].setPlaceholderText("Bölüm")
        apply_combo_title_case_formatting(self.ui["fakulte2"])
        edu_grid2.addWidget(self.ui["fakulte2"], 0, 1)

        self.ui["mezun_tarihi2"] = QDateEdit()
        self.ui["mezun_tarihi2"].setStyleSheet(S["date"])
        self.ui["mezun_tarihi2"].setCalendarPopup(True)
        self.ui["mezun_tarihi2"].setDisplayFormat("dd.MM.yyyy")
        self.ui["mezun_tarihi2"].setToolTip("Mezuniyet tarihi (Gün.Ay.Yıl)")
        if _le := self.ui["mezun_tarihi2"].lineEdit():
            _le.setPlaceholderText("gg.aa.yyyy")
        edu_grid2.addWidget(self.ui["mezun_tarihi2"], 0, 2)

        self.ui["diploma_no2"] = QLineEdit()
        self.ui["diploma_no2"].setStyleSheet(S["input"])
        self.ui["diploma_no2"].setPlaceholderText("Diploma No")
        edu_grid2.addWidget(self.ui["diploma_no2"], 0, 3)
        edu_lay.addLayout(edu_grid2)

        right_l.addWidget(edu_grp)

        # İlk Başlama Evrakları (PersonelDokumanPanel)
        self._dokuman_panel_container = QWidget()
        self._dokuman_panel_container.setStyleSheet("background: transparent;")
        self._dokuman_panel_layout = QVBoxLayout(self._dokuman_panel_container)
        self._dokuman_panel_layout.setContentsMargins(0, 0, 0, 0)

        right_l.addWidget(self._dokuman_panel_container)
        right_l.addStretch()

        content_layout.addWidget(left_grp, alignment=Qt.AlignmentFlag.AlignTop)
        content_layout.addWidget(right, 1)

        scroll.setWidget(content)
        main.addWidget(scroll, 1)

        # ── FOOTER ──
        footer = QHBoxLayout()
        footer.setSpacing(12)

        self.progress = QProgressBar()
        self.progress.setFixedWidth(150)
        self.progress.setFixedHeight(16)
        self.progress.setVisible(False)
        self.progress.setStyleSheet(S["progress"])
        footer.addWidget(self.progress)
        footer.addStretch()

        btn_iptal = QPushButton("İPTAL")
        btn_iptal.setProperty("style-role", "danger")
        btn_iptal.style().unpolish(btn_iptal); btn_iptal.style().polish(btn_iptal)
        btn_iptal.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_iptal.clicked.connect(self._on_cancel)
        IconRenderer.set_button_icon(btn_iptal, "x", color=DarkTheme.TEXT_PRIMARY, size=14)
        footer.addWidget(btn_iptal)

        # Yeni Personel Ekle butonu (sadece edit mode'da görünür)
        self.btn_yeni_personel = QPushButton("YENİ PERSONEL")
        self.btn_yeni_personel.setProperty("style-role", "secondary")
        self.btn_yeni_personel.style().unpolish(self.btn_yeni_personel)
        self.btn_yeni_personel.style().polish(self.btn_yeni_personel)
        self.btn_yeni_personel.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_yeni_personel.clicked.connect(self._reset_form_for_new_personel)
        IconRenderer.set_button_icon(self.btn_yeni_personel, "plus", color=DarkTheme.TEXT_PRIMARY, size=14)
        self.btn_yeni_personel.setVisible(self._is_edit)  # Sadece edit mode'da görünür
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self.btn_yeni_personel, "personel.write")
        footer.addWidget(self.btn_yeni_personel)

        title = "GÜNCELLE" if self._is_edit else "KAYDET"
        self.btn_kaydet = QPushButton(f"KİŞİYİ {title}")
        self.btn_kaydet.setProperty("style-role", "action")
        self.btn_kaydet.style().unpolish(self.btn_kaydet); self.btn_kaydet.style().polish(self.btn_kaydet)
        self.btn_kaydet.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_kaydet.clicked.connect(self._on_save)
        IconRenderer.set_button_icon(self.btn_kaydet, "save", color=DarkTheme.TEXT_PRIMARY, size=14)
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self.btn_kaydet, "personel.write")
        footer.addWidget(self.btn_kaydet)

        main.addLayout(footer)

    # ═══════════════════════════════════════════
    #  DOKUMAN PANEL YÖNETİMİ
    # ═══════════════════════════════════════════

    def _update_dokuman_panel(self):
        """TC No değiştiğinde PersonelDokumanPanel'i güncelle/enable-disable yap."""
        tc_no = self.ui["tc"].text().strip()
        
        # Panel yoksa oluştur (TC fark etmeksizin)
        if not self._dokuman_panel and self._db:
            self._dokuman_panel = PersonelDokumanPanel(
                personel_id="",  # Başlangıçta boş
                db=self._db,
                sabitler_cache=self._all_sabit,
                parent=self
            )
            self._dokuman_panel_layout.addWidget(self._dokuman_panel)
        
        # TC No durumuna göre panel'ı enable/disable et
        if self._dokuman_panel:
            if tc_no:
                # TC No varsa: panel enabled ve entity id'yi güncelle
                self._dokuman_panel.setEnabled(True)
                self._dokuman_panel.set_entity_id(tc_no)
            else:
                # TC No yoksa: panel disabled
                self._dokuman_panel.setEnabled(False)

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
        if not self._personel_svc:
            return

        try:
            # ── Sabitler'den ──
            sabitler = self._personel_svc.get_sabitler_repo()
            if not sabitler:
                return
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
            personeller = self._personel_svc.get_personel_repo()
            if not personeller:
                return
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
        }

        self._pending_uploads = 0
        self._completed_uploads = 0
        self._upload_errors = []

        for file_key, file_path in self._file_paths.items():
            if file_key not in upload_map:
                continue
            map_info = upload_map[file_key]
            ext = os.path.splitext(file_path)[1]
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
            MesajKutusu.uyari(
                self,
                "Bazı dosyalar yüklenemedi:\n" + "\n".join(self._upload_errors),
                "Drive Yükleme Uyarısı"
            )
        if hasattr(self, "_upload_callback"):
            self._upload_callback()

    # ═══════════════════════════════════════════
    #  REAL-TIME FORM VALIDASYON
    # ═══════════════════════════════════════════

    def _set_validation_status(self, label_widget, is_valid):
        """Validasyon statusunu ayarla: ✓ (ok), ✗ (err), ⚠ (muted)."""
        style = "font-size: 16px;"
        if is_valid is None:
            # Boş/kontrol edilmemiş
            label_widget.setText("⚠")
            label_widget.setProperty("color-role", "muted")
        elif is_valid:
            # Geçerli
            label_widget.setText("✓")
            label_widget.setProperty("color-role", "ok")
        else:
            # Geçersiz
            label_widget.setText("✗")
            label_widget.setProperty("color-role", "err")
        
        label_widget.setStyleSheet(style)
        label_widget.style().unpolish(label_widget)
        label_widget.style().polish(label_widget)

    def _validate_tc_on_change(self):
        """TC Kimlik No real-time validasyonu (merkezi validator kullanır)."""
        tc_text = self.ui["tc"].text().strip()
        
        if not tc_text:
            self._set_validation_status(self._tc_status, None)
        elif validate_tc_kimlik_no(tc_text):
            self._set_validation_status(self._tc_status, True)
        else:
            self._set_validation_status(self._tc_status, False)

    def _validate_email_on_change(self):
        """E-posta real-time validasyonu (merkezi validator kullanır)."""
        email_text = self.ui["eposta"].text().strip()
        
        if not email_text:
            self._set_validation_status(self._email_status, None)
        elif validate_email(email_text):
            self._set_validation_status(self._email_status, True)
        else:
            self._set_validation_status(self._email_status, False)

    def _validate_phone_on_change(self):
        """Telefon numarası real-time validasyonu (merkezi validator kullanır)."""
        phone_text = self.ui["cep_tel"].text().strip()
        
        if not phone_text:
            self._set_validation_status(self._phone_status, None)
        elif validate_phone_number(phone_text):
            self._set_validation_status(self._phone_status, True)
        else:
            self._set_validation_status(self._phone_status, False)

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
        
        phone = self._get_widget_value("cep_tel")
        if phone and not validate_phone_number(phone):
            errors.append("Telefon numarası geçersiz (05XX XXX XX XX formatında olmalı)")

        if not self._get_widget_value("hizmet_sinifi"):
            errors.append("Hizmet Sınıfı seçilmeli")
        if not self._get_widget_value("kadro_unvani"):
            errors.append("Kadro Ünvanı seçilmeli")

        return errors

    def _on_save(self):
        """Kaydet: validasyon → Drive yükleme → DB kayıt."""
        # Çift tıklama koruması
        self.btn_kaydet.setEnabled(False)
        
        if self._action_guard and not self._action_guard.check_and_warn(
            self, "personel.write", "Personel Kaydetme"
        ):
            self.btn_kaydet.setEnabled(True)
            return
        errors = self._validate()
        if errors:
            MesajKutusu.uyari(
                self,
                "\n".join(f"• {e}" for e in errors),
                "Eksik Bilgi"
            )
            self.btn_kaydet.setEnabled(True)
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
                if not self._personel_svc:
                    return
                existing = self._personel_svc.get_personel_by_tc(tc_no)
                if existing:
                    MesajKutusu.uyari(
                        self,
                        f"TC {tc_no} ile kayıtlı personel zaten var.",
                        "Kayıt Mevcut"
                    )
                    self.btn_kaydet.setEnabled(True)
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
        }
        for drive_key, db_col in link_map.items():
            link = self._drive_links.get(drive_key, "")
            if link:
                data[db_col] = link

        try:
            if not self._personel_svc:
                MesajKutusu.hata(self, "Veritabanı bağlantısı bulunamadı.", "Hata")
                self.btn_kaydet.setEnabled(True)
                return

            if self._is_edit:
                ok = self._personel_svc.guncelle(data["KimlikNo"], data)
                if not ok:
                    MesajKutusu.hata(self, "Personel kaydı güncellenemedi.", "Hata")
                    self.btn_kaydet.setEnabled(True)
                    return
                logger.info(f"Personel güncellendi: {data['KimlikNo']}")
                
                MesajKutusu.bilgi(
                    self,
                    "Personel kaydı başarıyla güncellendi.",
                    "Başarılı"
                )

                if self._on_saved:
                    self._on_saved()
                
                self.btn_kaydet.setEnabled(True)
            else:
                ok = self._personel_svc.ekle(data)
                if not ok:
                    MesajKutusu.hata(
                        self,
                        "Personel kaydı eklenemedi.\nTC Kimlik No ve zorunlu alanları kontrol edin.",
                        "Hata"
                    )
                    self.btn_kaydet.setEnabled(True)
                    return
                logger.info(f"Yeni personel eklendi: {data['KimlikNo']}")

                # Yeni personel için Izin_Bilgi kaydı oluştur
                try:
                    if self._izin_svc:
                        ok_izin = self._izin_svc.create_or_update_izin_bilgi(
                            tc=data.get("KimlikNo", ""),
                            ad_soyad=data.get("AdSoyad", ""),
                            baslama_tarihi=data.get("MemuriyeteBaslamaTarihi", ""),
                        )
                        if not ok_izin:
                            logger.warning(f"Izin_Bilgi kaydı oluşturulamadı: {data.get('KimlikNo', '')}")
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

                # Yeni ekleme: kullanıcıya belge yükleme seçeneği sun
                yanit = MesajKutusu.soru(
                    self,
                    "Personel kaydı başarıyla eklendi.\n\nBelge yüklemek istiyor musunuz?",
                    "Başarılı"
                )

                if yanit:
                    # Form'u edit mode'a geçir ve açık tut
                    self._is_edit = True
                    self._edit_data = data

                    # ── Sağlık Takip: IlkMuayene satırı aç ──────────────────
                    saglik_kayit_no = None
                    try:
                        import uuid as _uuid
                        from datetime import date as _date
                        from core.di import get_registry as _get_reg
                        _reg = _get_reg(self._db)
                        _saglik_repo = _reg.get("Personel_Saglik_Takip")
                        saglik_kayit_no = _uuid.uuid4().hex[:12].upper()
                        _saglik_repo.insert({
                            "KayitNo":    saglik_kayit_no,
                            "Personelid": str(data.get("KimlikNo", "")).strip(),
                            "AdSoyad":    str(data.get("AdSoyad",  "")).strip(),
                            "Birim":      str(data.get("GorevYeri","")).strip(),
                            "Yil":        _date.today().year,
                            "Durum":      "IlkMuayene",
                        })
                        logger.info(
                            f"IlkMuayene satırı açıldı: "
                            f"{data.get('AdSoyad')} / KayitNo={saglik_kayit_no}"
                        )
                    except Exception as _se:
                        logger.warning(f"IlkMuayene satırı açılamadı: {_se}")
                        saglik_kayit_no = None
                    # ─────────────────────────────────────────────────────────

                    # Form başlığını güncelle
                    if self.lbl_baslik:
                        self.lbl_baslik.setText(f"Personel Düzenle — {data.get('AdSoyad', '')}")

                    # Kaydet butonunu güncelle
                    if hasattr(self, 'btn_kaydet') and self.btn_kaydet:
                        self.btn_kaydet.setText("KİŞİYİ GÜNCELLE")

                    # Yeni Personel butonu göster
                    if hasattr(self, 'btn_yeni_personel') and self.btn_yeni_personel:
                        self.btn_yeni_personel.setVisible(True)

                    # Belge panelini aç ve saglik kaydına bağla
                    if hasattr(self, '_dokuman_panel') and self._dokuman_panel:
                        self._dokuman_panel.set_entity_id(data["KimlikNo"])
                        if saglik_kayit_no:
                            self._dokuman_panel.set_related_record(
                                iliskili_id  = saglik_kayit_no,
                                iliskili_tip = "Personel_Saglik_Takip",
                            )
                            # Varsayılan belge türünü İşe Giriş Muayenesi yap
                            self._dokuman_panel.set_default_belge_turu("İşe Giriş Muayenesi")

                    MesajKutusu.bilgi(
                        self,
                        "Artık belge yükleyebilirsiniz.\n\nİşlemler bittiğinde:\n- 'YENİ PERSONEL' → Başka personel ekleyin\n- 'İptal' → Listeye dönün",
                        "Bilgi"
                    )
                else:
                    # Hayır dedi, normal akış devam etsin
                    if self._on_saved:
                        self._on_saved()
                    
                    self.btn_kaydet.setEnabled(True)

        except Exception as e:
            logger.error(f"Kaydetme hatası: {e}")
            MesajKutusu.hata(self, f"Kaydetme sırasında hata:\n{e}", "Hata")
            self.btn_kaydet.setEnabled(True)

    def _on_cancel(self):
        """İptal — form kapanış sinyali emitir."""
        self.form_closed.emit()

    def _reset_form_for_new_personel(self):
        """Formu temizle ve yeni personel eklemek için hazırla."""
        try:
            # Mod değiştir
            self._is_edit = False
            self._edit_data = None

            # Form başlığını güncelle
            if self.lbl_baslik:
                self.lbl_baslik.setText("Personel Ekle")

            # Kaydet butonu metnini güncelle
            if hasattr(self, 'btn_kaydet') and self.btn_kaydet:
                self.btn_kaydet.setText("KİŞİYİ KAYDET")

            # Yeni Personel butonunu gizle
            if hasattr(self, 'btn_yeni_personel') and self.btn_yeni_personel:
                self.btn_yeni_personel.setVisible(False)

            # Tüm text input'ları temizle
            for key, widget in self.ui.items():
                if isinstance(widget, QLineEdit):
                    widget.clear()
                elif isinstance(widget, QComboBox):
                    widget.setCurrentIndex(0)
                elif isinstance(widget, QDateEdit):
                    widget.setDate(QDate.currentDate())

            # Fotoğrafı temizle
            if hasattr(self, 'lbl_resim') and self.lbl_resim:
                self.lbl_resim.clear()
                self.lbl_resim.setText("Fotoğraf Yok")

            # TC status icon'u temizle
            if hasattr(self, '_tc_status') and self._tc_status:
                self._tc_status.clear()

            # Drive links ve file paths temizle
            self._drive_links = {}
            self._file_paths = {}

            # Belge panelini temizle
            if hasattr(self, '_dokuman_panel') and self._dokuman_panel:
                self._dokuman_panel.set_entity_id("")

            logger.info("Form yeni personel için temizlendi")
            MesajKutusu.bilgi(
                self,
                "Form yeni personel eklemek için temizlendi.",
                "Form Hazır"
            )

        except Exception as e:
            logger.error(f"Form temizleme hatası: {e}")
            MesajKutusu.uyari(self, f"Form temizlenirken hata oluştu: {e}", "Uyarı")

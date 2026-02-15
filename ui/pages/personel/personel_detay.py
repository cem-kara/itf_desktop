# -*- coding: utf-8 -*-
import os
import tempfile
from PySide6.QtCore import Qt, QDate, QThread, Signal, QRegularExpression, QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QProgressBar, QFrame, QComboBox, QLineEdit,
    QDateEdit, QGroupBox, QMessageBox, QFileDialog, QTabWidget,
    QGridLayout
)
from PySide6.QtGui import QCursor, QPixmap, QRegularExpressionValidator, QDesktopServices

from core.logger import logger
from core.hata_yonetici import exc_logla
from ui.theme_manager import ThemeManager


# ─── Drive Yükleme Worker ───
class DriveUploadWorker(QThread):
    finished = Signal(str, str)
    error = Signal(str, str)

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
            exc_logla("PersonelDetay.DosyaYukleyici", e)
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


# ═══════════════════════════════════════════════
#  PERSONEL DETAY SAYFASI
# ═══════════════════════════════════════════════

class PersonelDetayPage(QWidget):

    ayrilis_requested = Signal(dict)  # personel_data
    """
    Personel Detay / Düzenleme sayfası.
    db: SQLiteManager
    personel_data: dict → personel satır verisi
    on_back: callback → listeye geri dönüş
    """

    def __init__(self, db=None, personel_data=None, on_back=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(S["page"])
        self._db = db
        self._data = personel_data or {}
        self._on_back = on_back
        self._editing = False
        self.ui = {}
        self._file_paths = {}
        self._drive_links = {}
        self._drive_folders = {}
        self._upload_workers = []

        self._setup_ui()
        self._populate_combos()
        self._fill_form(self._data)
        self._set_edit_mode(False)

    # ═══════════════════════════════════════════
    #  ANA UI
    # ═══════════════════════════════════════════

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 12, 20, 12)
        main.setSpacing(12)

        # ── HEADER ──
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 32, 44, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }
        """)
        header = QHBoxLayout(header_frame)
        header.setContentsMargins(20, 12, 20, 12)
        header.setSpacing(12)

        btn_back = QPushButton("← Geri")
        btn_back.setStyleSheet(S["cancel_btn"])
        btn_back.setCursor(QCursor(Qt.PointingHandCursor))
        btn_back.setFixedHeight(36)
        btn_back.clicked.connect(self._go_back)
        header.addWidget(btn_back)

        self.lbl_ad = QLabel("👤 ")
        self.lbl_ad.setStyleSheet(S["header_name"])
        header.addWidget(self.lbl_ad)

        self.lbl_durum = QLabel("")
        header.addWidget(self.lbl_durum)
        header.addStretch()

        self.btn_edit = QPushButton("✏️ Düzenle")
        self.btn_edit.setStyleSheet(S["edit_btn"])
        self.btn_edit.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_edit.setFixedHeight(36)
        self.btn_edit.clicked.connect(self._toggle_edit)
        header.addWidget(self.btn_edit)

        self.btn_save = QPushButton("💾 Kaydet")
        self.btn_save.setStyleSheet(S["save_btn"])
        self.btn_save.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_save.setFixedHeight(36)
        self.btn_save.clicked.connect(self._on_save)
        self.btn_save.setVisible(False)
        header.addWidget(self.btn_save)

        self.btn_cancel_edit = QPushButton("✕ İptal")
        self.btn_cancel_edit.setStyleSheet(S["cancel_btn"])
        self.btn_cancel_edit.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_cancel_edit.setFixedHeight(36)
        self.btn_cancel_edit.clicked.connect(self._cancel_edit)
        self.btn_cancel_edit.setVisible(False)
        header.addWidget(self.btn_cancel_edit)

        main.addWidget(header_frame)

        # ── TAB WIDGET ──
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(S["tab"])

        # Tab 1: Bilgiler
        tab_bilgi = QWidget()
        tab_bilgi.setStyleSheet("background: transparent;")
        self._setup_bilgi_tab(tab_bilgi)
        self.tabs.addTab(tab_bilgi, "📋 Personel Bilgileri")

        # Tab 2: İzinler
        tab_izin = QWidget()
        tab_izin.setStyleSheet("background: transparent;")
        self._setup_izin_tab(tab_izin)
        self.tabs.addTab(tab_izin, "🏖️ İzin Bilgileri")

        main.addWidget(self.tabs, 1)

        # ── FOOTER PROGRESS ──
        self.progress = QProgressBar()
        self.progress.setFixedHeight(16)
        self.progress.setVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 4px; color: #8b8fa3; font-size: 11px;
            }
            QProgressBar::chunk {
                background-color: rgba(29, 117, 254, 0.6);
                border-radius: 3px;
            }
        """)
        main.addWidget(self.progress)

    # ── TAB 1: BİLGİLER ──

    def _setup_bilgi_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 8, 0, 0)

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
        photo_grp = QGroupBox("📷  Fotoğraf")
        photo_grp.setStyleSheet(S["group"])
        photo_lay = QVBoxLayout(photo_grp)
        photo_lay.setAlignment(Qt.AlignCenter)

        self.lbl_resim = QLabel("Fotoğraf\nYüklenmedi")
        self.lbl_resim.setFixedSize(160, 200)
        self.lbl_resim.setAlignment(Qt.AlignCenter)
        self.lbl_resim.setStyleSheet(S["photo_area"])
        photo_lay.addWidget(self.lbl_resim, alignment=Qt.AlignCenter)

        self.btn_photo = QPushButton("📷 Fotoğraf Değiştir")
        self.btn_photo.setStyleSheet(S["photo_btn"])
        self.btn_photo.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_photo.clicked.connect(self._select_photo)
        photo_lay.addWidget(self.btn_photo, alignment=Qt.AlignCenter)
        left_l.addWidget(photo_grp)

        # Kimlik
        id_grp = QGroupBox("🪪  Kimlik Bilgileri")
        id_grp.setStyleSheet(S["group"])
        id_lay = QVBoxLayout(id_grp)
        id_lay.setSpacing(10)

        row1 = QHBoxLayout()
        self.ui["tc"] = self._make_input("TC Kimlik No", row1)
        self.ui["tc"].setMaxLength(11)
        self.ui["tc"].setValidator(QRegularExpressionValidator(
            QRegularExpression(r"^\d{0,11}$")
        ))
        self.ui["ad_soyad"] = self._make_input("Ad Soyad", row1)
        id_lay.addLayout(row1)

        row2 = QHBoxLayout()
        self.ui["dogum_yeri"] = self._make_combo("Doğum Yeri", row2, editable=True)
        self.ui["dogum_tarihi"] = self._make_date("Doğum Tarihi", row2)
        id_lay.addLayout(row2)

        left_l.addWidget(id_grp)

        # İletişim
        contact_grp = QGroupBox("📞  İletişim Bilgileri")
        contact_grp.setStyleSheet(S["group"])
        contact_lay = QVBoxLayout(contact_grp)
        row_c = QHBoxLayout()
        self.ui["cep_tel"] = self._make_input("Cep Telefonu", row_c)
        self.ui["eposta"] = self._make_input("E-posta Adresi", row_c)
        contact_lay.addLayout(row_c)
        left_l.addWidget(contact_grp)

        left_l.addStretch()

        # ── SAĞ SÜTUN ──
        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setSpacing(12)
        right_l.setContentsMargins(0, 0, 0, 0)

        # Kurumsal
        corp_grp = QGroupBox("🏛️  Kadro ve Kurumsal Bilgiler")
        corp_grp.setStyleSheet(S["group"])
        corp_lay = QVBoxLayout(corp_grp)
        corp_lay.setSpacing(10)

        row_k1 = QHBoxLayout()
        self.ui["hizmet_sinifi"] = self._make_combo("Hizmet Sınıfı", row_k1)
        self.ui["kadro_unvani"] = self._make_combo("Kadro Ünvanı", row_k1)
        corp_lay.addLayout(row_k1)

        row_k2 = QHBoxLayout()
        self.ui["gorev_yeri"] = self._make_combo("Görev Yeri", row_k2)
        self.ui["sicil_no"] = self._make_input("Kurum Sicil No", row_k2)
        corp_lay.addLayout(row_k2)

        row_k3 = QHBoxLayout()
        self.ui["baslama_tarihi"] = self._make_date("Memuriyete Başlama Tarihi", row_k3)
        row_k3.addStretch()
        corp_lay.addLayout(row_k3)

        # İşten Ayrılış butonu
        self.btn_ayrilis = QPushButton("⚠️ İşten Çıkış Yap")
        self.btn_ayrilis.setStyleSheet(S["danger_btn"])
        self.btn_ayrilis.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_ayrilis.setFixedHeight(40)
        self.btn_ayrilis.clicked.connect(self._on_ayrilis)
        corp_lay.addWidget(self.btn_ayrilis)

        right_l.addWidget(corp_grp)

        # Eğitim
        edu_grp = QGroupBox("🎓  Eğitim Bilgileri")
        edu_grp.setStyleSheet(S["group"])
        edu_main = QHBoxLayout(edu_grp)
        edu_main.setSpacing(16)

        for i in ["1", "2"]:
            col = QVBoxLayout()
            col.setSpacing(8)

            header_lbl = QLabel(f"{'Lisans' if i == '1' else 'Yüksek Lisans / 2. Okul'}")
            header_lbl.setStyleSheet("color: #6bd3ff; font-size: 12px; font-weight: bold; background: transparent;")
            col.addWidget(header_lbl)

            self.ui[f"okul{i}"] = self._make_combo_v("Okul Adı", col, editable=True)
            self.ui[f"fakulte{i}"] = self._make_combo_v("Bölüm / Fakülte", col, editable=True)
            self.ui[f"mezun_tarihi{i}"] = self._make_input_v("Mezuniyet Tarihi", col)
            self.ui[f"diploma_no{i}"] = self._make_input_v("Diploma No", col)

            btn_dip = QPushButton(f"📄 Diploma {i} Seç")
            btn_dip.setStyleSheet(S["file_btn"])
            btn_dip.setCursor(QCursor(Qt.PointingHandCursor))
            btn_dip.clicked.connect(lambda checked, idx=i: self._select_diploma(idx))
            col.addWidget(btn_dip)
            self.ui[f"btn_diploma{i}"] = btn_dip

            btn_open = QPushButton(f"Diploma {i} Aç")
            btn_open.setStyleSheet(S["file_btn"])
            btn_open.setCursor(QCursor(Qt.PointingHandCursor))
            btn_open.clicked.connect(lambda checked, idx=i: self._open_diploma(idx))
            col.addWidget(btn_open)
            self.ui[f"btn_diploma_open{i}"] = btn_open

            lbl_file = QLabel("")
            lbl_file.setStyleSheet("color: #4ade80; font-size: 11px; background: transparent;")
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
        layout.addWidget(scroll)

    # ── TAB 2: İZİN BİLGİLERİ ──

    def _setup_izin_tab(self, parent):
        layout = QHBoxLayout(parent)
        layout.setContentsMargins(8, 16, 8, 8)
        layout.setSpacing(12)

        # Yıllık İzin
        grp_yillik = QGroupBox("📅  Yıllık İzin Durumu")
        grp_yillik.setStyleSheet(S["group"])
        g = QGridLayout(grp_yillik)
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(6)
        g.setContentsMargins(14, 12, 14, 12)

        self.lbl_y_devir = self._add_stat(g, 0, "Devir Eden İzin", "stat_value")
        self.lbl_y_hak = self._add_stat(g, 1, "Bu Yıl Hak Edilen", "stat_value")

        sep1 = QFrame(); sep1.setFixedHeight(1); sep1.setStyleSheet(S["separator"])
        g.addWidget(sep1, 2, 0, 1, 2)

        self.lbl_y_toplam = self._add_stat(g, 3, "TOPLAM İZİN HAKKI", "stat_highlight")
        self.lbl_y_kullanilan = self._add_stat(g, 4, "Kullanılan Yıllık İzin", "stat_red")

        sep2 = QFrame(); sep2.setFixedHeight(1); sep2.setStyleSheet(S["separator"])
        g.addWidget(sep2, 5, 0, 1, 2)

        self.lbl_y_kalan = self._add_stat(g, 6, "KALAN YILLIK İZİN", "stat_green")

        g.setRowStretch(7, 1)
        layout.addWidget(grp_yillik)

        # Şua ve Diğer
        grp_diger = QGroupBox("☢️  Şua ve Diğer İzinler")
        grp_diger.setStyleSheet(S["group"])
        g2 = QGridLayout(grp_diger)
        g2.setHorizontalSpacing(10)
        g2.setVerticalSpacing(6)
        g2.setContentsMargins(14, 12, 14, 12)

        self.lbl_s_hak = self._add_stat(g2, 0, "Hak Edilen Şua İzin", "stat_value")
        self.lbl_s_kul = self._add_stat(g2, 1, "Kullanılan Şua İzinleri", "stat_red")

        sep3 = QFrame(); sep3.setFixedHeight(1); sep3.setStyleSheet(S["separator"])
        g2.addWidget(sep3, 2, 0, 1, 2)

        self.lbl_s_kalan = self._add_stat(g2, 3, "KALAN ŞUA İZNİ", "stat_green")

        # Cari yıl kazanım
        sep4 = QFrame(); sep4.setFixedHeight(1); sep4.setStyleSheet(S["separator"])
        g2.addWidget(sep4, 4, 0, 1, 2)

        self.lbl_s_cari = self._add_stat(g2, 5, "Cari Yıl Şua Kazanım", "stat_value")
        self.lbl_diger = self._add_stat(g2, 6, "Toplam Rapor/Mazeret", "stat_value")

        g2.setRowStretch(7, 1)
        layout.addWidget(grp_diger)

    def _add_stat(self, grid, row, text, style_key):
        lbl = QLabel(text)
        lbl.setStyleSheet(S["stat_label"])
        grid.addWidget(lbl, row, 0)
        val = QLabel("—")
        val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        val.setStyleSheet(S[style_key])
        grid.addWidget(val, row, 1)
        return val

    # ═══════════════════════════════════════════
    #  WIDGET FABRİKALARI
    # ═══════════════════════════════════════════

    def _make_input(self, label, parent_layout, placeholder=""):
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label"])
        lay.addWidget(lbl)
        inp = QLineEdit()
        inp.setStyleSheet(S["input"])
        if placeholder:
            inp.setPlaceholderText(placeholder)
        lay.addWidget(inp)
        parent_layout.addWidget(container)
        return inp

    def _make_combo(self, label, parent_layout, editable=False):
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label"])
        lay.addWidget(lbl)
        cmb = QComboBox()
        cmb.setStyleSheet(S["combo"])
        cmb.setEditable(editable)
        lay.addWidget(cmb)
        parent_layout.addWidget(container)
        return cmb

    def _make_date(self, label, parent_layout):
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label"])
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
            from database.repository_registry import RepositoryRegistry
            registry = RepositoryRegistry(self._db)
            sabitler = registry.get("Sabitler")
            all_sabit = sabitler.get_all()

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

            # Personel'den benzersiz değerler
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

            # Drive klasör ID'leri
            self._drive_folders = {
                str(r.get("MenuEleman", "")).strip(): str(r.get("Aciklama", "")).strip()
                for r in all_sabit
                if r.get("Kod") == "Sistem_DriveID" and r.get("Aciklama", "").strip()
            }

        except Exception as e:
            logger.error(f"Combo doldurma hatası: {e}")

    # ═══════════════════════════════════════════
    #  FORM ↔ VERİ
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
                    d = QDate.fromString(value, "yyyy-MM-dd")
                    if d.isValid():
                        w.setDate(d)
                except Exception:
                    pass

    def _fill_form(self, row_data):
        for db_col, ui_key in FIELD_MAP.items():
            self._set_widget_value(ui_key, row_data.get(db_col, ""))
        self._set_photo_preview(row_data.get("Resim", ""))
        self._refresh_diploma_ui("1", row_data.get("Diploma1", ""))
        self._refresh_diploma_ui("2", row_data.get("Diploma2", ""))

        # Başlık güncelle
        ad = row_data.get("AdSoyad", "")
        tc = row_data.get("KimlikNo", "")
        self.lbl_ad.setText(f"👤 {ad}")

        durum = str(row_data.get("Durum", "Aktif")).strip()
        durum_styles = {
            "Aktif": S["header_durum_aktif"],
            "Pasif": S["header_durum_pasif"],
            "İzinli": S["header_durum_izinli"],
        }
        self.lbl_durum.setText(durum)
        self.lbl_durum.setStyleSheet(durum_styles.get(durum, S["header_durum_aktif"]))

        # İzin bilgilerini doldur
        self._load_izin_data(tc)

    def _set_photo_preview(self, photo_ref):
        """Fotoğraf alanını yerel dosya veya Drive linkinden önizler."""
        photo_ref = str(photo_ref or "").strip()
        self.lbl_resim.setToolTip("")
        self.lbl_resim.setPixmap(QPixmap())

        if not photo_ref:
            self.lbl_resim.setText("Fotoğraf\nYüklenmedi")
            return

        # Yerel dosya ise doğrudan yükle
        if os.path.exists(photo_ref):
            pixmap = QPixmap(photo_ref)
            if not pixmap.isNull():
                self.lbl_resim.setText("")
                self.lbl_resim.setPixmap(
                    pixmap.scaled(160, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                self.lbl_resim.setToolTip(os.path.basename(photo_ref))
                return

        # Drive linki ise geçici dosyaya indirip önizle
        if photo_ref.startswith("http"):
            try:
                from database.google import GoogleDriveService
                drive = GoogleDriveService()
                file_id = drive.extract_file_id(photo_ref)
                if file_id:
                    fd, tmp_path = tempfile.mkstemp(prefix="personel_resim_", suffix=".img")
                    os.close(fd)
                    if drive.download_file(file_id, tmp_path):
                        pixmap = QPixmap(tmp_path)
                        try:
                            os.remove(tmp_path)
                        except OSError:
                            pass
                        if not pixmap.isNull():
                            self.lbl_resim.setText("")
                            self.lbl_resim.setPixmap(
                                pixmap.scaled(160, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            )
                            self.lbl_resim.setToolTip("Drive fotoğrafı")
                            return
            except Exception as e:
                logger.warning(f"Fotoğraf önizleme yüklenemedi: {e}")

        self.lbl_resim.setText("Fotoğraf\nYüklenemedi")
        self.lbl_resim.setToolTip(photo_ref[:200])

    def _refresh_diploma_ui(self, idx, db_value=None):
        file_key = f"Diploma{idx}"
        lbl = self.ui.get(f"diploma_file_lbl{idx}")
        open_btn = self.ui.get(f"btn_diploma_open{idx}")
        if not lbl:
            return

        selected = str(self._file_paths.get(file_key, "")).strip()
        existing = str(db_value if db_value is not None else self._data.get(file_key, "")).strip()
        active_ref = selected or existing

        if selected:
            lbl.setText(f"Seçildi: {os.path.basename(selected)}")
        elif existing.startswith("http"):
            lbl.setText("Yüklü dosya (Drive) - Aç ile görüntüleyin")
        elif existing and os.path.exists(existing):
            lbl.setText(f"Yüklü dosya: {os.path.basename(existing)}")
        elif existing:
            lbl.setText("Yüklü dosya mevcut")
        else:
            lbl.setText("Dosya yok")

        if open_btn:
            open_btn.setEnabled(bool(active_ref))
            open_btn.setToolTip(active_ref if active_ref else "Diploma dosyası yok")

    def _open_diploma(self, idx):
        file_key = f"Diploma{idx}"
        ref = str(self._file_paths.get(file_key, "")).strip()
        if not ref:
            ref = str(self._data.get(file_key, "")).strip()
        if not ref:
            QMessageBox.information(self, "Bilgi", f"Diploma {idx} dosyası bulunamadı.")
            return

        if ref.startswith("http"):
            ok = QDesktopServices.openUrl(QUrl(ref))
        else:
            ok = QDesktopServices.openUrl(QUrl.fromLocalFile(ref))
        if not ok:
            QMessageBox.warning(self, "Uyarı", f"Diploma {idx} dosyası açılamadı.")

    def _collect_data(self):
        data = {}
        for db_col, ui_key in FIELD_MAP.items():
            data[db_col] = self._get_widget_value(ui_key)

        # Title Case
        for field in ["AdSoyad", "DogumYeri", "MezunOlunanOkul", "MezunOlunanFakulte",
                       "MezunOlunanOkul2", "MezunOlunanFakulte2"]:
            if data.get(field):
                data[field] = data[field].title()

        return data

    def _load_izin_data(self, tc_kimlik):
        """İzin_Bilgi tablosundan izin verilerini yükler."""
        if not self._db or not tc_kimlik:
            return
        try:
            from database.repository_registry import RepositoryRegistry
            registry = RepositoryRegistry(self._db)
            repo = registry.get("Izin_Bilgi")
            izin = repo.get_by_id(tc_kimlik)

            if izin:
                self.lbl_y_devir.setText(str(izin.get("YillikDevir", "0")))
                self.lbl_y_hak.setText(str(izin.get("YillikHakedis", "0")))
                self.lbl_y_toplam.setText(str(izin.get("YillikToplamHak", "0")))
                self.lbl_y_kullanilan.setText(str(izin.get("YillikKullanilan", "0")))
                self.lbl_y_kalan.setText(str(izin.get("YillikKalan", "0")))
                self.lbl_s_hak.setText(str(izin.get("SuaKullanilabilirHak", "0")))
                self.lbl_s_kul.setText(str(izin.get("SuaKullanilan", "0")))
                self.lbl_s_kalan.setText(str(izin.get("SuaKalan", "0")))
                self.lbl_s_cari.setText(str(izin.get("SuaCariYilKazanim", "0")))
                self.lbl_diger.setText(str(izin.get("RaporMazeretTop", "0")))
            else:
                for lbl in [self.lbl_y_devir, self.lbl_y_hak, self.lbl_y_toplam,
                            self.lbl_y_kullanilan, self.lbl_y_kalan, self.lbl_s_hak,
                            self.lbl_s_kul, self.lbl_s_kalan, self.lbl_s_cari, self.lbl_diger]:
                    lbl.setText("—")

        except Exception as e:
            logger.error(f"İzin bilgisi yükleme hatası: {e}")

    # ═══════════════════════════════════════════
    #  DÜZENLEME MODU
    # ═══════════════════════════════════════════

    def _set_edit_mode(self, editing):
        self._editing = editing

        self.btn_edit.setVisible(not editing)
        self.btn_save.setVisible(editing)
        self.btn_cancel_edit.setVisible(editing)

        # TC her zaman readonly
        self.ui["tc"].setReadOnly(True)

        for key, widget in self.ui.items():
            if key in ("tc", "diploma_file_lbl1", "diploma_file_lbl2"):
                continue
            if isinstance(widget, QLineEdit):
                widget.setReadOnly(not editing)
            elif isinstance(widget, QComboBox):
                widget.setEnabled(editing)
            elif isinstance(widget, QDateEdit):
                widget.setEnabled(editing)

        self.btn_photo.setVisible(editing)
        self.btn_ayrilis.setVisible(not editing)
        for i in ("1", "2"):
            btn_select = self.ui.get(f"btn_diploma{i}")
            if btn_select:
                btn_select.setVisible(editing)
                btn_select.setEnabled(editing)
            self._refresh_diploma_ui(i)

    def _toggle_edit(self):
        self._set_edit_mode(True)

    def _cancel_edit(self):
        self._file_paths.clear()
        self._drive_links.clear()
        self._fill_form(self._data)
        self._set_edit_mode(False)

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
            self._set_photo_preview(path)
            logger.info(f"Fotoğraf seçildi: {path}")

    def _select_diploma(self, idx):
        if not self._editing:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, f"Diploma {idx} Seç", "",
            "Dosyalar (*.pdf *.jpg *.jpeg *.png);;Tüm Dosyalar (*)"
        )
        if path:
            self._file_paths[f"Diploma{idx}"] = path
            self._refresh_diploma_ui(str(idx))
            lbl = self.ui.get(f"diploma_file_lbl{idx}")
            if lbl:
                lbl.setText(f"✓ {os.path.basename(path)}")
            logger.info(f"Diploma {idx} seçildi: {path}")

    def _get_drive_folder_id(self, folder_name):
        return self._drive_folders.get(folder_name, "")

    def _upload_files_to_drive(self, tc_no, callback):
        if not self._file_paths:
            callback()
            return

        upload_map = {
            "Resim": ("Personel_Resim", "Resim"),
            "Diploma1": ("Personel_Diploma", "Diploma1"),
            "Diploma2": ("Personel_Diploma", "Diploma2"),
        }

        self._pending_uploads = 0
        self._upload_errors = []

        for file_key, file_path in self._file_paths.items():
            if file_key not in upload_map:
                continue
            folder_name, db_field = upload_map[file_key]
            folder_id = self._get_drive_folder_id(folder_name)
            if not folder_id:
                self._upload_errors.append(f"{db_field}: Drive klasörü bulunamadı ({folder_name})")
                logger.warning(f"Drive klasörü bulunamadı: {folder_name}")
                continue

            ext = os.path.splitext(file_path)[1]
            custom_name = f"{tc_no}_{db_field}{ext}"

            self._pending_uploads += 1
            worker = DriveUploadWorker(file_path, folder_id, custom_name, db_field)
            worker.finished.connect(self._on_upload_finished)
            worker.error.connect(self._on_upload_error)
            self._upload_workers.append(worker)
            worker.start()

        if self._pending_uploads == 0:
            if self._upload_errors:
                QMessageBox.warning(
                    self, "Drive Yükleme Uyarısı",
                    "Bazı dosyalar yüklenemedi:\n" + "\n".join(self._upload_errors)
                )
            callback()
        else:
            self._upload_callback = callback
            self.progress.setVisible(True)
            self.progress.setRange(0, 0)
            self.btn_save.setEnabled(False)

    def _on_upload_finished(self, alan_adi, link):
        self._drive_links[alan_adi] = link
        self._delete_old_drive_file(alan_adi, link)
        logger.info(f"Drive yükleme OK: {alan_adi} → {link}")
        self._pending_uploads -= 1
        if self._pending_uploads <= 0:
            self._finalize_uploads()

    def _on_upload_error(self, alan_adi, hata):
        self._upload_errors.append(f"{alan_adi}: {hata}")
        logger.error(f"Drive yükleme HATA: {alan_adi} → {hata}")
        self._pending_uploads -= 1
        if self._pending_uploads <= 0:
            self._finalize_uploads()

    def _delete_old_drive_file(self, db_field, new_link):
        """Yeni dosya yüklendikten sonra eski Drive dosyasını siler."""
        old_link = str(self._data.get(db_field, "")).strip()
        if not old_link or not old_link.startswith("http"):
            return
        if old_link == str(new_link).strip():
            return

        try:
            from database.google import GoogleDriveService
            old_file_id = GoogleDriveService.extract_file_id(old_link)
            if not old_file_id:
                return

            drive = GoogleDriveService()
            if drive.delete_file(old_file_id):
                logger.info(f"Eski Drive dosyasi silindi: {db_field} -> {old_file_id}")
            else:
                self._upload_errors.append(f"{db_field}: eski Drive dosyasi silinemedi")
                logger.warning(f"Eski Drive dosyasi silinemedi: {db_field} -> {old_file_id}")
        except Exception as e:
            self._upload_errors.append(f"{db_field}: eski Drive dosyasi silme hatasi")
            logger.warning(f"Eski Drive dosya silme hatasi ({db_field}): {e}")

    def _finalize_uploads(self):
        self.progress.setVisible(False)
        self.btn_save.setEnabled(True)
        self._upload_workers.clear()

        if self._upload_errors:
            QMessageBox.warning(
                self, "Drive Yükleme Uyarısı",
                "Bazı dosyalar yüklenemedi:\n" + "\n".join(self._upload_errors)
            )

        if hasattr(self, "_upload_callback"):
            self._upload_callback()

    # ═══════════════════════════════════════════
    #  KAYDET
    # ═══════════════════════════════════════════

    def _on_save(self):
        data = self._collect_data()
        tc_no = data["KimlikNo"]

        if not tc_no or not data.get("AdSoyad"):
            QMessageBox.warning(self, "Eksik Bilgi", "TC Kimlik No ve Ad Soyad boş olamaz.")
            return

        self._pending_data = data
        self._upload_files_to_drive(tc_no, self._save_to_db)

    def _save_to_db(self):
        data = self._pending_data

        link_map = {"Resim": "Resim", "Diploma1": "Diploma1", "Diploma2": "Diploma2"}
        for drive_key, db_col in link_map.items():
            link = self._drive_links.get(drive_key, "")
            if link:
                data[db_col] = link

        # Mevcut Durum'u koru
        data["Durum"] = self._data.get("Durum", "Aktif")

        try:
            from database.repository_registry import RepositoryRegistry
            registry = RepositoryRegistry(self._db)
            repo = registry.get("Personel")
            repo.update(data["KimlikNo"], data)
            logger.info(f"Personel güncellendi: {data['KimlikNo']}")

            # Yerel veriyi güncelle
            self._data.update(data)

            QMessageBox.information(self, "Başarılı", "Personel kaydı güncellendi.")

            self._file_paths.clear()
            self._drive_links.clear()
            self._fill_form(self._data)
            self._set_edit_mode(False)

        except Exception as e:
            logger.error(f"Güncelleme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Güncelleme hatası:\n{e}")

    # ═══════════════════════════════════════════
    #  İŞTEN AYRILMA
    # ═══════════════════════════════════════════

    def _on_ayrilis(self):
        """İşten ayrılık sayfasına yönlendir."""
        self.ayrilis_requested.emit(self._data)

    # ═══════════════════════════════════════════
    #  GERİ DÖN
    # ═══════════════════════════════════════════

    def _go_back(self):
        if self._on_back:
            self._on_back()

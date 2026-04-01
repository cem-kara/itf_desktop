# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout, 
    QGroupBox, QScrollArea, QLineEdit, QPushButton, QComboBox,
    QCompleter, QDateEdit, QFileDialog
)
from PySide6.QtCore import Qt, QDate, Signal, QThread
from PySide6.QtGui import QCursor, QPixmap
from core.di import get_personel_service, get_izin_service, get_dokuman_service
from core.hata_yonetici import bilgi_goster, hata_goster, uyari_goster
from core.logger import logger
from core.paths import DB_PATH
from ui.styles import DarkTheme
from ui.styles.icons import IconRenderer
from ui.components.formatted_widgets import apply_combo_title_case_formatting
import os
import tempfile


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
            svc = get_dokuman_service(db)
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

class PersonelOverviewPanel(QWidget):
    """
    Personel Merkez ekranı için 'Genel Bakış' sekmesi içeriği.
    Özet metrikleri ve düzenlenebilir personel bilgilerini gösterir.
    """
    open_documents = Signal()
    
    def __init__(self, ozet_data, db=None, sabitler_cache=None, parent=None):
        super().__init__(parent)
        self.data = ozet_data or {}
        self.db = db
        
        # Service enjeksiyonu (geliştirici rehberi: db parametresi)
        if db:
            self._personel_svc = get_personel_service(db)
            self._izin_svc = get_izin_service(db)
        else:
            self._personel_svc = None
            self._izin_svc = None
            
        self.sabitler_cache = sabitler_cache  # Cache'den gelen Sabitler listesi
        self.personel_data = self.data.get("personel", {})
        
        self._widgets = {}  # Alan adı -> QLineEdit/QComboBox
        self._view_buttons = {}  # Diploma görüntüleme butonları (sadece mevcut dosyaları açmak için)
        self._groups = {}   # Grup adı -> (layout, edit_btn, save_btn, cancel_btn)
        
        # Dosya upload yönetimi (sadece fotoğraf yükleme, diploma belgeler sayfasında)
        self._file_paths = {}          # {'Resim': local_path}
        self._drive_links = {}         # {'Resim': drive_link}
        self._drive_folders = {}       # {'Personel_Resim': folder_id}
        self._all_sabit = []           # Sistem_DriveID ve diğer sabitler
        self._upload_workers = []
        self._pending_uploads = 0
        self._upload_errors = []
        self._upload_meta = {}  # alan_adi -> metadata
        
        self._setup_ui()
        self._populate_combos()

    def _setup_ui(self):
        # Eski widget ve grup referanslarını temizle (silinmiş objelerden kaçınmak için)
        self._widgets.clear()
        self._groups.clear()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setProperty("bg-role", "plain")

        content = QWidget()
        content.setProperty("bg-role", "plain")
        content_vbox = QVBoxLayout(content)
        content_vbox.setSpacing(16)
        content_vbox.setContentsMargins(16, 16, 16, 16)

        if not self.personel_data:
            from core.logger import logger
            logger.warning(f"PersonelOverviewPanel: personel_data boş! (ozet_data: {self.data})")
            content_vbox.addWidget(QLabel("Personel verisi bulunamadı."))
            scroll.setWidget(content)
            main_layout.addWidget(scroll)
            return

        # ══════════════════════════════════════════════════════
        # SOL KART — Fotoğraf ve Kimlik
        # ══════════════════════════════════════════════════════
        left_grp = QGroupBox("Fotograf ve Kimlik Bilgileri")
        left_grp.setFixedWidth(270)
        left_l = QVBoxLayout(left_grp)
        left_l.setSpacing(0)
        left_l.setContentsMargins(12, 12, 12, 16)

        # — Fotoğraf —
        photo_wrap = QWidget()
        photo_wrap.setFixedHeight(200)
        pw_l = QVBoxLayout(photo_wrap)
        pw_l.setContentsMargins(0, 0, 0, 0)
        pw_l.setSpacing(6)

        self.lbl_resim = QLabel()
        self.lbl_resim.setFixedSize(160, 180)
        self.lbl_resim.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_resim.setProperty("bg-role", "panel")
        self.lbl_resim.setProperty("style-role", "profile-photo")  # QSS'de tanımlı olmalı
        pw_l.addWidget(self.lbl_resim, alignment=Qt.AlignmentFlag.AlignCenter)
        left_l.addWidget(photo_wrap)

        self._photo_upload_btn = QPushButton("Resim Yükle")
        self._photo_upload_btn.setProperty("style-role", "upload")
        self._photo_upload_btn.setFixedHeight(28)
        self._photo_upload_btn.clicked.connect(self._on_photo_upload)
        IconRenderer.set_button_icon(self._photo_upload_btn, "upload", color="primary", size=13)
        left_l.addWidget(self._photo_upload_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        left_l.addSpacing(10)

        # — Ad Soyad büyük —
        ad_soyad_val = str(self.personel_data.get("AdSoyad", ""))
        self.ad_display = QLabel(ad_soyad_val)
        self.ad_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ad_display.setWordWrap(True)
        self.ad_display.setProperty("style-role", "section-title")
        self.ad_display.setProperty("formatted", True)
        left_l.addWidget(self.ad_display)
        left_l.addSpacing(8)

        # — Ayırıcı —
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setProperty("bg-role", "separator")
        left_l.addWidget(sep)
        left_l.addSpacing(8)

        # — Kimlik bilgileri grid —
        kimlik_grid = QGridLayout()
        kimlik_grid.setHorizontalSpacing(8)
        kimlik_grid.setVerticalSpacing(6)
        kimlik_grid.setColumnStretch(1, 1)

        def _kimlik_row(grid, row, label_txt, value_txt, is_accent=False):
            lbl = QLabel(label_txt)
            lbl.setProperty("color-role", "muted")
            lbl.setStyleSheet("font-size: 10px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            val = QLabel(str(value_txt) if value_txt else "—")
            val.setWordWrap(True)
            if is_accent:
                val.setProperty("color-role", "accent")
                val.setStyleSheet("font-size: 11px; font-weight: 600;")
            else:
                val.setProperty("color-role", "primary")
                val.setStyleSheet("font-size: 12px; font-weight: 500;")

            grid.addWidget(lbl, row, 0)
            grid.addWidget(val, row, 1)
            return val

        self.tc_display       = _kimlik_row(kimlik_grid, 0, "TC Kimlik No",  self.personel_data.get("KimlikNo", ""), is_accent=True)
        self.dogum_yeri_display = _kimlik_row(kimlik_grid, 1, "Doğum Yeri",  self.personel_data.get("DogumYeri", ""))
        self.dogum_tarihi_display = _kimlik_row(kimlik_grid, 2, "Doğum Tarihi", self._fmt_date(self.personel_data.get("DogumTarihi", "")))

        left_l.addLayout(kimlik_grid)
        left_l.addStretch()

        self._set_photo_preview(self.personel_data.get("Resim"))

        # ══════════════════════════════════════════════════════
        # SAĞ SÜTUN — İletişim + Kadro
        # ══════════════════════════════════════════════════════
        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setSpacing(12)
        right_l.setContentsMargins(0, 0, 0, 0)

        # İletişim Grubu
        grp_iletisim = self._create_editable_group("İletişim Bilgileri", "iletisim")
        iletisim_content_widget = self._groups["iletisim"]["widget"]
        g_ilet = QGridLayout(iletisim_content_widget)
        g_ilet.setSpacing(12)
        g_ilet.setColumnStretch(0, 1)
        g_ilet.setColumnStretch(1, 1)
        self._add_editable_item(g_ilet, 0, 0, "Cep Telefonu", "CepTelefonu", "iletisim")
        self._add_editable_item(g_ilet, 0, 1, "E-posta", "Eposta", "iletisim")
        right_l.addWidget(grp_iletisim)

        # Kadro Grubu
        grp_kurum = self._create_editable_group("Kadro ve Kurumsal Bilgiler", "kadro")
        kadro_content_widget = self._groups["kadro"]["widget"]
        g_kad = QGridLayout(kadro_content_widget)
        g_kad.setSpacing(12)
        g_kad.setColumnStretch(0, 1)
        g_kad.setColumnStretch(1, 1)
        self._add_editable_combo(g_kad, 0, 0, "Hizmet Sınıfı", "HizmetSinifi", "kadro")
        self._add_editable_combo(g_kad, 0, 1, "Kadro Ünvanı",  "KadroUnvani",  "kadro")
        self._add_editable_combo(g_kad, 1, 0, "Görev Yeri",    "GorevYeri",    "kadro")
        self._add_editable_item( g_kad, 1, 1, "Sicil No",      "KurumSicilNo", "kadro")
        self._add_editable_date( g_kad, 2, 0, "Başlama Tarihi","MemuriyeteBaslamaTarihi","kadro")
        self._add_durum_item(    g_kad, 2, 1, self.personel_data.get("Durum"))
        right_l.addWidget(grp_kurum)

        # ── Üst satır: sol kart | sağ form ──
        form_row = QHBoxLayout()
        form_row.setSpacing(16)
        form_row.addWidget(left_grp, alignment=Qt.AlignmentFlag.AlignTop)
        form_row.addWidget(right, 1)
        content_vbox.addLayout(form_row)

        # ══════════════════════════════════════════════════════
        # EĞİTİM GRUBU — tam genişlik
        # ══════════════════════════════════════════════════════
        grp_egitim = self._create_editable_group("Eğitim Bilgileri", "egitim")
        egitim_content_widget = self._groups["egitim"]["widget"]
        eg_vbox = QVBoxLayout(egitim_content_widget)
        eg_vbox.setSpacing(6)
        eg_vbox.setContentsMargins(0, 0, 0, 0)

        # Hint satırı
        hint_row = QHBoxLayout()
        hint = QLabel("Diploma ve ek belgeler için Belgeler sekmesini kullanın.")
        hint.setProperty("color-role", "muted")
        hint.setStyleSheet("font-size: 11px;")
        btn_docs = QPushButton("Belgeler")
        btn_docs.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_docs.setProperty("style-role", "secondary")
        try:
            IconRenderer.set_button_icon(btn_docs, "upload", color=DarkTheme.TEXT_SECONDARY, size=14)
        except Exception:
            pass
        btn_docs.clicked.connect(self.open_documents.emit)
        hint_row.addWidget(hint)
        hint_row.addStretch()
        hint_row.addWidget(btn_docs)
        eg_vbox.addLayout(hint_row)

        # Başlık satırı
        def _eg_header(text, stretch):
            lbl = QLabel(text)
            lbl.setProperty("color-role", "muted")
            lbl.setStyleSheet("font-size: 11px; font-weight: 600; padding-bottom: 2px;")
            return lbl, stretch

        header_row = QHBoxLayout()
        header_row.setSpacing(8)
        header_row.setContentsMargins(0, 4, 0, 2)
        for lbl, st in [_eg_header("Okul Adı", 2), _eg_header("Bölüm / Fakülte", 2),
                        _eg_header("Mezuniyet Tarihi", 1), _eg_header("Diploma No", 2)]:
            header_row.addWidget(lbl, st)
        eg_vbox.addLayout(header_row)

        # 1. Eğitim satırı
        g_ed1 = QGridLayout()
        g_ed1.setHorizontalSpacing(8)
        g_ed1.setVerticalSpacing(0)
        g_ed1.setContentsMargins(0, 0, 0, 0)
        g_ed1.setColumnStretch(0, 2); g_ed1.setColumnStretch(1, 2)
        g_ed1.setColumnStretch(2, 1); g_ed1.setColumnStretch(3, 2)
        self._add_editable_combo_only(g_ed1, 0, 0, "MezunOlunanOkul",    "egitim")
        self._add_editable_combo_only(g_ed1, 0, 1, "MezunOlunanFakulte", "egitim")
        self._add_editable_date_only( g_ed1, 0, 2, "MezuniyetTarihi",    "egitim")
        self._add_editable_field_only(g_ed1, 0, 3, "DiplomaNo",          "egitim")
        eg_vbox.addLayout(g_ed1)

        # Ayırıcı
        sep2 = QFrame()
        sep2.setProperty("bg-role", "separator")
        sep2.setFixedHeight(1)
        eg_vbox.addWidget(sep2)

        # 2. Eğitim satırı
        g_ed2 = QGridLayout()
        g_ed2.setHorizontalSpacing(8)
        g_ed2.setVerticalSpacing(0)
        g_ed2.setContentsMargins(0, 0, 0, 0)
        g_ed2.setColumnStretch(0, 2); g_ed2.setColumnStretch(1, 2)
        g_ed2.setColumnStretch(2, 1); g_ed2.setColumnStretch(3, 2)
        self._add_editable_combo_only(g_ed2, 0, 0, "MezunOlunanOkul2",    "egitim")
        self._add_editable_combo_only(g_ed2, 0, 1, "MezunOlunanFakulte2", "egitim")
        self._add_editable_date_only( g_ed2, 0, 2, "MezuniyetTarihi2",    "egitim")
        self._add_editable_field_only(g_ed2, 0, 3, "DiplomaNo2",          "egitim")
        eg_vbox.addLayout(g_ed2)

        content_vbox.addWidget(grp_egitim)
        content_vbox.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll, 1)

    def _set_photo_preview(self, photo_ref):
        """Fotoğraf alanını yerel dosya veya Drive linkinden önizler."""
        photo_ref = str(photo_ref or "").strip()
        self.lbl_resim.setToolTip("")
        self.lbl_resim.setPixmap(QPixmap())

        if not photo_ref:
            self.lbl_resim.setText("Fotoğraf\nYok")
            logger.debug("Fotoğraf referansı boş")
            return

        # Yerel dosya ise doğrudan yükle
        if os.path.exists(photo_ref):
            try:
                pixmap = QPixmap(photo_ref)
                if not pixmap.isNull():
                    self.lbl_resim.setText("")
                    self.lbl_resim.setPixmap(
                        pixmap.scaled(
                            self.lbl_resim.size(),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
                    self.lbl_resim.setToolTip(os.path.basename(photo_ref))
                    logger.debug(f"Lokal fotoğraf yüklendi: {os.path.basename(photo_ref)}")
                    return
                else:
                    logger.warning(f"Fotoğraf dosyası geçersiz (pixmap null): {photo_ref}")
            except Exception as e:
                logger.error(f"Lokal fotoğraf yükleme hatası: {e}", exc_info=True)

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
                        except OSError as oe:
                            logger.warning(f"Geçici dosya silinemedi: {oe}")
                        
                        if not pixmap.isNull():
                            self.lbl_resim.setText("")
                            self.lbl_resim.setPixmap(
                                pixmap.scaled(
                                    self.lbl_resim.size(),
                                    Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation,
                                )
                            )
                            self.lbl_resim.setToolTip("Drive fotoğrafı")
                            logger.debug("Drive fotoğrafı yüklendi")
                            return
                        else:
                            logger.warning("Drive'dan indirilen fotoğraf geçersiz (pixmap null)")
                    else:
                        logger.warning(f"Drive download başarısız: {file_id}")
            except Exception as e:
                logger.warning(f"Drive fotoğraf önizleme hatası: {e}", exc_info=True)

        self.lbl_resim.setText("Fotoğraf\nYüklenemedi")
        self.lbl_resim.setToolTip(photo_ref[:200])
        logger.warning(f"Fotoğraf yüklenemedi: {photo_ref[:100]}")

    def _populate_combos(self):
        """Combo box'ları Sabitler ve Personel tablosundan doldur"""
        if not self._personel_svc:
            return
        
        try:
            # Cache'den gelmediyse DB'yi sorgula
            if self.sabitler_cache:
                all_sabit = self.sabitler_cache
            else:
                sabitler_sonuc = self._personel_svc.get_sabitler_repo()
                if not sabitler_sonuc.basarili or not sabitler_sonuc.veri:
                    logger.warning("Sabitler repository bulunamadı")
                    return

                sabitler_repo = sabitler_sonuc.veri
                all_sabit = sabitler_repo.get_all() or []

            def get_sabit(kod):
                """Belirli bir Sabitler kodunun değerlerini al"""
                return sorted([
                    str((r or {}).get("MenuEleman") or "").strip()
                    for r in all_sabit
                    if isinstance(r, dict)
                    and r.get("Kod") == kod
                    and str(r.get("MenuEleman") or "").strip()
                ])

            # Populate Kadro combos (Hizmet Sınıfı, Kadro Ünvanı, Görev Yeri)
            for key, kod in [("HizmetSinifi", "Hizmet_Sinifi"), 
                             ("KadroUnvani", "Kadro_Unvani"), 
                             ("GorevYeri", "Gorev_Yeri")]:
                combo = self._widgets.get(key)
                if isinstance(combo, QComboBox):
                    try:
                        current_val = combo.currentText()
                    except RuntimeError:
                        continue  # Silinmiş widget, atla
                    items = get_sabit(kod)
                    combo.clear()
                    combo.addItem("")
                    combo.addItems(items)
                    if current_val:
                        combo.setCurrentText(current_val)
                    # Text formatting'ı koru
                    apply_combo_title_case_formatting(combo)

            # Populate Eğitim combos (Okul ve Fakülte listeleri)
            personel_repo_sonuc = self._personel_svc.get_personel_repo()
            if personel_repo_sonuc.basarili and personel_repo_sonuc.veri:
                personel_repo = personel_repo_sonuc.veri
                all_personel = personel_repo.get_all() or []

                for col_key, combo_keys in [
                    (("MezunOlunanOkul", "MezunOlunanOkul2"), ("MezunOlunanOkul", "MezunOlunanOkul2")),
                    (("MezunOlunanFakulte", "MezunOlunanFakulte2"), ("MezunOlunanFakulte", "MezunOlunanFakulte2"))
                ]:
                    unique_vals = sorted(set(
                        s
                        for r in all_personel
                        if isinstance(r, dict)
                        for col in col_key
                        if (s := str(r.get(col) or "").strip())
                    ))
                    for key in combo_keys:
                        combo = self._widgets.get(key)
                        if isinstance(combo, QComboBox):
                            try:
                                current_val = combo.currentText()
                            except RuntimeError:
                                continue  # Silinmiş widget, atla
                            combo.clear()
                            combo.addItem("")
                            combo.addItems(unique_vals)
                            if current_val:
                                combo.setCurrentText(current_val)
                            # Text formatting'ı koru
                            apply_combo_title_case_formatting(combo)

            # Drive klasör ID'lerini yükle
            self._all_sabit = all_sabit
            self._drive_folders = {
                str(r.get("MenuEleman") or "").strip(): str(r.get("Aciklama") or "").strip()
                for r in all_sabit
                if isinstance(r, dict)
                and r.get("Kod") == "Sistem_DriveID"
                and str(r.get("Aciklama") or "").strip()
            }
            
            if not self.sabitler_cache and all_sabit:
                logger.info(f"Sabitler yüklendi: {len(all_sabit)} kayıt, {len(self._drive_folders)} drive klasörü")

        except Exception as e:
            logger.error(f"Combo doldurma hatası: {e}", exc_info=True)

    def _create_editable_group(self, title, group_id):
        grp = QGroupBox(title)

        vbox = QVBoxLayout(grp)
        vbox.setContentsMargins(12, 6, 12, 12)
        vbox.setSpacing(8)

        # Buton satırı — sağa hizalı, minimum yükseklik
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(4)
        header_row.addStretch()

        btn_edit   = self._create_icon_btn("edit", "Düzenle", lambda: self._toggle_edit(group_id, True))
        btn_save   = self._create_icon_btn("save", "Kaydet",  lambda: self._save_group(group_id),        visible=False)
        btn_cancel = self._create_icon_btn("x",    "İptal",   lambda: self._toggle_edit(group_id, False), visible=False)

        btn_save.setProperty("style-role", "success-filled")
        btn_cancel.setProperty("style-role", "danger")

        header_row.addWidget(btn_edit)
        header_row.addWidget(btn_save)
        header_row.addWidget(btn_cancel)
        vbox.addLayout(header_row)

        content_widget = QWidget()
        vbox.addWidget(content_widget)

        self._groups[group_id] = {
            "widget":     content_widget,
            "btn_edit":   btn_edit,
            "btn_save":   btn_save,
            "btn_cancel": btn_cancel,
            "fields":     [],
        }
        return grp

    def _create_icon_btn(self, icon_name, tooltip, callback, visible=True):
        btn = QPushButton("")
        btn.setToolTip(tooltip)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setFixedSize(30, 26)
        btn.setVisible(visible)
        IconRenderer.set_button_icon(btn, icon_name, color=DarkTheme.TEXT_SECONDARY, size=14)
        btn.setProperty("style-role", "quick-action")
        btn.clicked.connect(callback)
        return btn


    def _add_durum_item(self, layout, row, col, durum_val):
        """Durum alanı için renkli badge gösterir."""
        container = QWidget()
        l = QVBoxLayout(container)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(2)

        lbl_t = QLabel("Durum")
        lbl_t.setProperty("color-role", "muted")
        lbl_t.setStyleSheet("font-size: 11px;")
        l.addWidget(lbl_t)

        val_str = str(durum_val) if durum_val else "—"
        lbl_v = QLabel(val_str)
        lbl_v.setWordWrap(False)

        # Badge rengi
        durum_role = {
            "Aktif":   "header-durum-aktif",
            "Pasif":   "header-durum-pasif",
            "İzinli":  "header-durum-izinli",
        }.get(val_str)
        if durum_role:
            lbl_v.setProperty("style-role", durum_role)
        else:
            lbl_v.setProperty("color-role", "primary")
            lbl_v.setStyleSheet("font-size: 13px; font-weight: 500;")
        l.addWidget(lbl_v)
        l.addStretch()

        layout.addWidget(container, row, col)

    def _add_readonly_item(self, layout, row, col, label, value):
        container = QWidget()
        l = QVBoxLayout(container)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(2)

        lbl_t = QLabel(label)
        lbl_t.setProperty("color-role", "muted")
        lbl_t.setStyleSheet("font-size: 11px;")
        l.addWidget(lbl_t)

        lbl_v = QLabel(str(value) if value else "—")
        lbl_v.setProperty("color-role", "primary")
        lbl_v.setStyleSheet("font-size: 13px; font-weight: 500;")
        lbl_v.setWordWrap(True)
        l.addWidget(lbl_v)

        layout.addWidget(container, row, col)

    def _add_editable_item(self, layout, row, col, label, db_key, group_id):
        """Etiket + Input şeklinde ekler."""
        container = QWidget()
        l = QVBoxLayout(container)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(2)
        
        lbl_t = QLabel(label)
        lbl_t.setProperty("color-role", "muted")
        lbl_t.setStyleSheet("font-size: 11px;")
        l.addWidget(lbl_t)
        
        val = self.personel_data.get(db_key, "")
        inp = QLineEdit(str(val) if val else "")
        inp.setReadOnly(True)

        l.addWidget(inp)
        
        layout.addWidget(container, row, col)
        
        self._widgets[db_key] = inp
        self._groups[group_id]["fields"].append(db_key)

    def _add_editable_combo(self, layout, row, col, label, db_key, group_id):
        """Etiket + QComboBox şeklinde ekler."""
        container = QWidget()
        l = QVBoxLayout(container)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(2)
        
        lbl_t = QLabel(label)
        lbl_t.setProperty("color-role", "muted")
        lbl_t.setStyleSheet("font-size: 11px;")
        l.addWidget(lbl_t)
        
        val = self.personel_data.get(db_key, "")
        combo = QComboBox()
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        combo.addItem(str(val) if val else "")
        combo.setCurrentText(str(val) if val else "")
        combo.setEnabled(False)

        
        completer = QCompleter(self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        combo.setCompleter(completer)

        l.addWidget(combo)
        layout.addWidget(container, row, col)
        
        self._widgets[db_key] = combo
        self._groups[group_id]["fields"].append(db_key)

    def _add_editable_combo_only(self, layout, row, col, db_key, group_id):
        """Sadece QComboBox ekler (Eğitim tablosu için)."""
        val = self.personel_data.get(db_key, "")
        combo = QComboBox()
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        combo.setPlaceholderText("-")
        combo.addItem(str(val) if val else "")
        combo.setCurrentText(str(val) if val else "")
        combo.setEnabled(False)

        completer = QCompleter(self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        combo.setCompleter(completer)
        
        layout.addWidget(combo, row, col)
        
        self._widgets[db_key] = combo
        self._groups[group_id]["fields"].append(db_key)

    def _add_editable_field_only(self, layout, row, col, db_key, group_id):
        """Sadece Input ekler (Diploma alanı için - sadece görüntüleme)."""
        val = self.personel_data.get(db_key, "")
        inp = QLineEdit(str(val) if val else "")
        inp.setReadOnly(True)
        inp.setPlaceholderText("-")

        # Container: input + görüntüle butonu
        container = QWidget()
        h = QHBoxLayout(container)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        h.addWidget(inp, 1)

        # Görüntüle butonu (mevcut diploma varsa aç)
        view_btn = QPushButton("Görüntüle")
        #view_btn.setFixedSize(80, 22)
        view_btn.setEnabled(False)
        view_btn.setToolTip("Mevcut diplomayı görüntüle")
        view_btn.clicked.connect(lambda _checked, k=db_key: self._on_view_diploma(k))
        h.addWidget(view_btn)

        layout.addWidget(container, row, col)

        self._widgets[db_key] = inp
        self._view_buttons[db_key] = view_btn
        self._groups[group_id]["fields"].append(db_key)

        # İlk durum için gösterimi güncelle
        self._refresh_diploma_display(db_key)

    def _add_editable_date(self, layout, row, col, label, db_key, group_id):
        """Etiket + QDateEdit şeklinde ekler."""
        container = QWidget()
        l = QVBoxLayout(container)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(2)
        
        lbl_t = QLabel(label)
        lbl_t.setProperty("color-role", "muted")
        lbl_t.setStyleSheet("font-size: 11px;")
        l.addWidget(lbl_t)
        
        val = self.personel_data.get(db_key, "")
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDisplayFormat("dd.MM.yyyy")
        
        d = QDate.fromString(str(val), "yyyy-MM-dd")
        date_edit.setDate(d if d.isValid() else QDate.currentDate())

        date_edit.setEnabled(False)

        l.addWidget(date_edit)
        layout.addWidget(container, row, col)
        
        self._widgets[db_key] = date_edit
        self._groups[group_id]["fields"].append(db_key)

    def _add_editable_date_only(self, layout, row, col, db_key, group_id):
        """Sadece QDateEdit ekler (Eğitim tablosu için)."""
        val = self.personel_data.get(db_key, "")
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDisplayFormat("dd.MM.yyyy")

        d = QDate.fromString(str(val), "yyyy-MM-dd")
        date_edit.setDate(d if d.isValid() else QDate.currentDate())

        date_edit.setEnabled(False)
        
        layout.addWidget(date_edit, row, col)
        
        self._widgets[db_key] = date_edit
        self._groups[group_id]["fields"].append(db_key)

    def _toggle_edit(self, group_id, edit_mode):
        grp = self._groups[group_id]
        grp["btn_edit"].setVisible(not edit_mode)
        grp["btn_save"].setVisible(edit_mode)
        grp["btn_cancel"].setVisible(edit_mode)
        
        # Edit / read modu: setProperty ile QSS role sistemi kullanılır
        
        for key in grp["fields"]:
            widget = self._widgets[key]
            if isinstance(widget, QLineEdit):
                widget.setReadOnly(not edit_mode)
            elif isinstance(widget, QComboBox):
                widget.setEnabled(edit_mode)
            elif isinstance(widget, QDateEdit):
                widget.setEnabled(edit_mode)
            
            # İptal edilirse eski veriyi geri yükle
            if not edit_mode:
                val = self.personel_data.get(key, "")
                if isinstance(widget, QLineEdit):
                    widget.setText(str(val) if val else "")
                elif isinstance(widget, QComboBox):
                    widget.setCurrentText(str(val) if val else "")
                elif isinstance(widget, QDateEdit):
                    d = QDate.fromString(str(val), "yyyy-MM-dd")
                    widget.setDate(d if d.isValid() else QDate.currentDate())
            
            # Diploma görüntüleme butonunu güncelle (dosya varsa etkin)
            if key in self._view_buttons:
                try:
                    # "Aç" butonu: dosya varsa tıklanabilir olsun (edit modu fark etmiyor)
                    has_file = bool(self.personel_data.get({
                        'DiplomaNo': 'Diploma1',
                        'DiplomaNo2': 'Diploma2'
                    }.get(key)) or self.personel_data.get(f"{key}_file"))
                    self._view_buttons[key].setEnabled(has_file)
                except Exception:
                    pass

    def _recalc_izin_if_needed(self, group_id: str, tc: str, update_data: dict):
        """
        Kadro grubu kaydedilince MemuriyeteBaslamaTarihi değişmiş olabilir.
        İzin hak edişini yeniden hesapla ve Izin_Bilgi'yi güncelle.
        Diğer gruplarda çağrılsa da sessizce çıkar.
        """
        if group_id != "kadro":
            return
        baslama = str(update_data.get("MemuriyeteBaslamaTarihi", "")).strip()
        if not baslama:
            logger.debug("_recalc_izin: MemuriyeteBaslamaTarihi boş, atlandı.")
            return
        if not self._izin_svc:
            logger.warning("_recalc_izin: izin_svc yok, atlandı.")
            return
        try:
            ad_soyad = str(self.personel_data.get("AdSoyad", "")).strip()
            ok = self._izin_svc.create_or_update_izin_bilgi(
                tc=tc,
                ad_soyad=ad_soyad,
                baslama_tarihi=baslama,
            )
            if ok:
                logger.info(f"İzin hak edişi yeniden hesaplandı: {tc} | BaslamaTarihi={baslama}")
            else:
                logger.warning(f"İzin hak ediş güncellenemedi: {tc}")
        except Exception as e:
            logger.error(f"_recalc_izin hatası: {e}")

    def _save_group(self, group_id):
        """Grup verilerini kaydet"""
        if not self._personel_svc:
            logger.error("Service yok, veri kaydı başarısız")
            hata_goster(self, "Veritabanı bağlantısı yoktur.")
            return

        grp = self._groups[group_id]
        update_data = {}
        
        try:
            # Verileri topla ve valide et
            for key in grp["fields"]:
                widget = self._widgets[key]
                val = ""
                
                if isinstance(widget, QLineEdit):
                    val = widget.text().strip()
                    # Zorunlu alanları kontrol et
                    if not val and key in ["Ad", "Soyad", "CepTel", "Email"]:
                        raise ValueError(f"{key} alanı boş bırakılamaz.")
                elif isinstance(widget, QComboBox):
                    val = widget.currentText().strip()
                elif isinstance(widget, QDateEdit):
                    val = widget.date().toString("yyyy-MM-dd")
                    # Geçerli tarih kontrolü
                    if not widget.date().isValid():
                        raise ValueError(f"Geçersiz tarih formatı ({key}).")
                
                update_data[key] = val
        except ValueError as e:
            logger.warning(f"Veri validasyon hatası ({group_id}): {e}")
            uyari_goster(self, str(e))
            return
            
        try:
            # Service üzerinden Personel repository'sini al
            repo_sonuc = self._personel_svc.get_personel_repo()
            if not repo_sonuc.basarili or not repo_sonuc.veri:
                raise RuntimeError("Personel repository bulunamadı.")
            repo = repo_sonuc.veri

            tc = self.personel_data.get("KimlikNo")
            if not tc:
                raise ValueError("TC Kimlik No geliştirici verilerinde bulunamadı.")
            
            logger.debug(f"Personel güncelleme başlatıldı: {tc} (grup: {group_id})")

            # Dosya yükleme adımı: sadece fotoğraf yükleme burada yapılır
            # Diploma yüklemeleri Belgeler sayfasında yapılır
            self._file_paths = {}
            foto = self.personel_data.get("Resim", "")
            if foto and os.path.exists(str(foto)):
                self._file_paths["Resim"] = foto

            # Eğer yükleme gerekmiyorsa doğrudan kaydet
            if not self._file_paths:
                repo.update(tc, update_data)
                self.personel_data.update(update_data)
                # Kadro grubu kaydedilince izin hak edişini yeniden hesapla
                self._recalc_izin_if_needed(group_id, tc, update_data)
                self._toggle_edit(group_id, False)
                logger.info(f"Personel başarıyla güncellendi: {tc} ({group_id})")
                bilgi_goster(self, "Veriler kaydedildi.")
                return

            # Upload callback sonrası DB güncellemesi
            def _after_upload():
                for drive_key, link in self._drive_links.items():
                    if drive_key == 'Resim':
                        update_data['Resim'] = link
                
                # Lokal dosyalar da kaydet (Drive'a yüklenen dosyalar veya lokal kalanlar)
                if 'Resim' in self._file_paths:
                    if 'Resim' not in self._drive_links:  # Drive'a yüklenmedi
                        local_path = self._save_file_locally(self._file_paths['Resim'], tc, 'Resim')
                        if local_path:
                            update_data['Resim'] = local_path

                repo.update(tc, update_data)
                self.personel_data.update(update_data)
                self._recalc_izin_if_needed(group_id, tc, update_data)
                self._toggle_edit(group_id, False)
                logger.info(f"Personel (dosya dahil) başarıyla güncellendi: {tc} ({group_id})")
                bilgi_goster(self, "Veriler ve dosyalar kaydedildi.")

            self._upload_files_to_drive(tc, _after_upload)

        except ValueError as ve:
            logger.warning(f"Veri hatası (kayıt): {ve}")
            uyari_goster(self, str(ve))
        except RuntimeError as re:
            logger.error(f"İşlem hatası: {re}")
            hata_goster(self, str(re))
        except Exception as e:
            logger.error(f"Beklenmeyen güncelleme hatası ({group_id}): {e}", exc_info=True)
            hata_goster(self, "Güncelleme başarısız:\nAyrıntılar için logları kontrol edin.")

    def _on_photo_upload(self):
        """Fotoğraf seçim ve yükleme işlemini tetikler."""
        try:
            path, _ = QFileDialog.getOpenFileName(self, "Fotoğraf Seç", "", "Görüntü Dosyaları (*.png *.jpg *.jpeg *.bmp);;Tüm Dosyalar (*)")
            if not path:
                logger.debug("Fotoğraf seçimi iptal edildi")
                return
            
            # Önizlemeyi güncelle
            self._set_photo_preview(path)
            self.personel_data["Resim"] = path
            logger.debug(f"Fotoğraf seçildi: {os.path.basename(path)}")
            
            # Resmi otomatik olarak Drive'a yükle ve veritabanına kaydet
            if self.db:
                self._save_photo_to_db(path)
        except Exception as e:
            logger.warning(f"Fotoğraf yüklenemedi: {e}", exc_info=True)
            uyari_goster(self, f"İşlem gerçekleştirilemedi:\n{str(e)}")

    def _save_photo_to_db(self, photo_path):
        """Resmi Drive'a yükleyip veritabanına kaydeder."""
        try:
            if not self._personel_svc:
                raise RuntimeError("Service başlatılmamış, fotoğraf kaydedilemez")
            
            repo_sonuc = self._personel_svc.get_personel_repo()
            if not repo_sonuc.basarili or not repo_sonuc.veri:
                raise RuntimeError("Personel repository bulunamadı")
            repo = repo_sonuc.veri
            
            tc = self.personel_data.get("KimlikNo")
            if not tc:
                raise ValueError("TC Kimlik No bulunamadı")
            
            logger.debug(f"Fotoğraf kaydı başlatıldı: {tc}")
            
            # Resmi Drive'a yükle
            self._file_paths = {"Resim": photo_path}
            self._drive_links = {}
            
            def _after_upload():
                try:
                    # Drive linki veritabanına kaydet
                    if "Resim" in self._drive_links:
                        drive_link = self._drive_links["Resim"]
                        repo.update(tc, {"Resim": drive_link})
                        self.personel_data["Resim"] = drive_link
                        logger.info(f"Fotoğraf Drive'a yüklendi ve DB güncellendi: {tc}")
                        bilgi_goster(self, "Fotoğraf başarıyla güncellendi.")
                    else:
                        # Drive yok, lokal dosyayı kaydet
                        local_path = self._save_file_locally(photo_path, tc, "Resim")
                        if local_path:
                            repo.update(tc, {"Resim": local_path})
                            self.personel_data["Resim"] = local_path
                            logger.info(f"Fotoğraf lokal klasöre kaydedildi: {local_path}")
                            bilgi_goster(self, "Fotoğraf güncellendi (lokal kayıt).")
                        else:
                            raise RuntimeError("Dosya kaydedilemedi, lokal klasör oluşturulamadı")
                except Exception as e:
                    logger.error(f"Upload callback hatası: {e}", exc_info=True)
                    hata_goster(self, f"Fotoğraf kaydedilemedi:\n{str(e)}")
            
            self._upload_files_to_drive(tc, _after_upload)
            
        except ValueError as ve:
            logger.warning(f"Veri hatası (fotoğraf): {ve}")
            uyari_goster(self, str(ve))
        except RuntimeError as re:
            logger.error(f"İşlem hatası (fotoğraf): {re}")
            hata_goster(self, str(re))
        except Exception as e:
            logger.error(f"Fotoğraf kaydetme hatası: {e}", exc_info=True)
            hata_goster(self, "Fotoğraf kaydedilemedi:\nAyrıntılar için logları kontrol edin.")

    def _save_file_locally(self, source_file_path, tc_no, file_type):
        """
        Dosyayı lokal klasöre kaydeder.
        Cloud adapter'ın offline_folder_name yapısı ile uyumlu.
        Example: data/offline_uploads/Personel_Resim/TC_Resim.jpg
        """
        try:
            from core.paths import BASE_DIR
            
            if not os.path.exists(source_file_path):
                raise FileNotFoundError(f"Kaynak dosya bulunamadı: {source_file_path}")
            
            # Dosya türüne göre klasör eşlemesi
            file_class_map = {
                "Resim": "Personel_Resim",
                "Diploma1": "Personel_Diploma",
                "Diploma2": "Personel_Diploma",
            }
            
            folder_name = file_class_map.get(file_type, "")
            if not folder_name:
                raise ValueError(f"Bilinmeyen dosya türü: {file_type}")
            
            # Lokal klasör oluştur (offline_uploads direktinin altında, cloud adapter ile uyumlu)
            local_base = os.path.join(BASE_DIR, "data", "offline_uploads", folder_name)
            os.makedirs(local_base, exist_ok=True)
            
            # Hedef dosya adı: TC_Resim.ext veya TC_Diploma1.ext
            ext = os.path.splitext(source_file_path)[1]
            dest_filename = f"{tc_no}_{file_type}{ext}"
            dest_path = os.path.join(local_base, dest_filename)
            
            # Dosyayı kopyala
            import shutil
            shutil.copy2(source_file_path, dest_path)
            logger.info(f"Dosya lokal klasöre kaydedildi: {dest_path}")
            
            return dest_path
            
        except FileNotFoundError as fe:
            logger.warning(f"Dosya bulunamadı (lokal kayıt): {fe}")
            return None
        except ValueError as ve:
            logger.warning(f"Geçersiz parametre (lokal kayıt): {ve}")
            return None
        except Exception as e:
            logger.error(f"Lokal dosya kaydetme hatası: {e}", exc_info=True)
            return None

    def _upload_files_to_drive(self, tc_no, callback):
        """Seçili dosyaları DokumanService ile yükler, bitince callback çağırır (sadece fotoğraf)."""
        
        # Dosya map: self._file_paths örn {'Resim': path}
        if not getattr(self, "_file_paths", None):
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
        self._upload_errors = []
        self._drive_links = {}
        self._upload_meta = {}

        for file_key, file_path in list(self._file_paths.items()):
            if file_key not in upload_map:
                continue
            map_info = upload_map[file_key]

            ext = os.path.splitext(file_path)[1]
            # Fotoğraf dosya adı: TCKimlik_Resim.ext
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

    def _on_upload_finished(self, alan_adi, sonuc):
        """Tek dosya yükleme tamamlandı (sadece fotoğraf)."""
        try:
            # alan_adi: db field like 'Resim'
            kayit_linki = sonuc.get("drive_link") or sonuc.get("local_path") or ""
            self._drive_links[alan_adi] = kayit_linki
            logger.info(f"Dosya yükleme başarılı: {alan_adi} → {os.path.basename(kayit_linki) if kayit_linki else 'N/A'}")
            self._pending_uploads -= 1
            
            # UI'ı güncelle: personel_data'ya ekle
            if alan_adi == 'Resim':
                self.personel_data['Resim'] = kayit_linki
            
            if self._pending_uploads <= 0:
                logger.debug(f"Tüm dosyalar yüklendi ({len(self._drive_links)} kayıt)")
                self._finalize_uploads()
                
        except Exception as e:
            logger.error(f"Upload finished callback hatası: {e}", exc_info=True)

    def _refresh_diploma_display(self, db_key):
        """Diploma görüntüle butonunun durumunu dosya mevcudiyetine göre güncelle."""
        try:
            # db_key örnek: 'DiplomaNo' veya 'DiplomaNo2'
            # Drive alanlarına eşleme: DiplomaNo → Diploma1, DiplomaNo2 → Diploma2
            mapping = {'DiplomaNo': 'Diploma1', 'DiplomaNo2': 'Diploma2'}
            drive_key = mapping.get(db_key, None)
            
            view_btn = self._view_buttons.get(db_key)
            if not view_btn:
                return
            
            # Kaydedilmiş drive linki tercih et
            link = ''
            if drive_key and self.personel_data.get(drive_key):
                link = self.personel_data.get(drive_key)
            # Yedek olarak staged dosya
            elif self.personel_data.get(f"{db_key}_file"):
                link = self.personel_data.get(f"{db_key}_file")

            # "Aç" butonu sadece dosya varsa tıklanabilir
            view_btn.setEnabled(bool(link))
            logger.debug(f"Diploma görüntüleme güncellendi: {db_key} → {'etkin' if link else 'kapalı'}")
            
        except Exception as e:
            logger.warning(f"Diploma display refresh hatası: {e}", exc_info=True)

    def _on_view_diploma(self, db_key):
        """Diploma dosyasını aç: web linki veya lokal dosya."""
        try:
            mapping = {'DiplomaNo': 'Diploma1', 'DiplomaNo2': 'Diploma2'}
            drive_key = mapping.get(db_key, None)
            
            link = None
            if drive_key and self.personel_data.get(drive_key):
                link = self.personel_data.get(drive_key)
            elif self.personel_data.get(f"{db_key}_file"):
                link = self.personel_data.get(f"{db_key}_file")
            
            if not link:
                logger.warning(f"Diploma linki bulunamadı: {db_key}")
                return
            
            import webbrowser
            if link.startswith('http'):
                webbrowser.open(link)
                logger.debug(f"Web tarayıcısında diploma açıldı: {db_key}")
            else:
                # Lokal dosya
                try:
                    os.startfile(link)
                    logger.debug(f"Lokal dosya açıldı: {os.path.basename(link)}")
                except Exception:
                    webbrowser.open('file://' + os.path.abspath(link))
                    logger.debug(f"Dosya tarayıcısı ile açıldı: {os.path.basename(link)}")
        except Exception as e:
            logger.error(f"Diploma görüntülenemiyor ({db_key}): {e}", exc_info=True)
            uyari_goster(self, f"Diploma dosyası açılamadı:\n{str(e)}")

    def _on_upload_error(self, alan_adi, hata):
        """Tek dosya yükleme hatası."""
        self._upload_errors.append(f"{alan_adi}: {hata}")
        logger.error(f"Drive yükleme hatası: {alan_adi} → {hata}")
        self._pending_uploads -= 1
        
        if self._pending_uploads <= 0:
            logger.warning(f"Upload tamamlandı (hatalı): {len(self._upload_errors)} dosya yüklenemedi")
            self._finalize_uploads()

    def _finalize_uploads(self):
        """Tüm yüklemeler tamamlandığında çağrılır."""
        try:
            # Temizle
            self._upload_workers.clear()

            if self._upload_errors:
                logger.warning(f"Upload tamamlandı (hatalı): {len(self._upload_errors)} dosya yüklenemedi")
                uyari_goster(
                    self,
                    f"Bazı dosyalar yüklenemedi ({len(self._upload_errors)} hata):\n" + "\n".join(self._upload_errors)
                )
            else:
                logger.debug("Tüm dosyalar başarıyla yüklendi")

            if hasattr(self, "_upload_callback") and callable(self._upload_callback):
                try:
                    self._upload_callback()
                except Exception as e:
                    logger.error(f"Upload callback hatası: {e}", exc_info=True)
                    hata_goster(self, f"İşlem tamamlanamadı:\n{str(e)}")
        except Exception as e:
            logger.error(f"Finalize uploads hatası: {e}", exc_info=True)

    def _fmt_date(self, val):
        """Tarihi YYYY-MM-DD formatından DD.MM.YYYY formatına çevir."""
        if not val:
            return "-"
        try:
            from datetime import datetime
            if "-" in str(val):
                d = datetime.strptime(str(val), "%Y-%m-%d")
                return d.strftime("%d.%m.%Y")
        except ValueError as ve:
            logger.warning(f"Tarih formatı hatası: {val} → {ve}")
        except Exception as e:
            logger.error(f"Tarih formatı dönüşüm hatası: {e}", exc_info=True)
        return str(val)

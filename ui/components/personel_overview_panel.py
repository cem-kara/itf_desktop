# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout, 
    QGroupBox, QScrollArea, QLineEdit, QPushButton, QMessageBox, QComboBox,
    QCompleter, QDateEdit, QFileDialog
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QCursor, QPixmap
from core.logger import logger
from ui.theme_manager import ThemeManager
import os
import tempfile

S = ThemeManager.get_all_component_styles()

class PersonelOverviewPanel(QWidget):
    """
    Personel Merkez ekranı için 'Genel Bakış' sekmesi içeriği.
    Özet metrikleri ve düzenlenebilir personel bilgilerini gösterir.
    """
    def __init__(self, ozet_data, db=None, parent=None):
        super().__init__(parent)
        self.data = ozet_data or {}
        self.db = db
        self.personel_data = self.data.get("personel", {})
        self._widgets = {}  # Alan adı -> QLineEdit
        self._upload_buttons = {}  # Alan adı -> QPushButton (diploma gibi)
        self._groups = {}   # Grup adı -> (layout, edit_btn, save_btn, cancel_btn)
        # Dosya upload yönetimi (personel_ekle ile uyumlu)
        self._file_paths = {}          # {'Resim': local_path, 'Diploma1': local_path, ...}
        self._drive_links = {}         # {'Resim': drive_link, 'Diploma1': link, ...}
        self._drive_folders = {}       # {'Personel_Resim': folder_id, ...}
        self._upload_workers = []
        self._pending_uploads = 0
        self._upload_errors = []
        self._view_buttons = {}     # db_key -> QPushButton
        self._setup_ui()
        self._populate_combos()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll Area (İçerik uzayabileceği için)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        if not self.personel_data:
            layout.addWidget(QLabel("Personel verisi bulunamadı."))
            scroll.setWidget(content)
            main_layout.addWidget(scroll)
            return

        # ── 1. Kimlik Bilgileri (Header Kısmı - Düzenlenemez) ──
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 32, 44, 0.4);
                border-radius: 8px;
            }
        """)
        h_main_layout = QHBoxLayout(header_frame)
        h_main_layout.setContentsMargins(15, 15, 15, 15)
        h_main_layout.setSpacing(20)

        # Sol: Fotoğraf + yükleme butonu
        self.lbl_resim = QLabel()
        self.lbl_resim.setFixedSize(80, 100)
        self.lbl_resim.setAlignment(Qt.AlignCenter)
        self.lbl_resim.setStyleSheet("border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; background: rgba(0,0,0,0.2); color: #666;")

        photo_v = QVBoxLayout()
        photo_v_widget = QWidget()
        photo_v_widget.setLayout(photo_v)
        photo_v.addWidget(self.lbl_resim, 0, Qt.AlignHCenter)

        self._photo_upload_btn = QPushButton("📸Resim Yükle")
        self._photo_upload_btn.setFixedSize(90, 26)
        self._photo_upload_btn.setStyleSheet("background: rgba(59,130,246,0.12); border-radius:4px;")
        self._photo_upload_btn.clicked.connect(self._on_photo_upload)
        photo_v.addWidget(self._photo_upload_btn, 0, Qt.AlignHCenter)

        h_main_layout.addWidget(photo_v_widget)

        # Sağ: Bilgiler
        info_widget = QWidget()
        info_widget.setStyleSheet("background:transparent;")
        h_layout = QGridLayout(info_widget)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setVerticalSpacing(15)
        h_layout.setHorizontalSpacing(20)

        # Başlık
        lbl_baslik = QLabel("KİMLİK BİLGİLERİ")
        lbl_baslik.setStyleSheet("color: #6bd3ff; font-weight: bold; font-size: 12px; letter-spacing: 1px;")
        h_layout.addWidget(lbl_baslik, 0, 0, 1, 2)

        # Bilgiler
        self._add_readonly_item(h_layout, 1, 0, "TC Kimlik No", self.personel_data.get("KimlikNo"))
        self._add_readonly_item(h_layout, 1, 1, "Ad Soyad", self.personel_data.get("AdSoyad"))
        self._add_readonly_item(h_layout, 2, 0, "Doğum Yeri", self.personel_data.get("DogumYeri"))
        self._add_readonly_item(h_layout, 2, 1, "Doğum Tarihi", self._fmt_date(self.personel_data.get("DogumTarihi")))
        
        h_main_layout.addWidget(info_widget, 1)

        layout.addWidget(header_frame)
        
        self._set_photo_preview(self.personel_data.get("Resim"))

        # Fotoğraf yükle butonunu yalnızca düzenleme sırasında etkinleştirmek istiyorsanız,
        # grup düzenleme mantığına bağlayabilirsiniz. Şu an varsayılan olarak aktif bırakıyoruz.

        # ── 2. İletişim ve Kadro (Yan Yana) ──
        mid_layout = QHBoxLayout()
        mid_layout.setSpacing(20)

        # İletişim Grubu
        grp_iletisim = self._create_editable_group("📞 İletişim Bilgileri", "iletisim")
        iletisim_content_widget = self._groups["iletisim"]["widget"]
        g2 = QGridLayout(iletisim_content_widget)
        g2.setSpacing(12)
        self._add_editable_item(g2, 0, 0, "Cep Telefonu", "CepTelefonu", "iletisim")
        self._add_editable_item(g2, 1, 0, "E-posta", "Eposta", "iletisim")
        mid_layout.addWidget(grp_iletisim)

        # Kadro Grubu
        grp_kurum = self._create_editable_group("🏛️ Kadro ve Kurumsal Bilgiler", "kadro")
        kadro_content_widget = self._groups["kadro"]["widget"]
        g3 = QGridLayout(kadro_content_widget)
        g3.setSpacing(12)
        self._add_editable_combo(g3, 0, 0, "Hizmet Sınıfı", "HizmetSinifi", "kadro")
        self._add_editable_combo(g3, 0, 1, "Kadro Ünvanı", "KadroUnvani", "kadro")
        self._add_editable_item(g3, 1, 1, "Sicil No", "KurumSicilNo", "kadro")
        self._add_editable_combo(g3, 1, 0, "Görev Yeri", "GorevYeri", "kadro")
        self._add_editable_date(g3, 2, 0, "Başlama Tarihi", "MemuriyeteBaslamaTarihi", "kadro")
        self._add_readonly_item(g3, 2, 1, "Durum", self.personel_data.get("Durum")) # Durum buradan değişmesin
        mid_layout.addWidget(grp_kurum)

        layout.addLayout(mid_layout)

        # ── 3. Eğitim Bilgileri (4 Kolonlu Grid) ──
        grp_egitim = self._create_editable_group("🎓 Eğitim Bilgileri", "egitim")
        egitim_content_widget = self._groups["egitim"]["widget"]
        g4 = QGridLayout(egitim_content_widget)
        g4.setSpacing(15)
        
        # Başlıklar
        headers = ["Okul Adı", "Bölüm / Fakülte", "Mezuniyet Tarihi", "Diploma No"]
        for i, h in enumerate(headers):
            lbl = QLabel(h)
            lbl.setStyleSheet("color: #8b8fa3; font-size: 11px; font-weight: bold;")
            g4.addWidget(lbl, 0, i)

        # 1. Okul
        self._add_editable_combo_only(g4, 1, 0, "MezunOlunanOkul", "egitim")
        self._add_editable_combo_only(g4, 1, 1, "MezunOlunanFakulte", "egitim")
        self._add_editable_date_only(g4, 1, 2, "MezuniyetTarihi", "egitim")
        self._add_editable_field_only(g4, 1, 3, "DiplomaNo", "egitim")

        # 2. Okul
        self._add_editable_combo_only(g4, 2, 0, "MezunOlunanOkul2", "egitim")
        self._add_editable_combo_only(g4, 2, 1, "MezunOlunanFakulte2", "egitim")
        self._add_editable_date_only(g4, 2, 2, "MezuniyetTarihi2", "egitim")
        self._add_editable_field_only(g4, 2, 3, "DiplomaNo2", "egitim")
        
        layout.addWidget(grp_egitim)

        layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _set_photo_preview(self, photo_ref):
        """Fotoğraf alanını yerel dosya veya Drive linkinden önizler."""
        photo_ref = str(photo_ref or "").strip()
        self.lbl_resim.setToolTip("")
        self.lbl_resim.setPixmap(QPixmap())

        if not photo_ref:
            self.lbl_resim.setText("Fotoğraf\nYok")
            return

        # Yerel dosya ise doğrudan yükle
        if os.path.exists(photo_ref):
            pixmap = QPixmap(photo_ref)
            if not pixmap.isNull():
                self.lbl_resim.setText("")
                self.lbl_resim.setPixmap(
                    pixmap.scaled(self.lbl_resim.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
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
                                pixmap.scaled(self.lbl_resim.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            )
                            self.lbl_resim.setToolTip("Drive fotoğrafı")
                            return
            except Exception as e:
                logger.warning(f"Fotoğraf önizleme yüklenemedi: {e}")

        self.lbl_resim.setText("Fotoğraf\nYüklenemedi")
        self.lbl_resim.setToolTip(photo_ref[:200])

    def _populate_combos(self):
        if not self.db:
            return
        try:
            from database.repository_registry import RepositoryRegistry
            registry = RepositoryRegistry(self.db)
            sabitler_repo = registry.get("Sabitler")
            all_sabit = sabitler_repo.get_all()

            def get_sabit(kod):
                return sorted([
                    str(r.get("MenuEleman", "")).strip()
                    for r in all_sabit
                    if r.get("Kod") == kod and r.get("MenuEleman", "").strip()
                ])

            # Populate Kadro combos
            for key, kod in [("HizmetSinifi", "Hizmet_Sinifi"), 
                             ("KadroUnvani", "Kadro_Unvani"), 
                             ("GorevYeri", "Gorev_Yeri")]:
                combo = self._widgets.get(key)
                if isinstance(combo, QComboBox):
                    current_val = combo.currentText()
                    items = get_sabit(kod)
                    combo.clear()
                    combo.addItem("")
                    combo.addItems(items)
                    combo.setCurrentText(current_val)
                    if combo.completer():
                        combo.completer().setModel(combo.model())

            # Populate Egitim combos
            personel_repo = registry.get("Personel")
            all_personel = personel_repo.get_all()

            for col_key, combo_keys in [
                (("MezunOlunanOkul", "MezunOlunanOkul2"), ("MezunOlunanOkul", "MezunOlunanOkul2")),
                (("MezunOlunanFakulte", "MezunOlunanFakulte2"), ("MezunOlunanFakulte", "MezunOlunanFakulte2"))
            ]:
                unique_vals = sorted(set(
                    s for r in all_personel for col in col_key if (s := str(r.get(col, "")).strip())
                ))
                for key in combo_keys:
                    combo = self._widgets.get(key)
                    if isinstance(combo, QComboBox):
                        current_val = combo.currentText()
                        combo.clear()
                        combo.addItem("")
                        combo.addItems(unique_vals)
                        combo.setCurrentText(current_val)
                        if combo.completer():
                            combo.completer().setModel(combo.model())

        except Exception as e:
            logger.error(f"PersonelOverviewPanel combo doldurma hatası: {e}")

    def _create_editable_group(self, title, group_id):
        grp = QGroupBox()
        grp.setStyleSheet("""
            QGroupBox {
                background-color: rgba(30, 32, 44, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                margin-top: 24px;
                font-weight: bold;
                color: #e0e2ea;
            }
        """)
        
        # Başlık ve Butonlar için Layout
        # QGroupBox layout'u yerine içine bir layout koyup en üste butonları ekliyoruz
        vbox = QVBoxLayout(grp)
        vbox.setContentsMargins(10, 10, 10, 10)
        
        # Header Satırı (Başlık + Butonlar)
        header_row = QHBoxLayout()
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #6bd3ff; font-weight: bold; font-size: 13px;")
        header_row.addWidget(lbl_title)
        header_row.addStretch()

        # Butonlar
        btn_edit = self._create_icon_btn("✏️", "Düzenle", lambda: self._toggle_edit(group_id, True))
        btn_save = self._create_icon_btn("💾", "Kaydet", lambda: self._save_group(group_id), visible=False)
        btn_cancel = self._create_icon_btn("✕", "İptal", lambda: self._toggle_edit(group_id, False), visible=False)
        
        # Stil özelleştirme
        btn_save.setStyleSheet("background: #2ea04f; color: white; border-radius: 4px; padding: 4px 8px;")
        btn_cancel.setStyleSheet("background: #d73a49; color: white; border-radius: 4px; padding: 4px 8px;")

        header_row.addWidget(btn_edit)
        header_row.addWidget(btn_save)
        header_row.addWidget(btn_cancel)
        
        vbox.addLayout(header_row)
        
        # İçerik için placeholder widget (Grid layout buna eklenecek)
        content_widget = QWidget()
        vbox.addWidget(content_widget)
        
        # Referansları sakla
        self._groups[group_id] = {
            "widget": content_widget,
            "btn_edit": btn_edit,
            "btn_save": btn_save,
            "btn_cancel": btn_cancel,
            "fields": [] # Bu gruba ait field key'leri
        }
        
        return grp

    def _create_icon_btn(self, text, tooltip, callback, visible=True):
        btn = QPushButton(text)
        btn.setToolTip(tooltip)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.setFixedSize(30, 26)
        btn.setVisible(visible)
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.1); 
                border: none; border-radius: 4px; color: #ccc;
            }
            QPushButton:hover { background: rgba(255,255,255,0.2); color: white; }
        """)
        btn.clicked.connect(callback)
        return btn

    def _add_readonly_item(self, layout, row, col, label, value):
        container = QWidget()
        l = QVBoxLayout(container)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(2)
        
        lbl_t = QLabel(label)
        lbl_t.setStyleSheet("color: #8b8fa3; font-size: 11px;")
        l.addWidget(lbl_t)
        
        val_str = str(value) if value else "-"
        lbl_v = QLabel(val_str)
        lbl_v.setStyleSheet("color: #e0e2ea; font-size: 13px; font-weight: 500;")
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
        lbl_t.setStyleSheet("color: #8b8fa3; font-size: 11px;")
        l.addWidget(lbl_t)
        
        val = self.personel_data.get(db_key, "")
        inp = QLineEdit(str(val) if val else "")
        inp.setReadOnly(True)
        inp.setStyleSheet("background: transparent; border: none; color: #e0e2ea; font-size: 13px; font-weight: 500;")
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
        lbl_t.setStyleSheet("color: #8b8fa3; font-size: 11px;")
        l.addWidget(lbl_t)
        
        val = self.personel_data.get(db_key, "")
        combo = QComboBox()
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.NoInsert)
        combo.addItem(str(val) if val else "")
        combo.setCurrentText(str(val) if val else "")
        combo.setEnabled(False)
        combo.setStyleSheet("background: transparent; border: none; color: #e0e2ea; font-size: 13px; font-weight: 500; padding: 4px;")
        
        completer = QCompleter(self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
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
        combo.setInsertPolicy(QComboBox.NoInsert)
        combo.setPlaceholderText("-")
        combo.addItem(str(val) if val else "")
        combo.setCurrentText(str(val) if val else "")
        combo.setEnabled(False)
        combo.setStyleSheet("background: transparent; border: none; color: #e0e2ea; font-size: 13px; padding: 4px;")

        completer = QCompleter(self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        combo.setCompleter(completer)
        
        layout.addWidget(combo, row, col)
        
        self._widgets[db_key] = combo
        self._groups[group_id]["fields"].append(db_key)

    def _add_editable_field_only(self, layout, row, col, db_key, group_id):
        """Sadece Input ekler (Eğitim tablosu için)."""
        val = self.personel_data.get(db_key, "")
        inp = QLineEdit(str(val) if val else "")
        inp.setReadOnly(True)
        inp.setPlaceholderText("-")
        inp.setStyleSheet("background: transparent; border: none; color: #e0e2ea; font-size: 13px;")

        # Container: input + upload button (diploma için)
        container = QWidget()
        h = QHBoxLayout(container)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        h.addWidget(inp, 1)

        upload_btn = QPushButton("Yükle")
        upload_btn.setFixedSize(70, 26)
        upload_btn.setEnabled(False)  # yalnızca edit modda etkin olacak
        upload_btn.setStyleSheet("background: rgba(255,255,255,0.04); border-radius:4px;")
        upload_btn.clicked.connect(lambda _checked, k=db_key: self._on_upload_diploma(k))
        h.addWidget(upload_btn)

        # Görüntüle butonu (edit modda da her zaman görünür, ama dosya yoksa tıklanamaz)
        view_btn = QPushButton("Aç")
        view_btn.setFixedSize(40, 22)
        view_btn.setEnabled(False)
        view_btn.clicked.connect(lambda _checked, k=db_key: self._on_view_diploma(k))
        h.addWidget(view_btn)

        layout.addWidget(container, row, col)

        self._widgets[db_key] = inp
        self._upload_buttons[db_key] = upload_btn
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
        lbl_t.setStyleSheet("color: #8b8fa3; font-size: 11px;")
        l.addWidget(lbl_t)
        
        val = self.personel_data.get(db_key, "")
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDisplayFormat("dd.MM.yyyy")
        
        d = QDate.fromString(str(val), "yyyy-MM-dd")
        date_edit.setDate(d if d.isValid() else QDate.currentDate())

        date_edit.setEnabled(False)
        date_edit.setStyleSheet("background: transparent; border: none; color: #e0e2ea; font-size: 13px; font-weight: 500; padding: 4px;")
        
        ThemeManager.setup_calendar_popup(date_edit)

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
        date_edit.setStyleSheet("background: transparent; border: none; color: #e0e2ea; font-size: 13px; padding: 4px;")

        ThemeManager.setup_calendar_popup(date_edit)
        
        layout.addWidget(date_edit, row, col)
        
        self._widgets[db_key] = date_edit
        self._groups[group_id]["fields"].append(db_key)

    def _toggle_edit(self, group_id, edit_mode):
        grp = self._groups[group_id]
        grp["btn_edit"].setVisible(not edit_mode)
        grp["btn_save"].setVisible(edit_mode)
        grp["btn_cancel"].setVisible(edit_mode)
        
        style_edit = "background: #1e202c; border: 1px solid #3b82f6; border-radius: 4px; padding: 4px; color: white;"
        style_read = "background: transparent; border: none; color: #e0e2ea; font-weight: 500;"
        style_combo_read = "background: transparent; border: none; color: #e0e2ea; font-size: 13px; font-weight: 500; padding: 4px;"
        style_date_read = "background: transparent; border: none; color: #e0e2ea; font-size: 13px; font-weight: 500; padding: 4px;"
        
        for key in grp["fields"]:
            widget = self._widgets[key]
            if isinstance(widget, QLineEdit):
                widget.setReadOnly(not edit_mode)
                widget.setStyleSheet(style_edit if edit_mode else style_read)
            elif isinstance(widget, QComboBox):
                widget.setEnabled(edit_mode)
                widget.setStyleSheet(S["combo"] if edit_mode else style_combo_read)
            elif isinstance(widget, QDateEdit):
                widget.setEnabled(edit_mode)
                widget.setStyleSheet(S["date"] if edit_mode else style_date_read)
            
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
            
            # Diploma yükleme ve açma butonlarını grup düzenleme moduna göre etkinleştir
            if key in self._upload_buttons:
                try:
                    self._upload_buttons[key].setEnabled(edit_mode)
                except Exception:
                    pass
            if key in self._view_buttons:
                try:
                    # "Aç" butonu: dosya varsa tıklanabilir olsun (edit modu fark etmiyor)
                    # ama stil olarak edit modunda ara bilgilendirme yapabiliriz
                    # Şimdilik: sadece dosya varsa etkin yap
                    has_file = bool(self.personel_data.get({
                        'DiplomaNo': 'Diploma1',
                        'DiplomaNo2': 'Diploma2'
                    }.get(key)) or self.personel_data.get(f"{key}_file"))
                    self._view_buttons[key].setEnabled(has_file)
                except Exception:
                    pass

    def _save_group(self, group_id):
        if not self.db:
            QMessageBox.warning(self, "Hata", "Veritabanı bağlantısı yok.")
            return

        grp = self._groups[group_id]
        update_data = {}
        
        # Verileri topla
        for key in grp["fields"]:
            widget = self._widgets[key]
            val = ""
            if isinstance(widget, QLineEdit):
                val = widget.text().strip()
            elif isinstance(widget, QComboBox):
                val = widget.currentText().strip()
            elif isinstance(widget, QDateEdit):
                val = widget.date().toString("yyyy-MM-dd")
            update_data[key] = val
            
        try:
            from database.repository_registry import RepositoryRegistry
            registry = RepositoryRegistry(self.db)
            repo = registry.get("Personel")

            tc = self.personel_data.get("KimlikNo")
            if not tc:
                raise ValueError("TC Kimlik No bulunamadı.")

            # Dosya yükleme adımı: eğer kullanıcı diploma veya fotoğraf seçtiyse
            # önce Drive'a yükle, sonra DB güncellemesini yap
            # _file_paths oluştur
            self._file_paths = {}
            foto = self.personel_data.get("Resim", "")
            if foto and os.path.exists(str(foto)):
                self._file_paths["Resim"] = foto

            if self.personel_data.get("DiplomaNo_file"):
                self._file_paths["Diploma1"] = self.personel_data.get("DiplomaNo_file")
            if self.personel_data.get("DiplomaNo2_file"):
                self._file_paths["Diploma2"] = self.personel_data.get("DiplomaNo2_file")

            # Eğer yükleme gerekmiyorsa doğrudan kaydet
            if not self._file_paths:
                repo.update(tc, update_data)
                self.personel_data.update(update_data)
                self._toggle_edit(group_id, False)
                logger.info(f"Personel güncellendi ({group_id}): {tc}")
                return

            # Upload callback sonrası DB güncellemesi
            def _after_upload():
                for drive_key, link in self._drive_links.items():
                    if drive_key == 'Resim':
                        update_data['Resim'] = link
                    elif drive_key == 'Diploma1':
                        update_data['Diploma1'] = link
                    elif drive_key == 'Diploma2':
                        update_data['Diploma2'] = link

                repo.update(tc, update_data)
                self.personel_data.update(update_data)
                self._toggle_edit(group_id, False)
                logger.info(f"Personel güncellendi ({group_id}): {tc}")

            self._upload_files_to_drive(tc, _after_upload)

        except Exception as e:
            logger.error(f"Güncelleme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Güncelleme başarısız:\n{e}")

    def _on_upload_diploma(self, db_key):
        """Diploma veya ek dosya yükleme işlemini tetikler (dosya seçici)."""
        try:
            path, _ = QFileDialog.getOpenFileName(self, "Diploma Dosyası Seç", "", "PDF Dosyaları (*.pdf);;Tüm Dosyalar (*)")
            if not path:
                return

            # Seçilen dosyanın yolunu widget'a ve iç veriye kaydet
            widget = self._widgets.get(db_key)
            if isinstance(widget, QLineEdit):
                widget.setText(path)
                widget.setToolTip(path)

            # Ayrıca personel_data içine dosya yolunu saklayalım (DB kaydı opsiyonel)
            self.personel_data[f"{db_key}_file"] = path
            # Güncelle UI
            self._refresh_diploma_display(db_key)

        except Exception as e:
            logger.error(f"Diploma yükleme hatası ({db_key}): {e}")
            QMessageBox.warning(self, "Yükleme Hatası", f"Dosya yüklenemedi: {e}")

    def _on_photo_upload(self):
        try:
            path, _ = QFileDialog.getOpenFileName(self, "Fotoğraf Seç", "", "Görüntü Dosyaları (*.png *.jpg *.jpeg *.bmp);;Tüm Dosyalar (*)")
            if not path:
                return
            # Önizlemeyi güncelle
            self._set_photo_preview(path)
            self.personel_data["Resim"] = path
        except Exception as e:
            logger.warning(f"Fotoğraf yüklenemedi: {e}")

    def _upload_files_to_drive(self, tc_no, callback):
        """Seçili dosyaları Drive'a yükler, bitince callback çağırır."""
        # Dosya map: self._file_paths örn {'Resim': path, 'Diploma1': path}
        if not getattr(self, "_file_paths", None):
            callback()
            return

        upload_map = {
            "Resim": ("Personel_Resim", "Resim"),
            "Diploma1": ("Personel_Diploma", "Diploma1"),
            "Diploma2": ("Personel_Diploma", "Diploma2"),
        }

        self._pending_uploads = 0
        self._upload_errors = []
        self._drive_links = {}

        for file_key, file_path in list(self._file_paths.items()):
            if file_key not in upload_map:
                continue
            folder_name, db_field = upload_map[file_key]
            folder_id = self._drive_folders.get(folder_name, "")
            if not folder_id:
                logger.warning(f"Drive klasör bulunamadı: {folder_name}")
                continue

            ext = os.path.splitext(file_path)[1]
            custom_name = f"{tc_no}_{db_field}{ext}"

            try:
                from ui.pages.personel.personel_ekle import DriveUploadWorker
            except Exception:
                from ui.pages.personel.personel_ekle import DriveUploadWorker

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

    def _on_upload_finished(self, alan_adi, link):
        """Tek dosya yükleme tamamlandı."""
        # alan_adi: db field like 'Resim' or 'Diploma1'
        self._drive_links[alan_adi] = link
        logger.info(f"Drive yükleme OK: {alan_adi} → {link}")
        self._pending_uploads -= 1
        # UI'ı güncelle: personel_data'ya ekle ve label'ı set et
        try:
            if alan_adi == 'Diploma1':
                self.personel_data['Diploma1'] = link
            elif alan_adi == 'Diploma2':
                self.personel_data['Diploma2'] = link
            elif alan_adi == 'Resim':
                self.personel_data['Resim'] = link
            # refresh display for diploma keys
            if alan_adi in ('Diploma1', 'Diploma2'):
                key = 'DiplomaNo' if alan_adi == 'Diploma1' else 'DiplomaNo2'
                self._refresh_diploma_display(key)
        except Exception:
            pass
        if self._pending_uploads <= 0:
            self._finalize_uploads()

    def _refresh_diploma_display(self, db_key):
        """Update diploma view button state based on saved or staged file."""
        # db_key is like 'DiplomaNo' or 'DiplomaNo2'
        # map to Drive fields: DiplomaNo -> Diploma1, DiplomaNo2 -> Diploma2
        mapping = { 'DiplomaNo': 'Diploma1', 'DiplomaNo2': 'Diploma2' }
        drive_key = mapping.get(db_key, None)
        view = self._view_buttons.get(db_key)
        if view is None:
            return
        # Prefer saved drive link
        link = ''
        if drive_key and self.personel_data.get(drive_key):
            link = self.personel_data.get(drive_key)
        # Fallback local staged file
        elif self.personel_data.get(f"{db_key}_file"):
            link = self.personel_data.get(f"{db_key}_file")

        # Enable "Aç" button only if file exists
        view.setEnabled(bool(link))

    def _on_view_diploma(self, db_key):
        """Open diploma: web link or local file."""
        mapping = { 'DiplomaNo': 'Diploma1', 'DiplomaNo2': 'Diploma2' }
        drive_key = mapping.get(db_key, None)
        link = None
        if drive_key and self.personel_data.get(drive_key):
            link = self.personel_data.get(drive_key)
        elif self.personel_data.get(f"{db_key}_file"):
            link = self.personel_data.get(f"{db_key}_file")
        if not link:
            return
        try:
            import webbrowser
            if link.startswith('http'):
                webbrowser.open(link)
            else:
                # local file
                try:
                    os.startfile(link)
                except Exception:
                    webbrowser.open('file://' + os.path.abspath(link))
        except Exception as e:
            logger.error(f"Diploma görüntülenemedi: {e}")

    def _on_upload_error(self, alan_adi, hata):
        """Tek dosya yükleme hatası."""
        self._upload_errors.append(f"{alan_adi}: {hata}")
        logger.error(f"Drive yükleme HATA: {alan_adi} → {hata}")
        self._pending_uploads -= 1
        if self._pending_uploads <= 0:
            self._finalize_uploads()

    def _finalize_uploads(self):
        """Tüm yüklemeler tamamlandığında çağrılır."""
        # Temizle
        self._upload_workers.clear()

        if self._upload_errors:
            QMessageBox.warning(
                self, "Drive Yükleme Uyarısı",
                "Bazı dosyalar yüklenemedi:\n" + "\n".join(self._upload_errors)
            )

        if hasattr(self, "_upload_callback") and callable(self._upload_callback):
            try:
                self._upload_callback()
            except Exception as e:
                logger.error(f"Upload callback hatası: {e}")

    def _fmt_date(self, val):
        if not val: return "-"
        try:
            from datetime import datetime
            if "-" in str(val):
                d = datetime.strptime(str(val), "%Y-%m-%d")
                return d.strftime("%d.%m.%Y")
        except:
            pass
        return str(val)
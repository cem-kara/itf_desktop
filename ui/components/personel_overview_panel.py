# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout, 
    QGroupBox, QScrollArea, QLineEdit, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from core.logger import logger

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
        self._groups = {}   # Grup adı -> (layout, edit_btn, save_btn, cancel_btn)
        self._setup_ui()

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
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
            }
        """)
        h_layout = QGridLayout(header_frame)
        h_layout.setContentsMargins(15, 15, 15, 15)
        h_layout.setSpacing(15)

        # Başlık
        lbl_baslik = QLabel("KİMLİK BİLGİLERİ")
        lbl_baslik.setStyleSheet("color: #6bd3ff; font-weight: bold; font-size: 12px; letter-spacing: 1px;")
        h_layout.addWidget(lbl_baslik, 0, 0, 1, 4)

        # Bilgiler
        self._add_readonly_item(h_layout, 1, 0, "TC Kimlik No", self.personel_data.get("KimlikNo"))
        self._add_readonly_item(h_layout, 1, 1, "Ad Soyad", self.personel_data.get("AdSoyad"))
        self._add_readonly_item(h_layout, 1, 2, "Doğum Yeri", self.personel_data.get("DogumYeri"))
        self._add_readonly_item(h_layout, 1, 3, "Doğum Tarihi", self._fmt_date(self.personel_data.get("DogumTarihi")))

        layout.addWidget(header_frame)

        # ── 2. İletişim ve Kadro (Yan Yana) ──
        mid_layout = QHBoxLayout()
        mid_layout.setSpacing(20)

        # İletişim Grubu
        grp_iletisim = self._create_editable_group("📞 İletişim Bilgileri", "iletisim")
        g2 = QGridLayout(grp_iletisim)
        g2.setSpacing(12)
        self._add_editable_item(g2, 0, 0, "Cep Telefonu", "CepTelefonu", "iletisim")
        self._add_editable_item(g2, 1, 0, "E-posta", "Eposta", "iletisim")
        mid_layout.addWidget(grp_iletisim)

        # Kadro Grubu
        grp_kurum = self._create_editable_group("🏛️ Kadro ve Kurumsal Bilgiler", "kadro")
        g3 = QGridLayout(grp_kurum)
        g3.setSpacing(12)
        self._add_editable_item(g3, 0, 0, "Hizmet Sınıfı", "HizmetSinifi", "kadro")
        self._add_editable_item(g3, 0, 1, "Kadro Ünvanı", "KadroUnvani", "kadro")
        self._add_editable_item(g3, 1, 0, "Görev Yeri", "GorevYeri", "kadro")
        self._add_editable_item(g3, 1, 1, "Sicil No", "KurumSicilNo", "kadro")
        self._add_editable_item(g3, 2, 0, "Başlama Tarihi", "MemuriyeteBaslamaTarihi", "kadro")
        self._add_readonly_item(g3, 2, 1, "Durum", self.personel_data.get("Durum")) # Durum buradan değişmesin
        mid_layout.addWidget(grp_kurum)

        layout.addLayout(mid_layout)

        # ── 3. Eğitim Bilgileri (4 Kolonlu Grid) ──
        grp_egitim = self._create_editable_group("🎓 Eğitim Bilgileri", "egitim")
        g4 = QGridLayout(grp_egitim)
        g4.setSpacing(15)
        
        # Başlıklar
        headers = ["Okul Adı", "Bölüm / Fakülte", "Mezuniyet Tarihi", "Diploma No"]
        for i, h in enumerate(headers):
            lbl = QLabel(h)
            lbl.setStyleSheet("color: #8b8fa3; font-size: 11px; font-weight: bold;")
            g4.addWidget(lbl, 0, i)

        # 1. Okul
        self._add_editable_field_only(g4, 1, 0, "MezunOlunanOkul", "egitim")
        self._add_editable_field_only(g4, 1, 1, "MezunOlunanFakulte", "egitim")
        self._add_editable_field_only(g4, 1, 2, "MezuniyetTarihi", "egitim")
        self._add_editable_field_only(g4, 1, 3, "DiplomaNo", "egitim")

        # 2. Okul
        self._add_editable_field_only(g4, 2, 0, "MezunOlunanOkul2", "egitim")
        self._add_editable_field_only(g4, 2, 1, "MezunOlunanFakulte2", "egitim")
        self._add_editable_field_only(g4, 2, 2, "MezuniyetTarihi2", "egitim")
        self._add_editable_field_only(g4, 2, 3, "DiplomaNo2", "egitim")
        
        layout.addWidget(grp_egitim)

        layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

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

    def _add_editable_field_only(self, layout, row, col, db_key, group_id):
        """Sadece Input ekler (Eğitim tablosu için)."""
        val = self.personel_data.get(db_key, "")
        inp = QLineEdit(str(val) if val else "")
        inp.setReadOnly(True)
        inp.setPlaceholderText("-")
        inp.setStyleSheet("background: transparent; border: none; color: #e0e2ea; font-size: 13px;")
        
        layout.addWidget(inp, row, col)
        
        self._widgets[db_key] = inp
        self._groups[group_id]["fields"].append(db_key)

    def _toggle_edit(self, group_id, edit_mode):
        grp = self._groups[group_id]
        grp["btn_edit"].setVisible(not edit_mode)
        grp["btn_save"].setVisible(edit_mode)
        grp["btn_cancel"].setVisible(edit_mode)
        
        style_edit = "background: #1e202c; border: 1px solid #3b82f6; border-radius: 4px; padding: 4px; color: white;"
        style_read = "background: transparent; border: none; color: #e0e2ea; font-weight: 500;"
        
        for key in grp["fields"]:
            widget = self._widgets[key]
            widget.setReadOnly(not edit_mode)
            widget.setStyleSheet(style_edit if edit_mode else style_read)
            
            # İptal edilirse eski veriyi geri yükle
            if not edit_mode:
                val = self.personel_data.get(key, "")
                widget.setText(str(val) if val else "")

    def _save_group(self, group_id):
        if not self.db:
            QMessageBox.warning(self, "Hata", "Veritabanı bağlantısı yok.")
            return

        grp = self._groups[group_id]
        update_data = {}
        
        # Verileri topla
        for key in grp["fields"]:
            val = self._widgets[key].text().strip()
            update_data[key] = val
            
        try:
            from database.repository_registry import RepositoryRegistry
            registry = RepositoryRegistry(self.db)
            repo = registry.get("Personel")
            
            tc = self.personel_data.get("KimlikNo")
            if not tc:
                raise ValueError("TC Kimlik No bulunamadı.")
                
            repo.update(tc, update_data)
            
            # Yerel veriyi güncelle
            self.personel_data.update(update_data)
            
            # UI'ı normal moda döndür
            self._toggle_edit(group_id, False)
            
            # Kullanıcıya bilgi ver (opsiyonel, çok sık çıkmasın diye logluyoruz)
            logger.info(f"Personel güncellendi ({group_id}): {tc}")
            
        except Exception as e:
            logger.error(f"Güncelleme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Güncelleme başarısız:\n{e}")

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
# -*- coding: utf-8 -*-
"""
Hızlı Sağlık Muayene Girişi Dialog (saglik_takip.py referans alınarak güncellendi)
"""
import uuid
from datetime import datetime, date
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDateEdit, QLineEdit, QFrame, QGridLayout,
    QMessageBox, QGroupBox, QScrollArea, QTextEdit
)
from PySide6.QtGui import QCursor

from core.logger import logger
from core.date_utils import parse_date, to_db_date
from ui.theme_manager import ThemeManager

S = ThemeManager.get_all_component_styles()
STATUS_OPTIONS = ["", "Uygun", "Şartlı Uygun", "Uygun Değil"]

class HizliSaglikGirisDialog(QWidget):
    """
    Personel Merkez ekranında sol panelde hızlı sağlık muayene girişi widget'ı.
    ui/pages/personel/saglik_takip.py referans alınarak tasarlanmıştır.
    """
    saglik_kaydedildi = Signal()
    cancelled = Signal()

    def __init__(self, db, personel_data, parent=None):
        super().__init__(parent)
        self._db = db
        self._personel = personel_data or {}
        self._exam_keys = ["Dermatoloji", "Dahiliye", "Goz", "Goruntuleme"]
        self._exam_widgets = {}

        self.setStyleSheet(S["page"])

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMaximumWidth(320)
        scroll.setStyleSheet(S.get("scroll", ""))
        
        form_content = QWidget()
        form_content.setStyleSheet("background: transparent;")
        form_lay = QVBoxLayout(form_content)
        form_lay.setContentsMargins(0, 0, 8, 0)
        form_lay.setSpacing(10)

        # Muayene Durumları
        muayene_container = QWidget()
        muayene_layout = QVBoxLayout(muayene_container)
        muayene_layout.setContentsMargins(0, 0, 0, 0)
        muayene_layout.setSpacing(15)

        self._add_exam_fields(muayene_layout, 0, "Dermatoloji", "Dermatoloji Muayenesi")
        self._add_exam_fields(muayene_layout, 1, "Dahiliye", "Dahiliye Muayenesi")
        self._add_exam_fields(muayene_layout, 2, "Goz", "Göz Muayenesi")
        self._add_exam_fields(muayene_layout, 3, "Goruntuleme", "Görüntüleme Teknikleri (Varsa)")
        form_lay.addWidget(muayene_container)

        # Ek Bilgiler
        grp_ek = QGroupBox("Ek Bilgiler")
        grp_ek.setStyleSheet(S["group"])
        grp_ek.setMaximumWidth(300)
        g3 = QGridLayout(grp_ek)
        g3.setContentsMargins(12, 12, 12, 12)
        g3.setHorizontalSpacing(10)
        g3.setVerticalSpacing(8)
        
        g3.addWidget(QLabel("Not"), 0, 0)
        self.inp_not = QLineEdit()
        self.inp_not.setMaximumWidth(280)
        self.inp_not.setStyleSheet(S["input"])
        g3.addWidget(self.inp_not, 0, 1)
        form_lay.addWidget(grp_ek)
        
        scroll.setWidget(form_content)
        main.addWidget(scroll)

        # Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_iptal = QPushButton("İptal", styleSheet=S["cancel_btn"], cursor=QCursor(Qt.PointingHandCursor))
        btn_iptal.clicked.connect(self.cancelled.emit)
        btn_layout.addWidget(btn_iptal)
        btn_kaydet = QPushButton("✓ Kaydet", styleSheet=S["save_btn"], cursor=QCursor(Qt.PointingHandCursor))
        btn_kaydet.clicked.connect(self._on_save)
        btn_layout.addWidget(btn_kaydet)
        main.addLayout(btn_layout)

    def _add_exam_fields(self, layout, row_idx, key, title):
        """Muayene alanlarını sade biçimde ekle."""
        # Başlık
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(S.get("section_title", ""))
        layout.addWidget(lbl_title)
        
        # Grid layout for inputs
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(4)
        
        # Row 0: Labels
        lbl_tarih = QLabel("Tarih")
        lbl_tarih.setStyleSheet(S.get("label", ""))
        lbl_tarih.setMaximumWidth(100)
        grid.addWidget(lbl_tarih, 0, 0)
        
        lbl_durum = QLabel("Durum")
        lbl_durum.setStyleSheet(S.get("label", ""))
        lbl_durum.setMaximumWidth(150)
        grid.addWidget(lbl_durum, 0, 1)
        
        # Row 1: Inputs
        de = QDateEdit(QDate.currentDate())
        de.setDisplayFormat("dd.MM.yyyy")
        de.setCalendarPopup(True)
        de.setMaximumWidth(100)
        de.setMinimumHeight(35)
        de.setStyleSheet(S["date"])
        ThemeManager.setup_calendar_popup(de)
        grid.addWidget(de, 1, 0)
        
        cmb = QComboBox()
        cmb.addItems(STATUS_OPTIONS)
        cmb.setMaximumWidth(150)
        cmb.setMinimumHeight(35)
        cmb.setStyleSheet(S["combo"])
        grid.addWidget(cmb, 1, 1)
        
        layout.addLayout(grid)
        
        # Açıklama
        lbl_aciklama = QLabel("Açıklama")
        lbl_aciklama.setStyleSheet(S.get("label", ""))
        layout.addWidget(lbl_aciklama)
        
        inp = QTextEdit()
        inp.setPlaceholderText("Gerekiyorsa açıklama...")
        inp.setMinimumHeight(35)
        inp.setMaximumHeight(60)
        inp.setStyleSheet(S["input"])
        inp.setEnabled(False)
        layout.addWidget(inp)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        sep.setStyleSheet(S.get("separator", ""))
        layout.addWidget(sep)
        
        self._exam_widgets[key] = {"tarih": de, "durum": cmb, "aciklama": inp}

    def _connect_signals(self):
        for key in self._exam_keys:
            self._exam_widgets[key]["durum"].currentTextChanged.connect(
                lambda _txt, k=key: self._on_exam_status_changed(k)
            )

    def _on_exam_status_changed(self, key):
        """saglik_takip.py'den alınan yardımcı metod."""
        w = self._exam_widgets.get(key, {})
        durum = str(w.get("durum").currentText()).strip()
        aciklama = w.get("aciklama")
        if not aciklama:
            return
        enabled = durum in ("Şartlı Uygun", "Uygun Değil")
        aciklama.setEnabled(enabled)
        if not enabled:
            aciklama.clear()

    def _compute_summary(self):
        """saglik_takip.py'den alınan yardımcı metod."""
        exam_data = []
        for key in self._exam_keys:
            w = self._exam_widgets[key]
            tarih_db = self._exam_date_if_set(key)
            durum = str(w["durum"].currentText()).strip()
            exam_data.append((tarih_db, durum))

        dates = [d for d, _ in exam_data if parse_date(d)]
        latest = max(dates) if dates else ""
        sonraki = ""
        if latest:
            d = datetime.strptime(latest, "%Y-%m-%d").date()
            try:
                sonraki = d.replace(year=d.year + 1).isoformat()
            except ValueError: # 29 Şubat durumu
                sonraki = d.replace(month=2, day=28, year=d.year + 1).isoformat()

        statuses = [s for _, s in exam_data if s]
        if "Uygun Değil" in statuses:
            sonuc = "Uygun Değil"
            durum = "Riskli"
        elif "Şartlı Uygun" in statuses:
            sonuc = "Şartlı Uygun"
            durum = "Gecerli"
        elif "Uygun" in statuses:
            sonuc = "Uygun"
            if parse_date(sonraki) and parse_date(sonraki) < date.today():
                durum = "Gecikmis"
            else:
                durum = "Gecerli"
        else:
            sonuc = ""
            durum = "Planlandı"

        return latest, sonraki, sonuc, durum

    def _exam_date_if_set(self, key):
        """saglik_takip.py'den alınan yardımcı metod."""
        w = self._exam_widgets[key]
        if not str(w["durum"].currentText()).strip():
            return ""
        return to_db_date(w["tarih"].date().toString("yyyy-MM-dd"))

    def _on_save(self):
        # Zorunlu alan kontrolü
        ad_map = {
            "Dermatoloji": "Dermatoloji", "Dahiliye": "Dahiliye",
            "Goz": "Göz", "Goruntuleme": "Görüntüleme Teknikleri"
        }
        for key in self._exam_keys:
            durum = str(self._exam_widgets[key]["durum"].currentText()).strip()
            aciklama = self._exam_widgets[key]["aciklama"].text().strip()
            if durum in ("Şartlı Uygun", "Uygun Değil") and not aciklama:
                QMessageBox.warning(
                    self, "Eksik Bilgi",
                    f"{ad_map.get(key, key)} muayenesi için seçilen durumda açıklama zorunludur."
                )
                return

        personel_data = self._personel
        muayene_db, sonraki_db, sonuc, durum = self._compute_summary()
        
        if not sonuc:
            QMessageBox.warning(self, "Eksik Bilgi", "En az bir muayene sonucu girilmelidir.")
            return

        kayit_no = uuid.uuid4().hex[:12].upper()
        
        payload = {
            "KayitNo": kayit_no,
            "Personelid": personel_data.get("KimlikNo", ""),
            "AdSoyad": personel_data.get("AdSoyad", ""),
            "Birim": personel_data.get("GorevYeri", ""),
            "Yil": int(datetime.now().year),
            "MuayeneTarihi": muayene_db,
            "SonrakiKontrolTarihi": sonraki_db,
            "Sonuc": sonuc,
            "Durum": durum,
            "DermatolojiMuayeneTarihi": self._exam_date_if_set("Dermatoloji"),
            "DermatolojiDurum": str(self._exam_widgets["Dermatoloji"]["durum"].currentText()).strip(),
            "DermatolojiAciklama": self._exam_widgets["Dermatoloji"]["aciklama"].text().strip(),
            "DahiliyeMuayeneTarihi": self._exam_date_if_set("Dahiliye"),
            "DahiliyeDurum": str(self._exam_widgets["Dahiliye"]["durum"].currentText()).strip(),
            "DahiliyeAciklama": self._exam_widgets["Dahiliye"]["aciklama"].text().strip(),
            "GozMuayeneTarihi": self._exam_date_if_set("Goz"),
            "GozDurum": str(self._exam_widgets["Goz"]["durum"].currentText()).strip(),
            "GozAciklama": self._exam_widgets["Goz"]["aciklama"].text().strip(),
            "GoruntulemeMuayeneTarihi": self._exam_date_if_set("Goruntuleme"),
            "GoruntulemeDurum": str(self._exam_widgets["Goruntuleme"]["durum"].currentText()).strip(),
            "GoruntulemeAciklama": self._exam_widgets["Goruntuleme"]["aciklama"].text().strip(),
            "RaporDosya": "", # Hızlı girişte dosya yükleme yok
            "Notlar": self.inp_not.text().strip(),
        }

        try:
            from core.di import get_registry
            registry = get_registry(self._db)
            takip_repo = registry.get("Personel_Saglik_Takip")
            personel_repo = registry.get("Personel")
            
            takip_repo.insert(payload)

            # Ana personel tablosundaki özet bilgiyi de güncelle
            personel_sonuc = "uygun" if sonuc == "Uygun" else sonuc
            personel_repo.update(payload["Personelid"], {
                "MuayeneTarihi": muayene_db,
                "Sonuc": personel_sonuc,
            })

            QMessageBox.information(self, "Başarılı", "Sağlık takip kaydı başarıyla eklendi.")
            self.saglik_kaydedildi.emit()
            self.accept()

        except Exception as e:
            logger.error(f"Hızlı sağlık kaydetme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Kayıt sırasında hata oluştu:\n{e}")
# -*- coding: utf-8 -*-
"""
Hızlı İzin Girişi Dialog
"""
import uuid
from datetime import datetime, timedelta, date
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDateEdit, QSpinBox, QFrame, QGridLayout,
    QAbstractSpinBox, QMessageBox
)
from PySide6.QtGui import QCursor

from core.logger import logger
from core.date_utils import parse_date as parse_any_date
from ui.theme_manager import ThemeManager

S = ThemeManager.get_all_component_styles()

# max_label stili merkezi temada yoksa diye fallback
if "max_label" not in S:
    S["max_label"] = "color: #facc15; font-size: 11px; font-style: italic; background: transparent;"

def _parse_date(val):
    return parse_any_date(val)

class HizliIzinGirisDialog(QDialog):
    """
    Personel Merkez ekranından hızlı izin girişi için kullanılan modal dialog.
    """
    izin_kaydedildi = Signal()

    def __init__(self, db, personel_data, parent=None):
        super().__init__(parent)
        self._db = db
        self._personel = personel_data or {}
        self._tatiller = []
        self._izin_tipleri = []
        self._izin_max_gun = {}
        self.ui = {}

        self.setWindowTitle(f"Hızlı İzin Girişi — {self._personel.get('AdSoyad', '')}")
        self.setMinimumWidth(450)
        self.setStyleSheet(S["page"])
        self.setModal(True)

        self._setup_ui()
        self._load_sabitler()
        self._calculate_bitis()

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(15, 15, 15, 15)
        main.setSpacing(12)

        form = QGridLayout()
        form.setSpacing(10)

        # İzin Tipi
        form.addWidget(QLabel("İzin Tipi", styleSheet=S["label"]), 0, 0)
        self.ui["izin_tipi"] = QComboBox(styleSheet=S["combo"])
        form.addWidget(self.ui["izin_tipi"], 0, 1)

        # Max gün uyarı
        self.ui["max_gun_label"] = QLabel("", styleSheet=S["max_label"])
        form.addWidget(self.ui["max_gun_label"], 1, 1)

        # Başlama Tarihi
        form.addWidget(QLabel("Başlama Tarihi", styleSheet=S["label"]), 2, 0)
        self.ui["baslama"] = QDateEdit(QDate.currentDate(), calendarPopup=True, displayFormat="dd.MM.yyyy", styleSheet=S["date"])
        ThemeManager.setup_calendar_popup(self.ui["baslama"])
        form.addWidget(self.ui["baslama"], 2, 1)

        # Süre
        form.addWidget(QLabel("Süre (Gün)", styleSheet=S["label"]), 3, 0)
        self.ui["gun"] = QSpinBox(minimum=1, maximum=365, value=1, styleSheet=S["spin"])
        form.addWidget(self.ui["gun"], 3, 1)

        # Bitiş Tarihi
        form.addWidget(QLabel("İşe Dönüş Tarihi", styleSheet=S["label"]), 4, 0)
        self.ui["bitis"] = QDateEdit(readOnly=True, displayFormat="dd.MM.yyyy", buttonSymbols=QAbstractSpinBox.NoButtons, styleSheet=S["date"])
        form.addWidget(self.ui["bitis"], 4, 1)

        main.addLayout(form)
        main.addStretch()

        # Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_iptal = QPushButton("İptal", styleSheet=S["cancel_btn"], cursor=QCursor(Qt.PointingHandCursor))
        btn_iptal.clicked.connect(self.reject)
        btn_layout.addWidget(btn_iptal)
        btn_kaydet = QPushButton("✓ Kaydet", styleSheet=S["save_btn"], cursor=QCursor(Qt.PointingHandCursor))
        btn_kaydet.clicked.connect(self._on_save)
        btn_layout.addWidget(btn_kaydet)
        main.addLayout(btn_layout)

        # Sinyaller
        self.ui["baslama"].dateChanged.connect(self._calculate_bitis)
        self.ui["gun"].valueChanged.connect(self._calculate_bitis)
        self.ui["izin_tipi"].currentTextChanged.connect(self._on_izin_tipi_changed)

    def _load_sabitler(self):
        try:
            from core.di import get_registry
            registry = get_registry(self._db)
            sabitler = registry.get("Sabitler").get_all()
            self._izin_max_gun = {}
            tip_adlari = []
            for r in sabitler:
                if str(r.get("Kod", "")).strip() != "İzin_Tipi": continue
                tip_adi = str(r.get("MenuEleman", "")).strip()
                if not tip_adi: continue
                tip_adlari.append(tip_adi)
                aciklama = str(r.get("Aciklama", "")).strip()
                if aciklama:
                    try: self._izin_max_gun[tip_adi] = int(aciklama)
                    except ValueError: pass
            
            self._izin_tipleri = sorted(tip_adlari)
            self.ui["izin_tipi"].clear()
            self.ui["izin_tipi"].addItems(self._izin_tipleri)
            
            tatiller = registry.get("Tatiller").get_all()
            self._tatiller = [
                _parse_date(r.get("Tarih", "")).isoformat()
                for r in tatiller if _parse_date(r.get("Tarih", ""))
            ]
        except Exception as e:
            logger.error(f"Hızlı izin sabitleri yükleme hatası: {e}")

    def _on_izin_tipi_changed(self, tip_text):
        tip_text = str(tip_text).strip()
        max_gun = self._izin_max_gun.get(tip_text, 0)
        if max_gun and max_gun > 0:
            self.ui["gun"].setMaximum(max_gun)
            if self.ui["gun"].value() > max_gun:
                self.ui["gun"].setValue(max_gun)
            self.ui["max_gun_label"].setText(f"Bu izin tipi için en fazla {max_gun} gün girilebilir.")
        else:
            self.ui["gun"].setMaximum(365)
            self.ui["max_gun_label"].setText("")

    def _calculate_bitis(self):
        baslama = self.ui["baslama"].date().toPython()
        gun = self.ui["gun"].value()
        kalan = gun
        current = baslama
        while kalan > 0:
            current += timedelta(days=1)
            if current.weekday() in (5, 6): continue
            if current.isoformat() in self._tatiller: continue
            kalan -= 1
        self.ui["bitis"].setDate(QDate(current.year, current.month, current.day))

    def _on_save(self):
        tc = self._personel.get("KimlikNo")
        ad = self._personel.get("AdSoyad")
        sinif = self._personel.get("HizmetSinifi")
        izin_tipi = self.ui["izin_tipi"].currentText().strip()
        baslama_str = self.ui["baslama"].date().toString("yyyy-MM-dd")
        bitis_str = self.ui["bitis"].date().toString("yyyy-MM-dd")
        gun = self.ui["gun"].value()

        try:
            from core.di import get_registry
            registry = get_registry(self._db)
            
            # Çakışma kontrolü
            all_izin = registry.get("Izin_Giris").get_all()
            yeni_bas = _parse_date(baslama_str)
            yeni_bit = _parse_date(bitis_str)
            for kayit in all_izin:
                if str(kayit.get("Durum", "")) == "İptal": continue
                if str(kayit.get("Personelid", "")) != tc: continue
                vt_bas = _parse_date(kayit.get("BaslamaTarihi", ""))
                vt_bit = _parse_date(kayit.get("BitisTarihi", ""))
                if vt_bas and vt_bit and (yeni_bas <= vt_bit) and (yeni_bit >= vt_bas):
                    QMessageBox.warning(self, "Çakışma", "Bu tarihlerde zaten bir izin kaydı mevcut.")
                    return

            # Bakiye kontrolü
            if izin_tipi in ["Yıllık İzin", "Şua İzni"]:
                izin_bilgi = registry.get("Izin_Bilgi").get_by_id(tc)
                if izin_bilgi:
                    alan = "YillikKalan" if izin_tipi == "Yıllık İzin" else "SuaKalan"
                    kalan = float(izin_bilgi.get(alan, 0))
                    if gun > kalan:
                        cevap = QMessageBox.question(self, "Yetersiz Bakiye", f"Kalan bakiye: {kalan} gün. Devam edilsin mi?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                        if cevap != QMessageBox.Yes: return

            # Kaydet
            izin_id = str(uuid.uuid4())[:8].upper()
            yeni_kayit = {
                "Izinid": izin_id, "HizmetSinifi": sinif, "Personelid": tc,
                "AdSoyad": ad, "IzinTipi": izin_tipi, "BaslamaTarihi": baslama_str,
                "Gun": gun, "BitisTarihi": bitis_str, "Durum": "Onaylandı",
            }
            registry.get("Izin_Giris").insert(yeni_kayit)
            
            self._bakiye_dus(registry, tc, izin_tipi, gun)

            QMessageBox.information(self, "Başarılı", "İzin başarıyla kaydedildi.")
            self.izin_kaydedildi.emit()
            self.accept()

        except Exception as e:
            logger.error(f"Hızlı izin kaydetme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"İşlem başarısız: {e}")

    def _bakiye_dus(self, registry, tc, izin_tipi, gun):
        try:
            izin_bilgi = registry.get("Izin_Bilgi").get_by_id(tc)
            if not izin_bilgi: return
            if izin_tipi == "Yıllık İzin":
                yeni_kul = float(izin_bilgi.get("YillikKullanilan", 0)) + gun
                yeni_kal = float(izin_bilgi.get("YillikKalan", 0)) - gun
                registry.get("Izin_Bilgi").update(tc, {"YillikKullanilan": yeni_kul, "YillikKalan": yeni_kal})
            elif izin_tipi == "Şua İzni":
                yeni_kul = float(izin_bilgi.get("SuaKullanilan", 0)) + gun
                yeni_kal = float(izin_bilgi.get("SuaKalan", 0)) - gun
                registry.get("Izin_Bilgi").update(tc, {"SuaKullanilan": yeni_kul, "SuaKalan": yeni_kal})
            elif izin_tipi in ["Rapor", "Mazeret İzni", "Sağlık Raporu"]:
                yeni_top = float(izin_bilgi.get("RaporMazeretTop", 0)) + gun
                registry.get("Izin_Bilgi").update(tc, {"RaporMazeretTop": yeni_top})
        except Exception as e:
            logger.error(f"Bakiye düşme hatası: {e}")
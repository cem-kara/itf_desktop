# -*- coding: utf-8 -*-
"""
Hızlı İzin Girişi Dialog
"""
import uuid
from datetime import datetime, timedelta, date
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDateEdit, QSpinBox, QFrame, QGridLayout,
    QAbstractSpinBox, QMessageBox, QDialog
)
from PySide6.QtGui import QCursor

from core.logger import logger
from core.date_utils import parse_date
from core.di import get_izin_service
from database.repository_registry import RepositoryRegistry
from ui.styles.components import STYLES as S

class HizliIzinGirisDialog(QDialog):
    """
    Personel Merkez ekranında sol panelde hızlı izin girişi widget'ı.
    """
    izin_kaydedildi = Signal()
    cancelled = Signal()

    def __init__(self, db, personel_data, parent=None):
        super().__init__(parent)
        self._db = db
        self._personel = personel_data or {}
        self._tatiller = []
        self._izin_tipleri = []
        self._izin_max_gun = {}
        self.ui = {}

        self.setStyleSheet(S["page"])

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
        lbl_izin = QLabel("İzin Tipi")
        lbl_izin.setStyleSheet(S["label"])
        form.addWidget(lbl_izin, 0, 0)
        self.ui["izin_tipi"] = QComboBox()
        self.ui["izin_tipi"].setStyleSheet(S["combo"])
        form.addWidget(self.ui["izin_tipi"], 0, 1)

        # Max gün uyarı
        self.ui["max_gun_label"] = QLabel("")
        self.ui["max_gun_label"].setStyleSheet(S["max_label"])
        form.addWidget(self.ui["max_gun_label"], 1, 1)

        # Başlama Tarihi
        lbl_baslama = QLabel("Başlama Tarihi")
        lbl_baslama.setStyleSheet(S["label"])
        form.addWidget(lbl_baslama, 2, 0)
        self.ui["baslama"] = QDateEdit()
        self.ui["baslama"].setDate(QDate.currentDate())
        self.ui["baslama"].setCalendarPopup(True)
        self.ui["baslama"].setDisplayFormat("dd.MM.yyyy")
        self.ui["baslama"].setStyleSheet(S["date"])
        form.addWidget(self.ui["baslama"], 2, 1)

        # Süre
        lbl_gun = QLabel("Süre (Gün)")
        lbl_gun.setStyleSheet(S["label"])
        form.addWidget(lbl_gun, 3, 0)
        self.ui["gun"] = QSpinBox()
        self.ui["gun"].setMinimum(1)
        self.ui["gun"].setMaximum(365)
        self.ui["gun"].setValue(1)
        self.ui["gun"].setStyleSheet(S["spin"])
        form.addWidget(self.ui["gun"], 3, 1)

        # Bitiş Tarihi
        lbl_bitis = QLabel("İşe Dönüş Tarihi")
        lbl_bitis.setStyleSheet(S["label"])
        form.addWidget(lbl_bitis, 4, 0)
        self.ui["bitis"] = QDateEdit()
        self.ui["bitis"].setReadOnly(True)
        self.ui["bitis"].setDisplayFormat("dd.MM.yyyy")
        self.ui["bitis"].setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.ui["bitis"].setStyleSheet(S["date"])
        form.addWidget(self.ui["bitis"], 4, 1)

        main.addLayout(form)
        main.addStretch()

        # Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_iptal = QPushButton("İptal")
        btn_iptal.setStyleSheet(S["cancel_btn"])
        btn_iptal.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_iptal.clicked.connect(self.cancelled.emit)
        btn_layout.addWidget(btn_iptal)
        btn_kaydet = QPushButton("Kaydet")
        btn_kaydet.setStyleSheet(S["save_btn"])
        btn_kaydet.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_kaydet.clicked.connect(self._on_save)
        btn_layout.addWidget(btn_kaydet)
        main.addLayout(btn_layout)

        # Sinyaller
        self.ui["baslama"].dateChanged.connect(self._calculate_bitis)
        self.ui["gun"].valueChanged.connect(self._calculate_bitis)
        self.ui["izin_tipi"].currentTextChanged.connect(self._on_izin_tipi_changed)

    def _load_sabitler(self):
        try:
            from core.di import get_fhsz_service
            fhsz_svc = get_fhsz_service(self._db)
            sabitler = fhsz_svc.get_sabitler_repo().get_all()
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
            
            registry = RepositoryRegistry(self._db)
            tatiller = registry.get("Tatiller").get_all()
            self._tatiller = []
            for r in tatiller:
                date_obj = parse_date(r.get("Tarih", ""))
                if date_obj:
                    self._tatiller.append(date_obj.isoformat())
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

    def _should_set_pasif(self, izin_tipi: str, gun: int) -> bool:
        tip = str(izin_tipi or "").strip().lower()
        return gun > 30 or "aylıksız" in tip or "ucretsiz" in tip or "ücretsiz" in tip

    def _set_personel_pasif(self, registry, tc: str, izin_tipi: str, gun: int) -> None:
        if not tc or not self._should_set_pasif(izin_tipi, gun):
            return
        try:
            registry.get("Personel").update(tc, {"Durum": "Pasif"})
            logger.info(f"Personel pasif yapıldı: {tc} — {izin_tipi} — {gun} gün")
        except Exception as e:
            logger.error(f"Personel durum güncelleme hatası: {e}")

    def _on_save(self):
        tc = self._personel.get("KimlikNo")
        ad = self._personel.get("AdSoyad")
        sinif = self._personel.get("HizmetSinifi")
        izin_tipi = self.ui["izin_tipi"].currentText().strip()
        baslama_str = self.ui["baslama"].date().toString("yyyy-MM-dd")
        bitis_str = self.ui["bitis"].date().toString("yyyy-MM-dd")
        gun = self.ui["gun"].value()

        try:
            izin_svc = get_izin_service(self._db)
            registry = RepositoryRegistry(self._db)
            
            # Çakışma kontrolü
            all_izin = izin_svc.get_izin_giris_repo().get_all()
            yeni_bas = parse_date(baslama_str)
            yeni_bit = parse_date(bitis_str)
            for kayit in all_izin:
                if str(kayit.get("Durum", "")) == "İptal": continue
                if str(kayit.get("Personelid", "")) != tc: continue
                vt_bas = parse_date(kayit.get("BaslamaTarihi", ""))
                vt_bit = parse_date(kayit.get("BitisTarihi", ""))
                if vt_bas and vt_bit and yeni_bas and yeni_bit and (yeni_bas <= vt_bit) and (yeni_bit >= vt_bas):
                    QMessageBox.warning(self, "Çakışma", "Bu tarihlerde zaten bir izin kaydı mevcut.")
                    return

            # Bakiye kontrolü
            if izin_tipi in ["Yıllık İzin", "Şua İzni"]:
                izin_bilgi = registry.get("Izin_Bilgi").get_by_id(tc or "")
                if izin_bilgi:
                    alan = "YillikKalan" if izin_tipi == "Yıllık İzin" else "SuaKalan"
                    kalan = float(izin_bilgi.get(alan, 0))
                    if gun > kalan:
                        cevap = QMessageBox.question(self, "Yetersiz Bakiye", f"Kalan bakiye: {kalan} gün. Devam edilsin mi?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
                        if cevap != QMessageBox.StandardButton.Yes: return

            # Kaydet
            izin_id = str(uuid.uuid4())[:8].upper()
            yeni_kayit = {
                "Izinid": izin_id, "HizmetSinifi": sinif, "Personelid": tc,
                "AdSoyad": ad, "IzinTipi": izin_tipi, "BaslamaTarihi": baslama_str,
                "Gun": gun, "BitisTarihi": bitis_str, "Durum": "Onaylandı",
            }
            registry.get("Izin_Giris").insert(yeni_kayit)
            
            if tc:
                self._bakiye_dus(registry, tc, izin_tipi, gun)
                self._set_personel_pasif(registry, tc, izin_tipi, gun)

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

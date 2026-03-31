# -*- coding: utf-8 -*-
"""
Hızlı İzin Girişi Dialog
"""
import uuid
from datetime import timedelta
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QDateEdit, QSpinBox, QGridLayout, QAbstractSpinBox,
    QDialog
)
from PySide6.QtGui import QCursor

from core.logger import logger
from core.date_utils import parse_date
from core.hata_yonetici import bilgi_goster, hata_goster, uyari_goster
from core.di import get_izin_service
from database.repository_registry import RepositoryRegistry

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

        self.setProperty("bg-role", "page")

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
        lbl_izin.setProperty("style-role", "label")
        form.addWidget(lbl_izin, 0, 0)
        self.ui["izin_tipi"] = QComboBox()
        self.ui["izin_tipi"].setProperty("style-role", "combo")
        form.addWidget(self.ui["izin_tipi"], 0, 1)

        # Max gün uyarı
        self.ui["max_gun_label"] = QLabel("")
        self.ui["max_gun_label"].setProperty("style-role", "stat-label")
        form.addWidget(self.ui["max_gun_label"], 1, 1)

        # Başlama Tarihi
        lbl_baslama = QLabel("Başlama Tarihi")
        lbl_baslama.setProperty("style-role", "label")
        form.addWidget(lbl_baslama, 2, 0)
        self.ui["baslama"] = QDateEdit()
        self.ui["baslama"].setDate(QDate.currentDate())
        self.ui["baslama"].setCalendarPopup(True)
        self.ui["baslama"].setDisplayFormat("dd.MM.yyyy")
        self.ui["baslama"].setProperty("style-role", "date")
        form.addWidget(self.ui["baslama"], 2, 1)

        # Süre
        lbl_gun = QLabel("Süre (Gün)")
        lbl_gun.setProperty("style-role", "label")
        form.addWidget(lbl_gun, 3, 0)
        self.ui["gun"] = QSpinBox()
        self.ui["gun"].setMinimum(1)
        self.ui["gun"].setMaximum(365)
        self.ui["gun"].setValue(1)
        self.ui["gun"].setProperty("style-role", "spin")
        form.addWidget(self.ui["gun"], 3, 1)

        # Bitiş Tarihi
        lbl_bitis = QLabel("İşe Dönüş Tarihi")
        lbl_bitis.setProperty("style-role", "label")
        form.addWidget(lbl_bitis, 4, 0)
        self.ui["bitis"] = QDateEdit()
        self.ui["bitis"].setReadOnly(True)
        self.ui["bitis"].setDisplayFormat("dd.MM.yyyy")
        self.ui["bitis"].setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.ui["bitis"].setProperty("style-role", "date")
        form.addWidget(self.ui["bitis"], 4, 1)

        main.addLayout(form)
        main.addStretch()

        # Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_iptal = QPushButton("İptal")
        btn_iptal.setProperty("style-role", "danger")
        btn_iptal.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_iptal.clicked.connect(self.cancelled.emit)
        btn_layout.addWidget(btn_iptal)
        btn_kaydet = QPushButton("Kaydet")
        btn_kaydet.setProperty("style-role", "action")
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
        tip_lower = tip_text.lower()
        is_yillik_izin = ("yıllık" in tip_lower) or ("yillik" in tip_lower)
        tc = str(self._personel.get("KimlikNo", "") or "")

        max_gun = None
        try:
            izin_svc = get_izin_service(self._db)
            if izin_svc and tip_text and tc:
                max_gun = izin_svc.get_izin_max_gun(tc=tc, izin_tipi=tip_text).veri or []
        except Exception as e:
            logger.error(f"Hızlı izin max gün hesaplama hatası: {e}")

        # fallback: sabit tanım
        if max_gun is None:
            fallback = self._izin_max_gun.get(tip_text, 0)
            max_gun = fallback if fallback > 0 else None

        if max_gun is not None:
            if max_gun > 0:
                self.ui["gun"].setMaximum(max_gun)
                if not is_yillik_izin:
                    # Yıllık izin dışındaki tiplerde gün otomatik olarak max seçilsin.
                    self.ui["gun"].setValue(max_gun)
                elif self.ui["gun"].value() > max_gun:
                    self.ui["gun"].setValue(max_gun)
                self.ui["max_gun_label"].setText(f"Bu izin tipi için en fazla {max_gun} gün girilebilir.")
            else:
                self.ui["gun"].setMaximum(365)
                self.ui["max_gun_label"].setText("Bu izin tipi için kullanılabilir gün yok.")
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
            izin_svc = get_izin_service(self._db)
            registry = RepositoryRegistry(self._db)

            # Max gün kontrolü (kesin engelleme)
            ok_limit, limit_msg = izin_svc.validate_izin_sure_limit(
                tc=str(tc or ""), izin_tipi=izin_tipi, gun=gun
            )
            if not ok_limit:
                uyari_goster(self, limit_msg, "Limit Aşımı")
                return
            
            # Çakışma kontrolü
            giris_repo = izin_svc.get_izin_giris_repo().veri
            all_izin = giris_repo.get_all() if giris_repo else []
            yeni_bas = parse_date(baslama_str)
            yeni_bit = parse_date(bitis_str)
            for kayit in all_izin:
                if str(kayit.get("Durum", "")) == "İptal": continue
                if str(kayit.get("Personelid", "")) != tc: continue
                vt_bas = parse_date(kayit.get("BaslamaTarihi", ""))
                vt_bit = parse_date(kayit.get("BitisTarihi", ""))
                if vt_bas and vt_bit and yeni_bas and yeni_bit and (yeni_bas <= vt_bit) and (yeni_bit >= vt_bas):
                    uyari_goster(self, "Bu tarihlerde zaten bir izin kaydı mevcut.", "Çakışma")
                    return

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
                izin_svc.set_personel_pasif(str(tc), izin_tipi, gun)

            bilgi_goster(self, "İzin başarıyla kaydedildi.", "Başarılı")
            self.izin_kaydedildi.emit()
            self.accept()

        except Exception as e:
            logger.error(f"Hızlı izin kaydetme hatası: {e}")
            hata_goster(self, f"İşlem başarısız: {e}")

    def _bakiye_dus(self, registry, tc, izin_tipi, gun):
        try:
            izin_bilgi = registry.get("Izin_Bilgi").get_by_id(tc)
            if not izin_bilgi: return
            if izin_tipi == "Yıllık İzin":
                yeni_kul = float(izin_bilgi.get("YillikKullanilan") or 0) + gun
                yeni_kal = float(izin_bilgi.get("YillikKalan") or 0) - gun
                registry.get("Izin_Bilgi").update(tc, {"YillikKullanilan": yeni_kul, "YillikKalan": yeni_kal})
            elif izin_tipi == "Şua İzni":
                yeni_kul = float(izin_bilgi.get("SuaKullanilan") or 0) + gun
                yeni_kal = float(izin_bilgi.get("SuaKalan") or 0) - gun
                registry.get("Izin_Bilgi").update(tc, {"SuaKullanilan": yeni_kul, "SuaKalan": yeni_kal})
            elif izin_tipi in ["Rapor", "Mazeret İzni", "Sağlık Raporu"]:
                yeni_top = float(izin_bilgi.get("RaporMazeretTop") or 0) + gun
                registry.get("Izin_Bilgi").update(tc, {"RaporMazeretTop": yeni_top})
        except Exception as e:
            logger.error(f"Bakiye düşme hatası: {e}")

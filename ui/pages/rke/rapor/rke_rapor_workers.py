# -*- coding: utf-8 -*-
"""
RKE Rapor Worker Thread'leri
������������������������������
� VeriYukleyiciThread    � RKE_List + RKE_Muayene birle�tirerek rapor verisi haz�rlar
� RaporOlusturucuThread  � PDF olu�turur ve Drive'a y�kler

Rapor modlar�:
    1 � Genel Kontrol Raporu
    2 � Hurda (HEK) Raporu
    3 � Personel Bazl� Raporlar (ki�i � tarih gruplar�)
"""
import os
import datetime

from PySide6.QtCore import QThread, Signal

from core.logger import logger
from core.hata_yonetici import exc_logla

from .rke_pdf_builder import html_genel_rapor, html_hurda_rapor, pdf_olustur


# ��� Tarih ayr��t�rma (iki yerde kullan�l�rd�, art�k tek yerde) ��������������

def _parse_date(s: str) -> datetime.date:
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except Exception:
            continue
    return datetime.date.min


# ===============================================
#  VER� Y�KLEYICI
# ===============================================

class VeriYukleyiciThread(QThread):
    """
    RKE_List ve RKE_Muayene tablolar�n� birle�tirerek
    raporlama i�in haz�r veri seti olu�turur.

    Sinyal: veri_hazir(data, abd_listesi, birim_listesi, tarih_listesi)
    """
    veri_hazir  = Signal(list, list, list, list)
    hata_olustu = Signal(str)

    def run(self):
        from database.sqlite_manager import SQLiteManager
        from core.di import get_registry
        db = None
        try:
            db       = SQLiteManager()
            registry = get_registry(db)

            # Envanter haritas�: EkipmanNo � {ABD, Birim, Cins, Pb}
            envanter_map = {
                str(row.get("EkipmanNo", "")).strip(): {
                    "ABD":   str(row.get("AnaBilimDali",   "")).strip(),
                    "Birim": str(row.get("Birim",          "")).strip(),
                    "Cins":  str(row.get("KoruyucuCinsi",  "")).strip(),
                    "Pb":    str(row.get("KursunEsdegeri", "")).strip(),
                }
                for row in registry.get("RKE_List").get_all()
                if str(row.get("EkipmanNo", "")).strip()
            }

            birlesik  = []
            abd_set   = set()
            birim_set = set()
            tarih_set = set()

            for row in registry.get("RKE_Muayene").get_all():
                eno   = str(row.get("EkipmanNo",      "")).strip()
                tarih = str(row.get("FMuayeneTarihi", "")).strip()
                fiz   = str(row.get("FizikselDurum",  "")).strip()
                sko   = str(row.get("SkopiDurum",     "")).strip()
                env   = envanter_map.get(eno, {})

                abd_set.add(env.get("ABD",   ""))
                birim_set.add(env.get("Birim", ""))
                if tarih:
                    tarih_set.add(tarih)

                sonuc = (
                    "Kullan�ma Uygun De�il"
                    if "De�il" in fiz or "De�il" in sko
                    else "Kullan�ma Uygun"
                )

                birlesik.append({
                    "EkipmanNo":   eno,
                    "Cins":        env.get("Cins",  ""),
                    "Pb":          env.get("Pb",    ""),
                    "Birim":       env.get("Birim", ""),
                    "ABD":         env.get("ABD",   ""),
                    "Tarih":       tarih,
                    "Fiziksel":    fiz,
                    "Skopi":       sko,
                    "Sonuc":       sonuc,
                    "KontrolEden": str(row.get("KontrolEdenUnvani", "")).strip(),
                    "Aciklama":    str(row.get("Aciklamalar",       "")).strip(),
                })

            sirali_tarih = sorted(tarih_set, key=_parse_date, reverse=True)

            self.veri_hazir.emit(
                birlesik,
                sorted(abd_set   - {""}),
                sorted(birim_set - {""}),
                sirali_tarih,
            )
        except Exception as e:
            exc_logla("RKERapor.VeriYukleyici", e)
            self.hata_olustu.emit(str(e))
        finally:
            if db:
                db.close()


# ===============================================
#  RAPOR OLU�TURUCU
# ===============================================

class RaporOlusturucuThread(QThread):
    """
    Se�ili mod ve verilerle PDF �retir, Drive'a y�kler.

    mod: 1 = Genel, 2 = Hurda, 3 = Personel Bazl�
    """
    log_mesaji  = Signal(str)
    islem_bitti = Signal()

    def __init__(self, mod: int, veriler: list, ozet: str):
        super().__init__()
        self._mod    = mod
        self._veriler = veriler
        self._ozet   = ozet

    def run(self):
        gecici_dosyalar = []
        zaman = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            if self._mod == 1:
                gecici_dosyalar += self._mod_genel(zaman)
            elif self._mod == 2:
                gecici_dosyalar += self._mod_hurda(zaman)
            elif self._mod == 3:
                gecici_dosyalar += self._mod_personel(zaman)
        except Exception as e:
            self.log_mesaji.emit(f"HATA: {e}")
            logger.error(f"RaporOlusturucu hatas�: {e}")
        finally:
            self._temizle(gecici_dosyalar)
            self.islem_bitti.emit()

    # �� Mod i�leyicileri ����������������������������������������������������

    def _mod_genel(self, zaman: str) -> list:
        if not self._veriler:
            self.log_mesaji.emit("UYARI: Rapor i�in veri bulunamad�.")
            return []
        dosya_adi = f"RKE_Genel_{zaman}.pdf"
        html = html_genel_rapor(self._veriler, self._ozet)
        if pdf_olustur(html, dosya_adi):
            self._yukle_drive(dosya_adi)
            return [dosya_adi]
        self.log_mesaji.emit("HATA: PDF olu�turulamad�.")
        return []

    def _mod_hurda(self, zaman: str) -> list:
        hurda = [v for v in self._veriler if "De�il" in v.get("Sonuc", "")]
        if not hurda:
            self.log_mesaji.emit("UYARI: Hurda aday� kay�t bulunamad�.")
            return []
        dosya_adi = f"RKE_Hurda_{zaman}.pdf"
        html = html_hurda_rapor(hurda)
        if pdf_olustur(html, dosya_adi):
            self._yukle_drive(dosya_adi)
            return [dosya_adi]
        self.log_mesaji.emit("HATA: Hurda PDF olu�turulamad�.")
        return []

    def _mod_personel(self, zaman: str) -> list:
        gruplar: dict = {}
        for item in self._veriler:
            key = (item.get("KontrolEden", ""), item.get("Tarih", ""))
            gruplar.setdefault(key, []).append(item)

        self.log_mesaji.emit(f"B�LG�: {len(gruplar)} farkl� rapor haz�rlan�yor...")
        dosyalar = []
        for (kisi, tarih), liste in gruplar.items():
            ad        = f"Rapor_{kisi}_{tarih}".replace(" ", "_")
            dosya_adi = f"{ad}_{zaman}.pdf"
            html = html_genel_rapor(liste, f"Kontrol�r: {kisi} � {tarih}")
            if pdf_olustur(html, dosya_adi):
                dosyalar.append(dosya_adi)
                self._yukle_drive(dosya_adi)
                self.log_mesaji.emit(f"BA�ARILI: {dosya_adi} y�klendi.")
        return dosyalar

    # �� Drive y�kleme ��������������������������������������������������������

    def _yukle_drive(self, dosya_adi: str):
        db = None
        try:
            from database.sqlite_manager import SQLiteManager
            from core.di import get_registry, get_cloud_adapter
            from database.google.utils import resolve_storage_target

            db             = SQLiteManager()
            registry       = get_registry(db)
            storage_target = resolve_storage_target(
                registry.get("Sabitler").get_all(), "RKE_Raporlar"
            )
            cloud = get_cloud_adapter()
            link  = cloud.upload_file(
                dosya_adi,
                parent_folder_id=storage_target["drive_folder_id"],
                offline_folder_name=storage_target["offline_folder_name"],
            )
            if link:
                hedef = "Drive'a y�klendi" if cloud.is_online and str(link).startswith("http") else "Yerel klas�re kaydedildi"
                self.log_mesaji.emit(f"BA�ARILI: {hedef}.")
            else:
                self.log_mesaji.emit("UYARI: Drive y�kleme atland�/ba�ar�s�z (offline olabilir).")
        except Exception as e:
            self.log_mesaji.emit(f"UYARI: Drive hatas�: {e}")
            logger.warning(f"Drive y�kleme hatas�: {e}")
        finally:
            if db:
                db.close()

    # �� Temizlik �������������������������������������������������������������

    @staticmethod
    def _temizle(dosyalar: list):
        for f in dosyalar:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception as e:
                logger.warning(f"Ge�ici dosya silinemedi: {f} � {e}")

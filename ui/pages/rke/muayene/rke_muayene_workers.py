# -*- coding: utf-8 -*-
"""
RKE Muayene Worker Thread'leri
────────────────────────────────
• VeriYukleyiciThread       – Tüm sayfa verilerini yükler
• KayitWorkerThread         – Tekli muayene kaydı + RKE_List güncelleme
• TopluKayitWorkerThread    – Toplu muayene kaydı + RKE_List güncelleme

RKE_List güncelleme kuralı (_guncelle_durum):
  - KontrolTarihi  ← fiziksel muayene tarihi
  - Durum          ← fiziksel VEYA skopi "Uygun Değil" ise "Kullanıma Uygun Değil",
                     ikisi de uygunsa "Kullanıma Uygun"
  - Aciklama       ← muayene açıklaması (üzerine yazılır)
"""
import time

from PySide6.QtCore import QThread, Signal

from core.logger import logger
from core.hata_yonetici import exc_logla


# ═══════════════════════════════════════════════
#  VERİ YÜKLEYİCİ
# ═══════════════════════════════════════════════

class VeriYukleyiciThread(QThread):
    """
    Sayfa açılışında ve yenileme sırasında tüm verileri arka planda yükler.
    Sinyal: veri_hazir(rke_data, teknik_acik, kontrol_edenler, birim_sorumlulari, tum_muayene)
    """
    veri_hazir  = Signal(list, list, list, list, list)
    hata_olustu = Signal(str)

    def run(self):
        from database.sqlite_manager import SQLiteManager
        from core.di import get_registry
        db = None
        try:
            db       = SQLiteManager()
            registry = get_registry(db)

            rke_data  = registry.get("RKE_List").get_all()
            all_sabit = registry.get("Sabitler").get_all()

            teknik = [
                str(x.get("MenuEleman", "")).strip()
                for x in all_sabit
                if x.get("Kod") == "RKE_Teknik" and x.get("MenuEleman", "").strip()
            ]

            tum_muayene = registry.get("RKE_Muayene").get_all()

            kontrol_edenler = sorted({
                str(r.get("KontrolEdenUnvani", "")).strip()
                for r in tum_muayene
                if str(r.get("KontrolEdenUnvani", "")).strip()
            })
            birim_sorumlulari = sorted({
                str(r.get("BirimSorumlusuUnvani", "")).strip()
                for r in tum_muayene
                if str(r.get("BirimSorumlusuUnvani", "")).strip()
            })

            self.veri_hazir.emit(
                rke_data, teknik, kontrol_edenler, birim_sorumlulari, tum_muayene
            )
        except Exception as e:
            exc_logla("RKEMuayene.VeriYukleyici", e)
            self.hata_olustu.emit(str(e))
        finally:
            if db:
                db.close()


# ═══════════════════════════════════════════════
#  ORTAK GÜNCELLEME MANTIĞI
# ═══════════════════════════════════════════════

def _hesapla_durum(fiziksel: str, skopi: str) -> str:
    """
    Her iki muayene de "Kullanıma Uygun" ise → "Kullanıma Uygun"
    Birinde bile "Değil" varsa → "Kullanıma Uygun Değil"
    """
    if "Değil" in fiziksel or "Değil" in skopi:
        return "Kullanıma Uygun Değil"
    return "Kullanıma Uygun"


def guncelle_rke_list(registry, veri: dict):
    """
    Muayene verisi kaydedildikten sonra RKE_List tablosunu günceller.

    Güncellenen alanlar:
      KontrolTarihi  ← FMuayeneTarihi
      Durum          ← fiziksel + skopi sonucuna göre hesaplanır
      Aciklama       ← muayene Aciklamalar alanından alınır
    """
    ekipman_no = str(veri.get("EkipmanNo", "")).strip()
    if not ekipman_no:
        return

    fiziksel  = str(veri.get("FizikselDurum", ""))
    skopi     = str(veri.get("SkopiDurum",    ""))
    aciklama  = str(veri.get("Aciklamalar",   "")).strip()
    tarih     = str(veri.get("FMuayeneTarihi","")).strip()

    yeni_durum = _hesapla_durum(fiziksel, skopi)

    repo_list = registry.get("RKE_List")
    target = next(
        (x for x in repo_list.get_all()
         if str(x.get("EkipmanNo", "")).strip() == ekipman_no),
        None,
    )
    if not target:
        logger.warning(f"RKE_List'te ekipman bulunamadı: {ekipman_no}")
        return

    guncelleme = {
        "Durum":         yeni_durum,
        "KontrolTarihi": tarih,
        "Aciklama":      aciklama,
    }
    repo_list.update(target["EkipmanNo"], guncelleme)
    logger.info(
        f"RKE_List güncellendi — {ekipman_no}: "
        f"Durum={yeni_durum}, Tarih={tarih}, Açıklama={aciklama!r}"
    )


# ═══════════════════════════════════════════════
#  TEKLİ KAYIT WORKER
# ═══════════════════════════════════════════════

class KayitWorkerThread(QThread):
    """
    Tek ekipman muayene kaydı ekler, RKE_List'i günceller,
    varsa rapor dosyasını Drive'a yükler.
    """
    kayit_tamam = Signal(str)
    hata_olustu = Signal(str)

    def __init__(self, veri_dict: dict, dosya_yolu: str = None):
        super().__init__()
        self._veri       = veri_dict
        self._dosya_yolu = dosya_yolu

    def run(self):
        from database.sqlite_manager import SQLiteManager
        from core.di import get_registry
        db = None
        try:
            db       = SQLiteManager()
            registry = get_registry(db)

            # Drive yükleme
            if self._dosya_yolu:
                from core.di import get_cloud_adapter
                from database.google.utils import resolve_storage_target
                cloud          = get_cloud_adapter()
                storage_target = resolve_storage_target(
                    registry.get("Sabitler").get_all(), "RKE_Raporlar"
                )
                link = cloud.upload_file(
                    self._dosya_yolu,
                    parent_folder_id=storage_target["drive_folder_id"],
                    offline_folder_name=storage_target["offline_folder_name"],
                )
                if link:
                    self._veri["Rapor"] = link
                else:
                    logger.info("RKE Muayene: rapor yükleme atlandı/başarısız (offline olabilir)")

            # Muayene kaydı
            registry.get("RKE_Muayene").insert(self._veri)

            # RKE_List: Durum + KontrolTarihi + Aciklama güncelle
            guncelle_rke_list(registry, self._veri)

            self.kayit_tamam.emit("Kayıt Başarılı")
        except Exception as e:
            exc_logla("RKEMuayene.KayitWorker", e)
            self.hata_olustu.emit(str(e))
        finally:
            if db:
                db.close()


# ═══════════════════════════════════════════════
#  TOPLU KAYIT WORKER
# ═══════════════════════════════════════════════

class TopluKayitWorkerThread(QThread):
    """
    Birden fazla ekipman için toplu muayene kaydı ekler.
    Her ekipman için ortak_veri kopyalanır, EkipmanNo ayrıştırılır.
    """
    kayit_tamam = Signal(str)
    hata_olustu = Signal(str)

    def __init__(self, ekipman_listesi: list, ortak_veri: dict, dosya_yolu: str = None):
        super().__init__()
        self._ekipmanlar = ekipman_listesi
        self._ortak_veri = ortak_veri
        self._dosya_yolu = dosya_yolu

    def run(self):
        from database.sqlite_manager import SQLiteManager
        from core.di import get_registry
        db = None
        try:
            db       = SQLiteManager()
            registry = get_registry(db)

            repo_muayene = registry.get("RKE_Muayene")

            # Ortak rapor dosyası Drive'a bir kez yüklenir
            dosya_link = ""
            if self._dosya_yolu:
                from core.di import get_cloud_adapter
                from database.google.utils import resolve_storage_target
                cloud          = get_cloud_adapter()
                storage_target = resolve_storage_target(
                    registry.get("Sabitler").get_all(), "RKE_Raporlar"
                )
                dosya_link = cloud.upload_file(
                    self._dosya_yolu,
                    parent_folder_id=storage_target["drive_folder_id"],
                    offline_folder_name=storage_target["offline_folder_name"],
                ) or ""

            for ekipman_no in self._ekipmanlar:
                item = self._ortak_veri.copy()
                item["EkipmanNo"] = ekipman_no
                item["KayitNo"]   = f"M-{int(time.time())}-{ekipman_no}"
                if dosya_link:
                    item["Rapor"] = dosya_link

                repo_muayene.insert(item)

                # RKE_List: Durum + KontrolTarihi + Aciklama güncelle
                guncelle_rke_list(registry, item)

            self.kayit_tamam.emit("Toplu Kayıt Başarılı")
        except Exception as e:
            exc_logla("RKEMuayene.TopluKayitWorker", e)
            self.hata_olustu.emit(str(e))
        finally:
            if db:
                db.close()

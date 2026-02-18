# -*- coding: utf-8 -*-
"""
RKE Muayene Worker Thread'leri
ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½
ï¿½ VeriYukleyiciThread       ï¿½  sayfa verilerini yï¿½kler
ï¿½ KayitWorkerThread         ï¿½ Tekli muayene kaydï¿½ + durum gï¿½ncelleme
ï¿½ TopluKayitWorkerThread    ï¿½ Toplu muayene kaydï¿½ + durum gï¿½ncelleme

Drive yï¿½kleme iï¿½in projenin mevcut upload altyapï¿½sï¿½ kullanï¿½lï¿½r;
baï¿½ï¿½msï¿½z bir yardï¿½mcï¿½ yazï¿½lmamï¿½ï¿½tï¿½r.
"""
import time

from PySide6.QtCore import QThread, Signal

from core.logger import logger
from core.hata_yonetici import exc_logla


# ===============================================
#  VERÄ° YÃœKLEYÄ°CÄ°
# ===============================================

class VeriYukleyiciThread(QThread):
    """
    Sayfa aÃ§Ä±lÄ±ÅŸÄ±nda ve yenileme sÄ±rasÄ±nda tÃ¼m verileri arka planda yÃ¼kler.

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

            self.veri_hazir.emit(rke_data, teknik, kontrol_edenler, birim_sorumlulari, tum_muayene)
        except Exception as e:
            exc_logla("RKEMuayene.VeriYukleyici", e)
            self.hata_olustu.emit(str(e))
        finally:
            if db:
                db.close()


# ===============================================
#  TEKLÄ° KAYIT WORKER
# ===============================================

class KayitWorkerThread(QThread):
    """
    Tek ekipman muayene kaydÄ± ekler, RKE_List durumunu gÃ¼nceller,
    varsa rapor dosyasÄ±nÄ± Drive'a yÃ¼kler.
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

            # Drive yÃ¼kleme
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
                    logger.info("RKE Muayene: rapor yÃ¼kleme atlandÄ±/baÅŸarÄ±sÄ±z (offline olabilir)")

            # Muayene kaydÄ±
            registry.get("RKE_Muayene").insert(self._veri)

            # RKE_List durum gÃ¼ncelle
            self._guncelle_durum(registry, self._veri)

            self.kayit_tamam.emit("KayÄ±t BaÅŸarÄ±lÄ±")
        except Exception as e:
            exc_logla("RKEMuayene.KayitWorker", e)
            self.hata_olustu.emit(str(e))
        finally:
            if db:
                db.close()

    @staticmethod
    def _guncelle_durum(registry, veri: dict):
        """Muayene sonucuna gÃ¶re RKE_List tablosundaki durumu gÃ¼nceller."""
        ekipman_no = veri.get("EkipmanNo")
        if not ekipman_no:
            return
        yeni_durum = (
            "KullanÄ±ma Uygun DeÄŸil"
            if "DeÄŸil" in veri.get("FizikselDurum", "") or "DeÄŸil" in veri.get("SkopiDurum", "")
            else "KullanÄ±ma Uygun"
        )
        repo_list = registry.get("RKE_List")
        target    = next(
            (x for x in repo_list.get_all() if str(x.get("EkipmanNo")) == str(ekipman_no)),
            None,
        )
        if target and target.get("EkipmanNo"):
            repo_list.update(target["EkipmanNo"], {
                "Durum":         yeni_durum,
                "KontrolTarihi": veri.get("FMuayeneTarihi"),
            })


# ===============================================
#  TOPLU KAYIT WORKER
# ===============================================

class TopluKayitWorkerThread(QThread):
    """
    Birden fazla ekipman iÃ§in toplu muayene kaydÄ± ekler.
    Her ekipman iÃ§in aynÄ± ortak_veri kullanÄ±lÄ±r; EkipmanNo alanÄ± ekipmana gÃ¶re set edilir.
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
            repo_list    = registry.get("RKE_List")
            all_rke      = repo_list.get_all()

            # Ortak rapor dosyasÄ± Drive'a bir kez yÃ¼klenir
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

                # Durum gÃ¼ncelle
                yeni_durum = (
                    "KullanÄ±ma Uygun DeÄŸil"
                    if "DeÄŸil" in item.get("FizikselDurum", "") or "DeÄŸil" in item.get("SkopiDurum", "")
                    else "KullanÄ±ma Uygun"
                )
                target = next(
                    (x for x in all_rke if str(x.get("EkipmanNo")) == str(ekipman_no)),
                    None,
                )
                if target and target.get("EkipmanNo"):
                    repo_list.update(target["EkipmanNo"], {
                        "Durum":         yeni_durum,
                        "KontrolTarihi": item.get("FMuayeneTarihi"),
                    })

            self.kayit_tamam.emit("Toplu KayÄ±t BaÅŸarÄ±lÄ±")
        except Exception as e:
            exc_logla("RKEMuayene.TopluKayitWorker", e)
            self.hata_olustu.emit(str(e))
        finally:
            if db:
                db.close()

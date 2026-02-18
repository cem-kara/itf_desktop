# -*- coding: utf-8 -*-
"""
RKE Muayene Worker Thread'leri
��������������������������������
� VeriYukleyiciThread       �  sayfa verilerini y�kler
� KayitWorkerThread         � Tekli muayene kayd� + durum g�ncelleme
� TopluKayitWorkerThread    � Toplu muayene kayd� + durum g�ncelleme

Drive y�kleme i�in projenin mevcut upload altyap�s� kullan�l�r;
ba��ms�z bir yard�mc� yaz�lmam��t�r.
"""
import time

from PySide6.QtCore import QThread, Signal

from core.logger import logger
from core.hata_yonetici import exc_logla


# ===============================================
#  VERİ YÜKLEYİCİ
# ===============================================

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

            self.veri_hazir.emit(rke_data, teknik, kontrol_edenler, birim_sorumlulari, tum_muayene)
        except Exception as e:
            exc_logla("RKEMuayene.VeriYukleyici", e)
            self.hata_olustu.emit(str(e))
        finally:
            if db:
                db.close()


# ===============================================
#  TEKLİ KAYIT WORKER
# ===============================================

class KayitWorkerThread(QThread):
    """
    Tek ekipman muayene kaydı ekler, RKE_List durumunu günceller,
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

            # RKE_List durum güncelle
            self._guncelle_durum(registry, self._veri)

            self.kayit_tamam.emit("Kayıt Başarılı")
        except Exception as e:
            exc_logla("RKEMuayene.KayitWorker", e)
            self.hata_olustu.emit(str(e))
        finally:
            if db:
                db.close()

    @staticmethod
    def _guncelle_durum(registry, veri: dict):
        """Muayene sonucuna göre RKE_List tablosundaki durumu günceller."""
        ekipman_no = veri.get("EkipmanNo")
        if not ekipman_no:
            return
        yeni_durum = (
            "Kullanıma Uygun Değil"
            if "Değil" in veri.get("FizikselDurum", "") or "Değil" in veri.get("SkopiDurum", "")
            else "Kullanıma Uygun"
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
    Birden fazla ekipman için toplu muayene kaydı ekler.
    Her ekipman için aynı ortak_veri kullanılır; EkipmanNo alanı ekipmana göre set edilir.
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

                # Durum güncelle
                yeni_durum = (
                    "Kullanıma Uygun Değil"
                    if "Değil" in item.get("FizikselDurum", "") or "Değil" in item.get("SkopiDurum", "")
                    else "Kullanıma Uygun"
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

            self.kayit_tamam.emit("Toplu Kayıt Başarılı")
        except Exception as e:
            exc_logla("RKEMuayene.TopluKayitWorker", e)
            self.hata_olustu.emit(str(e))
        finally:
            if db:
                db.close()

"""
KalibrasyonService — Cihaz kalibrasyon işlemleri için service katmanı
Sorumluluklar:
- Kalibrasyon verisi yükleme
- Kalibrasyon türleri ve durumları
- Kalibrasyon kaydı
"""
from typing import Optional, List, Dict
from core.hata_yonetici import SonucYonetici

from database.repository_registry import RepositoryRegistry


class KalibrasyonService:
    """Kalibrasyon işlemleri hizmeti"""
    
    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("RepositoryRegistry boş olamaz")
        self._r = registry
    
    def get_kalibrasyon_listesi(self, cihaz_id: Optional[str] = None) -> SonucYonetici:
        """Kalibrasyon listesini getir."""
        try:
            rows = self._r.get("Kalibrasyon").get_all() or []
            if cihaz_id:
                rows = [r for r in rows if str(r.get("Cihazid", "")).strip() == str(cihaz_id).strip()]
            return SonucYonetici.tamam(veri=rows)
        except Exception as e:
            return SonucYonetici.hata(e, "KalibrasyonService.get_kalibrasyon_listesi")
    
    def get_kalibrasyon_tipleri(self) -> SonucYonetici:
        """Kalibrasyon türlerini getir."""
        try:
            sabitler = self._r.get("Sabitler").get_all() or []
            tipleri = [
                str(s.get("MenuEleman", "")).strip()
                for s in sabitler
                if str(s.get("Kod", "")).strip() == "KalibrasyonTipi"
            ]
            return SonucYonetici.tamam(veri=sorted(list(set(tipleri))))
        except Exception as e:
            return SonucYonetici.hata(e, "KalibrasyonService.get_kalibrasyon_tipleri")
    
    def get_cihaz_listesi(self) -> SonucYonetici:
        """Cihaz listesini getir."""
        try:
            rows = self._r.get("Cihazlar").get_all() or []
            return SonucYonetici.tamam(veri=rows)
        except Exception as e:
            return SonucYonetici.hata(e, "KalibrasyonService.get_cihaz_listesi")
    
    def kaydet(self, veri: Dict, guncelle: bool = False) -> SonucYonetici:
        """Kalibrasyon kaydı ekle veya güncelle."""
        try:
            repo = self._r.get("Kalibrasyon")
            if guncelle:
                kal_id = veri.get("Kalid")
                if not kal_id:
                    return SonucYonetici.hata(Exception("Güncelleme için Kalid gerekli"), "KalibrasyonService.kaydet")
                repo.update(kal_id, veri)
                return SonucYonetici.tamam("Kalibrasyon güncellendi.")
            else:
                repo.insert(veri)
                return SonucYonetici.tamam("Kalibrasyon eklendi.")
        except Exception as e:
            return SonucYonetici.hata(e, "KalibrasyonService.kaydet")
    
    def sil(self, kal_id: str) -> SonucYonetici:
        """Kalibrasyon kaydını sil."""
        try:
            self._r.get("Kalibrasyon").delete(kal_id)
            return SonucYonetici.tamam("Kalibrasyon silindi.")
        except Exception as e:
            return SonucYonetici.hata(e, "KalibrasyonService.sil")

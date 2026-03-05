"""
KalibrasyonService — Cihaz kalibrasyon işlemleri için service katmanı
Sorumluluklar:
- Kalibrasyon verisi yükleme
- Kalibrasyon türleri ve durumları
- Kalibrasyon kaydı
"""
from typing import Optional, List, Dict
from core.logger import logger
from database.repository_registry import RepositoryRegistry


class KalibrasyonService:
    """Kalibrasyon işlemleri hizmeti"""
    
    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("RepositoryRegistry boş olamaz")
        self._r = registry
    
    def get_kalibrasyon_listesi(self, cihaz_id: Optional[str] = None) -> List[Dict]:
        """Kalibrasyon listesini getir."""
        try:
            rows = self._r.get("Kalibrasyon").get_all() or []
            if cihaz_id:
                rows = [r for r in rows if str(r.get("Cihazid", "")).strip() == str(cihaz_id).strip()]
            return rows
        except Exception as e:
            logger.error(f"Kalibrasyon listesi yükleme hatası: {e}")
            return []
    
    def get_kalibrasyon_tipleri(self) -> List[str]:
        """Kalibrasyon türlerini getir."""
        try:
            sabitler = self._r.get("Sabitler").get_all() or []
            tipleri = [
                str(s.get("MenuEleman", "")).strip()
                for s in sabitler
                if str(s.get("Kod", "")).strip() == "KalibrasyonTipi"
            ]
            return sorted(list(set(tipleri)))
        except Exception as e:
            logger.error(f"Kalibrasyon türleri yükleme hatası: {e}")
            return []
    
    def get_cihaz_listesi(self) -> List[Dict]:
        """Cihaz listesini getir."""
        try:
            return self._r.get("Cihazlar").get_all() or []
        except Exception as e:
            logger.error(f"Cihaz listesi yükleme hatası: {e}")
            return []
    
    def kaydet(self, veri: Dict, guncelle: bool = False) -> bool:
        """Kalibrasyon kaydı ekle veya güncelle."""
        try:
            repo = self._r.get("Kalibrasyon")
            if guncelle:
                kal_id = veri.get("Kaid")
                if not kal_id:
                    return False
                repo.update(kal_id, veri)
            else:
                repo.insert(veri)
            return True
        except Exception as e:
            logger.error(f"Kalibrasyon kaydet hatası: {e}")
            return False
    
    def sil(self, kal_id: str) -> bool:
        """Kalibrasyon kaydını sil."""
        try:
            self._r.get("Kalibrasyon").delete(kal_id)
            return True
        except Exception as e:
            logger.error(f"Kalibrasyon silme hatası: {e}")
            return False

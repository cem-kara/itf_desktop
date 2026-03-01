"""
BakimService — Periyodik bakım işlemleri için service katmanı
Sorumluluklar:
- Bakım verisi yükleme ve filtreleme
- Bakım türleri listesi
- Cihaz bilgileri
- Bakım kaydı (INSERT/UPDATE)
"""
from typing import Optional, List, Dict
from core.logger import logger
from database.repository_registry import RepositoryRegistry


class BakimService:
    """Periyodik bakım işlemleri hizmeti"""
    
    def __init__(self, registry: RepositoryRegistry):
        """
        Servis oluştur.
        
        Args:
            registry: RepositoryRegistry örneği
        """
        if not registry:
            raise ValueError("RepositoryRegistry boş olamaz")
        self._r = registry
    
    def get_bakim_listesi(self, cihaz_id: Optional[str] = None) -> List[Dict]:
        """
        Bakım listesini getir.
        
        Args:
            cihaz_id: Filtreleme için cihaz ID'si (isteğe bağlı)
        
        Returns:
            Bakım kayıtları, planlanan tarihe göre DESC sıralanmış
        """
        try:
            rows = self._r.get("Periyodik_Bakim").get_all() or []
            
            # Cihaz ID'sine göre filtrele
            if cihaz_id:
                rows = [
                    r for r in rows 
                    if str(r.get("Cihazid", "")).strip() == str(cihaz_id).strip()
                ]
            
            # Planlanan tarihe göre DESC sırala
            return sorted(
                rows,
                key=lambda r: r.get("PlanlananTarih") or "",
                reverse=True
            )
        except Exception as e:
            logger.error(f"Bakım listesi yükleme hatası: {e}")
            return []
    
    def get_bakim_tipleri(self) -> List[str]:
        """
        Bakım türlerini getir.
        
        Returns:
            Bakım türleri listesi
        """
        try:
            sabitler = self._r.get("Sabitler").get_all() or []
            tipleri = [
                str(s.get("MenuEleman", "")).strip()
                for s in sabitler
                if str(s.get("Kod", "")).strip() == "BakimTipi"
                and str(s.get("MenuEleman", "")).strip()
            ]
            return sorted(list(set(tipleri)))  # Tekrarları temizle, A-Z'ye sırala
        except Exception as e:
            logger.error(f"Bakım türleri yükleme hatası: {e}")
            return []
    
    def get_cihaz_listesi(self) -> List[Dict]:
        """
        Cihaz listesini getir.
        
        Returns:
            Tüm cihazlar
        """
        try:
            return self._r.get("Cihazlar").get_all() or []
        except Exception as e:
            logger.error(f"Cihaz listesi yükleme hatası: {e}")
            return []
    
    def get_cihaz_adlari(self) -> List[str]:
        """
        Cihaz adlarını getir (formlar için).
        
        Returns:
            Cihaz adları listesi
        """
        cihazlar = self.get_cihaz_listesi()
        adlar = [
            str(c.get("CihazAdi", "")).strip()
            for c in cihazlar
            if str(c.get("CihazAdi", "")).strip()
        ]
        return sorted(list(set(adlar)))
    
    def get_cihaz(self, cihaz_id: str) -> Optional[Dict]:
        """
        Tek bir cihazı getir.
        
        Args:
            cihaz_id: Cihaz ID'si
        
        Returns:
            Cihaz kaydı veya None
        """
        try:
            return self._r.get("Cihazlar").get_by_pk(cihaz_id)
        except Exception as e:
            logger.error(f"Cihaz '{cihaz_id}' yükleme hatası: {e}")
            return None
    
    def kaydet(self, veri: Dict, guncelle: bool = False) -> bool:
        """
        Bakım kaydı ekle veya güncelle.
        
        Args:
            veri: Bakım verisi
            guncelle: True ise UPDATE, False ise INSERT
        
        Returns:
            Başarılı ise True
        """
        try:
            repo = self._r.get("Periyodik_Bakim")
            if guncelle:
                plan_id = veri.get("Planid")
                if not plan_id:
                    logger.error("UPDATE için Planid gerekli")
                    return False
                repo.update(plan_id, veri)
                logger.info(f"Bakım planı #{plan_id} güncellendi")
            else:
                repo.insert(veri)
                logger.info("Yeni bakım planı oluşturuldu")
            return True
        except Exception as e:
            logger.error(f"Bakım kaydet hatası: {e}")
            return False
    
    def sil(self, plan_id: str) -> bool:
        """
        Bakım planını sil.
        
        Args:
            plan_id: Bakım planı ID'si
        
        Returns:
            Başarılı ise True
        """
        try:
            self._r.get("Periyodik_Bakim").delete(plan_id)
            logger.info(f"Bakım planı #{plan_id} silindi")
            return True
        except Exception as e:
            logger.error(f"Bakım silme hatası: {e}")
            return False

"""
ArizaService — Hatalı ve arızalı cihazlar işlemleri için service katmanı
Sorumluluklar:
- Arıza verisi yükleme ve filtreleme
- Arıza türleri ve durumları listesi
- Arıza kaydı (INSERT/UPDATE/DELETE)
"""
from typing import Optional, List, Dict
from core.logger import logger
from database.repository_registry import RepositoryRegistry


class ArizaService:
    """Arıza işlemleri hizmeti"""
    
    def __init__(self, registry: RepositoryRegistry):
        """
        Servis oluştur.
        
        Args:
            registry: RepositoryRegistry örneği
        """
        if not registry:
            raise ValueError("RepositoryRegistry boş olamaz")
        self._r = registry
    
    def get_ariza_listesi(self, cihaz_id: Optional[str] = None) -> List[Dict]:
        """
        Arıza listesini getir.
        
        Args:
            cihaz_id: Filtreleme için cihaz ID'si (isteğe bağlı)
        
        Returns:
            Arıza kayıtları
        """
        try:
            rows = self._r.get("Cihaz_Ariza").get_all() or []
            
            # Cihaz ID'sine göre filtrele
            if cihaz_id:
                rows = [
                    r for r in rows 
                    if str(r.get("Cihazid", "")).strip() == str(cihaz_id).strip()
                ]
            
            return rows
        except Exception as e:
            logger.error(f"Arıza listesi yükleme hatası: {e}")
            return []
    
    def get_ariza_tipleri(self) -> List[str]:
        """
        Arıza türlerini getir.
        
        Returns:
            Arıza türleri listesi
        """
        try:
            sabitler = self._r.get("Sabitler").get_all() or []
            tipleri = [
                str(s.get("MenuEleman", "")).strip()
                for s in sabitler
                if str(s.get("Kod", "")).strip() == "ArızaTipi"
                and str(s.get("MenuEleman", "")).strip()
            ]
            return sorted(list(set(tipleri)))
        except Exception as e:
            logger.error(f"Arıza türleri yükleme hatası: {e}")
            return []
    
    def get_ariza_durumlari(self) -> List[str]:
        """
        Arıza durumlarını getir.
        
        Returns:
            Arıza durumları listesi
        """
        try:
            sabitler = self._r.get("Sabitler").get_all() or []
            durumlar = [
                str(s.get("MenuEleman", "")).strip()
                for s in sabitler
                if str(s.get("Kod", "")).strip() == "ArızaDurumu"
                and str(s.get("MenuEleman", "")).strip()
            ]
            return sorted(list(set(durumlar)))
        except Exception as e:
            logger.error(f"Arıza durumları yükleme hatası: {e}")
            return []
    
    def get_oncelik_seviyeleri(self) -> List[str]:
        """
        Arıza öncelik seviyelerini getir.
        
        Returns:
            Öncelik seviyeleri listesi
        """
        try:
            sabitler = self._r.get("Sabitler").get_all() or []
            seviyeler = [
                str(s.get("MenuEleman", "")).strip()
                for s in sabitler
                if str(s.get("Kod", "")).strip() == "Oncelik"
                and str(s.get("MenuEleman", "")).strip()
            ]
            return sorted(list(set(seviyeler)))
        except Exception as e:
            logger.error(f"Öncelik seviyeleri yükleme hatası: {e}")
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
        Arıza kaydı ekle veya güncelle.
        
        Args:
            veri: Arıza verisi
            guncelle: True ise UPDATE, False ise INSERT
        
        Returns:
            Başarılı ise True
        """
        try:
            repo = self._r.get("Cihaz_Ariza")
            if guncelle:
                ariza_id = veri.get("ArizaId")
                if not ariza_id:
                    logger.error("UPDATE için ArizaId gerekli")
                    return False
                repo.update(ariza_id, veri)
                logger.info(f"Arıza #{ariza_id} güncellendi")
            else:
                repo.insert(veri)
                logger.info("Yeni arıza kaydı oluşturuldu")
            return True
        except Exception as e:
            logger.error(f"Arıza kaydet hatası: {e}")
            return False
    
    def sil(self, ariza_id: str) -> bool:
        """
        Arıza kaydını sil.
        
        Args:
            ariza_id: Arıza ID'si
        
        Returns:
            Başarılı ise True
        """
        try:
            self._r.get("Cihaz_Ariza").delete(ariza_id)
            logger.info(f"Arıza #{ariza_id} silindi")
            return True
        except Exception as e:
            logger.error(f"Arıza silme hatası: {e}")
            return False

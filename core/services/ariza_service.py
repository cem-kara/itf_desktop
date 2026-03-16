"""
ArizaService — Hatalı ve arızalı cihazlar işlemleri için service katmanı
Sorumluluklar:
- Arıza verisi yükleme ve filtreleme
- Arıza türleri ve durumları listesi
- Arıza kaydı (INSERT/UPDATE/DELETE)
"""
from typing import Optional, List, Dict
from core.hata_yonetici import SonucYonetici
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
    
    def get_ariza_listesi(self, cihaz_id: Optional[str] = None) -> SonucYonetici:
        """
        Arıza listesini getir.
        
        Args:
            cihaz_id: Filtreleme için cihaz ID'si (isteğe bağlı)
        
        Returns:
            SonucYonetici
        """
        try:
            rows = self._r.get("Cihaz_Ariza").get_all() or []
            if cihaz_id:
                rows = [
                    r for r in rows
                    if str(r.get("Cihazid", "")).strip() == str(cihaz_id).strip()
                ]
            return SonucYonetici.tamam(veri=rows)
        except Exception as e:
            return SonucYonetici.hata(e, "ArizaService.get_ariza_listesi")
    
    def get_ariza_tipleri(self) -> SonucYonetici:
        """
        Arıza türlerini getir.
        
        Returns:
            SonucYonetici
        """
        try:
            sabitler = self._r.get("Sabitler").get_all() or []
            tipleri = [
                str(s.get("MenuEleman", "")).strip()
                for s in sabitler
                if str(s.get("Kod", "")).strip() == "ArızaTipi"
                and str(s.get("MenuEleman", "")).strip()
            ]
            return SonucYonetici.tamam(veri=sorted(list(set(tipleri))))
        except Exception as e:
            return SonucYonetici.hata(e, "ArizaService.get_ariza_tipleri")
    
    def get_ariza_durumlari(self) -> SonucYonetici:
        """
        Arıza durumlarını getir.
        
        Returns:
            SonucYonetici
        """
        try:
            sabitler = self._r.get("Sabitler").get_all() or []
            durumlar = [
                str(s.get("MenuEleman", "")).strip()
                for s in sabitler
                if str(s.get("Kod", "")).strip() == "ArızaDurumu"
                and str(s.get("MenuEleman", "")).strip()
            ]
            return SonucYonetici.tamam(veri=sorted(list(set(durumlar))))
        except Exception as e:
            return SonucYonetici.hata(e, "ArizaService.get_ariza_durumlari")
    
    def get_oncelik_seviyeleri(self) -> SonucYonetici:
        """
        Arıza öncelik seviyelerini getir.
        
        Returns:
            SonucYonetici
        """
        try:
            sabitler = self._r.get("Sabitler").get_all() or []
            seviyeler = [
                str(s.get("MenuEleman", "")).strip()
                for s in sabitler
                if str(s.get("Kod", "")).strip() == "Oncelik"
                and str(s.get("MenuEleman", "")).strip()
            ]
            return SonucYonetici.tamam(veri=sorted(list(set(seviyeler))))
        except Exception as e:
            return SonucYonetici.hata(e, "ArizaService.get_oncelik_seviyeleri")
    
    def get_cihaz_listesi(self) -> SonucYonetici:
        """
        Cihaz listesini getir.
        
        Returns:
            SonucYonetici
        """
        try:
            rows = self._r.get("Cihazlar").get_all() or []
            return SonucYonetici.tamam(veri=rows)
        except Exception as e:
            return SonucYonetici.hata(e, "ArizaService.get_cihaz_listesi")
    
    def get_cihaz(self, cihaz_id: str) -> SonucYonetici:
        """
        Tek bir cihazı getir.
        
        Args:
            cihaz_id: Cihaz ID'si
        
        Returns:
            SonucYonetici
        """
        try:
            row = self._r.get("Cihazlar").get_by_pk(cihaz_id)
            return SonucYonetici.tamam(veri=row)
        except Exception as e:
            return SonucYonetici.hata(e, "ArizaService.get_cihaz")
    
    def kaydet(self, veri: Dict, guncelle: bool = False) -> SonucYonetici:
        """
        Arıza kaydı ekle veya güncelle.
        
        Args:
            veri: Arıza verisi
            guncelle: True ise UPDATE, False ise INSERT
        
        Returns:
            SonucYonetici
        """
        try:
            repo = self._r.get("Cihaz_Ariza")
            if guncelle:
                ariza_id = veri.get("ArizaId")
                if not ariza_id:
                    return SonucYonetici.hata("UPDATE için ArizaId gerekli", "ArizaService.kaydet")
                repo.update(ariza_id, veri)
                return SonucYonetici.tamam(f"Arıza #{ariza_id} güncellendi.")
            else:
                repo.insert(veri)
                return SonucYonetici.tamam("Yeni arıza kaydı oluşturuldu.")
        except Exception as e:
            return SonucYonetici.hata(e, "ArizaService.kaydet")
    
    def sil(self, ariza_id: str) -> SonucYonetici:
        """
        Arıza kaydını sil.
        
        Args:
            ariza_id: Arıza ID'si
        
        Returns:
            SonucYonetici
        """
        try:
            self._r.get("Cihaz_Ariza").delete(ariza_id)
            return SonucYonetici.tamam(f"Arıza #{ariza_id} silindi.")
        except Exception as e:
            return SonucYonetici.hata(e, "ArizaService.sil")

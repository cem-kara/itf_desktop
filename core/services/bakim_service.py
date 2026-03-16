"""
BakimService — Periyodik bakım işlemleri için service katmanı
Sorumluluklar:
- Bakım verisi yükleme ve filtreleme
- Bakım türleri listesi
- Cihaz bilgileri
- Bakım kaydı (INSERT/UPDATE)
"""
from typing import Optional, List, Dict
from core.hata_yonetici import SonucYonetici
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
    
    def get_bakim_listesi(self, cihaz_id: Optional[str] = None) -> SonucYonetici:
        """
        Bakım listesini getir.
        
        Args:
            cihaz_id: Filtreleme için cihaz ID'si (isteğe bağlı)
        
        Returns:
            SonucYonetici
        """
        try:
            rows = self._r.get("Periyodik_Bakim").get_all() or []
            if cihaz_id:
                rows = [
                    r for r in rows
                    if str(r.get("Cihazid", "")).strip() == str(cihaz_id).strip()
                ]
            rows = sorted(
                rows,
                key=lambda r: r.get("PlanlananTarih") or "",
                reverse=True
            )
            return SonucYonetici.tamam(veri=rows)
        except Exception as e:
            return SonucYonetici.hata(e, "BakimService.get_bakim_listesi")
    
    def get_bakim_tipleri(self) -> SonucYonetici:
        """
        Bakım türlerini getir.
        
        Returns:
            SonucYonetici
        """
        try:
            sabitler = self._r.get("Sabitler").get_all() or []
            tipleri = [
                str(s.get("MenuEleman", "")).strip()
                for s in sabitler
                if str(s.get("Kod", "")).strip() == "BakimTipi"
                and str(s.get("MenuEleman", "")).strip()
            ]
            return SonucYonetici.tamam(veri=sorted(list(set(tipleri))))
        except Exception as e:
            return SonucYonetici.hata(e, "BakimService.get_bakim_tipleri")
    
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
            return SonucYonetici.hata(e, "BakimService.get_cihaz_listesi")
    def get_cihaz_adlari(self) -> List[str]:
        """
        Cihaz adlarını getir (formlar için).
        
        Returns:
            Cihaz adları listesi
        """
        sonuc = self.get_cihaz_listesi()
        if not sonuc.basarili or not sonuc.data:
            return []
        adlar = [
            str(c.get("CihazAdi", "")).strip()
            for c in sonuc.data
            if str(c.get("CihazAdi", "")).strip()
        ]
        return sorted(list(set(adlar)))
    
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
            return SonucYonetici.hata(e, "BakimService.get_cihaz")
    
    def kaydet(self, veri: Dict, guncelle: bool = False) -> SonucYonetici:
        """
        Bakım kaydı ekle veya güncelle.
        
        Args:
            veri: Bakım verisi
            guncelle: True ise UPDATE, False ise INSERT
        
        Returns:
            SonucYonetici
        """
        try:
            repo = self._r.get("Periyodik_Bakim")
            if guncelle:
                plan_id = veri.get("Planid")
                if not plan_id:
                    return SonucYonetici.hata("UPDATE için Planid gerekli", "BakimService.kaydet")
                repo.update(plan_id, veri)
                return SonucYonetici.tamam(f"Bakım planı #{plan_id} güncellendi.")
            else:
                repo.insert(veri)
                return SonucYonetici.tamam("Yeni bakım planı oluşturuldu.")
        except Exception as e:
            return SonucYonetici.hata(e, "BakimService.kaydet")
    
    def sil(self, plan_id: str) -> SonucYonetici:
        """
        Bakım planını sil.
        
        Args:
            plan_id: Bakım planı ID'si
        
        Returns:
            SonucYonetici
        """
        try:
            self._r.get("Periyodik_Bakim").delete(plan_id)
            return SonucYonetici.tamam(f"Bakım planı #{plan_id} silindi.")
        except Exception as e:
            return SonucYonetici.hata(e, "BakimService.sil")

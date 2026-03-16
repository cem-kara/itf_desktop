"""
PersonelService — Personel yönetimi işlemleri için service katmanı
Sorumluluklar:
- Personel verisi yükleme ve filtreleme
- TC Kimlik No doğrulama (resmi T.C. algoritması)
- Personel kaydı (INSERT/UPDATE/DELETE)
"""
from typing import Optional, List, Dict
from database.base_repository import BaseRepository
from core.hata_yonetici import SonucYonetici, logger
from core.validators import validate_tc_kimlik_no
from database.repository_registry import RepositoryRegistry


class PersonelService:
    """Personel işlemleri hizmeti"""
    
    def __init__(self, registry: RepositoryRegistry):
        """
        Servis oluştur.
        
        Args:
            registry: RepositoryRegistry örneği
        """
        if not registry:
            raise ValueError("RepositoryRegistry boş olamaz")
        self._r = registry
    
    # ───────────────────────────────────────────────────────────
    #  Repository Accessors
    # ───────────────────────────────────────────────────────────
    
    def get_personel_repo(self) -> BaseRepository:
        """Personel repository'sine eriş."""
        return self._r.get("Personel")
    
    # ───────────────────────────────────────────────────────────
    #  İş Kuralları
    # ───────────────────────────────────────────────────────────
    
    def validate_tc(self, tc: str) -> bool:
        """
        TC Kimlik No doğrulaması.
        
        Merkezi validator kullanır (core.validators.validate_tc_kimlik_no)
        """
        try:
            tc = str(tc).strip()
            return validate_tc_kimlik_no(tc)
        except Exception as e:
            return False
    
    # ───────────────────────────────────────────────────────────
    #  Veri Yükleme
    # ───────────────────────────────────────────────────────────
    
    def get_personel_listesi(self, aktif_only: bool = False) -> SonucYonetici:
        """
        Personel listesini getir.
        
        Args:
            aktif_only: Sadece aktif personelleri göster
        
        Returns:
            Personel kayıtları
        """
        try:
            rows = self._r.get("Personel").get_all() or []
            
            if aktif_only:
                rows = [
                    r for r in rows
                    if str(r.get("Durum", "")).strip().lower() != "pasif"
                ]
            
            return SonucYonetici.tamam(data=rows)
        except Exception as e:
            return SonucYonetici.hata(e, "PersonelService.get_personel_listesi")
    
    def get_personel(self, tc: str) -> SonucYonetici:
        """
        Tek bir personeli TC Kimlik No'ya göre getir.
        
        Args:
            tc: TC Kimlik No
        
        Returns:
            Personel kaydı veya None
        """
        try:
            data = self._r.get("Personel").get_by_pk(tc)
            return SonucYonetici.tamam(data=data)
        except Exception as e:
            return SonucYonetici.hata(e, f"PersonelService.get_personel({tc})")
    
    def get_bolumler(self) -> SonucYonetici:
        """
        Bölüm listesini getir.
        
        Returns:
            Bölüm adları
        """
        try:
            sabitler = self._r.get("Sabitler").get_all() or []
            bolumler = [
                str(s.get("MenuEleman", "")).strip()
                for s in sabitler
                if str(s.get("Kod", "")).strip() == "Bölüm"
            ]
            return SonucYonetici.tamam(data=sorted(list(set(bolumler))))
        except Exception as e:
            return SonucYonetici.hata(e, "PersonelService.get_bolumler")
    
    def get_gorev_yerleri(self) -> SonucYonetici:
        """
        Görev yeri listesini getir.
        
        Returns:
            Görev yeri adları
        """
        try:
            sabitler = self._r.get("Sabitler").get_all() or []
            gorev_yerleri = [
                str(s.get("MenuEleman", "")).strip()
                for s in sabitler
                if str(s.get("Kod", "")).strip() == "Gorev_Yeri"
                and str(s.get("MenuEleman", "")).strip()
            ]
            return SonucYonetici.tamam(data=sorted(list(set(gorev_yerleri))))
        except Exception as e:
            return SonucYonetici.hata(e, "PersonelService.get_gorev_yerleri")
    
    def get_hizmet_siniflari(self) -> SonucYonetici:
        """
        Hizmet sınıfı listesini getir.
        
        Returns:
            Hizmet sınıfı adları
        """
        try:
            sabitler = self._r.get("Sabitler").get_all() or []
            siniflar = [
                str(s.get("MenuEleman", "")).strip()
                for s in sabitler
                if str(s.get("Kod", "")).strip() == "Hizmet_Sinifi"
                and str(s.get("MenuEleman", "")).strip()
            ]
            return SonucYonetici.tamam(data=sorted(list(set(siniflar))))
        except Exception as e:
            return SonucYonetici.hata(e, "PersonelService.get_hizmet_siniflari")
    
    # ───────────────────────────────────────────────────────────
    #  CRUD İşlemleri
    # ───────────────────────────────────────────────────────────
    
    def ekle(self, veri: Dict) -> SonucYonetici:
        """
        Yeni personel ekle.
        
        Args:
            veri: Personel verisi (TC Kimlik No içermelidir)
        
        Returns:
            SonucYonetici
        """
        try:
            # KimlikNo (yeni akış) veya TC (geri uyumluluk) doğrula
            tc = str(veri.get("KimlikNo") or veri.get("TC") or "").strip()
            if not self.validate_tc(tc):
                return SonucYonetici.hata(Exception(f"Geçersiz TC Kimlik No: {tc}"), "PersonelService.ekle")
            
            self._r.get("Personel").insert(veri)
            return SonucYonetici.tamam(f"Personel {tc} eklendi")
        except Exception as e:
            return SonucYonetici.hata(e, "PersonelService.ekle")
    
    def guncelle(self, tc: str, veri: Dict) -> SonucYonetici:
        """
        Personel bilgilerini güncelle.
        
        Args:
            tc: TC Kimlik No
            veri: Güncellenecek veriler
        
        Returns:
            SonucYonetici
        """
        try:
            self._r.get("Personel").update(tc, veri)
            return SonucYonetici.tamam(f"Personel {tc} güncellendi")
        except Exception as e:
            return SonucYonetici.hata(e, "PersonelService.guncelle")
    
    def sil(self, tc: str) -> SonucYonetici:
        """
        Personel kaydını sil.
        
        Args:
            tc: TC Kimlik No
        
        Returns:
            SonucYonetici
        """
        try:
            self._r.get("Personel").delete(tc)
            return SonucYonetici.tamam(f"Personel {tc} silindi")
        except Exception as e:
            return SonucYonetici.hata(e, "PersonelService.sil")

    # ───────────────────────────────────────────────────────────
    #  Repository Accessor Methods
    # ───────────────────────────────────────────────────────────

    def get_sabitler_repo(self) -> Optional[BaseRepository]:
        """Sabitler repository'sini döndür (combo verisi için)."""
        try:
            return self._r.get("Sabitler")
        except Exception as e:
            logger.error(f"Sabitler repository erişim hatası: {e}")
            return None

    def get_personel_by_tc(self, tc: str) -> SonucYonetici:
        """TC'ye göre personel kaydını getir."""
        try:
            repo = self._r.get("Personel")
            data = repo.get_by_id(tc)
            return SonucYonetici.tamam(data=data)
        except Exception as e:
            return SonucYonetici.hata(e, "PersonelService.get_personel_by_tc")

    def get_all_sabitler(self) -> SonucYonetici:
        """Tüm Sabitler kaydını getir."""
        try:
            repo = self._r.get("Sabitler")
            data = repo.get_all() or []
            return SonucYonetici.tamam(data=data)
        except Exception as e:
            return SonucYonetici.hata(e, "PersonelService.get_all_sabitler")

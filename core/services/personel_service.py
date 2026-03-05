"""
PersonelService — Personel yönetimi işlemleri için service katmanı
Sorumluluklar:
- Personel verisi yükleme ve filtreleme
- TC Kimlik No doğrulama (Luhn algoritması)
- Personel kaydı (INSERT/UPDATE/DELETE)
"""
from typing import Optional, List, Dict
from core.logger import logger
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
    #  İş Kuralları
    # ───────────────────────────────────────────────────────────
    
    def validate_tc(self, tc: str) -> bool:
        """
        TC Kimlik No doğrulaması (Luhn algoritması).
        
        - 11 haneli sayı olmalı
        - İlk hane 0 olamaz
        - Luhn checksum geçmeli
        
        Args:
            tc: TC Kimlik No
        
        Returns:
            Geçerli ise True
        """
        try:
            # String temizle
            tc = str(tc).strip()
            
            # 11 hane kontrol
            if len(tc) != 11:
                return False
            
            # Sadece rakam içermelidir
            if not tc.isdigit():
                return False
            
            # İlk hane 0 olamaz
            if tc[0] == "0":
                return False
            
            # Luhn algoritması
            toplam = 0
            for i in range(10):
                digit = int(tc[i])
                if i % 2 == 0:  # Tek konumlar (1, 3, 5, 7, 9)
                    digit *= 3
                toplam += digit
            
            checksum_hesaplandi = (10 - (toplam % 10)) % 10
            checksum_gereken = int(tc[10])
            
            return checksum_hesaplandi == checksum_gereken
        except Exception as e:
            logger.error(f"TC doğrulama hatası: {e}")
            return False
    
    # ───────────────────────────────────────────────────────────
    #  Veri Yükleme
    # ───────────────────────────────────────────────────────────
    
    def get_personel_listesi(self, aktif_only: bool = False) -> List[Dict]:
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
            
            return rows
        except Exception as e:
            logger.error(f"Personel listesi yükleme hatası: {e}")
            return []
    
    def get_personel(self, tc: str) -> Optional[Dict]:
        """
        Tek bir personeli TC Kimlik No'ya göre getir.
        
        Args:
            tc: TC Kimlik No
        
        Returns:
            Personel kaydı veya None
        """
        try:
            return self._r.get("Personel").get_by_pk(tc)
        except Exception as e:
            logger.error(f"Personel '{tc}' yükleme hatası: {e}")
            return None
    
    def get_bolumler(self) -> List[str]:
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
            return sorted(list(set(bolumler)))
        except Exception as e:
            logger.error(f"Bölüm listesi yükleme hatası: {e}")
            return []
    
    def get_gorev_yerleri(self) -> List[str]:
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
            return sorted(list(set(gorev_yerleri)))
        except Exception as e:
            logger.error(f"Görev yeri listesi yükleme hatası: {e}")
            return []
    
    def get_hizmet_siniflari(self) -> List[str]:
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
            return sorted(list(set(siniflar)))
        except Exception as e:
            logger.error(f"Hizmet sınıfı listesi yükleme hatası: {e}")
            return []
    
    # ───────────────────────────────────────────────────────────
    #  CRUD İşlemleri
    # ───────────────────────────────────────────────────────────
    
    def ekle(self, veri: Dict) -> bool:
        """
        Yeni personel ekle.
        
        Args:
            veri: Personel verisi (TC Kimlik No içermelidir)
        
        Returns:
            Başarılı ise True
        """
        try:
            # TC doğrula
            tc = veri.get("TC", "")
            if not self.validate_tc(tc):
                logger.error(f"Geçersiz TC Kimlik No: {tc}")
                return False
            
            self._r.get("Personel").insert(veri)
            logger.info(f"Personel {tc} eklendi")
            return True
        except Exception as e:
            logger.error(f"Personel ekleme hatası: {e}")
            return False
    
    def guncelle(self, tc: str, veri: Dict) -> bool:
        """
        Personel bilgilerini güncelle.
        
        Args:
            tc: TC Kimlik No
            veri: Güncellenecek veriler
        
        Returns:
            Başarılı ise True
        """
        try:
            self._r.get("Personel").update(tc, veri)
            logger.info(f"Personel {tc} güncellendi")
            return True
        except Exception as e:
            logger.error(f"Personel güncelleme hatası: {e}")
            return False
    
    def sil(self, tc: str) -> bool:
        """
        Personel kaydını sil.
        
        Args:
            tc: TC Kimlik No
        
        Returns:
            Başarılı ise True
        """
        try:
            self._r.get("Personel").delete(tc)
            logger.info(f"Personel {tc} silindi")
            return True
        except Exception as e:
            logger.error(f"Personel silme hatası: {e}")
            return False

    # ───────────────────────────────────────────────────────────
    #  Repository Accessor Methods
    # ───────────────────────────────────────────────────────────

    def get_personel_repo(self):
        """Personel repository'sini döndür (direkt tablo erişimi için)."""
        try:
            return self._r.get("Personel")
        except Exception as e:
            logger.error(f"Personel repository erişim hatası: {e}")
            return None

    def get_sabitler_repo(self):
        """Sabitler repository'sini döndür (combo verisi için)."""
        try:
            return self._r.get("Sabitler")
        except Exception as e:
            logger.error(f"Sabitler repository erişim hatası: {e}")
            return None

    def get_personel_by_tc(self, tc: str) -> Optional[Dict]:
        """TC'ye göre personel kaydını getir."""
        try:
            repo = self._r.get("Personel")
            return repo.get_by_id(tc)
        except Exception as e:
            logger.error(f"Personel TC getirme hatası: {e}")
            return None

    def get_all_sabitler(self) -> list[Dict]:
        """Tüm Sabitler kaydını getir."""
        try:
            repo = self._r.get("Sabitler")
            return repo.get_all() or []
        except Exception as e:
            logger.error(f"Sabitler getirme hatası: {e}")
            return []

"""
IzinService — Personel izin takibi işlemleri için service katmanı
Sorumluluklar:
- İzin verisi yükleme ve filtreleme
- İzin türleri listesi
- Pasif personel kuralı (30+ gün veya ücretsiz/aylıksız izin)
- İzin kaydı (INSERT/UPDATE/DELETE)
- Bugünkü izinli personel listesi
"""
from typing import Optional, List, Dict, Tuple
from datetime import date
from core.logger import logger
from core.date_utils import parse_date, to_ui_date
from database.repository_registry import RepositoryRegistry


class IzinService:
    """İzin ve izin takibi hizmeti"""
    
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
    
    def get_izin_bilgi_repo(self):
        """İzin Bilgi repository'sine eriş."""
        return self._r.get("Izin_Bilgi")
    
    def get_izin_giris_repo(self):
        """İzin Giriş repository'sine eriş."""
        return self._r.get("Izin_Giris")

    def insert_izin_giris(self, data: dict) -> None:
        """İzin giriş kaydı ekle."""
        try:
            self._r.get("Izin_Giris").insert(data)
        except Exception as e:
            logger.error(f"İzin giriş ekleme hatası: {e}")
            raise

    def update_izin_giris(self, izin_id: str, data: dict) -> None:
        """İzin giriş kaydını güncelle."""
        try:
            self._r.get("Izin_Giris").update(izin_id, data)
        except Exception as e:
            logger.error(f"İzin giriş güncelleme hatası: {e}")
            raise
    
    # ───────────────────────────────────────────────────────────
    #  İş Kuralları
    # ───────────────────────────────────────────────────────────
    
    def should_set_pasif(self, izin_tipi: str, gun: int) -> bool:
        """
        Personeli pasif yapıp yapmayacağını belirle.
        
        İzin süresi 30+ gün VEYA ücretsiz/aylıksız izin → pasif olur.
        
        Args:
            izin_tipi: İzin türü (örn: "Yıllık İzin", "Ücretsiz İzin")
            gun: İzin süresi gün cinsinden
        
        Returns:
            Pasif yapılmalı ise True
        """
        # Gün kontrolü
        if gun > 30:
            return True
        
        # İzin türü kontrolü
        tip_lower = str(izin_tipi or "").strip().lower()
        if "aylıksız" in tip_lower or "ücretsiz" in tip_lower or "ucretsiz" in tip_lower:
            return True
        
        return False
    
    # ───────────────────────────────────────────────────────────
    #  Veri Yükleme
    # ───────────────────────────────────────────────────────────
    
    def get_izin_listesi(
        self,
        ay: Optional[int] = None,
        yil: Optional[int] = None,
        tc: Optional[str] = None
    ) -> List[Dict]:
        """
        İzin listesini getir.
        
        Args:
            ay: Filtreleme için ay (isteğe bağlı)
            yil: Filtreleme için yıl (isteğe bağlı)
            tc: Filtreleme için TC Kimlik No (isteğe bağlı)
        
        Returns:
            İzin kayıtları
        """
        try:
            rows = self._r.get("Izin_Giris").get_all() or []
            
            if tc:
                rows = [r for r in rows if str(r.get("TC", "")).strip() == str(tc).strip()]
            
            if ay and yil:
                rows = [
                    r for r in rows
                    if str(r.get("Ay", "")).strip() == str(ay).strip()
                    and str(r.get("Yil", "")).strip() == str(yil).strip()
                ]
            elif ay:
                rows = [r for r in rows if str(r.get("Ay", "")).strip() == str(ay).strip()]
            elif yil:
                rows = [r for r in rows if str(r.get("Yil", "")).strip() == str(yil).strip()]
            
            return rows
        except Exception as e:
            logger.error(f"İzin listesi yükleme hatası: {e}")
            return []
    
    def get_izin_tipleri(self) -> List[str]:
        """
        İzin türlerini getir.
        
        Returns:
            İzin türleri listesi
        """
        try:
            sabitler = self._r.get("Sabitler").get_all() or []
            tipleri = [
                str(s.get("MenuEleman", "")).strip()
                for s in sabitler
                if str(s.get("Kod", "")).strip() == "IzinTipi"
                and str(s.get("MenuEleman", "")).strip()
            ]
            return sorted(list(set(tipleri)))
        except Exception as e:
            logger.error(f"İzin türleri yükleme hatası: {e}")
            return []
    
    def get_personel_listesi(self) -> List[Dict]:
        """
        Personel listesini getir.
        
        Returns:
            Tüm personeller
        """
        try:
            return self._r.get("Personel").get_all() or []
        except Exception as e:
            logger.error(f"Personel listesi yükleme hatası: {e}")
            return []
    
    def get_izinli_personeller_bugun(self) -> Dict[str, List[Tuple[str, str]]]:
        """
        Bugün izinli olan personellerin detaylı listesini getir.
        
        Returns:
            Dict[TC, List[(başlangıç_str, bitiş_str)]]
            Örnek: {"12345678901": [("01.03.2026", "05.03.2026")]}
        """
        try:
            today = date.today()
            izin_kayitlari = self._r.get("Izin_Giris").get_all() or []
            
            izinli_map: Dict[str, List[Tuple[str, str]]] = {}
            
            for kayit in izin_kayitlari:
                tc = str(kayit.get("Personelid", "")).strip()
                bas_tarih = parse_date(kayit.get("BaslamaTarihi", ""))
                bit_tarih = parse_date(kayit.get("BitisTarihi", ""))
                
                if not tc or not bas_tarih:
                    continue
                
                # Bitiş tarihi yoksa başlangıç tarihiyle aynı kabul et
                if not bit_tarih:
                    bit_tarih = bas_tarih
                
                # Bugün izin aralığında mı?
                if bas_tarih <= today <= bit_tarih:
                    bas_str = to_ui_date(kayit.get("BaslamaTarihi", ""), "")
                    bit_str = to_ui_date(kayit.get("BitisTarihi", ""), bas_str)
                    
                    if tc not in izinli_map:
                        izinli_map[tc] = []
                    izinli_map[tc].append((bas_str, bit_str))
            
            # Her TC için tarihleri sırala
            for tc in izinli_map:
                izinli_map[tc].sort(key=lambda x: x[0])
            
            return izinli_map
        except Exception as e:
            logger.error(f"İzinli personel sorgusu hatası: {e}")
            return {}
    
    # ───────────────────────────────────────────────────────────
    #  CRUD İşlemleri
    # ───────────────────────────────────────────────────────────
    
    def kaydet(self, veri: Dict, guncelle: bool = False) -> bool:
        """
        İzin kaydı ekle veya güncelle.
        
        Args:
            veri: İzin verisi
            guncelle: True ise UPDATE, False ise INSERT
        
        Returns:
            Başarılı ise True
        """
        try:
            repo = self._r.get("Izin_Giris")
            if guncelle:
                izin_id = veri.get("Izinid")
                if not izin_id:
                    logger.error("UPDATE için IzinId gerekli")
                    return False
                repo.update(izin_id, veri)
                logger.info(f"İzin #{izin_id} güncellendi")
            else:
                repo.insert(veri)
                logger.info("Yeni izin kaydı oluşturuldu")
            return True
        except Exception as e:
            logger.error(f"İzin kaydet hatası: {e}")
            return False
    
    def iptal_et(self, izin_id: str) -> bool:
        """
        İzin kaydını iptal et (sil).
        
        Args:
            izin_id: İzin ID'si
        
        Returns:
            Başarılı ise True
        """
        try:
            self._r.get("Izin_Giris").delete(izin_id)
            logger.info(f"İzin #{izin_id} iptal edildi")
            return True
        except Exception as e:
            logger.error(f"İzin iptal hatası: {e}")
            return False

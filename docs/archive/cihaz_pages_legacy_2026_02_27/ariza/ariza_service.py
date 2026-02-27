# -*- coding: utf-8 -*-
"""
Arıza Sayfası - Service Layer
==============================
Business logic, CRUD operations, validations.
Repository layer ile iletişim.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from core.logger import logger


class ArizaService:
    """Arıza işlemleri servis"""
    
    def __init__(self, repositories=None):
        """
        Args:
            repositories: RepositoryRegistry instance
        """
        self._repositories = repositories
        self._ariza_repo = repositories.get("ariza") if repositories else None
        self._cihaz_repo = repositories.get("cihaz") if repositories else None
        self._notification_service = None  # TBD
    
    # ──────────────────────────────────────────────────────
    # Read Operations
    # ──────────────────────────────────────────────────────
    
    def get_ariza_list(self, cihaz_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Tüm arızaları veya belirli cihaza ait arızaları getir
        
        Args:
            cihaz_id: İsteğe bağlı cihaz filtresi
        
        Returns:
            Arıza listesi (dict'ler)
        """
        if not self._ariza_repo:
            logger.warning("ArizaRepository yok, boş liste döndürülüyor")
            return []
        
        try:
            if cihaz_id:
                return self._ariza_repo.find_by_cihaz(cihaz_id)
            else:
                return self._ariza_repo.find_all()
        except Exception as e:
            logger.error(f"Arıza listesi yükleme hatası: {e}")
            return []
    
    def get_ariza_by_id(self, ariza_id: str) -> Optional[Dict[str, Any]]:
        """Arızayı ID ile getir"""
        if not self._ariza_repo:
            return None
        
        try:
            return self._ariza_repo.find_by_id(ariza_id)
        except Exception as e:
            logger.error(f"Arıza getirme hatası ({ariza_id}): {e}")
            return None
    
    def get_durum_options(self) -> List[str]:
        """Arıza durum seçenekleri"""
        return ["Açık", "Devam Ediyor", "Kapalı"]
    
    def get_oncelik_options(self) -> List[str]:
        """Arıza öncelik seçenekleri"""
        return ["Kritik", "Yüksek", "Orta", "Düşük"]
    
    def get_tip_options(self) -> List[str]:
        """Arıza tipi seçenekleri"""
        return ["Elektrik", "Mekanik", "Yazılım", "Kontrol", "Diğer"]
    
    # ──────────────────────────────────────────────────────
    # Create Operations
    # ──────────────────────────────────────────────────────
    
    def create_ariza(self, ariza_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Yeni arıza oluştur
        
        Args:
            ariza_data: {
                "Cihazid": "...",
                "Baslik": "...",
                "Aciklama": "...",
                "ArizaTipi": "...",
                "Oncelik": "...",
                ...
            }
        
        Returns:
            Oluşturulan arıza veya None (hata durumunda)
        """
        # Validasyon
        errors = self.validate_ariza(ariza_data)
        if errors:
            logger.warning(f"Arıza validasyon hatası: {errors}")
            return None
        
        # Varsayılanları ekle
        ariza_data.setdefault("BaslangicTarihi", datetime.now().isoformat())
        ariza_data.setdefault("Durum", "Açık")
        ariza_data.setdefault("Oncelik", "Orta")
        
        if not self._ariza_repo:
            logger.error("ArizaRepository yok")
            return None
        
        try:
            result = self._ariza_repo.create(ariza_data)
            logger.info(f"Arıza oluşturuldu: {result.get('Arizaid')}")
            
            # Notification trigger (TBD)
            self._trigger_notification(result)
            
            return result
        except Exception as e:
            logger.error(f"Arıza oluşturma hatası: {e}")
            return None
    
    # ──────────────────────────────────────────────────────
    # Update Operations
    # ──────────────────────────────────────────────────────
    
    def update_ariza(self, ariza_id: str, updates: Dict[str, Any]) -> bool:
        """
        Arıza güncelle
        
        Args:
            ariza_id: Arıza ID'si
            updates: Güncellenecek alanlar
        
        Returns:
            Başarılı mı
        """
        # Validasyon
        errors = self.validate_ariza(updates)
        if errors:
            logger.warning(f"Arıza validasyon hatası: {errors}")
            return False
        
        if not self._ariza_repo:
            logger.error("ArizaRepository yok")
            return False
        
        try:
            self._ariza_repo.update(ariza_id, updates)
            logger.info(f"Arıza güncellendi: {ariza_id}")
            return True
        except Exception as e:
            logger.error(f"Arıza güncelleme hatası ({ariza_id}): {e}")
            return False
    
    def close_ariza(self, ariza_id: str, closing_note: str = "") -> bool:
        """
        Arızayı kapat
        
        Args:
            ariza_id: Arıza ID'si
            closing_note: Kapanış notu
        
        Returns:
            Başarılı mı
        """
        return self.update_ariza(ariza_id, {
            "Durum": "Kapalı",
            "KapalisTarihi": datetime.now().isoformat(),
            "KapanisNotu": closing_note,
        })
    
    # ──────────────────────────────────────────────────────
    # Delete Operations
    # ──────────────────────────────────────────────────────
    
    def delete_ariza(self, ariza_id: str) -> bool:
        """
        Arıza sil
        
        Args:
            ariza_id: Arıza ID'si
        
        Returns:
            Başarılı mı
        """
        if not self._ariza_repo:
            logger.error("ArizaRepository yok")
            return False
        
        try:
            self._ariza_repo.delete(ariza_id)
            logger.info(f"Arıza silindi: {ariza_id}")
            return True
        except Exception as e:
            logger.error(f"Arıza silme hatası ({ariza_id}): {e}")
            return False
    
    # ──────────────────────────────────────────────────────
    # Validations
    # ──────────────────────────────────────────────────────
    
    def validate_ariza(self, ariza_data: Dict[str, Any]) -> List[str]:
        """
        Arıza verisi validasyonu
        
        Returns:
            Hata mesajları listesi (boşsa hata yok)
        """
        errors = []
        
        # Cihaz kontrol
        if not ariza_data.get("Cihazid"):
            errors.append("Cihaz seçilmelidir")
        
        # Başlık kontrol
        baslik = ariza_data.get("Baslik", "").strip()
        if not baslik:
            errors.append("Başlık girilmelidir")
        elif len(baslik) < 3:
            errors.append("Başlık en az 3 karakter olmalıdır")
        
        # Tipo kontrol
        if "ArizaTipi" in ariza_data:
            tip = ariza_data.get("ArizaTipi", "")
            if tip and tip not in self.get_tip_options():
                errors.append(f"Geçersiz arıza tipi: {tip}")
        
        # Öncelik kontrol
        if "Oncelik" in ariza_data:
            oncelik = ariza_data.get("Oncelik", "")
            if oncelik and oncelik not in self.get_oncelik_options():
                errors.append(f"Geçersiz öncelik: {oncelik}")
        
        # Durum kontrol
        if "Durum" in ariza_data:
            durum = ariza_data.get("Durum", "")
            if durum and durum not in self.get_durum_options():
                errors.append(f"Geçersiz durum: {durum}")
        
        return errors
    
    # ──────────────────────────────────────────────────────
    # Business Logic
    # ──────────────────────────────────────────────────────
    
    def calculate_average_resolution_time(self, ariza_list: List[Dict[str, Any]]) -> float:
        """
        Ortalama çözüm süresini hesapla (gün)
        
        Args:
            ariza_list: Arıza listesi
        
        Returns:
            Ortalama gün sayısı
        """
        kapali_arizalar = [
            a for a in ariza_list
            if a.get("Durum") in ("Kapalı", "Kapali")
        ]
        
        if not kapali_arizalar:
            return 0.0
        
        total_days = 0
        for ariza in kapali_arizalar:
            try:
                baslangic = datetime.fromisoformat(str(ariza.get("BaslangicTarihi", "")))
                kapalis = datetime.fromisoformat(str(ariza.get("KapalisTarihi", "")))
                total_days += (kapalis - baslangic).days
            except (ValueError, TypeError):
                pass
        
        return total_days / len(kapali_arizalar) if kapali_arizalar else 0.0
    
    def get_critical_arizalar(self, ariza_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Kritik arızaları getir"""
        return [
            a for a in ariza_list
            if a.get("Oncelik") == "Kritik" and a.get("Durum") in ("Açık", "Acik")
        ]
    
    # ──────────────────────────────────────────────────────
    # Internal Methods
    # ──────────────────────────────────────────────────────
    
    def _trigger_notification(self, ariza: Dict[str, Any]):
        """Yeni arıza notifikasyonu gönder (TBD)"""
        # TODO: Bildirim servisi entegrasyonu
        logger.info(f"Notifikasyon: Yeni arıza #{ariza.get('Arizaid')}")

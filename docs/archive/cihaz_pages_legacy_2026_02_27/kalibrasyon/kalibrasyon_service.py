# -*- coding: utf-8 -*-
"""
Kalibrasyon Sayfası - Service Layer
===================================
Business logic - kalibrasyon CRUD ve validasyon.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from core.logger import logger


class KalibrasyonService:
    """Kalibrasyon işlemleri servis"""
    
    def __init__(self, repositories=None):
        self._repositories = repositories
        self._kalibrasyon_repo = repositories.get("Kalibrasyon") if repositories else None
        self._cihaz_repo = repositories.get("cihaz") if repositories else None
    
    # ──────────────────────────────────────────────────────
    # Read Operations
    # ──────────────────────────────────────────────────────
    
    def get_kalibrasyon_list(self, cihaz_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Kalibrasyon listesi getir"""
        if not self._kalibrasyon_repo:
            logger.warning("KalibrasyonRepository yok")
            return []
        
        try:
            if cihaz_id:
                return self._kalibrasyon_repo.find_by_cihaz(cihaz_id)
            else:
                return self._kalibrasyon_repo.find_all()
        except Exception as e:
            logger.error(f"Kalibrasyon listesi hatası: {e}")
            return []
    
    def get_kalibrasyon_by_id(self, kalibid: str) -> Optional[Dict[str, Any]]:
        """Kalibrasyon kaydı getir"""
        if not self._kalibrasyon_repo:
            return None
        
        try:
            return self._kalibrasyon_repo.find_by_id(kalibid)
        except Exception as e:
            logger.error(f"Kalibrasyon getirme hatası: {e}")
            return None
    
    def get_durum_options(self) -> List[str]:
        return ["Geçti", "İnceleme", "Başarısız", "Bekleniyor"]
    
    def get_tip_options(self) -> List[str]:
        return ["Standart", "Hassas", "Rutin"]
    
    # ──────────────────────────────────────────────────────
    # Create Operations
    # ──────────────────────────────────────────────────────
    
    def create_kalibrasyon_record(self, record_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Kalibrasyon kaydı oluştur"""
        errors = self.validate_kalibrasyon(record_data)
        if errors:
            logger.warning(f"Kalibrasyon validasyon hatası: {errors}")
            return None
        
        record_data.setdefault("Durum", "Bekleniyor")
        record_data.setdefault("KalibrasyonTipi", "Standart")
        
        if not self._kalibrasyon_repo:
            logger.error("KalibrasyonRepository yok")
            return None
        
        try:
            result = self._kalibrasyon_repo.create(record_data)
            logger.info(f"Kalibrasyon kaydı oluşturuldu: {result.get('Kalibid')}")
            return result
        except Exception as e:
            logger.error(f"Kalibrasyon oluşturma hatası: {e}")
            return None
    
    # ──────────────────────────────────────────────────────
    # Update Operations
    # ──────────────────────────────────────────────────────
    
    def update_kalibrasyon(self, kalibid: str, updates: Dict[str, Any]) -> bool:
        """Kalibrasyon kaydı güncelle"""
        errors = self.validate_kalibrasyon(updates)
        if errors:
            logger.warning(f"Kalibrasyon validasyon hatası: {errors}")
            return False
        
        if not self._kalibrasyon_repo:
            logger.error("KalibrasyonRepository yok")
            return False
        
        try:
            self._kalibrasyon_repo.update(kalibid, updates)
            logger.info(f"Kalibrasyon güncellendi: {kalibid}")
            return True
        except Exception as e:
            logger.error(f"Kalibrasyon güncelleme hatası: {e}")
            return False
    
    def record_result(self, kalibid: str, result_data: Dict[str, Any]) -> bool:
        """Kalibrasyon sonucunu kaydet"""
        return self.update_kalibrasyon(kalibid, {
            "KalibrasyonTarihi": result_data.get("KalibrasyonTarihi"),
            "Durum": result_data.get("Durum"),
            "Aciklama": result_data.get("Aciklama", ""),
            "SonraksıTarih": self._calculate_next_calibration_date(
                result_data.get("KalibrasyonTarihi"),
                result_data.get("KalibrasyonTipi", "Standart")
            ),
        })
    
    # ──────────────────────────────────────────────────────
    # Delete Operations
    # ──────────────────────────────────────────────────────
    
    def delete_kalibrasyon(self, kalibid: str) -> bool:
        """Kalibrasyon kaydı sil"""
        if not self._kalibrasyon_repo:
            logger.error("KalibrasyonRepository yok")
            return False
        
        try:
            self._kalibrasyon_repo.delete(kalibid)
            logger.info(f"Kalibrasyon silindi: {kalibid}")
            return True
        except Exception as e:
            logger.error(f"Kalibrasyon silme hatası: {e}")
            return False
    
    # ──────────────────────────────────────────────────────
    # Validations
    # ──────────────────────────────────────────────────────
    
    def validate_kalibrasyon(self, data: Dict[str, Any]) -> List[str]:
        """Kalibrasyon verisi validasyonu"""
        errors = []
        
        if "Cihazid" in data and not data.get("Cihazid"):
            errors.append("Cihaz seçilmelidir")
        
        if "KalibrasyonTarihi" in data:
            tarih = data.get("KalibrasyonTarihi", "")
            if tarih:
                try:
                    datetime.fromisoformat(tarih)
                except (ValueError, TypeError):
                    errors.append(f"Geçersiz tarih: {tarih}")
        
        if "KalibrasyonTipi" in data:
            tip = data.get("KalibrasyonTipi", "")
            if tip and tip not in self.get_tip_options():
                errors.append(f"Geçersiz tip: {tip}")
        
        if "Durum" in data:
            durum = data.get("Durum", "")
            if durum and durum not in self.get_durum_options():
                errors.append(f"Geçersiz durum: {durum}")
        
        return errors
    
    # ──────────────────────────────────────────────────────
    # Business Logic
    # ──────────────────────────────────────────────────────
    
    def _calculate_next_calibration_date(self, baslangic_tarihi: str, tip: str) -> str:
        """
        Sonraki kalibrasyon tarihini hesapla
        
        Kurallar:
        - Hassas aletler: 1 yıl
        - Standart: 2 yıl
        - Rutin: 3 yıl
        """
        try:
            base_date = datetime.fromisoformat(baslangic_tarihi)
        except (ValueError, TypeError):
            return ""
        
        if tip == "Hassas":
            next_date = base_date + relativedelta(years=1)
        elif tip == "Standart":
            next_date = base_date + relativedelta(years=2)
        else:  # Rutin
            next_date = base_date + relativedelta(years=3)
        
        return next_date.isoformat()[:10]
    
    def get_overdue_kalibrasyonlar(self, kalibrasyon_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Süresi geçmiş kalibrasyon kayıtları"""
        overdue = []
        today = datetime.now().date()
        
        for kalib in kalibrasyon_list:
            if kalib.get("SonraksıTarih"):
                try:
                    sonraki_date = datetime.fromisoformat(kalib.get("SonraksıTarih", "")).date()
                    if sonraki_date < today:
                        overdue.append(kalib)
                except (ValueError, TypeError):
                    pass
        
        return overdue
    
    def get_hassas_aletler(self, kalibrasyon_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Hassas aletlerin kalibrasyon kayıtları"""
        return [k for k in kalibrasyon_list if k.get("KalibrasyonTipi") == "Hassas"]

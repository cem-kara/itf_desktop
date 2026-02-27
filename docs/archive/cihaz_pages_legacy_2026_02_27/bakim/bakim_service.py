# -*- coding: utf-8 -*-
"""
Bakım Sayfası - Service Layer
=============================
Business logic, CRUD operations, auto-plan generation, validations.
Repository layer ile iletişim.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from core.logger import logger


class BakimService:
    """Bakım işlemleri servis"""
    
    def __init__(self, repositories=None):
        """
        Args:
            repositories: RepositoryRegistry instance
        """
        self._repositories = repositories
        self._bakim_repo = repositories.get("Periyodik_Bakim") if repositories else None
        self._cihaz_repo = repositories.get("cihaz") if repositories else None
    
    # ──────────────────────────────────────────────────────
    # Read Operations
    # ──────────────────────────────────────────────────────
    
    def get_bakim_list(self, cihaz_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Tüm bakım kayıtlarını veya belirli cihaza ait olanları getir
        
        Args:
            cihaz_id: İsteğe bağlı cihaz filtresi
        
        Returns:
            Bakım kaydı listesi
        """
        if not self._bakim_repo:
            logger.warning("BakimRepository yok, boş liste döndürülüyor")
            return []
        
        try:
            if cihaz_id:
                return self._bakim_repo.find_by_cihaz(cihaz_id)
            else:
                return self._bakim_repo.find_all()
        except Exception as e:
            logger.error(f"Bakım listesi yükleme hatası: {e}")
            return []
    
    def get_bakim_by_id(self, bakim_id: str) -> Optional[Dict[str, Any]]:
        """Bakım kaydını ID ile getir"""
        if not self._bakim_repo:
            return None
        
        try:
            return self._bakim_repo.find_by_id(bakim_id)
        except Exception as e:
            logger.error(f"Bakım getirme hatası ({bakim_id}): {e}")
            return None
    
    def get_durum_options(self) -> List[str]:
        """Bakım durum seçenekleri"""
        return ["Planlandı", "Yapıldı", "Gecikmiş"]
    
    def get_tip_options(self) -> List[str]:
        """Bakım tipi seçenekleri"""
        return ["Rutin", "Acil", "Preventif", "Aydınlatma"]
    
    def get_periyot_options(self) -> List[str]:
        """Bakım periyodu seçenekleri"""
        return ["3 Ay", "6 Ay", "1 Yıl"]
    
    # ──────────────────────────────────────────────────────
    # Create Operations
    # ──────────────────────────────────────────────────────
    
    def create_bakim_plan(self, bakim_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Bakım planı oluştur
        
        Args:
            bakim_data: {
                "Cihazid": "...",
                "PlanlananTarih": "yyyy-MM-dd",
                "BakimPeriyodu": "3 Ay" / "6 Ay" / "1 Yıl",
                "BakimTipi": "...",
                ...
            }
        
        Returns:
            Oluşturulan bakım planı veya None
        """
        # Validasyon
        errors = self.validate_bakim(bakim_data)
        if errors:
            logger.warning(f"Bakım validasyon hatası: {errors}")
            return None
        
        # Varsayılanları ekle
        bakim_data.setdefault("Durum", "Planlandı")
        bakim_data.setdefault("BakimTipi", "Rutin")
        
        if not self._bakim_repo:
            logger.error("BakimRepository yok")
            return None
        
        try:
            result = self._bakim_repo.create(bakim_data)
            logger.info(f"Bakım planı oluşturuldu: {result.get('Planid')}")
            return result
        except Exception as e:
            logger.error(f"Bakım planı oluşturma hatası: {e}")
            return None
    
    # ──────────────────────────────────────────────────────
    # Auto-Plan Generation (Önemli!)
    # ──────────────────────────────────────────────────────
    
    def generate_automatic_plans(self, cihaz_id: str, start_date: str, 
                                periyot_months: int = 3) -> List[Dict[str, Any]]:
        """
        Cihaz için otomatik bakım planları oluştur
        
        Args:
            cihaz_id: Cihaz ID'si
            start_date: Başlangıç tarihi (yyyy-MM-dd)
            periyot_months: Periyot (3, 6, vb. ay)
        
        Returns:
            Oluşturulan planlar listesi
        
        Kural: 
        - 3 ay: sonraki 12 ay boyunca her 3 ayda bir plan yap (4 adet)
        - 6 ay: sonraki 12 ay boyunca her 6 ayda bir plan yap (2 adet)
        - 1 yıl: sadece 12 ay sonrası
        """
        try:
            base_date = datetime.fromisoformat(start_date)
        except (ValueError, TypeError):
            logger.error(f"Geçersiz tarih: {start_date}")
            return []
        
        plans = []
        
        # Planlama periyotuna göre plan sayısını belirle
        if periyot_months == 3:
            plan_count = 4  # 3, 6, 9, 12 ay sonrası
        elif periyot_months == 6:
            plan_count = 2  # 6, 12 ay sonrası
        else:  # 12 ay
            plan_count = 1  # 12 ay sonrası
        
        # Planları oluştur
        for i in range(1, plan_count + 1):
            plan_date = base_date + relativedelta(months=periyot_months * i)
            
            plan_data = {
                "Cihazid": cihaz_id,
                "PlanlananTarih": plan_date.isoformat()[:10],  # yyyy-MM-dd
                "BakimPeriyodu": f"{periyot_months} Ay",
                "BakimTipi": "Rutin",
                "Durum": "Planlandı",
            }
            
            created = self.create_bakim_plan(plan_data)
            if created:
                plans.append(created)
        
        logger.info(f"Cihaz {cihaz_id} için {len(plans)} otomatik plan oluşturuldu")
        return plans
    
    # ──────────────────────────────────────────────────────
    # Update Operations
    # ──────────────────────────────────────────────────────
    
    def update_bakim(self, bakim_id: str, updates: Dict[str, Any]) -> bool:
        """
        Bakım planını güncelle
        
        Args:
            bakim_id: Bakım planı ID'si
            updates: Güncellenecek alanlar
        
        Returns:
            Başarılı mı
        """
        # Validasyon
        errors = self.validate_bakim(updates)
        if errors:
            logger.warning(f"Bakım validasyon hatası: {errors}")
            return False
        
        if not self._bakim_repo:
            logger.error("BakimRepository yok")
            return False
        
        try:
            self._bakim_repo.update(bakim_id, updates)
            logger.info(f"Bakım planı güncellendi: {bakim_id}")
            return True
        except Exception as e:
            logger.error(f"Bakım güncelleme hatası ({bakim_id}): {e}")
            return False
    
    def record_execution(self, bakim_id: str, execution_data: Dict[str, Any]) -> bool:
        """
        Yapılan bakımı kaydet
        
        Args:
            bakim_id: Bakım planı ID'si
            execution_data: {
                "BakimTarihi": "yyyy-MM-dd",
                "Teknisyen": "...",
                "Aciklama": "...",
                ...
            }
        
        Returns:
            Başarılı mı
        """
        return self.update_bakim(bakim_id, {
            "BakimTarihi": execution_data.get("BakimTarihi"),
            "Durum": "Yapıldı",
            "Teknisyen": execution_data.get("Teknisyen", ""),
            "Aciklama": execution_data.get("Aciklama", ""),
        })
    
    # ──────────────────────────────────────────────────────
    # Delete Operations
    # ──────────────────────────────────────────────────────
    
    def delete_bakim_plan(self, bakim_id: str) -> bool:
        """
        Bakım planını sil
        
        Args:
            bakim_id: Bakım planı ID'si
        
        Returns:
            Başarılı mı
        """
        if not self._bakim_repo:
            logger.error("BakimRepository yok")
            return False
        
        try:
            self._bakim_repo.delete(bakim_id)
            logger.info(f"Bakım planı silindi: {bakim_id}")
            return True
        except Exception as e:
            logger.error(f"Bakım silme hatası ({bakim_id}): {e}")
            return False
    
    # ──────────────────────────────────────────────────────
    # Validations
    # ──────────────────────────────────────────────────────
    
    def validate_bakim(self, bakim_data: Dict[str, Any]) -> List[str]:
        """
        Bakım verisi validasyonu
        
        Returns:
            Hata mesajları listesi (boşsa hata yok)
        """
        errors = []
        
        # Cihaz kontrol
        if not bakim_data.get("Cihazid"):
            errors.append("Cihaz seçilmelidir")
        
        # Planlanan tarih kontrol
        if "PlanlananTarih" in bakim_data:
            tarih = bakim_data.get("PlanlananTarih", "")
            if tarih:
                try:
                    datetime.fromisoformat(tarih)
                except (ValueError, TypeError):
                    errors.append(f"Geçersiz tarih formatı: {tarih}")
        
        # Bakım tipi kontrol
        if "BakimTipi" in bakim_data:
            tip = bakim_data.get("BakimTipi", "")
            if tip and tip not in self.get_tip_options():
                errors.append(f"Geçersiz bakım tipi: {tip}")
        
        # Periyot kontrol
        if "BakimPeriyodu" in bakim_data:
            periyot = bakim_data.get("BakimPeriyodu", "")
            if periyot and periyot not in self.get_periyot_options():
                errors.append(f"Geçersiz periyot: {periyot}")
        
        # Durum kontrol
        if "Durum" in bakim_data:
            durum = bakim_data.get("Durum", "")
            if durum and durum not in self.get_durum_options():
                errors.append(f"Geçersiz durum: {durum}")
        
        return errors
    
    # ──────────────────────────────────────────────────────
    # Business Logic
    # ──────────────────────────────────────────────────────
    
    def get_overdue_bakim(self, bakim_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Süresi geçmiş bakımları getir"""
        overdue = []
        today = datetime.now().date()
        
        for bakim in bakim_list:
            if bakim.get("Durum") == "Planlandı":
                try:
                    plan_date = datetime.fromisoformat(bakim.get("PlanlananTarih", "")).date()
                    if plan_date < today:
                        overdue.append(bakim)
                except (ValueError, TypeError):
                    pass
        
        return overdue
    
    def calculate_average_interval(self, bakim_list: List[Dict[str, Any]]) -> float:
        """
        Ortalama bakım aralığını hesapla (gün)
        
        Tamamlanmış bakımlar arasındaki ortalama gün sayısı
        """
        yapildi_list = [
            b for b in bakim_list
            if b.get("Durum") == "Yapıldı" and b.get("BakimTarihi")
        ]
        
        if len(yapildi_list) < 2:
            return 0.0
        
        # Tarihe göre sırala
        sorted_list = sorted(yapildi_list, key=lambda x: x.get("BakimTarihi", ""))
        
        total_days = 0
        for i in range(1, len(sorted_list)):
            try:
                prev_date = datetime.fromisoformat(sorted_list[i - 1].get("BakimTarihi", ""))
                curr_date = datetime.fromisoformat(sorted_list[i].get("BakimTarihi", ""))
                total_days += (curr_date - prev_date).days
            except (ValueError, TypeError):
                pass
        
        return total_days / (len(sorted_list) - 1) if len(sorted_list) > 1 else 0.0

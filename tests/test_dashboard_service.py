"""
DashboardService Test Suite

Kapsam:
- Başlatma
- get_dashboard_data: tüm istatistikleri getir
- Bileşen metodlar: yaklasan_ndk, aylik_bakim, vb.

Not: get_dashboard_data tüm istatistikleri tek dict'te döndürür.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from core.services.dashboard_service import DashboardService


# ─────────────────────────────────────────────────────────────
#  Fixture'lar
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def reg():
    return MagicMock()


@pytest.fixture
def svc(reg):
    return DashboardService(reg)


# ─────────────────────────────────────────────────────────────
#  Başlatma
# ─────────────────────────────────────────────────────────────

class TestDashboardServiceInit:
    def test_none_registry_hata_firlatar(self):
        with pytest.raises(ValueError):
            DashboardService(None)

    def test_registry_saklanir(self, reg):
        s = DashboardService(reg)
        assert s._r is reg


# ─────────────────────────────────────────────────────────────
#  get_dashboard_data
# ─────────────────────────────────────────────────────────────

class TestGetDashboardData:
    def _mock_veri(self, reg):
        """Mock tüm repository'leri."""
        reg.get("Cihazlar").get_all.return_value = [
            {"Cihazid": "C01", "BitisTarihi": "2026-12-01"},
            {"Cihazid": "C02", "BitisTarihi": "2026-06-01"},
        ]
        reg.get("Periyodik_Bakim").get_all.return_value = [
            {"Planid": "P1", "PlanlananTarih": "2026-02-15"},
        ]
        reg.get("Kalibrasyon").get_all.return_value = [
            {"Kalid": "K1", "BitisTarihi": "2026-03-10"},
        ]
        reg.get("Cihaz_Ariza").get_all.return_value = [
            {"Arizaid": "A1", "BitisTarihi": None, "Tarih": datetime.now().strftime("%Y-%m-%d")},
        ]
        reg.get("Personel").get_all.return_value = [
            {"KimlikNo": "P1", "Aktif": 1},
            {"KimlikNo": "P2", "Aktif": 1},
        ]
        reg.get("RKE_Muayene").get_all.return_value = []
        reg.get("Personel_Saglik_Takip").get_all.return_value = []
        reg.get("Izin_Giris").get_all.return_value = [
            {"Personelid": "P1", "Tarih": datetime.now().strftime("%Y-%m-%d")},
        ]

    def test_dashboard_data_tamam(self, svc, reg):
        """Dashboard veri hatasız döndürülür."""
        self._mock_veri(reg)
        result = svc.get_dashboard_data()
        assert result.basarili is True
        assert "yaklasan_ndk" in result.veri
        assert "aylik_bakim" in result.veri
        assert "aktif_personel" in result.veri

    def test_dashboard_data_aktif_personel_sayisi(self, svc, reg):
        """Aktif personel sayısı doğru hesaplanır."""
        repos = {name: MagicMock() for name in [
            "Cihazlar",
            "Periyodik_Bakim",
            "Kalibrasyon",
            "Cihaz_Ariza",
            "Personel",
            "RKE_List",
            "RKE_Muayene",
            "Personel_Saglik_Takip",
            "Izin_Giris",
            "Sabitler",
        ]}
        repos["Cihazlar"].get_all.return_value = []
        repos["Periyodik_Bakim"].get_all.return_value = []
        repos["Kalibrasyon"].get_all.return_value = []
        repos["Cihaz_Ariza"].get_all.return_value = []
        repos["Personel"].get_all.return_value = [
            {"KimlikNo": "P1", "Durum": "Aktif"},
            {"KimlikNo": "P2", "Durum": "Aktif"},
            {"KimlikNo": "P3", "Durum": "Pasif"},
        ]
        repos["RKE_List"].get_all.return_value = []
        repos["RKE_Muayene"].get_all.return_value = []
        repos["Personel_Saglik_Takip"].get_all.return_value = []
        repos["Izin_Giris"].get_all.return_value = []
        repos["Sabitler"].get_all.return_value = []
        reg.get.side_effect = lambda table: repos[table]

        result = svc.get_dashboard_data()
        assert result.basarili is True
        # Aktif personel = 2
        assert result.veri.get("aktif_personel") == 2

    def test_dashboard_data_repo_hatasi(self, svc, reg):
        """Repository hatası durumunda servis güvenli fallback ile tamam döner."""
        reg.get("Cihazlar").get_all.side_effect = Exception("DB Hatası")
        result = svc.get_dashboard_data()
        assert result.basarili is True
        assert isinstance(result.veri, dict)

    def test_dashboard_data_bos_tablolar(self, svc, reg):
        """Boş tablolarla da çalışır."""
        reg.get("Cihazlar").get_all.return_value = []
        reg.get("Periyodik_Bakim").get_all.return_value = []
        reg.get("Kalibrasyon").get_all.return_value = []
        reg.get("Cihaz_Ariza").get_all.return_value = []
        reg.get("Personel").get_all.return_value = []
        reg.get("RKE_Muayene").get_all.return_value = []
        reg.get("Personel_Saglik_Takip").get_all.return_value = []
        reg.get("Izin_Giris").get_all.return_value = []

        result = svc.get_dashboard_data()
        assert result.basarili is True
        # Tüm sayılar 0 olmalı
        assert result.veri.get("aktif_personel") == 0


# ─────────────────────────────────────────────────────────────
#  Bileşen Metodlar
# ─────────────────────────────────────────────────────────────

class TestDashboardComponentMethods:
    """Bileşen metodları (private) test edilebilir şekilde."""
    
    def test_parse_date_helper(self, svc):
        """Tarih parse helper'ı test et."""
        from core.services.dashboard_service import _parse_date
        
        # YYYY-MM-DD
        dt = _parse_date("2026-03-15")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 3
        assert dt.day == 15

        # DD.MM.YYYY
        dt2 = _parse_date("15.03.2026")
        assert dt2 is not None
        assert dt2.year == 2026

        # Boş/None
        assert _parse_date(None) is None
        assert _parse_date("") is None

        # Geçersiz format
        assert _parse_date("invalid") is None

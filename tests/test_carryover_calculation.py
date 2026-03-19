# -*- coding: utf-8 -*-
"""
Unit Test: Yıl Sonu Devir Hesaplaması (657 SK md.102)

657 SK md.102: "Cari yıl ile bir önceki yıl hariç, önceki yıllara ait
kullanılmayan izin hakları düşer."

Devir Formülü: min(mevcut_kalan, yillik_hakedis, yillik_hakedis × 2)

Bu testler pure matematiksel devir hesaplamasını doğrularlar.
"""
import pytest
from core.services.izin_service import IzinService

from database.repository_registry import RepositoryRegistry
from unittest.mock import MagicMock


@pytest.fixture
def mock_registry():
    """Boş bir registry mock'u oluştur (calculate_carryover repo kullanmıyor)."""
    return MagicMock(spec=RepositoryRegistry)


@pytest.fixture
def svc(mock_registry):
    """IzinService örneği."""
    return IzinService(mock_registry)


class TestCarryoverFormula:
    """657 SK md.102 devir formülü testleri."""

    def test_normal_devir_kalan_az(self, svc):
        """
        Senaryö: Normal devir — kalan < hakediş
        
        Mevcut Kalan: 35 gün
        Hakediş: 20 gün
        
        Hesaplama: min(35, 20, 40) = 20 gün
        """
        devir = svc.calculate_carryover(35, 20)
        assert devir == 20.0

    def test_zamanasimi_fazla_kalan(self, svc):
        """
        Senaryö: Zamanaşımı — kalan > 2× hakediş
        
        Mevcut Kalan: 65 gün (3+ yıl birikimi)
        Hakediş: 20 gün
        
        Hesaplama: min(65, 20, 40) = 20 gün
        → Fazla 45 gün zamanaşımına uğrar
        """
        devir = svc.calculate_carryover(65, 20)
        assert devir == 20.0

    def test_10_plus_yil_hizmet(self, svc):
        """
        Senaryö: 10+ yıl hizmet (hakediş 30 gün)
        
        Mevcut Kalan: 55 gün
        Hakediş: 30 gün
        
        Hesaplama: min(55, 30, 60) = 30 gün
        """
        devir = svc.calculate_carryover(55, 30)
        assert devir == 30.0

    def test_exact_2year_limit(self, svc):
        """
        Senaryö: Tam 2 yıllık birikim
        
        Mevcut Kalan: 40 gün
        Hakediş: 20 gün
        
        Hesaplama: min(40, 20, 40) = 20 gün
        """
        devir = svc.calculate_carryover(40, 20)
        assert devir == 20.0

    def test_first_year_minimal(self, svc):
        """
        Senaryö: İlk yıl — az kullanım
        
        Mevcut Kalan: 15 gün
        Hakediş: 20 gün
        
        Hesaplama: min(15, 20, 40) = 15 gün
        """
        devir = svc.calculate_carryover(15, 20)
        assert devir == 15.0

    def test_excessive_accumulation(self, svc):
        """
        Senaryö: Aşırı birikim
        
        Mevcut Kalan: 80 gün (4 yıl)
        Hakediş: 30 gün
        
        Hesaplama: min(80, 30, 60) = 30 gün
        → Fazla 50 gün zamanaşımına uğrar
        """
        devir = svc.calculate_carryover(80, 30)
        assert devir == 30.0

    def test_zero_remaining(self, svc):
        """
        Senaryö: Hiç kalan yok
        
        Mevcut Kalan: 0 gün
        Hakediş: 20 gün
        
        Hesaplama: min(0, 20, 40) = 0 gün
        """
        devir = svc.calculate_carryover(0, 20)
        assert devir == 0.0

    def test_partial_usage(self, svc):
        """
        Senaryö: Kısmi kullanım
        
        Mevcut Kalan: 25 gün
        Hakediş: 30 gün
        
        Hesaplama: min(25, 30, 60) = 25 gün
        """
        devir = svc.calculate_carryover(25, 30)
        assert devir == 25.0

    def test_floating_point_precision(self, svc):
        """
        Senaryö: Ondalık sayılar (nadir ama mümkün)
        
        Mevcut Kalan: 25.5 gün
        Hakediş: 20.0 gün
        
        Hesaplama: min(25.5, 20.0, 40.0) = 20.0 gün
        """
        devir = svc.calculate_carryover(25.5, 20.0)
        assert devir == 20.0

    def test_negative_inputs_clamped(self, svc):
        """
        Senaryö: Geçersiz negatif değerler (guard)
        
        Mevcut Kalan: -10 gün (geçersiz)
        Hakediş: 20 gün
        
        Result: 0 gün (clamped)
        """
        devir = svc.calculate_carryover(-10, 20)
        assert devir == 0.0

    def test_none_inputs_default(self, svc):
        """
        Senaryö: None değerler (güvenli)
        
        Mevcut Kalan: None
        Hakediş: 20 gün
        
        Result: min(0, 20, 40) = 0 gün
        """
        devir = svc.calculate_carryover(None, 20)
        assert devir == 0.0


class TestDevirEdgeCases:
    """Sınır durumları ve özel senaryolar."""

    def test_both_zero(self, svc):
        """Kalan ve hakediş sıfır → sıfır devir."""
        devir = svc.calculate_carryover(0, 0)
        assert devir == 0.0

    def test_large_hakedis(self, svc):
        """30 gün hakediş (10+ yıl hizmet)."""
        devir = svc.calculate_carryover(45, 30)
        assert devir == 30.0

    def test_exactly_at_boundary(self, svc):
        """
        Boundary: kalan = 2× hakediş (sınırda)
        
        min(40, 20, 40) = 20 gün
        """
        devir = svc.calculate_carryover(40, 20)
        assert devir == 20.0

    def test_just_above_boundary(self, svc):
        """
        Boundary: kalan = 2× hakediş + 0.1 (sınırı geç)
        
        min(40.1, 20, 40) = 20 gün
        """
        devir = svc.calculate_carryover(40.1, 20)
        assert devir == 20.0

    def test_string_inputs_parsed(self, svc):
        """
        String inputlar float'a dönüştürülür.
        
        Mevcut Kalan: "35"
        Hakediş: "20"
        """
        devir = svc.calculate_carryover("35", "20")
        assert devir == 20.0


class TestRealisticScenarios:
    """Gerçek dünya senaryoları."""

    def test_scenario_new_employee_first_year(self, svc):
        """
        Yeni memur, 1. yıl sonunda az kullanım
        
        Başlama: Ocak 1
        Hakediş: 20 gün
        Kullanım: 5 gün
        Kalan: 15 gün
        
        Devir: 15 gün
        """
        devir = svc.calculate_carryover(15, 20)
        assert devir == 15.0

    def test_scenario_veteran_efficient(self, svc):
        """
        Deneyimli memur, kullanımda disiplinli
        
        Hizmet: 12 yıl (hakediş 30 gün)
        Kalan: 28 gün
        
        Devir: 28 gün (hakediş altında)
        """
        devir = svc.calculate_carryover(28, 30)
        assert devir == 28.0

    def test_scenario_accumulated_over_years(self, svc):
        """
        Birkaç yıl birikmesi
        
        Kalan: 50 gün (2.5 yıl)
        Hakediş: 20 gün
        
        Devir: 20 gün (2 yıl limiti)
        Ekspor: 30 gün
        """
        devir = svc.calculate_carryover(50, 20)
        assert devir == 20.0
        expired = 50 - 20
        assert expired == 30

    def test_scenario_medical_leave_stockpiling(self, svc):
        """
        Tıbbi rapor/mazeret izleriyle stoklanmış hesap
        
        Kalan: 72 gün
        Hakediş: 20 gün (sadece yıllık)
        
        Devir: 20 gün (zamanaşımı killi)
        """
        devir = svc.calculate_carryover(72, 20)
        assert devir == 20.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

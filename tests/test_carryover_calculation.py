# -*- coding: utf-8 -*-
"""Yıl sonu devir hesaplama testleri (SonucYonetici uyumlu)."""

import pytest
from unittest.mock import MagicMock
from database.repository_registry import RepositoryRegistry
from core.services.izin_service import IzinService


@pytest.fixture
def mock_registry():
    return MagicMock(spec=RepositoryRegistry)


@pytest.fixture
def svc(mock_registry):
    return IzinService(mock_registry)


def _devir(svc: IzinService, kalan, hakedis) -> float:
    sonuc = svc.calculate_carryover(kalan, hakedis)
    assert sonuc.basarili is True
    return float(sonuc.veri)


class TestCarryoverFormula:
    def test_normal_devir_kalan_az(self, svc):
        assert _devir(svc, 35, 20) == 20.0

    def test_zamanasimi_fazla_kalan(self, svc):
        assert _devir(svc, 65, 20) == 20.0

    def test_10_plus_yil_hizmet(self, svc):
        assert _devir(svc, 55, 30) == 30.0

    def test_exact_2year_limit(self, svc):
        assert _devir(svc, 40, 20) == 20.0

    def test_first_year_minimal(self, svc):
        assert _devir(svc, 15, 20) == 15.0

    def test_excessive_accumulation(self, svc):
        assert _devir(svc, 80, 30) == 30.0

    def test_zero_remaining(self, svc):
        assert _devir(svc, 0, 20) == 0.0

    def test_partial_usage(self, svc):
        assert _devir(svc, 25, 30) == 25.0

    def test_floating_point_precision(self, svc):
        assert _devir(svc, 25.5, 20.0) == 20.0
        assert abs(_devir(svc, 19.999, 20) - 19.999) < 1e-9

    def test_negative_inputs_clamped(self, svc):
        assert _devir(svc, -10, 20) == 0.0

    def test_none_inputs_default(self, svc):
        assert _devir(svc, None, 20) == 0.0


class TestDevirEdgeCases:
    def test_both_zero(self, svc):
        assert _devir(svc, 0, 0) == 0.0

    def test_large_hakedis(self, svc):
        assert _devir(svc, 45, 30) == 30.0

    def test_exactly_at_boundary(self, svc):
        assert _devir(svc, 40, 20) == 20.0

    def test_just_above_boundary(self, svc):
        assert _devir(svc, 40.1, 20) == 20.0

    def test_string_inputs_parsed(self, svc):
        assert _devir(svc, "35", "20") == 20.0


class TestRealisticScenarios:
    def test_scenario_new_employee_first_year(self, svc):
        assert _devir(svc, 15, 20) == 15.0

    def test_scenario_veteran_efficient(self, svc):
        assert _devir(svc, 28, 30) == 28.0

    def test_scenario_accumulated_over_years(self, svc):
        devir = _devir(svc, 50, 20)
        assert devir == 20.0
        assert (50 - devir) == 30

    def test_scenario_medical_leave_stockpiling(self, svc):
        assert _devir(svc, 72, 20) == 20.0

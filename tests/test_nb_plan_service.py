import pytest
from unittest.mock import MagicMock

from core.services.nobet.nb_plan_service import NbPlanService


@pytest.fixture
def repos():
    return {
        "NB_Plan": MagicMock(),
        "NB_PlanSatir": MagicMock(),
        "NB_MesaiHesap": MagicMock(),
        "NB_Vardiya": MagicMock(),
        "Personel": MagicMock(),
        "Izin_Giris": MagicMock(),
        "NB_Tercih": MagicMock(),
        "NB_MesaiHedef": MagicMock(),
        "Sabitler": MagicMock(),
        "Tatiller": MagicMock(),
    }


@pytest.fixture
def reg(repos):
    reg = MagicMock()
    reg.get.side_effect = lambda name: repos.setdefault(name, MagicMock())
    return reg


@pytest.fixture
def svc(reg):
    return NbPlanService(reg)


class TestInit:
    def test_none_registry_hata(self):
        with pytest.raises(ValueError):
            NbPlanService(None)


class TestGetPlan:
    def test_en_yuksek_versiyon(self, svc, repos):
        repos["NB_Plan"].get_all.return_value = [
            {"PlanID": "P1", "BirimID": "B1", "Yil": 2026, "Ay": 3, "Versiyon": 1},
            {"PlanID": "P2", "BirimID": "B1", "Yil": 2026, "Ay": 3, "Versiyon": 2},
        ]
        sonuc = svc.get_plan("B1", 2026, 3)
        assert sonuc.basarili is True
        assert sonuc.veri["PlanID"] == "P2"

    def test_plan_yok(self, svc, repos):
        repos["NB_Plan"].get_all.return_value = []
        sonuc = svc.get_plan("B1", 2026, 3)
        assert sonuc.basarili is True
        assert sonuc.veri is None


class TestPlanAlVeyaOlustur:
    def test_yeni_plan_olusturur(self, svc, repos):
        repos["NB_Plan"].get_all.return_value = []
        sonuc = svc.plan_al_veya_olustur("B1", 2026, 3)
        assert sonuc.basarili is True
        assert repos["NB_Plan"].insert.called

    def test_mevcut_taslagi_doner(self, svc, repos):
        repos["NB_Plan"].get_all.return_value = [
            {"PlanID": "P1", "BirimID": "B1", "Yil": 2026, "Ay": 3, "Versiyon": 1, "Durum": "taslak"}
        ]
        sonuc = svc.plan_al_veya_olustur("B1", 2026, 3)
        assert sonuc.basarili is True
        assert sonuc.veri["PlanID"] == "P1"


class TestOnayDurumu:
    def test_plan_yoksa_yok(self, svc, repos):
        repos["NB_Plan"].get_all.return_value = []
        sonuc = svc.onay_durumu("B1", 2026, 3)
        assert sonuc.basarili is True
        assert sonuc.veri == "yok"


class TestSatirlar:
    def test_sadece_aktif_satirlar(self, svc, repos):
        repos["NB_PlanSatir"].get_all.return_value = [
            {"SatirID": "S1", "PlanID": "P1", "Durum": "aktif"},
            {"SatirID": "S2", "PlanID": "P1", "Durum": "iptal"},
            {"SatirID": "S3", "PlanID": "P2", "Durum": "aktif"},
        ]
        sonuc = svc.get_satirlar("P1", sadece_aktif=True)
        assert sonuc.basarili is True
        assert len(sonuc.veri) == 1
        assert sonuc.veri[0]["SatirID"] == "S1"

    def test_gun_satirlari(self, svc, repos):
        repos["NB_PlanSatir"].get_all.return_value = [
            {"SatirID": "S1", "PlanID": "P1", "Durum": "aktif", "NobetTarihi": "2026-03-10"},
            {"SatirID": "S2", "PlanID": "P1", "Durum": "aktif", "NobetTarihi": "2026-03-11"},
        ]
        sonuc = svc.get_gun_satirlari("P1", "2026-03-10")
        assert sonuc.basarili is True
        assert len(sonuc.veri) == 1
        assert sonuc.veri[0]["SatirID"] == "S1"

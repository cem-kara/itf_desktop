import pytest
from unittest.mock import MagicMock

from core.services.nobet.nobet_adapter import NobetAdapter


@pytest.fixture
def repos():
    return {
        "Personel": MagicMock(),
        "NB_Birim": MagicMock(),
        "NB_Vardiya": MagicMock(),
        "NB_Plan": MagicMock(),
        "NB_PlanSatir": MagicMock(),
        "Sabitler": MagicMock(),
        "Tatiller": MagicMock(),
        "NB_MesaiHedef": MagicMock(),
    }


@pytest.fixture
def reg(repos):
    reg = MagicMock()
    reg.get.side_effect = lambda name: repos.setdefault(name, MagicMock())
    return reg


@pytest.fixture
def adapter(reg):
    return NobetAdapter(reg)


class TestInit:
    def test_registry_saklanir(self, adapter, reg):
        assert adapter._r is reg


class TestBirimler:
    def test_get_birimler_sonuc(self, adapter):
        adapter.birim.get_birimler = MagicMock(return_value=MagicMock(basarili=True, veri=[{"BirimID": "B1"}]))
        sonuc = adapter.get_birimler()
        assert sonuc.basarili is True
        assert len(sonuc.veri) == 1


class TestPersonelVeVardiya:
    def test_get_personel_listesi(self, adapter, repos):
        repos["Personel"].get_all.return_value = [
            {"KimlikNo": "2", "AdSoyad": "B Kisi", "GorevYeri": "Radyoloji"},
            {"KimlikNo": "1", "AdSoyad": "A Kisi", "GorevYeri": "Radyoloji"},
        ]
        sonuc = adapter.get_personel_listesi("Radyoloji")
        assert sonuc.basarili is True
        assert [r["AdSoyad"] for r in sonuc.veri] == ["A Kisi", "B Kisi"]

    def test_get_vardiyalar_birim_adi_ile(self, adapter):
        adapter._birim_id_coz = MagicMock(return_value="B1")
        adapter.vardiya.get_vardiyalar = MagicMock(return_value=MagicMock(basarili=True, veri=[{"VardiyaID": "V1"}]))
        sonuc = adapter.get_vardiyalar("Radyoloji")
        assert sonuc.basarili is True
        assert len(sonuc.veri) == 1


class TestGetPlan:
    def test_plan_satirlarini_joinler(self, adapter, repos):
        adapter._birim_id_coz = MagicMock(return_value="B1")
        adapter.plan.get_plan = MagicMock(return_value=MagicMock(basarili=True, veri={"PlanID": "P1"}))
        adapter.plan.get_satirlar = MagicMock(return_value=MagicMock(
            basarili=True,
            veri=[{"SatirID": "S1", "VardiyaID": "V1", "PersonelID": "1", "NobetTarihi": "2026-03-01"}],
        ))
        repos["NB_Vardiya"].get_all.return_value = [
            {"VardiyaID": "V1", "VardiyaAdi": "Gunduz", "BasSaat": "08:00", "BitSaat": "16:00", "SureDakika": 480}
        ]

        sonuc = adapter.get_plan(2026, 3, "B1")
        assert sonuc.basarili is True
        assert len(sonuc.veri) == 1
        assert sonuc.veri[0]["VardiyaAdi"] == "Gunduz"

    def test_plan_yoksa_bos(self, adapter):
        adapter._birim_id_coz = MagicMock(return_value="B1")
        adapter.plan.get_plan = MagicMock(return_value=MagicMock(basarili=True, veri=None))
        sonuc = adapter.get_plan(2026, 3, "B1")
        assert sonuc.basarili is True
        assert sonuc.veri == []


class TestOnayliRapor:
    def test_onayli_rapor_donusu(self, adapter, repos):
        adapter.get_birimler = MagicMock(return_value=MagicMock(basarili=True, veri=[{"BirimID": "B1", "BirimAdi": "Radyoloji"}]))
        adapter.plan.get_plan = MagicMock(return_value=MagicMock(basarili=True, veri={"PlanID": "P1", "Durum": "onaylandi"}))
        adapter.plan.get_satirlar = MagicMock(return_value=MagicMock(basarili=True, veri=[]))
        repos["Personel"].get_all.return_value = []
        repos["NB_Vardiya"].get_all.return_value = []

        sonuc = adapter.get_onayli_rapor_verisi(2026, 3)
        assert sonuc.basarili is True
        assert "planlar" in sonuc.veri
        assert "satirlar" in sonuc.veri

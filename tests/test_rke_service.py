"""
RkeService Test Suite

Kapsam:
- Başlatma
- get_rke_listesi / get_rke
- rke_ekle / rke_guncelle / rke_sil
- get_muayene_listesi / get_muayene
- muayene_ekle / muayene_guncelle / muayene_sil
"""
import pytest
from unittest.mock import MagicMock
from core.services.rke_service import RkeService


@pytest.fixture
def reg():
    return MagicMock()


@pytest.fixture
def svc(reg):
    return RkeService(reg)


class TestInit:
    def test_none_registry_hata_firlatar(self):
        with pytest.raises(ValueError):
            RkeService(None)

    def test_registry_saklanir(self, reg):
        s = RkeService(reg)
        assert s._r is reg


class TestGetRkeListesi:
    def test_bos_liste(self, svc, reg):
        reg.get("RKE_List").get_all.return_value = []
        result = svc.get_rke_listesi()
        assert result.basarili is True
        assert result.veri == []

    def test_tum_liste(self, svc, reg):
        reg.get("RKE_List").get_all.return_value = [
            {"EkipmanNo": "E01", "Durum": "Aktif"},
            {"EkipmanNo": "E02", "Durum": "Aktif"},
        ]
        result = svc.get_rke_listesi()
        assert result.basarili is True
        assert len(result.veri) == 2

    def test_repo_hatasi(self, svc, reg):
        reg.get("RKE_List").get_all.side_effect = Exception("DB")
        result = svc.get_rke_listesi()
        assert result.basarili is False


class TestGetRke:
    def test_var_olan_kayit(self, svc, reg):
        reg.get("RKE_List").get_by_pk.return_value = {"EkipmanNo": "E01"}
        result = svc.get_rke("E01")
        assert result.basarili is True
        assert result.veri["EkipmanNo"] == "E01"

    def test_olmayan_kayit_none(self, svc, reg):
        reg.get("RKE_List").get_by_pk.return_value = None
        result = svc.get_rke("YOOOK")
        assert result.basarili is True
        assert result.veri is None


class TestRkeEkleGuncelleSil:
    def test_ekle(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        veri = {"EkipmanNo": "E01", "KoruyucuCinsi": "Önlük"}
        result = svc.rke_ekle(veri)
        assert result.basarili is True
        mock_repo.insert.assert_called_once_with(veri)

    def test_guncelle(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        result = svc.rke_guncelle("E01", {"Durum": "Pasif"})
        assert result.basarili is True
        mock_repo.update.assert_called_once_with("E01", {"Durum": "Pasif"})

    def test_sil(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        result = svc.rke_sil("E01")
        assert result.basarili is True
        mock_repo.delete.assert_called_once_with("E01")

    def test_db_hatasi_basarisiz(self, svc, reg):
        mock_repo = MagicMock()
        mock_repo.insert.side_effect = Exception("Hata")
        reg.get.return_value = mock_repo
        result = svc.rke_ekle({"EkipmanNo": "E01"})
        assert result.basarili is False


class TestMuayene:
    def test_get_muayene_listesi_tum(self, svc, reg):
        reg.get("RKE_Muayene").get_all.return_value = [
            {"KayitNo": "M1", "EkipmanNo": "E01"},
            {"KayitNo": "M2", "EkipmanNo": "E02"},
        ]
        result = svc.get_muayene_listesi()
        assert result.basarili is True
        assert len(result.veri) == 2

    def test_get_muayene_listesi_filtreli(self, svc, reg):
        reg.get("RKE_Muayene").get_all.return_value = [
            {"KayitNo": "M1", "EkipmanNo": "E01"},
            {"KayitNo": "M2", "EkipmanNo": "E02"},
        ]
        result = svc.get_muayene_listesi(ekipman_no="E01")
        assert result.basarili is True
        assert len(result.veri) == 1
        assert result.veri[0]["EkipmanNo"] == "E01"

    def test_muayene_ekle(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        veri = {"EkipmanNo": "E01", "FMuayeneTarihi": "2026-03-01"}
        result = svc.muayene_ekle(veri)
        assert result.basarili is True
        mock_repo.insert.assert_called_once_with(veri)

    def test_muayene_guncelle(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        result = svc.muayene_guncelle("M1", {"FizikselDurum": "Uygun"})
        assert result.basarili is True
        mock_repo.update.assert_called_once()

    def test_muayene_sil(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        result = svc.muayene_sil("M1")
        assert result.basarili is True
        mock_repo.delete.assert_called_once_with("M1")

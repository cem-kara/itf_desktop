"""
CihazService Test Suite

Kapsam:
- Başlatma
- get_cihaz_listesi / get_cihaz / get_cihaz_paginated
- cihaz_ekle / cihaz_guncelle
- get_ariza_listesi / ariza_ekle / ariza_islem_ekle
- get_bakim_listesi / bakim_ekle / get_kalibrasyon_listesi / kalibrasyon_ekle
"""
import pytest
from unittest.mock import MagicMock
from core.services.cihaz_service import CihazService


@pytest.fixture
def reg():
    return MagicMock()


@pytest.fixture
def svc(reg):
    return CihazService(reg)


class TestInit:
    def test_none_registry_hata_firlatar(self):
        with pytest.raises(ValueError):
            CihazService(None)

    def test_registry_saklanir(self, reg):
        s = CihazService(reg)
        assert s._r is reg


class TestGetCihazListesi:
    def test_bos_liste(self, svc, reg):
        reg.get("Cihazlar").get_all.return_value = []
        result = svc.get_cihaz_listesi()
        assert result.basarili is True
        assert result.veri == []

    def test_tum_liste(self, svc, reg):
        reg.get("Cihazlar").get_all.return_value = [
            {"Cihazid": "C01", "Marka": "Philips"},
            {"Cihazid": "C02", "Marka": "Siemens"},
        ]
        result = svc.get_cihaz_listesi()
        assert result.basarili is True
        assert len(result.veri) == 2

    def test_repo_hatasi(self, svc, reg):
        reg.get("Cihazlar").get_all.side_effect = Exception("Hata")
        result = svc.get_cihaz_listesi()
        assert result.basarili is False


class TestGetCihaz:
    def test_var_olan_cihaz(self, svc, reg):
        reg.get("Cihazlar").get_by_kod.return_value = [{"Cihazid": "C01"}]
        result = svc.get_cihaz("C01")
        assert result.basarili is True
        assert result.veri["Cihazid"] == "C01"

    def test_olmayan_cihaz(self, svc, reg):
        reg.get("Cihazlar").get_by_kod.return_value = []
        result = svc.get_cihaz("YOK")
        assert result.basarili is True
        assert result.veri is None


class TestGetCihazPaginated:
    def test_sayfalama_dogru_dilimliyor(self, svc, reg):
        reg.get("Cihazlar").get_paginated.return_value = {
            "items": [{"Cihazid": f"C{i:02d}"} for i in range(10)],
            "total": 25,
            "page": 1,
            "page_size": 10,
        }

        result = svc.get_cihaz_paginated(page=1, page_size=10)
        assert result.basarili is True
        assert len(result.veri["items"]) == 10
        assert result.veri["total"] == 25
        assert result.veri["page"] == 1

    def test_son_sayfa_eksik_elemanli(self, svc, reg):
        reg.get("Cihazlar").get_paginated.return_value = {
            "items": [{"Cihazid": f"C{i:02d}"} for i in range(20, 25)],
            "total": 25,
            "page": 3,
            "page_size": 10,
        }

        result = svc.get_cihaz_paginated(page=3, page_size=10)
        assert result.basarili is True
        assert len(result.veri["items"]) == 5


class TestCihazEkleGuncelle:
    def test_ekle(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        veri = {"Cihazid": "C01", "Marka": "Philips"}
        result = svc.cihaz_ekle(veri)
        assert result.basarili is True
        mock_repo.insert.assert_called_once_with(veri)

    def test_guncelle(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        result = svc.cihaz_guncelle("C01", {"Marka": "Siemens"})
        assert result.basarili is True
        mock_repo.update.assert_called_once_with("C01", {"Marka": "Siemens"})

    def test_db_hatasi_basarisiz(self, svc, reg):
        mock_repo = MagicMock()
        mock_repo.insert.side_effect = Exception("Hata")
        reg.get.return_value = mock_repo
        result = svc.cihaz_ekle({"Cihazid": "C01"})
        assert result.basarili is False


class TestArizaIslemleri:
    def test_get_ariza_listesi(self, svc, reg):
        reg.get("Cihaz_Ariza").get_all.return_value = [
            {"Arizaid": "A1", "Cihazid": "C01"},
            {"Arizaid": "A2", "Cihazid": "C01"},
        ]
        result = svc.get_ariza_listesi("C01")
        assert result.basarili is True
        assert len(result.veri) == 2

    def test_ariza_ekle(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        veri = {"Arizaid": "A1", "Cihazid": "C01"}
        result = svc.ariza_ekle(veri)
        assert result.basarili is True
        mock_repo.insert.assert_called_once_with(veri)

    def test_ariza_islem_ekle(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        veri = {"Islemid": "I1", "Arizaid": "A1"}
        result = svc.ariza_islem_ekle(veri)
        assert result.basarili is True
        mock_repo.insert.assert_called_once_with(veri)


class TestBakimKalibrasyon:
    def test_get_bakim_listesi(self, svc, reg):
        reg.get("Periyodik_Bakim").get_all.return_value = [
            {"Planid": "B1", "Cihazid": "C01"},
        ]
        result = svc.get_bakim_listesi("C01")
        assert result.basarili is True
        assert len(result.veri) == 1

    def test_bakim_ekle(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        veri = {"Planid": "B1", "Cihazid": "C01"}
        result = svc.bakim_ekle(veri)
        assert result.basarili is True
        mock_repo.insert.assert_called_once_with(veri)

    def test_get_kalibrasyon_listesi(self, svc, reg):
        reg.get("Kalibrasyon").get_all.return_value = [
            {"Kalid": "K1", "Cihazid": "C01"},
        ]
        result = svc.get_kalibrasyon_listesi("C01")
        assert result.basarili is True
        assert len(result.veri) == 1

    def test_kalibrasyon_ekle(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        veri = {"Kalid": "K1", "Cihazid": "C01"}
        result = svc.kalibrasyon_ekle(veri)
        assert result.basarili is True
        mock_repo.insert.assert_called_once_with(veri)

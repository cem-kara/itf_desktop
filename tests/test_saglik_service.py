"""
SaglikService Test Suite

Kapsam:
- Başlatma
- get_saglik_kayitlari: tümü, personel filtresi, hata
- get_saglik_kaydi
- saglik_kaydi_ekle / guncelle / sil
- get_personel_saglik_ozeti
"""
import pytest
from unittest.mock import MagicMock
from core.services.saglik_service import SaglikService


@pytest.fixture
def reg():
    return MagicMock()


@pytest.fixture
def svc(reg):
    return SaglikService(reg)


class TestInit:
    def test_none_registry_hata_firlatar(self):
        with pytest.raises(ValueError):
            SaglikService(None)

    def test_registry_saklanir(self, reg):
        s = SaglikService(reg)
        assert s._r is reg


class TestGetSaglikKayitlari:
    def _veri(self):
        return [
            {"KayitNo": "K1", "Personelid": "111", "Yil": 2026, "Sonuc": "Uygun"},
            {"KayitNo": "K2", "Personelid": "222", "Yil": 2026, "Sonuc": "Uygun"},
            {"KayitNo": "K3", "Personelid": "111", "Yil": 2025, "Sonuc": "Uygun Değil"},
        ]

    def test_tum_kayitlar(self, svc, reg):
        reg.get("Personel_Saglik_Takip").get_all.return_value = self._veri()
        result = svc.get_saglik_kayitlari()
        assert result.basarili is True
        assert len(result.veri) == 3

    def test_personel_filtresi(self, svc, reg):
        reg.get("Personel_Saglik_Takip").get_all.return_value = self._veri()
        result = svc.get_saglik_kayitlari(personel_id="111")
        assert result.basarili is True
        assert len(result.veri) == 2
        assert all(r["Personelid"] == "111" for r in result.veri)

    def test_bos_liste(self, svc, reg):
        reg.get("Personel_Saglik_Takip").get_all.return_value = []
        result = svc.get_saglik_kayitlari()
        assert result.basarili is True
        assert result.veri == []

    def test_repo_hatasi(self, svc, reg):
        reg.get("Personel_Saglik_Takip").get_all.side_effect = Exception("Hata")
        result = svc.get_saglik_kayitlari()
        assert result.basarili is False


class TestGetSaglikKaydi:
    def test_var_olan_kayit(self, svc, reg):
        reg.get("Personel_Saglik_Takip").get_by_pk.return_value = {
            "KayitNo": "K1", "Sonuc": "Uygun"
        }
        result = svc.get_saglik_kaydi("K1")
        assert result.basarili is True
        assert result.veri["Sonuc"] == "Uygun"

    def test_olmayan_kayit(self, svc, reg):
        reg.get("Personel_Saglik_Takip").get_by_pk.return_value = None
        result = svc.get_saglik_kaydi("YOOOK")
        assert result.basarili is True
        assert result.veri is None


class TestSaglikKaydiEkleGuncelleSil:
    def test_ekle(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        veri = {"KayitNo": "K1", "Personelid": "111", "Sonuc": "Uygun"}
        result = svc.saglik_kaydi_ekle(veri)
        assert result.basarili is True
        mock_repo.insert.assert_called_once_with(veri)

    def test_guncelle(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        result = svc.saglik_kaydi_guncelle("K1", {"Sonuc": "Uygun"})
        assert result.basarili is True
        mock_repo.update.assert_called_once_with("K1", {"Sonuc": "Uygun"})

    def test_sil(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        result = svc.saglik_kaydi_sil("K1")
        assert result.basarili is True
        mock_repo.delete.assert_called_once_with("K1")

    def test_db_hatasi_basarisiz(self, svc, reg):
        mock_repo = MagicMock()
        mock_repo.insert.side_effect = Exception("Hata")
        reg.get.return_value = mock_repo
        result = svc.saglik_kaydi_ekle({"KayitNo": "K1"})
        assert result.basarili is False


class TestPersonelSaglikOzeti:
    def test_ozet_aliniyor(self, svc, reg):
        reg.get("Personel_Saglik_Takip").get_all.return_value = [
            {"KayitNo": "K1", "Personelid": "111", "Yil": 2026, "Sonuc": "Uygun"},
            {"KayitNo": "K2", "Personelid": "111", "Yil": 2025, "Sonuc": "Uygun"},
        ]
        result = svc.get_personel_saglik_ozeti("111")
        assert result.basarili is True
        assert result.veri is not None

    def test_bos_personel_ozeti(self, svc, reg):
        reg.get("Personel_Saglik_Takip").get_all.return_value = []
        result = svc.get_personel_saglik_ozeti("999")
        assert result.basarili is True

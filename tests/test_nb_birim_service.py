import pytest
from unittest.mock import MagicMock

from core.services.nobet.nb_birim_service import NbBirimService


@pytest.fixture
def reg():
    return MagicMock()


@pytest.fixture
def svc(reg):
    s = NbBirimService(reg)
    s._sync_missing_sabit_birimler = lambda: None
    return s


class TestInit:
    def test_none_registry_hata(self):
        with pytest.raises(ValueError):
            NbBirimService(None)


class TestGetBirimler:
    def test_aktifleri_getirir(self, svc, reg):
        reg.get("NB_Birim").get_all.return_value = [
            {"BirimID": "B1", "BirimAdi": "Radyoloji", "BirimKodu": "RAD", "Sira": 2, "Aktif": 1, "is_deleted": 0},
            {"BirimID": "B2", "BirimAdi": "USG", "BirimKodu": "USG", "Sira": 1, "Aktif": 0, "is_deleted": 0},
        ]

        sonuc = svc.get_birimler(sadece_aktif=True)
        assert sonuc.basarili is True
        assert len(sonuc.veri) == 1
        assert sonuc.veri[0]["BirimID"] == "B1"

    def test_siralama(self, svc, reg):
        reg.get("NB_Birim").get_all.return_value = [
            {"BirimID": "B1", "BirimAdi": "Zeta", "BirimKodu": "Z", "Sira": 2, "Aktif": 1, "is_deleted": 0},
            {"BirimID": "B2", "BirimAdi": "Alfa", "BirimKodu": "A", "Sira": 1, "Aktif": 1, "is_deleted": 0},
        ]

        sonuc = svc.get_birimler(sadece_aktif=False)
        assert sonuc.basarili is True
        assert sonuc.veri[0]["BirimID"] == "B2"


class TestGetBirim:
    def test_bulur(self, svc, reg):
        reg.get("NB_Birim").get_all.return_value = [{"BirimID": "B1", "BirimAdi": "Radyoloji"}]
        sonuc = svc.get_birim("B1")
        assert sonuc.basarili is True
        assert sonuc.veri["BirimAdi"] == "Radyoloji"

    def test_bulamaz(self, svc, reg):
        reg.get("NB_Birim").get_all.return_value = []
        sonuc = svc.get_birim("B99")
        assert sonuc.basarili is False


class TestBirimIdBul:
    def test_adi_idye_cevirir(self, svc, reg):
        reg.get("NB_Birim").get_all.return_value = [
            {"BirimID": "B1", "BirimAdi": "Radyoloji", "is_deleted": 0}
        ]
        sonuc = svc.birim_id_bul("Radyoloji")
        assert sonuc.basarili is True
        assert sonuc.veri == "B1"


class TestYazmaIslemleri:
    def test_birim_ekle(self, svc, reg):
        reg.get("NB_Birim").get_all.return_value = []
        sonuc = svc.birim_ekle("Tomografi", "TOMO")
        assert sonuc.basarili is True
        assert reg.get("NB_Birim").insert.called

    def test_birim_guncelle(self, svc, reg):
        reg.get("NB_Birim").get_all.return_value = [{"BirimID": "B1", "BirimAdi": "Radyoloji"}]
        sonuc = svc.birim_guncelle("B1", birim_adi="Yeni")
        assert sonuc.basarili is True
        assert reg.get("NB_Birim").update.called

    def test_aktif_toggle(self, svc, reg):
        reg.get("NB_Birim").get_all.return_value = [{"BirimID": "B1", "Aktif": 1}]
        sonuc = svc.birim_aktif_toggle("B1")
        assert sonuc.basarili is True
        reg.get("NB_Birim").update.assert_called_once()

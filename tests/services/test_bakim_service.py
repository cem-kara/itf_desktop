"""BakimService testleri (SonucYonetici uyumlu)."""
import pytest
from unittest.mock import MagicMock
from core.services.bakim_service import BakimService


@pytest.fixture
def reg():
    return MagicMock()


@pytest.fixture
def svc(reg):
    return BakimService(reg)


def test_init_registry_gerekli():
    with pytest.raises(ValueError):
        BakimService(None)


def test_get_bakim_listesi_bos(svc, reg):
    reg.get("Periyodik_Bakim").get_all.return_value = []
    sonuc = svc.get_bakim_listesi()
    assert sonuc.basarili is True
    assert sonuc.veri == []


def test_get_bakim_listesi_sirali(svc, reg):
    reg.get("Periyodik_Bakim").get_all.return_value = [
        {"Planid": 1, "PlanlananTarih": "2026-01-15"},
        {"Planid": 2, "PlanlananTarih": "2026-02-10"},
        {"Planid": 3, "PlanlananTarih": "2026-01-01"},
    ]
    sonuc = svc.get_bakim_listesi()
    assert sonuc.basarili is True
    assert [r["Planid"] for r in sonuc.veri] == [2, 1, 3]


def test_get_bakim_tipleri(svc, reg):
    reg.get("Sabitler").get_all.return_value = [
        {"Kod": "BakimTipi", "MenuEleman": "Yağlama"},
        {"Kod": "BakimTipi", "MenuEleman": "Kontrol"},
        {"Kod": "BakimTipi", "MenuEleman": "Yağlama"},
    ]
    sonuc = svc.get_bakim_tipleri()
    assert sonuc.basarili is True
    assert sonuc.veri == ["Kontrol", "Yağlama"]


def test_kaydet_insert_ve_update(svc, reg):
    repo = MagicMock()
    reg.get.return_value = repo

    ekle = svc.kaydet({"Cihazid": "C01"}, guncelle=False)
    assert ekle.basarili is True
    repo.insert.assert_called_once()

    guncelle = svc.kaydet({"Planid": "1", "Cihazid": "C01"}, guncelle=True)
    assert guncelle.basarili is True
    repo.update.assert_called_once_with("1", {"Planid": "1", "Cihazid": "C01"})


def test_sil(svc, reg):
    repo = MagicMock()
    reg.get.return_value = repo
    sonuc = svc.sil("1")
    assert sonuc.basarili is True
    repo.delete.assert_called_once_with("1")

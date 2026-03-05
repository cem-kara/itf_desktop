"""
KalibrasyonService Test Suite

Kapsam:
- Başlatma doğrulaması
- get_kalibrasyon_listesi: tümü ve cihaz filtresi
- get_kalibrasyon_tipleri
- get_cihaz_listesi
- kaydet: INSERT ve UPDATE
- sil

Not: kaydet(guncelle=True) testi şu an FAIL verir.
Servis veri.get("KalibrasyonId") kullanıyor, gerçek PK "Kalid".
kalibrasyon_service.py'de düzelt:
    veri.get("KalibrasyonId")  →  veri.get("Kalid")
"""
import pytest
from unittest.mock import MagicMock
from core.services.kalibrasyon_service import KalibrasyonService


# ─────────────────────────────────────────────────────────────
#  Fixture'lar
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def reg():
    return MagicMock()


@pytest.fixture
def svc(reg):
    return KalibrasyonService(reg)


# ─────────────────────────────────────────────────────────────
#  Başlatma
# ─────────────────────────────────────────────────────────────

class TestInit:
    def test_none_registry_hata_firlatar(self):
        with pytest.raises(ValueError):
            KalibrasyonService(None)

    def test_registry_saklanir(self, reg):
        s = KalibrasyonService(reg)
        assert s._r is reg


# ─────────────────────────────────────────────────────────────
#  get_kalibrasyon_listesi
# ─────────────────────────────────────────────────────────────

class TestGetKalibrasyonListesi:
    def test_bos_liste(self, svc, reg):
        reg.get("Kalibrasyon").get_all.return_value = []
        assert svc.get_kalibrasyon_listesi() == []

    def test_tum_liste(self, svc, reg):
        veri = [
            {"Kalid": "1", "Cihazid": "C01", "BitisTarihi": "2026-06-01"},
            {"Kalid": "2", "Cihazid": "C02", "BitisTarihi": "2026-12-01"},
        ]
        reg.get("Kalibrasyon").get_all.return_value = veri
        result = svc.get_kalibrasyon_listesi()
        assert len(result) == 2

    def test_cihaz_filtresi(self, svc, reg):
        veri = [
            {"Kalid": "1", "Cihazid": "C01"},
            {"Kalid": "2", "Cihazid": "C02"},
            {"Kalid": "3", "Cihazid": "C01"},
        ]
        reg.get("Kalibrasyon").get_all.return_value = veri
        result = svc.get_kalibrasyon_listesi(cihaz_id="C01")
        assert len(result) == 2
        assert all(r["Cihazid"] == "C01" for r in result)

    def test_cihaz_filtresi_eslesme_yok(self, svc, reg):
        reg.get("Kalibrasyon").get_all.return_value = [
            {"Kalid": "1", "Cihazid": "C01"}
        ]
        assert svc.get_kalibrasyon_listesi(cihaz_id="C99") == []

    def test_repo_hatasi_bos_liste(self, svc, reg):
        reg.get("Kalibrasyon").get_all.side_effect = Exception("Hata")
        assert svc.get_kalibrasyon_listesi() == []

    def test_cihaz_id_string_donusumu(self, svc, reg):
        """Cihaz ID tipi farklı olsa da karşılaştırma çalışmalı."""
        reg.get("Kalibrasyon").get_all.return_value = [
            {"Kalid": "1", "Cihazid": "101"},
        ]
        result = svc.get_kalibrasyon_listesi(cihaz_id=101)  # int gönderiliyor
        assert len(result) == 1


# ─────────────────────────────────────────────────────────────
#  get_kalibrasyon_tipleri
# ─────────────────────────────────────────────────────────────

class TestGetKalibrasyonTipleri:
    def test_tipleri_getirir(self, svc, reg):
        reg.get("Sabitler").get_all.return_value = [
            {"Kod": "KalibrasyonTipi", "MenuEleman": "İç Kalibrasyon"},
            {"Kod": "KalibrasyonTipi", "MenuEleman": "Dış Kalibrasyon"},
            {"Kod": "BaskaBir",        "MenuEleman": "Dahil Edilmez"},
        ]
        result = svc.get_kalibrasyon_tipleri()
        assert "İç Kalibrasyon" in result
        assert "Dış Kalibrasyon" in result
        assert "Dahil Edilmez" not in result

    def test_tekrarlar_temizlenir(self, svc, reg):
        reg.get("Sabitler").get_all.return_value = [
            {"Kod": "KalibrasyonTipi", "MenuEleman": "İç Kalibrasyon"},
            {"Kod": "KalibrasyonTipi", "MenuEleman": "İç Kalibrasyon"},
        ]
        result = svc.get_kalibrasyon_tipleri()
        assert result.count("İç Kalibrasyon") == 1

    def test_alfabetik_sirali(self, svc, reg):
        reg.get("Sabitler").get_all.return_value = [
            {"Kod": "KalibrasyonTipi", "MenuEleman": "Zorlu"},
            {"Kod": "KalibrasyonTipi", "MenuEleman": "Ağır"},
        ]
        result = svc.get_kalibrasyon_tipleri()
        assert result == sorted(result)

    def test_sabitler_hatasi(self, svc, reg):
        reg.get("Sabitler").get_all.side_effect = Exception("Hata")
        assert svc.get_kalibrasyon_tipleri() == []


# ─────────────────────────────────────────────────────────────
#  get_cihaz_listesi
# ─────────────────────────────────────────────────────────────

class TestGetCihazListesi:
    def test_cihaz_listesi(self, svc, reg):
        reg.get("Cihazlar").get_all.return_value = [
            {"Cihazid": "C01"}, {"Cihazid": "C02"}
        ]
        assert len(svc.get_cihaz_listesi()) == 2

    def test_repo_hatasi_bos_liste(self, svc, reg):
        reg.get("Cihazlar").get_all.side_effect = Exception("Hata")
        assert svc.get_cihaz_listesi() == []


# ─────────────────────────────────────────────────────────────
#  kaydet
# ─────────────────────────────────────────────────────────────

class TestKaydet:
    def test_insert(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        veri = {"Cihazid": "C01", "YapilanTarih": "2026-01-15"}
        assert svc.kaydet(veri, guncelle=False) is True
        mock_repo.insert.assert_called_once_with(veri)

    def test_update_basarili(self, svc, reg):
        """
        BUG: Bu test şu an FAIL verir.
        Servis veri.get("KalibrasyonId") kullanıyor, gerçek PK "Kalid".
        kalibrasyon_service.py'de düzelt:
            veri.get("KalibrasyonId")  →  veri.get("Kalid")
        """
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        veri = {"Kalid": "5", "Durum": "Geçerli"}
        assert svc.kaydet(veri, guncelle=True) is True
        mock_repo.update.assert_called_once_with("5", veri)

    def test_update_pk_yoksa_false(self, svc, reg):
        veri = {"Cihazid": "C01"}
        assert svc.kaydet(veri, guncelle=True) is False

    def test_db_hatasi_false(self, svc, reg):
        mock_repo = MagicMock()
        mock_repo.insert.side_effect = Exception("Hata")
        reg.get.return_value = mock_repo
        assert svc.kaydet({"Cihazid": "C01"}, guncelle=False) is False


# ─────────────────────────────────────────────────────────────
#  sil
# ─────────────────────────────────────────────────────────────

class TestSil:
    def test_sil_basarili(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        assert svc.sil("5") is True
        mock_repo.delete.assert_called_once_with("5")

    def test_sil_hatasi(self, svc, reg):
        mock_repo = MagicMock()
        mock_repo.delete.side_effect = Exception("Hata")
        reg.get.return_value = mock_repo
        assert svc.sil("5") is False

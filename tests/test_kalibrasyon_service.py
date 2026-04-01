"""
KalibrasyonService Test Suite

Kapsam:
- Başlatma
- get_kalibrasyon_listesi: tümü ve cihaz filtresi
- get_kalibrasyon_tipleri
- get_cihaz_listesi
- kaydet: INSERT ve UPDATE (SonucYonetici döndürür)
- sil

Not: Tüm metodlar SonucYonetici döndürür. Test'ler SonucYonetici.basarili ve SonucYonetici.veri'yi doğrular.
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
        result = svc.get_kalibrasyon_listesi()
        assert result.basarili is True
        assert result.veri == []

    def test_tum_liste(self, svc, reg):
        veri = [
            {"Kalid": "1", "Cihazid": "C01", "BitisTarihi": "2026-06-01"},
            {"Kalid": "2", "Cihazid": "C02", "BitisTarihi": "2026-12-01"},
        ]
        reg.get("Kalibrasyon").get_all.return_value = veri
        result = svc.get_kalibrasyon_listesi()
        assert result.basarili is True
        assert len(result.veri) == 2

    def test_cihaz_filtresi(self, svc, reg):
        veri = [
            {"Kalid": "1", "Cihazid": "C01"},
            {"Kalid": "2", "Cihazid": "C02"},
            {"Kalid": "3", "Cihazid": "C01"},
        ]
        reg.get("Kalibrasyon").get_all.return_value = veri
        result = svc.get_kalibrasyon_listesi(cihaz_id="C01")
        assert result.basarili is True
        assert len(result.veri) == 2
        assert all(r["Cihazid"] == "C01" for r in result.veri)

    def test_cihaz_filtresi_eslesme_yok(self, svc, reg):
        reg.get("Kalibrasyon").get_all.return_value = [
            {"Kalid": "1", "Cihazid": "C01"}
        ]
        result = svc.get_kalibrasyon_listesi(cihaz_id="C99")
        assert result.basarili is True
        assert result.veri == []

    def test_repo_hatasi(self, svc, reg):
        reg.get("Kalibrasyon").get_all.side_effect = Exception("Hata")
        result = svc.get_kalibrasyon_listesi()
        assert result.basarili is False

    def test_cihaz_id_string_donusumu(self, svc, reg):
        """Cihaz ID tipi farklı olsa da karşılaştırma çalışmalı."""
        reg.get("Kalibrasyon").get_all.return_value = [
            {"Kalid": "1", "Cihazid": "101"},
        ]
        result = svc.get_kalibrasyon_listesi(cihaz_id=101)  # int
        assert result.basarili is True
        assert len(result.veri) == 1


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
        assert result.basarili is True
        assert "İç Kalibrasyon" in result.veri
        assert "Dış Kalibrasyon" in result.veri
        assert "Dahil Edilmez" not in result.veri

    def test_tekrarlar_temizlenir(self, svc, reg):
        reg.get("Sabitler").get_all.return_value = [
            {"Kod": "KalibrasyonTipi", "MenuEleman": "İç Kalibrasyon"},
            {"Kod": "KalibrasyonTipi", "MenuEleman": "İç Kalibrasyon"},
        ]
        result = svc.get_kalibrasyon_tipleri()
        assert result.basarili is True
        assert result.veri.count("İç Kalibrasyon") == 1

    def test_alfabetik_sirali(self, svc, reg):
        reg.get("Sabitler").get_all.return_value = [
            {"Kod": "KalibrasyonTipi", "MenuEleman": "Zorlu"},
            {"Kod": "KalibrasyonTipi", "MenuEleman": "Ağır"},
        ]
        result = svc.get_kalibrasyon_tipleri()
        assert result.basarili is True
        assert result.veri == sorted(result.veri)

    def test_sabitler_hatasi(self, svc, reg):
        reg.get("Sabitler").get_all.side_effect = Exception("Hata")
        result = svc.get_kalibrasyon_tipleri()
        assert result.basarili is False


# ─────────────────────────────────────────────────────────────
#  get_cihaz_listesi
# ─────────────────────────────────────────────────────────────

class TestGetCihazListesi:
    def test_cihaz_listesi(self, svc, reg):
        reg.get("Cihazlar").get_all.return_value = [
            {"Cihazid": "C01"}, {"Cihazid": "C02"}
        ]
        result = svc.get_cihaz_listesi()
        assert result.basarili is True
        assert len(result.veri) == 2

    def test_repo_hatasi(self, svc, reg):
        reg.get("Cihazlar").get_all.side_effect = Exception("Hata")
        result = svc.get_cihaz_listesi()
        assert result.basarili is False


# ─────────────────────────────────────────────────────────────
#  kaydet
# ─────────────────────────────────────────────────────────────

class TestKaydet:
    def test_insert_basarili(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        veri = {"Cihazid": "C01", "YapilanTarih": "2026-01-15"}
        result = svc.kaydet(veri, guncelle=False)
        assert result.basarili is True
        mock_repo.insert.assert_called_once_with(veri)

    def test_update_basarili(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        veri = {"Kalid": "5", "Durum": "Geçerli"}
        result = svc.kaydet(veri, guncelle=True)
        assert result.basarili is True
        mock_repo.update.assert_called_once_with("5", veri)

    def test_update_pk_yoksa_hata(self, svc, reg):
        veri = {"Cihazid": "C01"}
        result = svc.kaydet(veri, guncelle=True)
        assert result.basarili is False

    def test_insert_repo_hatasi(self, svc, reg):
        mock_repo = MagicMock()
        mock_repo.insert.side_effect = Exception("DB Hatası")
        reg.get.return_value = mock_repo
        result = svc.kaydet({"Cihazid": "C01"}, guncelle=False)
        assert result.basarili is False


# ─────────────────────────────────────────────────────────────
#  sil
# ─────────────────────────────────────────────────────────────

class TestSil:
    def test_sil_basarili(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        result = svc.sil("5")
        assert result.basarili is True
        mock_repo.delete.assert_called_once_with("5")

    def test_sil_repo_hatasi(self, svc, reg):
        mock_repo = MagicMock()
        mock_repo.delete.side_effect = Exception("Silinemedi")
        reg.get.return_value = mock_repo
        result = svc.sil("5")
        assert result.basarili is False

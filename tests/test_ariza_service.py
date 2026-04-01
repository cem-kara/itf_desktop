"""ArizaService testleri (SonucYonetici uyumlu)."""
import pytest
from unittest.mock import MagicMock
from core.services.ariza_service import ArizaService



# ─────────────────────────────────────────────────────────────
#  Fixture'lar
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def reg():
    """Her test için taze MagicMock registry."""
    return MagicMock()


@pytest.fixture
def svc(reg):
    return ArizaService(reg)


# ─────────────────────────────────────────────────────────────
#  Başlatma
# ─────────────────────────────────────────────────────────────

class TestInit:
    def test_none_registry_hata_firlatar(self):
        with pytest.raises(ValueError):
            ArizaService(None)

    def test_registry_saklanir(self, reg):
        s = ArizaService(reg)
        assert s._r is reg


# ─────────────────────────────────────────────────────────────
#  get_ariza_listesi
# ─────────────────────────────────────────────────────────────

class TestGetArizaListesi:
    def test_bos_liste(self, svc, reg):
        reg.get("Cihaz_Ariza").get_all.return_value = []
        sonuc = svc.get_ariza_listesi()
        assert sonuc.basarili is True
        assert sonuc.veri == []

    def test_tum_liste(self, svc, reg):
        veri = [
            {"Arizaid": "1", "Cihazid": "C01"},
            {"Arizaid": "2", "Cihazid": "C02"},
        ]
        reg.get("Cihaz_Ariza").get_all.return_value = veri
        sonuc = svc.get_ariza_listesi()
        assert sonuc.basarili is True
        assert len(sonuc.veri) == 2

    def test_cihaz_filtresi(self, svc, reg):
        veri = [
            {"Arizaid": "1", "Cihazid": "C01"},
            {"Arizaid": "2", "Cihazid": "C02"},
            {"Arizaid": "3", "Cihazid": "C01"},
        ]
        reg.get("Cihaz_Ariza").get_all.return_value = veri
        sonuc = svc.get_ariza_listesi(cihaz_id="C01")
        assert sonuc.basarili is True
        assert len(sonuc.veri) == 2
        assert all(r["Cihazid"] == "C01" for r in sonuc.veri)

    def test_cihaz_filtresi_bos_sonuc(self, svc, reg):
        reg.get("Cihaz_Ariza").get_all.return_value = [
            {"Arizaid": "1", "Cihazid": "C01"}
        ]
        sonuc = svc.get_ariza_listesi(cihaz_id="C99")
        assert sonuc.basarili is True
        assert sonuc.veri == []

    def test_repo_hatasi_bos_liste_doner(self, svc, reg):
        reg.get("Cihaz_Ariza").get_all.side_effect = Exception("DB çöktü")
        sonuc = svc.get_ariza_listesi()
        assert sonuc.basarili is False


# ─────────────────────────────────────────────────────────────
#  Sabitler'den liste metodları
# ─────────────────────────────────────────────────────────────

class TestGetSabitlerListeleri:
    def _sabitler(self):
        return [
            {"Kod": "ArızaTipi",   "MenuEleman": "Mekanik"},
            {"Kod": "ArızaTipi",   "MenuEleman": "Elektrik"},
            {"Kod": "ArızaTipi",   "MenuEleman": "Elektrik"},  # tekrar
            {"Kod": "ArızaDurumu", "MenuEleman": "Açık"},
            {"Kod": "ArızaDurumu", "MenuEleman": "Kapalı"},
            {"Kod": "Oncelik",     "MenuEleman": "Yüksek"},
            {"Kod": "Oncelik",     "MenuEleman": "Düşük"},
            {"Kod": "BaskaBir",    "MenuEleman": "Gürültü"},  # dahil edilmemeli
        ]

    def test_ariza_tipleri(self, svc, reg):
        reg.get("Sabitler").get_all.return_value = self._sabitler()
        sonuc = svc.get_ariza_tipleri()
        assert sonuc.basarili is True
        assert sorted(sonuc.veri) == ["Elektrik", "Mekanik"]

    def test_ariza_tipleri_tekrar_yok(self, svc, reg):
        reg.get("Sabitler").get_all.return_value = self._sabitler()
        sonuc = svc.get_ariza_tipleri()
        assert sonuc.basarili is True
        assert sonuc.veri.count("Elektrik") == 1

    def test_ariza_tipleri_alfabetik(self, svc, reg):
        reg.get("Sabitler").get_all.return_value = self._sabitler()
        sonuc = svc.get_ariza_tipleri()
        assert sonuc.basarili is True
        assert sonuc.veri == sorted(sonuc.veri)

    def test_ariza_durumlari(self, svc, reg):
        reg.get("Sabitler").get_all.return_value = self._sabitler()
        sonuc = svc.get_ariza_durumlari()
        assert sonuc.basarili is True
        assert "Açık" in sonuc.veri
        assert "Kapalı" in sonuc.veri
        assert "Gürültü" not in sonuc.veri

    def test_oncelik_seviyeleri(self, svc, reg):
        reg.get("Sabitler").get_all.return_value = self._sabitler()
        sonuc = svc.get_oncelik_seviyeleri()
        assert sonuc.basarili is True
        assert "Yüksek" in sonuc.veri
        assert "Düşük" in sonuc.veri

    def test_sabitler_hatasi_bos_liste(self, svc, reg):
        reg.get("Sabitler").get_all.side_effect = Exception("Hata")
        assert svc.get_ariza_tipleri().basarili is False
        assert svc.get_ariza_durumlari().basarili is False
        assert svc.get_oncelik_seviyeleri().basarili is False


# ─────────────────────────────────────────────────────────────
#  Cihaz metodları
# ─────────────────────────────────────────────────────────────

class TestCihaz:
    def test_cihaz_listesi(self, svc, reg):
        reg.get("Cihazlar").get_all.return_value = [
            {"Cihazid": "C01"}, {"Cihazid": "C02"}
        ]
        sonuc = svc.get_cihaz_listesi()
        assert sonuc.basarili is True
        assert len(sonuc.veri) == 2

    def test_tek_cihaz(self, svc, reg):
        reg.get("Cihazlar").get_by_pk.return_value = {"Cihazid": "C01", "Adi": "CT"}
        sonuc = svc.get_cihaz("C01")
        assert sonuc.basarili is True
        assert sonuc.veri["Adi"] == "CT"

    def test_cihaz_bulunamadi(self, svc, reg):
        reg.get("Cihazlar").get_by_pk.return_value = None
        sonuc = svc.get_cihaz("YOK")
        assert sonuc.basarili is True
        assert sonuc.veri is None


# ─────────────────────────────────────────────────────────────
#  kaydet
# ─────────────────────────────────────────────────────────────

class TestKaydet:
    def test_insert(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        veri = {"Cihazid": "C01", "Aciklama": "Arıza var"}
        sonuc = svc.kaydet(veri, guncelle=False)
        assert sonuc.basarili is True
        mock_repo.insert.assert_called_once_with(veri)

    def test_update_basarili(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        veri = {"Arizaid": "42", "Durum": "Kapalı"}
        sonuc = svc.kaydet(veri, guncelle=True)
        assert sonuc.basarili is True
        mock_repo.update.assert_called_once_with("42", veri)

    def test_update_pk_yoksa_false(self, svc, reg):
        veri = {"Aciklama": "PK yok"}
        sonuc = svc.kaydet(veri, guncelle=True)
        assert sonuc.basarili is False

    def test_insert_db_hatasi(self, svc, reg):
        mock_repo = MagicMock()
        mock_repo.insert.side_effect = Exception("Yazma hatası")
        reg.get.return_value = mock_repo
        sonuc = svc.kaydet({"Cihazid": "C01"}, guncelle=False)
        assert sonuc.basarili is False


# ─────────────────────────────────────────────────────────────
#  sil
# ─────────────────────────────────────────────────────────────

class TestSil:
    def test_sil_basarili(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        sonuc = svc.sil("42")
        assert sonuc.basarili is True
        mock_repo.delete.assert_called_once_with("42")

    def test_sil_hatasi(self, svc, reg):
        mock_repo = MagicMock()
        mock_repo.delete.side_effect = Exception("Silme hatası")
        reg.get.return_value = mock_repo
        sonuc = svc.sil("42")
        assert sonuc.basarili is False

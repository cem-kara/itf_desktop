"""
ArizaService Test Suite

Kapsam:
- Başlatma doğrulaması
- get_ariza_listesi: tümü, cihaz filtresi, hata durumu
- get_ariza_tipleri / get_ariza_durumlari / get_oncelik_seviyeleri
- get_cihaz_listesi / get_cihaz
- kaydet: INSERT ve UPDATE
- sil

Not: kaydet(guncelle=True) testi şu an FAIL verir çünkü
servis veri.get("ArizaId") kullanıyor, gerçek PK adı "Arizaid".
Testi geçirmek için ariza_service.py satır 144'ü düzelt:
    veri.get("ArizaId")  →  veri.get("Arizaid")
"""
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
        assert svc.get_ariza_listesi() == []

    def test_tum_liste(self, svc, reg):
        veri = [
            {"Arizaid": "1", "Cihazid": "C01"},
            {"Arizaid": "2", "Cihazid": "C02"},
        ]
        reg.get("Cihaz_Ariza").get_all.return_value = veri
        result = svc.get_ariza_listesi()
        assert len(result) == 2

    def test_cihaz_filtresi(self, svc, reg):
        veri = [
            {"Arizaid": "1", "Cihazid": "C01"},
            {"Arizaid": "2", "Cihazid": "C02"},
            {"Arizaid": "3", "Cihazid": "C01"},
        ]
        reg.get("Cihaz_Ariza").get_all.return_value = veri
        result = svc.get_ariza_listesi(cihaz_id="C01")
        assert len(result) == 2
        assert all(r["Cihazid"] == "C01" for r in result)

    def test_cihaz_filtresi_bos_sonuc(self, svc, reg):
        reg.get("Cihaz_Ariza").get_all.return_value = [
            {"Arizaid": "1", "Cihazid": "C01"}
        ]
        result = svc.get_ariza_listesi(cihaz_id="C99")
        assert result == []

    def test_repo_hatasi_bos_liste_doner(self, svc, reg):
        reg.get("Cihaz_Ariza").get_all.side_effect = Exception("DB çöktü")
        assert svc.get_ariza_listesi() == []


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
        result = svc.get_ariza_tipleri()
        assert sorted(result) == ["Elektrik", "Mekanik"]

    def test_ariza_tipleri_tekrar_yok(self, svc, reg):
        reg.get("Sabitler").get_all.return_value = self._sabitler()
        result = svc.get_ariza_tipleri()
        assert result.count("Elektrik") == 1

    def test_ariza_tipleri_alfabetik(self, svc, reg):
        reg.get("Sabitler").get_all.return_value = self._sabitler()
        result = svc.get_ariza_tipleri()
        assert result == sorted(result)

    def test_ariza_durumlari(self, svc, reg):
        reg.get("Sabitler").get_all.return_value = self._sabitler()
        result = svc.get_ariza_durumlari()
        assert "Açık" in result
        assert "Kapalı" in result
        assert "Gürültü" not in result

    def test_oncelik_seviyeleri(self, svc, reg):
        reg.get("Sabitler").get_all.return_value = self._sabitler()
        result = svc.get_oncelik_seviyeleri()
        assert "Yüksek" in result
        assert "Düşük" in result

    def test_sabitler_hatasi_bos_liste(self, svc, reg):
        reg.get("Sabitler").get_all.side_effect = Exception("Hata")
        assert svc.get_ariza_tipleri() == []
        assert svc.get_ariza_durumlari() == []
        assert svc.get_oncelik_seviyeleri() == []


# ─────────────────────────────────────────────────────────────
#  Cihaz metodları
# ─────────────────────────────────────────────────────────────

class TestCihaz:
    def test_cihaz_listesi(self, svc, reg):
        reg.get("Cihazlar").get_all.return_value = [
            {"Cihazid": "C01"}, {"Cihazid": "C02"}
        ]
        assert len(svc.get_cihaz_listesi()) == 2

    def test_tek_cihaz(self, svc, reg):
        reg.get("Cihazlar").get_by_pk.return_value = {"Cihazid": "C01", "Adi": "CT"}
        result = svc.get_cihaz("C01")
        assert result["Adi"] == "CT"

    def test_cihaz_bulunamadi(self, svc, reg):
        reg.get("Cihazlar").get_by_pk.return_value = None
        assert svc.get_cihaz("YOK") is None


# ─────────────────────────────────────────────────────────────
#  kaydet
# ─────────────────────────────────────────────────────────────

class TestKaydet:
    def test_insert(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        veri = {"Cihazid": "C01", "Aciklama": "Arıza var"}
        assert svc.kaydet(veri, guncelle=False) is True
        mock_repo.insert.assert_called_once_with(veri)

    def test_update_basarili(self, svc, reg):
        """
        BUG: Bu test şu an FAIL verir.
        Servis veri.get("ArizaId") kullanıyor ama gerçek PK "Arizaid".
        ariza_service.py satır 144:  veri.get("ArizaId")  →  veri.get("Arizaid")
        """
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        veri = {"Arizaid": "42", "Durum": "Kapalı"}
        assert svc.kaydet(veri, guncelle=True) is True
        mock_repo.update.assert_called_once_with("42", veri)

    def test_update_pk_yoksa_false(self, svc, reg):
        """PK olmadan UPDATE False döner (bug düzeldikten sonra da geçmeli)."""
        veri = {"Aciklama": "PK yok"}
        assert svc.kaydet(veri, guncelle=True) is False

    def test_insert_db_hatasi(self, svc, reg):
        mock_repo = MagicMock()
        mock_repo.insert.side_effect = Exception("Yazma hatası")
        reg.get.return_value = mock_repo
        assert svc.kaydet({"Cihazid": "C01"}, guncelle=False) is False


# ─────────────────────────────────────────────────────────────
#  sil
# ─────────────────────────────────────────────────────────────

class TestSil:
    def test_sil_basarili(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        assert svc.sil("42") is True
        mock_repo.delete.assert_called_once_with("42")

    def test_sil_hatasi(self, svc, reg):
        mock_repo = MagicMock()
        mock_repo.delete.side_effect = Exception("Silme hatası")
        reg.get.return_value = mock_repo
        assert svc.sil("42") is False

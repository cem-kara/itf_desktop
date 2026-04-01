import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock

from core.services.izin_service import IzinService


@pytest.fixture
def reg():
    return MagicMock()


@pytest.fixture
def svc(reg):
    return IzinService(reg)


class TestInit:
    def test_none_registry_hata(self):
        with pytest.raises(ValueError):
            IzinService(None)


class TestShouldSetPasif:
    def test_31_gun_true(self, svc):
        assert svc.should_set_pasif("Yillik Izin", 31).veri is True

    def test_30_gun_false(self, svc):
        assert svc.should_set_pasif("Yillik Izin", 30).veri is False

    def test_ucretsiz_true(self, svc):
        assert svc.should_set_pasif("Ucretsiz Izin", 1).veri is True


class TestGetIzinListesi:
    def test_filtreler(self, svc, reg):
        reg.get("Izin_Giris").get_all.return_value = [
            {"Izinid": "1", "TC": "111", "Ay": "1", "Yil": "2026"},
            {"Izinid": "2", "TC": "222", "Ay": "1", "Yil": "2026"},
            {"Izinid": "3", "TC": "111", "Ay": "2", "Yil": "2026"},
        ]

        hepsi = svc.get_izin_listesi()
        assert hepsi.basarili is True
        assert len(hepsi.veri) == 3

        tc_filtre = svc.get_izin_listesi(tc="111")
        assert len(tc_filtre.veri) == 2

        ay_yil = svc.get_izin_listesi(ay=1, yil=2026)
        assert len(ay_yil.veri) == 2

    def test_repo_hatasi(self, svc, reg):
        reg.get("Izin_Giris").get_all.side_effect = Exception("db")
        sonuc = svc.get_izin_listesi()
        assert sonuc.basarili is False


class TestGetIzinTipleri:
    def test_liste_ve_tekrar_temizleme(self, svc, reg):
        reg.get("Sabitler").get_all.return_value = [
            {"Kod": "IzinTipi", "MenuEleman": "Yillik Izin"},
            {"Kod": "IzinTipi", "MenuEleman": "Yillik Izin"},
            {"Kod": "IzinTipi", "MenuEleman": "Mazeret Izni"},
            {"Kod": "Diger", "MenuEleman": "Haric"},
        ]
        sonuc = svc.get_izin_tipleri()
        assert sonuc.basarili is True
        assert sonuc.veri.count("Yillik Izin") == 1
        assert "Mazeret Izni" in sonuc.veri


class TestKaydetVeIptal:
    def test_insert(self, svc, reg):
        veri = {"TC": "111", "IzinTipi": "Yillik Izin", "Gun": 5}
        sonuc = svc.kaydet(veri, guncelle=False)
        assert sonuc.basarili is True
        reg.get("Izin_Giris").insert.assert_called_once_with(veri)

    def test_update(self, svc, reg):
        veri = {"Izinid": "7", "Durum": "Onayli"}
        sonuc = svc.kaydet(veri, guncelle=True)
        assert sonuc.basarili is True
        reg.get("Izin_Giris").update.assert_called_once_with("7", veri)

    def test_update_pk_yok(self, svc):
        sonuc = svc.kaydet({"Durum": "Onayli"}, guncelle=True)
        assert sonuc.basarili is False

    def test_iptal(self, svc, reg):
        sonuc = svc.iptal_et("9")
        assert sonuc.basarili is True
        reg.get("Izin_Giris").delete.assert_called_once_with("9")


class TestYillikHak:
    def test_hizmet_yili_hesabi(self, svc):
        az = (date.today() - timedelta(days=200)).isoformat()
        assert svc.hesapla_yillik_hak(az).veri == 0.0

        t = date.today()
        bes = date(t.year - 5, t.month, min(t.day, 28)).isoformat()
        assert svc.hesapla_yillik_hak(bes).veri == 20.0

        onbir = date(t.year - 11, t.month, min(t.day, 28)).isoformat()
        assert svc.hesapla_yillik_hak(onbir).veri == 30.0


class TestCreateOrUpdateIzinBilgi:
    def test_insert_yapar(self, svc, reg):
        repo = reg.get("Izin_Bilgi")
        repo.get_by_id.return_value = None

        sonuc = svc.create_or_update_izin_bilgi("123", "Test Kisi", "2015-01-01")
        assert sonuc.basarili is True
        assert repo.insert.called

    def test_update_yapar(self, svc, reg):
        repo = reg.get("Izin_Bilgi")
        repo.get_by_id.return_value = {"TCKimlik": "123"}

        sonuc = svc.create_or_update_izin_bilgi("123", "Test Kisi", "2015-01-01")
        assert sonuc.basarili is True
        assert repo.update.called


class TestMaxGunVeLimit:
    def test_yillik_max_60(self, svc, reg):
        izin_repo = MagicMock()
        sabit_repo = MagicMock()
        izin_repo.get_by_id.return_value = {"YillikKalan": 70}
        sabit_repo.get_all.return_value = []

        reg.get.side_effect = lambda name: izin_repo if name == "Izin_Bilgi" else sabit_repo

        max_sonuc = svc.get_izin_max_gun("111", "Yıllık İzin")
        assert max_sonuc == 60

        limit = svc.validate_izin_sure_limit("111", "Yıllık İzin", 61)
        assert limit.basarili is False

    def test_insert_limit_disi_kaydi_engeller(self, svc, reg):
        izin_repo = MagicMock()
        sabit_repo = MagicMock()
        giris_repo = MagicMock()

        izin_repo.get_by_id.return_value = {"YillikKalan": 70}
        sabit_repo.get_all.return_value = []

        def _get(name):
            if name == "Izin_Bilgi":
                return izin_repo
            if name == "Sabitler":
                return sabit_repo
            if name == "Izin_Giris":
                return giris_repo
            return MagicMock()

        reg.get.side_effect = _get

        sonuc = svc.insert_izin_giris({"Personelid": "111", "IzinTipi": "Yıllık İzin", "Gun": 61})
        assert sonuc.basarili is False
        giris_repo.insert.assert_not_called()


class TestIzinCakisma:
    def test_cakisma_true(self, svc, reg):
        reg.get("Izin_Giris").get_all.return_value = [
            {
                "Izinid": "A1",
                "Personelid": "111",
                "BaslamaTarihi": "2026-03-10",
                "BitisTarihi": "2026-03-15",
                "Durum": "Onaylandi",
            }
        ]
        sonuc = svc.has_izin_cakisma("111", "2026-03-14", "2026-03-20")
        assert sonuc.basarili is True
        assert sonuc.veri is True

    def test_cakisma_false(self, svc, reg):
        reg.get("Izin_Giris").get_all.return_value = []
        sonuc = svc.has_izin_cakisma("111", "2026-03-14", "2026-03-20")
        assert sonuc.basarili is True
        assert sonuc.veri is False

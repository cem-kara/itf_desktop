"""
IzinService Test Suite

Kapsam:
- Başlatma doğrulaması
- should_set_pasif: tüm edge case'ler (KRİTİK iş kuralı)
- get_izin_listesi: filtreleme
- get_izin_tipleri
- kaydet / iptal_et

Önemli: should_set_pasif 30 gün sınırı iş kuralıdır.
Bu testin tamamı geçmeli, geçmiyorsa izin_service.py'yi düzelt.
"""
import pytest
from unittest.mock import MagicMock
from datetime import date, timedelta
from typing import Any, cast
from core.services.izin_service import IzinService


# ─────────────────────────────────────────────────────────────
#  Fixture'lar
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def reg():
    return MagicMock()


@pytest.fixture
def svc(reg):
    return IzinService(reg)


# ─────────────────────────────────────────────────────────────
#  Başlatma
# ─────────────────────────────────────────────────────────────

class TestInit:
    def test_none_registry_hata_firlatar(self):
        with pytest.raises(ValueError):
            IzinService(cast(Any, None))

    def test_registry_saklanir(self, reg):
        s = IzinService(reg)
        assert s._r is reg


# ─────────────────────────────────────────────────────────────
#  should_set_pasif — KRİTİK İŞ KURALI
#
#  Kural: 30+ gün VEYA ücretsiz/aylıksız izin → personel Pasif olur
#  Bu kural yanlış çalışırsa personel yanlışlıkla pasife alınır
#  ya da alınması gerekirken aktif kalır.
# ─────────────────────────────────────────────────────────────

class TestShouldSetPasif:

    # ── Gün sınırı ──────────────────────────────────────────

    def test_31_gun_pasif_olmali(self, svc):
        assert svc.should_set_pasif("Yıllık İzin", 31) is True

    def test_30_gun_pasif_olmamali(self, svc):
        """Tam 30 gün: sınır dahil değil, aktif kalmalı."""
        assert svc.should_set_pasif("Yıllık İzin", 30) is False

    def test_29_gun_pasif_olmamali(self, svc):
        assert svc.should_set_pasif("Yıllık İzin", 29) is False

    def test_1_gun_pasif_olmamali(self, svc):
        assert svc.should_set_pasif("Yıllık İzin", 1) is False

    def test_0_gun_pasif_olmamali(self, svc):
        assert svc.should_set_pasif("Yıllık İzin", 0) is False

    # ── Ücretsiz / aylıksız izin türleri ────────────────────

    def test_ucretsiz_izin_1_gun_pasif_olmali(self, svc):
        """Süresine bakılmaksızın ücretsiz izin → pasif."""
        assert svc.should_set_pasif("Ücretsiz İzin", 1) is True

    def test_ucretsiz_izin_ascii_1_gun_pasif_olmali(self, svc):
        """ASCII yazım (ucretsiz) da tanınmalı."""
        assert svc.should_set_pasif("Ucretsiz Izin", 1) is True

    def test_ayliksiz_izin_1_gun_pasif_olmali(self, svc):
        assert svc.should_set_pasif("Aylıksız İzin", 1) is True

    def test_ayliksiz_izin_kucuk_harf(self, svc):
        assert svc.should_set_pasif("aylıksız izin", 1) is True

    def test_ayliksiz_bosluklu(self, svc):
        """Baştaki/sondaki boşluklar sorun çıkarmamalı."""
        assert svc.should_set_pasif("  Aylıksız İzin  ", 1) is True

    # ── Normal izin türleri ──────────────────────────────────

    def test_yillik_izin_30_gun_pasif_olmamali(self, svc):
        assert svc.should_set_pasif("Yıllık İzin", 30) is False

    def test_mazeret_izin_5_gun_pasif_olmamali(self, svc):
        assert svc.should_set_pasif("Mazeret İzni", 5) is False

    def test_dogum_izni_10_gun_pasif_olmamali(self, svc):
        assert svc.should_set_pasif("Doğum İzni", 10) is False

    def test_saglik_raporu_30_gun_pasif_olmamali(self, svc):
        assert svc.should_set_pasif("Sağlık Raporu", 30) is False

    # ── Edge case'ler ────────────────────────────────────────

    def test_none_izin_tipi(self, svc):
        """None izin tipi hata fırlatmamalı."""
        assert svc.should_set_pasif(None, 5) is False

    def test_bos_izin_tipi(self, svc):
        assert svc.should_set_pasif("", 5) is False

    def test_31_gun_ve_ucretsiz_birlikte(self, svc):
        """İkisi de sağlanıyor — hâlâ True."""
        assert svc.should_set_pasif("Ücretsiz İzin", 31) is True


# ─────────────────────────────────────────────────────────────
#  get_izin_listesi
# ─────────────────────────────────────────────────────────────

class TestGetIzinListesi:
    def _veri(self):
        return [
            {"Izinid": "1", "TC": "111", "Ay": "1", "Yil": "2026"},
            {"Izinid": "2", "TC": "222", "Ay": "1", "Yil": "2026"},
            {"Izinid": "3", "TC": "111", "Ay": "2", "Yil": "2026"},
            {"Izinid": "4", "TC": "111", "Ay": "1", "Yil": "2025"},
        ]

    def test_tum_liste(self, svc, reg):
        reg.get("Izin_Giris").get_all.return_value = self._veri()
        assert len(svc.get_izin_listesi()) == 4

    def test_tc_filtresi(self, svc, reg):
        reg.get("Izin_Giris").get_all.return_value = self._veri()
        result = svc.get_izin_listesi(tc="111")
        assert len(result) == 3
        assert all(r["TC"] == "111" for r in result)

    def test_ay_yil_filtresi(self, svc, reg):
        reg.get("Izin_Giris").get_all.return_value = self._veri()
        result = svc.get_izin_listesi(ay=1, yil=2026)
        assert len(result) == 2

    def test_repo_hatasi_bos_liste(self, svc, reg):
        reg.get("Izin_Giris").get_all.side_effect = Exception("Hata")
        assert svc.get_izin_listesi() == []


# ─────────────────────────────────────────────────────────────
#  get_izin_tipleri
# ─────────────────────────────────────────────────────────────

class TestGetIzinTipleri:
    def test_tipleri_getirir(self, svc, reg):
        reg.get("Sabitler").get_all.return_value = [
            {"Kod": "IzinTipi", "MenuEleman": "Yıllık İzin"},
            {"Kod": "IzinTipi", "MenuEleman": "Mazeret İzni"},
            {"Kod": "BaskaBir", "MenuEleman": "Dahil Edilmez"},
        ]
        result = svc.get_izin_tipleri()
        assert "Yıllık İzin" in result
        assert "Mazeret İzni" in result
        assert "Dahil Edilmez" not in result

    def test_tekrarlar_temizlenir(self, svc, reg):
        reg.get("Sabitler").get_all.return_value = [
            {"Kod": "IzinTipi", "MenuEleman": "Yıllık İzin"},
            {"Kod": "IzinTipi", "MenuEleman": "Yıllık İzin"},
        ]
        result = svc.get_izin_tipleri()
        assert result.count("Yıllık İzin") == 1

    def test_alfabetik_sirali(self, svc, reg):
        reg.get("Sabitler").get_all.return_value = [
            {"Kod": "IzinTipi", "MenuEleman": "Ücretli"},
            {"Kod": "IzinTipi", "MenuEleman": "Aylıksız"},
        ]
        result = svc.get_izin_tipleri()
        assert result == sorted(result)


# ─────────────────────────────────────────────────────────────
#  kaydet
# ─────────────────────────────────────────────────────────────

class TestKaydet:
    def test_insert(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        veri = {"TC": "111", "IzinTipi": "Yıllık İzin", "Gun": 5}
        assert svc.kaydet(veri, guncelle=False) is True
        mock_repo.insert.assert_called_once_with(veri)

    def test_update_basarili(self, svc, reg):
        """
        NOT: Bu test şu an FAIL VEREBİLİR.
        Servis veri.get("IzinId") kullanıyor, gerçek PK "Izinid".
        izin_service.py'de düzelt: veri.get("IzinId")  →  veri.get("Izinid")
        """
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        veri = {"Izinid": "7", "Durum": "Onaylı"}
        assert svc.kaydet(veri, guncelle=True) is True
        mock_repo.update.assert_called_once_with("7", veri)

    def test_update_pk_yoksa_false(self, svc, reg):
        veri = {"IzinTipi": "Yıllık İzin"}
        assert svc.kaydet(veri, guncelle=True) is False

    def test_db_hatasi_false_doner(self, svc, reg):
        mock_repo = MagicMock()
        mock_repo.insert.side_effect = Exception("Hata")
        reg.get.return_value = mock_repo
        assert svc.kaydet({"TC": "111"}, guncelle=False) is False


# ─────────────────────────────────────────────────────────────
#  iptal_et
# ─────────────────────────────────────────────────────────────

class TestIptalEt:
    def test_iptal_basarili(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        assert svc.iptal_et("7") is True
        mock_repo.delete.assert_called_once_with("7")

    def test_iptal_hatasi(self, svc, reg):
        mock_repo = MagicMock()
        mock_repo.delete.side_effect = Exception("Hata")
        reg.get.return_value = mock_repo
        assert svc.iptal_et("7") is False


# ─────────────────────────────────────────────────────────────
#  Yıllık Hak Hesaplama
# ─────────────────────────────────────────────────────────────

class TestHesaplaYillikHak:
    def test_1_yildan_az_hizmet_0_gun(self, svc):
        baslama = (date.today() - timedelta(days=200)).isoformat()
        assert svc.hesapla_yillik_hak(baslama) == 0.0

    def test_1_ile_10_yil_arasi_20_gun(self, svc):
        t = date.today()
        baslama = date(t.year - 5, t.month, min(t.day, 28)).isoformat()
        assert svc.hesapla_yillik_hak(baslama) == 20.0

    def test_10_yil_dahil_20_gun(self, svc):
        t = date.today()
        baslama = date(t.year - 10, t.month, min(t.day, 28)).isoformat()
        assert svc.hesapla_yillik_hak(baslama) == 20.0

    def test_10_yildan_fazla_30_gun(self, svc):
        t = date.today()
        baslama = date(t.year - 11, t.month, min(t.day, 28)).isoformat()
        assert svc.hesapla_yillik_hak(baslama) == 30.0

    def test_gecersiz_tarih_0_gun(self, svc):
        assert svc.hesapla_yillik_hak("gecersiz") == 0.0


# ─────────────────────────────────────────────────────────────
#  Izin_Bilgi oluşturma / güncelleme
# ─────────────────────────────────────────────────────────────

class TestCreateOrUpdateIzinBilgi:
    def test_yeni_kayit_insert_yapar(self, svc, reg):
        repo = MagicMock()
        repo.get_by_id.return_value = None
        reg.get.return_value = repo

        ok = svc.create_or_update_izin_bilgi(
            tc="12345678901",
            ad_soyad="Test Kisi",
            baslama_tarihi="2015-01-01",
        )

        assert ok is True
        repo.insert.assert_called_once()
        payload = repo.insert.call_args[0][0]
        assert payload["TCKimlik"] == "12345678901"
        assert payload["AdSoyad"] == "Test Kisi"
        assert payload["YillikKalan"] in (20.0, 30.0)

    def test_mevcut_kayit_update_yapar(self, svc, reg):
        repo = MagicMock()
        repo.get_by_id.return_value = {"TCKimlik": "12345678901"}
        reg.get.return_value = repo

        ok = svc.create_or_update_izin_bilgi(
            tc="12345678901",
            ad_soyad="Test Kisi",
            baslama_tarihi="2015-01-01",
        )

        assert ok is True
        repo.update.assert_called_once()
        update_tc, payload = repo.update.call_args[0]
        assert update_tc == "12345678901"
        assert payload["TCKimlik"] == "12345678901"

    def test_tc_bos_ise_false(self, svc):
        assert svc.create_or_update_izin_bilgi("", "Test", "2015-01-01") is False

    def test_sayisal_alanlar_none_olamaz_0_kaydedilir(self, svc, reg):
        repo = MagicMock()
        repo.get_by_id.return_value = None
        reg.get.return_value = repo

        # Hesaplama beklenmedik None dönerse bile payload normalize edilmeli.
        svc.hesapla_yillik_hak = MagicMock(return_value=None)

        ok = svc.create_or_update_izin_bilgi(
            tc="12345678901",
            ad_soyad="Test Kisi",
            baslama_tarihi="",
        )

        assert ok is True
        payload = repo.insert.call_args[0][0]
        assert payload["YillikDevir"] == 0.0
        assert payload["YillikHakedis"] == 0.0
        assert payload["YillikToplamHak"] == 0.0
        assert payload["YillikKullanilan"] == 0.0
        assert payload["YillikKalan"] == 0.0
        assert payload["SuaKullanilabilirHak"] == 0.0
        assert payload["SuaKullanilan"] == 0.0
        assert payload["SuaKalan"] == 0.0
        assert payload["SuaCariYilKazanim"] == 0.0
        assert payload["RaporMazeretTop"] == 0.0


# ─────────────────────────────────────────────────────────────
#  Max gün hesaplama
# ─────────────────────────────────────────────────────────────

class TestGetIzinMaxGun:
    def test_yillik_izin_min_30_ve_kalan(self, svc, reg):
        izin_repo = MagicMock()
        sabit_repo = MagicMock()
        izin_repo.get_by_id.return_value = {"YillikKalan": 50}
        sabit_repo.get_all.return_value = []

        def _get(name):
            return izin_repo if name == "Izin_Bilgi" else sabit_repo

        reg.get.side_effect = _get

        assert svc.get_izin_max_gun("111", "Yıllık İzin") == 30

    def test_yillik_izin_kalan_kadar(self, svc, reg):
        izin_repo = MagicMock()
        sabit_repo = MagicMock()
        izin_repo.get_by_id.return_value = {"YillikKalan": 12}
        sabit_repo.get_all.return_value = []

        def _get(name):
            return izin_repo if name == "Izin_Bilgi" else sabit_repo

        reg.get.side_effect = _get

        assert svc.get_izin_max_gun("111", "Yıllık İzin") == 12

    def test_sua_izin_sua_kullanilabilir_hak(self, svc, reg):
        izin_repo = MagicMock()
        sabit_repo = MagicMock()
        izin_repo.get_by_id.return_value = {"SuaKullanilabilirHak": 7}
        sabit_repo.get_all.return_value = []

        def _get(name):
            return izin_repo if name == "Izin_Bilgi" else sabit_repo

        reg.get.side_effect = _get

        assert svc.get_izin_max_gun("111", "Şua İzni") == 7

    def test_diger_izin_sabitler_aciklama_sayisal(self, svc, reg):
        izin_repo = MagicMock()
        sabit_repo = MagicMock()
        izin_repo.get_by_id.return_value = {}
        sabit_repo.get_all.return_value = [
            {"Kod": "İzin_Tipi", "MenuEleman": "Babalık İzni", "Aciklama": "10 gün"}
        ]

        def _get(name):
            return izin_repo if name == "Izin_Bilgi" else sabit_repo

        reg.get.side_effect = _get

        assert svc.get_izin_max_gun("111", "Babalık İzni") == 10

    def test_diger_izin_aciklama_bos_limitsiz(self, svc, reg):
        izin_repo = MagicMock()
        sabit_repo = MagicMock()
        izin_repo.get_by_id.return_value = {}
        sabit_repo.get_all.return_value = [
            {"Kod": "İzin_Tipi", "MenuEleman": "Özel İzin", "Aciklama": ""}
        ]

        def _get(name):
            return izin_repo if name == "Izin_Bilgi" else sabit_repo

        reg.get.side_effect = _get

        assert svc.get_izin_max_gun("111", "Özel İzin") is None


# ─────────────────────────────────────────────────────────────
#  Limit doğrulama ve insert güvence
# ─────────────────────────────────────────────────────────────

class TestValidateIzinSureLimit:
    def test_gun_sifir_ve_alti_engellenir(self, svc):
        ok, msg = svc.validate_izin_sure_limit("111", "Yıllık İzin", 0)
        assert ok is False
        assert "0'dan büyük" in msg

    def test_limit_yoksa_true(self, svc, reg):
        izin_repo = MagicMock()
        sabit_repo = MagicMock()
        izin_repo.get_by_id.return_value = {}
        sabit_repo.get_all.return_value = [
            {"Kod": "İzin_Tipi", "MenuEleman": "Limitsiz İzin", "Aciklama": ""}
        ]

        def _get(name):
            return izin_repo if name == "Izin_Bilgi" else sabit_repo

        reg.get.side_effect = _get

        ok, msg = svc.validate_izin_sure_limit("111", "Limitsiz İzin", 120)
        assert ok is True
        assert msg == ""

    def test_limit_asimi_false(self, svc, reg):
        izin_repo = MagicMock()
        sabit_repo = MagicMock()
        izin_repo.get_by_id.return_value = {"YillikKalan": 40}
        sabit_repo.get_all.return_value = []

        def _get(name):
            return izin_repo if name == "Izin_Bilgi" else sabit_repo

        reg.get.side_effect = _get

        ok, msg = svc.validate_izin_sure_limit("111", "Yıllık İzin", 31)
        assert ok is False
        assert "maksimum 30" in msg


class TestInsertIzinGirisLimitEnforcement:
    def test_limit_geciyorsa_insert_hata_firlatir(self, svc, reg):
        izin_repo = MagicMock()
        sabit_repo = MagicMock()
        giris_repo = MagicMock()

        izin_repo.get_by_id.return_value = {"YillikKalan": 40}
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

        with pytest.raises(ValueError):
            svc.insert_izin_giris({
                "Personelid": "111",
                "IzinTipi": "Yıllık İzin",
                "Gun": 31,
            })

        giris_repo.insert.assert_not_called()

    def test_limit_icindeyse_insert_yapar(self, svc, reg):
        izin_repo = MagicMock()
        sabit_repo = MagicMock()
        giris_repo = MagicMock()

        izin_repo.get_by_id.return_value = {"YillikKalan": 25}
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

        kayit = {
            "Personelid": "111",
            "IzinTipi": "Yıllık İzin",
            "Gun": 20,
        }
        svc.insert_izin_giris(kayit)
        giris_repo.insert.assert_called_once_with(kayit)


# ─────────────────────────────────────────────────────────────
#  İzin Çakışma Kontrolü
# ─────────────────────────────────────────────────────────────

class TestIzinCakismaKontrolu:
    def test_ayni_personel_tarih_kesisirse_true(self, svc, reg):
        reg.get("Izin_Giris").get_all.return_value = [
            {
                "Izinid": "A1",
                "Personelid": "111",
                "BaslamaTarihi": "2026-03-10",
                "BitisTarihi": "2026-03-15",
                "Durum": "Onaylandı",
            }
        ]
        assert svc.has_izin_cakisma("111", "2026-03-14", "2026-03-20") is True

    def test_ayni_personel_tarih_kesismezse_false(self, svc, reg):
        reg.get("Izin_Giris").get_all.return_value = [
            {
                "Izinid": "A1",
                "Personelid": "111",
                "BaslamaTarihi": "2026-03-10",
                "BitisTarihi": "2026-03-15",
                "Durum": "Onaylandı",
            }
        ]
        assert svc.has_izin_cakisma("111", "2026-03-16", "2026-03-18") is False

    def test_farkli_personel_ise_false(self, svc, reg):
        reg.get("Izin_Giris").get_all.return_value = [
            {
                "Izinid": "A1",
                "Personelid": "222",
                "BaslamaTarihi": "2026-03-10",
                "BitisTarihi": "2026-03-15",
                "Durum": "Onaylandı",
            }
        ]
        assert svc.has_izin_cakisma("111", "2026-03-12", "2026-03-13") is False

    def test_iptal_durumlu_kayitlar_dikkate_alinmaz(self, svc, reg):
        reg.get("Izin_Giris").get_all.return_value = [
            {
                "Izinid": "A1",
                "Personelid": "111",
                "BaslamaTarihi": "2026-03-10",
                "BitisTarihi": "2026-03-15",
                "Durum": "İptal",
            }
        ]
        assert svc.has_izin_cakisma("111", "2026-03-12", "2026-03-13") is False

    def test_sinir_tarihte_dokunma_cakisma_sayilir(self, svc, reg):
        reg.get("Izin_Giris").get_all.return_value = [
            {
                "Izinid": "A1",
                "Personelid": "111",
                "BaslamaTarihi": "2026-03-10",
                "BitisTarihi": "2026-03-15",
                "Durum": "Onaylandı",
            }
        ]
        # Yeni başlangıç eski bitiş ile aynı gün -> çakışma
        assert svc.has_izin_cakisma("111", "2026-03-15", "2026-03-18") is True

    def test_bitis_bos_ise_baslama_ile_ayni_kabul_edilir(self, svc, reg):
        reg.get("Izin_Giris").get_all.return_value = [
            {
                "Izinid": "A1",
                "Personelid": "111",
                "BaslamaTarihi": "2026-03-10",
                "BitisTarihi": "",
                "Durum": "Onaylandı",
            }
        ]
        assert svc.has_izin_cakisma("111", "2026-03-10", "2026-03-10") is True

    def test_ignore_izin_id_guncellemede_kendisini_hariç_tutar(self, svc, reg):
        reg.get("Izin_Giris").get_all.return_value = [
            {
                "Izinid": "A1",
                "Personelid": "111",
                "BaslamaTarihi": "2026-03-10",
                "BitisTarihi": "2026-03-15",
                "Durum": "Onaylandı",
            }
        ]
        assert svc.has_izin_cakisma("111", "2026-03-12", "2026-03-14", ignore_izin_id="A1") is False

    def test_gecersiz_yeni_tarih_false(self, svc, reg):
        reg.get("Izin_Giris").get_all.return_value = []
        assert svc.has_izin_cakisma("111", "gecersiz", "2026-03-14") is False

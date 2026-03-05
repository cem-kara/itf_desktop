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
            IzinService(None)

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

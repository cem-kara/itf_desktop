"""
PersonelService Test Suite

Kapsam:
- Başlatma doğrulaması
- validate_tc: geçerli/geçersiz TC numaraları (KRİTİK iş kuralı)
- get_personel_listesi: tümü ve aktif filtresi
- get_personel
- get_bolumler
- ekle: TC doğrulama ile birlikte
- guncelle / sil

Not: Public servis metodları SonucYonetici döndürür; testler veri alanını doğrular.
"""
import pytest
from unittest.mock import MagicMock
from core.services.personel_service import PersonelService



# ─────────────────────────────────────────────────────────────
#  Fixture'lar
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def reg():
    return MagicMock()


@pytest.fixture
def svc(reg):
    return PersonelService(reg)


# ─────────────────────────────────────────────────────────────
#  Başlatma
# ─────────────────────────────────────────────────────────────

class TestInit:
    def test_none_registry_hata_firlatar(self):
        with pytest.raises(ValueError):
            PersonelService(None)

    def test_registry_saklanir(self, reg):
        s = PersonelService(reg)
        assert s._r is reg


# ─────────────────────────────────────────────────────────────
#  validate_tc — KRİTİK İŞ KURALI
#
#  TC Kimlik No algoritması:
#  - 11 haneli sayı
#  - İlk hane 0 olamaz
#  - Checksum: pozisyon * ağırlık toplamından hesaplanır
#
#  Test TC numaraları core.validators içindeki mevcut algoritmaya göredir.
# ─────────────────────────────────────────────────────────────

class TestValidateTc:

    # ── Geçerli TC numaraları ────────────────────────────────

    def test_gecerli_tc_1(self, svc):
        assert svc.validate_tc("10000000146").veri is True

    def test_gecerli_tc_2(self, svc):
        assert svc.validate_tc("11111111110").veri is True

    def test_gecerli_tc_3(self, svc):
        assert svc.validate_tc("24681357994").veri is True

    def test_gecerli_tc_4(self, svc):
        assert svc.validate_tc("31415926562").veri is True

    # ── Format hataları ──────────────────────────────────────

    def test_10_haneli_gecersiz(self, svc):
        assert svc.validate_tc("1234567890").veri is False

    def test_12_haneli_gecersiz(self, svc):
        assert svc.validate_tc("123456789056").veri is False

    def test_bos_string_gecersiz(self, svc):
        assert svc.validate_tc("").veri is False

    def test_harf_iceren_gecersiz(self, svc):
        assert svc.validate_tc("1234567890a").veri is False

    def test_bosluklu_gecersiz(self, svc):
        assert svc.validate_tc("1234 567890").veri is False

    def test_none_gecersiz(self, svc):
        """None → hata fırlatmamalı, False dönmeli."""
        assert svc.validate_tc(None).veri is False

    # ── İş kuralı hataları ──────────────────────────────────

    def test_sifirla_baslayan_gecersiz(self, svc):
        """TC ilk hanesi 0 olamaz."""
        assert svc.validate_tc("02345678905").veri is False

    def test_yanlis_checksum_gecersiz(self, svc):
        """Checksum yanlış → geçersiz."""
        assert svc.validate_tc("12345678900").veri is False

    def test_tum_sifir_gecersiz(self, svc):
        assert svc.validate_tc("00000000000").veri is False

    # ── Tip toleransı ───────────────────────────────────────

    def test_bosluklu_input_strip_yapilmali(self, svc):
        """Baştaki/sondaki boşluklar trim edilmeli."""
        assert svc.validate_tc("  10000000146  ").veri is True


# ─────────────────────────────────────────────────────────────
#  get_personel_listesi
#
#  Public API SonucYonetici döndürür.
# ─────────────────────────────────────────────────────────────

class TestGetPersonelListesi:
    def _veri(self):
        return [
            {"KimlikNo": "111", "Ad": "Ali",  "Durum": "Aktif"},
            {"KimlikNo": "222", "Ad": "Ayşe", "Durum": "Pasif"},
            {"KimlikNo": "333", "Ad": "Can",  "Durum": "Aktif"},
        ]

    def test_tum_liste(self, svc, reg):
        reg.get("Personel").get_all.return_value = self._veri()
        result = svc.get_personel_listesi()
        assert result.basarili is True
        assert len(result.veri) == 3

    def test_aktif_filtresi(self, svc, reg):
        reg.get("Personel").get_all.return_value = self._veri()
        result = svc.get_personel_listesi(aktif_only=True)
        assert result.basarili is True
        assert len(result.veri) == 2
        assert all(r["Durum"] != "Pasif" for r in result.veri)

    def test_bos_liste(self, svc, reg):
        reg.get("Personel").get_all.return_value = []
        result = svc.get_personel_listesi()
        assert result.basarili is True
        assert result.veri == []

    def test_repo_hatasi_bos_liste(self, svc, reg):
        reg.get("Personel").get_all.side_effect = Exception("Hata")
        result = svc.get_personel_listesi()
        assert result.basarili is False
        assert result.veri is None

    def test_pasif_kucuk_harf(self, svc, reg):
        """Durum alanı küçük harf 'pasif' olsa da filtre çalışmalı."""
        reg.get("Personel").get_all.return_value = [
            {"KimlikNo": "111", "Durum": "pasif"},
            {"KimlikNo": "222", "Durum": "Aktif"},
        ]
        result = svc.get_personel_listesi(aktif_only=True)
        assert result.basarili is True
        assert len(result.veri) == 1


# ─────────────────────────────────────────────────────────────
#  get_personel
# ─────────────────────────────────────────────────────────────

class TestGetPersonel:
    def test_var_olan_personel(self, svc, reg):
        reg.get("Personel").get_by_pk.return_value = {"KimlikNo": "111", "Ad": "Ali"}
        result = svc.get_personel("111")
        assert result.basarili is True
        assert result.veri["Ad"] == "Ali"

    def test_olmayan_personel_none(self, svc, reg):
        reg.get("Personel").get_by_pk.return_value = None
        result = svc.get_personel("999")
        assert result.basarili is True
        assert result.veri is None

    def test_repo_hatasi_none(self, svc, reg):
        reg.get("Personel").get_by_pk.side_effect = Exception("Hata")
        result = svc.get_personel("111")
        assert result.basarili is False
        assert result.veri is None


# ─────────────────────────────────────────────────────────────
#  ekle — TC doğrulaması dahil
# ─────────────────────────────────────────────────────────────

class TestEkle:
    def test_gecerli_tc_ile_ekleme(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        veri = {"TC": "10000000146", "Ad": "Ali"}
        result = svc.ekle(veri)
        assert result.basarili is True
        mock_repo.insert.assert_called_once_with(veri)

    def test_gecersiz_tc_ile_ekleme_reddedilir(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        veri = {"TC": "12345678900", "Ad": "Ali"}  # Yanlış checksum
        result = svc.ekle(veri)
        assert result.basarili is False
        mock_repo.insert.assert_not_called()

    def test_tc_olmadan_ekleme_reddedilir(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        veri = {"Ad": "Ali"}  # TC yok
        result = svc.ekle(veri)
        assert result.basarili is False
        mock_repo.insert.assert_not_called()

    def test_db_hatasi_false(self, svc, reg):
        mock_repo = MagicMock()
        mock_repo.insert.side_effect = Exception("Hata")
        reg.get.return_value = mock_repo
        veri = {"TC": "10000000146", "Ad": "Ali"}
        result = svc.ekle(veri)
        assert result.basarili is False


# ─────────────────────────────────────────────────────────────
#  guncelle
# ─────────────────────────────────────────────────────────────

class TestGuncelle:
    def test_guncelle_basarili(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        result = svc.guncelle("111", {"Ad": "Ali Yeni"})
        assert result.basarili is True
        mock_repo.update.assert_called_once_with("111", {"Ad": "Ali Yeni"})

    def test_db_hatasi_false(self, svc, reg):
        mock_repo = MagicMock()
        mock_repo.update.side_effect = Exception("Hata")
        reg.get.return_value = mock_repo
        result = svc.guncelle("111", {"Ad": "Ali"})
        assert result.basarili is False


# ─────────────────────────────────────────────────────────────
#  sil
# ─────────────────────────────────────────────────────────────

class TestSil:
    def test_sil_basarili(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        result = svc.sil("111")
        assert result.basarili is True
        mock_repo.delete.assert_called_once_with("111")

    def test_sil_hatasi(self, svc, reg):
        mock_repo = MagicMock()
        mock_repo.delete.side_effect = Exception("Hata")
        reg.get.return_value = mock_repo
        result = svc.sil("111")
        assert result.basarili is False

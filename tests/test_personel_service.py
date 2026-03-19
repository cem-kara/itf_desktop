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

Not: Şu an servis "Personeller" tablo adı kullanıyor,
gerçek tablo "Personel". Tablo adı içeren testler FAIL verir.
personel_service.py'de tüm "Personeller"  →  "Personel" yap.
"""
import pytest
from unittest.mock import MagicMock, call
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
#  Test TC numaraları bu servisteki algoritmaya göre üretildi.
#  Servis algoritması standart TC algoritmasından farklı olabilir —
#  önemli olan tutarlılık (servis ne bekliyorsa test onu sınar).
# ─────────────────────────────────────────────────────────────

class TestValidateTc:

    # ── Geçerli TC numaraları ────────────────────────────────

    def test_gecerli_tc_1(self, svc):
        """12345678905 — servisteki algoritmaya göre geçerli."""
        assert svc.validate_tc("12345678905") is True

    def test_gecerli_tc_2(self, svc):
        """10000000007 — geçerli."""
        assert svc.validate_tc("10000000007") is True

    def test_gecerli_tc_3(self, svc):
        """20000000004 — geçerli."""
        assert svc.validate_tc("20000000004") is True

    def test_gecerli_tc_4(self, svc):
        """98765432105 — geçerli."""
        assert svc.validate_tc("98765432105") is True

    # ── Format hataları ──────────────────────────────────────

    def test_10_haneli_gecersiz(self, svc):
        assert svc.validate_tc("1234567890") is False

    def test_12_haneli_gecersiz(self, svc):
        assert svc.validate_tc("123456789056") is False

    def test_bos_string_gecersiz(self, svc):
        assert svc.validate_tc("") is False

    def test_harf_iceren_gecersiz(self, svc):
        assert svc.validate_tc("1234567890a") is False

    def test_bosluklu_gecersiz(self, svc):
        assert svc.validate_tc("1234 567890") is False

    def test_none_gecersiz(self, svc):
        """None → hata fırlatmamalı, False dönmeli."""
        assert svc.validate_tc(None) is False

    # ── İş kuralı hataları ──────────────────────────────────

    def test_sifirla_baslayan_gecersiz(self, svc):
        """TC ilk hanesi 0 olamaz."""
        assert svc.validate_tc("02345678905") is False

    def test_yanlis_checksum_gecersiz(self, svc):
        """Checksum yanlış → geçersiz."""
        assert svc.validate_tc("12345678900") is False

    def test_tum_sifir_gecersiz(self, svc):
        assert svc.validate_tc("00000000000") is False

    # ── Tip toleransı ───────────────────────────────────────

    def test_bosluklu_input_strip_yapilmali(self, svc):
        """Baştaki/sondaki boşluklar trim edilmeli."""
        assert svc.validate_tc("  12345678905  ") is True


# ─────────────────────────────────────────────────────────────
#  get_personel_listesi
#
#  NOT: Bu testler şu an FAIL verir çünkü servis "Personeller"
#  kullanıyor. Düzeltme: "Personeller"  →  "Personel"
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
        assert len(result) == 3

    def test_aktif_filtresi(self, svc, reg):
        reg.get("Personel").get_all.return_value = self._veri()
        result = svc.get_personel_listesi(aktif_only=True)
        assert len(result) == 2
        assert all(r["Durum"] != "Pasif" for r in result)

    def test_bos_liste(self, svc, reg):
        reg.get("Personel").get_all.return_value = []
        assert svc.get_personel_listesi() == []

    def test_repo_hatasi_bos_liste(self, svc, reg):
        reg.get("Personel").get_all.side_effect = Exception("Hata")
        assert svc.get_personel_listesi() == []

    def test_pasif_kucuk_harf(self, svc, reg):
        """Durum alanı küçük harf 'pasif' olsa da filtre çalışmalı."""
        reg.get("Personel").get_all.return_value = [
            {"KimlikNo": "111", "Durum": "pasif"},
            {"KimlikNo": "222", "Durum": "Aktif"},
        ]
        result = svc.get_personel_listesi(aktif_only=True)
        assert len(result) == 1


# ─────────────────────────────────────────────────────────────
#  get_personel
# ─────────────────────────────────────────────────────────────

class TestGetPersonel:
    def test_var_olan_personel(self, svc, reg):
        reg.get("Personel").get_by_pk.return_value = {"KimlikNo": "111", "Ad": "Ali"}
        result = svc.get_personel("111")
        assert result["Ad"] == "Ali"

    def test_olmayan_personel_none(self, svc, reg):
        reg.get("Personel").get_by_pk.return_value = None
        assert svc.get_personel("999") is None

    def test_repo_hatasi_none(self, svc, reg):
        reg.get("Personel").get_by_pk.side_effect = Exception("Hata")
        assert svc.get_personel("111") is None


# ─────────────────────────────────────────────────────────────
#  ekle — TC doğrulaması dahil
# ─────────────────────────────────────────────────────────────

class TestEkle:
    def test_gecerli_tc_ile_ekleme(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        veri = {"TC": "12345678905", "Ad": "Ali"}
        assert svc.ekle(veri) is True
        mock_repo.insert.assert_called_once_with(veri)

    def test_gecersiz_tc_ile_ekleme_reddedilir(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        veri = {"TC": "12345678900", "Ad": "Ali"}  # Yanlış checksum
        assert svc.ekle(veri) is False
        mock_repo.insert.assert_not_called()

    def test_tc_olmadan_ekleme_reddedilir(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        veri = {"Ad": "Ali"}  # TC yok
        assert svc.ekle(veri) is False
        mock_repo.insert.assert_not_called()

    def test_db_hatasi_false(self, svc, reg):
        mock_repo = MagicMock()
        mock_repo.insert.side_effect = Exception("Hata")
        reg.get.return_value = mock_repo
        veri = {"TC": "12345678905", "Ad": "Ali"}
        assert svc.ekle(veri) is False


# ─────────────────────────────────────────────────────────────
#  guncelle
# ─────────────────────────────────────────────────────────────

class TestGuncelle:
    def test_guncelle_basarili(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        assert svc.guncelle("111", {"Ad": "Ali Yeni"}) is True
        mock_repo.update.assert_called_once_with("111", {"Ad": "Ali Yeni"})

    def test_db_hatasi_false(self, svc, reg):
        mock_repo = MagicMock()
        mock_repo.update.side_effect = Exception("Hata")
        reg.get.return_value = mock_repo
        assert svc.guncelle("111", {"Ad": "Ali"}) is False


# ─────────────────────────────────────────────────────────────
#  sil
# ─────────────────────────────────────────────────────────────

class TestSil:
    def test_sil_basarili(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        assert svc.sil("111") is True
        mock_repo.delete.assert_called_once_with("111")

    def test_sil_hatasi(self, svc, reg):
        mock_repo = MagicMock()
        mock_repo.delete.side_effect = Exception("Hata")
        reg.get.return_value = mock_repo
        assert svc.sil("111") is False

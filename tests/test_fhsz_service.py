"""
FhszService Test Suite

Kapsam:
- Başlatma
- get_sabitler_listesi: sabitler filtreleme
- get_puantaj_listesi: puantaj filtreleme (yıl/dönem/personel)
- get_donem_puantaj_listesi: belirtilen dönem puantajı
- sua_bakiye_guncelle: SUA bakiyesi güncelleme

Not: Tüm metodlar SonucYonetici döndürür.
"""
import pytest
from unittest.mock import MagicMock
from core.services.fhsz_service import FhszService


# ─────────────────────────────────────────────────────────────
#  Fixture'lar
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def reg():
    return MagicMock()


@pytest.fixture
def svc(reg):
    return FhszService(reg)


# ─────────────────────────────────────────────────────────────
#  Başlatma
# ─────────────────────────────────────────────────────────────

class TestFhszServiceInit:
    def test_none_registry_hata_firlatar(self):
        with pytest.raises(ValueError):
            FhszService(None)

    def test_registry_saklanir(self, reg):
        s = FhszService(reg)
        assert s._r is reg


# ─────────────────────────────────────────────────────────────
#  get_sabitler_listesi
# ─────────────────────────────────────────────────────────────

class TestGetSabitlerListesi:
    def test_tum_sabitler(self, svc, reg):
        """Tüm sabitler döner."""
        reg.get("Sabitler").get_all.return_value = [
            {"Kod": "Birim", "MenuEleman": "Radyoloji"},
            {"Kod": "Birim", "MenuEleman": "Ultrason"},
            {"Kod": "CalismaSartiI", "MenuEleman": "Gündüz"},
        ]
        result = svc.get_sabitler_listesi()
        assert result.basarili is True
        assert len(result.veri) == 3

    def test_kod_filtresi(self, svc, reg):
        """Belirtilen kod ile filtrelenir."""
        reg.get("Sabitler").get_all.return_value = [
            {"Kod": "Birim", "MenuEleman": "Radyoloji"},
            {"Kod": "Birim", "MenuEleman": "Ultrason"},
            {"Kod": "CalismaSartiI", "MenuEleman": "Gündüz"},
        ]
        result = svc.get_sabitler_listesi(kod="Birim")
        assert result.basarili is True
        assert len(result.veri) == 2
        assert all(r["Kod"] == "Birim" for r in result.veri)

    def test_bos_liste(self, svc, reg):
        """Eşleşme yoksa boş liste döner."""
        reg.get("Sabitler").get_all.return_value = []
        result = svc.get_sabitler_listesi()
        assert result.basarili is True
        assert result.veri == []

    def test_repo_hatasi(self, svc, reg):
        """Repository hatası durumunda hata döndürür."""
        reg.get("Sabitler").get_all.side_effect = Exception("Hata")
        result = svc.get_sabitler_listesi()
        assert result.basarili is False


# ─────────────────────────────────────────────────────────────
#  get_puantaj_listesi
# ─────────────────────────────────────────────────────────────

class TestGetPuantajListesi:
    def _veri(self):
        return [
            {"Personelid": "111", "AitYil": "2026", "Donem": "1", "FiiliCalismaSaat": 160},
            {"Personelid": "222", "AitYil": "2026", "Donem": "1", "FiiliCalismaSaat": 150},
            {"Personelid": "111", "AitYil": "2026", "Donem": "2", "FiiliCalismaSaat": 165},
        ]

    def test_tum_puantaj(self, svc, reg):
        """Tüm puantajları döner."""
        reg.get("FHSZ_Puantaj").get_all.return_value = self._veri()
        result = svc.get_puantaj_listesi()
        assert result.basarili is True
        assert len(result.veri) == 3

    def test_yil_filtresi(self, svc, reg):
        """Yıl filtresiyle döner."""
        reg.get("FHSZ_Puantaj").get_all.return_value = self._veri()
        result = svc.get_puantaj_listesi(yil=2026)
        assert result.basarili is True
        assert len(result.veri) == 3
        assert all(r["AitYil"] == "2026" for r in result.veri)

    def test_donem_filtresi(self, svc, reg):
        """Dönem filtresiyle döner."""
        reg.get("FHSZ_Puantaj").get_all.return_value = self._veri()
        result = svc.get_puantaj_listesi(donem="1")
        assert result.basarili is True
        assert len(result.veri) == 2
        assert all(r["Donem"] == "1" for r in result.veri)

    def test_personel_filtresi(self, svc, reg):
        """Personel filtresiyle döner."""
        reg.get("FHSZ_Puantaj").get_all.return_value = self._veri()
        result = svc.get_puantaj_listesi(personel_id="111")
        assert result.basarili is True
        assert len(result.veri) == 2
        assert all(r["Personelid"] == "111" for r in result.veri)

    def test_kombineli_filtre(self, svc, reg):
        """Yıl + dönem + personel filtresi."""
        reg.get("FHSZ_Puantaj").get_all.return_value = self._veri()
        result = svc.get_puantaj_listesi(yil=2026, donem="1", personel_id="111")
        assert result.basarili is True
        assert len(result.veri) == 1

    def test_bos_liste(self, svc, reg):
        """Eşleşme yoksa boş liste."""
        reg.get("FHSZ_Puantaj").get_all.return_value = []
        result = svc.get_puantaj_listesi()
        assert result.basarili is True
        assert result.veri == []

    def test_repo_hatasi(self, svc, reg):
        """Repository hatası."""
        reg.get("FHSZ_Puantaj").get_all.side_effect = Exception("Hata")
        result = svc.get_puantaj_listesi()
        assert result.basarili is False


# ─────────────────────────────────────────────────────────────
#  get_donem_puantaj_listesi
# ─────────────────────────────────────────────────────────────

class TestGetDonemPuantajListesi:
    def test_donem_puantaj(self, svc, reg):
        """Belirtilen dönem puantajını döner."""
        reg.get("FHSZ_Puantaj").get_all.return_value = [
            {"Personelid": "111", "AitYil": "2026", "Donem": "1", "FiiliCalismaSaat": 160},
            {"Personelid": "222", "AitYil": "2026", "Donem": "1", "FiiliCalismaSaat": 150},
        ]
        result = svc.get_donem_puantaj_listesi("2026", "1")
        assert result.basarili is True
        assert len(result.veri) == 2

    def test_yil_int_string_uyumlu(self, svc, reg):
        """Yıl int veya string olabilir."""
        reg.get("FHSZ_Puantaj").get_all.return_value = [
            {"Personelid": "111", "AitYil": "2026", "Donem": "1"},
        ]
        result1 = svc.get_donem_puantaj_listesi(2026, "1")
        result2 = svc.get_donem_puantaj_listesi("2026", 1)
        assert result1.basarili is True
        assert result2.basarili is True


# ─────────────────────────────────────────────────────────────
#  sua_bakiye_guncelle
# ─────────────────────────────────────────────────────────────

class TestSuaBakiyeGuncelle:
    def test_sua_bakiye_guncelle_basarili(self, svc, reg):
        """SUA bakiyesi güncellenir."""
        puantaj_repo = MagicMock()
        izin_repo = MagicMock()
        
        reg.get.side_effect = lambda tbl: {
            "FHSZ_Puantaj": puantaj_repo,
            "Izin_Bilgi": izin_repo,
        }.get(tbl)
        
        puantaj_repo.get_all.return_value = [
            {"Personelid": "111", "AitYil": "2026", "FiiliCalismaSaat": "160"},
        ]
        izin_repo.get_by_id.return_value = None
        
        result = svc.sua_bakiye_guncelle("2026")
        assert result.basarili is True

    def test_sua_bakiye_guncelle_hata(self, svc, reg):
        """Hata durumunda SonucYonetici.hata döner."""
        reg.get.side_effect = Exception("DB Hatası")
        result = svc.sua_bakiye_guncelle("2026")
        assert result.basarili is False

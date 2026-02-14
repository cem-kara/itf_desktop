# -*- coding: utf-8 -*-
"""
test_hata_yonetimi.py  (v3)
═════════════════════════════════════
Kapsam:
  1. BaseRepository.get_by_kod
  2. BaseRepository.get_where
  3. core.hata_yonetici — mock.patch ile logger doğrudan test edilir
     (caplog ITF_APP logger'ı yakalayamıyor çünkü handler root'ta)
  4. KalibrasyonKaydedici — __init__ parametre sırası
  5. ariza_islem — __file__ tabanlı import kontrolü
"""
import sys
import os
import logging
import pytest
from unittest.mock import patch, MagicMock

_PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


# ── Qt fixture ───────────────────────────────────────────────
@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication(sys.argv)


# ── Sahte DB ─────────────────────────────────────────────────
class FakeRow(dict):
    def keys(self): return super().keys()

class FakeCursor:
    def __init__(self, rows): self._rows = rows
    def fetchall(self): return [FakeRow(r) for r in self._rows]
    def fetchone(self): return FakeRow(self._rows[0]) if self._rows else None

class FakeDB:
    def __init__(self, rows=None, raise_on=None):
        self._rows = rows or []
        self._raise_on = raise_on
    def execute(self, sql, params=None):
        if self._raise_on and self._raise_on in sql:
            raise Exception(f"Simulated DB error: {self._raise_on}")
        return FakeCursor(self._rows)
    def close(self): pass

SABITLER_ROWS = [
    {"Rowid": 1, "Kod": "Ariza_Islem_Turu", "MenuEleman": "Bakım",   "Aciklama": ""},
    {"Rowid": 2, "Kod": "Ariza_Islem_Turu", "MenuEleman": "Onarım",  "Aciklama": ""},
    {"Rowid": 3, "Kod": "Ariza_Durum",       "MenuEleman": "Açık",   "Aciklama": ""},
    {"Rowid": 4, "Kod": "Ariza_Durum",       "MenuEleman": "Kapalı", "Aciklama": ""},
    {"Rowid": 5, "Kod": "firmalar",           "MenuEleman": "ACME",   "Aciklama": ""},
]
PERSONEL_ROWS = [
    {"KimlikNo": "11111", "AdSoyad": "Ali Veli", "Durum": "aktif"},
    {"KimlikNo": "22222", "AdSoyad": "Can Can",  "Durum": "pasif"},
]

def make_repo(rows, pk="Rowid"):
    from database.base_repository import BaseRepository
    return BaseRepository(
        db=FakeDB(rows), table_name="Sabitler", pk=pk,
        columns=["Rowid", "Kod", "MenuEleman", "Aciklama"], has_sync=False,
    )

def _cagri_icerisinde(mock_method, metin: str) -> bool:
    """Mock metod çağrı listesinde metin arar."""
    return any(metin in str(c) for c in mock_method.call_args_list)


# =============================================================
#  1. get_by_kod
# =============================================================
class TestGetByKod:

    def test_sonuc_listesi_donuyor(self):
        assert isinstance(make_repo(SABITLER_ROWS).get_by_kod("Ariza_Islem_Turu"), list)

    def test_her_eleman_dict(self):
        for item in make_repo(SABITLER_ROWS).get_by_kod("Ariza_Islem_Turu"):
            assert isinstance(item, dict)

    def test_MenuEleman_anahtari_var(self):
        for item in make_repo(SABITLER_ROWS).get_by_kod("Ariza_Islem_Turu"):
            assert "MenuEleman" in item

    def test_db_hatasinda_bos_liste(self):
        from database.base_repository import BaseRepository
        db = FakeDB(raise_on="WHERE Kod")
        repo = BaseRepository(db=db, table_name="Sabitler",
                              pk="Rowid", columns=["Rowid","Kod","MenuEleman","Aciklama"],
                              has_sync=False)
        assert repo.get_by_kod("herhangi") == []

    def test_ozel_kolum_parametresi(self):
        assert isinstance(
            make_repo(PERSONEL_ROWS, pk="KimlikNo").get_by_kod("aktif", kolum="Durum"),
            list
        )

    def test_bos_string_kod(self):
        assert isinstance(make_repo(SABITLER_ROWS).get_by_kod(""), list)

    def test_satir_sayisi(self):
        r = make_repo(SABITLER_ROWS).get_by_kod("Ariza_Islem_Turu")
        assert len(r) == len(SABITLER_ROWS)


# =============================================================
#  2. get_where
# =============================================================
class TestGetWhere:

    def test_bos_kosul_get_all_gibi(self):
        repo = make_repo(SABITLER_ROWS)
        assert len(repo.get_where({})) == len(repo.get_all())

    def test_tek_kosul(self):
        assert isinstance(make_repo(SABITLER_ROWS).get_where({"Kod": "Ariza_Islem_Turu"}), list)

    def test_coklu_kosul(self):
        r = make_repo(SABITLER_ROWS).get_where({"Kod": "Ariza_Islem_Turu", "MenuEleman": "Bakım"})
        assert isinstance(r, list)

    def test_db_hatasi_bos_liste(self):
        from database.base_repository import BaseRepository
        repo = BaseRepository(db=FakeDB(raise_on="WHERE Kod"),
                              table_name="Sabitler", pk="Rowid",
                              columns=["Rowid","Kod","MenuEleman","Aciklama"],
                              has_sync=False)
        assert repo.get_where({"Kod": "test"}) == []


# =============================================================
#  3. core.hata_yonetici — mock.patch ile test
#     caplog yerine mock kullanıyoruz:
#     ITF_APP logger'ın handler'ı root'ta olduğundan caplog
#     logger="ITF_APP" ile güvenilir şekilde yakalayamıyor.
# =============================================================
class TestHataYonetici:

    def test_exc_logla_error_cagrilir(self):
        from core.hata_yonetici import exc_logla
        with patch('core.hata_yonetici.logger') as m:
            exc_logla("TestModul.func", ValueError("test hatası"))
            assert m.error.called

    def test_exc_logla_konum_loglanir(self):
        from core.hata_yonetici import exc_logla
        with patch('core.hata_yonetici.logger') as m:
            exc_logla("TestModul.func", ValueError("test hatası"))
            assert _cagri_icerisinde(m.error, "TestModul")

    def test_exc_logla_mesaj_loglanir(self):
        from core.hata_yonetici import exc_logla
        with patch('core.hata_yonetici.logger') as m:
            exc_logla("TestModul.func", ValueError("test hatası"))
            assert _cagri_icerisinde(m.error, "test hatası")

    def test_exc_logla_hata_tipi_loglanir(self):
        from core.hata_yonetici import exc_logla
        with patch('core.hata_yonetici.logger') as m:
            exc_logla("Test", TypeError("tip hatası"))
            assert _cagri_icerisinde(m.error, "TypeError")

    def test_exc_logla_istisna_firlatmaz(self):
        from core.hata_yonetici import exc_logla
        try:
            exc_logla("Test.konum", RuntimeError("hata"))
        except Exception as e:
            pytest.fail(f"exc_logla exception fırlattı: {e}")

    def test_hata_goster_logger_error_cagrilir(self):
        from core.hata_yonetici import hata_goster
        with patch('core.hata_yonetici.logger') as m:
            hata_goster(None, "Bir şeyler yanlış gitti")
            assert m.error.called

    def test_hata_goster_mesaj_loglanir(self):
        from core.hata_yonetici import hata_goster
        with patch('core.hata_yonetici.logger') as m:
            hata_goster(None, "Bir şeyler yanlış gitti")
            assert _cagri_icerisinde(m.error, "Bir şeyler yanlış gitti")

    def test_hata_goster_baslik_loglanir(self):
        from core.hata_yonetici import hata_goster
        with patch('core.hata_yonetici.logger') as m:
            hata_goster(None, "mesaj", baslik="Test Başlığı")
            assert _cagri_icerisinde(m.error, "Test Başlığı")

    def test_uyari_goster_logger_warning_cagrilir(self):
        from core.hata_yonetici import uyari_goster
        with patch('core.hata_yonetici.logger') as m:
            uyari_goster(None, "Eksik alan")
            assert m.warning.called

    def test_uyari_goster_mesaj_loglanir(self):
        from core.hata_yonetici import uyari_goster
        with patch('core.hata_yonetici.logger') as m:
            uyari_goster(None, "Eksik alan")
            assert _cagri_icerisinde(m.warning, "Eksik alan")

    def test_uyari_goster_error_cagrilmaz(self):
        from core.hata_yonetici import uyari_goster
        with patch('core.hata_yonetici.logger') as m:
            uyari_goster(None, "sadece uyarı")
            assert not m.error.called

    def test_hata_logla_goster_loglara_yazar(self):
        from core.hata_yonetici import hata_logla_goster
        with patch('core.hata_yonetici.logger') as m:
            hata_logla_goster(None, "Test.func", RuntimeError("çalışma zamanı"))
            assert m.error.called
            assert (
                _cagri_icerisinde(m.error, "RuntimeError") or
                _cagri_icerisinde(m.error, "çalışma zamanı")
            )


# =============================================================
#  4. KalibrasyonKaydedici — Parametre Sırası
# =============================================================
class TestKalibrasyonKaydediciInit:

    def test_varsayilan_mod_yeni(self, qapp):
        from ui.pages.cihaz.kalibrasyon_takip import KalibrasyonKaydedici
        w = KalibrasyonKaydedici([])
        assert w._mod == "yeni"
        assert w._kayit_id is None

    def test_mod_guncelle_keyword(self, qapp):
        from ui.pages.cihaz.kalibrasyon_takip import KalibrasyonKaydedici
        w = KalibrasyonKaydedici({}, mod="guncelle", kayit_id="KAL-1")
        assert w._mod == "guncelle"
        assert w._kayit_id == "KAL-1"

    def test_mod_yeni_explicit(self, qapp):
        from ui.pages.cihaz.kalibrasyon_takip import KalibrasyonKaydedici
        assert KalibrasyonKaydedici([{"a": 1}], mod="yeni")._mod == "yeni"

    def test_veri_saklaniyor(self, qapp):
        from ui.pages.cihaz.kalibrasyon_takip import KalibrasyonKaydedici
        veri = [{"Kalibrasyonid": "KAL-1"}]
        assert KalibrasyonKaydedici(veri, mod="yeni")._veri == veri

    def test_parent_none_gecilince_calisir(self, qapp):
        from ui.pages.cihaz.kalibrasyon_takip import KalibrasyonKaydedici
        assert KalibrasyonKaydedici({}, mod="guncelle", kayit_id="X", parent=None) is not None

    def test_coklu_deger_hatasi_yok(self, qapp):
        """Regresyon: 'got multiple values for argument mod' hatası dönemez."""
        from ui.pages.cihaz.kalibrasyon_takip import KalibrasyonKaydedici
        try:
            KalibrasyonKaydedici({}, mod="guncelle", kayit_id="K1", parent=None)
        except TypeError as e:
            pytest.fail(f"KalibrasyonKaydedici init hatası (regresyon): {e}")

    def test_liste_veri_kabul(self, qapp):
        from ui.pages.cihaz.kalibrasyon_takip import KalibrasyonKaydedici
        assert len(KalibrasyonKaydedici([{"a": 1}, {"b": 2}], mod="yeni")._veri) == 2

    def test_dict_veri_kabul(self, qapp):
        from ui.pages.cihaz.kalibrasyon_takip import KalibrasyonKaydedici
        veri = {"Kalibrasyonid": "K-1", "Firma": "Test"}
        assert KalibrasyonKaydedici(veri, mod="guncelle", kayit_id="K-1")._veri == veri


# =============================================================
#  5. ariza_islem — import kontrolü
# =============================================================
class TestArizaIslemImport:

    @pytest.fixture
    def ariza_islem_icerik(self):
        yol = os.path.join(_PROJECT_ROOT, "ui", "pages", "cihaz", "ariza_islem.py")
        if not os.path.exists(yol):
            pytest.skip(f"ariza_islem.py bulunamadı: {yol}")
        return open(yol, encoding="utf-8").read()

    def test_exc_logla_import_mevcut(self, ariza_islem_icerik):
        assert "from core.hata_yonetici import exc_logla" in ariza_islem_icerik

    def test_local_logger_kaldirildi(self, ariza_islem_icerik):
        assert 'logging.getLogger("ArizaIslem")' not in ariza_islem_icerik

    def test_core_logger_mevcut(self, ariza_islem_icerik):
        assert "from core.logger import logger" in ariza_islem_icerik

    def test_exc_logla_en_az_2_kez_kullaniliyor(self, ariza_islem_icerik):
        sayi = ariza_islem_icerik.count("exc_logla(")
        assert sayi >= 2, f"exc_logla kullanım sayısı: {sayi}"

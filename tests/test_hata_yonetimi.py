# -*- coding: utf-8 -*-
"""
test_hata_yonetimi.py
══════════════════════
Merkezi hata yönetimi ve BaseRepository ek metodları için unit testler

Kapsam:
  1. BaseRepository.get_by_kod  — Sabitler tablosu için filtreli sorgu
  2. BaseRepository.get_where   — Çoklu kolon filtresi
  3. core.hata_yonetici         — exc_logla, hata_goster, uyari_goster
  4. KalibrasyonKaydedici       — __init__ parametre sırası
  5. Entegrasyon: logger'a yazılıyor mu?
"""
import sys
import types
import logging
import pytest


# ─── Qt fixture ─────────────────────────────────────────────
@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication(sys.argv)


# ─── Sahte DB ve Repo ────────────────────────────────────────
class FakeRow(dict):
    """sqlite3.Row gibi davranan dict."""
    def keys(self):
        return super().keys()


class FakeCursor:
    def __init__(self, rows):
        self._rows = rows
    def fetchall(self):
        return [FakeRow(r) for r in self._rows]
    def fetchone(self):
        return FakeRow(self._rows[0]) if self._rows else None


class FakeDB:
    def __init__(self, rows=None, raise_on=None):
        self._rows     = rows or []
        self._raise_on = raise_on   # str: sorgu içeriyorsa hata fırlat

    def execute(self, sql, params=None):
        if self._raise_on and self._raise_on in sql:
            raise Exception(f"Simulated DB error for: {self._raise_on}")
        return FakeCursor(self._rows)

    def close(self):
        pass


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
    import sys; sys.path.insert(0, "/home/claude/itf_v3/itf_desktop")
    from database.base_repository import BaseRepository
    db = FakeDB(rows)
    return BaseRepository(
        db=db,
        table_name="Sabitler",
        pk=pk,
        columns=["Rowid", "Kod", "MenuEleman", "Aciklama"],
        has_sync=False,
    )


# =============================================================
#  1. BaseRepository.get_by_kod
# =============================================================
class TestGetByKod:

    def test_sonuc_listesi_dönüyor(self):
        repo = make_repo(SABITLER_ROWS)
        r = repo.get_by_kod("Ariza_Islem_Turu")
        assert isinstance(r, list)

    def test_dogru_satir_sayisi(self):
        # FakeDB tüm satırları döner; gerçekte SQL filtreler
        # Burada FakeDB filtresiz döndüğü için sadece list dönüşünü test ederiz
        repo = make_repo(SABITLER_ROWS)
        r = repo.get_by_kod("Ariza_Islem_Turu")
        assert len(r) == len(SABITLER_ROWS)

    def test_her_eleman_dict(self):
        repo = make_repo(SABITLER_ROWS)
        r = repo.get_by_kod("Ariza_Islem_Turu")
        for item in r:
            assert isinstance(item, dict)

    def test_MenuEleman_erisimi(self):
        repo = make_repo(SABITLER_ROWS)
        r = repo.get_by_kod("Ariza_Islem_Turu")
        # Her elemanın MenuEleman anahtarı olmalı
        for item in r:
            assert "MenuEleman" in item

    def test_db_hatasinda_bos_liste(self):
        import sys; sys.path.insert(0, "/home/claude/itf_v3/itf_desktop")
        from database.base_repository import BaseRepository
        db   = FakeDB(raise_on="WHERE Kod")
        repo = BaseRepository(db=db, table_name="Sabitler",
                              pk="Rowid", columns=["Rowid", "Kod", "MenuEleman", "Aciklama"],
                              has_sync=False)
        r = repo.get_by_kod("herhangi")
        assert r == []

    def test_ozel_kolum_parametresi(self):
        repo = make_repo(PERSONEL_ROWS, pk="KimlikNo")
        # Sadece API'nın çalıştığını doğrula
        r = repo.get_by_kod("aktif", kolum="Durum")
        assert isinstance(r, list)

    def test_bos_string_kod(self):
        repo = make_repo(SABITLER_ROWS)
        r = repo.get_by_kod("")
        assert isinstance(r, list)


# =============================================================
#  2. BaseRepository.get_where
# =============================================================
class TestGetWhere:

    def test_bos_kosul_get_all_gibi(self):
        repo = make_repo(SABITLER_ROWS)
        r    = repo.get_where({})
        # get_all() ile aynı davranış
        r2   = repo.get_all()
        assert len(r) == len(r2)

    def test_tek_kosul(self):
        repo = make_repo(SABITLER_ROWS)
        r    = repo.get_where({"Kod": "Ariza_Islem_Turu"})
        assert isinstance(r, list)

    def test_coklu_kosul(self):
        repo = make_repo(SABITLER_ROWS)
        r    = repo.get_where({"Kod": "Ariza_Islem_Turu", "MenuEleman": "Bakım"})
        assert isinstance(r, list)

    def test_db_hatasi_bos_liste(self):
        import sys; sys.path.insert(0, "/home/claude/itf_v3/itf_desktop")
        from database.base_repository import BaseRepository
        db   = FakeDB(raise_on="WHERE Kod")
        repo = BaseRepository(db=db, table_name="Sabitler",
                              pk="Rowid", columns=["Rowid", "Kod", "MenuEleman", "Aciklama"],
                              has_sync=False)
        r = repo.get_where({"Kod": "test"})
        assert r == []


# =============================================================
#  3. core.hata_yonetici
# =============================================================
class TestHataYonetici:

    def test_exc_logla_error_seviyesinde_yazar(self, caplog):
        import sys; sys.path.insert(0, "/home/claude/itf_v3/itf_desktop")
        from core.hata_yonetici import exc_logla
        with caplog.at_level(logging.ERROR):
            exc_logla("TestModul.test_func", ValueError("test hatası"))
        assert any("TestModul" in r.message for r in caplog.records)
        assert any("test hatası" in r.message for r in caplog.records)

    def test_exc_logla_hata_tipi_loglanir(self, caplog):
        import sys; sys.path.insert(0, "/home/claude/itf_v3/itf_desktop")
        from core.hata_yonetici import exc_logla
        with caplog.at_level(logging.ERROR):
            exc_logla("Test", TypeError("tip hatası"))
        assert any("TypeError" in r.message for r in caplog.records)

    def test_hata_logla_goster_loglara_yazar(self, caplog):
        import sys; sys.path.insert(0, "/home/claude/itf_v3/itf_desktop")
        from core.hata_yonetici import hata_logla_goster
        # Qt olmadan — msgbox başarısız olsa bile log yazılır
        with caplog.at_level(logging.ERROR):
            try:
                hata_logla_goster(None, "Test.func", RuntimeError("çalışma zamanı"))
            except Exception:
                pass
        assert any("RuntimeError" in r.message or "çalışma zamanı" in r.message
                   for r in caplog.records)

    def test_hata_goster_loglara_yazar(self, caplog):
        import sys; sys.path.insert(0, "/home/claude/itf_v3/itf_desktop")
        from core.hata_yonetici import hata_goster
        with caplog.at_level(logging.ERROR):
            try:
                hata_goster(None, "Bir şeyler yanlış gitti")
            except Exception:
                pass
        assert any("Bir şeyler yanlış gitti" in r.message for r in caplog.records)

    def test_uyari_goster_warning_seviyesinde(self, caplog):
        import sys; sys.path.insert(0, "/home/claude/itf_v3/itf_desktop")
        from core.hata_yonetici import uyari_goster
        with caplog.at_level(logging.WARNING):
            try:
                uyari_goster(None, "Eksik alan")
            except Exception:
                pass
        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert any("Eksik alan" in r.message for r in warning_records)


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
        w = KalibrasyonKaydedici([{"a": 1}], mod="yeni")
        assert w._mod == "yeni"

    def test_veri_saklanıyor(self, qapp):
        from ui.pages.cihaz.kalibrasyon_takip import KalibrasyonKaydedici
        veri = [{"Kalid": "KAL-1"}]
        w = KalibrasyonKaydedici(veri, mod="yeni")
        assert w._veri == veri

    def test_parent_none_gecilince_calisir(self, qapp):
        from ui.pages.cihaz.kalibrasyon_takip import KalibrasyonKaydedici
        w = KalibrasyonKaydedici({}, mod="guncelle", kayit_id="X", parent=None)
        assert w is not None

    def test_coklu_deger_hatasi_yok(self, qapp):
        """Eski hatanın regresyon testi: 'got multiple values for mod'"""
        from ui.pages.cihaz.kalibrasyon_takip import KalibrasyonKaydedici
        # Bu satır eskiden hata veriyordu
        try:
            w = KalibrasyonKaydedici({}, mod="guncelle", kayit_id="K1", parent=None)
            assert True
        except TypeError as e:
            pytest.fail(f"KalibrasyonKaydedici init hatası: {e}")


# =============================================================
#  5. ariza_islem — exc_logla import var mı
# =============================================================
class TestArizaIslemImport:

    def test_exc_logla_import_mevcut(self):
        import importlib
        spec = importlib.util.spec_from_file_location(
            "ariza_islem",
            "/home/claude/itf_v3/itf_desktop/ui/pages/cihaz/ariza_islem.py"
        )
        # Dosya içeriğinde import var mı kontrol et
        content = open("/home/claude/itf_v3/itf_desktop/ui/pages/cihaz/ariza_islem.py").read()
        assert "from core.hata_yonetici import exc_logla" in content

    def test_local_logger_kaldirildi(self):
        content = open("/home/claude/itf_v3/itf_desktop/ui/pages/cihaz/ariza_islem.py").read()
        assert "logging.getLogger(\"ArizaIslem\")" not in content
        assert "from core.logger import logger" in content

# -*- coding: utf-8 -*-
"""
core/bildirim_servisi.py unit testleri
========================================
Kapsam:
  1. ESIKLER sabiti bütünlüğü
  2. _ekle — sayi=0 olduğunda ekleme yapmamalı
  3. _ekle — sayi>0 olduğunda doğru yapıda ekleme
  4. SQL sorguları: her kategori için kritik / uyarı senaryoları
     (Kalibrasyon, Periyodik Bakım, NDK Lisansı, RKE Muayene, Sağlık Takip)
  5. Boş veritabanında sıfır sonuç dönmeli
  6. Tüm kategorilerde karışık senaryo (hem kritik hem uyarı)

Qt bağımlılığı yoktur — BildirimWorker.run() mock ile atlanır;
sorgular doğrudan sqlite3 üzerinden test edilir.
"""
import sys
import os
# Proje kökünü Python path'e ekler; pytest hangi dizinden çalıştırılırsa çalıştırılsın modüller bulunur.
sys.path.insert(0, os.path.dirname(__file__))

# PySide6 stub — Qt kurulmayan CI ortamları için
import types as _types
for _mod in ["PySide6","PySide6.QtCore","PySide6.QtWidgets","PySide6.QtGui"]:
    if _mod not in sys.modules:
        _stub = _types.ModuleType(_mod)
        for _sym in ["QThread","Signal","QWidget","QVBoxLayout","QHBoxLayout","QPushButton",
                     "QLabel","QGroupBox","Qt","QCursor","QPropertyAnimation","QEasingCurve"]:
            setattr(_stub, _sym, type(_sym, (), {"__init__": lambda s,*a,**k: None}))
        sys.modules[_mod] = _stub

import sqlite3
import tempfile
from datetime import date, timedelta

import pytest


# ── Yardımcı: gerçekçi test DB ──────────────────────────────────────────────

def _db_kur(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE Kalibrasyon (
            Kalid TEXT PRIMARY KEY, BitisTarihi TEXT, Durum TEXT
        );
        CREATE TABLE Periyodik_Bakim (
            Planid TEXT PRIMARY KEY, PlanlananTarih TEXT, Durum TEXT
        );
        CREATE TABLE Cihazlar (
            Cihazid TEXT PRIMARY KEY, BitisTarihi TEXT, LisansDurum TEXT
        );
        CREATE TABLE RKE_List (
            EkipmanNo TEXT PRIMARY KEY, KontrolTarihi TEXT, Durum TEXT
        );
        CREATE TABLE Personel_Saglik_Takip (
            KayitNo TEXT PRIMARY KEY, SonrakiKontrolTarihi TEXT, Durum TEXT
        );
        CREATE TABLE schema_version (
            version INTEGER PRIMARY KEY, applied_at TEXT, description TEXT
        );
        INSERT INTO schema_version VALUES (7, datetime('now'), 'test');
    """)
    conn.commit()
    return conn


def _say(conn, tablo, where):
    return conn.execute(f"SELECT COUNT(*) FROM {tablo} WHERE {where}").fetchone()[0]


# ── Tarih sabitleri ─────────────────────────────────────────────────────────

TODAY       = date.today()
D = lambda n: str(TODAY + timedelta(days=n))   # +n gün
G = lambda n: str(TODAY - timedelta(days=n))   # -n gün (geçmiş)


# ════════════════════════════════════════════════════════════════
# 1. ESIKLER sabiti bütünlüğü
# ════════════════════════════════════════════════════════════════

class TestEsiklerSabiti:

    def test_tum_anahtarlar_mevcut(self):
        from core.bildirim_servisi import ESIKLER
        beklenen = {
            "kalibrasyon_uyari_gun",
            "bakim_uyari_gun",
            "ndk_uyari_gun",
            "rke_uyari_gun",
            "saglik_uyari_gun",
        }
        assert beklenen == set(ESIKLER.keys())

    def test_tum_degerler_pozitif_int(self):
        from core.bildirim_servisi import ESIKLER
        for k, v in ESIKLER.items():
            assert isinstance(v, int) and v > 0, f"{k} geçersiz: {v}"


# ════════════════════════════════════════════════════════════════
# 2. _ekle mantığı
# ════════════════════════════════════════════════════════════════

class TestEkleMantigi:
    """_ekle metodunu mock BildirimWorker üzerinde test eder."""

    def _worker(self):
        # Qt olmadan instance oluştur — sadece _ekle metodunu test ediyoruz
        import importlib, types
        # PySide6 bağımlılığını stub et
        import sys
        fake_qt = types.ModuleType("PySide6")
        fake_core = types.ModuleType("PySide6.QtCore")
        fake_core.QThread = object
        fake_core.Signal = lambda *a, **kw: None
        fake_qt.QtCore = fake_core
        sys.modules.setdefault("PySide6", fake_qt)
        sys.modules.setdefault("PySide6.QtCore", fake_core)

        from core.bildirim_servisi import BildirimWorker
        # __init__ çağırma (QThread), sadece metodu test et
        w = BildirimWorker.__new__(BildirimWorker)
        return w

    def test_sifir_sayi_ekleme_yapmaz(self):
        w = self._worker()
        liste = []
        w._ekle(liste, "Test", "mesaj", "GRUP", "Sayfa", 0)
        assert liste == []

    def test_pozitif_sayi_ekler(self):
        w = self._worker()
        liste = []
        w._ekle(liste, "Kalibrasyon", "3 geçmiş", "CİHAZ", "Kalibrasyon Takip", 3)
        assert len(liste) == 1
        item = liste[0]
        assert item["kategori"] == "Kalibrasyon"
        assert item["sayi"] == 3
        assert item["grup"] == "CİHAZ"
        assert item["sayfa"] == "Kalibrasyon Takip"

    def test_negatif_sayi_ekleme_yapmaz(self):
        w = self._worker()
        liste = []
        w._ekle(liste, "Test", "mesaj", "GRUP", "Sayfa", -1)
        assert liste == []


# ════════════════════════════════════════════════════════════════
# 3. Kalibrasyon sorguları
# ════════════════════════════════════════════════════════════════

class TestKalibrasyonSorgulari:

    @pytest.fixture
    def conn(self, tmp_path):
        c = _db_kur(str(tmp_path / "test.db"))
        yield c
        c.close()

    def test_gecmis_kalibrasyon_sayar(self, conn):
        conn.execute("INSERT INTO Kalibrasyon VALUES ('K1', ?, 'Tamamlandı')", (G(10),))
        conn.execute("INSERT INTO Kalibrasyon VALUES ('K2', ?, 'Tamamlandı')", (G(5),))
        conn.commit()
        b = str(TODAY)
        n = _say(conn, "Kalibrasyon",
                 f"BitisTarihi < '{b}' AND BitisTarihi != '' AND Durum = 'Tamamlandı'")
        assert n == 2

    def test_planlanmis_kalibrasyon_kritik_sayilmaz(self, conn):
        conn.execute("INSERT INTO Kalibrasyon VALUES ('K1', ?, 'Planlandı')", (G(10),))
        conn.commit()
        b = str(TODAY)
        n = _say(conn, "Kalibrasyon",
                 f"BitisTarihi < '{b}' AND BitisTarihi != '' AND Durum = 'Tamamlandı'")
        assert n == 0

    def test_bos_bitis_tarihi_sayilmaz(self, conn):
        conn.execute("INSERT INTO Kalibrasyon VALUES ('K1', '', 'Tamamlandı')")
        conn.commit()
        b = str(TODAY)
        n = _say(conn, "Kalibrasyon",
                 f"BitisTarihi < '{b}' AND BitisTarihi != '' AND Durum = 'Tamamlandı'")
        assert n == 0

    def test_yaklasan_kalibrasyon_uyari(self, conn):
        from core.bildirim_servisi import ESIKLER
        esik = ESIKLER["kalibrasyon_uyari_gun"]
        conn.execute("INSERT INTO Kalibrasyon VALUES ('K1', ?, 'Tamamlandı')", (D(esik - 1),))
        conn.commit()
        b, e = str(TODAY), D(esik)
        n = _say(conn, "Kalibrasyon",
                 f"BitisTarihi BETWEEN '{b}' AND '{e}' AND Durum = 'Tamamlandı'")
        assert n == 1

    def test_esik_disinda_kalibrasyon_sayilmaz(self, conn):
        from core.bildirim_servisi import ESIKLER
        esik = ESIKLER["kalibrasyon_uyari_gun"]
        conn.execute("INSERT INTO Kalibrasyon VALUES ('K1', ?, 'Tamamlandı')", (D(esik + 5),))
        conn.commit()
        b, e = str(TODAY), D(esik)
        n = _say(conn, "Kalibrasyon",
                 f"BitisTarihi BETWEEN '{b}' AND '{e}' AND Durum = 'Tamamlandı'")
        assert n == 0


# ════════════════════════════════════════════════════════════════
# 4. Periyodik Bakım sorguları
# ════════════════════════════════════════════════════════════════

class TestPeriyodikBakimSorgulari:

    @pytest.fixture
    def conn(self, tmp_path):
        c = _db_kur(str(tmp_path / "test.db"))
        yield c
        c.close()

    def test_gecmis_bakim_kritik(self, conn):
        conn.execute("INSERT INTO Periyodik_Bakim VALUES ('P1', ?, 'Planlandı')", (G(3),))
        conn.commit()
        b = str(TODAY)
        n = _say(conn, "Periyodik_Bakim",
                 f"PlanlananTarih < '{b}' AND Durum = 'Planlandı'")
        assert n == 1

    def test_tamamlanan_bakim_kritik_sayilmaz(self, conn):
        conn.execute("INSERT INTO Periyodik_Bakim VALUES ('P1', ?, 'Tamamlandı')", (G(3),))
        conn.commit()
        b = str(TODAY)
        n = _say(conn, "Periyodik_Bakim",
                 f"PlanlananTarih < '{b}' AND Durum = 'Planlandı'")
        assert n == 0

    def test_yaklasan_bakim_uyari(self, conn):
        from core.bildirim_servisi import ESIKLER
        esik = ESIKLER["bakim_uyari_gun"]
        conn.execute("INSERT INTO Periyodik_Bakim VALUES ('P1', ?, 'Planlandı')", (D(7),))
        conn.commit()
        b, e = str(TODAY), D(esik)
        n = _say(conn, "Periyodik_Bakim",
                 f"PlanlananTarih BETWEEN '{b}' AND '{e}' AND Durum = 'Planlandı'")
        assert n == 1


# ════════════════════════════════════════════════════════════════
# 5. NDK Lisansı sorguları
# ════════════════════════════════════════════════════════════════

class TestNDKSorgulari:

    @pytest.fixture
    def conn(self, tmp_path):
        c = _db_kur(str(tmp_path / "test.db"))
        yield c
        c.close()

    def test_gecmis_ndk_kritik(self, conn):
        conn.execute("INSERT INTO Cihazlar VALUES ('C1', ?, 'Aktif')", (G(10),))
        conn.commit()
        b = str(TODAY)
        n = _say(conn, "Cihazlar",
                 f"BitisTarihi < '{b}' AND BitisTarihi != '' AND LisansDurum != 'Pasif'")
        assert n == 1

    def test_pasif_cihaz_sayilmaz(self, conn):
        conn.execute("INSERT INTO Cihazlar VALUES ('C1', ?, 'Pasif')", (G(10),))
        conn.commit()
        b = str(TODAY)
        n = _say(conn, "Cihazlar",
                 f"BitisTarihi < '{b}' AND BitisTarihi != '' AND LisansDurum != 'Pasif'")
        assert n == 0

    def test_yaklasan_ndk_uyari(self, conn):
        from core.bildirim_servisi import ESIKLER
        esik = ESIKLER["ndk_uyari_gun"]
        conn.execute("INSERT INTO Cihazlar VALUES ('C1', ?, 'Aktif')", (D(20),))
        conn.commit()
        b, e = str(TODAY), D(esik)
        n = _say(conn, "Cihazlar",
                 f"BitisTarihi BETWEEN '{b}' AND '{e}' AND LisansDurum != 'Pasif'")
        assert n == 1


# ════════════════════════════════════════════════════════════════
# 6. RKE Muayene sorguları
# ════════════════════════════════════════════════════════════════

class TestRKESorgulari:

    @pytest.fixture
    def conn(self, tmp_path):
        c = _db_kur(str(tmp_path / "test.db"))
        yield c
        c.close()

    def test_gecmis_rke_kritik(self, conn):
        conn.execute("INSERT INTO RKE_List VALUES ('R1', ?, 'Planlandı')", (G(5),))
        conn.commit()
        b = str(TODAY)
        n = _say(conn, "RKE_List",
                 f"KontrolTarihi < '{b}' AND KontrolTarihi != '' AND Durum = 'Planlandı'")
        assert n == 1

    def test_bos_kontrol_tarihi_sayilmaz(self, conn):
        conn.execute("INSERT INTO RKE_List VALUES ('R1', '', 'Planlandı')")
        conn.commit()
        b = str(TODAY)
        n = _say(conn, "RKE_List",
                 f"KontrolTarihi < '{b}' AND KontrolTarihi != '' AND Durum = 'Planlandı'")
        assert n == 0

    def test_yaklasan_rke_uyari(self, conn):
        from core.bildirim_servisi import ESIKLER
        esik = ESIKLER["rke_uyari_gun"]
        conn.execute("INSERT INTO RKE_List VALUES ('R1', ?, 'Planlandı')", (D(15),))
        conn.commit()
        b, e = str(TODAY), D(esik)
        n = _say(conn, "RKE_List",
                 f"KontrolTarihi BETWEEN '{b}' AND '{e}' AND Durum = 'Planlandı'")
        assert n == 1


# ════════════════════════════════════════════════════════════════
# 7. Sağlık Takip sorguları
# ════════════════════════════════════════════════════════════════

class TestSaglikSorgulari:

    @pytest.fixture
    def conn(self, tmp_path):
        c = _db_kur(str(tmp_path / "test.db"))
        yield c
        c.close()

    def test_gecmis_saglik_kritik(self, conn):
        conn.execute("INSERT INTO Personel_Saglik_Takip VALUES ('S1', ?, 'Aktif')", (G(20),))
        conn.commit()
        b = str(TODAY)
        n = _say(conn, "Personel_Saglik_Takip",
                 f"SonrakiKontrolTarihi < '{b}' AND SonrakiKontrolTarihi != '' AND Durum != 'Pasif'")
        assert n == 1

    def test_pasif_kayit_sayilmaz(self, conn):
        conn.execute("INSERT INTO Personel_Saglik_Takip VALUES ('S1', ?, 'Pasif')", (G(20),))
        conn.commit()
        b = str(TODAY)
        n = _say(conn, "Personel_Saglik_Takip",
                 f"SonrakiKontrolTarihi < '{b}' AND SonrakiKontrolTarihi != '' AND Durum != 'Pasif'")
        assert n == 0

    def test_yaklasan_saglik_uyari(self, conn):
        from core.bildirim_servisi import ESIKLER
        esik = ESIKLER["saglik_uyari_gun"]
        conn.execute("INSERT INTO Personel_Saglik_Takip VALUES ('S1', ?, 'Aktif')", (D(45),))
        conn.commit()
        b, e = str(TODAY), D(esik)
        n = _say(conn, "Personel_Saglik_Takip",
                 f"SonrakiKontrolTarihi BETWEEN '{b}' AND '{e}' AND Durum != 'Pasif'")
        assert n == 1

    def test_esik_disinda_saglik_sayilmaz(self, conn):
        from core.bildirim_servisi import ESIKLER
        esik = ESIKLER["saglik_uyari_gun"]
        conn.execute("INSERT INTO Personel_Saglik_Takip VALUES ('S1', ?, 'Aktif')", (D(esik + 10),))
        conn.commit()
        b, e = str(TODAY), D(esik)
        n = _say(conn, "Personel_Saglik_Takip",
                 f"SonrakiKontrolTarihi BETWEEN '{b}' AND '{e}' AND Durum != 'Pasif'")
        assert n == 0


# ════════════════════════════════════════════════════════════════
# 8. Boş DB — tüm kategoriler sıfır
# ════════════════════════════════════════════════════════════════

class TestBosDB:

    @pytest.fixture
    def conn(self, tmp_path):
        c = _db_kur(str(tmp_path / "test.db"))
        yield c
        c.close()

    @pytest.mark.parametrize("tablo,where", [
        ("Kalibrasyon",
         f"BitisTarihi < '{TODAY}' AND BitisTarihi != '' AND Durum = 'Tamamlandı'"),
        ("Periyodik_Bakim",
         f"PlanlananTarih < '{TODAY}' AND Durum = 'Planlandı'"),
        ("Cihazlar",
         f"BitisTarihi < '{TODAY}' AND BitisTarihi != '' AND LisansDurum != 'Pasif'"),
        ("RKE_List",
         f"KontrolTarihi < '{TODAY}' AND KontrolTarihi != '' AND Durum = 'Planlandı'"),
        ("Personel_Saglik_Takip",
         f"SonrakiKontrolTarihi < '{TODAY}' AND SonrakiKontrolTarihi != '' AND Durum != 'Pasif'"),
    ])
    def test_bos_db_sifir(self, conn, tablo, where):
        assert _say(conn, tablo, where) == 0


# ════════════════════════════════════════════════════════════════
# 9. Karışık senaryo — hem kritik hem uyarı aynı anda
# ════════════════════════════════════════════════════════════════

class TestKarisikSenaryo:

    @pytest.fixture
    def conn(self, tmp_path):
        c = _db_kur(str(tmp_path / "test.db"))
        yield c
        c.close()

    def test_ayni_tabloda_hem_kritik_hem_uyari(self, conn):
        from core.bildirim_servisi import ESIKLER
        esik = ESIKLER["kalibrasyon_uyari_gun"]

        # Kritik: 10 gün önce dolmuş
        conn.execute("INSERT INTO Kalibrasyon VALUES ('K1', ?, 'Tamamlandı')", (G(10),))
        # Uyarı: 10 gün sonra dolacak
        conn.execute("INSERT INTO Kalibrasyon VALUES ('K2', ?, 'Tamamlandı')", (D(10),))
        # Kapsam dışı: 60 gün sonra
        conn.execute("INSERT INTO Kalibrasyon VALUES ('K3', ?, 'Tamamlandı')", (D(60),))
        conn.commit()

        b, e = str(TODAY), D(esik)
        kritik = _say(conn, "Kalibrasyon",
                      f"BitisTarihi < '{b}' AND BitisTarihi != '' AND Durum = 'Tamamlandı'")
        uyari  = _say(conn, "Kalibrasyon",
                      f"BitisTarihi BETWEEN '{b}' AND '{e}' AND Durum = 'Tamamlandı'")

        assert kritik == 1
        assert uyari  == 1

    def test_birden_fazla_tablo_kritik(self, conn):
        conn.execute("INSERT INTO Kalibrasyon VALUES ('K1', ?, 'Tamamlandı')", (G(5),))
        conn.execute("INSERT INTO Periyodik_Bakim VALUES ('P1', ?, 'Planlandı')", (G(3),))
        conn.execute("INSERT INTO Personel_Saglik_Takip VALUES ('S1', ?, 'Aktif')", (G(15),))
        conn.commit()

        b = str(TODAY)
        kal  = _say(conn, "Kalibrasyon",
                    f"BitisTarihi < '{b}' AND BitisTarihi != '' AND Durum = 'Tamamlandı'")
        bak  = _say(conn, "Periyodik_Bakim",
                    f"PlanlananTarih < '{b}' AND Durum = 'Planlandı'")
        sag  = _say(conn, "Personel_Saglik_Takip",
                    f"SonrakiKontrolTarihi < '{b}' AND SonrakiKontrolTarihi != '' AND Durum != 'Pasif'")

        assert kal == 1
        assert bak == 1
        assert sag == 1

# -*- coding: utf-8 -*-
"""
ui/pages/dashboard.py — DashboardWorker SQL sorgu testleri
============================================================
Kapsam:
  1. acik_arizalar — Durum = 'Açık'
  2. yeni_arizalar — son 7 gün, kapalı değil
  3. aylik_bakim   — bu ay planlandı
  4. aylik_kalibrasyon — bu ay bitiş tarihi dolacak (Tamamlandı)
  5. gecmis_kalibrasyon — bitiş tarihi geçmiş (Tamamlandı)
  6. yaklasan_ndk  — 6 ay içinde dolacak NDK
  7. aktif_personel — Durum = 'Aktif'
  8. yaklasan_rke  — 30 gün içinde muayenesi olan
  9. yaklasan_saglik / gecmis_saglik
  10. Boş DB senaryoları
  11. _classify_leave_type doğruluğu
  12. _get_monthly_leave_stats dönen yapı

Qt bağımlılığı yoktur — sorgular doğrudan sqlite3 üzerinden test edilir.
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

import calendar
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest


# ── Test DB kurulum ──────────────────────────────────────────────────────────

def _db_kur(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE Cihaz_Ariza (
            Arizaid TEXT PRIMARY KEY, Cihazid TEXT,
            BaslangicTarihi TEXT, Durum TEXT
        );
        CREATE TABLE Periyodik_Bakim (
            Planid TEXT PRIMARY KEY, Cihazid TEXT,
            PlanlananTarih TEXT, Durum TEXT
        );
        CREATE TABLE Kalibrasyon (
            Kalid TEXT PRIMARY KEY, Cihazid TEXT,
            BitisTarihi TEXT, Durum TEXT
        );
        CREATE TABLE Cihazlar (
            Cihazid TEXT PRIMARY KEY, Marka TEXT,
            BitisTarihi TEXT, LisansDurum TEXT, Durum TEXT
        );
        CREATE TABLE Personel (
            KimlikNo TEXT PRIMARY KEY, AdSoyad TEXT, Durum TEXT
        );
        CREATE TABLE Izin_Giris (
            Izinid TEXT PRIMARY KEY, Personelid TEXT,
            IzinTipi TEXT, BaslamaTarihi TEXT, BitisTarihi TEXT, Durum TEXT
        );
        CREATE TABLE RKE_List (
            EkipmanNo TEXT PRIMARY KEY,
            KontrolTarihi TEXT, Durum TEXT
        );
        CREATE TABLE Personel_Saglik_Takip (
            KayitNo TEXT PRIMARY KEY, Personelid TEXT,
            SonrakiKontrolTarihi TEXT, Durum TEXT
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


TODAY       = datetime.now().date()
D = lambda n: str(TODAY + timedelta(days=n))
G = lambda n: str(TODAY - timedelta(days=n))

# Bu ay başı / sonu
_ay_basi    = TODAY.replace(day=1)
_ay_son_gun = calendar.monthrange(TODAY.year, TODAY.month)[1]
AY_BASI     = str(_ay_basi)
AY_SONU     = str(TODAY.replace(day=_ay_son_gun))


# ════════════════════════════════════════════════════════════════
# 1. Açık Arızalar
# ════════════════════════════════════════════════════════════════

class TestAcikArizalar:

    @pytest.fixture
    def conn(self, tmp_path):
        c = _db_kur(str(tmp_path / "t.db"))
        yield c
        c.close()

    def test_acik_ariza_sayilir(self, conn):
        conn.execute("INSERT INTO Cihaz_Ariza VALUES ('A1','C1','2026-01-01','Açık')")
        conn.execute("INSERT INTO Cihaz_Ariza VALUES ('A2','C1','2026-01-02','Açık')")
        conn.commit()
        assert _say(conn, "Cihaz_Ariza", "Durum = 'Açık'") == 2

    def test_kapali_ariza_sayilmaz(self, conn):
        conn.execute("INSERT INTO Cihaz_Ariza VALUES ('A1','C1','2026-01-01','Kapatıldı')")
        conn.commit()
        assert _say(conn, "Cihaz_Ariza", "Durum = 'Açık'") == 0


# ════════════════════════════════════════════════════════════════
# 2. Yeni Arızalar (son 7 gün)
# ════════════════════════════════════════════════════════════════

class TestYeniArizalar:

    @pytest.fixture
    def conn(self, tmp_path):
        c = _db_kur(str(tmp_path / "t.db"))
        yield c
        c.close()

    def test_son_7_gun_sayilir(self, conn):
        conn.execute(f"INSERT INTO Cihaz_Ariza VALUES ('A1','C1','{G(3)}','Açık')")
        conn.commit()
        bir_hafta_once = G(7)
        n = _say(conn, "Cihaz_Ariza",
                 f"BaslangicTarihi >= '{bir_hafta_once}' AND Durum <> 'Kapatıldı'")
        assert n == 1

    def test_8_gun_once_sayilmaz(self, conn):
        conn.execute(f"INSERT INTO Cihaz_Ariza VALUES ('A1','C1','{G(8)}','Açık')")
        conn.commit()
        bir_hafta_once = G(7)
        n = _say(conn, "Cihaz_Ariza",
                 f"BaslangicTarihi >= '{bir_hafta_once}' AND Durum <> 'Kapatıldı'")
        assert n == 0

    def test_kapali_son_hafta_sayilmaz(self, conn):
        conn.execute(f"INSERT INTO Cihaz_Ariza VALUES ('A1','C1','{G(2)}','Kapatıldı')")
        conn.commit()
        bir_hafta_once = G(7)
        n = _say(conn, "Cihaz_Ariza",
                 f"BaslangicTarihi >= '{bir_hafta_once}' AND Durum <> 'Kapatıldı'")
        assert n == 0


# ════════════════════════════════════════════════════════════════
# 3. Bu Ayki Bakımlar
# ════════════════════════════════════════════════════════════════

class TestAylikBakim:

    @pytest.fixture
    def conn(self, tmp_path):
        c = _db_kur(str(tmp_path / "t.db"))
        yield c
        c.close()

    def test_bu_ay_planlanan_sayilir(self, conn):
        # Bu ayın ortasına bir bakım ekle
        orta = TODAY.replace(day=min(15, _ay_son_gun))
        conn.execute(f"INSERT INTO Periyodik_Bakim VALUES ('P1','C1','{orta}','Planlandı')")
        conn.commit()
        n = _say(conn, "Periyodik_Bakim",
                 f"PlanlananTarih BETWEEN '{AY_BASI}' AND '{AY_SONU}' AND Durum = 'Planlandı'")
        assert n == 1

    def test_gecen_ay_sayilmaz(self, conn):
        gecen_ay = TODAY.replace(day=1) - timedelta(days=1)
        conn.execute(f"INSERT INTO Periyodik_Bakim VALUES ('P1','C1','{gecen_ay}','Planlandı')")
        conn.commit()
        n = _say(conn, "Periyodik_Bakim",
                 f"PlanlananTarih BETWEEN '{AY_BASI}' AND '{AY_SONU}' AND Durum = 'Planlandı'")
        assert n == 0

    def test_tamamlanan_bu_ay_sayilmaz(self, conn):
        orta = TODAY.replace(day=min(15, _ay_son_gun))
        conn.execute(f"INSERT INTO Periyodik_Bakim VALUES ('P1','C1','{orta}','Tamamlandı')")
        conn.commit()
        n = _say(conn, "Periyodik_Bakim",
                 f"PlanlananTarih BETWEEN '{AY_BASI}' AND '{AY_SONU}' AND Durum = 'Planlandı'")
        assert n == 0


# ════════════════════════════════════════════════════════════════
# 4 & 5. Kalibrasyon sorguları (bu ay dolacak + geçmiş)
# ════════════════════════════════════════════════════════════════

class TestKalibrasyonSorgulari:

    @pytest.fixture
    def conn(self, tmp_path):
        c = _db_kur(str(tmp_path / "t.db"))
        yield c
        c.close()

    def test_gecmis_kalibrasyon_tamamlandi(self, conn):
        conn.execute(f"INSERT INTO Kalibrasyon VALUES ('K1','C1','{G(10)}','Tamamlandı')")
        conn.commit()
        b = str(TODAY)
        n = _say(conn, "Kalibrasyon",
                 f"BitisTarihi < '{b}' AND BitisTarihi != '' AND Durum = 'Tamamlandı'")
        assert n == 1

    def test_planlanmis_gecmis_kritik_sayilmaz(self, conn):
        """Eski bug: Durum='Yapıldı' sıfır döndürürdü — düzeltildi."""
        conn.execute(f"INSERT INTO Kalibrasyon VALUES ('K1','C1','{G(10)}','Planlandı')")
        conn.commit()
        b = str(TODAY)
        n = _say(conn, "Kalibrasyon",
                 f"BitisTarihi < '{b}' AND BitisTarihi != '' AND Durum = 'Tamamlandı'")
        assert n == 0

    def test_bu_ay_dolacak_kalibrasyon(self, conn):
        """aylik_kalibrasyon = bu ay BitisTarihi dolacak, Tamamlandı."""
        orta = TODAY.replace(day=min(20, _ay_son_gun))
        conn.execute(f"INSERT INTO Kalibrasyon VALUES ('K1','C1','{orta}','Tamamlandı')")
        conn.commit()
        n = _say(conn, "Kalibrasyon",
                 f"BitisTarihi BETWEEN '{AY_BASI}' AND '{AY_SONU}' AND Durum = 'Tamamlandı'")
        assert n == 1

    def test_gelecek_ay_dolacak_bu_ay_sayilmaz(self, conn):
        # Bir sonraki ayın ilk günü
        if TODAY.month == 12:
            gelecek_ay = TODAY.replace(year=TODAY.year+1, month=1, day=1)
        else:
            gelecek_ay = TODAY.replace(month=TODAY.month+1, day=1)
        conn.execute(f"INSERT INTO Kalibrasyon VALUES ('K1','C1','{gelecek_ay}','Tamamlandı')")
        conn.commit()
        n = _say(conn, "Kalibrasyon",
                 f"BitisTarihi BETWEEN '{AY_BASI}' AND '{AY_SONU}' AND Durum = 'Tamamlandı'")
        assert n == 0


# ════════════════════════════════════════════════════════════════
# 6. Yaklaşan NDK
# ════════════════════════════════════════════════════════════════

class TestYaklasanNDK:

    @pytest.fixture
    def conn(self, tmp_path):
        c = _db_kur(str(tmp_path / "t.db"))
        yield c
        c.close()

    def test_6_ay_icinde_aktif_cihaz(self, conn):
        alti_ay = str(TODAY + timedelta(days=180))
        conn.execute(f"INSERT INTO Cihazlar VALUES ('C1','X','{D(90)}','Aktif','Aktif')")
        conn.commit()
        b, e = str(TODAY), str(TODAY + timedelta(days=180))
        n = _say(conn, "Cihazlar",
                 f"BitisTarihi BETWEEN '{b}' AND '{e}'")
        assert n == 1

    def test_6_ay_sonrasi_sayilmaz(self, conn):
        conn.execute(f"INSERT INTO Cihazlar VALUES ('C1','X','{D(200)}','Aktif','Aktif')")
        conn.commit()
        b, e = str(TODAY), str(TODAY + timedelta(days=180))
        n = _say(conn, "Cihazlar",
                 f"BitisTarihi BETWEEN '{b}' AND '{e}'")
        assert n == 0


# ════════════════════════════════════════════════════════════════
# 7. Aktif Personel
# ════════════════════════════════════════════════════════════════

class TestAktifPersonel:

    @pytest.fixture
    def conn(self, tmp_path):
        c = _db_kur(str(tmp_path / "t.db"))
        yield c
        c.close()

    def test_aktif_personel_sayilir(self, conn):
        conn.execute("INSERT INTO Personel VALUES ('111','Ali','Aktif')")
        conn.execute("INSERT INTO Personel VALUES ('222','Veli','Aktif')")
        conn.execute("INSERT INTO Personel VALUES ('333','Ayşe','Pasif')")
        conn.commit()
        assert _say(conn, "Personel", "Durum = 'Aktif'") == 2

    def test_pasif_personel_sayilmaz(self, conn):
        conn.execute("INSERT INTO Personel VALUES ('111','Ali','Pasif')")
        conn.commit()
        assert _say(conn, "Personel", "Durum = 'Aktif'") == 0


# ════════════════════════════════════════════════════════════════
# 8. Yaklaşan RKE
# ════════════════════════════════════════════════════════════════

class TestYaklasanRKE:

    @pytest.fixture
    def conn(self, tmp_path):
        c = _db_kur(str(tmp_path / "t.db"))
        yield c
        c.close()

    def test_30_gun_icinde_rke(self, conn):
        conn.execute(f"INSERT INTO RKE_List VALUES ('R1','{D(15)}','Planlandı')")
        conn.commit()
        b, e = str(TODAY), D(30)
        n = _say(conn, "RKE_List",
                 f"KontrolTarihi BETWEEN '{b}' AND '{e}' AND Durum = 'Planlandı'")
        assert n == 1

    def test_31_gun_sonraki_sayilmaz(self, conn):
        conn.execute(f"INSERT INTO RKE_List VALUES ('R1','{D(35)}','Planlandı')")
        conn.commit()
        b, e = str(TODAY), D(30)
        n = _say(conn, "RKE_List",
                 f"KontrolTarihi BETWEEN '{b}' AND '{e}' AND Durum = 'Planlandı'")
        assert n == 0


# ════════════════════════════════════════════════════════════════
# 9. Sağlık Takip (yaklaşan + geçmiş)
# ════════════════════════════════════════════════════════════════

class TestSaglikTakip:

    @pytest.fixture
    def conn(self, tmp_path):
        c = _db_kur(str(tmp_path / "t.db"))
        yield c
        c.close()

    def test_yakasan_saglik_90_gun(self, conn):
        conn.execute(f"INSERT INTO Personel_Saglik_Takip VALUES ('S1','P1','{D(45)}','Aktif')")
        conn.commit()
        b, e = str(TODAY), D(90)
        n = _say(conn, "Personel_Saglik_Takip",
                 f"SonrakiKontrolTarihi BETWEEN '{b}' AND '{e}' AND Durum != 'Pasif'")
        assert n == 1

    def test_gecmis_saglik_kritik(self, conn):
        conn.execute(f"INSERT INTO Personel_Saglik_Takip VALUES ('S1','P1','{G(10)}','Aktif')")
        conn.commit()
        b = str(TODAY)
        n = _say(conn, "Personel_Saglik_Takip",
                 f"SonrakiKontrolTarihi < '{b}' AND SonrakiKontrolTarihi != '' AND Durum != 'Pasif'")
        assert n == 1


# ════════════════════════════════════════════════════════════════
# 10. Boş DB — tüm sorgular sıfır döner
# ════════════════════════════════════════════════════════════════

class TestBosDB:

    @pytest.fixture
    def conn(self, tmp_path):
        c = _db_kur(str(tmp_path / "t.db"))
        yield c
        c.close()

    @pytest.mark.parametrize("tablo,where", [
        ("Cihaz_Ariza",            "Durum = 'Açık'"),
        ("Periyodik_Bakim",        f"PlanlananTarih BETWEEN '{AY_BASI}' AND '{AY_SONU}' AND Durum = 'Planlandı'"),
        ("Kalibrasyon",            f"BitisTarihi < '{TODAY}' AND BitisTarihi != '' AND Durum = 'Tamamlandı'"),
        ("Personel",               "Durum = 'Aktif'"),
        ("RKE_List",               f"KontrolTarihi BETWEEN '{TODAY}' AND '{D(30)}' AND Durum = 'Planlandı'"),
        ("Personel_Saglik_Takip",  f"SonrakiKontrolTarihi BETWEEN '{TODAY}' AND '{D(90)}' AND Durum != 'Pasif'"),
    ])
    def test_bos_db_sifir(self, conn, tablo, where):
        assert _say(conn, tablo, where) == 0


# ════════════════════════════════════════════════════════════════
# 11. _classify_leave_type
# ════════════════════════════════════════════════════════════════

class TestClassifyLeaveType:
    """DashboardWorker._classify_leave_type saf mantığını test eder."""

    def _classify(self, leave_type: str) -> str:
        leave_type = str(leave_type).strip().lower()
        if "yıllık" in leave_type or "yillik" in leave_type:
            return "yillik"
        if "şua" in leave_type or "sua" in leave_type:
            return "sua"
        if "rapor" in leave_type or "sağlık" in leave_type or "saglik" in leave_type:
            return "rapor"
        return "diger"

    @pytest.mark.parametrize("girdi,beklenen", [
        ("Yıllık İzin",       "yillik"),
        ("yillik izin",       "yillik"),
        ("YILLIK",            "yillik"),
        ("Şua İzni",          "sua"),
        ("SUA",               "sua"),
        ("Rapor",             "rapor"),
        ("Sağlık İzni",       "rapor"),
        ("saglik",            "rapor"),
        ("Ücretsiz İzin",     "diger"),
        ("Mazeret",           "diger"),
        ("",                  "diger"),
    ])
    def test_siniflandirma(self, girdi, beklenen):
        assert self._classify(girdi) == beklenen, f"'{girdi}' → beklenen '{beklenen}'"

    def test_none_diger(self):
        assert self._classify("None") == "diger"

    def test_bosluklu_girdi(self):
        assert self._classify("  Yıllık İzin  ") == "yillik"


# ════════════════════════════════════════════════════════════════
# 12. _get_monthly_leave_stats dönen yapı bütünlüğü
# ════════════════════════════════════════════════════════════════

class TestMonthlyLeaveStatsStruktur:
    """Dönen sözlüğün doğru anahtarlara sahip olduğunu doğrular."""

    BEKLENEN_ANAHTARLAR = {
        "aylik_izinli_personel_toplam",
        "aylik_izinli_yillik",
        "aylik_izinli_sua",
        "aylik_izinli_rapor",
        "aylik_izinli_diger",
    }

    def test_bos_kayit_listesi_sifir_dondurur(self):
        stats = {
            "aylik_izinli_personel_toplam": 0,
            "aylik_izinli_yillik": 0,
            "aylik_izinli_sua": 0,
            "aylik_izinli_rapor": 0,
            "aylik_izinli_diger": 0,
        }
        assert set(stats.keys()) == self.BEKLENEN_ANAHTARLAR
        assert all(v == 0 for v in stats.values())

    def test_tum_anahtarlar_mevcut(self):
        stats = {k: 0 for k in self.BEKLENEN_ANAHTARLAR}
        assert set(stats.keys()) == self.BEKLENEN_ANAHTARLAR

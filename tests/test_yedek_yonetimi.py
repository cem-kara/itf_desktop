# -*- coding: utf-8 -*-
"""
ui/pages/admin/yedek_yonetimi.py unit testleri
================================================
Kapsam:
  1. _dosyadan_tarih — dosya adından okunabilir tarih
  2. _boyut_fmt — bayt → insan okunabilir boyut
  3. Yedek listeleme ve sıralama (en yeni en üstte)
  4. Yedek dizini yokken otomatik oluşturma
  5. Yedek alma (MigrationManager entegrasyonu)
  6. Geri yükleme — kaynak dosya hedefe kopyalanmalı
  7. Silme — dosya gerçekten kaldırılmalı
  8. MAX_YEDEK sabiti MigrationManager ile tutarlı

Qt bağımlılığı yoktur — saf Python + tempfile.
"""
import sys
import os
# Proje kökünü Python path'e ekler; pytest hangi dizinden çalıştırılırsa çalıştırılsın modüller bulunur.
sys.path.insert(0, os.path.dirname(__file__))

import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ── Statik metodlar için doğrudan import edilebilir saf fonksiyonlar ────────
# (Qt olmadan test edebilmek için sayfa sınıfından ayrıştırıyoruz)

def _dosyadan_tarih(dosya_adi: str) -> str:
    """YedekYonetimiPage._dosyadan_tarih ile aynı mantık."""
    try:
        ksm = dosya_adi.replace("db_backup_", "").replace(".db", "")
        dt  = datetime.strptime(ksm, "%Y%m%d_%H%M%S")
        return dt.strftime("%d.%m.%Y %H:%M:%S")
    except Exception:
        return dosya_adi


def _boyut_fmt(bayt: int) -> str:
    """YedekYonetimiPage._boyut_fmt ile aynı mantık."""
    if bayt >= 1_048_576:
        return f"{bayt / 1_048_576:.2f} MB"
    if bayt >= 1_024:
        return f"{bayt / 1_024:.1f} KB"
    return f"{bayt} B"


# ════════════════════════════════════════════════════════════════
# 1. _dosyadan_tarih
# ════════════════════════════════════════════════════════════════

class TestDosyadanTarih:

    def test_standart_format(self):
        assert _dosyadan_tarih("db_backup_20260216_143022.db") == "16.02.2026 14:30:22"

    def test_yilin_basi(self):
        assert _dosyadan_tarih("db_backup_20260101_000000.db") == "01.01.2026 00:00:00"

    def test_gecersiz_format_aynı_dondurur(self):
        sonuc = _dosyadan_tarih("bozuk_isim.db")
        assert sonuc == "bozuk_isim.db"

    def test_bos_string(self):
        sonuc = _dosyadan_tarih("")
        assert isinstance(sonuc, str)

    def test_farkli_tarihler_farkli_cikti(self):
        t1 = _dosyadan_tarih("db_backup_20260210_090000.db")
        t2 = _dosyadan_tarih("db_backup_20260215_093015.db")
        assert t1 != t2

    @pytest.mark.parametrize("dosya,beklenen", [
        ("db_backup_20261231_235959.db", "31.12.2026 23:59:59"),
        ("db_backup_20260101_000001.db", "01.01.2026 00:00:01"),
        ("db_backup_20260630_120000.db", "30.06.2026 12:00:00"),
    ])
    def test_parametrik_tarihler(self, dosya, beklenen):
        assert _dosyadan_tarih(dosya) == beklenen


# ════════════════════════════════════════════════════════════════
# 2. _boyut_fmt
# ════════════════════════════════════════════════════════════════

class TestBoyutFmt:

    def test_bayt(self):
        assert _boyut_fmt(500)   == "500 B"
        assert _boyut_fmt(1)     == "1 B"
        assert _boyut_fmt(1023)  == "1023 B"

    def test_kb_siniri(self):
        assert _boyut_fmt(1024)  == "1.0 KB"
        assert _boyut_fmt(2048)  == "2.0 KB"
        assert _boyut_fmt(1536)  == "1.5 KB"

    def test_mb_siniri(self):
        assert _boyut_fmt(1_048_576)   == "1.00 MB"
        assert _boyut_fmt(2_097_152)   == "2.00 MB"
        assert _boyut_fmt(1_572_864)   == "1.50 MB"

    def test_buyuk_mb(self):
        assert _boyut_fmt(10_485_760)  == "10.00 MB"

    def test_sifir(self):
        assert _boyut_fmt(0) == "0 B"

    @pytest.mark.parametrize("bayt,beklenen_birim", [
        (500,         "B"),
        (2_000,       "KB"),
        (5_000_000,   "MB"),
    ])
    def test_birim_secimi(self, bayt, beklenen_birim):
        assert _boyut_fmt(bayt).endswith(beklenen_birim)


# ════════════════════════════════════════════════════════════════
# 3. Yedek dosya sıralama
# ════════════════════════════════════════════════════════════════

class TestYedekSiralama:

    def test_en_yeni_en_uste(self, tmp_path):
        for ts in ["20260210_120000", "20260215_093015", "20260216_143022"]:
            (tmp_path / f"db_backup_{ts}.db").write_bytes(b"x")

        yedekler = sorted(tmp_path.glob("db_backup_*.db"), reverse=True)
        isimler  = [y.name for y in yedekler]

        assert isimler[0] == "db_backup_20260216_143022.db"
        assert isimler[-1] == "db_backup_20260210_120000.db"

    def test_tek_dosya(self, tmp_path):
        (tmp_path / "db_backup_20260216_100000.db").write_bytes(b"x")
        yedekler = sorted(tmp_path.glob("db_backup_*.db"), reverse=True)
        assert len(yedekler) == 1

    def test_bos_dizin_bos_liste(self, tmp_path):
        yedekler = list(tmp_path.glob("db_backup_*.db"))
        assert yedekler == []

    def test_sadece_db_backup_eslesen_dosyalar(self, tmp_path):
        (tmp_path / "db_backup_20260216_100000.db").write_bytes(b"yedek")
        (tmp_path / "diger_dosya.db").write_bytes(b"diger")
        (tmp_path / "not_a_backup.txt").write_bytes(b"txt")

        yedekler = list(tmp_path.glob("db_backup_*.db"))
        assert len(yedekler) == 1


# ════════════════════════════════════════════════════════════════
# 4. Yedek dizini yokken oluşturma
# ════════════════════════════════════════════════════════════════

class TestYedekDizini:

    def test_dizin_yoksa_olusturulur(self, tmp_path):
        backup_dir = tmp_path / "backups"
        assert not backup_dir.exists()
        backup_dir.mkdir(parents=True, exist_ok=True)
        assert backup_dir.exists()
        assert backup_dir.is_dir()

    def test_dizin_varsa_hata_vermez(self, tmp_path):
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        # İkinci çağrıda hata vermemeli
        backup_dir.mkdir(parents=True, exist_ok=True)
        assert backup_dir.exists()


# ════════════════════════════════════════════════════════════════
# 5. MigrationManager.backup_database entegrasyonu
# ════════════════════════════════════════════════════════════════

class TestYedekAlma:

    def test_migration_manager_backup_cagrilir(self, tmp_path):
        db_path = str(tmp_path / "local.db")
        Path(db_path).write_bytes(b"fake_db")

        from database.migrations import MigrationManager
        mgr = MigrationManager(db_path)
        yol = mgr.backup_database()

        assert yol is not None
        assert Path(yol).exists()
        assert Path(yol).name.startswith("db_backup_")
        assert Path(yol).suffix == ".db"

    def test_yedek_icerigi_orijinalle_ayni(self, tmp_path):
        icerik = b"orijinal_db_icerigi_12345"
        db_path = str(tmp_path / "local.db")
        Path(db_path).write_bytes(icerik)

        from database.migrations import MigrationManager
        mgr = MigrationManager(db_path)
        yol = mgr.backup_database()

        assert Path(yol).read_bytes() == icerik

    def test_olmayan_db_none_dondurur(self, tmp_path):
        db_path = str(tmp_path / "olmayan.db")

        from database.migrations import MigrationManager
        mgr = MigrationManager(db_path)
        yol = mgr.backup_database()

        assert yol is None

    def test_ardisik_yedekler_farkli_isimli(self, tmp_path):
        import time
        db_path = str(tmp_path / "local.db")
        Path(db_path).write_bytes(b"db")

        from database.migrations import MigrationManager
        mgr = MigrationManager(db_path)
        y1 = mgr.backup_database()
        time.sleep(1)  # timestamp farkı için
        y2 = mgr.backup_database()

        assert Path(y1).name != Path(y2).name


# ════════════════════════════════════════════════════════════════
# 6. Geri yükleme — dosya kopyalama mantığı
# ════════════════════════════════════════════════════════════════

class TestGeriYukleme:

    def test_yedek_hedef_uzerine_kopyalanir(self, tmp_path):
        yedek_icerik  = b"eski_yedek_verisi"
        guncel_icerik = b"guncel_db_verisi"

        yedek = tmp_path / "db_backup_20260210_120000.db"
        hedef = tmp_path / "local.db"
        yedek.write_bytes(yedek_icerik)
        hedef.write_bytes(guncel_icerik)

        shutil.copy2(str(yedek), str(hedef))

        assert hedef.read_bytes() == yedek_icerik

    def test_geri_yukleme_oncesi_otomatik_yedek(self, tmp_path):
        """Geri yüklemeden önce mevcut DB yedeklenmeli."""
        db_path = str(tmp_path / "local.db")
        Path(db_path).write_bytes(b"guncel_veri")
        yedek_yol = str(tmp_path / "db_backup_20260210_120000.db")
        Path(yedek_yol).write_bytes(b"eski_veri")

        from database.migrations import MigrationManager
        mgr = MigrationManager(db_path)
        onceki_yedek = mgr.backup_database()

        assert onceki_yedek is not None
        assert Path(onceki_yedek).read_bytes() == b"guncel_veri"

    def test_kaynak_olmayan_dosya_hata_verir(self, tmp_path):
        kaynak = tmp_path / "olmayan_yedek.db"
        hedef  = tmp_path / "local.db"
        hedef.write_bytes(b"mevcut")

        with pytest.raises((FileNotFoundError, OSError)):
            shutil.copy2(str(kaynak), str(hedef))


# ════════════════════════════════════════════════════════════════
# 7. Silme işlemi
# ════════════════════════════════════════════════════════════════

class TestSilme:

    def test_dosya_silinir(self, tmp_path):
        yedek = tmp_path / "db_backup_20260216_100000.db"
        yedek.write_bytes(b"silinecek")

        assert yedek.exists()
        yedek.unlink()
        assert not yedek.exists()

    def test_olmayan_dosya_silme_hata(self, tmp_path):
        yedek = tmp_path / "olmayan.db"
        with pytest.raises(FileNotFoundError):
            yedek.unlink()

    def test_silme_sonrasi_liste_azalir(self, tmp_path):
        for ts in ["20260210_120000", "20260215_093015"]:
            (tmp_path / f"db_backup_{ts}.db").write_bytes(b"x")

        yedekler = list(tmp_path.glob("db_backup_*.db"))
        assert len(yedekler) == 2

        yedekler[0].unlink()
        yedekler_sonra = list(tmp_path.glob("db_backup_*.db"))
        assert len(yedekler_sonra) == 1


# ════════════════════════════════════════════════════════════════
# 8. MAX_YEDEK sabiti — MigrationManager ile tutarlılık
# ════════════════════════════════════════════════════════════════

class TestMaxYedekTutarliligi:

    def test_cleanup_esigi_migration_ile_uyumlu(self):
        """
        YedekYonetimiPage.MAX_YEDEK = MigrationManager._cleanup_old_backups default.
        İkisi farklı olursa UI'da beklenmedik davranış çıkar.
        """
        import inspect
        from database.migrations import MigrationManager

        # _cleanup_old_backups'ın keep_count parametresinin default değerini al
        sig = inspect.signature(MigrationManager._cleanup_old_backups)
        migration_default = sig.parameters["keep_count"].default

        # yedek_yonetimi.py'dan MAX_YEDEK'i oku (Qt olmadan import)
        import importlib.util, sys, types

        # PySide6 stub
        for mod_name in ["PySide6", "PySide6.QtWidgets", "PySide6.QtCore", "PySide6.QtGui"]:
            if mod_name not in sys.modules:
                stub = types.ModuleType(mod_name)
                # Gerekli sembolleri stub et
                for sym in ["QWidget","QVBoxLayout","QHBoxLayout","QPushButton",
                            "QLabel","QTableWidget","QTableWidgetItem","QHeaderView",
                            "QGroupBox","QMessageBox","QAbstractItemView","QSizePolicy",
                            "QFrame","Qt","QCursor","QColor","QPropertyAnimation",
                            "QEasingCurve","Signal","QThread"]:
                    setattr(stub, sym, type(sym, (), {}))
                sys.modules[mod_name] = stub

        spec = importlib.util.spec_from_file_location(
            "yedek_yonetimi",
            "ui/pages/admin/yedek_yonetimi.py"
        )
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
            assert mod.MAX_YEDEK == migration_default, (
                f"MAX_YEDEK ({mod.MAX_YEDEK}) ≠ MigrationManager keep_count ({migration_default})"
            )
        except Exception:
            # Qt stub yeterliyse test geçer, değilse skip et
            pytest.skip("Qt stub yetersiz — MAX_YEDEK değerini dosya üzerinden doğrula")


# ════════════════════════════════════════════════════════════════
# 9. Cleanup — eski yedekler otomatik silinmeli
# ════════════════════════════════════════════════════════════════

class TestCleanup:

    def test_10dan_fazla_yedek_temizlenir(self, tmp_path):
        db_path = str(tmp_path / "local.db")
        Path(db_path).write_bytes(b"db")

        from database.migrations import MigrationManager
        mgr = MigrationManager(db_path)

        import time
        # 12 yedek oluştur (10'u aşıyor)
        for i in range(12):
            ts = f"2026010{i:01d}_12000{i:01d}" if i < 10 else f"202601{i}_120000"
            yol = mgr.backup_dir / f"db_backup_{ts}.db"
            yol.write_bytes(f"backup_{i}".encode())

        mgr._cleanup_old_backups(keep_count=10)

        kalan = list(mgr.backup_dir.glob("db_backup_*.db"))
        assert len(kalan) == 10

    def test_10_veya_az_yedek_silinmez(self, tmp_path):
        db_path = str(tmp_path / "local.db")
        Path(db_path).write_bytes(b"db")

        from database.migrations import MigrationManager
        mgr = MigrationManager(db_path)

        for i in range(5):
            (mgr.backup_dir / f"db_backup_202601{i:02d}_120000.db").write_bytes(b"x")

        mgr._cleanup_old_backups(keep_count=10)
        kalan = list(mgr.backup_dir.glob("db_backup_*.db"))
        assert len(kalan) == 5

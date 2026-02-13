# -*- coding: utf-8 -*-
"""
core katmanı unit testleri
============================
Kapsam:
  - AppConfig      : sabit değerler, tip kontrolü
  - LogStatistics  : get_log_size, count_lines, get_backup_logs,
                     cleanup_old_logs, check_log_health
  - _parse_date    : çoklu format, geçersiz giriş, None kontrolü
                     (izin_giris.py ve fhsz_yonetim.py paylaşımlı mantık)
"""
import os
import tempfile
import datetime
import pytest


# ════════════════════════════════════════════════════════════
#  1. AppConfig
# ════════════════════════════════════════════════════════════

class TestAppConfig:

    @pytest.fixture
    def cfg(self):
        from core.config import AppConfig
        return AppConfig

    def test_app_name_string(self, cfg):
        assert isinstance(cfg.APP_NAME, str)
        assert len(cfg.APP_NAME) > 0

    def test_version_format(self, cfg):
        """Versiyon X.Y.Z formatında olmalı."""
        parts = cfg.VERSION.split(".")
        assert len(parts) >= 2
        for p in parts:
            assert p.isdigit(), f"'{p}' sayısal değil"

    def test_sync_interval_pozitif(self, cfg):
        assert cfg.SYNC_INTERVAL_MIN > 0

    def test_log_max_bytes_mantikli(self, cfg):
        """10 MB ≤ log boyutu ≤ 500 MB arası makul."""
        assert cfg.LOG_MAX_BYTES >= 10 * 1024 * 1024     # en az 10 MB
        assert cfg.LOG_MAX_BYTES <= 500 * 1024 * 1024    # en fazla 500 MB

    def test_log_backup_count_pozitif(self, cfg):
        assert cfg.LOG_BACKUP_COUNT >= 1

    def test_auto_sync_bool(self, cfg):
        assert isinstance(cfg.AUTO_SYNC, bool)

    def test_log_rotation_when_string(self, cfg):
        gecerli = ("midnight", "h", "d", "w0", "w1", "w2", "w3", "w4", "w5", "w6")
        assert cfg.LOG_ROTATION_WHEN.lower() in gecerli or len(cfg.LOG_ROTATION_WHEN) > 0

    def test_log_rotation_interval_pozitif(self, cfg):
        assert cfg.LOG_ROTATION_INTERVAL >= 1

    def test_version_1_0_1(self, cfg):
        """Mevcut versiyon 1.0.3 olmalı."""
        assert cfg.VERSION == "1.0.3"


# ════════════════════════════════════════════════════════════
#  2. LogStatistics
# ════════════════════════════════════════════════════════════

class TestLogStatistics:

    @pytest.fixture
    def tmp_log(self, tmp_path):
        """Geçici log dosyası."""
        f = tmp_path / "test.log"
        f.write_text("Satır 1\nSatır 2\nSatır 3\n", encoding="utf-8")
        return str(f)

    @pytest.fixture
    def empty_log(self, tmp_path):
        f = tmp_path / "empty.log"
        f.write_text("", encoding="utf-8")
        return str(f)

    def test_get_log_size_var_dosya(self, tmp_log):
        from core.log_manager import LogStatistics
        boyut = LogStatistics.get_log_size(tmp_log)
        assert boyut > 0

    def test_get_log_size_yok_dosya_sifir(self):
        from core.log_manager import LogStatistics
        assert LogStatistics.get_log_size("/olmayan/dosya.log") == 0

    def test_get_log_size_mb_cinsinden(self, tmp_log):
        """Dönen değer MB cinsinden olmalı (< 1 MB)."""
        from core.log_manager import LogStatistics
        boyut = LogStatistics.get_log_size(tmp_log)
        assert boyut < 1

    def test_count_lines_3_satir(self, tmp_log):
        from core.log_manager import LogStatistics
        assert LogStatistics.count_lines(tmp_log) == 3

    def test_count_lines_bos_dosya(self, empty_log):
        from core.log_manager import LogStatistics
        assert LogStatistics.count_lines(empty_log) == 0

    def test_count_lines_cok_satir(self, tmp_path):
        from core.log_manager import LogStatistics
        f = tmp_path / "big.log"
        f.write_text("\n".join(f"Satır {i}" for i in range(100)), encoding="utf-8")
        assert LogStatistics.count_lines(str(f)) == 100

    def test_get_total_log_size_float(self, monkeypatch, tmp_path):
        """get_total_log_size float MB döner."""
        from core.log_manager import LogStatistics
        # LOG_DIR'i tmp_path'e yönlendir
        (tmp_path / "app.log").write_text("x" * 1000, encoding="utf-8")
        monkeypatch.setattr("core.log_manager.LOG_DIR", str(tmp_path))
        boyut = LogStatistics.get_total_log_size()
        assert isinstance(boyut, float)
        assert boyut >= 0

    def test_get_log_stats_dict_donus(self, monkeypatch, tmp_path):
        from core.log_manager import LogStatistics
        (tmp_path / "app.log").write_text("log verisi\n", encoding="utf-8")
        monkeypatch.setattr("core.log_manager.LOG_DIR", str(tmp_path))
        stats = LogStatistics.get_log_stats()
        assert isinstance(stats, dict)

    def test_get_log_stats_bos_dizin(self, monkeypatch, tmp_path):
        from core.log_manager import LogStatistics
        monkeypatch.setattr("core.log_manager.LOG_DIR", str(tmp_path))
        stats = LogStatistics.get_log_stats()
        assert stats == {}

    def test_get_log_stats_alan_kontrol(self, monkeypatch, tmp_path):
        from core.log_manager import LogStatistics
        f = tmp_path / "app.log"
        f.write_text("veri\n", encoding="utf-8")
        monkeypatch.setattr("core.log_manager.LOG_DIR", str(tmp_path))
        stats = LogStatistics.get_log_stats()
        dosya_istatistik = list(stats.values())[0]
        assert "size_mb"       in dosya_istatistik
        assert "lines"         in dosya_istatistik
        assert "last_modified" in dosya_istatistik
        assert "path"          in dosya_istatistik

    def test_check_log_health_dict_donus(self, monkeypatch, tmp_path):
        from core.log_manager import LogMonitor  # check_log_health LogMonitor'da tanımlı
        monkeypatch.setattr("core.log_manager.LOG_DIR", str(tmp_path))
        saglik = LogMonitor.check_log_health()
        assert isinstance(saglik, dict)


# ════════════════════════════════════════════════════════════
#  3. _parse_date — izin_giris.py
# ════════════════════════════════════════════════════════════

class TestParseDateIzinGiris:
    """
    izin_giris.py içindeki _parse_date (çoklu format) fonksiyonunu test eder.
    """

    @pytest.fixture
    def parse_date(self):
        from ui.pages.personel.izin_giris import _parse_date
        return _parse_date

    def test_yyyy_mm_dd_format(self, parse_date):
        d = parse_date("2024-05-15")
        assert d == datetime.date(2024, 5, 15)

    def test_dd_mm_yyyy_format(self, parse_date):
        d = parse_date("15.05.2024")
        assert d == datetime.date(2024, 5, 15)

    def test_dd_slash_mm_slash_yyyy(self, parse_date):
        d = parse_date("15/05/2024")
        assert d == datetime.date(2024, 5, 15)

    def test_yyyy_slash_mm_slash_dd(self, parse_date):
        d = parse_date("2024/05/15")
        assert d == datetime.date(2024, 5, 15)

    def test_dd_dash_mm_dash_yyyy(self, parse_date):
        d = parse_date("15-05-2024")
        assert d == datetime.date(2024, 5, 15)

    def test_bos_string_none(self, parse_date):
        assert parse_date("") is None

    def test_none_str_none(self, parse_date):
        assert parse_date("None") is None

    def test_sadece_bosluk_none(self, parse_date):
        assert parse_date("   ") is None

    def test_gecersiz_format_none(self, parse_date):
        assert parse_date("bu-tarih-degil") is None

    def test_yanlis_tarih_none(self, parse_date):
        assert parse_date("2024-13-45") is None

    def test_date_objesi_donus(self, parse_date):
        d = parse_date("2024-01-01")
        assert isinstance(d, datetime.date)

    def test_aralik_31(self, parse_date):
        d = parse_date("2024-12-31")
        assert d == datetime.date(2024, 12, 31)

    def test_artik_yil_subat_29(self, parse_date):
        d = parse_date("2024-02-29")
        assert d == datetime.date(2024, 2, 29)

    def test_artik_olmayan_subat_29_none(self, parse_date):
        """2023 artık yıl değil, 29 Şubat yok."""
        assert parse_date("2023-02-29") is None


# ════════════════════════════════════════════════════════════
#  4. _parse_date — fhsz_yonetim.py
# ════════════════════════════════════════════════════════════

class TestParseDateFhsz:
    """
    fhsz_yonetim.py içindeki _parse_date datetime objesi döner
    (izin_giris.py'den farklı olarak date değil datetime).
    """

    @pytest.fixture
    def parse_date(self):
        from ui.pages.personel.fhsz_yonetim import _parse_date
        return _parse_date

    def test_yyyy_mm_dd_datetime(self, parse_date):
        d = parse_date("2024-05-15")
        assert isinstance(d, datetime.datetime)
        assert d.year == 2024 and d.month == 5 and d.day == 15

    def test_bos_none(self, parse_date):
        assert parse_date("") is None

    def test_gecersiz_none(self, parse_date):
        assert parse_date("xyz") is None

    def test_dd_mm_yyyy(self, parse_date):
        d = parse_date("15.05.2024")
        assert d is not None
        assert d.month == 5


# ════════════════════════════════════════════════════════════
#  5. İzin Tipleri Sabitleri
# ════════════════════════════════════════════════════════════

class TestIzinTipleri:

    def test_izin_tipleri_list(self):
        from ui.pages.personel.izin_giris import IZIN_TIPLERI
        assert isinstance(IZIN_TIPLERI, list)
        assert len(IZIN_TIPLERI) > 0

    def test_yillik_izin_var(self):
        from ui.pages.personel.izin_giris import IZIN_TIPLERI
        assert "Yıllık İzin" in IZIN_TIPLERI

    def test_sua_izni_var(self):
        from ui.pages.personel.izin_giris import IZIN_TIPLERI
        assert "Şua İzni" in IZIN_TIPLERI

    def test_mazeret_izni_var(self):
        from ui.pages.personel.izin_giris import IZIN_TIPLERI
        assert "Mazeret İzni" in IZIN_TIPLERI

    def test_tiplerde_tekrar_yok(self):
        from ui.pages.personel.izin_giris import IZIN_TIPLERI
        assert len(IZIN_TIPLERI) == len(set(IZIN_TIPLERI))

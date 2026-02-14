# -*- coding: utf-8 -*-
"""
test_log_goruntuleme.py
========================
LogGoruntuleme sayfasi ve yardimci siniflar icin unit testleri

Kapsam:
  1. Seviye tespiti       — log satirindan seviye ayrıstırma
  2. Arama filtresi       — metin eslesmesi
  3. Seviye filtresi      — INFO / WARNING / ERROR satirlari
  4. Dosya meta           — boyut formatlamasi
  5. Klasor yoksa         — bos icerik donmesi
  6. Qt sayfa             — widget varligi, baslangic durumu
  7. Qt etkileşim         — seviye butonlari, canli takip
"""
import sys
import os
import tempfile
import pytest


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication(sys.argv)


# ─── Test icin gercek log satirlari ────────────────────────────
SATIR_INFO    = "2025-02-13 10:00:01,123 - INFO - Uygulama basladi"
SATIR_WARNING = "2025-02-13 10:00:02,456 - WARNING - Bellek dusuk"
SATIR_ERROR   = "2025-02-13 10:00:03,789 - ERROR - Baglanti kesildi"
SATIR_DEBUG   = "2025-02-13 10:00:04,000 - DEBUG - Cache temizlendi"
SATIR_SYNC    = "2025-02-13 10:00:05,111 - INFO - Personel sync tamamlandi"

TUM_SATIRLAR = [
    SATIR_INFO    + "\n",
    SATIR_WARNING + "\n",
    SATIR_ERROR   + "\n",
    SATIR_DEBUG   + "\n",
    SATIR_SYNC    + "\n",
]


# ─── Saf Python yardimci fonksiyonlar (Qt olmadan test) ───────

def _seviye_bul(satir: str) -> str:
    for s in ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"):
        if f" - {s} - " in satir or f" - {s}:" in satir:
            return s
    return "DEFAULT"


def _filtrele(satirlar: list, seviye: str, arama: str = "") -> list:
    sonuc = []
    for s in satirlar:
        if seviye != "TUMÜ" and seviye != "TÜMÜ":
            if f" - {seviye} - " not in s and f" - {seviye}:" not in s:
                continue
        if arama and arama.lower() not in s.lower():
            continue
        sonuc.append(s)
    return sonuc


def _boyut_formatla(boyut_bytes: int) -> str:
    if boyut_bytes < 1024:
        return f"{boyut_bytes} B"
    elif boyut_bytes < 1024 * 1024:
        return f"{boyut_bytes / 1024:.1f} KB"
    else:
        return f"{boyut_bytes / 1024 / 1024:.1f} MB"


# =============================================================
#  1. Seviye Tespiti
# =============================================================
class TestSeviyeTespiti:

    def test_info_tespiti(self):
        assert _seviye_bul(SATIR_INFO) == "INFO"

    def test_warning_tespiti(self):
        assert _seviye_bul(SATIR_WARNING) == "WARNING"

    def test_error_tespiti(self):
        assert _seviye_bul(SATIR_ERROR) == "ERROR"

    def test_debug_tespiti(self):
        assert _seviye_bul(SATIR_DEBUG) == "DEBUG"

    def test_sync_info_tespiti(self):
        assert _seviye_bul(SATIR_SYNC) == "INFO"

    def test_bos_satir_default(self):
        assert _seviye_bul("") == "DEFAULT"

    def test_formatsiz_satir_default(self):
        assert _seviye_bul("sadece metin") == "DEFAULT"

    def test_critical_tespiti(self):
        satir = "2025-01-01 - CRITICAL - Sistem cataliyor"
        assert _seviye_bul(satir) == "CRITICAL"


# =============================================================
#  2. Arama Filtresi
# =============================================================
class TestAramaFiltresi:

    def test_eslesen_satirlar_donuyor(self):
        sonuc = _filtrele(TUM_SATIRLAR, "TÜMÜ", "basladi")
        assert len(sonuc) == 1
        assert SATIR_INFO + "\n" in sonuc

    def test_eslesen_yok_bos_liste(self):
        sonuc = _filtrele(TUM_SATIRLAR, "TÜMÜ", "bulunmayan_kelime_xyz")
        assert sonuc == []

    def test_bos_arama_tumunu_verir(self):
        sonuc = _filtrele(TUM_SATIRLAR, "TÜMÜ", "")
        assert len(sonuc) == len(TUM_SATIRLAR)

    def test_kucuk_buyuk_harf_duyarsiz(self):
        sonuc_kucuk = _filtrele(TUM_SATIRLAR, "TÜMÜ", "baglanti")
        sonuc_buyuk = _filtrele(TUM_SATIRLAR, "TÜMÜ", "BAGLANTI")
        assert len(sonuc_kucuk) == len(sonuc_buyuk)

    def test_kısmi_esleme(self):
        sonuc = _filtrele(TUM_SATIRLAR, "TÜMÜ", "sync")
        assert any("sync" in s.lower() for s in sonuc)


# =============================================================
#  3. Seviye Filtresi
# =============================================================
class TestSeviyeFiltresi:

    def test_sadece_error_satirlari(self):
        sonuc = _filtrele(TUM_SATIRLAR, "ERROR")
        assert all(" - ERROR - " in s or " - ERROR:" in s for s in sonuc)
        assert len(sonuc) == 1

    def test_sadece_warning_satirlari(self):
        sonuc = _filtrele(TUM_SATIRLAR, "WARNING")
        assert len(sonuc) == 1
        assert SATIR_WARNING + "\n" in sonuc

    def test_sadece_info_satirlari(self):
        sonuc = _filtrele(TUM_SATIRLAR, "INFO")
        # SATIR_INFO ve SATIR_SYNC
        assert len(sonuc) == 2

    def test_sadece_debug_satirlari(self):
        sonuc = _filtrele(TUM_SATIRLAR, "DEBUG")
        assert len(sonuc) == 1

    def test_tumu_tum_satirlari_verir(self):
        sonuc = _filtrele(TUM_SATIRLAR, "TÜMÜ")
        assert len(sonuc) == len(TUM_SATIRLAR)

    def test_kombinasyon_error_ve_arama(self):
        sonuc = _filtrele(TUM_SATIRLAR, "ERROR", "baglanti")
        assert len(sonuc) == 1

    def test_kombinasyon_info_ve_sync(self):
        sonuc = _filtrele(TUM_SATIRLAR, "INFO", "sync")
        assert len(sonuc) == 1

    def test_bulunamayan_seviye_bos_liste(self):
        sonuc = _filtrele(TUM_SATIRLAR, "CRITICAL")
        assert sonuc == []


# =============================================================
#  4. Dosya Meta Bilgileri
# =============================================================
class TestDosyaMeta:

    def test_byte_formatlamasi(self):
        assert _boyut_formatla(512) == "512 B"

    def test_kb_formatlamasi(self):
        assert "KB" in _boyut_formatla(2048)

    def test_mb_formatlamasi(self):
        assert "MB" in _boyut_formatla(5 * 1024 * 1024)

    def test_tam_sinir_1kb(self):
        assert "KB" in _boyut_formatla(1024)

    def test_tam_sinir_1mb(self):
        assert "MB" in _boyut_formatla(1024 * 1024)

    def test_sifir_byte(self):
        assert _boyut_formatla(0) == "0 B"


# =============================================================
#  5. LogOkuyucuThread — Dosya Okuma
# =============================================================
class TestLogOkuyucu:

    def test_var_olan_dosya_okunuyor(self):
        from ui.pages.admin.log_goruntuleme import LogOkuyucuThread
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".log", delete=False, encoding="utf-8"
        ) as f:
            f.write("".join(TUM_SATIRLAR))
            yol = f.name
        try:
            sonuc = {"icerik": None, "meta": None}
            thread = LogOkuyucuThread(yol)
            thread.veri_hazir.connect(lambda ic, m: sonuc.update({"icerik": ic, "meta": m}))
            thread.run()  # Dogrudan calistir (thread olmadan)
            assert sonuc["icerik"] is not None
            assert "INFO" in sonuc["icerik"]
        finally:
            os.unlink(yol)

    def test_olmayan_dosya_bos_icerik(self):
        from ui.pages.admin.log_goruntuleme import LogOkuyucuThread
        sonuc = {"icerik": None, "meta": None}
        thread = LogOkuyucuThread("/olmayan/yol/dosya.log")
        thread.veri_hazir.connect(lambda ic, m: sonuc.update({"icerik": ic, "meta": m}))
        thread.run()
        assert sonuc["icerik"] == ""
        assert sonuc["meta"]["boyut"] == 0

    def test_meta_alanlar_mevcut(self):
        from ui.pages.admin.log_goruntuleme import LogOkuyucuThread
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".log", delete=False, encoding="utf-8"
        ) as f:
            f.write(SATIR_INFO + "\n")
            yol = f.name
        try:
            meta_al = {}
            thread = LogOkuyucuThread(yol)
            thread.veri_hazir.connect(lambda ic, m: meta_al.update(m))
            thread.run()
            for alan in ["boyut", "satirlar", "son_guncelleme", "mtime"]:
                assert alan in meta_al, f"{alan} meta'da eksik"
        finally:
            os.unlink(yol)

    def test_max_satir_siniri(self):
        from ui.pages.admin.log_goruntuleme import LogOkuyucuThread
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".log", delete=False, encoding="utf-8"
        ) as f:
            for i in range(100):
                f.write(f"2025-01-01 - INFO - Satir {i}\n")
            yol = f.name
        try:
            meta_al = {}
            thread = LogOkuyucuThread(yol, max_satir=50)
            thread.veri_hazir.connect(lambda ic, m: meta_al.update(m))
            thread.run()
            assert meta_al.get("gosterilen", 100) <= 50
        finally:
            os.unlink(yol)


# =============================================================
#  6. Qt Sayfa — Widget Varligi ve Baslangic Durumu
# =============================================================
class TestLogGoruntulemePageQt:

    def test_sayfa_olusturuluyor(self, qapp):
        from ui.pages.admin.log_goruntuleme import LogGoruntuleme
        page = LogGoruntuleme()
        assert page is not None

    def test_cmb_dosya_var(self, qapp):
        from ui.pages.admin.log_goruntuleme import LogGoruntuleme
        page = LogGoruntuleme()
        assert hasattr(page, "_cmb_dosya")

    def test_txt_arama_var(self, qapp):
        from ui.pages.admin.log_goruntuleme import LogGoruntuleme
        page = LogGoruntuleme()
        assert hasattr(page, "_txt_arama")

    def test_txt_log_alani_var(self, qapp):
        from ui.pages.admin.log_goruntuleme import LogGoruntuleme
        page = LogGoruntuleme()
        assert hasattr(page, "_txt")

    def test_txt_readonly(self, qapp):
        from ui.pages.admin.log_goruntuleme import LogGoruntuleme
        page = LogGoruntuleme()
        assert page._txt.isReadOnly()

    def test_btn_yenile_var(self, qapp):
        from ui.pages.admin.log_goruntuleme import LogGoruntuleme
        page = LogGoruntuleme()
        assert hasattr(page, "_btn_yenile")

    def test_btn_klasor_var(self, qapp):
        from ui.pages.admin.log_goruntuleme import LogGoruntuleme
        page = LogGoruntuleme()
        assert hasattr(page, "_btn_klasor")

    def test_chk_canli_baslangicta_isaretli(self, qapp):
        from ui.pages.admin.log_goruntuleme import LogGoruntuleme
        page = LogGoruntuleme()
        assert page._chk_canli.isChecked()

    def test_seviye_butonlari_var(self, qapp):
        from ui.pages.admin.log_goruntuleme import LogGoruntuleme
        page = LogGoruntuleme()
        assert hasattr(page, "_seviye_butonlari")
        assert len(page._seviye_butonlari) == 5  # TÜMÜ DEBUG INFO WARNING ERROR

    def test_lbl_filtre_var(self, qapp):
        from ui.pages.admin.log_goruntuleme import LogGoruntuleme
        page = LogGoruntuleme()
        assert hasattr(page, "_lbl_filtre")


# =============================================================
#  7. Qt Etkilesim — Seviye ve Canli Takip
# =============================================================
class TestLogGoruntulemeEtkilesimQt:

    def test_tuumu_butonu_baslangicta_secili(self, qapp):
        from ui.pages.admin.log_goruntuleme import LogGoruntuleme
        page = LogGoruntuleme()
        assert page._seviye_butonlari["TÜMÜ"].isChecked()

    def test_seviye_secince_diger_butonlar_kalkiyor(self, qapp):
        from ui.pages.admin.log_goruntuleme import LogGoruntuleme
        page = LogGoruntuleme()
        page._seviye_sec("ERROR")
        assert page._seviye_butonlari["ERROR"].isChecked()
        assert not page._seviye_butonlari["TÜMÜ"].isChecked()
        assert not page._seviye_butonlari["INFO"].isChecked()

    def test_seviye_tumüye_donunce_diger_kalkiyor(self, qapp):
        from ui.pages.admin.log_goruntuleme import LogGoruntuleme
        page = LogGoruntuleme()
        page._seviye_sec("WARNING")
        page._seviye_sec("TÜMÜ")
        assert page._seviye_butonlari["TÜMÜ"].isChecked()
        assert not page._seviye_butonlari["WARNING"].isChecked()

    def test_canli_takip_kapaninca_timer_duruyor(self, qapp):
        from ui.pages.admin.log_goruntuleme import LogGoruntuleme
        page = LogGoruntuleme()
        page._chk_canli.setChecked(False)
        assert not page._timer.isActive()

    def test_canli_takip_acilinca_timer_basliyor(self, qapp):
        from ui.pages.admin.log_goruntuleme import LogGoruntuleme
        page = LogGoruntuleme()
        page._chk_canli.setChecked(False)
        page._chk_canli.setChecked(True)
        assert page._timer.isActive()

    def test_seviye_degisince_property_guncelleniyor(self, qapp):
        from ui.pages.admin.log_goruntuleme import LogGoruntuleme
        page = LogGoruntuleme()
        page._seviye_sec("ERROR")
        assert page._seviye == "ERROR"

    def test_highlighter_bagli(self, qapp):
        from ui.pages.admin.log_goruntuleme import LogGoruntuleme
        page = LogGoruntuleme()
        assert page._highlighter is not None

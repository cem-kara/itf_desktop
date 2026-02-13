# -*- coding: utf-8 -*-
"""
core/hesaplamalar.py için unit testler
======================================
Kapsam:
  - tr_upper             : Türkçe karakter dönüşümü
  - sua_hak_edis_hesapla : FHSZ yönetmeliği hak ediş tablosu
  - is_gunu_hesapla      : İki tarih arası iş günü
  - ay_is_gunu           : Aylık iş günü

Çalıştır:
  pytest tests/test_hesaplamalar.py -v
  pytest tests/test_hesaplamalar.py -v --tb=short
"""

import sys
import os
import pytest
from datetime import date

# Proje kökünü path'e ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.hesaplamalar import (
    tr_upper,
    sua_hak_edis_hesapla,
    is_gunu_hesapla,
    ay_is_gunu,
)


# ══════════════════════════════════════════════════════════════
# tr_upper
# ══════════════════════════════════════════════════════════════

class TestTrUpper:
    """Türkçe büyük harf dönüşümü testleri."""

    def test_noktalı_i_buyuk_harf(self):
        """'i' → 'İ' (noktalı i büyük harf)"""
        assert tr_upper("istanbul") == "İSTANBUL"

    def test_noktasiz_i_buyuk_harf(self):
        """'ı' → 'I' (noktasız ı büyük harf)"""
        assert tr_upper("ıspanak") == "ISPANAK"

    def test_yumusak_g(self):
        """'ğ' → 'Ğ'"""
        assert tr_upper("yağmur") == "YAĞMUR"

    def test_u_umlauti(self):
        """'ü' → 'Ü'"""
        assert tr_upper("üzüm") == "ÜZÜM"

    def test_s_cedilla(self):
        """'ş' → 'Ş'"""
        assert tr_upper("şeker") == "ŞEKER"

    def test_o_umlauti(self):
        """'ö' → 'Ö'"""
        assert tr_upper("öğrenci") == "ÖĞRENCİ"

    def test_c_cedilla(self):
        """'ç' → 'Ç'"""
        assert tr_upper("çiçek") == "ÇİÇEK"

    def test_tum_turkce_karakterler_bir_arada(self):
        """Tüm Türkçe özel karakterlerin aynı string içinde doğru dönüşümü."""
        assert tr_upper("ışığı çöğ üş") == "IŞIĞI ÇÖĞ ÜŞ"

    def test_latin_karakterler_degismez(self):
        """ASCII harfler standart upper() gibi çalışır."""
        assert tr_upper("hello world") == "HELLO WORLD"

    def test_zaten_buyuk_harf(self):
        """Zaten büyük harfli string aynı kalır."""
        assert tr_upper("ANKARA") == "ANKARA"

    def test_bos_string(self):
        """Boş string boş string döner."""
        assert tr_upper("") == ""

    def test_rakamlar_ve_semboller(self):
        """Rakamlar ve özel semboller değişmeden geçer."""
        assert tr_upper("abc123!@#") == "ABC123!@#"

    def test_int_girdi(self):
        """int girildiğinde str'e çevirip upper() uygular."""
        assert tr_upper(42) == "42"

    def test_float_girdi(self):
        """float girildiğinde str'e çevirip upper() uygular."""
        result = tr_upper(3.14)
        assert result == "3.14"

    def test_none_girdi(self):
        """None girildiğinde str(None).upper() = 'NONE' döner."""
        assert tr_upper(None) == "NONE"

    def test_liste_girdi(self):
        """Liste girildiğinde str(list).upper() döner, hata vermez."""
        result = tr_upper([1, 2])
        assert isinstance(result, str)

    def test_kisim_turkce_kisim_latin(self):
        """Karma Türkçe/Latin kelimeler doğru dönüşür."""
        assert tr_upper("İstanbul city") == "İSTANBUL CİTY"


# ══════════════════════════════════════════════════════════════
# sua_hak_edis_hesapla
# ══════════════════════════════════════════════════════════════

class TestSuaHakEdisHesapla:
    """
    FHSZ yönetmeliği tablosuna göre hak ediş günü testleri.

    Tablo özeti:
      0 saat        → 0 gün
      50-99 saat    → 1 gün
      100-149 saat  → 2 gün
      ...
      950-999 saat  → 19 gün
      1000-1099     → 20 gün
      1100-1199     → 25 gün  (büyük atlama: 21-24 gün yok)
      1200-1299     → 26 gün
      1300-1399     → 28 gün  (27 gün tablodan dışarıda)
      1400-1449     → 29 gün
      1450+         → 30 gün  (tavan)
    """

    # ── Sıfır ve negatif ──────────────────────────────────────

    def test_sifir_saat(self):
        assert sua_hak_edis_hesapla(0) == 0

    def test_negatif_saat(self):
        """Negatif saat → 0 gün (herhangi bir haktan aşağıda)."""
        assert sua_hak_edis_hesapla(-1) == 0
        assert sua_hak_edis_hesapla(-999) == 0

    def test_sifirdan_kucuk_kesirliler(self):
        assert sua_hak_edis_hesapla(-0.1) == 0

    # ── İlk eşik ─────────────────────────────────────────────

    def test_50_saatten_az(self):
        """49 saat → hak kazanılmamış (0 gün)."""
        assert sua_hak_edis_hesapla(49) == 0
        assert sua_hak_edis_hesapla(49.9) == 0

    def test_50_saat_tam_esik(self):
        """50 saat tam eşiği → 1 gün."""
        assert sua_hak_edis_hesapla(50) == 1

    def test_50_99_arasi(self):
        """50-99 arası → 1 gün."""
        assert sua_hak_edis_hesapla(75) == 1
        assert sua_hak_edis_hesapla(99) == 1
        assert sua_hak_edis_hesapla(99.9) == 1

    # ── 50'şer artış bölgesi (0-1000 saat) ───────────────────

    @pytest.mark.parametrize("saat,beklenen_gun", [
        (100,  2), (150,  3), (200,  4), (250,  5),
        (300,  6), (350,  7), (400,  8), (450,  9),
        (500, 10), (550, 11), (600, 12), (650, 13),
        (700, 14), (750, 15), (800, 16), (850, 17),
        (900, 18), (950, 19), (1000, 20),
    ])
    def test_esik_degerleri(self, saat, beklenen_gun):
        """Her eşik noktasının tam üstündeki değer doğru gün döndürür."""
        assert sua_hak_edis_hesapla(saat) == beklenen_gun

    @pytest.mark.parametrize("saat,beklenen_gun", [
        (99.9,  1), (149.9,  2), (199.9,  3), (249.9,  4),
        (299.9, 5), (349.9,  6), (399.9,  7), (449.9,  8),
        (499.9, 9), (549.9, 10), (599.9, 11), (649.9, 12),
        (699.9, 13), (749.9, 14), (799.9, 15), (849.9, 16),
        (899.9, 17), (949.9, 18), (999.9, 19),
    ])
    def test_esik_altlari(self, saat, beklenen_gun):
        """Her eşiğin hemen altı bir önceki gün sayısını döndürür."""
        assert sua_hak_edis_hesapla(saat) == beklenen_gun

    # ── 1000 saat sonrası düzensiz artışlar ───────────────────

    def test_1000_1099_arasi(self):
        """1000-1099 arası → 20 gün."""
        assert sua_hak_edis_hesapla(1000) == 20
        assert sua_hak_edis_hesapla(1050) == 20
        assert sua_hak_edis_hesapla(1099) == 20
        assert sua_hak_edis_hesapla(1099.9) == 20

    def test_1100_buyuk_atlama(self):
        """
        1100 saatte 21→25 büyük atlaması: 21, 22, 23, 24 günler yoktur.
        Tablodaki düzensiz artışın korunduğunu doğrular.
        """
        assert sua_hak_edis_hesapla(1099.9) == 20
        assert sua_hak_edis_hesapla(1100) == 25  # ← 4 gün atlama

    def test_1100_1199_arasi(self):
        """1100-1199 arası → 25 gün."""
        assert sua_hak_edis_hesapla(1100) == 25
        assert sua_hak_edis_hesapla(1150) == 25
        assert sua_hak_edis_hesapla(1199.9) == 25

    def test_1200_1299_arasi(self):
        """1200-1299 arası → 26 gün (27 gün tablodan dışarıda)."""
        assert sua_hak_edis_hesapla(1200) == 26
        assert sua_hak_edis_hesapla(1250) == 26
        assert sua_hak_edis_hesapla(1299.9) == 26

    def test_27_gun_yoktur(self):
        """
        Yönetmelik tablosunda 27 gün yoktur.
        1299 saat → 26 gün, 1300 saat → 28 gün (27 atlanır).
        """
        assert sua_hak_edis_hesapla(1299.9) == 26
        assert sua_hak_edis_hesapla(1300) == 28

    def test_1300_1399_arasi(self):
        """1300-1399 arası → 28 gün."""
        assert sua_hak_edis_hesapla(1300) == 28
        assert sua_hak_edis_hesapla(1350) == 28
        assert sua_hak_edis_hesapla(1399.9) == 28

    def test_1400_1449_arasi(self):
        """1400-1449 arası → 29 gün."""
        assert sua_hak_edis_hesapla(1400) == 29
        assert sua_hak_edis_hesapla(1425) == 29
        assert sua_hak_edis_hesapla(1449.9) == 29

    # ── Tavan ─────────────────────────────────────────────────

    def test_1450_tavan(self):
        """1450 saat → 30 gün (maksimum)."""
        assert sua_hak_edis_hesapla(1450) == 30

    def test_1450_ustu_hep_30(self):
        """1450 saatin üzerindeki her değer tavanı (30) döndürür."""
        assert sua_hak_edis_hesapla(1451) == 30
        assert sua_hak_edis_hesapla(2000) == 30
        assert sua_hak_edis_hesapla(9999) == 30

    # ── Girdi türleri ─────────────────────────────────────────

    def test_string_sayi_kabul_edilir(self):
        """Sayısal string → float'a çevrilir, hata vermez."""
        assert sua_hak_edis_hesapla("500") == 10
        assert sua_hak_edis_hesapla("1100") == 25

    def test_string_ondalikli(self):
        """Ondalıklı string → doğru hesaplanır."""
        assert sua_hak_edis_hesapla("50.0") == 1

    def test_float_girdi(self):
        """Float girdi → doğru hesaplanır."""
        assert sua_hak_edis_hesapla(50.0) == 1
        assert sua_hak_edis_hesapla(499.5) == 9

    def test_gecersiz_string(self):
        """Sayısal olmayan string → 0 döner, exception atmaz."""
        assert sua_hak_edis_hesapla("abc") == 0
        assert sua_hak_edis_hesapla("") == 0
        assert sua_hak_edis_hesapla("--") == 0

    def test_none_girdi(self):
        """None → 0 döner, exception atmaz."""
        assert sua_hak_edis_hesapla(None) == 0

    def test_liste_girdi(self):
        """Liste → 0 döner, exception atmaz."""
        assert sua_hak_edis_hesapla([500]) == 0

    def test_boolean_girdi(self):
        """True=1.0, False=0.0 olarak işlenir (Python bool is int)."""
        assert sua_hak_edis_hesapla(True) == 0   # 1.0 → 0 gün
        assert sua_hak_edis_hesapla(False) == 0  # 0.0 → 0 gün


# ══════════════════════════════════════════════════════════════
# is_gunu_hesapla
# ══════════════════════════════════════════════════════════════

class TestIsGunuHesapla:
    """
    İki tarih arasındaki iş günü hesabı testleri.
    Referans: Ocak 2024 → 1 Ocak Pazartesi
    """

    # ── Tek gün ───────────────────────────────────────────────

    def test_tek_gun_pazartesi(self):
        """Pazartesi günü aralığı → 1 iş günü."""
        assert is_gunu_hesapla(date(2024, 1, 1), date(2024, 1, 1)) == 1

    def test_tek_gun_cumartesi(self):
        """Cumartesi günü aralığı → 0 iş günü."""
        assert is_gunu_hesapla(date(2024, 1, 6), date(2024, 1, 6)) == 0

    def test_tek_gun_pazar(self):
        """Pazar günü aralığı → 0 iş günü."""
        assert is_gunu_hesapla(date(2024, 1, 7), date(2024, 1, 7)) == 0

    # ── Tam iş haftası ────────────────────────────────────────

    def test_tam_is_haftasi(self):
        """Pazartesi→Cuma = 5 iş günü."""
        assert is_gunu_hesapla(date(2024, 1, 1), date(2024, 1, 5)) == 5

    def test_haftasonu_dahil_yedi_gun(self):
        """Pazartesi→Pazar = 7 takvim günü = 5 iş günü."""
        assert is_gunu_hesapla(date(2024, 1, 1), date(2024, 1, 7)) == 5

    def test_iki_tam_hafta(self):
        """Pazartesi→Cuma (2 hafta) = 10 iş günü."""
        assert is_gunu_hesapla(date(2024, 1, 1), date(2024, 1, 12)) == 10

    # ── Hafta sonu aralıkları ─────────────────────────────────

    def test_tam_hafta_sonu(self):
        """Cumartesi→Pazar = 0 iş günü."""
        assert is_gunu_hesapla(date(2024, 1, 6), date(2024, 1, 7)) == 0

    def test_cuma_pazartesi(self):
        """Cuma→Pazartesi = 4 takvim günü = 2 iş günü (Cuma + Pazartesi)."""
        assert is_gunu_hesapla(date(2024, 1, 5), date(2024, 1, 8)) == 2

    # ── Tatil listesi ─────────────────────────────────────────

    def test_pazartesi_tatil(self):
        """Pazartesi→Cuma, Pazartesi tatil → 4 iş günü."""
        assert is_gunu_hesapla(
            date(2024, 1, 1), date(2024, 1, 5),
            tatil_listesi=['2024-01-01']
        ) == 4

    def test_tatil_hafta_sonuna_denk_gelirse_etki_yok(self):
        """Cumartesiye denk gelen tatil iş günü sayısını etkilemez."""
        assert is_gunu_hesapla(
            date(2024, 1, 1), date(2024, 1, 5),
            tatil_listesi=['2024-01-06']  # Cumartesi
        ) == 5

    def test_birden_fazla_tatil(self):
        """2 tatil günü → 5 iş gününden 2 düşülür = 3."""
        assert is_gunu_hesapla(
            date(2024, 1, 1), date(2024, 1, 5),
            tatil_listesi=['2024-01-01', '2024-01-02']
        ) == 3

    def test_ayni_gune_iki_tatil_bir_dusulur(self):
        """
        Aynı tarihe iki farklı tatil düşerse (örn. Ramazan + 23 Nisan)
        numpy.busday_count yalnızca 1 iş günü düşer.
        """
        assert is_gunu_hesapla(
            date(2024, 4, 22), date(2024, 4, 26),
            tatil_listesi=['2024-04-23', '2024-04-23']
        ) == 4  # 5 gün - 1 tatil

    def test_bos_tatil_listesi(self):
        """Boş tatil listesi → normal hesap."""
        assert is_gunu_hesapla(
            date(2024, 1, 1), date(2024, 1, 5),
            tatil_listesi=[]
        ) == 5

    def test_tatil_listesi_none(self):
        """tatil_listesi=None → varsayılan boş liste gibi çalışır."""
        assert is_gunu_hesapla(
            date(2024, 1, 1), date(2024, 1, 5),
            tatil_listesi=None
        ) == 5

    # ── Ay/yıl sınırları ─────────────────────────────────────

    def test_ay_sonu_gecisi(self):
        """Ay sonu geçişi hesaba dahil edilir (Ocak 31 → Şubat 2)."""
        # 31 Ocak Çarşamba → 2 Şubat Cuma = 3 iş günü
        assert is_gunu_hesapla(date(2024, 1, 31), date(2024, 2, 2)) == 3

    def test_yil_sonu_gecisi(self):
        """Yıl sonu geçişi doğru hesaplanır (28 Ara Pzt → 3 Oca Prş)."""
        # 30 Ara 2024 Pzt → 3 Oca 2025 Cuma = 7 iş günü
        assert is_gunu_hesapla(date(2024, 12, 30), date(2025, 1, 3)) == 5

    # ── Negatif / ters aralık ─────────────────────────────────

    def test_baslangic_bitis_sonra(self):
        """
        Başlangıç > bitiş → negatif iş günü döner.
        Bu numpy.busday_count'un doğal davranışıdır.
        Çağıran kodun tarihleri doğru sıraladığı varsayılır.
        """
        result = is_gunu_hesapla(date(2024, 1, 5), date(2024, 1, 1))
        assert result < 0

    # ── Gerçek dünya senaryoları ──────────────────────────────

    def test_cumhuriyet_bayrami_haftasi(self):
        """
        28 Eki 2024 (Pzt) → 1 Kas 2024 (Cuma) = 5 iş günü
        29 Ekim tatil → 4 iş günü.
        """
        assert is_gunu_hesapla(
            date(2024, 10, 28), date(2024, 11, 1),
            tatil_listesi=['2024-10-29']
        ) == 4

    def test_uzun_tatil_dizisi(self):
        """
        Ramazan Bayramı: 3 günlük tatil bloku.
        Tatil haftaiçine denk gelirse tam 3 gün düşülür.
        """
        # 10-14 Mart 2024 Pzt-Cum = 5 gün,
        # 11-12-13 Mart tatil = 3 gün düşülür → 2 iş günü
        assert is_gunu_hesapla(
            date(2024, 3, 11), date(2024, 3, 15),
            tatil_listesi=['2024-03-11', '2024-03-12', '2024-03-13']
        ) == 2


# ══════════════════════════════════════════════════════════════
# ay_is_gunu
# ══════════════════════════════════════════════════════════════

class TestAyIsGunu:
    """
    Belirli bir ay+yıl'daki toplam iş günü testleri.
    Referans değerler numpy.busday_count ile hesaplanmıştır.
    """

    def test_ocak_2024(self):
        """Ocak 2024: 31 gün, 8 hafta sonu = 23 iş günü."""
        assert ay_is_gunu(2024, 1) == 23

    def test_subat_2024_artik_yil(self):
        """Şubat 2024 (artık yıl, 29 gün): 8 hafta sonu = 21 iş günü."""
        assert ay_is_gunu(2024, 2) == 21

    def test_subat_2023_artik_olmayan(self):
        """Şubat 2023 (artık değil, 28 gün): 8 hafta sonu = 20 iş günü."""
        assert ay_is_gunu(2023, 2) == 20

    def test_nisan_2024(self):
        """Nisan 2024: 30 gün = 22 iş günü."""
        assert ay_is_gunu(2024, 4) == 22

    def test_aralik_2024(self):
        """Aralık 2024: 31 gün = 22 iş günü."""
        assert ay_is_gunu(2024, 12) == 22

    def test_ocak_tatil_ile(self):
        """Ocak 2024, 1 Ocak (Pzt) tatil → 22 iş günü."""
        assert ay_is_gunu(2024, 1, tatil_listesi=['2024-01-01']) == 22

    def test_tatil_hafta_sonuna_denk(self):
        """6 Ocak 2024 Cumartesi tatil → iş günü sayısı değişmez (23)."""
        assert ay_is_gunu(2024, 1, tatil_listesi=['2024-01-06']) == 23

    def test_iki_tatil_ayni_ay(self):
        """Ocak 2024, iki hafta içi tatil → 21 iş günü."""
        assert ay_is_gunu(
            2024, 1,
            tatil_listesi=['2024-01-01', '2024-01-02']
        ) == 21

    def test_bos_tatil_listesi(self):
        """Boş tatil listesi → tatilsiz hesap ile aynı sonuç."""
        assert ay_is_gunu(2024, 1, tatil_listesi=[]) == 23

    def test_tatil_listesi_none(self):
        """tatil_listesi=None → boş liste gibi davranır."""
        assert ay_is_gunu(2024, 1, tatil_listesi=None) == 23

    @pytest.mark.parametrize("yil,ay,beklenen", [
        (2024, 1,  23),
        (2024, 2,  21),
        (2024, 3,  21),
        (2024, 4,  22),
        (2024, 5,  23),
        (2024, 6,  20),
        (2024, 7,  23),
        (2024, 8,  22),
        (2024, 9,  21),
        (2024, 10, 23),
        (2024, 11, 21),
        (2024, 12, 22),
    ])
    def test_2024_tum_aylar(self, yil, ay, beklenen):
        """2024'teki 12 ayın iş günü sayısı (tatilsiz)."""
        assert ay_is_gunu(yil, ay) == beklenen

    def test_artik_yil_vs_normal_subat(self):
        """Artık yıl Şubatı her zaman normal yıldan 1 iş günü fazladır (eğer 29. gün hafta içi düşüyorsa)."""
        artik = ay_is_gunu(2024, 2)   # 29 Şubat Perşembe → +1
        normal = ay_is_gunu(2023, 2)  # 28 gün
        assert artik > normal

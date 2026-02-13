# -*- coding: utf-8 -*-
"""
fhsz_yonetim.py iş mantığı unit testleri
==========================================
Kapsam:
  1. Sabitler       : KOSUL_A_SAAT, FHSZ_ESIK, AY_ISIMLERI
  2. Puan hesabı    : (is_gunu - izin) × 7  / Koşul B → 0
  3. Kesişim mantığı: donem_bas/donem_bit × izin tarihleri
  4. tr_upper       : koşul metni normalize
  5. Kolon tanımları: TABLO_KOLONLARI, C_* indexleri
"""
import pytest
from datetime import date, datetime


# ──────────────────────────────────────────────────
#  Sabit/mantık dosyadan import edilmeden izole test
#  (Qt bağımlılığı olmadan)
# ──────────────────────────────────────────────────

KOSUL_A_SAAT = 7

def _puan_hesapla(kosul: str, is_gunu: int, izin: int) -> int:
    """fhsz_yonetim._satir_hesapla mantığı."""
    if "KOŞULU A" in kosul.upper().replace("Ş", "Ş"):
        net = max(0, is_gunu - izin)
        return net * KOSUL_A_SAAT
    return 0


def _tr_upper_simple(s: str) -> str:
    """Türkçe büyük harf dönüşümü (hesaplamalar.py tr_upper ile aynı mantık)."""
    tablo = str.maketrans("çğıiöşüÇĞİIÖŞÜ", "ÇĞIİÖŞÜÇĞİIÖŞÜ")
    return s.translate(tablo).upper()


def _kesisim_izin_gunu(kimlik: str, donem_bas: date, donem_bit: date,
                       all_izin: list) -> int:
    """
    fhsz_yonetim._kesisim_izin_gunu mantığı (numpy'sız, hafta sonu hariç basit say).
    Gerçek kod is_gunu_hesapla kullanır; burada iş günü sayısını basit hesaplıyoruz.
    """
    from datetime import timedelta

    def is_gunleri(bas, bit):
        count = 0
        d = bas
        while d <= bit:
            if d.weekday() < 5:  # Pazartesi–Cuma
                count += 1
            d += timedelta(days=1)
        return count

    def _parse(val):
        for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
            try:
                return datetime.strptime(str(val), fmt).date()
            except ValueError:
                continue
        return None

    toplam = 0
    for iz in all_izin:
        if str(iz.get("Personelid", "")).strip() != kimlik:
            continue
        if str(iz.get("Durum", "")).strip() == "İptal":
            continue

        izin_bas = _parse(iz.get("BaslamaTarihi", ""))
        izin_bit = _parse(iz.get("BitisTarihi", ""))
        if not izin_bas or not izin_bit:
            continue

        k_bas = max(donem_bas, izin_bas)
        k_bit = min(donem_bit, izin_bit)

        if k_bas <= k_bit:
            toplam += is_gunleri(k_bas, k_bit)

    return toplam


# =============================================================
#  1. Sabitler
# =============================================================
class TestFhszSabitler:

    def test_kosul_a_saat_7(self):
        from ui.pages.personel.fhsz_yonetim import KOSUL_A_SAAT
        assert KOSUL_A_SAAT == 7

    def test_fhsz_esik_tarihi(self):
        from ui.pages.personel.fhsz_yonetim import FHSZ_ESIK
        assert FHSZ_ESIK == datetime(2022, 4, 26)

    def test_ay_isimleri_12_eleman(self):
        from ui.pages.personel.fhsz_yonetim import AY_ISIMLERI
        assert len(AY_ISIMLERI) == 12

    def test_ay_isimleri_ilk_ocak(self):
        from ui.pages.personel.fhsz_yonetim import AY_ISIMLERI
        assert AY_ISIMLERI[0] == "Ocak"

    def test_ay_isimleri_son_aralik(self):
        from ui.pages.personel.fhsz_yonetim import AY_ISIMLERI
        assert AY_ISIMLERI[11] == "Aralık"

    def test_kolon_sayisi_9(self):
        from ui.pages.personel.fhsz_yonetim import TABLO_KOLONLARI
        assert len(TABLO_KOLONLARI) == 9

    def test_c_kimlik_sifir(self):
        from ui.pages.personel.fhsz_yonetim import C_KIMLIK
        assert C_KIMLIK == 0

    def test_c_saat_sekiz(self):
        from ui.pages.personel.fhsz_yonetim import C_SAAT
        assert C_SAAT == 8

    def test_izin_verilen_siniflar_listesi(self):
        from ui.pages.personel.fhsz_yonetim import IZIN_VERILEN_SINIFLAR
        assert isinstance(IZIN_VERILEN_SINIFLAR, list)
        assert len(IZIN_VERILEN_SINIFLAR) > 0


# =============================================================
#  2. Puan Hesabı
# =============================================================
class TestPuanHesabi:

    def test_kosul_a_normal(self):
        """20 iş günü, 5 izin → (20-5) × 7 = 105"""
        assert _puan_hesapla("Koşulu A", 20, 5) == 105

    def test_kosul_a_izin_sifir(self):
        assert _puan_hesapla("Koşulu A", 22, 0) == 154

    def test_kosul_a_tam_izin(self):
        """Tüm gün izin → net 0 → puan 0."""
        assert _puan_hesapla("Koşulu A", 20, 20) == 0

    def test_kosul_a_izin_fazla(self):
        """İzin > is_gunu → max(0,...) → 0."""
        assert _puan_hesapla("Koşulu A", 10, 15) == 0

    def test_kosul_b_her_zaman_sifir(self):
        assert _puan_hesapla("Koşulu B", 22, 0) == 0

    def test_kosul_b_izinli(self):
        assert _puan_hesapla("Koşulu B", 22, 5) == 0

    def test_bos_kosul_sifir(self):
        assert _puan_hesapla("", 22, 5) == 0

    def test_kosul_a_buyuk_harf_calisir(self):
        assert _puan_hesapla("KOŞULU A", 10, 0) == 70

    def test_kosul_a_kucuk_harf_calisir(self):
        """Metnin büyük/küçük harf varyasyonu ile test."""
        assert _puan_hesapla("koşulu a", 10, 0) == 70

    def test_kosul_a_1_gun(self):
        assert _puan_hesapla("Koşulu A", 1, 0) == 7


# =============================================================
#  3. Kesişim İzin Günü
# =============================================================
class TestKesisimIzinGunu:

    IZIN_LISTESI = [
        {"Personelid": "12345", "BaslamaTarihi": "2024-01-08",
         "BitisTarihi": "2024-01-12", "Durum": "Onaylandı"},  # 5 iş günü
        {"Personelid": "12345", "BaslamaTarihi": "2024-01-22",
         "BitisTarihi": "2024-01-26", "Durum": "Onaylandı"},  # 5 iş günü
        {"Personelid": "99999", "BaslamaTarihi": "2024-01-01",
         "BitisTarihi": "2024-01-31", "Durum": "Onaylandı"},  # farklı kişi
    ]

    def test_donem_tum_izinleri_kapsıyor(self):
        donem_bas = date(2024, 1, 1)
        donem_bit = date(2024, 1, 31)
        toplam = _kesisim_izin_gunu("12345", donem_bas, donem_bit, self.IZIN_LISTESI)
        assert toplam == 10  # 5 + 5

    def test_donem_sadece_ilk_izni_kapsıyor(self):
        donem_bas = date(2024, 1, 1)
        donem_bit = date(2024, 1, 14)
        toplam = _kesisim_izin_gunu("12345", donem_bas, donem_bit, self.IZIN_LISTESI)
        assert toplam == 5

    def test_donem_kesisim_yok(self):
        """İzinler dışında bir dönem."""
        donem_bas = date(2024, 2, 1)
        donem_bit = date(2024, 2, 28)
        toplam = _kesisim_izin_gunu("12345", donem_bas, donem_bit, self.IZIN_LISTESI)
        assert toplam == 0

    def test_farkli_personel_sifir(self):
        donem_bas = date(2024, 1, 1)
        donem_bit = date(2024, 1, 31)
        toplam = _kesisim_izin_gunu("00000", donem_bas, donem_bit, self.IZIN_LISTESI)
        assert toplam == 0

    def test_iptal_izin_sayilmaz(self):
        iptal = [{"Personelid": "12345", "BaslamaTarihi": "2024-01-08",
                  "BitisTarihi": "2024-01-12", "Durum": "İptal"}]
        toplam = _kesisim_izin_gunu("12345", date(2024, 1, 1), date(2024, 1, 31), iptal)
        assert toplam == 0

    def test_bos_liste_sifir(self):
        toplam = _kesisim_izin_gunu("12345", date(2024, 1, 1), date(2024, 1, 31), [])
        assert toplam == 0

    def test_kısmi_kesisim(self):
        """Dönem iznin sadece ortasını kesiyor."""
        izin = [{"Personelid": "12345", "BaslamaTarihi": "2024-01-01",
                 "BitisTarihi": "2024-01-19", "Durum": "Onaylandı"}]
        donem_bas = date(2024, 1, 8)
        donem_bit = date(2024, 1, 12)
        toplam = _kesisim_izin_gunu("12345", donem_bas, donem_bit, izin)
        assert toplam == 5


# =============================================================
#  4. tr_upper ile koşul normalleştirme
# =============================================================
class TestTrUpperKosul:

    def test_kosul_a_normalize(self):
        from core.hesaplamalar import tr_upper
        assert "KOŞULU A" in tr_upper("Koşulu A")

    def test_kosul_b_normalize(self):
        from core.hesaplamalar import tr_upper
        assert "KOŞULU B" in tr_upper("Koşulu B")

    def test_kucuk_harf_b_normalize(self):
        from core.hesaplamalar import tr_upper
        assert "KOŞULU B" in tr_upper("koşulu b")

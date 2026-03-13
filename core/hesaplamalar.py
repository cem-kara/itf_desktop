# -*- coding: utf-8 -*-
"""
Hesaplama modülü
- Fiili Hizmet Süresi Zammı (Şua) hak ediş hesabı
- İş günü hesabı (numpy busday_count)
- Türkçe karakter desteği
"""
import numpy as np
import bisect
import math
from datetime import timedelta


# --- YARDIMCI METİN FONKSİYONLARI ---
def tr_upper(text):
    """Türkçe karakter destekli büyük harfe çevirme."""
    if not isinstance(text, str):
        return str(text).upper()
    return text.replace('i', 'İ').replace('ı', 'I').replace('ğ', 'Ğ') \
               .replace('ü', 'Ü').replace('ş', 'Ş').replace('ö', 'Ö') \
               .replace('ç', 'Ç').upper()


# --- HESAPLAMA MANTIĞI ---
def sua_hak_edis_hesapla(toplam_saat):
    """
    Fiili hizmet süresi zammı (Şua) gün sayısını hesaplar.
    30 tane if-else bloğu yerine 'bisect' algoritması kullanılarak optimize edilmiştir.
    """
    try:
        saat = float(toplam_saat)
    except (ValueError, TypeError):
        return 0

    # Sağlık İzni Tablosu (0-50 -> 1 gün ... 1451-1500 -> 30 gün)
    # 50 saatlik dilimlerde artar ve 30 günde tavanlanır.
    if saat <= 0:
        return 0
    gun = int(math.ceil(saat / 50.0))
    return min(30, max(1, gun))


def is_gunu_hesapla(baslangic, bitis, tatil_listesi=None):
    """
    İki tarih arasındaki iş günlerini hesaplar.
    Hafta sonları ve verilen tatil listesi düşülür.
    numpy.busday_count ile yüksek performanslı hesap.
    """
    if tatil_listesi is None:
        tatil_listesi = []

    try:
        dates_start = baslangic.strftime('%Y-%m-%d')
        # Bitiş günü dahil olsun diye +1 gün eklenir
        dates_end = (bitis + timedelta(days=1)).strftime('%Y-%m-%d')

        # '1111100' -> Pzt-Cum çalışılır (1), Cmt-Paz tatil (0)
        workdays = np.busday_count(
            dates_start, dates_end,
            weekmask='1111100',
            holidays=tatil_listesi
        )
        return int(workdays)
    except Exception:
        return 0


def ay_is_gunu(yil, ay, tatil_listesi=None):
    """Belirli bir ay+yıl'daki iş günü sayısını hesaplar."""
    import calendar
    from datetime import date
    son_gun = calendar.monthrange(yil, ay)[1]
    bas = date(yil, ay, 1)
    bit = date(yil, ay, son_gun)
    return is_gunu_hesapla(bas, bit, tatil_listesi)

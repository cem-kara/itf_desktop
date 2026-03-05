# -*- coding: utf-8 -*-
"""
Personel Bilgi Şablonu Kullanım Örneği
═════════════════════════════════════════════════════════════════════════════

Bu dosya, rapor_servisi.py'deki RaporServisi sınıfını kullanarak
personel bilgi raporlarını (PDF) nasıl üretileceğini gösterir.

Şablon: data/templates/pdf/personel_bilgi.html
"""

from core.rapor_servisi import RaporServisi
from core.date_utils import to_ui_date
from datetime import datetime


def personel_bilgi_raporu(
    personel_kimlik_no: str,
    db_session=None,
    kayit_yolu: str | None = None,
) -> str | None:
    """
    Belirtilen personel için bilgi raporu üretir.
    
    Parameters
    ----------
    personel_kimlik_no : str
        Personelin TC Kimlik No veya Kimlik No
    db_session : SQLAlchemy session (isteğe bağlı)
        Veritabanından personel bilgilerini çekmek için
    kayit_yolu : str | None
        Dosya kaydedilecek yol. None ise /tmp dizinine kaydedilir.
    
    Returns
    -------
    str | None
        Oluşturulan PDF dosyasının yolu; hata durumunda None
    """
    
    # ── ÖRNEK VERİ (Gerçek uygulamada veritabanından çekilir) ──────────────
    personel = {
        "adi_soyadi": "Ahmet Yilmaz",
        "tc_kimlik_no": "12345678901",
        "dogum_tarihi": "15.05.1990",
        "cinsiyet": "Erkek",
        "medeni_durum": "Evli",
        "telefon": "+90 532 123 45 67",
        "personel_numarasi": "P-2024-001",
        "departman": "Bilgi İşlem",
        "pozisyon": "Yazılım Geliştici",
        "ise_baslama_tarihi": "01.01.2023",
        "is_yeri": "Ankara",
        "durum": "Aktif",
        "ev_adresi": "Ankara, Çankaya Mahallesi, Örnek Sokak No:123",
    }
    
    # ── SAĞLIK KONTROL GEÇMİŞİ (Tablo verisi) ────────────────────────────
    saglik_geçmişi = [
        {
            "muayene_sinifi": "Dahiliye",
            "tarih": "15.01.2026",
            "durum": "Uygun",
            "aciklama": "Rutin muayene",
            "rapor_durumu": "Yüklendi ✓",
        },
        {
            "muayene_sinifi": "Göz",
            "tarih": "15.01.2026",
            "durum": "Uygun",
            "aciklama": "Görüş testi normal",
            "rapor_durumu": "Yüklendi ✓",
        },
        {
            "muayene_sinifi": "Diş",
            "tarih": "10.01.2026",
            "durum": "Şartlı Uygun",
            "aciklama": "Devam eden tedavi var",
            "rapor_durumu": "Beklemede",
        },
    ]
    
    # ── RAPOR CONTEXT (Yer tutucular) ───────────────────────────────────
    context = {
        # Başlık bilgileri
        "sirket_adi": "İTF (İş Tarihi Fotoğrafları) A.Ş.",
        "rapor_tarihi": to_ui_date(datetime.now()),
        "rapor_donemi": "2026 Ocak",
        
        # Personel kimlik bilgileri
        "adi_soyadi": personel.get("adi_soyadi", ""),
        "tc_kimlik_no": personel.get("tc_kimlik_no", ""),
        "dogum_tarihi": personel.get("dogum_tarihi", ""),
        "cinsiyet": personel.get("cinsiyet", ""),
        "medeni_durum": personel.get("medeni_durum", ""),
        "telefon": personel.get("telefon", ""),
        
        # İş bilgileri
        "personel_numarasi": personel.get("personel_numarasi", ""),
        "departman": personel.get("departman", ""),
        "pozisyon": personel.get("pozisyon", ""),
        "ise_baslama_tarihi": personel.get("ise_baslama_tarihi", ""),
        "is_yeri": personel.get("is_yeri", ""),
        "durum": personel.get("durum", ""),
        
        # Adres
        "ev_adresi": personel.get("ev_adresi", ""),
        
        # Notlar ve imzalar
        "notlar": "Rapor kontrol edilmiş ve onaylanmıştır.",
        "hazirlayan": "İK Müdürü - Fatma Çetinoğlu",
        "cikis_tarihi": to_ui_date(datetime.now()),
    }
    
    # ── RAPOR ÜRETME ───────────────────────────────────────────────────
    rapor_yolu = RaporServisi.pdf(
        sablon="personel_bilgi",       # templates/pdf/personel_bilgi.html
        context=context,                # Yer tutucuları doldur
        tablo=saglik_geçmişi,          # Sağlık tablosu
        kayit_yolu=kayit_yolu,         # None ise /tmp'ye kaydedilir
    )
    
    return rapor_yolu


def personel_bilgi_raporu_excel(
    personel_kimlik_no: str,
    kayit_yolu: str | None = None,
) -> str | None:
    """
    Personel bilgi raporu Excel (.xlsx) formatında üretir.
    
    Not: Excel şablonunu `data/templates/excel/personel_bilgi.xlsx` 
    olarak oluşturmanız gerekir. Şablon şu hücreleri içermeli:
    
    - {{sirket_adi}}: Şirket adı
    - {{adi_soyadi}}: Personel adı soyadı
    - {{tc_kimlik_no}}: TC No
    - {{personel_numarasi}}: Personel No
    - {{departman}}: Departman adı
    - {{durum}}: Aktif/Pasif/vb.
    - {{rapor_tarihi}}: Rapor tarihi
    - Tablo için {{ROW}} satırı (sağlık geçmişi için)
    """
    
    personel = {
        "adi_soyadi": "Ahmet Yilmaz",
        "tc_kimlik_no": "12345678901",
        "personel_numarasi": "P-2024-001",
        "departman": "Bilgi İşlem",
        "durum": "Aktif",
    }
    
    saglik_geçmişi = [
        {
            "muayene_sinifi": "Dahiliye",
            "tarih": "15.01.2026",
            "durum": "Uygun",
        },
        {
            "muayene_sinifi": "Göz",
            "tarih": "15.01.2026",
            "durum": "Uygun",
        },
    ]
    
    context = {
        "sirket_adi": "İTF A.Ş.",
        "adi_soyadi": personel.get("adi_soyadi"),
        "tc_kimlik_no": personel.get("tc_kimlik_no"),
        "personel_numarasi": personel.get("personel_numarasi"),
        "departman": personel.get("departman"),
        "durum": personel.get("durum"),
        "rapor_tarihi": to_ui_date(datetime.now()),
    }
    
    rapor_yolu = RaporServisi.excel(
        sablon="personel_bilgi",       # templates/excel/personel_bilgi.xlsx
        context=context,
        tablo=saglik_geçmişi,
        kayit_yolu=kayit_yolu,
    )
    
    return rapor_yolu


# ═════════════════════════════════════════════════════════════════════════════
#  KULLANIM ÖRNEĞI
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from pathlib import Path
    import tempfile
    
    # PDF raporu oluştur
    pdf_yolu = personel_bilgi_raporu(personel_kimlik_no="12345678901")
    
    if pdf_yolu:
        print(f"✓ PDF raporu oluşturuldu: {pdf_yolu}")
        # Dosyayı aç (isteğe bağlı)
        # RaporServisi.ac(pdf_yolu)
    else:
        print("✗ PDF raporu oluşturulamadı")
    
    # Excel raporu oluştur
    excel_yolu = personel_bilgi_raporu_excel(personel_kimlik_no="12345678901")
    
    if excel_yolu:
        print(f"✓ Excel raporu oluşturuldu: {excel_yolu}")
    else:
        print("✗ Excel raporu oluşturulamadı")

# -*- coding: utf-8 -*-
"""
dozimetre_import_page.py — Toplu Dozimetre Ölçüm Excel İçe Aktarma

Dozimetre_Olcum tablosu kolonları (table_config'den otomatik gelir):
    KayitNo*, SiraNo, RaporNo, Periyot, PeriyotAdi, Yil, DozimetriTipi,
    AdSoyad, TCKimlikNo, CalistiBirim, PersonelID,
    DozimetreNo, VucutBolgesi, Hp10, Hp007, DozSiniri_Hp10, DozSiniri_Hp007, Durum

Konfig yalnızca özel muamele gereken alanları tanımlar;
geri kalanı alanlar_tam_listesi() ile otomatik eklenir.

PDF tabanlı import için: dozimetre_pdf_import_page.py (DozimetrePdfImportPage)
"""

from core.services.excel_import_service import AlanTanimi, DuplicateKontrol, ImportKonfig

from core.validators import validate_tc_kimlik_no
from core.text_utils import turkish_title_case
from ui.pages.imports.components.base_import_page import BaseImportPage


def _tc_v(v): return validate_tc_kimlik_no(v), "Geçersiz TC Kimlik No (hane algoritması)"


def _normalize(kayit: dict) -> dict:
    if kayit.get("AdSoyad"):
        kayit["AdSoyad"] = turkish_title_case(kayit["AdSoyad"])
    return kayit


def _get_servis(db):
    from core.di import get_dozimetre_service
    return get_dozimetre_service(db)


KONFIG = ImportKonfig(
    baslik="Toplu Dozimetre Ölçüm İçe Aktarma (Excel)",
    servis_fabrika=_get_servis,
    servis_metod="olcum_ekle",
    tablo_adi="Dozimetre_Olcum",
    normalize_fn=_normalize,

    duplicate=DuplicateKontrol(
        pk_alanlar=["TCKimlikNo", "Periyot", "Yil"],
        pk_cakisma="raporla",
    ),

    alanlar=[
        # ── Zorunlu + validator ─────────────────────────────────────────
        AlanTanimi(
            "TCKimlikNo", "TC Kimlik No *", "tc",
            zorunlu=True,
            validator=_tc_v,
            anahtar_kelimeler=["tckimlikno", "kimlikno", "tc", "kimlik", "tcno"],
        ),
        AlanTanimi(
            "Periyot", "Periyot *", "str",
            zorunlu=True,
            anahtar_kelimeler=["periyot", "donem", "period", "quarter"],
        ),
        AlanTanimi(
            "Yil", "Yıl *", "int",
            zorunlu=True,
            anahtar_kelimeler=["yil", "year"],
        ),

        # ── Okunabilir etiket + anahtar kelimeler gereken alanlar ───────
        AlanTanimi(
            "AdSoyad", "Ad Soyad", "str",
            anahtar_kelimeler=["adsoyad", "ad", "isim", "name"],
        ),
        AlanTanimi(
            "CalistiBirim", "Çalıştığı Birim", "str",
            anahtar_kelimeler=["calistibirim", "birim", "bolum", "department"],
        ),
        AlanTanimi(
            "PersonelID", "Personel ID / TC", "tc",
            anahtar_kelimeler=["personelid", "personel"],
        ),

        # ── Doz değerleri — gerçek DB kolon adları: Hp10, Hp007 ─────────
        AlanTanimi(
            "Hp10",  "Hp(10) — Derin Doz (mSv)", "float",
            anahtar_kelimeler=["hp10", "derindoz", "derin", "deepdose"],
        ),
        AlanTanimi(
            "Hp007", "Hp(0,07) — Yüzeysel Doz (mSv)", "float",
            anahtar_kelimeler=["hp007", "yuzeyeldoz", "yuzeysel", "shallowdose"],
        ),
        AlanTanimi(
            "DozSiniri_Hp10",  "Doz Sınırı Hp(10)", "float",
            anahtar_kelimeler=["dozsinirihp10", "sinir10", "limitdose"],
        ),
        AlanTanimi(
            "DozSiniri_Hp007", "Doz Sınırı Hp(0,07)", "float",
            anahtar_kelimeler=["dozsinirihp007", "sinir007"],
        ),

        # ── Dozimetre bilgisi ────────────────────────────────────────────
        AlanTanimi(
            "DozimetreNo", "Dozimetre No", "str",
            anahtar_kelimeler=["dozimetreno", "dozimetre", "badgeno"],
        ),
        AlanTanimi(
            "VucutBolgesi", "Vücut Bölgesi", "str",
            anahtar_kelimeler=["vucutbolgesi", "vucut", "bodylocation"],
        ),
        AlanTanimi(
            "PeriyotAdi", "Periyot Adı", "str",
            anahtar_kelimeler=["periyotadi", "periyotisim", "periodname"],
        ),
        AlanTanimi(
            "DozimetriTipi", "Dozimetri Tipi", "str",
            varsayilan="Excel",
            anahtar_kelimeler=["dozimetritipi", "tip", "type"],
        ),

        # ── Durum ───────────────────────────────────────────────────────
        AlanTanimi(
            "Durum", "Durum", "str",
            varsayilan="Sınırın Altında",
            anahtar_kelimeler=["durum", "status", "sonuc"],
        ),
    ],
)


class DozimetreImportPage(BaseImportPage):
    def _konfig(self) -> ImportKonfig:
        return KONFIG

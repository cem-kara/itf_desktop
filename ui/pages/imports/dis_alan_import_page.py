# -*- coding: utf-8 -*-
"""
dis_alan_import_page.py — Toplu Dış Alan Çalışma Excel İçe Aktarma

Dis_Alan_Calisma kolonları (table_config'den otomatik gelir):
    TCKimlik, AdSoyad, DonemAy, DonemYil, AnaBilimDali, Birim,
    IslemTipi, Katsayi, OrtSureDk, VakaSayisi, HesaplananSaat,
    ToplamSureDk, TutanakNo, TutanakTarihi
    (KayitTarihi, KaydedenKullanici — sistem, otomatik atlanır)

Not: TCKimlik opsiyoneldir — sisteme kayıtlı olmayan dış alan personeli
     de girilebilir. TutanakNo + Dönem benzersizliği sağlar.
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
    from core.di import get_dis_alan_service
    return get_dis_alan_service(db)


KONFIG = ImportKonfig(
    baslik="Toplu Dış Alan Çalışma İçe Aktarma",
    servis_fabrika=_get_servis,
    servis_metod="dis_alan_ekle",
    tablo_adi="Dis_Alan_Calisma",
    normalize_fn=_normalize,

    duplicate=DuplicateKontrol(
        pk_alanlar=["TCKimlik", "DonemAy", "DonemYil", "TutanakNo"],
        pk_cakisma="raporla",
    ),

    alanlar=[
        # ── TC Kimlik — opsiyonel ama validator var ──────────────────────
        AlanTanimi(
            "TCKimlik", "TC Kimlik No", "tc",
            zorunlu=False,          # Dış alan personeli sisteme kayıtlı olmayabilir
            validator=_tc_v,
            anahtar_kelimeler=["tckimlik", "kimlik", "tc", "tcno", "kimlikno"],
        ),

        # ── Zorunlu alanlar ─────────────────────────────────────────────
        AlanTanimi(
            "AdSoyad", "Ad Soyad *", "str",
            zorunlu=True,
            anahtar_kelimeler=["adsoyad", "ad", "isim", "name"],
        ),
        AlanTanimi(
            "DonemAy", "Dönem Ay *", "int",
            zorunlu=True,
            anahtar_kelimeler=["doneay", "donemay", "ay", "month"],
        ),
        AlanTanimi(
            "DonemYil", "Dönem Yıl *", "int",
            zorunlu=True,
            anahtar_kelimeler=["donemyil", "yil", "year"],
        ),
        AlanTanimi(
            "TutanakNo", "Tutanak No *", "str",
            zorunlu=True,
            anahtar_kelimeler=["tutanakno", "tutanak", "documentno", "belgeno"],
        ),

        # ── Anahtar kelime gereken alanlar ──────────────────────────────
        AlanTanimi(
            "AnaBilimDali", "Ana Bilim Dalı", "str",
            anahtar_kelimeler=["anabilimdali", "abd", "department"],
        ),
        AlanTanimi(
            "Birim", "Birim", "str",
            anahtar_kelimeler=["birim", "bolum", "unit"],
        ),
        AlanTanimi(
            "IslemTipi", "İşlem Tipi / Alan Adı", "str",
            anahtar_kelimeler=["islemtipi", "islem", "alanadi", "proceduretype"],
        ),
        AlanTanimi(
            "Katsayi", "Katsayı", "float",
            anahtar_kelimeler=["katsayi", "coefficient", "factor"],
        ),
        AlanTanimi(
            "OrtSureDk", "Ort. Süre (dk)", "int",
            anahtar_kelimeler=["ortsuredk", "ortalamasure", "averagetime"],
        ),
        AlanTanimi(
            "VakaSayisi", "Vaka Sayısı", "int",
            anahtar_kelimeler=["vakasayisi", "vaka", "casecount", "sayisi"],
        ),
        AlanTanimi(
            "HesaplananSaat", "Hesaplanan Saat", "float",
            anahtar_kelimeler=["hesaplanansaat", "hesaplanan", "calculatedhours"],
        ),
        AlanTanimi(
            "ToplamSureDk", "Toplam Süre (dk)", "int",
            anahtar_kelimeler=["toplamasuredk", "toplamure", "totalduration"],
        ),
        AlanTanimi(
            "TutanakTarihi", "Tutanak Tarihi", "date",
            anahtar_kelimeler=["tutanaktarihi", "tarih", "documentdate"],
        ),
    ],
)


class DisAlanImportPage(BaseImportPage):
    def _konfig(self) -> ImportKonfig:
        return KONFIG

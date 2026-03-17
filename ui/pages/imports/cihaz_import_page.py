# -*- coding: utf-8 -*-
"""
cihaz_import_page.py — Toplu Cihaz Excel İçe Aktarma

Cihazlar tablosu kolonları (table_config'den otomatik gelir):
    Cihazid, CihazTipi, Marka, Model, Amac, Kaynak, SeriNo, NDKSeriNo,
    HizmeteGirisTarihi, RKS, Sorumlusu, Gorevi, NDKLisansNo,
    BaslamaTarihi, BitisTarihi, LisansDurum, AnaBilimDali, Birim,
    BulunduguBina, GarantiDurumu, GarantiBitisTarihi, DemirbasNo,
    KalibrasyonGereklimi, BakimDurum, Durum
    (Img, NDKLisansBelgesi — binary, otomatik atlanır)
"""

from core.services.excel_import_service import AlanTanimi, DuplicateKontrol, ImportKonfig
from core.text_utils import turkish_title_case
from ui.pages.imports.components.base_import_page import BaseImportPage


def _normalize(kayit: dict) -> dict:
    if kayit.get("Sorumlusu"):
        kayit["Sorumlusu"] = turkish_title_case(kayit["Sorumlusu"])
    return kayit


def _get_servis(db):
    from core.di import get_cihaz_service
    return get_cihaz_service(db)


KONFIG = ImportKonfig(
    baslik="Toplu Cihaz İçe Aktarma",
    servis_fabrika=_get_servis,
    servis_metod="cihaz_ekle",
    tablo_adi="Cihazlar",
    normalize_fn=_normalize,

    duplicate=DuplicateKontrol(
        pk_alanlar=["Cihazid"],
        pk_cakisma="raporla",
    ),

    alanlar=[
        # ── Zorunlu ─────────────────────────────────────────────────────
        AlanTanimi(
            "Cihazid", "Cihaz ID *", "str",
            zorunlu=True,
            anahtar_kelimeler=["cihazid", "cihazno", "deviceid", "id"],
        ),

        # ── Anahtar kelime gereken alanlar ──────────────────────────────
        AlanTanimi(
            "CihazTipi", "Cihaz Tipi", "str",
            anahtar_kelimeler=["cihaztipi", "tip", "type", "devicetype"],
        ),
        AlanTanimi(
            "Marka", "Marka", "str",
            anahtar_kelimeler=["marka", "brand", "manufacturer"],
        ),
        AlanTanimi(
            "Model", "Model", "str",
            anahtar_kelimeler=["model", "modelno"],
        ),
        AlanTanimi(
            "SeriNo", "Seri No", "str",
            anahtar_kelimeler=["serino", "seri", "serialno", "serial"],
        ),
        AlanTanimi(
            "NDKSeriNo", "NDK Seri No", "str",
            anahtar_kelimeler=["ndkserino", "ndkseri", "ndkno"],
        ),
        AlanTanimi(
            "Amac", "Amaç / Kullanım", "str",
            anahtar_kelimeler=["amac", "kullanim", "purpose"],
        ),
        AlanTanimi(
            "Kaynak", "Kaynak", "str",
            anahtar_kelimeler=["kaynak", "source", "temin"],
        ),
        AlanTanimi(
            "HizmeteGirisTarihi", "Hizmete Giriş Tarihi", "date",
            anahtar_kelimeler=["hizmetegiristarihi", "hizmete", "servicedate"],
        ),
        AlanTanimi(
            "BaslamaTarihi", "Başlama Tarihi", "date",
            anahtar_kelimeler=["baslamatarihi", "baslama", "startdate"],
        ),
        AlanTanimi(
            "BitisTarihi", "Bitiş Tarihi", "date",
            anahtar_kelimeler=["bitistarihi", "bitis", "enddate"],
        ),
        AlanTanimi(
            "GarantiBitisTarihi", "Garanti Bitiş Tarihi", "date",
            anahtar_kelimeler=["garantibitistarihi", "garanti", "warrantydate"],
        ),
        AlanTanimi(
            "RKS", "RKS No", "str",
            anahtar_kelimeler=["rks", "rksno"],
        ),
        AlanTanimi(
            "NDKLisansNo", "NDK Lisans No", "str",
            anahtar_kelimeler=["ndklisansno", "ndklisans", "licenceno"],
        ),
        AlanTanimi(
            "Sorumlusu", "Sorumlusu", "str",
            anahtar_kelimeler=["sorumlusu", "sorumlu", "responsible"],
        ),
        AlanTanimi(
            "Gorevi", "Görevi", "str",
            anahtar_kelimeler=["gorevi", "gorev", "position"],
        ),
        AlanTanimi(
            "AnaBilimDali", "Ana Bilim Dalı", "str",
            anahtar_kelimeler=["anabilimdali", "abd", "department"],
        ),
        AlanTanimi(
            "Birim", "Birim", "str",
            anahtar_kelimeler=["birim", "bolum", "unit"],
        ),
        AlanTanimi(
            "BulunduguBina", "Bulunduğu Bina", "str",
            anahtar_kelimeler=["bulundugubina", "bina", "building", "location"],
        ),
        AlanTanimi(
            "DemirbasNo", "Demirbaş No", "str",
            anahtar_kelimeler=["demirbasno", "demrbas", "inventoryno"],
        ),
        AlanTanimi(
            "LisansDurum", "Lisans Durum", "str",
            anahtar_kelimeler=["lisansdurum", "lisans", "licensestatus"],
        ),
        AlanTanimi(
            "GarantiDurumu", "Garanti Durumu", "str",
            anahtar_kelimeler=["garantidurumu", "garantidurum", "warranty"],
        ),
        AlanTanimi(
            "KalibrasyonGereklimi", "Kalibrasyon Gerekli mi", "str",
            varsayilan="Evet",
            anahtar_kelimeler=["kalibrasyongerekli", "kalibrasyon", "calibration"],
        ),
        AlanTanimi(
            "BakimDurum", "Bakım Durum", "str",
            anahtar_kelimeler=["bakimdurum", "bakim", "maintenance"],
        ),
        AlanTanimi(
            "Durum", "Durum", "str",
            varsayilan="Aktif",
            anahtar_kelimeler=["durum", "status"],
        ),
    ],
)


class CihazImportPage(BaseImportPage):
    def _konfig(self) -> ImportKonfig:
        return KONFIG

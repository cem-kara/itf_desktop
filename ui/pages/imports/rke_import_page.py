# -*- coding: utf-8 -*-
"""
rke_import_page.py — Toplu RKE Excel İçe Aktarma

İki sayfa:
  RkeListImportPage    → RKE_List    (ekipman kaydı)
  RkeMuayeneImportPage → RKE_Muayene (periyodik muayene)

RKE_List kolonları (table_config'den otomatik):
    EkipmanNo*, KoruyucuNumarasi, AnaBilimDali, Birim, KoruyucuCinsi,
    KursunEsdegeri, HizmetYili, Bedeni, KontrolTarihi, Durum,
    Aciklama, VarsaDemirbasNo, KayitTarih, Barkod

RKE_Muayene kolonları (table_config'den otomatik):
    KayitNo*, EkipmanNo, FMuayeneTarihi, FizikselDurum, SMuayeneTarihi,
    SkopiDurum, Aciklamalar, KontrolEdenUnvani, BirimSorumlusuUnvani,
    Notlar
    (Rapor — binary, otomatik atlanır)
"""

from core.services.excel_import_service import AlanTanimi, DuplicateKontrol, ImportKonfig

from ui.pages.imports.components.base_import_page import BaseImportPage


def _get_rke_servis(db):
    from core.di import get_rke_service
    return get_rke_service(db)


# ---------------------------------------------------------------------------
# RKE List — Ekipman Kaydı
# ---------------------------------------------------------------------------

KONFIG_RKE_LIST = ImportKonfig(
    baslik="Toplu RKE Ekipman Listesi İçe Aktarma",
    servis_fabrika=_get_rke_servis,
    servis_metod="rke_ekle",
    tablo_adi="RKE_List",

    duplicate=DuplicateKontrol(
        pk_alanlar=["EkipmanNo"],
        pk_cakisma="raporla",
    ),

    alanlar=[
        # ── Zorunlu ─────────────────────────────────────────────────────
        AlanTanimi(
            "EkipmanNo", "Ekipman No *", "str",
            zorunlu=True,
            anahtar_kelimeler=["ekipmanno", "ekipmano", "equipmentno", "no"],
        ),

        # ── Anahtar kelime gereken alanlar ──────────────────────────────
        AlanTanimi(
            "KoruyucuNumarasi", "Koruyucu Numarası", "str",
            anahtar_kelimeler=["koruyucunumarasi", "koruyucuno", "protectorno"],
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
            "KoruyucuCinsi", "Koruyucu Cinsi", "str",
            anahtar_kelimeler=["koruyucucinsi", "koruyucu", "protectortype"],
        ),
        AlanTanimi(
            "KursunEsdegeri", "Kurşun Eşdeğeri", "str",
            anahtar_kelimeler=["kursunesd", "kursunesdegeri", "leadequivalent"],
        ),
        AlanTanimi(
            "HizmetYili", "Hizmet Yılı", "int",
            anahtar_kelimeler=["hizmetyili", "hizmet", "serviceyear"],
        ),
        AlanTanimi(
            "Bedeni", "Bedeni", "str",
            anahtar_kelimeler=["bedeni", "beden", "size"],
        ),
        AlanTanimi(
            "KontrolTarihi", "Kontrol Tarihi", "date",
            anahtar_kelimeler=["kontroltarihi", "kontrol", "checkdate"],
        ),
        AlanTanimi(
            "VarsaDemirbasNo", "Demirbaş No", "str",
            anahtar_kelimeler=["varsademirbasno", "demirbasno", "inventoryno"],
        ),
        AlanTanimi(
            "Barkod", "Barkod", "str",
            anahtar_kelimeler=["barkod", "barcode"],
        ),
        AlanTanimi(
            "Durum", "Durum", "str",
            varsayilan="Aktif",
            anahtar_kelimeler=["durum", "status"],
        ),
        AlanTanimi(
            "Aciklama", "Açıklama", "str",
            anahtar_kelimeler=["aciklama", "notlar", "notes"],
        ),
    ],
)


# ---------------------------------------------------------------------------
# RKE Muayene — Periyodik Muayene Kaydı
# ---------------------------------------------------------------------------

KONFIG_RKE_MUAYENE = ImportKonfig(
    baslik="Toplu RKE Muayene Kaydı İçe Aktarma",
    servis_fabrika=_get_rke_servis,
    servis_metod="muayene_ekle",
    tablo_adi="RKE_Muayene",

    duplicate=DuplicateKontrol(
        pk_alanlar=["EkipmanNo", "FMuayeneTarihi"],
        pk_cakisma="raporla",
        # Aynı ekipman aynı gün iki muayene → yumuşak uyarı
        yumusak_alanlar=["EkipmanNo", "SMuayeneTarihi"],
        yumusak_cakisma="uyar",
    ),

    alanlar=[
        # ── Zorunlu ─────────────────────────────────────────────────────
        AlanTanimi(
            "EkipmanNo", "Ekipman No *", "str",
            zorunlu=True,
            anahtar_kelimeler=["ekipmanno", "ekipmano", "equipmentno", "no"],
        ),
        AlanTanimi(
            "FMuayeneTarihi", "Fiili Muayene Tarihi *", "date",
            zorunlu=True,
            anahtar_kelimeler=["fmuayenetarihi", "filimuayene", "muayenetarihi",
                               "muayene", "examdate"],
        ),

        # ── Anahtar kelime gereken alanlar ──────────────────────────────
        AlanTanimi(
            "SMuayeneTarihi", "Sonraki Muayene Tarihi", "date",
            anahtar_kelimeler=["smuayenetarihi", "sonrakimuayene", "nextexam"],
        ),
        AlanTanimi(
            "FizikselDurum", "Fiziksel Durum", "str",
            anahtar_kelimeler=["fizikseldurum", "fiziksel", "physicalcondition"],
        ),
        AlanTanimi(
            "SkopiDurum", "Skopi Durum", "str",
            anahtar_kelimeler=["skopidurum", "skopi", "fluoroscopy"],
        ),
        AlanTanimi(
            "Aciklamalar", "Açıklamalar", "str",
            anahtar_kelimeler=["aciklamalar", "aciklama", "notlar", "notes"],
        ),
        AlanTanimi(
            "KontrolEdenUnvani", "Kontrol Eden Ünvanı", "str",
            anahtar_kelimeler=["kontroledenunvani", "kontroleden", "inspector"],
        ),
        AlanTanimi(
            "BirimSorumlusuUnvani", "Birim Sorumlusu Ünvanı", "str",
            anahtar_kelimeler=["birimsorumlusu", "sorumlu", "supervisor"],
        ),
        AlanTanimi(
            "Notlar", "Notlar", "str",
            anahtar_kelimeler=["notlar", "not", "notes"],
        ),
    ],
)


# ---------------------------------------------------------------------------
# Sayfalar
# ---------------------------------------------------------------------------

class RkeListImportPage(BaseImportPage):
    def _konfig(self) -> ImportKonfig:
        return KONFIG_RKE_LIST


class RkeMuayeneImportPage(BaseImportPage):
    def _konfig(self) -> ImportKonfig:
        return KONFIG_RKE_MUAYENE

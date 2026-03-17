# -*- coding: utf-8 -*-
"""
izin_giris_import_page.py — Toplu İzin Giriş Excel İçe Aktarma

table_config.TABLES["Izin_Giris"] kolonları:
    Izinid, HizmetSinifi, Personelid, AdSoyad,
    IzinTipi, BaslamaTarihi, Gun, BitisTarihi, Durum

Konfig yalnızca özel alanları tanımlar; geri kalanı otomatik eklenir.
Yumuşak duplicate: aynı personel çakışan tarih aralığında → uyarı.
"""

from core.services.excel_import_service import AlanTanimi, DuplicateKontrol, ImportKonfig
from core.validators import validate_tc_kimlik_no
from core.text_utils import turkish_title_case
from ui.pages.imports.components.base_import_page import BaseImportPage
from core.di import get_izin_service


def _tc_v(v): return validate_tc_kimlik_no(v), "Geçersiz TC Kimlik No (hane algoritması)"


def _normalize(kayit: dict) -> dict:
    """AdSoyad → Türkçe Title Case."""
    if kayit.get("AdSoyad"):
        kayit["AdSoyad"] = turkish_title_case(kayit["AdSoyad"])
    return kayit


KONFIG = ImportKonfig(
    baslik="Toplu İzin Giriş İçe Aktarma",
    servis_fabrika=get_izin_service,
    servis_metod="insert_izin_giris",
    tablo_adi="Izin_Giris",
    normalize_fn=_normalize,

    duplicate=DuplicateKontrol(
        pk_alanlar=["Personelid", "BaslamaTarihi", "IzinTipi"],
        pk_cakisma="raporla",
        yumusak_alanlar=["Personelid", "BaslamaTarihi", "BitisTarihi"],
        yumusak_cakisma="uyar",
    ),

    alanlar=[
        # ── Zorunlu + validator ─────────────────────────────────────────
        AlanTanimi(
            "Personelid", "TC Kimlik No *", "tc",
            zorunlu=True,
            validator=_tc_v,
            anahtar_kelimeler=["personelid", "tckimlik", "kimlik", "tc", "tcno"],
        ),
        AlanTanimi(
            "AdSoyad", "Ad Soyad", "str",
            anahtar_kelimeler=["adsoyad", "ad", "isim", "name"],
        ),
        AlanTanimi(
            "IzinTipi", "İzin Tipi *", "str",
            zorunlu=True,
            anahtar_kelimeler=["izintipi", "tip", "leavetype", "type"],
        ),
        AlanTanimi(
            "BaslamaTarihi", "Başlama Tarihi *", "date",
            zorunlu=True,
            anahtar_kelimeler=["baslamatarihi", "baslama", "startdate"],
        ),
        AlanTanimi(
            "BitisTarihi", "Bitiş Tarihi *", "date",
            zorunlu=True,
            anahtar_kelimeler=["bitistarihi", "bitis", "enddate"],
        ),

        # ── "Gun" — table_config'deki gerçek kolon adı ──────────────────
        # insert_izin_giris metodu da "Gun" anahtarını okuyor.
        AlanTanimi(
            "Gun", "Gün Sayısı", "int",
            anahtar_kelimeler=["gun", "gunsayisi", "izingunsayisi", "days"],
        ),

        # ── Varsayılan değerli alanlar ───────────────────────────────────
        AlanTanimi(
            "Durum", "Durum", "str",
            varsayilan="Aktif",
            anahtar_kelimeler=["durum", "status"],
        ),
        AlanTanimi(
            "HizmetSinifi", "Hizmet Sınıfı", "str",
            anahtar_kelimeler=["hizmetsinifi", "sinif", "hizmet"],
        ),
    ],
)


class IzinGirisImportPage(BaseImportPage):
    def _konfig(self) -> ImportKonfig:
        return KONFIG

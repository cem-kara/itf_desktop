# -*- coding: utf-8 -*-
"""
personel_import_page.py — Toplu Personel Excel İçe Aktarma

Konfig yalnızca özel muamele gereken alanları tanımlar.
Geri kalan kolonlar table_config.TABLES["Personel"] üzerinden
alanlar_tam_listesi() tarafından otomatik eklenir.
"""

from core.services.excel_import_service import AlanTanimi, DuplicateKontrol, ImportKonfig
from core.validators import validate_tc_kimlik_no, validate_email, validate_phone_number
from core.text_utils import turkish_title_case
from ui.pages.imports.components.base_import_page import BaseImportPage


# ---------------------------------------------------------------------------
# Validator'lar
# ---------------------------------------------------------------------------

def _tc_v(v):    return validate_tc_kimlik_no(v), "Geçersiz TC Kimlik No (hane algoritması)"
def _mail_v(v):  return validate_email(v),         "Geçersiz e-posta formatı"
def _tel_v(v):   return validate_phone_number(v),  "Geçersiz telefon numarası"


def _normalize(kayit: dict) -> dict:
    if kayit.get("AdSoyad"):
        kayit["AdSoyad"] = turkish_title_case(kayit["AdSoyad"])
    return kayit


# ---------------------------------------------------------------------------
# Konfig  — sadece özel alanlar
# Kalan kolonlar (DogumYeri, HizmetSinifi, KadroUnvani, GorevYeri,
# KurumSicilNo, MezunOlunanOkul, DiplomaNo, Durum vb.)
# table_config üzerinden otomatik eklenir.
# ---------------------------------------------------------------------------

KONFIG = ImportKonfig(
    baslik="Toplu Personel İçe Aktarma",
    servis_fabrika=lambda db: __import__(
        "core.di", fromlist=["get_personel_service"]
    ).get_personel_service(db),
    servis_metod="ekle",
    tablo_adi="Personel",
    normalize_fn=_normalize,

    duplicate=DuplicateKontrol(
        pk_alanlar=["KimlikNo"],
        pk_cakisma="raporla",
    ),

    alanlar=[
        # ── Zorunlu + validator ─────────────────────────────────────────
        AlanTanimi(
            "KimlikNo", "TC Kimlik No *", "tc",
            zorunlu=True,
            validator=_tc_v,
            anahtar_kelimeler=["kimlik", "tc", "tckimlik", "kimlikno", "tcno"],
        ),
        AlanTanimi(
            "AdSoyad", "Ad Soyad *", "str",
            zorunlu=True,
            anahtar_kelimeler=["adsoyad", "ad", "isim", "namesurname", "adisoyadi"],
        ),

        # ── Auto-match için anahtar kelime gereken alanlar ──────────────
        AlanTanimi(
            "DogumTarihi", "Doğum Tarihi", "date",
            anahtar_kelimeler=["dogumtarihi", "dogum", "birthdate"],
        ),
        AlanTanimi(
            "DogumYeri", "Doğum Yeri", "str",
            anahtar_kelimeler=["dogumyeri", "birthplace"],
        ),
        AlanTanimi(
            "HizmetSinifi", "Hizmet Sınıfı", "str",
            anahtar_kelimeler=["hizmetsinifi", "sinif", "hizmet"],
        ),
        AlanTanimi(
            "KadroUnvani", "Kadro Unvanı", "str",
            anahtar_kelimeler=["kadrounvani", "unvan", "title"],
        ),
        AlanTanimi(
            "GorevYeri", "Görev Yeri", "str",
            anahtar_kelimeler=["gorevyeri", "bolum", "birim", "department"],
        ),
        AlanTanimi(
            "KurumSicilNo", "Kurum Sicil No", "str",
            anahtar_kelimeler=["kurumsicilno", "sicilno", "sicil"],
        ),
        AlanTanimi(
            "MemuriyeteBaslamaTarihi", "Memuriyete Başlama", "date",
            anahtar_kelimeler=["memuriyetbaslama", "memuriyetbaslatarih", "isebas"],
        ),

        # ── Validator gereken iletişim alanları ─────────────────────────
        AlanTanimi(
            "CepTelefonu", "Cep Telefonu", "str",
            validator=_tel_v,
            anahtar_kelimeler=["ceptelefonu", "telefon", "tel", "phone", "gsm"],
        ),
        AlanTanimi(
            "Eposta", "E-Posta", "str",
            validator=_mail_v,
            anahtar_kelimeler=["eposta", "email", "mail"],
        ),

        # ── Okunabilir etiket gerektiren diploma alanları ───────────────
        AlanTanimi(
            "MezunOlunanOkul",    "Mezun Okul (1)",     "str",
            anahtar_kelimeler=["mezunokul", "okul", "school"],
        ),
        AlanTanimi(
            "MezunOlunanFakulte", "Mezun Fakülte (1)",  "str",
            anahtar_kelimeler=["mezunfakulte", "fakulte", "faculty"],
        ),
        AlanTanimi(
            "MezuniyetTarihi",    "Mezuniyet Tarihi (1)", "date",
            anahtar_kelimeler=["mezuniyettarihi", "mezuniyet", "graduationdate"],
        ),
        AlanTanimi(
            "DiplomaNo",          "Diploma No (1)",     "str",
            anahtar_kelimeler=["diplomano", "diploma"],
        ),
        AlanTanimi(
            "MezunOlunanOkul2",   "Mezun Okul (2)",     "str",
            anahtar_kelimeler=["mezunokul2", "okul2", "school2"],
        ),
        AlanTanimi(
            "MezunOlunanFakulte2","Mezun Fakülte (2)",  "str",
            anahtar_kelimeler=["mezunfakulte2", "fakulte2", "faculty2"],
        ),
        AlanTanimi(
            "MezuniyetTarihi2",   "Mezuniyet Tarihi (2)", "date",
            anahtar_kelimeler=["mezuniyettarihi2", "mezuniyet2"],
        ),
        AlanTanimi(
            "DiplomaNo2",         "Diploma No (2)",     "str",
            anahtar_kelimeler=["diplomano2", "diploma2"],
        ),

        # ── Varsayılan değer / anahtar kelime gereken diğer alanlar ────
        AlanTanimi(
            "Durum", "Durum", "str",
            varsayilan="Aktif",
            anahtar_kelimeler=["durum", "status"],
        ),
        AlanTanimi(
            "AyrilisTarihi", "Ayrılış Tarihi", "date",
            anahtar_kelimeler=["ayilistarihi", "ayrilis", "leavedate"],
        ),
        AlanTanimi(
            "AyrilmaNedeni", "Ayrılma Nedeni", "str",
            anahtar_kelimeler=["ayrilmanedeni", "leavereason"],
        ),
        AlanTanimi(
            "MuayeneTarihi", "Muayene Tarihi", "date",
            anahtar_kelimeler=["muayenetarihi", "muayene", "examdate"],
        ),
        AlanTanimi(
            "Sonuc", "Muayene Sonucu", "str",
            anahtar_kelimeler=["sonuc", "muayenesonucu", "examresult"],
        ),
    ],
)


class PersonelImportPage(BaseImportPage):
    def _konfig(self) -> ImportKonfig:
        return KONFIG

# -*- coding: utf-8 -*-
"""
UTS Parser - Field Mapping
===========================
UTS API JSON response'ini DB field'larına mapping etme.
"""
from typing import Dict
import json

from core.logger import logger
from .uts_cache import _yn, JSON_KEY_TO_DB_FIELD


# ─────────────────────────────────────────────────────────────────────────────
# API Response Parsing
# ─────────────────────────────────────────────────────────────────────────────

def parse_uts_api_response(api_response: dict, urun_no: str) -> Dict[str, str]:
    """
    UTS API JSON response'ini parse et ve DB schema'sına göre mapping yap.
    
    Args:
        api_response: API'den gelen raw JSON
        urun_no: Ürün numarası
    
    Returns:
        Mapping yapılmış field dictionary'si
    """
    r: Dict[str, str] = {}

    if not api_response or "data" not in api_response:
        logger.warning("API response yapısı hatalı (data array yok)")
        return r

    data_array = api_response.get("data", [])
    if not data_array or not isinstance(data_array, list):
        logger.warning(f"Data array boş veya hatalı (tip: {type(data_array)})")
        return r

    item = data_array[0]
    if not isinstance(item, dict):
        logger.warning("Data item dict değil")
        return r

    logger.debug(f"API JSON parse başlıyor (item keys: {len(item)})")

    # ── Temel Ürün Bilgileri ───────────────────────────────────────────────────
    _map_api_field(r, item, "birincilUrunNumarasi", str)
    _map_api_field(r, item, "markaAdi", str)
    _map_api_field(r, item, "etiketAdi", str)
    _map_api_field(r, item, "urunTanimi", str)
    _map_api_field(r, item, "versiyonModel", str)
    _map_api_field(r, item, "katalogNo", str)
    _map_api_field(r, item, "temelUdiDi", str)
    _map_api_field(r, item, "aciklama", str)

    # ── Kurum Bilgileri ────────────────────────────────────────────────────────
    if "kurum" in item and isinstance(item["kurum"], dict):
        kurum = item["kurum"]
        _map_nested_field(r, kurum, "unvan", "KurumUnvan")
        _map_nested_field(r, kurum, "gorunenAd", "KurumGorunenAd")
        _map_nested_field(r, kurum, "kurumNo", "KurumNo", int)
        _map_nested_field(r, kurum, "telefon", "KurumTelefon")
        _map_nested_field(r, kurum, "eposta", "KurumEposta")

    # ── Durum ve Kayıt Bilgileri ────────────────────────────────────────────────
    _map_api_field(r, item, "durum", str)
    _map_api_field(r, item, "utsBaslangicTarihi", str)
    _map_api_field(r, item, "kontroleGonderildigiTarih", str)
    _map_api_field(r, item, "cihazKayitTipi", str)

    # ── Ürün Tipi ve Sınıflandırma ────────────────────────────────────────────
    _map_api_field(r, item, "urunTipi", str)
    _map_api_field(r, item, "sinif", str)

    # ── İthal/İmal Bilgileri ────────────────────────────────────────────────────
    _map_api_field(r, item, "ithalImalBilgisi", str)
    _map_array_field(r, item, "menseiUlkeSet", "MenseiUlkeSet")
    _map_array_field(r, item, "ithalEdilenUlkeSet", "IthalEdilenUlkeSet")

    # ── GMDN Terim Bilgileri ────────────────────────────────────────────────────
    if "gmdnTerim" in item and isinstance(item["gmdnTerim"], dict):
        gmdn = item["gmdnTerim"]
        _map_nested_field(r, gmdn, "kod", "GmdnTerimKod", int)
        _map_nested_field(r, gmdn, "turkceAd", "GmdnTerimTurkceAd")
        _map_nested_field(r, gmdn, "turkceAciklama", "GmdnTerimTurkceAciklama")

    # ── Kalibrasyon ve Bakım Bilgileri ─────────────────────────────────────────
    if "kalibrasyonaTabiMi" in item and item["kalibrasyonaTabiMi"]:
        result = _yn(item["kalibrasyonaTabiMi"])
        if result:
            r["KalibrasyonaTabiMi"] = result
            logger.debug(f"KalibrasyonaTabiMi: {result}")

    _map_api_field(r, item, "kalibrasyonPeriyodu", int)

    if "bakimaTabiMi" in item and item["bakimaTabiMi"]:
        result = _yn(item["bakimaTabiMi"])
        if result:
            r["BakimaTabiMi"] = result
            logger.debug(f"BakimaTabiMi: {result}")

    _map_api_field(r, item, "bakimPeriyodu", int)

    # ── Teknik Özellikler (Evet/Hayır alanları) ───────────────────────────────
    evet_hayir_alanlari = {
        "iyonizeRadyasyonIcerir": "IyonizeRadyasyonIcerir",
        "mrgUyumlu": "MrgUyumlu",
        "tekHastayaKullanilabilir": "TekHastayaKullanilabilir",
        "sinirliKullanimSayisiVar": "SinirliKullanimSayisiVar",
        "baskaImalatciyaUrettirildiMi": "BaskaImalatciyaUrettirildiMi",
    }

    for json_field, db_field in evet_hayir_alanlari.items():
        if json_field in item and item[json_field]:
            result = _yn(item[json_field])
            if result:
                r[db_field] = result
                logger.debug(f"{db_field}: {result}")

    # ── Ek Teknik Bilgiler ──────────────────────────────────────────────────────
    _map_api_field(r, item, "sinirliKullanimSayisi", int)
    _map_array_field(r, item, "sutEslesmesiSet", "SutEslesmesiSet")

    if "basvuruyaHazirMi" in item and item["basvuruyaHazirMi"] is not None:
        val = "Evet" if item["basvuruyaHazirMi"] else "Hayır"
        r["BasvuruHazir"] = val
        logger.debug(f"BasvuruHazir: {val}")

    _map_api_field(r, item, "rafOmru", int)

    if "rafOmruVar" in item and item["rafOmruVar"]:
        result = _yn(item["rafOmruVar"])
        if result:
            r["RafOmruVarMi"] = result
            logger.debug(f"RafOmruVarMi: {result}")

    logger.info(f"API JSON parse tamamlandı: {len(r)} alan başarıyla eklendi")
    return r


# ─────────────────────────────────────────────────────────────────────────────
# HTML Label Mapping
# ─────────────────────────────────────────────────────────────────────────────

def map_label_to_db(data: dict, label: str, value: str) -> None:
    """
    HTML label'dan DB field'ına mapping yap.
    
    Args:
        data: Hedef dictionary
        label: HTML label metni
        value: Field değeri
    """
    label_upper = label.upper().strip()
    value = str(value).strip()

    if not value:
        return

    mapping = {
        "ÜRÜN ADI": "UrunAdi",
        "MARKA": "Marka",
        "MODEL": "UrunAdi",
        "FIRMA": "Firma",
        "SIRAÇ": "Sinif",
        "SINIF": "Sinif",
        "GMDN KODU": "GmdnKod",
        "GMDN TERİMİ": "GmdnTurkce",
        "İTHAL/İMAL": "IthalImalBilgisi",
        "MENŞEI ÜLKE": "MenseiUlke",
        "STERIL": "SterilPaketlendiMi",
        "TEK KULLANIM": "TekKullanimlikMi",
        "KALİBRASYON": "KalibrasyonaTabiMi",
        "BAKIM": "BakimaTabiMi",
        "LATEKS": "LateksIceriyorMu",
        "FTALAT": "FtalatDEHPIceriyorMu",
        "RADYASYON": "IyonizeRadyasyonIcerirMi",
        "NANOMAT": "NanomateryalIceriyorMu",
        "MRG": "MRGGuvenlikBilgisi",
        "İMPLANT": "ImplanteEdilebilirMi",
    }

    for key, db_field in mapping.items():
        if key in label_upper:
            data[db_field] = _yn(value)
            return


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

def _map_api_field(data: dict, item: dict, json_key: str, type_func=str):
    """API field'ını JSON'dan mapping et."""
    if json_key in item and item[json_key]:
        try:
            val = type_func(item[json_key])
            db_key = JSON_KEY_TO_DB_FIELD.get(json_key, json_key)
            data[db_key] = val
            logger.debug(f"{db_key}: {val}")
        except (ValueError, TypeError) as e:
            logger.warning(f"Field mapping hatası ({json_key}): {e}")


def _map_nested_field(data: dict, parent: dict, json_key: str, db_key: str, type_func=str):
    """Nested field'ı parent dict'ten mapping et."""
    if json_key in parent and parent[json_key]:
        try:
            val = type_func(parent[json_key]) if type_func != str else str(parent[json_key]).strip()
            data[db_key] = val
            logger.debug(f"{db_key}: {val}")
        except (ValueError, TypeError) as e:
            logger.warning(f"Nested field mapping hatası ({json_key}): {e}")


def _map_array_field(data: dict, item: dict, json_key: str, db_key: str):
    """Array field'ını virgülle ayrılmış string'e çevir."""
    if json_key in item and item[json_key]:
        val = item[json_key]
        if isinstance(val, list):
            val = ", ".join([str(v) for v in val if v])
        if val:
            data[db_key] = str(val)
            logger.debug(f"{db_key}: {val}")

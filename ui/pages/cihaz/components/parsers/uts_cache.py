# -*- coding: utf-8 -*-
"""
UTS Parser - Caching & Field Validation
=========================================
Veritabanı field'larını yükleme, filtreleme ve cache'leme.
"""
from typing import Dict, Optional, Set

from database.table_config import TABLES
from core.logger import logger


# ─────────────────────────────────────────────────────────────────────────────
# Field Loading & Filtering
# ─────────────────────────────────────────────────────────────────────────────

def load_allowed_db_fields(table_name: str = "Cihaz_Teknik") -> Set[str]:
    """
    Veritabanında izin verilen kolonları yükle.
    
    Args:
        table_name: Tablo adı (default: "Cihaz_Teknik")
    
    Returns:
        Kolon adları seti
    """
    config = TABLES.get(table_name, {})
    cols = config.get("columns", [])
    logger.debug(f"DB field'ları yüklendi: {table_name} → {len(cols)} kolon")
    return set(cols)


def filter_allowed_fields(data: Dict[str, str], allowed_fields: Optional[Set[str]] = None) -> Dict[str, str]:
    """
    Parse edilen veriyi sadece bilinen DB kolonlarına filtrele.
    
    Args:
        data: Parse edilmiş veri dict'i
        allowed_fields: İzin verilen kolon seti (None → DB'den yükle)
    
    Returns:
        Filtrelenmiş dict
    """
    if not data:
        return {}
    
    if allowed_fields is None:
        allowed_fields = load_allowed_db_fields()
    
    filtered = {k: v for k, v in data.items() if k in allowed_fields}
    logger.debug(f"Veri filtrelendi: {len(data)} → {len(filtered)} alan")
    return filtered


def _yn(val) -> str:
    """
    Evet/Hayır dönüştürme.
    
    Args:
        val: Evet/Hayır benzeri değer
    
    Returns:
        "Evet" veya "Hayır"
    """
    if val is None:
        return ""
    
    v = str(val).upper().strip()
    if v in ("EVET", "YES", "TRUE", "1"):
        return "Evet"
    if v in ("HAYIR", "NO", "FALSE", "0"):
        return "Hayır"
    
    return str(val)


# ─────────────────────────────────────────────────────────────────────────────
# JSON Field Mapping
# ─────────────────────────────────────────────────────────────────────────────

# UTS API JSON key'lerinden DB field'larına mapping
JSON_KEY_TO_DB_FIELD = {
    "markaAdi": "MarkaAdi",
    "versiyonModel": "VersiyonModel",
    "urunTanimi": "UrunTanimi",
    "gmdnTerim.turkceAd": "GmdnTerimTurkceAd",
    "gmdnTerim.turkceAciklama": "GmdnTerimTurkceAciklama",
    "birincilUrunNumarasi": "BirincilUrunNumarasi",
    "durum": "Durum",
    "utsBaslangicTarihi": "UtsBaslangicTarihi",
    "ithalImalBilgisi": "IthalImalBilgisi",
    "menseiUlkeSet": "MenseiUlkeSet",
    "baskaCihazinBilesenAksesuarYedekParcasiMi": "SutEslesmesiSet",
    "iyonizeRadyasyonIcerir": "IyonizeRadyasyonIcerir",
    "mrgUyumlu": "MrgUyumlu",
    "vucudaImplanteEdilebilirMi": "BaskaImalatciyaUrettirildiMi",
    "tekKullanimlik": "SinirliKullanimSayisiVar",
    "tekHastayaKullanilabilir": "TekHastayaKullanilabilir",
    "kalibrasyonaTabiMi": "KalibrasyonaTabiMi",
    "kalibrasyonPeriyodu": "KalibrasyonPeriyodu",
    "bakimaTabiMi": "BakimaTabiMi",
    "bakimPeriyodu": "BakimPeriyodu",
    "kurum.unvan": "KurumUnvan",
    "kurum.eposta": "KurumEposta",
    "gmdnTerim.kod": "GmdnTerimKod",
    "etiket": "EtiketAdi",
    "siniflandirma": "Sinif",
    "katalogNo": "KatalogNo",
    "temelUdiDi": "TemelUdiDi",
    "aciklama": "Aciklama",
    "kurumGorunenAd": "KurumGorunenAd",
    "kurumNo": "KurumNo",
    "kurumTelefon": "KurumTelefon",
    "cihazKayitTipi": "CihazKayitTipi",
    "urunTipi": "UrunTipi",
    "ithalEdilenUlkeSet": "IthalEdilenUlkeSet",
}

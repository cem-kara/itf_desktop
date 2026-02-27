# -*- coding: utf-8 -*-
"""Bakım Formu — Yardımcı Fonksiyonlar ve Utils."""
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from core.date_utils import to_ui_date


def ay_ekle(kaynak_tarih: datetime, ay_sayisi: int) -> datetime:
    """Bir tarihe belirtilen ay sayısını ekler."""
    return kaynak_tarih + relativedelta(months=ay_sayisi)


def format_bakım_tarihi(tarih_str: str, fallback: str = "—") -> str:
    """Bakım tarihini UI formatında göster."""
    return to_ui_date(tarih_str, fallback)


def validate_bakim_form(baslik: str, periyot: str, teknisyen: str) -> tuple:
    """Bakım formu validasyonu. (is_valid, error_message)"""
    if not baslik or not baslik.strip():
        return False, "Başlık boş olamaz"
    if not periyot or not periyot.strip():
        return False, "Periyot seçilmelidir"
    if not teknisyen or not teknisyen.strip():
        return False, "Teknisyen boş olamaz"
    return True, ""

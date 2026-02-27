# -*- coding: utf-8 -*-
"""
UTS Parser - Backward Compatibility Wrapper
=============================================
Eski kodla uyumluluğu sağlamak için.
Tüm işlemler parsers/ modülüne taşınmıştır.

Kullanım:
    from ui.pages.cihaz.components.uts_parser import scrape_uts
    result = await scrape_uts(urun_no)
"""

from .parsers import (
    scrape_uts,
    load_allowed_db_fields,
    filter_allowed_fields,
)

__all__ = [
    "scrape_uts",
    "load_allowed_db_fields",
    "filter_allowed_fields",
]

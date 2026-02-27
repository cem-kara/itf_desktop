# -*- coding: utf-8 -*-
"""Cihaz listesi tablo modeli - BaseTableModel'den extend."""

from PySide6.QtCore import Qt
from ui.components.base_table_model import BaseTableModel

# ─── Sütun tanımları ──────────────────────────────────────────
COLUMNS = [
    ("_cihaz", "Cihaz", 250),
    ("_marka_model", "Marka / Model", 130),
    ("_seri", "Seri / NDK", 140),
    ("Birim", "Birim", 160),
    ("DemirbasNo", "Demirbas No", 120),
    ("Durum", "Durum", 90),
    # ("BakimDurum", "Bakım", 90),
    ("_actions", "", 200),
]
COL_IDX = {c[0]: i for i, c in enumerate(COLUMNS)}


class CihazTableModel(BaseTableModel):
    """Cihaz listesi tablo modeli - BaseTableModel'den extend."""
    
    def __init__(self, data=None, parent=None):
        super().__init__(columns=COLUMNS, data=data, parent=parent)
    
    def get_row_display(self, row: int, col: int, key: str, raw_row: dict) -> str:
        """
        Hücre display metnini döndür - composit alanları birleştir.
        """
        if key == "_cihaz":
            return f"{raw_row.get('Cihazid', '')} {raw_row.get('CihazTipi', '')}".strip()
        
        if key == "_marka_model":
            return f"{raw_row.get('Marka', '')} {raw_row.get('Model', '')}".strip()
        
        if key == "_seri":
            return f"{raw_row.get('SeriNo', '')} {raw_row.get('NDKSeriNo', '')}".strip()
        
        return str(raw_row.get(key, ""))

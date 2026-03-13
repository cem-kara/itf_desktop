from PySide6.QtCore import Qt
from ui.components.base_table_model import BaseTableModel

KAT_SAYI_COLUMNS = [
    ("AnaBilimDali",      "Ana Bilim Dalı",   150),
    ("Birim",             "Birim",            120),
    ("Katsayi",           "Katsayı",           80),
    ("OrtSureDk",         "Ort. Süre (dk)",    90),
    ("ProtokolRef",       "Protokol Ref",     120),
    ("GecerlilikBaslangic","Başlangıç",        90),
    ("GecerlilikBitis",   "Bitiş",             90),
    ("Aktif",             "Aktif",             60),
]

class DisAlanKatsayiModel(BaseTableModel):
    DATE_KEYS    = frozenset({"GecerlilikBaslangic", "GecerlilikBitis"})
    ALIGN_CENTER = frozenset({"Katsayi", "OrtSureDk", "Aktif"})

    def __init__(self, rows=None, parent=None):
        super().__init__(KAT_SAYI_COLUMNS, rows, parent)

    def _fg(self, key, row):
        if key == "Aktif":
            return self.status_fg("Aktif" if row.get("Aktif") else "Pasif")
        return None

    def _bg(self, key, row):
        if key == "Aktif":
            return self.status_bg("Aktif" if row.get("Aktif") else "Pasif")
        return None

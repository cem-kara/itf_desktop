# ui/pages/fhsz/dis_alan_hbys_referans_model.py
from PySide6.QtCore import Qt
from ui.components.base_table_model import BaseTableModel

REFERANS_COLUMNS = [
    ("HbysReferansKodu",   "Referans Kodu",   120),
    ("HbysReferansAdi",    "Referans Adı",    200),
    ("Aciklama",           "Açıklama",        0),   # 0 → stretch
    ("Aktif",              "Aktif",           60),
    ("KayitTarihi",        "Kayıt Tarihi",    110),
    ("KaydedenKullanici",  "Kaydeden",        100),
]

class DisAlanHbysReferansModel(BaseTableModel):
    DATE_KEYS    = frozenset({"KayitTarihi"})
    ALIGN_CENTER = frozenset({"Aktif"})

    def __init__(self, rows=None, parent=None):
        super().__init__(REFERANS_COLUMNS, rows, parent)

    def _fg(self, key, row):
        if key == "Aktif":
            return self.status_fg("Aktif" if row.get("Aktif") else "Pasif")
        return None

    def _bg(self, key, row):
        if key == "Aktif":
            return self.status_bg("Aktif" if row.get("Aktif") else "Pasif")
        return None

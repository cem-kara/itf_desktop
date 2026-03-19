# -*- coding: utf-8 -*-
"""
CihazDokumanPanel — Cihaz teknik belgelerini yönetir.

Tüm UI ve upload mantığı BaseDokumanPanel'de.
"""
from ui.components.base_dokuman_panel import BaseDokumanPanel


class CihazDokumanPanel(BaseDokumanPanel):
    def __init__(self, cihaz_id, db=None, parent=None):
        super().__init__(
            entity_type   = "cihaz",
            entity_id     = cihaz_id,
            folder_name   = "Cihaz_Belgeler",
            doc_type      = "Cihaz_Belge",
            belge_tur_kod = "Cihaz_Belge_Tur",
            db            = db,
            parent        = parent
)

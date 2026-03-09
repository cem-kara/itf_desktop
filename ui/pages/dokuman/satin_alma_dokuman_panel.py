# -*- coding: utf-8 -*-
"""
satin_alma_dokuman_panel.py
Satın alma belgelerini yönetir (Sözleşme, Fatura, Şartname vb.)

Kullanım:
    from ui.pages.satin_alma.satin_alma_dokuman_panel import SatinAlmaDokumanPanel
    panel = SatinAlmaDokumanPanel(entity_id="SATIN-001", db=self._db)
"""
from ui.components.base_dokuman_panel import BaseDokumanPanel


class SatinAlmaDokumanPanel(BaseDokumanPanel):
    def __init__(self, entity_id: str = "genel", db=None, parent=None):
        super().__init__(
            entity_type   = "satin_alma",
            entity_id     = entity_id,
            folder_name   = "Satin_Alma_Belge",
            doc_type      = "Satin_Alma_Belge",
            belge_tur_kod = "Satin_Alma_Belge_Tur",
            db            = db,
            parent        = parent,
        )

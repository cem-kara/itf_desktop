# -*- coding: utf-8 -*-
"""
kurumsal_dokuman_panel.py
Kurumsal belgeleri yönetir (Yönetmelik, Prosedür, Yazışma vb.)

Kullanım:
from ui.pages.kurumsal.kurumsal_dokuman_panel import KurumsalDokumanPanel
    panel = KurumsalDokumanPanel(db=self._db)
"""
from ui.components.base_dokuman_panel import BaseDokumanPanel


class KurumsalDokumanPanel(BaseDokumanPanel):
    def __init__(self, entity_id: str = "kurum", db=None, parent=None):
        super().__init__(
            entity_type   = "kurumsal",
            entity_id     = entity_id,
            folder_name   = "Kurumsal_Belge",
            doc_type      = "Kurumsal_Belge",
            belge_tur_kod = "Kurumsal_Belge_Tur",
            db            = db,
            parent        = parent,
        )

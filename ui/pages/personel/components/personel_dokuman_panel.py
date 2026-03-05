# -*- coding: utf-8 -*-
"""
PersonelDokumanPanel — Personel belgelerini yönetir.

Tüm UI ve upload mantığı BaseDokumanPanel'de.
"""
from ui.components.base_dokuman_panel import BaseDokumanPanel


class PersonelDokumanPanel(BaseDokumanPanel):
    def __init__(self, personel_id, db=None, sabitler_cache=None, parent=None):
        super().__init__(
            entity_type   = "personel",
            entity_id     = personel_id,
            folder_name   = "Personel_Belge",
            doc_type      = "Personel_Belge",
            belge_tur_kod = "Personel_Belge_Tur",
            db            = db,
            sabitler_cache= sabitler_cache,
            parent        = parent,
        )

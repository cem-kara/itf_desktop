# -*- coding: utf-8 -*-
"""RKE Yönetim — Yardımcı Fonksiyonlar."""
from typing import Dict
from core.logger import logger


def load_sabitler_from_db(db) -> Dict:
    """Sabitler tablosundan verileri oku ve kısaltmaları döndür."""
    if not db:
        return {}
    try:
        sql = "SELECT Kod, MenuEleman, Aciklama FROM Sabitler"
        rows = db.execute(sql).fetchall()
        
        result = {}
        maps = {"AnaBilimDali": {}, "Birim": {}, "Koruyucu_Cinsi": {}, "Beden": {}}
        
        for row in rows:
            kod = str(row["Kod"] or "").strip()
            eleman = str(row["MenuEleman"] or "").strip()
            kis = str(row["Aciklama"] or "").strip()
            
            if kod and eleman:
                result.setdefault(kod, []).append(eleman)
                if kis and kod in maps:
                    maps[kod][eleman] = kis
        
        # Kısaltmaları döndür
        return maps
    except Exception as e:
        logger.error(f"Sabitler yüklenirken hata: {e}")
        return {}

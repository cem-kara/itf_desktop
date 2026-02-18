# -*- coding: utf-8 -*-
"""
RKE Worker Thread'leri
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
â€¢ VeriYukleyiciThread    â€“ Sabitler + RKE_List + RKE_Muayene verisini yÃ¼kler
â€¢ IslemKaydediciThread   â€“ INSERT / UPDATE iÅŸlemi yapar
â€¢ GecmisYukleyiciThread  â€“ SeÃ§ili ekipmanÄ±n muayene geÃ§miÅŸini yÃ¼kler
"""
from PySide6.QtCore import QThread, Signal

from core.logger import logger
from core.hata_yonetici import exc_logla


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  VERÄ° YÃœKLEYICI
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class VeriYukleyiciThread(QThread):
    """Sabitler + RKE_List + RKE_Muayene verisini arka planda yÃ¼kler."""
    veri_hazir  = Signal(dict, dict, list, list)   # sabitler, kisaltma_maps, rke_data, muayene_data
    hata_olustu = Signal(str)

    _SABIT_KODLAR = ["AnaBilimDali", "Birim", "Koruyucu_Cinsi", "Bedeni"]
    _MAP_KODLAR   = {"AnaBilimDali", "Birim", "Koruyucu_Cinsi"}

    def run(self):
        from database.sqlite_manager import SQLiteManager
        from core.di import get_registry
        db = None
        try:
            db       = SQLiteManager()
            registry = get_registry(db)

            sabitler = {}
            maps     = {k: {} for k in self._MAP_KODLAR}

            all_sabit = registry.get("Sabitler").get_all()
            for kod in self._SABIT_KODLAR:
                sabitler[kod] = []
                for satir in (x for x in all_sabit if x.get("Kod") == kod):
                    eleman   = str(satir.get("MenuEleman", "")).strip()
                    kisaltma = str(satir.get("Aciklama",   "")).strip()
                    if eleman:
                        sabitler[kod].append(eleman)
                        if kod in maps and kisaltma:
                            maps[kod][eleman] = kisaltma

            rke_data     = registry.get("RKE_List").get_all()
            muayene_data = registry.get("RKE_Muayene").get_all()

            self.veri_hazir.emit(sabitler, maps, rke_data, muayene_data)
        except Exception as e:
            exc_logla("RKEYonetim.VeriYukleyici", e)
            self.hata_olustu.emit(f"Veri yÃ¼kleme hatasÄ±: {e}")
        finally:
            if db:
                db.close()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  Ä°ÅLEM KAYDEDÄ°CÄ°
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class IslemKaydediciThread(QThread):
    """INSERT veya UPDATE iÅŸlemini arka planda yapar."""
    islem_tamam = Signal()
    hata_olustu = Signal(str)

    def __init__(self, mod: str, veri_dict: dict):
        super().__init__()
        self._mod  = mod        # "INSERT" | "UPDATE"
        self._veri = veri_dict

    def run(self):
        from database.sqlite_manager import SQLiteManager
        from core.di import get_registry
        db = None
        try:
            db       = SQLiteManager()
            registry = get_registry(db)
            repo     = registry.get("RKE_List")

            if self._mod == "INSERT":
                repo.insert(self._veri)
            elif self._mod == "UPDATE":
                repo.update(self._veri.get("KayitNo"), self._veri)

            self.islem_tamam.emit()
        except Exception as e:
            exc_logla("RKEYonetim.IslemKaydedici", e)
            self.hata_olustu.emit(f"Ä°ÅŸlem hatasÄ±: {e}")
        finally:
            if db:
                db.close()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  GEÃ‡MÄ°Å YÃœKLEYICI
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class GecmisYukleyiciThread(QThread):
    """SeÃ§ili ekipmanÄ±n muayene geÃ§miÅŸini yÃ¼kler."""
    gecmis_hazir = Signal(list)

    def __init__(self, ekipman_no: str):
        super().__init__()
        self._ekipman_no = ekipman_no

    def run(self):
        from database.sqlite_manager import SQLiteManager
        from core.di import get_registry
        db = None
        try:
            db       = SQLiteManager()
            registry = get_registry(db)
            all_data = registry.get("RKE_Muayene").get_all()
            gecmis   = [
                x for x in all_data
                if str(x.get("EkipmanNo")) == str(self._ekipman_no)
            ]
            gecmis.sort(key=lambda x: x.get("FMuayeneTarihi", ""), reverse=True)
            self.gecmis_hazir.emit(gecmis)
        except Exception as e:
            logger.error(f"GeÃ§miÅŸ yÃ¼kleme hatasÄ±: {e}")
            self.gecmis_hazir.emit([])
        finally:
            if db:
                db.close()

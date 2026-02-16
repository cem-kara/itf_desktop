# -*- coding: utf-8 -*-
"""
Bildirim Servisi
Uygulama aÃ§Ä±lÄ±ÅŸÄ±nda ve sync sonrasÄ±nda Ã§alÄ±ÅŸÄ±r; sÃ¼resi yaklaÅŸan veya
geÃ§miÅŸ kayÄ±tlarÄ± kategorize ederek BildirimPaneli'ne iletir.
"""
from datetime import datetime, timedelta

from PySide6.QtCore import QThread, Signal

from core.logger import logger
from core.paths import DB_PATH


# â”€â”€ EÅŸik tanÄ±mlarÄ± â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
ESIKLER = {
    "kalibrasyon_uyari_gun":   30,   # gÃ¼n iÃ§inde dolacak â†’ uyarÄ±
    "bakim_uyari_gun":         30,
    "ndk_uyari_gun":           60,   # NDK lisansÄ± iÃ§in daha geniÅŸ pencere
    "rke_uyari_gun":           30,
    "saglik_uyari_gun":        90,
}


class BildirimWorker(QThread):
    """
    Arka planda veritabanÄ±nÄ± sorgular ve bildirim listesini sinyal ile dÃ¶ndÃ¼rÃ¼r.

    Ã‡Ä±ktÄ± formatÄ±:
        {
            "kritik": [{"kategori": str, "mesaj": str, "grup": str,
                        "sayfa": str, "sayi": int}, ...],
            "uyari":  [...aynÄ± yapÄ±...]
        }
    """
    sonuc_hazir = Signal(dict)

    def __init__(self, db_path: str = None):
        super().__init__()
        self._db_path = db_path or DB_PATH

    # â”€â”€ Ana Ã§alÄ±ÅŸma dÃ¶ngÃ¼sÃ¼ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def run(self):
        kritik = []
        uyari  = []
        try:
            from database.sqlite_manager import SQLiteManager
            from core.di import get_registry

            db = SQLiteManager(db_path=self._db_path)
            registry = get_registry(db)
            bugun = datetime.now().date()

            # 1) Kalibrasyon
            self._kalibrasyon_kontrol(registry, bugun, kritik, uyari)

            # 2) Periyodik BakÄ±m
            self._bakim_kontrol(registry, bugun, kritik, uyari)

            # 3) NDK LisansÄ± (Cihazlar.BitisTarihi)
            self._ndk_kontrol(registry, bugun, kritik, uyari)

            # 4) RKE Muayene
            self._rke_kontrol(registry, bugun, kritik, uyari)

            # 5) Personel SaÄŸlÄ±k Takip
            self._saglik_kontrol(registry, bugun, kritik, uyari)

            db.close()

        except Exception as e:
            logger.error(f"BildirimWorker hatasÄ±: {e}")

        self.sonuc_hazir.emit({"kritik": kritik, "uyari": uyari})

    # â”€â”€ Sorgu yardÄ±mcÄ±larÄ± â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _say(self, registry, tablo, where):
        """WHERE koÅŸulunu saÄŸlayan satÄ±r sayÄ±sÄ±nÄ± dÃ¶ndÃ¼rÃ¼r; hata durumunda 0."""
        try:
            repo = registry.get(tablo)
            cur  = repo.db.execute(f"SELECT COUNT(*) FROM {tablo} WHERE {where}")
            return cur.fetchone()[0] or 0
        except Exception as e:
            logger.warning(f"Bildirim sayÄ±m hatasÄ± ({tablo}): {e}")
            return 0

    def _ekle(self, hedef: list, kategori, mesaj, grup, sayfa, sayi):
        if sayi > 0:
            hedef.append({
                "kategori": kategori,
                "mesaj":    mesaj,
                "grup":     grup,
                "sayfa":    sayfa,
                "sayi":     sayi,
            })

    # â”€â”€ Kontrol metodlarÄ± â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _kalibrasyon_kontrol(self, registry, bugun, kritik, uyari):
        bugun_str   = str(bugun)
        esik_str    = str(bugun + timedelta(days=ESIKLER["kalibrasyon_uyari_gun"]))

        gecmis = self._say(
            registry, "Kalibrasyon",
            f"BitisTarihi < '{bugun_str}' AND BitisTarihi != '' AND Durum = 'TamamlandÄ±'"
        )
        self._ekle(kritik, "Kalibrasyon", f"{gecmis} cihazÄ±n kalibrasyonu geÃ§miÅŸ",
                   "CÄ°HAZ", "Kalibrasyon Takip", gecmis)

        yaklasan = self._say(
            registry, "Kalibrasyon",
            f"BitisTarihi BETWEEN '{bugun_str}' AND '{esik_str}' AND Durum = 'TamamlandÄ±'"
        )
        self._ekle(uyari, "Kalibrasyon",
                   f"{yaklasan} kalibrasyon {ESIKLER['kalibrasyon_uyari_gun']} gÃ¼n iÃ§inde dolacak",
                   "CÄ°HAZ", "Kalibrasyon Takip", yaklasan)

    def _bakim_kontrol(self, registry, bugun, kritik, uyari):
        bugun_str = str(bugun)
        esik_str  = str(bugun + timedelta(days=ESIKLER["bakim_uyari_gun"]))

        gecmis = self._say(
            registry, "Periyodik_Bakim",
            f"PlanlananTarih < '{bugun_str}' AND Durum = 'PlanlandÄ±'"
        )
        self._ekle(kritik, "Periyodik BakÄ±m", f"{gecmis} bakÄ±m gecikmiÅŸ",
                   "CÄ°HAZ", "Periyodik BakÄ±m", gecmis)

        yaklasan = self._say(
            registry, "Periyodik_Bakim",
            f"PlanlananTarih BETWEEN '{bugun_str}' AND '{esik_str}' AND Durum = 'PlanlandÄ±'"
        )
        self._ekle(uyari, "Periyodik BakÄ±m",
                   f"{yaklasan} bakÄ±m {ESIKLER['bakim_uyari_gun']} gÃ¼n iÃ§inde planlandÄ±",
                   "CÄ°HAZ", "Periyodik BakÄ±m", yaklasan)

    def _ndk_kontrol(self, registry, bugun, kritik, uyari):
        bugun_str = str(bugun)
        esik_str  = str(bugun + timedelta(days=ESIKLER["ndk_uyari_gun"]))

        gecmis = self._say(
            registry, "Cihazlar",
            f"BitisTarihi < '{bugun_str}' AND BitisTarihi != '' AND LisansDurum != 'Pasif'"
        )
        self._ekle(kritik, "NDK LisansÄ±", f"{gecmis} cihazÄ±n NDK lisansÄ± geÃ§miÅŸ",
                   "CÄ°HAZ", "Cihaz Listesi", gecmis)

        yaklasan = self._say(
            registry, "Cihazlar",
            f"BitisTarihi BETWEEN '{bugun_str}' AND '{esik_str}' AND LisansDurum != 'Pasif'"
        )
        self._ekle(uyari, "NDK LisansÄ±",
                   f"{yaklasan} NDK lisansÄ± {ESIKLER['ndk_uyari_gun']} gÃ¼n iÃ§inde dolacak",
                   "CÄ°HAZ", "Cihaz Listesi", yaklasan)

    def _rke_kontrol(self, registry, bugun, kritik, uyari):
        bugun_str = str(bugun)
        esik_str  = str(bugun + timedelta(days=ESIKLER["rke_uyari_gun"]))

        gecmis = self._say(
            registry, "RKE_List",
            f"KontrolTarihi < '{bugun_str}' AND KontrolTarihi != '' AND Durum = 'PlanlandÄ±'"
        )
        self._ekle(kritik, "RKE Muayene", f"{gecmis} RKE muayenesi gecikmiÅŸ",
                   "RKE", "RKE Muayene", gecmis)

        yaklasan = self._say(
            registry, "RKE_List",
            f"KontrolTarihi BETWEEN '{bugun_str}' AND '{esik_str}' AND Durum = 'PlanlandÄ±'"
        )
        self._ekle(uyari, "RKE Muayene",
                   f"{yaklasan} RKE muayenesi {ESIKLER['rke_uyari_gun']} gÃ¼n iÃ§inde",
                   "RKE", "RKE Muayene", yaklasan)

    def _saglik_kontrol(self, registry, bugun, kritik, uyari):
        bugun_str = str(bugun)
        esik_str  = str(bugun + timedelta(days=ESIKLER["saglik_uyari_gun"]))

        gecmis = self._say(
            registry, "Personel_Saglik_Takip",
            f"SonrakiKontrolTarihi < '{bugun_str}' AND SonrakiKontrolTarihi != '' AND Durum != 'Pasif'"
        )
        self._ekle(kritik, "SaÄŸlÄ±k Takip", f"{gecmis} personelin muayene tarihi geÃ§miÅŸ",
                   "PERSONEL", "Saglik Takip", gecmis)

        yaklasan = self._say(
            registry, "Personel_Saglik_Takip",
            f"SonrakiKontrolTarihi BETWEEN '{bugun_str}' AND '{esik_str}' AND Durum != 'Pasif'"
        )
        self._ekle(uyari, "SaÄŸlÄ±k Takip",
                   f"{yaklasan} personelin muayenesi {ESIKLER['saglik_uyari_gun']} gÃ¼n iÃ§inde",
                   "PERSONEL", "Saglik Takip", yaklasan)



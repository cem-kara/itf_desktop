# -*- coding: utf-8 -*-
"""
Bildirim Servisi
Uygulama açılışında ve sync sonrasında çalışır; süresi yaklaşan veya
geçmiş kayıtları kategorize ederek BildirimPaneli'ne iletir.
"""
from datetime import datetime, timedelta

from PySide6.QtCore import QThread, Signal

from core.logger import logger
from core.paths import DB_PATH


# ── Eşik tanımları ──────────────────────────────────────────────────────────
ESIKLER = {
    "kalibrasyon_uyari_gun":   30,   # gün içinde dolacak → uyarı
    "bakim_uyari_gun":         30,
    "ndk_uyari_gun":           60,   # NDK lisansı için daha geniş pencere
    "rke_uyari_gun":           30,
    "saglik_uyari_gun":        90,
}


class BildirimWorker(QThread):
    """
    Arka planda veritabanını sorgular ve bildirim listesini sinyal ile döndürür.

    Çıktı formatı:
        {
            "kritik": [{"kategori": str, "mesaj": str, "grup": str,
                        "sayfa": str, "sayi": int}, ...],
            "uyari":  [...aynı yapı...]
        }
    """
    sonuc_hazir = Signal(dict)

    def __init__(self, db_path: str = None):
        super().__init__()
        self._db_path = db_path or DB_PATH

    # ── Ana çalışma döngüsü ─────────────────────────────────────────────────

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

            # 2) Periyodik Bakım
            self._bakim_kontrol(registry, bugun, kritik, uyari)

            # 3) NDK Lisansı (Cihazlar.BitisTarihi)
            self._ndk_kontrol(registry, bugun, kritik, uyari)

            # 4) RKE Muayene
            self._rke_kontrol(registry, bugun, kritik, uyari)

            # 5) Personel Sağlık Takip
            self._saglik_kontrol(registry, bugun, kritik, uyari)

            db.close()

        except Exception as e:
            logger.error(f"BildirimWorker hatası: {e}")

        self.sonuc_hazir.emit({"kritik": kritik, "uyari": uyari})

    # ── Sorgu yardımcıları ──────────────────────────────────────────────────

    def _say(self, registry, tablo, where):
        """WHERE koşulunu sağlayan satır sayısını döndürür; hata durumunda 0."""
        try:
            repo = registry.get(tablo)
            cur  = repo.db.execute(f"SELECT COUNT(*) FROM {tablo} WHERE {where}")
            return cur.fetchone()[0] or 0
        except Exception as e:
            logger.warning(f"Bildirim sayım hatası ({tablo}): {e}")
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

    # ── Kontrol metodları ───────────────────────────────────────────────────

    def _kalibrasyon_kontrol(self, registry, bugun, kritik, uyari):
        bugun_str   = str(bugun)
        esik_str    = str(bugun + timedelta(days=ESIKLER["kalibrasyon_uyari_gun"]))

        gecmis = self._say(
            registry, "Kalibrasyon",
            f"BitisTarihi < '{bugun_str}' AND BitisTarihi != '' AND Durum = 'Tamamlandı'"
        )
        self._ekle(kritik, "Kalibrasyon", f"{gecmis} cihazın kalibrasyonu geçmiş",
                   "CİHAZ", "Kalibrasyon Takip", gecmis)

        yaklasan = self._say(
            registry, "Kalibrasyon",
            f"BitisTarihi BETWEEN '{bugun_str}' AND '{esik_str}' AND Durum = 'Tamamlandı'"
        )
        self._ekle(uyari, "Kalibrasyon",
                   f"{yaklasan} kalibrasyon {ESIKLER['kalibrasyon_uyari_gun']} gün içinde dolacak",
                   "CİHAZ", "Kalibrasyon Takip", yaklasan)

    def _bakim_kontrol(self, registry, bugun, kritik, uyari):
        bugun_str = str(bugun)
        esik_str  = str(bugun + timedelta(days=ESIKLER["bakim_uyari_gun"]))

        gecmis = self._say(
            registry, "Periyodik_Bakim",
            f"PlanlananTarih < '{bugun_str}' AND Durum = 'Planlandı'"
        )
        self._ekle(kritik, "Periyodik Bakım", f"{gecmis} bakım gecikmiş",
                   "CİHAZ", "Periyodik Bakım", gecmis)

        yaklasan = self._say(
            registry, "Periyodik_Bakim",
            f"PlanlananTarih BETWEEN '{bugun_str}' AND '{esik_str}' AND Durum = 'Planlandı'"
        )
        self._ekle(uyari, "Periyodik Bakım",
                   f"{yaklasan} bakım {ESIKLER['bakim_uyari_gun']} gün içinde planlandı",
                   "CİHAZ", "Periyodik Bakım", yaklasan)

    def _ndk_kontrol(self, registry, bugun, kritik, uyari):
        bugun_str = str(bugun)
        esik_str  = str(bugun + timedelta(days=ESIKLER["ndk_uyari_gun"]))

        gecmis = self._say(
            registry, "Cihazlar",
            f"BitisTarihi < '{bugun_str}' AND BitisTarihi != '' AND LisansDurum != 'Pasif'"
        )
        self._ekle(kritik, "NDK Lisansı", f"{gecmis} cihazın NDK lisansı geçmiş",
                   "CİHAZ", "Cihaz Listesi", gecmis)

        yaklasan = self._say(
            registry, "Cihazlar",
            f"BitisTarihi BETWEEN '{bugun_str}' AND '{esik_str}' AND LisansDurum != 'Pasif'"
        )
        self._ekle(uyari, "NDK Lisansı",
                   f"{yaklasan} NDK lisansı {ESIKLER['ndk_uyari_gun']} gün içinde dolacak",
                   "CİHAZ", "Cihaz Listesi", yaklasan)

    def _rke_kontrol(self, registry, bugun, kritik, uyari):
        bugun_str = str(bugun)
        esik_str  = str(bugun + timedelta(days=ESIKLER["rke_uyari_gun"]))

        gecmis = self._say(
            registry, "RKE_List",
            f"KontrolTarihi < '{bugun_str}' AND KontrolTarihi != '' AND Durum = 'Planlandı'"
        )
        self._ekle(kritik, "RKE Muayene", f"{gecmis} RKE muayenesi gecikmiş",
                   "RKE", "RKE Muayene", gecmis)

        yaklasan = self._say(
            registry, "RKE_List",
            f"KontrolTarihi BETWEEN '{bugun_str}' AND '{esik_str}' AND Durum = 'Planlandı'"
        )
        self._ekle(uyari, "RKE Muayene",
                   f"{yaklasan} RKE muayenesi {ESIKLER['rke_uyari_gun']} gün içinde",
                   "RKE", "RKE Muayene", yaklasan)

    def _saglik_kontrol(self, registry, bugun, kritik, uyari):
        bugun_str = str(bugun)
        esik_str  = str(bugun + timedelta(days=ESIKLER["saglik_uyari_gun"]))

        gecmis = self._say(
            registry, "Personel_Saglik_Takip",
            f"SonrakiKontrolTarihi < '{bugun_str}' AND SonrakiKontrolTarihi != '' AND Durum != 'Pasif'"
        )
        self._ekle(kritik, "Sağlık Takip", f"{gecmis} personelin muayene tarihi geçmiş",
                   "PERSONEL", "Saglik Takip", gecmis)

        yaklasan = self._say(
            registry, "Personel_Saglik_Takip",
            f"SonrakiKontrolTarihi BETWEEN '{bugun_str}' AND '{esik_str}' AND Durum != 'Pasif'"
        )
        self._ekle(uyari, "Sağlık Takip",
                   f"{yaklasan} personelin muayenesi {ESIKLER['saglik_uyari_gun']} gün içinde",
                   "PERSONEL", "Saglik Takip", yaklasan)



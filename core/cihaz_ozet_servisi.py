# core/cihaz_ozet_servisi.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Cihaz Özet Servisi
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from typing import Dict, Any, Optional
from datetime import datetime

from core.logger import logger
from core.paths import DB_PATH
from database.sqlite_manager import SQLiteManager
from database.repository_registry import RepositoryRegistry


class CihazOzetServisi:
    """
    Cihaz özette kullanılan verileri hazırlayan servis.
    Dashboard ve cihaz sayfasında gösterilecek veriler.
    
    Kullanım:
        ozet = CihazOzetServisi()
        veriler = ozet.get_dashboard_ozeti()
    """

    def __init__(self, db_path: str = DB_PATH):
        try:
            self.db = SQLiteManager(db_path)
            self.registry = RepositoryRegistry(self.db)
            self.cihaz_repo = self.registry.cihaz
        except Exception as e:
            logger.error(f"CihazOzetServisi başlatılırken hata: {e}")
            self.db = None
            self.registry = None
            self.cihaz_repo = None

    # ── Temel Sayımlar ─────────────────────────────────────────

    def get_toplam_cihaz(self) -> int:
        """Toplam cihaz sayısı."""
        try:
            return self.cihaz_repo.count_all() if self.cihaz_repo else 0
        except Exception as e:
            logger.error(f"Toplam cihaz sayısı alınırken hata: {e}")
            return 0

    def get_arizali_cihaz_sayisi(self) -> int:
        """Arızası olan cihaz sayısı."""
        try:
            if not self.cihaz_repo:
                return 0
            arizali = self.cihaz_repo.get_arizali_cihazlar()
            return len(arizali)
        except Exception as e:
            logger.warning(f"Arızalı cihaz sayısı alınırken hata: {e}")
            return 0

    def get_kalibrasyon_vade_bitmek_uzere_sayisi(self, gun: int = 30) -> int:
        """
        Kalibrasyon vade bitişi yaklaşan cihaz sayısı.
        
        Args:
            gun: Kaç gün içinde bitmek üzere olanları say
            
        Returns:
            Cihaz sayısı
        """
        try:
            if not self.cihaz_repo:
                return 0
            cihazlar = self.cihaz_repo.get_kalibrasyon_vade_bitmek_uzere(gun)
            return len(cihazlar)
        except Exception as e:
            logger.warning(f"Kalibrasyon vade sorgusu hatası: {e}")
            return 0

    # ── Cihaz Tipi Dağılımı ────────────────────────────────────

    def get_cihaz_tipi_dagilimi(self) -> Dict[str, int]:
        """
        Cihazların tiplerine göre dağılımı.
        
        Returns:
            {"CT": 5, "Rentgen": 3, ...}
        """
        try:
            sql = """
            SELECT CihazTipi, COUNT(*) as cnt
            FROM Cihazlar
            GROUP BY CihazTipi
            ORDER BY cnt DESC
            """
            rows = self.db.execute(sql).fetchall()
            
            dagilim = {}
            for row in rows:
                dagilim[row["CihazTipi"]] = row["cnt"]
            
            return dagilim
        except Exception as e:
            logger.warning(f"Cihaz tipi dağılımı sorgusu hatası: {e}")
            return {}

    def get_marka_dagilimi(self) -> Dict[str, int]:
        """
        Cihazların markalara göre dağılımı.
        
        Returns:
            {"Siemens": 4, "Philips": 2, ...}
        """
        try:
            sql = """
            SELECT Marka, COUNT(*) as cnt
            FROM Cihazlar
            GROUP BY Marka
            ORDER BY cnt DESC
            """
            rows = self.db.execute(sql).fetchall()
            
            dagilim = {}
            for row in rows:
                dagilim[row["Marka"]] = row["cnt"]
            
            return dagilim
        except Exception as e:
            logger.warning(f"Marka dağılımı sorgusu hatası: {e}")
            return {}

    # ── Arıza İstatistikleri ───────────────────────────────────

    def get_ariza_istatistikleri(self) -> Dict[str, Any]:
        """
        Arıza ile ilgili istatistikler.
        
        Returns:
            {'aktif_ariza': int, 'cozulen': int, ...}
        """
        try:
            # Aktif arızalar
            sql_aktif = """
            SELECT COUNT(*) as cnt
            FROM Cihaz_Ariza
            WHERE DurumAf IS NULL
            """
            aktif = self.db.execute(sql_aktif).fetchone()
            aktif_ariza = aktif["cnt"] if aktif else 0
            
            # Çözülen arızalar (bu ay)
            sql_cozulen = """
            SELECT COUNT(*) as cnt
            FROM Cihaz_Ariza
            WHERE DurumAf IS NOT NULL
            AND STRFTIME('%Y-%m', DurumAf) = STRFTIME('%Y-%m', date('now'))
            """
            cozulen = self.db.execute(sql_cozulen).fetchone()
            cozulen_ariza = cozulen["cnt"] if cozulen else 0
            
            return {
                "aktif_ariza": aktif_ariza,
                "bu_ay_cozulen": cozulen_ariza,
            }
        except Exception as e:
            logger.warning(f"Arıza istatistikleri sorgusu hatası: {e}")
            return {}

    # ── Kalibrasyon İstatistikleri ─────────────────────────────

    def get_kalibrasyon_durumu(self) -> Dict[str, Any]:
        """
        Kalibrasyon ile ilgili durumu.
        
        Returns:
            {'bitmek_uzere_30_gun': int, 'vade_gecmis': int, ...}
        """
        try:
            # Vade 30 gün içinde bitecek
            sql_30 = """
            SELECT COUNT(DISTINCT c.Cihazid) as cnt
            FROM Cihazlar c
            LEFT JOIN Kalibrasyon k ON c.Cihazid = k.Cihazid
            WHERE k.KalibrasiyonVadesi 
                BETWEEN date('now') 
                AND date('now', '+30 days')
            """
            result_30 = self.db.execute(sql_30).fetchone()
            bitmek_uzere = result_30["cnt"] if result_30 else 0
            
            # Vade geçmiş
            sql_gecmis = """
            SELECT COUNT(DISTINCT c.Cihazid) as cnt
            FROM Cihazlar c
            LEFT JOIN Kalibrasyon k ON c.Cihazid = k.Cihazid
            WHERE k.KalibrasiyonVadesi < date('now')
            """
            result_gecmis = self.db.execute(sql_gecmis).fetchone()
            vade_gecmis = result_gecmis["cnt"] if result_gecmis else 0
            
            return {
                "bitmek_uzere_30_gun": bitmek_uzere,
                "vade_gecmis": vade_gecmis,
            }
        except Exception as e:
            logger.warning(f"Kalibrasyon durumu sorgusu hatası: {e}")
            return {}

    # ── Periyodik Bakım İstatistikleri ─────────────────────────

    def get_bakim_durumu(self) -> Dict[str, Any]:
        """
        Periyodik bakım durumu.
        
        Returns:
            {'beklemede': int, 'tamamlandi': int, ...}
        """
        try:
            sql = """
            SELECT 
                COUNT(CASE WHEN Durum = 'Beklemede' THEN 1 END) as beklemede,
                COUNT(CASE WHEN Durum = 'Tamamlandı' THEN 1 END) as tamamlandi,
                COUNT(CASE WHEN STRFTIME('%Y-%m', BakimTarihi) = STRFTIME('%Y-%m', date('now')) THEN 1 END) as bu_ay
            FROM Periyodik_Bakim
            """
            result = self.db.execute(sql).fetchone()
            
            return {
                "beklemede": result["beklemede"] if result else 0,
                "tamamlandi": result["tamamlandi"] if result else 0,
                "bu_ay": result["bu_ay"] if result else 0,
            }
        except Exception as e:
            logger.warning(f"Bakım durumu sorgusu hatası: {e}")
            return {}

    # ── Dashboard Özeti ────────────────────────────────────────

    def get_dashboard_ozeti(self) -> Dict[str, Any]:
        """
        Dashboard için tüm gerekli özet veriler.
        
        Returns:
            Çeşitli istatistikler içeren sözlük
        """
        try:
            ozet = {
                "timestamp": datetime.now().isoformat(),
                "cihaz": {
                    "toplam": self.get_toplam_cihaz(),
                    "arizali": self.get_arizali_cihaz_sayisi(),
                    "kalibrasyon_vade_bitmek_uzere": self.get_kalibrasyon_vade_bitmek_uzere_sayisi(),
                },
                "tipler": self.get_cihaz_tipi_dagilimi(),
                "markalar": self.get_marka_dagilimi(),
                "ariza": self.get_ariza_istatistikleri(),
                "kalibrasyon": self.get_kalibrasyon_durumu(),
                "bakim": self.get_bakim_durumu(),
            }
            
            # Detaylı istatistikler
            if self.cihaz_repo:
                stats = self.cihaz_repo.get_statistics()
                ozet["cihaz_detay"] = stats
            
            return ozet
        except Exception as e:
            logger.error(f"Dashboard özeti hazırlanırken hata: {e}")
            return {}

    # ── Uyarı & Riskler ────────────────────────────────────────

    def get_uygari_listesi(self) -> Dict[str, Any]:
        """
        Sistem tarafından oluşturulan uyarılar.
        
        Returns:
            {'kritik': [...], 'uyari': [...]}
        """
        try:
            uyarilar = {
                "kritik": [],
                "uyari": [],
            }
            
            # Kalibrasyon vade geçmiş
            vade_gecmis = self.get_kalibrasyon_durumu().get("vade_gecmis", 0)
            if vade_gecmis > 0:
                uyarilar["kritik"].append(
                    f"{vade_gecmis} cihazın kalibrasyon vade tarihi geçmiş"
                )
            
            # Arızalı cihazlar
            arizali = self.get_arizali_cihaz_sayisi()
            if arizali > 0:
                uyarilar["uyari"].append(
                    f"{arizali} cihazın aktif arızası var"
                )
            
            # Kalibrasyon bitişi yaklaşıyor
            bitmek_uzere = self.get_kalibrasyon_durumu().get("bitmek_uzere_30_gun", 0)
            if bitmek_uzere > 0:
                uyarilar["uyari"].append(
                    f"{bitmek_uzere} cihazın kalibrasyon vade tarihi 30 gün içinde bitiyor"
                )
            
            return uyarilar
        except Exception as e:
            logger.warning(f"Uyarı listesi hazırlanırken hata: {e}")
            return {"kritik": [], "uyari": []}

    # ── Sağlık Check ────────────────────────────────────────────

    def is_veritabani_basli(self) -> bool:
        """Veritabanı başlı mı."""
        return self.db is not None and self.cihaz_repo is not None

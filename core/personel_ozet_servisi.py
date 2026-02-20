# core/personel_ozet_servisi.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Personel Özet Servisi
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from core.logger import logger
from core.paths import DB_PATH
from database.sqlite_manager import SQLiteManager
from database.repository_registry import RepositoryRegistry


class PersonelOzetServisi:
    """
    Personel özette kullanılan verileri hazırlayan servis.
    Dashboard ve ana sayfada gösterilecek veriler.
    
    Kullanım:
        ozet = PersonelOzetServisi()
        veriler = ozet.get_dashboard_ozeti()
    """

    def __init__(self, db_path: str = DB_PATH):
        try:
            self.db = SQLiteManager(db_path)
            self.registry = RepositoryRegistry(self.db)
            self.personel_repo = self.registry.personel
        except Exception as e:
            logger.error(f"PersonelOzetServisi başlatılırken hata: {e}")
            self.db = None
            self.registry = None
            self.personel_repo = None

    # ── Temel Sayımlar ─────────────────────────────────────────

    def get_toplam_personel(self) -> int:
        """Toplam personel sayısı."""
        try:
            return self.personel_repo.count_all() if self.personel_repo else 0
        except Exception as e:
            logger.error(f"Toplam personel sayısı alınırken hata: {e}")
            return 0

    def get_aktif_personel_sayisi(self) -> int:
        """Aktif personel sayısı."""
        try:
            return self.personel_repo.count_by_durum("Aktif") if self.personel_repo else 0
        except Exception as e:
            logger.error(f"Aktif personel sayısı alınırken hata: {e}")
            return 0

    def get_pasif_personel_sayisi(self) -> int:
        """Pasif/İstifa personel sayısı."""
        try:
            if not self.personel_repo:
                return 0
            
            toplam = self.personel_repo.count_all()
            aktif = self.personel_repo.count_by_durum("Aktif")
            return toplam - aktif
        except Exception as e:
            logger.error(f"Pasif personel sayısı alınırken hata: {e}")
            return 0

    # ── İzin İstatistikleri ────────────────────────────────────

    def get_izin_istatistikleri(self) -> Dict[str, Any]:
        """
        İzin ile ilgili istatistikler.
        
        Returns:
            {'toplam_hak': int, 'kullanilan': int, 'kalan': int, ...}
        """
        try:
            sql = """
            SELECT 
                COUNT(*) as toplam_kayit,
                SUM(COALESCE(Gun, 0)) as toplam_gun
            FROM Izin_Giris
            WHERE YEAR(BaslamaTarihi) = YEAR(CURRENT_DATE)
            """
            result = self.db.execute(sql).fetchone()
            
            return {
                "toplam_kayit": result["toplam_kayit"] if result else 0,
                "toplam_gun": result["toplam_gun"] if result else 0,
            }
        except Exception as e:
            logger.warning(f"İzin istatistikleri alınırken hata: {e}")
            return {}

    def get_yakin_muayeneler(self, gun: int = 30) -> int:
        """
        X gün içinde muayenesi olması gerekenler.
        
        Args:
            gun: Kaç gün içine bakılacak
            
        Returns:
            Muayenesi yaklaşan personel sayısı
        """
        try:
            sql = """
            SELECT COUNT(*) as cnt
            FROM Personel
            WHERE MuayeneTarihi IS NOT NULL
            AND MuayeneTarihi 
                BETWEEN DATE('now') 
                AND DATE('now', '+? days')
            """
            result = self.db.execute(sql, [gun]).fetchone()
            return result["cnt"] if result else 0
        except Exception as e:
            logger.warning(f"Yakın muayene sorgusu hatası: {e}")
            return 0

    # ── FHSZ İstatistikleri ────────────────────────────────────

    def get_fhsz_ozeti(self) -> Dict[str, Any]:
        """
        FHSZ (Fiili Hizmet Süresi Zammı) özeti.
        
        Returns:
            {'toplam_personel': int, 'hak_edecek_personel': int, ...}
        """
        try:
            sql = """
            SELECT 
                COUNT(DISTINCT Personelid) as toplam_personel,
                SUM(CASE WHEN FiiliCalismaSaat >= 10000 THEN 1 ELSE 0 END) as hak_edecek
            FROM FHSZ_Puantaj
            WHERE AitYil = YEAR(CURRENT_DATE)
            """
            result = self.db.execute(sql).fetchone()
            
            return {
                "toplam_personel": result["toplam_personel"] if result else 0,
                "hak_edecek": result["hak_edecek"] if result else 0,
            }
        except Exception as e:
            logger.warning(f"FHSZ özeti alınırken hata: {e}")
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
                "personel": {
                    "toplam": self.get_toplam_personel(),
                    "aktif": self.get_aktif_personel_sayisi(),
                    "pasif": self.get_pasif_personel_sayisi(),
                    "yakin_muayene": self.get_yakin_muayeneler(),
                },
                "izin": self.get_izin_istatistikleri(),
                "fhsz": self.get_fhsz_ozeti(),
            }
            
            # Detaylı istatistikler
            if self.personel_repo:
                stats = self.personel_repo.get_statistics()
                ozet["personel_detay"] = stats
            
            return ozet
        except Exception as e:
            logger.error(f"Dashboard özeti hazırlanırken hata: {e}")
            return {}

    # ── Raporlar & Listeler ────────────────────────────────────

    def get_gunluk_aktifleme_raporu(self) -> Dict[str, Any]:
        """
        Günlük personel aktiviteleri raporu.
        
        Returns:
            {"yeni_eklemeleri": int, "degisen": int, ...}
        """
        try:
            simdi = datetime.now()
            bugün_basında = simdi.replace(hour=0, minute=0, second=0, microsecond=0)
            
            sql = """
            SELECT 
                COUNT(*) as toplam_degisiklik,
                COUNT(CASE WHEN updated_at >= ? THEN 1 END) as bugün_degisen
            FROM Personel
            WHERE updated_at >= DATE('now', '-7 days')
            """
            result = self.db.execute(sql, [bugün_basında.isoformat()]).fetchone()
            
            return {
                "toplam_degisiklik_haftada": result["toplam_degisiklik"] if result else 0,
                "bugün_degisen": result["bugün_degisen"] if result else 0,
            }
        except Exception as e:
            logger.warning(f"Günlük aktivite raporu hatası: {e}")
            return {}

    def get_gorev_yeri_dagilimi(self) -> Dict[str, int]:
        """
        Personellerin görev yerlerine göre dağılımı.
        
        Returns:
            {"Görev Yeri": sayı, ...}
        """
        try:
            sql = """
            SELECT GorevYeri, COUNT(*) as cnt
            FROM Personel
            WHERE Durum = 'Aktif'
            GROUP BY GorevYeri
            ORDER BY cnt DESC
            """
            rows = self.db.execute(sql).fetchall()
            
            dagilim = {}
            for row in rows:
                dagilim[row["GorevYeri"]] = row["cnt"]
            
            return dagilim
        except Exception as e:
            logger.warning(f"Görev yeri dağılımı sorgusu hatası: {e}")
            return {}

    def get_unvan_dagilimi(self) -> Dict[str, int]:
        """
        Personellerin unvanlarına göre dağılımı.
        
        Returns:
            {"Unvan": sayı, ...}
        """
        try:
            sql = """
            SELECT KadroUnvani, COUNT(*) as cnt
            FROM Personel
            WHERE Durum = 'Aktif'
            GROUP BY KadroUnvani
            ORDER BY cnt DESC
            """
            rows = self.db.execute(sql).fetchall()
            
            dagilim = {}
            for row in rows:
                dagilim[row["KadroUnvani"]] = row["cnt"]
            
            return dagilim
        except Exception as e:
            logger.warning(f"Unvan dağılımı sorgusu hatası: {e}")
            return {}

    # ── Sağlık Check ────────────────────────────────────────────

    def is_veritabani_basli(self) -> bool:
        """Veritabanı başlı mı."""
        return self.db is not None and self.personel_repo is not None

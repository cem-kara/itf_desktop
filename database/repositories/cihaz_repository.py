# database/repositories/cihaz_repository.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Cihaz Verileri Repository
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from typing import Dict, List, Optional, Any

from core.logger import logger
from database.base_repository import BaseRepository
from database.table_config import TABLES


class CihazRepository(BaseRepository):
    """
    Cihaz tablosu CRUD ve özel operasyonları.
    
    Kullanım:
        registry = RepositoryRegistry(db)
        repo = registry.cihaz
        
        # Cihaz bilgilerini al
        ct = repo.get_by_pk("CT001")
        
        # Cihaz tipine göre filtrele
        rentgen = repo.get_by_tip("Rentgen")
        
        # Kalibrasyon vadesi bitmek üzere olan cihazlar
        urgen = repo.get_kalibrasyon_vade_bitmek_uzere()
    """

    def __init__(self, db, table_name: str = "Cihazlar"):
        config = TABLES.get(table_name, {})
        super().__init__(
            db=db,
            table_name=table_name,
            pk=config.get("pk", "Cihazid"),
            columns=config.get("columns", []),
            has_sync=True,
            date_fields=config.get("date_fields", []),
        )

    # ── Temel Sorgular ──────────────────────────────────────────

    def get_by_pk(self, cihaz_id: str) -> Optional[Dict[str, Any]]:
        """
        Cihaz ID'ye göre cihaz bilgilerini al.
        
        Args:
            cihaz_id: Cihaz ID
            
        Returns:
            Cihaz sözlüğü veya None
        """
        sql = f"SELECT * FROM {self.table} WHERE Cihazid = ?"
        result = self.db.execute(sql, [cihaz_id]).fetchone()
        return dict(result) if result else None

    def get_all(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Tüm cihazları liste.
        
        Args:
            limit: Maksimum satır sayısı (None = tümü)
            
        Returns:
            Cihaz listesi
        """
        sql = f"SELECT * FROM {self.table} ORDER BY Marka, Model"
        if limit:
            sql += f" LIMIT {limit}"
        
        rows = self.db.execute(sql).fetchall()
        return [dict(row) for row in rows]

    def get_by_tip(self, cihaz_tipi: str) -> List[Dict[str, Any]]:
        """
        Cihaz tipine göre cihazları filtrele.
        
        Args:
            cihaz_tipi: Cihaz tipi (CT, Rentgen, vb)
            
        Returns:
            Cihaz listesi
        """
        sql = f"""
        SELECT * FROM {self.table}
        WHERE CihazTipi = ?
        ORDER BY Marka, Model
        """
        rows = self.db.execute(sql, [cihaz_tipi]).fetchall()
        return [dict(row) for row in rows]

    def get_by_marka(self, marka: str) -> List[Dict[str, Any]]:
        """
        Markaya göre cihazları filtrele.
        
        Args:
            marka: Cihaz markası
            
        Returns:
            Cihaz listesi
        """
        sql = f"""
        SELECT * FROM {self.table}
        WHERE Marka = ?
        ORDER BY Model
        """
        rows = self.db.execute(sql, [marka]).fetchall()
        return [dict(row) for row in rows]

    # ── Sayma İşlemleri ────────────────────────────────────────

    def count_all(self) -> int:
        """Toplam cihaz sayısı."""
        sql = f"SELECT COUNT(*) as cnt FROM {self.table}"
        result = self.db.execute(sql).fetchone()
        return result["cnt"] if result else 0

    def count_by_tip(self, cihaz_tipi: str) -> int:
        """Cihaz tipine göre sayı."""
        sql = f"SELECT COUNT(*) as cnt FROM {self.table} WHERE CihazTipi = ?"
        result = self.db.execute(sql, [cihaz_tipi]).fetchone()
        return result["cnt"] if result else 0

    # ── Sayfalama (Lazy-loading) ──────────────────────────────

    def get_paginated(self, page: int = 1, page_size: int = 100) -> tuple[List[Dict[str, Any]], int]:
        """
        Cihaz kayıtlarını sayfalı şekilde getirir.

        Args:
            page: Sayfa numarası (1-based)
            page_size: Sayfa başına kayıt sayısı

        Returns:
            (cihaz_listesi, toplam_kayit)
        """
        try:
            if page < 1:
                page = 1
            offset = (page - 1) * page_size

            sql = f"""
            SELECT * FROM {self.table}
            ORDER BY Marka, Model
            LIMIT {page_size} OFFSET {offset}
            """
            rows = self.db.execute(sql).fetchall()
            cihazlar = [dict(row) for row in rows]

            total = self.count_all()
            return cihazlar, total
        except Exception as e:
            logger.warning(f"Cihaz sayfalama hatası: {e}")
            return self.get_all(), self.count_all()

    # ── Arıza & Bakım İşlemleri ────────────────────────────────

    def get_arizali_cihazlar(self) -> List[Dict[str, Any]]:
        """
        Arızası olan cihazları al.
        
        Returns:
            Arızalı cihaz listesi
        """
        try:
            # Arıza tablosundan cihazid'lere göre join
            sql = f"""
            SELECT DISTINCT c.* FROM {self.table} c
            LEFT JOIN Cihaz_Ariza ca ON c.Cihazid = ca.Cihazid
            WHERE ca.Cihazid IS NOT NULL
            AND ca.DurumAf IS NULL
            ORDER BY c.Marka, c.Model
            """
            rows = self.db.execute(sql).fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.warning(f"Arızalı cihazlar listelenirken hata: {e}")
            return []

    # ── Kalibrasyon İşlemleri ──────────────────────────────────

    def get_kalibrasyon_vade_bitmek_uzere(self, gun: int = 30) -> List[Dict[str, Any]]:
        """
        Kalibrasyon vade bitişi yaklaşan cihazları al.
        
        Args:
            gun: Kaç gün içinde bitmek üzere olanları al (default: 30)
            
        Returns:
            Cihaz listesi
        """
        try:
            sql = f"""
            SELECT DISTINCT c.* FROM {self.table} c
            LEFT JOIN Kalibrasyon k ON c.Cihazid = k.Cihazid
            WHERE k.KalibrasiyonVadesi IS NOT NULL
            AND k.KalibrasiyonVadesi 
                BETWEEN date('now') 
                AND date('now', '+{gun} days')
            ORDER BY k.KalibrasiyonVadesi ASC
            """
            rows = self.db.execute(sql).fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.warning(f"Kalibrasyon vade sorgusu hatası: {e}")
            return []

    # ── Arama & Filtreleme ─────────────────────────────────────

    def search_by_seri_no(self, seri_no: str) -> List[Dict[str, Any]]:
        """
        Seri no'ya göre cihaz arama.
        
        Args:
            seri_no: Cihaz seri numarası
            
        Returns:
            Cihaz listesi
        """
        sql = f"""
        SELECT * FROM {self.table}
        WHERE SeriNo LIKE ? OR NDKSeriNo LIKE ?
        """
        rows = self.db.execute(sql, [f"%{seri_no}%", f"%{seri_no}%"]).fetchall()
        return [dict(row) for row in rows]

    def search_by_model(self, model: str) -> List[Dict[str, Any]]:
        """
        Model adı ile arama (case-insensitive).
        
        Args:
            model: Cihaz modeli
            
        Returns:
            Cihaz listesi
        """
        sql = f"""
        SELECT * FROM {self.table}
        WHERE LOWER(Model) LIKE LOWER(?)
        ORDER BY Marka
        """
        rows = self.db.execute(sql, [f"%{model}%"]).fetchall()
        return [dict(row) for row in rows]

    # ── Güncelleme & Silme ─────────────────────────────────────

    def delete(self, cihaz_id: str) -> bool:
        """
        Cihaz kaydını sil.
        
        Args:
            cihaz_id: Cihaz ID
            
        Returns:
            Başarılıysa True
        """
        try:
            sql = f"DELETE FROM {self.table} WHERE Cihazid = ?"
            self.db.execute(sql, [cihaz_id])
            logger.info(f"Cihaz silindi: {cihaz_id}")
            return True
        except Exception as e:
            logger.error(f"Cihaz silinirken hata: {e}")
            return False

    # ── İstatistikler ──────────────────────────────────────────

    def get_statistics(self) -> Dict[str, Any]:
        """
        Cihaz istatistikleri.
        
        Returns:
            {'toplam': int, 'tipler': {...}, 'arizali_sayisi': int, ...}
        """
        try:
            toplam = self.count_all()
            arizali = len(self.get_arizali_cihazlar())
            kalibrasyon_vade = len(self.get_kalibrasyon_vade_bitmek_uzere())
            
            # Cihaz tiplerini say
            tipler = {}
            sql = f"""
            SELECT CihazTipi, COUNT(*) as cnt
            FROM {self.table}
            GROUP BY CihazTipi
            """
            rows = self.db.execute(sql).fetchall()
            for row in rows:
                tipler[row["CihazTipi"]] = row["cnt"]
            
            return {
                "toplam": toplam,
                "arizali": arizali,
                "kalibrasyon_vade_bitmek_uzere": kalibrasyon_vade,
                "tipler": tipler,
            }
        except Exception as e:
            logger.error(f"İstatistik hesaplanırken hata: {e}")
            return {}

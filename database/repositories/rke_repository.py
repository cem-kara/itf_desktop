# database/repositories/rke_repository.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RKE Verileri Repository
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from typing import Dict, List, Optional, Any

from core.logger import logger
from database.base_repository import BaseRepository
from database.table_config import TABLES


class RKERepository(BaseRepository):
    """
    RKE (Radyoloji Kalite Envanteri) tablosu CRUD ve özel operasyonları.
    
    Kullanım:
        registry = RepositoryRegistry(db)
        repo = registry.rke
        
        # RKE listesini al
        rke_list = repo.get_all()
        
        # Uygunluk durumuna göre filtrele
        uygun = repo.get_by_uygunluk("Uygun")
        
        # Duruma göre istatistik
        stats = repo.get_statistics()
    """

    def __init__(self, db, table_name: str = "RKE_List"):
        config = TABLES.get(table_name, {})
        super().__init__(
            db=db,
            table_name=table_name,
            pk=config.get("pk", "RKEID"),
            columns=config.get("columns", []),
            has_sync=True,
            date_fields=config.get("date_fields", []),
        )

    # ── Temel Sorgular ──────────────────────────────────────────

    def get_by_pk(self, rke_id: str) -> Optional[Dict[str, Any]]:
        """
        RKE ID'ye göre RKE bilgilerini al.
        
        Args:
            rke_id: RKE ID
            
        Returns:
            RKE sözlüğü veya None
        """
        sql = f"SELECT * FROM {self.table} WHERE RKEID = ?"
        result = self.db.execute(sql, [rke_id]).fetchone()
        return dict(result) if result else None

    def get_all(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Tüm RKE envanteri listesi.
        
        Args:
            limit: Maksimum satır sayısı (None = tümü)
            
        Returns:
            RKE listesi
        """
        sql = f"SELECT * FROM {self.table} ORDER BY RKEID DESC"
        if limit:
            sql += f" LIMIT {limit}"
        
        rows = self.db.execute(sql).fetchall()
        return [dict(row) for row in rows]

    def get_by_uygunluk(self, uygunluk: str) -> List[Dict[str, Any]]:
        """
        Uygunluk durumuna göre RKE'leri filtrele.
        
        Args:
            uygunluk: Uygunluk durumu (Uygun, Koşullu Uygun, Uygun Değil, vb)
            
        Returns:
            RKE listesi
        """
        try:
            sql = f"""
            SELECT * FROM {self.table}
            WHERE Uygunluk = ?
            ORDER BY RKEID DESC
            """
            rows = self.db.execute(sql, [uygunluk]).fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.warning(f"Uygunluk sorgusu hatası: {e}")
            return []

    def get_by_cihaz_tipi(self, cihaz_tipi: str) -> List[Dict[str, Any]]:
        """
        Cihaz tipine göre RKE'leri filtrele.
        
        Args:
            cihaz_tipi: Cihaz tipi (CT, Rentgen, vb)
            
        Returns:
            RKE listesi
        """
        sql = f"""
        SELECT * FROM {self.table}
        WHERE CihazTipi = ?
        ORDER BY RKEID DESC
        """
        rows = self.db.execute(sql, [cihaz_tipi]).fetchall()
        return [dict(row) for row in rows]

    # ── Sayma İşlemleri ────────────────────────────────────────

    def count_all(self) -> int:
        """Toplam RKE sayısı."""
        sql = f"SELECT COUNT(*) as cnt FROM {self.table}"
        result = self.db.execute(sql).fetchone()
        return result["cnt"] if result else 0

    def count_by_uygunluk(self, uygunluk: str) -> int:
        """Uygunluk durumuna göre RKE sayısı."""
        try:
            sql = f"SELECT COUNT(*) as cnt FROM {self.table} WHERE Uygunluk = ?"
            result = self.db.execute(sql, [uygunluk]).fetchone()
            return result["cnt"] if result else 0
        except Exception:
            return 0

    def count_uygun(self) -> int:
        """Uygun olan RKE sayısı."""
        return self.count_by_uygunluk("Uygun")

    def count_kosullu_uygun(self) -> int:
        """Koşullu uygun olan RKE sayısı."""
        return self.count_by_uygunluk("Koşullu Uygun")

    # ── Arama & Filtreleme ─────────────────────────────────────

    def search_by_cihaz_adi(self, cihaz_adi: str) -> List[Dict[str, Any]]:
        """
        Cihaz adı ile arama (case-insensitive).
        
        Args:
            cihaz_adi: Cihaz adı
            
        Returns:
            RKE listesi
        """
        sql = f"""
        SELECT * FROM {self.table}
        WHERE LOWER(CihazAdi) LIKE LOWER(?)
        ORDER BY RKEID DESC
        """
        rows = self.db.execute(sql, [f"%{cihaz_adi}%"]).fetchall()
        return [dict(row) for row in rows]

    def search_by_muayene_tarihi(self, tarih: str) -> List[Dict[str, Any]]:
        """
        Muayene tarihine göre RKE'leri bul.
        
        Args:
            tarih: Muayene tarihi (YYYY-MM-DD)
            
        Returns:
            RKE listesi
        """
        try:
            sql = f"""
            SELECT * FROM {self.table}
            WHERE MuayeneTarihi = ?
            ORDER BY RKEID DESC
            """
            rows = self.db.execute(sql, [tarih]).fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.warning(f"Tarih sorgusu hatası: {e}")
            return []

    # ── Güncelleme & Silme ─────────────────────────────────────

    def update_uygunluk(self, rke_id: str, yeni_uygunluk: str, not_text: Optional[str] = None) -> bool:
        """
        RKE uygunluk durumunu güncelle.
        
        Args:
            rke_id: RKE ID
            yeni_uygunluk: Yeni uygunluk durumu
            not_text: İsteğe bağlı not
            
        Returns:
            Başarılıysa True
        """
        try:
            data = {"Uygunluk": yeni_uygunluk}
            if not_text:
                data["Not"] = not_text
            
            self.update(rke_id, data)
            logger.info(f"RKE uygunluğu güncellendi: {rke_id} → {yeni_uygunluk}")
            return True
        except Exception as e:
            logger.error(f"RKE uygunluğu güncellenirken hata: {e}")
            return False

    def delete(self, rke_id: str) -> bool:
        """
        RKE kaydını sil.
        
        Args:
            rke_id: RKE ID
            
        Returns:
            Başarılıysa True
        """
        try:
            sql = f"DELETE FROM {self.table} WHERE RKEID = ?"
            self.db.execute(sql, [rke_id])
            logger.info(f"RKE silindi: {rke_id}")
            return True
        except Exception as e:
            logger.error(f"RKE silinirken hata: {e}")
            return False

    # ── İstatistikler ──────────────────────────────────────────

    def get_statistics(self) -> Dict[str, Any]:
        """
        RKE istatistikleri.
        
        Returns:
            {'toplam': int, 'uygun': int, 'kosullu_uygun': int, 'uygun_degil': int, 'tipler': {...}}
        """
        try:
            toplam = self.count_all()
            uygun = self.count_uygun()
            kosullu_uygun = self.count_kosullu_uygun()
            uygun_degil = toplam - uygun - kosullu_uygun
            
            # Cihaz tiplerine göre dağılım
            tipler = {}
            sql = f"""
            SELECT CihazTipi, COUNT(*) as cnt
            FROM {self.table}
            GROUP BY CihazTipi
            """
            rows = self.db.execute(sql).fetchall()
            for row in rows:
                tipler[row["CihazTipi"]] = row["cnt"]
            
            # Uygunluk dağılımı
            uygunluk_dagilimi = {}
            sql = f"""
            SELECT Uygunluk, COUNT(*) as cnt
            FROM {self.table}
            GROUP BY Uygunluk
            """
            rows = self.db.execute(sql).fetchall()
            for row in rows:
                uygunluk_dagilimi[row["Uygunluk"]] = row["cnt"]
            
            return {
                "toplam": toplam,
                "uygun": uygun,
                "kosullu_uygun": kosullu_uygun,
                "uygun_degil": uygun_degil,
                "tipler": tipler,
                "uygunluk_dagilimi": uygunluk_dagilimi,
            }
        except Exception as e:
            logger.error(f"İstatistik hesaplanırken hata: {e}")
            return {}

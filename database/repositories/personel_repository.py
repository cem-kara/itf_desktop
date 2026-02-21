# database/repositories/personel_repository.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Personel Verileri Repository
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from typing import Dict, List, Optional, Any
from datetime import datetime

from core.logger import logger
from database.base_repository import BaseRepository
from database.table_config import TABLES


class PersonelRepository(BaseRepository):
    """
    Personel tablosu CRUD ve özel operasyonları.
    
    Kullanım:
        registry = RepositoryRegistry(db)
        repo = registry.personel
        
        # Personel tarafından Kimlik No'yu al
        ekip = repo.get_by_pk("12345678901")
        
        # Tüm personelleri liste
        depo = repo.get_all()
        
        # Durum bazında filtrele
        aktif = repo.get_by_durum("Aktif")
    """

    def __init__(self, db, table_name: str = "Personel"):
        config = TABLES.get(table_name, {})
        super().__init__(
            db=db,
            table_name=table_name,
            pk=config.get("pk", "KimlikNo"),
            columns=config.get("columns", []),
            has_sync=True,
            date_fields=config.get("date_fields", []),
        )

    # ── Temel Sorgular ──────────────────────────────────────────

    def get_by_pk(self, kimlik_no: str) -> Optional[Dict[str, Any]]:
        """
        TC Kimlik No ile personel bilgilerini al.
        
        Args:
            kimlik_no: TC Kimlik numarası
            
        Returns:
            Personel sözlüğü veya None
        """
        sql = f"""
        SELECT * FROM {self.table}
        WHERE KimlikNo = ?
        """
        result = self.db.execute(sql, [kimlik_no]).fetchone()
        return dict(result) if result else None

    def get_all(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Tüm personelleri liste.
        
        Args:
            limit: Maksimum satır sayısı (None = tümü)
            
        Returns:
            Personel listesi
        """
        sql = f"SELECT * FROM {self.table} ORDER BY AdSoyad"
        if limit:
            sql += f" LIMIT {limit}"
        
        rows = self.db.execute(sql).fetchall()
        return [dict(row) for row in rows]

    def get_by_durum(self, durum: str) -> List[Dict[str, Any]]:
        """
        Duruma göre personel listesi (Aktif, İstifa, vb).
        
        Args:
            durum: Personel durumu
            
        Returns:
            Personel listesi
        """
        sql = f"""
        SELECT * FROM {self.table}
        WHERE Durum = ?
        ORDER BY AdSoyad
        """
        rows = self.db.execute(sql, [durum]).fetchall()
        return [dict(row) for row in rows]

    def get_by_gorev_yeri(self, gorev_yeri: str) -> List[Dict[str, Any]]:
        """
        Görev yerine göre personel.
        
        Args:
            gorev_yeri: Görev yeri adı
            
        Returns:
            Personel listesi
        """
        sql = f"""
        SELECT * FROM {self.table}
        WHERE GorevYeri = ?
        ORDER BY AdSoyad
        """
        rows = self.db.execute(sql, [gorev_yeri]).fetchall()
        return [dict(row) for row in rows]

    def get_aktif_personel(self) -> List[Dict[str, Any]]:
        """
        Aktif personelleri al.
        
        Returns:
            Aktif personel listesi
        """
        return self.get_by_durum("Aktif")

    # ── Sayma İşlemleri ────────────────────────────────────────

    def count_all(self) -> int:
        """Toplam personel sayısı."""
        sql = f"SELECT COUNT(*) as cnt FROM {self.table}"
        result = self.db.execute(sql).fetchone()
        return result["cnt"] if result else 0

    def count_by_durum(self, durum: str) -> int:
        """Duruma göre personel sayısı."""
        sql = f"SELECT COUNT(*) as cnt FROM {self.table} WHERE Durum = ?"
        result = self.db.execute(sql, [durum]).fetchone()
        return result["cnt"] if result else 0

    def count_aktif(self) -> int:
        """Aktif personel sayısı."""
        return self.count_by_durum("Aktif")

    # ── Arama & Filtreleme ─────────────────────────────────────

    def search_by_name(self, ad_soyad: str) -> List[Dict[str, Any]]:
        """
        Adı/Soyadı ile arama (case-insensitive).
        
        Args:
            ad_soyad: Aranacak ad-soyad
            
        Returns:
            Eşleşen personel listesi
        """
        sql = f"""
        SELECT * FROM {self.table}
        WHERE LOWER(AdSoyad) LIKE LOWER(?)
        ORDER BY AdSoyad
        """
        rows = self.db.execute(sql, [f"%{ad_soyad}%"]).fetchall()
        return [dict(row) for row in rows]

    def search_by_kimlik_no(self, kimlik_no: str) -> Optional[Dict[str, Any]]:
        """Kimlik No ile tam eşleşme araması."""
        return self.get_by_pk(kimlik_no)

    # ── Güncelleme & Silme ─────────────────────────────────────

    def update_durum(self, kimlik_no: str, yeni_durum: str) -> bool:
        """
        Personel durumu güncelle.
        
        Args:
            kimlik_no: TC Kimlik numarası
            yeni_durum: Yeni durum (Aktif, İstifa, vb)
            
        Returns:
            Başarılıysa True
        """
        try:
            self.update(kimlik_no, {"Durum": yeni_durum})
            logger.info(f"Personel durumu güncellendi: {kimlik_no} → {yeni_durum}")
            return True
        except Exception as e:
            logger.error(f"Personel durumu güncellenirken hata: {e}")
            return False

    def delete(self, kimlik_no: str) -> bool:
        """
        Personel kaydını sil.
        
        Args:
            kimlik_no: TC Kimlik numarası
            
        Returns:
            Başarılıysa True
        """
        try:
            sql = f"DELETE FROM {self.table} WHERE KimlikNo = ?"
            self.db.execute(sql, [kimlik_no])
            logger.info(f"Personel silindi: {kimlik_no}")
            return True
        except Exception as e:
            logger.error(f"Personel silinirken hata: {e}")
            return False

    # ── İstatistikler ──────────────────────────────────────────

    def get_statistics(self) -> Dict[str, Any]:
        """
        Personel istatistikleri.
        
        Returns:
            {'toplam': int, 'aktif': int, 'istifa': int, ...}
        """
        try:
            toplam = self.count_all()
            aktif = self.count_by_durum("Aktif")
            istifa = self.count_by_durum("İstifa")
            
            return {
                "toplam": toplam,
                "aktif": aktif,
                "istifa": istifa,
                "pasif": toplam - aktif - istifa,
            }
        except Exception as e:
            logger.error(f"İstatistik hesaplanırken hata: {e}")
            return {}
    # ── Performance Optimized Query ──────────────────────────────────────────

    def get_all_with_bakiye(self) -> List[Dict[str, Any]]:
        """
        Tüm personel kayıtlarını izin bakiye bilgileriyle birlikte tek sorguda getirir.
        N+1 query sorununu çözer: 2 ayrı sorgu yerine 1 JOIN sorgusu.
        
        Returns:
            List[dict]: Personel ve izin bakiye bilgileri birleşmiş kayıtlar.
                        Bakiye bilgisi yoksa ilgili alanlar None olur.
        
        Example:
            >>> repo = registry.get("Personel")
            >>> personel_listesi = repo.get_all_with_bakiye()
            >>> for p in personel_listesi:
            >>>     print(f"{p['AdSoyad']}: {p['YillikKalan']}/{p['YillikToplamHak']}")
        """
        try:
            # Personel kolonları
            p_cols = ", ".join([f"p.{col} AS p_{col}" for col in self.columns])
            
            # İzin_Bilgi kolonları (TCKimlik hariç, çünkü p.KimlikNo ile aynı)
            izin_cols = [
                "YillikDevir", "YillikHakedis", "YillikToplamHak",
                "YillikKullanilan", "YillikKalan", "SuaKullanilabilirHak",
                "SuaKullanilan", "SuaKalan", "SuaCariYilKazanim", "RaporMazeretTop"
            ]
            ib_cols = ", ".join([f"ib.{col} AS ib_{col}" for col in izin_cols])
            
            sql = f"""
            SELECT {p_cols}, {ib_cols}
            FROM Personel p
            LEFT JOIN Izin_Bilgi ib ON p.KimlikNo = ib.TCKimlik
            """
            
            cur = self.db.execute(sql)
            rows = cur.fetchall()
            
            result = []
            for row in rows:
                row_dict = dict(row)
                
                # Personel verileri (p_ prefix'ini kaldır)
                personel_data = {}
                for col in self.columns:
                    personel_data[col] = row_dict.get(f"p_{col}")
                
                # İzin bakiye verileri (ib_ prefix'ini kaldır, ana dict'e ekle)
                for col in izin_cols:
                    personel_data[col] = row_dict.get(f"ib_{col}")
                
                result.append(personel_data)
            
            logger.debug(f"get_all_with_bakiye: {len(result)} personel yüklendi (JOIN ile)")
            return result
            
        except Exception as e:
            logger.error(f"get_all_with_bakiye hatası: {e}")
            # Fallback: Ayrı sorgular
            logger.warning("Fallback: Ayrı sorgularla yükleniyor...")
            return self.get_all()

    def get_paginated_with_bakiye(self, page: int = 1, page_size: int = 100) -> tuple[List[Dict[str, Any]], int]:
        """
        Personel kayıtlarını sayfalara bölerek izin bakiye bilgileriyle birlikte getirir.
        Lazy-loading desteği: tablonun scroll'unu takip ederek sayfa yükle.
        
        Args:
            page: Sayfa numarası (1-based)
            page_size: Her sayfada kaç kayıt (default: 100)
            
        Returns:
            Tuple[List[dict], int]: (Personel listesi, Toplam kayıt sayısı)
        
        Example:
            >>> page1, total = repo.get_paginated_with_bakiye(page=1, page_size=100)
            >>> print(f"{len(page1)} personel, Toplam: {total}")
            >>> # Daha fazla: page2, _ = repo.get_paginated_with_bakiye(page=2, page_size=100)
        """
        try:
            if page < 1:
                page = 1
            
            offset = (page - 1) * page_size
            
            # Personel kolonları
            p_cols = ", ".join([f"p.{col} AS p_{col}" for col in self.columns])
            
            # İzin_Bilgi kolonları
            izin_cols = [
                "YillikDevir", "YillikHakedis", "YillikToplamHak",
                "YillikKullanilan", "YillikKalan", "SuaKullanilabilirHak",
                "SuaKullanilan", "SuaKalan", "SuaCariYilKazanim", "RaporMazeretTop"
            ]
            ib_cols = ", ".join([f"ib.{col} AS ib_{col}" for col in izin_cols])
            
            # Sayfalanmış sorgu
            sql = f"""
            SELECT {p_cols}, {ib_cols}
            FROM Personel p
            LEFT JOIN Izin_Bilgi ib ON p.KimlikNo = ib.TCKimlik
            ORDER BY p.AdSoyad
            LIMIT {page_size} OFFSET {offset}
            """
            
            cur = self.db.execute(sql)
            rows = cur.fetchall()
            
            # Toplam kayıt sayısı (for pagination info)
            total_sql = "SELECT COUNT(*) as cnt FROM Personel"
            total_result = self.db.execute(total_sql).fetchone()
            total_count = total_result["cnt"] if total_result else 0
            
            result = []
            for row in rows:
                row_dict = dict(row)
                
                # Personel verileri (p_ prefix'ini kaldır)
                personel_data = {}
                for col in self.columns:
                    personel_data[col] = row_dict.get(f"p_{col}")
                
                # İzin bakiye verileri (ib_ prefix'ini kaldır)
                for col in izin_cols:
                    personel_data[col] = row_dict.get(f"ib_{col}")
                
                result.append(personel_data)
            
            logger.debug(f"get_paginated_with_bakiye: Sayfa {page}, {len(result)} kayıt / Toplam {total_count}")
            return result, total_count
            
        except Exception as e:
            logger.error(f"get_paginated_with_bakiye hatası: {e}")
            # Fallback: Pagination olmadan tümü
            logger.warning("Fallback: Paginator olmadan tümü yükleniyor...")
            return self.get_all_with_bakiye(), self.count_all()
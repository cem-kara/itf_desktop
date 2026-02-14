from datetime import datetime
from core.logger import logger


class BaseRepository:
    def __init__(self, db, table_name, pk, columns, has_sync=True):
        self.db = db
        self.table = table_name
        self.columns = columns
        self.has_sync = has_sync

        # PK: string veya list (composite)
        if isinstance(pk, list):
            self.pk_list = pk
            self.is_composite = True
        else:
            self.pk_list = [pk] if pk else []
            self.is_composite = False

    @property
    def pk(self):
        """Geriye uyumluluk: tekli PK için string döner."""
        if not self.is_composite and self.pk_list:
            return self.pk_list[0]
        return self.pk_list

    # ════════════════ PK HELPERS ════════════════

    def _pk_where(self):
        """WHERE Personelid=? AND AitYil=? AND Donem=?"""
        return " AND ".join(f"{col}=?" for col in self.pk_list)

    def _pk_values_from_dict(self, data):
        """PK değerlerini dict'ten çıkarır."""
        return [data.get(col) for col in self.pk_list]

    def _pk_key(self, data):
        """Composite PK → tekil string key (index/log için)."""
        return "|".join(str(data.get(col, "")).strip() for col in self.pk_list)

    def _resolve_pk_params(self, pk_value):
        """pk_value'yu her zaman list olarak döner."""
        if isinstance(pk_value, dict):
            return [pk_value.get(col) for col in self.pk_list]
        elif isinstance(pk_value, (list, tuple)):
            return list(pk_value)
        else:
            return [pk_value]

    # ════════════════ CRUD ════════════════

    def insert(self, data: dict):
        now = datetime.now().isoformat()

        if "updated_at" in self.columns and not data.get("updated_at"):
            data["updated_at"] = now

        # 🔧 FIX: sync_status sadece açıkça belirtilmemişse 'dirty' yap
        # Pull işlemi sync_status='clean' gönderdiğinde onu koru
        if self.has_sync and "sync_status" in self.columns:
            if "sync_status" not in data:
                data["sync_status"] = "dirty"
            # else: data'da zaten var (clean veya dirty), onu koru

        cols = ", ".join(self.columns)
        placeholders = ", ".join(["?"] * len(self.columns))
        values = [data.get(col) for col in self.columns]

        sql = f"""
        INSERT OR REPLACE INTO {self.table}
        ({cols})
        VALUES ({placeholders})
        """
        self.db.execute(sql, values)

    def update(self, pk_value, data: dict):
        now = datetime.now().isoformat()

        if "updated_at" in self.columns:
            data["updated_at"] = now

        # Sadece data'da bulunan kolonları güncelle (partial update)
        non_pk = [c for c in self.columns if c not in self.pk_list and c in data]
        if not non_pk:
            return

        sets_parts = [f"{c}=?" for c in non_pk]
        values = [data.get(c) for c in non_pk]

        # 🔧 FIX: sync_status sadece açıkça belirtilmemişse 'dirty' yap
        # Pull işlemi sync_status='clean' gönderdiğinde onu koru
        if self.has_sync and "sync_status" not in data:
            sets_parts.append("sync_status='dirty'")

        sets = ", ".join(sets_parts)
        where_vals = self._resolve_pk_params(pk_value)

        sql = f"""
        UPDATE {self.table}
        SET {sets}
        WHERE {self._pk_where()}
        """
        self.db.execute(sql, values + where_vals)

    def get_by_id(self, pk_value):
        sql = f"SELECT * FROM {self.table} WHERE {self._pk_where()}"
        params = self._resolve_pk_params(pk_value)
        cur = self.db.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None

    def get_all(self):
        cur = self.db.execute(f"SELECT * FROM {self.table}")
        return [dict(r) for r in cur.fetchall()]

    def get_by_kod(self, kod_degeri: str, kolum: str = "Kod") -> list:
        """
        Belirtilen kolona göre filtreli kayıtları döner.
        Varsayılan olarak 'Kod' kolonunu kullanır (Sabitler tablosu için).

        Örnek:
            sabitler_repo.get_by_kod("Ariza_Islem_Turu")
            sabitler_repo.get_by_kod("aktif", kolum="Durum")
        """
        sql = f"SELECT * FROM {self.table} WHERE {kolum} = ?"
        try:
            cur = self.db.execute(sql, (kod_degeri,))
            return [dict(r) for r in cur.fetchall()]
        except Exception as exc:
            logger.error(
                f"BaseRepository.get_by_kod hatası — "
                f"tablo={self.table}, kolum={kolum}, deger={kod_degeri}: {exc}"
            )
            return []

    def get_where(self, kosullar: dict) -> list:
        """
        Birden fazla kolona göre filtreleme.

        Örnek:
            repo.get_where({"Durum": "aktif", "Tur": "A"})
        """
        if not kosullar:
            return self.get_all()
        where  = " AND ".join(f"{k}=?" for k in kosullar)
        values = list(kosullar.values())
        sql    = f"SELECT * FROM {self.table} WHERE {where}"
        try:
            cur = self.db.execute(sql, values)
            return [dict(r) for r in cur.fetchall()]
        except Exception as exc:
            logger.error(
                f"BaseRepository.get_where hatası — "
                f"tablo={self.table}, kosullar={kosullar}: {exc}"
            )
            return []

    # ════════════════ SYNC ════════════════

    def get_dirty(self):
        if not self.has_sync:
            return []
        sql = f"SELECT * FROM {self.table} WHERE sync_status='dirty'"
        cur = self.db.execute(sql)
        return [dict(r) for r in cur.fetchall()]

    def mark_clean(self, pk_value):
        if not self.has_sync:
            return
        where_vals = self._resolve_pk_params(pk_value)
        sql = f"""
        UPDATE {self.table}
        SET sync_status='clean'
        WHERE {self._pk_where()}
        """
        self.db.execute(sql, where_vals)

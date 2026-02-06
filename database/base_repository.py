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

        non_pk = [c for c in self.columns if c not in self.pk_list]
        sets_parts = [f"{c}=?" for c in non_pk]
        values = [data.get(c) for c in non_pk]

        # sync_status sadece sync tablolarında
        if self.has_sync:
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

import sqlite3
from core.logger import logger


class BaseRepository:
    def __init__(self, db, table_name, pk, columns):
        self.db = db
        self.table = table_name
        self.pk = pk
        self.columns = columns

    # ---------------- CRUD ----------------

    def insert(self, data: dict):
        cols = ", ".join(self.columns)
        placeholders = ", ".join(["?"] * len(self.columns))
        values = [data.get(col) for col in self.columns]

        sql = f"""
        INSERT OR REPLACE INTO {self.table}
        ({cols})
        VALUES ({placeholders})
        """

        self.db.execute(sql, values)
        logger.info(f"{self.table} INSERT: {data.get(self.pk)}")

    def update(self, pk_value, data: dict):
        sets = ", ".join([f"{c}=?" for c in self.columns if c != self.pk])
        values = [data.get(c) for c in self.columns if c != self.pk]
        values.append(pk_value)

        sql = f"""
        UPDATE {self.table}
        SET {sets},
            sync_status='dirty'
        WHERE {self.pk}=?
        """

        self.db.execute(sql, values)
        logger.info(f"{self.table} UPDATE: {pk_value}")

    def get_by_id(self, pk_value):
        sql = f"SELECT * FROM {self.table} WHERE {self.pk}=?"
        cur = self.db.execute(sql, [pk_value])
        row = cur.fetchone()
        return dict(row) if row else None

    def get_all(self):
        cur = self.db.execute(f"SELECT * FROM {self.table}")
        return [dict(r) for r in cur.fetchall()]

    # ---------------- SYNC ----------------

    def get_dirty(self):
        sql = f"SELECT * FROM {self.table} WHERE sync_status='dirty'"
        cur = self.db.execute(sql)
        return [dict(r) for r in cur.fetchall()]

    def mark_clean(self, pk_value):
        sql = f"""
        UPDATE {self.table}
        SET sync_status='clean'
        WHERE {self.pk}=?
        """
        self.db.execute(sql, [pk_value])

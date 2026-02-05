from datetime import datetime
from core.logger import logger
from database.sqlite_manager import SQLiteManager


class BaseRepository:
    """
    Tüm repository sınıflarının temel sınıfı.
    """

    TABLE_NAME = None          # alt sınıf set edecek
    PRIMARY_KEY = None         # alt sınıf set edecek

    def __init__(self):
        if not self.TABLE_NAME or not self.PRIMARY_KEY:
            raise ValueError("TABLE_NAME ve PRIMARY_KEY tanımlanmalı")

        self.db = SQLiteManager()

    # =========================
    # Yardımcılar
    # =========================
    def _now(self):
        return datetime.now().isoformat(timespec="seconds")

    def _mark_dirty(self, data: dict):
        data["updated_at"] = self._now()
        data["sync_status"] = "dirty"
        return data

    # =========================
    # CRUD
    # =========================
    def insert(self, data: dict):
        logger.info(f"{self.TABLE_NAME} INSERT")

        data = self._mark_dirty(data)

        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        values = list(data.values())

        sql = f"""
        INSERT INTO {self.TABLE_NAME}
        ({columns})
        VALUES ({placeholders})
        """

        self.db.execute(sql, values)

    def update(self, pk_value, data: dict):
        logger.info(f"{self.TABLE_NAME} UPDATE {pk_value}")

        data = self._mark_dirty(data)

        set_clause = ", ".join([f"{k}=?" for k in data.keys()])
        values = list(data.values())
        values.append(pk_value)

        sql = f"""
        UPDATE {self.TABLE_NAME}
        SET {set_clause}
        WHERE {self.PRIMARY_KEY} = ?
        """

        self.db.execute(sql, values)

    def delete(self, pk_value):
        """
        Fiziksel silme – ileride soft delete eklenebilir
        """
        logger.warning(f"{self.TABLE_NAME} DELETE {pk_value}")

        sql = f"""
        DELETE FROM {self.TABLE_NAME}
        WHERE {self.PRIMARY_KEY} = ?
        """

        self.db.execute(sql, (pk_value,))

    # =========================
    # READ
    # =========================
    def get_by_id(self, pk_value):
        sql = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE {self.PRIMARY_KEY} = ?
        """
        cur = self.db.execute(sql, (pk_value,))
        return dict(cur.fetchone()) if cur.fetchone() else None

    def get_all(self):
        sql = f"SELECT * FROM {self.TABLE_NAME}"
        cur = self.db.execute(sql)
        return [dict(row) for row in cur.fetchall()]

    def get_dirty_records(self):
        """
        Sync için: henüz gönderilmemiş kayıtlar
        """
        sql = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE sync_status = 'dirty'
        """
        cur = self.db.execute(sql)
        return [dict(row) for row in cur.fetchall()]

    def mark_clean(self, pk_value):
        """
        Sync sonrası çağrılır
        """
        sql = f"""
        UPDATE {self.TABLE_NAME}
        SET sync_status = 'clean'
        WHERE {self.PRIMARY_KEY} = ?
        """
        self.db.execute(sql, (pk_value,))

    def close(self):
        self.db.close()

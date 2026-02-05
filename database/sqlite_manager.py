import sqlite3
from core.paths import DB_PATH
from core.logger import logger

class SQLiteManager:
    def __init__(self):
        logger.info("SQLite bağlantısı açılıyor")
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row

    def execute(self, query, params=()):
        cur = self.conn.cursor()
        cur.execute(query, params)
        self.conn.commit()
        return cur

    def executemany(self, query, params_list):
        cur = self.conn.cursor()
        cur.executemany(query, params_list)
        self.conn.commit()

    def close(self):
        logger.info("SQLite bağlantısı kapatılıyor")
        self.conn.close()

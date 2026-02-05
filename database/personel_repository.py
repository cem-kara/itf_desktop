import pandas as pd
from database.base_repository import BaseRepository
from core.logger import logger


class PersonelRepository(BaseRepository):
    TABLE_NAME = "Personel"
    PRIMARY_KEY = "Kimlik_No"

    def __init__(self):
        super().__init__()

    # =========================
    # Özel CRUD
    # =========================
    def add_personel(self, data: dict):
        """
        Yeni personel ekler
        """
        if "Kimlik_No" not in data:
            raise ValueError("Kimlik_No zorunludur")

        logger.info(f"Personel ekleniyor: {data['Kimlik_No']}")

        data.setdefault("created_at", self._now())
        data.setdefault("updated_by", "LOCAL")

        self.insert(data)

    def update_personel(self, kimlik_no: str, data: dict):
        """
        Personel güncelle
        """
        logger.info(f"Personel güncelleniyor: {kimlik_no}")

        data.setdefault("updated_by", "LOCAL")
        self.update(kimlik_no, data)

    # =========================
    # Okuma / Listeleme
    # =========================
    def get_personel(self, kimlik_no: str):
        return self.get_by_id(kimlik_no)

    def get_all_personel(self):
        return self.get_all()

    def get_all_df(self):
        """
        UI ve raporlar için pandas DataFrame
        """
        records = self.get_all()
        if not records:
            return pd.DataFrame()

        return pd.DataFrame(records)

    def get_active_personel_df(self):
        """
        Aktif personeller
        """
        sql = f"""
        SELECT *
        FROM {self.TABLE_NAME}
        WHERE Durum IS NULL OR Durum != 'Pasif'
        """
        cur = self.db.execute(sql)
        return pd.DataFrame([dict(r) for r in cur.fetchall()])

    # =========================
    # Sync yardımcıları
    # =========================
    def get_dirty_personel(self):
        return self.get_dirty_records()

    def mark_personel_clean(self, kimlik_no: str):
        self.mark_clean(kimlik_no)

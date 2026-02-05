from datetime import datetime
from core.logger import logger
from database.personel_repository import PersonelRepository
from database.gsheet_manager import GSheetManager


class SyncService:
    """
    Google Sheets <-> SQLite senkronizasyon servisi
    """

    def __init__(self):
        self.personel_repo = PersonelRepository()
        self.gsheet = GSheetManager()

    # =========================
    # GENEL YARDIMCILAR
    # =========================
    def _parse_dt(self, value):
        if not value:
            return None
        return datetime.fromisoformat(value)

    # =========================
    # PERSONEL SYNC
    # =========================
    def sync_personel(self):
        logger.info("Personel sync başladı")

        # 1️⃣ LOCAL -> REMOTE
        dirty_records = self.personel_repo.get_dirty_personel()
        logger.info(f"Local dirty kayıt sayısı: {len(dirty_records)}")

        for row in dirty_records:
            self.gsheet.upsert_personel(row)
            self.personel_repo.mark_personel_clean(row["Kimlik_No"])

        # 2️⃣ REMOTE -> LOCAL
        remote_records = self.gsheet.get_all_personel()
        logger.info(f"GSheets kayıt sayısı: {len(remote_records)}")

        for remote in remote_records:
            local = self.personel_repo.get_personel(remote["Kimlik_No"])

            if not local:
                # yeni kayıt
                self.personel_repo.insert(remote)
                self.personel_repo.mark_personel_clean(remote["Kimlik_No"])
                continue

            # çakışma kontrolü
            local_dt = self._parse_dt(local.get("updated_at"))
            remote_dt = self._parse_dt(remote.get("updated_at"))

            if remote_dt and (not local_dt or remote_dt > local_dt):
                self.personel_repo.update(remote["Kimlik_No"], remote)
                self.personel_repo.mark_personel_clean(remote["Kimlik_No"])

        logger.info("Personel sync tamamlandı")

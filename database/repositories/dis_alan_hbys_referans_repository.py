# database/repositories/dis_alan_hbys_referans_repository.py
from database.base_repository import BaseRepository

class DisAlanHbysReferansRepository(BaseRepository):
    """
    Dis_Alan_Hbys_Referans tablosu için repository.
    """
    def __init__(self, conn):
        super().__init__(conn, "Dis_Alan_Hbys_Referans", "HbysReferansKodu")

    # Gerekirse özel sorgular eklenebilir

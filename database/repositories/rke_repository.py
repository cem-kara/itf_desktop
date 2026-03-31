# database/repositories/rke_repository.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RKE_List Repository
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
RKE_List tablosu için özel repository.

Tablo şeması (migrations.py ile uyumlu):
    EkipmanNo TEXT PK, KoruyucuNumarasi, AnaBilimDali, Birim,
    KoruyucuCinsi, KursunEsdegeri, HizmetYili, Bedeni,
    KontrolTarihi, Durum, Aciklama, VarsaDemirbasNo, KayitTarih,
    Barkod, sync_status, updated_at

Kullanım:
    registry = RepositoryRegistry(db)
    repo = registry.get("RKE_List")   # RKERepository döner

NOT: RepositoryRegistry'ye "RKE_List" -> RKERepository olarak
     kayitlidir (repository_registry.py).
"""

from typing import Dict, List, Any

from core.logger import logger

from database.base_repository import BaseRepository
from database.table_config import TABLES


class RKERepository(BaseRepository):
    """
    RKE_List tablosu icin ozel sorgular.
    Tum temel CRUD islemleri BaseRepository'den miras alinir.
    """

    def __init__(self, db, table_name: str = "RKE_List"):
        config = TABLES.get(table_name, {})
        super().__init__(
            db=db,
            table_name=table_name,
            pk=config.get("pk", "EkipmanNo"),
            columns=config.get("columns", []),
            has_sync=True,
            date_fields=config.get("date_fields", []),
        )

    # -- Arama & Filtreleme ----------------------------------------

    def search_by_cihaz_adi(self, aramaMetni: str) -> List[Dict[str, Any]]:
        """KoruyucuCinsi veya EkipmanNo uzerinde metin aramasi."""
        try:
            tum = self.get_all() or []
            aranan = str(aramaMetni).lower().strip()
            return [
                r for r in tum
                if aranan in str(r.get("KoruyucuCinsi", "")).lower()
                or aranan in str(r.get("EkipmanNo", "")).lower()
            ]
        except Exception as e:
            logger.warning(f"RKERepository.search_by_cihaz_adi hatasi: {e}")
            return []

    def get_by_abd(self, ana_bilim_dali: str) -> List[Dict[str, Any]]:
        """Ana bilim dalina gore filtrele."""
        return self.get_where({"AnaBilimDali": ana_bilim_dali})

    def get_by_birim(self, birim: str) -> List[Dict[str, Any]]:
        """Birime gore filtrele."""
        return self.get_where({"Birim": birim})

    def get_by_durum(self, durum: str) -> List[Dict[str, Any]]:
        """Duruma gore filtrele."""
        return self.get_where({"Durum": durum})

    # -- Istatistikler ---------------------------------------------

    def count_uygun(self) -> int:
        """Kullanima uygun ekipman sayisi."""
        try:
            tum = self.get_all() or []
            return sum(
                1 for r in tum
                if "uygun" in str(r.get("Durum", "")).lower()
                and "degil" not in str(r.get("Durum", "")).lower()
            )
        except Exception:
            return 0

    def get_statistics(self) -> Dict[str, Any]:
        """RKE envanter istatistikleri."""
        try:
            tum = self.get_all() or []
            durum_dag: Dict[str, int] = {}
            abd_dag:   Dict[str, int] = {}
            cins_dag:  Dict[str, int] = {}

            for r in tum:
                d = str(r.get("Durum", "-") or "-").strip()
                a = str(r.get("AnaBilimDali", "-") or "-").strip()
                c = str(r.get("KoruyucuCinsi", "-") or "-").strip()
                durum_dag[d] = durum_dag.get(d, 0) + 1
                abd_dag[a]   = abd_dag.get(a, 0) + 1
                cins_dag[c]  = cins_dag.get(c, 0) + 1

            return {
                "toplam":         len(tum),
                "durum_dagilimi": durum_dag,
                "abd_dagilimi":   abd_dag,
                "cins_dagilimi":  cins_dag,
            }
        except Exception as e:
            logger.error(f"RKERepository.get_statistics hatasi: {e}")
            return {"toplam": 0, "durum_dagilimi": {}, "abd_dagilimi": {}, "cins_dagilimi": {}}

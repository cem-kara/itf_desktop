"""
FileSyncService — Offline kaydedilen dosyaları Drive'a yükler.

Akış (SyncWorker tarafından sync_all()'dan ÖNCE çağrılır):

1. Dokumanlar tablosunda LocalPath dolu, DrivePath boş kayıtları bul
2. Her kayıt için:
   a. Dosya diskte var mı kontrol et  → yoksa "skipped"
   b. DocType'tan Drive klasörünü belirle
   c. Sabitler'den Drive klasör ID'sini çöz  → yoksa "failed"
   d. Drive'a yükle → link al
   e. DrivePath'i güncelle, LocalPath korunur, sync_status='dirty' yap
3. Tek hata tümünü durdurmasın — devam et, logla
4. Özet dict döndür

Neden sync_all'dan ÖNCE?
  Dokumanlar artık Sheets'e sync ediliyor. Eğer dosya sync sonra
  çalışırsa bu sync döngüsünde DrivePath hâlâ boş kalır.
  Önce dosyaları yükle → DrivePath dolu kayıtlar Sheets'e gitsin.
"""

from typing import Optional
from core.logger import logger


# DocType → Sabitler'deki klasör adı eşlemesi.
# Sabitler: Kod='Sistem_DriveID', MenuEleman=<klasör_adı>, Aciklama=<drive_id>
DOCTYPE_FOLDER_MAP = {
    "Cihaz_Belge":       "Cihaz_Belgeler",
    "Personel_Belge":    "Personel_Belge",
    "RKE_Rapor":         "RKE_Rapor",
    "Personel_Resim":    "Personel_Resim",
    "Personel_Diploma":  "Personel_Diploma",
}


class FileSyncService:
    """
    Offline modda local'e kaydedilen dosyaları Drive'a yükler.

    Kullanım:
        file_svc = FileSyncService(db=db, registry=registry)
        sonuc = file_svc.push_pending_files()
        # {"total": 3, "uploaded": 2, "skipped": 1, "failed": 0}
    """

    def __init__(self, db, registry):
        self._db = db
        self._registry = registry
        self._sabitler_cache: Optional[list[dict]] = None

    # ──────────────────────────────────────────────────────────
    #  Public API
    # ──────────────────────────────────────────────────────────

    def push_pending_files(self) -> dict:
        """
        LocalPath dolu, DrivePath boş Dokumanlar kayıtlarını Drive'a yükle.

        Returns:
            {
              "total":    int,   # bulunan bekleyen kayıt sayısı
              "uploaded": int,   # Drive'a yüklendi, DrivePath güncellendi
              "skipped":  int,   # dosya diskte yok, atlandı
              "failed":   int,   # drive hatası veya klasör bulunamadı
            }
        """
        result = {"total": 0, "uploaded": 0, "skipped": 0, "failed": 0}

        try:
            pending = self._get_pending_records()
        except Exception as e:
            logger.error(f"FileSyncService: Bekleyen kayıtlar okunamadı: {e}")
            return result

        result["total"] = len(pending)
        if not pending:
            logger.info("FileSyncService: Bekleyen dosya yok, atlanıyor.")
            return result

        logger.info(f"FileSyncService: {len(pending)} bekleyen dosya bulundu.")

        for record in pending:
            status = self._upload_one(record)
            result[status] += 1

        logger.info(
            f"FileSyncService tamamlandı: "
            f"{result['uploaded']} yüklendi, "
            f"{result['skipped']} atlandı (dosya yok), "
            f"{result['failed']} başarısız."
        )
        return result

    # ──────────────────────────────────────────────────────────
    #  İç metodlar
    # ──────────────────────────────────────────────────────────

    def _get_pending_records(self) -> list:
        """LocalPath dolu, DrivePath boş Dokumanlar kayıtlarını döner."""
        cur = self._db.execute("""
            SELECT EntityType, EntityId, BelgeTuru, Belge,
                   DocType, LocalPath, DrivePath
            FROM   Dokumanlar
            WHERE  LocalPath  IS NOT NULL
              AND  LocalPath  != ''
              AND  (DrivePath IS NULL OR DrivePath = '')
        """)
        return [dict(row) for row in cur.fetchall()]

    def _upload_one(self, record: dict) -> str:
        """
        Tek bir kaydı Drive'a yükler.

        Returns:
            "uploaded" | "skipped" | "failed"
        """
        import os

        local_path  = record.get("LocalPath", "")
        doc_type    = record.get("DocType", "")
        entity_info = (
            f"{record.get('EntityType')}/{record.get('EntityId')}/"
            f"{record.get('BelgeTuru')}/{record.get('Belge')}"
        )

        # 1 — Dosya diskte var mı?
        if not local_path or not os.path.exists(local_path):
            logger.warning(
                f"FileSyncService: Diskte bulunamadı, atlanıyor: "
                f"'{local_path}' [{entity_info}]"
            )
            return "skipped"

        # 2 — Drive klasörünü belirle
        folder_name = DOCTYPE_FOLDER_MAP.get(doc_type, doc_type)
        if not folder_name:
            logger.warning(
                f"FileSyncService: DocType için klasör tanımı yok: "
                f"'{doc_type}' [{entity_info}]"
            )
            return "failed"

        # 3 — Sabitler'den Drive klasör ID'sini çöz
        drive_folder_id = self._resolve_drive_folder_id(folder_name)
        if not drive_folder_id:
            logger.warning(
                f"FileSyncService: Sabitler'de Drive ID bulunamadı: "
                f"klasör='{folder_name}' [{entity_info}]"
            )
            return "failed"

        # 4 — Drive'a yükle
        try:
            from database.google.drive import get_drive_service
            drive = get_drive_service()
            custom_name = os.path.basename(local_path)
            drive_link = drive.upload_file(
                local_path,
                parent_folder_id=drive_folder_id,
                custom_name=custom_name,
            )
        except Exception as e:
            logger.error(
                f"FileSyncService: Drive yükleme hatası [{entity_info}]: {e}"
            )
            return "failed"

        if not drive_link:
            logger.error(
                f"FileSyncService: Drive link döndürmedi [{entity_info}]"
            )
            return "failed"

        # 5 — DrivePath'i güncelle (LocalPath korunur, sync_status=dirty)
        if self._update_drive_path(record, drive_link):
            logger.info(
                f"FileSyncService: ✓ [{entity_info}] → {drive_link}"
            )
            return "uploaded"

        # Drive'a gitti ama DB güncellenemedi — bu kritik bir durum
        logger.error(
            f"FileSyncService: Drive'a yüklendi AMA DrivePath güncellenemedi: "
            f"[{entity_info}] link={drive_link}"
        )
        return "failed"

    def _resolve_drive_folder_id(self, folder_name: str) -> str:
        """Sabitler tablosundan Drive klasör ID'sini döner."""
        from database.google.utils import resolve_storage_target
        sabitler = self._get_sabitler()
        target = resolve_storage_target(sabitler, folder_name)
        return target.get("drive_folder_id", "")

    def _get_sabitler(self) -> list[dict]:
        """Sabitler'i lazy yükler, cache'ler (sync boyunca bir kez)."""
        if self._sabitler_cache is None:
            try:
                self._sabitler_cache = self._registry.get("Sabitler").get_all()
            except Exception as e:
                logger.warning(f"FileSyncService: Sabitler yüklenemedi: {e}")
                self._sabitler_cache = []
        # Type narrowing: if bloğundan sonra kesinlikle list[dict]
        assert self._sabitler_cache is not None
        return self._sabitler_cache

    def _update_drive_path(self, record: dict, drive_link: str) -> bool:
        """
        Dokumanlar tablosunda DrivePath'i günceller.
        sync_status='dirty' yapılır ki Sheets'e push edilsin.
        """
        try:
            self._db.execute("""
                UPDATE Dokumanlar
                SET    DrivePath   = ?,
                       sync_status = 'dirty'
                WHERE  EntityType = ?
                  AND  EntityId   = ?
                  AND  BelgeTuru  = ?
                  AND  Belge      = ?
            """, (
                drive_link,
                record["EntityType"],
                record["EntityId"],
                record["BelgeTuru"],
                record["Belge"],
            ))
            return True
        except Exception as e:
            logger.error(f"FileSyncService: DrivePath güncellenemedi: {e}")
            return False

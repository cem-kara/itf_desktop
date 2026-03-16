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
from core.hata_yonetici import SonucYonetici


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

    def __init__(self, db, registry): # registry tipi belirtilmeli
        self._db = db
        self._registry = registry
        self._sabitler_cache: Optional[list[dict]] = None

    # ──────────────────────────────────────────────────────────
    #  Public API
    # ──────────────────────────────────────────────────────────

    def push_pending_files(self) -> SonucYonetici:
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
        result = {"total": 0, "uploaded": 0, "skipped": 0, "failed": 0} # SonucYonetici.data için

        try:
            pending_sonuc = self._get_pending_records()
            if not pending_sonuc.basarili:
                return SonucYonetici.hata(Exception(f"Bekleyen kayıtlar okunamadı: {pending_sonuc.mesaj}"), "FileSyncService.push_pending_files")
            pending = pending_sonuc.data or []
        except Exception as e:
            return SonucYonetici.hata(e, "FileSyncService.push_pending_files")

        result["total"] = len(pending) # SonucYonetici.data için
        if not pending:
            logger.info("FileSyncService: Bekleyen dosya yok, atlanıyor.")
            return SonucYonetici.tamam(veri=result)

        logger.info(f"FileSyncService: {len(pending)} bekleyen dosya bulundu.")

        for record in pending:
            upload_status_sonuc = self._upload_one(record)
            # upload_status_sonuc.data None olursa default 'failed' olarak say.
            # Pylance'in tip uyarısını gidermek için açıkça string olduğundan emin ol.
            data_value = upload_status_sonuc.data if isinstance(upload_status_sonuc.data, str) else "failed"
            status_key = data_value if data_value in ("uploaded", "skipped", "failed") else "failed"
            if upload_status_sonuc.basarili:
                result[status_key] += 1
            else:
                logger.error(f"Dosya yükleme hatası: {upload_status_sonuc.mesaj}")
                result["failed"] += 1
        return SonucYonetici.tamam(f"Dosya senkronizasyonu tamamlandı. Yüklendi: {result['uploaded']}, Atlandı: {result['skipped']}, Başarısız: {result['failed']}", data=result)

    # ──────────────────────────────────────────────────────────
    #  İç metodlar
    # ──────────────────────────────────────────────────────────

    def _get_pending_records(self) -> SonucYonetici:
        """LocalPath dolu, DrivePath boş Dokumanlar kayıtlarını döner."""
        try:
            cur = self._db.execute("""
            SELECT EntityType, EntityId, BelgeTuru, Belge,
                   DocType, LocalPath, DrivePath
            FROM   Dokumanlar
            WHERE  LocalPath  IS NOT NULL
              AND  LocalPath  != ''
              AND  (DrivePath IS NULL OR DrivePath = '')
        """)
            return SonucYonetici.tamam(veri=[dict(row) for row in cur.fetchall()])
        except Exception as e:
            return SonucYonetici.hata(e, "FileSyncService._get_pending_records")

    def _upload_one(self, record: dict) -> SonucYonetici:
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
            return SonucYonetici.tamam(veri="skipped")
        # 2 — Drive klasörünü belirle
        folder_name = DOCTYPE_FOLDER_MAP.get(doc_type, doc_type)
        if not folder_name:
            logger.warning(
                f"FileSyncService: DocType için klasör tanımı yok: "
                f"'{doc_type}' [{entity_info}]"
            )
            return SonucYonetici.tamam(veri="failed")
        # 3 — Sabitler'den Drive klasör ID'sini çöz
        drive_folder_id = self._resolve_drive_folder_id(folder_name)
        if not drive_folder_id:
            logger.warning(
                f"FileSyncService: Sabitler'de Drive ID bulunamadı: "
                f"klasör='{folder_name}' [{entity_info}]"
            )
            return SonucYonetici.tamam(veri="failed")
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
            return SonucYonetici.hata(e, f"FileSyncService._upload_one [{entity_info}]")
        
        if not drive_link:
            return SonucYonetici.hata(Exception("Drive link döndürmedi"), f"FileSyncService._upload_one [{entity_info}]")
        
        # 5 — DrivePath'i güncelle (LocalPath korunur, sync_status=dirty)
        update_sonuc = self._update_drive_path(record, drive_link)
        if update_sonuc.basarili:
            return SonucYonetici.tamam(veri="uploaded")
        else:
            return SonucYonetici.hata(Exception(f"DrivePath güncellenemedi: {update_sonuc.mesaj}"), f"FileSyncService._upload_one [{entity_info}]")

    def _resolve_drive_folder_id(self, folder_name: str) -> str:
        """Sabitler tablosundan Drive klasör ID'sini döner."""
        from database.google.utils import resolve_storage_target
        sabitler_sonuc = self._get_sabitler()
        sabitler = sabitler_sonuc.data or []
        target = resolve_storage_target(sabitler, folder_name)
        return target.get("drive_folder_id", "")

    def _get_sabitler(self) -> SonucYonetici:
        """Sabitler'i lazy yükler, cache'ler (sync boyunca bir kez)."""
        if self._sabitler_cache is None:
            try:
                self._sabitler_cache = self._registry.get("Sabitler").get_all()
            except Exception as e:
                return SonucYonetici.hata(e, "FileSyncService._get_sabitler")
        return SonucYonetici.tamam(veri=self._sabitler_cache)

    def _update_drive_path(self, record: dict, drive_link: str) -> SonucYonetici:
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
            return SonucYonetici.tamam("DrivePath güncellendi.")
        except Exception as e:
            return SonucYonetici.hata(e, "FileSyncService._update_drive_path")

    # Yinelenen ve tip uyumsuz versiyonlar kaldırıldı. Sadece SonucYonetici döndüren versiyonlar yukarıda mevcut.

    # Bool döndüren versiyon kaldırıldı. Sadece SonucYonetici döndüren versiyon yukarıda mevcut.

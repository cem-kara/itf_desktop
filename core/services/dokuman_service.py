"""
DokumanService — Tüm modüller için merkezi belge yükleme ve yönetim servisi.

Sorumluluklar:
- Drive klasörlerini otomatik bul/oluştur (Sabitler'e gerek yok)
- Dosyayı hibrit yükle (online→Drive, offline→local)
- Dokumanlar tablosuna kaydet
- Belge listeleme ve silme

Kullanım:
    svc = DokumanService(db)
    sonuc = svc.upload_and_save(
        file_path="C:/temp/rapor.pdf",
        entity_type="cihaz",
        entity_id="URO-XRY-SKP-10",
        belge_turu="NDK Lisansı",
        folder_name="Cihaz_Belgeler",
        doc_type="Cihaz_Belge",
    )
    # sonuc: {"ok": True, "mode": "drive", "drive_link": "...", "local_path": "..."}

Drive klasör yapısı (otomatik oluşturulur):
    REPYS/
        Cihaz_Belgeler/
        Personel_Belge/
        Personel_Resim/
        Personel_Diploma/
        RKE_Rapor/
        Saglik_Raporlari/
"""

import os
import uuid
from datetime import datetime
from typing import Optional, List, Dict

from core.logger import logger

from core.paths import DATA_DIR
from database.repository_registry import RepositoryRegistry
from core.hata_yonetici import SonucYonetici


# Drive'da tüm REPYS klasörlerinin üst klasörü.
# None → Drive root'una oluşturulur.
# Sabitler'de Kod='Sistem_DriveID', MenuEleman='REPYS_Root' varsa oradan okunur.
_REPYS_ROOT_FOLDER = "REPYS"


class DokumanService:
    """
    Merkezi belge yükleme ve yönetim servisi.
    Tüm paneller ve worker'lar bu servisi kullanır.
    """

    def __init__(self, db, registry: Optional[RepositoryRegistry] = None):
        # Allow callers to accidentally pass a RepositoryRegistry as first arg.
        # Normalize: ensure self._db is SQLiteManager-like and self._registry is RepositoryRegistry.
        if isinstance(db, RepositoryRegistry):
            registry = db
            db = getattr(registry, 'db', db)

        self._db = db
        self._registry = registry or RepositoryRegistry(db)
        # Drive klasör ID'leri process boyunca cache'lenir
        # {"Cihaz_Belgeler": "1AbC...", "REPYS_Root": "xyz..."}
        self._folder_cache: Dict[str, str] = {}

    # ──────────────────────────────────────────────────────────
    #  Ana API
    # ──────────────────────────────────────────────────────────

    def upload_and_save(
        self,
        file_path: str,
        entity_type: str,
        entity_id: str,
        belge_turu: str,
        folder_name: str,
        doc_type: str,
        aciklama: str = "",
        iliskili_id: Optional[str] = None,
        iliskili_tip: Optional[str] = None,
        custom_name: Optional[str] = None,
    ) -> SonucYonetici:
        """
        Dosyayı yükle ve Dokumanlar tablosuna kaydet.

        Args:
            file_path:    Yüklenecek dosyanın tam yolu
            entity_type:  "cihaz" | "personel" | "rke"
            entity_id:    Cihaz ID, TC, EkipmanNo vb.
            belge_turu:   "NDK Lisansı", "Rapor", "Diploma1" vb.
            folder_name:  "Cihaz_Belgeler", "Personel_Belge" vb.
            doc_type:     "Cihaz_Belge", "Personel_Belge", "RKE_Rapor" vb.
            aciklama:     Belge açıklaması
            iliskili_id:  İlişkili kayıt ID (opsiyonel)
            iliskili_tip: İlişkili kayıt tipi (opsiyonel)
            custom_name:  Özel dosya adı (None → otomatik üretilir)

        Returns:
            {
              "ok":         bool,
              "mode":       "drive" | "local" | "none",
              "drive_link": str,
              "local_path": str,
              "error":      str,
              "belge_adi":  str,  # DB'ye yazılan dosya adı
            }
        """
        if not file_path or not os.path.exists(file_path):
            return SonucYonetici.hata(Exception(f"Dosya bulunamadı: {file_path}"), "DokumanService.upload_and_save")

        # 1 — Dosya adı üret
        if not custom_name:
            _, ext = os.path.splitext(file_path)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_tur = belge_turu.replace(" ", "_")
            custom_name = f"{entity_id}_{safe_tur}_{ts}{ext}"
        
        # 2 — Hibrit yükleme
        upload_sonuc = self._upload(file_path, folder_name, custom_name, entity_type, entity_id)
        if not upload_sonuc.basarili:
            return upload_sonuc
        
        upload_data = upload_sonuc.veri or {}
        
        # 3 — Dokumanlar tablosuna kaydet (DokumanId atama)
        try:
            dokuman_id = str(uuid.uuid4())
            self._registry.get("Dokumanlar").insert({
                "DokumanId": dokuman_id,
                "EntityType":       entity_type,
                "EntityId":         str(entity_id),
                "BelgeTuru":        belge_turu,
                "Belge":            custom_name,
                "DocType":          doc_type,
                "DisplayName":      os.path.basename(file_path),
                "LocalPath":        upload_data.get("local_path") or "",
                "DrivePath":        upload_data.get("drive_link") or "",
                "BelgeAciklama":    aciklama,
                "YuklenmeTarihi":   datetime.now().isoformat(),
                "IliskiliBelgeID":  iliskili_id,
                "IliskiliBelgeTipi": iliskili_tip,
            })
            # expose DokumanId to caller
            logger.info(
                f"DokumanService: kayıt oluşturuldu "
                f"[{entity_type}/{entity_id}] {custom_name} ({upload_data.get('mode')})"
            )
            return SonucYonetici.tamam(
                f"Belge başarıyla yüklendi: {custom_name}",
                veri={
                    "dokuman_id": dokuman_id,
                    "mode": upload_data.get("mode"),
                    "drive_link": upload_data.get("drive_link"),
                    "local_path": upload_data.get("local_path"),
                    "belge_adi": custom_name,
                })
        except Exception as e:
            return SonucYonetici.hata(e, "DokumanService.upload_and_save")

    def get_belgeler(self, entity_type: str, entity_id: Optional[str] = None) -> SonucYonetici:
        """Entity'e ait tüm belgeleri döner.

        If `entity_id` is None, returns all documents matching `EntityType`.
        """
        try:
            repo = self._registry.get("Dokumanlar")
            if not entity_id or str(entity_id).lower() == "all":
                data = repo.get_where({"EntityType": entity_type})
            else:
                data = repo.get_where({
                "EntityType": entity_type,
                "EntityId":   str(entity_id),
            })
            return SonucYonetici.tamam(veri=data)
        except Exception as e:
            return SonucYonetici.hata(e, "DokumanService.get_belgeler")

    def sil(self, entity_type: str, entity_id: str, belge_turu: str, belge: str) -> SonucYonetici:
        """Belge kaydını DB'den sil (fiziksel dosyaya dokunmaz)."""
        try:
            repo = self._registry.get("Dokumanlar")
            pk = {
                "EntityType": entity_type,
                "EntityId":   str(entity_id),
                "BelgeTuru":  belge_turu,
                "Belge":      belge,
            }
            repo.delete(pk)
            return SonucYonetici.tamam(f"Belge silindi: [{entity_type}/{entity_id}] {belge}")
        except Exception as e:
            return SonucYonetici.hata(e, "DokumanService.sil")

    # ──────────────────────────────────────────────────────────
    #  İç metodlar
    # ──────────────────────────────────────────────────────────

    def _upload(self,
                file_path: str,
                folder_name: str,
                custom_name: str,
                entity_type: str,
                entity_id: str) -> SonucYonetici:
        """
        Online modda Drive'a, offline modda local'e yükler.

        Drive klasörü yoksa otomatik oluşturur (find_or_create_folder).
        Sabitler tablosuna yazmaz — ID'ler process memory'de cache'lenir.
        """
        from core.config import AppConfig

        if AppConfig.is_online_mode():
            try:
                folder_id = self._get_or_create_drive_folder(folder_name)
                from database.google.drive import get_drive_service
                drive = get_drive_service()
                link = drive.upload_file(
                    file_path,
                    parent_folder_id=folder_id,
                    custom_name=custom_name,
                )
                if link:
                    return SonucYonetici.tamam(veri={"mode": "drive", "drive_link": link})
                logger.warning("Drive upload link döndürmedi, local'e düşülüyor")
            except Exception as e:
                logger.warning(f"Drive yükleme başarısız, local'e düşülüyor: {e}")

        # Offline veya Drive başarısız → local'e kaydet
        local_save_sonuc = self._save_local(file_path, folder_name, custom_name, entity_type, entity_id)
        if local_save_sonuc.basarili:
            return SonucYonetici.tamam(veri={"mode": "local", "local_path": local_save_sonuc.veri})
        else:
            return SonucYonetici.hata(Exception("Local kopyalama başarısız"), "DokumanService._upload")



    def _get_or_create_drive_folder(self, folder_name: str) -> str:
        """
        Drive'da klasör ID'sini döner, yoksa oluşturur.
        REPYS_Root altına oluşturur, ID'leri memory'de cache'ler.
        """
        if folder_name in self._folder_cache:
            return self._folder_cache[folder_name]

        from database.google.drive import get_drive_service
        drive = get_drive_service()

        # REPYS kök klasörünü bul/oluştur
        root_id = self._folder_cache.get("__root__")
        if not root_id:
            root_id = drive.find_or_create_folder(_REPYS_ROOT_FOLDER)
            self._folder_cache["__root__"] = root_id

        # Alt klasörü bul/oluştur
        folder_id = drive.find_or_create_folder(folder_name, parent_folder_id=root_id)
        self._folder_cache[folder_name] = folder_id
        return folder_id

    def _save_local(
        self,
        file_path: str,
        folder_name: str,
        custom_name: str,
        entity_type: str,
        entity_id: str,
    ) -> SonucYonetici:
        """Dosyayı local offline_uploads klasörüne kopyalar."""
        import shutil
        try:
            entity_type = str(entity_type or "").strip().lower()
            entity_id = str(entity_id or "").strip()

            if entity_type == "personel" and entity_id:
                # Personel dosyaları tek klasörde toplanır:
                # data/offline_uploads/personel/<TCKimlikNo>/
                target_dir = os.path.join(DATA_DIR, "offline_uploads", "personel", entity_id)
            elif entity_type == "cihaz" and entity_id:
                # Cihaz belgeleri cihaz id altına kaydedilir:
                # data/offline_uploads/Cihaz_Belgeler/<Cihazid>/
                target_dir = os.path.join(DATA_DIR, "offline_uploads", "Cihaz_Belgeler", entity_id)
            else:
                target_dir = os.path.join(DATA_DIR, "offline_uploads", folder_name)

            os.makedirs(target_dir, exist_ok=True)
            dest = os.path.join(target_dir, custom_name)

            # Aynı isimde dosya varsa _1, _2 ... ekle
            if os.path.exists(dest):
                root, ext = os.path.splitext(custom_name)
                i = 1
                while os.path.exists(dest):
                    dest = os.path.join(target_dir, f"{root}_{i}{ext}")
                    i += 1

            shutil.copy2(file_path, dest)
            logger.info(f"DokumanService: local kayıt → {dest}")
            return SonucYonetici.tamam(veri=dest)
        except Exception as e:
            return SonucYonetici.hata(e, "DokumanService._save_local")

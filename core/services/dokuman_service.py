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
from datetime import datetime
from typing import Optional, List, Dict

from core.logger import logger
from core.paths import DATA_DIR
from database.repository_registry import RepositoryRegistry


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
    ) -> dict:
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
        result = {
            "ok": False, "mode": "none",
            "drive_link": "", "local_path": "", "error": "", "belge_adi": "",
        }

        if not file_path or not os.path.exists(file_path):
            result["error"] = f"Dosya bulunamadı: {file_path}"
            logger.warning(result["error"])
            return result

        # 1 — Dosya adı üret
        if not custom_name:
            _, ext = os.path.splitext(file_path)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_tur = belge_turu.replace(" ", "_")
            custom_name = f"{entity_id}_{safe_tur}_{ts}{ext}"

        result["belge_adi"] = custom_name

        # 2 — Hibrit yükleme
        upload = self._upload(file_path, folder_name, custom_name)

        if upload["mode"] == "none":
            result["error"] = upload.get("error", "Yükleme başarısız")
            return result

        result.update({
            "mode":       upload["mode"],
            "drive_link": upload.get("drive_link", ""),
            "local_path": upload.get("local_path", ""),
        })

        # 3 — Dokumanlar tablosuna kaydet
        try:
            self._registry.get("Dokumanlar").insert({
                "EntityType":       entity_type,
                "EntityId":         str(entity_id),
                "BelgeTuru":        belge_turu,
                "Belge":            custom_name,
                "DocType":          doc_type,
                "DisplayName":      os.path.basename(file_path),
                "LocalPath":        upload.get("local_path") or "",
                "DrivePath":        upload.get("drive_link") or "",
                "BelgeAciklama":    aciklama,
                "YuklenmeTarihi":   datetime.now().isoformat(),
                "IliskiliBelgeID":  iliskili_id,
                "IliskiliBelgeTipi": iliskili_tip,
            })
            result["ok"] = True
            logger.info(
                f"DokumanService: kayıt oluşturuldu "
                f"[{entity_type}/{entity_id}] {custom_name} ({upload['mode']})"
            )
        except Exception as e:
            logger.error(f"DokumanService: Dokumanlar kaydı eklenemedi: {e}")
            result["error"] = f"DB kaydı başarısız: {e}"

        return result

    def get_belgeler(self, entity_type: str, entity_id: str) -> List[dict]:
        """Entity'e ait tüm belgeleri döner."""
        try:
            return self._registry.get("Dokumanlar").get_where({
                "EntityType": entity_type,
                "EntityId":   str(entity_id),
            })
        except Exception as e:
            logger.error(f"DokumanService: get_belgeler hatası: {e}")
            return []

    def sil(
        self,
        entity_type: str,
        entity_id: str,
        belge_turu: str,
        belge: str,
    ) -> bool:
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
            logger.info(f"DokumanService: silindi [{entity_type}/{entity_id}] {belge}")
            return True
        except Exception as e:
            logger.error(f"DokumanService: silme hatası: {e}")
            return False

    # ──────────────────────────────────────────────────────────
    #  İç metodlar
    # ──────────────────────────────────────────────────────────

    def _upload(self, file_path: str, folder_name: str, custom_name: str) -> dict:
        """
        Online modda Drive'a, offline modda local'e yükler.

        Drive klasörü yoksa otomatik oluşturur (find_or_create_folder).
        Sabitler tablosuna yazmaz — ID'ler process memory'de cache'lenir.
        """
        from core.config import AppConfig

        result = {"mode": "none", "drive_link": "", "local_path": "", "error": ""}

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
                    result.update({"mode": "drive", "drive_link": link})
                    return result
                logger.warning("Drive upload link döndürmedi, local'e düşülüyor")
            except Exception as e:
                logger.warning(f"Drive yükleme başarısız, local'e düşülüyor: {e}")

        # Offline veya Drive başarısız → local'e kaydet
        local_path = self._save_local(file_path, folder_name, custom_name)
        if local_path:
            result.update({"mode": "local", "local_path": local_path})
        else:
            result["error"] = "Local kopyalama başarısız"

        return result

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
    ) -> Optional[str]:
        """Dosyayı local offline_uploads klasörüne kopyalar."""
        import shutil
        try:
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
            return dest
        except Exception as e:
            logger.error(f"DokumanService: local kayıt hatası: {e}")
            return None

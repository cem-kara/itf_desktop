"""
BackupService — Veritabanı yedekleme ve geri yükleme servisi

Sorumluluklar:
- Manuel yedek oluşturma (DB + dosyalar)
- Yedek listesini getirme
- Yedek geri yükleme
- Eski yedekleri temizleme
- Disk alanı kontrolü
"""
from __future__ import annotations

import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.logger import logger
from core.hata_yonetici import SonucYonetici

from core.paths import DB_PATH, DATA_DIR, LOG_DIR


class BackupService:
    """Veritabanı yedekleme servisi"""
    
    BACKUP_DIR = os.path.join(DATA_DIR, "backups")
    
    def __init__(self):
        """Backup servisi oluştur"""
        # Backup klasörünü oluştur
        os.makedirs(self.BACKUP_DIR, exist_ok=True)
    
    def create_backup(self, description: str = "") -> SonucYonetici:
        """
        Yeni yedek oluştur.
        
        Args:
            description: Yedek açıklaması (opsiyonel)
        
        Returns:
            Dict: {"success": bool, "path": str, "size_mb": float, "message": str}
        """
        try:
            # Veritabanı dosyası var mı?
            if not os.path.exists(DB_PATH):
                return SonucYonetici.hata(
                    ValueError("Veritabanı dosyası bulunamadı"),
                    "BackupService.create_backup"
                )
            
            # Yedek dosya adı: backup_YYYYMMDD_HHMMSS.db
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{timestamp}.db"
            backup_path = os.path.join(self.BACKUP_DIR, backup_filename)
            
            # SQLite veritabanını kopyala (WAL dosyalarıyla birlikte)
            try:
                # Ana dosyayı kopyala
                shutil.copy2(DB_PATH, backup_path)
                logger.info(f"Veritabanı kopyalandı: {backup_filename}")
                
                # WAL ve SHM dosyalarını da kopyala (varsa)
                wal_path = DB_PATH + "-wal"
                shm_path = DB_PATH + "-shm"
                
                if os.path.exists(wal_path):
                    shutil.copy2(wal_path, backup_path + "-wal")
                if os.path.exists(shm_path):
                    shutil.copy2(shm_path, backup_path + "-shm")
                    
            except PermissionError:
                # WAL dosyaları kilitli olabilir - sadece main DB'yi kopyala
                logger.warning("WAL dosyaları kopyalanamadı (kilitli), sadece main DB kopyalandı")
            
            # Dosya boyutu
            size_bytes = os.path.getsize(backup_path)
            size_mb = size_bytes / (1024 * 1024)
            
            # Açıklama dosyası oluştur (opsiyonel)
            if description:
                desc_path = backup_path.replace(".db", ".txt")
                with open(desc_path, 'w', encoding='utf-8') as f:
                    f.write(f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Açıklama: {description}\n")
            
            logger.info(f"Yedek oluşturuldu: {backup_filename} ({size_mb:.2f} MB)")
            
            return SonucYonetici.tamam(
                mesaj=f"Yedek başarıyla oluşturuldu: {backup_filename}",
                veri={
                    "path": backup_path,
                    "size_mb": round(size_mb, 2),
                }
            )
            
        except Exception as e:
            logger.error(f"Yedek oluşturma hatası: {str(e)}", exc_info=True)
            return SonucYonetici.hata(e, "BackupService.create_backup")
    
    def get_backups(self) -> SonucYonetici:
        """
        Tüm yedekleri listele (hem .db hem .zip dosyaları).
        
        Returns:
            List[Dict]: [{"filename": str, "path": str, "size_mb": float, 
                         "created": str, "description": str}, ...]
        """
        backups = []
        
        try:
            # Sadece DB yedekleri (backup_*.db)
            for file in Path(self.BACKUP_DIR).glob("backup_*.db"):
                try:
                    size_bytes = os.path.getsize(file)
                    size_mb = size_bytes / (1024 * 1024)
                    
                    # Oluşturma tarihi
                    mtime = os.path.getmtime(file)
                    created = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Açıklama dosyası var mı?
                    desc_path = str(file).replace(".db", ".txt")
                    description = ""
                    if os.path.exists(desc_path):
                        with open(desc_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            for line in lines:
                                if line.startswith("Açıklama:"):
                                    description = line.replace("Açıklama:", "").strip()
                                    break
                    
                    backups.append({
                        "filename": file.name,
                        "path": str(file),
                        "size_mb": round(size_mb, 2),
                        "created": created,
                        "description": description
                    })
                    
                except Exception as e:
                    logger.warning(f"Yedek bilgisi alınamadı ({file}): {e}")
            
            # Tam yedekler (backup_full_*.zip)
            for file in Path(self.BACKUP_DIR).glob("backup_full_*.zip"):
                try:
                    size_bytes = os.path.getsize(file)
                    size_mb = size_bytes / (1024 * 1024)
                    
                    # Oluşturma tarihi
                    mtime = os.path.getmtime(file)
                    created = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Açıklama dosyası var mı? (.txt dosyası)
                    desc_path = str(file).replace(".zip", ".txt")
                    description = ""
                    if os.path.exists(desc_path):
                        with open(desc_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            for line in lines:
                                if line.startswith("Açıklama:"):
                                    description = line.replace("Açıklama:", "").strip()
                                    break
                    
                    backups.append({
                        "filename": file.name,
                        "path": str(file),
                        "size_mb": round(size_mb, 2),
                        "created": created,
                        "description": description
                    })
                    
                except Exception as e:
                    logger.warning(f"Yedek bilgisi alınamadı ({file}): {e}")
            
            # En yeni önce sırala
            backups.sort(key=lambda x: x["created"], reverse=True)
            
        except Exception as e:
            logger.error(f"Yedek listesi hatası: {e}")
        
        return SonucYonetici.tamam(veri=backups)
    
    def restore_backup(self, backup_path: str) -> SonucYonetici:
        """
        Yedeği geri yükle.
        
        Args:
            backup_path: Yedek dosyasının tam yolu
        
        Returns:
            Dict: {"success": bool, "message": str}
        """
        try:
            # Yedek dosyası var mı?
            if not os.path.exists(backup_path):
                return SonucYonetici.hata(
                    ValueError("Yedek dosyası bulunamadı"),
                    "BackupService.restore_backup"
                )
            
            # Mevcut veritabanını yedekle (güvenlik için)
            safety_backup_path = DB_PATH + ".before_restore"
            if os.path.exists(DB_PATH):
                shutil.copy2(DB_PATH, safety_backup_path)
                logger.info(f"Güvenlik yedeği oluşturuldu: {safety_backup_path}")
            
            # Yedeği geri yükle
            shutil.copy2(backup_path, DB_PATH)
            
            logger.info(f"Yedek geri yüklendi: {os.path.basename(backup_path)}")
            
            return SonucYonetici.tamam(
                mesaj="Yedek başarıyla geri yüklendi.\n\nUygulama yeniden başlatılmalıdır!"
            )
            
        except Exception as e:
            logger.error(f"Yedek geri yükleme hatası: {str(e)}", exc_info=True)
            return SonucYonetici.hata(e, "BackupService.restore_backup")
    
    def delete_backup(self, backup_path: str) -> SonucYonetici:
        """
        Yedeği sil.
        
        Args:
            backup_path: Yedek dosyasının tam yolu
        
        Returns:
            Dict: {"success": bool, "message": str}
        """
        try:
            # Dosya var mı?
            if not os.path.exists(backup_path):
                return SonucYonetici.hata(
                    ValueError("Yedek dosyası bulunamadı"),
                    "BackupService.delete_backup"
                )
            
            # Dosyayı silmeye çalış
            deleted_files = []
            errors = []
            
            try:
                os.remove(backup_path)
                deleted_files.append(os.path.basename(backup_path))
            except PermissionError as e:
                errors.append(f"Ana dosya silinemiyor: {e}")
            except Exception as e:
                errors.append(f"Ana dosya silinemiyor: {e}")
                return SonucYonetici.hata(e, "BackupService.delete_backup")
            
            # Partner dosyaları sil (.txt açıklama dosyası)
            base_path = backup_path.rsplit('.', 1)[0]  # Uzantıyı kaldır
            desc_path = base_path + ".txt"
            if os.path.exists(desc_path):
                try:
                    os.remove(desc_path)
                    deleted_files.append(os.path.basename(desc_path))
                except Exception as e:
                    logger.warning(f"Açıklama dosyası silinemedi ({desc_path}): {e}")
            
            # .db dosyaları için WAL ve SHM dosyalarını da sil
            if backup_path.endswith('.db'):
                wal_path = backup_path + "-wal"
                shm_path = backup_path + "-shm"
                
                if os.path.exists(wal_path):
                    try:
                        os.remove(wal_path)
                        deleted_files.append(os.path.basename(wal_path))
                    except Exception as e:
                        logger.warning(f"WAL dosyası silinemedi ({wal_path}): {e}")
                
                if os.path.exists(shm_path):
                    try:
                        os.remove(shm_path)
                        deleted_files.append(os.path.basename(shm_path))
                    except Exception as e:
                        logger.warning(f"SHM dosyası silinemedi ({shm_path}): {e}")
            
            logger.info(f"Yedek silindi: {os.path.basename(backup_path)} ({len(deleted_files)} dosya)")
            
            return SonucYonetici.tamam(
                mesaj=f"Yedek başarıyla silindi ({len(deleted_files)} dosya)",
                veri={"deleted_files": deleted_files}
            )
            
        except Exception as e:
            logger.error(f"Yedek silme hatası: {str(e)}", exc_info=True)
            return SonucYonetici.hata(e, "BackupService.delete_backup")
    
    def create_backup_with_files(
        self,
        description: str = "",
        include_folders: Optional[list[str]] = None
    ) -> SonucYonetici:
        """
        Veritabanı + seçili dosya/klasörleri ZIP olarak yedekle.
        
        Args:
            description: Yedek açıklaması
            include_folders: Dahil edilecek klasörler (mutlak yollar)
                Örn: ["/path/to/offline_uploads", "/path/to/logs", "/path/to/templates"]
        
        Returns:
            Dict: {"success": bool, "path": str, "size_mb": float, "message": str}
        """
        try:
            if not os.path.exists(DB_PATH):
                return SonucYonetici.hata(
                    ValueError("Veritabanı dosyası bulunamadı"),
                    "BackupService.create_backup_with_files"
                )
            
            # ZIP dosya adı
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_filename = f"backup_full_{timestamp}.zip"
            zip_path = os.path.join(self.BACKUP_DIR, zip_filename)
            
            # ZIP oluştur
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Veritabanı dosyasını ekle
                zf.write(DB_PATH, arcname="local.db")
                logger.info("ZIP'e eklendi: local.db")
                
                # Seçili klasörleri ekle
                if include_folders:
                    for folder_path in include_folders:
                        # folder_path mutlak yol olması gerekir
                        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
                            logger.warning(f"Klasör bulunamadı: {folder_path}")
                            continue
                        
                        folder_name = os.path.basename(folder_path)
                        
                        # Klasördeki tüm dosyaları ekle
                        for root, dirs, files in os.walk(folder_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                # ZIP içinde göreli yolu koru
                                rel_path = os.path.relpath(file_path, folder_path)
                                arcname = os.path.join(folder_name, rel_path)
                                try:
                                    zf.write(file_path, arcname=arcname)
                                except Exception as e:
                                    logger.warning(f"Dosya eklenemedi ({file_path}): {e}")
                        
                        logger.info(f"ZIP'e eklendi: {folder_name}/")
            
            # Dosya boyutu
            size_bytes = os.path.getsize(zip_path)
            size_mb = size_bytes / (1024 * 1024)
            
            # Açıklama dosyası
            if description:
                desc_path = zip_path.replace(".zip", ".txt")
                with open(desc_path, 'w', encoding='utf-8') as f:
                    f.write(f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Açıklama: {description}\n")
                    if include_folders:
                        f.write(f"Dahil Klasörler: {', '.join(include_folders)}\n")
            
            logger.info(f"Tam yedek oluşturuldu: {zip_filename} ({size_mb:.2f} MB)")
            
            return SonucYonetici.tamam(
                mesaj=f"Tam yedek başarıyla oluşturuldu: {zip_filename} ({size_mb:.2f} MB)",
                veri={
                    "path": zip_path,
                    "size_mb": round(size_mb, 2),
                }
            )
            
        except Exception as e:
            logger.error(f"Tam yedek oluşturma hatası: {str(e)}", exc_info=True)
            return SonucYonetici.hata(e, "BackupService.create_backup_with_files")
    
    def restore_backup_with_files(self, zip_path: str, restore_folders: bool = True) -> SonucYonetici:
        """
        ZIP yedekten veritabanı ve dosyaları geri yükle.
        
        Args:
            zip_path: ZIP dosyasının tam yolu
            restore_folders: Klasörleri de geri yükle mi?
        
        Returns:
            Dict: {"success": bool, "message": str}
        """
        try:
            if not os.path.exists(zip_path):
                return SonucYonetici.hata(
                    ValueError("ZIP yedek dosyası bulunamadı"),
                    "BackupService.restore_backup_with_files"
                )
            
            # Güvenlik: Mevcut veritabanını yedekle
            safety_backup_path = DB_PATH + ".before_restore"
            if os.path.exists(DB_PATH):
                shutil.copy2(DB_PATH, safety_backup_path)
                logger.info(f"Güvenlik yedeği oluşturuldu: {safety_backup_path}")
            
            # ZIP'i çıkar
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # Veritabanını geri yükle
                if "local.db" in zf.namelist():
                    zf.extract("local.db", path=DATA_DIR)
                    # Dosyayı doğru yere taşı
                    extracted_db = os.path.join(DATA_DIR, "local.db")
                    shutil.move(extracted_db, DB_PATH)
                    logger.info("Veritabanı geri yüklendi")
                
                # Klasörleri geri yükle
                if restore_folders:
                    # ZIP'teki tüm dosyaları process et
                    for file_info in zf.filelist:
                        filename = file_info.filename
                        
                        # Veritabanı dosyasını atla (zaten yükledi)
                        if filename == "local.db":
                            continue
                        
                        # logs/ klasöründeki dosyalar → root LOG_DIR'e
                        if filename.startswith("logs/"):
                            rel_path = filename[5:]  # "logs/" prefix'i kaldır
                            target_path = os.path.join(LOG_DIR, rel_path)
                        # offline_uploads/, templates/ vb. → DATA_DIR altına
                        else:
                            target_path = os.path.join(DATA_DIR, filename)
                        
                        # Hedef klasörünü oluştur
                        target_dir = os.path.dirname(target_path)
                        os.makedirs(target_dir, exist_ok=True)
                        
                        # Dosya ise çıkart
                        if not filename.endswith('/'):
                            with zf.open(file_info) as src, open(target_path, 'wb') as tgt:
                                tgt.write(src.read())
                    
                    logger.info("Dosya klasörleri geri yüklendi")
            
            logger.info(f"ZIP yedek geri yüklendi: {os.path.basename(zip_path)}")
            
            return SonucYonetici.tamam(
                mesaj="Tam yedek başarıyla geri yüklendi.\n\nUygulama yeniden başlatılmalıdır!"
            )
            
        except Exception as e:
            logger.error(f"ZIP yedek geri yükleme hatası: {str(e)}", exc_info=True)
            return SonucYonetici.hata(e, "BackupService.restore_backup_with_files")
    
    def cleanup_old_backups(self, keep_count: int = 10) -> SonucYonetici:
        """
        Eski yedekleri temizle (en yeni N tanesini tut).
        
        Args:
            keep_count: Tutulacak yedek sayısı
        
        Returns:
            Dict: {"success": bool, "deleted_count": int, "freed_mb": float, "message": str}
        """
        try:
            backups_sonuc = self.get_backups()
            if not backups_sonuc.basarili:
                return backups_sonuc
            backups = backups_sonuc.veri or []
            
            if len(backups) <= keep_count:
                return SonucYonetici.tamam(
                    mesaj=f"Temizlenecek yedek yok (toplam {len(backups)} yedek)",
                    veri={"deleted_count": 0, "freed_mb": 0}
                )
            
            # Silinecek yedekler
            to_delete = backups[keep_count:]
            
            deleted_count = 0
            freed_space = 0
            
            for backup in to_delete:
                size_mb = backup["size_mb"]
                result = self.delete_backup(backup["path"])
                if result.basarili:
                    deleted_count += 1
                    freed_space += size_mb
            
            logger.info(f"Eski yedekler temizlendi: {deleted_count} dosya, {freed_space:.2f} MB")
            
            return SonucYonetici.tamam(
                mesaj=f"{deleted_count} eski yedek silindi ({freed_space:.2f} MB boşaltıldı)",
                veri={
                    "deleted_count": deleted_count,
                    "freed_mb": round(freed_space, 2),
                }
            )
            
        except Exception as e:
            logger.error(f"Yedek temizleme hatası: {str(e)}", exc_info=True)
            return SonucYonetici.hata(e, "BackupService.cleanup_old_backups")
    
    def get_disk_space_info(self) -> SonucYonetici:
        """
        Disk alanı bilgisi.
        
        Returns:
            Dict: {"total_mb": float, "used_mb": float, "free_mb": float, "percent_used": float}
        """
        try:
            import psutil
            
            # Veritabanı klasörünün bulunduğu disk
            disk_usage = psutil.disk_usage(DATA_DIR)
            
            return SonucYonetici.tamam(veri={
                "total_mb": round(disk_usage.total / (1024 * 1024), 2),
                "used_mb": round(disk_usage.used / (1024 * 1024), 2),
                "free_mb": round(disk_usage.free / (1024 * 1024), 2),
                "percent_used": round(disk_usage.percent, 2)
            })
            
        except ImportError:
            # psutil yoksa basit bilgi döndür
            logger.warning("psutil yüklü değil, disk bilgisi sınırlı")
            return SonucYonetici.tamam(veri={
                "total_mb": 0,
                "used_mb": 0,
                "free_mb": 0,
                "percent_used": 0
            })
        except Exception as e:
            logger.error(f"Disk bilgisi hatası: {e}")
            return SonucYonetici.hata(e, "BackupService.get_disk_space_info")
    
    def get_backup_stats(self) -> SonucYonetici:
        """
        Yedekleme istatistikleri.
        
        Returns:
            Dict: {"backup_count": int, "total_size_mb": float, "oldest": str, "newest": str}
        """
        try:
            backups_sonuc = self.get_backups()
            if not backups_sonuc.basarili:
                return backups_sonuc
            backups = backups_sonuc.veri or []
            
            if not backups:
                return SonucYonetici.tamam(veri={
                    "backup_count": 0,
                    "total_size_mb": 0,
                    "oldest": "",
                    "newest": ""
                })
            
            total_size = sum(b["size_mb"] for b in backups)
            oldest = backups[-1]["created"] if backups else ""
            newest = backups[0]["created"] if backups else ""
            
            return SonucYonetici.tamam(veri={
                "backup_count": len(backups),
                "total_size_mb": round(total_size, 2),
                "oldest": oldest,
                "newest": newest
            })
            
        except Exception as e:
            logger.error(f"Yedek istatistikleri hatası: {e}")
            return SonucYonetici.hata(e, "BackupService.get_backup_stats")

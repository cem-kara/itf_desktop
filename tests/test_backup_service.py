"""
BackupService Test Suite

Kapsam:
- Başlatma
- create_backup: yedek oluştur
- get_backups: yedek listesini getir
- get_backup_info: yedek bilgisi
- restore_backup: geri yükle
- cleanup_old_backups: eski yedekleri temizle

Not: Tüm metodlar SonucYonetici döndürür.
"""
import pytest
from unittest.mock import patch
from pathlib import Path
from core.services.backup_service import BackupService


# ─────────────────────────────────────────────────────────────
#  Başlatma
# ─────────────────────────────────────────────────────────────

class TestBackupServiceInit:
    def test_init_olustur(self):
        """BackupService oluşturulabilir."""
        with patch("os.makedirs"):
            svc = BackupService()
            assert svc is not None

    def test_backup_dir_create(self):
        """Backup klasörü oluşturulur."""
        with patch("os.makedirs") as mock_mkdir:
            svc = BackupService()
            mock_mkdir.assert_called()


# ─────────────────────────────────────────────────────────────
#  create_backup
# ─────────────────────────────────────────────────────────────

class TestCreateBackup:
    def test_create_backup_basarili(self):
        """Yedek başarıyla oluşturulur."""
        with patch("os.path.exists", return_value=True), \
             patch("os.path.getsize", return_value=1024*1024*50), \
             patch("shutil.copy2"), \
             patch("os.makedirs"), \
             patch("builtins.open", create=True):
            svc = BackupService()
            result = svc.create_backup("Test yedek")
            assert result.basarili is True
            assert "path" in result.veri
            assert "size_mb" in result.veri

    def test_create_backup_db_bulunamadi(self):
        """DB file bulunamazsa hata döndürür."""
        with patch("os.path.exists", return_value=False), \
             patch("os.makedirs"):
            svc = BackupService()
            result = svc.create_backup("Test")
            assert result.basarili is False

    def test_create_backup_exception(self):
        """Exception durumunda hata döndürür."""
        with patch("os.path.exists", return_value=True), \
             patch("shutil.copy2", side_effect=Exception("Kopyalama hatası")), \
             patch("os.makedirs"):
            svc = BackupService()
            result = svc.create_backup("Test")
            assert result.basarili is False

    def test_create_backup_bos_aciklama(self):
        """Açıklama olmadan da çalışır."""
        with patch("os.path.exists", return_value=True), \
             patch("os.path.getsize", return_value=1024*100), \
             patch("shutil.copy2"), \
             patch("os.makedirs"):
            svc = BackupService()
            result = svc.create_backup()
            assert result.basarili is True


# ─────────────────────────────────────────────────────────────
#  get_backups
# ─────────────────────────────────────────────────────────────

class TestGetBackups:
    def test_backuplari_listele(self):
        """Yedekleri döner."""
        mock_paths = [
            Path("backup_20260101_120000.db"),
            Path("backup_20260102_120000.db"),
        ]
        with patch("pathlib.Path.glob", side_effect=[mock_paths, []]), \
             patch("os.path.getsize", return_value=1024*50), \
             patch("os.path.getmtime", return_value=1000000000), \
             patch("os.path.exists", return_value=False), \
             patch("os.makedirs"):
            svc = BackupService()
            result = svc.get_backups()
            assert result.basarili is True
            assert len(result.veri) > 0

    def test_backup_yok(self):
        """Yedek yoksa boş liste döner."""
        with patch("pathlib.Path.glob", side_effect=[[], []]), \
             patch("os.makedirs"):
            svc = BackupService()
            result = svc.get_backups()
            assert result.basarili is True
            assert result.veri == []

    def test_glob_exceptionde_bile_tamam_doner(self):
        """Servis listeleme hatasında boş/tamam döner (tasarım gereği)."""
        with patch("pathlib.Path.glob", side_effect=Exception("Listele hatası")), \
             patch("os.makedirs"):
            svc = BackupService()
            result = svc.get_backups()
            assert result.basarili is True


# ─────────────────────────────────────────────────────────────
#  restore_backup
# ─────────────────────────────────────────────────────────────

class TestRestoreBackup:
    def test_restore_basarili(self):
        """Yedek geri yükleme başarılı."""
        with patch("os.path.exists", return_value=True), \
             patch("shutil.copy2"), \
             patch("os.makedirs"):
            svc = BackupService()
            result = svc.restore_backup("backup_test.db")
            assert result.basarili is True

    def test_restore_backup_bulunamadi(self):
        """Geri yüklenecek backup bulunamazsa hata."""
        with patch("os.path.exists", return_value=False), \
             patch("os.makedirs"):
            svc = BackupService()
            result = svc.restore_backup("backup_yok.db")
            assert result.basarili is False

    def test_restore_copy_error(self):
        """Kopyalama hatası durumunda hata döndürür."""
        with patch("os.path.exists", return_value=True), \
             patch("shutil.copy2", side_effect=Exception("Kopyalama hatası")), \
             patch("os.makedirs"):
            svc = BackupService()
            result = svc.restore_backup("backup_test.db")
            assert result.basarili is False


# ─────────────────────────────────────────────────────────────
#  cleanup_old_backups
# ─────────────────────────────────────────────────────────────

class TestCleanupOldBackups:
    def test_eski_yedekleri_sil(self):
        """keep_count üstündeki yedekleri temizler."""
        mock_paths = [
            Path("backup_1.db"),
            Path("backup_2.db"),
            Path("backup_3.db"),
        ]
        with patch("pathlib.Path.glob", return_value=mock_paths), \
             patch("os.path.getmtime", return_value=1000), \
             patch("os.path.getsize", return_value=1024), \
             patch("os.path.exists", return_value=False), \
             patch("os.remove"), \
             patch("os.makedirs"):
            svc = BackupService()
            result = svc.cleanup_old_backups(keep_count=1)
            assert result.basarili is True
            assert "deleted_count" in result.veri

    def test_cleanup_no_backups(self):
        """Yedek yoksa problem değil."""
        with patch("pathlib.Path.glob", return_value=[]), \
             patch("os.makedirs"):
            svc = BackupService()
            result = svc.cleanup_old_backups(keep_count=10)
            assert result.basarili is True

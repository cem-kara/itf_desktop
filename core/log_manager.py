# core/log_manager.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Log Yönetimi Utility
# 
# Log rotasyonu, disk kullanımı, cleanup ve monitoring için
# yardımcı araçlar ve istatistikler sağlar.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import os
import glob
from datetime import datetime, timedelta
from core.logger import logger

from core.paths import LOG_DIR
from core.config import AppConfig


class LogStatistics:
    """Log dosyalarının istatistiklerini hesaplar."""

    @staticmethod
    def get_log_size(log_file):
        """Dosya boyutunu MB cinsinden döner."""
        if not os.path.exists(log_file):
            return 0
        return os.path.getsize(log_file) / (1024 * 1024)  # MB

    @staticmethod
    def get_total_log_size():
        """Tüm log dosyalarının toplam boyutunu döner."""
        pattern = os.path.join(LOG_DIR, "*.log*")
        total = 0
        for log_file in glob.glob(pattern):
            total += os.path.getsize(log_file)
        return total / (1024 * 1024)  # MB
    
    @staticmethod
    def get_log_stats():
        """Tüm log dosyalarının detaylı istatistiklerini döner."""
        stats = {}
        
        # Tüm log dosyaları (rotated includig)
        for log_file in glob.glob(os.path.join(LOG_DIR, "*.log*")):
            file_name = os.path.basename(log_file)
            size_mb = os.path.getsize(log_file) / (1024 * 1024)
            mtime = os.path.getmtime(log_file)
            mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            lines = LogStatistics.count_lines(log_file)
            
            stats[file_name] = {
                "size_mb": round(size_mb, 2),
                "lines": lines,
                "last_modified": mtime_str,
                "path": log_file
            }
        
        return stats
    
    @staticmethod
    def count_lines(file_path):
        """Dosyadaki satır sayısını döner (büyük dosyalarda hızlı)."""
        try:
            with open(file_path, 'rb') as f:
                return sum(1 for _ in f)
        except Exception as e:
            logger.warning(f"Satır sayısı hesaplamada hata ({file_path}): {e}")
            return 0
    

class LogCleanup:
    """Eski log dosyalarını temizler ve disk alanını yönetir."""

    @staticmethod
    def get_backup_logs():
        """Rotated (backup) log dosyalarının listesini döner."""
        pattern = os.path.join(LOG_DIR, "*.log.*")
        return sorted(glob.glob(pattern))

    @staticmethod
    def cleanup_old_logs(days=7):
        """
        Belirtilen günden eski log dosyalarını siler.
        
        Args:
            days: Kaç gün eski dosyalar silinecek (default: 7 gün)
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        cutoff_timestamp = cutoff_time.timestamp()
        
        deleted_count = 0
        freed_space = 0
        
        for log_file in LogCleanup.get_backup_logs():
            mtime = os.path.getmtime(log_file)
            
            if mtime < cutoff_timestamp:
                try:
                    size = os.path.getsize(log_file)
                    os.remove(log_file)
                    freed_space += size
                    deleted_count += 1
                    logger.info(f"Eski log silindi: {os.path.basename(log_file)} ({size/1024:.1f} KB)")
                except Exception as e:
                    logger.error(f"Log silememe hatası ({log_file}): {e}")
        
        if deleted_count > 0:
            logger.info(f"✓ {deleted_count} eski log silindi, {freed_space/(1024*1024):.1f} MB boşaltıldı")
        
        return deleted_count, freed_space

    @staticmethod
    def cleanup_by_space(max_size_mb=100):
        """
        Log dizininin toplam boyutunu limitin altında tutmaya çalışır.
        Limitin üzerindeyse en eski dosyaları siler.
        
        Args:
            max_size_mb: Log dizininin maksimum boyutu (MB)
        """
        total_size = LogStatistics.get_total_log_size()
        
        if total_size <= max_size_mb:
            logger.debug(f"Log dizini boyutu OK: {total_size:.1f} MB / {max_size_mb} MB")
            return 0, 0
        
        logger.warning(f"Log dizini limitle aşıyor: {total_size:.1f} MB > {max_size_mb} MB")
        
        # En eski backup'ları sil
        backup_logs = sorted(
            LogCleanup.get_backup_logs(),
            key=lambda f: os.path.getmtime(f)  # Eski olan önce
        )
        
        deleted_count = 0
        freed_space = 0
        
        for log_file in backup_logs:
            if total_size <= max_size_mb:
                break
            
            try:
                size = os.path.getsize(log_file)
                os.remove(log_file)
                freed_space += size
                total_size -= (size / (1024 * 1024))
                deleted_count += 1
                logger.info(f"Space cleanup: {os.path.basename(log_file)} silindi")
            except Exception as e:
                logger.error(f"Cleanup hatası: {e}")
        
        if deleted_count > 0:
            logger.info(f"✓ Space cleanup: {deleted_count} log silindi, {freed_space/(1024*1024):.1f} MB boşaltıldı")
        
        return deleted_count, freed_space


class LogMonitor:
    """Log dosyalarının durumunu izler ve uyarılar verir."""

    # Uyarı eşikleri
    WARN_SIZE_MB = 8  # Dosya bu boyuta yaklaştığında uyar (10 MB limit)
    WARN_TOTAL_MB = 80  # Toplam bu boyuta yaklaştığında uyar (100 MB limit)

    @staticmethod
    def check_log_health():
        """
        Log dosyaları sağlık kontrolü yapır ve sorunları uyarır.
        
        Returns:
            dict: health_status (OK, WARNING, CRITICAL), messages
        """
        status = "OK"
        messages = []
        
        # Bireysel dosya boyutu kontrolü
        for log_file in [
            os.path.join(LOG_DIR, "app.log"),
            os.path.join(LOG_DIR, "sync.log"),
            os.path.join(LOG_DIR, "errors.log")
        ]:
            if os.path.exists(log_file):
                size_mb = LogStatistics.get_log_size(log_file)
                if size_mb > LogMonitor.WARN_SIZE_MB:
                    status = "WARNING"
                    messages.append(
                        f"⚠️ {os.path.basename(log_file)} büyük: {size_mb:.1f} MB "
                        f"(Limit: {AppConfig.LOG_MAX_BYTES/(1024*1024):.0f} MB)"
                    )
        
        # Toplam boyut kontrolü
        total_mb = LogStatistics.get_total_log_size()
        if total_mb > LogMonitor.WARN_TOTAL_MB:
            status = "WARNING"
            messages.append(f"⚠️ Toplam log boyutu: {total_mb:.1f} MB")
        
        # Rotated dosya sayısı
        backup_logs = LogCleanup.get_backup_logs()
        if len(backup_logs) > (AppConfig.LOG_BACKUP_COUNT * 2):
            status = "WARNING"
            messages.append(f"⚠️ Çok sayıda rotated log: {len(backup_logs)} dosya")
        
        return {
            "status": status,
            "total_size_mb": round(total_mb, 2),
            "messages": messages
        }

    @staticmethod
    def log_health_status():
        """Sağlık durumunu logla."""
        health = LogMonitor.check_log_health()
        
        logger.info(f"📊 Log Health: {health['status']} | Total: {health['total_size_mb']:.1f} MB")
        
        for msg in health['messages']:
            if "CRITICAL" in health['status']:
                logger.error(msg)
            else:
                logger.warning(msg)


# ════════════════════════════════════════════════════════════════
# BAŞLANGIÇ KONTROLÜ
# ════════════════════════════════════════════════════════════════

def initialize_log_management():
    """
    Uygulama başlangıcında log yönetiminin başlatılması.
    
    - Eski logları temizle (7+ gün)
    - Disk kullanımını kontrol et
    - Sağlık durumunu logla
    """
    logger.info("=" * 70)
    logger.info("LOG MANAGEMENT İNİSİYALİZASYONU")
    logger.info("=" * 70)
    
    # 1. Eski logları temizle (7 günden eski)
    deleted, freed = LogCleanup.cleanup_old_logs(days=7)
    
    # 2. Disk alanını kontrol et ve temizle (100 MB limit)
    deleted_space, freed_space = LogCleanup.cleanup_by_space(max_size_mb=100)
    
    # 3. İstatistik göster
    stats = LogStatistics.get_log_stats()
    logger.info(f"\n📊 Log Dosyaları ({len(stats)} dosya):")
    for name, info in sorted(stats.items()):
        logger.info(
            f"  {name:30s} | {info['size_mb']:7.2f} MB | "
            f"{info['lines']:6d} lines | {info['last_modified']}"
        )
    
    # 4. Sağlık durumunu kontrol et
    LogMonitor.log_health_status()
    
    logger.info("=" * 70 + "\n")

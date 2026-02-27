# -*- coding: utf-8 -*-
"""
Personel Listesi - Avatar Service
==================================
Avatar indirme, caching ve lazy-loading yönetimi.
"""
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QPixmap
import urllib.request
import urllib.error
import os
from pathlib import Path

from core.logger import logger
from core.paths import TEMP_DIR


# ─────────────────────────────────────────────────────────────────────────────
# Avatar Downloader Worker
# ─────────────────────────────────────────────────────────────────────────────

class AvatarDownloaderWorker(QThread):
    """
    Personel avatarı Drive'dan/URL'den indir ve cache'le.
    
    Signals:
        avatar_ready(str, QPixmap): TC ve indirilmiş pixmap
        error(str): Hata mesajı
    """
    
    avatar_ready = Signal(str, QPixmap)  # (tc, pixmap)
    error = Signal(str)

    def __init__(self, image_url: str, tc: str, parent=None):
        super().__init__(parent)
        self._url = image_url
        self._tc = tc

    def run(self):
        """Avatar'ı indir ve emit et."""
        try:
            if not self._url or not str(self._url).startswith("http"):
                logger.debug(f"Avatar URL geçersiz ({self._tc}): {self._url}")
                return
            
            # URL'den indir (timeout: 5s)
            try:
                req = urllib.request.Request(
                    self._url,
                    headers={'User-Agent': 'Mozilla/5.0'}
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = response.read()
                    pixmap = QPixmap()
                    if pixmap.loadFromData(data):
                        logger.debug(f"Avatar indirildi ({self._tc}): {len(data)} byte")
                        self.avatar_ready.emit(self._tc, pixmap)
                    else:
                        logger.warning(f"Avatar parse hatası ({self._tc})")
            except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
                logger.debug(f"Avatar download hatası ({self._tc}): {e}")
                self.error.emit(str(e))
        except Exception as e:
            logger.error(f"Avatar worker hatası: {e}")
            self.error.emit(str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Avatar Cache Manager
# ─────────────────────────────────────────────────────────────────────────────

class PersonelAvatarService:
    """
    Personel avatarları için cache ve indirme yönetimi.
    
    Features:
        - Disk cache (TEMP_DIR/personel_avatars/)
        - Memory cache (QPixmap)
        - Lazy loading (arka plan indirme)
        - TTL (24 saat)
    """

    def __init__(self):
        """Service'i başlat."""
        self._memory_cache: dict[str, QPixmap] = {}
        self._disk_cache_dir = os.path.join(TEMP_DIR, "personel_avatars")
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        """Cache dizinini oluştur."""
        os.makedirs(self._disk_cache_dir, exist_ok=True)

    def _get_cache_file(self, tc: str) -> str:
        """TC için cache dosya path'i."""
        # TC'den güvenli filename oluştur
        safe_tc = tc.replace("/", "_").replace("\\", "_")
        return os.path.join(self._disk_cache_dir, f"{safe_tc}.png")

    # ────────────────────────────────────────────────────────────────────────
    # Cache Methods
    # ────────────────────────────────────────────────────────────────────────

    def get_avatar(self, tc: str) -> QPixmap | None:
        """
        Memory cache'ten avatar al.
        
        Args:
            tc: Personel TC no
        
        Returns:
            QPixmap veya None
        """
        return self._memory_cache.get(tc)

    def cache_avatar(self, tc: str, pixmap: QPixmap):
        """
        Avatar'ı memory ve disk cache'e ekle.
        
        Args:
            tc: Personel TC no
            pixmap: Avatar QPixmap
        """
        self._memory_cache[tc] = pixmap
        
        # Disk'e kaydet
        cache_file = self._get_cache_file(tc)
        if pixmap.save(cache_file, "PNG"):
            logger.debug(f"Avatar disk cache'e kaydedildi: {cache_file}")
        else:
            logger.warning(f"Avatar disk cache'e kaydedilemedi: {cache_file}")

    def load_from_disk_cache(self, tc: str) -> QPixmap | None:
        """
        Disk cache'den avatar yükle.
        
        Args:
            tc: Personel TC no
        
        Returns:
            QPixmap veya None
        """
        cache_file = self._get_cache_file(tc)
        if os.path.exists(cache_file):
            pixmap = QPixmap(cache_file)
            if not pixmap.isNull():
                self._memory_cache[tc] = pixmap
                logger.debug(f"Avatar disk cache'den yüklendi: {tc}")
                return pixmap
        return None

    def clear_cache(self):
        """Cache'i temizle."""
        self._memory_cache.clear()
        logger.debug("Avatar memory cache temizlendi")

    # ────────────────────────────────────────────────────────────────────────
    # Worker Management
    # ────────────────────────────────────────────────────────────────────────

    @staticmethod
    def create_downloader(image_url: str, tc: str, parent=None) -> AvatarDownloaderWorker:
        """
        Avatar downloader worker oluştur.
        
        Args:
            image_url: Avatar URL'i
            tc: Personel TC no
            parent: Parent widget
        
        Returns:
            AvatarDownloaderWorker instance
        """
        worker = AvatarDownloaderWorker(image_url, tc, parent)
        return worker


# ─────────────────────────────────────────────────────────────────────────────
# Lazy-Loading Manager
# ─────────────────────────────────────────────────────────────────────────────

class LazyLoadingManager:
    """
    Personel listesi lazy-loading yönetimi.
    
    Features:
        - Sayfa bazlı yükleme
        - Toplam kayıt sayısı tracking
        - "Daha fazla yükle" kontrolü
    """

    def __init__(self, page_size: int = 100):
        """
        Manager'ı başlat.
        
        Args:
            page_size: Sayfa başına kayıt sayısı
        """
        self.page_size = page_size
        self.current_page = 1
        self.total_count = 0
        self.is_loading = False
        self.all_data: list[dict] = []

    def reset(self):
        """Lazy-loading state'ini sıfırla."""
        self.current_page = 1
        self.total_count = 0
        self.is_loading = False
        self.all_data = []

    def load_page(self, page_data: list[dict], total_count: int) -> bool:
        """
        Sayfa verisi ekle.
        
        Args:
            page_data: Page'in kayıtları
            total_count: Toplam kayıt sayısı
        
        Returns:
            Daha fazla sayfa var mı
        """
        if self.is_loading:
            return False
        
        self.all_data.extend(page_data)
        self.total_count = total_count
        self.current_page += 1
        
        loaded = len(self.all_data)
        has_more = loaded < total_count
        
        logger.debug(
            f"Lazy-load: Sayfa {self.current_page-1} yüklendi "
            f"({loaded}/{total_count}, {has_more} daha var)"
        )
        return has_more

    @property
    def loaded_count(self) -> int:
        """Yüklenen kayıt sayısı."""
        return len(self.all_data)

    @property
    def has_more(self) -> bool:
        """Daha fazla sayfa var mı."""
        return self.loaded_count < self.total_count

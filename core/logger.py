import logging
import os
import json
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from core.paths import LOG_DIR
from core.config import AppConfig

# Log dosyaları
LOG_FILE = os.path.join(LOG_DIR, "app.log")
SYNC_LOG_FILE = os.path.join(LOG_DIR, "sync.log")
ERROR_LOG_FILE = os.path.join(LOG_DIR, "errors.log")
UI_LOG_FILE = os.path.join(LOG_DIR, "ui_log.log")

# Log dizinini oluştur
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)


class SyncLogFilter(logging.Filter):
    """Sadece sync ile ilgili logları filtrele"""
    def filter(self, record):
        return hasattr(record, 'sync_context') or 'sync' in record.getMessage().lower()


class ErrorLogFilter(logging.Filter):
    """Sadece ERROR ve üstü logları filtrele"""
    def filter(self, record):
        return record.levelno >= logging.ERROR


class UILogFilter(logging.Filter):
    """Sadece UI context ile işaretlenen logları filtrele"""
    def filter(self, record):
        return hasattr(record, "ui_context")


class StructuredFormatter(logging.Formatter):
    """
    Structured logging formatter
    Hata durumlarında ek bağlam bilgisi ekler
    """
    def format(self, record):
        # Standart format
        base = super().format(record)
        
        # Ek bağlam bilgisi varsa ekle
        if hasattr(record, 'sync_context'):
            ctx = record.sync_context
            extra = f" | Tablo: {ctx.get('table', 'N/A')}"
            if 'step' in ctx:
                extra += f" | Adım: {ctx['step']}"
            if 'count' in ctx:
                extra += f" | Kayıt: {ctx['count']}"
            base += extra

        # UI bağlam bilgisi varsa ekle
        if hasattr(record, "ui_context"):
            ctx = record.ui_context
            extra = f" | UI: {ctx.get('action', 'N/A')}"
            if "group" in ctx:
                extra += f" | Grup: {ctx['group']}"
            if "page" in ctx:
                extra += f" | Sayfa: {ctx['page']}"
            base += extra
        
        return base


# Ana log handler — RotatingFileHandler (boyut tabanlı rotasyon)
file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=AppConfig.LOG_MAX_BYTES,      # 10 MB
    backupCount=AppConfig.LOG_BACKUP_COUNT,  # 5 yedek
    encoding="utf-8"
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(StructuredFormatter(
    "%(asctime)s - %(levelname)s - %(message)s"
))

# Sync log handler — RotatingFileHandler
sync_handler = RotatingFileHandler(
    SYNC_LOG_FILE,
    maxBytes=AppConfig.LOG_MAX_BYTES,
    backupCount=AppConfig.LOG_BACKUP_COUNT,
    encoding="utf-8"
)
sync_handler.setLevel(logging.INFO)
sync_handler.addFilter(SyncLogFilter())
sync_handler.setFormatter(StructuredFormatter(
    "%(asctime)s - %(message)s"
))

# Error log handler — RotatingFileHandler
error_handler = RotatingFileHandler(
    ERROR_LOG_FILE,
    maxBytes=AppConfig.LOG_MAX_BYTES,
    backupCount=AppConfig.LOG_BACKUP_COUNT,
    encoding="utf-8"
)
error_handler.setLevel(logging.ERROR)
error_handler.addFilter(ErrorLogFilter())
error_handler.setFormatter(StructuredFormatter(
    "%(asctime)s - %(levelname)s - %(message)s"
))

# UI log handler — RotatingFileHandler
ui_handler = RotatingFileHandler(
    UI_LOG_FILE,
    maxBytes=AppConfig.LOG_MAX_BYTES,
    backupCount=AppConfig.LOG_BACKUP_COUNT,
    encoding="utf-8"
)
ui_handler.setLevel(logging.ERROR)
ui_handler.addFilter(UILogFilter())
ui_handler.setFormatter(StructuredFormatter(
    "%(asctime)s - %(levelname)s - %(message)s"
))

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s"
))

# Logger yapılandırması
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, sync_handler, error_handler, ui_handler, console_handler]
)

logger = logging.getLogger("ITF_APP")


# ════════════════════════════════════════════════
# YARDIMCI FONKSİYONLAR
# ════════════════════════════════════════════════

def log_sync_start(table_name):
    """Sync başlangıcını logla"""
    extra = {'sync_context': {'table': table_name, 'step': 'start'}}
    logger.info(f"Sync başladı: {table_name}", extra=extra)


def log_sync_step(table_name, step, count=None):
    """Sync adımını logla"""
    ctx = {'table': table_name, 'step': step}
    if count is not None:
        ctx['count'] = count
    extra = {'sync_context': ctx}
    
    msg = f"{table_name} - {step}"
    if count is not None:
        msg += f" ({count} kayıt)"
    
    logger.info(msg, extra=extra)


def log_sync_error(table_name, step, error):
    """Sync hatasını detaylı logla"""
    ctx = {'table': table_name, 'step': step}
    extra = {'sync_context': ctx}
    
    error_type = type(error).__name__
    error_msg = str(error)
    
    logger.error(
        f"{table_name} sync hatası | {step} | {error_type}: {error_msg}",
        extra=extra,
        exc_info=True
    )


def log_sync_complete(table_name, stats=None):
    """Sync tamamlanmasını logla"""
    ctx = {'table': table_name, 'step': 'complete'}
    if stats:
        ctx.update(stats)
    extra = {'sync_context': ctx}
    
    msg = f"Sync tamamlandı: {table_name}"
    if stats:
        msg += f" | Push: {stats.get('pushed', 0)}, Pull: {stats.get('pulled', 0)}"
    
    logger.info(msg, extra=extra)


def log_ui_error(action, error, group=None, page=None):
    """UI akışında yakalanan hataları ui_log.log dosyasına yazar."""
    ctx = {"action": action}
    if group is not None:
        ctx["group"] = group
    if page is not None:
        ctx["page"] = page
    extra = {"ui_context": ctx}
    logger.error(f"UI hata: {type(error).__name__}: {error}", extra=extra, exc_info=True)


def get_user_friendly_error(error, table_name=None):
    """
    Kullanıcı dostu hata mesajı oluştur
    
    Returns:
        tuple: (kısa_mesaj, detaylı_mesaj)
    """
    error_type = type(error).__name__
    error_msg = str(error)
    
    # Bilinen hata tiplerini kullanıcı dostu hale getir
    if "ConnectionError" in error_type or "Timeout" in error_type:
        short = "Bağlantı hatası"
        detail = "İnternet bağlantınızı kontrol edin"
    
    elif "PermissionError" in error_type or "Forbidden" in error_type:
        short = "Yetki hatası"
        detail = "Google Sheets erişim yetkinizi kontrol edin"
    
    elif "QuotaExceeded" in error_type or "RateLimitExceeded" in error_type:
        short = "API limit aşıldı"
        detail = "Lütfen birkaç dakika bekleyin ve tekrar deneyin"
    
    elif "KeyError" in error_type or "IndexError" in error_type:
        short = "Veri yapısı hatası"
        detail = f"Tablo yapısında uyumsuzluk: {error_msg}"
    
    elif "ValueError" in error_type or "TypeError" in error_type:
        short = "Veri formatı hatası"
        detail = f"Geçersiz veri: {error_msg}"
    
    else:
        short = f"Sync hatası ({error_type})"
        detail = error_msg[:100]  # İlk 100 karakter
    
    if table_name:
        short = f"{table_name}: {short}"
    
    return short, detail


import os

# Tema okuma/yazma için settings.py kullanan yardımcı
try:
    from core import settings as _app_settings
except ImportError:
    _app_settings = None

from core.paths import BASE_DIR


class AppConfig:
    APP_NAME = "Radyoloji Envanter ve Personel Yönetim Sistemi"
    VERSION = "3.0.0"

    AUTO_SYNC = True
    SYNC_INTERVAL_MIN = 15

    # Uygulama çalışma modu
    MODE_ONLINE = "online"
    MODE_OFFLINE = "offline"
    DEFAULT_MODE = MODE_OFFLINE

    SETTINGS_PATH = os.path.join(BASE_DIR, "ayarlar.json")
    CREDENTIALS_PATH = os.path.join(BASE_DIR, "database", "credentials.json")

    # Log rotasyon
    LOG_MAX_BYTES = 10485760  # 10 MB
    LOG_BACKUP_COUNT = 5
    LOG_ROTATION_WHEN = "midnight"
    LOG_ROTATION_INTERVAL = 1

    APP_MODE = DEFAULT_MODE
    APP_MODE_SOURCE = "default"

    @classmethod
    def _normalize_mode(cls, value):
        mode = str(value or "").strip().lower()
        if mode in (cls.MODE_ONLINE, cls.MODE_OFFLINE):
            return mode
        return None

    @classmethod
    def resolve_app_mode(cls):
        """
        Çalışma modunu şu öncelik sırasıyla belirler:
        1) APP_MODE environment variable
        2) ayarlar.json içindeki app_mode alanı  (settings.get ile)
        3) credentials.json yoksa offline fallback
        4) varsayılan offline
        """
        env_mode = cls._normalize_mode(os.getenv("APP_MODE"))
        if env_mode:
            cls.APP_MODE = env_mode
            cls.APP_MODE_SOURCE = "env"
            return cls.APP_MODE

        try:
            file_mode = cls._normalize_mode(_app_settings.get("app_mode"))
            if file_mode:
                cls.APP_MODE = file_mode
                cls.APP_MODE_SOURCE = "settings"
                return cls.APP_MODE
        except Exception:
            pass

        if not os.path.exists(cls.CREDENTIALS_PATH):
            cls.APP_MODE = cls.MODE_OFFLINE
            cls.APP_MODE_SOURCE = "credentials_missing"
            return cls.APP_MODE

        cls.APP_MODE = cls.DEFAULT_MODE
        cls.APP_MODE_SOURCE = "default"
        return cls.APP_MODE

    @classmethod
    def get_app_mode(cls):
        return cls.resolve_app_mode()

    @classmethod
    def is_online_mode(cls):
        return cls.get_app_mode() == cls.MODE_ONLINE

    @classmethod
    def set_app_mode(cls, mode, persist=False):
        normalized = cls._normalize_mode(mode)
        if not normalized:
            raise ValueError("app_mode must be 'online' or 'offline'")

        cls.APP_MODE = normalized
        cls.APP_MODE_SOURCE = "runtime"

        if persist and _app_settings:
            _app_settings.set("app_mode", normalized)

        return cls.APP_MODE

    @classmethod
    def set_auto_sync(cls, enabled: bool, persist=False):
        """Otomatik senkronizasyonu etkinleştir/devre dışı bırak."""
        cls.AUTO_SYNC = enabled
        if persist and _app_settings:
            _app_settings.set("auto_sync", enabled)
        return cls.AUTO_SYNC

    @classmethod
    def get_auto_sync(cls) -> bool:
        """Kaydedilmiş auto_sync değerini oku."""
        if _app_settings:
            return bool(_app_settings.get("auto_sync", cls.AUTO_SYNC))
        return cls.AUTO_SYNC


# Import anında modu çözümle (env/settings/credentials)
AppConfig.resolve_app_mode()

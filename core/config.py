import json
import os

from core.paths import BASE_DIR


class AppConfig:
    APP_NAME = "Radyoloji Envanter ve Personel Yönetim Sistemi"
    VERSION = "1.0.8"

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
        1) ITF_APP_MODE environment variable
        2) ayarlar.json içindeki app_mode alanı
        3) credentials.json yoksa offline fallback
        4) varsayılan online
        """
        env_mode = cls._normalize_mode(os.getenv("ITF_APP_MODE"))
        if env_mode:
            cls.APP_MODE = env_mode
            cls.APP_MODE_SOURCE = "env"
            return cls.APP_MODE

        try:
            if os.path.exists(cls.SETTINGS_PATH):
                with open(cls.SETTINGS_PATH, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                file_mode = cls._normalize_mode(settings.get("app_mode"))
                if file_mode:
                    cls.APP_MODE = file_mode
                    cls.APP_MODE_SOURCE = "settings"
                    return cls.APP_MODE
        except Exception:
            # Settings parse/read hatası modu bozmasın
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

        if persist:
            settings = {}
            if os.path.exists(cls.SETTINGS_PATH):
                try:
                    with open(cls.SETTINGS_PATH, "r", encoding="utf-8") as f:
                        settings = json.load(f)
                except Exception:
                    settings = {}
            settings["app_mode"] = normalized
            with open(cls.SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)

        return cls.APP_MODE


# Import anında modu çözümle (env/settings/credentials)
AppConfig.resolve_app_mode()

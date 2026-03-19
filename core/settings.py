# core/settings.py  ─  REPYS v3 · Merkezi Ayar Yöneticisi
# ═══════════════════════════════════════════════════════════════
#
#  ayarlar.json üzerinde tek bir get/set arayüzü.
#  AppConfig.SETTINGS_PATH ile aynı dosyayı kullanır —
#  her ikisi de tutarlı kalır.
#
#  Kullanım:
#     from core.settings import get, set as save

#     tema = get("theme", "dark")     → "dark" | "light"
#     save("theme", "light")          → True | False
#
# ═══════════════════════════════════════════════════════════════

import json
from pathlib import Path

from core.paths import BASE_DIR

_PATH = Path(BASE_DIR) / "ayarlar.json"


def _load() -> dict:
    """ayarlar.json'ı oku. Hata durumunda boş dict."""
    try:
        if _PATH.exists():
            return json.loads(_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save(data: dict) -> bool:
    """Veriyi ayarlar.json'a yaz. Başarılıysa True."""
    try:
        _PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True
    except Exception as e:
        try:
            from core.logger import logger
            logger.warning(f"[settings] Kayıt hatası: {e}")
        except Exception:
            pass
        return False


def get(key: str, default=None):
    """
    Ayar değerini oku.

    Örnekler:
        get("theme", "dark")       → "dark" veya kaydedilmiş değer
        get("app_mode", "offline") → "online" | "offline"
    """
    return _load().get(key, default)


def set(key: str, value) -> bool:
    """
    Ayar değerini kaydet.

    Mevcut dosyadaki diğer anahtarlar korunur.
    Döndürür: True (başarılı) | False (hata)
    """
    data = _load()
    data[key] = value
    return _save(data)


def get_all() -> dict:
    """Tüm ayarları dict olarak döndür (salt okunur kopya)."""
    return dict(_load())

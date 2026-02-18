from database.repository_registry import RepositoryRegistry
from database.cloud_adapter import get_cloud_adapter as _get_cloud_adapter
from database.repository_registry import RepositoryRegistry


_fallback_registry_cache = {}


def get_registry(db):
    """
    Return a shared RepositoryRegistry instance for the given db object.
    """
    if db is None:
        raise ValueError("db cannot be None")

    registry = getattr(db, "_repository_registry", None)
    if registry is not None:
        return registry

    registry = _fallback_registry_cache.get(id(db))
    if registry is not None:
        return registry

    registry = RepositoryRegistry(db)
    try:
        setattr(db, "_repository_registry", registry)
    except Exception:
        _fallback_registry_cache[id(db)] = registry

    return registry


def get_cloud_adapter(mode=None):
    """
    Uygulama çalışma moduna göre cloud adapter döndürür.
    """
    return _get_cloud_adapter(mode=mode)

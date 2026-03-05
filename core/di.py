from database.repository_registry import RepositoryRegistry
from database.cloud_adapter import get_cloud_adapter as _get_cloud_adapter

from core.auth.auth_service import AuthService
from core.auth.authorization_service import AuthorizationService
from core.auth.password_hasher import PasswordHasher
from core.auth.session_context import SessionContext

# ── Service factory'leri ────────────────────────────────────────
# Her çağrıda registry üzerinden taze servis döner.
# UI'da:
#   from core.di import get_cihaz_service
#   svc = get_cihaz_service(self._db)
# ────────────────────────────────────────────────────────────────

def get_cihaz_service(db):
    from core.services.cihaz_service import CihazService
    return CihazService(get_registry(db))

def get_rke_service(db):
    from core.services.rke_service import RkeService
    return RkeService(get_registry(db))

def get_saglik_service(db):
    from core.services.saglik_service import SaglikService
    return SaglikService(get_registry(db))

def get_fhsz_service(db):
    from core.services.fhsz_service import FhszService
    return FhszService(get_registry(db))

def get_personel_service(db):
    from core.services.personel_service import PersonelService
    return PersonelService(get_registry(db))

def get_dashboard_service(db):
    from core.services.dashboard_service import DashboardService
    return DashboardService(get_registry(db))

def get_izin_service(db):
    from core.services.izin_service import IzinService
    return IzinService(get_registry(db))

def get_ariza_service(db):
    from core.services.ariza_service import ArizaService
    return ArizaService(get_registry(db))

def get_bakim_service(db):
    from core.services.bakim_service import BakimService
    return BakimService(get_registry(db))

def get_kalibrasyon_service(db):
    from core.services.kalibrasyon_service import KalibrasyonService
    return KalibrasyonService(get_registry(db))

def get_dokuman_service(db):
    from core.services.dokuman_service import DokumanService
    return DokumanService(get_registry(db))

def get_backup_service(db):
    from core.services.backup_service import BackupService
    return BackupService()

def get_log_service(db):
    from core.services.log_service import LogService
    return LogService()

def get_settings_service(db):
    from core.services.settings_service import SettingsService
    return SettingsService()

def get_file_sync_service(db):
    from core.services.file_sync_service import FileSyncService
    return FileSyncService(db, get_registry(db))


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
    Uygulama calisma moduna gore cloud adapter dondurur.
    """
    return _get_cloud_adapter(mode=mode)


def get_auth_services(db):
    """
    Auth servislerini ortak sekilde kurar.
    """
    session_context = SessionContext()
    hasher = PasswordHasher()
    auth_service = AuthService(db=db, hasher=hasher, session=session_context)
    authorization_service = AuthorizationService(db)
    return auth_service, authorization_service, session_context

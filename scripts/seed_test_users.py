import sys
import os

# Proje kök dizinini Python path'e ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.auth.password_hasher import PasswordHasher

from core.auth.permission_keys import PermissionKeys
from core.logger import logger
from database.sqlite_manager import SQLiteManager
from database.auth_repository import AuthRepository
from database.permission_repository import PermissionRepository


def _get_or_create_role_id(db, perm_repo: PermissionRepository, name: str) -> int:
    cur = db.conn.cursor()
    cur.execute("SELECT RoleId FROM Roles WHERE RoleName = ?", (name,))
    row = cur.fetchone()
    if row:
        return row["RoleId"]
    return perm_repo.create_role(name=name)


def _get_or_create_permission_id(db, perm_repo: PermissionRepository, key: str) -> int:
    cur = db.conn.cursor()
    cur.execute("SELECT PermissionId FROM Permissions WHERE PermissionKey = ?", (key,))
    row = cur.fetchone()
    if row:
        return row["PermissionId"]
    return perm_repo.create_permission(key=key, description="")


def _assign_permissions_if_missing(
    db,
    perm_repo: PermissionRepository,
    role_id: int,
    permission_keys: list[str],
) -> None:
    mevcut_ids = set(perm_repo.get_role_permissions(role_id))
    for perm_key in permission_keys:
        perm_id = _get_or_create_permission_id(db, perm_repo, perm_key)
        if perm_id in mevcut_ids:
            continue
        perm_repo.assign_permission_to_role(role_id=role_id, permission_id=perm_id)
        mevcut_ids.add(perm_id)


def seed_initial_admin_user(db) -> int:
    """İlk kurulum için admin kullanıcısını ve admin rol atamasını garanti eder."""
    auth_repo = AuthRepository(db)
    perm_repo = PermissionRepository(db)
    hasher = PasswordHasher()

    admin_user = auth_repo.get_user_by_username("admin")
    if not admin_user:
        password_hash = hasher.hash("admin123")
        admin_user_id = auth_repo.create_user(
            username="admin",
            password_hash=password_hash,
            is_active=True,
        )
        logger.info("İlk kurulum admin kullanıcısı oluşturuldu: admin / admin123")
    else:
        admin_user_id = admin_user.id
        logger.info("İlk kurulum admin kullanıcısı zaten mevcut")

    admin_role_id = _get_or_create_role_id(db, perm_repo, "admin")

    _assign_permissions_if_missing(db, perm_repo, admin_role_id, PermissionKeys.all())

    try:
        auth_repo.assign_role(user_id=admin_user_id, role_id=admin_role_id)
    except Exception:
        pass

    return admin_user_id


def seed_test_users(db):
    """
    Test kullanıcıları oluştur:
    1. admin / admin123 - tüm yetkiler
    2. viewer / viewer123 - sadece okuma yetkileri
    """
    auth_repo = AuthRepository(db)
    perm_repo = PermissionRepository(db)
    hasher = PasswordHasher()

    # === ADMIN KULLANICISI ===
    admin_user_id = seed_initial_admin_user(db)

    # === VIEWER KULLANICISI (SADECE OKUMA) ===
    viewer_user = auth_repo.get_user_by_username("viewer")
    if not viewer_user:
        password_hash = hasher.hash("viewer123")
        viewer_user_id = auth_repo.create_user(
            username="viewer",
            password_hash=password_hash,
            is_active=True
        )
        logger.info("Viewer kullanıcısı oluşturuldu: viewer / viewer123")
    else:
        viewer_user_id = viewer_user.id
        logger.info("Viewer kullanıcısı zaten mevcut")

    # Viewer rolü
    viewer_role_id = _get_or_create_role_id(db, perm_repo, "viewer")
    
    # Viewer rolüne sadece okuma yetkilerini ata
    read_permissions = [
        PermissionKeys.PERSONEL_READ,
        PermissionKeys.CIHAZ_READ,
    ]
    
    _assign_permissions_if_missing(db, perm_repo, viewer_role_id, read_permissions)
    
    # Kullanıcıya rolü ata
    try:
        auth_repo.assign_role(user_id=viewer_user_id, role_id=viewer_role_id)
    except Exception:
        pass  # Already assigned

    logger.info("Test kullanıcıları hazır!")
    print("\n" + "="*60)
    print("TEST KULLANICILARI")
    print("="*60)
    print("1. Admin (Tüm Yetkiler):")
    print("   Kullanıcı Adı: admin")
    print("   Şifre: admin123")
    print()
    print("2. Viewer (Sadece Okuma Yetkileri):")
    print("   Kullanıcı Adı: viewer")
    print("   Şifre: viewer123")
    print("   - Personel Listesi (görünür)")
    print("   - Cihaz Listesi (görünür)")
    print("   - Personel/Cihaz Ekle (gizli)")
    print("   - Admin İşlemleri (gizli)")
    print("="*60)


def main() -> None:
    db = SQLiteManager()
    try:
        seed_test_users(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()

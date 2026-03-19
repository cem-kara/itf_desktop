import sys
import os

# Proje kök dizinini Python path'e ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from getpass import getpass

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


def _seed_admin_user(db, username: str, password: str) -> None:
    auth_repo = AuthRepository(db)
    perm_repo = PermissionRepository(db)
    existing = auth_repo.get_user_by_username(username)
    if existing:
        logger.info("Admin user already exists: %s", username)
        return

    hasher = PasswordHasher()
    password_hash = hasher.hash(password)
    user_id = auth_repo.create_user(username=username, password_hash=password_hash, is_active=True)

    admin_role_id = _get_or_create_role_id(db, perm_repo, "admin")
    auth_repo.assign_role(user_id=user_id, role_id=admin_role_id)

    for key in PermissionKeys.all():
        perm_id = _get_or_create_permission_id(db, perm_repo, key)
        perm_repo.assign_permission_to_role(role_id=admin_role_id, permission_id=perm_id)

    logger.info("Admin user created: %s", username)


def main() -> None:
    db = SQLiteManager()
    try:
        username = input("Admin username [admin]: ").strip() or "admin"
        password = getpass("Admin password: ").strip()
        if not password:
            print("Password is required.")
            return
        _seed_admin_user(db, username, password)
    finally:
        db.close()


if __name__ == "__main__":
    main()

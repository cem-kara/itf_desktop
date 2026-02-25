import sqlite3
from dataclasses import dataclass
from datetime import datetime
from core.paths import DB_PATH
from core.logger import logger


@dataclass(frozen=True)
class DbUser:
    id: int
    username: str
    password_hash: str
    is_active: bool


class SQLiteManager:
    def __init__(self, db_path=None, check_same_thread=True):
        self.db_path = db_path or DB_PATH
        logger.info("SQLite bağlantısı açılıyor")
        self.conn = sqlite3.connect(self.db_path, check_same_thread=check_same_thread, timeout=30)
        # WAL mode enable et (concurrent write access için)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.row_factory = sqlite3.Row

    def execute(self, query, params=()):
        cur = self.conn.cursor()
        cur.execute(query, params)
        self.conn.commit()
        return cur

    def executemany(self, query, params_list):
        cur = self.conn.cursor()
        cur.executemany(query, params_list)
        self.conn.commit()

    # ── Auth/RBAC helpers ──────────────────────────────────────────

    def get_user_by_username(self, username: str):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT UserId, Username, PasswordHash, IsActive FROM Users WHERE Username = ?",
            (username,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return DbUser(
            id=row["UserId"],
            username=row["Username"],
            password_hash=row["PasswordHash"],
            is_active=bool(row["IsActive"]),
        )

    def get_permissions_for_user(self, user_id: int):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT p.PermissionKey
            FROM Permissions p
            JOIN RolePermissions rp ON rp.PermissionId = p.PermissionId
            JOIN UserRoles ur ON ur.RoleId = rp.RoleId
            WHERE ur.UserId = ?
        """, (user_id,))
        return [r["PermissionKey"] for r in cur.fetchall()]

    def create_user(self, username: str, password_hash: str, is_active: bool = True) -> int:
        cur = self.execute(
            "INSERT INTO Users (Username, PasswordHash, IsActive, CreatedAt) VALUES (?, ?, ?, ?)",
            (username, password_hash, 1 if is_active else 0, datetime.now().isoformat())
        )
        return cur.lastrowid

    def create_role(self, name: str) -> int:
        cur = self.execute(
            "INSERT INTO Roles (RoleName) VALUES (?)",
            (name,)
        )
        return cur.lastrowid

    def create_permission(self, key: str, description: str = "") -> int:
        cur = self.execute(
            "INSERT INTO Permissions (PermissionKey, Description) VALUES (?, ?)",
            (key, description)
        )
        return cur.lastrowid

    def assign_role(self, user_id: int, role_id: int) -> None:
        self.execute(
            "INSERT OR IGNORE INTO UserRoles (UserId, RoleId) VALUES (?, ?)",
            (user_id, role_id)
        )

    def assign_permission_to_role(self, role_id: int, permission_id: int) -> None:
        self.execute(
            "INSERT OR IGNORE INTO RolePermissions (RoleId, PermissionId) VALUES (?, ?)",
            (role_id, permission_id)
        )

    def record_auth_audit(self, username: str, success: bool, reason: str = "") -> None:
        self.execute(
            "INSERT INTO AuthAudit (Username, Success, Reason, CreatedAt) VALUES (?, ?, ?, ?)",
            (username, 1 if success else 0, reason, datetime.now().isoformat())
        )

    def close(self):
        logger.info("SQLite bağlantısı kapatılıyor")
        self.conn.close()

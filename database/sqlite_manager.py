import sqlite3
import time
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
    must_change_password: bool


class SQLiteManager:
    def __init__(self, db_path=None, check_same_thread=True):
        self.db_path = db_path or DB_PATH
        logger.info("SQLite baglantisi aciliyor")
        self.conn = sqlite3.connect(self.db_path, check_same_thread=check_same_thread, timeout=30)
        # WAL mode enable et (concurrent write access icin)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.row_factory = sqlite3.Row

    def execute(self, query, params=()) -> sqlite3.Cursor:
        for attempt in range(5):
            try:
                cur = self.conn.cursor()
                cur.execute(query, params)
                self.conn.commit()
                return cur
            except sqlite3.OperationalError as exc:
                if "database is locked" in str(exc).lower() and attempt < 4:
                    time.sleep(0.1 * (attempt + 1))
                    continue
                raise
        # Tüm denemeler tükendiyse (teorik olarak ulaşılmaz)
        raise sqlite3.OperationalError("Database execution failed after 5 attempts")

    def executemany(self, query, params_list):
        cur = self.conn.cursor()
        cur.executemany(query, params_list)
        self.conn.commit()

    # -- Auth/RBAC helpers -------------------------------------------------

    def get_user_by_username(self, username: str):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT UserId, Username, PasswordHash, IsActive, MustChangePassword FROM Users WHERE Username = ?",
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
            must_change_password=bool(row["MustChangePassword"]),
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

    def create_user(
        self,
        username: str,
        password_hash: str,
        is_active: bool = True,
        must_change_password: bool = False,
    ) -> int:
        cur = self.execute(
            """
            INSERT INTO Users (Username, PasswordHash, IsActive, MustChangePassword, CreatedAt)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                username,
                password_hash,
                1 if is_active else 0,
                1 if must_change_password else 0,
                datetime.now().isoformat(),
            )
        )
        return cur.lastrowid or 0

    def create_role(self, name: str) -> int:
        cur = self.execute(
            "INSERT INTO Roles (RoleName) VALUES (?)",
            (name,)
        )
        return cur.lastrowid or 0

    def create_permission(self, key: str, description: str = "") -> int:
        cur = self.execute(
            "INSERT INTO Permissions (PermissionKey, Description) VALUES (?, ?)",
            (key, description)
        )
        return cur.lastrowid or 0

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

    def get_roles_with_permission_count(self):
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT r.RoleId, r.RoleName,
                   COUNT(rp.PermissionId) as PermCount
            FROM Roles r
            LEFT JOIN RolePermissions rp ON rp.RoleId = r.RoleId
            GROUP BY r.RoleId, r.RoleName
            ORDER BY r.RoleName
            """
        )
        return [
            {
                "id": row["RoleId"],
                "name": row["RoleName"],
                "perm_count": row["PermCount"],
            }
            for row in cur.fetchall()
        ]

    def update_role(self, role_id: int, name: str) -> None:
        self.execute(
            "UPDATE Roles SET RoleName = ? WHERE RoleId = ?",
            (name, role_id)
        )

    def get_role_user_count(self, role_id: int) -> int:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT COUNT(*) AS Cnt FROM UserRoles WHERE RoleId = ?",
            (role_id,)
        )
        row = cur.fetchone()
        return int(row["Cnt"]) if row else 0

    def delete_role(self, role_id: int) -> None:
        self.execute("DELETE FROM RolePermissions WHERE RoleId = ?", (role_id,))
        self.execute("DELETE FROM UserRoles WHERE RoleId = ?", (role_id,))
        self.execute("DELETE FROM Roles WHERE RoleId = ?", (role_id,))

    def get_permissions(self):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT PermissionId, PermissionKey, Description FROM Permissions ORDER BY PermissionKey"
        )
        return [
            {
                "id": row["PermissionId"],
                "key": row["PermissionKey"],
                "description": row["Description"],
            }
            for row in cur.fetchall()
        ]

    def get_role_permissions(self, role_id: int) -> set[int]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT PermissionId FROM RolePermissions WHERE RoleId = ?",
            (role_id,)
        )
        return {int(row["PermissionId"]) for row in cur.fetchall()}

    def set_role_permissions(self, role_id: int, permission_ids: list[int]) -> None:
        self.execute("DELETE FROM RolePermissions WHERE RoleId = ?", (role_id,))
        if permission_ids:
            self.executemany(
                "INSERT INTO RolePermissions (RoleId, PermissionId) VALUES (?, ?)",
                [(role_id, perm_id) for perm_id in permission_ids]
            )

    def record_auth_audit(self, username: str, success: bool, reason: str = "") -> None:
        self.execute(
            "INSERT INTO AuthAudit (Username, Success, Reason, CreatedAt) VALUES (?, ?, ?, ?)",
            (username, 1 if success else 0, reason, datetime.now().isoformat())
        )

    def get_recent_auth_failures(self, username: str, window_minutes: int) -> int:
        """Son N dakika icindeki basarisiz giris sayisini dondurur."""
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*) AS FailCount
            FROM AuthAudit
            WHERE Username = ?
              AND Success = 0
              AND datetime(CreatedAt) >= datetime('now', ?)
            """,
            (username, f"-{window_minutes} minutes")
        )
        row = cur.fetchone()
        return int(row["FailCount"]) if row else 0

    def get_auth_audit_logs(
        self,
        limit: int = 200,
        username_filter: str | None = None,
        success_filter: int | None = None,
    ):
        """AuthAudit kayitlarini getir (filtre ve limit destekli)."""
        query = (
            "SELECT Username, Success, Reason, CreatedAt "
            "FROM AuthAudit WHERE 1=1"
        )
        params: list[object] = []

        if username_filter:
            query += " AND Username LIKE ?"
            params.append(f"%{username_filter}%")

        if success_filter in (0, 1):
            query += " AND Success = ?"
            params.append(success_filter)

        query += " ORDER BY datetime(CreatedAt) DESC"

        if limit and limit > 0:
            query += " LIMIT ?"
            params.append(limit)

        cur = self.conn.cursor()
        cur.execute(query, tuple(params))
        return [
            {
                "username": row["Username"],
                "success": bool(row["Success"]),
                "reason": row["Reason"],
                "created_at": row["CreatedAt"],
            }
            for row in cur.fetchall()
        ]

    def prune_auth_audit(self, retention_days: int) -> int:
        """AuthAudit tablosunda belirtilen günden eski kayıtları siler."""
        try:
            days = int(retention_days)
        except (TypeError, ValueError):
            days = 0

        if days <= 0:
            return 0

        cur = self.execute(
            """
            DELETE FROM AuthAudit
            WHERE datetime(CreatedAt) < datetime('now', ?)
            """,
            (f"-{days} days",),
        )
        return int(cur.rowcount or 0)

    def get_all_users(self):
        """Tüm kullanıcıları getir"""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT UserId, Username, PasswordHash, IsActive, MustChangePassword FROM Users ORDER BY Username"
        )
        return [
            DbUser(
                id=row["UserId"],
                username=row["Username"],
                password_hash=row["PasswordHash"],
                is_active=bool(row["IsActive"]),
                must_change_password=bool(row["MustChangePassword"]),
            )
            for row in cur.fetchall()
        ]

    def get_user_by_id(self, user_id: int):
        """ID'ye göre kullanıcı getir"""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT UserId, Username, PasswordHash, IsActive, MustChangePassword FROM Users WHERE UserId = ?",
            (user_id,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return DbUser(
            id=row["UserId"],
            username=row["Username"],
            password_hash=row["PasswordHash"],
            is_active=bool(row["IsActive"]),
            must_change_password=bool(row["MustChangePassword"]),
        )

    def get_user_roles(self, user_id: int):
        """Kullanıcının rollerini getir"""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT r.RoleId, r.RoleName
            FROM Roles r
            JOIN UserRoles ur ON ur.RoleId = r.RoleId
            WHERE ur.UserId = ?
        """, (user_id,))
        return [{"id": row["RoleId"], "name": row["RoleName"]} for row in cur.fetchall()]

    def get_roles(self):
        cur = self.conn.cursor()
        cur.execute("SELECT RoleId, RoleName FROM Roles ORDER BY RoleName")
        return [{"id": row["RoleId"], "name": row["RoleName"]} for row in cur.fetchall()]

    def set_user_roles(self, user_id: int, role_ids: list[int]) -> None:
        self.execute("DELETE FROM UserRoles WHERE UserId = ?", (user_id,))
        if role_ids:
            self.executemany(
                "INSERT INTO UserRoles (UserId, RoleId) VALUES (?, ?)",
                [(user_id, role_id) for role_id in role_ids]
            )

    def update_user_password(self, user_id: int, password_hash: str) -> None:
        """Kullanıcı şifresini güncelle"""
        self.execute(
            "UPDATE Users SET PasswordHash = ? WHERE UserId = ?",
            (password_hash, user_id)
        )

    def update_user_must_change_password(self, user_id: int, must_change: bool) -> None:
        """Kullanıcı ilk giris sifre degistirme durumunu guncelle"""
        self.execute(
            "UPDATE Users SET MustChangePassword = ? WHERE UserId = ?",
            (1 if must_change else 0, user_id)
        )

    def update_user_status(self, user_id: int, is_active: bool) -> None:
        """Kullanıcı aktiflik durumunu güncelle"""
        self.execute(
            "UPDATE Users SET IsActive = ? WHERE UserId = ?",
            (1 if is_active else 0, user_id)
        )

    def delete_user(self, user_id: int) -> None:
        """Kullanıcıyı sil (önce ilişkileri temizle)"""
        # Önce UserRoles'deki kayıtları sil
        self.execute("DELETE FROM UserRoles WHERE UserId = ?", (user_id,))
        # Sonra kullanıcıyı sil
        self.execute("DELETE FROM Users WHERE UserId = ?", (user_id,))

    def close(self):
        logger.info("SQLite baglantisi kapatiliyor")
        self.conn.close()

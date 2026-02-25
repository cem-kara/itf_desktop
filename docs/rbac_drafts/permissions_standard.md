# Yetki Standarti ve Semalar (Taslak)

Tarih: 2026-02-25

## 1) Yetki Anahtar Standarti
- Form: `<modul>.<aksiyon>`
- Ornekler:
  - personel.read
  - personel.write
  - cihaz.read
  - cihaz.write
  - admin.panel
  - admin.logs.view
  - admin.backup
  - admin.settings

## 2) Tablo Semasi (Ozet)
Users
- UserId (PK)
- Username (unique)
- PasswordHash
- IsActive
- CreatedAt
- LastLoginAt

Roles
- RoleId (PK)
- RoleName (unique)

Permissions
- PermissionId (PK)
- PermissionKey (unique)
- Description

UserRoles
- UserId (FK -> Users.UserId)
- RoleId (FK -> Roles.RoleId)
- PK (UserId, RoleId)

RolePermissions
- RoleId (FK -> Roles.RoleId)
- PermissionId (FK -> Permissions.PermissionId)
- PK (RoleId, PermissionId)

AuthAudit (opsiyonel)
- AuditId (PK)
- Username
- Success
- Reason
- CreatedAt

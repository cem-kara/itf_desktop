class PermissionKeys:
    # Page-level permissions
    PERSONEL_READ = "personel.read"
    PERSONEL_WRITE = "personel.write"
    CIHAZ_READ = "cihaz.read"
    CIHAZ_WRITE = "cihaz.write"
    ADMIN_PANEL = "admin.panel"

    # Action-level permissions
    ADMIN_CRITICAL = "admin.critical"

    @classmethod
    def all(cls) -> list[str]:
        return [
            cls.PERSONEL_READ,
            cls.PERSONEL_WRITE,
            cls.CIHAZ_READ,
            cls.CIHAZ_WRITE,
            cls.ADMIN_PANEL,
            cls.ADMIN_CRITICAL,
        ]

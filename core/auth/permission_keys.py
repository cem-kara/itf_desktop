class PermissionKeys:

    # Page-level permissions (legacy)
    PERSONEL_READ = "personel.read"
    PERSONEL_WRITE = "personel.write"
    CIHAZ_READ = "cihaz.read"
    CIHAZ_WRITE = "cihaz.write"
    ADMIN_PANEL = "admin.panel"
    ADMIN_CRITICAL = "admin.critical"

    # Extended RBAC permissions
    DIS_ALAN_READ = "dis_alan.read"
    DIS_ALAN_WRITE = "dis_alan.write"
    RKE_READ = "rke.read"
    RKE_WRITE = "rke.write"
    SAGLIK_READ = "saglik.read"
    SAGLIK_WRITE = "saglik.write"
    DOZIMETRE_READ = "dozimetre.read"
    DOZIMETRE_WRITE = "dozimetre.write"
    FHSZ_READ = "fhsz.read"
    FHSZ_WRITE = "fhsz.write"
    DOKUMAN_READ = "dokuman.read"
    DOKUMAN_WRITE = "dokuman.write"
    RAPOR_EXCEL = "rapor.excel"
    RAPOR_PDF = "rapor.pdf"
    BACKUP_CREATE = "backup.create"
    BACKUP_RESTORE = "backup.restore"
    NOBET_PLAN = "nobet.plan"
    NOBET_OZET = "nobet.ozet"
    NOBET_RAPOR = "nobet.rapor"
    NOBET_WRITE = "nobet.write"

    @classmethod
    def all(cls) -> list[str]:
        return [
            cls.PERSONEL_READ,
            cls.PERSONEL_WRITE,
            cls.CIHAZ_READ,
            cls.CIHAZ_WRITE,
            cls.ADMIN_PANEL,
            cls.ADMIN_CRITICAL,
            cls.DIS_ALAN_READ,
            cls.DIS_ALAN_WRITE,
            cls.RKE_READ,
            cls.RKE_WRITE,
            cls.SAGLIK_READ,
            cls.SAGLIK_WRITE,
            cls.DOZIMETRE_READ,
            cls.DOZIMETRE_WRITE,
            cls.FHSZ_READ,
            cls.FHSZ_WRITE,
            cls.DOKUMAN_READ,
            cls.DOKUMAN_WRITE,
            cls.RAPOR_EXCEL,
            cls.RAPOR_PDF,
            cls.BACKUP_CREATE,
            cls.BACKUP_RESTORE,
            cls.NOBET_PLAN,
            cls.NOBET_OZET,
            cls.NOBET_RAPOR,
            cls.NOBET_WRITE,
        ]

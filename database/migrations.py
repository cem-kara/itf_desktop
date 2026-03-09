# database/migrations.py
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
from core.logger import logger


class MigrationManager:
    """
    Versiyon tabanlı migration yöneticisi.

    Özellikler:
    - Otomatik Şema versiyonlama
    - Güvenli migration adımları
    - Otomatik yedekleme
    - Rollback desteği
    - Veri kaybı olmadan Şema güncellemeleri

    Squash Geçmişi:
    - v1:v18 arası tüm migration'lar tek temiz kurulum adımına squash edildi.
    - Sıfırdan kurulumda v1 tüm tabloları doğrudan son şemalarıyla oluşturur.
    - Mevcut (eski) veritabanları: current_version >= CURRENT_VERSION ise
      güncel sayılır, hiçbir migration çalışmaz.

    Yeni migration eklerken:
    - CURRENT_VERSION değerini 1 artır (örn. 2)
    - _migrate_to_v2() metodunu yaz
    - create_tables() içindeki ilgili CREATE TABLE'ı da güncelle
    """

    # Mevcut Şema versiyonu
    CURRENT_VERSION = 2

    def __init__(self, db_path):
        self.db_path = db_path
        self.backup_dir = Path(db_path).parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)

    # ================================================
    # BAĞLANTI & VERSİYON
    # ================================================

    def connect(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def get_schema_version(self):
        """Mevcut Şema versiyonunu döndürür."""
        conn = self.connect()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='schema_version'
            """)

            if not cur.fetchone():
                cur.execute("""
                    CREATE TABLE schema_version (
                        version     INTEGER PRIMARY KEY,
                        applied_at  TEXT NOT NULL,
                        description TEXT
                    )
                """)
                conn.commit()
                return 0

            cur.execute("SELECT MAX(version) FROM schema_version")
            result = cur.fetchone()
            return result[0] if result[0] is not None else 0

        finally:
            conn.close()

    def set_schema_version(self, version, description=""):
        """Şema versiyonunu günceller."""
        conn = self.connect()
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO schema_version (version, applied_at, description)
                VALUES (?, ?, ?)
            """, (version, datetime.now().isoformat(), description))
            conn.commit()
            logger.info(f"Şema versiyonu {version} olarak güncellendi: {description}")

        finally:
            conn.close()

    # ================================================
    # YEDEKLEME
    # ================================================

    def backup_database(self):
        """Veritabanını yedekler."""
        if not Path(self.db_path).exists():
            logger.info("Yedeklenecek veritabanı bulunamadı")
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"db_backup_{timestamp}.db"

        try:
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Veritabanı yedeklendi: {backup_path}")
            self._cleanup_old_backups()
            return backup_path

        except Exception as e:
            logger.error(f"Yedekleme hatası: {e}")
            return None

    def _cleanup_old_backups(self, keep_count=10):
        """Eski yedekleri temizler."""
        backups = sorted(self.backup_dir.glob("db_backup_*.db"))

        if len(backups) > keep_count:
            for old_backup in backups[:-keep_count]:
                try:
                    old_backup.unlink()
                    logger.info(f"Eski yedek silindi: {old_backup.name}")
                except Exception as e:
                    logger.warning(f"Yedek silinemedi {old_backup.name}: {e}")

    # ================================================
    # MİGRATION Ã‡ALIŞTIRICI
    # ================================================

    def run_migrations(self):
        """
        Tüm bekleyen migration'ları çalıŞtırır.
        Veri kaybı olmadan Şemayı günceller.
        """
        current_version = self.get_schema_version()

        if current_version == self.CURRENT_VERSION:
            logger.info(f"Şema güncel (v{current_version})")
            return True

        if current_version > self.CURRENT_VERSION:
            # Squash sonrası eski veritabanları daha yüksek versiyonda olabilir.
            # Bu durumu "güncel" kabul et — veri kaybı riski yok.
            logger.info(
                f"Şema versiyonu ({current_version}) > kod versiyonu ({self.CURRENT_VERSION}) "
                "— squash öncesi kurulum, güncel sayılıyor."
            )
            return True

        backup_path = self.backup_database()
        if not backup_path:
            logger.warning("Yedekleme yapılamadı ama migration devam ediyor")

        logger.info(f"Migration baŞlıyor: v{current_version} â†’ v{self.CURRENT_VERSION}")

        try:
            for version in range(current_version + 1, self.CURRENT_VERSION + 1):
                migration_method = getattr(self, f"_migrate_to_v{version}", None)

                if migration_method:
                    logger.info(f"Migration v{version} uygulanıyor...")
                    migration_method()
                else:
                    # Tanımlı metod yok â†’ no-op; yine de versiyona kayıt yapılır.
                    logger.info(f"Migration v{version} â€” no-op, atlanıyor")

                self.set_schema_version(version, f"Migrated to v{version}")

            logger.info("✓ Tüm migration'lar baŞarıyla tamamlandı")
            return True

        except Exception as e:
            logger.error(f"Migration hatası: {e}")
            logger.error(f"Yedekten geri yükleme yapabilirsiniz: {backup_path}")
            raise

    # ================================================
    # MIGRATION METODLARI
    # ================================================

    def _migrate_to_v1(self):
        """
        v0 -> v1: TEK VE TAMAMLANMIS KURULUM — tüm tabloları güncel
                  şemalarıyla oluşturur, başlangıç ve auth verilerini ekler.

        Squash: v1-v18 arası tüm migration\'lar bu tek adıma indirgendi (Mart 2026).
        Yeni migration gerekirse _migrate_to_v2() ekle, CURRENT_VERSION=2 yap.
        """
        conn = self.connect()
        cur = conn.cursor()

        try:
            self.create_tables(cur)
            self._seed_initial_data(cur)
            self._seed_auth_data(cur)
            conn.commit()
            logger.info("v1: Tüm tablolar oluŞturuldu ve baŞlangıç verileri eklendi")

        finally:
            conn.close()

    def _migrate_to_v2(self):
        """v1 -> v2: Add Dozimetre_Olcum table."""
        conn = self.connect()
        cur = conn.cursor()
        try:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS Dozimetre_Olcum (
                KayitNo            TEXT PRIMARY KEY,
                SiraNo             INTEGER,
                RaporNo            TEXT,
                Periyot            INTEGER,
                PeriyotAdi         TEXT,
                Yil                INTEGER,
                DozimetriTipi      TEXT,
                AdSoyad            TEXT,
                TCKimlikNo         TEXT,
                CalistiBirim       TEXT,
                PersonelID         TEXT,
                DozimetreNo        TEXT,
                VucutBolgesi       TEXT,
                Hp10               REAL,
                Hp007              REAL,
                DozSiniri_Hp10     REAL,
                DozSiniri_Hp007    REAL,
                Durum              TEXT,
                OlusturmaTarihi    TEXT DEFAULT (date('now')),

                sync_status        TEXT DEFAULT 'clean',
                updated_at         TEXT
            )
            """)
            conn.commit()
            logger.info("v2: Dozimetre_Olcum tablosu eklendi")
        finally:
            conn.close()

    # ================================================
    # TABLO OLUŞTURMA (İLK KURULUM / RESET)
    # ================================================

    def create_tables(self, cur):
        """
        Tüm tabloları v14 (güncel) Şemasıyla oluŞturur.
        Yalnızca _migrate_to_v1 ve reset_database tarafından çağrılır.
        """

        # == PERSONEL ==========================================================
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Personel (
            KimlikNo                    TEXT PRIMARY KEY,
            AdSoyad                     TEXT,
            DogumYeri                   TEXT,
            DogumTarihi                 TEXT,
            HizmetSinifi                TEXT,
            KadroUnvani                 TEXT,
            GorevYeri                   TEXT,
            KurumSicilNo                TEXT,
            MemuriyeteBaslamaTarihi     TEXT,
            CepTelefonu                 TEXT,
            Eposta                      TEXT,
            MezunOlunanOkul             TEXT,
            MezunOlunanFakulte          TEXT,
            MezuniyetTarihi             TEXT,
            DiplomaNo                   TEXT,
            MezunOlunanOkul2            TEXT,
            MezunOlunanFakulte2         TEXT,
            MezuniyetTarihi2            TEXT,
            DiplomaNo2                  TEXT,
            Resim                       TEXT,
            Diploma1                    TEXT,
            Diploma2                    TEXT,
            OzlukDosyasi                TEXT,
            Durum                       TEXT,
            AyrilisTarihi               TEXT,
            AyrilmaNedeni               TEXT,
            MuayeneTarihi               TEXT,
            Sonuc                       TEXT,

            sync_status                 TEXT DEFAULT 'clean',
            updated_at                  TEXT
        )
        """)

        # == IZIN GIRIS ========================================================
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Izin_Giris (
            Izinid          TEXT PRIMARY KEY,
            HizmetSinifi    TEXT,
            Personelid      TEXT,
            AdSoyad         TEXT,
            IzinTipi        TEXT,
            BaslamaTarihi   TEXT,
            Gun             INTEGER,
            BitisTarihi     TEXT,
            Durum           TEXT,

            sync_status     TEXT DEFAULT 'clean',
            updated_at      TEXT
        )
        """)

        # == IZIN BILGI ========================================================
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Izin_Bilgi (
            TCKimlik                TEXT PRIMARY KEY,
            AdSoyad                 TEXT,
            YillikDevir             REAL,
            YillikHakedis           REAL,
            YillikToplamHak         REAL,
            YillikKullanilan        REAL,
            YillikKalan             REAL,
            SuaKullanilabilirHak    REAL,
            SuaKullanilan           REAL,
            SuaKalan                REAL,
            SuaCariYilKazanim       REAL,
            RaporMazeretTop         REAL,

            sync_status             TEXT DEFAULT 'clean',
            updated_at              TEXT
        )
        """)

        # == FHSZ PUANTAJ =====================================================
        cur.execute("""
        CREATE TABLE IF NOT EXISTS FHSZ_Puantaj (
            Personelid          TEXT NOT NULL,
            AdSoyad             TEXT,
            Birim               TEXT,
            CalismaKosulu       TEXT,
            AitYil              INTEGER NOT NULL,
            Donem               TEXT NOT NULL,
            AylikGun            INTEGER,
            KullanilanIzin      INTEGER,
            FiiliCalismaSaat    REAL,

            sync_status         TEXT DEFAULT 'clean',
            updated_at          TEXT,

            PRIMARY KEY (Personelid, AitYil, Donem)
        )
        """)

        # == CIHAZLAR ==========================================================
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Cihazlar (
            Cihazid                 TEXT PRIMARY KEY,
            CihazTipi               TEXT,
            Marka                   TEXT,
            Model                   TEXT,
            Amac                    TEXT,
            Kaynak                  TEXT,
            SeriNo                  TEXT,
            NDKSeriNo               TEXT,
            HizmeteGirisTarihi      TEXT,
            RKS                     TEXT,
            Sorumlusu               TEXT,
            Gorevi                  TEXT,
            NDKLisansNo             TEXT,
            BaslamaTarihi           TEXT,
            BitisTarihi             TEXT,
            LisansDurum             TEXT,
            AnaBilimDali            TEXT,
            Birim                   TEXT,
            BulunduguBina           TEXT,
            GarantiDurumu           TEXT,
            GarantiBitisTarihi      TEXT,
            DemirbasNo              TEXT,
            KalibrasyonGereklimi    TEXT,
            BakimDurum              TEXT,
            Durum                   TEXT,
            Img                     TEXT,
            NDKLisansBelgesi        TEXT,

            sync_status             TEXT DEFAULT 'clean',
            updated_at              TEXT
        )
        """)

        # == CIHAZ TEKNIK ======================================================
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Cihaz_Teknik (
            Cihazid                         TEXT PRIMARY KEY,
            BirincilUrunNumarasi            TEXT,
            MarkaAdi                        TEXT,
            EtiketAdi                       TEXT,
            UrunTanimi                      TEXT,
            VersiyonModel                   TEXT,
            KatalogNo                       TEXT,
            TemelUdiDi                      TEXT,
            Aciklama                        TEXT,
            KurumUnvan                      TEXT,
            KurumGorunenAd                  TEXT,
            KurumNo                         TEXT,
            KurumTelefon                    TEXT,
            KurumEposta                     TEXT,
            Durum                           TEXT,
            UtsBaslangicTarihi              TEXT,
            KontroleGonderildigiTarih       TEXT,
            CihazKayitTipi                  TEXT,
            UrunTipi                        TEXT,
            Sinif                           TEXT,
            IthalImalBilgisi                TEXT,
            GmdnTerimKod                    TEXT,
            GmdnTerimTurkceAd               TEXT,
            GmdnTerimTurkceAciklama         TEXT,
            KalibrasyonaTabiMi              TEXT,
            KalibrasyonPeriyodu             TEXT,
            BakimaTabiMi                    TEXT,
            BakimPeriyodu                   TEXT,
            IyonizeRadyasyonIcerir          TEXT,
            SinirliKullanimSayisiVar        TEXT,
            SinirliKullanimSayisi           TEXT,
            TekHastayaKullanilabilir        TEXT,
            MrgUyumlu                       TEXT,
            SutEslesmesiSet                 TEXT,
            BaskaImalatciyaUrettirildiMi    TEXT,
            MenseiUlkeSet                   TEXT,
            IthalEdilenUlkeSet              TEXT,

            sync_status                     TEXT DEFAULT 'clean',
            updated_at                      TEXT
        )
        """)

        # == CIHAZ TEKNIK BELGE ================================================
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Cihaz_Teknik_Belge (
            Cihazid         TEXT NOT NULL,
            BelgeTuru       TEXT NOT NULL,
            Belge           TEXT NOT NULL,
            BelgeAciklama   TEXT,
            YuklenmeTarihi  TEXT,

            sync_status     TEXT DEFAULT 'clean',
            updated_at      TEXT,

            PRIMARY KEY (Cihazid, BelgeTuru, Belge)
        )
        """)

        # == CIHAZ BELGELER (Merkezi Belgeler) =================================
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Cihaz_Belgeler (
            Cihazid             TEXT NOT NULL,
            BelgeTuru           TEXT NOT NULL,
            Belge               TEXT NOT NULL,
            BelgeAciklama       TEXT,
            YuklenmeTarihi      TEXT,
            IliskiliBelgeID     TEXT,
            IliskiliBelgeTipi   TEXT,

            sync_status         TEXT DEFAULT 'clean',
            updated_at          TEXT,

            PRIMARY KEY (Cihazid, BelgeTuru, Belge)
        )
        """)

        # == ORTAK DOKÃœMANLAR (Tüm modüller) ==================================
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Dokumanlar (
            EntityType          TEXT NOT NULL,
            EntityId            TEXT NOT NULL,
            BelgeTuru           TEXT NOT NULL,
            Belge               TEXT NOT NULL,
            DocType             TEXT,
            DisplayName         TEXT,
            LocalPath           TEXT,
            BelgeAciklama       TEXT,
            YuklenmeTarihi      TEXT,
            DrivePath           TEXT,
            IliskiliBelgeID     TEXT,
            IliskiliBelgeTipi   TEXT,

            sync_status         TEXT DEFAULT 'clean',
            updated_at          TEXT,

            PRIMARY KEY (EntityType, EntityId, BelgeTuru, Belge)
        )
        """)

        # == CIHAZ ARIZA =======================================================
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Cihaz_Ariza (
            Arizaid         TEXT PRIMARY KEY,
            Cihazid         TEXT,
            BaslangicTarihi TEXT,
            Saat            TEXT,
            Bildiren        TEXT,
            ArizaTipi       TEXT,
            Oncelik         TEXT,
            Baslik          TEXT,
            ArizaAcikla     TEXT,
            Durum           TEXT,
            Rapor           TEXT,

            sync_status     TEXT DEFAULT 'clean',
            updated_at      TEXT
        )
        """)

        # == ARIZA ISLEM =======================================================
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Ariza_Islem (
            Islemid         TEXT PRIMARY KEY,
            Arizaid         TEXT,
            Tarih           TEXT,
            Saat            TEXT,
            IslemYapan      TEXT,
            IslemTuru       TEXT,
            YapilanIslem    TEXT,
            YeniDurum       TEXT,
            Rapor           TEXT,

            sync_status     TEXT DEFAULT 'clean',
            updated_at      TEXT
        )
        """)

        # == PERIYODIK BAKIM ===================================================
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Periyodik_Bakim (
            Planid              TEXT PRIMARY KEY,
            Cihazid             TEXT,
            BakimPeriyodu       TEXT,
            BakimSirasi         INTEGER,
            PlanlananTarih      TEXT,
            Bakim               TEXT,
            Durum               TEXT,
            BakimTarihi         TEXT,
            BakimTipi           TEXT,
            YapilanIslemler     TEXT,
            Aciklama            TEXT,
            Teknisyen           TEXT,
            Rapor               TEXT,

            sync_status         TEXT DEFAULT 'clean',
            updated_at          TEXT
        )
        """)

        # == KALIBRASYON =======================================================
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Kalibrasyon (
            Kalid           TEXT PRIMARY KEY,
            Cihazid         TEXT,
            Firma           TEXT,
            SertifikaNo     TEXT,
            YapilanTarih    TEXT,
            Gecerlilik      TEXT,
            BitisTarihi     TEXT,
            Durum           TEXT,
            Dosya           TEXT,
            Aciklama        TEXT,

            sync_status     TEXT DEFAULT 'clean',
            updated_at      TEXT
        )
        """)

        # == SABITLER ==========================================================
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Sabitler (
            Rowid       TEXT PRIMARY KEY,
            Kod         TEXT,
            MenuEleman  TEXT,
            Aciklama    TEXT,

            sync_status TEXT DEFAULT 'clean',
            updated_at  TEXT
        )
        """)

        # == TATILLER ==========================================================
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Tatiller (
            Tarih       TEXT PRIMARY KEY,
            ResmiTatil  TEXT,

            sync_status TEXT DEFAULT 'clean',
            updated_at  TEXT
        )
        """)

        # == LOGLAR ============================================================
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Loglar (
            Tarih       TEXT,
            Saat        TEXT,
            Kullanici   TEXT,
            Modul       TEXT,
            Islem       TEXT,
            Detay       TEXT
        )
        """)

        # == RKE LIST ==========================================================
        cur.execute("""
        CREATE TABLE IF NOT EXISTS RKE_List (
            EkipmanNo       TEXT PRIMARY KEY,
            KoruyucuNumarasi TEXT,
            AnaBilimDali    TEXT,
            Birim           TEXT,
            KoruyucuCinsi   TEXT,
            KursunEsdegeri  TEXT,
            HizmetYili      INTEGER,
            Bedeni          TEXT,
            KontrolTarihi   TEXT,
            Durum           TEXT,
            Aciklama        TEXT,
            VarsaDemirbasNo TEXT,
            KayitTarih      TEXT,
            Barkod          TEXT,

            sync_status     TEXT DEFAULT 'clean',
            updated_at      TEXT
        )
        """)

        # == RKE MUAYENE =======================================================
        cur.execute("""
        CREATE TABLE IF NOT EXISTS RKE_Muayene (
            KayitNo                 TEXT PRIMARY KEY,
            EkipmanNo               TEXT,
            FMuayeneTarihi          TEXT,
            FizikselDurum           TEXT,
            SMuayeneTarihi          TEXT,
            SkopiDurum              TEXT,
            Aciklamalar             TEXT,
            KontrolEdenUnvani       TEXT,
            BirimSorumlusuUnvani    TEXT,
            Notlar                  TEXT,
            Rapor                   TEXT,

            sync_status             TEXT DEFAULT 'clean',
            updated_at              TEXT
        )
        """)

        # == PERSONEL SAGLIK TAKIP =============================================
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Personel_Saglik_Takip (
            KayitNo                     TEXT PRIMARY KEY,
            Personelid                  TEXT,
            AdSoyad                     TEXT,
            Birim                       TEXT,
            Yil                         INTEGER,
            MuayeneTarihi               TEXT,
            SonrakiKontrolTarihi        TEXT,
            Sonuc                       TEXT,
            Durum                       TEXT,
            RaporDosya                  TEXT,
            Notlar                      TEXT,
            DermatolojiMuayeneTarihi    TEXT,
            DermatolojiDurum            TEXT,
            DahiliyeMuayeneTarihi       TEXT,
            DahiliyeDurum               TEXT,
            GozMuayeneTarihi            TEXT,
            GozDurum                    TEXT,
            GoruntulemeMuayeneTarihi    TEXT,
            GoruntulemeDurum            TEXT,

            sync_status                 TEXT DEFAULT 'clean',
            updated_at                  TEXT
        )
        """)

        # == DOZIMETRE ÖLÇÜM ==================================================
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Dozimetre_Olcum (
            KayitNo            TEXT PRIMARY KEY,
            SiraNo             INTEGER,
            RaporNo            TEXT,
            Periyot            INTEGER,
            PeriyotAdi         TEXT,
            Yil                INTEGER,
            DozimetriTipi      TEXT,
            AdSoyad            TEXT,
            TCKimlikNo         TEXT,
            CalistiBirim       TEXT,
            PersonelID         TEXT,
            DozimetreNo        TEXT,
            VucutBolgesi       TEXT,
            Hp10               REAL,
            Hp007              REAL,
            DozSiniri_Hp10     REAL,
            DozSiniri_Hp007    REAL,
            Durum              TEXT,
            OlusturmaTarihi    TEXT DEFAULT (date('now')),

            sync_status        TEXT DEFAULT 'clean',
            updated_at         TEXT
        )
        """)

        # Auth/RBAC tabloları
        self._create_auth_tables(cur)

    def _create_auth_tables(self, cur):
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            UserId          INTEGER PRIMARY KEY AUTOINCREMENT,
            Username        TEXT UNIQUE NOT NULL,
            PasswordHash    TEXT NOT NULL,
            IsActive        INTEGER NOT NULL DEFAULT 1,
            MustChangePassword INTEGER NOT NULL DEFAULT 0,
            CreatedAt       TEXT NOT NULL,
            LastLoginAt     TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS Roles (
            RoleId      INTEGER PRIMARY KEY AUTOINCREMENT,
            RoleName    TEXT UNIQUE NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS Permissions (
            PermissionId    INTEGER PRIMARY KEY AUTOINCREMENT,
            PermissionKey   TEXT UNIQUE NOT NULL,
            Description     TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS UserRoles (
            UserId  INTEGER NOT NULL,
            RoleId  INTEGER NOT NULL,
            PRIMARY KEY (UserId, RoleId)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS RolePermissions (
            RoleId          INTEGER NOT NULL,
            PermissionId    INTEGER NOT NULL,
            PRIMARY KEY (RoleId, PermissionId)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS AuthAudit (
            AuditId     INTEGER PRIMARY KEY AUTOINCREMENT,
            Username    TEXT,
            Success     INTEGER NOT NULL,
            Reason      TEXT,
            CreatedAt   TEXT NOT NULL
        )
        """)

    def _seed_auth_data(self, cur):
        permissions = [
            ("personel.read", "Personel okuma"),
            ("personel.write", "Personel yazma"),
            ("cihaz.read", "Cihaz okuma"),
            ("cihaz.write", "Cihaz yazma"),
            ("admin.panel", "Admin panel eriŞimi"),
            ("admin.logs.view", "Log görüntüleme"),
            ("admin.backup", "Yedek yönetimi"),
            ("admin.settings", "Ayarlar yönetimi"),
        ]

        for key, desc in permissions:
            cur.execute("SELECT COUNT(*) FROM Permissions WHERE PermissionKey = ?", (key,))
            if cur.fetchone()[0] == 0:
                cur.execute(
                    "INSERT INTO Permissions (PermissionKey, Description) VALUES (?, ?)",
                    (key, desc)
                )

        roles = ["admin", "operator", "viewer"]
        for role in roles:
            cur.execute("SELECT COUNT(*) FROM Roles WHERE RoleName = ?", (role,))
            if cur.fetchone()[0] == 0:
                cur.execute("INSERT INTO Roles (RoleName) VALUES (?)", (role,))

        cur.execute("SELECT RoleId, RoleName FROM Roles")
        role_map = {row["RoleName"]: row["RoleId"] for row in cur.fetchall()}

        cur.execute("SELECT PermissionId, PermissionKey FROM Permissions")
        perm_map = {row["PermissionKey"]: row["PermissionId"] for row in cur.fetchall()}

        admin_id = role_map.get("admin")
        if admin_id:
            for perm_id in perm_map.values():
                cur.execute("""
                    SELECT COUNT(*) FROM RolePermissions
                    WHERE RoleId = ? AND PermissionId = ?
                """, (admin_id, perm_id))
                if cur.fetchone()[0] == 0:
                    cur.execute(
                        "INSERT INTO RolePermissions (RoleId, PermissionId) VALUES (?, ?)",
                        (admin_id, perm_id)
                    )

        operator_id = role_map.get("operator")
        if operator_id:
            for key in ("personel.read", "personel.write", "cihaz.read", "cihaz.write"):
                perm_id = perm_map.get(key)
                if not perm_id:
                    continue
                cur.execute("""
                    SELECT COUNT(*) FROM RolePermissions
                    WHERE RoleId = ? AND PermissionId = ?
                """, (operator_id, perm_id))
                if cur.fetchone()[0] == 0:
                    cur.execute(
                        "INSERT INTO RolePermissions (RoleId, PermissionId) VALUES (?, ?)",
                        (operator_id, perm_id)
                    )

        viewer_id = role_map.get("viewer")
        if viewer_id:
            for key in ("personel.read", "cihaz.read"):
                perm_id = perm_map.get(key)
                if not perm_id:
                    continue
                cur.execute("""
                    SELECT COUNT(*) FROM RolePermissions
                    WHERE RoleId = ? AND PermissionId = ?
                """, (viewer_id, perm_id))
                if cur.fetchone()[0] == 0:
                    cur.execute(
                        "INSERT INTO RolePermissions (RoleId, PermissionId) VALUES (?, ?)",
                        (viewer_id, perm_id)
                    )

    def _seed_initial_data(self, cur):
        """
        Sabitler tablosuna başlangıç / sistem verilerini ekler.
        Tatiller tablosuna tatil tarihlerini ekler.
        Yalnızca yeni kurulumda çağrılır; mevcut kayıtların üzerine yazmaz.
        """
        # === SİSTEM SABİTLERİ ===
        # Sabitler.csv baz alınarak seed listesi
        sistem_sabitler = [
            ("1", "İzin_Tipi", "Aylıksız İzin - Askerlik Nedeniyle", ""),
            ("2", "İzin_Tipi", "Aylıksız İzin - Doğum Nedeniyle", ""),
            ("3", "İzin_Tipi", "Doğum İzni (Eşinin)", "10"),
            ("4", "İzin_Tipi", "Doğum Öncesi İzin", "42"),
            ("5", "İzin_Tipi", "Doğum Sonrası İzin", "42"),
            ("6", "İzin_Tipi", "Evlenme-Ölüm İzni", ""),
            ("7", "İzin_Tipi", "Evlilik İzni", ""),
            ("8", "İzin_Tipi", "Heyet Raporu", ""),
            ("9", "İzin_Tipi", "İdari İzin", ""),
            ("11", "İzin_Tipi", "Kongre izni: 3 aya kadar", ""),
            ("12", "İzin_Tipi", "Mazeret", ""),
            ("13", "İzin_Tipi", "Rapor İzni", ""),
            ("14", "İzin_Tipi", "Refakatçı İzni", ""),
            ("15", "İzin_Tipi", "Şua İzni", "30"),
            ("16", "İzin_Tipi", "Tedavi İzni (Yatış Ve Ayaktan)", ""),
            ("17", "İzin_Tipi", "Yıllık İzin", "30"),
            ("18", "Amac", "Defibrilator", ""),
            ("19", "Amac", "EKG Cihazı", ""),
            ("20", "Amac", "Grafi", ""),
            ("21", "Amac", "Kaset Okuyucu", ""),
            ("22", "Amac", "Manyetik Rezonans", ""),
            ("23", "Amac", "Skopi", ""),
            ("24", "Amac", "Skopi (Ercp)", ""),
            ("25", "Amac", "Skopi (Eswl)", ""),
            ("26", "Amac", "Ultrasonografi", ""),
            ("27", "AnaBilimDali", "Beyin ve Sinir Cerrahisi ABD", "NRŞ"),
            ("32", "AnaBilimDali", "Göğüs Hastalıkları ABD", "GHA"),
            ("33", "AnaBilimDali", "İç Hastalıkları ABD", "DHL"),
            ("34", "AnaBilimDali", "Kalp ve Damar Cerrahisi ABD", "KDC"),
            ("35", "AnaBilimDali", "Kardiyoloji ABD", "KRD"),
            ("38", "AnaBilimDali", "Ortopedi ve Travmatoloji ABD", "ORT"),
            ("39", "AnaBilimDali", "Radyoloji ABD", "RAD"),
            ("40", "AnaBilimDali", "Üroloji ABD", "URO"),
            ("41", "Ariza_Durum", "İşlemde", ""),
            ("42", "Ariza_Durum", "Parça Bekliyor", ""),
            ("43", "Ariza_Durum", "Dış Serviste", ""),
            ("44", "Ariza_Durum", "Kapalı (Çözüldü)", ""),
            ("45", "Ariza_Durum", "Kapalı (İptal)", ""),
            ("46", "Ariza_Islem_Turu", "Arıza Tespiti / İnceleme", ""),
            ("47", "Ariza_Islem_Turu", "Onarım / Tamirat", ""),
            ("48", "Ariza_Islem_Turu", "Parça Değişimi", ""),
            ("49", "Ariza_Islem_Turu", "Yazılım Güncelleme", ""),
            ("50", "Ariza_Islem_Turu", "Kalibrasyon", ""),
            ("51", "Ariza_Islem_Turu", "Dış Servis Gönderimi", ""),
            ("52", "Ariza_Islem_Turu", "Kapatma / Sonlandırma", ""),
            ("53", "Bedeni", "L", ""),
            ("54", "Bedeni", "M", ""),
            ("55", "Bedeni", "Pediatrik", ""),
            ("56", "Bedeni", "S", ""),
            ("57", "Bedeni", "STN", ""),
            ("58", "Bedeni", "XL", ""),
            ("59", "Bedeni", "XS", ""),
            ("60", "Bedeni", "Yetişkin", ""),
            ("61", "Birim", "Acil Radyoloji", "ARAD"),
            ("63", "Birim", "Ameliyathane", "AML"),
            ("64", "Birim", "Anjiografi", "ANJ"),
            ("65", "Birim", "Endoskopi Ünitesi", "ENU"),
            ("66", "Birim", "Girişimsel Radyoloji Anjiografi", "RANJ"),
            ("67", "Birim", "Koroner Anjiografi", "KANJ"),
            ("68", "Birim", "Mamografi", "MAM"),
            ("69", "Birim", "Manyetik Rezonans Ünitesi", "MRI"),
            ("70", "Birim", "Nöroradyoloji Anjiografi", "NANJ"),
            ("71", "Birim", "Poliklinik", "POL"),
            ("72", "Birim", "Radyoloji USG", "USG"),
            ("73", "Birim", "Yoğun Bakım Ünitesi", "YBÜ"),
            ("74", "Cihaz_Belge_Tur", "NDK Lisansı", "Cihazın NDK (Uygunluk Beyanı) Lisansı"),
            ("75", "Cihaz_Belge_Tur", "RKS Belgesi", "Cihazın RKS (Radyasyon Koruma) Belgesi"),
            ("76", "Cihaz_Belge_Tur", "Sorumlu Diploması", "Sorumlu kişinin diploması"),
            ("77", "Cihaz_Belge_Tur", "Kullanım Klavuzu", "Cihaz kullanım kılavuzu"),
            ("78", "Cihaz_Belge_Tur", "Cihaz Sertifikası", "Cihaz sertifikası/belgelendirmesi"),
            ("79", "Cihaz_Belge_Tur", "Teknik Veri Sayfası", "Cihazın teknik özellikleri"),
            ("80", "Cihaz_Belge_Tur", "Garantı Belgesi", "Cihaz garanti belgesi"),
            ("81", "Cihaz_Tipi", "Görüntüleme (Diğer)", "GOR"),
            ("82", "Cihaz_Tipi", "Görüntüleme (Radyasyon Kaynaklı)", "XRY"),
            ("83", "Cihaz_Tipi", "Medikal Cihazlar", "MED"),
            ("84", "Gorev_Yeri", "Acil Radyoloji", "Çalışma Koşulu A"),
            ("85", "Gorev_Yeri", "Esnaf Has. Yerleşkesi", "Çalışma Koşulu B"),
            ("86", "Gorev_Yeri", "Girişimsel Radyoloji", "Çalışma Koşulu A"),
            ("87", "Gorev_Yeri", "Gögüs Hastalıkları", "Çalışma Koşulu B"),
            ("99", "Hizmet_Sinifi", "Akademik Personel", ""),
            ("100", "Hizmet_Sinifi", "Asistan Doktor", ""),
            ("101", "Hizmet_Sinifi", "Hemşire", ""),
            ("102", "Hizmet_Sinifi", "Radyasyon Görevlisi", ""),
            ("103", "Kadro_Unvani", "Araştırma Görevlisi", ""),
            ("104", "Kadro_Unvani", "Doçent Doktor", ""),
            ("105", "Kadro_Unvani", "Doktor", ""),
            ("106", "Kadro_Unvani", "Doktor Öğretim Üyesi", ""),
            ("107", "Kadro_Unvani", "Ebe", ""),
            ("108", "Kadro_Unvani", "Hasta Bakıcı", ""),
            ("109", "Kadro_Unvani", "Hemşire", ""),
            ("112", "Kadro_Unvani", "Profesör Doktor", ""),
            ("114", "Kadro_Unvani", "Radyoloji Teknikeri", ""),
            ("115", "Kadro_Unvani", "Radyoloji Teknisyeni", ""),
            ("116", "Kadro_Unvani", "Sağlık Memuru", ""),
            ("117", "Kadro_Unvani", "Sağlık Teknikeri", ""),
            ("118", "Kadro_Unvani", "Sağlık Teknisyeni", ""),
            ("121", "Kadro_Unvani", "Teknisyen", ""),
            ("123", "Kadro_Unvani", "Uzman Doktor", ""),
            ("125", "Kaynak", "Anjiyo", "ANJ"),
            ("126", "Kaynak", "C-Kollu", "CKL"),
            ("127", "Kaynak", "CR Cihazı", "CRC"),
            ("128", "Kaynak", "Mamografi", "MAM"),
            ("129", "Kaynak", "Manyetik Rezonans", "MRI"),
            ("130", "Kaynak", "Medikal Cihaz", "MED"),
            ("131", "Kaynak", "Mobil Bilgisayarlı Tomografi", "MCT"),
            ("132", "Kaynak", "Mobil Tek Tüplü Röntgen", "MTTR"),
            ("133", "Kaynak", "Tek Tüplü Röntgen", "TTR"),
            ("134", "Kaynak", "Tomografi", "CT"),
            ("135", "Kaynak", "Ultrasonografi", "USG"),
            ("136", "Koruyucu_Cinsi", "Gonad Koruyucu", "GK"),
            ("137", "Koruyucu_Cinsi", "Kurşun Başlık", "KB"),
            ("138", "Koruyucu_Cinsi", "Kurşun Eldiven", "KE"),
            ("139", "Koruyucu_Cinsi", "Kurşun Gözlük", "KG"),
            ("140", "Koruyucu_Cinsi", "Kurşun Paravan", "KP"),
            ("141", "Koruyucu_Cinsi", "Palto (Önlük)", "O"),
            ("142", "Koruyucu_Cinsi", "Tiroid Koruyucu", "TK"),
            ("143", "Koruyucu_Cinsi", "Uyarı İşaretleri", "UI"),
            ("144", "Koruyucu_Cinsi", "Yelek - Etek", "YE"),
            ("145", "Lisans_Durum", "Devir", ""),
            ("146", "Lisans_Durum", "Eksik Husus", ""),
            ("147", "Lisans_Durum", "Kullanım Dışı (Depo)", ""),
            ("148", "Lisans_Durum", "Kullanım Dışı (HEK)", ""),
            ("149", "Lisans_Durum", "Lisans Gerekli Değil", ""),
            ("150", "Lisans_Durum", "Lisansız", ""),
            ("151", "Lisans_Durum", "Lisanslı", ""),
            ("152", "Marka", "", ""),
            ("153", "RKE_Teknik", "Dikiş yerlerinde hasar var", ""),
            ("154", "RKE_Teknik", "Kullanım Ömrünü Doldurmuş", ""),
            ("155", "RKE_Teknik", "Kullanım ve bakım koşullarına uyulmamış", ""),
            ("156", "RKE_Teknik", "Kurşun, etek kısımlarında (aşağıya) toplanmış", ""),
            ("157", "RKE_Teknik", "Sabitleyici bantlar ve/veya tokalar deforme", ""),
            ("158", "RKE_Teknik", "Skopi altında kırık tespit edildi", ""),
            ("159", "RKE_Teknik", "Tüm testler normal ekipman kullanıma uygun", ""),
            ("160", "Sistem_DriveID", "Ariza_Raporlari", ""),
            ("161", "Sistem_DriveID", "Cihaz_Kunye", ""),
            ("162", "Sistem_DriveID", "Cihaz_Resim", ""),
            ("163", "Sistem_DriveID", "Kalibrasyon_Raporlari", ""),
            ("164", "Sistem_DriveID", "Cihaz_Lisanslar", ""),
            ("165", "Sistem_DriveID", "Personel_Diploma", ""),
            ("166", "Sistem_DriveID", "Personel_Dosya", ""),
            ("167", "Sistem_DriveID", "Personel_Resim", ""),
            ("168", "Sistem_DriveID", "RKE_Raporlari", ""),
            ("169", "Sistem_DriveID", "Eski_Personel_Dosyalari", ""),
            ("170", "Sistem_DriveID", "RKE_Muayene", ""),
            ("171", "Sistem_DriveID", "Saglik_Raporlari", ""),
        ]
        
        added_count = 0
        for rowid, kod, menu_eleman, aciklama in sistem_sabitler:
            cur.execute(
                "SELECT COUNT(*) FROM Sabitler WHERE Kod = ? AND MenuEleman = ?",
                (kod, menu_eleman)
            )
            if cur.fetchone()[0] == 0:
                cur.execute(
                    "INSERT INTO Sabitler (Rowid, Kod, MenuEleman, Aciklama) VALUES (?, ?, ?, ?)",
                    (rowid, kod, menu_eleman, aciklama)
                )
                added_count += 1
        
        if added_count > 0:
            logger.info(f"  ✓ Sabitler: {added_count} kayıt eklendi")
        
        # === TATİLLER ===
        # Tatiller.csv baz alınarak YYYY-MM-DD formatında seed listesi
        tatiller = [
            ("2026-01-01", "Yılbaşı"),
            ("2026-04-23", "Ulusal Egemenlik ve Çocuk Bayramı"),
            ("2026-05-01", "Emek ve Dayanışma Günü"),
            ("2026-05-19", "Atatürk’ü Anma Gençlik ve Spor Bayramı"),
            ("2026-07-15", "Demokrasi ve Millî Birlik Günü"),
            ("2026-08-30", "Zafer Bayramı"),
            ("2026-10-28", "Cumhuriyet Bayramı Arifesi"),
            ("2026-10-29", "Cumhuriyet Bayramı"),
            ("2026-12-31", "Yılbaşı gecesi"),
        ]
        
        added_tatil = 0
        for tarih, ad in tatiller:
            cur.execute(
                "SELECT COUNT(*) FROM Tatiller WHERE Tarih = ?",
                (tarih,)
            )
            if cur.fetchone()[0] == 0:
                cur.execute(
                    "INSERT INTO Tatiller (Tarih, ResmiTatil) VALUES (?, ?)",
                    (tarih, ad)
                )
                added_tatil += 1
        
        if added_tatil > 0:
            logger.info(f"  ✓ Tatillər: {added_tatil} kayıt eklendi")


    def reset_database(self):
        """
        âš ï¸  ACİL DURUM: Tüm tabloları sil ve yeniden oluŞtur.

        Ciddi veri bozulması durumunda manuel olarak çağrılmalıdır.
        Normal kullanımda run_migrations() tercih edilmelidir.
        """
        logger.warning("âš ï¸  VERİTABANI TAM RESET YAPILIYOR â€” TÃœM VERİ SİLİNECEK!")

        backup_path = self.backup_database()
        if backup_path:
            logger.info(f"Son yedek: {backup_path}")

        conn = self.connect()
        cur = conn.cursor()

        tables = [
            "Personel", "Izin_Giris", "Izin_Bilgi", "FHSZ_Puantaj",
            "Cihazlar", "Cihaz_Teknik", "Cihaz_Teknik_Belge", "Cihaz_Belgeler",
            "Cihaz_Ariza", "Ariza_Islem", "Periyodik_Bakim", "Kalibrasyon",
            "Sabitler", "Tatiller", "Loglar",
            "RKE_List", "RKE_Muayene", "Personel_Saglik_Takip",
            "Dokumanlar",
            "Users", "Roles", "Permissions", "UserRoles", "RolePermissions", "AuthAudit",
            "schema_version",
        ]

        for table in tables:
            cur.execute(f"DROP TABLE IF EXISTS {table}")
            logger.info(f"  {table} silindi")

        self.create_tables(cur)
        self._seed_initial_data(cur)

        cur.execute("""
            CREATE TABLE schema_version (
                version     INTEGER PRIMARY KEY,
                applied_at  TEXT NOT NULL,
                description TEXT
            )
        """)
        cur.execute("""
            INSERT INTO schema_version (version, applied_at, description)
            VALUES (?, ?, ?)
        """, (self.CURRENT_VERSION, datetime.now().isoformat(), "Full reset"))

        conn.commit()
        conn.close()

        logger.info(f"✓ Tüm tablolar yeniden oluŞturuldu (v{self.CURRENT_VERSION})")



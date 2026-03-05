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
    CURRENT_VERSION = 1

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
        Sabitler tablosuna baŞlangıç / sistem verilerini ekler.
        Yalnızca yeni kurulumda çağrılır; mevcut kayıtların üzerine yazmaz.
        """
        belge_turleri = [
            ("1",   "Cihaz_Belge_Tur",   "NDK Lisansı",         "Cihazın NDK (Uygunluk Beyanı) Lisansı"),
            ("2",   "Cihaz_Belge_Tur",   "RKS Belgesi",          "Cihazın RKS (Radyasyon Koruma) Belgesi"),
            ("3",   "Cihaz_Belge_Tur",   "Sorumlu Diploması",    "Sorumlu kiŞinin diploması"),
            ("4",   "Cihaz_Belge_Tur",   "Kullanım Klavuzu",     "Cihaz kullanım kılavuzu"),
            ("5",   "Cihaz_Belge_Tur",   "Cihaz Sertifikası",    "Cihaz sertifikası/belgelendirmesi"),
            ("6",   "Cihaz_Belge_Tur",   "Teknik Veri Sayfası",  "Cihazın teknik özellikleri"),
            ("7",   "Cihaz_Belge_Tur",   "Garantı Belgesi",      "Cihaz garanti belgesi"),

            ("101", "Personel_Belge_Tur", "Diploma",             "Personel diploması"),
            ("102", "Personel_Belge_Tur", "Sertifika",           "Personel sertifikası"),
            ("103", "Personel_Belge_Tur", "Ehliyet",             "Personel ehliyet belgesi"),
            ("104", "Personel_Belge_Tur", "Kimlik",              "Personel kimlik belgesi"),
            ("105", "Personel_Belge_Tur", "Diğer",               "Personel diğer belgeler"),
        ]
        for rowid, kod, menu_eleman, aciklama in belge_turleri:
            cur.execute(
                "SELECT COUNT(*) FROM Sabitler WHERE Kod = ? AND MenuEleman = ?",
                (kod, menu_eleman)
            )
            if cur.fetchone()[0] == 0:
                cur.execute(
                    "INSERT INTO Sabitler (Rowid, Kod, MenuEleman, Aciklama) VALUES (?, ?, ?, ?)",
                    (rowid, kod, menu_eleman, aciklama)
                )
                logger.info(f"  âœ“ Sabitler: '{menu_eleman}' eklendi")

    # ================================================
    # ACİL RESET (yalnızca manuel çağrı)
    # ================================================

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



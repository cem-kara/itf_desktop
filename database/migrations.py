# database/migrations.py
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
from core.logger import logger


class MigrationManager:
    """
    Versiyon tabanlÄ± migration yÃ¶neticisi.

    Ã–zellikler:
    - Otomatik ÅŸema versiyonlama
    - GÃ¼venli migration adÄ±mlarÄ±
    - Otomatik yedekleme
    - Rollback desteÄŸi
    - Veri kaybÄ± olmadan ÅŸema gÃ¼ncellemeleri

    Squash GeÃ§miÅŸi:
    - v1â€“v14 arasÄ± tÃ¼m ara migration'lar tek bir temiz kurulum adÄ±mÄ±na
      (v1: create_tables + baÅŸlangÄ±Ã§ verisi) indirgendi.
    - Mevcut v14 veritabanlarÄ± etkilenmez.
    - SÄ±fÄ±rdan kurulumda v1 tÃ¼m tablolarÄ± doÄŸrudan son hÃ¢liyle oluÅŸturur;
      v2â€“v14 otomatik olarak no-op geÃ§ilir.
    """

    # Mevcut ÅŸema versiyonu
    CURRENT_VERSION = 17

    def __init__(self, db_path):
        self.db_path = db_path
        self.backup_dir = Path(db_path).parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # BAÄLANTI & VERSÄ°YON
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def connect(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def get_schema_version(self):
        """Mevcut ÅŸema versiyonunu dÃ¶ndÃ¼rÃ¼r."""
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
        """Åema versiyonunu gÃ¼nceller."""
        conn = self.connect()
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO schema_version (version, applied_at, description)
                VALUES (?, ?, ?)
            """, (version, datetime.now().isoformat(), description))
            conn.commit()
            logger.info(f"Åema versiyonu {version} olarak gÃ¼ncellendi: {description}")

        finally:
            conn.close()

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # YEDEKLEME
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def backup_database(self):
        """VeritabanÄ±nÄ± yedekler."""
        if not Path(self.db_path).exists():
            logger.info("Yedeklenecek veritabanÄ± bulunamadÄ±")
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"db_backup_{timestamp}.db"

        try:
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"VeritabanÄ± yedeklendi: {backup_path}")
            self._cleanup_old_backups()
            return backup_path

        except Exception as e:
            logger.error(f"Yedekleme hatasÄ±: {e}")
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

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # MÄ°GRATION Ã‡ALIÅTIRICI
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def run_migrations(self):
        """
        TÃ¼m bekleyen migration'larÄ± Ã§alÄ±ÅŸtÄ±rÄ±r.
        Veri kaybÄ± olmadan ÅŸemayÄ± gÃ¼nceller.
        """
        current_version = self.get_schema_version()

        if current_version == self.CURRENT_VERSION:
            logger.info(f"Åema gÃ¼ncel (v{current_version})")
            return True

        if current_version > self.CURRENT_VERSION:
            logger.warning(
                f"Åema versiyonu ({current_version}) koddan ({self.CURRENT_VERSION}) yÃ¼ksek! "
                "Uygulama gÃ¼ncellemesi gerekebilir."
            )
            return False

        backup_path = self.backup_database()
        if not backup_path:
            logger.warning("Yedekleme yapÄ±lamadÄ± ama migration devam ediyor")

        logger.info(f"Migration baÅŸlÄ±yor: v{current_version} â†’ v{self.CURRENT_VERSION}")

        try:
            for version in range(current_version + 1, self.CURRENT_VERSION + 1):
                migration_method = getattr(self, f"_migrate_to_v{version}", None)

                if migration_method:
                    logger.info(f"Migration v{version} uygulanÄ±yor...")
                    migration_method()
                else:
                    # TanÄ±mlÄ± metod yok â†’ no-op; yine de versiyona kayÄ±t yapÄ±lÄ±r.
                    logger.info(f"Migration v{version} â€” no-op, atlanÄ±yor")

                self.set_schema_version(version, f"Migrated to v{version}")

            logger.info("âœ“ TÃ¼m migration'lar baÅŸarÄ±yla tamamlandÄ±")
            return True

        except Exception as e:
            logger.error(f"Migration hatasÄ±: {e}")
            logger.error(f"Yedekten geri yÃ¼kleme yapabilirsiniz: {backup_path}")
            raise

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # MIGRATION METODLARI
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def _migrate_to_v1(self):
        """
        v0 â†’ v1: Temiz kurulum â€” tÃ¼m tablolarÄ± son ÅŸemalarÄ±yla oluÅŸturur
                 ve baÅŸlangÄ±Ã§ verilerini (Sabitler) ekler.

        v2â€“v14: Squash sonrasÄ± no-op; run_migrations tarafÄ±ndan otomatik geÃ§ilir.
        """
        conn = self.connect()
        cur = conn.cursor()

        try:
            self.create_tables(cur)
            self._seed_initial_data(cur)
            self._seed_auth_data(cur)
            conn.commit()
            logger.info("v1: TÃ¼m tablolar oluÅŸturuldu ve baÅŸlangÄ±Ã§ verileri eklendi")

        finally:
            conn.close()

    def _migrate_to_v15(self):
        """
        v14 â†’ v15: Ortak dokÃ¼manlar tablosunu ekle ve DrivePath sÃ¼tununu garanti et.
        """
        conn = self.connect()
        cur = conn.cursor()

        try:
            logger.info("Migration v15: Dokumanlar tablosu oluÅŸturuluyor...")

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

            # Kolon gÃ¼vence: ileride versiyon arttÄ±rmadan eklemeye devam edebilmek iÃ§in
            cur.execute("PRAGMA table_info(Dokumanlar)")
            cols = {row[1] for row in cur.fetchall()}
            if "DocType" not in cols:
                cur.execute("""
                    ALTER TABLE Dokumanlar
                    ADD COLUMN DocType TEXT
                """)
                logger.info("  âœ“ Dokumanlar.DocType kolon eklendi")
            if "DisplayName" not in cols:
                cur.execute("""
                    ALTER TABLE Dokumanlar
                    ADD COLUMN DisplayName TEXT
                """)
                logger.info("  âœ“ Dokumanlar.DisplayName kolon eklendi")
            if "LocalPath" not in cols:
                cur.execute("""
                    ALTER TABLE Dokumanlar
                    ADD COLUMN LocalPath TEXT
                """)
                logger.info("  âœ“ Dokumanlar.LocalPath kolon eklendi")
            if "DrivePath" not in cols:
                cur.execute("""
                    ALTER TABLE Dokumanlar
                    ADD COLUMN DrivePath TEXT
                """)
                logger.info("  âœ“ Dokumanlar.DrivePath kolon eklendi")

            conn.commit()
            logger.info("v15: Migration tamamlandÄ±")

        finally:
            conn.close()

    def _migrate_to_v16(self):
        """
        v15 â†’ v16: Auth/RBAC tablolarÄ±nÄ± ekle ve temel seed uygula.
        """
        conn = self.connect()
        cur = conn.cursor()

        try:
            logger.info("Migration v16: Auth/RBAC tablolarÄ± oluÅŸturuluyor...")
            self._create_auth_tables(cur)
            self._seed_auth_data(cur)
            conn.commit()
            logger.info("v16: Migration tamamlandÄ±")
        finally:
            conn.close()

    def _migrate_to_v17(self):
        """
        v16 -> v17: Users tablosuna MustChangePassword alanini ekle.
        """
        conn = self.connect()
        cur = conn.cursor()
        try:
            cur.execute("PRAGMA table_info(Users)")
            cols = [row["name"] for row in cur.fetchall()]
            if "MustChangePassword" not in cols:
                cur.execute(
                    "ALTER TABLE Users ADD COLUMN MustChangePassword INTEGER NOT NULL DEFAULT 0"
                )
                conn.commit()
        finally:
            conn.close()

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # TABLO OLUÅTURMA (Ä°LK KURULUM / RESET)
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def create_tables(self, cur):
        """
        TÃ¼m tablolarÄ± v14 (gÃ¼ncel) ÅŸemasÄ±yla oluÅŸturur.
        YalnÄ±zca _migrate_to_v1 ve reset_database tarafÄ±ndan Ã§aÄŸrÄ±lÄ±r.
        """

        # â”€â”€ PERSONEL â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        # â”€â”€ IZIN GIRIS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        # â”€â”€ IZIN BILGI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        # â”€â”€ FHSZ PUANTAJ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        # â”€â”€ CIHAZLAR â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        # â”€â”€ CIHAZ TEKNIK â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        # â”€â”€ CIHAZ TEKNIK BELGE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        # â”€â”€ CIHAZ BELGELER (Merkezi Belgeler) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        # â”€â”€ ORTAK DOKÃœMANLAR (TÃ¼m modÃ¼ller) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        # â”€â”€ CIHAZ ARIZA â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        # â”€â”€ ARIZA ISLEM â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        # â”€â”€ PERIYODIK BAKIM â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        # â”€â”€ KALIBRASYON â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        # â”€â”€ SABITLER â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        # â”€â”€ TATILLER â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Tatiller (
            Tarih       TEXT PRIMARY KEY,
            ResmiTatil  TEXT,

            sync_status TEXT DEFAULT 'clean',
            updated_at  TEXT
        )
        """)

        # â”€â”€ LOGLAR â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        # â”€â”€ RKE LIST â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        # â”€â”€ RKE MUAYENE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        # â”€â”€ PERSONEL SAGLIK TAKIP â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        # Auth/RBAC tablolarÄ±
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
            ("admin.panel", "Admin panel eriÅŸimi"),
            ("admin.logs.view", "Log gÃ¶rÃ¼ntÃ¼leme"),
            ("admin.backup", "Yedek yÃ¶netimi"),
            ("admin.settings", "Ayarlar yÃ¶netimi"),
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
        Sabitler tablosuna baÅŸlangÄ±Ã§ / sistem verilerini ekler.
        YalnÄ±zca yeni kurulumda Ã§aÄŸrÄ±lÄ±r; mevcut kayÄ±tlarÄ±n Ã¼zerine yazmaz.
        """
        belge_turleri = [
            ("1",   "Cihaz_Belge_Tur",   "NDK LisansÄ±",         "CihazÄ±n NDK (Uygunluk BeyanÄ±) LisansÄ±"),
            ("2",   "Cihaz_Belge_Tur",   "RKS Belgesi",          "CihazÄ±n RKS (Radyasyon Koruma) Belgesi"),
            ("3",   "Cihaz_Belge_Tur",   "Sorumlu DiplomasÄ±",    "Sorumlu kiÅŸinin diplomasÄ±"),
            ("4",   "Cihaz_Belge_Tur",   "KullanÄ±m Klavuzu",     "Cihaz kullanÄ±m kÄ±lavuzu"),
            ("5",   "Cihaz_Belge_Tur",   "Cihaz SertifikasÄ±",    "Cihaz sertifikasÄ±/belgelendirmesi"),
            ("6",   "Cihaz_Belge_Tur",   "Teknik Veri SayfasÄ±",  "CihazÄ±n teknik Ã¶zellikleri"),
            ("7",   "Cihaz_Belge_Tur",   "GarantÄ± Belgesi",      "Cihaz garanti belgesi"),

            ("101", "Personel_Belge_Tur", "Diploma",             "Personel diplomasÄ±"),
            ("102", "Personel_Belge_Tur", "Sertifika",           "Personel sertifikasÄ±"),
            ("103", "Personel_Belge_Tur", "Ehliyet",             "Personel ehliyet belgesi"),
            ("104", "Personel_Belge_Tur", "Kimlik",              "Personel kimlik belgesi"),
            ("105", "Personel_Belge_Tur", "DiÄŸer",               "Personel diÄŸer belgeler"),
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

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # ACÄ°L RESET (yalnÄ±zca manuel Ã§aÄŸrÄ±)
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def reset_database(self):
        """
        âš ï¸  ACÄ°L DURUM: TÃ¼m tablolarÄ± sil ve yeniden oluÅŸtur.

        Ciddi veri bozulmasÄ± durumunda manuel olarak Ã§aÄŸrÄ±lmalÄ±dÄ±r.
        Normal kullanÄ±mda run_migrations() tercih edilmelidir.
        """
        logger.warning("âš ï¸  VERÄ°TABANI TAM RESET YAPILIYOR â€” TÃœM VERÄ° SÄ°LÄ°NECEK!")

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

        logger.info(f"âœ“ TÃ¼m tablolar yeniden oluÅŸturuldu (v{self.CURRENT_VERSION})")


# database/migrations.py
# ─────────────────────────────────────────────────────────────────────────────
#  REPYS — Versiyon Tabanlı Migration Yöneticisi
#
#  Tasarım kararları:
#    · CURRENT_VERSION = 1  — v1-v7 arası tüm şema bu dosyaya squash edildi.
#    · Mevcut kurulumlar (schema_version MAX >= 1) hiçbir işlem yapılmadan geçer.
#    · Yeni kurulumlar: v0 → v1 tek adımda (create_tables + seed).
#    · Gelecek değişiklik için _migrate_to_v2() ekle, CURRENT_VERSION = 2 yap.
#    · PRAGMA foreign_keys = ON her bağlantıda zorunlu olarak etkinleştirilir.
# ─────────────────────────────────────────────────────────────────────────────
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

from core.logger import logger


class MigrationManager:
    """
    Versiyon tabanlı migration yöneticisi.

    v1: Tüm tablolar — eski v1-v7 squash edildi, temiz kurulum şeması.

    Yeni migration eklemek için:
        1. _migrate_to_vN() metodunu yaz.
        2. CURRENT_VERSION = N yap.
        3. Metod imzası: def _migrate_to_vN(self) → None
    """

    CURRENT_VERSION = 1

    def __init__(self, db_path: str) -> None:
        self.db_path   = db_path
        self.backup_dir = Path(db_path).parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)

    # ══════════════════════════════════════════════════════════════════════════
    #  BAĞLANTI
    # ══════════════════════════════════════════════════════════════════════════

    def connect(self) -> sqlite3.Connection:
        """FK kısıtlaması ve WAL modu etkin bağlantı döndürür."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")   # ← SQLite varsayılanı OFF'dur
        return conn

    # ══════════════════════════════════════════════════════════════════════════
    #  ŞEMA VERSİYONU
    # ══════════════════════════════════════════════════════════════════════════

    def get_schema_version(self) -> int:
        conn = self.connect()
        cur  = conn.cursor()
        try:
            cur.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='schema_version'"
            )
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
            row = cur.fetchone()
            return row[0] if row[0] is not None else 0
        finally:
            conn.close()

    def _set_schema_version(self, conn: sqlite3.Connection,
                            version: int, description: str = "") -> None:
        conn.execute(
            "INSERT INTO schema_version (version, applied_at, description) "
            "VALUES (?, ?, ?)",
            (version, datetime.now().isoformat(), description),
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  YEDEKLEME
    # ══════════════════════════════════════════════════════════════════════════

    def backup_database(self) -> Path | None:
        if not Path(self.db_path).exists():
            return None
        ts          = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"db_backup_{ts}.db"
        try:
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Yedek alındı: {backup_path}")
            self._cleanup_old_backups()
            return backup_path
        except Exception as e:
            logger.error(f"Yedekleme hatası: {e}")
            return None

    def _cleanup_old_backups(self, keep: int = 10) -> None:
        backups = sorted(self.backup_dir.glob("db_backup_*.db"))
        for old in backups[:-keep]:
            try:
                old.unlink()
            except Exception as e:
                logger.warning(f"Eski yedek silinemedi: {old} ({e})")

    # ══════════════════════════════════════════════════════════════════════════
    #  MIGRATION ÇALIŞTIRICI
    # ══════════════════════════════════════════════════════════════════════════

    def run_migrations(self) -> bool:
        current = self.get_schema_version()

        if current >= self.CURRENT_VERSION:
            logger.info(f"Şema güncel (v{current})")
            return True

        backup_path = self.backup_database()
        logger.info(f"Migration başlıyor: v{current} → v{self.CURRENT_VERSION}")

        try:
            for v in range(current + 1, self.CURRENT_VERSION + 1):
                method = getattr(self, f"_migrate_to_v{v}", None)
                if method:
                    logger.info(f"  v{v} uygulanıyor…")
                    method()
                else:
                    logger.info(f"  v{v} no-op (metod yok)")
            logger.info("Tüm migration'lar tamamlandı")
            return True
        except Exception as e:
            logger.error(f"Migration hatası: {e} | Yedek: {backup_path}")
            raise

    # ══════════════════════════════════════════════════════════════════════════
    #  V1 — TEMİZ KURULUM  (eski v1-v7 squash)
    # ══════════════════════════════════════════════════════════════════════════

    def _migrate_to_v1(self) -> None:
        """
        v1: Tüm tablolar sıfırdan oluşturulur, temel veriler eklenir.

        Önceki sürümlerde ayrı migration'larla eklenen kolonlar
        (v3: FmMaxSaat, v5: MaxGunlukSureDakika, v6: HaftasonuCalismaVar /
         ResmiTatilCalismaVar / DiniBayramCalismaVar, v7: ArdisikGunIzinli)
        ve tablolar (v4: NB_HazirlikOnay) bu CREATE TABLE bloklarına dahildir.
        """
        conn = self.connect()
        try:
            cur = conn.cursor()
            self._create_all_tables(cur)
            self._seed_initial_data(cur)
            self._seed_auth_data(cur)
            self._set_schema_version(conn, 1, "Temiz kurulum (squash v1-v7)")
            conn.commit()
            logger.info("v1: Tüm tablolar oluşturuldu")
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ══════════════════════════════════════════════════════════════════════════
    #  TABLO OLUŞTURMA — TEK GİRİŞ NOKTASI
    # ══════════════════════════════════════════════════════════════════════════

    def _create_all_tables(self, cur: sqlite3.Cursor) -> None:
        """Tüm tabloları oluşturur. İdempotent — varsa atlar."""
        self._create_core_tables(cur)
        self._create_auth_tables(cur)
        self._create_nb_tables(cur)

    # ──────────────────────────────────────────────────────────────────────────
    #  CORE TABLOLAR
    # ──────────────────────────────────────────────────────────────────────────

    def _create_core_tables(self, cur: sqlite3.Cursor) -> None:

        cur.execute("""
        CREATE TABLE IF NOT EXISTS Personel (
            KimlikNo                TEXT PRIMARY KEY,
            AdSoyad                 TEXT,
            DogumYeri               TEXT,
            DogumTarihi             TEXT,
            HizmetSinifi            TEXT,
            KadroUnvani             TEXT,
            GorevYeri               TEXT,
            KurumSicilNo            TEXT,
            MemuriyeteBaslamaTarihi TEXT,
            CepTelefonu             TEXT,
            Eposta                  TEXT,
            MezunOlunanOkul         TEXT,
            MezunOlunanFakulte      TEXT,
            MezuniyetTarihi         TEXT,
            DiplomaNo               TEXT,
            MezunOlunanOkul2        TEXT,
            MezunOlunanFakulte2     TEXT,
            MezuniyetTarihi2        TEXT,
            DiplomaNo2              TEXT,
            Resim                   TEXT,
            Diploma1                TEXT,
            Diploma2                TEXT,
            OzlukDosyasi            TEXT,
            Durum                   TEXT,
            AyrilisTarihi           TEXT,
            AyrilmaNedeni           TEXT,
            MuayeneTarihi           TEXT,
            Sonuc                   TEXT,
            sync_status             TEXT DEFAULT 'clean',
            updated_at              TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS Izin_Giris (
            Izinid        TEXT PRIMARY KEY,
            HizmetSinifi  TEXT,
            Personelid    TEXT REFERENCES Personel(KimlikNo),
            AdSoyad       TEXT,
            IzinTipi      TEXT,
            BaslamaTarihi TEXT,
            Gun           INTEGER,
            BitisTarihi   TEXT,
            Durum         TEXT,
            sync_status   TEXT DEFAULT 'clean',
            updated_at    TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS Izin_Bilgi (
            TCKimlik             TEXT PRIMARY KEY REFERENCES Personel(KimlikNo),
            AdSoyad              TEXT,
            YillikDevir          REAL,
            YillikHakedis        REAL,
            YillikToplamHak      REAL,
            YillikKullanilan     REAL,
            YillikKalan          REAL,
            SuaKullanilabilirHak REAL,
            SuaKullanilan        REAL,
            SuaKalan             REAL,
            SuaCariYilKazanim    REAL,
            RaporMazeretTop      REAL,
            sync_status          TEXT DEFAULT 'clean',
            updated_at           TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS FHSZ_Puantaj (
            Personelid       TEXT    NOT NULL REFERENCES Personel(KimlikNo),
            AdSoyad          TEXT,
            Birim            TEXT,
            CalismaKosulu    TEXT,
            AitYil           INTEGER NOT NULL,
            Donem            TEXT    NOT NULL,
            AylikGun         INTEGER,
            KullanilanIzin   INTEGER,
            FiiliCalismaSaat REAL,
            sync_status      TEXT DEFAULT 'clean',
            updated_at       TEXT,
            PRIMARY KEY (Personelid, AitYil, Donem)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS Cihazlar (
            Cihazid              TEXT PRIMARY KEY,
            CihazTipi            TEXT,
            Marka                TEXT,
            Model                TEXT,
            Amac                 TEXT,
            Kaynak               TEXT,
            SeriNo               TEXT,
            NDKSeriNo            TEXT,
            HizmeteGirisTarihi   TEXT,
            RKS                  TEXT,
            Sorumlusu            TEXT,
            Gorevi               TEXT,
            NDKLisansNo          TEXT,
            BaslamaTarihi        TEXT,
            BitisTarihi          TEXT,
            LisansDurum          TEXT,
            AnaBilimDali         TEXT,
            Birim                TEXT,
            BulunduguBina        TEXT,
            GarantiDurumu        TEXT,
            GarantiBitisTarihi   TEXT,
            DemirbasNo           TEXT,
            KalibrasyonGereklimi TEXT,
            BakimDurum           TEXT,
            Durum                TEXT,
            Img                  TEXT,
            NDKLisansBelgesi     TEXT,
            sync_status          TEXT DEFAULT 'clean',
            updated_at           TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS Dokumanlar (
            EntityType        TEXT NOT NULL,
            EntityId          TEXT NOT NULL,
            BelgeTuru         TEXT NOT NULL,
            Belge             TEXT NOT NULL,
            DokumanId         TEXT,
            DocType           TEXT,
            DisplayName       TEXT,
            LocalPath         TEXT,
            BelgeAciklama     TEXT,
            YuklenmeTarihi    TEXT,
            DrivePath         TEXT,
            IliskiliBelgeID   TEXT,
            IliskiliBelgeTipi TEXT,
            sync_status       TEXT DEFAULT 'clean',
            updated_at        TEXT,
            PRIMARY KEY (EntityType, EntityId, BelgeTuru, Belge)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS Cihaz_Ariza (
            Arizaid         TEXT PRIMARY KEY,
            Cihazid         TEXT REFERENCES Cihazlar(Cihazid),
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

        cur.execute("""
        CREATE TABLE IF NOT EXISTS Ariza_Islem (
            Islemid     TEXT PRIMARY KEY,
            Arizaid     TEXT REFERENCES Cihaz_Ariza(Arizaid),
            Tarih       TEXT,
            Saat        TEXT,
            IslemYapan  TEXT,
            IslemTuru   TEXT,
            YapilanIslem TEXT,
            YeniDurum   TEXT,
            Rapor       TEXT,
            sync_status TEXT DEFAULT 'clean',
            updated_at  TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS Periyodik_Bakim (
            Planid          TEXT PRIMARY KEY,
            Cihazid         TEXT REFERENCES Cihazlar(Cihazid),
            BakimPeriyodu   TEXT,
            BakimSirasi     INTEGER,
            PlanlananTarih  TEXT,
            Bakim           TEXT,
            Durum           TEXT,
            BakimTarihi     TEXT,
            BakimTipi       TEXT,
            YapilanIslemler TEXT,
            Aciklama        TEXT,
            Teknisyen       TEXT,
            Rapor           TEXT,
            SozlesmeId      TEXT,
            sync_status     TEXT DEFAULT 'clean',
            updated_at      TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS Kalibrasyon (
            Kalid        TEXT PRIMARY KEY,
            Cihazid      TEXT REFERENCES Cihazlar(Cihazid),
            Firma        TEXT,
            SertifikaNo  TEXT,
            YapilanTarih TEXT,
            Gecerlilik   TEXT,
            BitisTarihi  TEXT,
            Durum        TEXT,
            Dosya        TEXT,
            Aciklama     TEXT,
            sync_status  TEXT DEFAULT 'clean',
            updated_at   TEXT
        )
        """)

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

        cur.execute("""
        CREATE TABLE IF NOT EXISTS Tatiller (
            Tarih       TEXT PRIMARY KEY,
            ResmiTatil  TEXT,
            sync_status TEXT DEFAULT 'clean',
            updated_at  TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS Loglar (
            Tarih     TEXT,
            Saat      TEXT,
            Kullanici TEXT,
            Modul     TEXT,
            Islem     TEXT,
            Detay     TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS RKE_List (
            EkipmanNo        TEXT PRIMARY KEY,
            KoruyucuNumarasi TEXT,
            AnaBilimDali     TEXT,
            Birim            TEXT,
            KoruyucuCinsi    TEXT,
            KursunEsdegeri   TEXT,
            HizmetYili       INTEGER,
            Bedeni           TEXT,
            KontrolTarihi    TEXT,
            Durum            TEXT,
            Aciklama         TEXT,
            VarsaDemirbasNo  TEXT,
            KayitTarih       TEXT,
            Barkod           TEXT,
            sync_status      TEXT DEFAULT 'clean',
            updated_at       TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS RKE_Muayene (
            KayitNo              TEXT PRIMARY KEY,
            EkipmanNo            TEXT REFERENCES RKE_List(EkipmanNo),
            FMuayeneTarihi       TEXT,
            FizikselDurum        TEXT,
            SMuayeneTarihi       TEXT,
            SkopiDurum           TEXT,
            Aciklamalar          TEXT,
            KontrolEdenUnvani    TEXT,
            BirimSorumlusuUnvani TEXT,
            Notlar               TEXT,
            Rapor                TEXT,
            sync_status          TEXT DEFAULT 'clean',
            updated_at           TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS Personel_Saglik_Takip (
            KayitNo                  TEXT PRIMARY KEY,
            Personelid               TEXT REFERENCES Personel(KimlikNo),
            AdSoyad                  TEXT,
            Birim                    TEXT,
            Yil                      INTEGER,
            MuayeneTarihi            TEXT,
            SonrakiKontrolTarihi     TEXT,
            Sonuc                    TEXT,
            Durum                    TEXT,
            RaporDosya               TEXT,
            Notlar                   TEXT,
            DermatolojiMuayeneTarihi TEXT,
            DermatolojiDurum         TEXT,
            DahiliyeMuayeneTarihi    TEXT,
            DahiliyeDurum            TEXT,
            GozMuayeneTarihi         TEXT,
            GozDurum                 TEXT,
            GoruntulemeMuayeneTarihi TEXT,
            GoruntulemeDurum         TEXT,
            sync_status              TEXT DEFAULT 'clean',
            updated_at               TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS Dozimetre_Olcum (
            KayitNo         TEXT PRIMARY KEY,
            RaporNo         TEXT,
            Periyot         INTEGER,
            PeriyotAdi      TEXT,
            Yil             INTEGER,
            DozimetriTipi   TEXT,
            AdSoyad         TEXT,
            CalistiBirim    TEXT,
            PersonelID      TEXT REFERENCES Personel(KimlikNo),
            DozimetreNo     TEXT,
            VucutBolgesi    TEXT,
            Hp10            REAL,
            Hp007           REAL,
            Durum           TEXT,
            OlusturmaTarihi TEXT DEFAULT (date('now')),
            sync_status     TEXT DEFAULT 'clean',
            updated_at      TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS Dis_Alan_Calisma (
            TCKimlik          TEXT    NOT NULL DEFAULT '',
            AdSoyad           TEXT    NOT NULL,
            DonemAy           INTEGER NOT NULL CHECK (DonemAy BETWEEN 1 AND 12),
            DonemYil          INTEGER NOT NULL CHECK (DonemYil > 2000),
            AnaBilimDali      TEXT    NOT NULL DEFAULT '',
            Birim             TEXT    NOT NULL DEFAULT '',
            IslemTipi         TEXT    NOT NULL,
            Katsayi           REAL    NOT NULL,
            VakaSayisi        INTEGER NOT NULL CHECK (VakaSayisi > 0),
            HesaplananSaat    REAL    NOT NULL,
            TutanakNo         TEXT    NOT NULL,
            TutanakTarihi     TEXT    NOT NULL,
            KayitTarihi       TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
            KaydedenKullanici TEXT,
            PRIMARY KEY (TCKimlik, DonemAy, DonemYil, TutanakNo)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS Dis_Alan_Izin_Ozet (
            TCKimlik        TEXT    NOT NULL DEFAULT '',
            AdSoyad         TEXT    NOT NULL,
            DonemAy         INTEGER NOT NULL CHECK (DonemAy BETWEEN 1 AND 12),
            DonemYil        INTEGER NOT NULL CHECK (DonemYil > 2000),
            ToplamSaat      REAL    NOT NULL DEFAULT 0.0,
            IzinGunHakki    REAL    NOT NULL DEFAULT 0.0,
            HesaplamaTarihi TEXT,
            RksOnay         INTEGER NOT NULL DEFAULT 0 CHECK (RksOnay IN (0,1)),
            Notlar          TEXT,
            PRIMARY KEY (TCKimlik, AdSoyad, DonemAy, DonemYil)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS Dis_Alan_Katsayi_Protokol (
            AnaBilimDali        TEXT NOT NULL,
            Birim               TEXT NOT NULL,
            GecerlilikBaslangic TEXT NOT NULL,
            Katsayi             REAL NOT NULL,
            OrtSureDk           INTEGER,
            AlanTipAciklama     TEXT,
            AciklamaFormul      TEXT,
            ProtokolRef         TEXT,
            GecerlilikBitis     TEXT,
            Aktif               INTEGER NOT NULL DEFAULT 1 CHECK (Aktif IN (0,1)),
            KayitTarihi         TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
            KaydedenKullanici   TEXT,
            PRIMARY KEY (AnaBilimDali, Birim, GecerlilikBaslangic)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS Cihaz_Teknik (
            Cihazid                      TEXT PRIMARY KEY REFERENCES Cihazlar(Cihazid),
            BirincilUrunNumarasi         TEXT,
            KurumUnvan                   TEXT,
            MarkaAdi                     TEXT,
            EtiketAdi                    TEXT,
            VersiyonModel                TEXT,
            UrunTipi                     TEXT,
            Sinif                        TEXT,
            KatalogNo                    TEXT,
            GmdnTerimKod                 TEXT,
            GmdnTerimTurkceAd            TEXT,
            TemelUdiDi                   TEXT,
            UrunTanimi                   TEXT,
            Aciklama                     TEXT,
            KurumGorunenAd               TEXT,
            KurumNo                      TEXT,
            KurumTelefon                 TEXT,
            KurumEposta                  TEXT,
            IthalImalBilgisi             TEXT,
            MenseiUlkeSet                TEXT,
            IthalEdilenUlkeSet           TEXT,
            SutEslesmesiSet              TEXT,
            Durum                        TEXT,
            CihazKayitTipi               TEXT,
            UtsBaslangicTarihi           TEXT,
            KontroleGonderildigiTarih    TEXT,
            KalibrasyonaTabiMi           TEXT,
            KalibrasyonPeriyodu          TEXT,
            BakimaTabiMi                 TEXT,
            BakimPeriyodu                TEXT,
            MrgUyumlu                    TEXT,
            IyonizeRadyasyonIcerir       TEXT,
            TekHastayaKullanilabilir     TEXT,
            SinirliKullanimSayisiVar     TEXT,
            SinirliKullanimSayisi        TEXT,
            BaskaImalatciyaUrettirildiMi TEXT,
            GmdnTerimTurkceAciklama      TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS Cihaz_Teknik_Belge (
            Cihazid        TEXT NOT NULL REFERENCES Cihazlar(Cihazid),
            BelgeTuru      TEXT NOT NULL,
            Belge          TEXT NOT NULL,
            BelgeAdi       TEXT,
            YuklenmeTarihi TEXT,
            DrivePath      TEXT,
            LocalPath      TEXT,
            PRIMARY KEY (Cihazid, BelgeTuru, Belge)
        )
        """)

    # ──────────────────────────────────────────────────────────────────────────
    #  AUTH TABLOLAR
    # ──────────────────────────────────────────────────────────────────────────

    def _create_auth_tables(self, cur: sqlite3.Cursor) -> None:

        cur.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            UserId             INTEGER PRIMARY KEY AUTOINCREMENT,
            Username           TEXT    UNIQUE NOT NULL,
            PasswordHash       TEXT    NOT NULL,
            IsActive           INTEGER NOT NULL DEFAULT 1,
            MustChangePassword INTEGER NOT NULL DEFAULT 0,
            CreatedAt          TEXT    NOT NULL,
            LastLoginAt        TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS Roles (
            RoleId   INTEGER PRIMARY KEY AUTOINCREMENT,
            RoleName TEXT UNIQUE NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS Permissions (
            PermissionId  INTEGER PRIMARY KEY AUTOINCREMENT,
            PermissionKey TEXT UNIQUE NOT NULL,
            Description   TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS UserRoles (
            UserId INTEGER NOT NULL REFERENCES Users(UserId),
            RoleId INTEGER NOT NULL REFERENCES Roles(RoleId),
            PRIMARY KEY (UserId, RoleId)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS RolePermissions (
            RoleId       INTEGER NOT NULL REFERENCES Roles(RoleId),
            PermissionId INTEGER NOT NULL REFERENCES Permissions(PermissionId),
            PRIMARY KEY (RoleId, PermissionId)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS AuthAudit (
            AuditId   INTEGER PRIMARY KEY AUTOINCREMENT,
            Username  TEXT,
            Success   INTEGER NOT NULL,
            Reason    TEXT,
            CreatedAt TEXT NOT NULL
        )
        """)

    # ──────────────────────────────────────────────────────────────────────────
    #  NÖBET MODÜLÜ TABLOLAR  (eski v2-v7 squash)
    # ──────────────────────────────────────────────────────────────────────────

    def _create_nb_tables(self, cur: sqlite3.Cursor) -> None:
        """
        NB_ (New Build) nöbet modülü tabloları.
        Tüm kolonlar (v3-v7 eklentileri dahil) bu tanımda mevcut.
        """

        cur.execute("""
        CREATE TABLE IF NOT EXISTS NB_Birim (
            BirimID    TEXT PRIMARY KEY,
            BirimKodu  TEXT NOT NULL UNIQUE,
            BirimAdi   TEXT NOT NULL,
            BirimTipi  TEXT NOT NULL DEFAULT 'radyoloji',
            UstBirimID TEXT REFERENCES NB_Birim(BirimID),
            Aktif      INTEGER NOT NULL DEFAULT 1,
            Sira       INTEGER NOT NULL DEFAULT 99,
            Aciklama   TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT,
            created_by TEXT,
            is_deleted INTEGER NOT NULL DEFAULT 0
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS NB_BirimAyar (
            AyarID                TEXT    PRIMARY KEY,
            BirimID               TEXT    NOT NULL REFERENCES NB_Birim(BirimID),
            GunlukSlotSayisi      INTEGER NOT NULL DEFAULT 4,
            GunlukSlotDakika      INTEGER,
            CalismaModu           TEXT    NOT NULL DEFAULT 'tam_gun',
            OtomatikBolunme       INTEGER NOT NULL DEFAULT 1,
            GunlukHedefDakika     INTEGER NOT NULL DEFAULT 420,
            HaftasonuNobetZorunlu INTEGER NOT NULL DEFAULT 1,
            DiniBayramAtama       INTEGER NOT NULL DEFAULT 0,
            -- v6: birim bazlı çalışma günü anahtarları
            HaftasonuCalismaVar   INTEGER NOT NULL DEFAULT 1,
            ResmiTatilCalismaVar  INTEGER NOT NULL DEFAULT 1,
            DiniBayramCalismaVar  INTEGER NOT NULL DEFAULT 0,
            -- v7: ardışık gün toleransı
            ArdisikGunIzinli      INTEGER NOT NULL DEFAULT 0,
            -- v3: FM gönüllü aylık max saat
            FmMaxSaat             INTEGER NOT NULL DEFAULT 60,
            -- v5: birim bazlı günlük max nöbet süresi
            MaxGunlukSureDakika   INTEGER NOT NULL DEFAULT 720,
            GeserlilikBaslangic   TEXT,
            GeserlilikBitis       TEXT,
            created_at            TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at            TEXT,
            UNIQUE (BirimID, GeserlilikBaslangic)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS NB_VardiyaGrubu (
            GrupID   TEXT PRIMARY KEY,
            BirimID  TEXT NOT NULL REFERENCES NB_Birim(BirimID),
            GrupAdi  TEXT NOT NULL,
            GrupTuru TEXT NOT NULL DEFAULT 'zorunlu',
            Sira     INTEGER NOT NULL DEFAULT 1,
            Aktif    INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT,
            UNIQUE (BirimID, GrupAdi)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS NB_Vardiya (
            VardiyaID           TEXT PRIMARY KEY,
            GrupID              TEXT NOT NULL REFERENCES NB_VardiyaGrubu(GrupID),
            BirimID             TEXT NOT NULL REFERENCES NB_Birim(BirimID),
            VardiyaAdi          TEXT NOT NULL,
            BasSaat             TEXT NOT NULL,
            BitSaat             TEXT NOT NULL,
            SureDakika          INTEGER NOT NULL,
            Rol                 TEXT NOT NULL DEFAULT 'ana',
            MinPersonel         INTEGER NOT NULL DEFAULT 1,
            Sira                INTEGER NOT NULL DEFAULT 1,
            GeserlilikBaslangic TEXT,
            GeserlilikBitis     TEXT,
            Aktif               INTEGER NOT NULL DEFAULT 1,
            created_at          TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at          TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS NB_PersonelTercih (
            TercihID          TEXT PRIMARY KEY,
            PersonelID        TEXT NOT NULL REFERENCES Personel(KimlikNo),
            BirimID           TEXT NOT NULL REFERENCES NB_Birim(BirimID),
            Yil               INTEGER NOT NULL,
            Ay                INTEGER NOT NULL CHECK (Ay BETWEEN 1 AND 12),
            NobetTercihi      TEXT NOT NULL DEFAULT 'zorunlu',
            HedefDakika       INTEGER,
            HedefTipi         TEXT NOT NULL DEFAULT 'normal',
            MaxNobetGun       INTEGER,
            TercihVardiyalar  TEXT,
            KacinilacakGunler TEXT,
            Notlar            TEXT,
            Durum             TEXT NOT NULL DEFAULT 'taslak',
            OnaylayanID       TEXT,
            OnayTarihi        TEXT,
            created_at        TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at        TEXT,
            UNIQUE (PersonelID, BirimID, Yil, Ay)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS NB_Plan (
            PlanID                 TEXT PRIMARY KEY,
            BirimID                TEXT    NOT NULL REFERENCES NB_Birim(BirimID),
            Yil                    INTEGER NOT NULL,
            Ay                     INTEGER NOT NULL CHECK (Ay BETWEEN 1 AND 12),
            Versiyon               INTEGER NOT NULL DEFAULT 1,
            Durum                  TEXT    NOT NULL DEFAULT 'taslak',
            AlgoritmaVersiyon      TEXT,
            OlusturmaParametreleri TEXT,
            Notlar                 TEXT,
            OnaylayanID            TEXT,
            OnayTarihi             TEXT,
            created_at             TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at             TEXT,
            created_by             TEXT,
            UNIQUE (BirimID, Yil, Ay, Versiyon)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS NB_PlanSatir (
            SatirID       TEXT PRIMARY KEY,
            PlanID        TEXT NOT NULL REFERENCES NB_Plan(PlanID),
            PersonelID    TEXT NOT NULL REFERENCES Personel(KimlikNo),
            VardiyaID     TEXT NOT NULL REFERENCES NB_Vardiya(VardiyaID),
            NobetTarihi   TEXT NOT NULL,
            Kaynak        TEXT NOT NULL DEFAULT 'algoritma',
            NobetTuru     TEXT NOT NULL DEFAULT 'normal',
            Durum         TEXT NOT NULL DEFAULT 'aktif',
            OncekiSatirID TEXT REFERENCES NB_PlanSatir(SatirID),
            Notlar        TEXT,
            created_at    TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at    TEXT,
            created_by    TEXT
        )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_nb_satir_tarih    ON NB_PlanSatir(NobetTarihi)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_nb_satir_personel ON NB_PlanSatir(PersonelID)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_nb_satir_plan     ON NB_PlanSatir(PlanID)")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS NB_MesaiHesap (
            HesapID           TEXT PRIMARY KEY,
            PersonelID        TEXT    NOT NULL REFERENCES Personel(KimlikNo),
            BirimID           TEXT    NOT NULL REFERENCES NB_Birim(BirimID),
            PlanID            TEXT    NOT NULL REFERENCES NB_Plan(PlanID),
            Yil               INTEGER NOT NULL,
            Ay                INTEGER NOT NULL CHECK (Ay BETWEEN 1 AND 12),
            CalisDakika       INTEGER NOT NULL DEFAULT 0,
            HedefDakika       INTEGER NOT NULL DEFAULT 0,
            FazlaDakika       INTEGER NOT NULL DEFAULT 0,
            DevirDakika       INTEGER NOT NULL DEFAULT 0,
            ToplamFazlaDakika INTEGER NOT NULL DEFAULT 0,
            OdenenDakika      INTEGER NOT NULL DEFAULT 0,
            DevireGidenDakika INTEGER NOT NULL DEFAULT 0,
            HesapDurumu       TEXT    NOT NULL DEFAULT 'taslak',
            HesapTarihi       TEXT,
            created_at        TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at        TEXT,
            UNIQUE (PersonelID, BirimID, Yil, Ay, PlanID)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS NB_MesaiKural (
            KuralID             TEXT PRIMARY KEY,
            KuralAdi            TEXT NOT NULL,
            KuralTuru           TEXT NOT NULL,
            Parametre           TEXT NOT NULL DEFAULT '{}',
            GeserlilikBaslangic TEXT NOT NULL,
            GeserlilikBitis     TEXT,
            Aciklama            TEXT,
            created_at          TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at          TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS NB_BirimPersonel (
            ID             TEXT PRIMARY KEY,
            BirimID        TEXT    NOT NULL REFERENCES NB_Birim(BirimID),
            PersonelID     TEXT    NOT NULL REFERENCES Personel(KimlikNo),
            Rol            TEXT    NOT NULL DEFAULT 'teknisyen',
            GorevBaslangic TEXT    NOT NULL,
            GorevBitis     TEXT,
            AnabirimMi     INTEGER NOT NULL DEFAULT 1,
            Aktif          INTEGER NOT NULL DEFAULT 1,
            Notlar         TEXT,
            created_at     TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at     TEXT,
            UNIQUE (BirimID, PersonelID, GorevBaslangic)
        )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_nb_birimper_personel ON NB_BirimPersonel(PersonelID)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_nb_birimper_birim    ON NB_BirimPersonel(BirimID)")

        # v4: Nöbet hazırlık onayı (plan başlamadan önce)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS NB_HazirlikOnay (
            OnayID     TEXT PRIMARY KEY,
            BirimID    TEXT    NOT NULL REFERENCES NB_Birim(BirimID),
            Yil        INTEGER NOT NULL,
            Ay         INTEGER NOT NULL CHECK (Ay BETWEEN 1 AND 12),
            Durum      TEXT    NOT NULL DEFAULT 'onaylandi',
            OnayTarihi TEXT    NOT NULL,
            Notlar     TEXT,
            created_at TEXT    NOT NULL DEFAULT (datetime('now')),
            UNIQUE (BirimID, Yil, Ay)
        )
        """)

    # ══════════════════════════════════════════════════════════════════════════
    #  SEED VERİLERİ
    # ══════════════════════════════════════════════════════════════════════════

    def _seed_initial_data(self, cur: sqlite3.Cursor) -> None:
        """Sabitler ve Tatiller başlangıç verilerini ekler. İdempotent."""

        sistem_sabitler = [
            ("1",   "Izin_Tipi", "Aylıksız İzin - Askerlik Nedeniyle", ""),
            ("2",   "Izin_Tipi", "Aylıksız İzin - Doğum Nedeniyle", ""),
            ("3",   "Izin_Tipi", "Doğum İzni (Eşinin)", "10"),
            ("4",   "Izin_Tipi", "Doğum Öncesi İzin", "42"),
            ("5",   "Izin_Tipi", "Doğum Sonrası İzin", "42"),
            ("6",   "Izin_Tipi", "Evlenme-Ölüm İzni", ""),
            ("7",   "Izin_Tipi", "Evlilik İzni", ""),
            ("8",   "Izin_Tipi", "Heyet Raporu", ""),
            ("9",   "Izin_Tipi", "İdari İzin", ""),
            ("11",  "Izin_Tipi", "Kongre izni: 3 aya kadar", ""),
            ("12",  "Izin_Tipi", "Mazeret", ""),
            ("13",  "Izin_Tipi", "Rapor İzni", ""),
            ("14",  "Izin_Tipi", "Refakatçı İzni", ""),
            ("15",  "Izin_Tipi", "Şua İzni", "30"),
            ("16",  "Izin_Tipi", "Tedavi İzni (Yatış Ve Ayaktan)", ""),
            ("17",  "Izin_Tipi", "Yıllık İzin", "30"),
            ("18",  "Amac", "Defibrilator", ""),
            ("19",  "Amac", "EKG Cihazı", ""),
            ("20",  "Amac", "Grafi", ""),
            ("21",  "Amac", "Kaset Okuyucu", ""),
            ("22",  "Amac", "Manyetik Rezonans", ""),
            ("23",  "Amac", "Skopi", ""),
            ("24",  "Amac", "Skopi (Ercp)", ""),
            ("25",  "Amac", "Skopi (Eswl)", ""),
            ("26",  "Amac", "Ultrasonografi", ""),
            ("27",  "AnaBilimDali", "Beyin ve Sinir Cerrahisi ABD", "NRS"),
            ("32",  "AnaBilimDali", "Göğüs Hastalıkları ABD", "GHA"),
            ("33",  "AnaBilimDali", "İç Hastalıkları ABD", "DHL"),
            ("34",  "AnaBilimDali", "Kalp ve Damar Cerrahisi ABD", "KDC"),
            ("35",  "AnaBilimDali", "Kardiyoloji ABD", "KRD"),
            ("38",  "AnaBilimDali", "Ortopedi ve Travmatoloji ABD", "ORT"),
            ("39",  "AnaBilimDali", "Radyoloji ABD", "RAD"),
            ("40",  "AnaBilimDali", "Üroloji ABD", "URO"),
            ("41",  "Ariza_Durum", "İşlemde", ""),
            ("42",  "Ariza_Durum", "Parça Bekliyor", ""),
            ("43",  "Ariza_Durum", "Dış Serviste", ""),
            ("44",  "Ariza_Durum", "Kapalı (Çözüldü)", ""),
            ("45",  "Ariza_Durum", "Kapalı (İptal)", ""),
            ("46",  "Ariza_Islem_Turu", "Arıza Tespiti / İnceleme", ""),
            ("47",  "Ariza_Islem_Turu", "Onarım / Tamirat", ""),
            ("48",  "Ariza_Islem_Turu", "Parça Değişimi", ""),
            ("49",  "Ariza_Islem_Turu", "Yazılım Güncelleme", ""),
            ("50",  "Ariza_Islem_Turu", "Kalibrasyon", ""),
            ("51",  "Ariza_Islem_Turu", "Dış Servis Gönderimi", ""),
            ("52",  "Ariza_Islem_Turu", "Kapatma / Sonlandırma", ""),
            ("53",  "Bedeni", "L", ""),
            ("54",  "Bedeni", "M", ""),
            ("55",  "Bedeni", "Pediatrik", ""),
            ("56",  "Bedeni", "S", ""),
            ("57",  "Bedeni", "STN", ""),
            ("58",  "Bedeni", "XL", ""),
            ("59",  "Bedeni", "XS", ""),
            ("60",  "Bedeni", "Yetişkin", ""),
            ("61",  "Birim", "Acil Radyoloji", "ARAD"),
            ("63",  "Birim", "Ameliyathane", "AML"),
            ("64",  "Birim", "Anjiografi", "ANJ"),
            ("65",  "Birim", "Endoskopi Ünitesi", "ENU"),
            ("66",  "Birim", "Girişimsel Radyoloji Anjiografi", "RANJ"),
            ("67",  "Birim", "Koroner Anjiografi", "KANJ"),
            ("68",  "Birim", "Mamografi", "MAM"),
            ("69",  "Birim", "Manyetik Rezonans Ünitesi", "MRI"),
            ("70",  "Birim", "Nöroradyoloji Anjiografi", "NANJ"),
            ("71",  "Birim", "Poliklinik", "POL"),
            ("72",  "Birim", "Radyoloji USG", "USG"),
            ("73",  "Birim", "Yoğun Bakım Ünitesi", "YBU"),
            ("74",  "Cihaz_Belge_Tur", "NDK Lisansı", ""),
            ("75",  "Cihaz_Belge_Tur", "RKS Belgesi", ""),
            ("76",  "Cihaz_Belge_Tur", "Sorumlu Diploması", ""),
            ("77",  "Cihaz_Belge_Tur", "Kullanım Kılavuzu", ""),
            ("78",  "Cihaz_Belge_Tur", "Cihaz Sertifikası", ""),
            ("79",  "Cihaz_Belge_Tur", "Teknik Veri Sayfası", ""),
            ("80",  "Cihaz_Belge_Tur", "Garanti Belgesi", ""),
            ("80a", "Cihaz_Belge_Tur", "Diğer", ""),
            ("200", "Personel_Belge_Tur", "Diploma", ""),
            ("201", "Personel_Belge_Tur", "Sertifika", ""),
            ("202", "Personel_Belge_Tur", "Periyodik Muayene Raporu", ""),
            ("202a","Personel_Belge_Tur", "İşe Giriş Muayenesi", ""),
            ("203", "Personel_Belge_Tur", "Hastalık Raporu", ""),
            ("204", "Personel_Belge_Tur", "Dozimetre Sonuçları", ""),
            ("205", "Personel_Belge_Tur", "Diğer", ""),
            ("300", "RKE_Belge_Tur", "Muayene Raporu", ""),
            ("301", "RKE_Belge_Tur", "Kalibrasyon Sertifikası", ""),
            ("302", "RKE_Belge_Tur", "Teknik Doküman", ""),
            ("303", "RKE_Belge_Tur", "Diğer", ""),
            ("400", "Satin_Alma_Belge_Tur", "Teklif", ""),
            ("401", "Satin_Alma_Belge_Tur", "Sözleşme", ""),
            ("402", "Satin_Alma_Belge_Tur", "Fatura", ""),
            ("403", "Satin_Alma_Belge_Tur", "İrsaliye", ""),
            ("404", "Satin_Alma_Belge_Tur", "Şartname", ""),
            ("405", "Satin_Alma_Belge_Tur", "Diğer", ""),
            ("500", "Kurumsal_Belge_Tur", "Yönetmelik", ""),
            ("501", "Kurumsal_Belge_Tur", "Prosedür", ""),
            ("502", "Kurumsal_Belge_Tur", "Sözleşme", ""),
            ("503", "Kurumsal_Belge_Tur", "Akreditasyon Belgesi", ""),
            ("504", "Kurumsal_Belge_Tur", "Yazışma", ""),
            ("505", "Kurumsal_Belge_Tur", "Diğer", ""),
            ("81",  "Cihaz_Tipi", "Görüntüleme (Diğer)", "GOR"),
            ("82",  "Cihaz_Tipi", "Görüntüleme (Radyasyon Kaynaklı)", "XRY"),
            ("83",  "Cihaz_Tipi", "Medikal Cihazlar", "MED"),
            ("84",  "Gorev_Yeri", "Acil Radyoloji", "Çalışma Koşulu A"),
            ("85",  "Gorev_Yeri", "Esnaf Has. Yerleşkesi", "Çalışma Koşulu B"),
            ("86",  "Gorev_Yeri", "Girişimsel Radyoloji", "Çalışma Koşulu A"),
            ("87",  "Gorev_Yeri", "Gögüs Hastalıkları", "Çalışma Koşulu B"),
            ("99",  "Hizmet_Sinifi", "Akademik Personel", ""),
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
            ("153", "RKE_Teknik", "Dikiş yerlerinde hasar var", ""),
            ("154", "RKE_Teknik", "Kullanım Ömrünü Doldurmuş", ""),
            ("155", "RKE_Teknik", "Kullanım ve bakım koşullarına uyulmamış", ""),
            ("156", "RKE_Teknik", "Kurşun, etek kısımlarında toplanmış", ""),
            ("157", "RKE_Teknik", "Sabitleyici bantlar ve tokalar deforme", ""),
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
            ("172", "Sistem_DriveID", "Cihaz_Belgeler", ""),
            ("173", "Sistem_DriveID", "Personel_Belge", ""),
            ("174", "Sistem_DriveID", "RKE_Rapor", ""),
            ("175", "Sistem_DriveID", "Sozlesme", ""),
            ("176", "Sistem_DriveID", "Satin_Alma_Belge", ""),
            ("177", "Sistem_DriveID", "Kurumsal_Belge", ""),
        ]

        added = 0
        for rowid, kod, menu_eleman, aciklama in sistem_sabitler:
            cur.execute(
                "SELECT COUNT(*) FROM Sabitler WHERE Kod=? AND MenuEleman=?",
                (kod, menu_eleman),
            )
            if cur.fetchone()[0] == 0:
                cur.execute(
                    "INSERT INTO Sabitler (Rowid, Kod, MenuEleman, Aciklama) "
                    "VALUES (?, ?, ?, ?)",
                    (rowid, kod, menu_eleman, aciklama),
                )
                added += 1
        if added:
            logger.info(f"  Sabitler: {added} kayıt eklendi")

        tatiller = [
            ("2026-01-01", "Yılbaşı"),
            ("2026-04-23", "Ulusal Egemenlik ve Çocuk Bayramı"),
            ("2026-05-01", "Emek ve Dayanışma Günü"),
            ("2026-05-19", "Atatürk'ü Anma Gençlik ve Spor Bayramı"),
            ("2026-07-15", "Demokrasi ve Milli Birlik Günü"),
            ("2026-08-30", "Zafer Bayramı"),
            ("2026-10-28", "Cumhuriyet Bayramı Arifesi"),
            ("2026-10-29", "Cumhuriyet Bayramı"),
            ("2026-12-31", "Yılbaşı Gecesi"),
        ]
        added_t = 0
        for tarih, ad in tatiller:
            cur.execute("SELECT COUNT(*) FROM Tatiller WHERE Tarih=?", (tarih,))
            if cur.fetchone()[0] == 0:
                cur.execute(
                    "INSERT INTO Tatiller (Tarih, ResmiTatil) VALUES (?, ?)",
                    (tarih, ad),
                )
                added_t += 1
        if added_t:
            logger.info(f"  Tatiller: {added_t} kayıt eklendi")

    def _seed_auth_data(self, cur: sqlite3.Cursor) -> None:
        """RBAC rolleri, izinleri ve rol-izin eşlemlerini ekler. İdempotent."""
        from core.auth.permission_keys import PermissionKeys

        desc_map = {
            "personel.read":    "Personel okuma",
            "personel.write":   "Personel yazma",
            "cihaz.read":       "Cihaz okuma",
            "cihaz.write":      "Cihaz yazma",
            "admin.panel":      "Admin panel erişimi",
            "admin.critical":   "Kritik admin işlemleri",
            "dis_alan.read":    "Dış alan okuma",
            "dis_alan.write":   "Dış alan yazma",
            "rke.read":         "RKE okuma",
            "rke.write":        "RKE yazma",
            "saglik.read":      "Sağlık okuma",
            "saglik.write":     "Sağlık yazma",
            "dozimetre.read":   "Dozimetre okuma",
            "dozimetre.write":  "Dozimetre yazma",
            "fhsz.read":        "FHSZ okuma",
            "fhsz.write":       "FHSZ yazma",
            "dokuman.read":     "Doküman okuma",
            "dokuman.write":    "Doküman yazma",
            "rapor.excel":      "Rapor Excel",
            "rapor.pdf":        "Rapor PDF",
            "backup.create":    "Yedek oluşturma",
            "backup.restore":   "Yedek geri yükleme",
        }

        for key in PermissionKeys.all():
            cur.execute(
                "SELECT COUNT(*) FROM Permissions WHERE PermissionKey=?", (key,)
            )
            if cur.fetchone()[0] == 0:
                cur.execute(
                    "INSERT INTO Permissions (PermissionKey, Description) VALUES (?, ?)",
                    (key, desc_map.get(key, key)),
                )

        for role in ("admin", "operator", "viewer"):
            cur.execute("SELECT COUNT(*) FROM Roles WHERE RoleName=?", (role,))
            if cur.fetchone()[0] == 0:
                cur.execute("INSERT INTO Roles (RoleName) VALUES (?)", (role,))

        cur.execute("SELECT RoleId, RoleName FROM Roles")
        role_map = {row["RoleName"]: row["RoleId"] for row in cur.fetchall()}

        cur.execute("SELECT PermissionId, PermissionKey FROM Permissions")
        perm_map = {row["PermissionKey"]: row["PermissionId"] for row in cur.fetchall()}

        def _grant(role_name: str, keys: list[str]) -> None:
            rid = role_map.get(role_name)
            if not rid:
                return
            for key in keys:
                pid = perm_map.get(key)
                if not pid:
                    continue
                cur.execute(
                    "SELECT COUNT(*) FROM RolePermissions WHERE RoleId=? AND PermissionId=?",
                    (rid, pid),
                )
                if cur.fetchone()[0] == 0:
                    cur.execute(
                        "INSERT INTO RolePermissions (RoleId, PermissionId) VALUES (?, ?)",
                        (rid, pid),
                    )

        _grant("admin",    list(perm_map.keys()))
        _grant("operator", ["personel.read", "personel.write",
                             "cihaz.read",   "cihaz.write"])
        _grant("viewer",   ["personel.read", "cihaz.read"])

    # ══════════════════════════════════════════════════════════════════════════
    #  ACİL RESET  (geliştirme / test ortamı)
    # ══════════════════════════════════════════════════════════════════════════

    def reset_database(self) -> None:
        """Tüm tabloları siler ve v1 şemasını yeniden oluşturur."""
        logger.warning("VERİTABANI RESET — TÜM VERİ SİLİNECEK!")
        backup_path = self.backup_database()
        if backup_path:
            logger.info(f"Son yedek alındı: {backup_path}")

        conn = self.connect()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [r[0] for r in cur.fetchall()]
            for tbl in tables:
                cur.execute(f"DROP TABLE IF EXISTS {tbl}")
            self._create_all_tables(cur)
            self._seed_initial_data(cur)
            self._seed_auth_data(cur)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version    INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL,
                    description TEXT
                )
            """)
            self._set_schema_version(conn, self.CURRENT_VERSION, "Full reset")
            conn.commit()
            logger.info(f"Tüm tablolar yeniden oluşturuldu (v{self.CURRENT_VERSION})")
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

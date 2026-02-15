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
    - Otomatik şema versiyonlama
    - Güvenli migration adımları
    - Otomatik yedekleme
    - Rollback desteği
    - Veri kaybı olmadan şema güncellemeleri
    """
    
    # Mevcut şema versiyonu
    CURRENT_VERSION = 7
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.backup_dir = Path(db_path).parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)

    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_schema_version(self):
        """Mevcut şema versiyonunu döndürür."""
        conn = self.connect()
        cur = conn.cursor()
        
        try:
            # schema_version tablosu var mı kontrol et
            cur.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='schema_version'
            """)
            
            if not cur.fetchone():
                # Tablo yoksa oluştur
                cur.execute("""
                    CREATE TABLE schema_version (
                        version INTEGER PRIMARY KEY,
                        applied_at TEXT NOT NULL,
                        description TEXT
                    )
                """)
                conn.commit()
                return 0
            
            # En son versiyonu getir
            cur.execute("SELECT MAX(version) FROM schema_version")
            result = cur.fetchone()
            version = result[0] if result[0] is not None else 0
            
            return version
            
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
            
            # Eski yedekleri temizle (son 10 yedek hariç)
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

    def run_migrations(self):
        """
        Tüm bekleyen migration'ları çalıştırır.
        Veri kaybı olmadan şemayı günceller.
        """
        current_version = self.get_schema_version()
        
        if current_version == self.CURRENT_VERSION:
            logger.info(f"Şema güncel (v{current_version})")
            return True
        
        if current_version > self.CURRENT_VERSION:
            logger.warning(
                f"Şema versiyonu ({current_version}) koddan ({self.CURRENT_VERSION}) yüksek! "
                "Uygulama güncellemesi gerekebilir."
            )
            return False
        
        # Yedekleme yap
        backup_path = self.backup_database()
        if not backup_path:
            logger.warning("Yedekleme yapılamadı ama migration devam ediyor")
        
        logger.info(f"Migration başlıyor: v{current_version} → v{self.CURRENT_VERSION}")
        
        try:
            # Sırayla migration'ları çalıştır
            for version in range(current_version + 1, self.CURRENT_VERSION + 1):
                migration_method = getattr(self, f"_migrate_to_v{version}", None)
                
                if migration_method:
                    logger.info(f"Migration v{version} uygulanıyor...")
                    migration_method()
                    self.set_schema_version(version, f"Migrated to v{version}")
                else:
                    logger.warning(f"Migration v{version} metodu bulunamadı, atlanıyor")
            
            logger.info("✓ Tüm migration'lar başarıyla tamamlandı")
            return True
            
        except Exception as e:
            logger.error(f"Migration hatası: {e}")
            logger.error(f"Yedekten geri yükleme yapabilirsiniz: {backup_path}")
            raise

    # ════════════════════════════════════════════════
    # MIGRATION METODLARI
    # ════════════════════════════════════════════════

    def _migrate_to_v1(self):
        """
        v0 → v1: İlk şema oluşturma
        Tüm tabloları oluşturur.
        """
        conn = self.connect()
        cur = conn.cursor()
        
        try:
            self.create_tables(cur)
            conn.commit()
            logger.info("v1: Tüm tablolar oluşturuldu")
            
        finally:
            conn.close()

    def _migrate_to_v2(self):
        """
        v1 → v2: sync_status ve updated_at kolonları ekleme
        Mevcut tablolara eksik kolonları ekler.
        """
        conn = self.connect()
        cur = conn.cursor()
        
        try:
            tables_with_sync = [
                "Personel", "Izin_Giris", "Izin_Bilgi", "FHSZ_Puantaj",
                "Cihazlar", "Cihaz_Ariza", "Ariza_Islem", "Periyodik_Bakim",
                "Kalibrasyon", "Sabitler", "Tatiller", "RKE_List", "RKE_Muayene"
            ]
            
            for table in tables_with_sync:
                # Tablo var mı kontrol et
                cur.execute(f"""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='{table}'
                """)
                
                if not cur.fetchone():
                    logger.warning(f"Tablo bulunamadı: {table}, atlanıyor")
                    continue
                
                # Mevcut kolonları kontrol et
                cur.execute(f"PRAGMA table_info({table})")
                existing_columns = {row[1] for row in cur.fetchall()}
                
                # sync_status ekle
                if "sync_status" not in existing_columns:
                    cur.execute(f"""
                        ALTER TABLE {table} 
                        ADD COLUMN sync_status TEXT DEFAULT 'clean'
                    """)
                    logger.info(f"  {table}.sync_status eklendi")
                
                # updated_at ekle
                if "updated_at" not in existing_columns:
                    cur.execute(f"""
                        ALTER TABLE {table} 
                        ADD COLUMN updated_at TEXT
                    """)
                    logger.info(f"  {table}.updated_at eklendi")
            
            conn.commit()
            logger.info("v2: sync_status ve updated_at kolonları eklendi")
            
        finally:
            conn.close()

    def _migrate_to_v3(self):
        """
        v2 → v3: Personel_Saglik_Takip tablosu ekleme (MVP saglik takip).
        """
        conn = self.connect()
        cur = conn.cursor()

        try:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS Personel_Saglik_Takip (
                KayitNo TEXT PRIMARY KEY,
                Personelid TEXT,
                AdSoyad TEXT,
                Birim TEXT,
                Yil INTEGER,
                MuayeneTarihi TEXT,
                SonrakiKontrolTarihi TEXT,
                Sonuc TEXT,
                Durum TEXT,
                RaporDosya TEXT,
                Notlar TEXT,
                sync_status TEXT DEFAULT 'clean',
                updated_at TEXT
            )
            """)
            conn.commit()
            logger.info("v3: Personel_Saglik_Takip tablosu olusturuldu")
        finally:
            conn.close()

    def _migrate_to_v4(self):
        """
        v3 → v4: Personel_Saglik_Takip tablosuna sync kolonlari ekleme.
        """
        conn = self.connect()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='Personel_Saglik_Takip'
            """)
            if not cur.fetchone():
                logger.warning("Tablo bulunamadi: Personel_Saglik_Takip, v4 atlandi")
                conn.commit()
                return

            cur.execute("PRAGMA table_info(Personel_Saglik_Takip)")
            existing_columns = {row[1] for row in cur.fetchall()}

            if "sync_status" not in existing_columns:
                cur.execute("""
                    ALTER TABLE Personel_Saglik_Takip
                    ADD COLUMN sync_status TEXT DEFAULT 'clean'
                """)
                logger.info("  Personel_Saglik_Takip.sync_status eklendi")

            if "updated_at" not in existing_columns:
                cur.execute("""
                    ALTER TABLE Personel_Saglik_Takip
                    ADD COLUMN updated_at TEXT
                """)
                logger.info("  Personel_Saglik_Takip.updated_at eklendi")

            conn.commit()
            logger.info("v4: Personel_Saglik_Takip sync kolonlari hazir")
        finally:
            conn.close()

    def _migrate_to_v5(self):
        """
        v4 → v5: Personel_Saglik_Takip tablosuna 4 muayene alanlari ekleme.
        """
        conn = self.connect()
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='Personel_Saglik_Takip'
            """)
            if not cur.fetchone():
                logger.warning("Tablo bulunamadi: Personel_Saglik_Takip, v5 atlandi")
                conn.commit()
                return

            cur.execute("PRAGMA table_info(Personel_Saglik_Takip)")
            existing = {row[1] for row in cur.fetchall()}
            new_cols = [
                ("DermatolojiMuayeneTarihi", "TEXT"),
                ("DermatolojiDurum", "TEXT"),
                ("DermatolojiAciklama", "TEXT"),
                ("DahiliyeMuayeneTarihi", "TEXT"),
                ("DahiliyeDurum", "TEXT"),
                ("DahiliyeAciklama", "TEXT"),
                ("GozMuayeneTarihi", "TEXT"),
                ("GozDurum", "TEXT"),
                ("GozAciklama", "TEXT"),
                ("GoruntulemeMuayeneTarihi", "TEXT"),
                ("GoruntulemeDurum", "TEXT"),
                ("GoruntulemeAciklama", "TEXT"),
            ]
            for col_name, col_type in new_cols:
                if col_name not in existing:
                    cur.execute(f"ALTER TABLE Personel_Saglik_Takip ADD COLUMN {col_name} {col_type}")
                    logger.info(f"  Personel_Saglik_Takip.{col_name} eklendi")

            conn.commit()
            logger.info("v5: Personel_Saglik_Takip muayene alanlari hazir")
        finally:
            conn.close()

    def _migrate_to_v6(self):
        """
        v5 → v6: Personel_Saglik_Takip tablosundan
        DozimetreUygun/BelirtiVar/GozSevkGerekli kolonlarini kaldir.
        """
        conn = self.connect()
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='Personel_Saglik_Takip'
            """)
            if not cur.fetchone():
                logger.warning("Tablo bulunamadi: Personel_Saglik_Takip, v6 atlandi")
                conn.commit()
                return

            cur.execute("PRAGMA table_info(Personel_Saglik_Takip)")
            existing = {row[1] for row in cur.fetchall()}
            drop_cols = {"DozimetreUygun", "BelirtiVar", "GozSevkGerekli"}

            if not (existing & drop_cols):
                logger.info("v6: Kaldirilacak kolon yok, atlandi")
                conn.commit()
                return

            # SQLite'da güvenli kolon kaldırma için tabloyu yeniden oluştur.
            cur.execute("""
            CREATE TABLE IF NOT EXISTS Personel_Saglik_Takip_new (
                KayitNo TEXT PRIMARY KEY,
                Personelid TEXT,
                AdSoyad TEXT,
                Birim TEXT,
                Yil INTEGER,
                MuayeneTarihi TEXT,
                SonrakiKontrolTarihi TEXT,
                Sonuc TEXT,
                Durum TEXT,
                DermatolojiMuayeneTarihi TEXT,
                DermatolojiDurum TEXT,
                DermatolojiAciklama TEXT,
                DahiliyeMuayeneTarihi TEXT,
                DahiliyeDurum TEXT,
                DahiliyeAciklama TEXT,
                GozMuayeneTarihi TEXT,
                GozDurum TEXT,
                GozAciklama TEXT,
                GoruntulemeMuayeneTarihi TEXT,
                GoruntulemeDurum TEXT,
                GoruntulemeAciklama TEXT,
                RaporDosya TEXT,
                Notlar TEXT,
                sync_status TEXT DEFAULT 'clean',
                updated_at TEXT
            )
            """)

            cur.execute("""
            INSERT INTO Personel_Saglik_Takip_new (
                KayitNo, Personelid, AdSoyad, Birim, Yil,
                MuayeneTarihi, SonrakiKontrolTarihi, Sonuc, Durum,
                DermatolojiMuayeneTarihi, DermatolojiDurum, DermatolojiAciklama,
                DahiliyeMuayeneTarihi, DahiliyeDurum, DahiliyeAciklama,
                GozMuayeneTarihi, GozDurum, GozAciklama,
                GoruntulemeMuayeneTarihi, GoruntulemeDurum, GoruntulemeAciklama,
                RaporDosya, Notlar, sync_status, updated_at
            )
            SELECT
                KayitNo, Personelid, AdSoyad, Birim, Yil,
                MuayeneTarihi, SonrakiKontrolTarihi, Sonuc, Durum,
                DermatolojiMuayeneTarihi, DermatolojiDurum, DermatolojiAciklama,
                DahiliyeMuayeneTarihi, DahiliyeDurum, DahiliyeAciklama,
                GozMuayeneTarihi, GozDurum, GozAciklama,
                GoruntulemeMuayeneTarihi, GoruntulemeDurum, GoruntulemeAciklama,
                RaporDosya, Notlar, sync_status, updated_at
            FROM Personel_Saglik_Takip
            """)

            cur.execute("DROP TABLE Personel_Saglik_Takip")
            cur.execute("ALTER TABLE Personel_Saglik_Takip_new RENAME TO Personel_Saglik_Takip")
            conn.commit()
            logger.info("v6: Dozimetre/Belirti/GozSevk kolonlari kaldirildi")
        finally:
            conn.close()

    def _migrate_to_v7(self):
        """
        v6 → v7: Personel tablosuna saglik ozet kolonlari ekleme.
        - MuayeneTarihi (TEXT)
        - Sonuc (TEXT)
        """
        conn = self.connect()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='Personel'
            """)
            if not cur.fetchone():
                logger.warning("Tablo bulunamadi: Personel, v7 atlandi")
                conn.commit()
                return

            cur.execute("PRAGMA table_info(Personel)")
            existing = {row[1] for row in cur.fetchall()}

            if "MuayeneTarihi" not in existing:
                cur.execute("ALTER TABLE Personel ADD COLUMN MuayeneTarihi TEXT")
                logger.info("  Personel.MuayeneTarihi eklendi")

            if "Sonuc" not in existing:
                cur.execute("ALTER TABLE Personel ADD COLUMN Sonuc TEXT")
                logger.info("  Personel.Sonuc eklendi")

            conn.commit()
            logger.info("v7: Personel saglik ozet kolonlari hazir")

        finally:
            conn.close()

    # ════════════════════════════════════════════════
    # TABLO OLUŞTURMA (İLK KURULUM)
    # ════════════════════════════════════════════════

    def create_tables(self, cur):
        """
        İlk kurulum için tüm tabloları oluşturur.
        Bu metod sadece v0 → v1 migration'ında çağrılır.
        """

        # ---------------- PERSONEL ----------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Personel (
            KimlikNo TEXT PRIMARY KEY,
            AdSoyad TEXT,
            DogumYeri TEXT,
            DogumTarihi TEXT,
            HizmetSinifi TEXT,
            KadroUnvani TEXT,
            GorevYeri TEXT,
            KurumSicilNo TEXT,
            MemuriyeteBaslamaTarihi TEXT,
            CepTelefonu TEXT,
            Eposta TEXT,
            MezunOlunanOkul TEXT,
            MezunOlunanFakulte TEXT,
            MezuniyetTarihi TEXT,
            DiplomaNo TEXT,
            MezunOlunanOkul2 TEXT,
            MezunOlunanFakulte2 TEXT,
            MezuniyetTarihi2 TEXT,
            DiplomaNo2 TEXT,
            Resim TEXT,
            Diploma1 TEXT,
            Diploma2 TEXT,
            OzlukDosyasi TEXT,
            Durum TEXT,
            AyrilisTarihi TEXT,
            AyrilmaNedeni TEXT,
            MuayeneTarihi TEXT,
            Sonuc TEXT,

            sync_status TEXT DEFAULT 'clean',
            updated_at TEXT
        )
        """)

        # ---------------- IZIN GIRIS ----------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Izin_Giris (
            Izinid TEXT PRIMARY KEY,
            HizmetSinifi TEXT,
            Personelid TEXT,
            AdSoyad TEXT,
            IzinTipi TEXT,
            BaslamaTarihi TEXT,
            Gun INTEGER,
            BitisTarihi TEXT,
            Durum TEXT,

            sync_status TEXT DEFAULT 'clean',
            updated_at TEXT
        )
        """)

        # ---------------- IZIN BILGI ----------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Izin_Bilgi (
            TCKimlik TEXT PRIMARY KEY,
            AdSoyad TEXT,
            YillikDevir REAL,
            YillikHakedis REAL,
            YillikToplamHak REAL,
            YillikKullanilan REAL,
            YillikKalan REAL,
            SuaKullanilabilirHak REAL,
            SuaKullanilan REAL,
            SuaKalan REAL,
            SuaCariYilKazanim REAL,
            RaporMazeretTop REAL,

            sync_status TEXT DEFAULT 'clean',
            updated_at TEXT
        )
        """)

        # ---------------- FHSZ PUANTAJ ----------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS FHSZ_Puantaj (
            Personelid TEXT NOT NULL,
            AdSoyad TEXT,
            Birim TEXT,
            CalismaKosulu TEXT,
            AitYil INTEGER NOT NULL,
            Donem TEXT NOT NULL,
            AylikGun INTEGER,
            KullanilanIzin INTEGER,
            FiiliCalismaSaat REAL,

            sync_status TEXT DEFAULT 'clean',
            updated_at TEXT,

            PRIMARY KEY (Personelid, AitYil, Donem)
        )
        """)

        # ---------------- CIHAZLAR ----------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Cihazlar (
            Cihazid TEXT PRIMARY KEY,
            CihazTipi TEXT,
            Marka TEXT,
            Model TEXT,
            Amac TEXT,
            Kaynak TEXT,
            SeriNo TEXT,
            NDKSeriNo TEXT,
            HizmeteGirisTarihi TEXT,
            RKS TEXT,
            Sorumlusu TEXT,
            Gorevi TEXT,
            NDKLisansNo TEXT,
            BaslamaTarihi TEXT,
            BitisTarihi TEXT,
            LisansDurum TEXT,
            AnaBilimDali TEXT,
            Birim TEXT,
            BulunduguBina TEXT,
            GarantiDurumu TEXT,
            GarantiBitisTarihi TEXT,
            DemirbasNo TEXT,
            KalibrasyonGereklimi TEXT,
            BakimDurum TEXT,
            Durum TEXT,
            Img TEXT,
            NDKLisansBelgesi TEXT,

            sync_status TEXT DEFAULT 'clean',
            updated_at TEXT
        )
        """)

        # ---------------- CIHAZ ARIZA ----------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Cihaz_Ariza (
            Arizaid TEXT PRIMARY KEY,
            Cihazid TEXT,
            BaslangicTarihi TEXT,
            Saat TEXT,
            Bildiren TEXT,
            ArizaTipi TEXT,
            Oncelik TEXT,
            Baslik TEXT,
            ArizaAcikla TEXT,
            Durum TEXT,
            Rapor TEXT,

            sync_status TEXT DEFAULT 'clean',
            updated_at TEXT
        )
        """)

        # ---------------- ARIZA ISLEM ----------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Ariza_Islem (
            Islemid TEXT PRIMARY KEY,
            Arizaid TEXT,
            Tarih TEXT,
            Saat TEXT,
            IslemYapan TEXT,
            IslemTuru TEXT,
            YapilanIslem TEXT,
            YeniDurum TEXT,
            Rapor TEXT,

            sync_status TEXT DEFAULT 'clean',
            updated_at TEXT
        )
        """)

        # ---------------- PERIYODIK BAKIM ----------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Periyodik_Bakim (
            Planid TEXT PRIMARY KEY,
            Cihazid TEXT,
            BakimPeriyodu TEXT,
            BakimSirasi INTEGER,
            PlanlananTarih TEXT,
            Bakim TEXT,
            Durum TEXT,
            BakimTarihi TEXT,
            BakimTipi TEXT,
            YapilanIslemler TEXT,
            Aciklama TEXT,
            Teknisyen TEXT,
            Rapor TEXT,

            sync_status TEXT DEFAULT 'clean',
            updated_at TEXT
        )
        """)

        # ---------------- KALIBRASYON ----------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Kalibrasyon (
            Kalid TEXT PRIMARY KEY,
            Cihazid TEXT,
            Firma TEXT,
            SertifikaNo TEXT,
            YapilanTarih TEXT,
            Gecerlilik TEXT,
            BitisTarihi TEXT,
            Durum TEXT,
            Dosya TEXT,
            Aciklama TEXT,

            sync_status TEXT DEFAULT 'clean',
            updated_at TEXT
        )
        """)

        # ---------------- SABITLER ----------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Sabitler (
            Rowid TEXT PRIMARY KEY,
            Kod TEXT,
            MenuEleman TEXT,
            Aciklama TEXT,
                    
            sync_status TEXT DEFAULT 'clean',
            updated_at TEXT
        )
        """)

        # ---------------- TATILLER ----------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Tatiller (
            Tarih TEXT PRIMARY KEY,
            ResmiTatil TEXT,
                    
            sync_status TEXT DEFAULT 'clean',
            updated_at TEXT
        )
        """)

        # ---------------- LOGLAR ----------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Loglar (
            Tarih TEXT,
            Saat TEXT,
            Kullanici TEXT,
            Modul TEXT,
            Islem TEXT,
            Detay TEXT
        )
        """)

        # ---------------- RKE LIST ----------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS RKE_List (
            EkipmanNo TEXT PRIMARY KEY,
            KoruyucuNumarasi TEXT,
            AnaBilimDali TEXT,
            Birim TEXT,
            KoruyucuCinsi TEXT,
            KursunEsdegeri TEXT,
            HizmetYili INTEGER,
            Bedeni TEXT,
            KontrolTarihi TEXT,
            Durum TEXT,
            Aciklama TEXT,
            VarsaDemirbasNo TEXT,
            KayitTarih TEXT,
            Barkod TEXT,

            sync_status TEXT DEFAULT 'clean',
            updated_at TEXT
        )
        """)

        # ---------------- RKE MUAYENE ----------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS RKE_Muayene (
            KayitNo TEXT PRIMARY KEY,
            EkipmanNo TEXT,
            FMuayeneTarihi TEXT,
            FizikselDurum TEXT,
            SMuayeneTarihi TEXT,
            SkopiDurum TEXT,
            Aciklamalar TEXT,
            KontrolEdenUnvani TEXT,
            BirimSorumlusuUnvani TEXT,
            Notlar TEXT,
            Rapor TEXT,

            sync_status TEXT DEFAULT 'clean',
            updated_at TEXT
        )
        """)

        # ---------------- PERSONEL SAGLIK TAKIP ----------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Personel_Saglik_Takip (
            KayitNo TEXT PRIMARY KEY,
            Personelid TEXT,
            AdSoyad TEXT,
            Birim TEXT,
            Yil INTEGER,
            MuayeneTarihi TEXT,
            SonrakiKontrolTarihi TEXT,
            Sonuc TEXT,
            Durum TEXT,
            DermatolojiMuayeneTarihi TEXT,
            DermatolojiDurum TEXT,
            DermatolojiAciklama TEXT,
            DahiliyeMuayeneTarihi TEXT,
            DahiliyeDurum TEXT,
            DahiliyeAciklama TEXT,
            GozMuayeneTarihi TEXT,
            GozDurum TEXT,
            GozAciklama TEXT,
            GoruntulemeMuayeneTarihi TEXT,
            GoruntulemeDurum TEXT,
            GoruntulemeAciklama TEXT,
            RaporDosya TEXT,
            Notlar TEXT,

            sync_status TEXT DEFAULT 'clean',
            updated_at TEXT
        )
        """)

    # ════════════════════════════════════════════════
    # ESKI RESET METODU (ACİL DURUMLARDA)
    # ════════════════════════════════════════════════

    def reset_database(self):
        """
        ⚠️  ACİL DURUM: Tüm tabloları sil ve yeniden oluştur
        
        Bu metod sadece ciddi veri bozulması durumunda manuel olarak çağrılmalıdır.
        Normal kullanımda run_migrations() tercih edilmelidir.
        """
        logger.warning("⚠️  VERİTABANI TAM RESET YAPILIYOR - TÜM VERİ SİLİNECEK!")
        
        # Yedek al
        backup_path = self.backup_database()
        if backup_path:
            logger.info(f"Son yedek: {backup_path}")
        
        conn = self.connect()
        cur = conn.cursor()

        tables = [
            "Personel", "Izin_Giris", "Izin_Bilgi", "FHSZ_Puantaj",
            "Cihazlar", "Cihaz_Ariza", "Ariza_Islem", "Periyodik_Bakim",
            "Kalibrasyon", "Sabitler", "Tatiller", "Loglar",
            "RKE_List", "RKE_Muayene", "Personel_Saglik_Takip", "schema_version"
        ]

        for table in tables:
            cur.execute(f"DROP TABLE IF EXISTS {table}")
            logger.info(f"  {table} silindi")

        self.create_tables(cur)
        
        # Versiyon tablosunu oluştur ve güncel versiyonu kaydet
        cur.execute("""
            CREATE TABLE schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL,
                description TEXT
            )
        """)
        cur.execute("""
            INSERT INTO schema_version (version, applied_at, description)
            VALUES (?, ?, ?)
        """, (self.CURRENT_VERSION, datetime.now().isoformat(), "Full reset"))

        conn.commit()
        conn.close()

        logger.info(f"✓ Tüm tablolar yeniden oluşturuldu (v{self.CURRENT_VERSION})")

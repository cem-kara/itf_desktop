# database/migrations.py
import sqlite3
from core.logger import logger


class MigrationManager:
    def __init__(self, db_path):
        self.db_path = db_path

    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def reset_database(self):
        logger.warning("SQLite tamamen yeniden yapilandiriliyor")

        conn = self.connect()
        cur = conn.cursor()

        tables = [
            "Personel",
            "Izin_Giris",
            "Izin_Bilgi",
            "FHSZ_Puantaj",
            "Cihazlar",
            "Cihaz_Ariza",
            "Ariza_Islem",
            "Periyodik_Bakim",
            "Kalibrasyon",
            "Sabitler",
            "Tatiller",
            "Loglar",
            "RKE_List",
            "RKE_Muayene"
        ]

        for table in tables:
            cur.execute(f"DROP TABLE IF EXISTS {table}")
            logger.info(f"{table} silindi")

        self.create_tables(cur)

        conn.commit()
        conn.close()

        logger.info("Tum tablolar basariyla olusturuldu")

    def create_tables(self, cur):

        # ---------------- PERSONEL ----------------
        cur.execute("""
        CREATE TABLE Personel (
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

            sync_status TEXT DEFAULT 'clean',
            updated_at TEXT
        )
        """)

        # ---------------- IZIN GIRIS ----------------
        cur.execute("""
        CREATE TABLE Izin_Giris (
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
        CREATE TABLE Izin_Bilgi (
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
        CREATE TABLE FHSZ_Puantaj (
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
        CREATE TABLE Cihazlar (
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
        CREATE TABLE Cihaz_Ariza (
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
        CREATE TABLE Ariza_Islem (
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
        CREATE TABLE Periyodik_Bakim (
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
        CREATE TABLE Kalibrasyon (
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
        CREATE TABLE Sabitler (
            Rowid INTEGER PRIMARY KEY AUTOINCREMENT,
            Kod TEXT,
            MenuEleman TEXT,
            Aciklama TEXT,
                    
            sync_status TEXT DEFAULT 'clean',
            updated_at TEXT
        )
        """)

        # ---------------- TATILLER ----------------
        cur.execute("""
        CREATE TABLE Tatiller (
            Tarih TEXT PRIMARY KEY,
            ResmiTatil TEXT,
                    
            sync_status TEXT DEFAULT 'clean',
            updated_at TEXT
        )
        """)

        # ---------------- LOGLAR ----------------
        cur.execute("""
        CREATE TABLE Loglar (
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
        CREATE TABLE RKE_List (
            KayitNo TEXT PRIMARY KEY,
            EkipmanNo TEXT,
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
        CREATE TABLE RKE_Muayene (
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

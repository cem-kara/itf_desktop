from database.sqlite_manager import SQLiteManager
from core.logger import logger


def enable_foreign_keys(db):
    db.execute("PRAGMA foreign_keys = ON;")

def create_meta(db):
    db.execute("""
    CREATE TABLE IF NOT EXISTS meta (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
# =========================
# CİHAZ YÖNETİMİ
# =========================
def create_cihazlar(db):
    db.execute("""
    CREATE TABLE IF NOT EXISTS Cihazlar (
        cihaz_id TEXT PRIMARY KEY,
        CihazTipi TEXT,
        Marka TEXT,
        Model TEXT,
        Amac TEXT,
        Kaynak TEXT,
        SeriNo TEXT,
        NDKSeriNo TEXT,
        HizmeteGirisTarihi DATE,
        RKS TEXT,
        Sorumlusu TEXT,
        Gorevi TEXT,
        NDKLisansNo TEXT,
        BaslamaTarihi DATE,
        BitisTarihi DATE,
        LisansDurum TEXT,
        AnaBilimDali TEXT,
        Birim TEXT,
        BulunduguBina TEXT,
        GarantiDurumu TEXT,
        GarantiBitisTarihi DATE,
        DemirbasNo TEXT,
        KalibrasyonGereklimi TEXT,
        BakimDurum TEXT,
        Durum TEXT,
        Img TEXT,
        NDK_Lisans_Belgesi TEXT,

        created_at TEXT,
        updated_at TEXT,
        updated_by TEXT,
        sync_status TEXT
    );
    """)


def create_cihaz_ariza(db):
    db.execute("""
    CREATE TABLE IF NOT EXISTS cihaz_ariza (
        ariza_id TEXT PRIMARY KEY,
        cihaz_id TEXT,
        baslangic_tarihi DATE,
        saat TEXT,
        bildiren TEXT,
        ariza_tipi TEXT,
        oncelik TEXT,
        baslik TEXT,
        ariza_acikla TEXT,
        durum TEXT,
        rapor TEXT,

        created_at TEXT,
        updated_at TEXT,
        updated_by TEXT,
        sync_status TEXT,

        FOREIGN KEY (cihaz_id) REFERENCES Cihazlar(cihaz_id)
    );
    """)


def create_ariza_islem(db):
    db.execute("""
    CREATE TABLE IF NOT EXISTS ariza_islem (
        IslemID TEXT PRIMARY KEY,
        ArizaID TEXT,
        Tarih DATE,
        Saat TEXT,
        IslemYapan TEXT,
        IslemTuru TEXT,
        YapilanIslem TEXT,
        YeniDurum TEXT,
        Rapor TEXT,

        created_at TEXT,
        updated_at TEXT,
        updated_by TEXT,
        sync_status TEXT,

        FOREIGN KEY (ArizaID) REFERENCES cihaz_ariza(ariza_id)
    );
    """)


def create_periyodik_bakim(db):
    db.execute("""
    CREATE TABLE IF NOT EXISTS Periyodik_Bakim (
        PlanID TEXT PRIMARY KEY,
        cihaz_id TEXT,
        BakimPeriyodu TEXT,
        BakimSirasi TEXT,
        PlanlananTarih DATE,
        Bakim TEXT,
        Durum TEXT,
        BakimTarihi DATE,
        BakimTipi TEXT,
        YapilanIslemler TEXT,
        Aciklama TEXT,
        Teknisyen TEXT,
        Rapor TEXT,

        created_at TEXT,
        updated_at TEXT,
        updated_by TEXT,
        sync_status TEXT,

        FOREIGN KEY (cihaz_id) REFERENCES Cihazlar(cihaz_id)
    );
    """)


def create_kalibrasyon(db):
    db.execute("""
    CREATE TABLE IF NOT EXISTS Kalibrasyon (
        ID TEXT PRIMARY KEY,
        cihaz_id TEXT,
        Firma TEXT,
        SertifikaNo TEXT,
        YapilanTarih DATE,
        Gecerlilik TEXT,
        BitisTarihi DATE,
        Durum TEXT,
        Dosya TEXT,
        Aciklama TEXT,

        created_at TEXT,
        updated_at TEXT,
        updated_by TEXT,
        sync_status TEXT,

        FOREIGN KEY (cihaz_id) REFERENCES Cihazlar(cihaz_id)
    );
    """)


# =========================
# PERSONEL
# =========================
def create_personel(db):
    db.execute("""
    CREATE TABLE IF NOT EXISTS Personel (
        Kimlik_No TEXT PRIMARY KEY,
        Ad_Soyad TEXT,
        Dogum_Yeri TEXT,
        Dogum_Tarihi DATE,
        Hizmet_Sinifi TEXT,
        Kadro_Unvani TEXT,
        Gorev_Yeri TEXT,
        Kurum_Sicil_No TEXT,
        Memuriyete_Baslama_Tarihi DATE,
        Cep_Telefonu TEXT,
        E_posta TEXT,
        Mezun_Olunan_Okul TEXT,
        Mezun_Olunan_Fakülte TEXT,
        Mezuniyet_Tarihi DATE,
        Diploma_No TEXT,
        Mezun_Olunan_Okul_2 TEXT,
        Mezun_Olunan_Fakülte_2 TEXT,
        Mezuniyet_Tarihi_2 DATE,
        Diploma_No_2 TEXT,
        Resim TEXT,
        Diploma1 TEXT,
        Diploma2 TEXT,
        Ozluk_Dosyasi TEXT,
        Durum TEXT,
        Ayrilis_Tarihi DATE,
        Ayrilma_Nedeni TEXT,

        created_at TEXT,
        updated_at TEXT,
        updated_by TEXT,
        sync_status TEXT
    );
    """)


def create_izin_giris(db):
    db.execute("""
    CREATE TABLE IF NOT EXISTS izin_giris (
        Id TEXT PRIMARY KEY,
        Hizmet_Sinifi TEXT,
        personel_id TEXT,
        Ad_Soyad TEXT,
        izin_tipi TEXT,
        Baslama_Tarihi DATE,
        Gun INTEGER,
        Bitis_Tarihi DATE,
        Durum TEXT,

        created_at TEXT,
        updated_at TEXT,
        updated_by TEXT,
        sync_status TEXT,

        FOREIGN KEY (personel_id) REFERENCES Personel(Kimlik_No)
    );
    """)


def create_izin_bilgi(db):
    db.execute("""
    CREATE TABLE IF NOT EXISTS izin_bilgi (
        TC_Kimlik TEXT PRIMARY KEY,
        Ad_Soyad TEXT,
        Yillik_Devir INTEGER,
        Yillik_Hakedis INTEGER,
        Yillik_Toplam_Hak INTEGER,
        Yillik_Kullanilan INTEGER,
        Yillik_Kalan INTEGER,
        Sua_Kullanilabilir_Hak INTEGER,
        Sua_Kullanilan INTEGER,
        Sua_Kalan INTEGER,
        Sua_Cari_Yil_Kazanim INTEGER,
        Rapor_Mazeret_Top INTEGER,

        created_at TEXT,
        updated_at TEXT,
        updated_by TEXT,
        sync_status TEXT,

        FOREIGN KEY (TC_Kimlik) REFERENCES Personel(Kimlik_No)
    );
    """)


def create_fhsz_puantaj(db):
    db.execute("""
    CREATE TABLE IF NOT EXISTS FHSZ_Puantaj (
        personel_id TEXT,
        Ad_Soyad TEXT,
        Birim TEXT,
        Calisma_Kosulu TEXT,
        Ait_yil INTEGER,
        Donem TEXT,
        Aylik_Gun INTEGER,
        Kullanilan_izin INTEGER,
        Fiili_calisma_saat REAL,

        created_at TEXT,
        updated_at TEXT,
        updated_by TEXT,
        sync_status TEXT,

        FOREIGN KEY (personel_id) REFERENCES Personel(Kimlik_No)
    );
    """)


def create_nobet(db):
    db.execute("""
    CREATE TABLE IF NOT EXISTS Nobet (
        nobet_id TEXT PRIMARY KEY,
        personel_id TEXT,
        tarih DATE,
        vardiya TEXT,

        created_at TEXT,
        updated_at TEXT,
        updated_by TEXT,
        sync_status TEXT,

        FOREIGN KEY (personel_id) REFERENCES Personel(Kimlik_No)
    );
    """)


def create_nobet_degisim(db):
    db.execute("""
    CREATE TABLE IF NOT EXISTS Nobet_Degisim (
        nobet_de_id TEXT PRIMARY KEY,
        talep_eden TEXT,
        verilecek_Tarihi DATE,
        verilecek_vardiya TEXT,
        alinacak_kisi TEXT,
        alinacak_tarih DATE,
        alinacak_vardiya TEXT,
        degisim_nedeni TEXT,
        birim_sorumlusu TEXT,
        birim_durum TEXT,
        rad_sorumlu TEXT,
        rad_durum TEXT,
        aciklama TEXT,

        created_at TEXT,
        updated_at TEXT,
        updated_by TEXT,
        sync_status TEXT
    );
    """)


# =========================
# RKE
# =========================
def create_rke_list(db):
    db.execute("""
    CREATE TABLE IF NOT EXISTS rke_list (
        KayitNo TEXT PRIMARY KEY,
        EkipmanNo TEXT,
        KoruyucuNumarasi TEXT,
        AnaBilimDali TEXT,
        Birim TEXT,
        KoruyucuCinsi TEXT,
        KursunEsdegeri TEXT,
        HizmetYili INTEGER,
        Bedeni TEXT,
        KontrolTarihi DATE,
        Durum TEXT,
        Aciklama TEXT,
        Varsa_Demirbas_No TEXT,
        KayitTarih DATETIME,
        Barkod TEXT,

        created_at TEXT,
        updated_at TEXT,
        updated_by TEXT,
        sync_status TEXT
    );
    """)


def create_rke_muayene(db):
    db.execute("""
    CREATE TABLE IF NOT EXISTS rke_muayene (
        KayitNo TEXT PRIMARY KEY,
        EkipmanNo TEXT,
        F_MuayeneTarihi DATE,
        FizikselDurum TEXT,
        S_MuayeneTarihi DATE,
        SkopiDurum TEXT,
        Aciklamalar TEXT,
        KontrolEden_Unvani TEXT,
        BirimSorumlusu_Unvani TEXT,
        Not_Alani TEXT,
        Rapor TEXT,

        created_at TEXT,
        updated_at TEXT,
        updated_by TEXT,
        sync_status TEXT,

        FOREIGN KEY (EkipmanNo) REFERENCES rke_list(EkipmanNo)
    );
    """)


# =========================
# SABİTLER & SİSTEM
# =========================
def create_sabitler(db):
    db.execute("""
    CREATE TABLE IF NOT EXISTS Sabitler (
        Row_ID TEXT PRIMARY KEY,
        Kod TEXT,
        MenuEleman TEXT,
        Aciklama TEXT,

        created_at TEXT,
        updated_at TEXT,
        updated_by TEXT,
        sync_status TEXT
    );
    """)


def create_loglar(db):
    db.execute("""
    CREATE TABLE IF NOT EXISTS Loglar (
        Tarih TEXT,
        Saat TEXT,
        Kullanici TEXT,
        Modul TEXT,
        Islem TEXT,
        Detay TEXT
    );
    """)


def create_tatiller(db):
    db.execute("""
    CREATE TABLE IF NOT EXISTS Tatiller (
        Tarih DATE PRIMARY KEY,
        Resmi_Tatil TEXT,

        created_at TEXT,
        updated_at TEXT,
        updated_by TEXT,
        sync_status TEXT
    );
    """)


# =========================
# RUN ALL
# =========================
def run_migrations():
    logger.info("Migration başlatıldı")
    db = SQLiteManager()
    enable_foreign_keys(db)

    create_cihazlar(db)
    create_cihaz_ariza(db)
    create_ariza_islem(db)
    create_periyodik_bakim(db)
    create_kalibrasyon(db)

    create_personel(db)
    create_izin_giris(db)
    create_izin_bilgi(db)
    create_fhsz_puantaj(db)
    create_nobet(db)
    create_nobet_degisim(db)

    create_rke_list(db)
    create_rke_muayene(db)

    create_sabitler(db)
    create_loglar(db)
    create_tatiller(db)

    db.close()
    logger.info("Migration tamamlandı")

TABLES = {

    # ─────────────── PERSONEL VT ───────────────

    "Personel": {
        "pk": "KimlikNo",
        "columns": [
            "KimlikNo","AdSoyad","DogumYeri","DogumTarihi","HizmetSinifi",
            "KadroUnvani","GorevYeri","KurumSicilNo","MemuriyeteBaslamaTarihi",
            "CepTelefonu","Eposta","MezunOlunanOkul","MezunOlunanFakulte",
            "MezuniyetTarihi","DiplomaNo","MezunOlunanOkul2",
            "MezunOlunanFakulte2","MezuniyetTarihi2","DiplomaNo2",
            "Resim","Diploma1","Diploma2","OzlukDosyasi","Durum",
            "AyrilisTarihi","AyrilmaNedeni","MuayeneTarihi","Sonuc"
        ],
        "date_fields": [
            "DogumTarihi",
            "MemuriyeteBaslamaTarihi",
            "MezuniyetTarihi",
            "MezuniyetTarihi2",
            "AyrilisTarihi",
            "MuayeneTarihi",
        ],
    },

    "Izin_Giris": {
        "pk": "Izinid",
        "columns": [
            "Izinid","HizmetSinifi","Personelid","AdSoyad",
            "IzinTipi","BaslamaTarihi","Gun","BitisTarihi","Durum"
        ],
        "date_fields": ["BaslamaTarihi", "BitisTarihi"],
    },

    "Izin_Bilgi": {
        "pk": "TCKimlik",
        "columns": [
            "TCKimlik","AdSoyad","YillikDevir","YillikHakedis",
            "YillikToplamHak","YillikKullanilan","YillikKalan",
            "SuaKullanilabilirHak","SuaKullanilan","SuaKalan",
            "SuaCariYilKazanim","RaporMazeretTop"
        ]
    },

    "FHSZ_Puantaj": {
        "pk": ["Personelid", "AitYil", "Donem"],   # composite PK
        "columns": [
            "Personelid","AdSoyad","Birim","CalismaKosulu",
            "AitYil","Donem","AylikGun","KullanilanIzin",
            "FiiliCalismaSaat"
        ]
    },

    # ─────────────── CİHAZ VT ───────────────

    "Cihazlar": {
        "pk": "Cihazid",
        "columns": [                          # ← "colums" → "columns"
            "Cihazid","CihazTipi","Marka","Model","Amac",
            "Kaynak","SeriNo","NDKSeriNo","HizmeteGirisTarihi",
            "RKS","Sorumlusu","Gorevi","NDKLisansNo","BaslamaTarihi",
            "BitisTarihi","LisansDurum","AnaBilimDali","Birim","BulunduguBina",
            "GarantiDurumu","GarantiBitisTarihi","DemirbasNo","KalibrasyonGereklimi",
            "BakimDurum","Durum","Img","NDKLisansBelgesi"
        ],
        "date_fields": [
            "HizmeteGirisTarihi",
            "BaslamaTarihi",
            "BitisTarihi",
            "GarantiBitisTarihi",
        ],
    },


    "Dokumanlar": {
        "pk": ["EntityType", "EntityId", "BelgeTuru", "Belge"],
        # sync=True: tüm metadata makineler arası Sheets üzerinden senkronize edilir.
        # LocalPath makineye özgü yolu saklar (diğer makinede geçersiz olabilir ama
        # DrivePath öncelikli açılır, LocalPath yedek olarak korunur).
        # ÖNEMLİ: Google Sheets'te "Dokumanlar" sayfasının oluşturulmuş olması gerekir.
        "sync": True,
        "columns": [
            "EntityType",
            "EntityId",
            "BelgeTuru",
            "Belge",
            "DokumanId",
            "DocType",
            "DisplayName",
            "LocalPath",
            "BelgeAciklama",
            "YuklenmeTarihi",
            "DrivePath",
            "IliskiliBelgeID",
            "IliskiliBelgeTipi",
        ],
        "date_fields": ["YuklenmeTarihi"],
    },


    "Cihaz_Ariza": {
        "pk": "Arizaid",
        "columns": [                          # ← "colums" → "columns"
            "Arizaid","Cihazid","BaslangicTarihi","Saat","Bildiren",
            "ArizaTipi","Oncelik","Baslik",   # ← "Baslık" encoding düzeltildi
            "ArizaAcikla","Durum","Rapor"
        ],
        "date_fields": ["BaslangicTarihi"],
    },

    "Cihaz_Teknik": {
        "pk": "Cihazid",
        "columns": [
            "Cihazid",
            "BirincilUrunNumarasi", "KurumUnvan", "MarkaAdi", "EtiketAdi",
            "VersiyonModel", "UrunTipi", "Sinif", "KatalogNo",
            "GmdnTerimKod", "GmdnTerimTurkceAd", "TemelUdiDi",
            "UrunTanimi", "Aciklama",
            "KurumGorunenAd", "KurumNo", "KurumTelefon", "KurumEposta",
            "IthalImalBilgisi", "MenseiUlkeSet", "IthalEdilenUlkeSet",
            "SutEslesmesiSet", "Durum", "CihazKayitTipi",
            "UtsBaslangicTarihi", "KontroleGonderildigiTarih",
            "KalibrasyonaTabiMi", "KalibrasyonPeriyodu",
            "BakimaTabiMi", "BakimPeriyodu",
            "MrgUyumlu", "IyonizeRadyasyonIcerir",
            "TekHastayaKullanilabilir", "SinirliKullanimSayisiVar",
            "SinirliKullanimSayisi", "BaskaImalatciyaUrettirildiMi",
            "GmdnTerimTurkceAciklama",
        ],
        "date_fields": ["UtsBaslangicTarihi", "KontroleGonderildigiTarih"],
        "sync": False,
    },

    "Cihaz_Teknik_Belge": {
        "pk": ["Cihazid", "BelgeTuru", "Belge"],
        "columns": [
            "Cihazid", "BelgeTuru", "Belge",
            "BelgeAdi", "YuklenmeTarihi", "DrivePath", "LocalPath",
        ],
        "date_fields": ["YuklenmeTarihi"],
        "sync": False,
    },

    "Ariza_Islem": {
        "pk": "Islemid",
        "columns": [                          # ← "colums" → "columns"
            "Islemid","Arizaid","Tarih","Saat","IslemYapan",
            "IslemTuru","YapilanIslem","YeniDurum","Rapor"
        ],
        "date_fields": ["Tarih"],
    },

    "Periyodik_Bakim": {
        "pk": "Planid",
        "columns": [                          # ← "colums" → "columns"
            "Planid","Cihazid","BakimPeriyodu","BakimSirasi","PlanlananTarih",
            "Bakim","Durum","BakimTarihi","BakimTipi","YapilanIslemler","Aciklama",
            "Teknisyen","Rapor","SozlesmeId"
        ],
        "date_fields": ["PlanlananTarih", "BakimTarihi"],
    },

    "Kalibrasyon": {
        "pk": "Kalid",
        "columns": [                          # ← "colums" → "columns"
            "Kalid","Cihazid",                # ← "cihazid" → "Cihazid" (migrations.py ile eşleşti)
            "Firma","SertifikaNo","YapilanTarih",
            "Gecerlilik","BitisTarihi","Durum","Dosya","Aciklama"
        ],
        "date_fields": ["YapilanTarih", "BitisTarihi"],
    },

    # ─────────────── SABİT VT ───────────────

    "Sabitler": {
        "pk": "Rowid",
        "sync_mode": "pull_only",  # Read-only table
        "columns": [
            "Rowid","Kod","MenuEleman","Aciklama"
        ],
    },

    "Tatiller": {
        "pk": "Tarih",
        "sync_mode": "pull_only",  # Read-only table
        "columns": [
            "Tarih","ResmiTatil"
        ],
        "date_fields": ["Tarih"],
        
    },

    "Loglar": {
        "pk": None,                           # ← "Personelid" kaldırıldı (Loglar'da PK yok)
        "columns": [
            "Tarih","Saat","Kullanici","Modul","Islem","Detay"
        ],
        "date_fields": ["Tarih"],
        "sync": False                         # Log tablosu sync dışı
    },

    # ─────────────── RKE VT ───────────────

    "RKE_List": {
        "pk": "EkipmanNo",                      # migrations.py ile uyumlu PK
        "columns": [
            "EkipmanNo","KoruyucuNumarasi","AnaBilimDali","Birim",
            "KoruyucuCinsi","KursunEsdegeri","HizmetYili","Bedeni","KontrolTarihi",
            "Durum","Aciklama",               # ← encoding düzeltildi
            "VarsaDemirbasNo",                # ← encoding düzeltildi
            "KayitTarih","Barkod"
        ],
        "date_fields": ["KontrolTarihi"],
    },

    "RKE_Muayene": {
        "pk": "KayitNo",                      # ← "Personelid" → "KayitNo" (migrations.py ile eşleşti)
        "columns": [
            "KayitNo","EkipmanNo","FMuayeneTarihi","FizikselDurum","SMuayeneTarihi",
            "SkopiDurum","Aciklamalar",
            "KontrolEdenUnvani",              # ← "/" kaldırıldı (SQLite kolon adında slash olmaz)
            "BirimSorumlusuUnvani",           # ← "/" kaldırıldı
            "Notlar",                         # ← "Not" → "Notlar" (migrations.py ile eşleşti)
            "Rapor"
        ],
        "date_fields": ["FMuayeneTarihi", "SMuayeneTarihi"],
    },

    "Personel_Saglik_Takip": {
        "pk": "KayitNo",
        "columns": [
            "KayitNo", "Personelid", "AdSoyad", "Birim", "Yil",
            "MuayeneTarihi", "SonrakiKontrolTarihi", "Sonuc", "Durum",
            "RaporDosya", "Notlar",
            "DermatolojiMuayeneTarihi", "DermatolojiDurum", 
            "DahiliyeMuayeneTarihi", "DahiliyeDurum",
            "GozMuayeneTarihi", "GozDurum",
            "GoruntulemeMuayeneTarihi", "GoruntulemeDurum",
        ],
        "date_fields": [
            "MuayeneTarihi", "SonrakiKontrolTarihi",
            "DermatolojiMuayeneTarihi", "DahiliyeMuayeneTarihi",
            "GozMuayeneTarihi", "GoruntulemeMuayeneTarihi"
        ],
    },
    
"Dis_Alan_Calisma": {
    # Personel tablosundan BAĞIMSIZ — dış alan personeli sisteme kayıtlı değil.
    # PK: TCKimlik + DonemAy + DonemYil + TutanakNo
    # TCKimlik boş gelebilir (opsiyonel), o zaman AdSoyad + TutanakNo benzersizlik sağlar.
    "pk": ["TCKimlik", "DonemAy", "DonemYil", "TutanakNo"],
    "columns": [
        "TCKimlik",          # Opsiyonel — 11 haneli TC (TEXT)
        "AdSoyad",           # Zorunlu
        "DonemAy",           # 1–12
        "DonemYil",          # 2024, 2025 …
        "AnaBilimDali",      # Zorunlu"
        "Birim",             # Zorunlu
        "IslemTipi",         # Alan adı
        "Katsayi",           # Kayıt anındaki katsayı (REAL)
        "OrtSureDk",         # Ortalama işlem süresi dk
        "VakaSayisi",        # INTEGER > 0
        "HesaplananSaat",    # VakaSayisi * Katsayi (REAL)
        "ToplamSureDk",      # VakaSayisi * OrtSureDk
        "TutanakNo",         # Zorunlu
        "TutanakTarihi",     # Import tarihi (YYYY-MM-DD)
        "KayitTarihi",       # Otomatik
        "KaydedenKullanici",
    ],
    "date_fields": ["TutanakTarihi", "KayitTarihi"],
    "sync": False,
},
 
"Dis_Alan_Izin_Ozet": {
    "pk": ["TCKimlik", "AdSoyad", "DonemAy", "DonemYil"],
    "columns": [
        "TCKimlik",
        "AdSoyad",
        "DonemAy",
        "DonemYil",
        "ToplamSaat",
        "IzinGunHakki",
        "HesaplamaTarihi",
        "RksOnay",
        "Notlar",
    ],
    "date_fields": ["HesaplamaTarihi"],
    "sync": False,
},

    "Dozimetre_Olcum": {
        "pk": "KayitNo",
        "columns": [
            "KayitNo", "RaporNo",
            "Periyot", "PeriyotAdi", "Yil", "DozimetriTipi",
            "AdSoyad", "CalistiBirim", "PersonelID",
            "DozimetreNo", "VucutBolgesi",
            "Hp10", "Hp007", "Durum",
            "OlusturmaTarihi",
        ],
        "date_fields": ["OlusturmaTarihi"],
        "sync": False
    },


    "Dis_Alan_Katsayi_Protokol": {
        "pk": ["AnaBilimDali", "Birim", "GecerlilikBaslangic"],
        "columns": [
            "AnaBilimDali",           # TEXT, PK
            "Birim",                  # TEXT, PK
            "GecerlilikBaslangic",    # TEXT, PK
            "Katsayi",                # REAL
            "OrtSureDk",              # INTEGER
            "AlanTipAciklama",        # TEXT
            "AciklamaFormul",         # TEXT
            "ProtokolRef",            # TEXT
            "GecerlilikBitis",        # TEXT, NULL olabilir
            "Aktif",                  # INTEGER, 1/0
            "KayitTarihi",            # TEXT, otomatik
            "KaydedenKullanici"       # TEXT
        ],
        "date_fields": ["GecerlilikBaslangic", "GecerlilikBitis", "KayitTarihi"],
        "sync":False
    },


}


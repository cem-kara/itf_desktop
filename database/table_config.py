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
            "AyrilisTarihi","AyrilmaNedeni"
        ],
        "date_fields": [
            "DogumTarihi",
            "MemuriyeteBaslamaTarihi",
            "MezuniyetTarihi",
            "MezuniyetTarihi2",
            "AyrilisTarihi",
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

    "Cihaz_Ariza": {
        "pk": "Arizaid",
        "columns": [                          # ← "colums" → "columns"
            "Arizaid","Cihazid","BaslangicTarihi","Saat","Bildiren",
            "ArizaTipi","Oncelik","Baslik",   # ← "BaslÄ±k" encoding düzeltildi
            "ArizaAcikla","Durum","Rapor"
        ],
        "date_fields": ["BaslangicTarihi"],
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
            "Teknisyen","Rapor"
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
        "columns": [
            "Rowid","Kod","MenuEleman","Aciklama"
        ],
        "sync_mode": "pull_only"  # Sadece Google Sheets → Local (veri kaynağı: Sheets)
    },

    "Tatiller": {
        "pk": "Tarih",
        "columns": [
            "Tarih","ResmiTatil"
        ],
        "date_fields": ["Tarih"],
        "sync_mode": "pull_only"  # Sadece Google Sheets → Local (resmi tatil takvimi)
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
        "pk": "EkipmanNo",                      # ← "Personelid" → "KayitNo" (migrations.py PK)
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
            "DermatolojiMuayeneTarihi", "DermatolojiDurum", "DermatolojiAciklama",
            "DahiliyeMuayeneTarihi", "DahiliyeDurum", "DahiliyeAciklama",
            "GozMuayeneTarihi", "GozDurum", "GozAciklama",
            "GoruntulemeMuayeneTarihi", "GoruntulemeDurum", "GoruntulemeAciklama",
            "RaporDosya", "Notlar"
        ],
        "date_fields": [
            "MuayeneTarihi", "SonrakiKontrolTarihi",
            "DermatolojiMuayeneTarihi", "DahiliyeMuayeneTarihi",
            "GozMuayeneTarihi", "GoruntulemeMuayeneTarihi"
        ],
    }

}

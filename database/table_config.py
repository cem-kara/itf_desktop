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
        ]
    },

    "Izin_Giris": {
        "pk": "Izinid",
        "columns": [
            "Izinid","HizmetSinifi","Personelid","AdSoyad",
            "IzinTipi","BaslamaTarihi","Gun","BitisTarihi","Durum"
        ]
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
        ]
    },

    "Cihaz_Ariza": {
        "pk": "Arizaid",
        "columns": [                          # ← "colums" → "columns"
            "Arizaid","Cihazid","BaslangicTarihi","Saat","Bildiren",
            "ArizaTipi","Oncelik","Baslik",   # ← "BaslÄ±k" encoding düzeltildi
            "ArizaAcikla","Durum","Rapor"
        ]
    },

    "Ariza_Islem": {
        "pk": "Islemid",
        "columns": [                          # ← "colums" → "columns"
            "Islemid","Arizaid","Tarih","Saat","IslemYapan",
            "IslemTuru","YapilanIslem","YeniDurum","Rapor"
        ]
    },

    "Periyodik_Bakim": {
        "pk": "Planid",
        "columns": [                          # ← "colums" → "columns"
            "Planid","Cihazid","BakimPeriyodu","BakimSirasi","PlanlananTarih",
            "Bakim","Durum","BakimTarihi","BakimTipi","YapilanIslemler","Aciklama",
            "Teknisyen","Rapor"
        ]
    },

    "Kalibrasyon": {
        "pk": "Kalid",
        "columns": [                          # ← "colums" → "columns"
            "Kalid","Cihazid",                # ← "cihazid" → "Cihazid" (migrations.py ile eşleşti)
            "Firma","SertifikaNo","YapilanTarih",
            "Gecerlilik","BitisTarihi","Durum","Dosya","Aciklama"
        ]
    },

    # ─────────────── SABİT VT ───────────────

    "Sabitler": {
        "pk": "Rowid",                        # ← "Personelid" → "Rowid" (migrations.py: AUTOINCREMENT PK)
        "columns": [
            "Rowid","Kod","MenuEleman","Aciklama"
        ]
        
    },

    "Tatiller": {
        "pk": "Tarih",                        # ← "Personelid" → "Tarih" (migrations.py PK)
        "columns": [
            "Tarih","ResmiTatil"
        ]
        
    },

    "Loglar": {
        "pk": None,                           # ← "Personelid" kaldırıldı (Loglar'da PK yok)
        "columns": [
            "Tarih","Saat","Kullanici","Modul","Islem","Detay"
        ],
        "sync": False                         # Log tablosu sync dışı
    },

    # ─────────────── RKE VT ───────────────

    "RKE_List": {
        "pk": "KayitNo",                      # ← "Personelid" → "KayitNo" (migrations.py PK)
        "columns": [
            "KayitNo","EkipmanNo","KoruyucuNumarasi","AnaBilimDali","Birim",
            "KoruyucuCinsi","KursunEsdegeri","HizmetYili","Bedeni","KontrolTarihi",
            "Durum","Aciklama",               # ← encoding düzeltildi
            "VarsaDemirbasNo",                # ← encoding düzeltildi
            "KayitTarih","Barkod"
        ]
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
        ]
    }

}
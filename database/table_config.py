TABLES = {

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

    "FHSZ_Puantaj" :{
	    "pk": "Personelid",
	    "colums":[
            "Personelid","AdSoyad","Birim","CalismaKosulu",
            "AitYil","Donem","AylikGun","KullanilanIzin",
            "FiiliCalisma(Saat)"
            ]
    },

    "Cihazlar" :{
	    "pk": "Cihazid",
	    "colums":[
            "Cihazid","CihazTipi","Marka","Model","Amac",
            "Kaynak","SeriNo","NDKSeriNo","HizmeteGirisTarihi",
            "RKS","Sorumlusu","Gorevi","NDKLisansNo","BaslamaTarihi",
            "BitisTarihi","LisansDurum","AnaBilimDali","Birim","BulunduguBina",
            "GarantiDurumu","GarantiBitisTarihi","DemirbasNo","KalibrasyonGereklimi",
            "BakimDurum","Durum","Img","NDKLisansBelgesi"]
    },

    "Cihaz_Ariza" :{
	    "pk": "Arizaid",
	    "colums":[
            "Arizaid","Cihazid","BaslangicTarihi","Saat","Bildiren",
            "ArizaTipi","Oncelik","Baslık","ArizaAcikla","Durum","Rapor"]
    },

    "Ariza_Islem" :{
	    "pk": "Islemid",
	    "colums":[
            "Islemid","Arizaid","Tarih","Saat","IslemYapan",
            "IslemTuru","YapilanIslem","YeniDurum","Rapor"]
    },

    "Periyodik_Bakim" :{
	    "pk": "Planid",
	    "colums":[
            "Planid","Cihazid","BakimPeriyodu","BakimSirasi","PlanlananTarih",
            "Bakim","Durum","BakimTarihi","BakimTipi","YapilanIslemler","Aciklama",
            "Teknisyen","Rapor"]
    },

    "Kalibrasyon" :{
	    "pk": "Kalid",
	    "colums":[
            "Kalid","cihazid","Firma","SertifikaNo","YapilanTarih",
            "Gecerlilik","BitisTarihi","Durum","Dosya","Aciklama"]
    },

    "Sabitler" :{
	    "pk": "Personelid",
	    "colums":[
            "Rowid","Kod","MenuEleman","Aciklama"]
    },

    "Tatiller" :{
	    "pk": "Personelid",
	    "colums":[
            "Tarih","ResmiTatil"]
    },

    "Loglar" :{
	    "pk": "Personelid",
	    "colums":[
            "Tarih","Saat","Kullanici","Modul","Islem","Detay"]
    },

    "RKE_List" :{
	    "pk": "Personelid",
	    "colums":[
            "KayitNo","EkipmanNo","KoruyucuNumarasi","AnaBilimDali","Birim",
            "KoruyucuCinsi","KursunEsdegeri","HizmetYili","Bedeni","KontrolTarihi",
            "Durum","Açiklama","VarsaDemirbaşNo","KayitTarih","Barkod"]
    },

    "RKE_Muayene" :{
	    "pk": "Personelid",
	    "colums":[
            "KayitNo","EkipmanNo","FMuayeneTarihi","FizikselDurum","SMuayeneTarihi",
            "SkopiDurum","Aciklamalar","KontrolEden/Unvani","BirimSorumlusu/Unvani","Not","Rapor"]
    }

}

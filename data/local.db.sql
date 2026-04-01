BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "Ariza_Islem" (
	"Islemid"	TEXT,
	"Arizaid"	TEXT,
	"Tarih"	TEXT,
	"Saat"	TEXT,
	"IslemYapan"	TEXT,
	"IslemTuru"	TEXT,
	"YapilanIslem"	TEXT,
	"YeniDurum"	TEXT,
	"Rapor"	TEXT,
	"sync_status"	TEXT DEFAULT 'clean',
	"updated_at"	TEXT,
	PRIMARY KEY("Islemid"),
	FOREIGN KEY("Arizaid") REFERENCES "Cihaz_Ariza"("Arizaid")
);
CREATE TABLE IF NOT EXISTS "AuthAudit" (
	"AuditId"	INTEGER,
	"Username"	TEXT,
	"Success"	INTEGER NOT NULL,
	"Reason"	TEXT,
	"CreatedAt"	TEXT NOT NULL,
	PRIMARY KEY("AuditId" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "Cihaz_Ariza" (
	"Arizaid"	TEXT,
	"Cihazid"	TEXT,
	"BaslangicTarihi"	TEXT,
	"Saat"	TEXT,
	"Bildiren"	TEXT,
	"ArizaTipi"	TEXT,
	"Oncelik"	TEXT,
	"Baslik"	TEXT,
	"ArizaAcikla"	TEXT,
	"Durum"	TEXT,
	"Rapor"	TEXT,
	"sync_status"	TEXT DEFAULT 'clean',
	"updated_at"	TEXT,
	PRIMARY KEY("Arizaid"),
	FOREIGN KEY("Cihazid") REFERENCES "Cihazlar"("Cihazid")
);
CREATE TABLE IF NOT EXISTS "Cihaz_Teknik" (
	"Cihazid"	TEXT,
	"BirincilUrunNumarasi"	TEXT,
	"KurumUnvan"	TEXT,
	"MarkaAdi"	TEXT,
	"EtiketAdi"	TEXT,
	"VersiyonModel"	TEXT,
	"UrunTipi"	TEXT,
	"Sinif"	TEXT,
	"KatalogNo"	TEXT,
	"GmdnTerimKod"	TEXT,
	"GmdnTerimTurkceAd"	TEXT,
	"TemelUdiDi"	TEXT,
	"UrunTanimi"	TEXT,
	"Aciklama"	TEXT,
	"KurumGorunenAd"	TEXT,
	"KurumNo"	TEXT,
	"KurumTelefon"	TEXT,
	"KurumEposta"	TEXT,
	"IthalImalBilgisi"	TEXT,
	"MenseiUlkeSet"	TEXT,
	"IthalEdilenUlkeSet"	TEXT,
	"SutEslesmesiSet"	TEXT,
	"Durum"	TEXT,
	"CihazKayitTipi"	TEXT,
	"UtsBaslangicTarihi"	TEXT,
	"KontroleGonderildigiTarih"	TEXT,
	"KalibrasyonaTabiMi"	TEXT,
	"KalibrasyonPeriyodu"	TEXT,
	"BakimaTabiMi"	TEXT,
	"BakimPeriyodu"	TEXT,
	"MrgUyumlu"	TEXT,
	"IyonizeRadyasyonIcerir"	TEXT,
	"TekHastayaKullanilabilir"	TEXT,
	"SinirliKullanimSayisiVar"	TEXT,
	"SinirliKullanimSayisi"	TEXT,
	"BaskaImalatciyaUrettirildiMi"	TEXT,
	"GmdnTerimTurkceAciklama"	TEXT,
	PRIMARY KEY("Cihazid"),
	FOREIGN KEY("Cihazid") REFERENCES "Cihazlar"("Cihazid")
);
CREATE TABLE IF NOT EXISTS "Cihaz_Teknik_Belge" (
	"Cihazid"	TEXT NOT NULL,
	"BelgeTuru"	TEXT NOT NULL,
	"Belge"	TEXT NOT NULL,
	"BelgeAdi"	TEXT,
	"YuklenmeTarihi"	TEXT,
	"DrivePath"	TEXT,
	"LocalPath"	TEXT,
	PRIMARY KEY("Cihazid","BelgeTuru","Belge"),
	FOREIGN KEY("Cihazid") REFERENCES "Cihazlar"("Cihazid")
);
CREATE TABLE IF NOT EXISTS "Cihazlar" (
	"Cihazid"	TEXT,
	"CihazTipi"	TEXT,
	"Marka"	TEXT,
	"Model"	TEXT,
	"Amac"	TEXT,
	"Kaynak"	TEXT,
	"SeriNo"	TEXT,
	"NDKSeriNo"	TEXT,
	"HizmeteGirisTarihi"	TEXT,
	"RKS"	TEXT,
	"Sorumlusu"	TEXT,
	"Gorevi"	TEXT,
	"NDKLisansNo"	TEXT,
	"BaslamaTarihi"	TEXT,
	"BitisTarihi"	TEXT,
	"LisansDurum"	TEXT,
	"AnaBilimDali"	TEXT,
	"Birim"	TEXT,
	"BulunduguBina"	TEXT,
	"GarantiDurumu"	TEXT,
	"GarantiBitisTarihi"	TEXT,
	"DemirbasNo"	TEXT,
	"KalibrasyonGereklimi"	TEXT,
	"BakimDurum"	TEXT,
	"Durum"	TEXT,
	"Img"	TEXT,
	"NDKLisansBelgesi"	TEXT,
	"sync_status"	TEXT DEFAULT 'clean',
	"updated_at"	TEXT,
	PRIMARY KEY("Cihazid")
);
CREATE TABLE IF NOT EXISTS "Dis_Alan_Calisma" (
	"TCKimlik"	TEXT NOT NULL DEFAULT '',
	"AdSoyad"	TEXT NOT NULL,
	"DonemAy"	INTEGER NOT NULL CHECK("DonemAy" BETWEEN 1 AND 12),
	"DonemYil"	INTEGER NOT NULL CHECK("DonemYil" > 2000),
	"AnaBilimDali"	TEXT NOT NULL DEFAULT '',
	"Birim"	TEXT NOT NULL DEFAULT '',
	"IslemTipi"	TEXT NOT NULL,
	"Katsayi"	REAL NOT NULL,
	"VakaSayisi"	INTEGER NOT NULL CHECK("VakaSayisi" > 0),
	"HesaplananSaat"	REAL NOT NULL,
	"TutanakNo"	TEXT NOT NULL,
	"TutanakTarihi"	TEXT NOT NULL,
	"KayitTarihi"	TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
	"KaydedenKullanici"	TEXT,
	PRIMARY KEY("TCKimlik","DonemAy","DonemYil","TutanakNo")
);
CREATE TABLE IF NOT EXISTS "Dis_Alan_Izin_Ozet" (
	"TCKimlik"	TEXT NOT NULL DEFAULT '',
	"AdSoyad"	TEXT NOT NULL,
	"DonemAy"	INTEGER NOT NULL CHECK("DonemAy" BETWEEN 1 AND 12),
	"DonemYil"	INTEGER NOT NULL CHECK("DonemYil" > 2000),
	"ToplamSaat"	REAL NOT NULL DEFAULT 0.0,
	"IzinGunHakki"	REAL NOT NULL DEFAULT 0.0,
	"HesaplamaTarihi"	TEXT,
	"RksOnay"	INTEGER NOT NULL DEFAULT 0 CHECK("RksOnay" IN (0, 1)),
	"Notlar"	TEXT,
	PRIMARY KEY("TCKimlik","AdSoyad","DonemAy","DonemYil")
);
CREATE TABLE IF NOT EXISTS "Dis_Alan_Katsayi_Protokol" (
	"AnaBilimDali"	TEXT NOT NULL,
	"Birim"	TEXT NOT NULL,
	"GecerlilikBaslangic"	TEXT NOT NULL,
	"Katsayi"	REAL NOT NULL,
	"OrtSureDk"	INTEGER,
	"AlanTipAciklama"	TEXT,
	"AciklamaFormul"	TEXT,
	"ProtokolRef"	TEXT,
	"GecerlilikBitis"	TEXT,
	"Aktif"	INTEGER NOT NULL DEFAULT 1 CHECK("Aktif" IN (0, 1)),
	"KayitTarihi"	TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
	"KaydedenKullanici"	TEXT,
	PRIMARY KEY("AnaBilimDali","Birim","GecerlilikBaslangic")
);
CREATE TABLE IF NOT EXISTS "Dokumanlar" (
	"EntityType"	TEXT NOT NULL,
	"EntityId"	TEXT NOT NULL,
	"BelgeTuru"	TEXT NOT NULL,
	"Belge"	TEXT NOT NULL,
	"DokumanId"	TEXT,
	"DocType"	TEXT,
	"DisplayName"	TEXT,
	"LocalPath"	TEXT,
	"BelgeAciklama"	TEXT,
	"YuklenmeTarihi"	TEXT,
	"DrivePath"	TEXT,
	"IliskiliBelgeID"	TEXT,
	"IliskiliBelgeTipi"	TEXT,
	"sync_status"	TEXT DEFAULT 'clean',
	"updated_at"	TEXT,
	PRIMARY KEY("EntityType","EntityId","BelgeTuru","Belge")
);
CREATE TABLE IF NOT EXISTS "Dozimetre_Olcum" (
	"KayitNo"	TEXT,
	"RaporNo"	TEXT,
	"Periyot"	INTEGER,
	"PeriyotAdi"	TEXT,
	"Yil"	INTEGER,
	"DozimetriTipi"	TEXT,
	"AdSoyad"	TEXT,
	"CalistiBirim"	TEXT,
	"PersonelID"	TEXT,
	"DozimetreNo"	TEXT,
	"VucutBolgesi"	TEXT,
	"Hp10"	REAL,
	"Hp007"	REAL,
	"Durum"	TEXT,
	"OlusturmaTarihi"	TEXT DEFAULT (date('now')),
	"sync_status"	TEXT DEFAULT 'clean',
	"updated_at"	TEXT,
	PRIMARY KEY("KayitNo"),
	FOREIGN KEY("PersonelID") REFERENCES "Personel"("KimlikNo")
);
CREATE TABLE IF NOT EXISTS "FHSZ_Puantaj" (
	"Personelid"	TEXT NOT NULL,
	"AdSoyad"	TEXT,
	"Birim"	TEXT,
	"CalismaKosulu"	TEXT,
	"AitYil"	INTEGER NOT NULL,
	"Donem"	TEXT NOT NULL,
	"AylikGun"	INTEGER,
	"KullanilanIzin"	INTEGER,
	"FiiliCalismaSaat"	REAL,
	"sync_status"	TEXT DEFAULT 'clean',
	"updated_at"	TEXT,
	PRIMARY KEY("Personelid","AitYil","Donem"),
	FOREIGN KEY("Personelid") REFERENCES "Personel"("KimlikNo")
);
CREATE TABLE IF NOT EXISTS "Izin_Bilgi" (
	"TCKimlik"	TEXT,
	"AdSoyad"	TEXT,
	"YillikDevir"	REAL,
	"YillikHakedis"	REAL,
	"YillikToplamHak"	REAL,
	"YillikKullanilan"	REAL,
	"YillikKalan"	REAL,
	"SuaKullanilabilirHak"	REAL,
	"SuaKullanilan"	REAL,
	"SuaKalan"	REAL,
	"SuaCariYilKazanim"	REAL,
	"RaporMazeretTop"	REAL,
	"sync_status"	TEXT DEFAULT 'clean',
	"updated_at"	TEXT,
	PRIMARY KEY("TCKimlik"),
	FOREIGN KEY("TCKimlik") REFERENCES "Personel"("KimlikNo")
);
CREATE TABLE IF NOT EXISTS "Izin_Giris" (
	"Izinid"	TEXT,
	"HizmetSinifi"	TEXT,
	"Personelid"	TEXT,
	"AdSoyad"	TEXT,
	"IzinTipi"	TEXT,
	"BaslamaTarihi"	TEXT,
	"Gun"	INTEGER,
	"BitisTarihi"	TEXT,
	"Durum"	TEXT,
	"sync_status"	TEXT DEFAULT 'clean',
	"updated_at"	TEXT,
	PRIMARY KEY("Izinid"),
	FOREIGN KEY("Personelid") REFERENCES "Personel"("KimlikNo")
);
CREATE TABLE IF NOT EXISTS "Kalibrasyon" (
	"Kalid"	TEXT,
	"Cihazid"	TEXT,
	"Firma"	TEXT,
	"SertifikaNo"	TEXT,
	"YapilanTarih"	TEXT,
	"Gecerlilik"	TEXT,
	"BitisTarihi"	TEXT,
	"Durum"	TEXT,
	"Dosya"	TEXT,
	"Aciklama"	TEXT,
	"sync_status"	TEXT DEFAULT 'clean',
	"updated_at"	TEXT,
	PRIMARY KEY("Kalid"),
	FOREIGN KEY("Cihazid") REFERENCES "Cihazlar"("Cihazid")
);
CREATE TABLE IF NOT EXISTS "Loglar" (
	"Tarih"	TEXT,
	"Saat"	TEXT,
	"Kullanici"	TEXT,
	"Modul"	TEXT,
	"Islem"	TEXT,
	"Detay"	TEXT
);
CREATE TABLE IF NOT EXISTS "NB_Birim" (
	"BirimID"	TEXT,
	"BirimKodu"	TEXT NOT NULL UNIQUE,
	"BirimAdi"	TEXT NOT NULL,
	"BirimTipi"	TEXT NOT NULL DEFAULT 'radyoloji',
	"UstBirimID"	TEXT,
	"Aktif"	INTEGER NOT NULL DEFAULT 1,
	"Sira"	INTEGER NOT NULL DEFAULT 99,
	"Aciklama"	TEXT,
	"created_at"	TEXT NOT NULL DEFAULT (datetime('now')),
	"updated_at"	TEXT,
	"created_by"	TEXT,
	"is_deleted"	INTEGER NOT NULL DEFAULT 0,
	PRIMARY KEY("BirimID"),
	FOREIGN KEY("UstBirimID") REFERENCES "NB_Birim"("BirimID")
);
CREATE TABLE IF NOT EXISTS "NB_BirimAyar" (
	"AyarID"	TEXT,
	"BirimID"	TEXT NOT NULL,
	"GunlukSlotSayisi"	INTEGER NOT NULL DEFAULT 4,
	"GunlukSlotDakika"	INTEGER,
	"CalismaModu"	TEXT NOT NULL DEFAULT 'tam_gun',
	"OtomatikBolunme"	INTEGER NOT NULL DEFAULT 1,
	"GunlukHedefDakika"	INTEGER NOT NULL DEFAULT 420,
	"HaftasonuNobetZorunlu"	INTEGER NOT NULL DEFAULT 1,
	"DiniBayramAtama"	INTEGER NOT NULL DEFAULT 0,
	"HaftasonuCalismaVar"	INTEGER NOT NULL DEFAULT 1,
	"ResmiTatilCalismaVar"	INTEGER NOT NULL DEFAULT 1,
	"DiniBayramCalismaVar"	INTEGER NOT NULL DEFAULT 0,
	"ArdisikGunIzinli"	INTEGER NOT NULL DEFAULT 0,
	"FmMaxSaat"	INTEGER NOT NULL DEFAULT 60,
	"MaxGunlukSureDakika"	INTEGER NOT NULL DEFAULT 720,
	"GeserlilikBaslangic"	TEXT,
	"GeserlilikBitis"	TEXT,
	"created_at"	TEXT NOT NULL DEFAULT (datetime('now')),
	"updated_at"	TEXT,
	PRIMARY KEY("AyarID"),
	UNIQUE("BirimID","GeserlilikBaslangic"),
	FOREIGN KEY("BirimID") REFERENCES "NB_Birim"("BirimID")
);
CREATE TABLE IF NOT EXISTS "NB_BirimPersonel" (
	"ID"	TEXT,
	"BirimID"	TEXT NOT NULL,
	"PersonelID"	TEXT NOT NULL,
	"Rol"	TEXT NOT NULL DEFAULT 'teknisyen',
	"GorevBaslangic"	TEXT NOT NULL,
	"GorevBitis"	TEXT,
	"AnabirimMi"	INTEGER NOT NULL DEFAULT 1,
	"Aktif"	INTEGER NOT NULL DEFAULT 1,
	"Notlar"	TEXT,
	"created_at"	TEXT NOT NULL DEFAULT (datetime('now')),
	"updated_at"	TEXT,
	UNIQUE("BirimID","PersonelID","GorevBaslangic"),
	PRIMARY KEY("ID"),
	FOREIGN KEY("BirimID") REFERENCES "NB_Birim"("BirimID"),
	FOREIGN KEY("PersonelID") REFERENCES "Personel"("KimlikNo")
);
CREATE TABLE IF NOT EXISTS "NB_HazirlikOnay" (
	"OnayID"	TEXT,
	"BirimID"	TEXT NOT NULL,
	"Yil"	INTEGER NOT NULL,
	"Ay"	INTEGER NOT NULL CHECK("Ay" BETWEEN 1 AND 12),
	"Durum"	TEXT NOT NULL DEFAULT 'onaylandi',
	"OnayTarihi"	TEXT NOT NULL,
	"Notlar"	TEXT,
	"created_at"	TEXT NOT NULL DEFAULT (datetime('now')),
	UNIQUE("BirimID","Yil","Ay"),
	PRIMARY KEY("OnayID"),
	FOREIGN KEY("BirimID") REFERENCES "NB_Birim"("BirimID")
);
CREATE TABLE IF NOT EXISTS "NB_MesaiHesap" (
	"HesapID"	TEXT,
	"PersonelID"	TEXT NOT NULL,
	"BirimID"	TEXT NOT NULL,
	"PlanID"	TEXT NOT NULL,
	"Yil"	INTEGER NOT NULL,
	"Ay"	INTEGER NOT NULL CHECK("Ay" BETWEEN 1 AND 12),
	"CalisDakika"	INTEGER NOT NULL DEFAULT 0,
	"HedefDakika"	INTEGER NOT NULL DEFAULT 0,
	"FazlaDakika"	INTEGER NOT NULL DEFAULT 0,
	"DevirDakika"	INTEGER NOT NULL DEFAULT 0,
	"ToplamFazlaDakika"	INTEGER NOT NULL DEFAULT 0,
	"OdenenDakika"	INTEGER NOT NULL DEFAULT 0,
	"DevireGidenDakika"	INTEGER NOT NULL DEFAULT 0,
	"HesapDurumu"	TEXT NOT NULL DEFAULT 'taslak',
	"HesapTarihi"	TEXT,
	"created_at"	TEXT NOT NULL DEFAULT (datetime('now')),
	"updated_at"	TEXT,
	PRIMARY KEY("HesapID"),
	UNIQUE("PersonelID","BirimID","Yil","Ay","PlanID"),
	FOREIGN KEY("BirimID") REFERENCES "NB_Birim"("BirimID"),
	FOREIGN KEY("PersonelID") REFERENCES "Personel"("KimlikNo"),
	FOREIGN KEY("PlanID") REFERENCES "NB_Plan"("PlanID")
);
CREATE TABLE IF NOT EXISTS "NB_MesaiKural" (
	"KuralID"	TEXT,
	"KuralAdi"	TEXT NOT NULL,
	"KuralTuru"	TEXT NOT NULL,
	"Parametre"	TEXT NOT NULL DEFAULT '{}',
	"GeserlilikBaslangic"	TEXT NOT NULL,
	"GeserlilikBitis"	TEXT,
	"Aciklama"	TEXT,
	"created_at"	TEXT NOT NULL DEFAULT (datetime('now')),
	"updated_at"	TEXT,
	PRIMARY KEY("KuralID")
);
CREATE TABLE IF NOT EXISTS "NB_PersonelTercih" (
	"TercihID"	TEXT,
	"PersonelID"	TEXT NOT NULL,
	"BirimID"	TEXT NOT NULL,
	"Yil"	INTEGER NOT NULL,
	"Ay"	INTEGER NOT NULL CHECK("Ay" BETWEEN 1 AND 12),
	"NobetTercihi"	TEXT NOT NULL DEFAULT 'zorunlu',
	"HedefDakika"	INTEGER,
	"HedefTipi"	TEXT NOT NULL DEFAULT 'normal',
	"MaxNobetGun"	INTEGER,
	"TercihVardiyalar"	TEXT,
	"KacinilacakGunler"	TEXT,
	"Notlar"	TEXT,
	"Durum"	TEXT NOT NULL DEFAULT 'taslak',
	"OnaylayanID"	TEXT,
	"OnayTarihi"	TEXT,
	"created_at"	TEXT NOT NULL DEFAULT (datetime('now')),
	"updated_at"	TEXT,
	UNIQUE("PersonelID","BirimID","Yil","Ay"),
	PRIMARY KEY("TercihID"),
	FOREIGN KEY("BirimID") REFERENCES "NB_Birim"("BirimID"),
	FOREIGN KEY("PersonelID") REFERENCES "Personel"("KimlikNo")
);
CREATE TABLE IF NOT EXISTS "NB_Plan" (
	"PlanID"	TEXT,
	"BirimID"	TEXT NOT NULL,
	"Yil"	INTEGER NOT NULL,
	"Ay"	INTEGER NOT NULL CHECK("Ay" BETWEEN 1 AND 12),
	"Versiyon"	INTEGER NOT NULL DEFAULT 1,
	"Durum"	TEXT NOT NULL DEFAULT 'taslak',
	"AlgoritmaVersiyon"	TEXT,
	"OlusturmaParametreleri"	TEXT,
	"Notlar"	TEXT,
	"OnaylayanID"	TEXT,
	"OnayTarihi"	TEXT,
	"created_at"	TEXT NOT NULL DEFAULT (datetime('now')),
	"updated_at"	TEXT,
	"created_by"	TEXT,
	UNIQUE("BirimID","Yil","Ay","Versiyon"),
	PRIMARY KEY("PlanID"),
	FOREIGN KEY("BirimID") REFERENCES "NB_Birim"("BirimID")
);
CREATE TABLE IF NOT EXISTS "NB_PlanSatir" (
	"SatirID"	TEXT,
	"PlanID"	TEXT NOT NULL,
	"PersonelID"	TEXT NOT NULL,
	"VardiyaID"	TEXT NOT NULL,
	"NobetTarihi"	TEXT NOT NULL,
	"Kaynak"	TEXT NOT NULL DEFAULT 'algoritma',
	"NobetTuru"	TEXT NOT NULL DEFAULT 'normal',
	"Durum"	TEXT NOT NULL DEFAULT 'aktif',
	"OncekiSatirID"	TEXT,
	"Notlar"	TEXT,
	"created_at"	TEXT NOT NULL DEFAULT (datetime('now')),
	"updated_at"	TEXT,
	"created_by"	TEXT,
	PRIMARY KEY("SatirID"),
	FOREIGN KEY("OncekiSatirID") REFERENCES "NB_PlanSatir"("SatirID"),
	FOREIGN KEY("PersonelID") REFERENCES "Personel"("KimlikNo"),
	FOREIGN KEY("PlanID") REFERENCES "NB_Plan"("PlanID"),
	FOREIGN KEY("VardiyaID") REFERENCES "NB_Vardiya"("VardiyaID")
);
CREATE TABLE IF NOT EXISTS "NB_Vardiya" (
	"VardiyaID"	TEXT,
	"GrupID"	TEXT NOT NULL,
	"BirimID"	TEXT NOT NULL,
	"VardiyaAdi"	TEXT NOT NULL,
	"BasSaat"	TEXT NOT NULL,
	"BitSaat"	TEXT NOT NULL,
	"SureDakika"	INTEGER NOT NULL,
	"Rol"	TEXT NOT NULL DEFAULT 'ana',
	"MinPersonel"	INTEGER NOT NULL DEFAULT 1,
	"Sira"	INTEGER NOT NULL DEFAULT 1,
	"GeserlilikBaslangic"	TEXT,
	"GeserlilikBitis"	TEXT,
	"Aktif"	INTEGER NOT NULL DEFAULT 1,
	"created_at"	TEXT NOT NULL DEFAULT (datetime('now')),
	"updated_at"	TEXT,
	PRIMARY KEY("VardiyaID"),
	FOREIGN KEY("BirimID") REFERENCES "NB_Birim"("BirimID"),
	FOREIGN KEY("GrupID") REFERENCES "NB_VardiyaGrubu"("GrupID")
);
CREATE TABLE IF NOT EXISTS "NB_VardiyaGrubu" (
	"GrupID"	TEXT,
	"BirimID"	TEXT NOT NULL,
	"GrupAdi"	TEXT NOT NULL,
	"GrupTuru"	TEXT NOT NULL DEFAULT 'zorunlu',
	"Sira"	INTEGER NOT NULL DEFAULT 1,
	"Aktif"	INTEGER NOT NULL DEFAULT 1,
	"created_at"	TEXT NOT NULL DEFAULT (datetime('now')),
	"updated_at"	TEXT,
	UNIQUE("BirimID","GrupAdi"),
	PRIMARY KEY("GrupID"),
	FOREIGN KEY("BirimID") REFERENCES "NB_Birim"("BirimID")
);
CREATE TABLE IF NOT EXISTS "Periyodik_Bakim" (
	"Planid"	TEXT,
	"Cihazid"	TEXT,
	"BakimPeriyodu"	TEXT,
	"BakimSirasi"	INTEGER,
	"PlanlananTarih"	TEXT,
	"Bakim"	TEXT,
	"Durum"	TEXT,
	"BakimTarihi"	TEXT,
	"BakimTipi"	TEXT,
	"YapilanIslemler"	TEXT,
	"Aciklama"	TEXT,
	"Teknisyen"	TEXT,
	"Rapor"	TEXT,
	"SozlesmeId"	TEXT,
	"sync_status"	TEXT DEFAULT 'clean',
	"updated_at"	TEXT,
	PRIMARY KEY("Planid"),
	FOREIGN KEY("Cihazid") REFERENCES "Cihazlar"("Cihazid")
);
CREATE TABLE IF NOT EXISTS "Permissions" (
	"PermissionId"	INTEGER,
	"PermissionKey"	TEXT NOT NULL UNIQUE,
	"Description"	TEXT,
	PRIMARY KEY("PermissionId" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "Personel" (
	"KimlikNo"	TEXT,
	"AdSoyad"	TEXT,
	"DogumYeri"	TEXT,
	"DogumTarihi"	TEXT,
	"HizmetSinifi"	TEXT,
	"KadroUnvani"	TEXT,
	"GorevYeri"	TEXT,
	"KurumSicilNo"	TEXT,
	"MemuriyeteBaslamaTarihi"	TEXT,
	"CepTelefonu"	TEXT,
	"Eposta"	TEXT,
	"MezunOlunanOkul"	TEXT,
	"MezunOlunanFakulte"	TEXT,
	"MezuniyetTarihi"	TEXT,
	"DiplomaNo"	TEXT,
	"MezunOlunanOkul2"	TEXT,
	"MezunOlunanFakulte2"	TEXT,
	"MezuniyetTarihi2"	TEXT,
	"DiplomaNo2"	TEXT,
	"Resim"	TEXT,
	"Diploma1"	TEXT,
	"Diploma2"	TEXT,
	"OzlukDosyasi"	TEXT,
	"Durum"	TEXT,
	"AyrilisTarihi"	TEXT,
	"AyrilmaNedeni"	TEXT,
	"MuayeneTarihi"	TEXT,
	"Sonuc"	TEXT,
	"sync_status"	TEXT DEFAULT 'clean',
	"updated_at"	TEXT,
	PRIMARY KEY("KimlikNo")
);
CREATE TABLE IF NOT EXISTS "Personel_Saglik_Takip" (
	"KayitNo"	TEXT,
	"Personelid"	TEXT,
	"AdSoyad"	TEXT,
	"Birim"	TEXT,
	"Yil"	INTEGER,
	"MuayeneTarihi"	TEXT,
	"SonrakiKontrolTarihi"	TEXT,
	"Sonuc"	TEXT,
	"Durum"	TEXT,
	"RaporDosya"	TEXT,
	"Notlar"	TEXT,
	"DermatolojiMuayeneTarihi"	TEXT,
	"DermatolojiDurum"	TEXT,
	"DahiliyeMuayeneTarihi"	TEXT,
	"DahiliyeDurum"	TEXT,
	"GozMuayeneTarihi"	TEXT,
	"GozDurum"	TEXT,
	"GoruntulemeMuayeneTarihi"	TEXT,
	"GoruntulemeDurum"	TEXT,
	"sync_status"	TEXT DEFAULT 'clean',
	"updated_at"	TEXT,
	PRIMARY KEY("KayitNo"),
	FOREIGN KEY("Personelid") REFERENCES "Personel"("KimlikNo")
);
CREATE TABLE IF NOT EXISTS "RKE_List" (
	"EkipmanNo"	TEXT,
	"KoruyucuNumarasi"	TEXT,
	"AnaBilimDali"	TEXT,
	"Birim"	TEXT,
	"KoruyucuCinsi"	TEXT,
	"KursunEsdegeri"	TEXT,
	"HizmetYili"	INTEGER,
	"Bedeni"	TEXT,
	"KontrolTarihi"	TEXT,
	"Durum"	TEXT,
	"Aciklama"	TEXT,
	"VarsaDemirbasNo"	TEXT,
	"KayitTarih"	TEXT,
	"Barkod"	TEXT,
	"sync_status"	TEXT DEFAULT 'clean',
	"updated_at"	TEXT,
	PRIMARY KEY("EkipmanNo")
);
CREATE TABLE IF NOT EXISTS "RKE_Muayene" (
	"KayitNo"	TEXT,
	"EkipmanNo"	TEXT,
	"FMuayeneTarihi"	TEXT,
	"FizikselDurum"	TEXT,
	"SMuayeneTarihi"	TEXT,
	"SkopiDurum"	TEXT,
	"Aciklamalar"	TEXT,
	"KontrolEdenUnvani"	TEXT,
	"BirimSorumlusuUnvani"	TEXT,
	"Notlar"	TEXT,
	"Rapor"	TEXT,
	"sync_status"	TEXT DEFAULT 'clean',
	"updated_at"	TEXT,
	PRIMARY KEY("KayitNo"),
	FOREIGN KEY("EkipmanNo") REFERENCES "RKE_List"("EkipmanNo")
);
CREATE TABLE IF NOT EXISTS "RolePermissions" (
	"RoleId"	INTEGER NOT NULL,
	"PermissionId"	INTEGER NOT NULL,
	PRIMARY KEY("RoleId","PermissionId"),
	FOREIGN KEY("PermissionId") REFERENCES "Permissions"("PermissionId"),
	FOREIGN KEY("RoleId") REFERENCES "Roles"("RoleId")
);
CREATE TABLE IF NOT EXISTS "Roles" (
	"RoleId"	INTEGER,
	"RoleName"	TEXT NOT NULL UNIQUE,
	PRIMARY KEY("RoleId" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "Sabitler" (
	"Rowid"	TEXT,
	"Kod"	TEXT,
	"MenuEleman"	TEXT,
	"Aciklama"	TEXT,
	"sync_status"	TEXT DEFAULT 'clean',
	"updated_at"	TEXT,
	PRIMARY KEY("Rowid")
);
CREATE TABLE IF NOT EXISTS "Tatiller" (
	"Tarih"	TEXT,
	"ResmiTatil"	TEXT,
	"sync_status"	TEXT,
	"updated_at"	TEXT,
	"TatilTuru"	TEXT
);
CREATE TABLE IF NOT EXISTS "UserRoles" (
	"UserId"	INTEGER NOT NULL,
	"RoleId"	INTEGER NOT NULL,
	PRIMARY KEY("UserId","RoleId"),
	FOREIGN KEY("RoleId") REFERENCES "Roles"("RoleId"),
	FOREIGN KEY("UserId") REFERENCES "Users"("UserId")
);
CREATE TABLE IF NOT EXISTS "Users" (
	"UserId"	INTEGER,
	"Username"	TEXT NOT NULL UNIQUE,
	"PasswordHash"	TEXT NOT NULL,
	"IsActive"	INTEGER NOT NULL DEFAULT 1,
	"MustChangePassword"	INTEGER NOT NULL DEFAULT 0,
	"CreatedAt"	TEXT NOT NULL,
	"LastLoginAt"	TEXT,
	PRIMARY KEY("UserId" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "schema_version" (
	"version"	INTEGER,
	"applied_at"	TEXT NOT NULL,
	"description"	TEXT,
	PRIMARY KEY("version")
);
CREATE INDEX IF NOT EXISTS "idx_nb_birimper_birim" ON "NB_BirimPersonel" (
	"BirimID"
);
CREATE INDEX IF NOT EXISTS "idx_nb_birimper_personel" ON "NB_BirimPersonel" (
	"PersonelID"
);
CREATE INDEX IF NOT EXISTS "idx_nb_satir_personel" ON "NB_PlanSatir" (
	"PersonelID"
);
CREATE INDEX IF NOT EXISTS "idx_nb_satir_plan" ON "NB_PlanSatir" (
	"PlanID"
);
CREATE INDEX IF NOT EXISTS "idx_nb_satir_tarih" ON "NB_PlanSatir" (
	"NobetTarihi"
);
COMMIT;

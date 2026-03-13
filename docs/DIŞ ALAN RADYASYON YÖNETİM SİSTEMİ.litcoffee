# DIŞ ALAN RADYASYON YÖNETİM SİSTEMİ — TODO

> Durum: `[ ]` Bekliyor · `[x]` Tamamlandı · `[~]` Kısmen yapıldı

---

## AŞAMA 0 — Tamamlananlar (Referans)

- [x] `Dis_Alan_Calisma` tablo tanımı (table_config)
- [x] `Dis_Alan_Izin_Ozet` tablo tanımı (table_config)
- [x] `Dis_Alan_Katsayi_Protokol` tablo tanımı (table_config) ← siz eklediniz
- [x] Migration v2 (_migrate_to_v2)
- [x] `dis_alan_service.py` — temel CRUD + izin hesabı
- [x] `dis_alan_import_service.py` — Excel okuma + Dokumanlar arşivi
- [x] `dis_alan_import_page.py` — Excel import UI
- [x] `dis_alan_merkez_page.py` — Tab container
- [x] `puantaj_rapor_page.py` — Puantaj raporu UI (taslak)
- [x] `Dis_Alan_Calisma_Sablonu_v3.xlsx` — Excel şablonu

---

## AŞAMA 1 — Katsayı Protokol Servisi

### 1.1 `dis_alan_katsayi_service.py` (YENİ DOSYA)
**Konum:** `core/services/dis_alan_katsayi_service.py`

- [ ] `get_aktif_katsayi(anabilim_dali, birim)` → dict | None
  - Aktif=1 ve GecerlilikBitis IS NULL veya bugün <= GecerlilikBitis
  - Birden fazla aktif kayıt varsa en son GecerlilikBaslangic'i döndür
- [ ] `get_tum_protokoller()` → list[dict] (yönetim ekranı için)
- [ ] `get_birim_listesi()` → list[tuple[str,str]] (anabilim, birim ikilisi — import dropdown için)
- [ ] `protokol_ekle(veri)` → bool
  - Aynı (AnaBilimDali, Birim, GecerlilikBaslangic) PK varsa reddet
- [ ] `protokol_guncelle(pk, veri)` → bool
  - Geçmişe dönük tarihli kayıt güncellenemez (GecerlilikBaslangic < bugün → sadece AciklamaFormul/ProtokolRef güncellenebilir)
- [ ] `protokol_pasife_al(anabilim_dali, birim)` → bool
  - Aktif=0 yapar, GecerlilikBitis = bugün set eder

### 1.2 `di.py` güncellemesi
- [ ] `get_dis_alan_katsayi_service(db)` fabrika fonksiyonu ekle

---

## AŞAMA 2 — Mevcut Servislerdeki Hatalar

### 2.1 `dis_alan_service.py`
- [ ] `get_calisma_listesi()` — `PersonelKimlik` → `TCKimlik` düzelt (satır 82)
- [ ] `calisma_kaydet()` — PK tuple'ı `PersonelKimlik` → `TCKimlik` düzelt (satır 102)
- [ ] `calisma_kaydet()` — log satırı `PersonelAd` → `AdSoyad` düzelt (satır 114)
- [ ] `ozet_hesapla_ve_kaydet()` — `PersonelKimlik` → `TCKimlik` düzelt (satır 245)
- [ ] `ozet_hesapla_ve_kaydet()` — `PersonelAd` → `AdSoyad` düzelt (satır 246)
- [ ] `get_dis_alan_personeli()` — bu modül Personel tablosundan BAĞIMSIZ,
      metodu kaldır veya `Dis_Alan_Calisma`'dan benzersiz kişi listesi döndürsün

### 2.2 `dis_alan_import_service.py`
- [ ] `KATSAYI_TABLOSU` sabit dict'i kaldır
- [ ] `_satiri_isle()` içinde katsayıyı `DisAlanKatsayiService.get_aktif_katsayi()` ile al
  - Servis bulamazsa → `hatalar.append("Bu birim için aktif katsayı protokolü yok")`
- [ ] `__init__()` parametresine `katsayi_service` ekle
- [ ] `get_birim_listesi()` → katsayı servisinden gelsin (Excel dropdown için de kullanılır)

### 2.3 `dis_alan_import_page.py`
- [ ] Import servisine `katsayi_service` inject et
- [ ] `_kaydet()` → `SessionContext` kullanımını `current_user` yerine projedeki
      mevcut pattern'a göre düzelt (diğer sayfalara bak)

---

## AŞAMA 3 — HBYS Referans Modülü

### 3.1 Tablo: `Dis_Alan_Hbys_Referans`
**Siz ekleyeceksiniz — table_config + migration**

Önerilen kolonlar:
```
AnaBilimDali    TEXT  NOT NULL
Birim           TEXT  NOT NULL
DonemAy         INTEGER
DonemYil        INTEGER
ToplamVaka      INTEGER
OrtIslemSureDk  REAL
PersonelSayisi  INTEGER
CKolluOrani     REAL   -- 0.0-1.0 arası, IT raporundan siz belirlersiniz
ImportTarihi    TEXT
KaynakDosya     TEXT
PK: (AnaBilimDali, Birim, DonemAy, DonemYil)
```

### 3.2 `dis_alan_hbys_service.py` (YENİ DOSYA)
**Konum:** `core/services/dis_alan_hbys_service.py`

- [ ] `excel_import(dosya_yolu)` → IT'den gelen raporu okur, tabloya yazar
- [ ] `get_referans(anabilim_dali, birim, donem_ay, donem_yil)` → dict | None
- [ ] `get_ust_sinir(anabilim_dali, birim, donem_ay, donem_yil)` → float
  - `ToplamVaka × OrtIslemSureDk × CKolluOrani / 60` = birimin max maruziyet havuzu (saat)
  - Bu değer denetim motoruna girecek

---

## AŞAMA 4 — Denetim Motoru

### 4.1 `dis_alan_denetim_service.py` (YENİ DOSYA)
**Konum:** `core/services/dis_alan_denetim_service.py`

Üç katmanlı kontrol — her kontrol bir `DenetimSonucu` döndürür:

```python
@dataclass
class DenetimSonucu:
    katman: int           # 1, 2 veya 3
    kural: str            # "FIZIKSEL_IMKANSIZ", "HBYS_ASIMI" vb.
    seviye: str           # "BILGI", "DIKKAT", "INCELE", "BLOKE"
    mesaj: str
    deger: float          # Bildirilen değer
    beklenen: float       # Referans / sınır değer
    sapma_yuzde: float
```

**Katman 1 — Matematiksel tutarlılık** (HBYS gerekmez)
- [ ] `k1_gun_kontrolu(vaka, ort_sure_dk, donem_ay, donem_yil)` → DenetimSonucu | None
  - `vaka × ort_sure_dk > ay_is_gunu × 480` → BLOKE (fiziksel imkansız)
- [ ] `k1_saat_kontrolu(hesaplanan_saat, donem_ay, donem_yil)` → DenetimSonucu | None
  - `hesaplanan_saat > ay_is_gunu × 8` → BLOKE
- [ ] `k1_onceki_ay_karsilastirma(tc, anabilim, birim, donem_ay, donem_yil)` → DenetimSonucu | None
  - Önceki aya göre %100+ artış → INCELE
  - %50-100 artış → DIKKAT

**Katman 2 — HBYS karşılaştırması** (referans veri varsa)
- [ ] `k2_vaka_kontrolu(bildirilen_vaka, anabilim, birim, donem_ay, donem_yil)` → DenetimSonucu | None
  - `bildirilen_vaka > hbys_toplam_vaka` → BLOKE (beyan edemez)
  - `%80-120 arası` → BILGI
  - `%120-150` → DIKKAT
  - `%150+` → INCELE
- [ ] `k2_ust_sinir_kontrolu(toplam_saat_birim, anabilim, birim, donem_ay, donem_yil)` → DenetimSonucu | None
  - Birimin tüm personelinin toplam saati > HBYS üst sınırı → INCELE

**Katman 3 — Tarihsel kıyaslama** (6+ ay veri varsa)
- [ ] `k3_kisi_profili(tc, anabilim, birim)` → DenetimSonucu | None
  - Son 6 ayın ortalamasının 2 katı üzerinde → INCELE
- [ ] `k3_birim_icindeki_ucukluk(donem_ay, donem_yil, anabilim, birim)` → list[DenetimSonucu]
  - Aynı birimde aynı ay, aynı alan için vaka sayısı ortalamasının 3σ dışında → DIKKAT

**Ana metot:**
- [ ] `denetle(import_sonucu)` → list[DenetimSonucu]
  - Tüm katmanları çalıştırır
  - BLOKE varsa import durur
  - Diğerleri uyarı olarak döner

### 4.2 `di.py` güncellemesi
- [ ] `get_dis_alan_denetim_service(db)` fabrika ekle

---

## AŞAMA 5 — Import Akışına Denetim Entegrasyonu

### 5.1 `dis_alan_import_service.py`
- [ ] `excel_oku()` sonunda `denetim_service.denetle()` çağır
- [ ] `ImportSonucu`'ya `denetim_sonuclari: list[DenetimSonucu]` alanı ekle
- [ ] BLOKE seviyesinde `kaydet()` çağrısı engellenir

### 5.2 `dis_alan_import_page.py`
- [ ] Denetim sonuçlarını ayrı bir panel/sekme olarak göster
- [ ] BLOKE varsa "Seçilileri Kaydet" butonu devre dışı kalsın
- [ ] INCELE/DIKKAT uyarıları onay checkbox'ı yanında ikon olarak gösterilsin
  - 🟡 DIKKAT · 🔴 INCELE · ⛔ BLOKE

---

## AŞAMA 6 — Katsayı Protokol Yönetim UI

### 6.1 `dis_alan_katsayi_page.py` (YENİ DOSYA)
**Konum:** `ui/pages/fhsz/dis_alan_katsayi_page.py`

- [ ] Üst tablo: tüm aktif protokoller (AnaBilimDali, Birim, Katsayı, OrtSüre, ProtokolRef, GecerlilikBaslangic)
- [ ] "Yeni Protokol Ekle" butonu → dialog
  - AnaBilimDali (text)
  - Birim (text)
  - Katsayı (double spinbox, 0.01-1.00)
  - OrtSüreDk (int spinbox)
  - AciklamaFormul (text — formülü açıkla)
  - ProtokolRef (text — uzman görüşü / protokol no)
  - GecerlilikBaslangic (date picker, default bugün)
- [ ] "Pasife Al" butonu → onay sonrası `protokol_pasife_al()`
- [ ] "Tarihçe Göster" butonu → pasif kayıtları da listele
- [ ] Kayıt silme YOK — sadece pasife alma

### 6.2 `dis_alan_merkez_page.py` güncellemesi
- [ ] Yeni sekme ekle: "Katsayı Protokolleri"

---

## AŞAMA 7 — HBYS Import UI

### 7.1 `dis_alan_hbys_import_page.py` (YENİ DOSYA)
**Konum:** `ui/pages/fhsz/dis_alan_hbys_import_page.py`

- [ ] IT'den gelen Excel/CSV'yi seç
- [ ] Kolon eşleştirme: IT raporu farklı başlıklar kullanabilir
  - "Klinik" → AnaBilimDali, "Ameliyathane" → Birim vb.
- [ ] Önizleme tablosu
- [ ] "Kaydet" → `hbys_service.excel_import()`
- [ ] Her import sonrası denetim motorunun referans verisi güncellenir

### 7.2 `dis_alan_merkez_page.py` güncellemesi
- [ ] Yeni sekme: "HBYS Referans Import"

---

## AŞAMA 8 — Puantaj Raporu Tamamlama

### 8.1 `puantaj_rapor_page.py`
- [ ] `_load_data()` → `_rows_cache` yerine her seferinde DB'den çek
      (şu an `showEvent` override yok, veri güncel gelmiyor olabilir)
- [ ] Denetim uyarılarını tabloya ekle — yeni kolon: "Uyarı"
  - BLOKE/INCELE/DIKKAT ikonları
- [ ] Özet satırı: toplam vaka, toplam saat, toplam izin günü
- [ ] RKS onay butonu — seçili satırı `ozet_onayla()` ile onayla
- [ ] Onaylı satırlar farklı renkte gösterilsin (kilitli)
- [ ] Excel export'u geliştir:
  - Şu an sadece tablo içeriği gidiyor
  - Başlık satırı (kurum, dönem, RKS adı) eklensin
  - Onay durumu kolonu eklensin

---

## AŞAMA 9 — Excel Şablonu Güncellemesi

### 9.1 `Dis_Alan_Calisma_Sablonu_v4.xlsx`
- [ ] Tutanak No kolonunu kaldır (artık sistem üretiyor)
- [ ] Çalışılan Alan dropdown'ı → DB'deki aktif katsayı protokollerinden dinamik üretilsin
  - Şu an hardcoded 6 seçenek var
  - Yeni birim eklenince şablon güncellenmeli — ya otomatik üret ya da kılavuza not düş
- [ ] Ort. Süre (dk) kolonunu koru — denetim motoruna girdi sağlıyor
- [ ] Kılavuz sayfasını güncelle — katsayı tablosunu "kurumsal protokole göre belirlenir" notu ile değiştir

---

## AŞAMA 10 — Test & Doğrulama

- [ ] Katsayı servisi unit testi: aktif protokol sorgusu, tarih aralığı
- [ ] Denetim motoru unit testi:
  - K1: 31 günlük ayda 35 günlük iş → BLOKE doğrulanır
  - K2: HBYS'de 100 vaka varken 150 bildirilmiş → INCELE doğrulanır
  - K3: 6 aylık ortalama 20 vaka, bu ay 80 → INCELE doğrulanır
- [ ] Import akışı entegrasyon testi: şablon doldur → oku → denetle → kaydet → puantaj'da gör
- [ ] Çakışma raporu testi: aynı TC, farklı ad → çakışma raporu üretilir

---

## UYGULAMA SIRASI (Önerilen)

```
1. Aşama 2   → Mevcut hataları düzelt (PersonelKimlik/Ad)
2. Aşama 1   → Katsayı servisini yaz
3. Aşama 2.2 → Import servisini katsayı servisine bağla
4. Aşama 6   → Katsayı UI — sisteme ilk protokolleri gir
5. Aşama 3   → HBYS tablo + servis (IT raporu gelince)
6. Aşama 4   → Denetim motoru (K1 önce, K2 HBYS gelince, K3 6 ay sonra)
7. Aşama 5   → Import'a denetim entegrasyonu
8. Aşama 7   → HBYS import UI
9. Aşama 8   → Puantaj raporu tamamlama
10. Aşama 9  → Şablon güncellemesi
11. Aşama 10 → Testler
```

---

## NOTLAR

**Katsayı protokolü kararı:**
Katsayılar radyasyon fiziği uzmanı görüşü + kurumsal protokol olarak imzalanacak.
Sisteme girilmeden önce fiziksel onay alınmalı.
`AciklamaFormul` alanına mutlaka hesap mantığı yazılmalı:
örn. `"45 dk × %47 ışın ≈ 21 dk → 21/60 = 0.35"`

**HBYS raporu:**
IT'den alınacak rapor için önce bir örnek talep et.
Kolon adları kurumdan kuruma değişebilir — kolon eşleştirme UI'ı bu yüzden önemli.

**Denetim motoru aktivasyon takvimi:**
- K1 (matematiksel): Hemen aktif
- K2 (HBYS): IT raporu geldikten sonra
- K3 (tarihsel): 6 ay veri biriktikten sonra

**`CKolluOrani` değeri:**
HBYS tüm ameliyatları sayıyor, sadece C-kollu olanları değil.
Bu oran siz tarafından belirlenmeli (örn. Ortopedi ameliyatlarının %60'ı C-kollu kullanır).
Protokol belgesiyle birlikte kayıt altına alınmal
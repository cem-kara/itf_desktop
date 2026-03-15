# DIŞ ALAN RADYASYON YÖNETİM SİSTEMİ — TODO

> Durum: `[ ]` Bekliyor · `[x]` Tamamlandı · `[~]` Kısmen yapıldı · `[-]` Kaldırıldı / Gerek Kalmadı

---

## AŞAMA 0 — Temel Altyapı

- [x] `Dis_Alan_Calisma` tablo tanımı (table_config)
- [x] `Dis_Alan_Izin_Ozet` tablo tanımı (table_config)
- [x] `Dis_Alan_Katsayi_Protokol` tablo tanımı (table_config)
- [x] `Dis_Alan_Calisma` → `Birim`, `OrtSureDk`, `ToplamSureDk` kolonları eklendi
- [x] Migration v1 (temiz kurulum — tüm tablolar)
- [x] Migration v2 (ALTER TABLE — eksik kolonlar)
- [x] `dis_alan_service.py` — temel CRUD + izin hesabı
- [x] `dis_alan_import_service.py` — Excel okuma + Dokumanlar arşivi
- [x] `Dis_Alan_Calisma_Sablonu.xlsx` — Excel şablonu (B3=AnaBilimDali, B4=Birim, D3=Ay, D4=Yıl)

---

## AŞAMA 1 — Katsayı Protokol Servisi `[x]`

- [x] `dis_alan_katsayi_service.py` oluşturuldu
  - [x] `get_aktif_katsayi(anabilim_dali, birim)` → dict | None
  - [x] `get_tum_aktif_dict()` → thread-safe cache için
  - [x] `get_birim_listesi()` → (anabilim, birim) ikilisi
  - [x] `protokol_ekle(veri)` → bool
  - [x] `protokol_guncelle(pk, veri)` → bool
  - [x] `protokol_pasife_al(anabilim_dali, birim)` → bool
- [x] `di.py` → `get_dis_alan_katsayi_service(db)` fabrikası eklendi

---

## AŞAMA 2 — Mevcut Servis Düzeltmeleri `[x]`

- [x] `dis_alan_service.py` — `PersonelKimlik` → `TCKimlik` düzeltmeleri
- [x] `dis_alan_import_service.py` — `KATSAYI_TABLOSU` sabit dict kaldırıldı
- [x] `dis_alan_import_service.py` — katsayı `DisAlanKatsayiService`'ten alınıyor
- [x] `dis_alan_import_service.py` — `katsayi_cache` thread-safe parametre
- [x] `dis_alan_import_service.py` — Dönem D3/D4 hücrelerinden okunuyor
- [x] `dis_alan_import_service.py` — `Birim`, `OrtSureDk`, `ToplamSureDk` kaydediliyor
- [x] `dis_alan_import_page.py` — `SessionContext` → `getattr` ile güvenli erişim

---

## AŞAMA 3 — HBYS Referans Modülü `[-]`

> **KARAR:** HBYS referans modülü kaldırıldı.
> Katsayı protokolü kurulum sihirbazı üzerinden yönetildiğinden
> ayrı HBYS referans verisi tutmaya gerek kalmadı.
> İleride K2 denetimi istenirse `Dis_Alan_Katsayi_Protokol`'a
> `BeklenenAylikVaka` kolonu eklenerek entegre edilebilir.

- [-] `Dis_Alan_Hbys_Referans` tablo tanımı
- [-] `dis_alan_hbys_service.py`
- [-] `dis_alan_hbys_eslestirme_service.py`
- [-] `dis_alan_hbys_referans_repository.py`
- [-] `dis_alan_hbys_import_page.py`
- [-] `dis_alan_hbys_referans_page.py`

**Temizlenen referanslar:** `di.py`, `table_config.py`, `migrations.py`,
`repository_registry.py`, `main_window.py`, `dis_alan_import_service.py`

---

## AŞAMA 4 — Denetim Motoru `[-]`

> **KARAR:** HBYS referans verisi olmadan K2/K3 katmanları anlamsız.
> K1 (matematiksel kontrol) ileride import servisine doğrudan entegre edilebilir.
> Şimdilik ertelendi.

- [-] `dis_alan_denetim_service.py`
- [-] K1/K2/K3 katmanları
- [ ] **İLERİDE:** K1 matematiksel kontrol import servisine eklenebilir
  - `vaka × ort_sure_dk > ay_is_gunu × 480` → BLOKE
  - Önceki aya göre %100+ artış → UYARI

---

## AŞAMA 5 — Import'a Denetim Entegrasyonu `[-]`

> Aşama 4 ertelendiğinden bu aşama da ertelendi.
> Import karşılaştırma sistemi veri kalitesini farklı bir yöntemle sağlıyor.

---

## AŞAMA 6 — Katsayı Protokol Yönetim UI `[x]`

- [x] `dis_alan_katsayi_page.py` oluşturuldu
  - [x] Tüm aktif protokoller tablosu
  - [x] Yeni protokol ekle dialog
  - [x] Pasife al butonu
  - [x] Tarihçe göster (pasif kayıtlar)
  - [x] Silme yok — sadece pasife alma
- [x] `dis_alan_merkez_page.py` → "Katsayı Protokolleri" sekmesi eklendi

---

## AŞAMA 7 — HBYS Import UI → Birim Kurulum Sihirbazı `[x]`

> **KARAR:** HBYS import UI kaldırıldı.
> Yerine kullanıcı dostu **Birim Kurulum Sihirbazı** eklendi.

- [x] `dis_alan_kurulum_page.py` oluşturuldu
  - [x] Kullanıcı girer: Anabilim Dalı, Birim, Protokol yılı,
        Günlük C-kollu işlem, Günlük toplam işlem, C-kollu süre (dk)
  - [x] Sistem hesaplar: C-kollu oran, Katsayı (`süre × oran / 60`)
  - [x] Canlı önizleme kartları (oran, katsayı)
  - [x] "Hesapla ve Önizle" → "Kaydet ve Uygula" akışı
  - [x] Mevcut protokol çakışma uyarısı
  - [x] Tek tıkla katsayı protokolü oluşturma
- [x] `dis_alan_merkez_page.py` → "Birim Kurulum" sekmesi eklendi

---

## AŞAMA 8 — Import Denetim & Karşılaştırma `[x]`

> **KARAR:** Puantaj raporu yerine import kalite kontrol ekranı önceliklendirildi.
> Veriyi kaynakta temizlemek puantajdan daha kritik.

### 8.1 `dis_alan_import_page.py` — İki sekmeye ayrıldı

**Sekme 1: Excel Import**
- [x] Önceki import uyarısı — dosya **okunduğunda** (kayıt öncesi) uyarı
- [x] `get_registry` yerine doğrudan DB sorgusu (thread-safe)
- [x] Kayıt sonrası karşılaştırma sekmesine yönlendirme

**Sekme 2: Import Karşılaştırma** (`_KarsilastirmaWidget`)
- [x] Dönem/birim filtresi → importları tarihe göre listele
- [x] Liste A ve Liste B seçimi
- [x] Karşılaştır → yan yana tablo
  - ✓ Eşit · ≠ Fark var · ◀ Sadece A · ▶ Sadece B
- [x] Özet kartlar: A/B kişi sayısı, mükerrer, eksik, vaka farkı
- [x] **Listeleri Birleştir:**
  - Sadece B'dekiler A'ya eklenir
  - Fark olanlarda kullanıcı seçim yapar (dialog)
  - B silinir, tek temiz liste kalır
- [x] **Liste Sil:** Seçili listeyi tamamen siler
- [x] **PDF Rapor:** reportlab ile özet + fark tablosu
- [x] **Excel'e Aktar:** openpyxl ile renk kodlu çıktı

### 8.2 `puantaj_rapor_page.py`

- [x] Kişi bazlı özet tablo (her kişi tek satır)
- [x] Anabilim Dalı / Birim / Ay / Yıl filtresi
- [x] Aylık saat, yıllık kümülatif, izin günü hesabı
- [x] Özet istatistik kartları
- [x] Dönem özeti hesapla & kaydet
- [x] RKS onay butonu
- [x] Excel'e aktar

---

## AŞAMA 9 — Excel Şablonu `[x]`

- [x] `Dis_Alan_Calisma_Sablonu.xlsx` güncellendi
  - [x] Tutanak No kolonu kaldırıldı (sistem üretiyor)
  - [x] B3=AnaBilimDali, B4=Birim, D3=Dönem Ay, D4=Dönem Yıl
  - [x] Kolonlar: A=TC Kimlik, B=Ad Soyad, C=Çalışılan Alan, D=Vaka Sayısı

---

## AŞAMA 10 — Test & Doğrulama `[~]`

- [x] Excel import — okuma ve kaydetme doğrulandı
- [x] Birim kurulum sihirbazı → katsayı protokolü oluşturma
- [x] İki farklı Excel import → karşılaştırma sekmesi çalışıyor
- [x] Listeleri birleştirme — fark dialog'u ile doğrulandı
- [x] `Birim` kolonu DB'ye kaydediliyor (v2 migration)
- [x] Önceki import uyarısı (okuma aşamasında) — doğrulandı
- [ ] Dönem özeti hesapla/kaydet → RKS onay akışı testi
- [ ] PDF rapor içerik doğrulaması
- [ ] Katsayı protokolü çakışma senaryosu testi
- [ ] Birleştirme sonrası veri bütünlüğü doğrulaması

---

## MEVCUT DURUM — Merkez Sekmeleri

| # | Sekme | Dosya | Durum |
|---|-------|-------|-------|
| 1 | 📥 Excel Import | `dis_alan_import_page.py` | ✓ Aktif |
| 2 | 🔍 Import Karşılaştırma | `dis_alan_import_page.py` | ✓ Aktif |
| 3 | 📊 Puantaj Raporu | `puantaj_rapor_page.py` | ✓ Aktif |
| 4 | ⚙ Katsayı Protokolleri | `dis_alan_katsayi_page.py` | ✓ Aktif |
| 5 | ⚙ Birim Kurulum | `dis_alan_kurulum_page.py` | ✓ Aktif |

---

## GÜNCEL DOSYA LİSTESİ

### Aktif Servisler (`core/services/`)
| Dosya | Görev |
|-------|-------|
| `dis_alan_service.py` | CRUD + izin hesabı |
| `dis_alan_import_service.py` | Excel okuma + arşiv |
| `dis_alan_katsayi_service.py` | Katsayı protokol yönetimi |

### Kaldırılan Servisler
| Dosya | Neden |
|-------|-------|
| `dis_alan_hbys_service.py` | HBYS modülü kaldırıldı |
| `dis_alan_hbys_eslestirme_service.py` | HBYS modülü kaldırıldı |
| `dis_alan_hbys_referans_service.py` | HBYS modülü kaldırıldı |
| `dis_alan_denetim_service.py` | HBYS bağımlılığı — ertelendi |

### Aktif UI Sayfaları (`ui/pages/fhsz/`)
| Dosya | Görev |
|-------|-------|
| `dis_alan_merkez_page.py` | Tab container (5 sekme) |
| `dis_alan_import_page.py` | Excel import + karşılaştırma |
| `dis_alan_katsayi_page.py` | Protokol yönetimi |
| `dis_alan_kurulum_page.py` | Birim kurulum sihirbazı |
| `puantaj_rapor_page.py` | Kişi bazlı dönem raporu |

---

## İLERİDE YAPILABİLECEKLER

- [ ] **K1 Matematiksel Denetim** — import servisine entegre
  - `vaka × ort_sure_dk > ay_is_gunu × 480` → kaydet butonu devre dışı
  - Önceki aya göre %100+ artış → uyarı ikonu
- [ ] **K2 HBYS Denetimi** — `Dis_Alan_Katsayi_Protokol`'a `BeklenenAylikVaka`
  kolonu eklenerek basit üst sınır kontrolü yapılabilir
- [ ] **K3 Tarihsel Kıyaslama** — 6+ ay veri biriktikten sonra
- [ ] **Dönem Özeti PDF** — puantaj sayfasından resmi çıktı
- [ ] **Toplu RKS Onay** — tüm dönemi tek tıkla onayla

---

## NOTLAR

**Katsayı protokolü:**
Katsayılar radyasyon fiziği uzmanı görüşü + kurumsal protokol olarak imzalanacak.
`AciklamaFormul` alanına mutlaka hesap mantığı yazılmalı:
örn. `"20 dk × 0.636 C-kollu oran / 60 = 0.2121"`

**Birim kurulum sihirbazı:**
Kullanıcı sadece 5 sayı girer (günlük C-kollu işlem, toplam işlem, C-kollu süre).
Sistem C-kollu oranı ve katsayıyı otomatik hesaplar.

**Import karşılaştırma:**
Aynı döneme iki farklı liste geldiğinde:
1. Okuma aşamasında uyarı çıkar
2. Kayıt sonrası karşılaştırma sekmesine yönlendirilir
3. "Birleştir" ile tek temiz liste elde edilir

**Denetim motoru aktivasyon takvimi:**
- K1 (matematiksel): Hazır, entegrasyon bekliyor
- K2 (HBYS üst sınırı): `BeklenenAylikVaka` kolonu eklenince
- K3 (tarihsel): 6 ay veri biriktikten sonra

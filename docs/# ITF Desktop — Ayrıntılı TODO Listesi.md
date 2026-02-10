# ITF Desktop — Ayrıntılı TODO Listesi

Bu dosya, proje üzerinde sonraki düzenlemeleri planlı, güvenli ve hızlı ilerletmek için hazırlanmıştır.

## Önceliklendirme Notasyonu
- **P0 (Kritik):** Hemen yapılmalı, veri/senkronizasyon riski yüksek
- **P1 (Yüksek):** İlk sprint içinde tamamlanmalı
- **P2 (Orta):** Yapısal kalite ve bakım kolaylığı
- **P3 (İyileştirme):** Test/operasyonel olgunluk artırımı

---

## P0 — Kritik

### 1) Sync `clean/dirty` davran???n? d?zelt
**Durum:** Tamamland? (2026-02-10)

**Yap?lanlar**
- `BaseRepository.insert` i?inde `sync_status` zorla `dirty` atamas?n? ko?ullu hale getirildi.
- Sync pull ak???nda gelen `clean` de?erinin ezilmesi engellendi.
- `BaseRepository.update` i?in de ayn? kural uyguland?.

**Neden**
- Pull ile gelen kay?tlar `clean` olmas? gerekirken tekrar `dirty` olursa gereksiz push d?ng?s? ve yanl?? senkron davran??? olu?abilir.

**Dosyalar**
- `database/base_repository.py`
- `docs/DEGISIKLIK_ACIKLAMASI.md`

**DoD (Kar??land?)**
- [x] Pull sonras? local kay?tta `sync_status=clean` korunuyor.
- [x] Ayn? kay?t gereksiz yere tekrar push edilmiyor.

---

### 2) DB reset yerine g?venli migration stratejisine ge?
**Durum:** Tamamland? (2026-02-10)

**Yap?lanlar**
- A??l??taki ?ema kontrol?nde tam reset yakla??m? kald?r?ld?.
- Versiyon tabanl? migration ad?mlar? eklendi.
- Migration ?ncesi otomatik yedekleme ve rollback (yedekten geri y?kleme) ak??? getirildi.

**Neden**
- ?ema uyumsuzlu?unda t?m tablolar?n silinmesi veri kayb? riski do?urur.

**Dosyalar**
- `main.pyw`
- `database/migrations.py`
- `docs/MIGRATION_STRATEJISI.md`
- `docs/MIGRATION_HIZLI_BASVURU.md`

**DoD (Kar??land?)**
- [x] Uyumlu olmayan ?ema, veri silinmeden migration ile g?ncelleniyor.
- [x] Uygulama a??l???nda data kayb? ya?anm?yor.

---

### 3) Sync hata g?r?n?rl???n? art?r
**Durum:** Tamamland? (2026-02-10)

**Yap?lanlar**
- Structured logging ile tablo/ad?m/kay?t say?s? gibi ba?lam bilgileri eklendi.
- 3 ayr? log dosyas? olu?turuldu: `app.log`, `sync.log`, `errors.log`.
- Sync hata sinyali k?sa + detay mesaj? ta??yacak ?ekilde geni?letildi.
- UI taraf?nda status bar + tooltip + popup ile anla??l?r hata g?sterimi eklendi.

**Neden**
- Operasyon s?ras?nda ?sync hatas??n?n k?k nedenini h?zl? bulmak kolayla??r.

**Dosyalar**
- `core/logger.py`
- `database/sync_worker.py`
- `database/sync_service.py`
- `ui/main_window.py`
- `docs/SYNC_HATA_GORUNURLUGU.md`

**DoD (Kar??land?)**
- [x] Hata al?nd???nda kullan?c? neyin bozuldu?unu anlayabiliyor.
- [x] Log sat?r?ndan tablo ve ak?? ad?m? g?r?lebiliyor.

---

## P1 — Yüksek

### 4) `pull_only` tabloları açıkça tanımla
**Yapılacaklar**
- `TABLES` içinde `Sabitler` ve `Tatiller` için `sync_mode: pull_only` netleştir.
- Sync servisinde bu mod için akışı test et.

**Neden**
- Niyetin konfigürasyonda açık olması hata olasılığını düşürür.

**Dosyalar**
- `database/table_config.py`
- `database/sync_service.py`

---

### 5) Menü config ile gerçek kodu hizala
**Yapılacaklar**
- `ayarlar.json` ve `database/ayarlar.json` içindeki modül/sınıf adlarını güncel kodla eşitle.
- Kullanılmayan alanları sadeleştir veya gerçek dinamik yükleme mekanizmasına geçir.

**Neden**
- Konfig-kod drift’i bakım maliyetini artırır ve yanlış beklenti oluşturur.

**Dosyalar**
- `ayarlar.json`
- `database/ayarlar.json`
- `ui/sidebar.py`
- `ui/main_window.py`

---

### 6) Google katmanını modülerleştir
**Yapılacaklar**
- `google_baglanti.py` dosyasını şu alt modüllere böl:
  - `google_auth.py`
  - `google_sheets.py`
  - `google_drive.py`
- Ortak hata sınıflarını tek yerde tut.

**Neden**
- Tek dosyada çok fazla sorumluluk var; test ve hata izolasyonu zor.

**Dosyalar**
- `database/google_baglanti.py` (refactor)
- Yeni modül dosyaları

---

## P2 — Orta

### 7) Dokümantasyonu kodla senkronize et
**Yapılacaklar**
- Mevcut doküman içeriğini gerçek kod durumuna göre güncelle.
- “var olan”/“planlanan” bölümleri ayır.

**Neden**
- Doğru dokümantasyon onboarding ve geliştirme hızını artırır.

**Dosyalar**
- `docs/itf_desktop_proje_dokumantasyonu.md`

---

### 8) Kopya/eski dosyaları temizle
**Yapılacaklar**
- `base_repository1.py`, `sync_service1.py` gibi kopya dosyaları kaldır ya da `archive/` altına taşı.
- Aktif olmayan dosyaları README’de not et.

**Neden**
- Yanlış dosyayı düzenleme riski azalır, repo sadeleşir.

**Dosyalar**
- `database/base_repository1.py`
- `database/sync_service1.py`

---

### 9) Büyük UI dosyalarını parçalara ayır
**Yapılacaklar**
- Personel modülü sayfalarını bileşenlere böl:
  - tablo model
  - filtre paneli
  - dialog/form parçaları
  - servis yardımcıları

**Neden**
- Okunabilirlik, test edilebilirlik ve yeniden kullanım artar.

**Dosyalar**
- `ui/pages/personel/*.py`

---

## P3 — İyileştirme

### 10) Sync entegrasyon testleri ekle
**Yapılacaklar**
- Senaryolar:
  - dirty kayıt push
  - remote update pull
  - composite PK doğrulama
  - çakışma çözümü

**Neden**
- Sync katmanı kritik; regresyon riski yüksek.

---

### 11) Hesaplama modülü birim testleri
**Yapılacaklar**
- `sua_hak_edis_hesapla`, `is_gunu_hesapla`, `ay_is_gunu` için sınır ve örnek vaka testleri yaz.

**Neden**
- İzin/FHSZ hesaplarında doğruluk kritik iş gereksinimi.

**Dosyalar**
- `core/hesaplamalar.py`
- `tests/` (yeni)

---

### 12) Log standardizasyonu
**Durum:** K?smi (2026-02-10)

**Yap?lanlar**
- Structured logging ile tablo/ad?m/kay?t say?s? ba?lam? eklendi.
- Sync ad?mlar? i?in standart log ?ablonu uygulanmaya ba?lad?.

**Yap?lacaklar**
- Olay ?emas?n? `event`, `table`, `record_key`, `result`, `error_code` alanlar?n? kapsayacak ?ekilde tamamla.
- `record_key` ve `error_code` standard?n? t?m kritik loglarda zorunlu hale getir.

**Neden**
- ?retimde olay analizi ve hata ay?klama h?zlan?r.

---
---

## Sprint Plan? ?nerisi
- **Sprint 1:** P0 (1, 2, 3) ? Tamamland? (2026-02-10)
- **Sprint 2:** P1 (4, 5, 6)
- **Sprint 3:** P2 (7, 8, 9)
- **Sprint 4:** P3 (10, 11, 12)

---

## Her Task için Kısa Kontrol Listesi
- [ ] Kod değişikliği tamamlandı
- [ ] Otomatik/manuel test tamamlandı
- [ ] Log doğrulaması yapıldı
- [ ] Dokümantasyon güncellendi
- [ ] Geri dönüş (rollback) notu eklendi

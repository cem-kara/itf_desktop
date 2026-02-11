# ITF Desktop — Ayrıntılı TODO Listesi

Bu dosya, proje üzerinde sonraki düzenlemeleri planlı, güvenli ve hızlı ilerletmek için hazırlanmıştır.

## Önceliklendirme Notasyonu
- **P0 (Kritik):** Hemen yapılmalı, veri/senkronizasyon riski yüksek
- **P1 (Yüksek):** İlk sprint içinde tamamlanmalı
- **P2 (Orta):** Yapısal kalite ve bakım kolaylığı
- **P3 (İyileştirme):** Test/operasyonel olgunluk artırımı

---

## P0 — Kritik

### 1) Sync `clean/dirty` davranışını düzelt
**Yapılacaklar**
- `BaseRepository.insert` içinde `sync_status` zorla `dirty` atamasını koşullu hale getir.
- Sync pull akışında gelen `clean` değerinin ezilmesini engelle.

**Neden**
- Pull ile gelen kayıtlar `clean` olması gerekirken tekrar `dirty` olursa gereksiz push döngüsü ve yanlış senkron davranışı oluşabilir.

**Dosyalar**
- `database/base_repository.py`
- `database/sync_service.py`

**DoD (Done tanımı)**
- Pull sonrası local kayıtta `sync_status=clean` korunuyor.
- Aynı kayıt değişiklik yoksa gereksiz yere tekrar push edilmemiş oluyor.
- Kullanıcı kayıt üzerinde değişiklik yaptığında kayıt `dirty` oluyor, bir sonraki sync’te push ediliyor ve başarılı push sonrası tekrar `clean` durumuna dönüyor.

## 📝 Notlar

- `sync_service.py` dosyasında değişiklik yapılmadı
- Tüm değişiklikler geriye dönük uyumlu
- Mevcut veri üzerinde herhangi bir migrasyon gerekmez
- Test senaryolarının tümü başarılı olmalı

## ✅ Definition of Done (DoD)

- [x] Pull sonrası local kayıtta `sync_status=clean` korunuyor
- [x] Aynı kayıt değişiklik yoksa gereksiz yere tekrar push edilmiyor
- [x] Kullanıcı kayıt üzerinde değişiklik yaptığında kayıt `dirty` oluyor
- [x] Başarılı push sonrası kayıt tekrar `clean` durumuna dönüyor
- [x] Conflict durumunda (local dirty + remote değişmiş) kullanıcı versiyonu korunuyor

---

### 2) DB reset yerine güvenli migration stratejisine geç
**Yapılacaklar**
- Açılıştaki şema kontrolünde tam reset yaklaşımını kaldır.
- Versiyon tabanlı migration adımları (`ALTER TABLE`, yeni kolon ekleme vb.) uygula.
- Kritik migration’larda yedekleme/rollback planı ekle.

**Neden**
- Şema uyumsuzluğunda tüm tabloların silinmesi veri kaybı riski doğurur.

**Dosyalar**
- `main.pyw`
- `database/migrations.py`

**DoD**
- Uyumlu olmayan şema, veri silinmeden migration ile güncelleniyor.
- Uygulama açılışında data kaybı yaşanmıyor.

**Durum / Notlar**
- ## ✅ Definition of Done (DoD)

- [x] Uyumlu olmayan şema, veri silinmeden migration ile güncelleniyor
- [x] Uygulama açılışında data kaybı yaşanmıyor
- [x] Her migration öncesi otomatik yedekleme yapılıyor
- [x] Rollback mekanizması mevcut
- [x] Versiyon takibi schema_version tablosu ile yapılıyor
- [x] Eski yedekler otomatik temizleniyor (son 10 tutulur)
- [x] İlk kurulum sorunsuz çalışıyor
- [x] Mevcut veritabanından güncelleme sorunsuz çalışıyor
- [x] Zaten güncel şema anında başlıyor

**Detaylı Notlar (Migration Stratejisi)**
- Versiyon akışı: v0 (yok) → v1 (temel tablolar) → v2 (`sync_status`, `updated_at` kolonları).
- Uygulama başlangıcı `run_migrations()` ile gerekli adımları uygular, reset yok.
- DB versiyonu koddan büyükse uyarı verilir ve açılış engellenir (veri bütünlüğü korunur).
- Otomatik yedekleme dizini: `data/backups/` (son 10 yedek tutulur).
- Geri yükleme akışı: mevcut DB yedeklenir, istenen yedek `data/itf_desktop.db` olarak kopyalanır.

**Test Senaryoları**
- İlk kurulum: DB yok → v0→v1→v2.
- Eski şema: v1 DB → v2'ye otomatik migration + yedek.
- Güncel şema: v2 DB → migration atlanır.

---

### 3) Sync hata görünürlüğünü artır
**Yapılacaklar**
- Sync hata mesajında tablo adı, hata tipi ve zaman bilgisini UI’da göster.
- Status bar + kullanıcıya anlaşılır kısa hata metni sağla.
- Loglarda hata kodu / bağlam bilgisi standardize et.

**Neden**
- Operasyon sırasında “sync hatası”nın kök nedenini hızlı bulmak kolaylaşır.

**Dosyalar**
- `database/sync_worker.py`
- `ui/main_window.py`
- `core/logger.py`

**DoD**
- Hata alındığında kullanıcı neyin bozulduğunu anlayabiliyor.
- Log satırından tablo ve akış adımı görülebiliyor.

**Durum / Notlar**
✅ Hata alındığında kullanıcı neyin bozulduğunu anlayabiliyor
✅ Log satırından tablo ve akış adımı görülebiliyor
✅ Status bar + kullanıcıya anlaşılır kısa hata metni sağlanıyor
✅ Loglarda hata kodu / bağlam bilgisi standardize edildi
✅ 3 ayrı log dosyası ile kolay debugging
✅ Kullanıcıya çözüm önerileri sunuluyor
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

## ✅ Definition of Done (DoD)

- [x] Hata alındığında kullanıcı neyin bozulduğunu anlayabiliyor
- [x] Log satırından tablo ve akış adımı görülebiliyor
- [x] Kullanıcıya anlaşılır kısa hata metni sağlanıyor
- [x] Status bar'da özet bilgi, tooltip'te detay var
- [x] Popup'ta çözüm önerileri sunuluyor
- [x] 3 ayrı log dosyası oluşturuluyor (app, sync, errors)
- [x] Her sync adımı structured logging ile loglanıyor
- [x] Hatalar tablo bazında izole ediliyor
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

## ✅ Definition of Done (DoD)

- [x] Kullanılmayan `modul` ve `sinif` alanları kaldırıldı
- [x] `implemented` flag eklendi
- [x] Icon typo'ları düzeltildi (Ariza → Arıza, Bakim → Bakım)
- [x] Hata yönetimi geliştirildi (logging)
- [x] Config-kod drift minimize edildi
- [x] Dokümantasyon hazırlandı
- [x] Implementation status belgelendi
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

Definition of Done (DoD)

 ✅ Tek dosya 6 modüle bölündü
 ✅ Her modül tek sorumluluk prensibine uyuyor
 ✅ Thread-safe singleton pattern'ler korundu
 ✅ Geriye dönük uyumluluk sağlandı
 ✅ Public API init.py'de tanımlandı
 ✅ Dokümantasyon hazırlandı
 ✅ Test örnekleri eklendi
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
**Yapılacaklar**
- Yapılandırılmış log formatı (event adı, tablo, kayıt anahtarı, hata kodu) tanımla.
- Sync adımları için standart log şablonu uygula.

**Neden**
- Üretimde olay analizi ve hata ayıklama hızlanır.

---

## Sprint Planı Önerisi
- **Sprint 1:** P0 (1, 2, 3)
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

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

## ✅ Definition of Done (DoD)

- [x] Uyumlu olmayan şema, veri silinmeden migration ile güncelleniyor
- [x] Uygulama açılışında data kaybı yaşanmıyor
- [x] Her migration öncesi otomatik yedekleme yapılıyor
- [x] Rollback mekanizması mevcut
- [x] Versiyon takibi schema_version tablosu ile yapılıyor
- [x] Eski yedekler otomatik temizleniyor (son 10 tutulur)
- [x] İlk kurulum sorunsuz çalışıyor
- [x] Mevcut veritabanından güncelleme sorunsuz çalışıyor
- [x] Zaten güncel şema anında başlıyor
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

- [x] `table_config.py`'de Sabitler ve Tatiller `sync_mode: "pull_only"` ile tanımlandı
- [x] `sync_service.py`'de pull_only mantığı iyileştirildi
- [x] Detaylı loglama eklendi (pull_only_start, read, complete)
- [x] Hata yönetimi geliştirildi (satır bazında resilience)
- [x] İstatistik takibi eklendi
- [x] Worksheet bulunamama durumu handle edildi
- [x] Dokümantasyon hazırlandı
- [x] Test senaryoları tanımlandı

## 🚀 Özet

Pull-only tablolar artık:
- ✅ Açıkça tanımlanmış (`sync_mode: "pull_only"`)
- ✅ Detaylı loglanıyor
- ✅ Hatalara dayanıklı
- ✅ İstatistikleri takip ediliyor
- ✅ Dokümante edilmiş

**Sonuç:** Pull-only modunun niyeti konfigürasyonda net, davranışı tahmin edilebilir ve hata durumları iyi yönetiliyor! 🎉
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

## 📈 Özet

| Özellik | Önce | Sonra |
|---------|------|-------|
| **Config karmaşıklığı** | Yüksek (modul, sinif) | Düşük (sadece baslik, icon) |
| **Sayfa durumu** | Belirsiz | Açık (implemented flag) |
| **Icon eşleşmesi** | Hatalı (typo'lar) | Doğru (Türkçe karakterler) |
| **Hata yönetimi** | Sessiz başarısızlık | Loglama |
| **Config-kod drift** | Yüksek risk | Düşük risk |
| **Maintainability** | Orta | Yüksek |

**Sonuç:** Menü konfigürasyonu artık **basit, güncel ve maintainable**! 🎉
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

### 6.1) Offline / Online Mod Geçişi (Yeni)
**Yapılacaklar**
- İlk kurulum/ayar seviyesinde `app_mode` (`offline|online`) kararı.
- Bulut erişimini tek arayüzde toplama (`CloudAdapter`).
- Sync ve Google Drive çağrılarını adapter üstünden yürütme.
- Offline modda UI davranışlarını kontrollü kapatma/fallback.

**Durum (2026-02-17)**
- [x] Aşama 1: `AppConfig` içine mode çözümleme eklendi.
- [x] Aşama 1: `ITF_APP_MODE` + `ayarlar.json(app_mode)` + credentials fallback aktif.
- [x] Aşama 2: `database/cloud_adapter.py` eklendi (`OnlineCloudAdapter`, `OfflineCloudAdapter`).
- [x] Aşama 2: `core/di.py` içine `get_cloud_adapter()` eklendi.
- [x] Aşama 2: `ui/main_window.py` offline modda sync başlatmayı engelliyor.
- [ ] Aşama 3: `database/sync_service.py` ve `database/gsheet_manager.py` adapter-aware refactor.
- [ ] Aşama 4: UI katmanındaki doğrudan `GoogleDriveService()` çağrılarının adapter’a taşınması.
- [ ] Aşama 5: Ayarlar ekranından mode değişimi + kullanıcı akışı.
- [ ] Aşama 6: Test ve dokümantasyon tamamlayıcıları.

---

## P2 — Orta

### 7) Dokümantasyonu kodla senkronize et
**Yapılacaklar**
- Mevcut doküman içeriğini gerçek kod durumuna göre güncelle.
- “var olan”/“planlanan” bölümleri ayır.
- Modül bazlı mükerrer dokümanları tek kanonik dosyada birleştir.

**Neden**
- Doğru dokümantasyon onboarding ve geliştirme hızını artırır.

**Dosyalar**
- `docs/proje_dokumantasyonu.md`
- `docs/OPERASYON_VE_RAPORLAMA_MERKEZI.md`

## ✅ Definition of Done (DoD)

- [x] Dokümantasyon içerikleri kodla senkronize edildi
- [x] Modül dokümanları `docs/proje_dokumantasyonu.md` içinde birleştirildi

---

### 8) Kopya/eski dosyaları temizle
**Yapılacaklar**
- `base_repository1.py`, `sync_service1.py` gibi kopya dosyaları kaldır ya da `archive/` altına taşı.
- Aktif olmayan dosyaları README’de not et.
- Dokümantasyonda mükerrer modül dosyalarını tek kanonik dosyada birleştir.

**Neden**
- Yanlış dosyayı düzenleme riski azalır, repo sadeleşir.

**Dosyalar**
- `database/base_repository1.py`
- `database/sync_service1.py`
- `docs/proje_dokumantasyonu.md`
- `docs/OPERASYON_VE_RAPORLAMA_MERKEZI.md`
- `README.md`

## ✅ Definition of Done (DoD)

- [x] Kopya dosya isimleri kontrol edildi (aktif kod tabanında `base_repository1.py` / `sync_service1.py` bulunmuyor)
- [x] Mükerrer modül dokümanları `docs/proje_dokumantasyonu.md` içinde birleştirildi
- [x] Ayrı modül doküman dosyaları temizlendi
- [x] README doküman yönlendirmeleri güncellendi

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

---

## Güncel Proje Takip — Son Durum (16 Şubat 2026)
Aşağıda workspace içi en son yapılacaklar listesi ve durumları yer alır. Bu bölüm elle güncellenebilir ve sprint takibinde kullanılabilir.

- [x] Kod tabanını keşfet
- [x] Temel modülleri oku (core, database, ui)
- [x] Bulguları topla ve analiz et
- [x] Detaylı geliştirme raporu hazırla
- [x] Öncelikli iyileştirme önerileri + tahminler
- [x] `requirements.txt` oluştur
- [x] Secrets temizle ve `.gitignore`
- [x] `README.md` ekle
- [x] Dokümantasyonları birleştir ve sadeleştir
- [x] `README.md` doküman haritasını güncelle
- [x] `TODO.md` doküman maddelerini güncelle
- [x] Unit test: `core/hesaplamalar.py`
- [x] CI: lint + test workflow
- [x] `RepositoryRegistry` DI refactor
- [x] Tiplendirme: `mypy` entegrasyonu
- [x] Log rotasyonu ve retention
- [ ] Paketleme / dağıtım betikleri
- [ ] Backups & secrets güvenlik incelemesi

### Kısa Notlar
- Önerilen ilk adımlar: `Secrets temizle ve .gitignore` → `requirements.txt` → `Unit test: core/hesaplamalar.py`.
- Her öğe için tahmini çaba ve DoD (Definition of Done) bu dosyaya eklenebilir.

---

_Not: Bu bölüm manuel olarak güncellenebilir; eklemek istediğiniz başka bir format (ör. CSV, GitHub Issues, proje tablosu) isterseniz söyleyin, dönüştüreyim._

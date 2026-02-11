# ITF Desktop — Güncel TODO Yeniden İnceleme Raporu

Bu rapor, güncellenen TODO listesinin (**TODO.md**) yeniden değerlendirilmesi için hazırlanmıştır.
Amaç; her maddenin mevcut kod tabanındaki karşılığını kontrol etmek, risk seviyesini netleştirmek ve uygulanabilir bir icra planı çıkarmaktır.

---

## 1) Yönetici Özeti

- TODO yapısı doğru önceliklenmiş: kritik riskler önce senkronizasyon ve veri bütünlüğü tarafında toplanıyor.
- En yüksek operasyonel risklerden ikisi (sync clean/dirty akışı ve reset yerine migration) artık uygulama tarafında kapatılmış durumda.
- P1/P2 maddelerinin bir kısmı “niyet olarak” listede var ama kodda henüz tamamlanmış değil (özellikle `pull_only` config netliği, Google katmanının modülerleşmesi, dokümantasyon uyumu).
- Test tarafı (özellikle sync entegrasyon testleri) henüz yeterli değil; bu durum değişikliklerden sonra regresyon riskini artırıyor.

---

## 2) İnceleme Kapsamı ve Yöntemi

Aşağıdaki yaklaşım izlendi:

1. Güncel TODO maddeleri öncelik bazında tek tek okundu.
2. Her madde için ilgili kod dosyaları açılıp mevcut davranış doğrulandı.
3. Her maddenin durumu için sınıflandırma yapıldı:
   - **Açık:** Henüz çözülmemiş
   - **Kısmi:** Başlangıç var ama DoD seviyesine ulaşmamış
   - **Tamamlandı:** TODO’daki kabul kriterleri büyük ölçüde karşılanmış
4. Her maddeye kısa risk notu ve uygulanabilir öneri eklendi.

---

## 3) Öncelik Bazlı Bulgular

## P0 — Kritik

### P0.1 Sync `clean/dirty` davranışı
**Durum:** Tamamlandı

**Gözlem:**
- Pull akışında `remote["sync_status"] = "clean"` değeri korunuyor.
- `local_status == "dirty"` ise pull atlanıyor; kullanıcı değişikliği bozulmuyor.
- Değişiklik yoksa gereksiz `dirty`/push döngüsü oluşmuyor.

**Risk:**
- Kapanmış durumda; yalnızca regresyon riski kaldı.

**Öneri:**
- Davranışın kalıcı olması için küçük bir regresyon testi önerilir.

---

### P0.2 DB reset yerine migration
**Durum:** Tamamlandı

**Gözlem:**
- `migrations.py` versiyon tabanlı hale getirildi; otomatik yedekleme ve rollback mevcut.
- `main.pyw` açılış kontrolü `run_migrations()` ile güvenli akışa alındı.
- `schema_version` tablosu ile versiyon takibi yapılıyor, eski yedekler otomatik temizleniyor (son 10).

**Risk:**
- Kapanmış durumda; yalnızca migration adımlarının doğruluğu ve test kapsamı riski kaldı.

**Öneri:**
- v0→v2, v1→v2, v2→v2 ve v3→v2 senaryoları için smoke testleri periyodik çalıştırın.

---

### P0.3 Sync hata görünürlüğü
**Durum:** Kısmi

**Gözlem:**
- Worker katmanında hata sinyali var.
- UI tarafında hata durumuna geçiliyor; ancak kullanıcıya hata içeriği (tablo adı/hata tipi) gösterilmiyor.
- Logger formatı genel düzeyde, olay bağlamı standardı henüz sınırlı.

**Risk:**
- Operasyon sırasında kök nedeni bulma süresi uzuyor.

**Öneri:**
- `error` sinyali mesajını status bar/tool-tip veya kısa toast ile kullanıcıya göster.
- Log formatını event-id/tablo/akış-adımı içerecek şekilde standardize et.

---

## P1 — Yüksek

### P1.4 `pull_only` tabloların açık tanımı
**Durum:** Açık

**Gözlem:**
- Sync servisinde `sync_mode == "pull_only"` koşulu var.
- Fakat `TABLES` içinde `Sabitler` ve `Tatiller` için bu alan açıkça tanımlı değil.

**Risk:**
- Konfigürasyon niyeti koddan farklı algılanabilir.

**Öneri:**
- `table_config.py` içinde iki tabloya da `sync_mode: pull_only` eklenmeli.

---

### P1.5 Menü config ve kod hizası
**Durum:** Kısmi

**Gözlem:**
- Sidebar ve MainWindow üzerinden sayfa yönlendirme var.
- `ayarlar.json` / `database/ayarlar.json` ile dinamik yükleme davranışının kapsamı net değil.

**Risk:**
- Konfigürasyon drift’i
- Yeni geliştiriciler için yanlış beklenti

**Öneri:**
- Kullanılan config anahtarları envanteri çıkarılsın.
- Kullanılmayan anahtarlar kaldırılıp tek kaynak ilkesi uygulanmalı.

---

### P1.6 Google katmanını modülerleştirme
**Durum:** Açık

**Gözlem:**
- Google entegrasyonu ağırlıklı tek dosya yaklaşımıyla ilerliyor.
- `sync_service` içinde doğrudan `google_baglanti` import edilen yerler var.

**Risk:**
- Hata izolasyonu zor
- Test yazmak ve mocklamak maliyetli

**Öneri:**
- Auth / Sheets / Drive ayrımı yapılarak küçük modüllere bölünmeli.

---

## P2 — Orta

### P2.7 Dokümantasyon-kod senkronu
**Durum:** Açık

**Gözlem:**
- Projede birden fazla doküman var; “mevcut” ve “planlanan” ayrımı tüm belgelerde tutarlı değil.

**Öneri:**
- Her ana dokümana “Current State / Planned State” başlık standardı eklenmeli.

---

### P2.8 Kopya/eski dosya temizliği
**Durum:** Açık

**Gözlem:**
- `base_repository1.py`, `sync_service1.py` gibi yedek/kopya dosyalar mevcut.

**Risk:**
- Yanlış dosyada geliştirme yapılması

**Öneri:**
- Arşiv klasörüne taşıma veya tamamen kaldırma + README notu.

---

### P2.9 Büyük UI dosyalarını parçalama
**Durum:** Açık

**Gözlem:**
- Personel modülü sayfaları ve ana pencere dosyası büyümeye açık.

**Öneri:**
- Sayfa bazlı service/helpers ve reusable component ayrımı ile kademeli refactor.

---

## P3 — İyileştirme

### P3.10 Sync entegrasyon testleri
**Durum:** Açık

**Öneri:**
- Önce mock GSheet katmanı ile deterministik testler, sonra gerçek servis smoke test.

### P3.11 Hesaplama modülü birim testleri
**Durum:** Açık

**Öneri:**
- `core/hesaplamalar.py` için sınır değer (tarih geçişleri, ay sonu, negatif durumlar) testleri eklenmeli.

### P3.12 Log standardizasyonu
**Durum:** Açık

**Öneri:**
- Ortak log şeması (`event`, `table`, `record_key`, `result`, `error_code`) tanımlanmalı.

---

## 4) Güncellenmiş Eylem Planı (Öneri)

### Faz A (Hızlı Risk Düşürme — 2-3 gün)
1. `pull_only` config netliği
2. Sync hata mesajının UI’da görünür hale getirilmesi

### Faz B (Veri Güvenliği — 3-5 gün)
1. Migration akışının periyodik smoke testleri
2. Backup ve rollback adımlarının dokümantasyon uyumu

### Faz C (Bakım Kolaylığı — 1 sprint)
1. Google katmanını bölme
2. Kopya dosyaları temizleme
3. Dokümantasyon standardizasyonu

### Faz D (Kalite Kapısı — sürekli)
1. Sync entegrasyon testleri
2. Hesaplama birim testleri
3. Log standardı ve izleme

---

## 5) Sonuç

Güncellenen TODO listesi teknik açıdan doğru yönde ve öncelik sıralaması anlamlı.
P0 başlıklarında iki kritik risk (sync state doğruluğu ve migration) uygulama tarafında kapatılmış durumda.
Kalan risk ağırlığı P0.3 (sync hata görünürlüğü) ve P1/P2 kalite/konfig uyumu tarafında.
Önerilen faz planı izlenirse kısa vadede operasyonel görünürlük artar, orta vadede bakım maliyeti düşer.

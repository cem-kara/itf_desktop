# REPYS Teknik Durum ve Yol Haritası Raporu

**Tarih:** 2026-02-24  
**Kapsam:** Kod tabanı incelemesi, mevcut durum analizi, riskler ve iyileştirme önerileri

---

## 1) Yönetici Özeti

REPYS; PySide6 tabanlı, masaüstü odaklı, **personel + cihaz + RKE** alanlarını aynı çatı altında birleştiren modüler bir uygulama. Mimari olarak `core` (iş kuralları), `database` (repository/senkron/migration), `ui` (sayfalar/bileşenler/tema) katmanlarına ayrılmış durumda. Kod tabanında fonksiyonel kapsam geniş, migration ve offline çalışma yaklaşımı olgun; ancak test otomasyonu, gözlemlenebilirlik (metrics), hata toparlama senaryoları ve sürdürülebilir UI standardizasyonu alanlarında belirgin geliştirme fırsatları mevcut.

Kısa vadede en yüksek etki sağlayacak adımlar:
1. **Test katmanı inşası** (repository + servis birim testleri),
2. **Offline/online davranışlarının net ürün sözleşmesi** (özellikle upload/sync hata akışları),
3. **Dokümante edilmiş operasyon runbook’u** (backup/restore, migration rollback, sync troubleshooting),
4. **UI teknik borçlarının azaltılması** (inline style ve büyük ekran sınıfları parçalama).

---

## 2) Mimari Durum (Mevcut Yapı)

### 2.1 Katmanlar

- **Giriş & yaşam döngüsü:** `main.pyw`
  - Uygulama başlarken log yönetimi başlatılıyor, DB migration kontrolü yapılıyor, tema uygulanıyor, ana pencere açılıyor.
  - Kapanışta `temp` klasörü temizleniyor.
- **Core katmanı:** konfigürasyon, yol yönetimi, logger, hesaplama, rapor ve özet servisleri.
- **Database katmanı:**
  - SQLite + WAL,
  - `RepositoryRegistry` ile tablo bazlı repository çözümleme,
  - `MigrationManager` ile sürüm kontrollü şema yönetimi,
  - Google Sheets/Drive ile online sync (offline adapter fallback).
- **UI katmanı:**
  - Sidebar + stacked page yaklaşımı,
  - Personel ve Cihaz modüllerinde detaylı sayfa ve component ayrımı,
  - ThemeManager + QSS şablonlama altyapısı.

### 2.2 Sayısal Envanter (kod organizasyonu)

İnceleme sırasında elde edilen kaba envanter:
- `core`: 13 Python dosyası
- `database`: 25 Python dosyası
- `ui`: 52 Python dosyası
- `docs`: 6 doküman

Bu dağılım, projenin ağırlık merkezinin UI ve domain ekranları olduğunu gösteriyor.

### 2.3 Veri modeli & senkron

- `table_config.py` içinde toplam **18 tablo** tanımı bulunuyor.
- Bunların **14’ü sync edilebilir**, **4’ü local-only** olarak işaretli:
  - `Cihaz_Teknik`, `Cihaz_Belgeler`, `Cihaz_Teknik_Belge`, `Loglar`.
- Migration yöneticisinde güncel şema seviyesi **v14**.
- Sync tarafında tablo bazlı hata toplama (`SyncBatchError`) ve “hata alsa da diğer tabloya devam et” stratejisi mevcut.

---

## 3) Güçlü Yönler

1. **Katmanlı mimari niyeti net**: UI-DB-Core ayrımı korunmuş.
2. **Migration disiplini var**: otomatik backup + şema versiyonlama yaklaşımı operasyonel açıdan değerli.
3. **Offline-first yaklaşımı mevcut**: cloud adapter katmanıyla online bağımlılık tek noktaya çekilmiş.
4. **Repository modeli ölçeklenebilir**: özel repository + generic repository birlikte kullanılıyor.
5. **Domain kapsamı geniş**: personel, cihaz, bakım, arıza, kalibrasyon, puantaj vb. ekranlar mevcut.
6. **Tema standardizasyonu yönünde adım atılmış**: template/QSS mimarisine geçiş başlamış.

---

## 4) Zayıf Yönler / Teknik Borç

1. **Test boşluğu kritik seviyede**
   - `pytest` çalıştırıldığında test keşfi var fakat test case yok (0 test).
   - Veri erişim, migration, sync ve iş kuralı katmanları için güvence zayıf.

2. **UI sınıflarında büyüme riski**
   - Özellikle `main_window.py` ve bazı sayfa dosyalarında sorumluluklar kalınlaşıyor.
   - Event yönetimi + data erişimi + hata mesajı + görünüm davranışı aynı sınıfta toplanabiliyor.

3. **Hata yönetiminde kullanıcı deneyimi standardı tam değil**
   - Bazı modüllerde iyi loglama var; ancak kullanıcıya gösterilen mesaj standardı tüm ekranlarda eşit değil.

4. **Sync gözlemlenebilirliği sınırlı**
   - Log var ama metrik dashboard, retry politikası, kalıcı dead-letter/queue yaklaşımı belirgin değil.

5. **Dokümantasyon güncellik riski**
   - README’de “v2” ifadesi, requirements’da “v3” ifadesi geçiyor; sürüm anlatısında tutarlılık ihtiyacı var.

---

## 5) Operasyonel Risk Analizi

### Yüksek Öncelik
- **Regresyon riski (test yokluğu):** kritik iş kuralları değişimlerinde fark edilmeden bozulma olasılığı yüksek.
- **Sync karmaşıklığı:** online/offline geçişlerinde veri tutarlılığı kenar senaryoları (çatışma, gecikmeli push, parse hataları) daha görünür test gerektiriyor.

### Orta Öncelik
- **Büyük UI dosyalarının bakım maliyeti:** yeni geliştirici onboarding süresi uzayabilir.
- **Dokümantasyon sürüm sapması:** operasyon ekiplerinde yanlış beklentiye neden olabilir.

### Düşük Öncelik
- **Tema sistemi ikinci faz:** runtime tema değiştirme gibi işlevler ürün değerine göre ertelenebilir.

---

## 6) Neler Yapılabilir? (Öneri Backlog’u)

### 6.1 Kısa Vade (0–4 hafta)

1. **Test temel hattı oluşturma**
   - `database/base_repository.py` için CRUD + dirty/clean akış testleri,
   - `database/migrations.py` için “boş db → v14” ve “mevcut db → migrate” senaryoları,
   - `core/hesaplamalar.py` için iş kuralı testleri.

2. **Sync servis güvence testleri**
   - mock GSheet ile push/pull çatışma senaryoları,
   - tarih alanı normalize davranış doğrulaması,
   - kısmi tablo hata durumunda batch hata raporlama doğrulaması.

3. **Runbook dokümantasyonu**
   - “migration failure durumunda geri dönüş”,
   - “offline modda dosya yükleme davranışı”,
   - “sync hatası triage adımları”.

4. **Sürüm ve doküman hizalaması**
   - README/requirements/app version terminolojisini tekleştirme.

### 6.2 Orta Vade (1–2 ay)

1. **UI refactor dalgası**
   - büyük sayfaları presenter/controller benzeri ara katmanla sadeleştirme,
   - state yönetimini tek merkezde toplama (minimum: page-level state object).

2. **Hata mesaj standardı**
   - domain-hata kodu + kullanıcı dostu mesaj sözlüğü,
   - tüm form/senkron ekranlarında ortak kullanım.

3. **Gözlemlenebilirlik**
   - sync süresi, başarısız tablo sayısı, retry sayısı gibi metriklerin ayrı log kanalına alınması.

### 6.3 Uzun Vade (2+ ay)

1. **Entegrasyon test pipeline’ı**
   - örnek SQLite fixture verisiyle uçtan uca smoke testler.

2. **Modüler paketleme**
   - personel/cihaz/rke alt modüllerinin bağımsız paket sınırlarına yaklaştırılması.

3. **Yetkilendirme & audit izi**
   - “kim neyi ne zaman değiştirdi” yapısı (özellikle kurumsal kullanım için kritik).

---

## 7) Modül Bazında Durum Notları

### Personel
- Kapsam ve fonksiyon zenginliği yüksek; mevcut durum belgeleri “production ready” seviyesine yakın bir olgunluk işaret ediyor.
- Öncelik: schema doğrulama ve edge-case validation testleri.

### Cihaz
- Arıza/bakım/kalibrasyon ekranlarının temel akışları mevcut.
- Belgelerde geçen eksikler (dosya seçici, düzenle/sil, filtreleme) ürün verimliliğini artıracak net hedefler.

### Tema/UI
- Şablon-temelli yaklaşım doğru yönde.
- Runtime tema değiştirme ikinci faz olarak planlanabilir.

---

## 8) Önerilen Önceliklendirme (Efor / Etki)

1. **P1:** Test altyapısı + kritik servis testleri (Yüksek etki, orta efor)
2. **P1:** Sync hata ve retry stratejisi netleştirme (Yüksek etki, orta efor)
3. **P2:** UI sınıf parçalama (Orta etki, orta-yüksek efor)
4. **P2:** Operasyon runbook + doküman hizalama (Orta etki, düşük efor)
5. **P3:** Runtime tema ve ileri UX iyileştirmeleri (Düşük/orta etki, düşük/orta efor)

---

## 9) Sonuç

REPYS, fonksiyonel açıdan güçlü ve gerçek kullanım senaryolarına temas eden bir kurumsal masaüstü uygulama omurgasına sahip. En büyük kaldıraç alanı artık **“özellik eklemekten çok güvence ve sürdürülebilirlik artırımı”**: test, operasyonel netlik, senkron güvenilirliği ve UI bakım maliyeti kontrolü.

Bu dört alana odaklanan bir iyileştirme sprinti ile proje, kurumsal ölçekte daha öngörülebilir ve daha düşük bakım riskiyle ilerleyebilir.

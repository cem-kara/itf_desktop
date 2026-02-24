# REPYS — Birleşik Son Durum ve Uygulama Planı Raporu

**Tarih:** 2026-02-24  
**Sürüm Referansı:** REPYS v3.0.0  
**Birleştirilen Kaynaklar:**
- `docs/REPYS_DURUM_RAPORU_2026-02.md` (önceki teknik durum)
- `docs/cihaz_todo.md` (cihaz modülü yapılacaklar)
- `docs/PERSONEL_STATUS.md` (personel modülü validasyon/olgunluk notları)
- `docs/tema_todo.md` (tema teknik borç ve yol haritası)

---

## 1) Yönetici Özeti

REPYS, mimari olarak doğru yönde (katmanlı yapı + migration + offline destek) ve fonksiyonel olarak güçlü bir masaüstü operasyon sistemidir. Personel ve cihaz alanları çalışır durumda; ancak sürdürülebilirlik için “özellik ekleme” yerine “güvence artırma” odağına geçilmelidir.

Bu birleşik raporun sonucu:
- **Personel modülü:** Yüksek olgunluk, kritik validasyon checklist’i tamamlanmalı.
- **Cihaz modülü:** Ana akışlar hazır, düzenle/sil/dosya seçici gibi operasyonel eksikler var.
- **Tema sistemi:** Temel temizlik yapılmış, runtime tema değiştirme entegrasyonu eksik.
- **Genel platform:** Test otomasyonu ve operasyon runbook en yüksek öncelik.

---

## 2) Güncel Durum Fotoğrafı (As-Is)

### 2.1 Mimari ve Platform
- Uygulama PySide6 tabanlı masaüstü yapıdadır.
- Başlatma akışı: tema uygula → log yönetimi başlat → migration kontrolü → ana pencere aç.
- Veritabanı: SQLite + WAL, migration manager ile versiyonlu şema güncelleme.
- Senkron: online/offline modlu bulut adaptörü yaklaşımı mevcut.

### 2.2 Modül Olgunluk Skoru

| Alan | Durum | Not |
|---|---|---|
| Personel | ✅ Yüksek | İşlevler geniş; kritik doğrulamalar tamamlanmalı |
| Cihaz | 🟡 Orta-Yüksek | Arıza/Bakım/Kalibrasyon aktif; CRUD genişletmesi gerekli |
| Tema/UI Altyapısı | 🟡 Orta | QSS template düzeni var; runtime tema geçişi eksik |
| Test/QA | 🔴 Düşük | Otomasyon test kapsaması yetersiz |
| Operasyon/SRE | 🟡 Orta | Migration/backup var, runbook ve metrik standardı eksik |

---

## 3) Kaynak Dokümanların Birleşik Bulguları

### 3.1 Personel modülünden gelen kritik bulgular
1. Şema varlığı ve edge-case senaryoları (özellikle sağlık/fotoğraf ilişkili tablolar) teyit edilmeli.
2. Pasif statü iş kuralı (30+ gün izin) uçtan uca doğrulanmalı.
3. Drive kesintisinde upload davranışı (hata/queue/silent fail) standartlaştırılmalı.

### 3.2 Cihaz modülünden gelen kritik bulgular
1. Mevcut: Arıza/Bakım/Kalibrasyon liste + detay + yeni kayıt akışları çalışıyor.
2. Eksik: düzenleme/silme aksiyonları, dosya seçici, filtreleme/arama, dosya önizleme.
3. Sınırlama: bazı dosya alanları halen sadece metin yol olarak kullanılıyor.

### 3.3 Tema dokümanından gelen kritik bulgular
1. Renk ve stil tanımlarında tekilleştirme büyük oranda yapılmış.
2. Takvim popup stilinin merkezileştirilmesi tamam.
3. Runtime tema değişimi (light/dark) için hazırlık dosyaları var, entegrasyon tamamlanmamış.

---

## 4) Öncelikli Riskler (Neden Hemen Ele Alınmalı?)

### R1 — Test güvencesi eksikliği (En kritik)
- **Risk:** Regresyonlar geç fark edilir, bakım maliyeti katlanır.
- **Etki:** Personel/Cihaz gibi kritik akışlarda sessiz kırılma.

### R2 — Online/Offline davranış sözleşmesi net değil
- **Risk:** Upload/sync hatalarında veri kaybı veya belirsiz kullanıcı deneyimi.
- **Etki:** Operasyon ekiplerinde güven kaybı.

### R3 — UI dosyalarında sorumluluk yoğunluğu
- **Risk:** Yeni geliştirme ve hata düzeltme süresi uzar.
- **Etki:** Değişiklik başına hata olasılığı artar.

### R4 — Operasyon runbook ve metrik standardı eksik
- **Risk:** Prod/kurum sahasında sorun çözüm süresi uzar.
- **Etki:** MTTR artar, ekip bağımlılığı artar.

---

## 5) P1 → P4 Uygulama Planı (Yapılacak İş / Neden / Nasıl)

> İstenen kapsam doğrultusunda P adımları “ne yapılacak, neden yapılacak, nasıl yapılacak” seviyesinde ayrıntılı hazırlanmıştır.

## P1 — Test ve Validasyon Temel Hattı (0–2 hafta)

### Ne yapılacak?
1. `database` katmanında repository ve migration testleri yazılacak.
2. Personel kritik akışları için validasyon test matrisi hazırlanacak.
3. Cihaz kritik akışları için smoke senaryoları yazılacak.

### Neden yapılacak?
- P2/P3/P4 refactor ve genişletme işlerine güvenli zemin oluşturmak için.
- Kırılmayı “yayına gitmeden” yakalamak için.

### Nasıl yapılacak?
- **Test altyapısı:** `tests/` altında katman bazlı dizin.
- **Hedef test seti:**
  - `test_base_repository.py`: insert/update/get_dirty/mark_clean
  - `test_migrations.py`: boş DB’den güncel şemaya geçiş + mevcut DB upgrade
  - `test_personel_rules.py`: 30+ gün izin => Pasif kuralı
  - `test_upload_offline_behavior.py`: Drive yokken expected davranış
- **Çıktı/Kabul kriteri:**
  - En az 25–30 otomasyon testi,
  - Kritik business-rule için %100 senaryo kapsaması,
  - CI’da tek komutla çalıştırılabilir test seti.

---

## P2 — Veri Güvenliği, Sync Sözleşmesi ve Operasyon Runbook (2–4 hafta)

### Ne yapılacak?
1. Online/offline upload ve sync davranış sözleşmesi yazılacak.
2. Sync hata sınıfları ve kullanıcı mesaj standardı oluşturulacak.
3. Operasyon runbook (backup, rollback, recovery) tamamlanacak.

### Neden yapılacak?
- Kesinti anlarında ekiplerin ne yapacağı netleşsin.
- Veri kaybı/silent fail riski azaltılsın.

### Nasıl yapılacak?
- **Sözleşme dokümanı:**
  - “Cloud down” durumunda sistem davranışı (retry, local fallback, kullanıcı bildirimi)
  - “Sync partial failure” durumunda tablo bazlı aksiyon kuralı
- **Hata standardı:**
  - Teknik hata → kullanıcı dostu kısa mesaj + detay log id
- **Runbook bölümleri:**
  - Migration fail rollback adımları
  - Offline yüklenen dosyaların tekrar senkron prosedürü
  - Schema doğrulama SQL komutları
- **Çıktı/Kabul kriteri:**
  - Doküman + örnek senaryo testleri
  - En az 1 tatbikat (simülasyon) kaydı

---

## P3 — UI Sınıf Parçalama ve Teknik Borç Azaltımı (4–8 hafta)

### Ne yapılacak?
Aşağıdaki dosyalarda parçalama uygulanacak (önceki raporla uyumlu):

**Dalga-1 (kritik):**
- `ui/main_window.py`
- `ui/pages/personel/personel_listesi.py`
- `ui/pages/personel/izin_takip.py`
- `ui/pages/cihaz/ariza_kayit.py`
- `ui/pages/cihaz/bakim_kalibrasyon_form.py`
- `ui/pages/personel/saglik_takip.py`

**Dalga-2 (takip):**
- `ui/pages/personel/fhsz_yonetim.py`
- `ui/pages/personel/personel_ekle.py`
- `ui/pages/dashboard.py`
- `ui/pages/cihaz/cihaz_listesi.py`

### Neden yapılacak?
- Büyük sınıfların bakım maliyeti ve regress riski düşürülecek.
- UI test edilebilirliği artırılacak.

### Nasıl yapılacak?
- Her dosyada standart ayrım:
  1. `View` (yalnız widget/render/sinyal)
  2. `Presenter/Controller` (event orchestration)
  3. `Service` (iş kuralı/use-case)
  4. `State/ViewModel` (sayfa state)
- Örnek hedef sınıf ayrımları:
  - `MainWindowShell` + `PageRouter` + `SyncController`
  - `PersonelListView` + `PersonelListPresenter` + `PersonelListState`
  - `ArizaPageCoordinator` + `ArizaCommandService`
- **Çıktı/Kabul kriteri:**
  - Hedef dosyalar < 500 satır bandına indirilecek,
  - UI dosyalarında doğrudan DB erişimi minimuma inecek,
  - Refactor sonrası smoke checklist eksiksiz geçecek.

---

## P4 — Tema Son Faz + Ürünleştirme Kalitesi (8–10 hafta)

### Ne yapılacak?
1. Runtime light/dark tema değiştirme özelliği entegre edilecek.
2. Tema seçimi kullanıcı ayarlarına yazılacak.
3. Kritik ekranlarda görsel tutarlılık ve erişilebilirlik gözden geçirilecek.

### Neden yapılacak?
- UI standardizasyonu tamamlanacak.
- Kullanıcı deneyimi daha kurumsal ve tutarlı hale gelecek.

### Nasıl yapılacak?
- Mevcut hazırlık dosyalarının entegrasyonu:
  - `ui/styles/light_theme.py`
  - `ui/theme_light_template.qss`
  - `ui/styles/theme_registry.py`
- `ThemeManager` içine `set_theme()` + uygulama çapı refresh akışı eklenecek.
- Ayar dosyasına `theme` anahtarı yazılacak/okunacak.
- **Çıktı/Kabul kriteri:**
  - Uygulama yeniden açıldığında tema tercihi korunur,
  - Tüm ana sayfalarda görsel regresyon checklist’i geçer.

---

## 6) Modül Bazlı Net İş Listesi (Özet)

### Personel
- [ ] Şema doğrulama checklist’ini tamamla.
- [ ] Pasif statü kuralını uçtan uca test et.
- [ ] Drive offline upload davranışını standartlaştır.

### Cihaz
- [ ] Arıza/Bakım/Kalibrasyon için düzenle-sil aksiyonlarını ekle.
- [ ] Dosya seçici + dosya önizleme ekle.
- [ ] Liste filtre/arama yeteneklerini geliştir.

### Tema
- [ ] Runtime tema değiştirme entegrasyonu.
- [ ] Ayarlara tema persist.
- [ ] Stil sabitlerini tek kaynakta tutma denetimi.

---

## 7) Sprint Sırası ve Bağımlılık Haritası

1. **Sprint-1 (P1):** Test hattı + kritik validasyon
2. **Sprint-2 (P2):** Sync sözleşmesi + runbook + hata standardı
3. **Sprint-3/4 (P3):** UI parçalama dalga-1 ve dalga-2
4. **Sprint-5 (P4):** Tema son faz + kalite kapanışları

Bağımlılık kuralı:
- P3 başlamadan P1 tamamlanmalı.
- P4 başlamadan P3 dalga-1 tamamlanmalı.

---

## 8) Ölçülebilir Başarı Kriterleri (KPI)

- Test sayısı: `0 → 30+`
- Kritik akış regresyonu: manuel checklist + otomasyon
- UI büyük dosya oranı: 900+ satır dosya sayısında belirgin azalma
- Sync incident çözüm süresi: runbook sonrası düşüş
- Kullanıcı hata mesajlarının standartlaşma oranı: kritik ekranlarda %100

---

## 9) Sonuç

REPYS için bir sonraki doğru adım, **özellik büyütme değil; güvence, sürdürülebilirlik ve operasyonel netlik artırımıdır**. Bu rapordaki P1→P4 planı aynı anda hem teknik borcu azaltır hem de yeni özellikler için güvenli geliştirme zemini kurar.

Bu plan onaylandığında önerilen başlangıç: **P1 test hattı + personel/cihaz kritik validasyon senaryolarının hemen yazımı**.

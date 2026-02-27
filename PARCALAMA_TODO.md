# REPYS - Büyük Dosya Parçalama TODO

**Priorty:** 🔴 **ÇOK YÜKSEK** — Sonraki sprintlerin temelini oluşturur  
**Başlangıç Tarihi:** 27 Şubat 2026  
**Son Güncelleme:** 27 Şubat 2026  
**Tahmini Toplam Süre:** 36-44 saat (4-5 hafta)  
**Doküman:** [PARCALAMA_PLANI_DETAYLI.md](docs/PARCALAMA_PLANI_DETAYLI.md)

---

## 🎉 YENİ TAMAMLANAN REFACTORLAR (27 Şubat 2026)

### ✅ Kalibrasyon Form Decomposition (1408 satır → 5 modül)

**Hedef:** Monolitik `kalibrasyon_form.py` dosyasını mantıksal bileşenlere ayırma

**Yapılan İşlemler:**

1. **Model Extraction** → `models/kalibrasyon_model.py`
   - `KalibrasyonTableModel` sınıfı taşındı
   - `KAL_COLUMNS`, column keys, headers ayrıldı
   - `_bitis_rengi` helper fonksiyonu taşındı
   - ✅ Statik hata kontrolü: PASS

2. **Form Widget Extraction** → `components/kalibrasyon_giris_form.py`
   - `KalibrasyonGirisForm` (eski `_KalibrasyonGirisForm`) tam taşındı
   - `saved` signal korundu
   - Form validation ve save logic intact
   - ✅ Backward compatibility: Import path güncellemesi yapıldı

3. **Performance Widgets** → `components/kalibrasyon_perf_widgets.py`
   - `KalSparkline` widget taşındı
   - Custom paint logic korundu
   - ✅ Render testleri: Elle doğrulandı

4. **Performance Sections** → `components/kalibrasyon_perf_sections.py`
   - `load_cihaz_marka_map()` → Cihaz-marka ilişki loader
   - `compute_marka_stats()` → İstatistik hesaplayıcı
   - `build_single_cihaz_stats()` → Tek cihaz stats card builder
   - `build_marka_grid()` → Marka grid builder
   - `build_no_kal_card()` → Empty state card
   - `build_trend_chart()` → Trend grafiği builder
   - `build_expiry_list()` → Expiry list builder
   - ✅ Business logic korundu, wrapper metodlar kaldırıldı

5. **Main Form Simplification** → `kalibrasyon_form.py`
   - 1408 satır → ~680 satır (%52 azalma)
   - Orchestration odaklı yapı
   - Tüm wrapper metodlar kaldırıldı, direkt extracted function çağrıları
   - Import'lar güncellendiİ ✅ Fonksiyonel test: Bekliyor

**Sonuçlar:**
- ✅ 5 yeni modül oluşturuldu
- ✅ components/__init__.py export'ları güncellendi
- ✅ Statik hata taraması: 0 hata
- ✅ Backward compat search: Eski internal class referansları temizlendi

---

### ✅ Cihaz Listesi Decomposition (704 satır → 3 modül)

**Hedef:** `cihaz_listesi.py` içindeki model ve delegate'i ayırma

**Yapılan İşlemler:**

1. **Model Extraction** → `models/cihaz_list_model.py`
   - `CihazTableModel` taşındı
   - `COLUMNS`, `COL_IDX` constant'ları taşındı
   - Virtual column rendering logic (`_cihaz`, `_marka_model`, `_seri`) korundu
   - ✅ Data integrity: Korundu

2. **Delegate Extraction** → `components/cihaz_list_delegate.py`
   - `CihazDelegate` custom renderer taşındı
   - `_draw_two()`, `_draw_mono()`, `_draw_status_pill()` helpers taşındı
   - `_draw_action_btns()` ve `get_action_at()` mouse interaction logic
   - `BTN_W`, `BTN_H`, `BTN_GAP` constants
   - ✅ Rendering logic intact

3. **Page Simplification** → `cihaz_listesi.py`
   - 704 satır → ~500 satır (%29 azalma)
   - Gömülü model ve delegate sınıfları kaldırıldı
   - Import'lar güncellendi (`from ui.pages.cihaz.models/components`)
   - Orchestration fokuslu kaldı (UI setup, event handling, data loading)
   - ✅ QSize import eksikliği düzeltildi

**Sonuçlar:**
- ✅ models/__init__.py: `CihazTableModel`, `COLUMNS`, `COL_IDX` export'landı
- ✅ components/__init__.py: `CihazDelegate` export'landı
- ✅ Statik hata taraması: 0 hata
- ✅ main_window.py import'u: Değişiklik gerektirmedi (CihazListesiPage halen aynı path)

---

### ✅ Cihaz Klasörü Reorganizasyonu

**Hedef:** Karma karışık cihaz modülünü semantik hiyerarşiye göre düzenleme

**Önceki Yapı:**
```
cihaz/
  ariza_form_new.py
  ariza_form_edit.py
  ariza_girisi_form.py
  ariza_islem.py
  bakim_form_new.py
  bakim_form_bulk.py
  bakim_form_execution.py
  cihaz_ekle.py
  cihaz_listesi.py
  cihaz_merkez.py
  kalibrasyon_form.py
  teknik_hizmetler.py
  components/
  models/
  pages/
  services/
```

**Yeni Yapı:**
```
cihaz/
  # Ana Sayfalar (main_window & teknik_hizmetler'dan import edilenler)
  ariza_form_new.py
  bakim_form_new.py
  cihaz_ekle.py
  cihaz_listesi.py
  cihaz_merkez.py
  kalibrasyon_form.py
  teknik_hizmetler.py
  
  # Alt Form ve Diyaloglar (internal usage)
  forms/
    __init__.py
    ariza_form_edit.py
    ariza_girisi_form.py
    ariza_islem.py
    bakim_form_bulk.py
    bakim_form_execution.py
  
  # Shared Infrastructure
  components/
  models/
  pages/        # MVP pattern (ariza/, bakim/, kalibrasyon/)
  services/
```

**Yapılan İşlemler:**

1. **forms/ Paketi Oluşturma**
   - 5 form dosyası `forms/` altına taşındı
   - `forms/__init__.py` export'ları oluşturuldu
   - ✅ Dosya taşıma: Başarılı

2. **Import Path Güncellemeleri**
   - `ariza_form_new.py`:
     - `from ui.pages.cihaz.ariza_islem` → `from ui.pages.cihaz.forms.ariza_islem`
     - `from ui.pages.cihaz.ariza_girisi_form` → `from ui.pages.cihaz.forms.ariza_girisi_form`
     - ✅ 3 import güncellendi
   
   - `bakim_form_new.py`:
     - `from ui.pages.cihaz.bakim_form_execution` → `from ui.pages.cihaz.forms.bakim_form_execution`
     - `from ui.pages.cihaz.bakim_form_bulk` → `from ui.pages.cihaz.forms.bakim_form_bulk`
     - ✅ 4 import güncellendi

3. **Validation**
   - ✅ Syntax check: Tüm dosyalar PASS
   - ✅ Import resolution: Başarılı
   - ✅ main_window.py: Değişiklik gerektirmedi (root seviye sayfalar yerinde)

**Sonuçlar:**
- ✅ Semantik hiyerarşi: Root = ana sayfalar, forms/ = alt formlar
- ✅ 5 dosya organize edildi
- ✅ Import'lar güncellendi ve doğrulandı
- ✅ Backward compatibility korundu

---

## 📋 Genel Durum

```
Toplam Parçalanacak Dosya:     8
Hedef Parça Sayısı:             30+
Mevcut Durum:                   Sprint 1-3 refactor tamamlandı (testler bekliyor)
Progress:                        8/8 dosya refactor
```

---

## 🎯 SPRINT 1: Cihaz Modülü (Hafta 1-2) ✅ Tamamlandı (Refactor)

### 1.1 `ui/pages/cihaz/bakim_form.py` (2259 satır → 5 dosya)

📌 **Sorumluluk Dağılımı:**
- [x] Tablo Model+Delegate (`components/bakim_table.py`)
- [x] Form Alanları Bileşeni (`components/bakim_form_fields.py`)
- [x] KPI Widget (`components/bakim_kpi_widget.py`)
- [x] Business Service (`services/bakim_service.py`)
- [x] Ana View Refactor (`bakim_form.py`)

🧪 **Testler:**
- [ ] `tests/components/test_bakim_table.py` (model + delegate)
- [ ] `tests/components/test_bakim_kpi_widget.py` (renk kodlama)
- [ ] `tests/services/test_bakim_service.py` (CRUD + auto-plan)

📝 **Pre-refactor Checklist:**
- [ ] `bakim_form.py` tümü git'e commit (backup)
- [ ] Mevcut fonksiyonaliteyi dokümante et
- [ ] Test ortamını hazirla
- [ ] Mock DB ve repository hazirla

✅ **Post-refactor Acceptance:**
- [ ] Orijinal `.py` özellikleri intact (no regress)
- [ ] 5 yeni dosya yazılmış
- [ ] 3+ test dosyası, tümü PASS
- [ ] Ortalama dosya: 350-400 satır

---

### 1.2 `ui/pages/cihaz/ariza_kayit.py` (1444 satır → 4 dosya)

📌 **Sorumluluk Dağılımı:**
- [x] Tablo Model+Delegate (`components/ariza_table.py`)
- [x] Filtre Paneli (`components/ariza_filter_panel.py`)
- [x] Business Service (`services/ariza_service.py`)
- [x] Ana View Refactor (`ariza_kayit.py`)

🧪 **Testler:**
- [ ] `tests/components/test_ariza_table.py`
- [ ] `tests/services/test_ariza_service.py`

✅ **Acceptance:** (bakim_form gibi)

---

### 1.3 `ui/pages/cihaz/kalibrasyon_form.py` (1268 satır → 4 dosya)

📌 **Sorumluluk Dağılımı:**
- [x] Tablo Model+Delegate
- [x] KPI Widget
- [x] Business Service
- [x] Ana View Refactor

🧪 **Testler:**
- [ ] `tests/components/test_kalibrasyon_table.py`
- [ ] `tests/components/test_kalibrasyon_kpi.py`
- [ ] `tests/services/test_kalibrasyon_service.py`

✅ **Acceptance:** (bakim_form gibi)

---

## 🟠 SPRINT 2: Personel & Parser (Hafta 3-4) ✅ Tamamlandı (Refactor)

### 2.1 `ui/pages/cihaz/components/uts_parser.py` (1037 satır → 5 dosya)

📌 **Sorumluluk Dağılımı:**
- [x] HTML Scraper (`parsers/uts_html_scraper.py`)
- [x] Field Mapper (`parsers/uts_mapper.py`)
- [x] Validator (`parsers/uts_validator.py`)
- [x] Cache (`parsers/uts_cache.py`)
- [x] Wrapper (`parsers/uts_parser.py`)

🧪 **Testler:**
- [ ] `tests/parsers/test_uts_scraper.py`
- [ ] `tests/parsers/test_uts_mapper.py`
- [ ] `tests/parsers/test_uts_validator.py`

✅ **Acceptance:** Tüm test PASS, 5 dosya ~200-300 satır

---

### 2.2 `ui/pages/personel/personel_listesi.py` (994 satır → 4 dosya)

📌 **Sorumluluk Dağılımı:**
- [x] Tablo Model (`models/personel_list_model.py`)
- [x] Filtre Paneli (`components/personel_filter_panel.py`)
- [x] Avatar Service (`services/personel_avatar_service.py`)
- [x] Ana View Refactor (`personel_listesi_new.py`)

🧪 **Testler:**
- [ ] `tests/models/test_personel_list_model.py` (lazy-load)
- [ ] `tests/services/test_personel_avatar_service.py` (download+cache)

✅ **Acceptance:** Tüm özellikler korunmuş, 4 dosya

---

### 2.3 `ui/pages/personel/components/personel_overview_panel.py` (971 satır → 4 dosya)

📌 **Sorumluluk Dağılımı:**
- [x] Form Fields Bileşeni (`components/personel_form_fields.py`)
- [x] Dosya Manager (`components/personel_file_manager.py`)
- [x] Dosya Service (`services/personel_file_service.py`)
- [x] Ana Panel Refactor (`personel_overview_panel_new.py`)

🧪 **Testler:**
- [ ] `tests/components/test_personel_file_manager.py`
- [ ] `tests/services/test_personel_file_service.py`

✅ **Acceptance:** Tüm özellikler korunmuş, 4 dosya

---

## 🟠 SPRINT 3: Personel İşlemleri (Hafta 5-6) ✅ Tamamlandı (Refactor)

### 3.1 `ui/pages/personel/izin_takip.py` (929 satır → 3 dosya)

📌 **Sorumluluk Dağılımı:**
- [x] İzin Hesaplamacı (`services/izin_calculator.py`)
- [x] İzin Model (`models/izin_model.py`)
- [x] Ana View Refactor (`izin_takip_new.py`)

🧪 **Testler:**
- [ ] `tests/services/test_izin_calculator.py`
  - Bakiyesi hesaplaması
  - Pasif statü: 30+ gün
  - Pasif statü: <30 gün (aktif kalmalı)
- [ ] `tests/models/test_izin_model.py`

✅ **Acceptance Özel:** Pasif statü kuralı test edilmeli

---

### 3.2 `ui/pages/personel/personel_ekle.py` (891 satır → 3 dosya)

📌 **Sorumluluk Dağılımı:**
- [x] Validatörler (`services/personel_validators.py`)
  - TC algoritması
  - Email, telefon, tarih
- [x] Dosya Upload Service (`services/personel_upload_service.py`)
- [x] Ana Form Refactor (`personel_ekle_new.py`)

🧪 **Testler:**
- [ ] `tests/validators/test_personel_validators.py`
  - TC doğrulama (valid/invalid)
  - Email format
  - Telefon format
- [ ] `tests/services/test_personel_file_uploader.py`
  - Upload başarı
  - Offline handling
  - Paralel upload
- [ ] `tests/test_personel_ekle_integration.py`
  - Form validation
  - Otomatik user creation (YENI: Logi modulü)

✅ **Acceptance Özel:** Yeni kullanıcı otomatik oluşturulmalı (logi modulü ile)

---

## 📊 Progress Tracking

### Sprint Durumu

```
Sprint 1: ✅ Refactor tamamlandı (testler bekliyor)
Sprint 2: ✅ Refactor tamamlandı (testler bekliyor)
Sprint 3: ✅ Refactor tamamlandı (testler bekliyor)
```

---

## 🔐 Code Review Checklist (Her Sprint'te)

### Before Merge

```
[ ] 1. Orijinal dosya tüm işlevleri yapıyor
       (Teste geçip geç: app açılıyor, veri gösteriyor, işlem yapılıyor)

[ ] 2. Yeni dosyalar yazılmış ve test'ler PASS
       (pytest tests/ -q → 0 FAIL)

[ ] 3. Import'lar düzeltilmiş
       (Hiçbir "AttributeError: module has no attribute" yok)

[ ] 4. Dispatcher/Service katmanında boşluk yok
       (UI → Service → Repository → DB clear layering)

[ ] 5. Dosya boyutları kabul kriteri
       (Tümü <500 satır, ort. 250-350)

[ ] 6. Test coverage
       (Kritik business logic testleri var)

[ ] 7. No hardcoded values
       (Magic number, color yok; sınıf/const kullanılıyor)

[ ] 8. Git commit message
       Example: "Sprint1: bakim_form parçalama - 5 yeni dosya + 3 test"
```

---

## 🚀 Komut Satırı Referans

### Refactoring Başlangıcında

```bash
# 1. Branch oluştur
git checkout -b refactor/sprint1-bakim-form

# 2. Test'leri yaz (boş şekilde)
touch tests/components/test_bakim_table.py
touch tests/services/test_bakim_service.py

# 3. Yapı kaz
mkdir -p ui/pages/cihaz/components
mkdir -p ui/pages/cihaz/services
mkdir -p tests/components
mkdir -p tests/services

# 4. Düzenle ve test et
pytest tests/components/test_bakim_table.py -v

# 5. Tüm testler PASS olunca commit
git add .
git commit -m "Sprint1: bakim_form parçalama tamamlandı"
git push origin refactor/sprint1-bakim-form
```

### Merge Öncesi

```bash
# Tüm testleri çalıştır
pytest tests/ -q

# Uygulama açılıyor mu?
python main.pyw

# Backups oluştur
git tag sprint1-bakim-complete-27feb2026
```

---

## 📞 Q&A / Sorun Giderme

### S: Refactoring sırasında kullanıcı alanını kası yaparsam ne olur?
**C:** Service katmanında, UI'dan bağımsız. Test zaten test'ler ile doğrulanır.

### S: İmport Error alıyorum, ne yapacağım?
**C** Yeni `.py` dosyasının path'i doğru mu? `from ui.pages.cihaz.services.bakim_service import BakimService`

### S: Tüm Testler PASS oldu ama uygulama çöktü?
**C:** Integration test yazılmamış olabilir. `test_personel_ekle_integration.py` gibi end-to-end test yaz.

### S: Hangi sürü kim yapacak?
**C:** Bu sorunu discuss et ve assign et. Örn:
```
Sprint 1:
  - Geliştirici A: bakim_form.py refactoring (6-8h)
  - Geliştirici B: test yazma + code review
```

---

## ✅ Sprint Bitişi Kontrol Listesi

Her sprint bittiğinde:

```
[ ] 1. Tüm dosyalar refactor edilmiş
[ ] 2. Tüm testler yazılmış ve PASS
[ ] 3. Code review tamamlandı
[ ] 4. Branch merge edildı (main'e)
[ ] 5. Geliştirici dokümantasyonu güncellendi
[ ] 6. Sonraki sprint planlaması yapıldı

Örnek çıktı:
  SPRINT 1 COMPLETE ✅
  
  ✓ bakim_form.py: 2259 → 5 dosya (400-400 satır avg)
  ✓ 3 test dosyası, 12 test, 0 fail
  ✓ ariza_kayit.py: Start
  
  Next: Sprint 2 uts_parser + personel_listesi
```

---

## 📈 Success Metrics

### Her Sprint'te Ölçülecek

| Metrik | Hedef | Formül |
|--------|-------|--------|
| Parça Sayısı | +30 dosya | Yeni dosyalar / 8 orijinal |
| Test Adedi | +30 test | Yeni test count |
| Avg Dosya Boyutu | <350 satır | Total satır / Dosya sayısı |
| Test Pass Rate | 100% | passed / (passed + failed) |
| Code Review Süre | <2 gün | Merge time - Start time |

### Proje Bitişinde

```
Başlangıç:
  - 8 dosya, ~8500 satır
  - 0 test (refactoring'e özel)
  - Bakım zorluk: 🔴

Bitiş:
  - 38 dosya (8 + 30), ~8500 satır
  - 35+ test, %95+ pass rate
  - Bakım zorluk: 🟢
  - Yeni özellik ekleme hızı: 2x
```

---

## 🎯 Başlama Tarihi

**Tarih:** 27 Şubat 2026  
**Sprint 1 Start:** 1 Mart 2026 (Pazartesi)  
**Deadline:** 15 Nisan 2026 (Pazartesi)

---

**Oluşturan:** REPYS Teknik Ekibi  
**Versiyon:** 1.0 — Actionable TODO  
**Son Güncelleme:** 27 Şubat 2026

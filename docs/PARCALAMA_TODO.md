# Global Mimari Standardı — Parçalama Uygulama TODO

**Tarih:** 27 Şubat 2026  
**Strateji:** Baştan standart mimari uygulamak, sonradan ayırmaktan daha verimli  
**Hedef:** Tüm UI modülü global architecture pattern'ı takip edecek şekilde yeniden düzenleme

---

## 🏗️ Global Architecture Pattern

```
ui/
  pages/
    [module]/
      pages/                    # Sayfa grupları (listesi, ekle, detay, vb.)
        [page_name]/
          [page_name]_view.py
          [page_name]_presenter.py
          [page_name]_state.py
          [page_name]_service.py
      components/               # Module-wide reusable components
        [shared_name]_widget.py
        [shared_name]_model.py
      services/                 # Module-level business logic
        [module]_service.py
        [module]_validator.py
      utils/                    # Utilities, parsers, helpers
        [utility]_helper.py
```

### ✨ Pattern Kuralları

1. **Sayfa Yapısı:** Her sayfa `_view.py` + `_presenter.py` + `_state.py` + `_service.py`
2. **Shared Components:** Module içinde tekrarlanan bileşenler `components/` altında
3. **Module Services:** Business logic ve validasyon `services/` altında
4. **Utils:** Parser, helper, formatter `utils/` altında
5. **Seviye Sınırı:** UI layer → Presenter layer → Service/Repository layer → DB

---

## 📊 Dönüşüm Tablosu — 8 Dosyadan 30+ Dosyaya

| Eski Dosya | Yeni Klasör Yapısı | Dosya Say | Status |
|---|---|---|---|
| `cihaz/ariza_kayit.py` | `cihaz/pages/ariza/` | 4 | 🔴 Sprint 1 |
| `cihaz/bakim_form.py` | `cihaz/pages/bakim/` + `cihaz/components/` | 5 | 🔴 Sprint 1 |
| `cihaz/kalibrasyon_form.py` | `cihaz/pages/kalibrasyon/` + `cihaz/components/` | 4 | 🔴 Sprint 1 |
| `cihaz/components/uts_parser.py` | `cihaz/utils/uts_parser/` | 4 | 🟠 Sprint 2 |
| `personel/personel_listesi.py` | `personel/pages/listesi/` + `personel/components/` | 4 | 🟠 Sprint 2 |
| `personel/personel_overview_panel.py` | `personel/pages/profil/` + `personel/components/` | 4 | 🟠 Sprint 2 |
| `personel/izin_takip.py` | `personel/pages/izin/` + `personel/services/` | 4 | 🟠 Sprint 3 |
| `personel/personel_ekle.py` | `personel/pages/ekle/` + `personel/services/` | 4 | 🟠 Sprint 3 |

**Toplam:** 8 dosya → 33 dosya (4,1x artış ile daha iyi modülarize)

---

## 🔴 SPRINT 1 (Hafta 1-2) — Cihaz Modülü Standardizasyonu

### Phase 1.A: Arıza Kayıt (`cihaz/pages/ariza/`)

#### Oluşturulacak Yapı
```
ui/pages/cihaz/
  pages/
    ariza/
      __init__.py
      ariza_view.py              # View + Layout (400 satır)
      ariza_presenter.py         # Event handling + state sync (300 satır)
      ariza_service.py           # CRUD + business logic (250 satır)
      ariza_state.py             # State dataclass (100 satır)
```

#### Sorumluluk Dağılımı

| Dosya | Sorumluluk | Satır |
|---|---|---|
| `ariza_view.py` | Tablo, filtre paneli, detay container layout | 400 |
| `ariza_presenter.py` | Tablo model, delegate, event wiring | 300 |
| `ariza_service.py` | get_ariza_list(), create(), update(), close_ariza() | 250 |
| `ariza_state.py` | @dataclass ArizaState, selected_ariza, filters | 100 |

#### Yazılacak Testler

```python
# tests/pages/cihaz/test_ariza_presenter.py
✓ test_load_ariza_list_from_db()
✓ test_filter_ariza_by_status()
✓ test_filter_ariza_by_device()
✓ test_create_new_ariza()
✓ test_close_ariza_workflow()

# tests/pages/cihaz/test_ariza_service.py
✓ test_ariza_service_crud()
✓ test_ariza_notification_trigger()
```

#### Çalışma Adımları

- [ ] 1. `ariza_view.py` oluştur — layout sadece
- [ ] 2. `ariza_state.py` oluştur — state dataclass
- [ ] 3. `ariza_presenter.py` oluştur — model+delegate extract
- [ ] 4. `ariza_service.py` oluştur — CRUD işlemleri
- [ ] 5. View'i presenter'a connect et
- [ ] 6. Import güncellemeleri (eski `ariza_kayit.py` → yeni klasör)
- [ ] 7. Test dosyaları yaz (3-4 test)
- [ ] 8. Eski `ariza_kayit.py` sil
- [ ] 9. İntegrasyon testi (arıza ekleme-silme workflow'u)
- [ ] 10. Code review checklist

---

### Phase 1.B: Bakım & Kalibrasyon Ortak Komponentleri (`cihaz/components/`)

#### Oluşturulacak Shared Components

**Cihaz modülü genelinde tekrar eden bileşenler:**

```
ui/pages/cihaz/
  components/
    __init__.py
    record_table_model.py        # Base table model (bakim + kalibrasyon)
    record_table_delegate.py     # Base delegate (durum renk kodlama)
    kpi_bar_widget.py            # Genel KPI barı (3-6-12 ay renk)
    filter_panel_widget.py       # Genel filtre paneli (durum, cihaz, tarih)
```

#### Oluşturulacak Dosyalar

| Dosya | Amaç | Satır |
|---|---|---|
| `record_table_model.py` | QAbstractTableModel base class | 200 |
| `record_table_delegate.py` | Durum renk kodlama delegate | 150 |
| `kpi_bar_widget.py` | KPI şeridi (yeşil/sarı/kırmızı) | 180 |
| `filter_panel_widget.py` | Durum + cihaz + tarih filtreleri | 200 |

#### Yazılacak Testler

```python
# tests/components/cihaz/test_record_table_model.py
✓ test_load_data()
✓ test_row_count()
✓ test_data_change_notification()

# tests/components/cihaz/test_kpi_bar_widget.py
✓ test_kpi_color_0_to_3_months()  # yeşil
✓ test_kpi_color_3_to_6_months()  # sarı
✓ test_kpi_color_6plus_months()   # kırmızı
```

#### Çalışma Adımları

- [ ] 1. Bakim + Kalibrasyon dosyalarını karşılaştır — ortak kod bul
- [ ] 2. `record_table_model.py` oluştur (extract common)
- [ ] 3. `record_table_delegate.py` oluştur
- [ ] 4. `kpi_bar_widget.py` oluştur
- [ ] 5. `filter_panel_widget.py` oluştur
- [ ] 6. Components için tests yaz (3-4 test)
- [ ] 7. Bakım + Kalibrasyon dosyalarında bu components'i kullan

---

### Phase 1.C: Bakım Sayfası (`cihaz/pages/bakim/`)

#### Oluşturulacak Yapı
```
ui/pages/cihaz/
  pages/
    bakim/
      __init__.py
      bakim_view.py              # View container (300 satır)
      bakim_presenter.py         # Model + state sync (250 satır)
      bakim_service.py           # Auto-plan + upload (200 satır)
      bakim_state.py             # State (100 satır)
```

#### Sorumluluk Dağılımı

| Dosya | Sorumluluk |
|---|---|
| `bakim_view.py` | KPI widget + tablo + form detay + upload button |
| `bakim_presenter.py` | Model+delegate wiring + form field binding |
| `bakim_service.py` | auto_generate_plan(), upload_report_to_drive() |
| `bakim_state.py` | selected_bakim, filters, upload_progress |

#### Yazılacak Testler

```python
# tests/pages/cihaz/test_bakim_service.py
✓ test_auto_generate_plan_3_months()
✓ test_auto_generate_plan_6_months()
✓ test_upload_report_to_drive()

# tests/pages/cihaz/test_bakim_presenter.py
✓ test_kpi_color_rendering()
✓ test_table_load_and_sort()
```

#### Çalışma Adımları

- [ ] 1. Eski `bakim_form.py` analiz et (sorumluluklara ayır)
- [ ] 2. `bakim_view.py` oluştur (layout sadece)
- [ ] 3. `bakim_state.py` oluştur
- [ ] 4. `bakim_presenter.py` oluştur (model extract)
- [ ] 5. `bakim_service.py` oluştur (business logic extract)
- [ ] 6. Components'i integrate et (record_table_model, kpi_bar_widget)
- [ ] 7. Tests yaz
- [ ] 8. Eski `bakim_form.py` sil

---

### Phase 1.D: Kalibrasyon Sayfası (`cihaz/pages/kalibrasyon/`)

**Bakım ile aynı pattern**, fakat:
- `auto_generate_plan()` yerine `validate_calibration_schedule()`
- KPI renk kodu: geçmiş (kırmızı) / normal (yeşil) / planlı (sarı)

#### Oluşturulacak Yapı
```
ui/pages/cihaz/
  pages/
    kalibrasyon/
      __init__.py
      kalibrasyon_view.py
      kalibrasyon_presenter.py
      kalibrasyon_service.py
      kalibrasyon_state.py
```

#### Çalışma Adımları

- [ ] 1. Eski `kalibrasyon_form.py` analiz
- [ ] 2. bakim pattern'ı takip et
- [ ] 3. `kalibrasyon_service.py`'de kalibrasyon-spesifik logic
- [ ] 4. Tests yaz
- [ ] 5. Eski dosya sil

---

### ✅ Sprint 1 Acceptance Criteria

- [ ] 12 yeni dosya oluşturuldu (ariza 4 + bakim 4 + kalibrasyon 4)
- [ ] 8 shared component oluşturuldu (record_table, kpi, filter)
- [ ] 10+ unit test yazıldı
- [ ] Arıza ekleme / bakım planlama / kalibrasyon doğrulama work flows bozulmadı
- [ ] Import güncellemeleri yapıldı (eski `ariza_kayit.py`, `bakim_form.py`, `kalibrasyon_form.py` silinecek)
- [ ] Average file size: 2259 → ~350 satır (84% azalış)

---

## 🟠 SPRINT 2 (Hafta 3-4) — Personel Modülü + Parser Standardizasyonu

### Phase 2.A: Personel Listesi (`personel/pages/listesi/`)

#### Oluşturulacak Yapı
```
ui/pages/personel/
  pages/
    listesi/
      __init__.py
      listesi_view.py            # Table + filter layout (300 satır)
      listesi_presenter.py       # Model + lazy-load (300 satır)
      listesi_service.py         # Query + avatar (150 satır)
      listesi_state.py           # State (100 satır)
```

#### Sorumluluk Dağılımı

| Dosya | Sorumluluk |
|---|---|
| `listesi_view.py` | Table widget, filter panel layout |
| `listesi_presenter.py` | Table model, lazy-loading, filtre sync |
| `listesi_service.py` | get_personel_list(), avatar_service.download() |
| `listesi_state.py` | selected_personel, filter_flags, pagination |

#### Yazılacak Testler

```python
# tests/pages/personel/test_listesi_presenter.py
✓ test_lazy_load_personel(batch_size=100)
✓ test_filter_by_name()
✓ test_filter_by_status_AKTIF()
✓ test_filter_by_status_PASIF()
✓ test_filter_by_unit()

# tests/pages/personel/test_listesi_service.py
✓ test_avatar_download_and_cache()
✓ test_avatar_timeout_handling()
```

#### Çalışma Adımları

- [ ] 1. Eski `personel_listesi.py` analiz
- [ ] 2. `listesi_view.py` oluştur
- [ ] 3. `listesi_state.py` oluştur
- [ ] 4. `listesi_presenter.py` oluştur (model + lazy-load extract)
- [ ] 5. `listesi_service.py` oluştur
- [ ] 6. Tests yaz (5-6 test)
- [ ] 7. Eski dosya sil

---

### Phase 2.B: Personel Shared Components (`personel/components/`)

#### Oluşturulacak Shared Components

```
ui/pages/personel/
  components/
    __init__.py
    personel_avatar_widget.py    # Avatar gösterimi + cache
    personel_form_fields.py      # TC Kimlik, Ad, Soyad alanları
    personel_status_indicator.py # AKTIF/PASIF/İZİNLİ badge
    file_upload_widget.py        # Dosya seçici + upload progress
```

#### Yazılacak Testler

```python
# tests/components/personel/test_avatar_widget.py
✓ test_avatar_display()
✓ test_avatar_cache_hit()

# tests/components/personel/test_status_indicator.py
✓ test_status_AKTIF_color()
✓ test_status_PASIF_color()
```

---

### Phase 2.C: Personel Profil Paneli (`personel/pages/profil/`)

#### Oluşturulacak Yapı
```
ui/pages/personel/
  pages/
    profil/
      __init__.py
      profil_view.py             # Özet + form + dosyalar (350 satır)
      profil_presenter.py        # Form field binding (250 satır)
      profil_service.py          # Save + file upload (200 satır)
      profil_state.py            # State (100 satır)
```

#### Sorumluluk Dağılımı

| Dosya | Sorumluluk |
|---|---|
| `profil_view.py` | Avatar + metriks + form fields + file manager |
| `profil_presenter.py` | Form field binding, validation feedback |
| `profil_service.py` | update_personel(), upload_file_to_drive() |
| `profil_state.py` | form_dirty, selected_files, upload_progress |

#### Çalışma Adımları

- [ ] 1. Eski `personel_overview_panel.py` analiz
- [ ] 2. pages/profil/ klasörü oluştur
- [ ] 3. `profil_view.py` oluştur
- [ ] 4. `profil_presenter.py` oluştur
- [ ] 5. `profil_service.py` oluştur
- [ ] 6. Shared components'i kullan (avatar_widget, status_indicator)
- [ ] 7. Tests yaz
- [ ] 8. Eski dosya sil

---

### Phase 2.D: UTS Parser Modülü (`cihaz/utils/uts_parser/`)

#### Oluşturulacak Yapı
```
ui/pages/cihaz/
  utils/
    uts_parser/
      __init__.py
      html_scraper.py            # BeautifulSoup parsing (300 satır)
      mapper.py                  # Field mapping (250 satır)
      validator.py               # Data validation (150 satır)
      cache.py                   # LRU cache (100 satır)
```

#### Sorumluluk Dağılımı

| Dosya | Sorumluluk |
|---|---|
| `html_scraper.py` | UTS HTML → device objects |
| `mapper.py` | UTS field → cihaz schema mapping |
| `validator.py` | Seri no, model no, tarih format kontrol |
| `cache.py` | Parsed sonuçları cache'le |

#### Yazılacak Testler

```python
# tests/utils/cihaz/test_uts_html_scraper.py
✓ test_parse_uts_page()
✓ test_extract_device_links()

# tests/utils/cihaz/test_uts_mapper.py
✓ test_field_mapping_accuracy()

# tests/utils/cihaz/test_uts_validator.py
✓ test_serial_no_format()
✓ test_model_no_format()
✓ test_validation_failure_handling()
```

#### Çalışma Adımları

- [ ] 1. Eski `uts_parser.py` analiz
- [ ] 2. `utils/uts_parser/` klasörü oluştur
- [ ] 3. `html_scraper.py` oluştur
- [ ] 4. `mapper.py` oluştur
- [ ] 5. `validator.py` oluştur
- [ ] 6. `cache.py` oluştur
- [ ] 7. Tests yaz
- [ ] 8. Eski dosya sil

---

### ✅ Sprint 2 Acceptance Criteria

- [ ] 16 yeni dosya oluşturuldu (listesi 4 + profil 4 + parser 4 + components 4)
- [ ] 12+ unit test yazıldı
- [ ] Personel listesi / profil güncelleme / UTS parsing workflows bozulmadı
- [ ] Avatar caching test edildi
- [ ] Import güncellemeleri yapıldı

---

## 🟠 SPRINT 3 (Hafta 5-6) — Personel İşlem Modülleri + Srvice Layer

### Phase 3.A: İzin Takip (`personel/pages/izin/`)

#### Oluşturulacak Yapı
```
ui/pages/personel/
  pages/
    izin/
      __init__.py
      izin_view.py               # Personel seçimi + tablo + form (350 satır)
      izin_presenter.py          # Model + state binding (250 satır)
      izin_service.py            # CRUD + pasif statü kuralı (200 satır)
      izin_state.py              # State (100 satır)
```

#### Sorumluluk Dağılımı

| Dosya | Sorumluluk |
|---|---|
| `izin_view.py` | Personel dropdown, ay/takvim, tablo, form |
| `izin_presenter.py` | Tablo model, bakiye hesaplama binding |
| `izin_service.py` | CRUD, pasif statü kuralı (30 gün → pasif), validasyon |
| `izin_state.py` | selected_personel, selected_month, izin_list |

#### **ÖNEMLİ:** Pasif Statü Kuralı Transferi

⚠️ İzin kayıtlarında 30+ gün pasif durum trigger'ı **service katmanına** taşınmalı:

```python
# izin_service.py içinde
class IzinService:
    def add_izin(self, personel_id, days, izin_type):
        """Yeni izin kaydı ekle ve pasif statü kontrol et"""
        izin = self._repository.create_izin(...)
        
        # ⚠️ KURAL: Toplam 30+ gün pasif alanına geç
        total_days = self._repository.sum_izin_days(personel_id, year)
        if total_days >= 30:
            self._personel_service.set_pasif(personel_id)
        
        return izin
```

#### Yazılacak Testler

```python
# tests/pages/personel/test_izin_presenter.py
✓ test_load_izin_for_personel()
✓ test_calculate_kalan_izin()
✓ test_filter_by_month()

# tests/pages/personel/test_izin_service.py
✓ test_add_izin_normal()
✓ test_add_izin_triggers_pasif_30_days()  # KRITIK KURAL!
✓ test_remove_izin_removes_pasif_status()
✓ test_set_pasif_after_30_days()

# tests/pages/personel/test_izin_integration.py (E2E)
✓ test_izin_30_days_pasif_workflow()
```

#### Çalışma Adımları

- [ ] 1. Eski `izin_takip.py` analiz
- [ ] 2. pages/izin/ klasörü oluştur
- [ ] 3. `izin_view.py` oluştur
- [ ] 4. `izin_state.py` oluştur
- [ ] 5. `izin_presenter.py` oluştur
- [ ] 6. `izin_service.py` oluştur — **pasif statü kuralını buraya taşı**
- [ ] 7. Tests yaz (5-6 test)
- [ ] 8. Integration test — İzin + pasif statü E2E
- [ ] 9. Eski dosya sil

---

### Phase 3.B: Personel Ekle (`personel/pages/ekle/`)

#### Oluşturulacak Yapı
```
ui/pages/personel/
  pages/
    ekle/
      __init__.py
      ekle_view.py               # Form layout (300 satır)
      ekle_presenter.py          # Form validation display (250 satır)
      ekle_service.py            # Save + auto-user-creation (200 satır)
      ekle_state.py              # Form state (100 satır)
```

#### Sorumluluk Dağılımı

| Dosya | Sorumluluk |
|---|---|
| `ekle_view.py` | Form fields (TC, Ad, Soyad, vb), filte seçimi |
| `ekle_presenter.py` | Validation feedback, required field indication |
| `ekle_service.py` | validate_personel(), save_personel(), **create_system_user()** |
| `ekle_state.py` | form_fields_dict, validation_errors |

#### **ÖNEMLİ:** Auto User Creation

⚠️ Yeni personel kaydı → otomatik sistem kullanıcısı oluştur:

```python
# ekle_service.py içinde
class PersonelEkleService:
    def save_personel(self, form_data):
        """Personel kaydet ve sistem kültürüne user ekle"""
        personel = self._repository.create_personel(form_data)
        
        # ÖNEMLİ: LOGI modülü entegrasyonu
        username = self._generate_username(personel.ad, personel.soyad)
        password = self._generate_initial_password(username)
        
        self._auth_service.create_user(
            username=username,
            password=password,
            personel_id=personel.id,
            role='VIEWER'  # Varsayılan rol
        )
        
        return personel
```

#### Yazılacak Testler

```python
# tests/pages/personel/test_ekle_presenter.py
✓ test_form_validation_tc_kimlik()
✓ test_form_validation_required_fields()

# tests/pages/personel/test_ekle_service.py
✓ test_save_personel()
✓ test_auto_create_system_user()
✓ test_username_generation_from_name()
✓ test_initial_password_generation()

# tests/pages/personel/test_ekle_integration.py (E2E)
✓ test_ekle_personel_creates_user_logi_module()  # KRITIK!
```

#### Çalışma Adımları

- [ ] 1. Eski `personel_ekle.py` analiz
- [ ] 2. pages/ekle/ klasörü oluştur
- [ ] 3. `ekle_view.py` oluştur
- [ ] 4. `ekle_state.py` oluştur
- [ ] 5. `ekle_presenter.py` oluştur
- [ ] 6. `ekle_service.py` oluştur — **auto user creation logic**
- [ ] 7. LOGI modülü (auth_service) integration kontrol et
- [ ] 8. Tests yaz (5-6 test)
- [ ] 9. Integration test — Personel ekleme + user oluşturma E2E
- [ ] 10. Eski dosya sil

---

### Phase 3.C: Personel Service Katmanı (`personel/services/`)

#### Oluşturulacak Yapı

```
ui/pages/personel/
  services/
    __init__.py
    personel_service.py          # Main orchestration (300 satır)
    personel_validator.py        # Shared validation rules (200 satır)
    pasif_status_manager.py      # Pasif statü kuralları (150 satır)
    avatar_service.py            # Avatar download + cache (150 satır)
    file_service.py              # File upload + sync (150 satır)
```

#### Sorumluluk Dağılımı

| Dosya | Sorumluluk |
|---|---|
| `personel_service.py` | get_personel(), update_personel(), delete_personel() |
| `personel_validator.py` | validate_tc_kimlik(), validate_email(), check_duplicates() |
| `pasif_status_manager.py` | get_pasif_reason(), set_pasif(), remove_pasif() |
| `avatar_service.py` | download_avatar(), cache_avatar(), get_avatar_pixmap() |
| `file_service.py` | upload_personel_file(), sync_drive_files(), download_file() |

#### Yazılacak Testler

```python
# tests/services/personel/test_personel_validator.py
✓ test_validate_tc_kimlik_format()
✓ test_validate_email_format()
✓ test_check_duplicate_tc()

# tests/services/personel/test_pasif_status_manager.py
✓ test_set_pasif_with_reason()
✓ test_remove_pasif_status()
✓ test_get_pasif_reason()
```

#### Çalışma Adımları

- [ ] 1. Personel modülü içine services/ klasörü oluştur
- [ ] 2. `personel_service.py` oluştur (orchestrator)
- [ ] 3. `personel_validator.py` oluştur (validation rules)
- [ ] 4. `pasif_status_manager.py` oluştur (30 gün kuralı vb.)
- [ ] 5. `avatar_service.py` oluştur
- [ ] 6. `file_service.py` oluştur
- [ ] 7. Tests yaz
- [ ] 8. İzin + ekle pages'i bu service'leri kullanacak şekilde güncelle

---

### ✅ Sprint 3 Acceptance Criteria

- [ ] 13 yeni dosya oluşturuldu (izin 4 + ekle 4 + services 5)
- [ ] 15+ unit test yazıldı
- [ ] **Pasif statü kuralı** service katmanında test edildi (30 gün trigger)
- [ ] **Auto user creation** service katmanında test edildi (LOGI integration)
- [ ] İzin ekleme/silme workflows bozulmadı
- [ ] Personel ekle → user oluşturma E2E bozulmadı
- [ ] Import güncellemeleri yapıldı

---

## 🎯 Global Acceptance Criteria (Tüm Sprintler)

### Dosya Yapısı
- [ ] 33 yeni dosya oluşturuldu
- [ ] 8 eski monolitik dosya silindi
- [ ] Global pattern tutarlı uygulandı (pages/, components/, services/, utils/)

### Tests
- [ ] 35+ unit test yazıldı
- [ ] 5+ integration test yazıldı
- [ ] Test pass rate: 100%
- [ ] **Kritik kurallar test edildi:**
  - [ ] Pasif statü (30 gün)
  - [ ] Auto user creation
  - [ ] Avatar caching
  - [ ] File upload offline handling

### Code Quality
- [ ] Average file size: ~350 satır (başta 1200 satır)
- [ ] Cyclomatic complexity: ~8 (başta 25+)
- [ ] Test coverage: 80%+ kritik services

### Performance
- [ ] Lazy-loading çalışıyor (personel listesi 100 batch)
- [ ] Avatar cache hit rate: >80%
- [ ] No memory leaks (Personel liste paging)

### Integration
- [ ] UI → Service → Repository → DB katmanı net
- [ ] LOGI modülü entegrasyonu (auth criar user)
- [ ] Drive sync hata handling

---

## 📝 Sprint Başlama Checklist

### Her Sprint Öncesi
- [ ] Eski dosya tam analiz edildi
- [ ] Yeni klasör yapısı oluşturuldu
- [ ] State dataclass tanımlandı
- [ ] Service interface yazıldı

### Her Sprint Sonrası
- [ ] Tüm testler geçti (pytest)
- [ ] Import güncellemeleri yapıldı
- [ ] Eski dosya backed up → silindiCode review yapıldı
- [ ] Documentation güncellendi

---

## 🚀 Başlangıç: Aşama 1 — UI Dosya Analizi

**Paralel olarak yapılacak:**

1. **Scan Tüm UI Dosyaları** — Mevcut yapı haritası
2. **Shared Components Identify** — Tekrar eden bileşenler
3. **Module Boundary Harita** — Her modülün sorumluluk sınırı
4. **Blueprint Taslağı** — Global pattern refiner

**Beklenen Çıktı:** `GLOBAL_ARCHITECTURE_BLUEPRINT.md` (detaylı 50-sayfalık rehber)

---

## 📚 Referanslar

- Original: `docs/PARCALAMA_PLANI_DETAYLI.md`
- Master: `docs/MASTER_TEKNIK_DURUM_VE_YOLHARITA.md`
- Pattern: `docs/REPYS_DURUM_RAPORU_2026-02.md` (Sektion 4.3)

# REPYS UI Taraması — Hızlı Özet

## Genel Bakış

| Metrik | Değer |
|--------|-------|
| **Toplam UI Dosyası** | 68 |
| **Toplam UI Satırı** | 30.115 |
| **Python Dosyası** | 66 (boş __init__.py hariç) |
| **Dosya Boyutu Ortalaması** | 456 satır |

## Modül Dağılımı

| Modül | Dosya sayısı | Satır | Durum |
|-------|--------------|-------|-------|
| **Cihaz** (merkez + list + forms + components) | 18 | 11.000+ | ⚠️ Mega (ariza: 1.444, bakim: 2.259, kalibrasyon: 1.268) |
| **Personel** (merkez + list + forms + components) | 17 | 8.000+ | ⚠️ Mega (ekle: 891, listesi: 994, izin: 929, overview: 971) |
| **RKE** (muayene, yönetim, rapor) | 3 | 2.689 | ⚠️ rke_muayene: 1.385 satır |
| **Admin** (panel + views) | 6 | 984 | ✓ Normal |
| **Auth** (login, password) | 3 | 106 | ✓ Basit |
| **Components** (shared) | 4 | 622 | ✓ Ortak kullanım |
| **Styles** (tema + renk + ikonlar) | 6 | 1.807 | ✓ Merkezi |
| **Guards** (YetkilendirmeControl) | 3 | 112 | ✓ Basit |
| **Permissions** | 2 | 33 | ✓ Minimal |

## Tekrar Eden Bileşenler (Optimizasyon Fırsatları)

### 1. QAbstractTableModel — 14 Dosya

```
Cihaz: cihaz_listesi, ariza_kayit, bakim_form, kalibrasyon_form, dokuman (5)
Personel: personel_listesi, izin_takip, saglik_takip, isten_ayrilik, puantaj (5)
RKE: rke_muayene, rke_yonetim, rke_rapor (3)
Shared: data_table (1)
```

**Sorun:** Her dosya kendi CustomTableModel sınıfını tanımladıyor  
**Çözüm:** BaseTableModel oluştur → **300+ satır tasarruf**

### 2. KPI Kartları — 5+ Dosya

```
dashboard.py, ariza_kayit.py, bakim_form.py, kalibrasyon_form.py, personel_overview_panel.py
```

**Çözüm:** KPICard widget → **200+ satır tasarruf**

### 3. Dialog'lar — 10+ Dosya

```
login, change_password, user_edit, hizli_izin_giris, hizli_saglik_giris, vb.
```

**Çözüm:** BaseDialog wrapper → **150+ satır tasarruf**

### 4. Search + Filter Panel — 7 Dosya

```
Tüm listeler: cihaz_listesi, ariza_kayit, bakim_form, kalibrasyon_form, 
personel_listesi, izin_takip, saglik_takip
```

**Çözüm:** FilterPanel component → **250+ satır tasarruf**

### 5. Avatar / Profil Resmi — 2 Dosya

```
personel_listesi.py, personel_overview_panel.py
```

**Çözüm:** AvatarWidget → **100+ satır tasarruf**

### 6. File Upload — 5+ Dosya

```
personel_ekle.py, cihaz_dokuman_panel.py, personel_dokuman_panel.py,
personel_overview_panel.py, bakim_form.py
```

**Çözüm:** FileUploadWidget → **300+ satır tasarruf**

### 7. Status Badge — 4 Dosya

```
ariza_kayit.py, kalibrasyon_form.py, personel_listesi.py, fhsz_yonetim.py
```

**Çözüm:** StatusBadge widget → **100+ satır tasarruf**

**TOPLAM TASARRUF POTANSIYELI: 1.400+ satır**

## En Büyük Dosyalar (Refactoring Hedefleri)

| Dosya | Satır | Bölme Önerisi |
|-------|-------|---------------|
| bakim_form.py | 2.259 | 6 dosyaya bölünmeli (→ ~350-500 satır) |
| ariza_kayit.py | 1.444 | 4 dosyaya bölünmeli (→ ~300-400 satır) |
| rke_muayene.py | 1.385 | 4 dosyaya bölünmeli (→ ~300-350 satır) |
| uts_parser.py | 1.037 | 3 dosyaya bölünmeli (data parsing, scraping, models) |
| personel_ekle.py | 891 | 3 dosyaya bölünmeli (form, file upload, validation) |
| personel_overview_panel.py | 971 | 3 dosyaya bölünmeli (main, edit mode, files) |
| kalibrasyon_form.py | 1.268 | 4 dosyaya bölünmeli (→ ~300-350 satır) |
| izin_takip.py | 929 | 3 dosyaya bölünmeli (→ ~300-350 satır) |
| saglik_takip.py | 850 | 3 dosyaya bölünmeli (→ ~250-350 satır) |
| personel_listesi.py | 994 | 2-3 dosyaya bölünmeli (→ ~350-500 satır) |

**Not:** >900 satır dosya başlamadan taraflı/refactoring gerekli (en az)

## Repository Kullanımı

✓ **Çoğu dosya Repository kullanıyor:**
- CihazRepository (7 dosya)
- PersonelRepository (5 dosya)
- ArizaRepository (3 dosya)
- BakimRepository (2 dosya)
- IzinRepository (3 dosya)
- SaglikRepository (2 dosya)
- RKERepository (3 dosya)
- vb.

⚠️ **Eksiklikler:**
- Service katmanı yok (business logic UI'da)
- Direct repository access (tight coupling)

**Önerilen:** 
```python
core/services/
├── cihaz_service.py
├── ariza_service.py
├── bakım_service.py
├── personel_service.py
├── izin_service.py
└── rke_service.py
```

## Google Drive Integration

**Kullanan dosyalar:**
- personel_ekle.py ✓
- cihaz_dokuman_panel.py ✓
- personel_dokuman_panel.py ✓
- personel_overview_panel.py ✓
- bakim_form.py ✓

**Sorun:** Upload logic dağınık, tekrar eden kod

**Çözüm:** `core/drive_service.py` merkezi yönetimi

## Theme/Style Sistemi

✓ **İyi organize:**
- DarkTheme (merkezi renk token'ları)
- ComponentStyles (QSS string'leri)
- IconSystem (grupplar + rendering)

✓ **Avantajlar:**
- Hard-coded renk yok
- Konsistent stil
- Tema değiştirme kolay

⚠️ **İyileştirebilir:**
- Light theme kullanılmıyor (stub)
- theme_registry minimal

## Import & Dependency

⚠️ **Potansiyel circular import risk:**
- styles ↔ components
- pages ↔ main_window
- ui ↔ database

✓ **Recomendation:** Lazy import veya resolve dep's

## Action Items (Sırayla)

### Phase 1 (2-3 hafta) — KRITIK

```
1. [ ] BaseTableModel oluştur
      → 14 dosya refactor
      → ~300 satır tasarruf

2. [ ] Common widgets library:
      → KPICard, StatusBadge, AvatarWidget, FileUploadWidget
      → ~500 satır tasarruf

3. [ ] BaseDialog ekleme
      → ~150 satır tasarruf
```

### Phase 2 (3-4 hafta) — ÖNEMLİ

```
1. [ ] Mega dosyaları bölme (8 dosya)
      → 20+ dosyaya dönüş
      → Her dosya <600 satır
      
2. [ ] Service katmanı:
      → CihazService, ArizaService, PersonelService
      → Business logic centralization
      
3. [ ] Import organization
      → ui/__init__.py
      → ui/pages/__init__.py
```

### Phase 3 (2 hafta) — İYİLEŞTİRME

```
1. [ ] Test infrastructure
2. [ ] Documentation (UI_ARCHITECTURE.md, COMPONENTS.md)
3. [ ] Code review & cleanup
```

## Beklenen Kazanımlar (Refactoring Sonrası)

| Metrik | Şimdiki | Hedef | Gain |
|--------|---------|-------|------|
| **Total Lines** | 30.115 | 25.000 | -14% |
| **Mega Files (>900)** | 8 | 0 | -100% |
| **Duplicate Code** | ~1.400 | ~100 | -93% |
| **Maintainability Index** | ⚠️ Orta | ✓ Yüksek | +40% |
| **TestCoverage** | 0% | 60%+ | +60% |
| **Dev Speed** | 1x | 1.3x | +30% |

## Dosya Lokasyonları

- **Ana rapor:** [UI_TARAMA_RAPORU.md](UI_TARAMA_RAPORU.md)
- **Bu dosya:** UI_TARAMA_OZET.md
- **Analiz data:** ui_analysis.json (generated)

---

**Son Güncelleme:** 27 Şubat 2026  
**Analiz Aracı:** Python regex + file walker  
**Kapsam:** 68 dosya, 30.115 satır

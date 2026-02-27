# REPYS Büyük Dosya Parçalama Planı — Detaylı Uygulama Rehberi

**Tarih:** 27 Şubat 2026  
**Prioriy:** 🔴 YÜKSEK — P3 yol haritasının temelini oluşturur  
**Toplam Parçalanacak Dosya:** 8 dosya (12 satır+ toplam ~8500 satır)  
**Hedef Sonuç:** 30+ dosyaya bölünecek (~350 satır ortalama)

---

## 📊 Özet Tablo

| Sıra | Dosya | Satır | Parça Sayısı | Tahmini Saat | Başlangıç |
|------|-------|-------|--------|---------|-----------|
| 🔴 1 | `bakim_form.py` | 2259 | 4-5 | 6-8h | Sprint 1 |
| 🔴 2 | `ariza_kayit.py` | 1444 | 3-4 | 5-6h | Sprint 1 |
| 🔴 3 | `kalibrasyon_form.py` | 1268 | 3-4 | 5-6h | Sprint 1 |
| 🟠 4 | `uts_parser.py` | 1037 | 3-4 | 4-5h | Sprint 2 |
| 🟠 5 | `personel_listesi.py` | 994 | 3-4 | 4-5h | Sprint 2 |
| 🟠 6 | `personel_overview_panel.py` | 971 | 3-4 | 4-5h | Sprint 2 |
| 🟠 7 | `izin_takip.py` | 929 | 3-4 | 4-5h | Sprint 3 |
| 🟠 8 | `personel_ekle.py` | 891 | 3-4 | 4-5h | Sprint 3 |

**Toplam Tahmini Süre:** 36-44 saat (4-5 hafta, 2-3 geliştirici)

---

## 🔴 SPRINT 1 (Hafta 1-2) — Cihaz Modülü Form Parçalaması

### 1.1 `ui/pages/cihaz/bakim_form.py` (2259 satır) → 4-5 dosya

#### 📋 Mevcut Sorumluluklar
- **KPI Şeridi** - Bakım durumu görselleştirmesi (0-3 ay renk kodlama)
- **Bakım Tablosu** - QAbstractTableModel + custom delegate
- **Otomatik Plan Oluşturma** - 3/6/12 ay periyodları
- **Google Drive Entegrasyonu** - Rapor dosyası upload
- **Form Detayları** - Bakım bilgisi CRUD alanları

#### ✂️ Parçalama Yapısı

**A. `bakim_form.py` (Kalan: 450 satır) — Ana View**
```python
class BakimFormView(QWidget):
    """Ana bakım formu container.
    - UI layout
    - Event wiring
    - Drive upload signal handling
    """
```
- UI bileşenlerini assemble et
- Signal/slot wiring
- Upload progress gösterimi

**B. `components/bakim_table.py` (300 satır) — Tablo Model+Delegate**
```python
class BakimTableModel(QAbstractTableModel):
    """Bakım kayıtları listesi modeli"""
    
class BakimTableDelegate(QStyledItemDelegate):
    """Bakım tablosu custom rendering (durum rengi, tarih formatting)"""
```

**C. `components/bakim_form_fields.py` (300 satır) — Form Alanları**
```python
class BakimFormFields(QGroupBox):
    """Bakım detayları form:
    - Tarih seçiciler
    - Durum dropdown
    - Rapor input alanları
    """
```

**D. `components/bakim_kpi_widget.py` (200 satır) — KPI Şeridi**
```python
class BakimKPIWidget(QWidget):
    """KPI renk şeridi:
    - 0-3 ay: yeşil
    - 3-6 ay: sarı
    - 6+ ay: kırmızı
    - Tooltip ile detlay
    """
```

**E. `services/bakim_service.py` (250 satır) — Business Logic**
```python
class BakimService:
    """Bakım işlemleri:
    - get_all_bakim()
    - create_bakim()
    - update_bakim()
    - auto_generate_plan(device_id, interval)
    - upload_report_to_drive()
    """
```

#### 🧪 Yazılacak Testler

```
tests/components/test_bakim_table.py
  ✓ BakimTableModel veri yükleme
  ✓ Satır sayısı doğruluğu
  ✓ BakimTableDelegate renk kodlama (0-3 ay yeşil, vs)

tests/components/test_bakim_kpi_widget.py
  ✓ KPI rengi 0-3 ay (yeşil)
  ✓ KPI rengi 6+ ay (kırmızı)

tests/services/test_bakim_service.py
  ✓ Auto-generate plan 3 ay aralığı
  ✓ Auto-generate plan 6 ay aralığı
  ✓ Update bakım satırı
```

---

### 1.2 `ui/pages/cihaz/ariza_kayit.py` (1444 satır) → 3-4 dosya

#### 📋 Mevcut Sorumluluklar
- **Arıza Tablosu** - Açık/kritik arızalar listesi
- **Durum Filtreleri** - Açık, Kapalı, Kritik vb.
- **Detay Paneli** - Arıza bilgisi gösterimi
- **İşlem Penceresi** - Arıza işlem ekleme
- **Notification Paneli** - Uyarılar ve hata mesajları

#### ✂️ Parçalama Yapısı

**A. `ariza_kayit.py` (500 satır) — Ana View**
```python
class ArizaKayitView(QWidget):
    """Ana arıza kayıt sayfası
    - Layout assembly
    - Tab/panel switching
    - Event handling
    """
```

**B. `components/ariza_table.py` (350 satır) — Tablo + Delegate**
```python
class ArizaTableModel(QAbstractTableModel):
    """Arıza listesi"""
    
class ArizaTableDelegate(QStyledItemDelegate):
    """Arıza silme renderı: durum rengi, öncelik ikonu"""
```

**C. `components/ariza_filter_panel.py` (200 satır) — Filtreler**
```python
class ArizaFilterPanel(QGroupBox):
    """Durum filtreleri:
    - Açık, Kapalı, Kritik, Gözlemleme
    - Bileşen seçici
    - Filtre uygula butonu
    """
```

**D. `services/ariza_service.py` (250 satır) — CRUD + İşlemler**
```python
class ArizaService:
    """Arıza işlemleri:
    - get_ariza_list(filter)
    - create_ariza()
    - close_ariza()
    - add_islem()
    """
```

#### 🧪 Yazılacak Testler

```
tests/components/test_ariza_table.py
  ✓ Tablo satırları doğru yükleniyor
  ✓ Filtre (Açık) uygulanıyor
  ✓ Filtre (Kritik) uygulanıyor

tests/services/test_ariza_service.py
  ✓ Yeni arıza yaratma
  ✓ Arıza kapatma
  ✓ İşlem ekleme
```

---

### 1.3 `ui/pages/cihaz/kalibrasyon_form.py` (1268 satır) → 3-4 dosya

#### 📋 Mevcut Sorumluluklar
- **KPI Göstergesi** - Kalibrasyon durumu (geç/normal/planlı)
- **Performans Grid'i** - Cihaz başına sıfır hata oranı
- **Bitiş Tarihi İzleme** - Yaklaşan kalibrasyonlar
- **Tablo+Delegate** - Kalibrasyon kayıtları listesi
- **Form Alanları** - Kalibrasyon detayları

#### ✂️ Parçalama Yapısı

**A. `kalibrasyon_form.py` (400 satır) — Ana View**
```python
class KalibrasyonFormView(QWidget):
    """Kalibrasyon formu container"""
```

**B. `components/kalibrasyon_table.py` (250 satır) — Tablo**
```python
class KalibrasyonTableModel(QAbstractTableModel):
    """Kalibrasyon listesi"""
    
class KalibrasyonDelegate(QStyledItemDelegate):
    """Durum renk kodlaması"""
```

**C. `components/kalibrasyon_kpi.py` (200 satır) — KPI Widget**
```python
class KalibrasyonKPIWidget(QWidget):
    """Kalibrasyon durumu KPI:
    - Geçmiş kalibrasyonlar: kırmızı
    - Normal aralık: yeşil
    - Planlı (1 ay içinde): sarı
    """
```

**D. `services/kalibrasyon_service.py` (250 satır) — Business Logic**
```python
class KalibrasyonService:
    """Kalibrasyon işlemleri"""
```

---

## 🟠 SPRINT 2 (Hafta 3-4) — Personel & Parser Modülleri

### 2.1 `ui/pages/cihaz/components/uts_parser.py` (1037 satır) → 3-4 dosya

#### 📋 Mevcut Sorumluluklar
- **HTML Scraping** - UTS arşivinden cihaz verisi çekme
- **JSON Mapping** - Fields eşleştirmesi
- **Validasyon** - Veri format kontrolleri
- **Cache** - Parsed verileri tutma

#### ✂️ Parçalama Yapısı

**A. `parsers/uts_html_scraper.py` (300 satır) — HTML Parser**
```python
class UTSHTMLScraper:
    """BeautifulSoup ile UTS HTML parsing"""
```

**B. `parsers/uts_mapper.py` (250 satır) — Field Mapping**
```python
class UTSFieldMapper:
    """UTS alanlarını cihaz modeline eşleştir"""
    
class UTSFieldConfig:
    """Field mapping tanımları"""
```

**C. `parsers/uts_validator.py` (200 satır) — Validasyon**
```python
class UTSValidator:
    """Parsed verilerin kontrolü"""
```

**D. `parsers/uts_cache.py` (150 satır) — Caching**
```python
class UTSCache:
    """Parsed verileri cache'le"""
```

#### 🧪 Yazılacak Testler

```
tests/parsers/test_uts_scraper.py
  ✓ HTML sayfasını parse etme
  ✓ Cihaz linklerini çıkarma
  ✓ Teknik veri çıkarma

tests/parsers/test_uts_mapper.py
  ✓ UTS field → cihaz column mapping
  ✓ Missing field handling

tests/parsers/test_uts_validator.py
  ✓ Seri no formatı
  ✓ Model numarası
  ✓ Tarih formatı
```

---

### 2.2 `ui/pages/personel/personel_listesi.py` (994 satır) → 3-4 dosya

#### 📋 Mevcut Sorumluluklar
- **Tablo Model** - Personel listesi
- **Proxy Filtresi** - Arama/durum filtreleri
- **Avatar İndir** - Görselleri cache'leme
- **Lazy-Loading** - 100 satır batch yükleme

#### ✂️ Parçalama Yapısı

**A. `personel_listesi.py` (300 satır) — Ana View**
```python
class PersonelListeView(QWidget):
    """Personel listesi sayfası"""
```

**B. `models/personel_list_model.py` (250 satır) — Table Model**
```python
class PersonelListModel(QAbstractTableModel):
    """Personel tablo modeli + lazy-loading"""
```

**C. `components/personel_filter_panel.py` (200 satır) — Filtreler**
```python
class PersonelFilterPanel(QGroupBox):
    """Personel filtreleri:
    - İsim arama
    - Durum (Aktif, Pasif, İzinli)
    - Birim
    """
```

**D. `services/personel_avatar_service.py` (150 satır) — Avatar**
```python
class PersonelAvatarService:
    """Avatar indirme ve caching"""
```

#### 🧪 Yazılacak Testler

```
tests/models/test_personel_list_model.py
  ✓ Model veri yükleme
  ✓ Lazy-loading (100 personel / batch)
  ✓ Filtre uygulanması

tests/services/test_personel_avatar_service.py
  ✓ Avatar indirme (başarılı)
  ✓ Avatar indirme (timeout handling)
  ✓ Cache kullanımı
```

---

### 2.3 `ui/pages/personel/components/personel_overview_panel.py` (971 satır) → 3-4 dosya

#### 📋 Mevcut Sorumluluklar
- **Özet Metriks** - Kişi bilgisi top card
- **Düzenlenebilir Form** - Personel bilgisi güncelleme
- **Dosya Upload** - Fotoğraf, diploma vb.
- **Drive Entegrasyonu** - Dosya senkronizasyonu

#### ✂️ Parçalama Yapısı

**A. `personel_overview_panel.py` (300 satır) — Ana Panel**
```python
class PersonelOverviewPanel(QWidget):
    """Personel özet panel container"""
```

**B. `components/personel_form_fields.py` (250 satır) — Form Fields**
```python
class PersonelFormFields(QGroupBox):
    """TC Kimlik, Ad Soyad, Doğum Tarihi, vb. form alanları"""
```

**C. `components/personel_file_manager.py` (200 satır) — Dosya Yönetimi**
```python
class PersonelFileManager(QGroupBox):
    """Fotoğraf, diploma, belgeler yönetimi"""
```

**D. `services/personel_file_service.py` (200 satır) — Dosya Servisi**
```python
class PersonelFileService:
    """Dosya upload, download, cache"""
```

#### 🧪 Yazılacak Testler

```
tests/components/test_personel_file_manager.py
  ✓ Dosya seçimi
  ✓ Dosya upload (Drive)
  ✓ Dosya upload (offline)

tests/services/test_personel_file_service.py
  ✓ File upload başarılı
  ✓ File upload timeout
  ✓ Cache handling
```

---

## 🟠 SPRINT 3 (Hafta 5-6) — Personel İşleme Modülleri

### 3.1 `ui/pages/personel/izin_takip.py` (929 satır) → 3-4 dosya

#### 📋 Mevcut Sorumluluklar
- **Personel Seçimi** - Dropdown + arama
- **Ay/Yıl Filtreleri** - Dönem seçimi
- **İzin Bakiyesi Hesaplaması** - Kütüphaneden veri çekme
- **CRUD İşlemleri** - İzin ekleme, silme, güncelleme

#### ✂️ Parçalama Yapısı

**A. `izin_takip.py` (350 satır) — Ana View**
```python
class IzinTakipView(QWidget):
    """İzin takip sayfası"""
```

**B. `components/izin_form.py` (250 satır) — İzin Form**
```python
class IzinFormWidget(QGroupBox):
    """İzin tanım formu:
    - Tarih aralığı seçici
    - İzin tipi (Yıllık, Ücretsiz, vb.)
    - Açıklama
    """
```

**C. `services/izin_calculator.py` (200 satır) — Hesaplama**
```python
class IzinCalculator:
    """İzin bakiyesi, pasif statü, quota hesaplaması"""
    
    def calculate_balance(personel_id, year) -> IzinBalance:
    def should_set_pasif(personel_id) -> bool:  # 30+ gün
```

**D. `models/izin_model.py` (150 satır) — Model**
```python
class IzinRecord:
    """İzin kaydı dataclass"""
    
class IzinBalance:
    """Bakiye bilgileri"""
```

#### 🧪 Yazılacak Testler

```
tests/services/test_izin_calculator.py
  ✓ Izin bakiyesi hesaplaması (normal)
  ✓ Pasif statü: 30+ gün izin
  ✓ Pasif statü: 30 gün altı (aktif kalmalı)
  ✓ Yıl sonu bakiye devri

tests/models/test_izin_model.py
  ✓ IzinBalance oluşturma
  ✓ Bakiye doğruluğu
```

---

### 3.2 `ui/pages/personel/personel_ekle.py` (891 satır) → 3-4 dosya

#### 📋 Mevcut Sorumluluklar
- **Form Bileşenleri** - TC, adres, iletişim alanları
- **TC Doğrulama** - Kimlik algoritması kontrolü
- **Dosya Upload** - Diploma, fotoğraf vb.
- **Validasyon** - Email, telefon, tarih formatı
- **Veritabanı Kayıt** - Insert + auto-commit

#### ✂️ Parçalama Yapısı

**A. `personel_ekle.py` (350 satır) — Ana Form**
```python
class PersonelEklePage(QWidget):
    """Personel ekleme sayfası"""
```

**B. `components/personel_form_sections.py` (250 satır) — Form Bölümleri**
```python
class PersonelInfoSection(QGroupBox):
    """Temel bilgiler: TC, ad, doğum tarihi"""
    
class PersonelContactSection(QGroupBox):
    """İletişim: telefon, email"""
    
class PersonelEmploymentSection(QGroupBox):
    """İstihdam: unvan, başlama tarihi"""
```

**C. `validators/personel_validators.py` (150 satır) — Validatörler**
```python
class PersonelValidator:
    """TC algoritması, email, telefon, tarih formatı"""
    
class TCValidator:
    """Türk Kimlik Numarası algoritması"""
```

**D. `services/personel_file_uploader.py` (200 satır) — Upload Service**
```python
class PersonelFileUploader:
    """Dosya upload (paralel worker)"""
    
    def upload_photo(file_path) → drive_link
    def upload_diploma(file_path) → drive_link
```

#### 🧪 Yazılacak Testler

```
tests/validators/test_personel_validators.py
  ✓ TC algoritması (geçerli TC)
  ✓ TC algoritması (geçersiz TC)
  ✓ Email validasyonu
  ✓ Telefon formatı

tests/services/test_personel_file_uploader.py
  ✓ Dosya upload (Drive up)
  ✓ Dosya upload (Drive down - offline queue)
  ✓ Paralel upload

tests/test_personel_ekle_integration.py
  ✓ Form doğrulama + kaydetme
  ✓ Dosya upload sonrası otomatik kullanıcı oluşturma
```

---

## 📋 Parçalama Sırası ve Bağımlılıklar

```
SPRINT 1 (Cihaz Modülü - Hafta 1-2)
├── bakim_form.py → bakim_table + bakim_form_fields + bakim_kpi + bakim_service
├── ariza_kayit.py → ariza_table + ariza_filter_panel + ariza_service
└── kalibrasyon_form.py → kalibrasyon_table + kalibrasyon_kpi + kalibrasyon_service

SPRINT 2 (Personel & Parser - Hafta 3-4)
├── uts_parser.py → uts_scraper + uts_mapper + uts_validator + uts_cache
├── personel_listesi.py → personel_list_model + personel_filter_panel + personel_avatar_service
└── personel_overview_panel.py → personel_form_fields + personel_file_manager + personel_file_service

SPRINT 3 (Personel İşlemleri - Hafta 5-6)
├── izin_takip.py → izin_form + izin_calculator + izin_model
└── personel_ekle.py → personel_form_sections + personel_validators + personel_file_uploader
```

---

## 🎯 Kabul Kriterleri (Her Sprint için)

### Sprint Completion Checklist

```
[ ] 1. Orijinal dosya fonksiyonalitesi korunmuş (regresyon yok)
[ ] 2. Yeni dosyalar yazılmış ve import edilmiş
[ ] 3. Test dosyaları yazılmış (minimum 2 test/bileşen)
[ ] 4. Tüm testler PASS (pytest -q)
[ ] 5. Code review tamamlandı
[ ] 6. Ortalama dosya boyutu: 250-350 satır (< 500)
[ ] 7. Git commit message: Sprint + Dosya adı (örn: "Sprint1: bakim_form parçalama")

Örnek:
pytest tests/components/test_bakim_table.py -v
pytest tests/services/test_bakim_service.py -v
→ 12 passed in 1.5s
```

---

## 🔧 Geliştirme Akışı (Örnek: bakim_form.py)

### Adım 1: Tablo Model Çıkartma

```python
# Öncesi: bakim_form.py içinde
class BakimForm(QDialog):
    def __init__(self):
        ...
        self.model = QAbstractTableModel()  # ← 200 satır

# Sonrası: components/bakim_table.py
class BakimTableModel(QAbstractTableModel):
    """Ayrı dosyada, testlenebilir"""
    def __init__(self, db):
        ...
```

### Adım 2: Delegate Çıkartma

```python
# Önceki: bakim_form.py içinde
def paint(self, painter, option, index):
    # 100 satırlık custom rendering ← çıkart

# Sonrası: components/bakim_table.py
class BakimTableDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        # 100 satırlık kod, test edilebilir
```

### Adım 3: Service Katmanı Oluşturma

```python
# Öncesi: bakim_form.py içinde
def load_data(self):
    db = RepositoryRegistry(self.db)
    repo = db.get("Bakim")
    return repo.get_all()  # ← seviye dışı

# Sonrası: services/bakim_service.py
class BakimService:
    def __init__(self, db):
        self.repo = RepositoryRegistry(db).get("Bakim")
    
    def load_all(self):
        return self.repo.get_all()
```

---

## 📈 Metriks Öncesi vs Sonrası

| Metrik | Öncesi | Sonrası | İyileştirme |
|--------|--------|---------|-----------|
| En büyük dosya | 2259 satır | 450 satır | 80% ↓ |
| Ortalama dosya | ~750 satır | ~300 satır | 60% ↓ |
| Testlenebilir kod | 30% | 80% | +50% |
| Kod tekrarı (benzer filtreler) | 3 yerde | 1 yerde (reusable) | -66% |
| Bakım zorluğu | 🔴 Çok Zor | 🟢 Kolay | Büyük ↓ |

---

## 🚀 Sonraki Adım

1. **Sprint 1 Başlangıcı:** bakim_form.py ile başla
   - Tablo model test yaz
   - Refactor et
   - Testler PASS kontrol et

2. **Paralel:** izin_takip.py için test scaffold hazırla

3. **Sprint Bitişi:** Sonraki sprintin planlaması yap

---

**Hazırlanmış:** REPYS Teknik Ekibi  
**Versiyon:** 1.0 — Detaylı Uygulama Rehberi  
**Düzenleme:** 27 Şubat 2026

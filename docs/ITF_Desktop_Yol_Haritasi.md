# ITF Desktop – Proje Analizi & Yol Haritası

## 🔍 Mevcut Durum Analizi

Projenin altyapısı güçlü bir şekilde kurulmuş. Katmanlı mimari, repository pattern, sync servisi ve Google Sheets entegrasyonu düşünülmüş. Ancak devam etmeden önce çözülmesi gereken **kritik tutarsızlıklar** ve **eksik parçalar** var.

---

## 🚨 Önce Düzeltilmesi Gereken Sorunlar

### Sorun 1: `sync_worker.py` — Bozuk Çağrı
```python
# ŞU AN (HATALI):
sync = SyncService()          # ← repositories parametresi yok!
sync.sync_personel()          # ← bu metod yok, sync_all() veya sync_table() olmalı

# OLMASI GEREKEN:
from database.sqlite_manager import SQLiteManager
from database.repository_registry import RepositoryRegistry

db = SQLiteManager()
registry = RepositoryRegistry(db)
sync = SyncService(registry.all())
sync.sync_all()
```

### Sorun 2: `gsheet_manager.py` — Olmayan Fonksiyon Çağrısı
```python
# ŞU AN:
from google_baglanti import get_worksheet    # ← BU FONKSİYON YOK

# google_baglanti.py'de olan: veritabani_getir(vt_tipi, sayfa_adi)
# Köprü gerekli — ya get_worksheet() yazılmalı ya da gsheet_manager adapte edilmeli
```

### Sorun 3: `table_config.py` — Eksik Tablolar
`migrations.py`'de **14 tablo** tanımlı, ama `table_config.py`'de sadece **3 tablo** var:
- ✅ Personel, Izin_Giris, Izin_Bilgi
- ❌ FHSZ_Puantaj, Cihazlar, Cihaz_Ariza, Ariza_Islem, Periyodik_Bakim, Kalibrasyon, Sabitler, Tatiller, Loglar, RKE_List, RKE_Muayene

### Sorun 4: `main.pyw` — QApplication Yok
`main.pyw` şu an sadece sync başlatıyor, ama:
- `QApplication` oluşturulmuyor
- Ana pencere (`QMainWindow`) yok
- `app.exec()` çağrılmıyor
- Uygulama aslında başlatılamıyor

### Sorun 5: `google_baglanti.py` ↔ Yeni Mimari Uyumsuzluğu
Eski dosyada (`google_baglanti.py`) `veritabani_getir("personel", "Personel")` yapısı var (vt_tipi + sayfa adı). Yeni `gsheet_manager.py` ise doğrudan tablo adı ile çalışıyor. Bu iki yaklaşım arasında bir **adaptör/köprü** gerekli.

---

## 🗺️ YOL HARİTASI

### 📌 Faz 0 — Altyapı Düzeltmeleri (Öncelik: KRİTİK)
> Tahmini Süre: 1-2 gün

| # | Görev | Dosya |
|---|-------|-------|
| 0.1 | `table_config.py`'ye tüm 14 tabloyu ekle | `database/table_config.py` |
| 0.2 | `gsheet_manager.py` ↔ `google_baglanti.py` köprüsü: `get_worksheet()` fonksiyonu yaz veya `gsheet_manager`'ı `veritabani_getir()` ile çalışacak şekilde düzenle | `database/gsheet_manager.py` |
| 0.3 | `sync_worker.py`'yi düzelt: SQLiteManager + RepositoryRegistry oluşturup SyncService'e ver | `database/sync_worker.py` |
| 0.4 | `main.pyw`'yi çalışır hale getir: QApplication + QMainWindow + sync entegrasyonu | `main.pyw` |
| 0.5 | `ayarlar.json`'daki sayfa isimleri ile `table_config.py` / `migrations.py` arasındaki isimlendirme farklarını eşitle | Çapraz kontrol |

---

### 📌 Faz 1 — Ana Pencere & Navigasyon Yapısı
> Tahmini Süre: 2-3 gün

| # | Görev | Açıklama |
|---|-------|----------|
| 1.1 | `ui/` klasörünü oluştur | `ui/main_window.py`, `ui/sidebar.py`, `ui/base_form.py` |
| 1.2 | Sol menü (sidebar) | `ayarlar.json` → `menu_yapilandirma`'dan dinamik menü oluştur |
| 1.3 | QMainWindow + QStackedWidget | Sayfa geçişleri için merkezi layout |
| 1.4 | Durum çubuğu (status bar) | Senkron durumu, son sync zamanı, bağlantı ikonu |
| 1.5 | Tema & stil | QSS ile kurumsal temel tema |

**Önerilen UI yapısı:**
```
ui/
├── main_window.py        # Ana pencere
├── sidebar.py            # Sol menü
├── status_bar.py         # Durum çubuğu
├── base_form.py          # Tüm formların temel sınıfı
├── components/
│   ├── data_table.py     # Ortak tablo widget'ı (QTableView)
│   ├── search_bar.py     # Arama bileşeni
│   └── sync_indicator.py # Senkron durum göstergesi
└── pages/
    ├── personel/
    ├── cihaz/
    ├── izin/
    ├── rke/
    └── dashboard/
```

---

### 📌 Faz 2 — Personel Modülü (İlk MVP)
> Tahmini Süre: 3-5 gün

| # | Görev | Açıklama |
|---|-------|----------|
| 2.1 | Personel listesi sayfası | QTableView + filtre + arama |
| 2.2 | Personel detay/düzenleme formu | QFormLayout ile tüm alanlar |
| 2.3 | Yeni personel ekleme | Validasyonlu form |
| 2.4 | Silme / pasif yapma | Soft delete (Durum = "Ayrıldı") |
| 2.5 | Repository → UI bağlantısı | Model/View pattern ile veri akışı |

---

### 📌 Faz 3 — İzin Yönetimi
> Tahmini Süre: 2-3 gün

| # | Görev |
|---|-------|
| 3.1 | İzin listesi (filtrelenebilir) |
| 3.2 | İzin ekleme formu |
| 3.3 | İzin bakiye hesaplama (Izin_Bilgi tablosu) |
| 3.4 | Takvim görünümü (opsiyonel) |

---

### 📌 Faz 4 — Cihaz Modülü
> Tahmini Süre: 3-5 gün

| # | Görev |
|---|-------|
| 4.1 | Cihaz listesi + detay sayfası |
| 4.2 | Arıza kayıt & listeleme |
| 4.3 | Arıza işlem takibi |
| 4.4 | Periyodik bakım planı |
| 4.5 | Kalibrasyon takibi |

---

### 📌 Faz 5 — RKE Modülü
> Tahmini Süre: 2-3 gün

| # | Görev |
|---|-------|
| 5.1 | RKE envanter listesi |
| 5.2 | Muayene girişi |
| 5.3 | RKE raporlama |

---

### 📌 Faz 6 — Senkronizasyon İyileştirmeleri
> Tahmini Süre: 2-3 gün

| # | Görev |
|---|-------|
| 6.1 | `updated_at` karşılaştırmalı çakışma çözümü (şu an pull'da sadece "yoksa ekle" var) |
| 6.2 | Senkron ilerleme göstergesi (progress bar) |
| 6.3 | Çakışma raporu ekranı |
| 6.4 | Manuel sync butonu |
| 6.5 | Offline mod göstergesi |

---

### 📌 Faz 7 — Dashboard & Raporlama
> Tahmini Süre: 3-4 gün

| # | Görev |
|---|-------|
| 7.1 | Ana dashboard: özet kartlar (toplam personel, aktif arızalar, yaklaşan bakımlar) |
| 7.2 | FHSZ puantaj yönetimi |
| 7.3 | Temel raporlar (PDF/Excel çıktı) |

---

### 📌 Faz 8 — Kullanıcı Yönetimi & Ayarlar
> Tahmini Süre: 2-3 gün

| # | Görev |
|---|-------|
| 8.1 | Login ekranı (`itf_user_vt` ile) |
| 8.2 | Rol bazlı erişim kontrolü |
| 8.3 | Ayarlar ekranı |
| 8.4 | Yıl sonu izin devir işlemi |

---

## 📊 Öncelik Sıralaması

```
Faz 0 ████████████ KRİTİK — Hemen yapılmalı
Faz 1 ██████████   YÜKSEK — UI olmadan devam edilemez
Faz 2 █████████    YÜKSEK — İlk çalışan modül
Faz 3 ███████      ORTA
Faz 4 ███████      ORTA
Faz 5 █████        ORTA-DÜŞÜK
Faz 6 ██████       ORTA
Faz 7 █████        DÜŞÜK
Faz 8 ████         DÜŞÜK
```

---

## 💡 Mimari Öneriler

1. **QSS Tema Dosyası**: Stil kodlarını `ui/theme.qss` dosyasında tutun, böylece tüm form ve widget'lar tutarlı görünür.

2. **Signal/Slot ile Loose Coupling**: UI ↔ Repository arasında PySide6 sinyalleri kullanarak bağımlılığı azaltın.

3. **BaseForm Sınıfı**: Tüm sayfalar için ortak davranışları (kaydet, iptal, validasyon, dirty check) tek yerde tanımlayın.

4. **DataTableWidget**: QTableView'ı sarmalayan, filtreleme/sıralama/export özellikli ortak bir bileşen yazın — her modülde tekrar kullanılır.

5. **Singleton DB Bağlantısı**: `SQLiteManager`'ı uygulama genelinde tek instance olarak yönetin (şu an her sync'de yeni instance oluşuyor).

---

## 🚀 Önerilen Başlangıç

**Hemen Faz 0 ile başlayalım.** Ben şu dosyaları düzeltebilirim:
1. `table_config.py` — tüm tabloları ekle
2. `gsheet_manager.py` — google_baglanti köprüsünü yaz
3. `sync_worker.py` — çalışır hale getir
4. `main.pyw` — QApplication + boş ana pencere

Hangisinden başlamamı istersin?

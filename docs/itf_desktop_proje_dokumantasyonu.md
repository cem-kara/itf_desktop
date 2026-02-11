# ITF Desktop Uygulaması – Proje Dokümantasyonu

Bu doküman, kod tabanının **11 Şubat 2026** tarihli mevcut durumunu yansıtır.

## 1. Genel Bakış
ITF Desktop, PySide6 tabanlı bir masaüstü uygulamasıdır.

- Yerel veri katmanı: SQLite (`data/local.db`)
- Senkron katmanı: Google Sheets
- Çalışma modeli: Offline-first, arka planda senkron

## 2. Mimari (Var Olan)

```text
UI (PySide6)
  -> RepositoryRegistry + BaseRepository
  -> SQLite (local.db)
  -> SyncWorker (QThread)
  -> SyncService
  -> GSheetManager
  -> google_baglanti (gspread + Google API)
```

## 3. Proje Yapısı (Var Olan)

```text
itf_desktop/
├── main.pyw
├── core/
│   ├── config.py
│   ├── hesaplamalar.py
│   ├── logger.py
│   └── paths.py
├── database/
│   ├── sqlite_manager.py
│   ├── migrations.py
│   ├── table_config.py
│   ├── base_repository.py
│   ├── repository_registry.py
│   ├── gsheet_manager.py
│   ├── google_baglanti.py
│   ├── sync_service.py
│   └── sync_worker.py
├── ui/
│   ├── main_window.py
│   ├── sidebar.py
│   ├── theme.qss
│   ├── components/
│   └── pages/
│       ├── placeholder.py
│       └── personel/
├── data/
│   └── local.db
├── logs/
│   └── app.log
├── ayarlar.json
└── database/ayarlar.json
```

## 4. Çekirdek Bileşenler (Var Olan)

### 4.1 `main.pyw`
- Uygulama başlangıcında DB kontrolü yapar (`ensure_database`).
- `Personel` tablosu veya kritik kolon yoksa DB’yi **reset** eder (`MigrationManager.reset_database`).
- `MainWindow` açar ve uygulamayı başlatır.

### 4.2 `core/paths.py`
- `data/` ve `logs/` klasörlerini otomatik oluşturur.
- DB yolu: `data/local.db`.

### 4.3 `core/logger.py`
- Tek log dosyası: `logs/app.log`.
- Console + file handler birlikte çalışır.

### 4.4 `core/config.py`
- `APP_NAME = "ITF Desktop App"`
- `VERSION = "1.0.1"`
- `AUTO_SYNC = True`
- `SYNC_INTERVAL_MIN = 15`

## 5. Veritabanı ve Repository (Var Olan)

### 5.1 `database/migrations.py`
- Tabloları oluşturan `create_tables` içerir.
- Strateji şu an sürüm bazlı migration değil; `reset_database` ile tabloları drop/create yapar.

### 5.2 `database/table_config.py`
- Tablo kolonları ve PK tanımları merkezî tutulur.
- Composite PK desteği vardır (ör. `FHSZ_Puantaj`).
- `Loglar` sync dışıdır (`sync: False`).

### 5.3 `database/base_repository.py`
- Generic CRUD işlemleri (`insert`, `update`, `get_by_id`, `get_all`).
- Sync yardımcıları (`get_dirty`, `mark_clean`).
- Sync tablolarda `insert` sırasında `sync_status` şu an zorunlu `dirty` atanır.

### 5.4 `database/repository_registry.py`
- `table_config` üzerinden repository üretir.
- Sync tablolara otomatik `sync_status` + `updated_at` kolonlarını ekler.

## 6. Senkronizasyon (Var Olan)

### 6.1 `database/sync_worker.py`
- Senkron işlemi `QThread` üzerinde çalışır.
- UI donmasını engeller.

### 6.2 `database/sync_service.py`
- Senkronize edilebilir tüm tabloları sırayla işler.
- Akış: `read_all` -> local dirty push -> mark clean -> remote pull.
- Remote kayıtlarda local `dirty` değilse güncelleme yapar.
- `pull_only` akışı kodda mevcut (`_pull_replace`) ama aktif konfigürasyon yok.

### 6.3 `database/gsheet_manager.py`
- Google Sheets erişiminde toplu okuma/yazma (`batch_update`, `batch_append`) uygular.
- API çağrı sayısını tablo bazında azaltmayı hedefler.

### 6.4 `database/google_baglanti.py`
- Google auth + gspread + Drive upload/download işlemleri tek dosyada tutulur.
- Worksheet eşleme köprüsü (`get_worksheet`) içerir.

## 7. UI Durumu (Var Olan / Planlanan)

### 7.1 Var Olan Sayfalar
`ui/main_window.py` içinde gerçek implementasyonu bulunanlar:
- Personel Listesi
- Personel Ekle
- İzin Takip
- FHSZ Yönetim
- Puantaj Rapor
- Personel Detay (liste içinden)
- İzin Giriş (detay/liste akışından)
- İşten Ayrılış (detay akışından)

### 7.2 Planlanan veya Placeholder Olanlar
- `ayarlar.json` menüsünde bulunan Cihaz, RKE ve Yönetici İşlemleri başlıklarının büyük kısmı henüz `PlaceholderPage` ile açılır.
- Menü konfigürasyonundaki `modul/sinif` alanları ile gerçek dinamik yükleme mekanizması birebir örtüşmez; şu an seçimler `main_window.py` içinde sabit eşleştirilir.

## 8. Teknik Notlar (Mevcut Gerçek Durum)

- Repoda eski/kopya dosyalar var: `database/base_repository1.py`, `database/sync_service1.py`.
- Dokümanda geçen `personel_repository.py` dosyası mevcut değil; personel işlemleri generic repository + UI katmanında yürütülüyor.
- DB migration yaklaşımı halen reset odaklıdır; sürüm tabanlı adım adım migration mekanizması aktif değildir.

## 9. Planlanan İşler

Aşağıdaki maddeler mevcut TODO kapsamıyla hizalıdır:

1. `sync_status` clean/dirty davranışını tam düzeltmek.
2. Reset yerine güvenli ve sürüm bazlı migration stratejisine geçmek.
3. Sync hata görünürlüğünü UI ve log seviyesinde artırmak.
4. `pull_only` tabloları (`Sabitler`, `Tatiller`) config içinde açık tanımlamak.
5. Menü config ile gerçek kod davranışını hizalamak.
6. `google_baglanti.py` dosyasını daha küçük modüllere ayırmak.
7. Eski/kopya dosyaları temizlemek veya arşivlemek.
8. Büyük UI dosyalarını daha küçük bileşenlere bölmek.
9. Sync ve hesaplama modülleri için test kapsamını artırmak.

## 10. Kısa Sonuç
Proje, çalışan bir SQLite + Google Sheets senkron altyapısına ve personel tarafında aktif UI ekranlarına sahip. Bununla birlikte migration, config-kod hizası ve bazı modüllerde ayrıştırma/refactor işleri halen planlanan geliştirme başlıklarıdır.

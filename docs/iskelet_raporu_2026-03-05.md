# İskelet Mimari Taraması ve İyileştirme Rehberi

Tarih: 2026-03-05

Bu doküman arayüz dışı iskelet yapıyı (core + database + services + sync + google entegrasyonları) ayrıntılı haritalandırır ve temiz kod / sürdürülebilir güncellemeler için pratik öneriler sunar. UI güncellemeleriyle uyumlu bir iskelet kurgusu hedeflenmiştir.

## 1. Modül Haritası (Katmanlar)

- Giriş ve yaşam döngüsü
  - main.pyw: log yönetimi, migration, auth akışı, ana pencere, temp temizliği.
- Konfigürasyon ve dosya yapısı
  - core/config.py: app modu, sync ayarları, settings ile entegrasyon.
  - core/settings.py: ayarlar.json okuma/yazma.
  - core/paths.py: BASE/DATA/LOG/TEMP ve dizinlerin oluşturulması.
- Loglama ve hata yönetimi
  - core/logger.py: çoklu handler, structured formatter, sync/ui filtreleri.
  - core/log_manager.py: log cleanup, stat ve health check.
- Auth/RBAC
  - core/auth/*: AuthService, AuthorizationService, PasswordHasher, SessionContext.
  - database/sqlite_manager.py: Users/Roles/Permissions + AuthAudit işlemleri.
- İş mantığı (service katmanı)
  - core/services/*: Cihaz, Personel, RKE, İzin, Bakım, Arıza, Doküman vb.
- Veri erişim katmanı
  - database/sqlite_manager.py: bağlantı ve temel execute/executemany.
  - database/base_repository.py: CRUD + sync_status yönetimi.
  - database/repository_registry.py: tablo → repo eşlemesi.
  - database/repositories/*: özel sorgular (Personel, Cihaz, RKE, Doküman).
  - database/table_config.py: şema kolonları, pk, sync ayarları.
- Senkronizasyon
  - database/cloud_adapter.py: online/offline adaptör.
  - database/gsheet_manager.py: batch read/write + index.
  - database/sync_service.py: push/pull akışı, pull_only modlar.
  - database/sync_worker.py: QThread tabanlı sync.
  - core/services/file_sync_service.py: offline dosyaları Drive’a yükleme.
- Google entegrasyonu
  - database/google/*: auth, drive, sheets, utils, signals.

## 2. Akış Haritası (Metin)

1. main.pyw başlar
2. initialize_log_management() → log cleanup + health check
3. ensure_database() → migration + backup
4. SQLiteManager + get_auth_services()
5. Login → (gerekirse şifre değişimi) → MainWindow
6. UI → service → repository → SQLite
7. Sync: SyncWorker → FileSyncService → SyncService → GSheetManager → CloudAdapter

## 3. Kritik Bulgular ve Riskler

1) get_by_pk arayüzü uyuşmazlığı (muhtemel runtime hata)
- Bazı servisler BaseRepository üzerinde get_by_pk çağırıyor.
- BaseRepository sadece get_by_id sağlıyor.
- Örnek: core/services/cihaz_service.py → _r.get("Cihaz_Ariza").get_by_pk(...)

2) Encoding (mojibake) problemi
- main.pyw, core/config.py, core/settings.py, core/logger.py, core/log_manager.py içinde bozuk Türkçe metinler.
- Kaynak encoding standardizasyonu eksik.

3) Import-time yan etkiler
- core/paths.py import sırasında klasör oluşturuyor.
- core/config.py import sırasında resolve_app_mode() çalıştırıyor.
- Test/CLI senaryolarında beklenmedik davranış riski.

4) Sync pull-only akışında atomiklik zayıf
- database/sync_service.py pull-only modda tabloyu DELETE ediyor, sonra insert yapıyor.
- Hata halinde tablo boş kalabilir.

5) SQLiteManager.execute her sorguda commit
- Okuma sorgularında commit gereksiz I/O üretir.

6) Exception yönetimi tutarsız
- Bazı katmanlarda genel try/except ile hata yutuluyor, kök neden kayboluyor.

## 4. Temiz Kod ve Sürdürülebilirlik Önerileri

- Repository sözleşmesini netleştir
  - BaseRepository içine get_by_pk alias ekle ya da servisleri get_by_id kullanacak şekilde standardize et.
- Encoding standardizasyonu
  - Tüm .py dosyaları UTF-8’e dönüştür, gerekirse coding header ekle.
- Side-effect importlarını azalt
  - core/paths.py dizin oluşturmayı initialize_paths() fonksiyonuna taşı.
  - AppConfig.resolve_app_mode() çağrısını main.pyw içinde explicit yap.
- SQL ve repo katmanı
  - get_all + Python filtre yerine repo seviyesinde WHERE’lı metotlar.
  - SQLiteManager’da read/write ayrımı (execute_read/execute_write).
- Hata yönetimi standardizasyonu
  - Servis katmanında domain odaklı hata tipleri ve kontrollü propagasyon.
- Tip güvenliği
  - Kritik domain verileri için dataclass kullanımını artır.

## 5. UI Güncelleme Rehberi (İskeletle Uyum)

- UI doğrudan DB’ye inmesin, core/services katmanı tek kapı olsun.
- Büyük listelerde pagination kullanımı (cihaz_repository.py’de örnek var).
- Tarih formatları için core/date_utils.py ile tek kaynaktan formatla.
- Validasyon için core/validators.py kullanımını standardize et.
- UI hata mesajlarını get_user_friendly_error ile üret.

## 6. Hızlı Düzeltme Listesi (Önceliklendirilmiş)

1. get_by_pk uyumsuzluklarını gider.
2. UTF-8 encoding standardizasyonu yap.
3. Sync pull-only işlemlerini transaction’la güvenceye al.
4. SQLiteManager commit davranışını read/write ayrımıyla düzenle.
5. Import-time side effects’i azalt.

## 7. Dosya Referansları

- Giriş: main.pyw
- Konfig: core/config.py, core/settings.py, core/paths.py
- Log: core/logger.py, core/log_manager.py
- Auth: core/auth/auth_service.py, database/sqlite_manager.py
- Repo: database/base_repository.py, database/repository_registry.py
- Sync: database/sync_service.py, database/gsheet_manager.py, database/sync_worker.py
- Dosya sync: core/services/file_sync_service.py
- Şema: database/table_config.py

---

İstersen bu raporu değişiklik planına dönüştürüp dosya bazında uygulanabilir adım listesi çıkarabilirim.

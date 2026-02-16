# ITF Desktop Proje Dokumantasyonu

Bu dokuman, projenin temel yapisini ve operasyonel kullanim basliklarini tek noktada toplar.

## Durum Ayrimi

### Mevcut Durum

- Masaustu uygulama katmanlari aktif: `ui/`, `database/`, `core/`, `scripts/`, `tests/`
- Migration ve tablo sozlesmeleri aktif olarak `database/migrations.py` ve `database/table_config.py` ile yonetiliyor
- Senkronizasyon akisi `database/sync_service.py` + `database/sync_worker.py` uzerinden calisiyor
- Sozlesme guvencesi icin merkezi smoke test mevcut: `tests/test_contract_smoke.py`
- `Personel_Saglik_Takip` tablo contract testi mevcut: `tests/test_personel_saglik_takip_contract.py`

### Planlanan Durum

- Dokumantasyon ve operasyon notlarinin tek aktif dosyada birlestirilmesi
- Ek entegrasyon/smoke testleriyle kritik akislarda daha erken regress yakalama
- Sync ve operasyonel hata gorunurlugu icin log/panel tarafinda daha tutarli event izleme

## 1) Proje Ozeti

ITF Desktop; personel, cihaz, izin, puantaj, RKE ve saglik takip sureclerini masaustu uygulama uzerinden yoneten bir sistemdir.

## 2) Ana Moduller

- `ui/`: Ekranlar, formlar, tablo ve sayfa bilesenleri
- `database/`: SQLite tablo olusumu, migration, repository, sync servisleri
- `core/`: Ortak uygulama servisleri ve yardimci katmanlar
- `scripts/`: Bakim, veri duzeltme ve rapor uretim araclari
- `tests/`: Birim ve davranis testleri
- Modul detaylari bu dosyanin alt bolumlerinde birlestirilmis halde tutulur.

## 3) Veri ve Senkronizasyon

- Tablo tanimlari: `database/table_config.py`
- Migration yonetimi: `database/migrations.py`
- Google Sheets senkronizasyonu: `database/sync_service.py`
- Senkronizasyon tablo eslesmeleri: `database/google/utils.py`

Not: `sync_status` ve `updated_at` gibi teknik kolonlar lokal takip icin kullanilabilir.

## 4) Tema ve Arayuz

- Tema yonetimi: `ui/theme_manager.py`
- Takvim popup stili merkezi olarak tema yoneticisi uzerinden uygulanir.

## 5) Raporlama ve Dokumanlar

- Aktif operasyon/raporlama kaynagi: `docs/OPERASYON_VE_RAPORLAMA_MERKEZI.md`
- Modul dokumantasyonlari: bu dosyanin "Birlestirilmis Modul Dokumani" bolumunde
- Proje inceleme raporu (referans): `docs/PROJE_TAM_INCELEME_VE_YAPILACAKLAR_RAPORU_2026-02-15.md`
- Guncel TODO raporu (referans): `docs/TODO_Guncel_Inceleme_Raporu.md`
- Genel TODO: `TODO.md`

## 6) Gelistirme Notlari

- Testleri calistirma: `pytest -q`
- Migration sozlesmesi degisikliklerinde test beklentileri birlikte guncellenmelidir.
- Tablo PK/sync kararlarinda `table_config` ve testler birlikte hizalanmalidir.

## 7) 2026-02-16 Guncelleme Eki

Bu bolum, son eklenen raporlama, bildirim, yedekleme ve dashboard guncellemelerini ozetler.

### Yeni Servis ve Bilesenler

- Merkezi rapor servisi eklendi: `core/rapor_servisi.py`
  - Excel: `{{alan}}` ve `{{ROW}}` satir genisletme kurali ile `.xlsx` uretimi
  - PDF: Jinja2 HTML render + Qt `QPdfWriter` ile `.pdf` uretimi
  - Public API: `excel`, `pdf`, `ac`, `kaydet_diyalogu`, `sablon_listesi`, `sablon_yolu`
- Sayfalara hizli disa aktarma bileseni eklendi: `ui/components/rapor_buton.py`
  - Tek widget ile Excel/PDF veya sadece tek tur cikti
  - `context_fn` ve `tablo_fn` callback modeli ile sayfadan bagimsiz kullanim
- Referans sablon uretici script eklendi: `scripts/demo_sablonlar_olustur.py`
  - Ornek excel/pdf sablonlarini olusturur
  - Kendi sablonunu tasarlamak icin referans gorevi gorur

### Bildirim ve Dashboard Akisi

- Bildirim servis katmani eklendi: `core/bildirim_servisi.py`
  - Kalibrasyon, Periyodik Bakim, NDK, RKE ve Saglik Takip icin kritik/uyari hesaplar
- Bildirim paneli eklendi: `ui/components/bildirim_paneli.py`
  - Main UI'da `page_title` ile stack arasinda konumlanir
  - Kapatilabilir (oturumluk dismiss), sync sonrasinda tekrar guncellenir
- Dashboard sorgu kapsami genisletildi: `ui/pages/dashboard.py`
  - Cihaz, personel, RKE, saglik ve aylik izinli personel metrikleri
  - Dashboard kartlari filtreli sayfa acilisina yonlendirir

### Yedekleme Yonetimi

- Admin sayfasi eklendi: `ui/pages/admin/yedek_yonetimi.py`
  - Manuel yedek alma
  - Yedek listeleme, silme, geri yukleme
  - Geri yukleme oncesi otomatik emniyet yedegi
- Migration tarafi ile uyumlu yedek naming ve cleanup kullanilir:
  - `database/migrations.py` (`db_backup_YYYYMMDD_HHMMSS.db`, keep_count varsayilan 10)

### Test Kapsami (Yeni)

- `tests/test_rapor_servisi.py` (25 test)
- `tests/test_bildirim_servisi.py`
- `tests/test_yedek_yonetimi.py`
- `tests/test_dashboard_worker.py`

### Sablon Dosyalari Notu

- Rapor servisi varsayilan olarak `data/templates/` dizinini kullanir.
- Depoda referans sablonlar su anda `data/template/` altinda gorunmektedir.
- Uretim kullaniminda tek dizin standardi korunmalidir (`templates`).

## 8) Birlestirilmis Modul Dokumani

Bu bolum, ayri modul dosyalarinin birlestirilmis surumudur.

### 8.1 Personel Modulu

Kapsam:
- Personel kayit/guncelleme/detay/ayrilis
- Izin giris ve takip
- FHSZ puantaj
- Saglik takip

UI sayfalari:
- `ui/pages/personel/personel_listesi.py`
- `ui/pages/personel/personel_ekle.py`
- `ui/pages/personel/izin_giris.py`
- `ui/pages/personel/izin_takip.py`
- `ui/pages/personel/fhsz_yonetim.py`
- `ui/pages/personel/puantaj_rapor.py`
- `ui/pages/personel/saglik_takip.py`
- `ui/pages/personel/isten_ayrilik.py`

Veri varliklari:
- `Personel`, `Izin_Giris`, `Izin_Bilgi`, `FHSZ_Puantaj`, `Personel_Saglik_Takip`

Test guvencesi:
- `tests/test_izin_logic.py`
- `tests/test_fhsz_logic.py`
- `tests/test_personel_saglik_takip_contract.py`
- `tests/test_dashboard_worker.py`

### 8.2 Cihaz Modulu

Kapsam:
- Cihaz envanteri
- Ariza kayit ve islem surecleri
- Periyodik bakim
- Kalibrasyon takip

UI sayfalari:
- `ui/pages/cihaz/cihaz_listesi.py`
- `ui/pages/cihaz/cihaz_ekle.py`
- `ui/pages/cihaz/cihaz_detay.py`
- `ui/pages/cihaz/ariza_kayit.py`
- `ui/pages/cihaz/ariza_ekle.py`
- `ui/pages/cihaz/ariza_islem.py`
- `ui/pages/cihaz/ariza_listesi.py`
- `ui/pages/cihaz/periyodik_bakim.py`
- `ui/pages/cihaz/kalibrasyon_takip.py`

Veri varliklari:
- `Cihazlar`, `Cihaz_Ariza`, `Ariza_Islem`, `Periyodik_Bakim`, `Kalibrasyon`

Test guvencesi:
- `tests/test_cihaz_listesi_logic.py`
- `tests/test_kalibrasyon_logic.py`
- `tests/test_periyodik_bakim_logic.py`
- `tests/test_dashboard_worker.py`

### 8.3 RKE Modulu

Kapsam:
- RKE envanter kayit ve takip
- Muayene/periyodik kontrol
- Raporlama ciktilari

UI sayfalari:
- `ui/pages/rke/rke_yonetim.py`
- `ui/pages/rke/rke_muayene.py`
- `ui/pages/rke/rke_rapor.py`

Veri varliklari:
- `RKE_List` (PK: `EkipmanNo`)
- `RKE_Muayene` (PK: `KayitNo`)

Test guvencesi:
- `tests/test_rke_yonetim_logic.py`
- `tests/test_rke_muayene_logic.py`
- `tests/test_rke_rapor_logic.py`
- `tests/test_dashboard_worker.py`

### 8.4 Yonetici (Admin) Modulu

Kapsam:
- Ayarlar (Sabitler/Tatiller)
- Yil sonu islemleri
- Log goruntuleme
- Yedek yonetimi

UI sayfalari:
- `ui/pages/admin/yonetim_ayarlar.py`
- `ui/pages/admin/yil_sonu_islemleri.py`
- `ui/pages/admin/log_goruntuleme.py`
- `ui/pages/admin/yedek_yonetimi.py`

Test guvencesi:
- `tests/test_yedek_yonetimi.py`
- `tests/test_log_goruntuleme.py`
- `tests/test_yil_sonu_logic.py`

### 8.5 Veri ve Sync Modulu

Kapsam:
- SQLite, repository, registry
- Migration ve yedekleme
- Google Sheets sync

Ana bilesenler:
- `database/sqlite_manager.py`
- `database/base_repository.py`
- `database/repository_registry.py`
- `database/table_config.py`
- `database/migrations.py`
- `database/sync_service.py`
- `database/sync_worker.py`
- `database/google/*`

Test guvencesi:
- `tests/test_sync_service.py`
- `tests/test_database.py`
- `tests/test_repository_registry.py`
- `tests/test_contract_smoke.py`

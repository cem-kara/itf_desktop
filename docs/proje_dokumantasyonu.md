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
- `RKE` (bagimsiz modul): `docs/RKE_MODUL_DOKUMANTASYONU.md`

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
- RKE modul dokumani (bagimsiz): `docs/RKE_MODUL_DOKUMANTASYONU.md`
- Proje inceleme raporu (referans): `docs/PROJE_TAM_INCELEME_VE_YAPILACAKLAR_RAPORU_2026-02-15.md`
- Guncel TODO raporu (referans): `docs/TODO_Guncel_Inceleme_Raporu.md`
- Genel TODO: `TODO.md`

## 6) Gelistirme Notlari

- Testleri calistirma: `pytest -q`
- Migration sozlesmesi degisikliklerinde test beklentileri birlikte guncellenmelidir.
- Tablo PK/sync kararlarinda `table_config` ve testler birlikte hizalanmalidir.

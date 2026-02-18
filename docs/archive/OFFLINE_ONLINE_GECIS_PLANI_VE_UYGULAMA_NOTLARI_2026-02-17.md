# Offline/Online Gecis Plani ve Uygulama Notlari (2026-02-17)

Bu dokuman, offline/online mode gecisi icin yapilan analizleri, plani ve bugune kadar tamamlanan uygulama adimlarini tek yerde toplar.

## 1) Inceleme Sonucu

Offline/online mod gecisi icin kod tabaninda iki ana bagimlilik vardir:

1. Senkronizasyon katmani (`sync_service` + `gsheet_manager`)
2. UI icinden dogrudan `GoogleDriveService` cagirilari (dosya yukleme)

Sonuc:
- Sadece ayar eklemek yeterli degil.
- Servis yonlendirme (adapter/factory) katmani zorunlu.

## 2) Degismesi Gereken Dosyalar (Oncelikli)

1. `core/config.py`
2. `core/di.py`
3. `database/sync_service.py`
4. `database/sync_worker.py`
5. `database/gsheet_manager.py`
6. `database/google/__init__.py`
7. `ui/main_window.py`
8. `ui/sidebar.py`

## 3) Dogrudan GoogleDriveService Kullanan UI Dosyalari

1. `ui/pages/personel/personel_ekle.py`
2. `ui/pages/personel/saglik_takip.py`
3. `ui/pages/personel/isten_ayrilik.py`
4. `ui/components/personel_overview_panel.py`
5. `ui/pages/cihaz/cihaz_ekle.py`
6. `ui/pages/cihaz/ariza_ekle.py`
7. `ui/pages/cihaz/ariza_islem.py`
8. `ui/pages/cihaz/kalibrasyon_takip.py`
9. `ui/pages/cihaz/periyodik_bakim.py`
10. `ui/pages/rke/rke_muayene.py`
11. `ui/pages/rke/rke_rapor.py`

## 4) Dokumantasyon/Test Guncellemesi Gerekenler

1. `README.md`
2. `docs/proje_dokumantasyonu.md`
3. `docs/OPERASYON_VE_RAPORLAMA_MERKEZI.md`
4. `tests/test_sync_service.py`
5. `tests/test_contract_smoke.py`
6. `tests/test_theme_manager.py` (mode etkisi varsa)

## 5) Revize Asamali Plan

### Asama 1: Mode Altyapisi
- `app_mode` (`offline|online`) tanimi
- config okuma
- startup fallback kurali (credentials yoksa offline)

### Asama 2: Servis Soyutlama
- Tek arayuz (`CloudAdapter`)
- `OnlineCloudAdapter` ve `OfflineCloudAdapter`
- DI ile secim

### Asama 3: Sync Katmani Adaptasyonu
- `sync_worker` / `sync_service` / `gsheet_manager` adapter uzerinden calissin
- offline modda sync no-op veya disabled state

### Asama 4: UI Entegrasyonu
- 11 UI dosyasindaki dogrudan `GoogleDriveService()` cagirilari adapter'a tasinsin
- offline davranisi kullanici dostu mesajla yonetilsin

### Asama 5: UX ve Log
- `ui_log.log` icine mode bilgisi eklensin
- `sidebar` / `main_window` uzerinde "Offline Mod" durum etiketi gosterilsin

### Asama 6: Test + Dokumantasyon
- offline acilis, menu gezinme, form kayit akis testleri
- online sync regresyon testleri
- README ve operasyon dokumanlarinin guncellenmesi

## 6) Bugune Kadar Yapilanlar (Tamamlananlar)

### Tamamlandi: Asama 1

`core/config.py` icinde:
- `MODE_ONLINE`, `MODE_OFFLINE`, `DEFAULT_MODE`
- `APP_MODE`, `APP_MODE_SOURCE`
- `resolve_app_mode()` (oncelik: env -> ayarlar.json -> credentials fallback -> default)
- `get_app_mode()`, `is_online_mode()`, `set_app_mode(..., persist=True)`

Desteklenen kaynaklar:
- `ITF_APP_MODE` env variable
- `ayarlar.json` icindeki `app_mode`
- `database/credentials.json` yoksa otomatik offline fallback

### Tamamlandi: Asama 2

Yeni dosya:
- `database/cloud_adapter.py`

Icerik:
- `CloudAdapter` (ortak arayuz)
- `OnlineCloudAdapter` (GoogleDriveService kullanan)
- `OfflineCloudAdapter` (no-op/fallback)
- `get_cloud_adapter(mode=None)` factory + cache

DI entegrasyonu:
- `core/di.py` icine `get_cloud_adapter(mode=None)` eklendi.

### Asama 1-2 Sonrasi Ilk Uygulama Davranisi

`ui/main_window.py`:
- offline modda sync butonu devre disi
- durum etiketi "Offline mod"
- `_start_sync()` offline modda erken cikis

### Tamamlandi: Asama 3

`database/cloud_adapter.py`:
- `CloudAdapter` arayuzune `get_worksheet(table_name)` eklendi.
- `OnlineCloudAdapter` icinde worksheet erisimi adapter uzerinden acildi.
- `OfflineCloudAdapter` icinde `get_worksheet` no-op olacak sekilde eklendi.

`database/gsheet_manager.py`:
- Dogrudan `database.google.get_worksheet` bagimliligi kaldirildi.
- `core.di.get_cloud_adapter()` ile adapter tabanli erisim eklendi.
- Offline modda worksheet olmadiginda anlamli hata uretecek kontrol eklendi.

`database/sync_service.py`:
- `AppConfig.is_online_mode()` kontrolu ile offline modda `sync_all()` no-op yapildi.
- Pull-only akisinda kalan dogrudan Google worksheet cagrisi kaldirildi ve
  `self.gsheet.get_worksheet()` kullanildi.

`database/sync_worker.py`:
- Offline modda worker senkronu baslatmadan `finished` sinyali ile guvenli cikis yapar hale getirildi.

Derleme dogrulamasi:
- `python -m py_compile database/cloud_adapter.py`
- `python -m py_compile database/gsheet_manager.py`
- `python -m py_compile database/sync_service.py`
- `python -m py_compile database/sync_worker.py`

### Baslandi: Asama 4 (RKE ile)

RKE klasorunde adapter gecisi uygulandi:

`ui/pages/rke/rke_muayene.py`:
- `GoogleDriveService` bagimliligi kaldirildi.
- Dosya yukleme akisi `get_cloud_adapter()` uzerinden `cloud.upload_file(...)` olacak sekilde guncellendi.
- Upload basarisiz/offline durumda kayit akisinin devam etmesi korundu ve bilgilendirici log eklendi.

`ui/pages/rke/rke_rapor.py`:
- `_yukle_drive()` icindeki dogrudan `GoogleDriveService` kullanimi kaldirildi.
- Yukleme `get_cloud_adapter()` uzerinden yapilacak sekilde guncellendi.
- Upload sonucu mesajlari offline olasiligini belirtecek sekilde netlestirildi.
- `SQLiteManager` kapatma akisi `finally` bloguna alinarak guvenli hale getirildi.

RKE derleme dogrulamasi:
- `python -m py_compile ui/pages/rke/rke_muayene.py`
- `python -m py_compile ui/pages/rke/rke_rapor.py`


## 7) Sonraki Adimlar (Aksiyon)

1. Asama 4 devam: Personel + Cihaz tarafindaki kalan dogrudan `GoogleDriveService` kullanimlarini adapter'a tasima
2. Asama 5: `ui_log.log` kayitlarina mode context ekleme
3. Asama 6: test ve dokuman tamamlayici guncellemeleri

## 8) Not

Bu dokuman tarihli gecis kaydidir. Guncel operasyon durumu icin:
- `docs/OPERASYON_VE_RAPORLAMA_MERKEZI.md`

## 9) 2026-02-18 Guncelleme (Net Durum Ozeti)

### A) Asama 1-3 Duzeltmeleri (Derleme/Calisma Hatasi Giderildi)
- `core/config.py`: cift `import json` temizlendi; `APP_MODE = DEFAULT_MODE`, `APP_MODE_SOURCE = "default"` seklinde duzeltildi.
- `core/di.py`: `RepositoryRegistry` importu eklendi.
- `database/gsheet_manager.py`: `import time` eklendi.
- `database/sync_worker.py`: `QThread`, `Signal` importlari eklendi.
- Not: Ortamda `python/py` komutu olmadigi icin `py_compile` dogrulamasi calistirilamadi.

### B) Offline Local Upload Altyapisi (Asama 2-4 Arasi)
- `database/cloud_adapter.py`: `upload_file(..., offline_folder_name=None)` imzasina gecildi.
  - Offline modda dosya `data/offline_uploads/<klasor>` altina kopyalaniyor.
  - Cakisma durumunda `_1`, `_2` ekleniyor.
- `database/google/utils.py`: `resolve_storage_target(all_sabit, folder_name)` eklendi.
  - Online: `Sistem_DriveID` -> `Aciklama` (Drive ID)
  - Offline: `Sistem_DriveID` -> `MenuEleman` (klasor adi)

### C) RKE Modulu (Test icin stabil hale getirildi)
- `ui/pages/rke/rke_muayene.py`: upload akisi `resolve_storage_target` + `offline_folder_name` kullanacak sekilde guncellendi.
- `ui/pages/rke/rke_rapor.py`: offline durumda "Yerel klasore kaydedildi" mesaji eklendi, final bilgi metni guncellendi.
- `ui/pages/rke/rke_yonetim.py`: Drive/upload kullanimi yok, degisiklik gerekmedi.

### D) Devam Eden Isler
- Personel ve Cihaz tarafindaki upload noktalarinin `resolve_storage_target` + `offline_folder_name` ile standardize edilmesi.
- Offline/online davranislarinin UI mesajlarinda netlestirilmesi.

# Durum ve Yol Haritasi

Bu dosya "yarin nerede kaldik" sorusuna net cevap vermek icin tek kaynaktir.

## Son Durum (2026-02-18)

### Yapilanlar (Net ve Kesin)
- Asama 1-3 kapsaminda eksik importlar ve `APP_MODE` varsayilani duzeltildi:
  - `core/config.py`: `APP_MODE = DEFAULT_MODE`, cift `import json` temizlendi.
  - `core/di.py`: `RepositoryRegistry` importu eklendi.
  - `database/gsheet_manager.py`: `import time` eklendi.
  - `database/sync_worker.py`: `QThread`, `Signal` importlari eklendi.
- Offline local upload altyapisi eklendi:
  - `database/cloud_adapter.py`: offline modda `data/offline_uploads/<klasor>` altina kopyalama.
  - `database/google/utils.py`: `resolve_storage_target(all_sabit, folder_name)` eklendi.
- RKE modulu test icin stabilize edildi:
  - `ui/pages/rke/rke_muayene.py`: `resolve_storage_target` + `offline_folder_name` ile upload.
  - `ui/pages/rke/rke_rapor.py`: offline mesajlari "Yerel klasore kaydedildi" olarak guncellendi.
  - `ui/pages/rke/rke_yonetim.py`: Drive/upload yok, degisiklik gerekmedi.
- Cihaz modulu upload standardizasyonu baslatildi:
  - [x] `ui/pages/cihaz/ariza_islem.py`: `CloudAdapter` entegrasyonu yapildi.
  - [x] `ui/pages/cihaz/cihaz_ekle.py`: Cihaz resmi yukleme (CloudAdapter entegrasyonu yapildi)
  - [x] `ui/pages/cihaz/kalibrasyon_takip.py`: Sertifika yukleme (CloudAdapter entegrasyonu yapildi)
  - [x] `ui/pages/cihaz/periyodik_bakim.py`: Bakim raporu yukleme (CloudAdapter entegrasyonu yapildi)
  - [x] `ui/pages/cihaz/ariza_ekle.py`: Ariza gorseli yukleme (CloudAdapter entegrasyonu yapildi)
- Personel modulu upload standardizasyonu tamamlandi:
  - [x] `ui/pages/personel/personel_ekle.py`: Resim/Diploma yukleme (CloudAdapter entegrasyonu yapildi)

### Bilinen Notlar
- Bu ortamda `python/py` komutu yok, `py_compile` dogrulamalari calistirilamadi.

## Hemen Devam Edilecek Is (Yarin Baslangic Noktasi)

1. Offline/online mesajlarini tum upload noktalarinda tutarli hale getirmek.

## Asama Durumu

- Asama 1: Tamamlandi
- Asama 2: Tamamlandi (offline local upload destegi eklendi)
- Asama 3: Tamamlandi
- Asama 4: RKE tam, Cihaz tam, Personel tam
- Asama 5: Bekliyor
- Asama 6: Bekliyor

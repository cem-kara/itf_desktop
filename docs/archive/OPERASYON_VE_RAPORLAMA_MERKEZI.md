# ITF Desktop - Operasyon ve Raporlama Merkezi

Bu dosya proje icin tek aktif operasyon/raporlama kaynagidir.
Tum guncel durum, acik maddeler ve operasyon notlari burada tutulur.

## 1) Mevcut Durum (Aktif)

- Test durumu: `PASSED` (son bilinen sonuc: `pytest -v` ile tum testler gecti).
- Kritik sozlesme maddeleri kapandi:
  - `CURRENT_VERSION` hizasi
  - `sync_mode` karari (Sabitler/Tatiller iki yonlu)
  - `RKE_List` PK karari (`EkipmanNo`)
  - `Personel_Saglik_Takip` tablo contract testi
- Merkezi contract smoke testi aktif: `tests/test_contract_smoke.py`
- Sync hata standardizasyonu aktif: `database/sync_service.py` icindeki `SyncBatchError`
- Offline/Online mod gecisi baslatildi:
  - `core/config.py` ile `app_mode` cozumleme (env + ayar + fallback)
  - `database/cloud_adapter.py` eklendi (online/offline adapter)
  - `core/di.py` uzerinden `get_cloud_adapter()` aktif
  - `ui/main_window.py` offline modda sync baslatmiyor

## 2) Planlanan Durum (Acik Isler)

### P3

1. Ek entegrasyon/smoke testleri genisletilecek.
2. Operasyonel gorunurluk (sync event izleme) daha merkezi hale getirilecek.
3. Offline/Online geciste kalan fazlar tamamlanacak:
   - sync servislerinin adapter-aware refactor'u
   - UI'deki dogrudan Google cagri noktalarinin adapter'a alinmasi
   - ayarlar ekranindan mode yonetimi

## 3) Test ve Kalite Ozet

- Hedef komut: `pytest -v`
- Hizli dogrulama komutlari:
  - `pytest tests/test_contract_smoke.py -q`
  - `pytest tests/test_personel_saglik_takip_contract.py -q`
  - `pytest tests/test_sync_service.py -q`

## 4) Operasyon Notlari (Runbook)

1. Senkronizasyon
- Akis: `ui/main_window.py` -> `database/sync_worker.py` -> `database/sync_service.py`
- Toplu hata modeli: `SyncBatchError`
- Kullaniciya hata yansitma: `MainWindow._on_sync_error`

2. Log dosyalari
- `logs/app.log`
- `logs/sync.log`
- `logs/errors.log`

3. Migration ve sozlesme
- Migration: `database/migrations.py`
- Tablo sozlesmeleri: `database/table_config.py`
- Merkezi contract testi: `tests/test_contract_smoke.py`

## 5) Dokuman Haritasi

### Aktif (kanonik)

- `docs/OPERASYON_VE_RAPORLAMA_MERKEZI.md` (bu dosya)
- `docs/proje_dokumantasyonu.md` (mimari ve genel teknik dokuman)
- Modul detaylari `docs/proje_dokumantasyonu.md` icinde birlestirilmis halde bulunur.

### Referans/Arsiv

- `docs/PROJE_TAM_INCELEME_VE_YAPILACAKLAR_RAPORU_2026-02-15.md`
- `docs/TODO_Guncel_Inceleme_Raporu.md`
- `docs/TODO.md`

## 6) Degisiklik Gunlugu

- 2026-02-16: Operasyon ve raporlama notlari tek dosyada birlestirildi.
- 2026-02-16: Rapor servisi, bildirim paneli, yedek yonetimi ve dashboard metrik guncellemeleri eklendi.
- 2026-02-17: Offline/Online mod gecisinin Asama 1-2 altyapisi eklendi (`AppConfig app_mode`, `CloudAdapter`, DI baglantisi).

## 7) 2026-02-16 Operasyon Ekleri

### Raporlama Runbook

1. Merkezi servis: `core/rapor_servisi.py`
2. UI bileseni: `ui/components/rapor_buton.py`
3. Sablonlar:
- Excel: `data/templates/excel/*.xlsx`
- PDF: `data/templates/pdf/*.html`
4. Referans sablon uretimi:
- `scripts/demo_sablonlar_olustur.py`
5. Hata durumlari:
- Sablon yoksa servis `None` doner ve log basar
- PDF ortaminda Qt yoksa `_preview.html` fallback olusur

### Bildirim Runbook

1. Worker: `core/bildirim_servisi.py::BildirimWorker`
2. UI panel: `ui/components/bildirim_paneli.py`
3. Main akisi:
- `ui/main_window.py` acilista `_setup_bildirim()`
- Sync sonrasi yeniden bildirim kontrolu
4. Kategoriler:
- Kritik/Uyari + grup/sayfa bilgisi ile tiklanabilir yonlendirme

### Yedekleme Runbook

1. Admin ekrani: `ui/pages/admin/yedek_yonetimi.py`
2. Altyapi: `database/migrations.py::backup_database()`
3. Dosya formati:
- `data/backups/db_backup_YYYYMMDD_HHMMSS.db`
4. Politika:
- Eski yedek temizligi varsayilan `keep_count=10`
- Geri yuklemede once emniyet yedegi alinmasi

### Yeni Test Paketleri

- `tests/test_rapor_servisi.py`
- `tests/test_bildirim_servisi.py`
- `tests/test_yedek_yonetimi.py`
- `tests/test_dashboard_worker.py`

## 8) Release Ready Notu

Durum: `Release-Ready`

Kapanis Ozeti:
- Kritik ve yuksek oncelikli maddeler tamamlandi.
- Migration/config/sync sozlesmeleri testlerle guvence altina alindi.
- `Personel_Saglik_Takip` icin tablo contract testi eklendi.
- Operasyon ve raporlama tek aktif dosyada toplandi.

Onay Kriterleri:
- Test suiti yesil (`pytest -v`).
- Merkezi sozlesme testleri yesil (`test_contract_smoke`, `test_personel_saglik_takip_contract`).
- Dokuman yonlendirmeleri merkezi kaynaga bagli.

## 9) 2026-02-18 Guncelleme (Offline/Online Gecisi)

Yapilanlar (net):
- Asama 1-3 kapsaminda eksik importlar ve `APP_MODE` varsayilani duzeltildi.
- Offline local upload altyapisi eklendi:
  - `database/cloud_adapter.py`: offline modda `data/offline_uploads/<klasor>` altina kopyalama.
  - `database/google/utils.py`: `resolve_storage_target` eklendi.
- RKE modulu test icin stabilize edildi:
  - `rke_muayene` ve `rke_rapor` upload akislarinda `offline_folder_name` kullaniliyor.
  - `rke_rapor` mesajlari offline icin “Yerel klasore kaydedildi” seklinde guncellendi.

Not:
- Bu ortamda `python/py` komutu bulunmadigi icin `py_compile` dogrulamalari calistirilamadi.

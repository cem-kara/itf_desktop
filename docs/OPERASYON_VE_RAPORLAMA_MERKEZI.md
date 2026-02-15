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

## 2) Planlanan Durum (Acik Isler)

### P3

1. Ek entegrasyon/smoke testleri genisletilecek.
2. Operasyonel gorunurluk (sync event izleme) daha merkezi hale getirilecek.

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
- `docs/RKE_MODUL_DOKUMANTASYONU.md` (RKE bagimsiz modul dokumani)

### Referans/Arsiv

- `docs/PROJE_TAM_INCELEME_VE_YAPILACAKLAR_RAPORU_2026-02-15.md`
- `docs/TODO_Guncel_Inceleme_Raporu.md`
- `docs/TODO.md`

## 6) Degisiklik Gunlugu

- 2026-02-16: Operasyon ve raporlama notlari tek dosyada birlestirildi.

## 7) Release Ready Notu

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

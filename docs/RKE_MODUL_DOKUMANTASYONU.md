# RKE Modulu Dokumantasyonu

RKE (Radyasyon Koruyucu Ekipman) bu proje icinde bagimsiz bir is modulu olarak ele alinir.

## 1) Modul Kapsami

- Koruyucu ekipman kayit ve takip islemleri
- Muayene/periyodik kontrol kayitlari
- Raporlama ve cikti surecleri

## 2) Temel Veri Varliklari

- `RKE_List`
  - Primer anahtar: `EkipmanNo`
  - Modulun ana envanter tablosu
- `RKE_Muayene`
  - Primer anahtar: `KayitNo`
  - Ekipman bazli muayene ve sonuc kayitlari

## 3) Kod Yerlesimi

- Sayfalar:
  - `ui/pages/rke/rke_yonetim.py`
  - `ui/pages/rke/rke_muayene.py`
  - `ui/pages/rke/rke_rapor.py`
- Tablo sozlesmeleri:
  - `database/table_config.py`
- Migration semasi:
  - `database/migrations.py`

## 4) Sozlesme ve Test Guvencesi

- Merkezi contract smoke: `tests/test_contract_smoke.py`
- RKE is kurali testleri:
  - `tests/test_rke_yonetim_logic.py`
  - `tests/test_rke_muayene_logic.py`
  - `tests/test_rke_rapor_logic.py`
- Tablo config testleri:
  - `tests/test_table_config.py`

## 5) Operasyon Notu

- RKE ile ilgili operasyonel guncel durumlar icin:
  - `docs/OPERASYON_VE_RAPORLAMA_MERKEZI.md`

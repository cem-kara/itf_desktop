# CHANGELOG

Tüm dikkate değer değişiklikler bu dosyada belgelenmiştir.

Format şu kurallara uyar: [Keep a Changelog](https://keepachangelog.com/tr/1.0.0/)

---

## [v0.3.0 - UI Stabilization] - 2026-03-06 (WIP)

### 2026-03-12 Güncellemesi

#### ✨ Fixed
- `ui/pages/personel/personel_ekle.py`: kayıt sonrası "Evet" dalında `btn_kaydet.setEnabled(True)` çağrısı eksikti — düzeltildi
- `ui/pages/personel/personel_ekle.py`: `QTabWidget` import satırına eklenmemişti — düzeltildi

#### ✨ Added
- `ui/pages/personel/personel_ekle.py`: Belge paneli sekmeli yapıya (QTabWidget) taşındı
  - Tab 1 — "👤 Kişisel Bilgiler": mevcut form (scroll içinde)
  - Tab 2 — "📎 Belgeler": kayıt öncesi kilitli (`setTabEnabled(1, False)`), kayıt sonrası otomatik açılır ve bu sekmeye geçer
  - Edit modunda açılışta Belgeler sekmesi zaten aktif
  - "Yeni Personel" reset akışında sekme tekrar kilitlenir

---

### 2026-03-07 Güncellemesi

#### ✨ Fixed
- `ui/pages/personel/personel_ekle.py`: kayıt sonrası kapanış + belge yükleme akışı düzeltildi
- `ui/components/base_dokuman_panel.py`: `set_entity_id()` sonrası form kontrollerinin enable/disable senkronu düzeltildi
- `ui/pages/personel/components/hizli_izin_giris.py`: `float(None)` kaynaklı hızlı izin kaydetme hatası giderildi
- `ui/pages/personel/izin_takip.py`: ilk açılışta kayıtların görünmesi için ay/yıl filtre varsayılanı `Tümü` yapıldı

#### ✨ Added
- `core/services/izin_service.py`:
  - yıllık hakediş hesaplama (`hesapla_yillik_hak`)
  - personel eklemede `Izin_Bilgi` bootstrap (`create_or_update_izin_bilgi`)
  - merkezi izin limit hesaplama/doğrulama (`get_izin_max_gun`, `validate_izin_sure_limit`)
  - merkezi çakışma kontrolü (`has_izin_cakisma`)
  - `Izin_Bilgi` sayısal alanlarda `None -> 0.0` normalize
- `tests/test_izin_service.py`: limit, hakediş, normalize ve çakışma senaryoları dahil kapsam genişletildi

#### 🔧 Changed
- `ui/pages/personel/izin_takip.py` ve `ui/pages/personel/components/hizli_izin_giris.py` limit kuralını servis katmanından ortak kullanacak şekilde güncellendi
- Limit aşımında kayıt akışı "uyarı + devam" yerine kesin engelleme davranışına alındı

#### ✅ Test
- `tests/test_izin_service.py`: `59 passed`

### 2026-03-06 Önceki WIP Değişiklikleri

### ✨ Fixed
- **Pylance 184+ type-checker uyarısı temizlendi**
  - `ui/styles/colors.py`: Theme değerleri güvenli şekilde daraltıldı (Any cast)
  - `ui/styles/components.py`: Dinamik C nesnesi Any tipine çevrildi
  - `ui/theme_manager.py`: Tema adı normalize edildi, QPalette enums güncellendi
  - `ui/pages/rke/rke_yonetim.py`: inputs Dict[str, Any], EditTrigger enums

- **UI Sayfaları Pylance Uyarıları**
  - `ui/pages/cihaz/ariza_islem.py`: reportOperatorIssue (in S) → S.get() güvenli erişim
  - `ui/pages/personel/fhsz_yonetim.py`: Table item None guards, _item_text helper
  - `ui/pages/personel/saglik_takip.py`: lineEdit() None guard, parse_date daraltma
  - `ui/pages/personel/components/hizli_saglik_giris.py`: Optional date karşılaştırma

- **Tatil Yönetimi**
  - `core/services/settings_service.py` - `add_tatil()`: UNIQUE constraint hatası için duplicate tarih kontrolü eklendi
  - Aynı tarihte iki tatil eklemeyi önlemek için ON INSERT kontrol (fetchone pattern)

- **Personel Ekle / Belge Paneli akışı düzeltildi**
  - `ui/pages/personel/personel_ekle.py`: kayıt sonrası form kapanma akışı yeniden düzenlendi
  - Belge paneli için hatalı `set_personel()` çağrıları kaldırıldı, `set_entity_id()` kullanıldı
  - "YENİ PERSONEL" butonu eklendi; form reset + yeni kayıt akışı stabilize edildi
  - `ui/components/base_dokuman_panel.py`: entity ID güncellemesinde form kontrolleri enable/disable senkronu düzeltildi

- **Hızlı İzin / İzin Girişi runtime hataları**
  - `ui/pages/personel/components/hizli_izin_giris.py`: `float(None)` kaynaklı hata giderildi (`or 0` güvenli dönüşüm)
  - `core/services/personel_service.py`: legacy TC doğrulama kaldırıldı, merkezi resmi algoritma ile hizalandı

- **İzin Takip ilk açılış görünürlüğü**
  - `ui/pages/personel/izin_takip.py`: Ay/Yıl filtreleri varsayılanı `Tümü` yapıldı
  - İlk açılışta kayıtların boş görünmesi sorunu giderildi

### ✨ Added
- **Modern Message Dialog System**
  - `ui/dialogs/mesaj_kutusu.py`: Yeni temalı mesaj kutusu (native QMessageBox yerine)
  - QMessageBox global hook (`qmessagebox_yakala`) — tüm mevcut çağrılar otomatik temalı dialoga düşer
  - Classic modal tasarım: yarı saydam overlay + elevation/shadow + kart layout
  - Frameless + transparan arka plan ile modern yarı modal deneyimi
  - Windows sistem temasından bağımsız (dark/light uyumluluk sorunu çözüldü)

- **İzin hakediş ve limit motoru (merkezi servis kuralı)**
  - `core/services/izin_service.py`:
    - `hesapla_yillik_hak()` eklendi (1-10 yıl: 20 gün, 10+ yıl: 30 gün)
    - `create_or_update_izin_bilgi()` eklendi (yeni personelde Izin_Bilgi bootstrap)
    - `get_izin_max_gun()` eklendi (Yıllık: `min(30, YillikKalan)`, Şua: `SuaKullanilabilirHak`, diğerleri: `Sabitler.Aciklama`)
    - `validate_izin_sure_limit()` eklendi (limit aşımında kesin engelleme)
    - `has_izin_cakisma()` eklendi (iptal hariç overlap kontrolü)
    - `Izin_Bilgi` numeric alanları için payload normalize (`None -> 0.0`)

- **Test kapsamı genişletildi (izin servisleri)**
  - `tests/test_izin_service.py`:
    - Yıllık hakediş hesaplama testleri
    - Izin_Bilgi create/update + None normalize testleri
    - İzin limit doğrulama testleri
    - `insert_izin_giris` limit enforcement testleri
    - İzin çakışma testleri (sınır gün, iptal hariç, ignore_izin_id dahil)
  - Toplam izin servis testi: `59 passed`

### 🔧 Changed
- **BaseTableModel Integration**
  - `set_rows()` → `set_data()` standardizasyonu (ariza_islem, fhsz_yonetim)
  - Model eager initialization (None → guard sonrası)

- **PySide6 Enum Uyumluluğu**
  - `Qt.WA_StyledBackground` → `Qt.WidgetAttribute.WA_StyledBackground`
  - `QPalette.Window` → `QPalette.ColorRole.Window`
  - `QAbstractItemView.NoEditTriggers` → `QAbstractItemView.EditTrigger.NoEditTriggers`

- **Type Safety Improvements**
  - Optional settings → safe narrowing (theme_name, donem_aralik)
  - Cursor/last_rowid None guards (sqlite_manager, settings_service)
  - Dynamic attributes → getattr() (logger.py)

- **İzin kayıt davranışı standardize edildi**
  - `ui/pages/personel/izin_takip.py` ve `ui/pages/personel/components/hizli_izin_giris.py` limit kontrolünde aynı servis metodlarını kullanır hale getirildi
  - Bakiye yetersizliğinde "devam et" davranışı kaldırıldı; kural ihlalinde kayıt engellenir

### 📚 Documentation
- `.github/instructions/copilot-instructions.md` güncellendi (DEĞİŞİKLİK LOGU)

---

## [v0.2.0 - Service & Repository Layer] - 2026-03-05

### ✨ Fixed
- 20+ type-checker hatası sistemli düzeltme
  - `core/services/*`: Type hints, None guards
  - `database/*`: Repository API standardizasyonu
  - `core/auth/*`: Permission system type-safety

### 🎯 Added
- DI Fabrika sistemi (15 service)
- BaseRepository API (delete, get_by_pk, get_where)
- Abstract method compliance (CloudAdapter)

### 🔧 Changed
- Repository registry pattern
- Service initialization flow

---

## [v0.1.0 - Core Infrastructure] - 2026-02-XX

### 🎯 Added
- Theme system (dark/light)
- BaseTableModel foundation
- Icon system
- Sidebar menu configuration

### 🔧 Changed
- Initial project structure

---

## Format Kuralları

- **Added**: Yeni özellikler
- **Changed**: Mevcut özelliklerin değiştirilmesi  
- **Fixed**: Hata düzeltmeleri
- **Deprecated**: Yakında kaldırılacak
- **Removed**: Silinen özellikler
- **Security**: Güvenlik güncellemeleri

Her commit messajında versiyonu yaz: `[v0.3.0]` veya `[WIP]`

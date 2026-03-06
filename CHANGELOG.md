# CHANGELOG

Tüm dikkate değer değişiklikler bu dosyada belgelenmiştir.

Format şu kurallara uyar: [Keep a Changelog](https://keepachangelog.com/tr/1.0.0/)

---

## [v0.3.0 - UI Stabilization] - 2026-03-06 (WIP)

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

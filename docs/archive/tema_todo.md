# Tema Temizliği — Yapılacaklar ("tema todo")

Bu doküman `REPYS` tema temizliği için hızlı yol haritası ve önerileri içerir.

## Amaç
- Tema tanımlarını tekilleştirmek.
- QPalette, Python sabitleri (`ui/styles/colors.py` / `DarkTheme`) ve QSS arasında tutarlılık sağlamak.
- Inline QSS'i merkezi komponent stillerine taşımak.

## Özet Bulgu
- Renkler hem `theme.qss`, hem `DarkTheme`/`Colors`, hem de `ThemeManager.apply_app_theme` içinde sabit olarak tekrar ediliyor.
- `ThemeManager.setup_calendar_popup` içinde uzun inline QSS var; yeniden kullanılabilir değil.
- `ui/styles/components.py` çoğu bileşim için sabitler sağlıyor — fakat takvim stili eksik.

## Yapılacaklar
- [x] Temel inceleme: `ui/theme_manager.py`, `ui/theme.qss`, `ui/styles/colors.py`, `ui/styles/components.py`
- [x] Takvim stilini `ComponentStyles.CALENDAR` olarak taşımak
- [x] `ThemeManager.apply_app_theme` palet atamalarını `DarkTheme`/`Colors` sabitlerine bağlamak
- [x] `theme.qss` şablonlama: `ui/styles/theme_template.qss` üretmek ve `load_stylesheet()` ile dinamik doldurmak
- [x] `ThemeManager.load_stylesheet()`'i şablonu destekleyecek şekilde güncellemek
- [x] Placeholder'ları renk sabitleriyle değiştirip tek kaynaktan yönetmek
- [x] **Runtime tema değiştirme (light/dark) için API eklemek** ✓ TAMAMLANDI

## Hızlı Notlar
- Değişiklikler geri dönük uyumluluk göz önünde bulundurularak yapılmalıdır.
- `ui/styles/components.py` içindeki stil sabitleri `ThemeManager.get_component_styles()` ile uyumludur.

## Sonraki Adım (isteğe bağlı)
Bu dokümanda kalan adımları otomatik uygulamamı isterseniz onay verin; şablon oluşturma ve `load_stylesheet()` entegrasyonu için devam edeceğim.

## Runtime Tema Değiştirme Hazırlıkları (isteğe bağlı)
Aşağıdaki dosyalar oluşturuldu — **henüz entegre edilmedi** (daha sonra yapılacak):
- [x] `ui/styles/light_theme.py` — Light tema renkleri (DarkTheme yapısıyla eşleşen)
- [x] `ui/theme_light_template.qss` — Light tema QSS şablonu
- [x] `ui/styles/theme_registry.py` — Tema kayıt ve yönetim sistemi

## Tamamlanan Implementasyon Detayları

### ThemeManager güncellemeleri (`ui/theme_manager.py`)
- ✅ **Signal eklendi**: `theme_changed = Signal(str)` — Tema değiştiğinde gönderilir
- ✅ **`_get_color_map(theme_class)` güncellendi**: Dinamik tema sınıfı parametresi alıyor
- ✅ **`load_stylesheet(theme_class)` güncellemeleri**: Tema sınıfına göre stylesheet oluşturuyor
- ✅ **`set_theme(app, theme_name)` metodu eklendi**:
  - `"dark"` veya `"light"` tema adını alıyor
  - ThemeRegistry'i güncelle
  - QPalette'i tema renklerine göre yapılandırır
  - Stylesheet'i yeniler
  - Signal gönderir
  - Döngü önlemek için veritabanına kayıt yapmasa da, ayarlar kaydı yapılacak

### Settings sayfası (`ui/admin/settings_page.py`)
- ✅ **Tema TAB eklendi**:
  - Radio button ile Dark/Light seçimi
  - "Tema Değişikliğini Uygula" butonu
  - `_apply_theme()` metodu gerçek tema değişikliğini yapıyor
  
- ✅ **Online/Offline TAB eklendi**:
  - Checkbox'lar ile Online mod kontrol
  - Otomatik senkronizasyon toggle
  - `_save_system_settings()` metodu

### Test ve Demo
- ✅ **`tests/theme_change_demo.py` oluşturuldu**:
  - Dark/Light tema değişimini test etmek için demo pencere
  - İlgili docstring ile kullanım açıklaması
  - Çalıştırma: `python tests/theme_change_demo.py`

### Entegrasyon için Sonraki Adımlar (Gelecek)
- [x] `ThemeManager` güncelle (`set_theme()` metodu ekle) ✓ TAMAMLANDI
- [ ] Tema değiştirme sinyali/callback sistemi (Signal gönderiliyor, dinleyen kod yazılması bekleniyor)
- [ ] Kullanıcı ayarlarına tema seçimi kaydet (`ayarlar.json`)
- [x] UI'da tema seçim menüsü oluştur ✓ (Settings sayfası → Tema Tab)

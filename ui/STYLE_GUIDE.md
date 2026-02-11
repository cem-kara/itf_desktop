# 🎨 Merkezi UI Stil Yönetim Rehberi

## Genel Bilgi

Tüm UI stil tanımları merkezi bir kaynaktan yönetilir. Bu, uygulamada stil tutarlılığını sağlar ve gelecekte tema değiştirilmesini kolaylaştırır.

### Dosya Yapısı

```
ui/
├── styles/
│   ├── __init__.py          # Paket tanımı
│   ├── colors.py            # Renk tanımları (Colors enum, DarkTheme sınıfı)
│   └── components.py        # Bileşen stiller (ComponentStyles sınıfı)
├── theme_manager.py         # Merkezi tema yönetimi (ThemeManager singleton)
└── pages/
    └── personel/
        ├── personel_listesi.py    # ✅ Merkezi theme'i kullanan örnek
        ├── personel_detay.py      # ✅ Merkezi theme'i kullanan örnek
        ├── personel_ekle.py       # ✅ Merkezi theme'i kullanan örnek
        ├── izin_giris.py          # ✅ Merkezi theme'i kullanan örnek
        └── izin_takip.py          # ✅ Merkezi theme'i kullanan örnek
```

---

## 1. Renkler (`ui/styles/colors.py`)

### Kullanım

```python
from ui.styles.colors import Colors, DarkTheme

# Temel renkler
color = Colors.GRAY_200      # Açık gri
color = Colors.BLUE_PRIMARY  # Ana mavi
color = Colors.GREEN_SUCCESS # Başarı yeşili
color = Colors.RED_ERROR     # Hata kırmızısı

# Koyu tema (W11 cam stili)
bg = DarkTheme.BG_PRIMARY        # #16172b
text = DarkTheme.TEXT_PRIMARY    # #e0e2ea
btn_bg = DarkTheme.BTN_PRIMARY_BG   # rgba(29, 117, 254, 0.25)
border = DarkTheme.BORDER_PRIMARY   # rgba(255, 255, 255, 0.08)
```

### Durum Renkleri (RGBA Tuples)

```python
# Şeffaf arka plan renkleri (hücre vb.)
from ui.styles.components import ComponentStyles

# Aktif (yeşil)
r, g, b, a = ComponentStyles.get_status_color("Aktif")  # (34, 197, 94, 40)

# Pasif (kırmızı)
r, g, b, a = ComponentStyles.get_status_color("Pasif")  # (239, 68, 68, 40)

# İzinli (sarı)
r, g, b, a = ComponentStyles.get_status_color("İzinli") # (234, 179, 8, 40)
```

### Yeni Renk Ekleme

**Adım 1:** `ui/styles/colors.py`'de renk tanımlayın:

```python
class Colors(Enum):
    # ... (mevcut renkler)
    PURPLE_ACCENT = "#a78bfa"  # Yeni
    
class DarkTheme:
    # ... (mevcut renkler)
    PURPLE_BG = "rgba(167, 139, 250, 0.15)"  # Yeni
```

**Adım 2:** `ComponentStyles`'te kullanın (aşağı bkz.)

---

## 2. Bileşen Stiller (`ui/styles/components.py`)

### Kullanım

```python
from ui.theme_manager import ThemeManager

# Tüm stiller
STYLES = ThemeManager.get_all_component_styles()

# Belirli bir stil
widget.setStyleSheet(STYLES["button_primary"])

# ya da

button_qss = ThemeManager.get_component_styles("btn_filter")
my_button.setStyleSheet(button_qss)
```

### Tanımlanmış Bileşenler

| Ad | Açıklama |
|---|---|
| `filter_panel` | Filtre paneli (çerçeveli QFrame) |
| `btn_filter` | Filtre düğmesi (gri, toggle özellikli) |
| `btn_filter_all` | "Tümü" düğmesi (açık gri) |
| `btn_action` | İşlem düğmesi (mavi) |
| `btn_refresh` | Yenile düğmesi (minimal) |
| `input_search` | Arama kutusu (QLineEdit) |
| `input_combo` | Seçim kutusu (QComboBox) |
| `input_date` | Tarih seçimi (QDateEdit) |
| `input_spin` | Sayı seçimi (QSpinBox) |
| `table` | Veri tablosu (QTableView) |
| `label_value` | Değer etiketi (kalın metin) |
| `context_menu` | Bağlam menüsü (QMenu) |

### Yeni Bileşen Stili Ekleme

**Adım 1:** `ui/styles/components.py`'de `ComponentStyles` sınıfına ekleyin:

```python
class ComponentStyles:
    # ... (mevcut stiller)
    
    # ─── Yeni: Warn Düğmesi ───
    BTN_WARN = f"""
        QPushButton {{
            background-color: {get_color('BTN_WARN_BG')};
            color: {get_color('BTN_WARN_FG')};
            border: 1px solid {get_color('BTN_WARN_BORDER')};
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 12px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: {get_color('BTN_WARN_BG_HOVER')};
        }}
    """
```

**Adım 2:** `STYLES` dict'ine ekleyin:

```python
STYLES = {
    # ... (mevcut elemanlar)
    "btn_warn": BTN_WARN,
}
```

**Adım 3:** Sayfanızda kullanın:

```python
from ui.theme_manager import ThemeManager

STYLES = ThemeManager.get_all_component_styles()

warn_button = QPushButton("Uyarı")
warn_button.setStyleSheet(STYLES["btn_warn"])
```

---

## 3. Tema Yöneticisi (`ui/theme_manager.py`)

### Singleton Kullanımı

```python
from ui.theme_manager import ThemeManager

# ✅ Tek örnek (singleton)
tm = ThemeManager()  # ya da
tm = ThemeManager.instance()

# Stil alma
qss = tm.get_component_styles("filter_panel")

# Renk alma
color = tm.get_color("TEXT_PRIMARY")
dark_color = tm.get_dark_theme_color("BG_PRIMARY")

# Durum rengi
status_color = tm.get_status_color("Aktif")  # QColor
status_from_text = tm.get_status_text_color("Pasif")  # QColor
```

### Öğe Başına Uygulanması

```python
# ─── Main penceresi başında ───
from ui.theme_manager import ThemeManager

class ITFMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # ...
        ThemeManager.instance().apply_app_theme(QApplication.instance())
```

---

## 4. Sayfaların Migrasyonunu Tamamlama

### Eski Yapı (❌ Hatalı - İnline Stiller)

```python
S = {
    "button": """
        QPushButton { background-color: ...; }
    """,
    "label": "color: ...",
}

class MyPage(QWidget):
    def __init__(self):
        # ...
        self.button.setStyleSheet(S["button"])
```

### Yeni Yapı (✅ Doğru - Merkezi Yönetim)

```python
from ui.theme_manager import ThemeManager

# Sayfanın başında
STYLES = ThemeManager.get_all_component_styles()

class MyPage(QWidget):
    def __init__(self):
        # ...
        self.button.setStyleSheet(STYLES.get("btn_action", ""))
```

### Kontrol Listesi

- [ ] Tüm inline `S` dict'lerini sil
- [ ] `from ui.theme_manager import ThemeManager` import ekle
- [ ] `STYLES = ThemeManager.get_all_component_styles()` sayfanın başında çağır
- [ ] Tüm `S["..."]` kullanımlarını `STYLES.get("...", "")` ile değiştir
- [ ] Durum renkleri içinse `ThemeManager.get_status_color()` kullan
- [ ] Syntax kontrolü: `python -m py_compile sayfanız.py`
- [ ] UI test: Sayfanın render düzgün görüntülendiğini kontrol et

---

## 5. En İyi Uygulamalar

### ✅ Yapılması Gereken

1. **Merkezi kaynaktan al** — Hiç zaman inline QSS yazma
   ```python
   # ✅ Doğru
   qss = STYLES.get("btn_action")
   ```

2. **Paletteyi takip et** — Yeni renkler eklemeden önce mevcut paleti kontrol et
   ```python
   # ✅ Doğru
   bg = DarkTheme.BG_PRIMARY
   
   # ❌ Hatalı (inline hardcoded)
   bg = "#16172b"
   ```

3. **Durum renkleri için helper kullan**
   ```python
   # ✅ Doğru
   color = ThemeManager.get_status_color("Aktif")
   
   # ❌ Hatalı (hardcoded)
   color = QColor(34, 197, 94, 40)
   ```

4. **Yeni bileşen eklerken docs güncelle**
   - Yukarıdaki "Tanımlanmış Bileşenler" tablosuna ekle
   - Örnekle anlat

### ❌ Yapılmaması Gereken

1. **Inline QSS hiçbir zaman**
   ```python
   # ❌ Hatalı
   button.setStyleSheet("background-color: #1d75fe;")
   ```

2. **Hardcoded renkler**
   ```python
   # ❌ Hatalı
   color = QColor("#4ade80")
   
   # ✅ Doğru
   color = DarkTheme.get_color("SUCCESS")
   ```

3. **Stil dict'lerini tekrar merkezleme**
   ```python
   # ❌ Hatalı - neden tekrar tanımlıyorsun?
   CUSTOM_STYLES = {
       "btn_something": "..."
   }
   
   # ✅ Doğru
   STYLES = ThemeManager.get_all_component_styles()
   ```

---

## 6. Tema Değişimi (Gelecek)

Geliş Örneği: Açık tema eklenirse:

**Adım 1:** `ui/styles/colors.py`'de `LightTheme` sınıfı ekle
**Adım 2:** `ThemeManager`'da tema seçimi logiki ekle
**Adım 3:** Tüm sayfalar otomatik güncellenir ✨

Bu nedenle, merkezi yönetim yapmak çok önemli!

---

## 7. Hızlı Başlangıç (Yeni Sayfa)

```python
# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt

from ui.theme_manager import ThemeManager

# ─── MERKEZİ STİL YÖNETIMI ───
STYLES = ThemeManager.get_all_component_styles()

class MyNewPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(STYLES.get("page", ""))  # Sayfa arka planı
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Label
        label = QLabel("Başlık")
        label.setStyleSheet(STYLES.get("label", ""))
        layout.addWidget(label)
        
        # Button
        button = QPushButton("İşlem Yap")
        button.setStyleSheet(STYLES.get("btn_action", ""))
        layout.addWidget(button)
```

---

## Sorular & Destek

Stil ile ilgili soru veya sorun? 
- `ui/theme_manager.py`'de `ThemeManager` sınıfını kontrol et
- `ui/styles/colors.py` ve `ui/styles/components.py`'de mevcut tanımları gözden geçir
- Yeni bir bileşen eklemek istersen, bu rehberi takip et

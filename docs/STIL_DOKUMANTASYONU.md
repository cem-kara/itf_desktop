# REPYS v3 — UI Stil Modülü Teknik Dökümantasyonu

> **Son güncelleme:** v3.1 — Temizlenmiş, duplikatsız, geriye dönük uyumlu

---

## İçindekiler

1. [Mimari Genel Bakış](#1-mimari-genel-bakış)
2. [Dosya Yapısı](#2-dosya-yapısı)
3. [colors.py — Renk Sistemi](#3-colorspy--renk-sistemi)
4. [components.py — Bileşen Stilleri](#4-componentspy--bileşen-stilleri)
5. [light_theme.py — Açık Tema](#5-light_themepy--açık-tema)
6. [theme_manager.py — Tema Uygulama](#6-theme_managerpy--tema-uygulama)
7. [theme_template.qss — Global QSS](#7-theme_templateqss--global-qss)
8. [STYLES Dict Referansı](#8-styles-dict-referansı)
9. [Geriye Dönük Uyumluluk Rehberi](#9-geriye-dönük-uyumluluk-rehberi)
10. [Yeni Sayfada Kullanım Şablonu](#10-yeni-sayfada-kullanım-şablonu)
11. [Sık Yapılan Hatalar](#11-sık-yapılan-hatalar)

---

## 1. Mimari Genel Bakış

Sistem **iki katmanlı renk mimarisi** kullanır:

```
┌─────────────────────────────────────────────────┐
│  Ham Palet   →   Colors (raw hex)               │
│  Semantic    →   DarkTheme / LightTheme (token) │
│  Component   →   ComponentStyles / STYLES dict  │
│  Global QSS  →   theme_template.qss             │
└─────────────────────────────────────────────────┘
```

**Renk akışı:**

```
Colors.RED_400 ("#f87171")
    └─→ DarkTheme.STATUS_ERROR / BTN_DANGER_TEXT
            └─→ ComponentStyles.BTN_DANGER
                    └─→ STYLES["btn_danger"]
                            └─→ widget.setStyleSheet(S["btn_danger"])
```

**Kural:** Sayfa/bileşen kodunda hiçbir zaman doğrudan `"#aabbcc"` yazmayın.
Her zaman `DarkTheme.<TOKEN>` veya `S["<key>"]` kullanın.

---

## 2. Dosya Yapısı

```
ui/
├── theme_manager.py          # Singleton tema uygulayıcı
├── theme_template.qss        # Dark tema global QSS şablonu
├── theme_light_template.qss  # Light tema global QSS şablonu
└── styles/
    ├── __init__.py           # Public API (import buradan)
    ├── colors.py             # Colors + DarkTheme sınıfları
    ├── light_theme.py        # LightTheme sınıfı
    ├── components.py         # ComponentStyles + STYLES dict
    ├── theme_registry.py     # Kayıt / runtime tema değiştirme
    └── icons.py              # SVG ikon kütüphanesi
```

---

## 3. colors.py — Renk Sistemi

### 3.1 Colors (Ham Palet)

Uygulama genelinde tekrar kullanılabilir renk referansları. **Doğrudan UI bileşenlerinde kullanılmaz.**

```python
from ui.styles.colors import Colors

# Yanlış ✗
label.setStyleSheet(f"color: {Colors.RED_400};")

# Doğru ✓
label.setStyleSheet(f"color: {DarkTheme.STATUS_ERROR};")
```

| Grup | Örnekler |
|------|----------|
| Mavi/Lacivert | `NAVY_950` … `NAVY_50` (13 kademe) |
| Cyan (accent) | `CYAN_500`, `CYAN_400`, `CYAN_300`, `CYAN_BG` |
| Gri | `GRAY_900` … `GRAY_100` (7 kademe) |
| Yeşil | `GREEN_600`, `GREEN_500`, `GREEN_400`, `GREEN_BG` |
| Kırmızı | `RED_600`, `RED_500`, `RED_400`, `RED_BG` |
| Sarı | `YELLOW_500`, `YELLOW_400`, `YELLOW_BG` |
| Turuncu | `ORANGE_500`, `ORANGE_400` |
| Mor | `PURPLE_500`, `PURPLE_400`, `PURPLE_BG` |

> **Not:** `Colors.SUCCESS` kaldırıldı (v3.0'da `GREEN_500` ile aynıydı).
> Kullanıyorsanız → `Colors.GREEN_500` ile değiştirin.

### 3.2 DarkTheme (Semantic Token'lar)

UI bileşenlerinde kullanılacak anlamsal token'lar. **Her attribute isminin proje genelinde tutarlı kullanılması zorunludur.**

#### Zemin hiyerarşisi

```
BG_PRIMARY (#0d1117)      ← Ana pencere
  └─ BG_SECONDARY (#121820)  ← Panel, kart
       └─ BG_ELEVATED (#1a2030)  ← Popup, input
```

> **Özel durum:** `BG_TERTIARY = BG_PRIMARY` — tablo zebra satırı için bilerek aynı değere
> ayarlanmıştır. Tablolarda iki satır arasında renk farkı istenirse `BG_ELEVATED` kullanın.

#### Kenarlık token'ları

| Token | Kullanım |
|-------|----------|
| `BORDER_PRIMARY` | Varsayılan kart / panel kenarlığı |
| `BORDER_SECONDARY` | Çok ince iç ayırıcılar |
| `BORDER_STRONG` | Belirgin kenarlık, hover geçişleri |
| `BORDER_FOCUS` | Odak halkası (mavi) |

> **Not:** `BORDER_SECONDARY` ve `BORDER_STRONG` şu anda aynı değere (`#253545`) sahiptir.
> Bu bilerek yapılmıştır; gelecekte bağımsız olarak ayarlanabilsin diye ayrı tutulmuştur.

#### Metin token'ları

| Token | Renk | Kullanım |
|-------|------|----------|
| `TEXT_PRIMARY` | `#e8edf5` | Başlıklar, aktif değerler |
| `TEXT_SECONDARY` | `#8fa3b8` | Normal form etiketleri, açıklamalar |
| `TEXT_MUTED` | `#4d6070` | Yer tutucu, yardımcı metin |
| `TEXT_DISABLED` | `#263850` | Devre dışı widget metni |

#### Durum token'ları

```python
DarkTheme.STATUS_SUCCESS   # "#2ec98e" — yeşil
DarkTheme.STATUS_WARNING   # "#e8a030" — sarı
DarkTheme.STATUS_ERROR     # "#e85555" — kırmızı
DarkTheme.STATUS_INFO      # "#3d8ef5" — mavi
```

#### v3.0'da kaldırılan attribute'lar

Aşağıdaki `RKE_*` attribute'lar `DarkTheme`'den kaldırılmıştır.
Mevcut kodunuzu aşağıdaki tabloya göre güncelleyin:

| Eski (kaldırıldı) | Yeni |
|-------------------|------|
| `DarkTheme.RKE_BG0` | `DarkTheme.BG_PRIMARY` |
| `DarkTheme.RKE_BG1` | `DarkTheme.BG_PRIMARY` |
| `DarkTheme.RKE_BG2` | `DarkTheme.BG_SECONDARY` |
| `DarkTheme.RKE_BG3` | `DarkTheme.BG_ELEVATED` |
| `DarkTheme.RKE_BD` | `DarkTheme.BORDER_PRIMARY` |
| `DarkTheme.RKE_BD2` | `DarkTheme.BORDER_STRONG` |
| `DarkTheme.RKE_TX0` | `DarkTheme.TEXT_PRIMARY` |
| `DarkTheme.RKE_TX1` | `DarkTheme.TEXT_SECONDARY` |
| `DarkTheme.RKE_TX2` | `DarkTheme.TEXT_MUTED` |
| `DarkTheme.RKE_RED` | `DarkTheme.STATUS_ERROR` |
| `DarkTheme.RKE_AMBER` | `DarkTheme.STATUS_WARNING` |
| `DarkTheme.RKE_GREEN` | `DarkTheme.STATUS_SUCCESS` |
| `DarkTheme.RKE_BLUE` | `DarkTheme.ACCENT` |
| `DarkTheme.RKE_CYAN` | `DarkTheme.ACCENT2` |
| `DarkTheme.RKE_PURP` | `Colors.PURPLE_500` |

---

## 4. components.py — Bileşen Stilleri

### 4.1 ComponentStyles Sınıfı

Her bileşen stili `ComponentStyles` sınıfında `f-string` olarak tanımlanır.
Tüm renkler `DarkTheme` token'larından türetilir; ham hex yasaklıdır.

### 4.2 STYLES Dict

Tüm stillere tek erişim noktası:

```python
from ui.styles.components import STYLES as S

btn.setStyleSheet(S["btn_action"])
table.setStyleSheet(S["table"])
```

#### Canonical key'ler (kullanılması gereken)

**Butonlar:**

| Key | Görünüm | Kullanım |
|-----|---------|----------|
| `btn_action` | Mavi dolgu | Birincil eylem (Kaydet, Onayla) |
| `btn_secondary` | Şeffaf, ince kenarlık | Geri, İptal |
| `btn_success` | Şeffaf → yeşil hover | Excel, Dışa Aktar |
| `btn_danger` | Şeffaf → kırmızı hover | Sil, Kapat |
| `btn_refresh` | Şeffaf → mavi hover | Yenile, küçük eylemler |
| `btn_filter` | Toggle filtre | Durum/grup filtreleri |
| `btn_filter_all` | Yuvarlak toggle | "Tümü" filtre butonu |
| `photo_btn` | Mavi dolgu (küçük) | Dosya yükle, Fotoğraf |

**Input'lar:**

| Key | Widget | Kullanım |
|-----|--------|----------|
| `input_field` | `QLineEdit` | Form girişleri |
| `input_search` | `QLineEdit` | Arama kutuları (padding-left: 30px) |
| `input_combo` | `QComboBox` | Dropdown seçimler |
| `input_date` | `QDateEdit` | Tarih seçiciler |
| `input_text` | `QTextEdit` | Çok satırlı metin |
| `spin` | `QSpinBox` | Sayısal girişler |

**Yapısal:**

| Key | Widget | Kullanım |
|-----|--------|----------|
| `table` | `QTableView/Widget` | Tüm tablolar |
| `group_box` | `QGroupBox` | Form grupları |
| `tab` | `QTabWidget/Bar` | Sekme grupları |
| `scrollbar` | `QScrollBar` | Kaydırma çubukları |
| `progress` | `QProgressBar` | 2-3px yükleme şeridi |
| `context_menu` | `QMenu` | Sağ tık menüleri |
| `splitter` | `QSplitter` | Bölünmüş paneller |
| `separator` | `QFrame` | Yatay ayırıcı çizgi |

**Etiketler:**

| Key | Font/Renk | Kullanım |
|-----|-----------|----------|
| `label_form` | 11px, 700w, ikincil | Form alan etiketleri |
| `label_title` | 15px, 700w, birincil | Panel başlıkları |
| `section_label` | 13px, 700w | Bölüm başlıkları |
| `footer_label` | 10px, muted | Alt bilgi, kayıt sayısı |
| `stat_value` | 16px, 600w, birincil | KPI değerleri |
| `stat_red` | 16px, kırmızı | Hata/uyarı KPI |
| `stat_green` | 16px, yeşil | Başarı KPI |
| `stat_highlight` | 16px, accent | Vurgulu KPI |

### 4.3 Durum Rengi Yardımcıları

```python
from ui.styles.components import ComponentStyles

# Badge arka plan rengi (RGBA tuple)
r, g, b, a = ComponentStyles.get_status_color("Aktif")
badge_color = QColor(r, g, b, a)

# Metin rengi (hex string)
text_color = ComponentStyles.get_status_text_color("Bakımda")
```

Desteklenen durum string'leri: `"Aktif"`, `"Pasif"`, `"İzinli"`, `"Arızalı"`,
`"Bakımda"`, `"Açık"`, `"İşlemde"`, `"Planlandı"`, `"Tamamlandı"`, `"Onaylandı"`,
`"Beklemede"`, `"İptal"`, `"Kalibrasyonda"`, `"Parça Bekliyor"`, `"Dış Serviste"`,
`"Kapalı (Çözüldü)"`

### 4.4 v3.0'da kaldırılan sınıf attribute'ları

Aşağıdaki sınıf içi takma adlar `ComponentStyles`'dan kaldırılmıştır.
Bunlar STYLES dict'te alias olarak yaşamaya devam eder; kod değişikliği gerekmez.

| Kaldırılan | Canonical karşılığı |
|------------|---------------------|
| `ComponentStyles.SAVE_BTN` | `ComponentStyles.BTN_SUCCESS` |
| `ComponentStyles.CANCEL_BTN` | `ComponentStyles.BTN_SECONDARY` |
| `ComponentStyles.EDIT_BTN` | `ComponentStyles.BTN_SECONDARY` |
| `ComponentStyles.DANGER_BTN` | `ComponentStyles.BTN_DANGER` |
| `ComponentStyles.REPORT_BTN` | `ComponentStyles.BTN_SECONDARY` |
| `ComponentStyles.PDF_BTN` | `ComponentStyles.BTN_SECONDARY` |
| `ComponentStyles.BACK_BTN` | `ComponentStyles.BTN_SECONDARY` |
| `ComponentStyles.CALC_BTN` | `ComponentStyles.BTN_SECONDARY` |
| `ComponentStyles.DATE` | `ComponentStyles.INPUT_DATE` |
| `ComponentStyles.LABEL` | `ComponentStyles.LABEL_FORM` |
| `ComponentStyles.INPUT` | `ComponentStyles.INPUT_FIELD` |
| `ComponentStyles.COMBO_FILTER` | `ComponentStyles.INPUT_COMBO` |
| `ComponentStyles.FILE_BTN` | `ComponentStyles.PHOTO_BTN` |

> **Önemli:** `ComponentStyles.XYZ` doğrudan erişimi (sınıf attribute) kullanıyorsanız
> yukarıdaki tablodan yeni adı bulun. `S["save_btn"]` gibi STYLES dict erişimi
> değişiklik gerektirmez — alias key'ler korunmuştur.

---

## 5. light_theme.py — Açık Tema

`LightTheme`, `DarkTheme` ile **birebir aynı attribute sözleşmesini** paylaşır.
Bu sayede `ThemeRegistry` üzerinden runtime'da tema değiştirilebilir.

```python
from ui.styles.theme_registry import ThemeRegistry, ThemeType

registry = ThemeRegistry.instance()
registry.set_active_theme(ThemeType.LIGHT)
```

> **v3.0'da tamamlanan:** Önceki versiyonda `LightTheme`'de 36 attribute eksikti
> (tüm `BTN_*`, `STATUS_*`, `STATE_*`, `MONOSPACE`). Artık tam eşleşme sağlanmıştır.

### Yeni attribute eklendiğinde

`DarkTheme`'e yeni bir attribute eklendiğinde `LightTheme`'de de aynı isimde
bir karşılık tanımlanmalıdır (ve tersi). Aksi hâlde runtime tema değişimi hata verir.

---

## 6. theme_manager.py — Tema Uygulama

### Temel Kullanım

```python
# main.py veya app başlangıcında
from ui.theme_manager import ThemeManager

app = QApplication(sys.argv)
ThemeManager.instance().apply_app_theme(app)
```

### Statik Yardımcılar

```python
manager = ThemeManager.instance()

# Bileşen stili
qss = manager.get_component_styles("btn_action")

# Renk değerleri
hex_color = manager.get_color("RED_400")              # Colors.RED_400
token_val  = manager.get_dark_theme_color("ACCENT")   # DarkTheme.ACCENT

# Durum renkleri
q_color  = manager.get_status_color("Aktif")          # QColor
txt_clr  = manager.get_status_text_color("Bakımda")   # str

# Takvim popup
manager.setup_calendar_popup(my_date_edit)
```

### QSS Renk Haritası

`theme_template.qss` içinde kullanılan tüm `{PLACEHOLDER}` değerleri:

| Placeholder | DarkTheme Token |
|-------------|-----------------|
| `{BG_PRIMARY}` | `DarkTheme.BG_PRIMARY` |
| `{BG_SECONDARY}` | `DarkTheme.BG_SECONDARY` |
| `{BG_TERTIARY}` | `DarkTheme.BG_TERTIARY` |
| `{BG_ELEVATED}` | `DarkTheme.BG_ELEVATED` |
| `{BG_DARK}` | `Colors.NAVY_950` |
| `{BORDER_PRIMARY}` | `DarkTheme.BORDER_PRIMARY` |
| `{TEXT_PRIMARY}` | `DarkTheme.TEXT_PRIMARY` |
| `{TEXT_SECONDARY}` | `DarkTheme.TEXT_SECONDARY` |
| `{TEXT_MUTED}` | `DarkTheme.TEXT_MUTED` |
| `{TEXT_DISABLED}` | `DarkTheme.TEXT_DISABLED` |
| `{ACCENT}` | `DarkTheme.ACCENT` |
| `{ACCENT2}` | `DarkTheme.ACCENT2` |

> QSS şablonuna yeni `{PLACEHOLDER}` eklenirse `ThemeManager._get_color_map()` metoduna
> da eklenmesi zorunludur; aksi hâlde şablonda çözümsüz placeholder kalır.

---

## 7. theme_template.qss — Global QSS

Uygulama genelindeki tüm widget türleri için temel stil tanımları içerir:

- `QWidget`, `QMainWindow`, `QDialog`
- `QMessageBox`, `QToolTip`
- `QScrollBar` (dikey + yatay)
- `QSplitter`
- `QProgressBar`
- `QCheckBox`, `QRadioButton`
- `QSpinBox`, `QTextBrowser`
- `QMenuBar`, `QMenu`
- `QStatusBar`
- `QCalendarWidget`
- `QDialogButtonBox`
- `QLabel` (fallback)
- `QGroupBox` (fallback)
- `QTabWidget`, `QTabBar`
- `QFrame` ayırıcılar

**Bileşene özel stiller** (tablo, form input, buton) STYLES dict üzerinden
`widget.setStyleSheet()` ile uygulanır; QSS şablonuna eklenmez.

---

## 8. STYLES Dict Referansı

### Canonical Key'ler (68 toplam)

```
Sayfa/Çerçeve:  page, filter_panel, separator, splitter
Butonlar:       btn_action, btn_secondary, btn_success, btn_danger,
                btn_refresh, btn_filter, btn_filter_all, photo_btn
Input:          input_search, input_field, input_combo, input_date,
                input_text, spin, calendar
Yapısal:        table, group_box, tab, scrollbar, progress, context_menu
Etiketler:      label_form, label_title, section_label, section_title,
                info_label, footer_label, header_name, required_label,
                max_label, donem_label
İstatistik:     stat_label, stat_value, stat_red, stat_green, stat_highlight, value
Durum badge:    header_durum_aktif, header_durum_pasif, header_durum_izinli
Fotoğraf:       photo_area, file_btn
```

### Alias Key'ler (geriye dönük uyumluluk)

```
save_btn    → btn_success       cancel_btn  → btn_secondary
edit_btn    → btn_secondary     danger_btn  → btn_danger
report_btn  → btn_secondary     pdf_btn     → btn_secondary
back_btn    → btn_secondary     calc_btn    → btn_secondary
action_btn  → btn_action        refresh_btn → btn_refresh
close_btn   → btn_danger        excel_btn   → btn_success
btn_close   → btn_danger        btn_excel   → btn_success
input       → input_field       search      → input_search
combo       → input_combo       combo_filter→ input_combo
date        → input_date        group       → group_box
label       → label_form        scroll      → scrollbar
```

---

## 9. Geriye Dönük Uyumluluk Rehberi

Bu bölüm mevcut sayfa kodunun değişiklik **gerektirip gerektirmediğini** açıklar.

### ✅ Değişiklik gerektirmeyen kullanımlar

```python
# STYLES dict erişimi — alias key'ler korundu
S["save_btn"]        # ✓
S["cancel_btn"]      # ✓
S["refresh_btn"]     # ✓
S["excel_btn"]       # ✓
S["close_btn"]       # ✓
S["group"]           # ✓
S["combo"]           # ✓
S["label"]           # ✓
S["scroll"]          # ✓

# DarkTheme semantic token'ları — değişmedi
DarkTheme.ACCENT     # ✓
DarkTheme.STATUS_ERROR  # ✓
DarkTheme.TEXT_PRIMARY  # ✓
DarkTheme.BG_SECONDARY  # ✓

# ThemeManager API — değişmedi
ThemeManager.instance().apply_app_theme(app)   # ✓
ThemeManager.instance().get_status_color(...)  # ✓
```

### ⚠️ Güncelleme gerektiren kullanımlar

| Mevcut kod | Güncellenmiş karşılık |
|------------|----------------------|
| `Colors.SUCCESS` | `Colors.GREEN_500` |
| `DarkTheme.RKE_BG0` | `DarkTheme.BG_PRIMARY` |
| `DarkTheme.RKE_BG2` | `DarkTheme.BG_SECONDARY` |
| `DarkTheme.RKE_BG3` | `DarkTheme.BG_ELEVATED` |
| `DarkTheme.RKE_BD` | `DarkTheme.BORDER_PRIMARY` |
| `DarkTheme.RKE_TX0` | `DarkTheme.TEXT_PRIMARY` |
| `DarkTheme.RKE_TX1` | `DarkTheme.TEXT_SECONDARY` |
| `DarkTheme.RKE_TX2` | `DarkTheme.TEXT_MUTED` |
| `DarkTheme.RKE_RED` | `DarkTheme.STATUS_ERROR` |
| `DarkTheme.RKE_AMBER` | `DarkTheme.STATUS_WARNING` |
| `DarkTheme.RKE_GREEN` | `DarkTheme.STATUS_SUCCESS` |
| `DarkTheme.RKE_BLUE` | `DarkTheme.ACCENT` |
| `DarkTheme.RKE_CYAN` | `DarkTheme.ACCENT2` |
| `ComponentStyles.SAVE_BTN` | `S["btn_success"]` |
| `ComponentStyles.CANCEL_BTN` | `S["btn_secondary"]` |
| `ComponentStyles.DANGER_BTN` | `S["btn_danger"]` |
| `ComponentStyles.FILE_BTN` | `S["file_btn"]` |

### Toplu değiştirme komutu (grep ile tespit)

```bash
# Kaldırılan attribute kullanımlarını bul
grep -rn "RKE_BG\|RKE_TX\|RKE_BD\|RKE_RED\|RKE_AMBER\|RKE_GREEN\|RKE_BLUE\|RKE_CYAN\|RKE_PURP" ui/
grep -rn "Colors\.SUCCESS\b" ui/
grep -rn "ComponentStyles\.\(SAVE\|CANCEL\|EDIT\|DANGER\|REPORT\|PDF\|BACK\|CALC\)_BTN" ui/
```

---

## 10. Yeni Sayfada Kullanım Şablonu

```python
# -*- coding: utf-8 -*-
"""Örnek sayfa — tema sistemi kullanımı."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QTableView,
)
from PySide6.QtGui import QColor

from ui.styles import DarkTheme
from ui.styles.colors import Colors
from ui.styles.components import STYLES as S, ComponentStyles

# ── Sabit renk referansları (QColor gereken yerlerde) ────────────
_RED   = DarkTheme.STATUS_ERROR    # "#e85555"
_GREEN = DarkTheme.STATUS_SUCCESS  # "#2ec98e"
_AMBER = DarkTheme.STATUS_WARNING  # "#e8a030"
_BLUE  = DarkTheme.ACCENT          # "#3d8ef5"


class OrnekSayfa(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(S["page"])
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Butonlar
        btn_kaydet = QPushButton("Kaydet")
        btn_kaydet.setStyleSheet(S["btn_success"])

        btn_iptal = QPushButton("İptal")
        btn_iptal.setStyleSheet(S["btn_secondary"])

        btn_sil = QPushButton("Sil")
        btn_sil.setStyleSheet(S["btn_danger"])

        btn_yenile = QPushButton("⟳")
        btn_yenile.setFixedSize(28, 28)
        btn_yenile.setStyleSheet(S["btn_refresh"])

        # Tablo
        tablo = QTableView()
        tablo.setStyleSheet(S["table"])
        tablo.setAlternatingRowColors(True)

        # Etiket
        baslik = QLabel("Ekipman Listesi")
        baslik.setStyleSheet(S["label_title"])

        # Durum rengi (badge'ler için)
        durum = "Aktif"
        r, g, b, a = ComponentStyles.get_status_color(durum)
        badge_rengi = QColor(r, g, b, a)
        metin_rengi = ComponentStyles.get_status_text_color(durum)

        # Tablo satır rengi (UserRole veri modeli)
        # model.setData(index, QColor(_RED), Qt.ForegroundRole)

        layout.addWidget(baslik)
        layout.addWidget(tablo)
```

---

## 11. Sık Yapılan Hatalar

### ❌ Hardcoded hex kullanımı

```python
# Yanlış
label.setStyleSheet("color: #e8edf5;")

# Doğru
label.setStyleSheet(f"color: {DarkTheme.TEXT_PRIMARY};")
```

### ❌ Inline QPushButton stili

```python
# Yanlış — bakımı imkânsız
btn.setStyleSheet("QPushButton { background: #3d8ef5; color: #060d1a; ... }")

# Doğru
btn.setStyleSheet(S["btn_action"])
```

### ❌ Colors'tan doğrudan UI rengi

```python
# Yanlış
badge.setStyleSheet(f"color: {Colors.RED_400};")

# Doğru — anlamsal token kullanın
badge.setStyleSheet(f"color: {DarkTheme.STATUS_ERROR};")
```

### ❌ LightTheme'e eksik attribute eklemeden DarkTheme güncelleme

```python
# DarkTheme'e yeni attribute ekliyorsanız:
class DarkTheme:
    MY_NEW_TOKEN = "#abcdef"   # ← burayı güncellediniz

# LightTheme'de de karşılığı olmalı:
class LightTheme:
    MY_NEW_TOKEN = "#fedcba"   # ← bunu da güncellemeniz gerekir!
```

### ❌ QSS şablonuna placeholder ekleyip haritayı güncellememek

```css
/* theme_template.qss'e eklendi */
QWidget { border-color: {MY_NEW_COLOR}; }
```

```python
# ThemeManager._get_color_map()'e de eklenmeli:
def _get_color_map(self):
    return {
        ...
        "MY_NEW_COLOR": DarkTheme.MY_NEW_TOKEN,  # ← eksik bırakırsanız placeholder çözümsüz kalır
    }
```

---

*REPYS v3 Stil Sistemi — Teknik Dökümantasyon*

# REPYS v3 — Tam Dönüşüm Planı

> Projenin mevcut durumu analiz edilerek hazırlanmıştır.  
> Her aşama bağımsız çalışır, uygulama her adım sonrası çalışmaya devam eder.  
> Tahmini toplam süre: **8–12 gün** (günde 3–4 saat)

---

## Mevcut Durum (Başlamadan Önce)

| Alan | Sayı | Durum |
|------|------|-------|
| Toplam .py dosyası | 145 | — |
| Toplam satır | 45.957 | — |
| Tema — inline f-string (sorunlu) | 5 | 🔴 Kalan sorunlar |
| Tema — hardcoded hex | 7 | 🟡 Temizlenecek |
| Tema — setProperty (rol sistemi) | 141 | ✅ Zaten dönüştürüldü |
| Tema — STYLES kullanan | 79 | 🟡 QSS'e taşınacak |
| UI'dan direkt DB çağrısı | 57 çağrı / 35 dosya | 🔴 Servis eksik |
| QAbstractTableModel sıfırdan | 3 | 🟡 BaseTableModel'e geçecek |
| Emoji kullanımı (UI) | 72 | 🟡 icons.py'ye geçecek |
| Eksik servisler | 5 adet | 🔴 Yazılacak |

---

## Aşama 0 — Zemin Hazırlığı (1 gün)

Bu aşama kodla ilgili değil. Sonraki her adımın güvencesidir.

### 0.1 Git dalı aç

```bash
git checkout -b refactor/clean-architecture
```

Her aşama için ayrı commit at. Bir şey bozulursa `git revert` ile geri dön.

### 0.2 Çalışan hali kaydet

```bash
git add -A && git commit -m "chore: refactor başlangıç snapshot"
```

### 0.3 `scripts/lint_theme.py` — Yasak Pattern Tarayıcısı

Aşağıdaki scripti `scripts/` klasörüne ekle. Her commit öncesi çalıştır.

```python
# scripts/lint_theme.py
"""
Yasak inline renk pattern'lerini tarar.
Kullanım: python scripts/lint_theme.py
"""
import os, re, sys

base = os.path.join(os.path.dirname(__file__), '..', 'ui')
YASAK = [
    (r'setStyleSheet\(f["\'].*?DarkTheme\.',   "DarkTheme f-string → setProperty kullan"),
    (r'setStyleSheet\(f["\'].*?get_current_theme', "get_current_theme f-string → setProperty kullan"),
    (r'setStyleSheet\("[^"]*#[0-9a-fA-F]{3,6}', "Hardcoded hex renk → DarkTheme token kullan"),
]

errors = []
for root, dirs, files in os.walk(base):
    dirs[:] = [d for d in dirs if '__pycache__' not in d]
    for fname in files:
        if not fname.endswith('.py'): continue
        fpath = os.path.join(root, fname)
        rel = fpath.replace(base + os.sep, '')
        with open(fpath, encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                stripped = line.strip()
                if stripped.startswith('#'): continue
                for pattern, msg in YASAK:
                    if re.search(pattern, line):
                        errors.append(f"  {rel}:{i}  {msg}\n    {stripped[:90]}")

if errors:
    print(f"❌ {len(errors)} ihlal bulundu:\n")
    for e in errors: print(e)
    sys.exit(1)
else:
    print(f"✅ Yasak pattern bulunamadı")
```

### 0.4 Pre-commit hook ekle

```bash
# .git/hooks/pre-commit
#!/bin/sh
python scripts/lint_theme.py || exit 1
```

```bash
chmod +x .git/hooks/pre-commit
```

---

## Aşama 1 — Tema Altyapısını Sadeleştir (2 gün)

**Ne değişiyor:** `DarkTheme` sınıfı + metaclass + registry + proxy → sade dict  
**Ne değişmiyor:** `ayarlar.json`, `theme_template.qss`, tüm sayfa dosyaları

### 1.1 `ui/styles/themes.py` oluştur

```python
# ui/styles/themes.py
"""
Tüm tema renkleri burada. Sınıf yok, dict var.
DarkTheme/LightTheme sınıfları bu dict'ten türetilir —
mevcut import'lar bozulmaz.
"""

DARK = {
    "BG_PRIMARY":    "#0d1117",
    "BG_SECONDARY":  "#121820",
    "BG_TERTIARY":   "#1a2332",
    "BG_ELEVATED":   "#1e2a3a",
    "BG_DARK":       "#080d13",
    "TEXT_PRIMARY":  "#e8edf5",
    "TEXT_SECONDARY":"#8fa3b8",
    "TEXT_MUTED":    "#4d6070",
    "TEXT_DISABLED": "#263850",
    "TEXT_TABLE_HEADER": "#a8bcd0",
    "BORDER_PRIMARY":  "rgba(255,255,255,0.08)",
    "BORDER_SECONDARY":"rgba(255,255,255,0.05)",
    "BORDER_STRONG":   "rgba(255,255,255,0.15)",
    "BORDER_FOCUS":    "#2563eb",
    "INPUT_BG":        "#0f1923",
    "ACCENT":          "#2563eb",
    "ACCENT2":         "#0891b2",
    "ACCENT_BG":       "rgba(37,99,235,0.12)",
    "STATUS_SUCCESS":  "#3ecf8e",
    "STATUS_WARNING":  "#facc15",
    "STATUS_ERROR":    "#f75f5f",
    "STATUS_INFO":     "#60a5fa",
    "BTN_PRIMARY_BG":  "#365a9f",
    "BTN_PRIMARY_HOVER":"#4a74c6",
    "BTN_PRIMARY_TEXT": "#e8edf5",
    "BTN_DANGER_BG":    "#c0392b",
    "BTN_DANGER_TEXT":  "#ffffff",
    "BTN_SUCCESS_BG":   "#27ae60",
    "BTN_SUCCESS_TEXT": "#ffffff",
    "MONOSPACE":        "\"Consolas\", \"Courier New\", monospace",
    "RKE_PURP":         "#a78bfa",
}

LIGHT = {
    "BG_PRIMARY":    "#f0f4f8",
    "BG_SECONDARY":  "#ffffff",
    "BG_TERTIARY":   "#e2e8f0",
    "BG_ELEVATED":   "#f8fafc",
    "BG_DARK":       "#1e293b",
    "TEXT_PRIMARY":  "#1e293b",
    "TEXT_SECONDARY":"#475569",
    "TEXT_MUTED":    "#64748b",
    "TEXT_DISABLED": "#94a3b8",
    "TEXT_TABLE_HEADER": "#334155",
    "BORDER_PRIMARY":  "rgba(0,0,0,0.10)",
    "BORDER_SECONDARY":"rgba(0,0,0,0.06)",
    "BORDER_STRONG":   "rgba(0,0,0,0.20)",
    "BORDER_FOCUS":    "#2563eb",
    "INPUT_BG":        "#ffffff",
    "ACCENT":          "#2563eb",
    "ACCENT2":         "#0891b2",
    "ACCENT_BG":       "rgba(37,99,235,0.08)",
    "STATUS_SUCCESS":  "#16a34a",
    "STATUS_WARNING":  "#d97706",
    "STATUS_ERROR":    "#dc2626",
    "STATUS_INFO":     "#2563eb",
    "BTN_PRIMARY_BG":  "#2563eb",
    "BTN_PRIMARY_HOVER":"#1d4ed8",
    "BTN_PRIMARY_TEXT": "#ffffff",
    "BTN_DANGER_BG":    "#dc2626",
    "BTN_DANGER_TEXT":  "#ffffff",
    "BTN_SUCCESS_BG":   "#16a34a",
    "BTN_SUCCESS_TEXT": "#ffffff",
    "MONOSPACE":        "\"Consolas\", \"Courier New\", monospace",
    "RKE_PURP":         "#7c3aed",
}

THEMES = {"dark": DARK, "light": LIGHT}

def get_tokens(name: str) -> dict:
    return THEMES.get(name.lower(), DARK)
```

### 1.2 `ui/styles/colors.py` sadeleştir

Mevcut `_LiveThemeMeta` + sınıf yapısını koru ama içini dict'ten besle:

```python
# ui/styles/colors.py
from ui.styles.themes import get_tokens
from core.settings import get as _get_setting

def get_current_theme_name() -> str:
    return _get_setting("theme", "dark")

def get_current_theme():
    """Geriye dönük uyumluluk — eski kod bozulmasın."""
    name = get_current_theme_name()
    return type("_Theme", (), get_tokens(name))()

class _LiveThemeMeta(type):
    def __getattribute__(cls, name):
        if name.startswith('_'):
            return type.__getattribute__(cls, name)
        try:
            tokens = get_tokens(get_current_theme_name())
            if name in tokens:
                return tokens[name]
        except Exception:
            pass
        return type.__getattribute__(cls, name)

class DarkTheme(metaclass=_LiveThemeMeta):
    """Mevcut importlar bozulmasın diye korunuyor."""
    pass  # Tüm attr'lar metaclass'tan geliyor

# Alias — bazı dosyalar C olarak import ediyor
C = DarkTheme
```

### 1.3 `core/settings.py` oluştur

```python
# core/settings.py
import json
from pathlib import Path
from core.paths import BASE_DIR

_PATH = Path(BASE_DIR) / "ayarlar.json"

def get(key: str, default=None):
    try:
        data = json.loads(_PATH.read_text("utf-8"))
        return data.get(key, default)
    except Exception:
        return default

def set(key: str, value) -> bool:
    try:
        data = {}
        if _PATH.exists():
            try:
                data = json.loads(_PATH.read_text("utf-8"))
            except Exception:
                data = {}
        data[key] = value
        _PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        return True
    except Exception as e:
        from core.logger import logger
        logger.warning(f"Ayar kaydedilemedi [{key}]: {e}")
        return False
```

### 1.4 `ui/theme_manager.py` sadeleştir

```python
# ui/theme_manager.py  — 60 satır, hepsi bu
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPalette, QColor
from pathlib import Path
from core import settings
from ui.styles.themes import get_tokens
from core.logger import logger

_QSS_PATH = Path(__file__).parent / "theme_template.qss"

class ThemeManager(QObject):
    theme_changed = Signal(str)
    _instance = None

    @classmethod
    def instance(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        super().__init__()
        self._current = settings.get("theme", "dark")

    def apply_app_theme(self, app: QApplication):
        """Başlangıçta kaydedilmiş temayı uygula."""
        app.setStyle("Fusion")
        self._apply(app, self._current)

    def set_theme(self, app: QApplication, name: str) -> bool:
        if name not in ("dark", "light"):
            return False
        try:
            self._apply(app, name)
            self._current = name
            settings.set("theme", name)
            self.theme_changed.emit(name)
            logger.info(f"Tema değiştirildi: {name}")
            return True
        except Exception as e:
            logger.error(f"Tema değişikliği hatası: {e}")
            return False

    def _apply(self, app: QApplication, name: str):
        tokens = get_tokens(name)
        # QSS
        qss = _QSS_PATH.read_text("utf-8")
        for k, v in tokens.items():
            qss = qss.replace(f"{{{k}}}", v)
        app.setStyleSheet(qss)
        # QPalette
        p = QPalette()
        p.setColor(QPalette.Window,          QColor(tokens["BG_PRIMARY"]))
        p.setColor(QPalette.WindowText,      QColor(tokens["TEXT_PRIMARY"]))
        p.setColor(QPalette.Base,            QColor(tokens["BG_TERTIARY"]))
        p.setColor(QPalette.AlternateBase,   QColor(tokens["BG_SECONDARY"]))
        p.setColor(QPalette.Text,            QColor(tokens["TEXT_PRIMARY"]))
        p.setColor(QPalette.Button,          QColor(tokens["BG_SECONDARY"]))
        p.setColor(QPalette.ButtonText,      QColor(tokens["TEXT_PRIMARY"]))
        p.setColor(QPalette.Highlight,       QColor(tokens["ACCENT"]))
        p.setColor(QPalette.HighlightedText, QColor("#ffffff" if name == "light" else tokens["BG_DARK"]))
        p.setColor(QPalette.PlaceholderText, QColor(tokens["TEXT_MUTED"]))
        app.setPalette(p)
```

### 1.5 `ui/styles/components.py` sadeleştir

Mevcut `_build_component_styles(C)` yapısını koru, ama `C` artık dict:

```python
# components.py'de sadece bu değişir:
from ui.styles.themes import get_tokens
from core.settings import get as _get_setting

def _build_component_styles():
    tokens = get_tokens(_get_setting("theme", "dark"))
    C = type("C", (), tokens)()   # dict → attribute erişimi
    # ... geri kalan aynı
```

**Aşama 1 sonunda commit:**
```bash
git add -A && git commit -m "refactor: tema altyapısı dict tabanlı mimariye geçirildi"
```

---

## Aşama 2 — STYLES'ı QSS'e Taşı (2 gün)

**Ne değişiyor:** 71 STYLES key'i → `theme_template.qss`'e eklenir  
**Neden:** STYLES kullanan widget'lar hâlâ tema değişiminde sayfa yeniden oluşturmak zorunda  
**Sonuç:** `app.setStyleSheet()` yeterli olur, sayfa yıkma gerekmez

### 2.1 Her STYLES key için QSS selector yaz

STYLES key'lerini üç gruba ayır:

**Grup A — Doğrudan QSS'e taşınır (basit, state yok):**
```css
/* theme_template.qss'e ekle */

/* ── STYLES["page"] → artık sadece QWidget var, widget-specific'e gerek yok */
/* ── STYLES["separator"] */
QFrame[style-role="separator"] {
    background-color: {BORDER_SECONDARY};
    max-height: 1px;
    border: none;
}

/* ── STYLES["label"], STYLES["label_form"] */
QLabel[style-role="form"]    { color: {TEXT_SECONDARY}; font-size: 12px; }
QLabel[style-role="title"]   { color: {TEXT_PRIMARY}; font-size: 14px; font-weight: 700; }
QLabel[style-role="section"] { color: {ACCENT}; font-size: 12px; font-weight: 700; letter-spacing: 0.05em; }
QLabel[style-role="footer"]  { color: {TEXT_MUTED}; font-size: 10px; }
QLabel[style-role="info"]    { color: {TEXT_MUTED}; font-size: 11px; }
QLabel[style-role="value"]   { color: {TEXT_PRIMARY}; font-size: 13px; font-weight: 600; }
QLabel[style-role="stat"]    { color: {TEXT_PRIMARY}; font-size: 22px; font-weight: 700; }
QLabel[style-role="required"]{ color: {STATUS_ERROR}; font-size: 11px; }
QLabel[style-role="donem"]   { color: {ACCENT2}; font-size: 12px; font-weight: 600; }

/* ── STYLES["scroll"] */
QScrollArea[style-role="plain"] { background: {BG_PRIMARY}; border: none; }
```

**Grup B — Hover/Focus state'i olan, QSS'te kalmalı:**
```css
/* Butonlar — zaten QSS'te çalışıyor, sadece style-role ekle */
QPushButton[style-role="action"]    { /* BTN_ACTION içeriği */ }
QPushButton[style-role="secondary"] { /* BTN_SECONDARY içeriği */ }
QPushButton[style-role="danger"]    { /* BTN_DANGER içeriği */ }
QPushButton[style-role="success"]   { /* BTN_SUCCESS içeriği */ }
QPushButton[style-role="refresh"]   { /* BTN_REFRESH içeriği */ }

/* Input'lar — zaten QSS'te var, ek selector gerekmez */
```

**Grup C — Özel/tek kullanım, STYLES'ta bırak:**
```python
# Bu key'ler STYLES'ta kalır çünkü çok spesifik:
# header_durum_aktif, header_durum_pasif, header_durum_izinli
# stat_red, stat_green, stat_highlight
# photo_area, photo_btn
```

### 2.2 Python dosyalarını güncelle

```python
# ESKİ
btn.setStyleSheet(STYLES["btn_action"])

# YENİ
btn.setProperty("style-role", "action")
```

```python
# ESKİ
lbl.setStyleSheet(STYLES["label_form"])

# YENİ
lbl.setProperty("style-role", "form")
```

> **Not:** Bu adım büyük. Önce `scripts/migrate_styles.py` yaz, otomatik dönüştür,
> sonra her dosyayı gözden geçir.

### 2.3 `_on_theme_changed` basitleştir

Sayfa yıkma artık gerekmez:

```python
def _on_theme_changed(self, theme_name: str):
    """Sadece sidebar ve status bar'ı refresh et."""
    self.style().unpolish(self)
    self.style().polish(self)
    self.update()
    # Sayfaları yıkmaya GEREK YOK — QSS otomatik güncelledi
    logger.info(f"Tema uygulandı: {theme_name}")
```

**Aşama 2 sonunda commit:**
```bash
git add -A && git commit -m "refactor: STYLES QSS role sistemine taşındı, sayfa yıkma kaldırıldı"
```

---

## Aşama 3 — Eksik Servisleri Yaz (3 gün)

**Öncelik sırası:** En çok direkt DB çağrısı olan servis önce.

### 3.1 `CihazService` — 48 çağrı, 13 dosya (1 gün)

```python
# core/services/cihaz_service.py
class CihazService:
    def get_cihaz_listesi(self, filtre=None) -> list: ...
    def get_cihaz(self, cihaz_id: str) -> dict: ...
    def kaydet(self, veri: dict, guncelle=False) -> bool: ...
    def sil(self, cihaz_id: str) -> bool: ...
    def get_ariza_listesi(self, cihaz_id: str) -> list: ...
    def ariza_kaydet(self, veri: dict) -> bool: ...
    def get_bakim_listesi(self, cihaz_id: str) -> list: ...
    def bakim_kaydet(self, veri: dict) -> bool: ...
```

Yazıldıktan sonra:
- `cihaz_listesi.py` — 6 çağrı taşı
- `cihaz_ekle.py` — 7 çağrı taşı
- `cihaz_merkez.py` — 3 çağrı taşı
- `ariza_islem.py` — 5 çağrı taşı
- `cihaz_overview_panel.py` — 7 çağrı taşı
- *(diğerleri...)*

### 3.2 `RkeService` — 16 çağrı, 4 dosya (½ gün)

```python
# core/services/rke_service.py
class RkeService:
    def get_rke_listesi(self) -> list: ...
    def get_muayene_listesi(self, rke_id: str) -> list: ...
    def muayene_kaydet(self, veri: dict) -> bool: ...
    def get_rapor_verisi(self, filtre: dict) -> list: ...
```

### 3.3 `SaglikService` — 11 çağrı, 3 dosya (½ gün)

```python
# core/services/saglik_service.py
class SaglikService:
    def get_saglik_kayitlari(self, tc_no: str) -> list: ...
    def kaydet(self, veri: dict) -> bool: ...
    def get_ozet(self, tc_no: str) -> dict: ...
```

### 3.4 `FhszService` — 7 çağrı, 1 dosya (½ gün)

```python
# core/services/fhsz_service.py
class FhszService:
    def get_fhsz_listesi(self, filtre=None) -> list: ...
    def kaydet(self, veri: dict) -> bool: ...
    def sil(self, fhsz_id: str) -> bool: ...
```

### 3.5 `YilSonuService` + `DashboardService` (½ gün)

Her yeni servise test yaz:

```python
# tests/services/test_cihaz_service.py
def test_kaydet_basarili(svc, reg): ...
def test_db_hata_false_doner(svc, reg): ...
def test_sil_pk_yoksa_false(svc, reg): ...
```

**Her servis sonrası commit:**
```bash
git add -A && git commit -m "feat: CihazService eklendi, 13 dosyada direkt DB çağrısı kaldırıldı"
```

---

## Aşama 4 — QAbstractTableModel Temizliği (½ gün)

Sadece 3 dosya:

| Dosya | Sınıf | Yapılacak |
|-------|-------|-----------|
| `ui/components/data_table.py` | `DictTableModel` | `BaseTableModel` extend et |
| `ui/pages/personel/components/personel_izin_panel.py` | `RecentLeaveTableModel` | `BaseTableModel` extend et |

> `ui/components/base_table_model.py` — bu zaten doğru, dokunma.

**Commit:**
```bash
git add -A && git commit -m "refactor: DictTableModel ve RecentLeaveTableModel BaseTableModel'e geçirildi"
```

---

## Aşama 5 — Emoji → icons.py (1 gün)

72 emoji kullanımı var. Fırsatçı değil, toplu temizlik:

```bash
# Emoji olan dosyalar
python3 -c "
import os, re
for root, _, files in os.walk('ui/'):
    for f in files:
        if not f.endswith('.py'): continue
        p = os.path.join(root, f)
        content = open(p).read()
        n = len(re.findall(r'[📄📁✅❌⚠🔔📊🔧💾🔄➕🔍📋👤]', content))
        if n: print(f'{n:3d}  {p}')
" | sort -rn
```

Dönüşüm:
```python
# ESKİ
btn = QPushButton("📁 Dosya Seç")

# YENİ
btn = QPushButton("Dosya Seç")
IconRenderer.set_button_icon(btn, "upload", color=IconColors.PRIMARY, size=16)
```

> Logger mesajlarındaki emoji'lere dokunma — log okunabilirliği için faydalı.

**Commit:**
```bash
git add -A && git commit -m "refactor: UI emoji'leri icons.py'ye taşındı"
```

---

## Aşama 6 — `ayarlar.json` Yapısını Düzenle (½ gün)

Şu an `ayarlar.json` içinde menu yapılandırması, tema, app_mode hepsi karışık.
Temizle:

```json
{
  "theme": "dark",
  "app_mode": "offline",
  "menu_yapilandirma": { ... }
}
```

`core/settings.py` zaten doğru çalışıyor. Sadece mevcut `AppConfig.resolve_app_mode()`
ve `ThemeManager` metodlarını `settings.get/set` kullanacak şekilde güncelle.

---

## Sonuç — Bitiş Durumu

| Alan | Başlangıç | Bitiş |
|------|-----------|-------|
| Tema altyapısı | 400+ satır (sınıf + metaclass + proxy + registry) | ~60 satır (dict + ThemeManager) |
| STYLES | 71 key, Python'da f-string | QSS'e taşındı, `style-role` property |
| Tema değişimi | Sayfaları yık + yeniden oluştur | `app.setStyleSheet()` yeterli |
| Direkt DB çağrısı | 57 | 0 (hepsi serviste) |
| Eksik servis | 5 | 0 |
| QAbstractTableModel sıfırdan | 3 | 0 |
| Emoji | 72 | 0 (logger hariç) |
| Tema kalıcılığı | ✅ (zaten eklendi) | ✅ |

---

## Önerilen Başlangıç Sırası

```
Bugün:    Aşama 0  — Git + lint script
Yarın:    Aşama 1  — Tema altyapısı (themes.py + settings.py)
3. gün:   Aşama 1  — ThemeManager + colors.py + components.py
4. gün:   Aşama 2  — STYLES → QSS (QSS yazımı)
5. gün:   Aşama 2  — Python dosyalarını güncelle
6. gün:   Aşama 3  — CihazService
7. gün:   Aşama 3  — RkeService + SaglikService
8. gün:   Aşama 3  — FhszService + YilSonuService + DashboardService
9. gün:   Aşama 4+5 — TableModel + Emoji
10. gün:  Aşama 6  — ayarlar.json + son kontrol
```

---

## Önemli Kurallar

1. **Her aşama bağımsız çalışır.** Aşama 1 bitmeden Aşama 2'ye geçme.
2. **Her commit öncesi `python scripts/lint_theme.py` çalıştır.**
3. **Her yeni servis için test yaz, sonra UI'a bağla.**
4. **Fırsatçı refactor değil, planlı refactor.** Listedeki dışına çıkma.
5. **Bir şey bozulursa `git revert` — yamalama değil.**

---

*Plan, projenin 03.03.2026 tarihli analizi temel alınarak hazırlanmıştır.*

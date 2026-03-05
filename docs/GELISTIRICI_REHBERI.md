# REPYS v3 — Geliştirici Rehberi
> Son güncelleme: Mart 2026 — Aşama 0–6 refactor tamamlandı.  
> Yeni modül eklerken, mevcut dosyaya girerken ve servis bağlarken bu dosyaya bak.

---

## 0. ÖNCE OKU — Mevcut Mimari Özeti

```
itf_desktop/
├── core/
│   ├── config.py          ← AppConfig (app_mode, auto_sync, log ayarları)
│   ├── settings.py        ← ayarlar.json okuma/yazma (get/set)
│   ├── di.py              ← Dependency Injection fabrika fonksiyonları
│   ├── date_utils.py      ← to_ui_date, parse_date, to_db_date
│   ├── validators.py      ← TC, email, telefon validasyonu
│   ├── text_utils.py      ← turkish_title_case, turkish_upper
│   └── services/          ← TÜM iş mantığı burada (UI'dan doğrudan DB YOK)
│       ├── cihaz_service.py
│       ├── personel_service.py
│       ├── rke_service.py
│       ├── saglik_service.py
│       ├── fhsz_service.py
│       ├── dashboard_service.py
│       ├── ariza_service.py
│       ├── bakim_service.py
│       ├── kalibrasyon_service.py
│       ├── izin_service.py
│       ├── dokuman_service.py
│       ├── backup_service.py
│       ├── log_service.py
│       ├── settings_service.py
│       └── file_sync_service.py
├── ui/
│   ├── theme_template.qss ← Tüm renkler burada (token tabanlı)
│   ├── theme_manager.py   ← Tema uygulama (ThemeManager.instance())
│   ├── styles/
│   │   ├── colors.py      ← DarkTheme / C alias (live token)
│   │   ├── themes.py      ← DARK / LIGHT dict (ham token değerleri)
│   │   ├── components.py  ← STYLES dict (geçiş döneminde, kademeli silinecek)
│   │   └── icons.py       ← Icons, IconRenderer, IconColors
│   └── components/
│       └── base_table_model.py  ← TÜM model sınıflarının ebeveyni
```

---

## 1. SİLİNECEK DOSYALAR

Hiçbir yerden import edilmiyor — güvenle silinebilir:

| Dosya | Sebep |
|---|---|
| `core/cihaz_ozet_servisi.py` | `CihazService` tarafından tamamen ikame edildi |
| `ui/components/data_table.py` | `DictTableModel` ve `DataTableWidget` — kullanılmıyor |

```bash
git rm core/cihaz_ozet_servisi.py
git rm ui/components/data_table.py
git commit -m "chore: kullanılmayan dosyalar silindi"
```

---

## 2. KOD İÇİ TEMİZLENECEK SATIRLAR

Bir dosyaya girdiğinde gördüklerini düzelt — fırsatçı refactor prensibi.

### 2.1 Lokal `_DURUM_COLOR` dict → `self.status_fg()` kullan

`BaseTableModel.status_fg()` tüm durum renklerini merkezi tutuyor. Bu dosyalardaki lokal dict'ler silinebilir:

- `ui/pages/cihaz/ariza_kayit.py` — `_DURUM_COLOR = {...}` bloğu
- `ui/pages/cihaz/bakim_form.py` — `_DURUM_COLOR = {...}` bloğu
- `ui/pages/cihaz/kalibrasyon_form.py` — `_DURUM_COLOR = {...}` bloğu
- `ui/pages/personel/izin_takip.py` — `DURUM_COLORS_FG = {...}` bloğu

```python
# ÖNCE (silinecek)
_DURUM_COLOR = {"Açık": "#ef4444", "Tamamlandı": "#22c55e"}
def _fg(self, key, row):
    if key == "Durum":
        c = _DURUM_COLOR.get(row.get("Durum", ""))
        return QColor(c) if c else None

# SONRA
def _fg(self, key, row):
    if key == "Durum":
        return self.status_fg(row.get("Durum", ""))
```

### 2.2 Lokal `set_rows()` alias tanımları → silinebilir

`BaseTableModel`'de zaten var. Bu dosyalarda lokal tanımı sil:

`rke_yonetim.py`, `rke_rapor.py`, `rke_muayene.py`, `ariza_islem.py`,
`kalibrasyon_form.py`, `ariza_kayit.py`, `bakim_form.py`, `saglik_takip.py`

```python
# Silinecek satır
def set_rows(self, rows): self.set_data(rows)
```

### 2.3 Model dosyalarındaki `to_ui_date` import → `self._fmt_date` veya `DATE_KEYS`

`BaseTableModel._fmt_date()` ve `DATE_KEYS` artık tüm tarih formatlamayı yapıyor.

Etkilenen dosyalar: `base_table_model.py`, `ariza_islem.py`, `kalibrasyon_form.py`,
`ariza_kayit.py`, `bakim_form.py`, `personel_saglik_panel.py`

```python
# ÖNCE
from core.date_utils import to_ui_date
def _display(self, key, row):
    if key == "Tarih": return to_ui_date(row.get(key,""), "")

# SONRA — seçenek A: DATE_KEYS (override gerektirmez)
class BakimModel(BaseTableModel):
    DATE_KEYS = frozenset({"PlanlananTarih", "BakimTarihi"})

# SONRA — seçenek B: _fmt_date
def _display(self, key, row):
    if key == "Tarih": return self._fmt_date(row.get(key,""), "")
```

### 2.4 `cihaz_listesi.py` — lokal `RAW_ROW_ROLE` tanımı

`BaseTableModel`'de tanımlı, lokal tanımı sil:
```python
# Silinecek satır
RAW_ROW_ROLE = Qt.ItemDataRole.UserRole + 1
```

---

## 3. DEVAM EDECEK GÜNCELLEMELER

### 3.1 🔴 DI'ya Eksik Servis Fabrikaları — `core/di.py`

9 servis DI'ya kayıtlı değil:

```python
# core/di.py — bunları ekle
def get_izin_service(db):
    from core.services.izin_service import IzinService
    return IzinService(get_registry(db))

def get_ariza_service(db):
    from core.services.ariza_service import ArizaService
    return ArizaService(get_registry(db))

def get_bakim_service(db):
    from core.services.bakim_service import BakimService
    return BakimService(get_registry(db))

def get_kalibrasyon_service(db):
    from core.services.kalibrasyon_service import KalibrasyonService
    return KalibrasyonService(get_registry(db))

def get_dokuman_service(db):
    from core.services.dokuman_service import DokumanService
    return DokumanService(get_registry(db))

def get_backup_service(db):
    from core.services.backup_service import BackupService
    return BackupService(get_registry(db))

def get_log_service(db):
    from core.services.log_service import LogService
    return LogService(get_registry(db))

def get_settings_service(db):
    from core.services.settings_service import SettingsService
    return SettingsService(get_registry(db))

def get_file_sync_service(db):
    from core.services.file_sync_service import FileSyncService
    return FileSyncService(get_registry(db))
```

### 3.2 🔴 Personel UI → Servis Katmanına Taşı

| Dosya | Çağrı | Hedef Servis |
|---|---|---|
| `personel/izin_takip.py` | 6x get_registry | `get_izin_service(db)` |
| `personel/isten_ayrilik.py` | 3x | `get_personel_service(db)` |
| `personel/personel_ekle.py` | 1x | `get_personel_service(db)` |
| `personel/personel_listesi.py` | 1x | `get_personel_service(db)` |
| `personel/personel_overview_panel.py` | 1x | `get_personel_service(db)` |
| `personel/components/hizli_izin_giris.py` | 2x | `get_izin_service(db)` |
| `personel/components/personel_izin_panel.py` | 1x | `get_izin_service(db)` |
| `personel/puantaj_rapor.py` | 1x | `get_fhsz_service(db)` |

### 3.3 🔴 RKE UI → Servis Katmanına Taşı

| Dosya | Çağrı | Hedef Servis |
|---|---|---|
| `rke/rke_muayene.py` | 3x | `get_rke_service(db)` |
| `rke/rke_rapor.py` | 1x | `get_rke_service(db)` |
| `rke/rke_yonetim.py` | 1x | `get_rke_service(db)` |

### 3.4 🟡 87 `setStyleSheet(f-string)` → `setProperty` ile QSS

Tema değiştirmede bu widget'lar güncellenmez. En kritik dosyalar:
`bakim_form.py` (12), `rke_rapor.py` (11), `kalibrasyon_form.py` (7), `sidebar.py` (4)

```python
# ÖNCE (tema değişince güncellenmez)
label.setStyleSheet(f"color: {C.TEXT_SECONDARY}; font-size: 12px;")

# SONRA (QSS otomatik günceller)
label.setProperty("color-role", "secondary")
label.setStyleSheet("font-size: 12px;")   # sadece renk dışı özellikler
```

### 3.5 🟡 `base_dokuman_panel.py` + `yil_sonu_devir_page.py` — RepositoryRegistry direkt

```python
# ÖNCE
from database.repository_registry import RepositoryRegistry
registry = RepositoryRegistry(self._db)

# SONRA
from core.di import get_dokuman_service
svc = get_dokuman_service(self._db)
```

### 3.6 🟢 Testler Yaz

```bash
mkdir -p tests/services
# pytest + MagicMock pattern için → Bölüm 6'ya bak
```

---

## 4. YENİ MODÜL EKLERKEN

### 4.1 Tablo adlarını kontrol et

```python
python -c "
import re
tables = re.findall(r'^    \"(\w+)\":', open('database/table_config.py').read(), re.M)
print(tables)
"
```

| Tablo | PK | Not |
|---|---|---|
| `Personel` | `KimlikNo` | "Personeller" değil |
| `Izin_Giris` | `Izinid` | "IzinId" değil |
| `Izin_Bilgi` | `TCKimlik` | İzin bakiye tablosu |
| `Cihaz_Ariza` | `Arizaid` | "ArizaId" değil |
| `Periyodik_Bakim` | `Planid` | |
| `Kalibrasyon` | `Kalid` | "KalibrasyonId" değil |
| `Cihazlar` | `Cihazid` | |
| `Sabitler` | `Rowid` | Dropdown listeleri |
| `Personel_Saglik_Takip` | `KayitNo` | |
| `RKE_Muayene` | `KayitNo` | |
| `RKE_List` | `EkipmanNo` | |
| `FHSZ_Puantaj` | — | Composite PK — table_config'e bak |
| `Ariza_Islem` | `Islemid` | |

### 4.2 Servis dosyası şablonu

```python
# core/services/xxx_service.py
from typing import Optional
from core.logger import logger
from database.repository_registry import RepositoryRegistry


class XxxService:
    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("RepositoryRegistry boş olamaz")
        self._r = registry

    def get_listesi(self, filtre_id: Optional[str] = None) -> list:
        try:
            rows = self._r.get("TABLO_ADI").get_all() or []
            if filtre_id:
                rows = [r for r in rows if str(r.get("ALAN","")) == str(filtre_id)]
            return rows
        except Exception as e:
            logger.error(f"XxxService.get_listesi hatası: {e}")
            return []

    def kaydet(self, veri: dict, guncelle: bool = False) -> bool:
        try:
            repo = self._r.get("TABLO_ADI")
            if guncelle:
                pk = veri.get("GERCEK_PK_ADI")   # table_config'den bak!
                if not pk:
                    logger.error("UPDATE için PK boş olamaz")
                    return False
                repo.update(pk, veri)
            else:
                repo.insert(veri)
            return True
        except Exception as e:
            logger.error(f"XxxService.kaydet hatası: {e}")
            return False

    def sil(self, pk: str) -> bool:
        try:
            self._r.get("TABLO_ADI").delete(pk)
            return True
        except Exception as e:
            logger.error(f"XxxService.sil hatası: {e}")
            return False
```

Servis yazıldıktan sonra **`core/di.py`'ye fabrika ekle:**
```python
def get_xxx_service(db):
    from core.services.xxx_service import XxxService
    return XxxService(get_registry(db))
```

**Kontrol listesi:**
```
[ ] Tablo adını table_config.py'den kopyaladım
[ ] PK adını table_config.py'den kopyaladım
[ ] Her method try/except ile sarılı
[ ] Hata durumunda [] veya False veya None dönüyor
[ ] logger.error() çağrılıyor
[ ] __init__'te None kontrolü var
[ ] core/di.py'ye get_xxx_service() eklendi
```

### 4.3 UI sayfası şablonu

```python
from core.di import get_xxx_service
from ui.styles.colors import DarkTheme as C
from ui.styles.icons import IconRenderer, IconColors

class XxxPage(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db  = db
        self._svc = get_xxx_service(db) if db else None
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        lbl = QLabel("Başlık")
        lbl.setProperty("color-role", "primary")   # f-string değil!

        btn = QPushButton("Kaydet")
        btn.setProperty("style-role", "action")
        IconRenderer.set_button_icon(btn, "save", color=IconColors.PRIMARY, size=14)

    def _load_data(self):
        if not self._svc:
            return
        self._model.set_data(self._svc.get_listesi())
```

**YAPMA:**
```python
# ❌ UI'dan direkt DB çağrısı
from core.di import get_registry
repo = get_registry(db).get("Periyodik_Bakim")

# ❌ Inline f-string renk
label.setStyleSheet(f"color: {C.TEXT_PRIMARY};")

# ✅ Doğrusu
self._svc.get_bakim_listesi(cihaz_id)
label.setProperty("color-role", "primary")
```

### 4.4 TableModel şablonu

```python
from ui.components.base_table_model import BaseTableModel

XXX_COLUMNS = [
    ("DbAlani1", "Başlık 1", 120),   # (db_key, header, genişlik_px)
    ("Tarih",    "Tarih",     90),
    ("Durum",    "Durum",     70),
]

class XxxTableModel(BaseTableModel):
    DATE_KEYS    = frozenset({"Tarih"})            # otomatik _fmt_date
    ALIGN_CENTER = frozenset({"Durum", "Tarih"})   # merkez hizalama

    def __init__(self, rows=None, parent=None):
        super().__init__(XXX_COLUMNS, rows, parent)

    def _fg(self, key, row):
        if key == "Durum":
            return self.status_fg(row.get("Durum", ""))
        return None
```

**BaseTableModel tam API:**

```python
# Veri yükleme
model.set_data(rows)         # tüm veriyi değiştir + reset
model.set_rows(rows)         # set_data alias — geriye uyumluluk
model.append_rows(rows)      # sayfalama: mevcut veriye ekle (reset yok)
model.clear()                # tüm veriyi temizle

# Satır erişimi
model.get_row(idx)           # indeks → dict (geçersizse None)
model.all_data()             # tüm satırlar → list[dict]
len(model)                   # satır sayısı

# QTableView entegrasyonu
model.setup_columns(view)                          # son kolon stretch
model.setup_columns(view, stretch_keys=["Baslik"]) # belirli kolonlar stretch

# Özel roller
index.data(model.RAW_ROW_ROLE)    # satır dict (tercih et)
index.data(Qt.ItemDataRole.UserRole)  # satır dict (eski API)

# Override noktaları
model._display(key, row)    # gösterim değeri
model._fg(key, row)         # ön plan rengi → QColor | None
model._bg(key, row)         # arka plan rengi → QColor | None
model._align(key)           # hizalama
model._fmt_date(val, "")    # tarih → "GG.AA.YYYY"
model.status_fg(durum)      # durum string → QColor
model.status_bg(durum)      # durum string → QColor (arka plan)
```

**Desteklenen durum renkleri (status_fg/status_bg):**
`Aktif`, `Pasif`, `İzinli`, `Açık`, `İşlemde`, `Beklemede`, `Planlandı`,
`Tamamlandı`, `Onaylandı`, `İptal`, `Geçerli`, `Geçersiz`,
`Uygun`, `Uygun Değil`, `Hurda`, `Tamirde`

**YAPMA:**
```python
# ❌ Sıfırdan QAbstractTableModel — 80 satır duplikasyon
class BakimModel(QAbstractTableModel):
    def rowCount(self, ...): ...

# ❌ Lokal durum dict
_DURUM_RENK = {"Açık": "#ef4444"}

# ❌ Lokal set_rows alias
def set_rows(self, rows): self.set_data(rows)

# ❌ to_ui_date (model içinde)
from core.date_utils import to_ui_date
```

---

## 5. TEMA SİSTEMİ — Doğru Kullanım

### 5.1 color-role (metin rengi)

```python
lbl.setProperty("color-role", "primary")    # TEXT_PRIMARY
lbl.setProperty("color-role", "secondary")  # TEXT_SECONDARY
lbl.setProperty("color-role", "muted")      # TEXT_MUTED
lbl.setProperty("color-role", "disabled")   # TEXT_DISABLED
lbl.setProperty("color-role", "accent")     # ACCENT
lbl.setProperty("color-role", "accent2")    # ACCENT2
lbl.setProperty("color-role", "ok")         # STATUS_SUCCESS
lbl.setProperty("color-role", "warn")       # STATUS_WARNING
lbl.setProperty("color-role", "err")        # STATUS_ERROR
lbl.setProperty("color-role", "info")       # STATUS_INFO
```

### 5.2 style-role (QPushButton)

```python
btn.setProperty("style-role", "action")     # mavi primary
btn.setProperty("style-role", "secondary")  # gri
btn.setProperty("style-role", "danger")     # kırmızı
btn.setProperty("style-role", "success")    # yeşil
btn.setProperty("style-role", "refresh")    # yenile
```

### 5.3 style-role (QLabel)

```python
lbl.setProperty("style-role", "title")
lbl.setProperty("style-role", "section")
lbl.setProperty("style-role", "section-title")
lbl.setProperty("style-role", "form")
lbl.setProperty("style-role", "value")
lbl.setProperty("style-role", "footer")
lbl.setProperty("style-role", "required")
lbl.setProperty("style-role", "stat-value")
lbl.setProperty("style-role", "stat-label")
lbl.setProperty("style-role", "stat-green")
lbl.setProperty("style-role", "stat-red")
lbl.setProperty("style-role", "stat-highlight")
```

### 5.4 Icon sistemi

```python
from ui.styles.icons import Icons, IconRenderer, IconColors

# Butona ikon
btn = QPushButton("Kaydet")
IconRenderer.set_button_icon(btn, "save", color=IconColors.PRIMARY, size=14)

# Label'a ikon
lbl = QLabel()
IconRenderer.set_label_icon(lbl, "users", size=20, color=IconColors.PRIMARY)

# QIcon (menü / action)
icon = Icons.get("calendar", size=16, color="#8b8fa3")

# Mevcut ikonlar
Icons.available()
```

`IconColors`: `PRIMARY`, `DANGER`, `SUCCESS`, `WARNING`, `MUTED`, `TEXT`, `EXCEL`, `PDF`, `NOTIFICATION`, `SYNC`

### 5.5 Ayarlar (AppConfig + settings.py)

```python
from core import settings
from core.config import AppConfig

# Okuma
settings.get("theme", "dark")         # "dark" | "light"
settings.get("app_mode", "offline")   # "online" | "offline"
settings.get("auto_sync", False)      # bool

# Yazma (ayarlar.json'a kaydeder)
settings.set("theme", "light")
AppConfig.set_app_mode("online", persist=True)
AppConfig.set_auto_sync(True, persist=True)
AppConfig.is_online_mode()
AppConfig.get_auto_sync()
```

---

## 6. TEST YAZMA

```python
# tests/services/test_xxx_service.py
import pytest
from unittest.mock import MagicMock
from core.services.xxx_service import XxxService


@pytest.fixture
def reg():
    return MagicMock()

@pytest.fixture
def svc(reg):
    return XxxService(reg)


class TestInit:
    def test_none_registry_hata_firlatar(self):
        with pytest.raises(ValueError):
            XxxService(None)


class TestGetListesi:
    def test_bos_liste(self, svc, reg):
        reg.get.return_value.get_all.return_value = []
        assert svc.get_listesi() == []

    def test_filtre_calisir(self, svc, reg):
        reg.get.return_value.get_all.return_value = [
            {"Pk": "1", "Alan": "A"},
            {"Pk": "2", "Alan": "B"},
        ]
        assert len(svc.get_listesi(filtre_id="A")) == 1

    def test_repo_hatasi_bos_doner(self, svc, reg):
        reg.get.return_value.get_all.side_effect = Exception("DB hatası")
        assert svc.get_listesi() == []


class TestKaydet:
    def test_insert(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        assert svc.kaydet({"Alan": "deger"}) is True
        mock_repo.insert.assert_called_once()

    def test_update_pk_yoksa_false(self, svc, reg):
        assert svc.kaydet({}, guncelle=True) is False

    def test_db_hatasi_false_doner(self, svc, reg):
        reg.get.return_value.insert.side_effect = Exception("Hata")
        assert svc.kaydet({"Alan": "deger"}) is False
```

```bash
pip install pytest
pytest tests/ -v
```

---

## 7. TÜRKÇE METİN VE VALİDASYON

```python
from core.text_utils import turkish_title_case, turkish_upper, turkish_lower
from core.validators import validate_tc_kimlik_no, validate_email, validate_not_empty
from ui.components.formatted_widgets import (
    apply_title_case_formatting,
    apply_numeric_only,
    apply_phone_number_formatting,
    apply_combo_title_case_formatting,
)

# QLineEdit otomatik formatlama
apply_title_case_formatting(self.txt_ad_soyad)
apply_numeric_only(self.txt_tc); self.txt_tc.setMaxLength(11)
apply_phone_number_formatting(self.txt_tel)

# Kaydetme validasyonu
if not validate_tc_kimlik_no(self.txt_tc.text().strip()):
    QMessageBox.warning(self, "Uyarı", "Geçersiz TC Kimlik No!")
    return
```

---

## 8. LINT & KALİTE KONTROL

```bash
# Commit öncesi çalıştır
python scripts/lint_theme.py

# Tek dosya syntax
python -m py_compile ui/pages/xxx/xxx.py

# Tüm dosyalar toplu
python -c "
import py_compile, os
for r,d,fs in os.walk('.'):
    d[:] = [x for x in d if '__pycache__' not in x]
    for f in fs:
        if f.endswith('.py'):
            py_compile.compile(os.path.join(r,f), doraise=True)
print('Tüm dosyalar temiz')
"
```

**Pre-commit hook (`.git/hooks/pre-commit`):**
```bash
#!/bin/sh
python scripts/lint_theme.py || exit 1
```

---

## 9. MEVCUT DOSYAYA GİRERKEN KONTROL LİSTESİ

```
[ ] setStyleSheet(f"...") var mı?          → setProperty("color-role", "...")
[ ] _DURUM_COLOR lokal dict var mı?        → self.status_fg() kullan, dict sil
[ ] def set_rows(self, rows): ... var mı?  → sil (BaseTableModel'de var)
[ ] to_ui_date import var mı (model içinde)?  → DATE_KEYS veya _fmt_date kullan
[ ] get_registry() direkt çağrı var mı?    → get_xxx_service(db) kullan
[ ] QAbstractTableModel'den türeyen model? → BaseTableModel kullan
[ ] Lokal _C = {...} renk dict var mı?     → from ui.styles.colors import DarkTheme as C
[ ] STYLES["key"] var mı?                  → setProperty("style-role", "...")
[ ] Lokal RAW_ROW_ROLE tanımı var mı?      → sil, BaseTableModel.RAW_ROW_ROLE kullan
```

---

*Bu rehber REPYS v3 — Aşama 0–6 refactor sonrası durumu yansıtır (Mart 2026).*  
*Sonraki büyük adım: DI tamamlama + Personel/RKE servis bağlantısı + Testler.*

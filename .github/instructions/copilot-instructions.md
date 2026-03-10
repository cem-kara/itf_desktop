# REPYS — Geliştirici Bağlam Yönergesi
> **VSCode bağlam dosyası.** Bu dosyayı her oturumda bağlam olarak ekle.
> Güncelleme: Mart 2026 — Kod tabanı zip analizi ile doğrulandı.

---

## PROJE

**REPYS** — Radyoloji bölümü masaüstü uygulaması (PySide6 + SQLite3 + Google Sheets)  
Giriş: `main.pyw` | Python 3.12 | Lint: `python scripts/lint_theme.py`

---

## MİMARİ — KATMAN KURALI

```
UI (ui/pages/)  →  Servis (core/services/)  →  Repository (database/)  →  SQLite
```

- UI **sadece** `core/di.py`'deki fabrika fonksiyonlarını kullanır
- Servisler `self._r.get("TABLO")` ile repo'ya erişir
- UI asla `get_registry()` veya `repo.get()` çağırmaz

**Doğru bağlantı kalıbı:**
```python
# UI __init__
from core.di import get_izin_service
self._svc = get_izin_service(db) if db else None

# Her metodda
def _on_save(self):
    if not self._svc:
        return
    self._svc.insert_izin_giris(kayit)
```

---

## DOSYA HARİTASI

```
REPYS/
│
├── main.pyw                     ← Giriş, log yönetimi, migration, auth akışı
│
├── core/
│   ├── config.py                ← AppConfig: app_mode, auto_sync, log ayarları
│   ├── settings.py              ← ayarlar.json okuma/yazma (get/set)
│   ├── paths.py                 ← BASE_DIR, LOG_DIR, DATA_DIR, TEMP_DIR
│   ├── di.py                    ← 15 DI fabrikası — buradan import et
│   ├── date_utils.py            ← parse_date, to_db_date, to_ui_date
│   ├── validators.py            ← TC, email, telefon, boş alan validasyonu
│   ├── text_utils.py            ← turkish_title_case, turkish_upper/lower
│   ├── logger.py                ← Çoklu handler, structured formatter
│   ├── log_manager.py           ← Log cleanup ve health check
│   ├── auth/
│   │   ├── auth_service.py      ← Giriş/çıkış, şifre değiştirme
│   │   ├── authorization_service.py  ← Yetki kontrol (RBAC)
│   │   ├── password_hasher.py   ← bcrypt hash
│   │   └── session_context.py   ← Aktif kullanıcı bilgisi
│   └── services/                ← TÜM iş mantığı (UI buraya erişir)
│       ├── cihaz_service.py         → CihazService
│       ├── personel_service.py      → PersonelService
│       ├── rke_service.py           → RkeService
│       ├── saglik_service.py        → SaglikService
│       ├── fhsz_service.py          → FhszService
│       ├── izin_service.py          → IzinService
│       ├── ariza_service.py         → ArizaService
│       ├── bakim_service.py         → BakimService
│       ├── kalibrasyon_service.py   → KalibrasyonService
│       ├── dashboard_service.py     → DashboardService
│       ├── dokuman_service.py       → DokumanService
│       ├── backup_service.py        → BackupService
│       ├── log_service.py           → LogService
│       ├── settings_service.py      → SettingsService
│       └── file_sync_service.py     → FileSyncService
│
├── database/
│   ├── sqlite_manager.py        ← Bağlantı, execute/executemany
│   ├── base_repository.py       ← insert, update, get_by_id, get_by_pk, get_all,
│   │                               get_by_kod, get_where, get_dirty, delete, mark_clean
│   ├── repository_registry.py   ← Tablo adı → repo eşlemesi (singleton)
│   ├── table_config.py          ← Tablo şemaları, PK'lar, sync ayarları — buradan kopyala
│   ├── migrations.py            ← CURRENT_VERSION = 1
│   ├── cloud_adapter.py         ← Online/offline adaptör
│   ├── gsheet_manager.py        ← Google Sheets batch okuma/yazma
│   ├── sync_service.py          ← Push/pull akışı
│   ├── sync_worker.py           ← QThread tabanlı sync
│   └── repositories/            ← Özel sorgular (BaseRepository extend eder)
│       ├── personel_repository.py   → PersonelRepository
│       ├── cihaz_repository.py      → CihazRepository
│       ├── rke_repository.py        → RKERepository
│       ├── cihaz_teknik_repository.py
│       ├── cihaz_teknik_belge_repository.py
│       ├── cihaz_belgeler_repository.py
│       └── dokumanlar_repository.py
│
└── ui/
    ├── theme_template.qss       ← Tüm renkler token tabanlı
    ├── theme_manager.py         ← ThemeManager.instance()
    ├── main_window.py           ← Ana pencere
    ├── sidebar.py               ← Menü
    ├── styles/
    │   ├── colors.py            ← DarkTheme / C alias
    │   ├── themes.py            ← DARK / LIGHT token dict
    │   ├── components.py        ← STYLES dict (KULLANIMI YASAK — yalnızca okunabilir)
    │   └── icons.py             ← Icons, IconRenderer, IconColors
    ├── components/
    │   ├── base_table_model.py  ← Tüm model sınıflarının ebeveyni
    │   └── formatted_widgets.py ← apply_title_case_formatting vb.
    ├── dialogs/
    │   ├── mesaj_kutusu.py      ← Merkezi dialog — bilgi/uyarı/hata/soru
    │   └── about_dialog.py      ← HakkindaDialog (LGPL bildirimi içerir)
    ├── pages/
    │   ├── dashboard.py
    │   ├── cihaz/
    │   ├── personel/
    │   ├── rke/
    │   └── placeholder.py
    └── admin/
        ├── admin_panel.py
        ├── settings_page.py
        ├── backup_page.py
        └── yil_sonu_devir_page.py
```

---

## TABLO VE PK REFERANSI

> **Kural:** Tablo adını ve PK'yı `database/table_config.py`'den kopyala, asla tahmin etme.

| Tablo | PK | Sync |
|---|---|---|
| `Personel` | `KimlikNo` | ✓ |
| `Izin_Giris` | `Izinid` | ✓ |
| `Izin_Bilgi` | `TCKimlik` | ✗ |
| `Cihazlar` | `Cihazid` | ✓ |
| `Cihaz_Ariza` | `Arizaid` | ✓ |
| `Ariza_Islem` | `Islemid` | ✓ |
| `Periyodik_Bakim` | `Planid` | ✓ |
| `Kalibrasyon` | `Kalid` | ✓ |
| `Sabitler` | `Rowid` | ✓ |
| `Personel_Saglik_Takip` | `KayitNo` | ✓ |
| `RKE_Muayene` | `KayitNo` | ✓ |
| `RKE_List` | `EkipmanNo` | ✓ |
| `FHSZ_Puantaj` | `["Personelid","AitYil","Donem"]` | ✗ |

---

## DI FABRİKALARI

```python
from core.di import (
    get_cihaz_service, get_rke_service, get_saglik_service,
    get_fhsz_service, get_personel_service, get_dashboard_service,
    get_izin_service, get_ariza_service, get_bakim_service,
    get_kalibrasyon_service, get_dokuman_service, get_backup_service,
    get_log_service, get_settings_service, get_file_sync_service,
)
```

**Yeni servis eklerken** `core/di.py`'ye şu kalıbı ekle:
```python
def get_xxx_service(db):
    from core.services.xxx_service import XxxService
    return XxxService(get_registry(db))
```

---

## REPOSITORY API

```python
repo = self._r.get("TABLO_ADI")

repo.get_all()                          # list[dict]
repo.get_by_id(pk)                      # dict | None
repo.get_by_pk(pk)                      # dict | None  (alias)
repo.get_where({"Kolon": "Deger"})      # list[dict]
repo.get_by_kod("Deger", kolum="Kolon") # list[dict]
repo.get_dirty()                        # list[dict]  sync_status='dirty'
repo.insert(veri_dict)
repo.update(pk, veri_dict)
repo.delete(pk)                         # bool
repo.mark_clean(pk)
```

**Composite PK (FHSZ_Puantaj):**
```python
repo.get_by_id(("TC123", "2025", "1"))  # tuple geç
```

---

## SERVIS ŞABLONU

```python
# core/services/xxx_service.py
from typing import Optional
from core.logger import logger
from database.repository_registry import RepositoryRegistry

class XxxService:
    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("Registry boş olamaz")
        self._r = registry

    def get_listesi(self, filtre_id: Optional[str] = None) -> list[dict]:
        try:
            if filtre_id:
                return self._r.get("TABLO").get_where({"FK": filtre_id})
            return self._r.get("TABLO").get_all() or []
        except Exception as e:
            logger.error(f"XxxService.get_listesi: {e}")
            return []

    def kaydet(self, veri: dict, guncelle: bool = False) -> bool:
        try:
            repo = self._r.get("TABLO")
            pk = veri.get("PK_ADI")
            if guncelle:
                if not pk:
                    return False
                repo.update(pk, veri)
            else:
                repo.insert(veri)
            return True
        except Exception as e:
            logger.error(f"XxxService.kaydet: {e}")
            return False

    def sil(self, pk: str) -> bool:
        try:
            return self._r.get("TABLO").delete(pk)
        except Exception as e:
            logger.error(f"XxxService.sil: {e}")
            return False
```

---

## UI SAYFASI ŞABLONU

```python
# ui/pages/xxx/xxx_page.py
from PySide6.QtWidgets import QWidget, QVBoxLayout
from core.di import get_xxx_service
from core.logger import logger

class XxxPage(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db  = db
        self._svc = get_xxx_service(db) if db else None
        self._setup_ui()
        self._load_data()

    def _load_data(self):
        if not self._svc:
            return
        try:
            self._model.set_data(self._svc.get_listesi())
        except Exception as e:
            logger.error(f"XxxPage yükleme: {e}")

    def _on_save(self):
        if not self._svc:
            return
        # ... kaydet
        self._load_data()
```

---

## SIDEBAR MENU EKLEME

**Kaynak:** `ayarlar.json` -> `menu_yapilandirma`

**Menu item formati (gercek yapidan):**
```json
{
  "baslik": "Personel Listesi",
  "implemented": true,
  "icon": "users"
}
```

**Zorunlu alan:** `baslik`
**Opsiyonel alanlar:** `implemented`, `icon`, `note`

**Notlar:**
- `ui/sidebar.py` `menu_yapilandirma` listesini okur ve `baslik` ile buton uretir.
- `icon` anahtari `ui/styles/icons.py` icindeki `Icons.available()` veya `MENU_ICON_MAP` ile eslesir.
- `baslik` stringi 3 yerde birebir ayni olmalidir:
  - `ayarlar.json` menu girdisi
  - `ui/main_window.py` icindeki `_create_page` kosulu
  - `ui/permissions/page_permissions.py` icindeki `PAGE_PERMISSIONS`

**MainWindow ekran baglantisi (sidebar entegrasyonu):**
1) `ayarlar.json` icine yeni `baslik` ekle.
2) `ui/permissions/page_permissions.py` icinde ayni basliga permission map ekle.
3) `ui/main_window.py` icinde `_create_page()` icine yeni blok ekle:
```python
if baslik == "Xxx Sayfasi":
    from ui.pages.xxx.xxx_page import XxxPage
    page = XxxPage(db=self._db, action_guard=self._action_guard)
    # gerekiyorsa sinyal bagla ve load_data cagir
    return page
```
4) Sayfayi programatik aciyorsan `self._on_menu_clicked("GRUP", "Xxx Sayfasi")` kullan.
5) Geri donuslerde aktif menu icin `self.sidebar.set_active("Xxx Sayfasi")` cagir.

---

## TABLE MODEL ŞABLONU

```python
from PySide6.QtCore import Qt
from ui.components.base_table_model import BaseTableModel

XXX_COLUMNS = [
    ("DbAlani",  "Başlık",   150),   # (db_key, header, genişlik_px)
    ("Tarih",    "Tarih",     90),
    ("Durum",    "Durum",     80),
    ("Aciklama", "Açıklama",   0),   # 0 → stretch
]

class XxxModel(BaseTableModel):
    DATE_KEYS    = frozenset({"Tarih"})
    ALIGN_CENTER = frozenset({"Durum", "Tarih"})

    def __init__(self, rows=None, parent=None):
        super().__init__(XXX_COLUMNS, rows, parent)

    def _fg(self, key, row):
        if key == "Durum":
            return self.status_fg(row.get("Durum", ""))  # ← status_fg, _status_fg DEĞİL
        return None

    def _bg(self, key, row):
        if key == "Durum":
            return self.status_bg(row.get("Durum", ""))
        return None
```

**BaseTableModel tam API:**
```python
model.set_data(rows)                # veri yükle + reset
model.get_row(idx)                  # int → dict | None
model.setup_columns(view)           # kolon genişlikleri, son kolon stretch
index.data(model.RAW_ROW_ROLE)      # → dict (seçili satır)
model._fmt_date(val)                # "YYYY-MM-DD" → "GG.AA.YYYY"
model.status_fg(durum)              # → QColor | None
model.status_bg(durum)             # → QColor | None
```

**Durum renkleri:**
| Durum | Renk |
|---|---|
| Aktif, Tamamlandı, Onaylandı, Uygun | 🟢 Yeşil |
| Açık, Pasif, Geçersiz, Uygun Değil | 🔴 Kırmızı |
| Beklemede, Planlandı, İşlemde, İzinli | 🟡 Sarı |
| İptal | ⚪ Gri |

---

## YENI TABLO EKLEME

**1) Schema tanimi**
`database/table_config.py` icine tablo sozlugu ekle.
- `pk`: tek kolon string ya da composite icin `[]`
- `columns`: kolon listesi
- `date_fields`: UI tarih formatlama icin
- `sync`: `False` ise local-only (sync edilmez)
- `sync_mode`: `"pull_only"` ise sadece uzak kaynaktan cekilir

**2) Migration (mevcut DB icin sart)**
`database/migrations.py` icinde:
- `CURRENT_VERSION` artir (orn. `2`)
- `_migrate_to_v2()` fonksiyonu ekle
- yeni tablo icin `CREATE TABLE` yaz

**3) Yeni kurulumlar**
`create_tables()` icine de ayni `CREATE TABLE` ekle (fresh install icin).

**Kritik notlar:**
- Sync edilecek tabloda `sync_status` ve `updated_at` kolonlari olmalidir.
- `pk` `None` ise sync disi kabul edilir.
- Ozel repository gerekiyorsa `database/repositories/` altinda olustur ve
  `database/repository_registry.py` icinde kaydet.

---

## TEMA SİSTEMİ

**Renk için `setStyleSheet` YAZMA — `setProperty` kullan:**
```python
# ❌
label.setStyleSheet(f"color: {C.TEXT_PRIMARY};")

# ✅
label.setProperty("color-role", "primary")
```

**color-role değerleri (QLabel, QWidget):**
```
primary | secondary | muted | disabled | accent | accent2
ok | warn | err | info
```

**style-role değerleri (QPushButton):**
```
action | secondary | danger | success | refresh
```

**style-role değerleri (QLabel):**
```
title | section | section-title | form | value | footer | required
stat-value | stat-label | stat-green | stat-red | stat-highlight
```

**İkon sistemi:**
```python
from ui.styles.icons import IconRenderer, IconColors

IconRenderer.set_button_icon(btn, "save", color=IconColors.PRIMARY, size=14)
IconRenderer.set_label_icon(lbl, "users", size=20, color=IconColors.PRIMARY)
```

**QTabWidget stili QSS'de global tanımlı — `setStyleSheet` GEREKMİYOR:**
```python
# ❌  — kaldır
self.tab_widget.setStyleSheet(STYLES.get("tab", ""))
# ✅  — yeterli
self.tab_widget = QTabWidget()
```

---

## YETKI (RBAC) SISTEMI

**1) Permission kaydi**
- Yeni permission anahtari icin `database/migrations.py` -> `_seed_auth_data()` listesine ekle.
- Ayr�ca `core/auth/permission_keys.py` sabitlerini guncelle (opsiyonel ama tavsiye).
- Mevcut kurulumlarda admin ekranindan ekleme icin `ui/admin/permissions_view.py` kullanilir.

**2) Sayfa (page-level) izinleri**
- `ui/permissions/page_permissions.py` icinde `PAGE_PERMISSIONS` map'ine ekle.
- (Varsa) `core/auth/permission_map.py` ile senkron tut.

**3) Kontrol noktasi (ActionGuard/PageGuard)**
- `PageGuard`: sayfa acilisinda kullanilir (MainWindow zaten uygular).
- `ActionGuard`: buton/aksiyon bazli kontrol icin:
```python
# sayfa icinde
if self._action_guard:
    self._action_guard.disable_if_unauthorized(self.btn_sil, "personel.write")
```

**4) MainWindow entegrasyonu**
- Sidebar secimi `baslik` -> `PAGE_PERMISSIONS` -> `PageGuard` zinciri ile filtrelenir.
- Yetki yoksa `MainWindow._on_menu_clicked` uyarir ve sayfayi acmaz.

**Kural:**
- Yeni ekran = yeni permission
- Permission stringleri `modul.aksiyon` formatinda (orn: `personel.read`)

---

## DIALOG SİSTEMİ

**QMessageBox kullanma — MesajKutusu kullan:**
```python
from ui.dialogs.mesaj_kutusu import MesajKutusu

MesajKutusu.bilgi(self, "Kayıt eklendi.")
MesajKutusu.uyari(self, "Alan boş olamaz.")
MesajKutusu.hata(self, "Bağlantı hatası.")
onay = MesajKutusu.soru(self, "Silmek istiyor musunuz?")
if onay:
    ...
```

---

## YARDIMCI MODÜLLER

```python
# Tarih
from core.date_utils import parse_date, to_db_date, to_ui_date
parse_date("15.03.2025")   # → date(2025,3,15)
to_db_date("15.03.2025")   # → "2025-03-15"   (DB'ye kaydetmek için)
to_ui_date("2025-03-15")   # → "15.03.2025"   (ekranda göstermek için)
# NOT: Model içinde to_ui_date kullanma — DATE_KEYS veya _fmt_date kullan

# Validasyon
from core.validators import validate_tc_kimlik_no, validate_not_empty, validate_email

# Türkçe metin
from core.text_utils import turkish_title_case, turkish_upper, turkish_lower

# Widget formatlama
from ui.components.formatted_widgets import (
    apply_title_case_formatting,   # Ad, soyad → lineEdit'e uygula
    apply_numeric_only,            # Sadece rakam
    apply_phone_number_formatting,
)

# Ayarlar
from core import settings
from core.config import AppConfig
settings.get("theme", "dark")
AppConfig.is_online_mode()
```

---

## PYSIDE6 ENUM KURALI

PySide6 6.x'te enum'lara kısa erişim çalışır ama type-checker uyarısı verir.
Enum grubunu her zaman açıkça belirt:

| ❌ Eski (uyarı) | ✅ Doğru |
|---|---|
| `QPropertyAnimation.DeleteWhenStopped` | `QAbstractAnimation.DeletionPolicy.DeleteWhenStopped` |
| `QEasingCurve.OutCubic` | `QEasingCurve.Type.OutCubic` |
| `QAbstractSpinBox.NoButtons` | `QAbstractSpinBox.ButtonSymbols.NoButtons` |
| `Qt.AlignLeft/Center/Right` | `Qt.AlignmentFlag.AlignLeft` vb. |
| `Qt.PointingHandCursor` | `Qt.CursorShape.PointingHandCursor` |
| `Qt.Dialog / Qt.Window` | `Qt.WindowType.Dialog` vb. |
| `QHeaderView.ResizeToContents` | `QHeaderView.ResizeMode.ResizeToContents` |
| `QHeaderView.Stretch` | `QHeaderView.ResizeMode.Stretch` |
| `QSizePolicy.Expanding` | `QSizePolicy.Policy.Expanding` |
| `QFrame.StyledPanel / HLine` | `QFrame.Shape.StyledPanel` vb. |
| `QFrame.Raised / Sunken` | `QFrame.Shadow.Raised` vb. |
| `QAbstractItemView.SelectRows` | `QAbstractItemView.SelectionBehavior.SelectRows` |
| `QAbstractItemView.SingleSelection` | `QAbstractItemView.SelectionMode.SingleSelection` |
| `QAbstractItemView.ScrollPerPixel` | `QAbstractItemView.ScrollMode.ScrollPerPixel` |

---

## TEKRAR EDEN HATA KALIPLARI

### 1. `self._svc` None guard eksik
```python
# ❌  — db=None ile crash
self._svc.insert(veri)

# ✅
if not self._svc:
    return
self._svc.insert(veri)
```

### 2. Metod içinde yeni servis nesnesi
```python
# ❌  — gereksiz, her çağrıda yeni nesne
def _load(self):
    svc = get_izin_service(self._db)

# ✅  — __init__'te kurulan self._svc kullan
def _load(self):
    if not self._svc:
        return
    self._svc.get_listesi()
```

### 3. `registry` tanımsız (TODO-3 kalıntısı)
```python
# ❌  — kısmen refactor, registry scope'ta tanımsız
sabitler = registry.get("Sabitler").get_all()

# ✅  — servise metod ekle, ondan çağır
sabitler = self._svc.get_sabitler_raw() if self._svc else []
```

### 4. `toPython()` cast eksik
```python
# ❌  — Pylance "object" görür
baslama = self.dt_baslama.date().toPython()

# ✅
from typing import cast
from datetime import date
baslama: date = cast(date, self.dt_baslama.date().toPython())
```

### 5. `lineEdit()` None guard eksik
```python
# ❌  — editable değilse crash
self.cmb.lineEdit().setPlaceholderText("Ara...")

# ✅
if _le := self.cmb.lineEdit():
    _le.setPlaceholderText("Ara...")
```

### 6. `status_fg` yerine `_status_fg` (BaseTableModel)
```python
# ❌  — metod yok, underscore yanlış
return self._status_fg(row.get("Durum", ""))

# ✅  — public API underscore'suz
return self.status_fg(row.get("Durum", ""))
```

### 7. Servis metod adı tahmini
```python
# ❌  — PersonelService'de get_all() yok
personel_svc.get_all()

# ✅  — önce core/services/personel_service.py'deki def satırlarına bak
personel_svc.get_personel_listesi()
```

---

## MEVCUT AÇIK TODO'LAR (Mart 2026)

| # | Dosya | Satır | Yapılacak |
|---|---|---|---|
| TODO-6 | Tüm UI | — | ✅ `setStyleSheet(f-string)` kalan: 0 (tamamlandı — Mart 2026) |
| TODO-8 | `tests/services/` | — | Test klasörü henüz yok |

---

## DOSYAYA GİRERKEN KONTROL LİSTESİ

```
TEMA (bkz. "TEMA SİSTEMİ — KESİN KURALLAR" bölümü)
[ ] setStyleSheet(f"...") var mı?            → setProperty("style-role", ...) kullan, YASAK
[ ] setStyleSheet("QPushButton{...}") var mı?→ setProperty("style-role", ...) kullan, YASAK
[ ] STYLES["key"] / S["key"] var mı?         → setProperty("style-role", ...) + S import sil
[ ] DarkTheme.XXX inline kullanımı var mı?   → setProperty("color-role"/"bg-role", ...) kullan
[ ] QTabWidget'e setStyleSheet var mı?        → satırı sil (QSS global)

MODEL
[ ] _DURUM_COLOR lokal dict var mı?     → status_fg/status_bg kullan, dict sil
[ ] def set_rows() var mı?              → sil (BaseTableModel'de var)
[ ] to_ui_date import (model içinde)?   → DATE_KEYS veya _fmt_date kullan
[ ] RAW_ROW_ROLE lokal tanım var mı?    → sil, model.RAW_ROW_ROLE kullan
[ ] _status_fg() çağrısı var mı?        → status_fg() yap

SERVİS / VERİ
[ ] get_registry() UI içinde var mı?    → get_xxx_service(db) kullan
[ ] self._svc None guard eksik mi?      → if not self._svc: return ekle
[ ] Metod içinde yeni svc nesnesi var mı? → self._svc kullan
[ ] get_all() + Python filter var mı?   → get_where() kullan

ENUM
[ ] Qt.AlignXxx kısa erişim var mı?     → Qt.AlignmentFlag.AlignXxx
[ ] QPropertyAnimation.DeleteWhen... ?  → QAbstractAnimation.DeletionPolicy...
[ ] QHeaderView.Stretch/ResizeTo...?    → QHeaderView.ResizeMode...
[ ] QSizePolicy.Expanding vb.?          → QSizePolicy.Policy...
[ ] QFrame.StyledPanel/HLine vb.?       → QFrame.Shape/Shadow...
```

---

## TEMA SİSTEMİ — KESİN KURALLAR

> ⛔ Bu bölüm **değiştirilemez kurallar** içerir. Aşağıdaki yasaklar hiçbir gerekçeyle esnetilemez.

### Stil Mimarisi

Projede **tek stil kaynağı** `ui/theme_template.qss` dosyasıdır.  
Python kodunda renk veya stil string'i **asla** üretilmez.

```
theme_template.qss   ← TEK YER — tüm renkler, boyutlar, durum stilleri burada
ThemeManager         ← QApplication.setStyleSheet() ile uygular
setProperty()        ← Python tarafı SADECE bunu kullanır
```

### ⛔ KESİN YASAKLAR

Aşağıdaki kalıpların **tamamı yasaktır.** Yeni kodda yazma, mevcut kodda görürsen düzelt.

```python
# ❌ YASAK 1 — f-string ile setStyleSheet
btn.setStyleSheet(f"QPushButton{{background:{DarkTheme.ACCENT};}}")

# ❌ YASAK 2 — .format() ile setStyleSheet (QPushButton/QLabel için)
btn.setStyleSheet("QPushButton{{background:{};}}".format(renk))

# ❌ YASAK 3 — STYLES dict / S.get() ile setStyleSheet
btn.setStyleSheet(S.get("btn_action"))
btn.setStyleSheet(STYLES.get("btn_secondary", ""))

# ❌ YASAK 4 — Ham renk kodu
btn.setStyleSheet("QPushButton { background: #0ea5e9; }")

# ❌ YASAK 5 — DarkTheme / C import ile inline stil
lbl.setStyleSheet(f"color: {C.TEXT_MUTED}; font-size: 12px;")
```

### ✅ DOĞRU KULLANIM

```python
# Butona stil ver → setProperty("style-role", "ROL_ADI")
btn.setProperty("style-role", "action")

# Etikete renk ver → setProperty("color-role", "ROL_ADI")
lbl.setProperty("color-role", "muted")

# Widget arka planı → setProperty("bg-role", "ROL_ADI")
panel.setProperty("bg-role", "panel")

# ÖNEMLİ: setProperty sonrası Qt cache'ini temizle (runtime değişimde)
btn.style().unpolish(btn)
btn.style().polish(btn)
```

### style-role Referans Tablosu (QPushButton / QLabel)

| role | Widget | Görünüm / Kullanım |
|---|---|---|
| `action` | QPushButton | Mavi dolu — ana işlem (Kaydet, Ekle, Onayla) |
| `secondary` | QPushButton | Şeffaf + kenarlık — ikincil işlem (Düzenle, Geri) |
| `success-filled` | QPushButton | Yeşil dolu — kesin kayıt (✓ KAYDET, ✓ BAŞLAT) |
| `warning` | QPushButton | Turuncu dolu — güncelleme/uyarı (↑ GÜNCELLE) |
| `danger` | QPushButton | Kırmızı hover — silme/iptal |
| `refresh` | QPushButton | Şeffaf + kenarlık — yenile ikonu ile |
| `upload` | QPushButton | BG_SECONDARY + kenarlık — dosya seç/yükle |
| `close` | QPushButton | Şeffaf, 22×22 — ✕ kapat butonu |
| `quick-action` | QPushButton | Sol hizalı, yuvarlak — panel hızlı işlem |
| `tab-active` | QPushButton | Mavi kenarlık-alt — aktif sekme |
| `tab-inactive` | QPushButton | Şeffaf — pasif sekme |
| `success` | QPushButton | Yeşil outline hover |
| `form` | QLabel | Form alan etiketi (gri, 12px) |
| `title` | QLabel | Büyük başlık |
| `section` | QLabel | Bölüm başlığı (büyük harf, tracking) |
| `section-title` | QLabel | Alt bölüm başlığı |
| `info` | QLabel | Bilgi etiketi (muted, 11px) |
| `footer` | QLabel | Alt bilgi / sayfalama (muted, 11px) |
| `header-name` | QLabel | Personel/cihaz adı başlığı |
| `required` | QLabel | Zorunlu alan yıldızı (*) |
| `stat-label` | QLabel | İstatistik etiketi (muted, 10px) |
| `stat-value` | QLabel | İstatistik değeri (büyük, bold) |
| `stat-red` | QLabel | Kırmızı istatistik değeri |
| `stat-green` | QLabel | Yeşil istatistik değeri |
| `stat-highlight` | QLabel | Vurgulu istatistik (accent renk) |
| `value` | QLabel | Tek değer gösterimi |
| `donem` | QLabel | Dönem/periyot etiketi |
| `plain` | QScrollArea | Sade scroll area (transparent, border yok) |

### color-role Referans Tablosu (renk tonu)

| role | Renk |
|---|---|
| `primary` | TEXT_PRIMARY |
| `secondary` | TEXT_SECONDARY |
| `muted` | TEXT_MUTED (gri açıklama) |
| `disabled` | TEXT_DISABLED |
| `accent` | ACCENT (mavi) |
| `accent2` | ACCENT2 |
| `ok` | STATUS_SUCCESS (yeşil) |
| `warn` | STATUS_WARNING (turuncu) |
| `err` | STATUS_ERROR (kırmızı) |
| `info` | STATUS_INFO (mavi) |

```python
# Kullanım: renk tonu vermek için
lbl.setProperty("color-role", "muted")    # gri açıklama
lbl.setProperty("color-role", "ok")       # yeşil başarı
lbl.setProperty("color-role", "err")      # kırmızı hata
lbl.setProperty("color-role", "warn")     # turuncu uyarı
```

### bg-role Referans Tablosu (arka plan)

| role | Arka Plan |
|---|---|
| `page` | BG_PRIMARY (sayfa) |
| `panel` | BG_SECONDARY (panel/kart) |
| `elevated` | BG_ELEVATED (üst katman) |
| `hover` | BG_TERTIARY (hover/seçili) |
| `input` | INPUT_BG (input alanı) |
| `separator` | BORDER_PRIMARY — 1px çizgi (max-height:1px) |
| `separator-secondary` | BORDER_SECONDARY — ince çizgi |
| `accent` | ACCENT (vurgulu arka plan) |
| `transparent` | Şeffaf + kenarsız |

### Yeni QSS Rolü Ekleme Kuralı

Yukarıdaki tablolarda olmayan bir stil gerekirse:

1. `ui/theme_template.qss` dosyasına ekle (dosyanın sonuna, `/* EK BUTON ROLLERİ */` bölümüne)
2. Python kodunda `setProperty("style-role", "yeni-rol")` kullan
3. Bu bölümdeki tabloya satır ekle

**Python koduna kesinlikle renk kodu veya stil string'i yazma.**

### İstisna: Gerçekten Dinamik Renkler

Sadece runtime'da hesaplanan renkler (örn. durum badge'i: `rgba(r,g,b,a)`) doğrudan
`setStyleSheet()` kullanabilir — ama **bu durumda `{{` ve `}}` ile escape zorunludur:**

```python
# ✅ İZİN VERİLEN TEK İSTİSNA — dinamik hesaplanmış renk
btn.setStyleSheet(
    f"QPushButton {{ background: rgba({r},{g},{b},{a}); color: {text}; }}"
    f"QPushButton:hover {{ background: rgba({r},{g},{b},{min(a+30,255)}); }}"
)
# NOT: {{ ve }} QSS literal brace için zorunlu. Değişkenler direkt kullanılabilir.
```

---

## LINT VE KALİTE

```bash
# Commit öncesi zorunlu
python scripts/lint_theme.py

# Tek dosya
python -m py_compile ui/pages/xxx/xxx.py

# Tüm dosyalar
python -c "
import py_compile, os
for r,d,fs in os.walk('.'):
    d[:] = [x for x in d if '__pycache__' not in x]
    for f in fs:
        if f.endswith('.py'):
            try: py_compile.compile(os.path.join(r,f), doraise=True)
            except Exception as e: print(e)
print('Bitti')
"

# Proje durumu kontrol
python3 - << 'EOF'
import os, re
BASE = '.'
def r(fp): return open(fp, errors='ignore').read() if os.path.exists(fp) else ''
def walk(d):
    for root,dirs,files in os.walk(d):
        dirs[:] = [x for x in dirs if '__pycache__' not in x]
        for f in files:
            if f.endswith('.py'): yield os.path.join(root,f)
br = r('database/base_repository.py')
print(f"BaseRepo delete/get_by_pk : {'✅' if 'def delete' in br and 'def get_by_pk' in br else '❌'}")
di = r('core/di.py')
print(f"DI fabrika                : {len(re.findall(r'^def get_\\w+_service', di, re.M))}/15")
gr_p = sum(len(re.findall(r'get_registry\(', r(f))) for f in walk('ui/pages/personel'))
print(f"Personel get_registry     : {gr_p} {'✅' if gr_p==0 else '❌'}")
by_c = sum(len(re.findall(r'_r\.get\(', r(f))) for f in walk('ui/pages/cihaz'))
print(f"Cihaz _r bypass           : {by_c} {'✅' if by_c==0 else '❌'}")
ss   = sum(len(re.findall(r'setStyleSheet\s*\(\s*f', r(f))) for f in walk('ui'))
print(f"setStyleSheet(f-string)   : {ss} adet")
EOF
```

---

## DEĞİŞİKLİK LOGU

```
2026-03-05  Aşama 0-6 tamamlandı (tema, servisler, BaseTableModel, ikonlar)
2026-03-05  BaseRepository delete/get_by_pk eklendi
2026-03-05  DI 15 fabrika tamamlandı
2026-03-05  RKE UI + Cihaz UI servis katmanına bağlandı
2026-03-05  Personel UI 10/12 bitti (2 kaldı: personel_overview_panel x2)
2026-03-05  Sync pull-only transaction (BEGIN/ROLLBACK) eklendi
2026-03-05  migrations.py squash — CURRENT_VERSION=1
2026-03-05  MesajKutusu (native QMessageBox yerine)
2026-03-05  HakkindaDialog + LGPL/MIT attributions
2026-03-05  izin_takip.py — 16 Pylance hatası düzeltildi
2026-03-05  izin_service.py — 5 yeni metod eklendi
2026-03-07  setStyleSheet(f-string) 352 → 0 (TODO-6 tamamlandı)
2026-03-05  Tüm proje Pylance hatasız — 20+ type-checker hatası düzeltildi
2026-03-05  file_sync_service.py — Optional[list[dict]] cache type hints
2026-03-05  personel_service.py — reportRedeclaration (get_personel_repo duplicate)
2026-03-05  settings_service.py — Cursor None guards (2 metod)
2026-03-05  bildirim_servisi.py — Optional[str] db_path type hint
2026-03-05  hata_yonetici.py — QMessageBox override return types + ExceptHookArgs.exc_traceback
2026-03-05  logger.py — Dynamic attribute access with getattr()
2026-03-05  personel_ozet_servisi.py — Repository access + db/cursor guards (7 metod)
2026-03-05  cloud_adapter.py — Abstract method get_folder_id implementation (Online+Offline)
2026-03-05  sqlite_manager.py — execute() return type + lastrowid guards
2026-03-06  UI katmanı toplu Pylance temizliği — theme/colors/components + personel/cihaz/rke sayfalarında Optional guard, enum ve override düzeltmeleri; proje yeniden hatasız
2026-03-06  settings_service.add_tatil() — UNIQUE constraint önlemek için duplicate tarih kontrolü
2026-03-06  TODO-3 tamamlandı (get_registry → DI)
2026-03-06  TODO-6b tamamlandı (STYLES.get import temizleme)
2026-03-06  TODO-6c tamamlandı (QPropertyAnimation enum dosyası zaten doğru)
2026-03-06  TODO-7 tamamlandı (obselete dosyalar git rm ile silindi)
2026-03-06  CHANGELOG.md + .gitmessage + copilot-instructions.md v2 deployed
2026-03-06  İlk standardize commit: "refactor(core,ui,database): Achieve project-wide type-safety" (v0.3.0) 
2026-03-07  personel_ekle.py + base_dokuman_panel.py — kayıt sonrası belge yükleme akışı ve form reset (Yeni Personel) düzeltildi
2026-03-07  izin_service.py — yıllık hakediş/izin limit motoru + çakışma kontrolü + Izin_Bilgi None→0 normalize eklendi
2026-03-07  izin_takip.py + hizli_izin_giris.py — limit kuralı servis katmanından ortak kullanılacak şekilde standardize edildi
2026-03-07  izin_takip.py — açılış filtreleri (Ay/Yıl) Tümü varsayılanına alındı
2026-03-07  tests/test_izin_service.py — hakediş, limit, normalize, çakışma senaryoları eklendi (59 passed)
2026-03-07  README.md + CHANGELOG.md — v0.3.0 WIP dokümantasyon güncellendi
── İLERİ AGENDA: TODO-8 (test infrastructure) ──
```


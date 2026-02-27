# REPYS UI Mimarisi — Visual Harita

## 1. Genel Yapı

```
┌─────────────────────────────────────────────────────────────┐
│                        MainWindow                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                     Sidebar                           │  │
│  │  - Dashboard                                          │  │
│  │  - Cihaz Modülü    ┐                                  │  │
│  │  - Personel Modülü ├─ Page Guard + Action Guard      │  │
│  │  - RKE Modülü      │  (Permission filtering)         │  │
│  │  - Admin Modülü    ┘                                  │  │
│  │  - Sync Btn                                           │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │          BildirimPaneli (Notification)   ↓ (fixed)    │  │
│  │  ├─ Yeni Arıza                                        │  │
│  │  ├─ Yaklaşan Bakım                                    │  │
│  │  └─ ...                                               │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │                  QStackedWidget                       │  │
│  │  (Page container: StackedLayout)                      │  │
│  │                                                       │  │
│  │  Sayfa 1: DashboardPage     (616 satır)             │  │
│  │  Sayfa 2: CihazMerkezPage   (377 satır)             │  │
│  │  Sayfa 3: PersonelMerkezPage (483 satır)            │  │
│  │  Sayfa 4: RKEYönetimPage    (774 satır)             │  │
│  │  Sayfa 5: AdminPanel        (151 satır)             │  │
│  │                                                       │  │
│  └────────────────────────────────────────────────────────┘  │
│         ┌─────────────────────────────────────┐              │
│         │  Status Bar (Sync, Connection)  │  │              │
│         └─────────────────────────────────────┘              │
├─────────────────────────────────────────────────────────────┤
│               Authentication Layer (Login)                   │
│  - LoginDialog + ChangePasswordDialog                        │
│  - AuthService + AuthRepository                             │
│  - PermissionRepository                                     │
└─────────────────────────────────────────────────────────────┘
```

## 2. Cihaz Modülü Ağacı

```
CihazMerkezPage (377 satır) ← Main hub
├── QStackedWidget (tab navigation)
│
├─ Tab 1: GENEL → cihaz_overview_panel.py (425)
│  ├─ Cihaz özeti (Marka, Model, Seri No, vb.)
│  ├─ KPI gösterimi (Değeri, Durum, vb.)
│  └─ RepositoryRegistry → CihazRepository
│
├─ Tab 2: TEKNIK → cihaz_teknik_panel.py (358)
│  ├─ Teknik specs
│  ├─ UTS (Ulusal Tıbbi Sistem) parse hasil
│  └─ uts_parser.py (1037) → BeautifulSoup, JSON mapping
│      └─ cihaz_teknik_uts_scraper.py (383) → async scraping
│
├─ Tab 3: BELGELER → cihaz_dokuman_panel.py (365)
│  ├─ Dosya listesi
│  ├─ Google Drive upload
│  ├─ FileUploadWidget (proposed)
│  └─ RepositoryRegistry → DokumanRepository
│
├─ Tab 4: ARIZA → ariza_kayit.py (1444) ⚠️ MEGA
│  ├─ Top: KPI şeridi (Toplam, Açık-Kritik, Ort. Çözüm, vb.)
│  ├─ Left: Filtre panel (Durum, Öncelik, Cihaz, Arama)
│  ├─ Main: Renk kodlu tablo
│  │   └─ ArizaTableModel (QAbstractTableModel)
│  ├─ Right: ariza_islem.py (475)
│  │   ├─ Detay header
│  │   ├─ Buton bar
│  │   └─ ArizaIslemForm (Tab, fields, save buttons)
│  └─ RepositoryRegistry → ArizaRepository
│      └─ [Dialog] ariza_girisi_form.py (174)
│
├─ Tab 5: BAKIM → bakim_form.py (2259) ⚠️ MEGA
│  ├─ Top: KPI şeridi (Toplam, Planlı, Yapıldı, Gecikmiş, Son)
│  ├─ Left: Filtre panel
│  ├─ Main: Tablo
│  │   └─ BakimTableModel (QAbstractTableModel)
│  ├─ Right: Form alanı (edit/create/execute)
│  │   ├─ Plan creation (3ay, 6ay, 1yıl otomatik)
│  │   ├─ Execution info (form fields)
│  │   └─ Google Drive upload
│  └─ RepositoryRegistry → BakimRepository
│      └─ GoogleDriveService (async)
│
└─ Tab 6: KALIBRASYON → kalibrasyon_form.py (1268) ⚠️ MEGA
   ├─ Top: KPI şeridi
   ├─ Left: Filtre panel
   ├─ Main: Tablo
   │   └─ KalibrasyonTableModel
   ├─ Tab 1: Kalibrasyon form
   │   ├─ Detail header
   │   └─ Expanded form
   ├─ Tab 2: Performans
   │   ├─ Marka bazlı grid
   │   ├─ Trend grafiği
   │   └─ Yaklaşan bitiş listesi
   └─ RepositoryRegistry → KalibrasyonRepository
```

### Cihaz Modülü — Bileşen Haritası

```
cihaz_listesi.py (592) — Cihaz envanteri
    ├─ CihazTableModel (QAbstractTableModel)
    ├─ FilterPanel (proposed)
    ├─ StatusBadge (proposed)
    ├─ QTableView + QHeaderView
    └─ RepositoryRegistry → CihazRepository

cihaz_ekle.py (507) — Yeni cihaz ekleme
    ├─ Form layout (QLineEdit, QComboBox, QDateEdit)
    ├─ FileUploadWidget (belge yükleme)
    ├─ GoogleDriveService (backup)
    └─ RepositoryRegistry → CihazRepository

ariza_detail_panel.py (30) — Minimal display
bakim_detail_panel.py (28) — Minimal display
kalibrasyon_detail_panel.py (28) — Minimal display

Toplam Cihaz Modülü: 18 dosya, ~11.000 satır
```

## 3. Personel Modülü Ağacı

```
PersonelMerkezPage (483 satır) ← Main hub
├── QStackedWidget (tab navigation)
│
├─ Tab 1: GENEL → personel_overview_panel.py (971) ⚠️ MEGA
│  ├─ Özet metrikleri (Arabuluculuk süresi, İzin bakiye, vb.)
│  ├─ Editlenebilir personel bilgileri (QLineEdit, QComboBox)
│  ├─ Dosya paneli
│  │   ├─ Resim (Avatar)
│  │   ├─ Diploma (file list + upload)
│  │   └─ FileUploadWidget (proposed)
│  ├─ Google Drive upload (async)
│  └─ RepositoryRegistry → PersonelRepository
│
├─ Tab 2: İZİN → personel_izin_panel.py (204)
│  ├─ İzin özeti tablo
│  ├─ Hızlı İzin Giriş Dialog
│  │   └─ hizli_izin_giris.py (206) — QDialog
│  └─ izin_takip.py (929) ⚠️ MEGA
│      ├─ KPI şeridi (Toplam, Kullanılan, Bakiye, vb.)
│      ├─ FilterPanel
│      ├─ IzinTableModel
│      └─ RepositoryRegistry → IzinRepository
│
├─ Tab 3: SAGLIK → personel_saglik_panel.py (168)
│  ├─ Sağlık kontrolleri listesi
│  ├─ Hızlı Sağlık Giriş Dialog
│  │   └─ hizli_saglik_giris.py (226) — QDialog
│  └─ saglik_takip.py (850) ⚠️ MEGA
│      ├─ KPI şeridi
│      ├─ FilterPanel
│      ├─ SaglikTableModel
│      └─ RepositoryRegistry → SaglikRepository
│
├─ Tab 4: BELGELER → personel_dokuman_panel.py (297)
│  ├─ Dosya listesi
│  ├─ Google Drive upload
│  └─ FileUploadWidget (proposed)
│
└─ Tab 5: AYRILIS → isten_ayrilik.py (539)
   ├─ İşten ayrılış kayıtları
   ├─ Tablo
   │   └─ AyrılışTableModel
   └─ RepositoryRegistry → AyrılışRepository

Diğer Personel Sayfaları:
├─ personel_listesi.py (994) ⚠️ MEGA
│   ├─ PersonelTableModel
│   ├─ AvatarDownloaderWorker (async)
│   ├─ AvatarWidget (proposed)
│   └─ RepositoryRegistry → PersonelRepository
│
├─ personel_ekle.py (891) ⚠️ MEGA
│   ├─ Form layout (tüm personel alanları)
│   ├─ Dosya upload (Resim, Diploma1, Diploma2, vb.)
│   ├─ GoogleDriveService (async)
│   ├─ ValidationService (proposed)
│   └─ RepositoryRegistry → PersonelRepository
│       └─ Sabitler Cache (MainWindow'dan)
│
├─ fhsz_yonetim.py (758) — FHSZ (Fiili Hizmet Süresi Zammı)
│   ├─ KosulDelegate (QStyledItemDelegate)
│   ├─ Dönem hesaplama (15 → 14, relativedelta)
│   ├─ SaglikService → hesaplamalar.py
│   └─ RepositoryRegistry → FhszRepository
│
├─ puantaj_rapor.py (545) — Puantaj raporları
│   ├─ PuantajTableModel
│   └─ RepositoryRegistry → PuantajRepository
│
├─ izin_fhsz_puantaj_merkez.py (187) — Hub
│   └─ Tab container (İzin, FHSZ, Puantaj sub-pages)
│
└─ personel_ozet_servisi.py (95) — Utility
    └─ personel_ozet_getir() → SQL queries, data assembly

Toplam Personel Modülü: 17 dosya, ~8.000 satır
```

## 4. RKE Modülü Ağacı

```
rke_yonetim.py (774) — RKE hub
├── QTabWidget
│
├─ Tab 1: Muayene → rke_muayene.py (1385) ⚠️ MEGA
│  ├─ KPI şeridi
│  ├─ FilterPanel
│  ├─ RKETableModel
│  ├─ Form dialogs (muayene bilgi giriş)
│  ├─ File upload (sertifika, vb.)
│  └─ RepositoryRegistry → RKERepository
│
├─ Tab 2: Yönetim → Inventory management
│  ├─ RKE listesi
│  └─ RKETableModel
│
└─ Tab 3: Raporlar → rke_rapor.py (530)
   ├─ Rapor tablosu
   ├─ ReportTableModel
   └─ RepositoryRegistry → RKERepository

Toplam RKE: 3 dosya, ~2.689 satır
```

## 5. Admin Modülü Ağacı

```
admin_panel.py (151) — Admin hub
├── QTabWidget
│
├─ Tab: Kullanıcılar → users_view.py (342)
│  ├─ UserDialog (QDialog, CRUD form)
│  ├─ QTableWidget (users list)
│  └─ AuthRepository + PasswordHasher
│
├─ Tab: Roller → roles_view.py (277)
│  ├─ QTableWidget (roles list)
│  ├─ RoleDialog (edit),
│  └─ PermissionRepository
│
├─ Tab: İzinler → permissions_view.py (111)
│  ├─ Permission grid (QTableWidget)
│  └─ PermissionRepository
│
└─ Tab: Denetim → audit_view.py (86)
   ├─ AuditLogWidget
   └─ AuditRepository (read-only)

Toplam Admin: 6 dosya, ~984 satır
```

## 6. Styles / Tema Sistemi (Merkezi)

```
ThemeManager (Singleton)
    ├─ DarkTheme (renk token'ları)
    │   ├─ BG_PRIMARY, BG_SECONDARY, BG_TERTIARY, BG_ELEVATED
    │   ├─ BORDER_PRIMARY, BORDER_SECONDARY, BORDER_STRONG
    │   ├─ TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED
    │   ├─ ACCENT, ACCENT2
    │   ├─ STATUS_SUCCESS, STATUS_WARNING, STATUS_ERROR
    │   └─ INPUT_BG, INPUT_BORDER, INPUT_BORDER_FOCUS
    │
    ├─ ComponentStyles (QSS string'leri)
    │   ├─ PAGE, FILTER_PANEL, SEPARATOR, SPLITTER
    │   ├─ BTN_ACTION, BTN_SECONDARY, BTN_DANGER, BTN_ICON
    │   ├─ INPUT_TEXT, INPUT_DATE, INPUT_COMBO, INPUT_TEXTAREA
    │   ├─ TABLE, SCROLL, PROGRESS, DIALOG
    │   └─ ... (800+ lines)
    │
    ├─ Icons (Group-based)
    │   ├─ MENU_ICON_MAP (Sidebar menu icons)
    │   ├─ GROUP_ICON_MAP (Group section icons)
    │   ├─ Icons.get(name, size, color)
    │   └─ IconRenderer (custom painting)
    │
    ├─ Colors (Extended palette)
    │   ├─ NAVY_950, SLATE_900, vb.
    │   └─ 26+ custom colors
    │
    └─ theme_registry.py
        └─ Theme switching (light/dark)

Toplam Styles: 6 dosya, ~1.807 satır
```

## 7. Bağımlılık Haritası (High-Level)

```
MainWindow (795)
    ├─ Sidebar (360) ← PageGuard, ActionGuard
    ├─ Dashboard (616) ← DashboardWorker (QThread)
    ├─ BildirimPaneli (222) ← Signal handling
    │
    ├─ Pages Hub
    │   ├─ CihazMerkez (377)
    │   ├─ PersonelMerkez (483)
    │   ├─ RKEYonetim (774)
    │   └─ AdminPanel (151)
    │
    ├─ Theme Management
    │   ├─ ThemeManager (132, Singleton)
    │   ├─ DarkTheme (renk sabitleri)
    │   └─ ComponentStyles (800+)
    │
    └─ Auth
        ├─ LoginDialog (36)
        ├─ ChangePasswordDialog (67)
        └─ AuthService, PermissionRepository

Every page:
    ├─ RepositoryRegistry (db init)
    ├─ DarkTheme (renk kodlama)
    ├─ ComponentStyles (QSS)
    └─ Icons (ikonlar)
```

## 8. Tekrar Eden Patterns (Refactoring Hedefleri)

```
Pattern 1: Table + Model
    ├─ 14 dosya (Custom QAbstractTableModel)
    └─ → BaseTableModel (proposed)

Pattern 2: KPI Card
    ├─ 5+ dosya (KPI gösterimi)
    └─ → KPICard Widget (proposed)

Pattern 3: Search + Filter
    ├─ 7 dosya (filterPanel kodu)
    └─ → FilterPanel Module (proposed)

Pattern 4: Dialog
    ├─ 10+ dosya (form dialogs)
    └─ → BaseDialog (proposed)

Pattern 5: File Upload
    ├─ 5+ dosya (upload logic)
    └─ → FileUploadWidget (proposed)

Pattern 6: Status Badge
    ├─ 4 dosya (renk kodlu durum)
    └─ → StatusBadge Widget (proposed)

Pattern 7: Avatar/Profile Picture
    ├─ 2 dosya (avatar loading, display)
    └─ → AvatarWidget (proposed)
```

## 9. Data Flow İçin Örnek: Yeni Arıza Kayıt

```
User: ariza_kayit.py
    ↓
[Form Dialog] → ArizaIslemForm (fields fill)
    ↓
[Save Button Click]
    ↓
ArizaService.create_ariza(data)
    ↓
RepositoryRegistry.ariza.create(data)
    ↓
[Database] SQLiteManager
    ↓
[RefreshTable] → ArizaTableModel.set_data(query_results)
    ↓
[Signal Emit] → MainWindow.bildirim_paneli.add_notification()
    ↓
User sees: Notification + Updated Table
```

## 10. Import Structure (Current vs Proposed)

### Şiddi (Current)

```python
from ui.pages.cihaz.cihaz_merkez import CihazMerkezPage
from ui.pages.cihaz.components.cihaz_overview_panel import CihazOverviewPanel
from ui.pages.cihaz.components.cihaz_teknik_panel import CihazTeknikPanel
# ... 20+ imports
```

### Proposed (Cleaner)

```python
from ui.pages import CihazPage  # Ordan tüm import edilir
# OR
from ui import MainWindow, AdminPage, CihazPage  # Root level
```

**File:**
```python
# ui/__init__.py
from ui.main_window import MainWindow
from ui.dashboard import DashboardPage
from ui.pages import CihazPage, PersonelPage, RKEPage, AdminPage
from ui.components import DataTable, KPICard, FileUploadWidget
from ui.styles import apply_theme

# ui/pages/__init__.py
from ui.pages.dashboard import DashboardPage
from ui.pages.cihaz import CihazPage
from ui.pages.personel import PersonelPage
# ...
```

---

**Son Güncelleme:** 27 Şubat 2026  
**Yönelim:** REPYS UI Architecture Visual Map

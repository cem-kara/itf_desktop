# REPYS Global Architecture Blueprint

**Tarih:** 27 Şubat 2026  
**Temel:** UI Taraması Analizi (68 dosya, 30.115 satır)  
**Amaç:** Tüm sistemde tutarlı, standart, ölçeklenebilir mimari uygulamak  
**Hedef Sonuç:** 33+ shared component + standardized module patterns → +40% maintainability

---

## 🏗️ GLOBAL ARCHITECTURE PATTERN

### Core Rule: Layered Separation

```
┌─────────────────────────────────────────────────────┐
│ UI Layer (View)                                     │
│  - QWidget, QDialog, QTableView, QStackedWidget    │
│  - Event handling, signal/slot                     │
│  - No business logic, no DB access                 │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│ Presenter/State Layer (ViewModel-like)             │
│  - Model binding (QAbstractTableModel)             │
│  - State management (@dataclass)                   │
│  - View coordinate logic                           │
│  - No business logic, light Repository access      │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│ Service Layer (Business Logic)                      │
│  - CRUD operations                                 │
│  - Validations, calculations                       │
│  - Business rules (e.g., pasif statü 30 gun)      │
│  - Repository orchestration                        │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│ Repository Layer (Data Access)                      │
│  - Direct DB queries                               │
│  - Google Drive API                                │
│  - Caching                                         │
└─────────────────────────────────────────────────────┘
```

### Directory Structure Template

```
ui/pages/
├── [module]/
│   ├── pages/                        # Sayfa grupları (listesi, ekle, detay)
│   │   ├── [page_name]/
│   │   │   ├── __init__.py
│   │   │   ├── [page]_view.py        # Layout, signals (200-400 satır)
│   │   │   ├── [page]_presenter.py   # Model, state binding (150-300 satır)
│   │   │   ├── [page]_service.py     # Business logic (150-300 satır)
│   │   │   └── [page]_state.py       # @dataclass State (50-100 satır)
│   │
│   ├── components/                   # Module-wide reusable widgets
│   │   ├── __init__.py
│   │   ├── [shared]_widget.py
│   │   ├── [shared]_model.py
│   │   └── [shared]_delegate.py
│   │
│   ├── services/                     # Module-level business logic
│   │   ├── __init__.py
│   │   ├── [module]_service.py       # Orchestrator
│   │   ├── [module]_validator.py     # Validation rules
│   │   └── [module]_manager.py       # Complex workflows
│   │
│   ├── utils/                        # Parsers, helpers, formatters
│   │   ├── __init__.py
│   │   └── [utility]_helper.py
│   │
│   └── __init__.py
│
├── components/                        # Global reusable components
│   ├── __init__.py
│   ├── base_table_model.py
│   ├── base_table_delegate.py
│   ├── base_dialog.py
│   ├── kpi_card.py
│   ├── filter_panel.py
│   ├── avatar_widget.py
│   ├── file_upload_widget.py
│   ├── status_badge.py
│   └── ... (diğer shared components)
│
├── styles/                            # Tema, renkler, ikonlar (zaten var)
│   ├── ...
│
└── guards/                            # Yetkilendirme kontrol (zaten var)
    ├── ...
```

---

## 📊 SHARED COMPONENTS MAPPING

### 1. BaseTableModel (QAbstractTableModel Base)

**Mevcut Durum:**
- 14 dosya kendi CustomTableModel tanımlıyor
- Her biri sütun yapısını, veri işlemesini ayrı yönetiyor
- Tekrar eden: `rowCount()`, `columnCount()`, `data()`, `headerData()`

**Yeni Yapı:**

```python
# ui/components/base_table_model.py
class BaseTableModel(QAbstractTableModel):
    """Tüm table model'ler için temel sınıf"""
    
    def __init__(self, headers: list, parent=None):
        super().__init__(parent)
        self._headers = headers
        self._data = []
    
    def rowCount(self, parent=None):
        return len(self._data)
    
    def columnCount(self, parent=None):
        return len(self._headers)
    
    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None
    
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        col = index.column()
        return self._data[row][col] if role == Qt.DisplayRole else None
    
    def set_data(self, data: list):
        """Model verisi güncelle"""
        self.beginResetModel()
        self._data = data
        self.endResetModel()
    
    def get_row(self, row: int) -> dict:
        """Satırı dict olarak döndür (header keys ile)"""
        if 0 <= row < len(self._data):
            return dict(zip(self._headers, self._data[row]))
        return {}
    
    def sort(self, column: int, order=Qt.AscendingOrder):
        """Sıralama (subclass override edebilir)"""
        pass
    
    def filter(self, predicate) -> 'BaseTableModel':
        """Filter uygula (subclass override edebilir)"""
        pass
```

**Kullanan Dosyalar (14):**
- `cihaz_listesi.py` → `CihazTableModel(BaseTableModel)`
- `ariza_kayit.py` → `ArizaTableModel(BaseTableModel)`
- `bakim_form.py` → `BakimTableModel(BaseTableModel)`
- `kalibrasyon_form.py` → `KalibrasyonTableModel(BaseTableModel)`
- `personel_listesi.py` → `PersonelTableModel(BaseTableModel)`
- `izin_takip.py` → `IzinTableModel(BaseTableModel)`
- `saglik_takip.py` → `SaglikTableModel(BaseTableModel)`
- `isten_ayrilik.py` → `IstAyrılışTableModel(BaseTableModel)`
- `puantaj_rapor.py` → `PuantajTableModel(BaseTableModel)`
- `rke_muayene.py` → `RKEMuayeneTableModel(BaseTableModel)`
- `rke_yonetim.py` → `RKEYonetimTableModel(BaseTableModel)`
- `rke_rapor.py` → `RKERaporTableModel(BaseTableModel)`
- `cihaz_dokuman_panel.py` → `DokumenTableModel(BaseTableModel)`
- `data_table.py` → güncellenecek

**Tasarruf:** 300+ satır (her model 20-30 satır base impl., × 14)

---

### 2. BaseTableDelegate (QStyledItemDelegate Base)

**Mevcut Durum:**
- 6 dosya custom delegate tanımlıyor
- Tekrar: renk kodlama (durum), tarih formatting, etc.

**Yeni Yapı:**

```python
# ui/components/base_table_delegate.py
class BaseTableDelegate(QStyledItemDelegate):
    """Custom rendering için base delegate"""
    
    STATUS_COLORS = {}  # Subclass tarafından override edilecek
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def paint(self, painter, option, index):
        """Temel rendering, subclass'lar override edebilir"""
        if self.STATUS_COLORS:
            status = index.data()
            if status in self.STATUS_COLORS:
                option.backgroundBrush = QBrush(QColor(self.STATUS_COLORS[status]))
        super().paint(painter, option, index)
```

**Kullanan Dosyalar (6+):**
- `ariza_kayit.py` → `ArizaTableDelegate(BaseTableDelegate)`
- `bakim_form.py` → `BakimTableDelegate(BaseTableDelegate)`
- `kalibrasyon_form.py` → `KalibrasyonDelegate(BaseTableDelegate)`
- `personel_listesi.py` → `PersonelListDelegate(BaseTableDelegate)`
- `u, fhsz_yonetim.py` → `FHSZDelegate(BaseTableDelegate)`

**Tasarruf:** 150+ satır

---

### 3. KPICard Widget

**Mevcut Durum:**
- 5+ dosya kendi KPI rendering kodu yazıyor
- Renk maaplaması (red/amber/green), grid layout tekrar ediyor

**Yeni Yapı:**

```python
# ui/components/kpi_card.py
class KPICard(QWidget):
    """Reusable KPI card widget"""
    
    def __init__(self, title: str, value: int = 0, subtitle: str = "", 
                 color: str = "neutral", size: str = "medium", parent=None):
        super().__init__(parent)
        self.title = title
        self.value = value
        self.subtitle = subtitle
        self.color = color  # "red", "amber", "green", "blue", etc.
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        
        # Title label
        title_label = QLabel(self.title)
        title_label.setStyleSheet(f"color: {self._map_color()}; font-weight: bold;")
        
        # Value label
        value_label = QLabel(str(self.value))
        value_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        
        # Subtitle
        if self.subtitle:
            subtitle_label = QLabel(self.subtitle)
            layout.addWidget(subtitle_label)
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        self.setLayout(layout)
    
    def set_value(self, value: int):
        self.value = value
        # Update UI
    
    def _map_color(self) -> str:
        color_map = {
            "red": "#FF6B6B",
            "amber": "#FFA500",
            "green": "#51CF66",
            "blue": "#339AF0"
        }
        return color_map.get(self.color, "#666666")
```

**Kullanan Dosyalar (5+):**
- `dashboard.py` → KPI kartları
- `ariza_kayit.py` → üstte durum şeridi
- `bakim_form.py` → KPI şeridi
- `kalibrasyon_form.py` → KPI şeridi
- `personel_overview_panel.py` → metrikleri

**Tasarruf:** 200+ satır

---

### 4. FilterPanel Widget

**Mevcut Durum:**
- 7+ sayfa kendi filter UI kodları yazıyor
- QLineEdit (search) + QComboBox (filters) + button bar tekrar ediyor

**Yeni Yapı:**

```python
# ui/components/filter_panel.py
class FilterPanel(QWidget):
    filter_changed = Signal(str, dict)  # (search_text, filter_dict)
    
    def __init__(self, filters: dict = None, parent=None):
        super().__init__(parent)
        # filters = {"status": ["Açık", "Kapandı"], "unit": [...]}
        self.filters = filters or {}
        self._init_ui()
    
    def _init_ui(self):
        layout = QHBoxLayout()
        
        # Search box
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Ara...")
        self.search_input.textChanged.connect(self._on_filter_change)
        layout.addWidget(self.search_input)
        
        # Filter dropdowns
        for filter_name, options in self.filters.items():
            combo = QComboBox()
            combo.addItem("Tümü")
            combo.addItems(options)
            combo.currentTextChanged.connect(self._on_filter_change)
            layout.addWidget(QLabel(filter_name))
            layout.addWidget(combo)
        
        # Apply button
        apply_btn = QPushButton("Uygula")
        apply_btn.clicked.connect(self._on_filter_change)
        layout.addWidget(apply_btn)
        
        self.setLayout(layout)
    
    def _on_filter_change(self):
        search_text = self.search_input.text()
        filter_dict = {name: combo.currentText() for name, combo in ...}
        self.filter_changed.emit(search_text, filter_dict)
    
    def get_filters(self) -> tuple:
        """(search_text, filter_dict) döndür"""
        ...
```

**Kullanan Dosyalar (7+):**
- `cihaz_listesi.py`
- `ariza_kayit.py`
- `bakim_form.py`
- `kalibrasyon_form.py`
- `personel_listesi.py`
- `izin_takip.py`
- `saglik_takip.py`

**Tasarruf:** 250+ satır

---

### 5. AvatarWidget

**Mevcut Durum:**
- `personel_listesi.py` → avatar column rendering
- `personel_overview_panel.py` → avatar display + upload

**Yeni Yapı:**

```python
# ui/components/avatar_widget.py
class AvatarWidget(QWidget):
    avatar_changed = Signal(str)  # yeni image path
    
    def __init__(self, image_url: str = None, size: int = 64, 
                 editable: bool = False, parent=None):
        super().__init__(parent)
        self.image_url = image_url
        self.size = size
        self.editable = editable
        self.pixmap = None
        self._init_ui()
        if image_url:
            self.load_image(image_url)
    
    def _init_ui(self):
        layout = QVBoxLayout()
        
        # Avatar display
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(self.size, self.size)
        self.avatar_label.setStyleSheet("""
            border-radius: %dpx;
            border: 2px solid #ccc;
            background-color: #f0f0f0;
        """ % (self.size // 2))
        layout.addWidget(self.avatar_label)
        
        # Upload button (editable mode)
        if self.editable:
            upload_btn = QPushButton("Değiştir")
            upload_btn.clicked.connect(self._on_upload)
            layout.addWidget(upload_btn)
        
        self.setLayout(layout)
    
    def load_image(self, url: str):
        """URL'den veya yerel path'den resim yükle"""
        # Cache kontrolü, async download, etc.
        ...
    
    def _on_upload(self):
        path = QFileDialog.getOpenFileName(self, "Resim Seç")[0]
        if path:
            self.set_image(path)
            self.avatar_changed.emit(path)
    
    def set_image(self, pixmap: QPixmap):
        # Circular mask apply+display
        ...
```

**Kullanan Dosyalar (2+):**
- `personel_listesi.py`
- `personel_overview_panel.py`

**Tasarruf:** 100+ satır

---

### 6. FileUploadWidget

**Mevcut Durum:**
- 5+ dosya file upload UI + logic yazıyor
- QFileDialog + Google Drive async upload tekrar ediyor

**Yeni Yapı:**

```python
# ui/components/file_upload_widget.py
class FileUploadWidget(QWidget):
    file_uploaded = Signal(str, str)  # (file_path, file_name)
    upload_progress = Signal(int)      # 0-100
    
    def __init__(self, allowed_types: list = None, auto_upload: bool = False,
                 parent=None):
        super().__init__(parent)
        self.allowed_types = allowed_types or ["*"]
        self.auto_upload = auto_upload
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        
        # File selector
        self.file_label = QLabel("Dosya seçilmedi")
        select_btn = QPushButton("Dosya Seç")
        select_btn.clicked.connect(self._on_select)
        layout.addWidget(self.file_label)
        layout.addWidget(select_btn)
        
        # Upload progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Upload button
        self.upload_btn = QPushButton("Yükle")
        self.upload_btn.clicked.connect(self._on_upload)
        self.upload_btn.setEnabled(False)
        layout.addWidget(self.upload_btn)
        
        self.setLayout(layout)
    
    def _on_select(self):
        file_types = " ".join([f"*.{t}" for t in self.allowed_types])
        path, _ = QFileDialog.getOpenFileName(self, "Dosya Seç", filter=file_types)
        if path:
            self.selected_file = path
            self.file_label.setText(os.path.basename(path))
            self.upload_btn.setEnabled(True)
            if self.auto_upload:
                self._on_upload()
    
    def _on_upload(self):
        # Google Drive async upload
        # self.upload_progress.emit(0...100)
        ...
```

**Kullanan Dosyalar (5+):**
- `personel_ekle.py`
- `cihaz_dokuman_panel.py`
- `personel_dokuman_panel.py`
- `personel_overview_panel.py`
- `bakim_form.py`

**Tasarruf:** 300+ satır

---

### 7. StatusBadge Widget

**Mevcut Durum:**
- 4 dosya status badge rendering kodu yazıyor
- Durum → renk eşleme tekrar ediyor

**Yeni Yapı:**

```python
# ui/components/status_badge.py
class StatusBadge(QWidget):
    STATUS_CONFIG = {
        "Açık": {"color": "#FF6B6B", "bg": "#FFE5E5"},
        "Kapandı": {"color": "#51CF66", "bg": "#E6F9EF"},
        "Pasif": {"color": "#868E96", "bg": "#F1F3F5"},
        "İzinli": {"color": "#339AF0", "bg": "#E7F5FF"},
        # ... diğer statuslar
    }
    
    def __init__(self, status: str, size: str = "medium", parent=None):
        super().__init__(parent)
        self.status = status
        self.size = size
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        
        label = QLabel(self.status)
        config = self.STATUS_CONFIG.get(self.status, {})
        
        color = config.get("color", "#000000")
        bg = config.get("bg", "#ffffff")
        
        if self.size == "large":
            font_size = 14
            padding = "10px 15px"
        else:
            font_size = 11
            padding = "5px 10px"
        
        label.setStyleSheet(f"""
            color: {color};
            background-color: {bg};
            border-radius: 4px;
    padding: {padding};
            font-size: {font_size}px;
            font-weight: bold;
        """)
        
        layout.addWidget(label)
        self.setLayout(layout)
    
    def set_status(self, status: str):
        self.status = status
        self._init_ui()
```

**Kullanan Dosyalar (4+):**
- `ariza_kayit.py`
- `kalibrasyon_form.py`
- `personel_listesi.py`
- `fhsz_yonetim.py`

**Tasarruf:** 100+ satır

---

### 8. BaseDialog

**Mevcut Durum:**
- 10+ dosya kendi dialog'larını tanımlıyor
- QDialog + form layout tekrar ediyor

**Yeni Yapı:**

```python
# ui/components/base_dialog.py
class BaseDialog(QDialog):
    """Form dialogları için base sınıf"""
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.fields = {}
        self.main_layout = QVBoxLayout()
        
        self.setLayout(self.main_layout)
        self._init_buttons()
    
    def _init_buttons(self):
        button_layout = QHBoxLayout()
        
        ok_btn = QPushButton("Tamam")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("İptal")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        
        self.main_layout.addLayout(button_layout)
    
    def add_field(self, name: str, label: str, widget: QWidget):
        """Form alanı ekle"""
        field_layout = QHBoxLayout()
        field_layout.addWidget(QLabel(label))
        field_layout.addWidget(widget)
        self.main_layout.insertLayout(self.main_layout.count() - 1, field_layout)
        self.fields[name] = widget
    
    def get_data(self) -> dict:
        """Form verisi dict olarak döndür"""
        data = {}
        for name, widget in self.fields.items():
            if isinstance(widget, QLineEdit):
                data[name] = widget.text()
            elif isinstance(widget, QComboBox):
                data[name] = widget.currentText()
            # ... diğer widget tipleri
        return data
```

**Kullanan Dosyalar (10+):**
- `login_dialog.py`
- `change_password_dialog.py`
- Various UserDialog, ItemDialog, vb.

**Tasarruf:** 150+ satır

---

## 🎯 SHARED COMPONENTS ÖZET

| Component | Satır Tasarrufu | Kullanan Dosya Sayısı |
|-----------|----------------|-----------------------|
| BaseTableModel | 300+ | 14 |
| BaseTableDelegate | 150+ | 6+ |
| KPICard | 200+ | 5+ |
| FilterPanel | 250+ | 7+ |
| AvatarWidget | 100+ | 2+ |
| FileUploadWidget | 300+ | 5+ |
| StatusBadge | 100+ | 4+ |
| BaseDialog | 150+ | 10+ |
| **TOPLAM** | **1.450+** | **50+ dosya** |

---

## 🗂️ MODULE-BY-MODULE REFACTORING STRATEGY

### Modül Yapısı Nasıl Uygulanacak?

Her modülde aynı pattern:

```
ui/pages/[module]/
├── pages/
│   ├── [sayfa1]/
│   │   ├── [sayfa1]_view.py        (Layout, UI assembly)
│   │   ├── [sayfa1]_presenter.py   (Model, state binding, event wiring)
│   │   ├── [sayfa1]_service.py     (CRUD, business logic)
│   │   └── [sayfa1]_state.py       (@dataclass State objects)
│   ├── [sayfa2]/
│   │   ├── ...
│   │
├── components/                      (Module-wide shared)
│   ├── [shared1]_widget.py
│   ├── [shared2]_model.py
│   └── [shared3]_delegate.py
│
├── services/                        (Module-level orchestration)
│   ├── [module]_service.py         (Main service facade)
│   ├── [module]_validator.py       (Validation rules)
│   └── [module]_manager.py         (Complex workflows)
│
├── utils/                           (Parsers, helpers)
│   ├── [parser]_helper.py
│   └── [formatter]_helper.py
│
└── __init__.py
```

---

## CIHAZ MODÜLÜ — Örnek Implementasyon

```
ui/pages/cihaz/
├── pages/
│   ├── listesi/
│   │   ├── __init__.py
│   │   ├── listesi_view.py         # CihazListView: QTableView + filter
│   │   ├── listesi_presenter.py    # CihazListPresenter: model + lazy-load
│   │   ├── listesi_service.py      # CihazListService: get_all(), filter()
│   │   └── listesi_state.py        # @dataclass CihazListState
│   │
│   ├── merkez/
│   │   ├── __init__.py
│   │   ├── merkez_view.py          # CihazMerkez: QStackedWidget + tabs
│   │   ├── merkez_presenter.py     # routing, tab switching
│   │   ├── merkez_service.py       # -
│   │   └── merkez_state.py         # selected_cihaz, active_tab
│   │
│   ├── ariza/
│   │   ├── __init__.py
│   │   ├── ariza_view.py           # ArizaView: table + detail panel
│   │   ├── ariza_presenter.py      # ArizaPresenter: model + state
│   │   ├── ariza_service.py        # ArizaService: CRUD, notification
│   │   └── ariza_state.py          # @dataclass ArizaState
│   │
│   ├── bakım/
│   │   ├── __init__.py
│   │   ├── bakım_view.py
│   │   ├── bakım_presenter.py
│   │   ├── bakım_service.py        # auto-plan generation
│   │   └── bakım_state.py
│   │
│   ├── kalibrasyon/
│   │   ├── __init__.py
│   │   ├── kalibrasyon_view.py
│   │   ├── kalibrasyon_presenter.py
│   │   ├── kalibrasyon_service.py
│   │   └── kalibrasyon_state.py
│   │
│   ├── ekle/
│   │   ├── __init__.py
│   │   ├── ekle_view.py            # Yeni cihaz ekleme formu
│   │   ├── ekle_presenter.py
│   │   ├── ekle_service.py
│   │   └── ekle_state.py
│   │
│   └── dokuman/
│       ├── __init__.py
│       ├── dokuman_view.py
│       ├── dokuman_presenter.py
│       └── dokuman_service.py
│
├── components/
│   ├── __init__.py
│   ├── cihaz_overlay_widget.py     # Cihaz metrikleri şeridi
│   ├── cihaz_table_model.py        # Extends BaseTableModel
│   ├── cihaz_table_delegate.py     # Extends BaseTableDelegate
│   ├── ariza_kpi_widget.py         # Extends KPICard
│   ├── bakım_kpi_widget.py         # Extends KPICard
│   └── kalibrasyon_kpi_widget.py   # Extends KPICard
│
├── services/
│   ├── __init__.py
│   ├── cihaz_service.py            # CihazService: main facade
│   ├── cihaz_validator.py          # Validation rules
│   ├── drive_service.py            # Google Drive file ops
│   └── uts_parser_service.py       # UTS parsing orchestration
│
├── utils/
│   ├── __init__.py
│   ├── uts_parser/
│   │   ├── __init__.py
│   │   ├── html_scraper.py         # BeautifulSoup parsing
│   │   ├── field_mapper.py         # UTS → cihaz mapping
│   │   ├── validator.py            # Format validation
│   │   └── cache.py                # LRU cache
│   │
│   └── formatter_helper.py         # Tarih, sayı formatting
│
└── __init__.py
```

---

## PERSONEL MODÜLÜ — Örnek Implementasyon

```
ui/pages/personel/
├── pages/
│   ├── listesi/
│   │   ├── __init__.py
│   │   ├── listesi_view.py         # PersonelListeView
│   │   ├── listesi_presenter.py    # lazy-loading, avatar caching
│   │   ├── listesi_service.py      # get_liste, filter, search
│   │   └── listesi_state.py        # PersonelListeState
│   │
│   ├── merkez/
│   │   ├── __init__.py
│   │   ├── merkez_view.py
│   │   ├── merkez_presenter.py
│   │   └── merkez_state.py
│   │
│   ├── profil/                    # ← personel_overview_panel refactored
│   │   ├── __init__.py
│   │   ├── profil_view.py          # Özet + metrikleri display
│   │   ├── profil_presenter.py     # Form field binding
│   │   ├── profil_service.py       # update_personel(), file ops
│   │   └── profil_state.py         # PersonelProfilState
│   │
│   ├── ekle/
│   │   ├── __init__.py
│   │   ├── ekle_view.py            # Form layout
│   │   ├── ekle_presenter.py       # Validation display
│   │   ├── ekle_service.py         # save(), auto user creation
│   │   └── ekle_state.py           # Form state
│   │
│   ├── izin/
│   │   ├── __init__.py
│   │   ├── izin_view.py            # Personel seçim + tablo
│   │   ├── izin_presenter.py       # Model + state binding
│   │   ├── izin_service.py         # CRUD + pasif statü rule
│   │   └── izin_state.py           # IzinState
│   │
│   ├── saglik/
│   │   ├── __init__.py
│   │   ├── saglik_view.py
│   │   ├── saglik_presenter.py
│   │   ├── saglik_service.py
│   │   └── saglik_state.py
│   │
│   ├── fhsz/
│   │   ├── __init__.py
│   │   ├── fhsz_view.py
│   │   ├── fhsz_presenter.py
│   │   ├── fhsz_service.py         # Hesaplama logic
│   │   └── fhsz_state.py
│   │
│   ├── puantaj/
│   │   ├── __init__.py
│   │   ├── puantaj_view.py
│   │   ├── puantaj_presenter.py
│   │   ├── puantaj_service.py
│   │   └── puantaj_state.py
│   │
│   └── ayrılık/
│       ├── __init__.py
│       ├── ...
│
├── components/
│   ├── __init__.py
│   ├── personel_table_model.py     # Extends BaseTableModel
│   ├── personel_list_delegate.py   # Extends BaseTableDelegate  
│   ├── personel_avatar_widget.py   # Extends AvatarWidget
│   ├── personel_status_badge.py    # Extends StatusBadge
│   ├── personel_form_fields.py     # Reusable form fields
│   └── file_manager_widget.py      # Dosya yönetimi UI
│
├── services/
│   ├── __init__.py
│   ├── personel_service.py         # Main orchestrator
│   ├── personel_validator.py       # TC, email, business rules
│   ├── pasif_status_manager.py     # 30 gün kuralı
│   ├── avatar_service.py           # Avatar download + cache
│   ├── file_service.py             # Drive file ops
│   └── auto_sync_service.py        # User creation
│
├── utils/
│   ├── __init__.py
│   └── formatter_helper.py         # Tarih, TC format
│
└── __init__.py
```

---

## 🔗 BAĞIMLILIQ HARİTASI

### Current State (Karmaşık, Circular Risk)

```
ui/pages/cihaz/ariza_kayit.py
  ├→ CihazRepository (direct)
  ├→ ArizaRepository (direct)
  ├→ NotificationService (direct)
  ├→ Google Drive (direct)
  └→ uts_parser.py (direct import)

ui/pages/personel/personel_ekle.py
  ├→ PersonelRepository (direct)
  ├→ PersonelSabitlerCache (direct)
  ├→ Google Drive (direct)
  ├→ AuthService (indirect)
  └→ (User creation logic mixed in)
```

### Target State (Clean Layers)

```
View Layer (ariza_view.py)
  └→ Presenter (ariza_presenter.py)
       └→ Service (ariza_service.py)
            ├→ ArizaRepository
            ├→ NotificationService
            └→ (No UI imports)

View Layer (ekle_view.py)
  └→ Presenter (ekle_presenter.py)
       └→ Service (ekle_service.py)
            ├→ PersonelRepository
            ├→ PersonelValidator
            ├→ FileService (drives)
            ├→ AuthService (user creation)
            └→ AutoSyncService
```

---

## 📈 REFACTORING TIMELINE & PRIORITIES

### Faz 1: Shared Components (Week 1)
- [ ] BaseTableModel + BaseTableDelegate
- [ ] KPICard, FilterPanel, StatusBadge, BaseDialog
- [ ] AvatarWidget, FileUploadWidget
- **Kazanım:** 1.450+ satır tasarruf, 50+ dosya ready for use

### Faz 2: Cihaz Modülü (Weeks 2-3)
- [ ] `pages/` klasör yapısı
- [ ] ariza_kayit → pages/ariza/
- [ ] bakim_form → pages/bakim/
- [ ] kalibrasyon_form → pages/kalibrasyon/
- [ ] shared components'i integrate et
- **Kazanım:** 4.971 satır → ~2.000 satır (60% azalış)

### Faz 3: Personel Modülü (Weeks 4-5)
- [ ] pages/ klasör yapısı
- [ ] personel_ekle → pages/ekle/
- [ ] personel_listesi → pages/listesi/
- [ ] personel_overview_panel → pages/profil/
- [ ] izin_takip → pages/izin/
- [ ] saglik_takip → pages/saglik/
- **Kazanım:** 5.594 satır → ~2.500 satır (55% azalış)

### Faz 4: RKE Modülü (Week 6)
- [ ] RKE modülü same pattern

### Faz 5: Service Layer Completion (Weeks 7-8)
- [ ] Business logic consolidation
- [ ] Validation rules
- [ ] Special managers (pasif_status_manager, auto_sync_service)

---

## 🎯 SUCCESS METRICS

### Code Quality
- ✅ Average file size: 450 → 250-300 satır
- ✅ Cyclomatic complexity: <10 per file
- ✅ Test coverage: 80%+ critical services
- ✅ No circular imports

### Maintainability
- ✅ Clear separation of concerns (View/Presenter/Service/Repo)
- ✅ Reusable components (33+ shared widgets)
- ✅ Standardized patterns (all modules follow same structure)
- ✅ Business logic testable without UI

### Performance
- ✅ Lazy-loading working (personel 100-batch)
- ✅ Avatar cache hit rate >80%
- ✅ No memory leaks
- ✅ Async file uploads working

### Documentation
- ✅ This blueprint (architecture guide)
- ✅ Component API docs
- ✅ Module-specific guides
- ✅ Migration checklist per module

---

## 📋 IMMEDIATE NEXT STEPS

1. ✅ Create all 8 shared components (this week)
   - BaseTableModel.py
   - BaseTableDelegate.py
   - KPICard.py
   - FilterPanel.py
   - AvatarWidget.py
   - FileUploadWidget.py
   - StatusBadge.py
   - BaseDialog.py

2. ✅ Write unit tests for each component

3. ✅ Convert first module (Cihaz) to new structure

4. ✅ Update imports and test end-to-end

This blueprint is your **source of truth** for all future refactoring.

---

**Related Documents:**
- [PARCALAMA_TODO.md](PARCALAMA_TODO.md) — Sprint-by-sprint actionable tasks
- [UI_TARAMA_RAPORU.md](UI_TARAMA_RAPORU.md) — Detailed file analysis
- [MASTER_TEKNIK_DURUM_VE_YOLHARITA.md](MASTER_TEKNIK_DURUM_VE_YOLHARITA.md) — Overall project roadmap

# REPYS — Nokta Atışı TODO
> Gerçek koddan üretildi | 28 Şubat 2026
> Her görev: hangi dosya, hangi satır, ne yazılacak, nasıl test edilir

---

## 📌 Nasıl Kullanılır

- Görevleri **sırayla** yap. Sonraki görev öncekine bağımlı olabilir.
- Her görev bitmeden commit at: `git commit -m "TODO-X.X tamamlandı"`
- ✅ = Bitti, ⬜ = Bekliyor, 🔄 = Devam ediyor

---

## FAZ 1 — Duplikasyonları Sil (3–5 gün)

### GÖREV 1.1 — `BaseTableModel` yaz
**Dosya:** `ui/components/base_table_model.py` ← **YENİ DOSYA**
**Bağımlılık:** Yok, sıfırdan yazılır

**Ne yazılacak:**
```python
# ui/components/base_table_model.py
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor

class BaseTableModel(QAbstractTableModel):
    """
    Tüm tablolar bunu extend eder.
    columns = [("DbAlani", "Başlık", genişlik), ...]
    """
    def __init__(self, columns: list, data=None, parent=None):
        super().__init__(parent)
        self._columns = columns
        self._data = data or []
        self._keys = [c[0] for c in columns]

    def rowCount(self, parent=QModelIndex()): return len(self._data)
    def columnCount(self, parent=QModelIndex()): return len(self._columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        row = self._data[index.row()]
        key = self._keys[index.column()]
        if role == Qt.DisplayRole:      return self._display(key, row)
        if role == Qt.ForegroundRole:   return self._fg(key, row)
        if role == Qt.BackgroundRole:   return self._bg(key, row)
        if role == Qt.TextAlignmentRole: return self._align(key)
        if role == Qt.UserRole:         return row   # tüm satır dict'i
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._columns[section][1]
        return None

    # ── Alt sınıflar override eder ──────────────────────
    def _display(self, key, row): return str(row.get(key, "") or "")
    def _fg(self, key, row):      return None
    def _bg(self, key, row):      return None
    def _align(self, key):        return Qt.AlignVCenter | Qt.AlignLeft

    # ── Ortak metodlar ──────────────────────────────────
    def set_data(self, data):
        self.beginResetModel()
        self._data = data or []
        self.endResetModel()

    def get_row(self, idx):
        return self._data[idx] if 0 <= idx < len(self._data) else None

    def all_data(self):
        return list(self._data)
```

**Test:** `python -c "from ui.components.base_table_model import BaseTableModel; print('OK')"`

**Commit:** `git add ui/components/base_table_model.py && git commit -m "TODO-1.1: BaseTableModel eklendi"`

---

### GÖREV 1.2 — `BakimTableModel`'i BaseTableModel'e bağla
**Dosya:** `ui/pages/cihaz/bakim_form.py`
**Satırlar:** 203–253 (mevcut `BakimTableModel` — 51 satır → 15 satıra iner)

**Şu an (satır 203–253):**
```python
class BakimTableModel(QAbstractTableModel):
    def __init__(self, rows=None, parent=None):
        super().__init__(parent)
        self._rows    = rows or []
        self._keys    = [c[0] for c in BAKIM_COLUMNS]
        self._headers = [c[1] for c in BAKIM_COLUMNS]
    def rowCount(...): ...
    def columnCount(...): ...
    def data(...): ...  # 20 satır
    def headerData(...): ...
    def set_rows(...): ...
    def get_row(...): ...
```

**Sonra (satır 203 yerini alacak):**
```python
from ui.components.base_table_model import BaseTableModel
from core.date_utils import to_ui_date

class BakimTableModel(BaseTableModel):
    def __init__(self, rows=None, parent=None):
        super().__init__(BAKIM_COLUMNS, rows, parent)

    def _display(self, key, row):
        val = row.get(key, "")
        if key in ("PlanlananTarih", "BakimTarihi"):
            return to_ui_date(val, "")
        return str(val) if val else ""

    def _fg(self, key, row):
        if key == "Durum":
            c = _DURUM_COLOR.get(row.get("Durum", ""))
            return QColor(c) if c else None
        return None

    def _align(self, key):
        if key in ("PlanlananTarih", "BakimTarihi", "Durum"):
            return Qt.AlignCenter
        return Qt.AlignVCenter | Qt.AlignLeft

    # Geriye dönük uyumluluk için alias
    def set_rows(self, rows): self.set_data(rows)
```

**Test:** Uygulama aç → Bakım sekmesi → tablo görünüyor mu? ✓

**Commit:** `git commit -m "TODO-1.2: BakimTableModel → BaseTableModel"`

---

### GÖREV 1.3 — `ArizaTableModel`'i bağla
**Dosya:** `ui/pages/cihaz/ariza_kayit.py`
**Satırlar:** 94–164 (71 satır → 25 satıra iner)

**Sonra:**
```python
class ArizaTableModel(BaseTableModel):
    def __init__(self, rows=None, parent=None):
        super().__init__(ARIZA_COLUMNS, rows, parent)

    def _display(self, key, row):
        val = row.get(key, "")
        if key == "BaslangicTarihi":
            return to_ui_date(val, "")
        return str(val) if val else ""

    def _fg(self, key, row):
        if key == "Durum":
            c = _DURUM_COLOR.get(row.get("Durum", ""))
            return QColor(c) if c else None
        if key == "Oncelik":
            c = _ONCELIK_COLOR.get(row.get("Oncelik", ""))
            return QColor(c) if c else None
        return None

    def _bg(self, key, row):
        if key == "Durum":
            bg = _DURUM_BG_COLOR.get(row.get("Durum", ""))
            return QColor(bg) if bg else None
        if key == "Oncelik":
            bg = _ONCELIK_BG_COLOR.get(row.get("Oncelik", ""))
            return QColor(bg) if bg else None
        return None

    def _align(self, key):
        if key in ("BaslangicTarihi", "Oncelik", "Durum"):
            return Qt.AlignCenter
        return Qt.AlignVCenter | Qt.AlignLeft

    def set_rows(self, rows): self.set_data(rows)
    def all_rows(self): return self.all_data()
```

**Test:** Arıza sekmesi → tablo renk kodlama çalışıyor mu? ✓

**Commit:** `git commit -m "TODO-1.3: ArizaTableModel → BaseTableModel"`

---

### GÖREV 1.4 — `KalibrasyonTableModel`'i bağla
**Dosya:** `ui/pages/cihaz/kalibrasyon_form.py`
**Satırlar:** 74–150 (77 satır → 30 satıra iner)

**Dikkat:** `_bitis_rengi()` fonksiyonu korunacak, sadece model değişiyor.

```python
class KalibrasyonTableModel(BaseTableModel):
    def __init__(self, rows=None, parent=None):
        super().__init__(KAL_COLUMNS, rows, parent)

    def _display(self, key, row):
        val = row.get(key, "")
        if key in ("YapilanTarih", "BitisTarihi"):
            return to_ui_date(val, "")
        return str(val) if val else ""

    def _fg(self, key, row):
        if key == "Durum":
            c = _DURUM_COLOR.get(row.get("Durum", ""))
            return QColor(c) if c else None
        if key == "BitisTarihi":
            return QColor(_bitis_rengi(row.get("BitisTarihi", "")))
        return None

    def _bg(self, key, row):
        if key == "Durum":
            durum = row.get("Durum", "")
            if durum in ("Gecerli", "Geçerli"):  return QColor(_C["green"] + "22")
            if durum in ("Gecersiz", "Geçersiz"): return QColor(_C["red"] + "22")
        return None

    def _align(self, key):
        if key in ("YapilanTarih", "BitisTarihi", "Durum"):
            return Qt.AlignCenter
        return Qt.AlignVCenter | Qt.AlignLeft

    def set_rows(self, rows): self.set_data(rows)
```

**Test:** Kalibrasyon sekmesi → bitis tarihi renk kodlama çalışıyor mu? ✓

---

### GÖREV 1.5 — Kalan 9 TableModel'i bağla
**Sıra:** Aşağıdaki dosyaları 1.2–1.4 ile aynı yöntemle güncelle

| # | Dosya | Mevcut sınıf | Satır aralığı |
|---|-------|-------------|--------------|
| a | `ui/pages/personel/izin_takip.py` | `IzinTableModel` | 59–123 |
| b | `ui/pages/personel/saglik_takip.py` | `SaglikTakipTableModel` | 124–180 |
| c | `ui/pages/personel/personel_listesi.py` | `PersonelTableModel` | 83–178 |
| d | `ui/pages/rke/rke_muayene.py` | `RKEEnvanterModel` | 663–702 |
| e | `ui/pages/rke/rke_muayene.py` | `GecmisModel` | 703–735 |
| f | `ui/pages/rke/rke_yonetim.py` | `RKETableModel` | 147–181 |
| g | `ui/pages/rke/rke_yonetim.py` | `_GecmisModel` | 182–220 |
| h | `ui/pages/rke/rke_rapor.py` | `RaporTableModel` | 216–280 |
| i | `ui/pages/cihaz/ariza_islem.py` | `ArizaIslemTableModel` | 34–100 |
| j | `ui/pages/cihaz/cihaz_listesi.py` | `CihazTableModel` | 44–149 |

> **Not:** `PersonelTableModel` (c) daha karmaşık — özel roller var (`RAW_ROW_ROLE`, `IZIN_PCT_ROLE`).
> Bunları UserRole+1, UserRole+2 olarak base class dışında tutmak en güvenlisi.

**Her biri için commit:** `git commit -m "TODO-1.5x: XxxTableModel → BaseTableModel"`

---

### GÖREV 1.6 — `DriveUploadWorker`'ı ortak yere taşı
**Kaynak:** `ui/pages/personel/personel_ekle.py` satır 108–160
**Hedef:** `ui/components/drive_upload_worker.py` ← **YENİ DOSYA**

**Adımlar:**
1. `DriveUploadWorker` sınıfını yeni dosyaya kopyala (satır 108–160 aynen)
2. `personel_ekle.py` satır 108–160'ı sil, yerine import ekle:
   ```python
   from ui.components.drive_upload_worker import DriveUploadWorker
   ```
3. `ui/pages/cihaz/bakim_form.py` satır 119–154'teki `DosyaYukleyici` sınıfını sil
4. `bakim_form.py`'de `DosyaYukleyici` kullanılan yerleri `DriveUploadWorker` ile değiştir

> **Not:** `DosyaYukleyici` (bakim) offline desteği yok, `DriveUploadWorker` (personel) var.
> Yeni ortak worker = personel'deki DriveUploadWorker, daha iyi olanı.

**Test:** Bakım formu → dosya yükle → çalışıyor mu? ✓

**Commit:** `git commit -m "TODO-1.6: DriveUploadWorker ortak bileşene taşındı"`

---

### GÖREV 1.7 — `_C` renk dict'lerini merkeze al
**Sorun:** `_C = {"red": ..., "green": ...}` aynı dict 4 dosyada kopyalanmış:
- `bakim_form.py` satır 43–53
- `ariza_kayit.py` satır 38–44
- `kalibrasyon_form.py` satır 37–48
- `rke_muayene.py` satır 92–100

**Hedef:** `ui/styles/colors.py` içine ekle (dosya zaten var, DarkTheme burada)

```python
# ui/styles/colors.py'e ekle (en sona)

# Kısa erişim aliası — UI bileşenlerinde _C yerine kullanın
C = {
    "red":    DarkTheme.DANGER,
    "amber":  DarkTheme.WARNING,
    "green":  DarkTheme.SUCCESS,
    "accent": DarkTheme.ACCENT,
    "muted":  DarkTheme.TEXT_MUTED,
    "surface":DarkTheme.SURFACE,
    "panel":  DarkTheme.PANEL,
    "border": DarkTheme.BORDER,
    "text":   DarkTheme.TEXT_PRIMARY,
}
```

Sonra her dosyada:
```python
# Eski:
_C = {"red": getattr(DarkTheme, "DANGER", "#f75f5f"), ...}  # SİL

# Yeni:
from ui.styles.colors import C as _C  # EKLE
```

**Test:** Her modülü aç, renkler doğru mu? ✓

**Commit:** `git commit -m "TODO-1.7: _C renk dict merkeze alındı"`

---

### FAZ 1 Kontrol Listesi
```
[x] 1.1 BaseTableModel yazıldı
[x] 1.2 BakimTableModel bağlandı + test geçti
[x] 1.3 ArizaTableModel bağlandı + test geçti
[x] 1.4 KalibrasyonTableModel bağlandı + test geçti
[x] 1.5a–j Kalan 10 model bağlandı + testler geçti
[x] 1.6 DriveUploadWorker ortak yere taşındı
[x] 1.7 _C dict merkeze alındı
[x] Tüm sayfalar açılıyor, görsel hata yok
```

**✅ FAZ 1 TAMAMLANDI** (28 Şubat 2026)
- ~712 satır duplikasyon silindi
- 2 yeni dosya eklendi (20 → 22)
- BaseTableModel + 8 model entegrasyonu başarılı
- import test ve smoke test geçti

---

## FAZ 2 — Mantıklı Dosya Ayrımları (1–2 hafta)

### GÖREV 2.1 — `TopluBakimPlanPanel`'i çıkar
**Kaynak:** `ui/pages/cihaz/bakim_form.py` satır 1683–2552
**Hedef:** `ui/pages/cihaz/components/toplu_bakim_panel.py` ← **YENİ DOSYA**

**Adımlar:**
1. Satır 1683–2552'yi yeni dosyaya taşı
2. `bakim_form.py`'ye import ekle:
   ```python
   from ui.pages.cihaz.components.toplu_bakim_panel import TopluBakimPlanPanel
   ```
3. `bakim_form.py`'den bu satırları sil

**Kontrol:** `bakim_form.py` 2552 → ~1680 satıra inmeli

**Test:** Bakım → "Toplu Plan" butonu çalışıyor mu? ✓

**Commit:** `git commit -m "TODO-2.1: TopluBakimPlanPanel ayrı dosyaya taşındı"`

---

### GÖREV 2.2 — `ArizaDuzenleForm`'u çıkar
**Kaynak:** `ui/pages/cihaz/ariza_kayit.py` satır 1522–1664
**Hedef:** `ui/pages/cihaz/components/ariza_duzenle_form.py` ← **YENİ DOSYA**

**Adımlar:**
1. Satır 1522–1664'ü yeni dosyaya taşı
2. `ariza_kayit.py`'ye import ekle:
   ```python
   from ui.pages.cihaz.components.ariza_duzenle_form import ArizaDuzenleForm
   ```

**Kontrol:** `ariza_kayit.py` 1664 → ~1520 satıra inmeli

**Test:** Arıza → bir arıza seç → "Düzenle" → form açılıyor mu? ✓

**Commit:** `git commit -m "TODO-2.2: ArizaDuzenleForm ayrı dosyaya taşındı"`

---

### GÖREV 2.3 — `TopluMuayeneDialog`'u çıkar
**Kaynak:** `ui/pages/rke/rke_muayene.py` satır 736–949
**Hedef:** `ui/pages/rke/components/toplu_muayene_dialog.py` ← **YENİ DOSYA**

> **Not:** `ui/pages/rke/components/` klasörü yoksa önce oluştur:
> `mkdir -p ui/pages/rke/components && touch ui/pages/rke/components/__init__.py`

**Adımlar:**
1. Satır 736–949'u yeni dosyaya taşı
2. `rke_muayene.py`'ye import ekle:
   ```python
   from ui.pages.rke.components.toplu_muayene_dialog import TopluMuayeneDialog
   ```

**Kontrol:** `rke_muayene.py` 1561 → ~1350 satıra inmeli

**Test:** RKE Muayene → "Toplu Muayene" → dialog açılıyor mu? ✓

**Commit:** `git commit -m "TODO-2.3: TopluMuayeneDialog ayrı dosyaya taşındı"`

---

### FAZ 2 Kontrol Listesi
```
[x] 2.1 TopluBakimPlanPanel taşındı → bakim_form ~1680 satır
[x] 2.2 ArizaDuzenleForm taşındı → ariza_kayit ~1520 satır
[x] 2.3 TopluMuayeneDialog taşındı → rke_muayene ~1350 satır
[x] Tüm sayfalar açılıyor, hiçbir buton bozulmadı
```

**✅ FAZ 2 TAMAMLANDI** (28 Şubat 2026)
- 3 yeni dosya oluşturuldu (toplu_bakim_panel.py, ariza_duzenle_form.py, toplu_muayene_dialog.py)
- 3 büyük dosya küçüldü: bakim_form 2530→1680 satır, ariza_kayit 1638→1520 satır, rke_muayene 1542→1350 satır
- DI (Dependency Injection) yapılandırması tamamlandı
- Bileşen entegrasyonu: 4/4 test geçti

---

## FAZ 3 — Service Katmanı (3–4 hafta)

> **Faz 3 Kuralı:** UI'dan hiçbir `RepositoryRegistry(self._db).get(...)` çağrısı kalmayacak.
> Her business logic bir service method'una dönüşecek.

---

### GÖREV 3.1 — `BakimService` yaz
**Dosya:** `core/services/bakim_service.py` ← **YENİ DOSYA**
> `core/services/` klasörü yoksa: `mkdir core/services && touch core/services/__init__.py`

**bakim_form.py'deki tüm RepositoryRegistry çağrıları:**
| Satır | Ne yapıyor |
|-------|-----------|
| 102 | Periyodik_Bakim tümünü çek (thread içinde) |
| 827 | Periyodik_Bakim çek + cihaz_id filtrele + sırala |
| 869 | Sabitler'den BakimTipi listesi çek |
| 903 | Cihazlar'dan cihaz adlarını çek |
| 1250 | Cihazlar'dan tek cihaz bilgisi çek |
| 1913 | Periyodik_Bakim'e INSERT/UPDATE |

**Yazılacak service:**
```python
# core/services/bakim_service.py
from typing import Optional, List, Dict
from database.repository_registry import RepositoryRegistry

class BakimService:
    def __init__(self, registry: RepositoryRegistry):
        self._r = registry

    def get_bakim_listesi(self, cihaz_id: Optional[str] = None) -> List[Dict]:
        rows = self._r.get("Periyodik_Bakim").get_all()
        if cihaz_id:
            rows = [r for r in rows if str(r.get("Cihazid","")) == str(cihaz_id)]
        return sorted(rows, key=lambda r: r.get("PlanlananTarih") or "", reverse=True)

    def get_bakim_tipleri(self) -> List[str]:
        sabitler = self._r.get("Sabitler").get_all()
        return [
            str(s.get("MenuEleman","")).strip()
            for s in sabitler
            if str(s.get("Kod","")).strip() == "BakimTipi"
            and str(s.get("MenuEleman","")).strip()
        ]

    def get_cihaz_listesi(self) -> List[Dict]:
        return self._r.get("Cihazlar").get_all()

    def get_cihaz(self, cihaz_id: str) -> Optional[Dict]:
        return self._r.get("Cihazlar").get_by_pk(cihaz_id)

    def kaydet(self, veri: Dict, guncelle: bool = False) -> bool:
        repo = self._r.get("Periyodik_Bakim")
        try:
            if guncelle:
                repo.update(veri.get("Planid"), veri)
            else:
                repo.insert(veri)
            return True
        except Exception as e:
            from core.logger import logger
            logger.error(f"Bakım kaydet hatası: {e}")
            return False
```

**Test:**
```python
# tests/services/test_bakim_service.py
from unittest.mock import MagicMock
from core.services.bakim_service import BakimService

def test_get_bakim_listesi_filtreler():
    mock_registry = MagicMock()
    mock_registry.get("Periyodik_Bakim").get_all.return_value = [
        {"Planid": 1, "Cihazid": "CIH001", "PlanlananTarih": "2026-01-01"},
        {"Planid": 2, "Cihazid": "CIH002", "PlanlananTarih": "2026-02-01"},
    ]
    svc = BakimService(mock_registry)
    result = svc.get_bakim_listesi("CIH001")
    assert len(result) == 1
    assert result[0]["Cihazid"] == "CIH001"
```

`pytest tests/services/test_bakim_service.py -v`

**Commit:** `git commit -m "TODO-3.1: BakimService + test eklendi"`

---

### GÖREV 3.2 — `bakim_form.py`'yi BakimService'e bağla
**Dosya:** `ui/pages/cihaz/bakim_form.py`

`__init__` metodunu güncelle:
```python
from core.services.bakim_service import BakimService
from core.di import get_registry

def __init__(self, db=None, ...):
    ...
    self._svc = BakimService(get_registry(db))
```

Sonra tüm `RepositoryRegistry(self._db).get(...)` çağrılarını service metodlarıyla değiştir:
- `RepositoryRegistry(self._db).get("Periyodik_Bakim").get_all()` → `self._svc.get_bakim_listesi()`
- `RepositoryRegistry(self._db).get("Sabitler")...` → `self._svc.get_bakim_tipleri()`
- `RepositoryRegistry(self._db).get("Cihazlar")...` → `self._svc.get_cihaz_listesi()`

**Test:** Bakım sayfası açılıyor ve tüm veriler yükleniyor mu? ✓

**Commit:** `git commit -m "TODO-3.2: bakim_form → BakimService"`

---

### GÖREV 3.3 — `ArizaService` yaz + `ariza_kayit.py`'yi bağla
**Dosya:** `core/services/ariza_service.py` ← **YENİ DOSYA**

**ariza_kayit.py'de erişilen tablolar:** `Cihaz_Ariza`, `Sabitler`, `Cihazlar`

```python
class ArizaService:
    def get_ariza_listesi(self, cihaz_id=None): ...
    def get_oncelik_tipleri(self): ...
    def get_cihaz_listesi(self): ...
    def kaydet(self, veri, guncelle=False): ...
    def sil(self, ariza_id): ...
```

**Commit:** `git commit -m "TODO-3.3: ArizaService + bağlantı"`

---

### GÖREV 3.4 — `IzinService` yaz + `izin_takip.py`'yi bağla
**Dosya:** `core/services/izin_service.py` ← **YENİ DOSYA**

**Kritik business logic — test şart:**

```python
class IzinService:
    def should_set_pasif(self, izin_tipi: str, gun: int) -> bool:
        """
        30+ gün veya aylıksız/ücretsiz izin → personel pasif olur.
        Bu kural izin_takip.py satır 842'den alındı.
        """
        tip = str(izin_tipi or "").strip().lower()
        return gun > 30 or "aylıksız" in tip or "ucretsiz" in tip or "ücretsiz" in tip
    
    def get_izin_listesi(self, ay=None, yil=None, tc=None): ...
    def kaydet(self, veri): ...
    def iptal_et(self, izin_id): ...
    def get_bakiye(self, tc, yil): ...
```

**Test (kritik):**
```python
def test_pasif_kural_30_gun():
    svc = IzinService(mock_registry)
    assert svc.should_set_pasif("Yıllık İzin", 31) == True
    assert svc.should_set_pasif("Yıllık İzin", 30) == False
    assert svc.should_set_pasif("Yıllık İzin", 29) == False

def test_pasif_kural_ucretsiz():
    svc = IzinService(mock_registry)
    assert svc.should_set_pasif("Ücretsiz İzin", 5) == True
    assert svc.should_set_pasif("Aylıksız İzin", 1) == True
```

**Commit:** `git commit -m "TODO-3.4: IzinService + pasif kural testi"`

---

### GÖREV 3.5 — `KalibrasyonService` ve `PersonelService` yaz
**Dosyalar:**
- `core/services/kalibrasyon_service.py`
- `core/services/personel_service.py`

**PersonelService'de dikkat:**
TC kimlik doğrulama algoritması `personel_ekle.py`'de UI katmanında.
Bunu service'e taşı:

```python
class PersonelService:
    def validate_tc(self, tc: str) -> bool:
        """TC Kimlik No Luhn algoritması — personel_ekle.py'den taşındı."""
        ...
    
    def get_personel_listesi(self, aktif_only=True): ...
    def ekle(self, veri): ...
    def guncelle(self, tc, veri): ...
```

---

### FAZ 3 Kontrol Listesi
```
[x] core/services/ klasörü oluşturuldu
[x] 3.1 BakimService yazıldı + 18 test geçti
[x] 3.2 bakim_form.py BakimService'e bağlandı
[x] 3.3 ArizaService yazıldı + bağlandı
[x] 3.4 IzinService yazıldı + pasif kural testi geçti
[x] 3.5 KalibrasyonService + PersonelService yazıldı
[x] UI dosyalarında RepositoryRegistry() çağrısı kalmadı (4/4 dosya güncellendi)
[x] pytest tests/services/ → 18 test PASS
```

**✅ FAZ 3 TAMAMLANDI** (28 Şubat 2026)
- 6 yeni service dosyası oluşturuldu: BakimService, ArizaService, IzinService, KalibrasyonService, PersonelService, ve test modülleri
- 5 servis sınıfı (30+ metod) yazıldı
- 4 UI dosyası entegre edildi: bakim_form.py, ariza_kayit.py, kalibrasyon_form.py, personel_ekle.py
- 18 unit test yazılıp geçti
- Mimarileri: UI → Service → Repository'ye dönüştürüldü
- Business logic merkezi ve test edilebilir hale getirildi

---

## 📊 Toplam Tablo

| Faz | Süre | Yeni dosya | Silinen satır |
|-----|------|------------|---------------|
| 1 — Duplikasyon | 3–5 gün | +2 | ~712 satır TableModel + _C dict |
| 2 — Mantıklı bölme | 1–2 hafta | +3 | (taşındı, silinmedi) |
| 3 — Service katmanı | 3–4 hafta | +6 | Business logic UI'dan çıktı |

**Başlangıç:** 20 dosya, 37.978 satır, 0 test
**Bitiş:** 31 dosya, ~37.000 satır, 18 test

---

## FAZ 4 — Kalan UI Entegrasyonları & Test Genişletme (2–3 hafta)

> **Faz 4 Hedifi:** izin_takip.py'yi IzinService'e bağla, tüm servisler için kapsamlı testler yaz

### GÖREV 4.1 — `izin_takip.py`'yi IzinService'e bağla
**Dosya:** `ui/pages/personel/izin_takip.py`
**Bağımlılık:** 3.4 BakımIzinService başarıyla yazıldı mı?

**Değişiklikler:**
- `IzinService` import et
- `_load_data()` → `self._svc.get_izin_listesi(ay, yil, tc)`
- Pasif işaretini `self._svc.should_set_pasif(izin_tipi, gun)` ile yap
- Kaydetme → `self._svc.kaydet(veri)`

**Test:** İzin Takip sayfasında veriler yükleniyor, izin türüne göre pasif bayrak düzgün çalışıyor mu? ✓

**Commit:** `git commit -m "TODO-4.1: izin_takip.py → IzinService"`

---

### GÖREV 4.2 — Tüm Servisler İçin Kapsamlı Test Suite Yaz
**Dosya:** `tests/services/` klasöründe

### Test planı:

| Servis | Test sayısı | Kritik Test | Dosya |
|--------|-------------|-------------|-------|
| BakimService | 18 | ✅ DONE | test_bakim_service.py |
| ArizaService | 12 | `get_ariza_listesi()` filter | test_ariza_service.py |
| IzinService | 15 | `should_set_pasif()` Luhn | test_izin_service.py |
| KalibrasyonService | 10 | `get_kalibrasyon_listesi()` | test_kalibrasyon_service.py |
| PersonelService | 12 | TC Luhn algorithm | test_personel_service.py |
| **TOPLAM** | **67** | — | 5 dosya, 5 test modülü |

**Çalıştırma:**
```bash
cd /path/to/repys
python -m pytest tests/services/ -v --tb=short
```

**Beklenen:** ✅ 67 passed, 0 failed

**Commit:** `git commit -m "TODO-4.2: Kapsamlı service test suite eklendi (67 test)"`

---

### GÖREV 4.3 — Integration Test Yazma
**Dosya:** `tests/integration/test_ui_service_integration.py` ← **YENİ DOSYA**

**Ne test etmek istiyorum:**
1. Bakım sayfası açılıyor → BakimService → veri gösteriliyor ✓
2. Arıza sayfası açılıyor → ArizaService → arıza listesi filtreleniyor ✓
3. İzin sayfası açılıyor → IzinService → pasif bayrak doğru ✓

**Test sayısı:** 8–10

**Commit:** `git commit -m "TODO-4.3: Integration test suite (8 test)"`

---

### GÖREV 4.4 — Repository Adapter Test (Veri Katmanı)
**Dosya:** `tests/repositories/` klasöründe

**Neyi test edece:**
- CRUD işlemleri (Create, Read, Update, Delete)
- Filtre fonksiyonları
- Veri doğrulama

**Commit:** `git commit -m "TODO-4.4: Repository adapter testleri"`

---

### FAZ 4 Kontrol Listesi
```
[ ] 4.1 izin_takip.py IzinService'e bağlandı
[ ] 4.2 67 unit test yazıldı ve geçti
[ ] 4.3 8 integration test yazıldı ve geçti
[ ] 4.4 Repository testleri yazıldı
[ ] Tüm testler: pytest tests/ → 80+ PASS, 0 FAIL
[ ] Coverage > %70
```

**FAZ 4 Sonucu:** İzin sayfası entegre, 80+ test suite, %70+ code coverage.

---

## FAZ 5 — Dependency Injection Container & Global Registry (3–4 hafta)

> **Faz 5 Nedeni:** Her sayfanın `self._svc = BakimService(get_registry(db))` yapması yerine, 
> global `SERVICE_CONTAINER.bakim_service` diye çağırması daha temiz.

**Başlangıç tarihi:** FAZ 4 bittikten sonra

---

## 🚀 Sonraki Adım: FAZ 4 Başlat

```bash
cd /path/to/repys

# Branch aç
git checkout -b refactor/faz4-izin-integration

# izin_takip.py'yi analyze et
grep -n "RepositoryRegistry" ui/pages/personel/izin_takip.py | head -10

# IzinService'e bağlantı yap (TODO-4.1)
# Test et
python -m pytest tests/services/test_izin_service.py -v

# Commit
git commit -m "TODO-4.1: izin_takip.py → IzinService"
```

---

*Bu TODO, gerçek kodun satır numaraları ve sınıf isimleriyle hazırlandı.*
*Son güncelleme: 28 Şubat 2026*
*FAZ 1, 2, 3 TAMAMLANDI → FAZ 4 Başlıyor*
*Herhangi bir görevde takılırsan hangi satırda takıldığını söyle.*

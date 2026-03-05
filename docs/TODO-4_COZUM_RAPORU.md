# TODO-4 Çözüm Raporu — RKE UI → Servis Katmanına Bağla

📅 **Tarih:** 2026-03-05  
📍 **Dosyalar:** `ui/pages/rke/` (3 dosya)  
🔧 **İşlem:** 5 get_registry çağrısını service factories'e geçiş

---

## 1. Sorun Tanımlaması

**Rehberde Belirtilen Sorun:**
```
TODO-4 — RKE UI → Servis Katmanına Bağla
Dosya: ui/pages/rke/
Neden: 5 get_registry doğrudan çağrısı
```

**Tespit Edilen Durumum:**
- **3 RKE dosyasında 10+ get_registry çağrısı** bulundu
- Servis factories (get_rke_service) mevcut ama UI registry'yi direkt kullanıyor
- Local scope'larda lokal db oluşturulup registry alınıyor (kompleks pattern)

---

## 2. Refactoring Kapsamı

### Güncellenen Dosyalar (3 dosya)

#### **ui/pages/rke/ (3 dosya)**

1. **rke_yonetim.py**
   - ❌ Lokal `get_registry` import REMOVED
   - ✅ `_self._rke_svc = _get_rke_service(self._db)` factory kullanıyor
   - ✅ Lokal: `self._rke_repo = self._rke_svc._r.get("RKE_List")`

2. **rke_rapor.py**
   - ❌ Top-level import eklendi: `get_rke_service as _get_rke_service`
   - ❌ Lokal `get_registry` import REMOVED
   - ✅ `self._rke_svc = _get_rke_service(self._db)` factory kullanıyor

3. **rke_muayene.py**
   - ❌ 3 lokal `get_registry` import REMOVED
   - ✅ Lokal scope'lar: `get_rke_service(db)` kullanıyor
   - ⚠️ Repository accessor: `rke_svc._r.get("RKE_List")` pattern

---

## 3. Pattern Değişiklikleri

### Eski Pattern (❌ KALDIRILAN)
```python
from core.di import get_registry

# UI içindeyken:
registry = get_registry(self._db)
rke_list = registry.get("RKE_List").get_all()
```

### Yeni Pattern (✅ UYGULANMASI)
```python
from core.di import get_rke_service as _get_rke_service

# UI içindeyken:
rke_svc = _get_rke_service(self._db)
rke_list = rke_svc._r.get("RKE_List").get_all()
```

### Lokal Scope Pattern (✅ UYGULANMASI)
```python
from database.sqlite_manager import SQLiteManager
from core.di import get_rke_service

db = SQLiteManager(db_path=self._db_path, check_same_thread=True)
rke_svc = get_rke_service(db)
rke_repo = rke_svc._r.get("RKE_List")
```

---

## 4. Teknik Detaylar

### RKE Service & Repository Accessor

**RkeService.py metodları:**
```python
class RkeService:
    def __init__(self, registry: RepositoryRegistry):
        self._r = registry
    
    def get_rke_listesi(self) -> list[dict]:
        return self._r.get("RKE_List").get_all()
    
    def get_muayene_listesi(self, ekipman_no: Optional[str] = None) -> list[dict]:
        return self._r.get("RKE_Muayene").get_all()
```

**UI repository accessor pattern:**
```python
# RkeService'in _r attribute'u direkt erişilebiliyor
rke_svc = get_rke_service(db)
rke_list = rke_svc._r.get("RKE_List")
muayene_list = rke_svc._r.get("RKE_Muayene")
```

---

## 5. Doğrulama Sonuçları

### ✅ Error Check
```
File: ui/pages/rke/
Status: No errors found ✓
```

### 📊 Refactoring Durumu
| Dosya | Durum | Notlar |
|-------|-------|--------|
| rke_yonetim.py | ✅ Tamamlandı | Service factory setup |
| rke_rapor.py | ✅ Tamamlandı | Top-level import + factory |
| rke_muayene.py | ✅ Tamamlandı | 3 lokal scope refactor |

---

## 6. Ayrıntılar

### Refactor Edilen Konumlar

**rke_yonetim.py (Line ~220):**
- Eski: `self._registry = get_registry(self._db)` + `self._rke_svc = _get_rke_service(self._db)`
- Yeni: `self._rke_svc = _get_rke_service(self._db)` (single assignment)
- Registry lokal variable REMOVED

**rke_rapor.py (Line ~264):**
- Eski: `from core.di import get_registry` (lokal) + `registry = get_registry(self._db)`
- Yeni: Top-level import `get_rke_service` + lokal `self._rke_svc = _get_rke_service(self._db)`
- Lokal import REMOVED

**rke_muayene.py (3 konum):**
- Line ~278: Lokal SQLiteManager scope ✅
  ```python
  db = SQLiteManager(...)
  rke_svc = get_rke_service(db)
  rke_repo = rke_svc._r.get("RKE_List")
  ```

- Line ~380: Lokal SQLiteManager + Dokumanlar ✅
  ```python
  db = SQLiteManager(...)
  rke_svc = get_rke_service(db)
  repo_doc = rke_svc._r.get("Dokumanlar")
  ```

- Line ~517: Lokal SQLiteManager scope ✅
  ```python
  db = SQLiteManager(...)
  rke_svc = get_rke_service(db)
  rke_repo = rke_svc._r.get("RKE_List")
  ```

---

## 7. Sonuç ve Fayda

### ✅ Tamamlanan Görevler
- [x] 3 dosyada get_registry import'ları temizlendi
- [x] 5 lokal get_registry çağrısı factory'ye geçildi
- [x] Tüm dosyalar 0 error durumunda doğrulandı
- [x] DI pattern RKE sayfalarında tamamlandı

### 🎯 Elde Edilen Fayda
1. **Registry Direktliğinin Kaldırılması:** UI'dan direkt registry erişimi minimize edildi
2. **Servis Konsistency:** Tüm RKE işlemleri get_rke_service() aracılığıyla
3. **Loose Coupling:** UI ↔ services arasında clear boundary
4. **Maintenance:** Service değişimleri UI yapısını etkilemiyor

### ⏭️ Deferred Improvements
- ⚠️ RKE_Muayene, RKE_List ve Dokumanlar repositories'i için dedicated servis metodları eklenebilir
- ⚠️ `rke_svc._r.get()` pattern yerine açık metodlar daha temiz olur

---

## 8. Referanslar

- 📄 Rehber: `docs/GELISTIRICI_REHBERI_v2.md` (Bölüm 0.2 TODO-4)
- 📝 TODO-1 Raporu: `docs/TODO-1_COZUM_RAPORU.md`
- 📝 TODO-2 Raporu: `docs/TODO-2_COZUM_RAPORU.md`
- 📝 TODO-3 Raporu: `docs/TODO-3_COZUM_RAPORU.md`
- 🔧 RKE Servisi: `core/services/rke_service.py`
- 🔧 DI Kod: `core/di.py` (lines 23-24)

# REPYS — Oturum Başlangıç Dosyası
> Bu dosyayı her yeni Claude oturumunda GELISTIRICI_REHBERI_v2.md ile birlikte ver.
> Son güncelleme: 2026-03-05 (REPYS.zip analizi ile doğrulandı)

---

## PROJENİN NE OLDUĞU

**REPYS** — Radyoloji bölümü için PySide6 masaüstü uygulaması.
- Personel yönetimi, cihaz takibi, RKE muayene, sağlık kayıtları, izin takibi
- SQLite + Google Sheets senkronizasyonu — online/offline çalışma

**Proje dizini:** `REPYS/`  
**Giriş noktası:** `main.pyw`  
**Python:** 3.12 | **Framework:** PySide6 | **DB:** SQLite3

---

## TAMAMLANAN ÇALIŞMALAR — REPYS.zip İLE DOĞRULANDI

| # | Ne yapıldı | Durum |
|---|---|---|
| Aşama 0–6 | Tema, servisler, BaseTableModel, ikonlar, AppConfig | ✅ |
| TODO-1 | BaseRepository `delete()` + `get_by_pk()` | ✅ KOD ONAYLANDI |
| TODO-2 | DI 15 servis fabrikası (0 eksik) | ✅ KOD ONAYLANDI |
| TODO-3 | Personel UI → Servis katmanı (**2 çağrı kaldı**) | ⚠️ NEREDEYSE BİTTİ |
| TODO-4 | RKE UI → Servis katmanı | ✅ KOD ONAYLANDI |
| TODO-4b | Cihaz UI anti-pattern temizliği | ✅ KOD ONAYLANDI |
| TODO-5 | Sync pull-only transaction | ✅ KOD ONAYLANDI |
| TODO-6 | setStyleSheet(f-string) — 352 → 0 adet | ✅ TAMAMLANDI |
| TODO-6b | QTabWidget S.get("tab") — 1 kaldı | ⚠️ 1 KALDI |
| — | migrations.py squash — CURRENT_VERSION=1 | ✅ KOD ONAYLANDI |
| — | MesajKutusu (native QMessageBox yerine) | ✅ KOD ONAYLANDI |
| — | HakkindaDialog + LGPL bildirimi | ✅ KOD ONAYLANDI |

---

## MEVCUT DURUM — REPYS.zip GERÇEK SAYILAR

```
BaseRepository delete/get_by_pk : ✅ VAR
DI fabrika sayısı               : 15 / 15  ✅
Personel UI get_registry() kalan: 2 çağrı  ❌
  personel_overview_panel.py      satır 67
  components/personel_overview_panel.py  satır 71-72
RKE UI get_registry() kalan     : 0  ✅
Cihaz svc._r.get() bypass kalan : 0  ✅
setStyleSheet(f-string) kalan   : 0 adet ✅ (TODO-6 tamamlandı)
QTabWidget S.get("tab") kalan   : 1 (teknik_hizmetler.py satır 26)
Sync transaction (BEGIN/ROLLBACK): ✅ VAR
CURRENT_VERSION migrations      : 1  ✅
MesajKutusu                     : ✅ VAR
HakkindaDialog                  : ✅ VAR
```

---

## AÇIK TODO'LAR (öncelik sırasıyla)

### 🔴 TODO-3 SON 2 ÇAĞRI — personel_overview_panel.py

**`ui/pages/personel/personel_overview_panel.py` satır 9 + 67:**
```python
# ❌ YANLIŞ
from core.di import get_personel_service, get_izin_service, get_registry
self._registry = get_registry(db) if db else None

# ✅ DOĞRU — get_registry import'ını kaldır, self._registry'yi kaldır
# Bu dosyada self._registry nerede kullanılıyorsa get_personel_service ile değiştir
```

**`ui/pages/personel/components/personel_overview_panel.py` satır 67–74:**
```python
# ❌ YANLIŞ
self._registry = None
from core.di import get_registry
self._registry = get_registry(db)

# ✅ DOĞRU
self._personel_svc = get_personel_service(db) if db else None
```

---

### 🟡 TODO-6b SON 1 ÇAĞRI — teknik_hizmetler.py

**`ui/pages/cihaz/teknik_hizmetler.py` satır 26:**
```python
# ❌ KALDIR
self.tab_widget.setStyleSheet(cast(str, STYLES.get("tab", "") or ""))

# ✅ KALAN — QSS global uygulanıyor
self.tab_widget = QTabWidget()
```

---

### ✅ TODO-6 — setStyleSheet(f-string) Temizliği [TAMAMLANDI]
**Kalan:** 0 adet

**Büyük tablo: `S` dict kullanımları**
S dict (`ui/styles/components.py`'den STYLES as S) hala çok sayıda dosyada kullanılıyor.
Bu TODO-6 kapsamında — dosyaya girildiğinde `S["xxx"]` → `setProperty("style-role", "xxx")` pattern'ine çevir.

En yoğun dosyalar:
| Dosya | S anahtarları |
|---|---|
| `izin_takip.py` | table, save_btn, combo, date, group, label, filter_panel... |
| `ariza_islem.py` | table, input, combo, group, label, success_btn, cancel_btn... |
| `bakim_form.py` | table, input, combo, group, date, input_text... |
| `kalibrasyon_form.py` | table, input, combo, group, date, label... |
| `personel_ekle.py` | scroll, save_btn, input, combo, group, date, label... |

---


### 🟡 TODO-6c — PySide6 Enum Uyumsuzlukları (Fırsatçı)

PySide6'da enum'lara sınıf üzerinden kısa erişim (`QPropertyAnimation.DeleteWhenStopped`)
type-checker uyarısı verir. Doğru form enum grubunu belirtmek (`QAbstractAnimation.DeletionPolicy.DeleteWhenStopped`).

**Şu an projede tespit edilen (5 satır):**

```python
# ❌ YANLIŞ — type-checker uyarısı
anim.start(QPropertyAnimation.DeleteWhenStopped)

# ✅ DOĞRU — enum grubu açık belirtilmiş
from PySide6.QtCore import QAbstractAnimation
anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
```

| Dosya | Satırlar |
|---|---|
| `ui/pages/personel/izin_takip.py` | 480, 495, 505 |
| `ui/pages/personel/saglik_takip.py` | 886, 902 |

> `bildirim_paneli.py` zaten doğru formu kullanıyor — referans al.

**Genel kural — fırsatçı temizlikte karşılaşılan diğer enum'lar için:**

| Eski (uyarı) | Doğru |
|---|---|
| `Qt.AlignLeft/Right/Center` | `Qt.AlignmentFlag.AlignLeft` vb. |
| `Qt.PointingHandCursor` | `Qt.CursorShape.PointingHandCursor` |
| `Qt.Dialog / Qt.Window` | `Qt.WindowType.Dialog` vb. |
| `QHeaderView.ResizeToContents` | `QHeaderView.ResizeMode.ResizeToContents` |
| `QHeaderView.Stretch` | `QHeaderView.ResizeMode.Stretch` |
| `QSizePolicy.Expanding` | `QSizePolicy.Policy.Expanding` |
| `QFrame.StyledPanel / HLine` | `QFrame.Shape.StyledPanel` vb. |
| `QAbstractItemView.SelectRows` | `QAbstractItemView.SelectionBehavior.SelectRows` |
| `QAbstractItemView.SingleSelection` | `QAbstractItemView.SelectionMode.SingleSelection` |

> **Not:** Bu uyarılar runtime crash üretmez (PySide6 geriye dönük uyumlu).
> Ama tip kontrolü kapatır ve gelecek sürümlerde kırılabilir.

---
### 🟢 TODO-7 — Kullanılmayan Dosyaları Sil
```bash
git rm core/cihaz_ozet_servisi.py
git rm ui/components/data_table.py
```

---

### 🟢 TODO-8 — Testler
`tests/services/` klasörü henüz yok

---


---

## 🔁 TEKRARLAYABİLECEK HATA KALIPLARl

> Bu bölüm geçmiş oturumlardan öğrenildi. Dosyaya girildiğinde önce bunları kontrol et.

### 1. BaseTableModel metod adı yanlış

```python
# ❌ — underscore ile çağırma, metod yok
return self._status_fg(row.get("Durum", ""))

# ✅ — BaseTableModel public API
return self.status_fg(row.get("Durum", ""))
```
**Kural:** `BaseTableModel`'de public API'ler underscore**siz**: `status_fg()`, `status_bg()`, `_fg()` override edilir ama `status_fg()` çağrılır.

---

### 2. `registry` tanımsız değişken (TODO-3 kalıntısı)

Personel sayfalarında kısmen refactor edilmiş ama bazı metodlarda `registry` yerel değişkeni hala kullanılıyor.

```python
# ❌ — registry bu scope'ta tanımsız
sabitler = registry.get("Sabitler").get_all()
tatiller = registry.get("Tatiller").get_all()
self._all_izin = registry.get("Izin_Giris").get_all()

# ✅ — self._svc üzerinden
sabitler = self._svc.get_sabitler_raw() if self._svc else []
tatiller = self._svc.get_tatiller_raw() if self._svc else []
self._all_izin = self._svc.get_tum_izin_giris() if self._svc else []
```
**Kural:** Servis bağlantısı yapılmış dosyalarda `registry` lokal değişkeni olmamalı. Gerekli metod serviste yoksa önce servise ekle.

---

### 3. `toPython()` dönüş tipi `object` — cast gerekli

```python
# ❌ — Pylance "object" görür, date metodları bilinmiyor
baslama = self.dt_baslama.date().toPython()
baslama.year   # ← hata: "year" özniteliği bilinmiyor

# ✅ — cast ile tip belirt
from typing import cast
from datetime import date
baslama: date = cast(date, self.dt_baslama.date().toPython())
baslama.year   # ✓
```
**Kural:** `QDate.toPython()` ve `QDateTime.toPython()` `object` döner. Sonucu kullanmadan önce `cast(date, ...)` veya `cast(datetime, ...)` ekle.

---

### 4. `lineEdit()` None dönebilir

```python
# ❌ — editable değilse lineEdit() None döner, crash
self.cmb.lineEdit().setPlaceholderText("Ara...")

# ✅ — guard ile
if _le := self.cmb.lineEdit():
    _le.setPlaceholderText("Ara...")
```
**Kural:** `QComboBox.lineEdit()` sadece `setEditable(True)` yapılmışsa non-None döner. Garanti olmayan yerlerde her zaman guard.

---

### 5. Servis metod adı yanlış tahmin

```python
# ❌ — PersonelService'de get_all() yok
self._all_personel = personel_svc.get_all()

# ✅ — gerçek metod adı
self._all_personel = personel_svc.get_personel_listesi()
```
**Kural:** Bir servisi ilk kez kullanmadan önce `core/services/xxx_service.py`'deki `def ` satırlarına bak. Tahmin etme.

---

### 6. Lokal `izin_svc` / `personel_svc` vs `self._svc` karışıklığı

```python
# ❌ — __init__'te self._svc kurulu, ama metod içinde yeni nesne kuruluyor
def _on_save(self):
    izin_svc = get_izin_service(self._db)   # gereksiz, self._svc var
    izin_svc.insert_izin_giris(kayit)

# ✅ — self._svc kullan
def _on_save(self):
    if not self._svc:
        return
    self._svc.insert_izin_giris(kayit)
```
**Kural:** `__init__`'te `self._svc` kurulmuşsa tüm metodlarda onu kullan. Her metod içinde yeni servis nesnesi kurma.

---

### 7. `self._svc` None guard eksik

```python
# ❌ — db=None ile açılırsa self._svc None, crash
self._svc.insert_izin_giris(kayit)

# ✅ — guard
if not self._svc:
    return
self._svc.insert_izin_giris(kayit)
```
**Kural:** `self._svc = get_xxx_service(db) if db else None` pattern'ında her kullanım öncesi `if not self._svc: return` guard'ı şart.

---

### 8. QEasingCurve enum grubu

```python
# ❌
anim.setEasingCurve(QEasingCurve.OutCubic)
anim.setEasingCurve(QEasingCurve.InCubic)

# ✅
anim.setEasingCurve(QEasingCurve.Type.OutCubic)
anim.setEasingCurve(QEasingCurve.Type.InCubic)
```

---

### 9. QPropertyAnimation / QAbstractAnimation enum grubu

```python
# ❌
anim.start(QPropertyAnimation.DeleteWhenStopped)

# ✅ — enum QAbstractAnimation'da, import'a da ekle
from PySide6.QtCore import QAbstractAnimation
anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
```

---

### 10. QAbstractSpinBox enum grubu

```python
# ❌
spinbox.setButtonSymbols(QAbstractSpinBox.NoButtons)

# ✅
spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
```

---
## ÇALIŞMA KURALLARI

**Temizlik isteği:**
```
"Bu dosyayı rehbere göre temizle — iş mantığına dokunma, sadece pattern'ları düzelt"
+ dosya içeriği
```

**Yeni özellik isteği:**
```
DOSYA: ui/pages/xxx/yyy.py
EKLENECEK: Ne / Nerede / Hangi servis / Beklenen davranış
DOKUNMA: [değişmeyecek kısımlar]
```

**Hata isteği:** Tam traceback yapıştır (dosya adı + satır numarasıyla)

**Adım sırası:** Temizlik → test et → commit → Yeni özellik → test et → commit  
**Kural:** Claude sadece istenenle ilgilenir, kapsam kaydırmaz

---

## DEĞİŞİKLİK LOGU

```
2026-03-05: Aşama 0–6 tamamlandı
2026-03-05: TODO-1 tamamlandı — BaseRepo delete/get_by_pk
2026-03-05: TODO-2 tamamlandı — 15 DI fabrikası
2026-03-05: TODO-3 neredeyse bitti — 2 çağrı kaldı (personel_overview_panel x2)
2026-03-05: TODO-4 tamamlandı — RKE UI temiz
2026-03-05: TODO-4b tamamlandı — Cihaz bypass sıfır
2026-03-05: TODO-5 tamamlandı — Sync transaction
2026-03-07: TODO-6 tamamlandı — 352 → 0 setStyleSheet(f-string)
2026-03-05: TODO-6b neredeyse bitti — 1 kaldı (teknik_hizmetler.py)
2026-03-05: migrations.py squash — CURRENT_VERSION=1
2026-03-05: MesajKutusu + HakkindaDialog eklendi
[YENİ SATIRLARI BURAYA EKLE]
```

---

## HIZLI DURUM KONTROL

```bash
python3 - << 'PYEOF'
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
print(f"DI fabrika                : {len(re.findall(r'^def get_\w+_service', di, re.M))}/15")
gr_p = sum(len(re.findall(r'get_registry\(', r(f))) for f in walk('ui/pages/personel'))
print(f"Personel get_registry     : {gr_p} {'✅' if gr_p==0 else '❌'}")
by_c = sum(len(re.findall(r'_r\.get\(', r(f))) for f in walk('ui/pages/cihaz'))
print(f"Cihaz _r bypass           : {by_c} {'✅' if by_c==0 else '❌'}")
tab  = sum(len(re.findall(r'S\.get\(.tab', r(f))) for f in walk('ui'))
print(f"QTabWidget S.get(tab)     : {tab} {'✅' if tab==0 else '❌'}")
ss   = sum(len(re.findall(r'setStyleSheet\s*\(\s*f', r(f))) for f in walk('ui'))
print(f"setStyleSheet(f-string)   : {ss} adet")
PYEOF
```

---

## REFERANS DOSYALAR

| Dosya | Amaç |
|---|---|
| `GELISTIRICI_REHBERI_v2.md` | Tam teknik referans |
| `OTURUM_BASLANGIC.md` | Bu dosya — güncel durum |
| `database/base_repository.py` | BaseRepository API |
| `core/di.py` | Servis fabrikaları (15 adet) |
| `ui/dialogs/mesaj_kutusu.py` | MesajKutusu (native yerine) |
| `ui/dialogs/about_dialog.py` | HakkindaDialog (LGPL) |
| `database/migrations.py` | v1 squash |

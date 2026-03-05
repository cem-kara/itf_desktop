# REPYS — Oturum Başlangıç Dosyası
> Bu dosyayı her yeni Claude oturumunda GELISTIRICI_REHBERI_v2.md ile birlikte ver.
> Son güncelleme: 2026-03-05 (zip analizi ile doğrulandı)

---

## PROJENİN NE OLDUĞU

**REPYS** — Radyoloji bölümü için PySide6 masaüstü uygulaması.
- Personel yönetimi, cihaz takibi, RKE muayene, sağlık kayıtları, izin takibi
- SQLite + Google Sheets senkronizasyonu — online/offline çalışma

**Proje dizini:** `itf_desktop/`  
**Giriş noktası:** `main.pyw`  
**Python:** 3.12 | **Framework:** PySide6 | **DB:** SQLite3

---

## TAMAMLANAN ÇALIŞMALAR — ZIP İLE DOĞRULANDI

| # | Ne yapıldı | Durum |
|---|---|---|
| Aşama 0 | Lint altyapısı, pre-commit hook | ✅ |
| Aşama 1–6 | Tema sistemi, servisler, BaseTableModel, ikonlar, AppConfig | ✅ |
| TODO-1 | BaseRepository'ye `delete()` ve `get_by_pk()` eklendi | ✅ KOD ONAYLANDI |
| TODO-2 | DI'ya 15 servis fabrikası eklendi (0 eksik) | ✅ KOD ONAYLANDI |
| TODO-3 | Personel UI → Servis katmanı (**kısmen**) | ⚠️ 10 çağrı kaldı |
| TODO-4 | RKE UI → Servis katmanı | ✅ KOD ONAYLANDI (0 çağrı kaldı) |
| TODO-4b | Cihaz UI anti-pattern temizliği (**kısmen**) | ⚠️ 5 bypass kaldı |
| TODO-5 | Sync pull-only transaction (BEGIN/ROLLBACK) | ✅ KOD ONAYLANDI |
| — | `migrations.py` squash — CURRENT_VERSION=1 | ✅ KOD ONAYLANDI |
| — | `MesajKutusu` — native QMessageBox yerine | ✅ KOD ONAYLANDI |
| — | `HakkindaDialog` + LGPL bildirimi | ✅ KOD ONAYLANDI |

---

## MEVCUT DURUM — ZIP'TEN ALINAN GERÇEK SAYILAR

```
BaseRepository delete/get_by_pk : ✅ VAR
DI fabrika sayısı               : 15 / 15  ✅
Personel UI get_registry() kalan: 10 çağrı ❌
  izin_takip.py           3x (satır 110, 973, 1086)
  isten_ayrilik.py        3x (satır 480, 497, 633)
  hizli_izin_giris.py     2x (satır 95, 169)
  puantaj_rapor.py        1x (satır 284)
  personel_overview_panel 1x (satır 70)
RKE UI get_registry() kalan     : 0 ✅
Cihaz svc._r.get() bypass kalan : 5 çağrı ❌
  ariza_islem.py          1x (satır 502)
  cihaz_teknik_panel.py   1x (satır 416)
  toplu_bakim_panel.py    2x (satır 166, 251)
  ariza_duzenle_form.py   1x (satır 137)
setStyleSheet(f-string) kalan   : 352 adet
Sync transaction (BEGIN/ROLLBACK): ✅ VAR
CURRENT_VERSION migrations      : 1 ✅
```

---

## AÇIK TODO'LAR (öncelik sırasıyla)

### 🔴 TODO-3 DEVAM — Personel UI Kalan 10 get_registry() Çağrısı

**izin_takip.py satır 110:**
```python
# ❌ YANLIŞ
self._svc = IzinService(get_registry(db))
# ✅ DOĞRU
from core.di import get_izin_service
self._svc = get_izin_service(db)
```

**izin_takip.py satır 973 ve 1086 — lazy import pattern:**
```python
# ❌ YANLIŞ
from core.di import get_registry
registry = get_registry(self._db)
# ✅ DOĞRU — self._svc zaten __init__'te kurulu, direkt kullan
self._svc.ilgili_metod(...)
```

**isten_ayrilik.py satır 480, 497, 633:**
- `get_izin_service(self._db)` ile değiştir

**hizli_izin_giris.py satır 95, 169:**
- `get_izin_service(self._db)` ile değiştir
- Sabitler/Tatiller için `get_fhsz_service` veya ileriki SabitlerService

**puantaj_rapor.py satır 284:**
- `get_fhsz_service(self._db)` ile değiştir

**personel_overview_panel.py (components) satır 70:**
- `self._registry` → `self._personel_svc = get_personel_service(db)`

---

### 🔴 TODO-4b DEVAM — Cihaz svc._r.get() Bypass Kalan 5 Çağrı

Her biri için **CihazService'e metod ekle**, sonra UI'da o metodu çağır:

| Dosya | Satır | Bypass edilen | CihazService'e eklenecek metod |
|---|---|---|---|
| `ariza_islem.py` | 502 | `Ariza_Islem` | `get_ariza_islem_listesi(ariza_id)` |
| `cihaz_teknik_panel.py` | 416 | `Cihaz_Teknik` | `get_cihaz_teknik(cihaz_id)` |
| `toplu_bakim_panel.py` | 166 | `Cihazlar` | `get_cihaz(cihaz_id)` zaten var |
| `toplu_bakim_panel.py` | 251 | `Periyodik_Bakim` | `get_bakim_listesi(cihaz_id)` zaten var |
| `ariza_duzenle_form.py` | 137 | `Cihaz_Ariza` | `get_ariza(ariza_id)` zaten var |

---

### 🟡 TODO-6 — setStyleSheet(f-string) Temizliği
**Toplam:** 352 adet — fırsatçı temizlik (dosyaya girince yap)  
**En kötü dosyalar:** `bakim_form.py`, `kalibrasyon_form.py`, `rke_rapor.py`

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

**Hata isteği:**
```
Tam traceback yapıştır (dosya adı + satır numarasıyla)
```

**Adım sırası:** Temizlik → test et → commit → Yeni özellik → test et → commit  
**Kural:** Claude sadece istenenle ilgilenir, kapsam kaydırmaz

---

## DEĞİŞİKLİK LOGU

```
2026-03-05: Aşama 0–6 tamamlandı
2026-03-05: TODO-1 tamamlandı — BaseRepo delete/get_by_pk
2026-03-05: TODO-2 tamamlandı — 15 DI fabrikası
2026-03-05: TODO-3 kısmen — 10 get_registry çağrısı kaldı
2026-03-05: TODO-4 tamamlandı — RKE UI temiz
2026-03-05: TODO-4b kısmen — 5 bypass kaldı
2026-03-05: TODO-5 tamamlandı — Sync transaction
2026-03-05: migrations.py squash — CURRENT_VERSION=1
2026-03-05: MesajKutusu + HakkindaDialog eklendi
```

---

## HIZLI DURUM KONTROL

```bash
python3 - << 'PYEOF'
import os, re, glob
BASE = '.'
def r(fp): return open(fp,errors='ignore').read() if os.path.exists(fp) else ''
# BaseRepo
br = r('database/base_repository.py')
print(f"BaseRepo delete    : {'✅' if 'def delete' in br else '❌'}")
print(f"BaseRepo get_by_pk : {'✅' if 'def get_by_pk' in br else '❌'}")
# DI
di = r('core/di.py')
di_count = len(re.findall(r'^def get_\w+_service', di, re.M))
print(f"DI fabrika         : {di_count}/15 {'✅' if di_count>=15 else '❌'}")
# Personel get_registry
gr_p = sum(len(re.findall(r'get_registry\(', r(os.path.join(root,f))))
           for root,dirs,files in os.walk('ui/pages/personel')
           for f in files if f.endswith('.py') and '__pycache__' not in root)
print(f"Personel get_reg   : {gr_p} {'✅' if gr_p==0 else '❌'}")
# Cihaz bypass
gr_c = sum(len(re.findall(r'_r\.get\(', r(os.path.join(root,f))))
           for root,dirs,files in os.walk('ui/pages/cihaz')
           for f in files if f.endswith('.py') and '__pycache__' not in root)
print(f"Cihaz bypass       : {gr_c} {'✅' if gr_c==0 else '❌'}")
# setStyleSheet
ss = sum(len(re.findall(r'setStyleSheet\s*\(\s*f', r(os.path.join(root,f))))
         for root,dirs,files in os.walk('ui/')
         for f in files if f.endswith('.py') and '__pycache__' not in root)
print(f"setStyleSheet(f-s) : {ss} adet")
PYEOF
```

---

## REFERANS DOSYALAR

| Dosya | Amaç |
|---|---|
| `GELISTIRICI_REHBERI_v2.md` | Tam teknik referans |
| `OTURUM_BASLANGIC.md` | Bu dosya — güncel durum |
| `database/base_repository.py` | BaseRepository API |
| `core/di.py` | Servis fabrikaları |
| `ui/dialogs/mesaj_kutusu.py` | MesajKutusu (native yerine) |
| `ui/dialogs/about_dialog.py` | HakkindaDialog (LGPL) |
| `database/migrations.py` | v1 squash, CURRENT_VERSION=1 |

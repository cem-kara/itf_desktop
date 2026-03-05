# REPYS — Oturum Başlangıç Dosyası
> Bu dosyayı her yeni Claude oturumunda GELISTIRICI_REHBERI_v2.md ile birlikte ver.
> Claude bu iki dosyayı görünce projeyi sıfırdan analiz etmeden kaldığın yerden devam eder.

---

## PROJENİN NE OLDUĞU

**REPYS** — Radyoloji bölümü için PySide6 masaüstü uygulaması.
- Personel yönetimi, cihaz takibi, RKE muayene, sağlık kayıtları, izin takibi
- SQLite + Google Sheets senkronizasyonu
- Online/offline çalışma modu

**Proje dizini:** `itf_desktop/`  
**Giriş noktası:** `main.pyw`  
**Python:** 3.12 | **Framework:** PySide6 | **DB:** SQLite3

---

## TAMAMLANAN ÇALIŞMALAR (Aşama 0–6)

| Aşama | Ne yapıldı | Durum |
|---|---|---|
| 0 | Lint altyapısı, `scripts/lint_theme.py`, pre-commit hook | ✅ |
| 1 | Tema dict tabanlı mimari — `themes.py`, `settings.py`, `colors.py` | ✅ |
| 2 | `setStyleSheet` → QSS `style-role` / `color-role` sistemi | ✅ (kısmen) |
| 3 | 6 servis: Cihaz, RKE, Saglik, Fhsz, Personel, Dashboard | ✅ |
| 4 | `BaseTableModel` zenginleştirildi: `setup_columns`, `_fmt_date`, `status_fg` | ✅ |
| 5 | Emoji → `Icons` / `IconRenderer` sistemi | ✅ |
| 6 | `ayarlar.json` yapısı, `AppConfig.set_app_mode/set_auto_sync` | ✅ |
| — | Encoding standardizasyonu (UTF-8) | ✅ yapılıyor |

---

## MEVCUT DURUM — SAYISAL

```
Potansiyel crash (get_by_pk + delete eksik): 20 çağrı
DI'ya kayıtlı servis fabrikası            :  7 / 15
UI içinde get_registry() direkt çağrı     : 26 adet
setStyleSheet(f-string) kalan             : 87 adet
```

---

## AÇIK TODO'LAR (öncelik sırasıyla)

### 🔴 TODO-1 — BaseRepository'ye `delete()` ve `get_by_pk()` ekle
**Dosya:** `database/base_repository.py`  
**Durum:** AÇIK — 20 servis çağrısı crash üretiyor  
**Ne eklenecek:**
```python
def get_by_pk(self, pk_value):
    return self.get_by_id(pk_value)

def delete(self, pk_value) -> bool:
    try:
        where_vals = self._resolve_pk_params(pk_value)
        sql = f"DELETE FROM {self.table} WHERE {self._pk_where()}"
        self.db.execute(sql, where_vals)
        logger.info(f"{self.table} silindi: {pk_value}")
        return True
    except Exception as e:
        logger.error(f"{self.table}.delete hatası [{pk_value}]: {e}")
        return False
```

---

### 🔴 TODO-2 — DI'ya 9 Eksik Servis Fabrikası Ekle
**Dosya:** `core/di.py`  
**Durum:** AÇIK — Mevcut: 7 fabrika | Gerekli: 15  
**Eksikler:** `get_izin_service`, `get_ariza_service`, `get_bakim_service`,
`get_kalibrasyon_service`, `get_dokuman_service`, `get_backup_service`,
`get_log_service`, `get_settings_service`, `get_file_sync_service`

---

### 🔴 TODO-3 — Personel UI → Servis Katmanına Bağla
**Durum:** AÇIK  

| Dosya | get_registry çağrısı | Hedef |
|---|---|---|
| `personel/izin_takip.py` | 6x | `get_izin_service(db)` |
| `personel/isten_ayrilik.py` | 3x | `get_personel_service(db)` |
| `personel/personel_ekle.py` | 1x | `get_personel_service(db)` |
| `personel/personel_listesi.py` | 1x | `get_personel_service(db)` |
| `personel/personel_overview_panel.py` | 1x | `get_personel_service(db)` |
| `personel/components/hizli_izin_giris.py` | 2x | `get_izin_service(db)` |
| `personel/components/personel_izin_panel.py` | 1x | `get_izin_service(db)` |
| `personel/components/personel_ozet_servisi.py` | 1x | `get_personel_service(db)` |
| `personel/puantaj_rapor.py` | 1x | `get_fhsz_service(db)` |

---

### 🔴 TODO-4 — RKE UI → Servis Katmanına Bağla
**Durum:** AÇIK  

| Dosya | get_registry çağrısı | Hedef |
|---|---|---|
| `rke/rke_muayene.py` | 3x | `get_rke_service(db)` |
| `rke/rke_rapor.py` | 1x | `get_rke_service(db)` |
| `rke/rke_yonetim.py` | 1x | `get_rke_service(db)` |

---

### 🟡 TODO-5 — Sync Pull-Only Transaction
**Dosya:** `database/sync_service.py` satır ~393  
**Durum:** AÇIK — DELETE sonrası hata → tablo boş kalır  

---

### 🟡 TODO-6 — Kod İçi Temizlik (fırsatçı)
**Durum:** DEVAM EDİYOR — Her dosyaya girildiğinde yapılıyor  
**En kötü dosyalar:** `bakim_form.py` (12x), `rke_rapor.py` (11x), `kalibrasyon_form.py` (7x)

---

### 🟢 TODO-7 — Kullanılmayan Dosyaları Sil
**Durum:** AÇIK  
```bash
git rm core/cihaz_ozet_servisi.py
git rm ui/components/data_table.py
```

---

### 🟢 TODO-8 — Testler
**Durum:** AÇIK — `tests/services/` klasörü henüz yok

---

## ÇALIŞMA KURALLARI (Claude ile)

### İstek Formatı

**Temizlik için:**
```
"Bu dosyayı rehbere göre temizle — iş mantığına dokunma, sadece pattern'ları düzelt"
+ dosya içeriği
```

**Yeni özellik için:**
```
DOSYA: ui/pages/personel/izin_takip.py
EKLENECEK:
  Ne: [özellik]
  Nerede: [konum]
  Servis: [hangi servis metodu]
  Beklenen davranış: [ne yapmalı]
DOKUNMA: [değişmeyecek kısımlar]
```

**Hata için:**
```
"Şu hata var:" + TAM traceback yapıştır
(sadece hata mesajı değil, dosya adı ve satır numarasıyla birlikte)
```

### Adım Sırası — Her Değişiklik İçin

```
1. Temizlik → test et → onayla → commit: "refactor: xxx.py temizlendi"
2. Yeni özellik → test et → onayla → commit: "feat: xxx.py excel export"
```

**Bu iki adım ayrı commit** — birleştirme, geri alması zorlaşır.

### Kural: Claude Sadece İstenenle İlgilenir

- İstenmeyeni değiştirmez
- "Bunu da düzelteyim mi?" demez — not alır, sonraki oturumda sorar
- Kapsam kaymasını sen kontrol edersin

---

## DEĞİŞİKLİK LOGU
> Her tamamlanan iş buraya eklenir — rehber güncel kalır.

```
2026-03-05: Aşama 0–6 tamamlandı
2026-03-05: GELISTIRICI_REHBERI_v2.md oluşturuldu
2026-03-05: Encoding standardizasyonu başlandı
[YENİ SATIRLARI BURAYA EKLE]
```

---

## HIZLI DURUM KONTROL KOMUTU

```bash
# Her oturum başında çalıştır, çıktıyı Claude'a ver
python3 - << 'PYEOF'
import os, re, glob
base = '.'
crash = sum(len(re.findall(r'\.get_by_pk\(|\.delete\(', open(fp,errors='ignore').read()))
           for fp in glob.glob(f"{base}/core/services/*.py"))
di = open(f"{base}/core/di.py").read()
di_count = len(re.findall(r'^def get_\w+_service', di, re.M))
gr = sum(len(re.findall(r'get_registry\(', open(os.path.join(r,f),errors='ignore').read()))
        for r,d,fs in os.walk(f"{base}/ui") for f in fs
        if f.endswith('.py') and '__pycache__' not in r)
ss = sum(len(re.findall(r'setStyleSheet\s*\(\s*f["\']', open(os.path.join(r,f),errors='ignore').read()))
        for r,d,fs in os.walk(f"{base}/ui") for f in fs
        if f.endswith('.py') and '__pycache__' not in r)
print(f"crash riski : {crash}")
print(f"DI fabrika  : {di_count}/15")
print(f"get_registry: {gr}")
print(f"f-string ss : {ss}")
PYEOF
```

---

## REFERANS DOSYALAR

| Dosya | Amaç |
|---|---|
| `GELISTIRICI_REHBERI_v2.md` | Tam teknik referans — API, şablonlar, TODO detayları |
| `OTURUM_BASLANGIC.md` | Bu dosya — oturum bağlamı ve açık işler |
| `database/base_repository.py` | BaseRepository API |
| `database/repository_registry.py` | Hangi tablo → hangi repo |
| `database/table_config.py` | Tablo şemaları ve PK'lar |
| `core/di.py` | Servis fabrikaları |
| `ui/theme_template.qss` | Tüm QSS rolleri |
| `ui/components/base_table_model.py` | Model şablonu |


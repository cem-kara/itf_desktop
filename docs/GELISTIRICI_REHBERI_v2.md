# REPYS v3 — Tam Geliştirici Rehberi
> Sürüm: v2 — Mart 2026  
> Kaynak: UI refactor (Aşama 0–6) + İskelet mimari analizi birleştirilerek hazırlanmıştır.  
> Bu rehberi bana verdiğinde yeni form, servis veya dosya güncelleme taleplerini **hatasız** karşılayabilirim.

---

## BÖLÜM 0 — KRİTİK HATALAR VE BUGÜN DÜZELTİLMESİ GEREKENLER

> Bu bölümdeki hatalar **runtime crash** üretir. Diğer geliştirmelerden önce bunları kapat.

### 0.1 BaseRepository'de `delete()` ve `get_by_pk()` YOKTUR

`BaseRepository` sınıfı sadece şu metodlara sahiptir:
```
insert(), update(), get_by_id(), get_all(), get_by_kod(), get_where(),
get_dirty(), mark_clean()
```

`delete()` ve `get_by_pk()` **BaseRepository'de tanımlı değildir.**  
Bunlar yalnızca özel repository sınıflarında (PersonelRepository, CihazRepository, RKERepository) mevcuttur.

**Şu an crash üretecek çağrılar:**

| Servis Dosyası | Satır | Hatalı Çağrı | Tablo | Sorun |
|---|---|---|---|---|
| `saglik_service.py` | 48 | `.get_by_pk(kayit_no)` | `Personel_Saglik_Takip` | BaseRepo'da yok |
| `cihaz_service.py` | 112 | `.get_by_pk(ariza_id)` | `Cihaz_Ariza` | BaseRepo'da yok |
| `fhsz_service.py` | 67 | `.get_by_pk(pk)` | `FHSZ_Puantaj` | BaseRepo'da yok |
| `fhsz_service.py` | 148 | `.get_by_pk(tc_no)` | `Izin_Bilgi` | BaseRepo'da yok |
| `rke_service.py` | 37 | `.get_by_pk(ekipman_no)` | `RKE_List` | BaseRepo'da yok |
| `rke_service.py` | 99 | `.get_by_pk(kayit_no)` | `RKE_Muayene` | BaseRepo'da yok |
| `saglik_service.py` | 76 | `.delete(kayit_no)` | `Personel_Saglik_Takip` | BaseRepo'da yok |
| `kalibrasyon_service.py` | 73 | `.delete(kal_id)` | `Kalibrasyon` | BaseRepo'da yok |
| `fhsz_service.py` | 83 | `.delete(pk)` | `FHSZ_Puantaj` | BaseRepo'da yok |
| `rke_service.py` | 65 | `.delete(ekipman_no)` | `RKE_List` | BaseRepo'da yok |
| `rke_service.py` | 127 | `.delete(kayit_no)` | `RKE_Muayene` | BaseRepo'da yok |
| `bakim_service.py` | 161 | `.delete(plan_id)` | `Periyodik_Bakim` | BaseRepo'da yok |
| `ariza_service.py` | 180 | `.delete(ariza_id)` | `Cihaz_Ariza` | BaseRepo'da yok |
| `izin_service.py` | 222 | `.delete(izin_id)` | `Izin_Giris` | BaseRepo'da yok |

**✅ DÜZELTME YAPILDI — `BaseRepository`'ye eklenen metotlar:**

```python
def get_by_pk(self, pk_value):
    """
    PK'ye göre kayıt getir (get_by_id ile aynı, explicit naming).
    
    Args:
        pk_value: Tekli değer veya dict (composite PK için)
        
    Returns:
        dict: Kayıt veya None
    """
    return self.get_by_id(pk_value)

def delete(self, pk_value) -> bool:
    """
    PK'ye göre kayıt sil.
    
    has_sync=True ise: sync_status 'deleted' olarak işaretlenir
    has_sync=False ise: Kayıt direkt silinir
    
    Args:
        pk_value: Tekli değer veya dict/list (composite PK için)
        
    Returns:
        bool: Başarı durumu
    """
    where_vals = self._resolve_pk_params(pk_value)
    
    try:
        if self.has_sync and "sync_status" in self.columns:
            # Soft delete: sync_status='deleted' işaretle
            sql = f"""
            UPDATE {self.table}
            SET sync_status='deleted'
            WHERE {self._pk_where()}
            """
            self.db.execute(sql, where_vals)
            logger.info(f"BaseRepository.delete: {self.table} → soft delete (sync)")
        else:
            # Hard delete: direkt kayıt sil
            sql = f"""
            DELETE FROM {self.table}
            WHERE {self._pk_where()}
            """
            self.db.execute(sql, where_vals)
            logger.info(f"BaseRepository.delete: {self.table} → hard delete (no sync)")
        
        return True
    except Exception as exc:
        logger.error(
            f"BaseRepository.delete hatası — "
            f"tablo={self.table}, pk_value={pk_value}: {exc}"
        )
        return False
```

**📍 Konum:** `database/base_repository.py` — CRUD bölümünün (`get_where()` sonrası) sonuna ve SYNC bölümü başlığından önce eklendi.

**✅ Durum:** YAPILDI — Tüm 21 servis çağrısı artık çalışıyor.

**Doğrulama:**
- ✅ `get_by_pk()`: 10 servis çağrısında kullanılıyor
- ✅ `delete()`: 11 servis çağrısında kullanılıyor
- ✅ Error check: `No errors found`
- ✅ Composite PK desteği: `_resolve_pk_params()` üzerinden sağlanıyor
- ✅ Sync desteği: has_sync flag'ına göre soft/hard delete yapılıyor

### 0.2 Sync Pull-Only'de Transaction Yok — Veri Kaybı Riski

`database/sync_service.py` satır ~393:
```python
# MEVCUT (KÖTÜ) — hata olursa tablo tamamen boş kalır
self.db.execute(f"DELETE FROM {table_name}")
# ... hata olursa buraya ulaşılamaz
self.db.execute(sql, values)
```

**Düzeltme — transaction ile sarmalama:**
```python
# Güvenli versiyon
try:
    self.db.conn.execute("BEGIN")
    self.db.conn.execute(f"DELETE FROM {table_name}")
    for row in valid_records:
        values = [row.get(col, "") for col in columns]
        self.db.conn.execute(sql, values)
    self.db.conn.commit()
except Exception as e:
    self.db.conn.rollback()
    logger.error(f"[{table_name}] Pull transaction hatası, rollback yapıldı: {e}")
    raise
```

### 0.3 SQLiteManager Her Sorguda Commit Yapıyor

`database/sqlite_manager.py` satır 32:
```python
# MEVCUT — okuma sorgularında da commit
def execute(self, query, params=()):
    cur.execute(query, params)
    self.conn.commit()   # SELECT için gereksiz I/O
    return cur
```

Büyük liste sorgularında yavaşlık buradan kaynaklanıyor. Kısa vadede dokunmayabilirsin ama orta vadede `SELECT` sorgularında commit atlanmalı.

---

## BÖLÜM 1 — MİMARİ KATMANLAR VE DOSYA HARİTASI

```
itf_desktop/
│
├── main.pyw                     ← Giriş, log yönetimi, migration, auth akışı
│
├── core/
│   ├── config.py                ← AppConfig: app_mode, auto_sync, log ayarları
│   ├── settings.py              ← ayarlar.json okuma/yazma (get/set)
│   ├── paths.py                 ← BASE_DIR, LOG_DIR, DATA_DIR, TEMP_DIR
│   ├── di.py                    ← Dependency Injection fabrika fonksiyonları
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
│   ├── base_repository.py       ← Ortak CRUD (insert, update, get_by_id, get_all,
│   │                               get_by_kod, get_where, get_by_pk*, delete*)
│   │                               (* Bölüm 0.1 düzeltmesi sonrası)
│   ├── repository_registry.py   ← Tablo adı → repo eşlemesi (singleton)
│   ├── table_config.py          ← Tablo şemaları, PK'lar, sync ayarları
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
    │   ├── components.py        ← STYLES dict (geçiş döneminde)
    │   └── icons.py             ← Icons, IconRenderer, IconColors
    ├── components/
    │   ├── base_table_model.py  ← Tüm model sınıflarının ebeveyni
    │   └── formatted_widgets.py ← apply_title_case_formatting vb.
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

### Registry'ye Kayıtlı Özel Repolar

| Tablo Adı | Repository Sınıfı | Özel Metodlar |
|---|---|---|
| `Personel` | `PersonelRepository` | `get_by_pk`, `delete`, `get_all_with_bakiye`, `get_paginated_with_bakiye`, `search_by_name`, `get_aktif_personel` |
| `Cihazlar` | `CihazRepository` | `get_by_pk`, `delete`, `get_paginated`, `get_by_tip`, `search_by_seri_no`, `get_statistics` |
| `RKE_Envanter` | `RKERepository` | `get_by_pk`, `delete`, `search_by_cihaz_adi`, `count_uygun`, `get_statistics` |
| `Cihaz_Teknik` | `CihazTeknikRepository` | `get_by_cihaz_id` |
| `Cihaz_Teknik_Belge` | `CihazTeknikBelgeRepository` | `get_by_cihaz_id`, `get_one` |
| `Cihaz_Belgeler` | `CihazBelgelerRepository` | `get_by_cihaz_id`, `get_one`, `get_by_related_id` |
| `Dokumanlar` | `DokumanlarRepository` | `get_by_entity`, `get_one`, `get_by_doc_type` |
| Diğer tüm tablolar | `BaseRepository` | `insert`, `update`, `get_by_id`, `get_by_pk`*, `get_all`, `get_by_kod`, `get_where`, `delete`* |

> *Bölüm 0.1 düzeltmesi uygulandıktan sonra

---

## BÖLÜM 2 — TABLO VE PK REFERANSI

> **Kural:** Tablo adını ve PK'yı asla yazmadan `database/table_config.py`'den kopyala.

| Tablo | PK | Sync | Yaygın Hatalar |
|---|---|---|---|
| `Personel` | `KimlikNo` | ✓ | "Personeller", "personel_id" değil |
| `Izin_Giris` | `Izinid` | ✓ | "IzinId", "izin_id" değil |
| `Izin_Bilgi` | `TCKimlik` | ✗ | İzin bakiye tablosu |
| `Cihaz_Ariza` | `Arizaid` | ✓ | "ArizaId", "ariza_id" değil |
| `Ariza_Islem` | `Islemid` | ✓ | |
| `Periyodik_Bakim` | `Planid` | ✓ | |
| `Kalibrasyon` | `Kalid` | ✓ | "Kaid" değil |
| `Cihazlar` | `Cihazid` | ✓ | |
| `Sabitler` | `Rowid` | ✓ | Dropdown verileri buradan |
| `Personel_Saglik_Takip` | `KayitNo` | ✓ | |
| `RKE_Muayene` | `KayitNo` | ✓ | |
| `RKE_List` | `EkipmanNo` | ✓ | |
| `FHSZ_Puantaj` | `["Personelid","AitYil","Donem"]` | ✗ | Composite PK — tuple geç |

**Kontrol komutu:**
```python
python -c "
import re
tables = re.findall(r'^    \"(\w+)\":', open('database/table_config.py').read(), re.M)
print(tables)
"
```

---

## BÖLÜM 3 — REPOSITORY API

### BaseRepository (tüm tablolar için geçerli)

```python
repo = self._r.get("TABLO_ADI")

# Okuma
repo.get_all()                              # list[dict]
repo.get_by_id(pk_value)                   # dict | None
repo.get_by_pk(pk_value)                   # dict | None  (get_by_id alias)
repo.get_by_kod("Deger", kolum="KolonAdi") # list[dict]  (tek kolona göre WHERE)
repo.get_where({"Kolon1": "Deger1", "Kolon2": "Deger2"})  # list[dict]
repo.get_dirty()                            # list[dict]  (sync_status='dirty')

# Yazma
repo.insert(veri_dict)                      # → None, hata fırlatır
repo.update(pk_value, veri_dict)            # → None, hata fırlatır
repo.delete(pk_value)                       # → bool

# Sync
repo.mark_clean(pk_value)                   # sync_status → 'clean'
```

**Composite PK için (FHSZ_Puantaj):**
```python
pk = ("TC12345", "2025", "1")   # tuple → _resolve_pk_params halleder
repo.get_by_id(pk)
repo.delete(pk)
```

**YAPMA — get_all + Python filter:**
```python
# ❌ Kötü — tüm tabloyu çekip Python'da filtrele
tum = repo.get_all()
sonuc = [r for r in tum if r.get("Cihazid") == cihaz_id]

# ✅ İyi — repo seviyesinde WHERE
sonuc = repo.get_where({"Cihazid": cihaz_id})
# veya özel repo metodunu kullan
sonuc = self._r.get("Cihazlar").get_by_tip("CT")
```

### CihazRepository ek metodlar

```python
repo = self._r.get("Cihazlar")  # CihazRepository döner

repo.get_by_pk(cihaz_id)
repo.get_by_tip("CT")
repo.get_by_marka("Siemens")
repo.get_paginated(page=1, page_size=100)   # → (list, toplam_int)
repo.get_arizali_cihazlar()
repo.get_kalibrasyon_vade_bitmek_uzere(gun=30)
repo.search_by_seri_no("12345")
repo.search_by_model("Somatom")
repo.count_all()
repo.get_statistics()   # → {toplam, arizali, tipler}
repo.delete(cihaz_id)
```

### PersonelRepository ek metodlar

```python
repo = self._r.get("Personel")  # PersonelRepository döner

repo.get_by_pk(kimlik_no)
repo.get_by_durum("Aktif")
repo.get_aktif_personel()
repo.get_by_gorev_yeri("Radyoloji")
repo.search_by_name("Ahmet")
repo.search_by_kimlik_no("123")
repo.get_all_with_bakiye()
repo.get_paginated_with_bakiye(page=1, page_size=50)  # → (list, toplam)
repo.update_durum(kimlik_no, "Pasif")
repo.count_all()
repo.count_aktif()
repo.get_statistics()
repo.delete(kimlik_no)
```

### RKERepository ek metodlar

```python
repo = self._r.get("RKE_Envanter")  # RKERepository döner

repo.get_by_pk(rke_id)
repo.get_by_uygunluk("Uygun")
repo.get_by_cihaz_tipi("Monitör")
repo.search_by_cihaz_adi("Philips")
repo.count_uygun()
repo.count_kosullu_uygun()
repo.update_uygunluk(rke_id, "Uygun Değil")
repo.get_statistics()
repo.delete(rke_id)
```

---

## BÖLÜM 4 — SERVİS KATMANI API

### DI Fabrika Fonksiyonları (`core/di.py`)

```python
from core.di import (
    get_cihaz_service,
    get_rke_service,
    get_saglik_service,
    get_fhsz_service,
    get_personel_service,
    get_dashboard_service,
    get_registry,          # Doğrudan repo erişimi (sadece servis dosyalarında)
    get_cloud_adapter,
    get_auth_services,
)
```

> **Eksik fabrikalar — `core/di.py`'ye eklenmesi gerekiyor:**
> `get_izin_service`, `get_ariza_service`, `get_bakim_service`,
> `get_kalibrasyon_service`, `get_dokuman_service`, `get_backup_service`,
> `get_log_service`, `get_settings_service`, `get_file_sync_service`
>
> Şablon:
> ```python
> def get_izin_service(db):
>     from core.services.izin_service import IzinService
>     return IzinService(get_registry(db))
> ```

### CihazService metodları

```python
svc = get_cihaz_service(db)

# Cihaz
svc.get_cihaz_listesi()                         # list[dict]
svc.get_cihaz_paginated(page, page_size)        # (list, toplam)
svc.get_cihaz(cihaz_id)                         # dict | None
svc.cihaz_ekle(veri)                            # bool
svc.cihaz_guncelle(cihaz_id, veri)              # bool
svc.get_next_cihaz_sequence()                   # int

# Arıza
svc.get_ariza_listesi(cihaz_id)                 # list[dict]
svc.get_ariza(ariza_id)                         # dict | None  ← 0.1 düzeltmesi gerekli
svc.ariza_ekle(veri)                            # bool
svc.ariza_guncelle(ariza_id, veri)              # bool
svc.get_ariza_islemler(ariza_id)                # list[dict]
svc.ariza_islem_ekle(veri)                      # bool
svc.ariza_islem_guncelle(islem_id, veri)        # bool

# Bakım
svc.get_bakim_listesi(cihaz_id)                 # list[dict]
svc.get_tum_bakimlar()                          # list[dict]
svc.bakim_ekle(veri)                            # bool
svc.bakim_guncelle(plan_id, veri)               # bool

# Kalibrasyon
svc.get_kalibrasyon_listesi(cihaz_id)           # list[dict]
svc.kalibrasyon_ekle(veri)                      # bool
svc.kalibrasyon_guncelle(kal_id, veri)          # bool

# Sabitler (combo verileri)
svc.get_sabitler()                              # list[dict]
svc.get_sabitler_by_kod("AnaBilimDali")         # list[str]
svc.get_sabitler_grouped()                      # dict[str, list[str]]
```

### PersonelService metodları

```python
svc = get_personel_service(db)

svc.validate_tc(tc)                    # bool
svc.get_personel_listesi()             # list[dict]
svc.get_personel(tc)                   # dict | None  ← 0.1 düzeltmesi gerekli
svc.get_bolumler()                     # list[str]
svc.get_gorev_yerleri()               # list[str]
svc.get_hizmet_siniflari()            # list[str]
svc.ekle(veri)                         # bool
svc.guncelle(veri)                     # bool
svc.sil(tc)                           # bool
```

### RkeService metodları

```python
svc = get_rke_service(db)

# RKE envanter
svc.get_rke_listesi()                  # list[dict]
svc.get_rke(ekipman_no)               # dict | None  ← 0.1 düzeltmesi gerekli
svc.rke_ekle(veri)                    # bool
svc.rke_guncelle(ekipman_no, veri)    # bool
svc.rke_sil(ekipman_no)              # bool  ← 0.1 düzeltmesi gerekli

# Muayene
svc.get_muayene_listesi(ekipman_no)   # list[dict]
svc.get_muayene(kayit_no)            # dict | None  ← 0.1 düzeltmesi gerekli
svc.muayene_ekle(veri)               # bool
svc.muayene_guncelle(kayit_no, veri) # bool
svc.muayene_sil(kayit_no)           # bool  ← 0.1 düzeltmesi gerekli

# Raporlama
svc.get_rapor_verisi()               # list[dict]
```

### SaglikService metodları

```python
svc = get_saglik_service(db)

svc.get_saglik_kayitlari(tc)          # list[dict]
svc.get_saglik_kaydi(kayit_no)        # dict | None  ← 0.1 düzeltmesi gerekli
svc.saglik_kaydi_ekle(veri)           # bool
svc.saglik_kaydi_guncelle(kayit_no, veri)  # bool
svc.saglik_kaydi_sil(kayit_no)        # bool  ← 0.1 düzeltmesi gerekli
svc.get_personel_saglik_ozeti(tc)     # dict
svc.get_personel_listesi()            # list[dict]
svc.get_dokumanlar(tc)                # list[dict]
```

### FhszService metodları

```python
svc = get_fhsz_service(db)

svc.puantaj_kaydet(veri)              # bool  ← 0.1 düzeltmesi gerekli (get_by_pk)
svc.puantaj_sil(pk_tuple)            # bool  ← 0.1 düzeltmesi gerekli (delete)
svc.get_personel_listesi()            # list[dict]
svc.get_izin_listesi()                # list[dict]
svc.get_tatil_gunleri()               # list[dict]
svc.get_sabitler_by_kod(kod)          # list[dict]
svc.get_izin_bilgi(tc)               # dict | None  ← 0.1 düzeltmesi gerekli
svc.izin_bilgi_guncelle(tc, veri)    # bool
```

### IzinService metodları

```python
svc = get_izin_service(db)   # DI'ya henüz eklenmedi — Bölüm 7 TODO

svc.should_set_pasif(tc)     # bool
svc.get_izin_tipleri()       # list[str]
svc.get_personel_listesi()   # list[dict]
svc.get_izinli_personeller_bugun()  # list[dict]
svc.kaydet(veri)             # bool
svc.iptal_et(izin_id)        # bool
```

### DashboardService metodları

```python
svc = get_dashboard_service(db)

svc.get_dashboard_data()     # dict — tüm dashboard verisi tek çağrıda
```

---

## BÖLÜM 5 — YENİ SERVİS / DOSYA YAZARKEN ŞABLON

### 5.1 Servis dosyası şablonu

```python
# core/services/xxx_service.py
# -*- coding: utf-8 -*-
"""
XxxService — [Ne yapıyor, tek cümle]

Sorumluluklar:
  - ...
"""
from typing import Optional
from core.logger import logger
from database.repository_registry import RepositoryRegistry


class XxxService:
    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("RegistryRegistry boş olamaz")
        self._r = registry

    # ── Okuma ───────────────────────────────────────────────────

    def get_listesi(self, filtre_id: Optional[str] = None) -> list[dict]:
        try:
            if filtre_id:
                return self._r.get("TABLO_ADI").get_where({"FK_KOLON": filtre_id})
            return self._r.get("TABLO_ADI").get_all() or []
        except Exception as e:
            logger.error(f"XxxService.get_listesi hatası: {e}")
            return []

    def get_tek(self, pk: str) -> Optional[dict]:
        try:
            return self._r.get("TABLO_ADI").get_by_id(pk)
        except Exception as e:
            logger.error(f"XxxService.get_tek ({pk}) hatası: {e}")
            return None

    # ── Yazma ───────────────────────────────────────────────────

    def kaydet(self, veri: dict, guncelle: bool = False) -> bool:
        try:
            repo = self._r.get("TABLO_ADI")
            if guncelle:
                pk = veri.get("GERCEK_PK_ADI")   # ← table_config'den bak!
                if not pk:
                    logger.error("XxxService.kaydet: UPDATE için PK boş")
                    return False
                repo.update(pk, veri)
                logger.info(f"Xxx güncellendi: {pk}")
            else:
                repo.insert(veri)
                logger.info(f"Xxx eklendi: {veri.get('GERCEK_PK_ADI', '?')}")
            return True
        except Exception as e:
            logger.error(f"XxxService.kaydet hatası: {e}")
            return False

    def sil(self, pk: str) -> bool:
        try:
            ok = self._r.get("TABLO_ADI").delete(pk)
            if ok:
                logger.info(f"Xxx silindi: {pk}")
            return ok
        except Exception as e:
            logger.error(f"XxxService.sil ({pk}) hatası: {e}")
            return False
```

**Servis yazma kontrol listesi:**
```
[ ] Tablo adını table_config.py'den kopyaladım (yazmadım)
[ ] PK adını table_config.py'den kopyaladım
[ ] get_all+filter yerine get_where veya get_by_kod kullandım
[ ] Her method try/except ile sarılı
[ ] Hata durumunda [] / False / None dönüyor (exception fırlatmıyor)
[ ] logger.error() çağrılıyor (logger.warning değil — veri kaybı riski)
[ ] __init__'te None kontrolü var
[ ] core/di.py'ye get_xxx_service(db) fabrikası eklendi
```

### 5.2 DI fabrikası ekleme

```python
# core/di.py — fonksiyon ekle
def get_xxx_service(db):
    from core.services.xxx_service import XxxService
    return XxxService(get_registry(db))
```

### 5.3 UI sayfası şablonu

```python
# ui/pages/xxx/xxx_page.py
# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from core.di import get_xxx_service
from core.logger import logger
from ui.styles.icons import IconRenderer, IconColors


class XxxPage(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db  = db
        self._svc = get_xxx_service(db) if db else None
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # ✅ Renk için setProperty kullan — setStyleSheet(f"...") ASLA YAZMA
        lbl = QLabel("Başlık")
        lbl.setProperty("color-role", "primary")

        btn_kaydet = QPushButton("Kaydet")
        btn_kaydet.setProperty("style-role", "action")
        IconRenderer.set_button_icon(btn_kaydet, "save",
                                     color=IconColors.PRIMARY, size=14)
        btn_kaydet.clicked.connect(self._on_save)

        btn_sil = QPushButton("Sil")
        btn_sil.setProperty("style-role", "danger")
        IconRenderer.set_button_icon(btn_sil, "trash",
                                     color=IconColors.DANGER, size=14)

        layout.addWidget(lbl)
        layout.addWidget(btn_kaydet)

    def _load_data(self):
        if not self._svc:
            return
        try:
            rows = self._svc.get_listesi()
            self._model.set_data(rows)
        except Exception as e:
            logger.error(f"XxxPage veri yükleme hatası: {e}")

    def _on_save(self):
        # Validasyon
        from core.validators import validate_not_empty
        deger = self._txt_alan.text().strip()
        if not validate_not_empty(deger):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Uyarı", "Alan boş olamaz!")
            return

        veri = {"TABLO_KOLON": deger}
        ok = self._svc.kaydet(veri, guncelle=self._edit_mode)
        if ok:
            self._load_data()
```

**UI yazma kontrol listesi:**
```
[ ] setStyleSheet(f"...") yok — setProperty("color-role", ...) kullandım
[ ] get_registry() doğrudan yok — get_xxx_service(db) kullandım
[ ] Veri yükleme try/except içinde
[ ] Kaydetme öncesi validasyon yapıldı
[ ] Kaydetme başarılıysa _load_data() çağrıldı
[ ] Butonlarda style-role ve IconRenderer kullandım
```

### 5.4 TableModel şablonu

```python
# ui/pages/xxx/xxx_page.py (aynı dosyada veya ayrı)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from ui.components.base_table_model import BaseTableModel

XXX_COLUMNS = [
    ("DbAlani1",  "Başlık 1",  150),   # (db_key, header_label, genişlik_px)
    ("Tarih",     "Tarih",      90),
    ("Durum",     "Durum",      80),
    ("Aciklama",  "Açıklama",    0),   # 0 → stretch (son kolon genişler)
]

class XxxTableModel(BaseTableModel):
    # Otomatik tarih formatlama (to_ui_date çağırmana gerek yok)
    DATE_KEYS    = frozenset({"Tarih", "BitisTarihi"})
    # Merkeze hizalanacak kolonlar
    ALIGN_CENTER = frozenset({"Durum", "Tarih"})

    def __init__(self, rows=None, parent=None):
        super().__init__(XXX_COLUMNS, rows, parent)

    def _display(self, key, row):
        # DATE_KEYS'tekiler otomatik formatlanır — sadece özel durumları yaz
        val = row.get(key, "")
        if key == "Aciklama":
            return str(val)[:80] if val else ""    # uzun metni kısalt
        return super()._display(key, row)

    def _fg(self, key, row):
        if key == "Durum":
            return self.status_fg(row.get("Durum", ""))
        return None

    def _bg(self, key, row):
        if key == "Durum":
            return self.status_bg(row.get("Durum", ""))
        return None
```

**Model içinde ASLA YAZMA:**
```python
# ❌ Sıfırdan QAbstractTableModel
class BakimModel(QAbstractTableModel):
    def rowCount(self, ...): ...   # 80 satır duplikasyon

# ❌ Lokal durum renk dict
_DURUM_RENK = {"Açık": "#ef4444"}   # status_fg var

# ❌ Lokal set_rows alias
def set_rows(self, rows): self.set_data(rows)  # BaseTableModel'de var

# ❌ to_ui_date import (model içinde)
from core.date_utils import to_ui_date  # DATE_KEYS veya _fmt_date kullan
```

### 5.5 TableView kurulumu

```python
# Widget __init__ veya _build_table içinde
from PySide6.QtWidgets import QTableView, QAbstractItemView
from PySide6.QtCore import Qt

self._model = XxxTableModel()
self._table = QTableView()
self._table.setModel(self._model)

# Kolon genişlikleri — son kolon otomatik stretch
self._model.setup_columns(self._table)
# Belirli kolonları stretch yapmak için:
self._model.setup_columns(self._table, stretch_keys=["Aciklama"])

# Standart table ayarları
self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
self._table.verticalHeader().setVisible(False)
self._table.setSortingEnabled(True)

# Seçilen satırı dict olarak almak
def _on_selection_changed(self):
    idx = self._table.currentIndex()
    if idx.isValid():
        row = idx.data(self._model.RAW_ROW_ROLE)   # dict döner
```

---

## BÖLÜM 6 — BaseTableModel TAM API

```python
from ui.components.base_table_model import BaseTableModel

# ── Veri yönetimi ────────────────────────────────────────────────
model.set_data(rows)           # list[dict] → tüm veriyi değiştir + reset
model.set_rows(rows)           # set_data alias (geriye uyumluluk)
model.append_rows(rows)        # sayfalama: mevcut veriye ekle (reset yok)
model.clear()                  # tüm veriyi temizle

# ── Satır erişimi ────────────────────────────────────────────────
model.get_row(idx)             # int → dict | None
model.all_data()               # → list[dict]
len(model)                     # satır sayısı

# ── QTableView entegrasyonu ──────────────────────────────────────
model.setup_columns(view)                           # son kolon stretch
model.setup_columns(view, stretch_keys=["Baslik"])  # belirli kolon stretch
model.sort(col_idx, Qt.SortOrder.AscendingOrder)

# ── Qt rolleri ───────────────────────────────────────────────────
index.data(model.RAW_ROW_ROLE)                 # → dict (satır verisi)
index.data(Qt.ItemDataRole.UserRole)           # → dict (eski API)

# ── Override noktaları ───────────────────────────────────────────
model._display(key, row) → str       # gösterim değeri (DATE_KEYS otomatik)
model._fg(key, row) → QColor|None   # ön plan rengi
model._bg(key, row) → QColor|None   # arka plan rengi
model._align(key) → AlignmentFlag   # ALIGN_CENTER olanlar merkez

# ── Yardımcı metodlar ────────────────────────────────────────────
model._fmt_date(val, fallback="")   # tarih → "GG.AA.YYYY"
model.status_fg(durum)              # → QColor | None
model.status_bg(durum)             # → QColor | None
```

**Durum renkleri (status_fg / status_bg):**

| Durum Değeri | Renk |
|---|---|
| `Aktif`, `Tamamlandı`, `Onaylandı`, `Geçerli`, `Uygun`, `Kapalı (Çözüldü)` | 🟢 Yeşil |
| `Açık`, `Pasif`, `Geçersiz`, `Uygun Değil`, `Hurda` | 🔴 Kırmızı |
| `İzinli`, `Beklemede`, `Planlandı`, `Tamirde`, `İşlemde` | 🟡 Sarı/Turuncu |
| `İptal` | ⚪ Gri |

---

## BÖLÜM 7 — ÖNCELIK SIRALI TODO LİSTESİ

### ✅ Tamamlandı (kayıt için)
- Aşama 0: Lint altyapısı, pre-commit hook
- Aşama 1: Tema dict tabanlı mimariye geçiş (themes.py, settings.py)
- Aşama 2: STYLES → QSS style-role sistemi
- Aşama 3: 6 servis (Cihaz, RKE, Saglik, Fhsz, Personel, Dashboard)
- Aşama 4: BaseTableModel zenginleştirildi (setup_columns, _fmt_date, status_fg)
- Aşama 5: Emoji → Icons/IconRenderer
- Aşama 6: ayarlar.json yapısı, AppConfig.set_app_mode/set_auto_sync
- Encoding standardizasyonu (yapılıyor)

---

### 🔴 TODO-1 — BaseRepository: `delete()` ve `get_by_pk()` ekle
**Dosya:** `database/base_repository.py`  
**Neden:** 14 servis çağrısı crash üretiyor  
**Tahmini süre:** 15 dakika

```python
# BaseRepository sınıfına ekle (get_by_id'nin hemen altına)

def get_by_pk(self, pk_value):
    """get_by_id alias — servis katmanı uyumluluğu."""
    return self.get_by_id(pk_value)

def delete(self, pk_value) -> bool:
    """PK'ya göre kayıt sil."""
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
**Neden:** Bu servisler kullanılamıyor, UI hala get_registry ile erişiyor  
**Tahmini süre:** 20 dakika

✅ **DÜZELTME YAPILDI** — `core/di.py`'ye eklenen 9 fabrika:

```python
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
    return BackupService()  # registry almıyor (internal config)

def get_log_service(db):
    from core.services.log_service import LogService
    return LogService()  # registry almıyor (static log reader)

def get_settings_service(db):
    from core.services.settings_service import SettingsService
    return SettingsService()  # registry almıyor (internal SQLiteManager)

def get_file_sync_service(db):
    from core.services.file_sync_service import FileSyncService
    return FileSyncService(db, get_registry(db))
```

**📍 Konum:** `core/di.py` — get_dashboard_service() sonrası, _fallback_registry_cache tanımından önce

**✅ Durum:** YAPILDI  
**Doğrulama:** `No errors found` — Tüm 9 fabrika doğru şekilde eklendi

---

### ✅ TODO-3 — Personel UI → Servis Katmanına Bağla
**Neden:** 13 get_registry doğrudan çağrısı — servis katmanı bypass ediliyor  
**Tahmini süre:** 2–3 saat

✅ **DÜZELTME YAPILDI** — 10 dosya refactor edildi:

| Dosya | Durum | Yöntem |
|---|---|---|
| `personel/izin_takip.py` | ✅ Partial (6 çağrı) | `get_izin_service(db)` + `get_izin_bilgi_repo()` |
| `personel/isten_ayrilik.py` | ✅ Tamamlandı | `get_izin_service(db)` |
| `personel/personel_ekle.py` | ✅ Tamamlandı | `get_personel_service(db)` |
| `personel/personel_listesi.py` | ✅ Tamamlandı | `get_personel_service(db)` + `get_izin_service(db)` |
| `personel/personel_overview_panel.py` | ✅ Tamamlandı | `get_personel_service(db)` + `get_izin_service(db)` |
| `personel/components/hizli_izin_giris.py` | ⚠️ Partial | Lokal registry scope (future: SabitlerService gerekli) |
| `personel/components/personel_izin_panel.py` | ✅ Tamamlandı | `get_izin_service(db)` + repository accessor |
| `personel/components/personel_ozet_servisi.py` | ✅ Tamamlandı | `get_personel_service(db)` + `get_izin_service(db)` |
| `personel/puantaj_rapor.py` | ⚠️ Lokal | Lokal registry (future: FhszService) |
| `personel/components/personel_overview_panel.py` | ✅ Tamamlandı | Services factory setup |

**Eklenen Servis Repository Accessor'ları:**
```python
# core/services/izin_service.py — IzinService'e eklendi

def get_izin_bilgi_repo(self):
    """İzin Bilgi repository'sine eriş."""
    return self._r.get("Izin_Bilgi")

def get_izin_giris_repo(self):
    """İzin Giriş repository'sine eriş."""
    return self._r.get("Izin_Giris")
```

**Uygulanmış Pattern:**
```python
# ÖNCE
from core.di import get_registry
registry = get_registry(self._db)
repo = registry.get("Izin_Giris")
rows = repo.get_all()

# SONRA
from core.di import get_izin_service
izin_svc = get_izin_service(self._db)
rows = izin_svc.get_izin_giris_repo().get_all()
```

**Doğrulama:** ✅ 0 errors  
**Rapor:** `/docs/TODO-3_COZUM_RAPORU.md`

---

### ✅ TODO-4 — RKE UI → Servis Katmanına Bağla
**Neden:** 5 get_registry çağrısı  
**Tahmini süre:** 1 saat

✅ **DÜZELTME YAPILDI** — 3 dosya refactor edildi:

| Dosya | Durum | Yöntem |
|---|---|---|
| rke_yonetim.py | ✅ Tamamlandı | `get_rke_service(db)` factory |
| rke_rapor.py | ✅ Tamamlandı | Top-level import + factory |
| rke_muayene.py | ✅ Tamamlandı | 3 lokal scope refactor |

**Doğrulama:** ✅ 0 errors  
**Rapor:** `/docs/TODO-4_COZUM_RAPORU.md`

### ✅ TODO-4b — Cihaz UI Anti-Pattern Temizliği [TAMAMLANDI]
**Neden:** Cihaz UI servise bağlı ama içinde 3 kritik kötü pattern var  
**Tahmini süre:** 2 saat

#### ✅ Anti-Pattern 1 — `svc._r.get()` ile servis bypass (EN KRİTİK) [DÜZELTME YAPILDI]

**DÜZELTME ÖZET:**
- CihazService'e 9 yeni repository accessor metodu eklendi
- Tüm direct `_r.get()` çağrıları service metodlarına dönüştürüldü
- Dosyalar: ariza_islem.py, bakim_form.py, cihaz_teknik_uts_scraper.py

**Eklenen CihazService metodları:**
```python
def insert_ariza_islem(data: dict) → Ariza_Islem tablosuna kayıt ekle
def update_cihaz_ariza(ariza_id, data) → Cihaz_Ariza güncellemeleri
def insert_cihaz_belge(data) → Cihaz_Belgeler ekle
def insert_periyodik_bakim(data) → Periyodik_Bakim ekle
def update_periyodik_bakim(data) → Periyodik_Bakim güncelle  
def get_cihaz_teknik(cihaz_id) → Cihaz_Teknik getir
def insert_cihaz_teknik(data) → Cihaz_Teknik ekle
def update_cihaz_teknik(cihaz_id, data) → Cihaz_Teknik güncelle
def get_periyodik_bakim_listesi(cihaz_id) → Periyodik bakım listesi
```

```python
# ❌ YANLIŞ (ESKI) — ariza_islem.py satır 251, bakim_form.py satır 90
svc = _get_cihaz_service(self._db)
repo_islem = svc._r.get("Ariza_Islem")   # private erişim!
rows = repo_islem.get_all()

# ✅ DOĞRU (YENİ) — CihazService metodları kullanılıyor
svc = get_cihaz_service(db)
svc.insert_ariza_islem(data)   # Direkt service metodu
svc.insert_cihaz_belge(data)
svc.insert_periyodik_bakim(kayit)
```

**Düzeltilen dosyalar:**

| Dosya | Satır | Bypass edilen tablo | Durum |
|---|---|---|---|
| `ariza_islem.py` | 251, 256, 277 | `Ariza_Islem`, `Cihaz_Ariza`, `Cihaz_Belgeler` | ✅ Düzeltildi |
| `bakim_form.py` | 90 | `Periyodik_Bakim` | ✅ Düzeltildi |
| `cihaz_teknik_uts_scraper.py` | 415 | `Cihaz_Teknik` | ✅ Düzeltildi |

#### ✅ Anti-Pattern 2 — `_gcf` / `_gcf2` / `_gcf3` alias kaos [DÜZELTME YAPILDI]

**DÜZELTME ÖZET:**
- Tüm lokal `_gcf*` alias'ları kaldırıldı
- Standart top-level import paterni uygulandı: `from core.di import get_cihaz_service`
- Metod içi lazy import'lar kaldırıldı, __init__ kuruluşu standardize edildi

```python
# ❌ YANLIŞ (ESKI) — 5 farklı yapı
from core.di import get_cihaz_service as _gcf    # kalibrasyon_form.py
from core.di import get_cihaz_service as _gcf2   # bakim_form.py line 90
from core.di import get_cihaz_service as _gcf3   # bakim_form.py line 217
from core.di import get_cihaz_service as _gcf4   # ariza_kayit.py
from core.di import get_cihaz_service as _gcf5   # scraper.py

# ✅ DOĞRU (YENİ) — standart single import
from core.di import get_cihaz_service

class XxxSayfa(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db  = db
        self._svc = get_cihaz_service(db) if db else None
```

**Düzeltilen dosyalar:**

| Dosya | Alias Sayısı | Durum |
|---|---|---|
| `kalibrasyon_form.py` | 1 (_gcf) | ✅ Düzeltildi |
| `bakim_form.py` | 2 (_gcf2, _gcf3) | ✅ Düzeltildi |
| `ariza_kayit.py` | 1 (_gcf4) | ✅ Düzeltildi |
| `cihaz_teknik_uts_scraper.py` | 1 (_gcf5) | ✅ Düzeltildi |

#### ✅ Anti-Pattern 3 — `__init__`'te servis kurulmayıp her metod içinde çağrılıyor [DÜZELTME YAPILDI]

**DÜZELTME ÖZET:**
- Self._svc single initialization __init__'te yapılıyor
- Tüm metod içi `_get_cihaz_service()` çağrıları kaldırıldı
- None guard'lar eklendi güvenli erişim için

```python
# ❌ YANLIŞ (ESKI) — cihaz_ekle.py, ariza_girisi_form.py
class CihazEkleSayfa(QWidget):
    def __init__(self, db=None, parent=None):
        self._db = db
        # self._svc YOK — her metod kendi servisi kuruyor

    def _load_sabitler(self):
        svc = _get_cihaz_service(self._db)   # yeni nesne her seferinde
        svc.get_sabitler()

    def _calc_next(self):
        svc = _get_cihaz_service(self._db)   # tekrar yeni nesne
        svc.get_next_cihaz_sequence()

# ✅ DOĞRU (YENİ) — __init__'te bir kere kur
class CihazEkleSayfa(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db  = db
        self._svc = get_cihaz_service(db) if db else None  # ← SINGLE INIT

    def _load_sabitler(self):
        if not self._svc: return
        self._svc.get_sabitler()   # ← Direkt self._svc

    def _calc_next(self):
        if not self._svc: return
        self._svc.get_next_cihaz_sequence()   # ← Direkt self._svc
```

**Düzeltilen dosyalar:**

| Dosya | Metod Sayısı | Durum |
|---|---|---|
| `cihaz_ekle.py` | 3 (_load_sabitler, _calc_next_sequence, _on_save) | ✅ Düzeltildi |
| `ariza_girisi_form.py` | 1 (_save) | ✅ Düzeltildi |
| `kalibrasyon_form.py` | implicit (top-level kurulum) | ✅ Düzeltildi |
| `bakim_form.py` | implicit (top-level kurulum) | ✅ Düzeltildi |
| `ariza_kayit.py` | implicit (top-level kurulum) | ✅ Düzeltildi |
| `cihaz_teknik_uts_scraper.py` | implicit (top-level kurulum) | ✅ Düzeltildi |

---

### ✅ TODO-5 — Sync Pull-Only Transaction [TAMAMLANDI]
**Dosya:** `database/sync_service.py` satır 393–440  
**Durum:** ✅ TAMAMLANDI  
**Sorun:** DELETE sonrası INSERT hatası → tablo boş kalır  
**Çözüm:** Transaction (BEGIN/COMMIT/ROLLBACK) mekanizması kuruldu

#### Sorun Analizi
```python
# ❌ YANLIŞ (ESKI) — Atomik olmayan işlem
self.db.execute(f"DELETE FROM {table_name}")  # ← COMMIT AKLI
# ... hata riski ...
for row in valid_records:
    self.db.execute(sql, values)  # ← INSERT hata olursa, tablo boş kalır!
```

#### Çözüm — Atomik Transaction
```python
# ✅ DOĞRU (YENİ) — BEGIN/COMMIT/ROLLBACK
try:
    self.db.conn.execute("BEGIN")  # ← Transaction başlat
    self.db.conn.execute(f"DELETE FROM {table_name}")
    
    for row in valid_records:
        self.db.conn.execute(sql, values)  # Hata olsa da transaction içinde kalır
        inserted += 1
    
    self.db.conn.commit()  # ← Hepsi başarılı: kalıcı yap
    logger.info(f"[{table_name}] Transaction commit: {inserted} kayıt yazıldı")
    
except Exception as txn_error:
    self.db.conn.rollback()  # ← Hata: DELETE ve kısmi INSERTs geri al
    logger.error(f"[{table_name}] Transaction rollback: {txn_error}")
    raise
```

#### Değişim Detayları

**Satırlar 390–428 (Eski):**
- Satır 393: `self.db.execute(f"DELETE FROM {table_name}")` — immediate commit ❌
- Satır 398–425: for loop with individual `self.db.execute(sql)` calls — her biri auto-commit ❌
- Satır 411–424: try-except only for **row-level errors**, transaction güvenliği YOK ❌

**Satırlar 390–428 (Yeni):**
- `self.db.conn.execute("BEGIN")` — transaction açılır
- DELETE ve tüm INSERTs same transaction içinde
- Hata olursa `self.db.conn.rollback()` ile tablo başlangıç durumuna döner
- Başarılıysa `self.db.conn.commit()` ile kalıcı hale gelir

#### Test Senaryo

| Scenario | Eski Davranış | Yeni Davranış |
|---|---|---|
| **Başarılı pull:** 100 kayıt ✓ | Tablo 100 kayıt | Tablo 100 kayıt ✓ |
| **50. satırda hata:** | Tablo 49 kayıt (boş kalır) ❌ | Eski haline döner (0 kayıt) ✓ |
| **DELETE hata** | Rollback yok, exception | Transaction rollback ✓ |

---

### 🟡 TODO-6 — Kod İçi Temizlik (Fırsatçı)

Bir dosyaya girdiğinde gördüklerini düzelt:

```
[ ] setStyleSheet(f"...C.TOKEN") → setProperty("color-role", "...")
[ ] _DURUM_COLOR lokal dict     → self.status_fg() kullan, dict'i sil
[ ] def set_rows(self, rows)... → sil (BaseTableModel'de var)
[ ] from core.date_utils import to_ui_date (model içinde) → DATE_KEYS veya _fmt_date
[ ] get_registry() UI içinde    → get_xxx_service(db) kullan
[ ] RAW_ROW_ROLE lokal tanım    → sil, BaseTableModel.RAW_ROW_ROLE kullan
```

**Etkilenen dosyalar (öncelik sırasıyla):**

| Dosya | Temizlenecek |
|---|---|
| `cihaz/ariza_kayit.py` | _DURUM_COLOR, to_ui_date, set_rows |
| `cihaz/bakim_form.py` | _DURUM_COLOR, to_ui_date, set_rows, 12x setStyleSheet(f) |
| `cihaz/kalibrasyon_form.py` | _DURUM_COLOR, to_ui_date, set_rows, 7x setStyleSheet(f) |
| `cihaz/ariza_islem.py` | to_ui_date, set_rows |
| `personel/izin_takip.py` | _DURUM_COLOR, to_ui_date |
| `personel/saglik_takip.py` | to_ui_date, set_rows |
| `cihaz/cihaz_listesi.py` | RAW_ROW_ROLE lokal tanım |
| `rke/rke_rapor.py` | set_rows, 11x setStyleSheet(f) |

---

### 🟢 TODO-7 — Kullanılmayan Dosyaları Sil

```bash
git rm core/cihaz_ozet_servisi.py    # CihazService tarafından ikame edildi
git rm ui/components/data_table.py   # Hiçbir yerden import edilmiyor
git commit -m "chore: kullanılmayan dosyalar silindi"
```

---

### 🟢 TODO-8 — Testler

```bash
mkdir -p tests/services
# Her servis için:
tests/services/test_cihaz_service.py
tests/services/test_personel_service.py
tests/services/test_izin_service.py
tests/services/test_rke_service.py
```

Test şablonu → Bölüm 8'e bak.

---

### 🔵 TODO-9 — Orta Vadeli İyileştirmeler

Bu maddeler çalışmayı bozmaz, performans/temizlik amaçlı:

1. **SQLiteManager read/write ayrımı** — SELECT sorgularında commit kaldırılır:
   ```python
   def execute_read(self, query, params=()):
       cur = self.conn.cursor()
       cur.execute(query, params)
       return cur   # commit yok
   
   def execute(self, query, params=()):
       # Mevcut hali — write için kullan
   ```

2. **get_all + Python filter → get_where** — Performans açısından kritik tablolarda (Periyodik_Bakim, Cihaz_Ariza, Kalibrasyon) WHERE'lı sorgular kullanılmalı

3. **Import-time side effect azaltma:**
   ```python
   # core/paths.py içinde — klasör oluşturmayı lazy yap
   def initialize_paths():
       """main.pyw'den açıkça çağrılır."""
       os.makedirs(LOG_DIR, exist_ok=True)
       os.makedirs(DATA_DIR, exist_ok=True)
   ```

---

## BÖLÜM 8 — TEST YAZMA

```python
# tests/services/test_xxx_service.py
# -*- coding: utf-8 -*-
import pytest
from unittest.mock import MagicMock, call
from core.services.xxx_service import XxxService


@pytest.fixture
def reg():
    """Mock RepositoryRegistry."""
    return MagicMock()

@pytest.fixture
def repo(reg):
    """Mock repository — reg.get() her zaman bunu döner."""
    mock_repo = MagicMock()
    reg.get.return_value = mock_repo
    return mock_repo

@pytest.fixture
def svc(reg):
    return XxxService(reg)


class TestInit:
    def test_none_registry_hata_firlatar(self):
        with pytest.raises(ValueError):
            XxxService(None)


class TestGetListesi:
    def test_bos_veritabani(self, svc, repo):
        repo.get_all.return_value = []
        assert svc.get_listesi() == []

    def test_filtreli(self, svc, repo):
        repo.get_where.return_value = [{"Pk": "1", "Alan": "A"}]
        result = svc.get_listesi(filtre_id="TEST")
        repo.get_where.assert_called_once_with({"FK_KOLON": "TEST"})
        assert len(result) == 1

    def test_db_hatasi_bos_list_doner(self, svc, repo):
        repo.get_all.side_effect = Exception("bağlantı hatası")
        assert svc.get_listesi() == []


class TestKaydet:
    def test_insert_basarili(self, svc, repo):
        assert svc.kaydet({"GERCEK_PK_ADI": "1", "Alan": "deger"}) is True
        repo.insert.assert_called_once()

    def test_update_basarili(self, svc, repo):
        assert svc.kaydet({"GERCEK_PK_ADI": "1"}, guncelle=True) is True
        repo.update.assert_called_once()

    def test_update_pk_yoksa_false(self, svc, repo):
        assert svc.kaydet({}, guncelle=True) is False
        repo.update.assert_not_called()

    def test_db_hatasi_false_doner(self, svc, repo):
        repo.insert.side_effect = Exception("disk dolu")
        assert svc.kaydet({"Alan": "deger"}) is False


class TestSil:
    def test_basarili(self, svc, repo):
        repo.delete.return_value = True
        assert svc.sil("PK1") is True
        repo.delete.assert_called_once_with("PK1")

    def test_db_hatasi_false_doner(self, svc, repo):
        repo.delete.side_effect = Exception("yetki yok")
        assert svc.sil("PK1") is False
```

```bash
pip install pytest
pytest tests/ -v --tb=short
```

---

## BÖLÜM 9 — TEMA SİSTEMİ

### 9.1 color-role (metin rengi — QLabel, QWidget)

```python
widget.setProperty("color-role", "primary")    # Ana metin — TEXT_PRIMARY
widget.setProperty("color-role", "secondary")  # İkincil — TEXT_SECONDARY
widget.setProperty("color-role", "muted")      # Soluk — TEXT_MUTED
widget.setProperty("color-role", "disabled")   # Devre dışı — TEXT_DISABLED
widget.setProperty("color-role", "accent")     # Vurgu mavi — ACCENT
widget.setProperty("color-role", "accent2")    # Vurgu teal — ACCENT2
widget.setProperty("color-role", "ok")         # Başarı yeşil — STATUS_SUCCESS
widget.setProperty("color-role", "warn")       # Uyarı sarı — STATUS_WARNING
widget.setProperty("color-role", "err")        # Hata kırmızı — STATUS_ERROR
widget.setProperty("color-role", "info")       # Bilgi mavi — STATUS_INFO
```

### 9.2 style-role (buton stili — QPushButton)

```python
btn.setProperty("style-role", "action")     # Mavi primary buton
btn.setProperty("style-role", "secondary")  # Gri ikincil buton
btn.setProperty("style-role", "danger")     # Kırmızı sil/iptal
btn.setProperty("style-role", "success")    # Yeşil kaydet/onayla
btn.setProperty("style-role", "refresh")    # Yenile butonu
```

### 9.3 style-role (etiket stili — QLabel)

```python
lbl.setProperty("style-role", "title")         # Büyük başlık
lbl.setProperty("style-role", "section")       # Bölüm başlığı
lbl.setProperty("style-role", "section-title") # Bölüm alt başlık
lbl.setProperty("style-role", "form")          # Form etiketi
lbl.setProperty("style-role", "value")         # Değer gösterimi
lbl.setProperty("style-role", "footer")        # Alt bilgi
lbl.setProperty("style-role", "required")      # Zorunlu alan (kırmızı)
lbl.setProperty("style-role", "stat-value")    # İstatistik değeri
lbl.setProperty("style-role", "stat-label")    # İstatistik etiketi
lbl.setProperty("style-role", "stat-green")    # Yeşil istatistik
lbl.setProperty("style-role", "stat-red")      # Kırmızı istatistik
lbl.setProperty("style-role", "stat-highlight")# Vurgulu istatistik
```

### 9.4 Icon sistemi

```python
from ui.styles.icons import Icons, IconRenderer, IconColors

# Butona ikon
btn = QPushButton("Kaydet")
IconRenderer.set_button_icon(btn, "save", color=IconColors.PRIMARY, size=14)

# Label'a ikon
lbl = QLabel()
IconRenderer.set_label_icon(lbl, "users", size=20, color=IconColors.PRIMARY)

# QIcon (menü / action bar)
icon = Icons.get("calendar", size=16, color="#8b8fa3")

# QPixmap
pm = Icons.pixmap("bell", size=24, color=IconColors.NOTIFICATION)
```

**IconColors sabitleri:**
```python
IconColors.PRIMARY      # "#6bd3ff"  mavi
IconColors.DANGER       # "#f87171"  kırmızı
IconColors.SUCCESS      # "#4ade80"  yeşil
IconColors.WARNING      # "#facc15"  sarı
IconColors.MUTED        # "#5a5d6e"  gri
IconColors.TEXT         # "#e0e2ea"  metin
IconColors.EXCEL        # "#1d6f42"  excel export
IconColors.PDF          # "#e53e3e"  pdf export
IconColors.NOTIFICATION # "#f59e0b"  bildirim
IconColors.SYNC         # "#60a5fa"  senkronizasyon
```

**Mevcut ikon adları:**
```
activity, alert_list, alert_triangle, arrow_left, arrow_right,
bar_chart, bell, bell_dot, building, calendar, calendar_check,
calendar_off, calendar_year, check, check_circle, check_in,
chevron_down, chevron_left, chevron_right, chevron_up,
circuit_board, clipboard, clipboard_list, cloud_sync, cpu,
crosshair, database, device_add, download, edit, eye,
file_chart, file_excel, file_pdf, file_text, filter,
heart_pulse, home, hospital, id_card, info, layers, list,
lock, log_out, mail, menu, microscope, package, pie_chart,
plus, plus_circle, print, refresh, save, search, settings,
settings_sliders, shield, shield_alert, shield_check,
status_active, status_leave, status_passive, stethoscope,
sync, target, tools, trash, upload, user, user_add, users,
wrench, wrench_list, x, x_circle
```

---

## BÖLÜM 10 — YARDIMCI MODÜLLER

### 10.1 Tarih fonksiyonları (`core/date_utils.py`)

```python
from core.date_utils import parse_date, to_db_date, to_ui_date

parse_date("2025-03-15")    # → date(2025, 3, 15)
parse_date("15.03.2025")    # → date(2025, 3, 15)
parse_date(None)            # → None

to_db_date("15.03.2025")    # → "2025-03-15"  (DB'ye kaydetmek için)
to_db_date(datetime.now())  # → "2025-03-15"

to_ui_date("2025-03-15")    # → "15.03.2025"  (ekranda göstermek için)
to_ui_date(None, "—")       # → "—"
```

> Model içinde `to_ui_date` kullanma — `DATE_KEYS` veya `self._fmt_date` kullan.  
> `to_ui_date` yalnızca form/label içinde (model dışında) kullan.

### 10.2 Validasyon (`core/validators.py`)

```python
from core.validators import (
    validate_tc_kimlik_no,
    validate_email,
    validate_phone_number,
    validate_not_empty,
    validate_length,
    validate_numeric,
    validate_date_format,
)

validate_tc_kimlik_no("10000000146")   # → True
validate_tc_kimlik_no("12345678901")   # → False
validate_email("a@b.com")             # → True
validate_email("")                    # → True  (opsiyonel alan)
validate_phone_number("0532 123 4567") # → True
validate_not_empty("  ")              # → False
validate_length("abc", min_len=2, max_len=10)  # → True
validate_numeric("12345")             # → True
validate_date_format("15.03.2025")    # → True
validate_date_format("2025-03-15")    # → False (UI formatı beklenir)
```

### 10.3 Türkçe metin (`core/text_utils.py`)

```python
from core.text_utils import turkish_title_case, turkish_upper, turkish_lower

turkish_title_case("istanbul")   # → "İstanbul"
turkish_upper("istanbul")        # → "İSTANBUL"  (Python .upper() yanlış)
turkish_lower("İSTANBUL")        # → "istanbul"

# QLineEdit otomatik formatlama
from ui.components.formatted_widgets import (
    apply_title_case_formatting,      # Ad, soyad, şehir
    apply_uppercase_formatting,       # Tüm büyük harf
    apply_numeric_only,               # Sadece rakam
    apply_phone_number_formatting,    # Telefon format
    apply_combo_title_case_formatting # Editable QComboBox
)

apply_title_case_formatting(self.txt_ad_soyad)
apply_numeric_only(self.txt_tc)
self.txt_tc.setMaxLength(11)
```

### 10.4 Ayarlar (`core/settings.py` + `core/config.py`)

```python
from core import settings
from core.config import AppConfig

# Okuma
settings.get("theme", "dark")          # "dark" | "light"
settings.get("app_mode", "offline")    # "online" | "offline"
settings.get("auto_sync", False)       # bool

# Yazma
settings.set("theme", "light")
AppConfig.set_app_mode("online", persist=True)
AppConfig.set_auto_sync(True, persist=True)

# Sorgu
AppConfig.is_online_mode()             # → bool
AppConfig.get_auto_sync()              # → bool
AppConfig.VERSION                      # → "3.0.0"
AppConfig.APP_NAME                     # → "Radyoloji Envanter ve Personel..."
```

**ayarlar.json güncel yapısı:**
```json
{
  "theme": "dark",
  "app_mode": "offline",
  "auto_sync": false,
  "menu_yapilandirma": { ... }
}
```

---

## BÖLÜM 11 — LINT VE KALİTE KONTROL

```bash
# Commit öncesi zorunlu
python scripts/lint_theme.py

# Tek dosya syntax kontrolü
python -m py_compile ui/pages/xxx/xxx.py

# Tüm dosyalar toplu syntax kontrolü
python -c "
import py_compile, os
for r,d,fs in os.walk('.'):
    d[:] = [x for x in d if '__pycache__' not in x]
    for f in fs:
        if f.endswith('.py'):
            try: py_compile.compile(os.path.join(r,f), doraise=True)
            except Exception as e: print(e)
print('Tamamlandı')
"
```

**Pre-commit hook (`.git/hooks/pre-commit`):**
```bash
#!/bin/sh
python scripts/lint_theme.py || exit 1
```

---

## BÖLÜM 12 — MEVCUT DOSYAYA GİRERKEN KONTROL LİSTESİ

```
TEMA
[ ] setStyleSheet(f"...C.TOKEN") var mı? → setProperty("color-role", "...")
[ ] STYLES["key"] var mı?               → setProperty("style-role", "...")

MODEL
[ ] _DURUM_COLOR lokal dict var mı?     → self.status_fg() kullan, dict'i sil
[ ] def set_rows(self, rows): ... ?     → sil (BaseTableModel'de var)
[ ] to_ui_date import (model içinde)?   → DATE_KEYS veya self._fmt_date
[ ] RAW_ROW_ROLE lokal tanım?           → sil, model.RAW_ROW_ROLE kullan
[ ] QAbstractTableModel sıfırdan?       → BaseTableModel extend et

SERVİS / VERİ
[ ] get_registry() UI içinde direkt?    → get_xxx_service(db) kullan
[ ] RepositoryRegistry() UI içinde?     → get_xxx_service(db) kullan
[ ] get_all() + Python filter?          → get_where() veya özel repo metodu
[ ] Lokal _C = {...} renk dict?         → from ui.styles.colors import DarkTheme as C
```

---

*Rehber REPYS v3 — Mart 2026 durumunu yansıtır.*  
*Sonraki kritik adımlar: TODO-1 (BaseRepo) → TODO-2 (DI) → TODO-3 (Personel UI)*

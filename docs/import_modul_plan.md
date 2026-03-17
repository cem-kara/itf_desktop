# Excel Import Modülü — Tasarım Planı (Güncel)

> Son güncelleme: Tüm geliştirme turları tamamlandı.
> `→ DEĞİŞTİ` = orijinal plandan farklılaşan kısım
> `→ YENİ` = orijinal planda olmayan eklenti

---

## 1. Genel Mimari

```
core/services/
    excel_import_service.py          ← Motor, veri modelleri, normalizasyon
    dozimetre_service.py             ← YENİ: PDF import ile aynı tabloya yazan Excel servisi

ui/pages/imports/                    ← Ana paket
    import_center.py                 ← YENİ: Tüm sekmeleri tek ekranda toplar
    personel_import_page.py
    cihaz_import_page.py
    rke_import_page.py               ← İki sınıf: RkeListImportPage + RkeMuayeneImportPage
    dozimetre_import_page.py         ← Excel tabanlı
    dozimetre_pdf_import_page.py     ← YENİ: PDF (RADAT) tabanlı, bağımsız sayfa
    dis_alan_import_page.py
    izin_bilgi_import_page.py
    izin_giris_import_page.py
    components/
        base_import_page.py          ← Ortak sihirbaz UI (4 adım) — PySide6
```

**Kural:** Yeni tablo eklemek için sadece `*_import_page.py` dosyası yazılır,
başka hiçbir şey değişmez.

**→ YENİ Kural:** `alanlar` listesi yalnızca **özel muamele gereken** alanları içerir
(zorunlu, validator, anahtar_kelimeler, varsayilan). Geri kalan tüm kolonlar
`table_config.TABLES` üzerinden `alanlar_tam_listesi()` ile otomatik eklenir.

---

## 2. Veri Modelleri (`excel_import_service.py`)

### `AlanTanimi`

```python
@dataclass
class AlanTanimi:
    alan: str                          # DB kolon adı ("KimlikNo")
    goruntu: str                       # Ekranda gösterilecek ad ("TC Kimlik No *")
    tip: str                           # "str" | "tc" | "date" | "int" | "float"
    zorunlu: bool = False
    varsayilan: str = ""               # Boş gelirse kullanılacak değer / Elle giriş default
    anahtar_kelimeler: list[str] = field(default_factory=list)
    # → YENİ:
    validator: Optional[Callable[[str], tuple[bool, str]]] = None
    # None   → validasyon yok
    # Fn     → (gecerli_mi, hata_mesaji) döner
    # Örnek: lambda v: (validate_tc_kimlik_no(v), "Geçersiz TC Kimlik No")
    elle_girilebilir: bool = True
    # False → "✏ Elle Gir" seçeneği ComboBox'ta gizlenir
```

### `DuplicateKontrol` *(Değişmedi)*

```python
@dataclass
class DuplicateKontrol:
    pk_alanlar: list[str]
    yumusak_alanlar: list[str] = field(default_factory=list)
    pk_cakisma: str = "raporla"   # "raporla" | "atla" | "ustune_yaz"
    yumusak_cakisma: str = "uyar" # "uyar" | "atla" | "raporla"
```

### `ImportKonfig`

```python
@dataclass
class ImportKonfig:
    baslik: str
    servis_fabrika: Callable
    servis_metod: str
    tablo_adi: str                     # table_config anahtarıyla birebir eşleşmeli
    alanlar: list[AlanTanimi]          # Sadece özel alanlar — geri kalanı table_config'den
    duplicate: DuplicateKontrol
    normalize_fn: Optional[Callable[[dict], dict]] = None
```

### `SatirSonucu` / `ImportSonucu` *(Değişmedi)*

---

## 3. Motor (`ExcelImportService`)

### → DEĞİŞTİ: `donustur()`

```python
def donustur(
    self,
    df: pd.DataFrame,
    harita: dict[str, str],                    # {excel_sutun: db_alan}
    konfig: ImportKonfig,
    manuel_degerler: Optional[dict[str, str]] = None,  # YENİ: {db_alan: sabit_deger}
) -> list[SatirSonucu]:
```

**Değer önceliği:**
1. Excel sütununa eşleştirilmişse → Excel'den al
2. `manuel_degerler`'de varsa → elle girilen sabit değeri kullan (tüm satırlara aynı)
3. `AlanTanimi.varsayilan` varsa → varsayılanı kullan
4. Hiçbiri → boş string

**→ YENİ: Validator kontrolü** — `AlanTanimi.validator` tanımlıysa ve değer doluysa çağrılır.
Başarısız → satır `"hatali"` olarak işaretlenir, önizleme tablosunda kırmızı gösterilir.

### → YENİ: `alanlar_tam_listesi(konfig)` (modül seviyesi fonksiyon)

```python
def alanlar_tam_listesi(konfig: ImportKonfig) -> list[AlanTanimi]:
```

`table_config.TABLES[konfig.tablo_adi]['columns']` ile `konfig.alanlar`'ı birleştirir.

| Durum | Sonuç |
|---|---|
| Konfig'de var | validator / zorunlu / anahtar_kelimeler korunur |
| table_config'de var, konfig'de yok | Otomatik `AlanTanimi` — tip `date_fields`'dan tespit |
| Konfig'de var, table_config'de yok | Sona eklenir (hesaplanmış / adapter alanı) |
| Binary / sistem kolon | Atlanır |

**Atlanacak kolonlar:**
`Resim`, `Diploma1`, `Diploma2`, `OzlukDosyasi`, `Img`, `NDKLisansBelgesi`,
`Dosya`, `Rapor`, `KayitTarihi`, `OlusturmaTarihi`

### Normalizasyon Kuralları *(Standart, değişmedi)*

| Tip | Kural |
|---|---|
| `tc` | `zfill(11)`, baştaki sıfır korunur |
| `date` | `YYYY-MM-DD` — çoklu format denenir, `format="mixed"` fallback |
| `int` | `int(float(val))`, hatalı → `""` |
| `float` | `float(val)`, virgül→nokta, hatalı → `""` |
| `str` | `.strip()`, unicode NFC normalize |

---

## 4. UI Katmanı (`base_import_page.py`)

### → DEĞİŞTİ: Toolkit
PyQt5 → **PySide6**
- `pyqtSignal` → `Signal`
- `exec_()` → `exec()`
- Tüm enum'lar tam yol: `Qt.AlignmentFlag.AlignCenter`, `QHeaderView.ResizeMode.Stretch` vb.

### → ÇÖZÜLDİ: SQLite Thread Sorunu
`sqlite_manager.py`'de `check_same_thread=False` (varsayılan değer değiştirildi).
`_ImportThread` (QThread) aktif — büyük dosyalar UI donmadan işlenir.

### → DEĞİŞTİ: Adım 2 — Ters Eşleştirme + Elle Giriş

**Eski:** Sol = Excel sütunu → Sağ = DB alanı seç
**Yeni:** Sol = **DB alanı** (table_config'den tam liste) → Sağ = Excel sütunu seç veya elle gir

```
DB Alanı              │  Excel Sütunu / Değer
──────────────────────┼─────────────────────────────────
TC Kimlik No ★        │  [ComboBox: Kimlik No       ▼]
Ad Soyad ★            │  [ComboBox: Ad Soyad        ▼]
Doğum Tarihi          │  [ComboBox: — Eşleştirme Yok ▼]
Hizmet Sınıfı         │  [ComboBox: ✏ Elle Gir      ▼] [657 Tabii ]
Durum                 │  [ComboBox: ✏ Elle Gir      ▼] [Aktif     ]
```

**Kurallar:**
- `elle_girilebilir=False` → "✏ Elle Gir" seçeneği gizlenir
- Aynı Excel sütunu iki alana eşlenirse kırmızı uyarı
- Zorunlu alanlar yeşil arka plan + ★ işareti
- `⚡ Otomatik Eşleştir` → `anahtar_kelimeler` ile otomatik öneri

### Sihirbaz Adımları

```
Adım 1 — Dosya Seç
    Excel yükle, satır/sütun sayısını göster

Adım 2 — Alan Eşleştir  ← DEĞİŞTİ
    Sol: DB alanı (alanlar_tam_listesi → table_config'den tam liste)
    Sağ: Excel sütunu seç VEYA "✏ Elle Gir" + QLineEdit

Adım 3 — Önizle
    🔴 pk_duplicate | 🟡 yumusak_duplicate | ⚫ zorunlu_eksik | 🔴 validator hatası

Adım 4 — Sonuç + Hata Düzeltme
    Özet kartları + [Hatalıları Düzenle] → HataDuzeltmeWidget
    [Yeni Import] → sihirbazı başa alır
```

---

## 5. Tablo Sayfaları

### Şablon (tüm tablolar için)

```python
from core.services.excel_import_service import AlanTanimi, DuplicateKontrol, ImportKonfig
from core.validators import validate_tc_kimlik_no   # gerekiyorsa
from core.text_utils import turkish_title_case       # gerekiyorsa
from ui.pages.imports.components.base_import_page import BaseImportPage

KONFIG = ImportKonfig(
    baslik="...",
    servis_fabrika=...,
    servis_metod="...",
    tablo_adi="...",        # ← table_config anahtarıyla birebir eşleşmeli
    normalize_fn=...,       # opsiyonel
    duplicate=DuplicateKontrol(...),
    alanlar=[
        # Yalnızca: zorunlu, validator, anahtar_kelimeler, varsayilan gereken alanlar
        # Geri kalanı table_config'den otomatik gelir
    ],
)

class XxxImportPage(BaseImportPage):
    def _konfig(self) -> ImportKonfig:
        return KONFIG
```

### Tablo Başına Duplicate + Servis Stratejisi

| Tablo | `pk_alanlar` | `yumusak_alanlar` | `pk_cakisma` | Servis Metodu |
|---|---|---|---|---|
| Personel | `["KimlikNo"]` | — | raporla | `ekle` |
| Cihazlar | `["Cihazid"]` | — | raporla | `cihaz_ekle` |
| RKE_List | `["EkipmanNo"]` | — | raporla | `rke_ekle` |
| RKE_Muayene | `["EkipmanNo","FMuayeneTarihi"]` | `["EkipmanNo","SMuayeneTarihi"]` | raporla | `muayene_ekle` |
| Dozimetre_Olcum | `["PersonelID","Periyot","Yil"]` | — | raporla | `olcum_ekle` (DozimetreService) |
| Dis_Alan_Calisma | `["TCKimlik","DonemAy","DonemYil","TutanakNo"]` | — | raporla | `dis_alan_ekle` |
| Izin_Giris | `["Personelid","BaslamaTarihi","IzinTipi"]` | `["Personelid","BaslamaTarihi","BitisTarihi"]` | raporla | `insert_izin_giris` |
| Izin_Bilgi | `["TCKimlik"]` | — | ustune_yaz | `izin_bilgi_kaydet` (adapter) |

### → DEĞİŞTİ / YENİ: Özel Durumlar

**`Izin_Giris`:**
- Servis metodu: `insert_izin_giris` (`izin_bilgi_ekle` değil — servis dosyasındaki gerçek isim)
- `Gun` kolonu tablo gerçek adıdır — anahtar kelimeler: `gun, gunsayisi, izingunsayisi`
- `normalize_fn` → AdSoyad Türkçe Title Case

**`Izin_Bilgi`:**
- `create_or_update_izin_bilgi()` **KULLANILMIYOR** — yıllık hakkı baslama_tarihi'nden
  yeniden hesaplar, Excel bakiye değerlerini görmezden gelir
- `_IzinBilgiDirectAdapter.izin_bilgi_kaydet()` kullanılıyor:
  `get_izin_bilgi_repo()` → doğrudan repo `insert`/`update`
- Excel sütun eşlemesi: `Hak Edilen→YillikHakedis`, `Devir→YillikDevir`,
  `Toplam→YillikToplamHak`, `Kullanılan→YillikKullanilan`, `Kalan→YillikKalan`

**`Dozimetre` (Excel):**
- `DozimetreService` (`core/services/dozimetre_service.py`) — minimal servis
- `_DDL` sabiti ve `tablo_olustur()` metodu kaldırıldı — tablo `migrations.py` tarafından yönetilir
- DB bağlantısı: `str`, `sqlite3.Connection` veya `.connection` attribute — hepsini destekler

**`Dozimetre` (PDF — RADAT):**
- `DozimetrePdfImportPage` — bağımsız sayfa, 4 adımlı sihirbaz kullanmaz
- pdfplumber tabanlı parser, personel otomatik eşleştirme, kendi thread döngüsü
- `CREATE TABLE IF NOT EXISTS` kaldırıldı — migrations hallediyor

### → DEĞİŞTİ: Dozimetre_Olcum Şeması

Kaldırılan kolonlar: `SiraNo`, `TCKimlikNo`, `DozSiniri_Hp10`, `DozSiniri_Hp007`, `UNIQUE(RaporNo, SiraNo)`

```sql
CREATE TABLE IF NOT EXISTS Dozimetre_Olcum (
    KayitNo         TEXT PRIMARY KEY,   -- UUID, PK yeterli
    RaporNo         TEXT,
    Periyot         INTEGER,
    PeriyotAdi      TEXT,
    Yil             INTEGER,
    DozimetriTipi   TEXT,
    AdSoyad         TEXT,
    PersonelID      TEXT,               -- TC kimlik no (gerçek veya masked)
    CalistiBirim    TEXT,
    DozimetreNo     TEXT,
    VucutBolgesi    TEXT,
    Hp10            REAL,
    Hp007           REAL,
    Durum           TEXT,
    OlusturmaTarihi TEXT DEFAULT (date('now')),
    sync_status     TEXT DEFAULT 'clean',
    updated_at      TEXT
)
```

**Neden kaldırıldı:**
- `SiraNo` — PDF sıra no, iş sürecinde anlamsız; `KayitNo` (UUID) yeterli
- `TCKimlikNo` — `PersonelID` zaten TC kimlik no'yu tutuyor, duplicate
- `DozSiniri_Hp10/007` — PDF'de bu değer parse edilemiyor, boş kalıyordu
- `UNIQUE(RaporNo, SiraNo)` — `SiraNo` kaldırıldığı için geçersiz

### → YENİ: Validator + Normalize Entegrasyonu

```python
from core.validators import validate_tc_kimlik_no, validate_email, validate_phone_number
from core.text_utils import turkish_title_case

def _normalize(kayit):
    if kayit.get("AdSoyad"):
        kayit["AdSoyad"] = turkish_title_case(kayit["AdSoyad"])
    return kayit
```

| Sayfa | Validator | normalize_fn |
|---|---|---|
| Personel | TC + e-posta + telefon | AdSoyad Title Case |
| Cihaz | — | Sorumlusu Title Case |
| Dis_Alan_Calisma | TC (opsiyonel, zorunlu değil) | AdSoyad Title Case |
| Dozimetre (Excel) | TC | AdSoyad Title Case |
| İzin Giriş | TC | AdSoyad Title Case |
| İzin Bilgi | TC | AdSoyad Title Case |

### → DEĞİŞTİ: Dozimetre (Excel) — Alan Adları

Konfig alanları doğrudan **DB kolon adlarıyla** tanımlı — `Hp10`, `Hp007`.
`DerinDoz`, `YuzeyselDoz` gibi kullanıcı dostu isimler `anahtar_kelimeler`'e taşındı.
`PersonelID` — TC kimlik no; Excel'den gelir veya PDF eşleştirmesinden yazılır.

### → DEĞİŞTİ: Dozimetre (PDF) — RaporNo Okuma

**Eski sorun:** `\b(\d{9})\b` — sadece 9 hane, sadece ilk sayfa; `AB-0730-T` içindeki `0730`'u yanlış yakalıyordu.

**Yeni mantık — iki aşamalı:**
1. `Rapor No: …` etiketi varsa → etiketten al (3–12 hane, büyük/küçük harf duyarsız)
2. Yoksa → her satırı tara, **satırda tek başına** duran 3–12 haneli sayıyı al
   - `AB-0730-T` → tire içinde → atlanır
   - `04-24` → tarih formatı → atlanır
   - `2643` → satırda tek → ✔ alınır
3. Tüm sayfalar taranır — ilk sayfada bulunamazsa sonrakine geçer

**`_PdfLoader` + `_DbSaver` — SQLiteManager uyumu:**
- `_db_path(db)` statik metodu: `str`, `SQLiteManager.db_path` veya diğer attribute'lardan yol çıkarır
- Tüm `sqlite3.connect()` çağrıları `check_same_thread=False` ile yapılır

### → DEĞİŞTİ: Dozimetre (PDF) — Personel Eşleştirme

**Sorun:** Aynı masked TC (`25*******44`) birden fazla kişiye ait olabilir.

**`match_personel` — iki aşamalı eşleştirme:**
1. Personel tablosundaki gerçek TC'lerle masked TC `_match_tc()` ile karşılaştırılır
2. Tek eşleşme → direkt o kişi (PersonelID = gerçek TC)
3. Birden fazla eşleşme → `_name_score()` ile ayırt edilir:
   - PDF'deki kısmi isim parçaları (`AR**`, `ÇEL**`) görünür kısımlarına kadar normalize edilir
   - Her parça için DB adlarında prefix eşleşmesi aranır, eşleşen **karakter sayısı** toplanır
   - Türkçe karakterler normalize edilir (`Ç→C`, `İ→I` vb.)
   - En yüksek skoru alan kişi seçilir
4. Skor 0 → tahmin edilmez, masked TC `PersonelID`'de kalır (sarı gösterilir)

**Önizleme tablosunda `TC / ID` sütunu:**
- 🟢 Yeşil = gerçek TC bulundu (eşleşme başarılı)
- 🟡 Sarı = masked TC, eşleşme bulunamadı

---

## 6. Import Center (`import_center.py`)

```python
class ImportCenterPage(QWidget):
    # Sekmeler (sırayla):
    # 👤 Personel          → PersonelImportPage
    # 🔧 Cihaz             → CihazImportPage
    # 📋 RKE Liste         → RkeListImportPage
    # 🔍 RKE Muayene       → RkeMuayeneImportPage
    # ☢️  Dozimetre (PDF)   → DozimetrePdfImportPage
    # ☢️  Dozimetre (Excel) → DozimetreImportPage
    # 🏗️  Dış Alan          → DisAlanImportPage
    # 📊 İzin Bakiye       → IzinBilgiImportPage
    # 📅 İzin Giriş        → IzinGirisImportPage
```

---

## 7. Bağımlılıklar

| Modül | Kullanıldığı yer |
|---|---|
| `core/validators.py` | TC kimlik, e-posta, telefon validasyonu |
| `core/text_utils.py` | `turkish_title_case` — AdSoyad normalize |
| `core/date_utils.py` | `to_db_date` — tarih normalizasyonu |
| `database/table_config.py` | `alanlar_tam_listesi` — kolon listesi kaynağı |
| `core/services/dozimetre_service.py` | Excel dozimetre import |

---

## 8. `di.py` Eklentisi

```python
def get_excel_import_service():
    from core.services.excel_import_service import ExcelImportService
    return ExcelImportService()
```

---

## 9. Önemli Altyapı Değişiklikleri

### `sqlite_manager.py`
```python
# → DEĞİŞTİ: check_same_thread varsayılanı False yapıldı
def __init__(self, db_path=None, check_same_thread=False):
```
WAL modu + `check_same_thread=False` birlikte güvenli — import thread'i bağlantıyı paylaşabilir.

---

## 10. Geliştirme Durumu

| # | Dosya | Durum | Not |
|---|---|---|---|
| 1 | `excel_import_service.py` | ✅ | validator, manuel_degerler, alanlar_tam_listesi |
| 2 | `base_import_page.py` | ✅ | PySide6, ters eşleştirme, elle giriş, TC/ID önizleme sütunu |
| 3 | `personel_import_page.py` | ✅ | validator, normalize_fn, table_config entegre |
| 4 | `cihaz_import_page.py` | ✅ | |
| 5 | `rke_import_page.py` | ✅ | 2 sayfa: List + Muayene |
| 6 | `dozimetre_import_page.py` | ✅ | Excel, DozimetreService, Hp10/Hp007 kolon adları |
| 6b | `dozimetre_pdf_import_page.py` | ✅ | RaporNo düzeltmesi, isim skoru eşleştirme, TC/ID sütunu |
| 6c | `dozimetre_service.py` | ✅ | SiraNo/TCKimlikNo kaldırıldı, migration ile uyumlu |
| 7 | `dis_alan_import_page.py` | ✅ | |
| 8 | `izin_bilgi_import_page.py` | ✅ | DirectAdapter, repo direkt yazım |
| 9 | `izin_giris_import_page.py` | ✅ | insert_izin_giris, Gun alanı |
| 10 | `di.py` güncelleme | ✅ | `get_excel_import_service` eklendi |
| 11 | `import_center.py` | ✅ | 9 sekme |
| 12 | `sqlite_manager.py` | ✅ | `check_same_thread=False` |
| 13 | `migrations.py` | ✅ | CURRENT_VERSION=1, Dozimetre_Olcum temiz şema |

**Toplam yeni dosya:** 13
**Değişen mevcut dosya:** 2 (`di.py`, `sqlite_manager.py`)

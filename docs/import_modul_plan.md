# Excel Import Modülü — Tasarım Planı

## 1. Genel Mimari

```
core/services/
    excel_import_service.py          ← Motor, veri modelleri, normalizasyon

ui/pages/import_/
    __init__.py
    base_import_page.py              ← Ortak sihirbaz UI (4 adım)
    personel_import_page.py          ← ~30 satır (sadece konfig)
    cihaz_import_page.py             ← ~30 satır
    rke_import_page.py               ← ~30 satır
    dozimetre_import_page.py         ← ~30 satır
    dis_alan_import_page.py          ← ~30 satır
    izin_bilgi_import_page.py        ← ~30 satır
    izin_giris_import_page.py        ← ~30 satır
```

**Kural:** Yeni tablo eklemek için sadece
`*_import_page.py` dosyası yazılır, başka hiçbir şey değişmez.

---

## 2. Veri Modelleri (`excel_import_service.py`)

### `AlanTanimi`
Tek DB kolonunu tanımlar.

```python
@dataclass
class AlanTanimi:
    alan: str                          # DB kolon adı ("KimlikNo")
    goruntu: str                       # Ekranda gösterilecek ad ("TC Kimlik No *")
    tip: str                           # "str" | "tc" | "date" | "int" | "float"
    zorunlu: bool = False
    varsayilan: str = ""               # Boş gelirse kullanılacak değer
    anahtar_kelimeler: list[str] = field(default_factory=list)
    # Otomatik eşleştirme için normalize edilmiş aday kelimeler
    # ["kimlik", "tc", "tcno"] → Excel başlığı bu kelimeleri içeriyorsa eşleştir
```

### `DuplicateKontrol`
Her tablo için farklı duplicate kuralı tanımlar.

```python
@dataclass
class DuplicateKontrol:
    pk_alanlar: list[str]
    # DB'de zaten var mı kontrolü için kullanılacak alanlar.
    # table_config.py'deki pk ile birebir eşleşmek zorunda değil —
    # import bağlamında anlamlı olan PK seçilir.
    # Örnekler:
    #   Personel:     ["KimlikNo"]
    #   Cihaz:        ["Cihazid"]
    #   RKE_List:     ["EkipmanNo"]
    #   RKE_Muayene:  ["EkipmanNo", "FMuayeneTarihi"]
    #   Dozimetre:    ["TCKimlikNo", "Periyot", "Yil"]
    #   Dis_Alan:     ["TCKimlik", "DonemAy", "DonemYil", "TutanakNo"]
    #   Izin_Giris:   ["Personelid", "BaslamaTarihi", "IzinTipi"]
    #   Izin_Bilgi:   ["TCKimlik"]

    yumusak_alanlar: list[str] = field(default_factory=list)
    # PK farklı ama mantıksal duplicate kontrolü.
    # Örnekler:
    #   Izin_Giris:  ["Personelid", "BaslamaTarihi", "BitisTarihi"]
    #                → aynı kişi çakışan tarih aralığı uyarı
    #   RKE_Muayene: ["EkipmanNo", "SMuayeneTarihi"]
    #                → aynı ekipman aynı gün iki muayene uyarı

    pk_cakisma: str = "raporla"
    # "raporla"    → hata listesine ekle, kaydetme
    # "atla"       → sessizce geç (INSERT OR IGNORE)
    # "ustune_yaz" → güncelle (INSERT OR REPLACE)

    yumusak_cakisma: str = "uyar"
    # "uyar"       → kaydet ama sonuç ekranında uyarı göster
    # "atla"       → kaydetme
    # "raporla"    → hata listesine ekle
```

### `ImportKonfig`
Tablo başına tek yapılandırma nesnesi.

```python
@dataclass
class ImportKonfig:
    baslik: str                        # "Toplu Personel İçe Aktarma"
    servis_fabrika: Callable           # get_personel_service
    servis_metod: str                  # "ekle" | "cihaz_ekle" | "rke_ekle"
    tablo_adi: str                     # Duplicate ön kontrolü için ("Personel")
    alanlar: list[AlanTanimi]
    duplicate: DuplicateKontrol

    normalize_fn: Optional[Callable[[dict], dict]] = None
    # None   → motor standart kuralları uygular (tip bazlı)
    # Fn     → tablo özel mantık; standart kurallar SONRASINDA çağrılır
    #          def normalize(kayit: dict) -> dict: ...
```

### `SatirSonucu`
Her satırın import sonucu.

```python
@dataclass
class SatirSonucu:
    satir_no: int
    veri: dict                         # Normalize edilmiş kayıt
    durum: str
    # "basarili"         → eklendi
    # "hatali"           → servis hata döndürdü
    # "pk_duplicate"     → DB'de zaten bu PK var
    # "yumusak_duplicate"→ yumuşak çakışma tespit edildi (yine de eklendi)
    # "zorunlu_eksik"    → zorunlu alan boş geldi
    hata_mesaji: str = ""
    duzeltilmis_veri: Optional[dict] = None
    # Kullanıcı hata düzeltme ekranında değiştirirse buraya yazılır
    # None → orijinal veri kullanılır
```

### `ImportSonucu`
Tüm import işleminin özeti.

```python
@dataclass
class ImportSonucu:
    toplam: int
    basarili: int
    hatali: int
    pk_duplicate: int
    yumusak_duplicate: int
    zorunlu_eksik: int
    satirlar: list[SatirSonucu]

    @property
    def duzeltilecekler(self) -> list[SatirSonucu]:
        return [s for s in self.satirlar
                if s.durum in ("hatali", "zorunlu_eksik")]

    @property
    def uyarilar(self) -> list[SatirSonucu]:
        return [s for s in self.satirlar
                if s.durum == "yumusak_duplicate"]
```

---

## 3. Motor (`ExcelImportService`)

### Metodlar

```python
class ExcelImportService:

    def excel_oku(self, dosya_yolu: str) -> SonucYonetici:
        # pd.read_excel(dtype=str) + fillna("")
        # Döner: SonucYonetici(veri=DataFrame)

    def otomatik_eslestir(
        self,
        sutunlar: list[str],
        konfig: ImportKonfig
    ) -> dict[str, str]:
        # excel_sutun → db_alan haritası
        # AlanTanimi.anahtar_kelimeler ile normalize karşılaştırma
        # Döner: {"TC Kimlik No": "KimlikNo", "Ad Soyad": "AdSoyad", ...}

    def donustur(
        self,
        df: pd.DataFrame,
        harita: dict[str, str],
        konfig: ImportKonfig
    ) -> list[SatirSonucu]:
        # 1. Sütun eşleştirmesi uygula
        # 2. Standart normalizasyon (tip bazlı)
        # 3. normalize_fn varsa çağır
        # 4. Zorunlu alan kontrolü → zorunlu_eksik
        # Döner: list[SatirSonucu] (henüz DB'ye yazılmamış)

    def duplicate_kontrol(
        self,
        satirlar: list[SatirSonucu],
        konfig: ImportKonfig,
        db
    ) -> list[SatirSonucu]:
        # 1. Tek DB sorgusuyla mevcut PK setini çek
        # 2. Yumuşak alanlar için mevcut kombinasyon setini çek
        # 3. Her satırı işaretle (pk_duplicate / yumusak_duplicate)
        # Toplu sorgu — satır başına DB çağrısı YOK

    def yukle(
        self,
        satirlar: list[SatirSonucu],
        konfig: ImportKonfig,
        db,
        kaydeden: str = ""
    ) -> ImportSonucu:
        # Sadece durum="" olan satırları işle
        # svc = konfig.servis_fabrika(db)
        # metod = getattr(svc, konfig.servis_metod)
        # Her satır için metod(satir.veri) → SonucYonetici
        # Başarısız → durum="hatali"
        # pk_cakisma="ustune_yaz" olanlar için güncelleme

    def yeniden_yukle(
        self,
        satirlar: list[SatirSonucu],
        konfig: ImportKonfig,
        db,
        kaydeden: str = ""
    ) -> ImportSonucu:
        # Hata düzeltme ekranından gelen düzeltilmiş satırları tekrar dener
        # satir.duzeltilmis_veri varsa onu, yoksa orijinal veriyi kullanır
```

### Normalizasyon Kuralları (Standart)

| Tip | Kural |
|---|---|
| `tc` | Sayısal ise `zfill(11)`, baştaki sıfır kaybolmasın |
| `date` | `to_db_date()` → `YYYY-MM-DD`, hatalı format → boş string |
| `int` | `int(float(val))`, hatalı → `""` |
| `float` | `float(val)`, hatalı → `""` |
| `str` | `.strip()`, unicode normalize |

`normalize_fn` standart kurallar **sonrasında** çalışır — sadece tablo özel ek mantık içerir.

---

## 4. UI Katmanı

### `BaseImportPage` — 4 Adımlı Sihirbaz

```
Adım 1 — Dosya Seç
    Excel yükle, satır/sütun sayısını göster

Adım 2 — Sütun Eşleştir
    Her Excel sütunu için ComboBox
    Otomatik eşleştirme önerisi
    Zorunlu alan uyarısı (kırmızı)
    Aynı DB alanına iki sütun → engelle

Adım 3 — Önizle
    Normalize edilmiş veri tablosu
    Duplicate kontrolü sonucu:
        🔴 pk_duplicate     → satır kırmızı
        🟡 yumusak_duplicate → satır sarı
        ⚫ zorunlu_eksik    → satır gri
    [Geri] [İçe Aktar]

Adım 4 — Sonuç + Hata Düzeltme
    Özet kartları: ✓ Eklendi | ✗ Hatalı | ⚠ Duplicate | ⚫ Eksik
    [Hatalıları Düzenle] butonu → HataDuzeltmeWidget açılır
    [Kapat] / [Yeni Import]
```

### `HataDuzeltmeWidget`
`BaseImportPage` içinde gömülü, sadece `duzeltilecekler` listesiyle açılır.

```
Tablo — sadece hatalı/eksik satırlar
    Her satırda hata mesajı son sütunda görünür
    Hücreler düzenlenebilir (QTableWidget veya inline edit)

Alt butonlar:
    [Seçilenleri Tekrar Dene]   → yeniden_yukle()
    [Tümünü Yoksay]             → ekranı kapat
    [Seçilenleri Yoksay]        → seçili satırları listeden çıkar
```

### Tablo Sayfası Şablonu

```python
# ui/pages/import_/personel_import_page.py

from core.di import get_personel_service
from core.services.excel_import_service import (
    ImportKonfig, AlanTanimi, DuplicateKontrol
)
from ui.pages.imports.components.base_import_page import BaseImportPage

KONFIG = ImportKonfig(
    baslik="Toplu Personel İçe Aktarma",
    servis_fabrika=get_personel_service,
    servis_metod="ekle",
    tablo_adi="Personel",
    duplicate=DuplicateKontrol(
        pk_alanlar=["KimlikNo"],
        pk_cakisma="raporla",
    ),
    alanlar=[
        AlanTanimi("KimlikNo", "TC Kimlik No *", "tc",  zorunlu=True,
                   anahtar_kelimeler=["kimlik","tc","tcno","kimlikno"]),
        AlanTanimi("AdSoyad",  "Ad Soyad *",     "str", zorunlu=True,
                   anahtar_kelimeler=["adsoyad","ad","isim","name"]),
        AlanTanimi("DogumTarihi",   "Doğum Tarihi",  "date",
                   anahtar_kelimeler=["dogumtarihi","dogum","birthdate"]),
        AlanTanimi("HizmetSinifi",  "Hizmet Sınıfı", "str",
                   anahtar_kelimeler=["hizmetsinifi","sinif","hizmet"]),
        AlanTanimi("GorevYeri",     "Görev Yeri",    "str",
                   anahtar_kelimeler=["gorevyeri","bolum","birim"]),
        # ... diğer alanlar
    ],
)

class PersonelImportPage(BaseImportPage):
    def _konfig(self) -> ImportKonfig:
        return KONFIG
```

---

## 5. Tablo Başına Duplicate Stratejisi

| Tablo | `pk_alanlar` | `yumusak_alanlar` | `pk_cakisma` |
|---|---|---|---|
| Personel | `["KimlikNo"]` | — | raporla |
| Cihazlar | `["Cihazid"]` | — | raporla |
| RKE_List | `["EkipmanNo"]` | — | raporla |
| RKE_Muayene | `["EkipmanNo","FMuayeneTarihi"]` | `["EkipmanNo","SMuayeneTarihi"]` | raporla |
| Dozimetre_Olcum | `["TCKimlikNo","Periyot","Yil"]` | — | raporla |
| Dis_Alan_Calisma | `["TCKimlik","DonemAy","DonemYil","TutanakNo"]` | — | raporla |
| Izin_Giris | `["Personelid","BaslamaTarihi","IzinTipi"]` | `["Personelid","BaslamaTarihi","BitisTarihi"]` | raporla |
| Izin_Bilgi | `["TCKimlik"]` | — | ustune_yaz |

**Not:** `Izin_Bilgi` için `ustune_yaz` — bakiye güncellemesi yapılırken mevcut kaydın üzerine yazılması beklenir.

---

## 6. `di.py` Eklentisi

```python
def get_excel_import_service():
    from core.services.excel_import_service import ExcelImportService
    return ExcelImportService()
```

---

## 7. Geliştirme Sırası

| # | Dosya | İş | Bağımlılık |
|---|---|---|---|
| 1 | `excel_import_service.py` | Veri modelleri + motor | — |
| 2 | `base_import_page.py` | Sihirbaz UI + HataDuzeltmeWidget | 1 |
| 3 | `personel_import_page.py` | İlk tablo, test referansı | 1, 2 |
| 4 | `cihaz_import_page.py` | — | 1, 2 |
| 5 | `rke_import_page.py` | RKE_List + RKE_Muayene | 1, 2 |
| 6 | `dozimetre_import_page.py` | — | 1, 2 |
| 7 | `dis_alan_import_page.py` | — | 1, 2 |
| 8 | `izin_bilgi_import_page.py` | — | 1, 2 |
| 9 | `izin_giris_import_page.py` | — | 1, 2 |
| 10 | `di.py` güncelleme | `get_excel_import_service` ekle | 1 |

**Toplam yeni dosya:** 10
**Değişen dosya:** 1 (`di.py`)
**Motor + UI toplam tahmini:** ~600-700 satır
**Tablo sayfası başına:** ~30 satır

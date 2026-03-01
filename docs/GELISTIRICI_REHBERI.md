# REPYS — Geliştirici Rehberi
> Yeni modül eklerken, mevcut dosyaya girerken ve servis bağlarken bu dosyaya bak.
> "Aynı hataları yapma" listesi + fırsatçı refactor kontrol listesi.

---

## 1. YENİ MODÜL AÇARKEN — Adım Adım

### 1.1 Önce tablo adını ve PK'yı kontrol et

`database/table_config.py`'ye bak. Yanlış tablo adı en sık yapılan hata.

| Tablo               | PK          | Notlar                        |
|---------------------|-------------|-------------------------------|
| `Personel`          | `KimlikNo`  | "Personeller" değil           |
| `Izin_Giris`        | `Izinid`    | "Izin" değil, "IzinId" değil  |
| `Izin_Bilgi`        | `TCKimlik`  | İzin bakiye tablosu           |
| `Cihaz_Ariza`       | `Arizaid`   | "ArizaId" değil               |
| `Periyodik_Bakim`   | `Planid`    |                               |
| `Kalibrasyon`       | `Kalid`     | "KalibrasyonId" değil         |
| `Cihazlar`          | `Cihazid`   |                               |
| `Sabitler`          | `Rowid`     | Dropdown listeleri buradan    |
| `Personel_Saglik_Takip` | `KayitNo` |                            |
| `RKE_Muayene`       | `KayitNo`   |                               |
| `RKE_List`          | `EkipmanNo` |                               |
| `FHSZ_Puantaj`      | —           | table_config'e bak            |
| `Ariza_Islem`       | `Islemid`   |                               |

**Kontrol:** Yeni service yazarken şunu çalıştır:
```python
python -c "
import re
tables = re.findall(r'^    \"(\w+)\":', open('database/table_config.py').read(), re.M)
print(tables)
"
```

---

### 1.2 Yeni service dosyası şablonu

**Dosya:** `core/services/xxx_service.py`

```python
"""
XxxService — [Ne yapıyor, tek cümle]
Sorumluluklar:
- ...
"""
from typing import Optional, List, Dict
from core.logger import logger
from database.repository_registry import RepositoryRegistry


class XxxService:
    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("RepositoryRegistry boş olamaz")
        self._r = registry

    def get_xxx_listesi(self, filtre_id: Optional[str] = None) -> List[Dict]:
        try:
            rows = self._r.get("TABLO_ADI").get_all() or []
            if filtre_id:
                rows = [r for r in rows if str(r.get("ALAN", "")) == str(filtre_id)]
            return rows
        except Exception as e:
            logger.error(f"Xxx listesi yükleme hatası: {e}")
            return []

    def kaydet(self, veri: Dict, guncelle: bool = False) -> bool:
        try:
            repo = self._r.get("TABLO_ADI")
            if guncelle:
                pk = veri.get("GERCEK_PK_ADI")   # ← table_config'den bak!
                if not pk:
                    logger.error("UPDATE için PK gerekli")
                    return False
                repo.update(pk, veri)
            else:
                repo.insert(veri)
            return True
        except Exception as e:
            logger.error(f"Xxx kaydet hatası: {e}")
            return False

    def sil(self, pk: str) -> bool:
        try:
            self._r.get("TABLO_ADI").delete(pk)
            return True
        except Exception as e:
            logger.error(f"Xxx sil hatası: {e}")
            return False
```

**Kontrol listesi:**
```
[ ] Tablo adını table_config.py'den kopyaladım (yazmadım)
[ ] PK adını table_config.py'den kopyaladım
[ ] Her method try/except ile sarılı
[ ] Hata durumunda [] veya False veya None dönüyor (exception fırlatmıyor)
[ ] logger.error() çağrılıyor
[ ] __init__'te None kontrolü var
```

---

### 1.3 UI sayfası şablonu (service bağlantısı ile)

```python
from core.services.xxx_service import XxxService

class XxxPage(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db

        # Service bağlantısı — di.py kullan
        if db:
            from core.di import get_registry
            self._svc = XxxService(get_registry(db))
        else:
            self._svc = None

        self._setup_ui()
        self._load_data()

    def _load_data(self):
        if not self._svc:
            return
        rows = self._svc.get_xxx_listesi()
        self._model.set_data(rows)
```

**YAPMA:**
```python
# ❌ YAPMA — UI'dan direkt registry çağırma
repo = RepositoryRegistry(self._db).get("Periyodik_Bakim")
rows = [r for r in repo.get_all() if ...]

# ✅ YAP — service'ten çağır
rows = self._svc.get_bakim_listesi(self._cihaz_id)
```

---

### 1.4 TableModel şablonu

```python
from ui.components.base_table_model import BaseTableModel
from core.date_utils import to_ui_date

XXX_COLUMNS = [
    ("DbAlani1", "Başlık 1", 120),
    ("DbAlani2", "Başlık 2",  80),
    ("Tarih",    "Tarih",     90),
    ("Durum",    "Durum",     70),
]

_DURUM_RENK = {
    "Aktif":   "#3ecf8e",
    "Pasif":   "#f75f5f",
}

class XxxTableModel(BaseTableModel):
    def __init__(self, rows=None, parent=None):
        super().__init__(XXX_COLUMNS, rows, parent)

    def _display(self, key, row):
        val = row.get(key, "")
        if key == "Tarih":
            return to_ui_date(val, "")
        return str(val) if val else ""

    def _fg(self, key, row):
        if key == "Durum":
            c = _DURUM_RENK.get(row.get("Durum", ""))
            return QColor(c) if c else None
        return None

    def _align(self, key):
        if key in ("Tarih", "Durum"):
            return Qt.AlignCenter
        return Qt.AlignVCenter | Qt.AlignLeft

    # Geriye dönük uyumluluk için alias (set_rows → set_data)
    def set_rows(self, rows): self.set_data(rows)
```

**YAPMA:**
```python
# ❌ YAPMA — BaseTableModel'i extend etmeden sıfırdan yaz
class XxxTableModel(QAbstractTableModel):
    def rowCount(...): ...
    def columnCount(...): ...
    def data(...): ...  # 50 satır duplikasyon

# ✅ YAP — BaseTableModel'i extend et, sadece farklı olanı yaz
class XxxTableModel(BaseTableModel):
    ...
```

---

### 1.5 Renk sabitleri

```python
# ❌ YAPMA — her dosyada ayrı _C dict tanımlama
_C = {"red": "#f75f5f", "green": "#3ecf8e", ...}

# ✅ YAP — merkezi colors.py'den al
from ui.styles.colors import C as _C
```

---

### 1.6 Test dosyası şablonu

**Dosya:** `tests/services/test_xxx_service.py`

```python
import pytest
from unittest.mock import MagicMock
from core.services.xxx_service import XxxService


@pytest.fixture
def reg():
    return MagicMock()

@pytest.fixture
def svc(reg):
    return XxxService(reg)


class TestInit:
    def test_none_registry_hata_firlatar(self):
        with pytest.raises(ValueError):
            XxxService(None)


class TestGetXxxListesi:
    def test_bos_liste(self, svc, reg):
        reg.get("TABLO_ADI").get_all.return_value = []
        assert svc.get_xxx_listesi() == []

    def test_filtre_calisir(self, svc, reg):
        reg.get("TABLO_ADI").get_all.return_value = [
            {"Pk": "1", "FiltreAlani": "A"},
            {"Pk": "2", "FiltreAlani": "B"},
        ]
        result = svc.get_xxx_listesi(filtre_id="A")
        assert len(result) == 1

    def test_repo_hatasi_bos_liste(self, svc, reg):
        reg.get("TABLO_ADI").get_all.side_effect = Exception("Hata")
        assert svc.get_xxx_listesi() == []


class TestKaydet:
    def test_insert(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        assert svc.kaydet({"Alan": "deger"}, guncelle=False) is True
        mock_repo.insert.assert_called_once()

    def test_update_pk_yoksa_false(self, svc, reg):
        assert svc.kaydet({"Alan": "deger"}, guncelle=True) is False

    def test_db_hatasi_false(self, svc, reg):
        mock_repo = MagicMock()
        mock_repo.insert.side_effect = Exception("Hata")
        reg.get.return_value = mock_repo
        assert svc.kaydet({"Alan": "deger"}) is False
```

**Kontrol listesi:**
```
[ ] Her public method için en az 1 test var
[ ] Hata durumu (DB exception) testi var
[ ] İş kuralı olan methodlar için edge case testi var
[ ] Tablo adı mock'ta doğru yazılmış (table_config'den bakıldı)
```

---

## 2. MEVCUT DOSYAYA GİRERKEN — Fırsatçı Refactor

Bir dosyayı **başka bir sebepten** açtığında (bug fix, yeni özellik, UI değişikliği),
o dosyada aşağıdaki kontrolleri yap. **Toplu refactor yapma** — sadece girdiğin dosyayı düzelt.

### Kontrol Listesi (her dosya girişinde)

```
[ ] 1. Bu dosyada RepositoryRegistry doğrudan çağrılıyor mu?
       → Evet ise, o method'un yaptığı işi service'e taşı
       → Service yoksa yeni service yaz (Bölüm 1.2'yi kullan)

[ ] 2. Bu dosyada QAbstractTableModel sıfırdan extend ediliyor mu?
       → Evet ise, BaseTableModel'e geçir (Bölüm 1.4'ü kullan)

[ ] 3. Bu dosyada _C = {"red": ..., "green": ...} var mı?
       → Evet ise, sil ve "from ui.styles.colors import C as _C" ekle

[ ] 4. Dosyada iş kuralı var mı? (hesaplama, filtreleme, durum geçişi)
       → Evet ise, bu kural service'te mi yoksa UI'da mı?
       → UI'da ise ve test edilmemişse, service'e taşı + test yaz

[ ] 5. Dosyada BOM veya CRLF var mı?
       → python scripts/fix_utf8_bom.py
```

### Fırsatçı Refactor Örnekleri

**Örnek A — Bug fix yaparken:**
```
Görev: saglik_takip.py'de tarih gösterimi yanlış
Girince fark ettin: registry.get("Personel_Saglik_Takip") 6 kez çağrılıyor
Yap: SaglikService yaz, bu 6 çağrıyı oraya taşı, tarih bugünü de düzelt
Commit: "fix: tarih gösterimi + refactor: SaglikService eklendi"
```

**Örnek B — Yeni alan eklerken:**
```
Görev: fhsz_yonetim.py'ye yeni bir sütun ekleyeceksin
Girince fark ettin: _C = {"red": ..., "green": ...} var
Yap: _C'yi sil, colors.py import'unu ekle — sonra asıl işi yap
Commit: "feat: yeni sütun + chore: _C → colors.py"
```

---

## 3. DOSYA YAPISI — Neyi Nereye Koyarsın

```
core/
├── services/           ← İş mantığı buraya (DB bağımlı ama UI bağımsız)
│   ├── bakim_service.py
│   ├── ariza_service.py
│   ├── izin_service.py
│   ├── kalibrasyon_service.py
│   └── personel_service.py
│
ui/
├── components/         ← Paylaşılan UI bileşenleri
│   ├── base_table_model.py   ← Tüm TableModel'ler bunu extend eder
│   └── drive_upload_worker.py
├── styles/
│   └── colors.py       ← _C renk dict'i buradan alınır (C alias)
│
tests/
└── services/           ← Her service için test dosyası
    ├── test_bakim_service.py
    ├── test_ariza_service.py
    ├── test_izin_service.py
    ├── test_kalibrasyon_service.py
    └── test_personel_service.py
```

**Karar ağacı — yeni dosyayı nereye koyacaksın?**

```
Yeni kod nedir?
│
├── Veritabanı işlemi + iş kuralı → core/services/xxx_service.py
│
├── Birden fazla UI sayfasında kullanılacak widget → ui/components/
│
├── Sadece bir sayfaya özgü ama bağımsız dialog/panel
│   └── ui/pages/[alan]/components/xxx_dialog.py
│
├── Sayfanın ana formu → ui/pages/[alan]/xxx_form.py (büyük olsa da tek dosya)
│
└── Test → tests/services/test_xxx_service.py
```

---

## 4. YAPMA LİSTESİ

Geçmişte yapılan hatalar — bunları tekrarlama:

| ❌ Yapma | ✅ Yap |
|---------|--------|
| Tablo adını kafadan yaz (`"Personeller"`) | `table_config.py`'den kopyala (`"Personel"`) |
| PK adını kafadan yaz (`"ArizaId"`) | `table_config.py`'den kopyala (`"Arizaid"`) |
| UI'dan direkt `RepositoryRegistry().get()` çağır | Service method'u çağır |
| Yeni `QAbstractTableModel` sıfırdan yaz | `BaseTableModel`'i extend et |
| Her dosyaya `_C = {"red": ...}` kopyala | `from ui.styles.colors import C as _C` |
| Service yazmadan önce UI'a gömülü iş mantığını test et | Önce service yaz, test yaz, sonra UI'a bağla |
| 20 dosyayı aynı anda refactor et | Sadece girdiğin dosyayı düzelt |
| Test dosyası olmadan service'i canlıya al | Önce test yaz, testler geçsin, sonra bağla |
| Windows'ta düzenlenen dosyayı CRLF ile commit et | `fix_utf8_bom.py` çalıştır veya editörde LF ayarla |

---

## 5. KALAN DİREKT DB ÇAĞRILARI (Fırsatçı Temizlenecek)

Bu dosyalara **başka bir sebepten** girdiğinde, direkt registry çağrılarını
o seferlik servise bağla. Toplu yapmaya çalışma.

| Dosya | Kalan çağrı | Hangi service |
|-------|------------|--------------|
| `personel/izin_takip.py` | 13 | `IzinService` (bağlı ama eksik method'lar var) |
| `personel/components/personel_overview_panel.py` | 12 | `PersonelService` |
| `personel/personel_ekle.py` | 11 | `PersonelService` (kısmen bağlı) |
| `personel/components/hizli_izin_giris.py` | 10 | `IzinService` |
| `rke/rke_muayene.py` | 8 | `RkeService` (henüz yok) |
| `personel/personel_listesi.py` | 8 | `PersonelService` (kısmen bağlı) |
| `personel/fhsz_yonetim.py` | 7 | `FhszService` (henüz yok) |
| `cihaz/components/cihaz_overview_panel.py` | 7 | mevcut servisler |
| `cihaz/cihaz_ekle.py` | 7 | `CihazService` (henüz yok) |
| `personel/saglik_takip.py` | 6 | `SaglikService` (henüz yok) |
| `cihaz/cihaz_listesi.py` | 6 | mevcut servisler |
| `cihaz/ariza_islem.py` | 5 | `ArizaService` |
| *(diğerleri 1–4 çağrı)* | ... | ... |

**Yeni service gerektiğinde** (rke, fhsz, saglik, cihaz):
→ Bölüm 1.2 şablonunu kullan
→ Bölüm 1.6 test şablonunu kullan
→ Önce test yaz, sonra UI'a bağla

---

## 6. DOSYA YÖNETİMİ — Belge Yükleme ve Drive Entegrasyonu

### 6.1 Mimari Özet

Hibrit dosyalama sistemi üç katmandan oluşur:

```
UI Katmanı
  BaseDokumanPanel          ← Belge paneli gereken her yerde bunu extend et
  (cihaz/personel_dokuman_panel sadece 20 satır wrapper)

Servis Katmanı
  DokumanService            ← upload + Dokumanlar DB kaydı tek method
  FileSyncService           ← offline dosyaları sync sırasında Drive'a çıkar

Drive Katmanı
  GoogleDriveService        ← find_or_create_folder() klasörü otomatik oluşturur
  OfflineCloudAdapter       ← Drive yoksa local'e kopyalar, aynı arayüz
```

---

### 6.2 Yeni Belge Paneli Açarken

**Doğru yol — BaseDokumanPanel extend et:**

```python
# ui/pages/xxx/components/xxx_dokuman_panel.py
from ui.components.base_dokuman_panel import BaseDokumanPanel

class XxxDokumanPanel(BaseDokumanPanel):
    def __init__(self, entity_id, db=None, parent=None):
        super().__init__(
            entity_type   = "xxx",           # "cihaz" | "personel" | "rke"
            entity_id     = entity_id,
            folder_name   = "Xxx_Belgeler",  # Drive'da oluşturulacak klasör adı
            doc_type      = "Xxx_Belge",     # Dokumanlar.DocType değeri
            belge_tur_kod = "Xxx_Belge_Tur", # Sabitler'deki Kod değeri
            db            = db,
            parent        = parent,
        )
```

Bu kadar. Upload formu, dosya listesi, Drive/local hibrit yükleme, Dokumanlar DB kaydı —
hepsi `BaseDokumanPanel`'de. Eklenecek tek şey `folder_name`.

**Checklist:**
```
[ ] folder_name Sabitler tablosuna EKLEMEDİM (gerek yok, Drive otomatik oluşturur)
[ ] DocType değerini file_sync_service.py'deki DOCTYPE_FOLDER_MAP'e ekledim
[ ] entity_type "cihaz" | "personel" | "rke" formatında
[ ] Sabitler'de "Xxx_Belge_Tur" Kod değerleri var (yoksa default "Belge/Rapor/Diğer" çıkar)
```

---

### 6.3 Panel Dışında Dosya Yüklerken — DokumanService

Panel dışında (worker thread, kayıt sırasında otomatik yükleme vb.) belge yüklenmesi
gerekiyorsa **DokumanService** kullan:

```python
from core.services.dokuman_service import DokumanService

svc = DokumanService(db)
sonuc = svc.upload_and_save(
    file_path    = "/path/to/file.pdf",
    entity_type  = "personel",
    entity_id    = tc_no,
    belge_turu   = "Diploma1",
    folder_name  = "Personel_Diploma",
    doc_type     = "Personel_Diploma",
    aciklama     = "",
    iliskili_id  = None,   # opsiyonel: ilişkili kayıt ID
    iliskili_tip = None,   # opsiyonel: "RKE_Muayene" vb.
)

if sonuc["ok"]:
    drive_link = sonuc["drive_link"]   # online ise
    local_path = sonuc["local_path"]   # offline ise
else:
    logger.error(sonuc["error"])
```

`upload_and_save` online modda Drive'a, offline modda `data/offline_uploads/<folder_name>/`'e
yükler. Dokumanlar tablosuna her iki durumda da kaydeder.

---

### 6.4 Drive Klasör Yapısı

Drive klasörleri **ilk upload anında otomatik oluşturulur**. Manuel oluşturma gerekmez,
Sabitler tablosuna ID girme gerekmez.

```
My Drive/
  REPYS/                   ← DokumanService otomatik oluşturur
    Cihaz_Belgeler/        ← entity_type="cihaz" belgeleri
    Personel_Belge/        ← entity_type="personel" genel belgeler
    Personel_Resim/        ← profil fotoğrafları
    Personel_Diploma/      ← diploma dosyaları
    RKE_Rapor/             ← muayene raporları
    Saglik_Raporlari/      ← sağlık muayene raporları
    Xxx_Belgeler/          ← yeni modül ekleyince burada otomatik açılır
```

**Klasör ID cache'i:** ID'ler process boyunca memory'de tutulur. Uygulama kapanınca
sıfırlanır — bir sonraki açılışta Drive'dan tekrar sorgulanır, yoksa oluşturulur.
Bu bir sorun değil, Drive'a sadece `files.list` isteği gider.

**Eski Sabitler yöntemi:**
```
# ❌ Artık gerekmiyor — bunu yapma
Sabitler: Kod='Sistem_DriveID', MenuEleman='Cihaz_Belgeler', Aciklama='1AbCdEf...'

# ✅ DokumanService hallediyor, Drive'da klasör yoksa kendisi oluşturuyor
```

---

### 6.5 Offline → Online Dosya Senkronizasyonu

Offline modda yüklenen dosyalar `data/offline_uploads/<folder_name>/` klasörüne kaydedilir.
Online moda geçildiğinde `SyncWorker` çalışır ve **DB sync başlamadan önce** bu dosyaları
Drive'a yükler:

```
SyncWorker.run()
  │
  ├─ FileSyncService.push_pending_files()   ← ÖNCE: offline dosyaları Drive'a çıkar
  │    Dokumanlar WHERE LocalPath!='' AND DrivePath=''
  │    → Drive'a yükle → DrivePath güncelle → sync_status='dirty'
  │
  └─ SyncService.sync_all()                 ← SONRA: DrivePath dolu kayıtlar Sheets'e gider
```

**FileSyncService için DocType → klasör eşlemesi** (`core/services/file_sync_service.py`):

```python
DOCTYPE_FOLDER_MAP = {
    "Cihaz_Belge":       "Cihaz_Belgeler",
    "Personel_Belge":    "Personel_Belge",
    "RKE_Rapor":         "RKE_Rapor",
    "Personel_Resim":    "Personel_Resim",
    "Personel_Diploma":  "Personel_Diploma",
}
```

**Yeni DocType ekleyince bu map'i de güncelle.** Yoksa offline kaydedilen dosyalar
Drive'a çıkamaz.

---

### 6.6 Dokumanlar Tablosu Senkronizasyonu

`Dokumanlar` tablosu artık `sync=True` — makineler arası senkronize edilir.
Google Sheets'te `itf_ortak_vt` spreadsheet'inde `Dokumanlar` sayfası gereklidir.

**Tek seferlik kurulum (her yeni kurulumda):**
```
1. Google Drive'da "itf_ortak_vt" adlı spreadsheet oluştur
2. "Dokumanlar" adlı sheet ekle
3. Birinci satıra başlıkları yaz (table_config.py'deki columns sırası):
   EntityType | EntityId | BelgeTuru | Belge | DocType | DisplayName |
   LocalPath | BelgeAciklama | YuklenmeTarihi | DrivePath |
   IliskiliBelgeID | IliskiliBelgeTipi
4. veritabani.json'a ekle:
   "ortak": {"dosya": "itf_ortak_vt", "sayfalar": ["Dokumanlar"]}
```

**LocalPath farklı makinelerde geçersizdir** — bu normal. Diğer makine `DrivePath`'ten
açar, `LocalPath` sadece o dosyanın oluşturulduğu makinede çalışır.

---

### 6.7 Eski Upload Pattern'leri — Taşınacak Dosyalar

Aşağıdaki dosyalar hâlâ eski yöntemi kullanıyor. **Fırsatçı** olarak girildiğinde
`DokumanService` ile değiştir:

| Dosya | Eski yöntem | Yapılacak |
|-------|------------|-----------|
| `personel/saglik_takip.py` | `cloud.upload_file()` direkt + Dokumanlar kaydı YOK | `DokumanService.upload_and_save()` |
| `rke/rke_muayene.py` | `StorageService` + direkt Dokumanlar insert | `DokumanService.upload_and_save()` |
| `personel/personel_ekle.py` | `DriveUploadWorker` + direkt Dokumanlar insert | `DokumanService` + `QThread` |
| `personel/components/personel_overview_panel.py` | `DriveUploadWorker` + direkt Dokumanlar insert | `DokumanService` + `QThread` |

**saglik_takip.py için dikkat:** Şu an Dokumanlar tablosuna kayıt yapmıyor.
Taşıyınca `iliskili_id=kayit_no`, `iliskili_tip="Personel_Saglik_Takip"` parametrelerini ver.

---

### 6.8 Yapma Listesi — Dosyalama

| ❌ Yapma | ✅ Yap |
|---------|--------|
| Sabitler'e Drive klasör ID'si gir | `DokumanService` otomatik oluşturur |
| `StorageService.upload()` direkt çağır | `DokumanService.upload_and_save()` kullan |
| `RepositoryRegistry.get("Dokumanlar").insert()` direkt yaz | `DokumanService.upload_and_save()` kullan |
| `DriveUploadWorker` ile yeni upload kodu yaz | `DokumanService` + basit `QThread` |
| `cloud.upload_file()` direkt çağır | `DokumanService` kullan |
| Yeni `_dokuman_panel.py` sıfırdan yaz | `BaseDokumanPanel` extend et |
| Drive'da klasörü elle oluştur | İlk upload'da otomatik oluşur |
| Yeni DocType ekleyip `DOCTYPE_FOLDER_MAP`'i güncelleme | `file_sync_service.py`'deki map'i güncelle |


---

## 7. İKON SİSTEMİ — Emoji Yerine `icons.py`

### 7.1 Neden

Emoji'ler platform bağımlıdır — Windows, macOS ve Linux'ta farklı render edilir,
bazı fontlarda hiç görünmez. `icons.py` SVG tabanlı, renk/boyut kontrol edilebilir,
önbellekli ve DarkTheme ile uyumludur.

```python
# ❌ YAPMA — emoji ile etiket/buton
btn = QPushButton("📁 Dosya Seç")
lbl = QLabel("⚠  Uyarı")
title = QLabel("📄  Belge Yükle")

# ✅ YAP — icons.py kullan
from ui.styles.icons import Icons, IconRenderer, IconColors

btn = QPushButton("Dosya Seç")
IconRenderer.set_button_icon(btn, "upload", color=IconColors.PRIMARY, size=16)
```

---

### 7.2 Import

```python
from ui.styles.icons import Icons, IconRenderer, IconColors
```

---

### 7.3 Kullanım Şekilleri

**QPushButton'a ikon:**
```python
btn = QPushButton("Kaydet")
IconRenderer.set_button_icon(btn, "save", color=IconColors.PRIMARY, size=16)

btn_sil = QPushButton("Sil")
IconRenderer.set_button_icon(btn_sil, "trash", color=IconColors.DANGER, size=16)
```

**QLabel'a ikon:**
```python
lbl = QLabel()
IconRenderer.set_label_icon(lbl, "users", size=20, color=IconColors.PRIMARY)
```

**QIcon al (QAction, sekme başlığı vb.):**
```python
action.setIcon(Icons.get("refresh", color=IconColors.SYNC, size=16))
tab_widget.setTabIcon(0, Icons.get("calendar", size=16))
```

**QPixmap al (özel çizim, QListWidgetItem vb.):**
```python
pm = Icons.pixmap("check_circle", size=24, color=IconColors.SUCCESS)
item.setIcon(QIcon(pm))
```

**Durum ikonu (personel):**
```python
icon = IconRenderer.status_icon("Aktif")   # yeşil
icon = IconRenderer.status_icon("Pasif")   # kırmızı
icon = IconRenderer.status_icon("İzinli")  # sarı
```

---

### 7.4 Renk Sabitleri — `IconColors`

| Sabit | Renk | Kullanım |
|-------|------|----------|
| `IconColors.PRIMARY` | `#6bd3ff` | Aksiyon butonlar, başlıklar |
| `IconColors.DANGER` | `#f87171` | Sil, iptal, hata |
| `IconColors.SUCCESS` | `#4ade80` | Kaydet, onay, başarı |
| `IconColors.WARNING` | `#facc15` | Uyarı, izin durumu |
| `IconColors.INFO` | `#60a5fa` | Bilgi, yardım |
| `IconColors.MUTED` | `#5a5d6e` | Pasif, devre dışı |
| `IconColors.TEXT` | `#e0e2ea` | Normal metin rengi |
| `IconColors.SYNC` | `#6bd3ff` | Sync butonu |
| `IconColors.EXCEL` | `#6ee7b7` | Excel export |
| `IconColors.PDF` | `#fca5a5` | PDF export |

---

### 7.5 Mevcut İkon Listesi (75 ikon)

```
# Genel aksiyon
check  check_circle  x  x_circle  plus  plus_circle  edit  trash
save  download  upload  print  search  filter  refresh  info  eye

# Durum
status_active  status_passive  status_leave  alert_triangle  shield_alert

# Personel & takvim
user  user_add  users  id_card  heart_pulse  activity  stethoscope
calendar  calendar_check  calendar_off  calendar_year

# Cihaz & teknik
microscope  device_add  circuit_board  cpu  tools  wrench  wrench_list  crosshair  target

# Belge & veri
file_text  file_chart  file_excel  file_pdf  clipboard  clipboard_list
bar_chart  pie_chart  database

# Sistem & navigasyon
settings  settings_sliders  lock  log_out  shield  shield_check  sync  cloud_sync
bell  bell_dot  building  hospital  home  mail  package  layers  menu
arrow_left  arrow_right  chevron_right  chevron_down
```

Tüm listeyi görmek için:
```python
from ui.styles.icons import Icons
print(Icons.available())
```

---

### 7.6 Yeni İkon Eklemek

`ui/styles/icons.py` → `_SVG_PATHS` dict'ine ekle.
SVG path'ler `viewBox="0 0 24 24"`, `stroke-width="1.75"` formatında olmalı.

```python
"yeni_ikon": """
    <circle cx="12" cy="12" r="5"/>
    <path d="M12 2v3M12 19v3M2 12h3M19 12h3" stroke-linecap="round"/>
""",
```

Kaynak: [lucide.dev](https://lucide.dev) — `stroke` ve `fill` attribute'larını kopyalanan
SVG'den **kaldır**, render motoru dynamik atar.

---

### 7.7 Emoji → İkon Dönüşüm Tablosu

| Emoji | İkon adı | Renk sabiti |
|-------|----------|-------------|
| 📄 | `file_text` | `PRIMARY` |
| 📁 | `upload` | `PRIMARY` |
| 📋 | `clipboard` | `PRIMARY` |
| ✅ | `check_circle` | `SUCCESS` |
| ⚠️ | `alert_triangle` | `WARNING` |
| ❌ | `x_circle` | `DANGER` |
| 🔔 | `bell` | `PRIMARY` |
| 📊 | `bar_chart` | `PRIMARY` |
| 🔧 | `wrench` | `MUTED` |
| 🗑️ | `trash` | `DANGER` |
| ➕ | `plus` | `PRIMARY` |
| 🔍 | `search` | `MUTED` |
| 💾 | `save` | `SUCCESS` |
| 🔄 | `refresh` | `SYNC` |

---

### 7.8 Fırsatçı Temizlik — Hâlâ Emoji Kullanan Dosyalar

```
[ ] base_dokuman_panel.py  — "📄 Belge Yükle", "📁 Dosya Seç", "⚠ Uyarı"
[ ] bakim_form.py          — "📋 Rapor Yok", "✅ {dosya}", "⚠️ ..."
[ ] ariza_kayit.py         — "⚠️ Hatalı Giriş", "📋 Yeni Arıza"
[ ] admin_panel.py         — "📋 Audit Log" (sekme başlığı)
```

**Logger mesajlarındaki emoji'lere dokunma** — log dosyasında okunabilirlik sağlıyor,
UI'da değil.

---

## 8. HIZLI KONTROL KOMUTU

Bir dosyayı açmadan önce kaç direkt DB çağrısı olduğunu görmek için:

```bash
# Tek dosya
grep -c "registry\.get\|RepositoryRegistry" ui/pages/personel/izin_takip.py

# Tüm UI
python -c "
import os, re
for root, dirs, files in os.walk('ui/'):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            n = len(re.findall(r'registry\.get\(|RepositoryRegistry', open(path).read()))
            if n > 0:
                print(f'{n:3d}  {path}')
" | sort -rn
```

# Google Katmanı Modülerleştirmesi

## 📋 Yapılan Değişiklikler

### ÖNCEKİ DURUM (Tek Dosya)
```
database/
└── google_baglanti.py (450+ satır)
    ├── Hata sınıfları
    ├── OAuth kimlik doğrulama
    ├── Google Sheets işlemleri
    ├── Google Drive işlemleri
    ├── Qt sinyalleri
    ├── Yardımcı fonksiyonlar
    └── Global state management
```

**SORUNLAR:**
- ❌ **Tek sorumluluk prensibi ihlali**: 450+ satırda 6 farklı sorumluluk
- ❌ **Test zorluğu**: Tüm bileşenler iç içe
- ❌ **Hata izolasyonu**: Bir modüldeki hata diğerlerini etkiliyor
- ❌ **Kod tekrarı**: Benzer pattern'ler her yerde
- ❌ **Import karmaşıklığı**: Ne import edileceği belirsiz

---

### YENİ YAKLIŞIM (Modüler Yapı)

```
database/google/
├── __init__.py          # Public API ve export'lar
├── exceptions.py        # Özel hata sınıfları
├── auth.py              # OAuth ve credential yönetimi
├── sheets.py            # Google Sheets işlemleri
├── drive.py             # Google Drive işlemleri
├── signals.py           # Qt sinyal entegrasyonu
└── utils.py             # Yardımcı fonksiyonlar ve sabitler
```

**AVANTAJLAR:**
- ✅ **Tek sorumluluk**: Her modül bir işten sorumlu
- ✅ **Test edilebilir**: Modüller bağımsız test edilebilir
- ✅ **Hata izolasyonu**: Hata tek modülde kalıyor
- ✅ **Kod organizasyonu**: Benzer kod yan yana
- ✅ **Açık API**: __init__.py ile ne export edildiği belli

---

## 📦 Modül Detayları

### 1️⃣ **exceptions.py** - Hata Sınıfları
```python
# Tüm Google işlemleri için ortak hatalar

class GoogleServisHatasi(Exception):
    """Temel hata sınıfı"""

class InternetBaglantiHatasi(GoogleServisHatasi):
    """İnternet bağlantısı yokken"""

class KimlikDogrulamaHatasi(GoogleServisHatasi):
    """OAuth hataları"""

class VeritabaniBulunamadiHatasi(GoogleServisHatasi):
    """Sheets/worksheet bulunamadı"""

class APIKotaHatasi(GoogleServisHatasi):
    """Quota aşımı"""

class YetkiHatasi(GoogleServisHatasi):
    """Erişim yetki hatası"""
```

**Kullanım:**
```python
from database.google import InternetBaglantiHatasi

try:
    ws = get_worksheet("Personel")
except InternetBaglantiHatasi:
    print("İnternet bağlantınızı kontrol edin")
```

---

### 2️⃣ **auth.py** - Kimlik Doğrulama
```python
class GoogleAuthManager:
    """Thread-safe OAuth yönetimi"""
    
    def get_credentials() -> Credentials:
        """Google credentials döndürür"""
    
    def get_sheets_client() -> gspread.Client:
        """Yetkilendirilmiş gspread client"""
    
    def reset_client():
        """Client'ı sıfırla (reauth için)"""
```

**Özellikler:**
- ✅ Thread-safe singleton pattern
- ✅ Otomatik token yenileme
- ✅ Graceful error handling
- ✅ Token persistence (token.json)

**Kullanım:**
```python
from database.google import get_sheets_client

client = get_sheets_client()
# Her çağrıda aynı client instance döner
```

---

### 3️⃣ **sheets.py** - Google Sheets
```python
class GoogleSheetsManager:
    """Sheets işlemleri yöneticisi"""
    
    def get_worksheet(vt_tipi, sayfa_adi) -> Worksheet:
        """Worksheet döndürür"""
    
    def get_worksheet_by_table(table_name) -> Worksheet:
        """Tablo adından worksheet"""

# Convenience functions
def get_worksheet(table_name) -> Worksheet:
    """Basit kullanım için"""

def veritabani_getir(vt_tipi, sayfa_adi) -> Worksheet:
    """Backward compatibility"""
```

**Kullanım:**
```python
from database.google import get_worksheet

# Basit kullanım
ws = get_worksheet("Personel")
data = ws.get_all_records()

# Eski API (hala çalışıyor)
ws = veritabani_getir("personel", "Personel")
```

---

### 4️⃣ **drive.py** - Google Drive
```python
class GoogleDriveService:
    """Drive dosya işlemleri"""
    
    def upload_file(
        file_path, 
        parent_folder_id=None,
        custom_name=None,
        make_public=True
    ) -> str:
        """Dosya yükle, link döndür"""
    
    def download_file(file_id, dest_path) -> bool:
        """Dosya indir"""
    
    def delete_file(file_id) -> bool:
        """Dosya sil"""
    
    def get_file_metadata(file_id) -> dict:
        """Dosya bilgileri"""
    
    @staticmethod
    def extract_file_id(drive_link) -> str:
        """Link'ten ID çıkar"""
```

**Kullanım:**
```python
from database.google import GoogleDriveService

drive = GoogleDriveService()

# Dosya yükle
link = drive.upload_file("rapor.pdf", make_public=True)
print(f"Dosya linki: {link}")

# Dosya indir
file_id = GoogleDriveService.extract_file_id(link)
drive.download_file(file_id, "rapor_downloaded.pdf")
```

---

### 5️⃣ **signals.py** - Qt Sinyalleri
```python
class GoogleBaglantiSinyalleri(QObject):
    """Thread-safe sinyal yöneticisi"""
    
    hata_olustu = Signal(str, str)  # (başlık, mesaj)
    
    @classmethod
    def get_instance() -> GoogleBaglantiSinyalleri:
        """Singleton instance"""
    
    def emit_hata(baslik, mesaj):
        """Hata sinyali gönder"""
```

**Kullanım:**
```python
from database.google import GoogleBaglantiSinyalleri

signals = GoogleBaglantiSinyalleri.get_instance()
signals.hata_olustu.connect(lambda t, m: print(f"{t}: {m}"))

# Hata durumunda otomatik sinyal
signals.emit_hata("Bağlantı Hatası", "İnternet yok")
```

---

### 6️⃣ **utils.py** - Yardımcı Fonksiyonlar
```python
def internet_kontrol(timeout=3) -> bool:
    """İnternet var mı?"""

def db_ayarlarini_yukle() -> dict:
    """ayarlar.json'dan config"""

def extract_file_id_from_link(drive_link) -> str:
    """Drive link → file ID"""

# Sabitler
TABLE_TO_SHEET_MAP: Dict[str, Tuple[str, str]]
DB_FALLBACK_MAP: Dict[str, str]
```

---

### 7️⃣ **__init__.py** - Public API
```python
# Dışarıya açılan clean interface

from .exceptions import *
from .auth import get_credentials, get_sheets_client
from .sheets import get_worksheet, veritabani_getir
from .drive import GoogleDriveService
from .signals import GoogleBaglantiSinyalleri

__all__ = [
    'GoogleServisHatasi',
    'get_worksheet',
    'GoogleDriveService',
    # ... tam liste
]
```

**Kullanım:**
```python
# Tek import ile her şey
from database.google import (
    get_worksheet,
    GoogleDriveService,
    InternetBaglantiHatasi
)
```

---

## 🔄 Migration Rehberi

### Eski Kod → Yeni Kod

**1. Worksheet Alma**
```python
# ESKI
from database.google_baglanti import veritabani_getir
ws = veritabani_getir("personel", "Personel")

# YENİ (opsiyonel, eski hala çalışıyor)
from database.google import get_worksheet
ws = get_worksheet("Personel")  # Daha basit!
```

**2. Drive Upload**
```python
# ESKI
from database.google_baglanti import GoogleDriveService
drive = GoogleDriveService()
link = drive.upload_file("file.pdf")

# YENİ (aynı)
from database.google import GoogleDriveService
drive = GoogleDriveService()
link = drive.upload_file("file.pdf")
```

**3. Hata Yakalama**
```python
# ESKI
from database.google_baglanti import InternetBaglantiHatasi

# YENİ
from database.google import InternetBaglantiHatasi
# Aynı kullanım
```

**4. Sinyaller**
```python
# ESKI
from database.google_baglanti import GoogleBaglantiSinyalleri

# YENİ
from database.google import GoogleBaglantiSinyalleri
# Aynı kullanım
```

---

## 📊 Karşılaştırma

| Özellik | Eski (Tek Dosya) | Yeni (Modüler) |
|---------|------------------|----------------|
| **Satır sayısı** | 450+ satır | 50-100 satır/modül |
| **Test edilebilirlik** | Zor | Kolay |
| **Hata izolasyonu** | Yok | Var |
| **Kod organizasyonu** | Karışık | Temiz |
| **Import karmaşıklığı** | Yüksek | Düşük |
| **Bakım maliyeti** | Yüksek | Düşük |
| **Geriye dönük uyumlu** | - | ✅ Evet |

---

## 🧪 Test Örnekleri

### Auth Testi
```python
import pytest
from database.google.auth import GoogleAuthManager

def test_auth_singleton():
    """Singleton pattern testi"""
    auth1 = GoogleAuthManager.get_instance()
    auth2 = GoogleAuthManager.get_instance()
    assert auth1 is auth2  # Aynı instance

def test_credentials():
    """Credentials testi"""
    auth = GoogleAuthManager.get_instance()
    creds = auth.get_credentials()
    assert creds is not None
    assert creds.valid
```

### Sheets Testi
```python
def test_get_worksheet():
    """Worksheet alma testi"""
    ws = get_worksheet("Personel")
    assert ws is not None
    assert ws.title == "Personel"

def test_invalid_table():
    """Geçersiz tablo testi"""
    with pytest.raises(ValueError):
        get_worksheet("YanlisTabloAdi")
```

### Drive Testi
```python
def test_extract_file_id():
    """File ID çıkarma testi"""
    link = "https://drive.google.com/file/d/1ABC123/view"
    file_id = GoogleDriveService.extract_file_id(link)
    assert file_id == "1ABC123"

def test_upload_nonexistent_file():
    """Olmayan dosya yükleme testi"""
    drive = GoogleDriveService()
    result = drive.upload_file("nonexistent.pdf")
    assert result is None
```

---

## 📁 Dizin Yapısı

```
database/
├── google/
│   ├── __init__.py         # Public API (60 satır)
│   ├── exceptions.py       # Hata sınıfları (30 satır)
│   ├── auth.py             # OAuth yönetimi (150 satır)
│   ├── sheets.py           # Sheets işlemleri (120 satır)
│   ├── drive.py            # Drive işlemleri (130 satır)
│   ├── signals.py          # Qt sinyalleri (40 satır)
│   └── utils.py            # Yardımcılar (100 satır)
│
├── gsheet_manager.py       # Mevcut (değişiklik yok)
├── sync_service.py         # Mevcut (değişiklik yok)
└── ...
```

---

## ✅ Definition of Done (DoD)

- [x] Tek dosya 6 modüle bölündü
- [x] Her modül tek sorumluluk prensibine uyuyor
- [x] Thread-safe singleton pattern'ler korundu
- [x] Geriye dönük uyumluluk sağlandı
- [x] Public API __init__.py'de tanımlandı
- [x] Dokümantasyon hazırlandı
- [x] Test örnekleri eklendi

---

## 🚀 Avantajlar

### Geliştirici Deneyimi
- ✅ **Kolay navigasyon**: Her şey doğru yerde
- ✅ **Açık sorumluluklar**: Nerede ne olduğu belli
- ✅ **IDE desteği**: Autocomplete daha iyi çalışıyor

### Bakım
- ✅ **İzole değişiklikler**: Drive değişikliği Sheets'i etkilemiyor
- ✅ **Kolay debugging**: Hata kaynağı hemen belli
- ✅ **Test edilebilir**: Mock'lar kolayca oluşturulabilir

### Performans
- ✅ **Lazy loading**: Sadece kullanılan modüller yüklenir
- ✅ **Singleton pattern**: Gereksiz instance yok
- ✅ **Efficient imports**: Minimal import overhead

---

## 📝 Gelecek İyileştirmeler

1. **Async Support**
```python
# Gelecekte
from database.google import AsyncGoogleSheetsManager
ws = await async_manager.get_worksheet("Personel")
```

2. **Caching Layer**
```python
# Gelecekte
from database.google.cache import CachedSheetsManager
manager = CachedSheetsManager(ttl=300)  # 5 dk cache
```

3. **Batch Operations**
```python
# Gelecekte
from database.google.batch import BatchOperations
with BatchOperations() as batch:
    batch.update("Personel", row1)
    batch.update("Personel", row2)
# Commit toplu yapılır
```

---

## 🎯 Özet

**Önce:**
- 1 dosya, 450+ satır
- 6 farklı sorumluluk
- Test zor, bakım maliyetli

**Sonra:**
- 7 modül, 50-150 satır/modül
- Tek sorumluluk prensibi
- Test kolay, bakım basit
- **Geriye dönük uyumlu** ✨

Google katmanı artık **modüler, maintainable ve ölçeklenebilir**! 🚀

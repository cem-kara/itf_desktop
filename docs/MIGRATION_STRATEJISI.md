# Güvenli Migration Stratejisi

## 📋 Yapılan Değişiklikler

### 1️⃣ **migrations.py - Versiyon Tabanlı Sistem**

**YENİ ÖZELLİKLER:**
- ✅ Otomatik şema versiyonlama
- ✅ Her migration öncesi otomatik yedekleme
- ✅ Veri kaybı olmadan şema güncellemeleri
- ✅ Rollback desteği (yedeklerden geri yükleme)
- ✅ Eski yedeklerin otomatik temizlenmesi (son 10 yedek tutulur)

**ÖNCEKİ YAKLAŞIM (KALDIRILDI):**
```python
# Şema uyumsuzsa → TÜM VERİYİ SİL
if "MezunOlunanFakulte" not in columns:
    MigrationManager(DB_PATH).reset_database()  # ❌ VERİ KAYBI!
```

**YENİ YAKLAŞIM:**
```python
# Migration'ları akıllıca uygula
migration_manager.run_migrations()  # ✅ VERİ KORUNUR
```

---

### 2️⃣ **main.pyw - Akıllı Başlangıç Kontrolü**

**ÖNCE:**
```python
def ensure_database():
    # Tek kolon kontrolü
    if "MezunOlunanFakulte" not in columns:
        # TÜM VERİTABANINI SİL VE YENİDEN OLUŞTUR
        MigrationManager(DB_PATH).reset_database()
```

**SONRA:**
```python
def ensure_database():
    # Otomatik migration yönetimi
    migration_manager = MigrationManager(DB_PATH)
    migration_manager.run_migrations()  # Sadece gerekli adımları uygula
```

---

## 🔄 Migration Sistemi Nasıl Çalışır?

### Şema Versiyonları

```
v0: Veritabanı yok (ilk kurulum)
v1: Tüm temel tablolar oluşturuldu
v2: sync_status ve updated_at kolonları eklendi
v3: (Gelecekte yeni özellikler...)
```

### Migration Akışı

```
1. Uygulama Başlatılıyor
   ↓
2. Mevcut Şema Versiyon Kontrolü
   ↓
3. Versiyonlar Karşılaştırılıyor
   ├─ Güncel → Devam et
   ├─ Eski → Migration gerekli
   └─ Yeni → Uyarı (uygulama güncellenmeli)
   ↓
4. [EĞER MIGRATION GEREKLİYSE]
   ├─ Otomatik Yedekleme
   ├─ Migration Adımlarını Uygula (v1 → v2 → v3...)
   ├─ Her Adım Sonrası Versiyon Güncelle
   └─ Başarı Logu
   ↓
5. Uygulama Hazır ✓
```

---

## 📊 Örnek Senaryolar

### ✅ Senaryo 1: İlk Kurulum (v0 → v2)

```
[Durum] Veritabanı dosyası yok
[Akış]
  1. Schema version = 0 (tablo bile yok)
  2. Migration v1 başlıyor...
     - Tüm tabloları oluştur
     - Schema version = 1
  3. Migration v2 başlıyor...
     - sync_status kolonlarını ekle (zaten CREATE'de var, atlanır)
     - Schema version = 2
  4. Tamamlandı ✓

[Sonuç] Tüm tablolar son haliyle oluşturuldu
[Kayıp] Yok
```

---

### ✅ Senaryo 2: Eski Şema Güncelleme (v1 → v2)

```
[Durum] Veritabanı var ama sync_status kolonları yok
[Akış]
  1. Schema version = 1
  2. Otomatik yedekleme → /data/backups/db_backup_20250210_143022.db
  3. Migration v2 başlıyor...
     - Personel tablosuna sync_status ekle ✓
     - Personel tablosuna updated_at ekle ✓
     - Izin_Giris tablosuna sync_status ekle ✓
     - ... (tüm tablolar)
     - Schema version = 2
  4. Tamamlandı ✓

[Sonuç] Mevcut veriler korundu, yeni kolonlar eklendi
[Kayıp] Yok
[Yedek] Geri yükleme için mevcut
```

---

### ✅ Senaryo 3: Zaten Güncel (v2 → v2)

```
[Durum] Veritabanı güncel
[Akış]
  1. Schema version = 2
  2. CURRENT_VERSION = 2
  3. Eşit → Migration atlanır
  4. "Şema güncel (v2)" logu

[Sonuç] Hiçbir işlem yapılmadı
[Performans] Anında başlangıç
```

---

### ⚠️ Senaryo 4: Versiyon Uyumsuzluğu (v3 → v2)

```
[Durum] Veritabanı daha yeni versiyon (gelecekten)
[Akış]
  1. Schema version = 3
  2. CURRENT_VERSION = 2
  3. DB > CODE → UYARI
  4. "Uygulama güncellemesi gerekebilir" uyarısı

[Sonuç] Uygulama başlamaz (veri bütünlüğü korunur)
[Çözüm] Uygulamayı güncelleyin
```

---

## 🛠️ Migration Metodu Ekleme Rehberi

Yeni bir şema değişikliği eklemek için:

### 1. `CURRENT_VERSION` Artır

```python
class MigrationManager:
    CURRENT_VERSION = 3  # 2'den 3'e çıkar
```

### 2. Yeni Migration Metodu Ekle

```python
def _migrate_to_v3(self):
    """
    v2 → v3: Personel tablosuna profil_resmi_url kolonu ekleme
    """
    conn = self.connect()
    cur = conn.cursor()
    
    try:
        # Kolon var mı kontrol et
        cur.execute("PRAGMA table_info(Personel)")
        existing_columns = {row[1] for row in cur.fetchall()}
        
        if "profil_resmi_url" not in existing_columns:
            cur.execute("""
                ALTER TABLE Personel 
                ADD COLUMN profil_resmi_url TEXT
            """)
            logger.info("  Personel.profil_resmi_url eklendi")
        
        conn.commit()
        logger.info("v3: Profil resmi URL kolonu eklendi")
        
    finally:
        conn.close()
```

### 3. Test Et

```bash
# İlk test: Yeni kurulum
rm data/itf_desktop.db
python main.pyw
# Beklenen: v0 → v1 → v2 → v3

# İkinci test: Mevcut v2'den güncelleme
# (v2 veritabanı kullan)
python main.pyw
# Beklenen: v2 → v3 (sadece)
```

---

## 🔒 Güvenlik ve Yedekleme

### Otomatik Yedekleme

```
/data/backups/
  ├── db_backup_20250210_140523.db
  ├── db_backup_20250210_141234.db
  ├── db_backup_20250210_143022.db  ← En son
  └── ... (son 10 yedek tutulur)
```

### Manuel Yedekten Geri Yükleme

```bash
# 1. Uygulamayı kapat
# 2. Mevcut veritabanını yedekle (ekstra güvenlik)
cp data/itf_desktop.db data/itf_desktop_current.db

# 3. İstediğiniz yedekten geri yükle
cp data/backups/db_backup_20250210_143022.db data/itf_desktop.db

# 4. Uygulamayı başlat
python main.pyw
```

### Acil Durum Reset (⚠️ VERİ SİLİNİR)

```python
# Sadece ciddi veri bozulması durumunda kullanın!
from database.migrations import MigrationManager
from core.paths import DB_PATH

manager = MigrationManager(DB_PATH)
manager.reset_database()  # ⚠️ TÜM VERİ SİLİNİR
```

---

## 📈 Avantajlar

| Özellik | Eski Sistem | Yeni Sistem |
|---------|------------|-------------|
| **Veri Kaybı** | ❌ Her şema değişikliğinde tüm veri silinir | ✅ Veri korunur |
| **Yedekleme** | ❌ Manuel | ✅ Otomatik |
| **Rollback** | ❌ İmkansız | ✅ Yedeklerden geri yükleme |
| **Versiyon Takibi** | ❌ Yok | ✅ schema_version tablosu |
| **Güvenli Güncelleme** | ❌ Hayır | ✅ Evet |
| **Geliştirici Deneyimi** | ❌ Kötü (veri kaybı korkusu) | ✅ İyi (güvenli test) |

---

## 🧪 Test Senaryoları

### Test 1: İlk Kurulum
```bash
# Veritabanını sil
rm data/itf_desktop.db

# Uygulamayı başlat
python main.pyw

# Beklenen Log:
# "Veritabanı bulunamadı — ilk kurulum yapılıyor"
# "Migration v1 uygulanıyor..."
# "v1: Tüm tablolar oluşturuldu"
# "Migration v2 uygulanıyor..."
# "v2: sync_status ve updated_at kolonları eklendi"
# "✓ Tüm migration'lar başarıyla tamamlandı"
```

### Test 2: v1'den v2'ye Güncelleme
```bash
# Eski şema (sync_status yok) veritabanı kullan
# Uygulamayı başlat
python main.pyw

# Beklenen Log:
# "Veritabanı bulundu — şema kontrolü yapılıyor"
# "Veritabanı yedeklendi: .../db_backup_20250210_143022.db"
# "Migration başlıyor: v1 → v2"
# "Migration v2 uygulanıyor..."
# "  Personel.sync_status eklendi"
# "  Personel.updated_at eklendi"
# ...
# "✓ Tüm migration'lar başarıyla tamamlandı"
```

### Test 3: Zaten Güncel
```bash
# Güncel veritabanı kullan
python main.pyw

# Beklenen Log:
# "Veritabanı bulundu — şema kontrolü yapılıyor"
# "Şema güncel (v2)"
# "Veritabanı hazır ✓"
```

---

## ✅ Definition of Done (DoD)

- [x] Uyumlu olmayan şema, veri silinmeden migration ile güncelleniyor
- [x] Uygulama açılışında data kaybı yaşanmıyor
- [x] Her migration öncesi otomatik yedekleme yapılıyor
- [x] Rollback mekanizması mevcut
- [x] Versiyon takibi schema_version tablosu ile yapılıyor
- [x] Eski yedekler otomatik temizleniyor (son 10 tutulur)
- [x] İlk kurulum sorunsuz çalışıyor
- [x] Mevcut veritabanından güncelleme sorunsuz çalışıyor
- [x] Zaten güncel şema anında başlıyor

---

## 📝 Gelecek Migration Örnekleri

### Örnek 1: Yeni Kolon Ekleme (v3)
```python
def _migrate_to_v3(self):
    """v2 → v3: Cihazlar tablosuna QR kod kolonu"""
    # ALTER TABLE Cihazlar ADD COLUMN qr_kod TEXT
```

### Örnek 2: Tablo Ekleme (v4)
```python
def _migrate_to_v4(self):
    """v3 → v4: Bildirimler tablosu oluşturma"""
    # CREATE TABLE Bildirimler (...)
```

### Örnek 3: Veri Dönüşümü (v5)
```python
def _migrate_to_v5(self):
    """v4 → v5: Tarih formatını dönüştür"""
    # UPDATE Personel SET DogumTarihi = strftime('%Y-%m-%d', DogumTarihi)
```

---

## 🎯 Sonuç

Artık veritabanı şema güncellemeleri:
- ✅ **Güvenli** (otomatik yedekleme)
- ✅ **Veri korur** (migration tabanlı)
- ✅ **Geri alınabilir** (yedeklerden restore)
- ✅ **Takip edilebilir** (versiyon sistemi)
- ✅ **Kolay geliştirilebilir** (yeni migration eklemek basit)

**Veri kaybı riski tamamen ortadan kaldırıldı!** 🎉

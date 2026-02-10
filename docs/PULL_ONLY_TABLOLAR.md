# Pull-Only Tablolar - Konfigürasyon ve Kullanım

## 📋 Yapılan Değişiklikler

### 1️⃣ **table_config.py - Açık Pull-Only Tanımları**

**ÖNCE:**
```python
"Sabitler": {
    "pk": "Rowid",
    "columns": ["Rowid", "Kod", "MenuEleman", "Aciklama"]
    # sync_mode belirtilmemiş - varsayılan davranış
},

"Tatiller": {
    "pk": "Tarih",
    "columns": ["Tarih", "ResmiTatil"]
    # sync_mode belirtilmemiş - varsayılan davranış
}
```

**SONRA:**
```python
"Sabitler": {
    "pk": "Rowid",
    "columns": ["Rowid", "Kod", "MenuEleman", "Aciklama"],
    "sync_mode": "pull_only"  # ✅ Açıkça belirtildi
},

"Tatiller": {
    "pk": "Tarih",
    "columns": ["Tarih", "ResmiTatil"],
    "sync_mode": "pull_only"  # ✅ Açıkça belirtildi
}
```

---

### 2️⃣ **sync_service.py - Pull-Only Mantığı İyileştirmeleri**

**YENİ ÖZELLİKLER:**

1. **Detaylı Loglama:**
```python
log_sync_step(table_name, "pull_only_start")
log_sync_step(table_name, "pull_only_read", len(records))
log_sync_step(table_name, "pull_only_complete", inserted)
```

2. **Hata Yönetimi:**
```python
try:
    # Her satır için ayrı try-catch
    for row in records:
        try:
            self.db.execute(...)
            inserted += 1
        except Exception as row_error:
            logger.warning(f"Satır eklenemedi: {row_error}")
            continue  # Diğer satırlara devam et
except Exception as e:
    log_sync_error(table_name, "pull_only", e)
    raise
```

3. **İstatistik Takibi:**
```python
stats = {'pushed': 0, 'pulled': inserted}
log_sync_complete(table_name, stats)
```

4. **Güvenlik Kontrolleri:**
```python
if not ws:
    logger.warning(f"{table_name} worksheet bulunamadı, atlanıyor")
    return
```

---

## 🎯 Pull-Only Modu Nedir?

### Tanım
Pull-only modda çalışan tablolar:
- ✅ **Sadece Google Sheets → Local** yönünde senkronize edilir
- ❌ **Local değişiklikler Google Sheets'e gönderilmez**
- 🔄 Her sync'te local tablo **tamamen silinip yeniden oluşturulur**

### Kullanım Alanları
| Tablo | Neden Pull-Only? |
|-------|------------------|
| **Sabitler** | Uygulama sabitleri merkezi olarak yönetilir (dropdown değerleri, kodlar) |
| **Tatiller** | Resmi tatil takvimi merkezi olarak güncellenir |

### Normal Sync ile Farkı

| Özellik | Normal Sync | Pull-Only |
|---------|-------------|-----------|
| **Yön** | Çift yönlü (↔️) | Tek yönlü (← Sheets) |
| **Local değişiklik** | Push edilir | Göz ardı edilir |
| **Dirty tracking** | Evet | Hayır |
| **Conflict resolution** | Gerekli | Gerekli değil |
| **Sync stratejisi** | Akıllı birleştirme | Tamamen değiştir |

---

## 📊 Sync Akışı

### Normal Tablolar (Örn: Personel)
```
1. Google Sheets'i oku
2. Local dirty kayıtları topla
3. PUSH: Dirty → Google Sheets (update + append)
4. Mark clean
5. PULL: Google Sheets → Local (new + update)
   - Local dirty kayıtlara dokunma
   - Clean kayıtları güncelle
```

### Pull-Only Tablolar (Sabitler, Tatiller)
```
1. Google Sheets'i oku
2. Local tabloyu SİL (DELETE FROM)
3. Sheets kayıtlarını ekle (INSERT)
   ✓ Basit
   ✓ Conflict yok
   ✓ Her zaman güncel
```

---

## 🧪 Test Senaryoları

### ✅ Senaryo 1: Normal Sync (Sabitler)

**Başlangıç:**
```sql
-- Google Sheets
Rowid | Kod      | MenuEleman | Aciklama
1     | IZIN_001 | Yıllık     | Yıllık izin
2     | IZIN_002 | Mazeret    | Mazeret izni

-- Local DB
Rowid | Kod      | MenuEleman | Aciklama
1     | IZIN_001 | Yıllık     | Yıllık izin
```

**Sync Sonrası:**
```sql
-- Local DB
Rowid | Kod      | MenuEleman | Aciklama
1     | IZIN_001 | Yıllık     | Yıllık izin
2     | IZIN_002 | Mazeret    | Mazeret izni  ← Yeni eklendi
```

**Log:**
```
[1/13] Sabitler sync başladı
  Sabitler pull_only modda çalışıyor
  Sabitler - pull_only_mode
  Sabitler - pull_only_start
  Google Sheets'ten 2 kayıt okundu
  Local Sabitler tablosu temizlendi
  Sabitler - pull_only_read (2 kayıt)
  Sabitler - pull_only_complete (2 kayıt)
  Sabitler pull_only: 2/2 kayıt yüklendi ✓
  Sync tamamlandı: Sabitler | Push: 0, Pull: 2
[1/13] Sabitler sync başarılı ✓
```

---

### ✅ Senaryo 2: Local Değişiklik Var (Pull-Only Davranışı)

**Başlangıç:**
```sql
-- Google Sheets
Tarih      | ResmiTatil
2025-01-01 | Yılbaşı
2025-05-01 | İşçi Bayramı

-- Local DB (kullanıcı manuel ekledi)
Tarih      | ResmiTatil
2025-01-01 | Yılbaşı
2025-12-31 | Yılsonu  ← Kullanıcı ekledi (ama yanlış)
```

**Sync Sonrası:**
```sql
-- Local DB (kullanıcı değişikliği kayboldu!)
Tarih      | ResmiTatil
2025-01-01 | Yılbaşı
2025-05-01 | İşçi Bayramı  ← Sheets'teki son hal
```

**Açıklama:**
- ✅ Bu **beklenen** davranıştır
- Pull-only tablolarda local değişiklikler korunmaz
- Google Sheets her zaman kaynak (source of truth)

---

### ✅ Senaryo 3: Satır Hatası (Resilience)

**Google Sheets:**
```
Rowid | Kod      | MenuEleman | Aciklama
1     | IZIN_001 | Yıllık     | OK
2     | (null)   | Mazeret    | ← Geçersiz Rowid
3     | IZIN_003 | Hastalık   | OK
```

**Sync Sonrası:**
```sql
-- Local DB
Rowid | Kod      | MenuEleman | Aciklama
1     | IZIN_001 | Yıllık     | OK
3     | IZIN_003 | Hastalık   | OK
-- Satır 2 atlandı
```

**Log:**
```
[1/13] Sabitler sync başladı
  Google Sheets'ten 3 kayıt okundu
  Local Sabitler tablosu temizlendi
  Satır eklenemedi: NOT NULL constraint failed: Sabitler.Rowid
  Sabitler pull_only: 2/3 kayıt yüklendi ✓
```

**Açıklama:**
- ✅ Geçersiz satır sync'i **durdurmadı**
- ✅ Diğer satırlar başarıyla eklendi
- ✅ Hata loglandı ama fatal olmadı

---

## 📝 Yeni Pull-Only Tablo Ekleme

### 1. table_config.py'de Tanımla
```python
"YeniTablo": {
    "pk": "TabloID",
    "columns": ["TabloID", "Alan1", "Alan2"],
    "sync_mode": "pull_only"  # ✅ Bunu ekle
}
```

### 2. Google Sheets'te Oluştur
```
- Sheet adı: YeniTablo
- Başlıklar: TabloID, Alan1, Alan2
```

### 3. Migration Ekle (migrations.py)
```python
def _migrate_to_v3(self):
    conn = self.connect()
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS YeniTablo (
            TabloID TEXT PRIMARY KEY,
            Alan1 TEXT,
            Alan2 TEXT,
            
            sync_status TEXT DEFAULT 'clean',
            updated_at TEXT
        )
    """)
    
    conn.commit()
    conn.close()
```

### 4. Test Et
```python
# Manuel test
from database.sync_service import SyncService
service = SyncService(db, registry)
service.sync_table("YeniTablo")

# Beklenen log:
# YeniTablo pull_only modda çalışıyor
# YeniTablo pull_only: X/X kayıt yüklendi ✓
```

---

## ⚠️ Önemli Notlar

### Pull-Only Tablolarda:
- ❌ **sync_status kullanılmaz** (her zaman clean)
- ❌ **Dirty tracking olmaz**
- ❌ **Local değişiklikler korunmaz**
- ✅ **Her sync'te tam yenileme**
- ✅ **Conflict yok** (tek kaynak)
- ✅ **Basit ve güvenilir**

### Hangi Tabloları Pull-Only Yapmalı?

**EVET (Pull-Only Uygun):**
- ✅ Uygulama sabitleri (dropdown değerleri)
- ✅ Sistem referans tabloları
- ✅ Merkezi yönetilen veriler
- ✅ Read-only veriler (kullanıcı düzenlemez)
- ✅ Küçük boyutlu tablolar (<1000 satır)

**HAYIR (Normal Sync Kullan):**
- ❌ Kullanıcı verisi (Personel, İzinler)
- ❌ Büyük tablolar (>1000 satır - performans)
- ❌ Çift yönlü senkronizasyon gereken veriler
- ❌ Değişiklik geçmişi takibi gereken veriler

---

## 🔍 Sorun Giderme

### Problem: Pull-only tablo sync olmuyor

**Kontrol Listesi:**
1. `table_config.py`'de `sync_mode: "pull_only"` var mı?
2. Google Sheets'te tablo mevcut mu?
3. Kolon adları eşleşiyor mu?
4. Log'da hata var mı?

**Debug:**
```python
# table_config kontrolü
print(TABLES["Sabitler"])
# Çıktı: {'pk': 'Rowid', 'columns': [...], 'sync_mode': 'pull_only'}

# Worksheet kontrolü
from database.google_baglanti import get_worksheet
ws = get_worksheet("Sabitler")
print(ws.get_all_records())
```

---

### Problem: Local değişiklikler kayboluyor

**Açıklama:**
- Bu **normal** davranıştır
- Pull-only tablolarda local değişiklikler korunmaz
- Google Sheets her zaman kaynak

**Çözüm:**
- Eğer local değişiklikler korunmalıysa → `sync_mode: "pull_only"` **kaldır**
- Normal sync moduna geç

---

## ✅ Definition of Done (DoD)

- [x] `table_config.py`'de Sabitler ve Tatiller `sync_mode: "pull_only"` ile tanımlandı
- [x] `sync_service.py`'de pull_only mantığı iyileştirildi
- [x] Detaylı loglama eklendi (pull_only_start, read, complete)
- [x] Hata yönetimi geliştirildi (satır bazında resilience)
- [x] İstatistik takibi eklendi
- [x] Worksheet bulunamama durumu handle edildi
- [x] Dokümantasyon hazırlandı
- [x] Test senaryoları tanımlandı

---

## 📈 Log Örnekleri

### Başarılı Pull-Only Sync
```
============================================================
SYNC İŞLEMİ BAŞLADI
============================================================
[1/13] Sabitler sync başladı
Sync başladı: Sabitler | Tablo: Sabitler | Adım: start
  Sabitler pull_only modda çalışıyor
  Sabitler - pull_only_mode | Tablo: Sabitler | Adım: pull_only_mode
  Sabitler - pull_only_start | Tablo: Sabitler | Adım: pull_only_start
  Google Sheets'ten 15 kayıt okundu
  Local Sabitler tablosu temizlendi
  Sabitler - pull_only_read (15 kayıt) | Tablo: Sabitler | Adım: pull_only_read | Kayıt: 15
  Sabitler - pull_only_complete (15 kayıt) | Tablo: Sabitler | Adım: pull_only_complete | Kayıt: 15
  Sabitler pull_only: 15/15 kayıt yüklendi ✓
  Sync tamamlandı: Sabitler | Push: 0, Pull: 15 | Tablo: Sabitler | Adım: complete
[1/13] Sabitler sync başarılı ✓
```

### Hatalı Satır Atlandı
```
[2/13] Tatiller sync başladı
  Tatiller pull_only modda çalışıyor
  Google Sheets'ten 10 kayıt okundu
  Local Tatiller tablosu temizlendi
  Satır eklenemedi: UNIQUE constraint failed: Tatiller.Tarih
  Satır eklenemedi: CHECK constraint failed: Tatiller
  Tatiller pull_only: 8/10 kayıt yüklendi ✓
```

---

## 🚀 Özet

Pull-only tablolar artık:
- ✅ Açıkça tanımlanmış (`sync_mode: "pull_only"`)
- ✅ Detaylı loglanıyor
- ✅ Hatalara dayanıklı
- ✅ İstatistikleri takip ediliyor
- ✅ Dokümante edilmiş

**Sonuç:** Pull-only modunun niyeti konfigürasyonda net, davranışı tahmin edilebilir ve hata durumları iyi yönetiliyor! 🎉

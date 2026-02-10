# Migration Hızlı Başvuru Kılavuzu

## 🚀 Hızlı Başlangıç

### Normal Kullanım
```python
# main.pyw içinde otomatik çalışır
ensure_database()
# Migration'lar otomatik uygulanır, veri korunur
```

### Manuel Migration
```python
from database.migrations import MigrationManager
from core.paths import DB_PATH

manager = MigrationManager(DB_PATH)
manager.run_migrations()
```

---

## 📝 Yeni Migration Ekleme (3 Adım)

### 1. Versiyon Numarasını Artır
```python
# migrations.py
class MigrationManager:
    CURRENT_VERSION = 3  # Önceki: 2
```

### 2. Migration Metodunu Yaz
```python
def _migrate_to_v3(self):
    """v2 → v3: Açıklama"""
    conn = self.connect()
    cur = conn.cursor()
    try:
        # Örnek: Yeni kolon ekle
        cur.execute("ALTER TABLE Personel ADD COLUMN yeni_alan TEXT")
        conn.commit()
        logger.info("v3: Yeni alan eklendi")
    finally:
        conn.close()
```

### 3. Test Et
```bash
python main.pyw
# Log'larda "Migration v3 uygulanıyor..." göreceksiniz
```

---

## 🔍 Sık Kullanılan Migration Örnekleri

### Yeni Kolon Ekleme
```python
def _migrate_to_vX(self):
    conn = self.connect()
    cur = conn.cursor()
    try:
        # Kolon var mı kontrol et (idempotent)
        cur.execute("PRAGMA table_info(Personel)")
        cols = {row[1] for row in cur.fetchall()}
        
        if "yeni_kolon" not in cols:
            cur.execute("""
                ALTER TABLE Personel 
                ADD COLUMN yeni_kolon TEXT DEFAULT 'varsayilan'
            """)
        
        conn.commit()
    finally:
        conn.close()
```

### Yeni Tablo Oluşturma
```python
def _migrate_to_vX(self):
    conn = self.connect()
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS Bildirimler (
                id TEXT PRIMARY KEY,
                baslik TEXT,
                icerik TEXT,
                tarih TEXT,
                okundu INTEGER DEFAULT 0
            )
        """)
        conn.commit()
    finally:
        conn.close()
```

### Veri Dönüştürme
```python
def _migrate_to_vX(self):
    conn = self.connect()
    cur = conn.cursor()
    try:
        # Tarih formatını dönüştür
        cur.execute("""
            UPDATE Personel 
            SET DogumTarihi = strftime('%Y-%m-%d', DogumTarihi)
            WHERE DogumTarihi IS NOT NULL
        """)
        conn.commit()
    finally:
        conn.close()
```

---

## 🔧 Sorun Giderme

### Problem: Migration hatası aldım
```bash
# 1. Log'lara bak
cat logs/app.log | grep -i migration

# 2. Yedekten geri yükle
cp data/backups/db_backup_TIMESTAMP.db data/itf_desktop.db

# 3. Tekrar dene
python main.pyw
```

### Problem: Şema versiyonu karışık
```python
# Manuel versiyon kontrolü
from database.migrations import MigrationManager
manager = MigrationManager("data/itf_desktop.db")
print(f"Mevcut versiyon: {manager.get_schema_version()}")
print(f"Hedef versiyon: {manager.CURRENT_VERSION}")
```

### Problem: Acil reset gerekli (⚠️ VERİ SİLİNİR)
```python
from database.migrations import MigrationManager
manager = MigrationManager("data/itf_desktop.db")
manager.reset_database()  # ⚠️ TÜM VERİ SİLİNİR
```

---

## 📊 Şema Versiyon Tablosu

```sql
-- Mevcut versiyonu görüntüle
SELECT * FROM schema_version ORDER BY version DESC;

-- Örnek çıktı:
-- version | applied_at              | description
-- 2       | 2025-02-10T14:30:22     | Migrated to v2
-- 1       | 2025-02-10T14:30:20     | Migrated to v1
```

---

## ✅ Migration Checklist

Yeni migration eklerken kontrol et:

- [ ] `CURRENT_VERSION` artırıldı mı?
- [ ] `_migrate_to_vX` metodu yazıldı mı?
- [ ] Migration idempotent mi? (birden fazla çalıştırılabilir)
- [ ] Başarılı log mesajı eklendi mi?
- [ ] Yeni kurulumda da çalışıyor mu? (create_tables güncellendi mi?)
- [ ] Test edildi mi? (hem yeni kurulum hem güncelleme)

---

## 🎯 Önemli Noktalar

1. **Her zaman idempotent yaz**: Migration'ın 2 kez çalışması sorun yaratmamalı
   ```python
   # Kötü
   cur.execute("ALTER TABLE X ADD COLUMN y TEXT")  # 2. çalışmada hata!
   
   # İyi
   if "y" not in existing_columns:
       cur.execute("ALTER TABLE X ADD COLUMN y TEXT")
   ```

2. **Yedekleme otomatik**: Migration öncesi her zaman yedek alınır

3. **Versiyon sıralı**: v1 → v2 → v3 şeklinde sırayla ilerle, atlamalar yapma

4. **CREATE TABLE güncellemelerini unutma**: Yeni kolon ekliyorsan `create_tables()` metodunu da güncelle

---

## 📞 Destek

Sorun yaşarsanız:
1. `logs/app.log` dosyasını kontrol edin
2. `data/backups/` dizinindeki yedekleri görün
3. Gerekirse eski yedekten geri yükleyin

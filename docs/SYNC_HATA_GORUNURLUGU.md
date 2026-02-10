# Sync Hata Görünürlüğü İyileştirmesi

## 📋 Yapılan Değişiklikler

### 1️⃣ **logger.py - Structured Logging Sistemi**

**YENİ ÖZELLİKLER:**
- ✅ **3 ayrı log dosyası**:
  - `app.log`: Tüm uygulama logları
  - `sync.log`: Sadece senkronizasyon logları
  - `errors.log`: Sadece hata logları
  
- ✅ **Structured logging**: Her log'a context eklenebiliyor
  ```python
  log_sync_step(table_name="Personel", step="push_update", count=5)
  # Output: 2025-02-10 14:30:22 - Personel - push_update (5 kayıt) | Tablo: Personel | Adım: push_update | Kayıt: 5
  ```

- ✅ **Kullanıcı dostu hata mesajları**:
  ```python
  get_user_friendly_error(error, table_name="Personel")
  # Returns: ("Personel: Bağlantı hatası", "İnternet bağlantınızı kontrol edin")
  ```

- ✅ **Yardımcı fonksiyonlar**:
  - `log_sync_start(table_name)`: Sync başlangıcını logla
  - `log_sync_step(table_name, step, count)`: Adım logla
  - `log_sync_error(table_name, step, error)`: Hata logla
  - `log_sync_complete(table_name, stats)`: Tamamlanmayı logla

---

### 2️⃣ **sync_worker.py - Detaylı Hata Raporlama**

**DEĞİŞİKLİKLER:**

**ÖNCE:**
```python
error = Signal(str)  # Sadece hata mesajı

self.error.emit(str(e))  # Ham hata mesajı
```

**SONRA:**
```python
error = Signal(str, str)  # (short_message, detailed_message)

# Kullanıcı dostu mesaj oluştur
short_msg, detail_msg = get_user_friendly_error(error)
self.error.emit(short_msg, detail_msg)
```

**YENİ LOGLAR:**
```
============================================================
SYNC İŞLEMİ BAŞLADI
============================================================
Tüm tabloların senkronizasyonu başlıyor...
[1/13] Personel sync başladı
  Personel - read_remote
  Personel - check_dirty
  ...
✓ Tüm tablolar başarıyla senkronize edildi
============================================================
SYNC İŞLEMİ TAMAMLANDI
============================================================
```

---

### 3️⃣ **main_window.py - Gelişmiş UI Feedback**

**YENİ ÖZELLİKLER:**

**Hata Mesajı İkilisi:**
```python
@Slot(str, str)
def _on_sync_error(self, short_msg, detail_msg):
    # short_msg: Status bar için kısa mesaj
    # detail_msg: Detaylı açıklama
```

**Status Bar'da:**
- Kısa hata mesajı gösteriliyor
- Tooltip'te detaylı bilgi

**Popup Dialog:**
- Anlaşılır hata başlığı
- Detaylı açıklama
- Çözüm önerileri
- Log dosyası yolları

**ÖRNEK POPUP:**
```
┌─────────────────────────────────────────┐
│ ⚠️  Senkronizasyon Hatası              │
├─────────────────────────────────────────┤
│ Personel: Bağlantı hatası               │
│                                         │
│ İnternet bağlantınızı kontrol edin     │
│                                         │
│ [Detayları Göster ▼]                   │
│                                         │
│ Hata zamanı: 14:30:22                  │
│                                         │
│ Çözüm önerileri:                       │
│ 1. İnternet bağlantınızı kontrol edin │
│ 2. Google Sheets erişim izinlerini    │
│    kontrol edin                        │
│ 3. Birkaç dakika bekleyip tekrar      │
│    deneyin                             │
│ 4. Sorun devam ederse log dosyalarını │
│    kontrol edin:                       │
│    - logs/app.log                      │
│    - logs/sync.log                     │
│    - logs/errors.log                   │
│                                         │
│            [ Tamam ]                    │
└─────────────────────────────────────────┘
```

---

### 4️⃣ **sync_service.py - Adım Adım Loglama**

**DEĞİŞİKLİKLER:**

**sync_all() metodunda:**
```python
# ÖNCE
logger.info(f"[{i}/{total}] {table_name} sync başladı")

# SONRA
logger.info(f"[{i}/{total}] {table_name} sync başladı")
log_sync_start(table_name)
# ... işlemler ...
log_sync_complete(table_name, stats={'pushed': 5, 'pulled': 3})
```

**sync_table() metodunda:**
```python
# Her adım loglanıyor
log_sync_step(table_name, "read_remote")
log_sync_step(table_name, "read_remote_complete", len(remote_rows))
log_sync_step(table_name, "check_dirty")
log_sync_step(table_name, "push_update", len(to_update))
log_sync_step(table_name, "push_append", len(to_append))
log_sync_step(table_name, "pull_remote")
log_sync_step(table_name, "pull_new", new_count)
log_sync_step(table_name, "pull_update", updated_count)
```

**Hata durumunda:**
```python
except Exception as e:
    log_sync_error(table_name, "sync_table", e)
    raise
```

---

## 📊 Log Dosyaları

### app.log - Tüm Loglar
```
2025-02-10 14:30:20 - INFO - ============================================================
2025-02-10 14:30:20 - INFO - SYNC İŞLEMİ BAŞLADI
2025-02-10 14:30:20 - INFO - ============================================================
2025-02-10 14:30:20 - INFO - Toplam 13 tablo senkronize edilecek
2025-02-10 14:30:20 - INFO - [1/13] Personel sync başladı
2025-02-10 14:30:20 - INFO - Sync başladı: Personel | Tablo: Personel | Adım: start
2025-02-10 14:30:21 - INFO - Personel - read_remote | Tablo: Personel | Adım: read_remote
2025-02-10 14:30:22 - INFO - Personel - read_remote_complete (150 kayıt) | Tablo: Personel | Adım: read_remote_complete | Kayıt: 150
2025-02-10 14:30:22 - INFO - Personel - check_dirty | Tablo: Personel | Adım: check_dirty
2025-02-10 14:30:22 - INFO -   Local dirty: 3
2025-02-10 14:30:22 - INFO - Personel - push_update (2 kayıt) | Tablo: Personel | Adım: push_update | Kayıt: 2
2025-02-10 14:30:23 - INFO -   PUSH güncelleme: 2
2025-02-10 14:30:23 - INFO - Personel - push_append (1 kayıt) | Tablo: Personel | Adım: push_append | Kayıt: 1
2025-02-10 14:30:23 - INFO -   PUSH yeni ekleme: 1
2025-02-10 14:30:23 - INFO - Personel - pull_remote | Tablo: Personel | Adım: pull_remote
2025-02-10 14:30:24 - INFO - Sync tamamlandı: Personel | Push: 3, Pull: 0 | Tablo: Personel | Adım: complete
2025-02-10 14:30:24 - INFO -   Personel sync tamamlandı ✓
2025-02-10 14:30:24 - INFO - [1/13] Personel sync başarılı ✓
```

### sync.log - Sadece Sync İşlemleri
```
2025-02-10 14:30:20 - SYNC İŞLEMİ BAŞLADI
2025-02-10 14:30:20 - Toplam 13 tablo senkronize edilecek
2025-02-10 14:30:20 - Sync başladı: Personel | Tablo: Personel | Adım: start
2025-02-10 14:30:21 - Personel - read_remote | Tablo: Personel | Adım: read_remote
2025-02-10 14:30:22 - Personel - read_remote_complete (150 kayıt) | Tablo: Personel | Adım: read_remote_complete | Kayıt: 150
2025-02-10 14:30:24 - Sync tamamlandı: Personel | Push: 3, Pull: 0 | Tablo: Personel | Adım: complete
```

### errors.log - Sadece Hatalar
```
2025-02-10 14:35:20 - ERROR - Izin_Giris sync hatası | sync_table | ConnectionError: Connection timeout | Tablo: Izin_Giris | Adım: sync_table
Traceback (most recent call last):
  File "/database/sync_service.py", line 120, in sync_table
    remote_rows, pk_index, ws = self.gsheet.read_all(table_name)
  File "/database/gsheet_manager.py", line 45, in read_all
    raise ConnectionError("Connection timeout")
ConnectionError: Connection timeout

2025-02-10 14:35:20 - ERROR - [3/13] Izin_Giris sync hatası: ConnectionError
2025-02-10 14:35:20 - ERROR -   - Izin_Giris: ConnectionError - Connection timeout
```

---

## 🎯 Hata Tipleri ve Kullanıcı Mesajları

| Hata Tipi | Kısa Mesaj | Detaylı Mesaj |
|-----------|------------|---------------|
| `ConnectionError` | "Bağlantı hatası" | "İnternet bağlantınızı kontrol edin" |
| `PermissionError` | "Yetki hatası" | "Google Sheets erişim yetkinizi kontrol edin" |
| `QuotaExceeded` | "API limit aşıldı" | "Lütfen birkaç dakika bekleyin ve tekrar deneyin" |
| `KeyError` | "Veri yapısı hatası" | "Tablo yapısında uyumsuzluk: {detay}" |
| `ValueError` | "Veri formatı hatası" | "Geçersiz veri: {detay}" |
| Diğer | "Sync hatası ({tip})" | "{ilk 100 karakter}" |

---

## 🧪 Test Senaryoları

### ✅ Senaryo 1: Başarılı Sync

**Akış:**
```
1. Kullanıcı sync butonuna basar
2. Status bar: "⏳ Senkronize ediliyor..."
3. Loglar:
   - SYNC İŞLEMİ BAŞLADI
   - [1/13] Personel sync başladı
   - ...tüm adımlar...
   - SYNC İŞLEMİ TAMAMLANDI
4. Status bar: "● Senkronize" (yeşil)
5. "Son sync: 14:30:22"
6. Aktif sayfa yenilenir
```

**Beklenen:**
- ✅ Hata popup'ı gösterilmez
- ✅ Log dosyalarında detaylı adımlar var
- ✅ sync.log'da sadece sync işlemleri
- ✅ errors.log boş

---

### ✅ Senaryo 2: Bağlantı Hatası

**Akış:**
```
1. İnternet bağlantısı kesilir
2. Sync başlar
3. Personel tablosu başarılı
4. Izin_Giris tablosu hata verir (ConnectionError)
5. Diğer tablolar devam eder
6. Sync tamamlanır (kısmi başarı)
```

**Kullanıcı Görür:**
```
Status Bar: "● 1 tabloda hata" (kırmızı)
Tooltip: "Başarısız tablolar: Izin_Giris"

Popup Dialog:
┌─────────────────────────────────┐
│ ⚠️  Senkronizasyon Hatası      │
│ 1 tabloda hata                  │
│ Başarısız tablolar: Izin_Giris  │
│ [Detayları Göster]              │
└─────────────────────────────────┘
```

**Log'da:**
```
app.log:
  [3/13] Izin_Giris sync hatası: ConnectionError
  SYNC ÖZETİ: 12/13 tablo başarılı
  Başarısız tablolar: 1
    - Izin_Giris: ConnectionError - Connection timeout

errors.log:
  Izin_Giris sync hatası | sync_table | ConnectionError: Connection timeout
  [Full traceback]
```

**Beklenen:**
- ✅ Kullanıcı hangi tablonun hata aldığını biliyor
- ✅ Hatanın nedeni anlaşılır
- ✅ Çözüm önerileri sunuluyor
- ✅ Log dosyası yolları veriliyor
- ✅ Diğer tablolar etkilenmiyor

---

### ✅ Senaryo 3: API Limit Aşımı

**Akış:**
```
1. Sync başlar
2. Google Sheets API limiti aşılır
3. QuotaExceeded hatası alınır
```

**Kullanıcı Görür:**
```
Status Bar: "● API limit aşıldı" (kırmızı)

Popup Dialog:
┌─────────────────────────────────────┐
│ ⚠️  Senkronizasyon Hatası          │
│ API limit aşıldı                    │
│ Lütfen birkaç dakika bekleyin ve   │
│ tekrar deneyin                      │
│ [Detayları Göster]                  │
└─────────────────────────────────────┘
```

**Beklenen:**
- ✅ Kullanıcı ne yapması gerektiğini biliyor
- ✅ Teknik jargon yok
- ✅ Aksiyon önerisi var

---

## 📈 İyileştirmeler Özeti

| Özellik | Önce | Sonra |
|---------|------|-------|
| **Hata mesajı** | "Senkron sırasında hata oluştu" | "Personel: Bağlantı hatası" |
| **Detay bilgisi** | Yok | "İnternet bağlantınızı kontrol edin" |
| **Log dosyası** | 1 dosya (app.log) | 3 dosya (app, sync, errors) |
| **Context tracking** | Yok | Tablo adı, adım, kayıt sayısı |
| **Kullanıcı popup'ı** | Yok | Detaylı açıklama + çözüm önerileri |
| **Adım loglama** | Minimal | Her adım detaylı loglanıyor |
| **Hata isolasyonu** | Tüm sync durur | Diğer tablolar devam eder |

---

## ✅ Definition of Done (DoD)

- [x] Hata alındığında kullanıcı neyin bozulduğunu anlayabiliyor
- [x] Log satırından tablo ve akış adımı görülebiliyor
- [x] Kullanıcıya anlaşılır kısa hata metni sağlanıyor
- [x] Status bar'da özet bilgi, tooltip'te detay var
- [x] Popup'ta çözüm önerileri sunuluyor
- [x] 3 ayrı log dosyası oluşturuluyor (app, sync, errors)
- [x] Her sync adımı structured logging ile loglanıyor
- [x] Hatalar tablo bazında izole ediliyor

---

## 🚀 Kullanım

### Loglara Bakmak

```bash
# Tüm loglar
tail -f logs/app.log

# Sadece sync işlemleri
tail -f logs/sync.log

# Sadece hatalar
tail -f logs/errors.log

# Belirli bir tablonun sync'i
grep "Personel" logs/sync.log

# Son 50 hata
tail -50 logs/errors.log
```

### Hata Analizi

```bash
# Hangi tablolarda hata var?
grep "sync hatası" logs/app.log | grep -oP '\[\d+/\d+\] \K\w+' | sort | uniq

# En çok hangi hata tipi?
grep "ERROR" logs/errors.log | grep -oP ': \K\w+Error' | sort | uniq -c | sort -rn

# Son sync özeti
grep "SYNC ÖZETİ" logs/app.log | tail -1
```

---

## 📝 Gelecek İyileştirmeler

- [ ] Sync progress bar (tablo bazında ilerleme)
- [ ] Hata istatistikleri sayfası (UI)
- [ ] Otomatik retry mekanizması
- [ ] Sync geçmişi log viewer (UI)
- [ ] Email bildirimleri (kritik hatalar için)

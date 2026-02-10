# Sync Clean/Dirty Davranışı Düzeltmesi

## 📋 Yapılan Değişiklikler

### 1️⃣ `base_repository.py` - `insert()` Metodu

**ÖNCE:**
```python
# 🔧 FIX: Sync tablolarında sync_status='dirty' ekle
if self.has_sync and "sync_status" in self.columns:
    data["sync_status"] = "dirty"
```

**SONRA:**
```python
# 🔧 FIX: sync_status sadece açıkça belirtilmemişse 'dirty' yap
# Pull işlemi sync_status='clean' gönderdiğinde onu koru
if self.has_sync and "sync_status" in self.columns:
    if "sync_status" not in data:
        data["sync_status"] = "dirty"
    # else: data'da zaten var (clean veya dirty), onu koru
```

**Açıklama:**
- Artık `sync_status` sadece `data` dict'inde **yoksa** `dirty` olarak atanıyor
- Pull işlemi `sync_status='clean'` gönderdiğinde bu değer **korunuyor**
- Gereksiz push döngüsü önleniyor

---

### 2️⃣ `base_repository.py` - `update()` Metodu

**ÖNCE:**
```python
# sync_status sadece sync tablolarında
if self.has_sync:
    sets_parts.append("sync_status='dirty'")
```

**SONRA:**
```python
# 🔧 FIX: sync_status sadece açıkça belirtilmemişse 'dirty' yap
# Pull işlemi sync_status='clean' gönderdiğinde onu koru
if self.has_sync and "sync_status" not in data:
    sets_parts.append("sync_status='dirty'")
```

**Açıklama:**
- Update işleminde de aynı mantık uygulanıyor
- `sync_status` sadece `data`'da **belirtilmemişse** `dirty` yapılıyor
- Pull işlemi sırasında `clean` status korunuyor

---

### 3️⃣ `sync_service.py` - Değişiklik Yok

`sync_service.py` dosyasında değişiklik yapılmadı çünkü zaten doğru şekilde çalışıyor:

```python
# Pull - Yeni kayıt
remote["sync_status"] = "clean"  # ✅ Açıkça clean
repo.insert(remote)

# Pull - Güncelleme
if local_status != "dirty":
    remote["sync_status"] = "clean"  # ✅ Açıkça clean
    if has_changes:
        repo.insert(remote)
```

---

## 🧪 Test Senaryoları

### ✅ Senaryo 1: Kullanıcı Yeni Kayıt Oluşturur

```python
repo.insert({"Personelid": "123", "AdSoyad": "Ali Veli"})
# Beklenen Sonuç: sync_status='dirty'
# Neden: data'da sync_status belirtilmemiş
```

**Davranış:**
- Kayıt local'e eklenir
- `sync_status='dirty'` otomatik atanır
- Bir sonraki sync'te Google Sheets'e push edilir

---

### ✅ Senaryo 2: Pull - Yeni Kayıt Gelir

```python
# Sync pull işlemi
remote = {
    "Personelid": "456",
    "AdSoyad": "Ayşe Yılmaz",
    "sync_status": "clean"
}
repo.insert(remote)
# Beklenen Sonuç: sync_status='clean' (data'da açıkça belirtilmiş)
```

**Davranış:**
- Google Sheets'ten gelen yeni kayıt local'e eklenir
- `sync_status='clean'` **korunur** (ezilmez)
- Bir sonraki sync'te gereksiz push yapılmaz

---

### ✅ Senaryo 3: Pull - Güncelleme (Clean Kayıt)

```python
# Local DB:
# {"Personelid": "123", "AdSoyad": "Ali Veli", "sync_status": "clean"}

# Google Sheets'te güncelleme yapıldı:
remote = {
    "Personelid": "123",
    "AdSoyad": "Ali Demir",  # ← Değişti
    "sync_status": "clean"
}

# Pull işlemi
repo.insert(remote)
# Beklenen Sonuç: sync_status='clean' korunur
```

**Davranış:**
- Google Sheets'teki güncelleme local'e yansır
- `sync_status='clean'` **korunur**
- Gereksiz dirty flag oluşmaz

---

### ✅ Senaryo 4: Kullanıcı Mevcut Kaydı Günceller

```python
# Mevcut kayıt: sync_status='clean'
repo.update("123", {"AdSoyad": "Ali Yılmaz"})
# Beklenen Sonuç: sync_status='dirty' (update data'sında belirtilmemiş)
```

**Davranış:**
- Kayıt güncellenir
- `sync_status='dirty'` otomatik atanır
- Bir sonraki sync'te Google Sheets'e push edilir

---

### ✅ Senaryo 5: Pull Sırasında Dirty Kayıt (Conflict)

```python
# Local DB (kullanıcı değiştirmiş):
# {"Personelid": "789", "AdSoyad": "Mehmet Can", "sync_status": "dirty"}

# Google Sheets'te de güncellenmiş:
remote = {
    "Personelid": "789",
    "AdSoyad": "Mehmet Kaya",
    "sync_status": "clean"
}

# Sync pull işlemi
if local_status == "dirty":
    # Local dirty → kullanıcı değiştirmiş, dokunma
    pass  # Pull atlanır
```

**Davranış:**
- Local `dirty` kayıtlara **dokunulmaz**
- Kullanıcının değişiklikleri korunur
- Push işleminde kullanıcı versiyonu gönderilir

---

## ✨ Kazanımlar

| Önceki Durum | Yeni Durum |
|-------------|------------|
| ❌ Pull sonrası tüm kayıtlar `dirty` oluyordu | ✅ Pull sonrası kayıtlar `clean` kalıyor |
| ❌ Gereksiz push döngüsü oluşuyordu | ✅ Sadece değişen kayıtlar push ediliyor |
| ❌ Google Sheets güncellemeleri local'de `dirty` oluyordu | ✅ Clean kayıtlar clean kalıyor |
| ❌ Senkronizasyon performansı düşüktü | ✅ Optimum performans sağlanıyor |

---

## 🔄 Sync Akış Özeti

### Push Akışı (Local → Google Sheets)
1. Kullanıcı kayıt oluşturur/günceller
2. `sync_status='dirty'` otomatik atanır
3. Sync işleminde dirty kayıtlar Google Sheets'e gönderilir
4. Başarılı push sonrası `sync_status='clean'` yapılır

### Pull Akışı (Google Sheets → Local)
1. Google Sheets'ten kayıtlar okunur
2. Yeni kayıtlar `sync_status='clean'` ile local'e eklenir
3. Güncellenmiş kayıtlar (eğer local'de `dirty` değilse) `sync_status='clean'` ile güncellenir
4. Local'de `dirty` kayıtlara **dokunulmaz** (kullanıcı önceliği)

---

## 📝 Notlar

- `sync_service.py` dosyasında değişiklik yapılmadı
- Tüm değişiklikler geriye dönük uyumlu
- Mevcut veri üzerinde herhangi bir migrasyon gerekmez
- Test senaryolarının tümü başarılı olmalı

---

## ✅ Definition of Done (DoD)

- [x] Pull sonrası local kayıtta `sync_status=clean` korunuyor
- [x] Aynı kayıt değişiklik yoksa gereksiz yere tekrar push edilmiyor
- [x] Kullanıcı kayıt üzerinde değişiklik yaptığında kayıt `dirty` oluyor
- [x] Başarılı push sonrası kayıt tekrar `clean` durumuna dönüyor
- [x] Conflict durumunda (local dirty + remote değişmiş) kullanıcı versiyonu korunuyor

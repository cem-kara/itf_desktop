# ITF Desktop Uygulaması – Proje Dokümantasyonu

## 1. Genel Bakış
ITF Desktop, Python (PySide6) ile geliştirilen, offline çalışabilen ve çoklu bilgisayarlarda veri paylaşımını Google Sheets senkronizasyonu ile sağlayan bir masaüstü uygulamasıdır.

Temel yaklaşım:
- **SQLite**: Her bilgisayarda yerel ve hızlı çalışma alanı
- **Google Sheets**: Merkezi, ücretsiz ve paylaşılabilir veri noktası

---

## 2. Mimari Yaklaşım

### 2.1 Katmanlı Mimari

```
UI (PySide6)
   ↓
Repository Katmanı
   ↓
SQLite (Local DB)
   ↓   (arka planda)
Sync Service
   ↓
Google Sheets
```

- UI veri kaynağını bilmez
- Tüm veri erişimi repository üzerinden yapılır
- Senkron işlemleri UI’dan bağımsızdır

---

## 3. Klasör Yapısı

```
itf_desktop/
│
├── main.pyw
│
├── core/
│   ├── config.py
│   ├── paths.py
│   └── logger.py
│
├── database/
│   ├── sqlite_manager.py
│   ├── migrations.py
│   ├── base_repository.py
│   ├── personel_repository.py
│   ├── gsheet_manager.py
│   └── sync_service.py
│
├── data/
│   └── local.db
│
├── logs/
│   └── app.log
│
└── ui/
```

---

## 4. Core Katmanı

### 4.1 paths.py
- Uygulama dizinlerini merkezi olarak yönetir
- data/ ve logs/ klasörlerini otomatik oluşturur

### 4.2 config.py
- Uygulama ayarları
- Versiyon, uygulama adı, senkron parametreleri

### 4.3 logger.py
- Konsol ve dosya bazlı loglama
- Senkron, hata ve işlem kayıtları

---

## 5. Database Katmanı

### 5.1 sqlite_manager.py
- SQLite bağlantısını yönetir
- execute / executemany metodları
- Foreign key desteği aktif

### 5.2 migrations.py
- Tüm tablo tanımları
- Şema değişiklikleri için tek merkez

Standart teknik alanlar:
- created_at
- updated_at
- updated_by
- sync_status

---

## 6. Repository Katmanı

### 6.1 base_repository.py

Tüm repository sınıflarının temelidir.

Sağladıkları:
- insert
- update
- delete
- get_by_id
- get_all
- get_dirty_records
- mark_clean

Otomatik davranışlar:
- updated_at güncelleme
- sync_status = dirty

### 6.2 personel_repository.py

Personel tablosuna özel işlemler:
- add_personel
- update_personel
- DataFrame çıktıları

---

## 7. Senkronizasyon Sistemi

### 7.1 sync_service.py

Görevleri:
1. Local dirty kayıtları tespit eder
2. Google Sheets’e gönderir (PUSH)
3. Google Sheets’ten verileri alır (PULL)
4. updated_at karşılaştırması yapar
5. Kazanan veriyi SQLite’a yazar

Çakışma kuralı:
> Son güncellenen kayıt kazanır

---

## 8. Google Sheets Entegrasyonu

### 8.1 gsheet_manager.py

- Google Sheets erişim katmanı
- UI tarafından doğrudan kullanılmaz
- Sadece SyncService tarafından çağrılır

Amaç:
- Google API kodlarını izole etmek
- Gelecekte farklı bir servisle kolayca değiştirebilmek

---

## 9. Loglama ve İzleme

Örnek log çıktısı:

```
SQLite bağlantısı açılıyor
Personel sync başladı
Local dirty kayıt sayısı: 1
GSheets kayıt sayısı: 0
Personel sync tamamlandı
```

Bu loglar:
- Senkron sisteminin çalıştığını
- Altyapının stabil olduğunu gösterir

---

## 10. Geliştirme Yol Haritası

### Kısa Vadeli
- Google Sheets gerçek entegrasyonu
- Diğer tablolar için repository’ler

### Orta Vadeli
- UI formları
- Yetkilendirme ve kullanıcı yönetimi

### Uzun Vadeli
- API tabanlı senkron
- SQLite yerine PostgreSQL opsiyonu

---

## 11. Sonuç

Bu dokümantasyon ile proje:
- Sürdürülebilir
- Genişletilebilir
- Kurumsal ölçekte geliştirilebilir

bir yapıya kavuşmuştur.


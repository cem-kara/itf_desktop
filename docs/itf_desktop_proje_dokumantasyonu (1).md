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

## 10. Otomatik Senkronizasyon (Yeni)

### 10.1 Açılışta ve Arka Planda Senkron

Uygulama açılışında ve belirli aralıklarla senkronizasyonun otomatik çalışması sağlanmıştır.

- Senkron işlemi **QThread** üzerinde çalışır
- UI donması engellenir
- Aynı anda birden fazla senkron çalışması önlenir

Teknik yaklaşım:
- `SyncWorker (QThread)` senkronu arka planda yürütür
- Global / instance referans tutulur (Qt thread yaşam döngüsü için zorunlu)
- `QTimer` ile periyodik tetikleme yapılır

Bu yapı sayesinde kullanıcı senkronu fark etmeden uygulamayı kullanmaya devam eder.

---

## 11. Google Sheets ↔ SQLite Gerçek Senkron Testleri

### 11.1 İlk Full Senkron (Pull)

- Google Sheets’te bulunan 183 Personel kaydı
- SQLite veritabanına hatasız şekilde aktarılmıştır
- Log çıktıları ile doğrulanmıştır

### 11.2 Local → Google Sheets (Push) Testi

- SQLite’ta bir Personel kaydı güncellenmiştir
- `sync_status = dirty` olarak işaretlenmiştir
- Senkron sırasında Google Sheets’e başarıyla gönderilmiştir

Kimlik_No alanında:
- string / number farkları
- boşluk problemleri

giderilerek güncelleme yerine yanlışlıkla yeni satır eklenmesi sorunu çözülmüştür.

---

## 12. Kritik Teknik Kararlar

### 12.1 Kolon İsimlendirme Stratejisi

- Google Sheets: kullanıcı dostu, boşluklu ve Türkçe başlıklar
- SQLite: sade, teknik, boşluksuz kolon isimleri

Bu iki yapı **GSheetManager** içinde kolon eşlemesi (map) ile ayrılmıştır.

### 12.2 Senkron Durum Yönetimi

- `sync_status = dirty` → Local değişiklik var
- `sync_status = clean` → Senkronize

Bu alan tüm tablolar için standarttır.

---

## 13. Mevcut Durum Özeti

Bu aşamada proje:

- Offline / online senaryolara hazır
- Çok bilgisayarlı kullanıma uygun
- Otomatik senkronizasyonlu
- Yeni tablo eklemeye hazır
- UI entegrasyonuna %100 hazır

---

## 14. Sonraki Adımlar (Plan)

### Kısa Vadeli
1. UI tarafında ilk ana ekran
2. Personel listeleme ve düzenleme formu
3. Senkron durumunun UI’da gösterimi

### Orta Vadeli
1. Diğer tabloların (cihaz, izin, sabitler) UI entegrasyonu
2. Yetkilendirme / kullanıcı rolleri
3. Senkron çakışma raporları

### Uzun Vadeli
1. Senkronun servis/API tabanlı hale getirilmesi
2. Mobil istemci desteği
3. SQLite yerine merkezi DB opsiyonu

---

## 15. Sonuç

ITF Desktop projesi bu aşamada:
- Deneysel olmaktan çıkmış
- Kurumsal ölçekte genişleyebilecek
- Bakımı ve geliştirmesi kolay

bir yazılım mimarisine ulaşmıştır.


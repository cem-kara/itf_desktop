# ADR-001 — Teknoloji Kararları (Sprint-1 / Adım 1)

- **Durum:** Kabul edildi
- **Tarih:** 2026-04-06
- **Kapsam:** Greenfield Personel Operasyon Platformu

## 1) Karar Özeti

Bu ADR ile aşağıdaki teknik kararlar kilitlenmiştir:

1. **Backend dili ve framework:** Python + FastAPI
2. **Frontend:** TypeScript + React/Next.js
3. **Veritabanı:** SQLite (MVP)
4. **Dosya depolama:** S3 uyumlu obje depolama (MinIO ile başlayıp S3’e taşınabilir)
5. **Asenkron işler/kuyruk:** Celery (Redis broker)
6. **API sözleşmesi:** OpenAPI-first yaklaşımı
7. **Mimari:** Modüler monolith (mikroservis değil)

---

## 2) Bağlam

Sistem; personel, izin, FHSZ/puantaj, sağlık, dozimetre, nöbet ve belge yönetimini tek platformda birleştirecek.
Öncelik: hızlı teslim + sürdürülebilir bakım + denetim izi.

---

## 3) Neden Bu Kararlar?

### 3.1 Python + FastAPI
- Domain policy ve veri odaklı süreçlerde geliştirme hızı yüksek.
- Pydantic ile tip güvenliği ve validasyon kolay.
- Async destekli, modern ve öğrenme eşiği düşük.

### 3.2 TypeScript + React/Next.js
- Ekran karmaşıklığı arttıkça tip güvenliği ve bileşen tekrar kullanımı avantajlı.
- Form/tablolar, state yönetimi ve erişim kontrolü için olgun ekosistem.

### 3.3 SQLite (MVP)
- Kurulum/operasyon maliyeti çok düşük, tek dosya ile hızlı başlangıç sağlar.
- WAL modu ile eşzamanlı okuma performansı MVP için yeterlidir.
- Migration disiplini korunursa ileride PostgreSQL'e taşınabilir.

### 3.4 S3/MinIO
- Belge yönetiminde versiyonlama, metadata, güvenli URL üretimi kolay.
- Ortamlar arasında taşınabilirlik sağlar.

### 3.5 Celery + Redis
- Import, rapor üretimi, arkaplan hesapları için olgun queue modeli.

### 3.6 Modüler monolith
- Erken fazda teslim hızını arttırır.
- Mikroservis operasyon yükünü başlangıçta engeller.

---

## 4) Sonuçlar (Etkiler)

### Pozitif
- Sprint-1’de hızlı dikey dilim çıkartma olasılığı artar.
- Ekip içi standartlar netleşir; mimari tartışmalar azalır.
- Test ve CI kuralları daha kolay standardize edilir.

### Negatif / Trade-off
- Python performans sınırları çok yüksek eşzamanlılıkta dikkat ister.
- Tek codebase büyüdükçe modül sınırlarını disiplinli korumak gerekir.

---

## 5) Uygulama Kuralları

1. API kontratı OpenAPI dosyasında versionlanmadan endpoint geliştirilmeyecek.
2. Domain policy kuralları servislere dağılmayacak; policy katmanında tutulacak.
3. Tüm write işlemlerinde audit zorunlu olacak.
4. CI kapıları (lint + test) yeşil değilse merge yapılmayacak.

---

## 6) Alternatifler ve Neden Elendi

- **Node.js (backend):** ekip Python odaklıysa teslim riski artar.
- **Java/.NET:** kurumsal olarak güçlü ama başlangıç hızında maliyet daha yüksek.
- **Go:** yüksek performans avantajlı; fakat domain geliştirme hızında ekip uyumu kritik.
- **Mikroservis başlangıcı:** operasyonel karmaşıklık erken aşamada gereksiz yük.

---

## 7) Bu ADR’nin Çıkış Kriteri

Aşağıdakiler tamamlandığında ADR-001 uygulanmaya geçmiş sayılır:
- Repo iskeletinde backend/frontend klasörleri açıldı.
- FastAPI `health` endpoint çalışıyor.
- Next.js başlangıç ekranı çalışıyor.
- SQLite dosyası + migration akışı doğrulandı.

---

## 8) Sonraki Adım

**Adım 2:** Domain sözlüğünü kilitle (`domain-glossary.md`).

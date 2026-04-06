# REPYS Next — Sıfırdan Yeni Program Önerisi (Revize)

Bu metin, **mevcut kodu referans almadan** tamamen sıfırdan kurulacak yeni bir sistem için öneridir.
Odak alanlar:
- Personel
- İzin (giriş + bakiye)
- FHSZ/Puantaj
- Sağlık takip
- Dozimetre takip
- Nöbet planlama
- Personel belge yönetimi

---

## 1) Ürün Vizyonu (Greenfield)

Amaç: Radyoloji birimi için tek ekrandan yönetilen, denetlenebilir, raporlanabilir ve sürdürülebilir bir **Personel Operasyon Platformu** geliştirmek.

Temel prensipler:
1. **Tek kimlik, tek doğruluk kaynağı** (personel master data)
2. **İş kuralları kodun her yerine dağılmayacak** (merkezi domain policy)
3. **Her kritik işlemin denetim izi olacak** (audit log + event)
4. **Offline/online kopmasına dayanıklı** (senkron kuyruk)
5. **Modüler ve test odaklı** (bağımsız geliştirme)

---

## 2) Sıfırdan Bilinçli Kapsam (MVP → v2)

### MVP (ilk 10–12 hafta)
- Personel kartı + durum yönetimi
- İzin talep/kayıt + bakiye hesaplama
- FHSZ dönem girişi + özet
- Sağlık muayene kayıtları + belge ilişkilendirme
- Dozimetre ölçüm import + uyarı paneli
- Nöbet manuel plan + temel otomatik öneri
- Rol bazlı yetkilendirme + audit

### v2
- Gelişmiş nöbet optimizasyon motoru
- Gelişmiş anomali tespiti (dozimetre)
- Yönetici dashboard + KPI ve trend raporları
- Kurum dışı sistemlerle entegrasyon API’leri

---

## 3) Önerilen Teknoloji Mimarisi

### 3.1 Uygulama mimarisi
- **Backend:** Python + FastAPI
- **Frontend:** Web tabanlı (React/Next.js) *veya* masaüstü devam edilecekse Qt istemcisi + backend API
- **Veritabanı:** SQLite (MVP) → gerekirse ileride PostgreSQL
- **Dosya/Belge:** S3 uyumlu obje depolama (lokal ortamda MinIO)
- **İş kuyruğu:** Celery/RQ (import, rapor üretimi, sync)

### 3.1.1 Programlama dili kararı (Net öneri)
- **Öneri:** Backend tarafında **Python ile devam edin**.
- Gerekçe:
  1. Mevcut ekip/alan bilgisi Python odaklıysa teslim hızı ciddi artar.
  2. Kural motoru, veri işleme, import/raporlama akışları Python’da hızlı geliştirilir.
  3. FastAPI + Pydantic ile tipli ve sürdürülebilir API katmanı kurulabilir.
- Ne zaman alternatif düşünülmeli?
  - Ekipte güçlü TypeScript/Java uzmanlığı olup Python tecrübesi düşükse.
  - Çok yüksek eşzamanlılık + ultra düşük gecikme hedefi varsa (Go değerlendirilebilir).

Kısa karar:
- **Backend: Python/FastAPI**
- **Frontend: TypeScript (React/Next.js)**
- **Ağır batch/analitik işler: Python worker**

### 3.2 Katmanlar
1. **Domain Layer** — iş kuralları, policy, hesap motorları
2. **Application Layer** — use-case’ler (komut/sorgu)
3. **Infrastructure Layer** — DB, dosya, dış servis adaptörleri
4. **Interface Layer** — REST API + UI

### 3.3 Mimari tercih
- Modül bazlı monolith ile başlanmalı (mikroservisle başlamayın).
- Her modül kendi bounded context’i ile tasarlanmalı:
  - personel
  - izin
  - fhsz
  - sağlık
  - dozimetre
  - nöbet
  - doküman

---

## 4) Yeni Veri Modeli (Öneri)

## 4.1 Çekirdek tablolar
- `employees` (master)
- `employee_status_history`
- `departments`, `titles`

## 4.2 İzin
- `leave_requests` (talep/olay)
- `leave_balances` (hesaplanan özet)
- `leave_policies` (yıllık, şua, özel izin kuralları)

## 4.3 FHSZ
- `fhsz_entries` (dönem satırları)
- `fhsz_summaries` (kişi/yıl özetleri)

## 4.4 Sağlık
- `health_visits`
- `health_visit_items` (branş bazlı sonuçlar)
- `health_followups`

## 4.5 Dozimetre
- `dosimeter_reports`
- `dosimeter_readings`
- `dosimeter_alerts`

## 4.6 Nöbet
- `shift_templates`
- `shift_constraints`
- `shift_plans`
- `shift_assignments`

## 4.7 Belge
- `documents`
- `document_links` (entity_type + entity_id)
- `document_versions`

---

## 5) İş Kuralı Motoru (Önemli)

Ayrı bir `policy_engine` modülü tasarlanmalı.

Örnek policy grupları:
- İzin limiti/uygunluk
- Pasifleşme kuralları
- Şua/FHSZ hesap kuralları
- Dozimetre eşik/uyarı kuralları
- Nöbet kısıtları (ardışık gün, izin çakışması, saat limiti)

Avantaj:
- Kural değişince UI veya repository kodu değil, policy değişir.

---

## 6) API Tasarımı (Örnek)

- `POST /employees`
- `GET /employees/{id}`
- `POST /leaves`
- `POST /fhsz/periods/{year}/{period}/entries`
- `POST /health/visits`
- `POST /dosimeter/import`
- `POST /shifts/plan/generate`
- `POST /documents/upload`

Not:
- Tüm write endpoint’lerinde idempotency key desteği önerilir.

---

## 7) Güvenlik ve Yetkilendirme

- RBAC + action-level permission
- JWT + refresh token
- Kişisel veri alanlarında maskeleme
- Tüm kritik işlemler için audit log
- Belge erişiminde imzalı URL yaklaşımı

---

## 8) Geliştirme Planı (Önerilen Takvim)

### Faz A — Keşif ve Tasarım (2 hafta)
- Domain sözlüğü
- ERD
- API sözleşmesi
- Yetki matrisi

### Faz B — Çekirdek Modüller (4 hafta)
- Personel, izin, belge
- Auth + RBAC
- Audit altyapısı

### Faz C — Operasyon Modülleri (4 hafta)
- FHSZ
- Sağlık
- Dozimetre
- Nöbet temel planlama

### Faz D — Stabilizasyon (2 hafta)
- Entegrasyon testleri
- Performans testleri
- Kullanıcı kabul testleri
- Eğitim + devreye alma

Toplam: yaklaşık **12 hafta** (ekip 4–6 kişi varsayımı).

---

## 9) Ekip Önerisi

- 1 Product Owner
- 1 Tech Lead / Architect
- 2 Backend Developer
- 1 Frontend Developer
- 1 QA/Test Engineer
- Part-time DevOps desteği

---

## 10) Başarı Kriterleri (KPI)

- Personel işlem süresi %40 kısalma
- Manuel Excel bağımlılığında %70 azalma
- Dozimetre rapor hata oranında %60 düşüş
- Nöbet planlama süresinde %50 azalma
- Kritik işlem audit kapsaması %100

---

## 11) “Bugün başlasak” ilk 5 teknik adım

1. Domain sözlüğünü ve ortak terimleri kilitleyin.
2. ERD + API kontratını versionlayın.
3. `personel + izin + belge` için ilk çalışma dikey dilimini çıkarın.
4. Otomatik test pipeline’ını (CI) zorunlu hale getirin.
5. Pilot birimde canlıya alıp geri bildirimle iterasyon yapın.

---

## Sonuç

Bu revize öneri, geçmiş koddan bağımsız şekilde yeni bir programı **modüler, denetlenebilir ve sürdürülebilir** biçimde kurmayı hedefler.
En kritik karar: önce sağlam domain + policy çekirdeği, sonra ekranlar.

# Sprint-1 Teknik Backlog (Epic / Story / Task / Acceptance Criteria)

Kapsam: Greenfield Personel Operasyon Platformu için ilk sprintte (2 hafta) çalışan bir "ince dikey dilim" çıkarmak.

Hedef dikey dilim:
- Auth + RBAC temel iskeleti
- Personel master kayıtları
- İzin talep + bakiye hesap çekirdeği
- Belge yükleme altyapısının ilk versiyonu
- CI + test + gözlemlenebilirlik temeli

---

## EPIC-1 — Platform Foundation (Auth, RBAC, Observability, CI)

### Story 1.1 — Proje iskeletinin kurulması
**Task 1.1.1** Monorepo/modüler yapı oluştur (`apps/api`, `apps/web`, `packages/domain`, `infra`).  
**Task 1.1.2** Ortak lint/format kuralları (ruff/black + eslint/prettier) ekle.  
**Task 1.1.3** Ortam değişkeni yönetimi (`.env.example`) ve config katmanı oluştur.

**Acceptance Criteria**
- Repo tek komutla ayağa kalkabilmeli (`docker compose up` veya eşdeğeri).
- API ve UI başlangıç şablonları health endpoint ile çalışmalı.
- Lint/format komutları CI’da zorunlu olmalı.

---

### Story 1.2 — Kimlik doğrulama ve yetkilendirme (MVP)
**Task 1.2.1** `users`, `roles`, `permissions`, `user_roles` şemasını ekle.  
**Task 1.2.2** JWT access + refresh token akışını implement et.  
**Task 1.2.3** Endpoint bazlı RBAC middleware yaz.  
**Task 1.2.4** Seed script ile `admin` rolü ve temel izinleri yükle.

**Acceptance Criteria**
- Login sonrası access/refresh token dönebilmeli.
- Yetkisiz kullanıcı `403` almalı.
- Admin rolü ile personel endpoint’leri erişilebilir olmalı.
- En az 10 auth/RBAC unit testi geçmeli.

---

### Story 1.3 — Audit ve gözlemlenebilirlik temeli
**Task 1.3.1** `audit_logs` tablosu oluştur (actor, action, entity, old/new snapshot, timestamp).  
**Task 1.3.2** Kritik write işlemlerinde audit event üret.  
**Task 1.3.3** Structured logging ve request correlation id ekle.  
**Task 1.3.4** Basit metrics endpoint (request count/latency) aç.

**Acceptance Criteria**
- Personel ve izin write işlemleri audit log üretmeli.
- Her API isteğinde correlation id loglanmalı.
- `/metrics` veya eşdeğer endpoint çalışmalı.

---

## EPIC-2 — Personel Master Domain (Core CRUD + Status History)

### Story 2.1 — Personel veri modeli ve migration
**Task 2.1.1** `employees` tablosu (UUID PK, national_id unique, ad/soyad, birim, unvan, durum).  
**Task 2.1.2** `employee_status_history` tablosu (aktif/pasif/ayrıldı geçişleri).  
**Task 2.1.3** DB migration + rollback scriptlerini yaz.

**Acceptance Criteria**
- `employees` için create/read/update çalışmalı.
- Durum değiştiğinde history satırı otomatik oluşmalı.
- Migration ileri/geri sorunsuz çalışmalı.

---

### Story 2.2 — Personel API (v1)
**Task 2.2.1** `POST /employees`  
**Task 2.2.2** `GET /employees/{id}`  
**Task 2.2.3** `GET /employees?search=&department=&status=`  
**Task 2.2.4** `PATCH /employees/{id}`

**Acceptance Criteria**
- National ID format doğrulaması zorunlu olmalı.
- Aynı national_id ile duplicate kayıt engellenmeli (`409`).
- Listeleme endpoint’i pagination desteklemeli.
- OpenAPI dokümantasyonu otomatik üretilmeli.

---

### Story 2.3 — Personel UI (minimum ekran)
**Task 2.3.1** Personel liste ekranı (arama + filtre).  
**Task 2.3.2** Personel detay ekranı.  
**Task 2.3.3** Personel ekleme/düzenleme formu.

**Acceptance Criteria**
- UI’den yeni personel kaydı oluşturulabilmeli.
- Validasyon hataları kullanıcıya alan bazlı gösterilmeli.
- Başarılı işlem sonrası liste anında güncellenmeli.

---

## EPIC-3 — İzin Domain (Leave Request + Balance Projection)

### Story 3.1 — İzin temel veri modeli
**Task 3.1.1** `leave_requests` tablosu (employee_id, leave_type, date_range, days, status).  
**Task 3.1.2** `leave_balances` tablosu (annual_entitled, used, remaining, sua_* alanları).  
**Task 3.1.3** `leave_policies` tablosu (kural parametreleri).

**Acceptance Criteria**
- Leave request oluşturulduğunda balance projection güncellenmeli.
- Policy tanımı değiştiğinde hesaplama servisi tekrar çalıştırılabilmeli.
- Tarih aralığı çakışmaları engellenmeli.

---

### Story 3.2 — Policy engine (izin kuralları v1)
**Task 3.2.1** Yıllık izin hakediş policy’si.  
**Task 3.2.2** Şua izin policy’si.  
**Task 3.2.3** Ücretsiz/aylıksız izin için pasifleşme policy’si.  
**Task 3.2.4** Policy test fixture seti yaz.

**Acceptance Criteria**
- Policy sonuçları deterministic olmalı (aynı girdi = aynı çıktı).
- En az 20 policy unit testi yeşil olmalı.
- Hata mesajları kullanıcıya anlaşılır dönmeli.

---

### Story 3.3 — İzin API + UI (MVP)
**Task 3.3.1** `POST /leaves` (talep oluştur).  
**Task 3.3.2** `GET /employees/{id}/leave-balance`  
**Task 3.3.3** UI’de izin talep formu + bakiye kartı.

**Acceptance Criteria**
- Talep sonrası bakiye kartı doğru güncellenmeli.
- Limit aşımı durumunda işlem reddedilmeli ve sebep gösterilmeli.
- İzin işlemleri audit log üretmeli.

---

## EPIC-4 — Belge Yönetimi (MVP)

### Story 4.1 — Belge storage abstraction
**Task 4.1.1** `documents` tablosu (id, file_name, mime, size, checksum, storage_key).  
**Task 4.1.2** `document_links` tablosu (entity_type, entity_id, document_id).  
**Task 4.1.3** Local/S3 adapter arayüzü (`StorageProvider`) yaz.

**Acceptance Criteria**
- Aynı dosya checksum ile tekrar yüklenirse duplicate uyarısı verilmeli.
- Belge bir personele bağlanabilmeli.
- Dosya metadata + link bilgisi DB’de tutarlı yazılmalı.

---

### Story 4.2 — Belge API + temel UI
**Task 4.2.1** `POST /documents/upload`  
**Task 4.2.2** `GET /employees/{id}/documents`  
**Task 4.2.3** Personel detay ekranında belge sekmesi ekle.

**Acceptance Criteria**
- PDF/JPG/DOCX yükleme desteklenmeli.
- Max dosya boyutu limiti uygulanmalı.
- Yetkisiz kullanıcı belge yükleyememeli.

---

## EPIC-5 — Quality Gates (Test, CI/CD, Definition of Done)

### Story 5.1 — Test altyapısı ve kapsama hedefi
**Task 5.1.1** Unit/integration test klasör yapısını oluştur.  
**Task 5.1.2** Test DB fixture ve seed verileri hazırla.  
**Task 5.1.3** Minimum coverage gate (%70) ekle.

**Acceptance Criteria**
- PR açıldığında test pipeline otomatik çalışmalı.
- Coverage %70 altına düşerse pipeline fail olmalı.
- Kritik domain policy testleri zorunlu olmalı.

---

### Story 5.2 — CI/CD akışı
**Task 5.2.1** CI aşamaları: lint → test → build → security scan.  
**Task 5.2.2** Semantik versiyonlama ve release not otomasyonu.  
**Task 5.2.3** Staging deploy pipeline (manual approval).

**Acceptance Criteria**
- Ana branch’e merge sadece yeşil pipeline ile mümkün olmalı.
- Build artifact üretimi izlenebilir olmalı.
- Güvenlik taramasında high severity açık kalmamalı.

---

## Sprint-1 Definition of Done (Genel)

Bir story “done” sayılabilmesi için:
1. Kod + test + dokümantasyon tamam.
2. Acceptance criteria tamamen sağlanmış.
3. CI pipeline yeşil.
4. Güvenlik/lint hatası yok.
5. Ürün sahibi demo onayı alınmış.

---

## Sprint-1 Çıktı Beklentisi (Demo Senaryosu)

Sprint sonunda canlı demoda şunlar gösterilmeli:
1. Admin login + yetki kontrollü erişim.
2. Yeni personel kaydı açma ve güncelleme.
3. Personel için izin talebi oluşturma ve bakiye etkisini görme.
4. Personele belge yükleme ve listede görüntüleme.
5. Tüm write işlemlerin audit kaydının düşmesi.

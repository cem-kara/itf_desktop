# Sırayla Başlangıç Planı (Adım Adım)

Bu doküman “sırayla başlayalım” talebi için en düşük riskli uygulama sırasını verir.

## Adım 1 — Karar Kilitleme (Gün 1)
1. Backend dili: **Python/FastAPI**
2. Frontend: **TypeScript + React/Next.js**
3. Veritabanı: **SQLite** (ilk faz için)
4. Depolama: **S3/MinIO**
5. Sprint süresi: **2 hafta**

**Çıktı:** 1 sayfalık teknik karar notu (ADR-001).

---

## Adım 2 — Domain Sözlüğü (Gün 1-2)
Tanımlar netleşmeden kod yazılmayacak.
- Employee, LeaveRequest, LeaveBalance
- FHSZEntry, HealthVisit, DosimeterReading
- ShiftPlan, Document

**Çıktı:** `domain-glossary.md`

---

## Adım 3 — ERD + API Kontratı (Gün 2-3)
Önce veri modeli, sonra endpoint.
- ERD v1
- OpenAPI v1
- Hata kodları standardı

**Çıktı:** `erd-v1.png` + `openapi.yaml`

---

## Adım 4 — Platform İskeleti (Gün 3-4)
- Repo yapısı (`apps/api`, `apps/web`, `packages/domain`)
- Lint/format
- CI (lint + test)
- Env/config altyapısı

**Çıktı:** Çalışan boş sistem + yeşil pipeline.

---

## Adım 5 — Auth + RBAC (Gün 4-6)
- Login
- Access/refresh token
- Rol bazlı endpoint koruması
- Admin seed

**Çıktı:** Yetki kontrollü giriş sistemi.

---

## Adım 6 — Personel Dikey Dilimi (Gün 6-8)
- `employees` + `employee_status_history`
- Personel CRUD API
- UI liste + detay + ekleme formu

**Çıktı:** Uçtan uca personel kaydı yönetimi.

---

## Adım 7 — İzin Dikey Dilimi (Gün 8-10)
- `leave_requests` + `leave_balances`
- Policy engine v1 (yıllık + şua temel)
- İzin talep formu + bakiye ekranı

**Çıktı:** Talep → kural kontrol → bakiye güncelleme akışı.

---

## Adım 8 — Belge Yükleme MVP (Gün 10-11)
- `documents` + `document_links`
- Upload endpoint
- Personel belge sekmesi

**Çıktı:** Personele dosya bağlama.

---

## Adım 9 — Demo ve Kapanış (Gün 12)
Canlı senaryo:
1. Admin login
2. Personel ekleme
3. İzin talebi + bakiye değişimi
4. Belge yükleme
5. Audit kaydı gösterimi

**Çıktı:** Sprint-1 demo onayı.

---

## Bu hafta hemen başlayalım (ilk 3 iş)
1. ADR-001: teknoloji kararlarını imzala.
2. Domain sözlüğünü kilitle.
3. ERD + OpenAPI taslağını çıkar.

Bu 3 adım tamamlanmadan geliştirme koduna geçmeyin.

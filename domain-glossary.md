# Domain Glossary (Adım 2)

Amaç: Tüm ekip için ortak terim sözlüğünü kilitlemek ve aynı kavrama farklı isim verilmesini önlemek.

## 1) Çekirdek Varlıklar

### Employee (Personel)
- Sistem içindeki çalışan kişiyi temsil eder.
- Teknik kimlik: `employee_id` (UUID)
- Kurumsal kimlik: `national_id` (TC kimlik)
- Durum: `active | passive | left`

### Department (Birim)
- Personelin çalıştığı organizasyonel birim.
- Örnek: MR, BT, Radyoterapi, Nükleer Tıp.

### Title (Unvan)
- Personelin kurumsal rol/unvan bilgisidir.
- Örnek: Tekniker, Uzman, Sorumlu Tekniker.

### EmployeeStatusHistory
- Personelin durum değişim geçmişi.
- Her geçiş bir kayıt olarak saklanır.

---

## 2) İzin Domaini

### LeaveRequest (İzin Talebi)
- Personelin belirli tarih aralığı için izin talebi.
- Alanlar: `leave_type`, `start_date`, `end_date`, `days`, `status`.

### LeaveType (İzin Türü)
- İzin kategorisi.
- Örnek: `annual`, `sua`, `unpaid`, `medical`, `administrative`.

### LeaveBalance (İzin Bakiyesi)
- Personelin izin hak/harcanan/kalan özetidir.
- Projection tablosudur; doğrudan serbest elle düzenlenmez.

### LeavePolicy
- İzin kurallarını tanımlayan parametre seti.
- Örnek: yıllık hakediş, şua limitleri, ücretsiz izin pasifleşme koşulu.

---

## 3) FHSZ Domaini

### FHSZEntry
- Dönem bazlı FHSZ puantaj satırı.
- Ana alanlar: `year`, `period`, `worked_hours`, `leave_days`.

### FHSZSummary
- Kişi/yıl bazında hesaplanmış FHSZ özeti.
- Projection amaçlı kullanılır.

### Period
- Zaman dilimi kimliği.
- Örnek: yıl içindeki 1..N dönem.

---

## 4) Sağlık Domaini

### HealthVisit
- Personelin bir sağlık kontrol ziyareti.
- Alanlar: `visit_date`, `result`, `next_control_date`.

### HealthVisitItem
- Tek bir ziyarette branş bazlı alt sonuç.
- Örnek branş: dermatoloji, dahiliye, göz.

### HealthFollowUp
- Sonraki takip/hatırlatma kaydı.

---

## 5) Dozimetre Domaini

### DosimeterReport
- Kurum dışından gelen dozimetre rapor üst kaydı.
- Kaynak dosya bilgisi ve periyot metadata içerir.

### DosimeterReading
- Tek personel için tek periyottaki ölçüm satırı.
- Alanlar: `hp10`, `hp007`, `period`, `year`.

### DosimeterAlert
- Eşik aşımlarından üretilen uyarı kaydı.
- Örnek seviye: `info | warning | critical`.

---

## 6) Nöbet Domaini

### ShiftTemplate
- Vardiya tipinin şablonu (başlangıç-bitiş, min personel).

### ShiftConstraint
- Atama kısıt kuralı.
- Örnek: ardışık gün yasağı, izin günü çakışması, aylık saat limiti.

### ShiftPlan
- Belirli dönem/birim için plan üst kaydı.

### ShiftAssignment
- Plan içinde personel-vardiya-tarih ataması.

---

## 7) Belge Domaini

### Document
- Sisteme yüklenen dosyanın metadata kaydı.
- Alanlar: `document_id`, `file_name`, `mime_type`, `checksum`, `storage_key`.

### DocumentLink
- Belgenin hangi varlığa bağlı olduğunu gösterir.
- Alanlar: `entity_type`, `entity_id`, `document_id`.

### DocumentVersion
- Aynı belgenin sürüm geçmişi.

---

## 8) Ortak Terimler

### AuditLog
- Kritik işlemlerin değişmez kayıt izi.
- Kim yaptı, neyi ne zaman değiştirdi sorusunu cevaplar.

### Policy Engine
- İş kurallarının merkezi çalıştırma katmanı.
- Kurallar UI veya repository içinde yazılmaz.

### Projection
- Event/işlem kayıtlarından türetilen raporlama/özet tablosu.

### Idempotency Key
- Aynı isteğin tekrarında çift yazmayı önleyen benzersiz anahtar.

### Source of Truth
- Bir bilginin resmi ve tek doğru kaynağı.

---

## 9) İsimlendirme Kuralları (Zorunlu)

1. Teknik kimlik alanı adı: `employee_id` (her yerde aynı).
2. TC alanı adı: `national_id` (eski `KimlikNo/PersonelID` varyasyonları yok).
3. Tarih alanları ISO format (`YYYY-MM-DD`) ile tutulur.
4. Enum alanları küçük harf snake_case.
5. API alan adları İngilizce, UI etiketleri Türkçe olabilir.

---

## 10) Bu Sözlüğün Kullanımı

- Yeni tablo/endpoint açılmadan önce bu sözlükte karşılığı kontrol edilir.
- Yeni terim gerekiyorsa önce sözlüğe eklenir, sonra implementasyona geçilir.
- Çelişen terimler ADR ile çözülür.

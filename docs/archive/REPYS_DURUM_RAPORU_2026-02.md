# REPYS — Nihai Durum Raporu (Revize) ve Detaylı P1–P4 Uygulama Planı

**Tarih:** 2026-02-24  
**Sürüm Referansı:** REPYS v3.0.0  
**Bu revizyonda odak:** Son durum raporunun yeniden düzenlenmesi ve özellikle **UI dosyalarını parçalama planının tekrar gözden geçirilmesi**.

**Birleştirilen kaynaklar:**
- `docs/REPYS_DURUM_RAPORU_2026-02.md` (önceki rapor)
- `docs/cihaz_todo.md`
- `docs/PERSONEL_STATUS.md`
- `docs/tema_todo.md`

---

## 1) Yönetici Özeti

REPYS işlevsel kapsam olarak güçlü; personel ve cihaz modüllerinde aktif kullanılan akışlar mevcut. Ancak sürdürülebilirlik açısından kritik darboğazlar şunlar:
1. Test otomasyonu eksikliği,
2. Sync/Offline davranış sözleşmesinin net olmaması,
3. Büyük UI dosyalarında sorumluluk yığılması.

Bu nedenle yol haritası **P1 → P4** olarak korunmuş, ama bu revizyonda özellikle **P3 (UI parçalama)** kısmı dosya bazlı, adım bazlı ve sprint uygulanabilirliğine göre yeniden detaylandırılmıştır.

---

## 2) Birleşik Son Durum (As-Is)

### 2.1 Modül olgunluk değerlendirmesi

| Alan | Seviye | Durum Özeti |
|---|---|---|
| Personel | Yüksek | Ana işlevler çalışır, validasyon checklist kapanışı gerekli |
| Cihaz | Orta-Yüksek | Arıza/Bakım/Kalibrasyon aktif, CRUD genişletme eksikleri var |
| Tema | Orta | Tekilleştirme ilerlemiş, runtime theme switch eksik |
| Test/QA | Düşük | Otomasyon test seti yok denecek kadar az |
| Operasyon | Orta | Migration/backup var, runbook standardı eksik |

### 2.2 Dokümanlardan konsolide kritik açıklar

#### Personel tarafı
- Şema/ilişkisel tablo doğrulaması tam kapatılmalı.
- 30+ gün izin => Pasif statü kuralı uçtan uca doğrulanmalı.
- Drive kesintisinde upload davranışı açık sözleşmeye bağlanmalı.

#### Cihaz tarafı
- Düzenle/Sil işlemleri tamamlanmalı.
- Dosya seçici + dosya önizleme + arama/filtreleme eklenmeli.
- Metin tabanlı dosya yolundan gerçek dosya akışına geçiş planı netleşmeli.

#### Tema tarafı
- Runtime light/dark geçişi tamamlanmalı.
- Tema seçiminin ayarlarda persist edilmesi gerekiyor.

---

## 3) Önceliklendirilmiş Riskler

### R1 — Test güvence eksikliği (En kritik)
**Neden kritik?** P2/P3 değişikliklerinde regress riski çok yüksek.  
**Etkisi:** Üretimde sessiz kırılma ve yüksek bakım maliyeti.

### R2 — Sync/Offline sözleşme boşluğu
**Neden kritik?** Drive/sheet erişim sorunlarında net davranış yoksa veri kaybı algısı oluşur.  
**Etkisi:** Operasyon güveni zedelenir.

### R3 — UI dosyalarının aşırı büyümesi
**Neden kritik?** Kod anlaşılabilirliği ve değişim güvenliği düşer.  
**Etkisi:** Yeni geliştirme hızı azalır, hata oranı artar.

### R4 — Runbook eksikliği
**Neden kritik?** Sorun anında bireysel bilgiye bağımlı operasyon oluşur.  
**Etkisi:** MTTR artışı.

---

## 4) P1–P4 Planı (Ne / Neden / Nasıl)

## P1 — Test ve Validasyon Temeli (0–2 hafta)

### Ne yapılacak?
1. Repository, migration ve kritik iş kuralı testleri yazılacak.
2. Personel/Cihaz için minimum smoke test seti oluşturulacak.
3. Validasyon checklist’leri test case’e dönüştürülecek.

### Neden yapılacak?
- P2–P4 çalışmalarının güvenli ilerlemesi için.

### Nasıl yapılacak?
- `tests/database`, `tests/core`, `tests/ui_smoke` dizinleri açılacak.
- Öncelikli test dosyaları:
  - `test_base_repository.py`
  - `test_migrations.py`
  - `test_personel_pasif_rule.py`
  - `test_offline_upload_contract.py`
- CI’de tek komut: `pytest -q`

### Kabul kriteri
- 30+ test,
- Kritik kurallarda senaryo bazlı doğrulama,
- Testlerin CI’da kararlı çalışması.

---

## P2 — Sync Sözleşmesi + Operasyon Runbook (2–4 hafta)

### Ne yapılacak?
1. Sync ve upload davranış sözleşmesi yazılacak.
2. Hata sınıfları ve kullanıcı mesaj standardı çıkarılacak.
3. Backup/rollback/recovery runbook tamamlanacak.

### Neden yapılacak?
- Kesinti ve hata durumlarında öngörülebilir işletim için.

### Nasıl yapılacak?
- “Cloud down”, “partial sync fail”, “token expired” akışları için karar tablosu hazırlanacak.
- Teknik hata → kullanıcı mesajı eşleme tablosu oluşturulacak.
- Operasyon komutları tek dokümanda standartlaştırılacak.

### Kabul kriteri
- Runbook onaylı,
- En az 1 kesinti simülasyonu raporlanmış,
- Offline/online davranışı dokümante ve testlenmiş.

---

## P3 — UI Dosyalarını Parçalama (4–8 hafta)  ✅ Bu revizyonda derinleştirildi

### 4.3.1 Parçalama adayları (en güncel tekrar değerlendirme)

Aşağıdaki liste gerçek dosya büyüklüğü + sorumluluk karışımı (UI + iş kuralı + veri erişimi) kriteriyle sıralanmıştır:

| Öncelik | Dosya | Yaklaşık Boyut | Ana Sorun |
|---|---|---:|---|
| P3-A1 | `ui/pages/cihaz/ariza_kayit.py` | 1242 | CRUD + panel koordinasyonu + state yönetimi tek dosyada |
| P3-A1 | `ui/pages/personel/izin_takip.py` | 1107 | İş kuralı + form + tablo + statü akışı birlikte |
| P3-A1 | `ui/pages/personel/personel_listesi.py` | 1105 | Listeleme, filtre, lazy load, avatar/cache aynı katmanda |
| P3-A2 | `ui/pages/cihaz/bakim_kalibrasyon_form.py` | 1082 | Bakım/kalibrasyon ortak davranış tekrarları |
| P3-A2 | `ui/pages/personel/saglik_takip.py` | 953 | timeline, dönüşüm ve state tek sınıfta |
| P3-A2 | `ui/pages/personel/fhsz_yonetim.py` | 923 | hesaplama + UI etkileşimi iç içe |
| P3-B1 | `ui/pages/personel/personel_ekle.py` | 899 | form validasyon + save + upload akışları tek yerde |
| P3-B1 | `ui/main_window.py` | 757 | shell + routing + sync + status sorumlulukları birleşik |
| P3-B2 | `ui/pages/cihaz/cihaz_listesi.py` | 697 | listeleme + filtre + aksiyonlar ayrışmamış |

> Not: `ui/pages/cihaz/components/uts_parser.py` büyük olmasına rağmen doğrudan “sayfa UI parçalama” kapsamında değil; ayrı bir “parser/service decomposition” işi olarak P3-B sonuna eklenmelidir.

### 4.3.2 Dosya bazlı parçalama yöntemi (tek tek)

#### 1) `ui/pages/cihaz/ariza_kayit.py`
- **Yapılacak:**
  - `ArizaKayitView`
  - `ArizaKayitPresenter`
  - `ArizaCommandService`
  - `ArizaState`
- **Neden:** En yüksek karmaşıklık ve hata potansiyeli.
- **Nasıl:** Önce command işlemlerini service’e çıkar; sonra selection/detail state’i `ArizaState`’e taşı; en son presenter ekle.

#### 2) `ui/pages/personel/izin_takip.py`
- **Yapılacak:**
  - `IzinTakipView`
  - `IzinTakipPresenter`
  - `IzinWorkflowService`
  - `IzinValidationService`
  - `IzinTakipState`
- **Neden:** Kritik business-rule (pasif statü) UI ile karışık.
- **Nasıl:** `_should_set_pasif()` benzeri kuralları servis katmanına taşı; UI sadece event üretici olsun.

#### 3) `ui/pages/personel/personel_listesi.py`
- **Yapılacak:**
  - `PersonelListView`
  - `PersonelListPresenter`
  - `PersonelQueryService`
  - `AvatarService`
  - `PersonelListState`
- **Neden:** Lazy-load, filtre, cache, render aynı sınıfta olduğu için değişim riski yüksek.
- **Nasıl:** Veri çekme ve filtreleme `PersonelQueryService`’e, avatar işlerini `AvatarService`’e ayır.

#### 4) `ui/pages/cihaz/bakim_kalibrasyon_form.py`
- **Yapılacak:**
  - `BaseMaintenanceCalibrationForm`
  - `BakimFormPresenter`
  - `KalibrasyonFormPresenter`
  - `MaintenanceValidationService`
- **Neden:** Benzer iki form akışı tekrarlı.
- **Nasıl:** Ortak alan/validation base sınıfa; farklı alanları adapter/presenter ile ayır.

#### 5) `ui/pages/personel/saglik_takip.py`
- **Yapılacak:**
  - `SaglikTakipView`
  - `SaglikTakipPresenter`
  - `SaglikRecordService`
  - `SaglikTimelineAdapter`
  - `SaglikTakipState`
- **Neden:** UI ve tarih/dönüşüm mantığı iç içe.
- **Nasıl:** Timeline hazırlama ve veri normalize etme servis/adaptöre taşınır.

#### 6) `ui/pages/personel/fhsz_yonetim.py`
- **Yapılacak:**
  - `FhszYonetimView`
  - `FhszPresenter`
  - `FhszCalculationService`
  - `FhszState`
- **Neden:** Hesaplama kuralları UI’dan bağımsız testlenebilir olmalı.
- **Nasıl:** Tüm hesap fonksiyonlarını servis modülüne taşı, presenter sonucu viewmodel’e dönüştürsün.

#### 7) `ui/pages/personel/personel_ekle.py`
- **Yapılacak:**
  - `PersonelEkleView`
  - `PersonelEklePresenter`
  - `PersonelValidationService`
  - `PersonelSaveService`
  - `PersonelFileUploadService`
- **Neden:** Form doğrulama ve kayıt işlemi tek sınıfta yoğun.
- **Nasıl:** Önce validation ayır, sonra save/upload servislerini ayır.

#### 8) `ui/main_window.py`
- **Yapılacak:**
  - `MainWindowShell`
  - `PageRouter`
  - `SyncController`
  - `StatusBarController`
- **Neden:** Uygulama orkestrasyonu tek dosyada.
- **Nasıl:** Routing/sync/status davranışları controller’lara taşınır; main window sadece container olur.

#### 9) `ui/pages/cihaz/cihaz_listesi.py`
- **Yapılacak:**
  - `CihazListView`
  - `CihazListPresenter`
  - `CihazQueryService`
  - `CihazListState`
- **Neden:** Listeleme + filtreleme + aksiyonlar tek sınıfta.
- **Nasıl:** Query/filter işlemlerini servis katmanına al, presenter ile UI’dan ayır.

### 4.3.3 Sprint bazlı uygulama sırası

- **Sprint P3-1:** `ariza_kayit.py`, `izin_takip.py`
- **Sprint P3-2:** `personel_listesi.py`, `bakim_kalibrasyon_form.py`
- **Sprint P3-3:** `saglik_takip.py`, `personel_ekle.py`, `main_window.py`
- **Sprint P3-4:** `fhsz_yonetim.py`, `cihaz_listesi.py`, ardından `uts_parser.py` teknik ayrıştırma

### 4.3.4 P3 kabul kriteri

1. Hedef dosyalar 500 satır altına veya makul modüler dağılıma indirildi.
2. UI katmanında doğrudan repository erişimi belirgin biçimde azaltıldı.
3. Her parçalanan dosya için en az 1 smoke + 1 unit test eklendi.
4. Kritik akışlar (Personel Liste, İzin Takip, Arıza Kayıt) regresyonsuz geçti.

### 4.3.5 Ek Gözden Geçirme: `bakim_form.py` ve `kalibrasyon_form.py`

Bu revizyonda özellikle atlanan iki dosya ayrıca incelendi:
- `ui/pages/cihaz/bakim_form.py` (~750 satır)
- `ui/pages/cihaz/kalibrasyon_form.py` (~767 satır)

#### Neden bu dosyalar da P3 kapsamına alınmalı?
1. Her iki dosyada da benzer yapı bulunuyor: KPI bar + filtre paneli + tablo modeli + detay/form yönetimi.
2. Renk sabitleri, tablo modeli ve filtre/aksiyon akışlarında tekrar eden kalıplar var.
3. `bakim_kalibrasyon_form.py` ile birlikte ele alınmadığında bakım maliyeti parçalı kalıyor.

#### Bu dosyalar için önerilen parçalama

**A) Ortak çekirdek oluştur (cihaz/forms/common):**
- `base_record_table_model.py` (ortak QAbstractTableModel davranışları)
- `kpi_bar_widget.py` (kart üretimi + güncelleme)
- `filter_panel_widget.py` (cihaz/durum/arama filtreleri)
- `record_detail_container.py` (sağ panel detay + form alanı)

**B) Bakım özel modülü (cihaz/forms/bakim):**
- `bakim_view.py`
- `bakim_presenter.py`
- `bakim_service.py`
- `bakim_state.py`

**C) Kalibrasyon özel modülü (cihaz/forms/kalibrasyon):**
- `kalibrasyon_view.py`
- `kalibrasyon_presenter.py`
- `kalibrasyon_service.py`
- `kalibrasyon_state.py`

#### Klasör yapısı önerisi (güncellenmiş)

```text
ui/pages/cihaz/
  forms/
    common/
      base_record_table_model.py
      kpi_bar_widget.py
      filter_panel_widget.py
      record_detail_container.py
    bakim/
      bakim_view.py
      bakim_presenter.py
      bakim_service.py
      bakim_state.py
    kalibrasyon/
      kalibrasyon_view.py
      kalibrasyon_presenter.py
      kalibrasyon_service.py
      kalibrasyon_state.py
```

#### Geçiş sırası (öneri)
1. Önce `bakim_form.py` ve `kalibrasyon_form.py` içindeki **ortak widget/model** parçalarını `forms/common` altına çıkar.
2. Sonra her dosyada presenter + service + state ayrımını yap.
3. Son adımda `bakim_kalibrasyon_form.py` ile çakışan mantıkları tek noktada birleştir.

#### Bu ek bölümün kabul kriteri
- `bakim_form.py` ve `kalibrasyon_form.py` içinde tekrar eden kod blokları belirgin biçimde azalır.
- Ortak bileşenler `forms/common` altında yeniden kullanılabilir hale gelir.
- Bakım/Kalibrasyon formlarındaki regress kontrol listesi (listeleme, filtreleme, kayıt ekleme, detay gösterimi) sorunsuz geçer.

---

## P4 — Tema Son Faz ve Ürün Kalitesi (8–10 hafta)

### Ne yapılacak?
1. Runtime light/dark switch.
2. Ayarlarda tema persist.
3. Görsel regress checklist.

### Neden yapılacak?
- Tutarlı kurumsal UX ve düşük görsel borç için.

### Nasıl yapılacak?
- `theme_registry` + `light_theme` + `theme_light_template` entegrasyonu.
- `ThemeManager.set_theme()` ve global refresh.

### Kabul kriteri
- Yeniden açılışta tema korunur,
- Ana ekranlarda görsel regress yok.

---

## 5) Modül Bazlı Net İş Listesi

### Personel
- [ ] Şema checklist kapanışı
- [ ] Pasif statü E2E doğrulama
- [ ] Drive offline upload sözleşmesi

### Cihaz
- [ ] Düzenle/Sil aksiyonları
- [ ] Dosya seçici + önizleme
- [ ] Filtreleme/arama iyileştirmesi

### Tema
- [ ] Runtime tema geçişi
- [ ] Ayarlara yazma/okuma
- [ ] Stil tek kaynak denetimi

---

## 6) Sprint ve Bağımlılık Haritası

1. **Sprint-1:** P1
2. **Sprint-2:** P2
3. **Sprint-3/4/5/6:** P3
4. **Sprint-7:** P4

Bağımlılık:
- P3 başlamadan P1 kabul kriterleri tamamlanmalı.
- P4 başlamadan P3-1 ve P3-2 kapanmış olmalı.

---

## 7) KPI Hedefleri

- Otomasyon test adedi: `0 → 30+`
- Kritik akış regress sayısı: sprint sonunda `0`
- 900+ satır UI dosya sayısı: her sprintte düşüş
- Sync olay çözüm süresi: runbook sonrası ölçülebilir düşüş

---

## 8) Sonuç ve Başlangıç Önerisi

Bu revizyonla rapor, özellikle **UI parçalama** konusunda yeniden kalibre edilmiştir. Uygulanabilir başlangıç:
1. **P1’i hemen başlat** (test + validasyon),
2. P1 kapanır kapanmaz **P3-1 dosyalarına** geç (`ariza_kayit.py`, `izin_takip.py`).

Bu sıra, hem riski düşürür hem de en yüksek bakım maliyetli dosyalardan hızlı kazanım sağlar.

# REPYS — Temizlik Takip Belgesi
> Dosya bazlı rapor (REPYS_dosya_bazli_rapor.html) baz alınmıştır.
> Son güncelleme: 31 Mart 2026
> Her tamamlanan madde `[x]` ile işaretlenir.

---

## ✅ Önceki Oturumda Tamamlananlar (Temizlik Raporu v1)

- [x] Madde 2 — Redefinition (tekrar tanım): 4 dosya düzeltildi
  - [x] `core/services/nobet_service.py` — `birim_ayar_kaydet` 3 kopya → 1
  - [x] `ui/pages/cihaz/ariza_girisi_form.py` — duplicate import kaldırıldı
  - [x] `ui/pages/personel/personel_ekle.py` — duplicate `Icons` import kaldırıldı
  - [x] `database/gsheet_manager.py` — duplicate `import time` kaldırıldı
- [x] Madde 3 — Unreachable code: 3 yer düzeltildi
  - [x] `core/services/dis_alan_import_service.py:84` — ölü blok kaldırıldı
  - [x] `ui/main_window.py:331` — NobetRaporPage unreachable blok kaldırıldı
  - [x] `ui/pages/cihaz/cihaz_listesi.py:163` — `CihazDelegate.paint()` yanlış girintiyle `sizeHint()` içindeydi, class seviyesine çıkarıldı
- [x] Madde 4 — Unused imports: `core/storage/__init__.py` → `__all__` eklendi
- [x] Madde 5 — Unused variables: Tüm dizinler temizlendi (core, admin, personel, cihaz, nobet, rke, fhsz, imports, components, database)

---

## 🔴 ADIM 0 — Güvenlik (ACİL)

> `database/token.json` ve `database/credentials.json` commit geçmişinde açıkta.

- [x] `database/credentials.json` dosyasını yeni token ile yenile veya içini boşalt
- [x] `database/token.json` dosyasını sil / yenile
- [x] `.gitignore`'a ekle:
  ```
  database/token.json
  database/credentials.json
  ```
- [x] `git filter-branch` veya `git-filter-repo` ile geçmiş commit'ten temizle (opsiyonel — private repo ise takip et)

---

## 🔴 ADIM 1 — QMessageBox → hata_yonetici (318 ihlal · 33 dosya)

> Dönüşüm kalıbı:
> ```python
> from core.hata_yonetici import hata_goster, uyari_goster, bilgi_goster, soru_sor
>
> # QMessageBox.critical(self, "Hata", msg)      → hata_goster(self, msg)
> # QMessageBox.warning(self, "Uyarı", msg)      → uyari_goster(self, msg)
> # QMessageBox.information(self, "Bilgi", msg)  → bilgi_goster(self, msg)
> # QMessageBox.question(...)                    → soru_sor(self, msg)
> ```

### Grup A — Kritik (40+ ihlal)
- [x] `ui/admin/settings_page.py` — 40 ihlal
- [x] `ui/admin/nobet_yonetim_page.py` — 28 ihlal
- [x] `ui/admin/backup_page.py` — 24 ihlal

### Grup B — Yüksek (10-20 ihlal)
- [x] `ui/pages/fhsz/dis_alan_import_page.py` — 19 ihlal
- [x] `ui/pages/nobet/nobet_merkez_page.py` — 18 ihlal
- [x] `ui/pages/personel/components/personel_overview_panel.py` — 17 ihlal
- [x] `ui/pages/personel/saglik_takip.py` — 17 ihlal
- [x] `ui/pages/nobet/nobet_plan_page.py` — 17 ihlal
- [x] `ui/admin/users_view.py` — 16 ihlal
- [x] `ui/admin/roles_view.py` — 13 ihlal
- [x] `ui/pages/fhsz/dis_alan_kurulum_page.py` — 11 ihlal
- [x] `ui/pages/personel/components/personel_saglik_panel.py` — 10 ihlal

### Grup C — Orta (5-9 ihlal)
- [x] `ui/pages/personel/dis_personel_fhsz.py` — 9 ihlal
- [x] `ui/pages/fhsz/dis_alan_puantaj_page.py` — 7 ihlal
- [x] `ui/pages/personel/personel_listesi.py` — 7 ihlal
- [x] `ui/pages/personel/isten_ayrilik.py` — 6 ihlal
- [x] `ui/pages/imports/dozimetre_import.py` — 5 ihlal
- [x] `ui/pages/imports/dozimetre_pdf_import_page.py` — 5 ihlal
- [x] `ui/pages/imports/components/base_import_page.py` — 5 ihlal
- [x] `ui/auth/change_password_dialog.py` — 5 ihlal
- [x] `ui/pages/personel/components/hizli_izin_giris.py` — 4 ihlal

### Grup D — Düşük (1-4 ihlal)
- [x] `ui/pages/dokuman/dokuman_listesi.py` — 4 ihlal
- [x] `ui/admin/permissions_view.py` — 3 ihlal
- [x] `ui/admin/log_viewer_page.py` — 3 ihlal
- [x] `ui/admin/yil_sonu_devir_page.py` — 3 ihlal
- [x] `ui/components/rapor_buton.py` — 3 ihlal
- [x] `ui/pages/personel/components/hizli_saglik_giris.py` — 3 ihlal
- [x] `ui/pages/personel/dozimetre_takip.py` — 3 ihlal
- [x] `ui/pages/personel/dozimetre_import.py` — 5 ihlal
- [x] `ui/pages/personel/personel_merkez.py` — 2 ihlal
- [x] `ui/pages/fhsz/dis_alan_katsayi_page.py` — 2 ihlal
- [x] `ui/pages/nobet/nobet_hazirlik_page.py` — 1 ihlal
- [x] `ui/main_window.py` — 3 ihlal

---

## 🔴 ADIM 2 — Tema: STYLES / S.get() ile setStyleSheet (75 ihlal · 9 dosya)

> Dönüşüm kalıbı:
> ```python
> # btn.setStyleSheet(S.get("btn_action"))  →  btn.setProperty("style-role", "action")
> # lbl.setStyleSheet(S.get("form_label"))  →  lbl.setProperty("style-role", "form")
> ```

- [x] `ui/pages/personel/personel_ekle.py` — **36 ihlal** ✅ tamamlandı
- [x] `ui/pages/personel/dis_personel_fhsz.py` — 9 ihlal ✅ tamamlandı
- [x] `ui/pages/dokuman/dokuman_listesi.py` — 8 ihlal ✅ tamamlandı
- [x] `ui/pages/fhsz/dis_alan_import_page.py` — 6 ihlal ✅ tamamlandı
- [x] `ui/pages/fhsz/dis_alan_donem_gecmisi_page.py` — 5 ihlal ✅ tamamlandı
- [x] `ui/pages/imports/dozimetre_import.py` — 3 ihlal ✅ tamamlandı
- [x] `ui/pages/personel/dozimetre_import.py` — 3 ihlal ✅ tamamlandı
- [x] `ui/pages/fhsz/dis_alan_kurulum_page.py` — 2 ihlal ✅ tamamlandı
- [x] `ui/pages/dashboard.py` — 1 ihlal ✅ tamamlandı
- [ ] `ui/styles/components.py` + `ui/styles/__init__.py` — 2 ihlal ⚠️ (altyapı — dokunma)

---

## 🟠 ADIM 3 — Tema: f-string setStyleSheet (23 ihlal · 11 dosya)

> Sadece gerçekten dinamik olmayan renkler için `setProperty` kullanılır.
> Dinamik hesaplanmış `rgba(r,g,b,a)` formatı → `{{ }}` ile escape edilerek kalabilir.

- [ ] `ui/pages/personel/dozimetre_import.py` — 4 ihlal
- [ ] `ui/pages/imports/dozimetre_pdf_import_page.py` — 4 ihlal
- [ ] `ui/pages/cihaz/bakim_form.py` — 3 ihlal
- [ ] `ui/pages/personel/fhsz_yonetim.py` — 2 ihlal
- [ ] `ui/pages/nobet/nobet_plan_page.py` — 2 ihlal
- [ ] Diğer 5 dosya (tekli ihlaller) — birer ihlal

---

## 🟡 ADIM 4 — Tema: Ham #hex kodu (6 ihlal · 3 dosya)

- [ ] `ui/pages/nobet/nobet_plan_page.py` — :522, :544
- [ ] `ui/pages/nobet/nobet_merkez_page.py` — :237, :245, :270
- [ ] `ui/pages/nobet/nobet_hazirlik_page.py` — :187

---

## 🟠 ADIM 5 — Mimari: _r.get() bypass (servis iç registry'ye doğrudan UI erişimi)

> Çözüm: Servise yeni metod ekle, UI sadece servisi çağırsın.

### _r.get() ihlalleri
- [ ] `ui/pages/personel/fhsz_yonetim.py` — 5 satır
- [ ] `ui/pages/personel/saglik_takip.py` — parçası
- [ ] `ui/pages/personel/components/personel_saglik_panel.py` — parçası
- [ ] `ui/pages/personel/components/hizli_saglik_giris.py` — parçası
- [ ] `ui/pages/nobet/nobet_rapor_page.py` — parçası
- [ ] `ui/pages/nobet/nobet_plan_page.py` — parçası
- [ ] `ui/pages/fhsz/dis_alan_puantaj_page.py` — parçası
- [ ] `ui/pages/rke/rke_page.py` — parçası

### get_registry() / registry.get() ihlalleri
- [ ] `ui/pages/fhsz/dis_alan_import_page.py` — 5 satır
- [ ] `ui/pages/imports/dozimetre_pdf_import_page.py` — parçası
- [ ] `ui/pages/imports/dozimetre_import.py` — parçası
- [ ] `ui/pages/personel/dozimetre_import.py` — parçası
- [ ] `ui/components/base_dokuman_panel.py` — 2 satır
- [ ] Diğer 5 dosya (~8 satır)

---

## 🟠 ADIM 6 — Mimari: Metod içi yeni servis nesnesi (62 ihlal · ~20 dosya)

> `__init__`'te `self._svc` kurulmuşsa metod içinde `get_xxx_service(db)` çağrısı yasak.

- [ ] `ui/pages/rke/rke_page.py` — 5 ihlal (:901, :1055, :1073, :1088, :1106)
- [ ] `ui/pages/personel/isten_ayrilik.py` — 4 ihlal (:341, :482, :500, :638)
- [ ] `ui/pages/cihaz/components/toplu_bakim_panel.py` — 4 ihlal (:171, :185, :249, :339)
- [ ] `ui/pages/personel/components/personel_ozet_servisi.py` — 3 ihlal (:46, :47, :49)
- [ ] `ui/pages/personel/components/hizli_izin_giris.py` — 3 ihlal (:123, :159, :208)
- [ ] `ui/pages/nobet/nobet_rapor_page.py` — 3 ihlal (:506, :532, :563)
- [ ] `ui/pages/fhsz/dis_alan_import_page.py` — 3 ihlal (:240, :248, :456)
- [ ] `ui/pages/personel/dis_personel_fhsz.py` — 3 ihlal (:258, :311, :354)
- [ ] `ui/pages/cihaz/ariza_islem.py` — 2 ihlal (:240, :487)
- [ ] `ui/pages/cihaz/cihaz_listesi.py` — 2 ihlal (:547, :597)
- [ ] `ui/pages/personel/fhsz_yonetim.py` — 2 ihlal (:736, :1032) — `self._svc` yeniden atanıyor
- [ ] `ui/pages/personel/izin_takip.py` — 2 ihlal (:559, :759)
- [ ] `ui/pages/personel/saglik_takip.py` — 2 ihlal (:367, :1435)
- [ ] `ui/pages/fhsz/dis_alan_kurulum_page.py` — 2 ihlal (:367, :416)
- [ ] `ui/pages/nobet/nobet_plan_page.py` — 1 ihlal (:152 — property her çağrıda yeni nesne)
- [ ] `ui/pages/nobet/nobet_merkez_page.py` — 1 ihlal (:84)
- [ ] Diğer ~15 dosya (tekli ihlaller — dashboard, rke_rapor, toplu_muayene, dozimetre_* vb.)

---

## 🟡 ADIM 7 — SonucYonetici Uyumsuzluğu (~40 ihlal · 11 servis)

> Public API metodları `bool` / `None` / `list` döndürüyor olmamalı → `SonucYonetici` döndürmeli.

- [ ] `core/services/izin_service.py` — 9 ihlal (öncelikli)
- [ ] `core/services/nobet/nb_tercih_service.py` — 6 ihlal
- [ ] `core/services/nobet/nb_plan_service.py` — ~4 ihlal
- [ ] `core/services/nobet/nb_mesai_service.py` — ~3 ihlal
- [ ] `core/services/dozimetre_service.py` — 4 ihlal
- [ ] `core/services/nobet/nobet_adapter.py` — ~3 ihlal
- [ ] `core/services/nobet_service.py` — ~4 ihlal (helper'lar hariç)
- [ ] `core/services/personel_service.py` — 2 ihlal
- [ ] `core/services/bakim_service.py` — 1 ihlal
- [ ] `core/services/dis_alan_import_service.py` — 2 ihlal
- [ ] `core/services/dashboard_service.py` — 2 ihlal (get_today_summary None dönüyor)

---

## 📊 İlerleme Özeti

| Adım | Konu | Toplam | Tamamlanan | Kalan |
|---|---|---|---|---|
| 0 | Güvenlik (token.json) | 4 | 0 | 4 |
| 1 | QMessageBox → hata_yonetici | 318 ihlal | 318 | 0 |
| 2 | Tema: STYLES/S.get() | 75 ihlal | 73 | 2 |
| 3 | Tema: f-string | 23 ihlal | 0 | 23 |
| 4 | Tema: #hex | 6 ihlal | 0 | 6 |
| 5 | _r.get() / get_registry() bypass | ~25 ihlal | 0 | ~25 |
| 6 | Metod içi yeni servis | 62 ihlal | 0 | 62 |
| 7 | SonucYonetici artıkları | ~40 ihlal | 0 | ~40 |

---

## 📝 Notlar

- `ui/styles/components.py` ve `ui/styles/__init__.py` — **dokunma** (altyapı ref dosyaları)
- Import sayfalarındaki (`ui/pages/imports/*.py`) modül seviyesi fabrika fonksiyonları kasıtlı olabilir — değiştirmeden önce akışı anla
- Private helper fonksiyonlar (`_atanabilir`, `_kisit_kontrol` vb.) `bool` döndürebilir — SonucYonetici'ye çevirme

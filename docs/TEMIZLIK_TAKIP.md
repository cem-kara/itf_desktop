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

- [x] `ui/pages/personel/dozimetre_import.py` — 4 ihlal ✅ tamamlandı
- [x] `ui/pages/imports/dozimetre_pdf_import_page.py` — 4 ihlal ✅ tamamlandı
- [x] `ui/pages/cihaz/bakim_form.py` — 3 ihlal ✅ tamamlandı
- [x] `ui/pages/personel/fhsz_yonetim.py` — 2 ihlal ✅ tamamlandı
- [x] `ui/pages/nobet/nobet_plan_page.py` — 2 ihlal ✅ tamamlandı
- [x] `ui/pages/imports/dozimetre_import.py` — 4 ihlal ✅ raporda atlanmıştı, tamamlandı
- [x] Diğer tekli ihlaller — uygulama kodunda görünür eşleşme kalmadı

---

## 🟡 ADIM 4 — Tema: Ham #hex kodu (6 ihlal · 3 dosya)

- [x] `ui/pages/nobet/nobet_plan_page.py` — :522, :544 ✅ tamamlandı
- [x] `ui/pages/nobet/nobet_merkez_page.py` — :237, :245, :270 ✅ tamamlandı
- [x] `ui/pages/nobet/nobet_hazirlik_page.py` — :187 ✅ tamamlandı

---

## 🟠 ADIM 5 — Mimari: _r.get() bypass (servis iç registry'ye doğrudan UI erişimi)

> Çözüm: Servise yeni metod ekle, UI sadece servisi çağırsın.

### _r.get() ihlalleri
- [x] `ui/pages/personel/fhsz_yonetim.py` — 5 satır ✅ tamamlandı
- [x] `ui/pages/personel/saglik_takip.py` — parçası ✅ tamamlandı
- [x] `ui/pages/personel/components/personel_saglik_panel.py` — parçası ✅ tamamlandı
- [x] `ui/pages/personel/components/hizli_saglik_giris.py` — parçası ✅ tamamlandı
- [x] `ui/pages/nobet/nobet_rapor_page.py` — parçası ✅ tamamlandı
- [x] `ui/pages/nobet/nobet_plan_page.py` — parçası ✅ tamamlandı
- [x] `ui/pages/fhsz/dis_alan_puantaj_page.py` — parçası ✅ tamamlandı
- [x] `ui/pages/rke/rke_page.py` — parçası ✅ tamamlandı

### get_registry() / registry.get() ihlalleri
- [x] `ui/pages/fhsz/dis_alan_import_page.py` — 5 satır ✅ tamamlandı
- [x] `ui/pages/imports/dozimetre_pdf_import_page.py` — parçası ✅ tamamlandı
- [x] `ui/pages/imports/dozimetre_import.py` — parçası ✅ tamamlandı
- [x] `ui/pages/personel/dozimetre_import.py` — parçası ✅ tamamlandı
- [x] `ui/components/base_dokuman_panel.py` — 2 satır ✅ tamamlandı
- [x] `ui/pages/personel/components/personel_nobet_mesai_panel.py` — 6 satır ✅ tamamlandı
- [x] `ui/pages/personel/components/personel_ozet_servisi.py` — 1 satır ✅ tamamlandı
- [x] `ui/pages/dokuman/dokuman_listesi.py` — 2 satır ✅ tamamlandı

### Yeni servis metodları (DisAlanService)
- [x] `get_tutanak_listesi(tutanak_no)` eklendi
- [x] `calisma_guncelle(...)` eklendi
- [x] `tutanak_listesi_sil(tutanak_no)` eklendi

### Yeni servis metodları (NobetAdapter)
- [x] `get_personel_nobet_gecmisi(personel_id)` eklendi
- [x] `get_personel_mesai_ozeti(personel_id)` eklendi

### Yeni servis metodları (DokumanService)
- [x] `get_tum_belgeler()` eklendi

### Kalan ihlaller → ADIM 6'ya devredildi
Aşağıdakiler ya `_reg` property (ADIM 6 konusu) ya da `izin_service` kapsamlı ihlallerdir:
- `ui/admin/yil_sonu_devir_page.py` — 3 ihlal
- `ui/admin/nobet_yonetim_page.py` — 1 ihlal (`_reg` property)
- `ui/pages/cihaz/components/cihaz_teknik_panel.py` — 1 ihlal
- `ui/pages/cihaz/components/cihaz_overview_panel.py` — 3 ihlal
- `ui/pages/personel/components/hizli_izin_giris.py` — 5 ihlal (izin_service)
- `ui/pages/nobet/nobet_merkez_page.py` — 1 ihlal (`_reg` property)
- `ui/pages/nobet/nobet_hazirlik_page.py` — 1 ihlal (`_reg` property)
- `ui/pages/fhsz/dis_alan_donem_gecmisi_page.py` — 1 ihlal
- `ui/pages/fhsz/dis_alan_kurulum_page.py` — 1 ihlal

---

## ✅ ADIM 6 — Mimari: Metod içi yeni servis nesnesi (62 ihlal · ~20 dosya) — TAMAMLANDI

> `__init__`'te `self._svc` kurulmuşsa metod içinde `get_xxx_service(db)` çağrısı yasak.

- [x] `ui/pages/rke/rke_page.py` — 5 ihlal ✅
- [x] `ui/pages/personel/isten_ayrilik.py` — 4 ihlal ✅
- [x] `ui/pages/cihaz/components/toplu_bakim_panel.py` — 4 ihlal ✅
- [x] `ui/pages/personel/components/hizli_izin_giris.py` — 3 ihlal ✅
- [x] `ui/pages/nobet/nobet_rapor_page.py` — 3 ihlal ✅
- [x] `ui/pages/fhsz/dis_alan_import_page.py` — 6 ihlal (DisAlanImportPage + _KarsilastirmaWidget) ✅
- [x] `ui/pages/personel/dis_personel_fhsz.py` — 3 ihlal ✅
- [x] `ui/pages/cihaz/ariza_islem.py` — 2 ihlal (ArizaIslemForm + ArizaIslemPenceresi) ✅
- [x] `ui/pages/cihaz/cihaz_listesi.py` — 2 ihlal ✅
- [x] `ui/pages/personel/fhsz_yonetim.py` — 2 ihlal (self._svc yeniden atama kaldırıldı) ✅
- [x] `ui/pages/personel/izin_takip.py` — 2 ihlal ✅
- [x] `ui/pages/personel/saglik_takip.py` — 2 ihlal ✅
- [x] `ui/pages/fhsz/dis_alan_kurulum_page.py` — 2 ihlal ✅
- [x] `ui/pages/nobet/nobet_plan_page.py` — 1 ihlal (_svc() → self._svc_instance minimal yaklaşım) ✅
- [x] `ui/pages/nobet/nobet_merkez_page.py` — QThread run() kasıtlı, atlandı ✅
- [x] `ui/pages/dokuman/dokuman_listesi.py` — 1 ihlal ✅
- [x] `ui/pages/personel/puantaj_rapor.py` — 1 ihlal ✅
- [x] `ui/admin/nobet_yonetim_page.py` — _reg() + _birim_svc() minimal yaklaşım ✅
- [x] `ui/admin/yil_sonu_devir_page.py` — 1 ihlal ✅
- [x] Diğer QThread run() metodları (rke_rapor, toplu_muayene_dialog, cihaz_ekle, dozimetre_*) — kasıtlı ✅
- [x] `ui/pages/personel/components/personel_ozet_servisi.py` — modül-seviye fonksiyon, ADIM 6 kapsamı dışı ✅

---

## 🟡 ADIM 7 — SonucYonetici Uyumsuzluğu (~40 ihlal · 11 servis)

> Public API metodları `bool` / `None` / `list` döndürüyor olmamalı → `SonucYonetici` döndürmeli.

- [x] `core/services/izin_service.py` — 9 ihlal ✅
- [x] `core/services/nobet/nb_tercih_service.py` — 6 ihlal ✅
- [x] `core/services/nobet/nb_plan_service.py` — ~4 ihlal ✅
- [x] `core/services/nobet/nb_mesai_service.py` — ~3 ihlal ✅
- [x] `core/services/dozimetre_service.py` — 4 ihlal ✅ (public API zaten uyumlu, ek düzeltme gerekmedi)
- [x] `core/services/nobet/nobet_adapter.py` — ~3 ihlal ✅ (private helper'lar kapsam dışı)
- [x] `core/services/nobet_service.py` — ~4 ihlal (helper'lar hariç) ✅
- [x] `core/services/personel_service.py` — 2 ihlal ✅
- [x] `core/services/bakim_service.py` — 1 ihlal ✅
- [x] `core/services/dis_alan_import_service.py` — 2 ihlal ✅
- [x] `core/services/dashboard_service.py` — 2 ihlal ✅ (mevcut kod uyumlu, ek düzeltme gerekmedi)

---

## 📊 İlerleme Özeti

| Adım | Konu | Toplam | Tamamlanan | Kalan |
|---|---|---|---|---|
| 0 | Güvenlik (token.json) | 4 | 0 | 4 |
| 1 | QMessageBox → hata_yonetici | 318 ihlal | 318 | 0 |
| 2 | Tema: STYLES/S.get() | 75 ihlal | 73 | 2 |
| 3 | Tema: f-string | 23 ihlal | 23 | 0 |
| 4 | Tema: #hex | 6 ihlal | 6 | 0 |
| 5 | _r.get() / get_registry() bypass | ~25 ihlal | ~17 | ~8 |
| 6 | Metod içi yeni servis | 62 ihlal | ~62 | 0 |
| 7 | SonucYonetici artıkları | ~40 ihlal | ~40 | 0 |

---

## 📝 Notlar

- `ui/styles/components.py` ve `ui/styles/__init__.py` — **dokunma** (altyapı ref dosyaları)
- Import sayfalarındaki (`ui/pages/imports/*.py`) modül seviyesi fabrika fonksiyonları kasıtlı olabilir — değiştirmeden önce akışı anla
- Private helper fonksiyonlar (`_atanabilir`, `_kisit_kontrol` vb.) `bool` döndürebilir — SonucYonetici'ye çevirme
- ADIM 7 sonrası ek standardizasyon: `core/services/backup_service.py` ve [ui/admin/backup_page.py](ui/admin/backup_page.py) yeni `SonucYonetici` sözleşmesine hizalandı.
- Genel servis taramasında kalan raw dönüşler sadece veri modeli/property düzeyinde: `dis_alan_import_service.ImportSonucu.basarili`, `dis_alan_import_service.SatirSonucu.durum`, `excel_import_service.ImportSonucu.duzeltilecekler`, `excel_import_service.ImportSonucu.uyarilar`.

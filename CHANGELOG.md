# CHANGELOG

Tüm dikkate değer değişiklikler bu dosyada belgelenmiştir.

Format: [Keep a Changelog](https://keepachangelog.com/tr/1.0.0/)

---

## [v0.4.0 — Code Quality & Architecture] - 2026-03-31

Bu sürüm yeni özellik içermez; mevcut kod tabanının kalite, güvenlik ve
mimari tutarlılığa kavuşturulmasına odaklanır. Değişikliklerin büyük çoğunluğu
çoklu YZ destekli geliştirme sürecinde biriken teknik borcu temizler.

### 🔐 Security

- **`database/token.json` ve `database/credentials.json` repodan çıkarıldı**
  - `token.json` içindeki gerçek Google OAuth token (refresh_token, client_secret dahil) güvenlik riski oluşturuyordu
  - Google Cloud Console üzerinden token iptal edildi
  - `.gitignore` güncellendi: `token.json`, `credentials.json`, `*.db`, `logs/` eklendi
  - `database/credentials.example.json` şablon dosyası eklendi

### 🧹 Dead Code Cleanup

- **pyflakes + vulture analiziyle 285 sorun giderildi:**
  - 219 kullanılmayan import (`autoflake --remove-all-unused-imports`)
  - 42 kullanılmayan yerel değişken (ör. `renk1`, `embedded`, `doluluk_renk`)
  - 13 boş f-string (`f"metin"` → `"metin"` veya değişken eklendi)
    - `backup_service.py` ×4, `rke_merkez.py` ×2, `ariza_islem.py`, `personel_overview_panel.py` ×2, diğerleri
  - 11 yeniden tanımlama: `nobet_service.py`'de `birim_ayar_kaydet` 3 kez, `main_window.py`'de `WelcomePage`, vb.
  - 4 ulaşılamaz kod (`return` sonrası satırlar)

### 💬 Dialog Sistemi

- **324 doğrudan `QMessageBox` çağrısı `core/hata_yonetici` modülüne taşındı** (33 dosya)
  - `QMessageBox.critical` → `hata_goster`
  - `QMessageBox.warning` → `uyari_goster`
  - `QMessageBox.information` → `bilgi_goster`
  - `QMessageBox.question` → `soru_sor`
  - En yoğun dosyalar: `settings_page.py` (40), `nobet_yonetim_page.py` (28), `backup_page.py` (24)
  - `mesaj_kutusu.py` ve `action_guard.py` meşru wrapper/guard sınıfları — dokunulmadı

### 🎨 Tema Sistemi

- **106 `setStyleSheet` ihlali giderildi** — Python kodunda renk string'i kalmadı:
  - 23 `setStyleSheet(f"...")` → `setProperty("style-role", ...)` / `setProperty("color-role", ...)`
  - 75 `setStyleSheet(S.get(...))` / `STYLES[...]` → `setProperty`
  - 8 ham `#hex` renk kodu → `setProperty` veya dinamik istisna kalıbı
  - En yoğun dosya: `personel_ekle.py` (36 STYLES ihlali)

### 🏗️ Mimari Katman

- **`get_registry()` UI içinde kullanım — 23 bypass temizlendi** (12 dosya)
  - `dis_alan_import_page.py`, `dozimetre_*_import`, `nobet_hazirlik_page.py`, vb.
  - Her bypass için karşılık gelen servise yeni metod eklendi
- **`_r.get()` UI'da doğrudan erişim — 23 bypass temizlendi** (8 dosya)
  - `fhsz_yonetim.py`, `saglik_takip.py`, `personel_saglik_panel.py`, `nobet_rapor_page.py`, vb.
- **Metod içinde yeni servis nesnesi — 62 ihlal temizlendi**
  - `__init__`'te kurulan `self._svc` kullanılacak şekilde refactor edildi
  - En yoğun: `rke_page.py` (5), `isten_ayrilik.py` (4), `toplu_bakim_panel.py` (4)

### 📦 SonucYonetici

- Servis katmanında kalan eski stil dönüşler (`return []`, `return None`, `return False`) temizlendi
- `izin_service.py`, `dozimetre_service.py`, `personel_service.py` öncelikli
- Private helper fonksiyonlar (`_atanabilir`, `_kisit_kontrol`) muaf tutuldu — bool döndürmeleri doğru

### 🗄️ Migration

- **`core/migrations.py` silindi** — 1375 satırlık zombie dosya; hiçbir yer import etmiyordu
  - Dosya başlığı `# database/migrations.py` diyordu — yanlışlıkla `core/` altına kopyalanmıştı
- **`database/migrations.py` sıfırdan yazıldı — temiz squash:**
  - `CURRENT_VERSION = 1` (eski v1–v7 tek `create_tables()` çağrısına birleştirildi)
  - v3–v7 arası eklenen tüm kolonlar (`FmMaxSaat`, `MaxGunlukSureDakika`, `HaftasonuCalismaVar`,
    `ResmiTatilCalismaVar`, `DiniBayramCalismaVar`, `ArdisikGunIzinli`) ve `NB_HazirlikOnay` tablosu
    doğrudan `CREATE TABLE` bloklarına dahil edildi
  - `PRAGMA foreign_keys=ON` — her bağlantıda zorunlu (SQLite varsayılanı OFF'dur)
  - FK kısıtları tüm yabancı anahtar kolonlarına eklendi (`Personel.KimlikNo`, `Cihazlar.Cihazid`, vb.)
  - Mevcut kurulumlar (schema_version MAX ≥ 1): hiçbir değişiklik gerekmez
  - `_set_schema_version` açık bağlantı alır — transaction bütünlüğü korunur

### 👻 Nöbet Modülü

- **`nobet_service.py` legacy durumu netleştirildi:**
  - `core/di.py`'deki `get_nobet_service(db)` `NobetAdapter` döndürüyor, `NobetService` değil
  - `nobet_service.py` DI üzerinden hiç instantiate edilmiyor — legacy kod olarak işaretlendi
  - Aktif implementasyon: `core/services/nobet/nobet_adapter.py`
- **Sessiz hata yutma → `logger.warning`:**
  - `nb_algoritma.py` plan satırı silme (`:449`) ve veri yükleme (`:367`)
  - `nobet_adapter.py` (`:429`, `:438`, `:610`)
  - `nb_mesai_service.py` (`:693`)

---

## [v0.3.0 — UI Stabilization] - 2026-03-06

### 2026-03-12 Güncellemesi

#### ✨ Fixed
- `personel_ekle.py`: "Evet" dalında `btn_kaydet.setEnabled(True)` eksikti — düzeltildi
- `personel_ekle.py`: `QTabWidget` import eksikliği — düzeltildi

#### ✨ Added
- `personel_ekle.py`: Belge paneli sekmeli yapıya (QTabWidget) taşındı
  - Tab 1 — "👤 Kişisel Bilgiler" / Tab 2 — "📎 Belgeler" (kayıt öncesi kilitli)
  - Kayıt sonrası Belgeler sekmesi otomatik açılır; "Yeni Personel" reset akışında kilitlenir

### 2026-03-07 Güncellemesi

#### ✨ Fixed
- `personel_ekle.py`: kayıt sonrası kapanış + belge yükleme akışı
- `base_dokuman_panel.py`: `set_entity_id()` sonrası form kontrolleri senkronu
- `hizli_izin_giris.py`: `float(None)` kaynaklı hata (`or 0` ile giderildi)
- `izin_takip.py`: ilk açılışta kayıtların görünmesi — ay/yıl filtre varsayılanı `Tümü`

#### ✨ Added
- `core/services/izin_service.py`:
  - `hesapla_yillik_hak()` — 1–10 yıl: 20 gün, 10+: 30 gün
  - `create_or_update_izin_bilgi()` — yeni personelde Izin_Bilgi bootstrap
  - `get_izin_max_gun()` — Yıllık/Şua/diğer limit hesaplama
  - `validate_izin_sure_limit()` — limit aşımında kesin engelleme
  - `has_izin_cakisma()` — iptal hariç overlap kontrolü
  - `Izin_Bilgi` numeric alanlar `None → 0.0` normalize
- `tests/test_izin_service.py`: `59 passed`

#### 🔧 Changed
- `izin_takip.py` ve `hizli_izin_giris.py` limit kontrolünde aynı servis metodları kullanıyor
- Limit ihlalinde "uyarı + devam" yerine kesin engelleme

### 2026-03-06 Önceki WIP

#### ✨ Fixed
- Pylance 184+ type-checker uyarısı temizlendi
- Tatil yönetimi: `add_tatil()` duplicate tarih kontrolü eklendi
- Personel Ekle / Belge Paneli akışı yeniden düzenlendi
- Hızlı izin / izin girişi runtime hataları giderildi

#### ✨ Added
- **Modern Dialog Sistemi** — `mesaj_kutusu.py`, `qmessagebox_yakala()` hook
- **İzin hakediş ve limit motoru** — merkezi servis katmanı kuralları
- **Test kapsamı** — `tests/test_izin_service.py`

#### 🔧 Changed
- `BaseTableModel`: `set_rows()` → `set_data()` standardizasyonu
- PySide6 enum uyumluluğu: `Qt.WA_StyledBackground` → `Qt.WidgetAttribute.WA_StyledBackground` vb.
- Auth: `SQLiteManager` → `AuthRepository` ayrıştırması (Mart 2026)
- `SonucYonetici` standart servis dönüş tipi olarak tanıtıldı

---

## [v0.2.0 — Service & Repository Layer] - 2026-03-05

### ✨ Fixed
- 20+ type-checker hatası sistemli düzeltme (core/services, database, core/auth)

### 🎯 Added
- DI Fabrika sistemi (15 servis)
- BaseRepository API (`delete`, `get_by_pk`, `get_where`)
- Abstract method compliance (CloudAdapter)

### 🔧 Changed
- Repository registry pattern
- Service initialization flow

---

## [v0.1.0 — Core Infrastructure] - 2026-02-XX

### 🎯 Added
- Tema sistemi (dark/light)
- BaseTableModel altyapısı
- Icon sistemi
- Sidebar menü yapılandırması

---

## Format Kuralları

- **Added**: Yeni özellikler
- **Changed**: Mevcut özelliklerin değiştirilmesi
- **Fixed**: Hata düzeltmeleri
- **Deprecated**: Yakında kaldırılacak
- **Removed**: Silinen özellikler
- **Security**: Güvenlik güncellemeleri

Her commit: `[v0.4.0] type(scope): Başlık`

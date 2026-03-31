# REPYS V3 — Radyoloji Veritabanı Yönetim Sistemi

> **v0.4.0** — Code Quality & Architecture 🏗️

Radyoloji Teknikeri Odası (RTO) için geliştirilmiş, modern ve tip-güvenli masaüstü uygulaması.
Personel yönetimi, cihaz takibi, RKE envanter ve muayene işlemlerini merkezi bir platformdan yönetin.

---

## 🎯 v0.4.0 Yenilikleri

- **Ölü Kod Temizliği** — pyflakes + vulture ile 285 sorun giderildi (kullanılmayan import/değişken, ulaşılamaz kod, boş f-string)
- **Dialog Sistemi Tamamlandı** — 324 `QMessageBox` çağrısı `core/hata_yonetici` modülüne taşındı
- **Tema Sistemi Tamamlandı** — 106 `setStyleSheet(f-string/STYLES/#hex)` ihlali giderildi; tüm stiller `setProperty` üzerinden
- **Mimari Katman Onarımı** — 68 `get_registry()` / `_r.get()` bypass ve metod içi servis instantiation düzeltildi
- **`SonucYonetici` Uyumu** — Servis katmanında homojen dönüş tipi, eski `return []` kalıpları temizlendi
- **Migration Squash** — v1–v7 tek temiz v1 şemasına birleştirildi; `PRAGMA foreign_keys=ON` eklendi
- **Güvenlik** — `token.json` ve `credentials.json` repodan çıkarıldı; `.gitignore` güncellendi
- **Zombie Dosya Silindi** — Hiç import edilmeyen `core/migrations.py` (1375 satır) kaldırıldı
- **Nöbet Modülü Netleşti** — `nobet_service.py` legacy kodu belirlendi; aktif implementasyon `NobetAdapter`

---

## 📋 Özellikler

### 👥 Personel Yönetimi
- **Personel Listesi** — Tüm personel kaydını merkezi veritabanında takip edin
- **Personel Ekleme** — Yeni personel bilgilerini sisteme kaydedin (sekmeli belge yükleme akışı)
- **İzin Takibi** — İzin giriş-çıkış işlemlerini ve izin bilgilerini yönetin
- **İzin Kural Motoru** — Yıllık/Şua/diğer izin limitleri merkezi servis katmanında
- **Sağlık Takibi** — Sağlık muayene takvimini tutun
- **FHSZ Yönetimi** — Fiili Hizmet Süresi Zammı hak ediş hesabı
- **Puantaj Raporları** — Aylık puantaj raporlarını otomatik oluşturun

### 🔧 Cihaz Yönetimi
- **Cihaz Listesi** — Radyoloji cihazlarının merkezi envanteri
- **UTS Entegrasyonu** — Türkiye Ürün Takip Sistemi'nden cihaz teknik verileri çekme
- **Teknik Hizmetler** — Cihaz arızaları, bakım geçmişi ve kalibrasyon takibi

### 📊 RKE İşlemleri
- **RKE Envanter** — Radyoloji Koruyucu Ekipman listesi ve detaylı rapor
- **RKE Muayene** — Muayene sonuçları ve uygunluk durumu
- **RKE Raporlama** — Standartlara göre muayene raporları

### 🔔 Nöbet Yönetimi
- **Otomatik Plan** — `NbAlgoritma` ile aylık nöbet planı oluşturma
- **Vardiya Yönetimi** — Birim bazlı vardiya grupları ve zaman dilimleri
- **Fazla Mesai** — Mesai hesaplama, hedef-fiili karşılaştırma ve ödeme takibi
- **Tercih Sistemi** — Personel bazlı aylık nöbet tercihleri

### ⚙️ Yönetici İşlemleri
- **Kullanıcı Yönetimi** — Oturum açma, rol tabanlı yetkilendirme (RBAC)
- **Log Görüntüleyici** — Uygulama log dosyalarını inceleyin
- **Yedek Yönetimi** — Veritabanı yedekleme ve geri yükleme
- **Ayarlar** — Sistem yapılandırması ve tatil takvimi

### 🎨 UI/UX
- **Merkezi Hata Yönetimi** — `hata_goster`, `uyari_goster`, `bilgi_goster`, `soru_sor`
- **Tema Sistemi** — Tamamen `setProperty("style-role", ...)` tabanlı
- **Dark Tema** — Özelleştirilmiş QSS token sistemi (`theme_template.qss`)
- **Icon System** — Merkezi `IconRenderer` ile tutarlı görsel dil

---

## 🚀 Kurulum

### Gereksinimler

- **Python** 3.12+
- **PySide6** 6.x
- Tam bağımlılık listesi: `requirements.txt`

### Adımlar

```bash
# 1. Repository klonla
git clone https://github.com/<kullanici>/REPYS.git
cd REPYS

# 2. Virtual environment
python -m venv venv
source venv/bin/activate      # Linux/macOS
venv\Scripts\activate         # Windows

# 3. Bağımlılıklar
pip install -r requirements.txt

# 4. Google entegrasyonu (opsiyonel)
cp database/credentials.example.json database/credentials.json
# credentials.json içini Google Cloud Console'dan doldurun

# 5. Başlat
python main.pyw
```

### İlk Çalıştırma

- Uygulama ilk açılışta veritabanını ve tüm tabloları otomatik oluşturur (`migrations.py`)
- Gerekli dizinler (`logs/`, `data/`, `database/backups/`) otomatik kurulur
- Varsayılan çalışma modu `offline` — Google entegrasyonu olmadan da çalışır
- İlk admin: Admin Panel → Kullanıcı Yönetimi

### Google Entegrasyonu (Opsiyonel)

1. [Google Cloud Console](https://console.cloud.google.com)'da proje oluşturun
2. Google Sheets API ve Drive API'yi etkinleştirin
3. OAuth 2.0 credentials indirin → `database/credentials.json` olarak kaydedin
4. Ayarlar → Uygulama Modu → `online`

> ⚠️ `credentials.json` ve `token.json` dosyalarını asla Git'e commit etmeyin.

---

## 📂 Proje Yapısı

```
REPYS/
├── main.pyw                        ← Giriş noktası, migration, auth akışı
├── ayarlar.json                    ← Menü yapılandırması
├── requirements.txt
├── CHANGELOG.md
├── SETUP.md                        ← Google kurulum + ilk admin rehberi
├── database/
│   └── credentials.example.json   ← Google credentials şablonu
│
├── core/
│   ├── di.py                      ← 15 DI fabrikası — buradan import et
│   ├── config.py                  ← AppConfig: mod, log, sync
│   ├── hata_yonetici.py           ← Merkezi hata yönetimi + SonucYonetici
│   ├── logger.py
│   ├── date_utils.py              ← parse_date, to_db_date, to_ui_date
│   ├── validators.py              ← TC, email, telefon validasyonu
│   ├── hesaplamalar.py
│   ├── rapor_servisi.py
│   ├── auth/                      ← auth_service, authorization_service, session
│   └── services/
│       ├── (15 servis dosyası)
│       └── nobet/                 ← NbAlgoritma, NobetAdapter ve NB_ servisleri
│
├── database/
│   ├── sqlite_manager.py          ← WAL + PRAGMA foreign_keys=ON
│   ├── base_repository.py
│   ├── repository_registry.py
│   ├── table_config.py            ← Tablo şemaları ve PK'lar — buradan kopyala
│   ├── migrations.py              ← CURRENT_VERSION=1 (v1–v7 squash)
│   ├── sync_service.py
│   ├── auth_repository.py
│   └── repositories/
│
├── ui/
│   ├── main_window.py
│   ├── sidebar.py
│   ├── theme_template.qss         ← Tek stil kaynağı — Python'da renk yok
│   ├── theme_manager.py
│   ├── dialogs/mesaj_kutusu.py
│   ├── guards/
│   ├── components/base_table_model.py
│   ├── pages/                     ← dashboard, cihaz, personel, rke, fhsz, nobet, imports
│   ├── admin/
│   └── styles/                    ← colors, themes, icons, components
│
├── data/
│   ├── templates/excel/
│   └── templates/pdf/
│
└── tests/
    └── services/test_izin_service.py   ← 59 passed
```

---

## 🔧 Geliştirme

### Katman Kuralı

```
UI (ui/pages/) → Servis (core/di.py) → Repository (database/) → SQLite
```

- UI **sadece** `core/di.py` fabrikalarını kullanır
- Servisler `self._r.get("TABLO")` ile repo'ya erişir
- UI asla `get_registry()`, `_r.get()` veya doğrudan repo çağrısı yapmaz

### Hata Yönetimi

```python
from core.hata_yonetici import hata_goster, uyari_goster, bilgi_goster, soru_sor

# ❌ YASAK
QMessageBox.critical(self, "Hata", mesaj)

# ✅ DOĞRU
hata_goster(self, mesaj)
```

### Tema Sistemi

```python
# ❌ YASAK
btn.setStyleSheet(f"background: {DarkTheme.ACCENT};")
btn.setStyleSheet(S.get("btn_action"))

# ✅ DOĞRU
btn.setProperty("style-role", "action")
lbl.setProperty("color-role", "muted")
```

### SonucYonetici

```python
# Servis
def kaydet(self, veri: dict) -> SonucYonetici:
    try:
        self._r.get("TABLO").insert(veri)
        return SonucYonetici.tamam("Kayıt eklendi.")
    except Exception as e:
        return SonucYonetici.hata(e, "XxxService.kaydet")

# UI
sonuc = self._svc.kaydet(veri)
if sonuc.basarili:
    bilgi_goster(self, sonuc.mesaj)
else:
    hata_goster(self, sonuc.mesaj)
```

---

## 📊 Veritabanı

| Tablo | PK | Sync |
|---|---|---|
| `Personel` | `KimlikNo` | ✓ |
| `Izin_Giris` | `Izinid` | ✓ |
| `Izin_Bilgi` | `TCKimlik` | ✗ |
| `Cihazlar` | `Cihazid` | ✓ |
| `Cihaz_Ariza` | `Arizaid` | ✓ |
| `Ariza_Islem` | `Islemid` | ✓ |
| `Periyodik_Bakim` | `Planid` | ✓ |
| `Kalibrasyon` | `Kalid` | ✓ |
| `Personel_Saglik_Takip` | `KayitNo` | ✓ |
| `RKE_Muayene` | `KayitNo` | ✓ |
| `RKE_List` | `EkipmanNo` | ✓ |
| `FHSZ_Puantaj` | `["Personelid","AitYil","Donem"]` | ✗ |

> Tam liste ve sync ayarları: `database/table_config.py`

---

## 🧪 Test

```bash
pytest tests/ -v
```

---

## 📝 Lisans

[MIT Lisansı](LICENSE)

---

## 🛠️ Proje Durumu

| Özellik | Durum |
|---|---|
| 👥 Personel Yönetimi | ✅ Aktif |
| 🔧 Cihaz Yönetimi | ✅ Aktif |
| 📊 RKE İşlemleri | ✅ Aktif |
| 🔔 Nöbet Yönetimi | ✅ Aktif |
| 🔐 Auth & RBAC | ✅ Tamamlandı |
| 💬 Hata Yönetimi (`hata_yonetici`) | ✅ Tamamlandı |
| 🎨 Tema Sistemi (`setProperty` tabanlı) | ✅ Tamamlandı |
| 🏗️ Mimari Katman Uyumu | ✅ Tamamlandı |
| 🧹 Ölü Kod Temizliği | ✅ Tamamlandı |
| 🔒 FK Kısıtlaması (`PRAGMA foreign_keys=ON`) | ✅ Tamamlandı |
| 🗄️ Migration Squash (v1 temiz) | ✅ Tamamlandı |
| 🧪 Type-Safety (Pylance 0 hata) | ✅ Tamamlandı |
| ✅ İzin Servis Testleri | ✅ 59 Passed |
| 🌐 Google Senkronizasyonu | ✅ Aktif |
| 📱 Runtime Tema Değiştirme | 🔄 Planlı |
| 🧪 Genişletilmiş Test Kapsamı | 🔄 TODO-8 |

---

**Son Güncelleme:** Mart 2026 | **Versiyon:** v0.4.0 (Code Quality & Architecture)

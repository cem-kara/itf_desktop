# ITF Desktop — Personel ve Cihaz Yönetim Uygulaması

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![PySide6](https://img.shields.io/badge/PySide6-6.4+-green.svg)
![License](https://img.shields.io/badge/license-Proprietary-red.svg)
![Status](https://img.shields.io/badge/status-Active%20Development-yellow.svg)

**ITF Desktop**, kurumsal personel yönetimi, izin takibi, FHSZ hesapları ve cihaz/bakım takibi için modern, masaüstü tabanlı bir uygulamadır. Verileri yerel SQLite veritabanında saklar ve Google Sheets ile real-time senkronizasyon sağlar.

---

## 📋 İçindekiler

- [Özellikler](#özellikler)
- [Teknik Yığın](#teknik-yığın)
- [Kurulum](#kurulum)
- [Çalıştırma](#çalıştırma)
- [Geliştirme](#geliştirme)
- [Mimari](#mimari)
- [Sorun Giderme](#sorun-giderme)
- [Katkıda Bulunma](#katkıda-bulunma)
- [Lisans](#lisans)

---

## ✨ Özellikler

### Personel Yönetimi
- ✅ Personel kaydı, güncelleme, silme
- ✅ Kimlik, eğitim, hizmet bilgileri depolama
- ✅ Durum izleme (Aktif, Pasif, İzinli)
- ✅ Çift tıkla detay görüntüleme

### İzin Takibi
- ✅ İzin girişi ve tarafından hesaplama
- ✅ Yıllık, mazeretli, Şua izin türleri
- ✅ İzin bakiyesi hesaplama
- ✅ İzin raporu

### FHSZ Yönetimi (Fiili Hizmet Süresi Zammı)
- ✅ Puantaj raporları
- ✅ Çalışma koşuluna göre hak hesabı
- ✅ Dönemsel takip

### Cihaz ve Bakım
- ✅ Cihaz tescili (tip, marka, model, seri no)
- ✅ Arıza bildirimi ve işlem takibi
- ✅ Periyodik bakım planlaması
- ✅ Kalibrasyon kayıtları
- ✅ RKE koruyucu donanım ve muayene

### Senkronizasyon
- ✅ Google Sheets ile otomatik senkronizasyon
- ✅ Dirty/clean flag ile güvenli veri eşitlemesi
- ✅ Composite tablo desteği (FHSZ_Puantaj vb.)
- ✅ Hata detaylandırması ve user-friendly mesajlar
- ✅ Arka plan senkronizasyonu (configurable interval)

### Veritabanı Yönetimi
- ✅ SQLite ile yerel depolama
- ✅ Versiyon kontrollü migration sistemi
- ✅ Otomatik yedekleme (son 10 yedek tutulur)
- ✅ Rollback desteği

---

## 🛠️ Teknik Yığın

| Katman | Teknoloji | Versiyon |
|--------|-----------|---------|
| **GUI** | PySide6 (Qt 6) | 6.4+ |
| **Veritabanı** | SQLite 3 | 3.8+ |
| **API** | Google Sheets / Drive | v4 |
| **Python** | CPython | 3.8–3.11 |
| **İşlemler** | NumPy | 1.20+ |
| **Auth** | Google OAuth 2.0 | - |

---

## 📦 Kurulum

### Ön Koşullar

- **Python 3.8+** (3.10+ önerilir)
- **Windows 10+** veya Linux/macOS
- **Google Cloud Project** (Sheets + Drive API aktivasyonu)
- **İnternet bağlantısı** (senkronizasyon için)

### 1️⃣ Virtual Environment Oluştur

```powershell
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 2️⃣ Bağımlılıkları Yükle

```powershell
pip install -r requirements.txt
```

### Tema Merkezi (UI) — Yapılan Güncellemeler

- Tüm bileşen QSS stilleri merkezi `ui/styles/components.py` içine taşındı.
- `ThemeManager` eklendi/iyileştirildi; komponent stilleri `ThemeManager.get_all_component_styles()` ile çekiliyor.
- `ui/sidebar.py` ve personel sayfaları inline QSS yerine merkezi stilleri (`S[...]` / `STYLES[...]`) kullanacak şekilde güncellendi.
- Eksik stil anahtarları (`page`, `label`, `required_label`, `stat_*`, `combo_filter`, `spin`, `calc_btn`, vb.) eklendi; import hataları giderildi.
- Bu değişiklikler UI bakımını kolaylaştırır ve renk/tasarım değişikliklerini tek noktadan yönetmeyi sağlar.


### 3️⃣ Google API Kurulumu

#### a. Google Cloud Console'dan Kimlik Bilgileri İndir

1. [Google Cloud Console](https://console.cloud.google.com/) aç
2. Proje seç (yoksa oluştur)
3. **APIs & Services** → **Credentials**
4. **+ Create Credentials** → **OAuth 2.0 Client ID** → **Desktop application**
5. İndirilen JSON dosyasını **`credentials.json`** olarak proje köküne kopyala

```powershell
# Windows Örneği
Copy-Item "Downloads\client_secret_*.json" ".\credentials.json"
```

#### b. Google Sheets ve Drive API'yi Etkinleştir

1. Console'da **APIs & Services** → **Library**
2. "Google Sheets API" ara ve **Enable** yap
3. "Google Drive API" ara ve **Enable** yap

### 4️⃣ İlk Çalıştırma

```powershell
python main.pyw
```

**Tarayıcı açılacak**, Google hesabıyla **yetkilendirme** yapın.  
Başarılıysa, `token.json` otomatik oluşturulacak.

### 5️⃣ Yapılandırma

İsteğe bağlı: `ayarlar.json` oluştur

```json
{
    "APP_NAME": "ITF Desktop",
    "VERSION": "1.0.8",
    "AUTO_SYNC": true,
    "SYNC_INTERVAL_MIN": 15
}
```

### Offline / Online Mod (Yeni)

Uygulama artık çalışma modunu `online` veya `offline` olarak belirleyebilir.

- `online`: Google Sheets/Drive ve sync özellikleri aktiftir.
- `offline`: Bulut işlemleri devre dışıdır, yerel SQLite akışı devam eder.

Mod belirleme önceliği:

1. `ITF_APP_MODE` ortam değişkeni (`online` / `offline`)
2. `ayarlar.json` içindeki `app_mode`
3. `database/credentials.json` yoksa otomatik `offline`
4. Varsayılan `online`

`ayarlar.json` örneği:

```json
{
  "app_mode": "offline",
  "AUTO_SYNC": false,
  "SYNC_INTERVAL_MIN": 15
}
```

Geçiş durumu (2026-02-17):

- Tamamlandı (Aşama 1): `AppConfig` ile mode çözümleme ve persist altyapısı.
- Tamamlandı (Aşama 2): `CloudAdapter` (online/offline) ve DI erişimi.
- Başlatıldı: Offline modda `main_window` sync davranışı devre dışı bırakma.
- Planlanan: Sync servisi ve tüm Google çağrılarının adapter üzerinden taşınması.

Geçiş durumu güncellemesi (2026-02-18):

- Aşama 1-3 düzeltmeleri: eksik importlar ve varsayılan `APP_MODE` değeri düzeltildi.
- Offline local upload altyapısı eklendi:
  - `database/cloud_adapter.py`: offline modda `data/offline_uploads/<klasor>` altına kopyalama.
  - `database/google/utils.py`: `resolve_storage_target` eklendi (Drive ID + offline klasör adı).
- RKE tarafı test için stabilize edildi:
  - `rke_muayene` ve `rke_rapor` upload akışları `offline_folder_name` ile uyumlu.
  - `rke_rapor` mesajları offline için “Yerel klasöre kaydedildi” şeklinde güncellendi.
- Not: Bu ortamda `python/py` komutu bulunmadığından `py_compile` doğrulaması çalıştırılamadı.

---

## 🚀 Çalıştırma

### Uygulamayı Başlat

```powershell
python main.pyw
```

### Arka Planda Logları Gözle

1. `logs/app.log` — Genel loglar
2. `logs/sync.log` — Senkronizasyon detayları
3. `logs/errors.log` — Hata ve uyarılar

**Otomatik Log Rotasyonu:**
- Log dosyaları **10 MB**'a ulaştığında otomatik olarak rotasyona girerler
- Son **5 rotated backup** dosyası tutulur (eski olanlar silinir)
- Uygulama başlangıcında otomatik cleanup:
  - 7+ gün eski log dosyaları silinir
  - Toplam boyut 100 MB sınırında tutulur
  - Log sağlık durumu loglanır

### Log Rotasyonunu Test Etmek

```powershell
# Log rotasyonunu test et
python test_log_rotation.py

# Rotasyonu tetiklemek için çok sayıda log oluştur (simülasyon)
python test_log_rotation.py --generate --count=100
```

**Beklenen Çıktı:**
- Log istatistikleri (dosya boyutu, satır sayısı, son güncellenme)
- Log sağlık durumu (OK, WARNING, CRITICAL)
- Cleanup işlemi (silinen dosya sayısı, boşaltılan alan)

### Veritabanını Sıfırla (Acil Durumda)

```powershell
python -c "
from database.migrations import MigrationManager
from core.paths import DB_PATH
mgr = MigrationManager(DB_PATH)
mgr.reset_database()
print('✓ Veritabanı sıfırlandı')
"
```

---

## 👨‍💻 Geliştirme

### Geliştirme Ortamını Kurulumu

```powershell
# Bağımlılıklar + dev paketleri
pip install -r requirements.txt

# Opsiyonel: pre-commit hooks (lint otomasyonu)
pip install pre-commit
pre-commit install
```

### Kod Stilini Biçimlendir

```powershell
# black ile formatla
black .

# flake8 ile lint kontrol et
flake8 . --max-line-length=100

# mypy ile tür kontrol et
mypy core/ database/ ui/
```

### Birim Testleri Çalıştır

```powershell
# Tüm testleri çalıştır
pytest tests/ -v

# Coverage raporu ile
pytest tests/ --cov=core --cov=database --cov-report=html
```

### Proje Yapısı

```
itf_desktop/
├── main.pyw                  # Giriş noktası
├── requirements.txt          # Bağımlılıklar
├── README.md                 # Bu dosya
├── SECRETS_MANAGEMENT.md     # Gizli bilgi yönetimi
├── TODO.md                   # Geliştirme TODO
│
├── core/                     # Temel modüller
│   ├── config.py            # Uygulama konfigürasyonu
│   ├── paths.py             # Dizin yolları
│   ├── logger.py            # Structured logging
│   └── hesaplamalar.py      # İş mantığı (Şua, iş günü vb.)
│
├── database/                 # Veri katmanı
│   ├── sqlite_manager.py    # SQLite bağlantısı
│   ├── migrations.py        # Schema versioning
│   ├── base_repository.py   # CRUD + sync
│   ├── repository_registry.py # Repo fabrikası
│   ├── table_config.py      # Tablo tanımları
│   ├── sync_service.py      # Google Sheets sync
│   ├── sync_worker.py       # QThread worker
│   └── google/              # Google API entegrasyonu
│       ├── auth.py
│       ├── sheets.py
│       ├── drive.py
│       └── utils.py
│
├── ui/                       # Kullanıcı arayüzü
│   ├── main_window.py       # Ana pencere
│   ├── sidebar.py           # Menü sidebar
│   ├── theme_manager.py     # Tema yönetimi
│   ├── theme.qss            # Dark theme
│   ├── components/
│   │   └── data_table.py    # Tablo bileşeni
│   └── pages/
│       ├── placeholder.py   # Template sayfası
│       └── personel/        # Personel modülü
│           ├── personel_listesi.py
│           ├── personel_ekle.py
│           ├── izin_giris.py
│           ├── izin_takip.py
│           ├── fhsz_yonetim.py
│           └── puantaj_rapor.py
│
├── data/                     # Runtime veri
│   ├── local.db             # SQLite (çalışma zamanında oluşturulur)
│   └── backups/             # Otomatik DB yedekleri
│
├── logs/                     # Uygulama logları
│   ├── app.log
│   ├── sync.log
│   └── errors.log
│
└── docs/                     # Dokümantasyon
    ├── OPERASYON_VE_RAPORLAMA_MERKEZI.md
    ├── proje_dokumantasyonu.md
    ├── PROJE_TAM_INCELEME_VE_YAPILACAKLAR_RAPORU_2026-02-15.md
    └── ITF_Desktop_Analiz_Raporu.md
```

---

## 🏗️ Mimari

### Veri Akışı

```
Kullanıcı (UI)
    ↓
MainWindow (ui/main_window.py)
    ↓
Page (PersonelListesi, İzinGirişi vb.)
    ↓
RepositoryRegistry + BaseRepository
    ↓
SQLiteManager (local.db)
    ↓
[Arka planda: SyncWorker → SyncService → Google Sheets]
```

### Senkronizasyon Mantığı

```
Local DB (dirty/clean) ←→ Google Sheets
     ↓                         ↓
INSERT/UPDATE → sync_status='dirty'
     ↓
SyncWorker.run() (QThread)
     ↓
Push (dirty → clean) + Pull (gelen veriler)
     ↓
Conflict çözünürlüğü (local wins)
```

### Migration Sistemi

```
v0 (no schema_version)
     ↓
v1 (create tables)
     ↓
v2 (add sync_status + updated_at columns)
     ↓
[Otomatik yedekleme + rollback desteği]
```

---

## 🚨 Sorun Giderme

### "ModuleNotFoundError: No module named 'PySide6'"

```powershell
# Virtual environment'ı kontrol et
which python  # (veya `where python` Windows'ta)
# Çıktı: venv/bin/python olmalı

# Bağımlılıkları yeniden yükle
pip install -r requirements.txt --force-reinstall
```

### "credentials.json bulunamadı"

```powershell
# 1. Google Cloud Console'dan indir
# 2. Proje kökünə (main.pyw ile aynı dizin) kopyala
# 3. .gitignore içinde credentials.json var mı kontrol et
ls -la credentials.json
```

### "Sync hatası: Bağlantı hatası"

```powershell
# 1. İnternet bağlantısını kontrol et
# 2. logs/sync.log'u gözle
# 3. logs/errors.log'i kontrol et
tail -f logs/errors.log

# 4. Token süresi dolmuş olabilir, sıfırla
rm token.json
# Uygulamayı yeniden başlat → tarayıcıda yetkilendirme
```

### Veritabanı Kilitli

```powershell
# Uygulamayı tamamen kapat
# Eski thread'ler kapalıysa şu yapabilirsin:
rm data/local.db
python main.pyw  # Yeni DB oluşturulacak
```

### Büyük Veritabanında Yavaş Yükleme

Öneriler:
- Tablo uzmanlaştırması (pagination, lazy load) kontrol edilecek
- Index ekleme (migration v3'te yapılabilir)
- Sync interval'ı artır (SYNC_INTERVAL_MIN)

---

## 📝 Katkıda Bulunma

### Geliştirme Prosedürü

1. **Branch Oluştur**
   ```powershell
   git checkout -b feature/my-feature
   ```

2. **Değişiklikler Yap ve Test Et**
   ```powershell
   pytest tests/ -v
   black .
   flake8 .
   ```

3. **Commit ve Push**
   ```powershell
   git add .
   git commit -m "feat: my feature"
   git push origin feature/my-feature
   ```

4. **Pull Request Aç**
   - GitHub'ta PR oluştur
   - Minimum 1 review gerekli
   - CI tests geçmeli

### Adlandırma Kuralları

- **Branch:** `feature/`, `bugfix/`, `docs/`, `refactor/` ön ekleri ile başla
- **Commit:** Conventional Commits kullan (`feat:`, `fix:`, `docs:`, vb.)
- **PR Title:** Açıklayıcı ve öz olsun

### Yeni Özellik Checklist

- [ ] Feature branch'inde geliştirildi
- [ ] Unit test yazıldı ve geçti
- [ ] Code review geçti
- [ ] `tests/` altında test dosyaları var
- [ ] `README.md` güncellendi (gerekirse)
- [ ] `TODO.md` güncellendi (task kapatıldı)
- [ ] Docstring eklendi (Python dosyaları)

---

## 📚 Dokümantasyon

Güncel dokümanlar:
- `docs/DURUM_VE_YOL_HARITASI.md` (yapılanlar + yapılacaklar + net durum)
- `docs/MIMARI_OVERVIEW.md` (mimari özet)
- `docs/ARSIV_INDEX.md` (arşive alınan eski dokümanların listesi)

Diğer:
- `SECRETS_MANAGEMENT.md`
- `TODO.md`

---

## 🔒 Güvenlik

### Gizli Dosyalar

Bu dosyalar **Git repo'suna eklenmemelidir**:
- `credentials.json` — Google OAuth kimlik bilgileri
- `token.json` — Google API access token
- `ayarlar.json` — Ortama özgü konfigürasyon
- `.env` — Ortam değişkenleri

`.gitignore` otomatik olarak bunları dışlar. Eğer yanlışlıkla eklendiyse:
- Bkz. [SECRETS_MANAGEMENT.md](SECRETS_MANAGEMENT.md) → "Geçmiş Commitlerden Kaldır"

---

## 📊 İstatistikler

| Metrik | Değer |
|--------|-------|
| **Kod satırı** | ~3000+ (UI + DB + Core) |
| **Python dosyası** | 30+ |
| **Veritabanı tablosu** | 14 |
| **UI sayfası** | 7+ (personel, izin, cihaz, vb.) |
| **Test kapsamı** | ~40% (geliştiriliyorum) |

---

## 🗺️ Roadmap

### Mevcut (v1.0.1)
- ✅ Personel yönetimi
- ✅ İzin takibi
- ✅ FHSZ hesaplamaları
- ✅ Cihaz ve bakım
- ✅ Google Sheets sync

### Planlanan (v1.1)
- 🔲 Unit test %80+ coverage
- 🔲 CI/CD pipeline (GitHub Actions)
- 🔲 Performans optimizasyonu (paging, index)
- 🔲 Rapor çıktısı (Excel, PDF)

### Gelecek (v2.0)
- 🔲 Çok kullanıcı desteği
- 🔲 Rol tabanlı erişim (RBAC)
- 🔲 Mobil app (React Native)
- 🔲 Web arayüzü (Django REST)

---

## 📞 İletişim ve Destek

| Kanal | Bilgi |
|-------|-------|
| **Bug Report** | GitHub Issues |
| **Documentation** | [docs/](docs/) klasörü |
| **Q&A** | TODO.md → "Sorular ve Sorunlar" bölümü |

---

## 📜 Lisans

Bu proje **Proprietary** lisanslıdır. Komersyal veya dış kullanım için izin gereklidir.

---

## ✍️ Tarih ve Versiyon

- **Versiyon:** 1.0.1
- **Son Güncelleme:** 11 Şubat 2026
- **Geliştirici:** ITF Team

---

**Sorularınız için** [SECRETS_MANAGEMENT.md](SECRETS_MANAGEMENT.md) veya [TODO.md](TODO.md) kontrol edin. 🚀

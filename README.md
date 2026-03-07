# REPYS V3 — Medikal Veritabanı Yönetim Sistemi

> **v0.3.0** — UI Stabilization & Type-Safety ✨

Radyoloji Teknikeri Odası (RTO) için geliştirilmiş, modern ve tip-güvenli masaüstü uygulaması. Personel yönetimi, cihaz takibi, RKE envanter ve muayene işlemlerini merkezi bir platformdan yönetin.

## 🎯 v0.3.0 Yenilikleri

- **Modern Dialog Sistemi** — Temalı mesaj kutuları, native QMessageBox yerine custom modal overlay
- **Type-Safety** — Pylance 184+ type-checker hatası temizlendi (proje-wide 0 hata)
- **Auth & RBAC** — Kullanıcı oturum yönetimi ve rol tabanlı yetkilendirme
- **PySide6 Uyumluluğu** — Tüm enum'lar modern `.Type` formatına güncellendi
- **BaseTableModel Standardizasyonu** — Tüm tablolar merkezi model üzerinden
- **Development Workflow** — CHANGELOG.md + .gitmessage + conventional commits
- **İzin Kural Motoru** — Yıllık/Şua/diğer izinler için merkezi max gün doğrulaması (servis katmanı)
- **İzin Çakışma Kontrolü** — Personel bazlı tarih overlap kontrolü (iptal kayıtları hariç)
- **Yeni Personelde İzin Bootstrap** — `Izin_Bilgi` otomatik oluşturma + `None -> 0.0` normalize
- **Test Kapsamı** — `tests/test_izin_service.py` içinde 59 geçen test (hakediş, limit, çakışma, normalize)

## 📋 Özellikler

### 👥 Personel Yönetimi
- **Personel Listesi** — Tüm personel kaydını merkezi database'de takip edin
- **Personel Ekleme** — Yeni personel bilgilerini sisteme kaydedin
- **Belge Yükleme Akışı** — Kayıt sonrası belge yükleme ve "Yeni Personel" ile hızlı form sıfırlama
- **İzin Takibi** — İzin giriş-çıkış işlemlerini ve izin bilgilerini yönetin
- **Sağlık Takibi** — Sağlık muayene takvimini tutun
- **FHSZ Yönetimi** — Fiili Hizmet Süresi Zammı hak ediş hesabı
- **Puantaj Raporları** — Aylık puantaj raporlarını otomatik oluşturun

### 🔧 Cihaz Yönetimi
- **Cihaz Listesi** — Radyoloji cihazlarının merkezi envanteri
- **Cihaz Ekleme** — Yeni cihaz kaydı oluşturma
- **Teknik Hizmetler** — Cihaz arızaları, bakım geçmişi ve kalibrasyon takibi

### 📊 RKE İşlemleri
- **RKE Envanter** — Radyoloji Kalite Envanteri liste ve detaylı rapor
- **RKE Muayene** — Muayene sonuçları ve uygunluk durumu
- **RKE Raporlama** — Ahmed ve ABD standartlarına göre raporlar

### ⚙️ Yönetici İşlemleri
- **Kullanıcı Yönetimi** — Oturum açma, rol tabanlı yetkilendirme (RBAC)
- **Log Görüntüleyici** — Uygulama log dosyalarını inceleyin
- **Yedek Yönetimi** — Veritabanı yedekleme ve geri yükleme
- **Ayarlar** — Sistem yapılandırması ve tatil takvimi

### 🎨 UI/UX
- **Modern Mesaj Kutuları** — Temalı, modal overlay ile popup deneyimi
- **Dark Tema** — Tamamen özelleştirilmiş QSS tema sistemi
- **Type-Safe Widgets** — Pylance destekli, hatasız UI katmanı
- **Icon System** — Merkezi ikon renderer ile tutarlı görsel dil

## 🚀 Başlangıç

### Gereksinimler

- **Python** 3.12+ (type hints ve modern syntax için)
- **PySide6** — Qt6 Python bindings (6.x)
- **openpyxl** — Excel işlemleri
- **numpy** — Hesaplamalar
- **Jinja2** — Template rendering
- **Pillow** — Görsel işleme
- **bcrypt** — Şifre hashing (auth sistemi)
- **Google API** — Google Sheets/Drive entegrasyonu (opsiyonel)
- **Pylance** — Type-checking (geliştirme için önerilir)

### Kurulum

1. **Repository klonla:**
   ```bash
    git clone https://github.com/<kullanici-veya-organizasyon>/REPYS.git
    cd REPYS
   ```

2. **Virtual Environment oluştur:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # veya
   venv\Scripts\activate  # Windows
   ```

3. **Bağımlılıkları yükle:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Uygulamayı başlat:**
   ```bash
   python main.pyw
   ```

### İlk Çalıştırma

- Uygulama ilk açılışında otomatik olarak veritabanı oluşturur
- Gerekli dizinler (`logs/`, `data/`, `database/` vb) otomatik kurulur
- Tema ve stil ayarları merkezi lokasyondan yönetilir

## 📂 Proje Yapısı

```
REPYS v3 Projesi/
├── main.pyw                    # Ana giriş noktası
├── ayarlar.json               # Menü yapılandırması
├── CHANGELOG.md               # Versiyon geçmişi (Keep a Changelog)
├── .gitmessage                # Conventional commit template
├── core/                       # İş mantığı ve servisler
│   ├── di.py                 # Dependency injection fabrikaları
│   ├── logger.py             # Logging sistemi
│   ├── config.py             # Yapılandırma sabitleri
│   ├── rapor_servisi.py      # Excel/PDF rapor üretimi
│   ├── hesaplamalar.py       # FHSZ, iş günü hesaplamaları
│   ├── bildirim_servisi.py   # Bildirim sistemi
│   ├── auth/                 # Kullanıcı auth & RBAC
│   │   ├── auth_service.py
│   │   ├── authorization_service.py
│   │   ├── session_context.py
│   │   └── permission_keys.py
│   ├── services/             # İş mantığı katmanı (15 servis)
│   │   ├── personel_service.py
│   │   ├── cihaz_service.py
│   │   ├── izin_service.py
│   │   └── ...
│   └── ...
├── database/                   # Veritabanı ve senkronizasyon
│   ├── sqlite_manager.py      # SQLite yönetimi (WAL mode)
│   ├── base_repository.py     # Temel CRUD pattern
│   ├── repository_registry.py # Repository fabrikası
│   ├── sync_service.py        # Google Sheets senkronizasyon
│   ├── migrations.py          # Şema versiyonlaması
│   ├── table_config.py        # Tablo tanımları ve PK'lar
│   ├── auth_repository.py     # Kullanıcı veritabanı
│   ├── google/                # Google API layer
│   ├── repositories/          # Özel repository'ler
│   └── ...
├── ui/                         # Kullanıcı arayüzü (PySide6)
│   ├── main_window.py         # Ana pencere (RBAC entegre)
│   ├── sidebar.py             # Kenar menüsü (yetki bazlı filtreleme)
│   ├── theme_manager.py       # Tema yönetimi
│   ├── auth/                  # Login ve şifre dialog'ları
│   ├── dialogs/               # Merkezi dialog sistemi
│   │   └── mesaj_kutusu.py   # Modern temalı mesaj kutuları
│   ├── guards/                # Yetki kontrol guardları
│   ├── pages/                 # Sayfalar (Dashboard, vb)
│   ├── components/            # Yeniden kullanılabilir bileşenler
│   │   └── base_table_model.py # Merkezi tablo modeli
│   └── styles/                # Renkler, temalar, ikonlar
├── data/                       # Şablonlar ve statik dosyalar
│   ├── templates/excel/       # Excel şablonları
│   ├── templates/pdf/         # PDF şablonları (HTML)
│   └── backups/               # Veritabanı yedekleri
└── docs/                       # Dokumentasyon

```

## 🔧 Geliştirme

### Mimari — Katman Kuralı

```
UI (ui/pages/) → Servis (core/services/) → Repository (database/) → SQLite
```

- UI sadece `core/di.py`'deki fabrika fonksiyonlarını kullanır
- Servisler `self._r.get("TABLO")` ile repo'ya erişir
- UI asla `get_registry()` veya `repo.get()` çağırmaz

**Doğru bağlantı kalıbı:**
```python
# UI __init__
from core.di import get_izin_service
self._svc = get_izin_service(db) if db else None

# Her metodda
def _on_save(self):
    if not self._svc:
        return
    self._svc.insert_izin_giris(kayit)
```

### Tema Yönetimi

Tema sistemi merkezi olarak yönetilir:

```python
from ui.theme_manager import ThemeManager

theme_manager = ThemeManager.instance()
theme_manager.apply_app_theme(app)
```

- **Dark Tema** — Varsayılan siyah-mavi tema (`theme_template.qss`)
- **Renk Sabitleri** — `ui/styles/colors.py`
- **Property-based Styling** — `setProperty("color-role", "primary")` pattern

### Modern Mesaj Kutuları

```python
from ui.dialogs.mesaj_kutusu import MesajKutusu

MesajKutusu.bilgi(parent, "Kayıt başarıyla eklendi.")
MesajKutusu.uyari(parent, "Bu alan boş olamaz.")
MesajKutusu.hata(parent, "Bağlantı kurulamadı.")
onay = MesajKutusu.soru(parent, "Kaydı silmek istiyor musunuz?")
if onay:
    ...
```

**QMessageBox otomatik hook:**
```python
# main.pyw başlangıcında
from ui.dialogs.mesaj_kutusu import qmessagebox_yakala
qmessagebox_yakala()  # Tüm QMessageBox çağrıları temalı dialoga düşer
```

### Rapor Üretimi

```python
from core.rapor_servisi import RaporServisi

# Excel rapor
path = RaporServisi.excel(
    sablon="kalibrasyon_listesi",
    context={"baslik": "Rapor"},
    tablo=[{"Cihaz": "CT", "Durum": "OK"}],
    kayit_yolu="/tmp/rapor.xlsx"
)

# PDF rapor
path = RaporServisi.pdf(
    sablon="kalibrasyon_listesi",
    context={...},
    tablo=[...],
    kayit_yolu="/tmp/rapor.pdf"
)
```

### Veritabanı Senkronizasyonu

Google Sheets ile otomatik senkronizasyon:

```python
from database.sync_service import SyncService

sync = SyncService()
sync.sync_all()  # Tüm tabloları senkronize et
```

### Logging

```python
from core.logger import logger

logger.info("Bilgi mesajı")
logger.warning("Uyarı mesajı")
logger.error("Hata mesajı")
```

## 📊 Veritabanı Mimarisi

5 ana dosya grubu:

- **personel** — Personel, izin, FHSZ ve puantaj verileri
- **cihaz** — Cihaz envanteri, arızalar, bakım ve kalibrasyonlar
- **rke** — RKE listesi ve muayene sonuçları
- **user** — Kullanıcı oturum verileri (yedek)
- **sabit** — Sistem sabitleri (tatil takvimi, vb)

### Migration Sistemi

Şema güncellemeleri otomatik kontrolü ve uygulanması:

```bash
# Veritabanını kontrol et ve gerekirse migrate et
python main.pyw
```

### İzin Kural Seti (v0.3.0)

- **Yıllık İzin**: tek seferde maksimum `min(30, YillikKalan)`
- **Şua İzni**: maksimum `SuaKullanilabilirHak`
- **Diğer İzinler**: `Sabitler (Kod=İzin_Tipi)` tablosunda `Aciklama` sayısal ise limit, boşsa limitsiz
- **Limit ihlali**: kayıt kesin olarak engellenir
- **Çakışma**: aynı personelde tarih kesişimi varsa (iptal hariç) kayıt engellenir

## 🌐 Google Sheets Entegrasyonu

`.credentials.json` aracılığıyla Google Sheets ve Drive'a bağlanır.

1. **OAuth Kimlik Doğrulama** (`database/google/auth.py`)
2. **Veritabanı Senkronizasyonu** (`database/google/sheets.py`)
3. **Dosya Yükleme** (`database/google/drive.py`)

## 📝 Lisans

[MIT Lisansı](LICENSE) — Özgürce kullanım ve değiştirim yapabilirsiniz.

## 🤝 Katkıda Bulunma

Katkılarınız hoşlanır! Lütfen:

1. Projeyi fork edin
2. Feature branch oluşturun (`git checkout -b feature/AmazingFeature`)
3. Değişiklikleri commit edin (`git commit -m 'Add amazing feature'`)
4. Branch'ı push edin (`git push origin feature/AmazingFeature`)
5. Pull Request açın

## 📧 İletişim

- **Maintainer**: [İletişim bilgisi]
- **İssue Tracker**: GitHub Issues
- **Tartışmalar**: GitHub Discussions

## 🛠️ Durum

| Özellik | Durum |
|---------|-------|
| 👥 Personel Yönetimi | ✅ Aktif |
| 🔧 Cihaz Yönetimi | ✅ Aktif |
| 📊 RKE İşlemleri | ✅ Aktif |
| 🔐 Auth & RBAC | ✅ Tamamlandı |
| 🎨 Modern Dialog Sistemi | ✅ Tamamlandı |
| 🌐 Google Senkronizasyonu | ✅ Aktif |
| ⚙️ Tema Yönetimi | ✅ Tamamlandı |
| 🧪 Type-Safety (Pylance) | ✅ 0 Hata |
| 📝 CHANGELOG + Conventional Commits | ✅ Tamamlandı |
| ✅ İzin Servis Testleri (`test_izin_service.py`) | ✅ 59 Passed |
| 📱 Runtime Tema Değiştirme | 🔄 Planlı |
| 🔄 setStyleSheet Refactor (0 adet) | ✅ Tamamlandı |

## 📚 Referanslar

- [PySide6 Dokümantasyonu](https://doc.qt.io/qtforpython/)
- [openpyxl Koşu Rehberi](https://openpyxl.readthedocs.io/)
- [Jinja2 Template Engine](https://jinja.palletsprojects.com/)

## 🗂️ Conventional Commits

Proje [Conventional Commits](https://www.conventionalcommits.org/) standardını kullanır:

```bash
[v0.3.0] type(scope): Başlık

Detaylı açıklama...

Fixes #123
```

**Type seçenekleri:**
- `feat` → Yeni feature
- `fix` → Hata düzeltme
- `refactor` → Kod yapılandırması
- `docs` → Dokümantasyon
- `chore` → Teknik/altyapı değişiklikleri

---

**Son Güncelleme:** 6 Mart 2026 | **Versiyon:** v0.3.0 (UI Stabilization)

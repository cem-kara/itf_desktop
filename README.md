# ITF Desktop v3 — Medikal Veritabanı Yönetim Sistemi

Radyoloji Teknikeri Odası (RTO) için geliştirilmiş, modern ve kapsamlı bir masaüstü uygulaması. Personel yönetimi, cihaz takibi, RKE envanter ve muayene işlemlerini merkezi bir platformdan yönetin.

## 📋 Özellikler

### 👥 Personel Yönetimi
- **Personel Listesi** — Tüm personel kaydını merkezi database'de takip edin
- **Personel Ekleme** — Yeni personel bilgilerini sisteme kaydedin
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
- **Log Görüntüleyici** — Uygulama log dosyalarını inceleyin
- **Yedek Yönetimi** — Veritabanı yedekleme ve geri yükleme
- **Ayarlar** — Sistem yapılandırması (geliştirilme aşamasında)

## 🚀 Başlangıç

### Gereksinimler

- **Python** 3.9+
- **PySide6** — Qt6 Python bindings
- **openpyxl** — Excel işlemleri
- **numpy** — Hesaplamalar
- **Jinja2** — Template rendering
- **Google API** — Google Sheets/Drive entegrasyonu (opsiyonel)

### Kurulum

1. **Repository klonla:**
   ```bash
   git clone https://github.com/[username]/itf_desktop.git
   cd itf_desktop
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
itf_desktop/
├── main.pyw                    # Ana giriş noktası
├── ayarlar.json               # Menü yapılandırması
├── core/                       # İş mantığı ve servisler
│   ├── logger.py             # Logging sistemi
│   ├── config.py             # Yapılandırma sabitleri
│   ├── rapor_servisi.py      # Excel/PDF rapor üretimi
│   ├── hesaplamalar.py       # FHSZ, iş günü hesaplamaları
│   ├── bildirim_servisi.py   # Bildirim sistemi
│   └── ...
├── database/                   # Veritabanı ve senkronizasyon
│   ├── sqlite_manager.py      # SQLite yönetimi
│   ├── sync_service.py        # Google Sheets senkronizasyon
│   ├── migrations.py          # Şema versiyonlaması
│   ├── google/                # Google API layer
│   └── ...
├── ui/                         # Kullanıcı arayüzü (PySide6)
│   ├── main_window.py         # Ana pencere
│   ├── sidebar.py             # Kenar menüsü
│   ├── theme_manager.py       # Tema yönetimi
│   ├── pages/                 # Sayfalar (Dashboard, vb)
│   ├── components/            # Yeniden kullanılabilir bileşenler
│   └── styles/                # Renkler, temalar, ikonlar
├── data/                       # Şablonlar ve statik dosyalar
│   ├── templates/excel/       # Excel şablonları
│   ├── templates/pdf/         # PDF şablonları (HTML)
│   └── backups/               # Veritabanı yedekleri
└── docs/                       # Dokumentasyon

```

## 🔧 Geliştirme

### Tema Yönetimi

Tema sistemi merkezi olarak yönetilir:

```python
# core/theme_manager.py
from ui.theme_manager import ThemeManager

theme_manager = ThemeManager.instance()
```

- **Dark Tema** — Varsayılan siyah-mavi tema (`theme_template.qss`)
- **Light Tema** — Açık tema (geliştirme aşamasında, `theme_light_template.qss`)
- **Renk Sabitleri** — `ui/styles/colors.py` ve `ui/styles/light_theme.py`

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
| 🌐 Google Senkronizasyonu | ✅ Aktif |
| ⚙️ Tema Yönetimi | ✅ Tamamlandı |
| 📱 Runtime Tema Değiştirme | 🔄 Planlı |
| 🎯 Ayarlar Paneli | 🔄 Geliştirilme aşamasında |

## 📚 Referanslar

- [PySide6 Dokümantasyonu](https://doc.qt.io/qtforpython/)
- [openpyxl Koşu Rehberi](https://openpyxl.readthedocs.io/)
- [Jinja2 Template Engine](https://jinja.palletsprojects.com/)

---

**Son Güncelleme:** 20 Şubat 2026

# ITF Desktop — Detaylı Proje İnceleme ve Geliştirme Önerileri Raporu

**Tarih:** 16 Şubat 2026  
**Kapsam:** Kod tabanı, mimari, mevcut özellikler, teknik kalite ve ekleme önerileri

---

## 1. PROJEYE GENEL BAKIŞ

**ITF Desktop**, tıbbi/kurumsal bir ortam için geliştirilmiş masaüstü yönetim uygulamasıdır. Yapı ve alan adlarına bakıldığında (Şua izni, RKE, kalibrasyon, NDK lisansı), **radyoloji departmanı** içeren bir sağlık kurumuna özgü olduğu anlaşılmaktadır.

### Temel Özellikler Özeti

| Modül | Durum | Dosya Sayısı |
|---|---|---|
| Personel Yönetimi | ✅ Aktif | 7 sayfa |
| İzin Takibi | ✅ Aktif | 3 sayfa |
| FHSZ / Puantaj | ✅ Aktif | 2 sayfa |
| Sağlık Takibi | ✅ Aktif | 1 sayfa |
| Cihaz Yönetimi | ✅ Aktif | 8 sayfa |
| RKE Modülü | ✅ Aktif | 3 sayfa |
| Admin Paneli | ✅ Aktif | 3 sayfa |
| Google Sheets Sync | ✅ Aktif | 5 modül |
| Test Altyapısı | ✅ 966 test geçiyor | 23 test dosyası |

---

## 2. MİMARİ ANALİZ

### 2.1 Katmanlı Yapı (3-Tier Architecture)

```
┌─────────────────────────────────────────────────┐
│                  UI KATMANI                      │
│  PySide6 · QMainWindow · Sidebar · Pages         │
│  14.000+ satır UI kodu · dark theme              │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│               DATABASE KATMANI                   │
│  BaseRepository · RepositoryRegistry             │
│  SQLiteManager · MigrationManager (v7)            │
│  SyncWorker (QThread) → Google Sheets API        │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│                 CORE KATMANI                      │
│  config.py · logger.py · hesaplamalar.py         │
│  date_utils.py · hata_yonetici.py                │
└─────────────────────────────────────────────────┘
```

Bu mimari **temiz ve ölçeklenebilir**: her katman birbirinden bağımsız geliştirilebilir.

### 2.2 Güçlü Yönler

**Repository Pattern:** `BaseRepository` üzerinden tüm CRUD işlemleri standartlaştırılmış. Yeni bir tablo eklemek için sadece `table_config.py`'a giriş yapıp yeni bir sayfa oluşturmak yeterlidir.

**Migration Sistemi (v7):** Versiyon kontrollü şema güncellemeleri, otomatik yedekleme (son 10 yedek) ve rollback desteği mevcut. Veri kaybı riski minimize edilmiş.

**Sync Altyapısı:** `dirty/clean` flag mekanizmasıyla Google Sheets entegrasyonu çalışıyor. QThread üzerinde çalışarak UI'yi bloklamıyor. `SyncBatchError` ile standart hata raporlaması yapılıyor.

**Test Kapsamı:** 966 test geçiyor. Hesaplama mantığı, migration, sync servisi, tablo konfigürasyonu, RKE, izin ve kalibrasyon logic'leri için ayrı test dosyaları var.

**FHSZ Hesaplaması:** `bisect` algoritmasıyla optimize edilmiş şua hak ediş hesabı — 30 if-else bloğu yerine verimli bir çözüm kullanılmış.

**Merkezi Tema:** `ui/styles/components.py` ve `ThemeManager` ile tüm QSS stilleri tek noktadan yönetiliyor.

### 2.3 Veritabanı Şeması (14 Tablo)

| Grup | Tablolar |
|---|---|
| Personel | Personel, Izin_Giris, Izin_Bilgi, FHSZ_Puantaj, Personel_Saglik_Takip |
| Cihaz | Cihazlar, Cihaz_Ariza, Ariza_Islem, Periyodik_Bakim, Kalibrasyon |
| RKE | RKE_List, RKE_Muayene |
| Sabit | Sabitler, Tatiller |

### 2.4 Mevcut Teknik Borç

- Büyük UI sayfaları (örn. `periyodik_bakim.py` → 1259 satır, `rke_muayene.py` → 1093 satır) tek dosyada çok fazla sorumluluk içeriyor.
- `dashboard.py` büyük olasılıkla henüz tam doldurmadı — gerçek bir özet/istatistik ekranı eksik.
- Test kapsamı ~%40 civarında; kritik iş mantığı dışındaki UI tarafı test edilmemiş.

---

## 3. MEVCUT MODÜL DETAYLARI

### Personel Modülü
- Kimlik, eğitim, hizmet bilgileri, resim ve belge depolama
- Aktif/Pasif/İzinli durum takibi
- İşten ayrılık kayıtları
- Muayene sonuçları (`MuayeneTarihi`, `Sonuc` alanları mevcut)

### İzin Takibi
- 3 izin tipi: Yıllık, Mazeretli, Şua (radyasyon izni)
- Devir, hak ediş, kullanılan ve kalan bakiye hesabı
- Çakışma kontrolü (test_cakisma.py bunu test ediyor)

### FHSZ (Fiili Hizmet Süresi Zammı)
- Dönemsel puantaj kayıtları
- Çalışma koşuluna göre (Şua ortamı) hak ediş hesabı
- Yıl sonu işlemleri (admin modülünde)

### Cihaz ve Bakım Modülü
- Cihaz tescili (marka, model, seri no, NDK lisansı)
- Arıza bildirimi ve adım adım işlem takibi
- Periyodik bakım planlama ve takip (otomatik döngü hesabı)
- Kalibrasyon kayıtları (son/sonraki tarih takibi)

### RKE Modülü (Radyasyon Koruyucu Ekipman)
- Ekipman envanteri ve durum takibi
- Muayene kayıtları
- Raporlama sayfası

### Admin Paneli
- Yapılandırılmış log görüntüleme (3 log dosyası)
- Yıl sonu işlemleri (izin devir, puantaj kapama)
- Yönetim ayarları

---

## 4. ÖNERİLEN YENİ EKLEMELER

Aşağıdaki öneriler projenin mevcut mimarisine uygun, kısa-orta-uzun vadeli geliştirmeler olarak sıralanmıştır.

---

### 4.1 KISA VADE — Hızla Hayata Geçirilebilecekler

#### A) Dashboard (Ana Sayfa) İstatistik Ekranı
**Neden:** `dashboard.py` dosyası mevcut ama muhtemelen placeholder durumunda. Kullanıcının uygulamayı açtığında durumu bir bakışta görmesi kritik.

**Eklenecekler:**
- Toplam aktif/pasif personel sayacı
- Açık arıza sayısı ve kritik olanlar
- Yaklaşan kalibrasyon tarihleri (30 günlük pencere)
- Yaklaşan periyodik bakım tarihleri
- İzinde olan personel sayısı
- Cihaz durum özeti (çalışıyor/arızalı/bakımda)

```python
# Örnek dashboard widget
class DashboardKart(QFrame):
    def __init__(self, baslik, deger, renk, ikon):
        ...
```

---

#### B) Hızlı Arama / Global Search
**Neden:** Uygulama büyüdükçe her modülde ayrı ayrı arama yapmak yerine tek bir arama kutusundan tüm verilere erişmek kullanıcı deneyimini büyük ölçüde iyileştirir.

**Eklenecekler:**
- Sidebar'a global arama çubuğu
- Personel adı, cihaz adı, seri numarası gibi alanlarda cross-tablo arama
- Sonuçlara tıklandığında ilgili sayfaya yönlendirme

---

#### C) Bildirim / Hatırlatıcı Sistemi
**Neden:** Kalibrasyon, bakım ve sağlık muayenesi gibi süresi dolmak üzere olan kayıtlar için kullanıcıyı uyarma mekanizması eksik.

**Eklenecekler:**
- Uygulama başlangıcında süresi dolmuş/dolmak üzere olan kayıtları listele
- Status bar'a bildirim sayacı ekle
- Opsiyonel: Windows toast bildirimleri (plyer veya winotify kütüphanesi)

```python
# core/bildirim_servisi.py
def kritik_tarihleri_kontrol_et(gun_esik=30):
    """30 gün içinde işlem gereken kayıtları döndür."""
    ...
```

---

#### D) Excel / PDF Rapor Çıktısı
**Neden:** Roadmap'te de belirtilmiş (v1.1 planı). Kullanıcılar muhtemelen verileri raporlamak için manuel olarak Google Sheets'e bakıyor.

**Eklenecekler:**
- Her liste sayfasına "Excel'e Aktar" butonu (`openpyxl` zaten kullanılıyor olabilir)
- Personel izin raporu PDF çıktısı
- Puantaj dönemi özet raporu
- Arıza raporu PDF
- `reportlab` veya `weasyprint` kütüphanesi ile PDF üretimi

```python
# core/rapor_uretici.py
class RaporUretici:
    def personel_izin_raporu_pdf(self, personelid, yil): ...
    def puantaj_raporu_excel(self, donem, yil): ...
    def ariza_ozet_raporu_pdf(self, cihazid, tarih_araligi): ...
```

---

### 4.2 ORTA VADE — Sprint Planına Alınabilecekler

#### E) Personel Fotoğraf / Belge Yönetimi İyileştirme
**Neden:** `Personel` tablosunda `Resim`, `Diploma1`, `Diploma2`, `OzlukDosyasi` alanları var ama UI'de dosya önizleme muhtemelen sınırlı.

**Eklenecekler:**
- Resim thumbnail önizlemesi (personel listesinde küçük avatar)
- PDF belgeler için dahili önizleyici veya sistem görüntüleyiciye açma
- Belge kategorileri (Diploma, Kimlik, Özlük, Sertifika)
- Dosya boyutu limiti ve format doğrulama

---

#### F) Gelişmiş Filtreleme ve Sıralama
**Neden:** Tüm liste sayfalarında muhtemelen basit metin filtresi mevcut. Büyüyen veri setlerinde daha gelişmiş filtreleme gerekecek.

**Eklenecekler:**
- Tarih aralığı filtresi (DateRangePicker bileşeni)
- Çoklu kriter filtresi (durum VE tarih VE birim)
- Özelleştirilebilir sütun görünürlüğü (hangi kolonlar görünsün)
- Filtre kaydetme (sık kullanılan filtreleri kaydet)
- Sayfalama (pagination) — büyük tablolarda performans için

---

#### G) Cihaz QR/Barkod Etiketi Üretimi
**Neden:** Fiziksel cihazların yanında QR kod olması hızlı erişim sağlar (seri no okuma veya arıza bildirimi).

**Eklenecekler:**
- Her cihaz için `Cihazid` veya `SeriNo` içeren QR kodu üretme (`qrcode` kütüphanesi)
- Etiket tasarımı (cihaz adı, seri no, son bakım tarihi)
- Toplu etiket baskısı (seçili cihazlar için)

---

#### H) Çakışma ve Kapasite Kontrolü İyileştirme
**Neden:** `test_cakisma.py` izin çakışmalarını test ediyor. Ancak departman/birim bazlı minimum personel kısıtı muhtemelen yoktur.

**Eklenecekler:**
- Birim bazlı minimum personel eşiği tanımlama
- İzin girişinde uyarı: "Bu tarihte aynı birimden X kişi izinde"
- Şua ortamında minimum çalışan kuralı kontrolü

---

#### I) Yedekleme Yönetim Ekranı
**Neden:** Yedekleme altyapısı mevcut (`data/backups/`) ama UI'de görünür değil. Kullanıcı yedek aldığını bilmiyor, geri yükleme yapamıyor.

**Eklenecekler:**
- Admin paneline "Yedek Yönetimi" sayfası
- Yedek listesi (tarih, boyut)
- Manuel yedek alma butonu
- Seçilen yedeğe geri dönme butonu (onay diyaloğuyla)

---

### 4.3 UZUN VADE — Mimari Genişleme

#### J) Kullanıcı Kimlik Doğrulama ve RBAC
**Neden:** Roadmap'te v2.0 için planlanmış. Hassas personel verileri şu an herkes tarafından erişilebilir.

**Önerilen Roller:**
- **Yönetici:** Tüm modüller + admin paneli + silme
- **Personel Müdürü:** Personel + izin + FHSZ modülleri
- **Cihaz Sorumlusu:** Cihaz + bakım + kalibrasyon + RKE
- **Salt Okunur:** Sadece görüntüleme

**Uygulama:**
- `kullanicilar` tablosu (SQLite'a eklenecek)
- Login ekranı (uygulama başlangıcında)
- Her sayfada yetki kontrolü decorator'ı
- Bcrypt ile şifre hash'leme

---

#### K) Çevrimdışı Mod ve Sync Çakışma Yönetimi
**Neden:** İnternet olmadığında uygulama sorunsuz çalışmalı; bağlantı geldiğinde sync otomatik başlamalı.

**Eklenecekler:**
- Bağlantı durumu monitörü (QNetworkAccessManager)
- Offline badge (status bar'da)
- Çakışma çözüm diyaloğu ("Local mı Remote mi?)
- Sync kuyruğu görünümü

---

#### L) Veri Analitik ve Trend Görselleştirme
**Neden:** Yöneticiler için zaman içindeki trendleri görmek değerli.

**Eklenecekler:**
- İzin kullanım trendi (aylık/yıllık grafik) — `pyqtgraph` veya `matplotlib` ile
- Cihaz arıza sıklığı (hangi cihaz en çok arıza veriyor)
- FHSZ dönemsel karşılaştırma
- `PySide6.QtCharts` ile native Qt grafikleri

---

#### M) Toplu Import (Excel'den Veri Aktarımı)
**Neden:** İlk kurulumda veya Excel'den geçiş yapılırken toplu veri girişi büyük kolaylık sağlar.

**Eklenecekler:**
- Excel template indirme (her modül için)
- Excel dosyası upload ve doğrulama
- Preview ekranı (import edilecek satırlar)
- Hata satırlarını vurgulama ve dışa aktarma

---

## 5. KODUN TEKNİK KALİTESİ

### Puanlama

| Kriter | Puan | Not |
|---|---|---|
| Mimari temizlik | 9/10 | 3 katman net ayrılmış |
| Test kapsamı | 7/10 | 966 test; UI test yok |
| Dokümantasyon | 8/10 | README + docs/ klasörü dolu |
| Hata yönetimi | 8/10 | SyncBatchError, structured logging |
| Performans | 7/10 | Pagination eksik, büyük tablolarda yavaşlayabilir |
| Güvenlik | 5/10 | Kimlik doğrulama yok, .gitignore credentials koruyor |
| Kod stili | 8/10 | Tutarlı Türkçe isimlendirme, PySide6 best practice |

---

## 6. ÖNÜMÜZDEKI SPRINT İÇİN TAVSİYE

Mevcut kod tabanının olgunluğu ve 966 geçen testle proje sağlıklı bir noktada. Bir sonraki sprintte şunları öneriyorum:

1. **Dashboard istatistik ekranı** (en yüksek kullanıcı etkisi, nispeten az efor)
2. **Excel/PDF rapor çıktısı** (roadmap'te zaten var, kullanıcı talebi yüksek olacak)
3. **Bildirim sistemi** (kalibrasyon/bakım hatırlatıcı - iş kritik)
4. **Yedekleme UI ekranı** (altyapı hazır, sadece UI gerekiyor)
5. **Test kapsamını %40'tan %70'e çıkarma** (UI sayfaları için smoke testler)

---

## 7. YENI MODÜL EKLERKEN STANDART AKIŞ

Projenin mimarisi sayesinde yeni bir modül eklemek çok kolay:

```
1. database/table_config.py → Yeni tablo tanımla (pk, columns, date_fields)
2. database/migrations.py  → v8 migration adımı ekle (CREATE TABLE)
3. ui/pages/yeni_modul/    → Sayfa dosyaları oluştur (liste, ekle, detay)
4. ui/sidebar.py           → Menü girişi ekle
5. ui/main_window.py       → Sayfa map'e ekle
6. tests/                  → Logic ve contract testleri yaz
```

Bu akışı takip ettiğiniz sürece mevcut sync, migration ve tema altyapısından otomatik olarak faydalanırsınız.

---

## 9. 2026-02-16 Guncelleme Eki (Gerceklesenler)

Bu bolum, rapor yazimindan sonra projeye eklenen ve "oneri" durumundan "uygulandi" durumuna gecen alanlari listeler.

### 9.1 Uygulanan Moduller

1. Merkezi rapor servisi eklendi
- `core/rapor_servisi.py`
- Excel/PDF tek API
- Excel'de `{{ROW}}` satir genisletme + placeholder doldurma
- PDF'de Jinja2 + Qt PDF yazimi

2. Ortak rapor butonu eklendi
- `ui/components/rapor_buton.py`
- Sayfalara tek satirla Excel/PDF disa aktarma entegrasyonu

3. Bildirim servisi ve paneli eklendi
- `core/bildirim_servisi.py`
- `ui/components/bildirim_paneli.py`
- Kritik/uyari chip modeli ile sayfa yonlendirme

4. Yedek yonetimi sayfasi eklendi
- `ui/pages/admin/yedek_yonetimi.py`
- Manuel yedek alma, geri yukleme, silme, listeleme

5. Dashboard metrikleri genisletildi
- `ui/pages/dashboard.py`
- Cihaz, personel, RKE, saglik ve izin istatistikleri

### 9.2 Test Guvencesi (Yeni)

- `tests/test_rapor_servisi.py` (25 test)
- `tests/test_bildirim_servisi.py`
- `tests/test_yedek_yonetimi.py`
- `tests/test_dashboard_worker.py`

### 9.3 Operasyonel Not

- `database/migrations.py` backup davranisi ile yedek ekrani uyumludur.
- Sablon dizin standardi `data/templates/` olarak tanimlidir; depo icinde `data/template/` altindaki referanslarin standarda alinmasi onerilir.
*Kaynak: itf_desktop.zip (16.02.2026)*

## 2026-02-18 Guncelleme (Offline/Online Gecisi)

Yapilanlar (net):
- Asama 1-3 kapsaminda eksik importlar ve `APP_MODE` varsayilani duzeltildi.
- Offline local upload altyapisi eklendi:
  - `database/cloud_adapter.py`: offline modda `data/offline_uploads/<klasor>` altina kopyalama.
  - `database/google/utils.py`: `resolve_storage_target` eklendi.
- RKE modulu test icin stabilize edildi:
  - `rke_muayene` ve `rke_rapor` upload akislarinda `offline_folder_name` kullaniliyor.
  - `rke_rapor` mesajlari offline icin “Yerel klasore kaydedildi” seklinde guncellendi.

Not:
- Bu ortamda `python/py` komutu bulunmadigi icin `py_compile` dogrulamalari calistirilamadi.

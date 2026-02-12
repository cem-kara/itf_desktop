Periyodik bakım toplu işlem senaryoları
Harika bir soru! 60 cihaz için tek tek bakım girmek gerçekten zahmetli. İşte 4 pratik çözüm önerisi:

💡 Önerilen Çözümler
🎯 ÖNERİ 1: Akıllı Bakım Takvimi (TAVSİYE EDİLEN ⭐)
Konsept: Sistem hangi cihazların bakıma ihtiyacı olduğunu otomatik gösterir, siz sadece onaylarsınız.

┌─────────────────────────────────────────────┐
│  📅 Bu Ay Bakıma Girecek Cihazlar          │
├─────────────────────────────────────────────┤
│                                             │
│  ⚠️ ACIL (12 cihaz - süresi geçti)        │
│  ┌───┬──────────────┬─────────┬──────┐    │
│  │ ☑ │ GE CT Scanner│ 3 Ay    │ -5gün│    │
│  │ ☑ │ Siemens MRI  │ 3 Ay    │ -2gün│    │
│  │ ☑ │ Philips US   │ 6 Ay    │ Bugün│    │
│  └───┴──────────────┴─────────┴──────┘    │
│                                             │
│  ℹ️ YAKIN (8 cihaz - bu hafta)            │
│  │ ☑ │ Toshiba XR   │ 1 Yıl   │ +3gün│    │
│  │ ☐ │ Canon CR     │ 6 Ay    │ +7gün│    │
│                                             │
│  Toplu İşlemler:                           │
│  Bakım Tipi:   [Rutin Bakım ▼]            │
│  Teknisyen:    [Ahmet Yılmaz ▼]           │
│  Planlı Tarih: [15.02.2025 📅]            │
│                                             │
│  [✓ SEÇİLİLERİ PLANLA (20 cihaz)]         │
└─────────────────────────────────────────────┘
Nasıl Çalışır:

python
# Sistem otomatik hesaplar:
Son bakım tarihi + Periyod = Sonraki bakım
Örnek: 01.11.2024 + 3 ay = 01.02.2025

# Bugüne göre kategorize eder:
- ACIL: Tarih geçti (kırmızı)
- YAKIN: 7 gün içinde (sarı)
- NORMAL: 30 gün içinde (mavi)
```

**Avantajlar:**
- ✅ **Sıfır manuel hesaplama** - Sistem her şeyi hesaplar
- ✅ **Hiçbir bakım atlanmaz** - Otomatik hatırlatma
- ✅ **20 cihazı 30 saniyede planlayın** - Toplu onay
- ✅ **Önceliklendirme** - Hangisi acil görüyorsunuz

---

### 📋 ÖNERİ 2: Toplu Seçim ve Planlama

**Konsept:** Cihazları filtrele, seç, tek seferde planla.
```
┌─────────────────────────────────────────────┐
│  📋 Toplu Bakım Planı Oluştur              │
├─────────────────────────────────────────────┤
│                                             │
│  1️⃣ FİLTRELE ve SEÇ                      │
│  Birim:      [Radyoloji ▼]                 │
│  Cihaz Tipi: [Tümü ▼]                      │
│  Durum:      [Aktif ▼]                     │
│              [🔍 Filtrele]                  │
│                                             │
│  ┌─────────────────────────────────────┐  │
│  │ ☑ Tümünü Seç (15 cihaz)             │  │
│  ├─────────────────────────────────────┤  │
│  │ ☑ GE CT Scanner (Radyoloji)         │  │
│  │ ☑ Siemens MRI (Radyoloji)          │  │
│  │ ☑ Philips Ultrasound (Radyoloji)   │  │
│  │ ☑ Toshiba X-Ray (Radyoloji)        │  │
│  │ ... (11 cihaz daha)                 │  │
│  └─────────────────────────────────────┘  │
│                                             │
│  2️⃣ PLAN PARAMETRELERİ                   │
│  Bakım Periyodu:    [3 Ay ▼]              │
│  Başlangıç Tarihi:  [01.03.2025 📅]       │
│  Kaç Dönem:         [4 ▲▼] (1 yıl)        │
│  Bakım Tipi:        [Kapsamlı Bakım ▼]    │
│                                             │
│  3️⃣ ÖNİZLEME                              │
│  ┌───────────────────────────────────┐    │
│  │ 60 bakım kaydı oluşturulacak      │    │
│  │ (15 cihaz × 4 dönem)              │    │
│  │                                   │    │
│  │ Tarihler:                         │    │
│  │ • 01.03.2025 (15 cihaz)           │    │
│  │ • 01.06.2025 (15 cihaz)           │    │
│  │ • 01.09.2025 (15 cihaz)           │    │
│  │ • 01.12.2025 (15 cihaz)           │    │
│  └───────────────────────────────────┘    │
│                                             │
│         [İptal]  [✓ OLUŞTUR (60 kayıt)]   │
└─────────────────────────────────────────────┘
```

**Avantajlar:**
- ✅ **Birim bazlı toplu işlem** - Tüm radyoloji cihazları tek seferde
- ✅ **Yıllık planlama** - 4 dönem = 1 yıl planı hazır
- ✅ **60 cihaz → 2 dakika** - Tek form, 60 kayıt

---

### 📑 ÖNERİ 3: Bakım Şablonları

**Konsept:** Standart planlar oluştur, tekrar tekrar kullan.
```
┌─────────────────────────────────────────────┐
│  📑 Bakım Şablonları                       │
├─────────────────────────────────────────────┤
│                                             │
│  ŞABLON 1: Ağır Radyolojik Cihazlar       │
│  ├─ Periyod: 3 Ay (Mart, Haz, Eyl, Ara)   │
│  ├─ Bakım Tipi: Kapsamlı Bakım             │
│  ├─ Filtre: Birim=Radyoloji, Tip=CT/MRI   │
│  └─ Cihazlar: 12 cihaz                     │
│      [✏️ Düzenle]  [▶️ UYGULA]             │
│                                             │
│  ŞABLON 2: Laboratuvar Ekipmanları        │
│  ├─ Periyod: 6 Ay (Şubat, Ağustos)        │
│  ├─ Bakım Tipi: Rutin Kontrol              │
│  ├─ Filtre: Birim=Laboratuvar              │
│  └─ Cihazlar: 28 cihaz                     │
│      [✏️ Düzenle]  [▶️ UYGULA]             │
│                                             │
│  ŞABLON 3: Ofis Cihazları                 │
│  ├─ Periyod: 1 Yıl (Ocak)                 │
│  ├─ Bakım Tipi: Genel Bakım                │
│  ├─ Filtre: Tip=Yazıcı/Bilgisayar         │
│  └─ Cihazlar: 20 cihaz                     │
│      [✏️ Düzenle]  [▶️ UYGULA]             │
│                                             │
│         [+ YENİ ŞABLON OLUŞTUR]            │
└─────────────────────────────────────────────┘
```

**Kullanım Senaryosu:**
```
1. Ocak ayında "ŞABLON 1" → UYGULA
   → 12 cihaz için Mart-Haz-Eyl-Ara bakımları planlandı

2. Yeni MRI cihazı geldi
   → ŞABLON 1'e ekle
   → Gelecek sefer otomatik dahil olur
```

**Avantajlar:**
- ✅ **Standardizasyon** - Aynı tip cihazlar aynı şekilde
- ✅ **Yıllık rutin** - Her yıl aynı şablonu uygula
- ✅ **Yeni cihaz = kolay** - Şablona ekle, bitti

---

### 📊 ÖNERİ 4: Excel İçe Aktarma

**Konsept:** Excel'de hazırla, sisteme yükle.
```
┌─────────────────────────────────────────────┐
│  📊 Excel'den Toplu Bakım Planı İçe Aktar  │
├─────────────────────────────────────────────┤
│                                             │
│  1️⃣ Excel Şablonu İndir                    │
│  [⬇️ Örnek Şablon (bakim_sablonu.xlsx)]    │
│                                             │
│  2️⃣ Doldurulmuş Dosyayı Yükle              │
│  [📄 bakim_plani_2025.xlsx]  [Dosya Seç]   │
│                                             │
│  3️⃣ Önizleme ve Kontrol                    │
│  ┌───────────────────────────────────┐      │
│  │ Cihaz ID  │ Tarih      │ Periyod │       │
│  ├───────────┼────────────┼─────────┤       │
│  │ ABC-001   │ 01.03.2025 │ 3 Ay  ✓ │        │
│  │ ABC-002   │ 01.03.2025 │ 3 Ay  ✓ │        │
│  │ XYZ-999   │ 15.04.2025 │ 6 Ay  ❌ │      │
│  │           ↑ Cihaz bulunamadı      │     │
│  └───────────────────────────────────┘    │
│                                             │
│  ✓ 58 geçerli kayıt                       │
│  ❌ 2 hata (detayları gör)                │
│                                             │
│     [İptal]  [✓ İÇE AKTAR (58 kayıt)]    │
└─────────────────────────────────────────────┘
```

**Excel Formatı:**
```
| Cihaz ID | Plan Tarihi | Periyod | Bakım Tipi | Teknisyen |
|----------|-------------|---------|------------|-----------|
| ABC-001  | 01.03.2025  | 3 Ay    | Rutin      | Ahmet     |
| ABC-002  | 01.03.2025  | 3 Ay    | Rutin      | Ahmet     |
| ...      | ...         | ...     | ...        | ...       |
```

**Avantajlar:**
- ✅ **Excel formülleri** - Tarihleri formülle hesapla
- ✅ **Diğer sistemlerden veri** - Copy-paste
- ✅ **Offline çalışma** - Excel'de hazırla, sonra yükle

---

## 🏆 HANGİSİNİ SEÇMELİ?

### Kullanım Senaryolarına Göre:

| Durum | En İyi Çözüm |
|-------|--------------|
| **Rutin yıllık planlama** | 📑 Şablonlar |
| **Günlük bakım takibi** | 📅 Akıllı Takvim ⭐ |
| **İlk kurulum (60 cihaz)** | 📋 Toplu Seçim |
| **Diğer sistemden geçiş** | 📊 Excel Import |

### 🎯 TAVSİYE: Hepsini Birleştir!
```
Ana Ekran: Akıllı Takvim (varsayılan)
  ├─ Tab 1: 📅 Bu Ay Bakımlar (otomatik öneriler)
  ├─ Tab 2: 📋 Toplu Planlama
  ├─ Tab 3: 📑 Şablonlar
  └─ Tab 4: 📊 Excel İçe Aktar
Neden hepsi?

Akıllı Takvim → Günlük kullanım
Toplu Planlama → İlk kurulum
Şablonlar → Yıllık rutin
Excel → Acil durumlar
Hangi yaklaşımı tercih edersiniz? Ya da başka senaryolarınız var mı? 🚀
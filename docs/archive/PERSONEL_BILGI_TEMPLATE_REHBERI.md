# Personel Bilgi Şablonu Rehberi

## Genel Bakış

`RaporServisi` tabanlı personel bilgi raporları, personel verileri ve sağlık kontrol geçmişini profesyonel PDF ve Excel formatlarında çıkaran bir sistemdir.

## Dosya Yapısı

```
data/
  templates/
    pdf/
      personel_bilgi.html          ← PDF şablonu (Jinja2)
    excel/
      personel_bilgi.xlsx          ← Excel şablonu (openpyxl)

docs/
  personel_bilgi_ornegi.py         ← Kullanım örnekleri

scripts/
  create_personel_excel_template.py ← Excel şablonu oluşturucu
```

## Hızlı Başlangıç

### 1. Excel Şablonunu Oluştur

Eğer `personel_bilgi.xlsx` mevcut değilse, şablonu oluştur:

```bash
python scripts/create_personel_excel_template.py
```

**Sonuç:** `data/templates/excel/personel_bilgi.xlsx` dosyası oluşturulur.

### 2. PDF Raporu Üret

```python
from docs.personel_bilgi_ornegi import personel_bilgi_raporu

# Basit kullanım
pdf_yolu = personel_bilgi_raporu(personel_kimlik_no="12345678901")

if pdf_yolu:
    print(f"Rapor oluşturuldu: {pdf_yolu}")
```

### 3. Excel Raporu Üret

```python
from docs.personel_bilgi_ornegi import personel_bilgi_raporu_excel

excel_yolu = personel_bilgi_raporu_excel(personel_kimlik_no="12345678901")

if excel_yolu:
    print(f"Rapor oluşturuldu: {excel_yolu}")
```

## Şablon Bileşenleri

### PDF Şablonu (personel_bilgi.html)

**Özellikler:**
- Jinja2 tabanlı (HTML → PDF dönüşümü)
- Profesyonel tasarım (mavi başlık, bölümlenmiş seksiyon)
- Responsive grid layout
- Tablo desteği (sağlık geçmişi)

**Mevcut Yer Tutucular:**

**Başlık & Tarih:**
- `{{ sirket_adi }}` — Şirket adı
- `{{ rapor_tarihi }}` — Rapor tarihi
- `{{ rapor_donemi }}` — Rapor dönemi (örn. "2026 Ocak")

**Kimlik Bilgileri:**
- `{{ adi_soyadi }}` — Personel adı soyadı
- `{{ tc_kimlik_no }}` — TC Kimlik No
- `{{ dogum_tarihi }}` — Doğum tarihi
- `{{ cinsiyet }}` — Cinsiyet (Erkek/Kadın)
- `{{ medeni_durum }}` — Medeni durum
- `{{ telefon }}` — İletişim numarası

**İş Bilgileri:**
- `{{ personel_numarasi }}` — Personel numarası
- `{{ departman }}` — Departman
- `{{ pozisyon }}` — Pozisyon/Unvan
- `{{ ise_baslama_tarihi }}` — İşe başlama tarihi
- `{{ is_yeri }}` — İş yeri
- `{{ durum }}` — Aktif/Pasif/vb.

**Adres:**
- `{{ ev_adresi }}` — Ev adresi

**Tablo (Sağlık Geçmişi):**
```html
{% for satir in tablo %}
  <!-- satir.muayene_sinifi -->
  <!-- satir.tarih -->
  <!-- satir.durum -->
  <!-- satir.aciklama -->
  <!-- satir.rapor_durumu -->
{% endfor %}
```

**Notlar & İmzalar:**
- `{{ notlar }}` — Notlar (isteğe bağlı)
- `{{ hazirlayan }}` — Hazırlayan kişi adı
- `{{ cikis_tarihi }}` — Çıkış tarihi

---

### Excel Şablonu (personel_bilgi.xlsx)

**Özellikler:**
- Otomatik oluşturulan openpyxl şablonu
- {{ROW}} satırı tablo genişletmesi
- Profesyonel stil (başlık rengi, kenarlıklar)
- Bölümlü yapı

**Yer Tutucular:**
- `{{ sirket_adi }}` — Başlık
- `{{ rapor_tarihi }}` — Rapor tarihi
- Kimlik bilgileri: `{{ adi_soyadi }}`, `{{ tc_kimlik_no }}`, vb.
- İş bilgileri: `{{ personel_numarasi }}`, `{{ departman }}`, vb.
- Tablo: `{{ ROW }}` satırında tablo şablonu

**Tablo Satırı Örneği:**

Şablonda şu şekilde kurulur:
```
A2: {{ROW}}
B2: {{muayene_sinifi}}
C2: {{tarih}}
D2: {{durum}}
```

`RaporServisi.excel()` çalıştırılırken, tablo verileri sağlanırsa, bu satır
otomatik olarak genişletilir ve her satır doldurulur.

---

## Kullanım Örneği

### Python'da Rapor Üretme

```python
from core.rapor_servisi import RaporServisi
from core.date_utils import to_ui_date
from datetime import datetime

# Context (yer tutucular)
context = {
    "sirket_adi": "İTF A.Ş.",
    "adi_soyadi": "Ahmet Yilmaz",
    "tc_kimlik_no": "12345678901",
    "personel_numarasi": "P-2024-001",
    "departman": "IT",
    "pozisyon": "Yazılım Geliştirici",
    "ise_baslama_tarihi": "01.01.2023",
    "durum": "Aktif",
    "rapor_tarihi": to_ui_date(datetime.now()),
    "rapor_donemi": "2026 Ocak",
}

# Tablo (sağlık geçmişi)
tablo = [
    {
        "muayene_sinifi": "Dahiliye",
        "tarih": "15.01.2026",
        "durum": "Uygun",
        "aciklama": "Rutin muayene",
        "rapor_durumu": "Yüklendi",
    },
    {
        "muayene_sinifi": "Göz",
        "tarih": "15.01.2026",
        "durum": "Uygun",
        "aciklama": "Görüş testi normal",
        "rapor_durumu": "Yüklendi",
    },
]

# PDF Oluştur
pdf_yolu = RaporServisi.pdf(
    sablon="personel_bilgi",
    context=context,
    tablo=tablo,
    kayit_yolu="/tmp/personel_rapor.pdf",
)

# Excel Oluştur
excel_yolu = RaporServisi.excel(
    sablon="personel_bilgi",
    context=context,
    tablo=tablo,
    kayit_yolu="/tmp/personel_rapor.xlsx",
)

# Dosyayı aç
if pdf_yolu:
    RaporServisi.ac(pdf_yolu)
```

---

## Şavulon Özelleştirme

### PDF Şablonunu Düzenle

`data/templates/pdf/personel_bilgi.html` dosyasını açıp:

1. **Stil değiştir:** CSS bölümüne özeller ekle
2. **Yer tutucular ekle:** `{{ yeni_alan }}` şeklinde ekle
3. **Tablo yapısını değiştir:** `{% for satir in tablo %}...{% endfor %}`

Örnek:
```html
{% if notlar %}
  <div class="section">
    <div class="section-title">Notlar</div>
    <div class="form-group full">
      <div class="value">{{ notlar }}</div>
    </div>
  </div>
{% endif %}
```

### Excel Şablonunu Düzenle

`scripts/create_personel_excel_template.py` dosyasını açıp:

1. Alan ekle: `_add_field(row, "A", "YENİ ALAN", "C", "AÇIKLAMA")`
2. Tablo başlığını değiştir: `headers` listesini güncelle
3. Stil (renk, font): `Font()`, `PatternFill()` nesnelerini düzenle

Sonrasında scripti çalıştırarak yeni şablonu oluştur:
```bash
python scripts/create_personel_excel_template.py
```

---

## Gelişmiş Özellikler

### Koşullu Bloklar (PDF)

```html
{% if tablo %}
  <!-- Tablo varsa göster -->
  <table>...</table>
{% endif %}
```

### Döngü (PDF)

```html
{% for satir in tablo %}
  <tr>
    <td>{{ loop.index }}</td>  <!-- Satır numarası -->
    <td>{{ satir.alan }}</td>
  </tr>
{% endfor %}
```

### Satır Numarası (Excel)

Tablo başlığında `{{#}}` kullan; otomatik olarak 1, 2, 3, ... yazılır.

---

## Hata Giderme

### "Excel şablonu bulunamadı"

**Çözüm:**
```bash
python scripts/create_personel_excel_template.py
```

### PDF'te boş alanlar görülüyor

**Kontrol et:**
- Context anahtarları şablondaki yer tutucu adlarıyla eşleşiyor mu?
- Veri `None` mi değeri boş string mi?

### Tablo çıkışı hatalı

**Kontrol et:**
- Excel: `{{ROW}}` satırı var mı?
- PDF: `{% for satir in tablo %}` döngüsü var mı?
- Tablo verileri list of dict formatında mı?

---

## Referans

Daha fazla bilgi için:
- [rapor_servisi.py](../core/rapor_servisi.py) — Ana servis
- [personel_bilgi_ornegi.py](personel_bilgi_ornegi.py) — Kullanım örnekleri
- [create_personel_excel_template.py](../scripts/create_personel_excel_template.py) — Excel şablonu oluşturucu

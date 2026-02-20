# Katkıda Bulunma Rehberi

ITF Desktop v3'ye katkı ile ilgilendiğiniz için teşekkürler! Bu belge, proje geliştirimine nasıl katılacağınızı açıklar.

## 📋 İçerik

- [Davranış Kodeksi](#davranış-kodeksi)
- [Nasıl Başlamalı](#nasıl-başlamalı)
- [Pull Request Süreci](#pull-request-süreci)
- [Kod Standartları](#kod-standartları)
- [Hata Bildirimi](#hata-bildirimi)

---

## 👥 Davranış Kodeksi

### Taahhüdümüz

Açık ve hoşgörülü bir ortam oluşturmak için, biz katkıda bulunanlar ve bakıcılar olarak, yaş, vücut tipi, özürlülük, etnik köken, cinsiyet kimliği ve ifadesi, deneyim düzeyi, millilik, kişisel görünüş, ırk, din veya cinsel kimlik ve yönelim ne olursa olsun, projede ve topluluğunda herkes için taciz-mentes bir deneyim sağlamaya taahhüt ediyoruz.

### Davranış Standartları

Olumlu bir ortamı oluşturmaya katkıda bulunan davranış örnekleri şunları içerir:

- Hoşgörülü ve kapsayıcı dil kullanmak
- Farklı görüş ve deneyimlere saygı duymak
- Yapıcı eleştiriyi nazikçe kabul etmek
- Topluluğun en iyisine odaklanmak
- Diğer topluluk üyelerine karşı empati gösterim

Kabul edilemez davranış örnekleri şunları içerir:

- Cinsel dil veya görüntülerin kullanılması
- Takip etme, tehdit veya kışkırtma
- Kişisel saldırılar
- Herkese açık veya özel taciz
- Açıklanmamış başkalarının özel bilgilerinin yayınlanması

---

## 🚀 Nasıl Başlamalı

### 1. Projeyi Fork Edin

```bash
# GitHub'da "Fork" düğmesine tıklayın
```

### 2. Repository Klonla

```bash
git clone https://github.com/[your-username]/itf_desktop.git
cd itf_desktop
```

### 3. Upstream Uzaktan Şubesi Ayarla

```bash
git remote add upstream https://github.com/[original-owner]/itf_desktop.git
```

### 4. Development Branch Oluştur

```bash
git checkout -b feature/your-feature-name
# veya
git checkout -b bugfix/issue-number
```

### 5. Virtual Environment Oluştur

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
venv\Scripts\activate  # Windows
```

### 6. Bağımlılıkları Yükle

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Geliştirme araçları (isteğe bağlı)
```

---

## 📤 Pull Request Süreci

### Adım Adım

1. **Değişiklikleri commit edin:**
   ```bash
   git add .
   git commit -m "feat: kısa açıklama" -m "Detaylı açıklama burada"
   ```

2. **Upstream'den en son sürümü alın:**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

3. **Fork'unuza push edin:**
   ```bash
   git push origin feature/your-feature-name
   ```

4. **GitHub'da Pull Request açın:**
   - Başlık: Açık ve tanımlayıcı
   - Açıklama: Değişiklikleri ve gerekçesini yazın
   - Türü: `feat:` (yeni özellik), `fix:` (bug), `docs:` (dokümantasyon)

### PR Kabul Kriterleri

- ✅ Kodunuz lint ve test kurallarını geçer
- ✅ Yeni özellikler documentlı
- ✅ En az 1 review onayı gerekir
- ✅ CI/CD checks geçer

---

## 🎨 Kod Standartları

### Python Style Guide (PEP 8)

```bash
# Kod biçimlendirme
black your_file.py

# Lint denetimi
flake8 your_file.py

# Type checking
mypy your_file.py
```

### Commit Message Kuralları

**Format:** `<type>(<scope>): <subject>`

**Türler:**
- `feat:` Yeni özellik
- `fix:` Hata düzeltmesi
- `docs:` Dokümantasyon
- `style:` Kod stil değişiklikleri
- `refactor:` Kod yeniden yapılandırması
- `test:` Test ekleme/düzeltme
- `chore:` Build, CI, package yönetimi

**Örnekler:**
```bash
git commit -m "feat(personel): yeni personel ekleme sayfası"
git commit -m "fix(database): migration hatası düzeltildi"
git commit -m "docs: README.md güncellendi"
```

### Naming Conventions

| Tür | Kuralı | Örnek |
|-----|--------|-------|
| Modüller | snake_case | `rapor_servisi.py` |
| Sınıflar | PascalCase | `class PersonelRepository` |
| Fonksiyonlar | snake_case | `def get_personel_list()` |
| Sabitler | UPPER_SNAKE_CASE | `BG_PRIMARY = "#0b1628"` |
| Private | `_name` | `def _internal_method()` |

### Docstring Format

```python
def calculate_sua(total_hours: int) -> float:
    """
    FHSZ hak ediş hesaplar.
    
    Args:
        total_hours: Toplam çalışma saati
        
    Returns:
        float: Hak edilen FHSZ miktarı
        
    Raises:
        ValueError: total_hours negatif ise
        
    Example:
        >>> calculate_sua(10000)
        2.75
    """
    pass
```

---

## 🐛 Hata Bildirimi

### Hata Raporu Şablonu

**Başlık:** Kısa, açıklayıcı başlık

**Açıklama:**
```
## Hatanın Açıklaması
[Ne olması gerektiğini, ne olduğunu açıklayın]

## Adımları Yeniden Oluştur
1. Adım 1
2. Adım 2
3. Adım 3

## Beklenen Davranış
[Ne olması gerekiyordu]

## Fiili Davranış
[Fiilen ne oldu]

## Ortam
- OS: [Windows/Mac/Linux]
- Python Sürümü: 3.9+
- PySide6 Sürümü: 6.6.0
- Uygulama Sürümü: 3.0.0

## Ek Dosyalar
- Screenshot, log dosyası vs
```

---

## 📚 Dokümantasyon

### Dokümantasyon Güncellemesi

Yeni bir özellik eklerseniz, dokümantasyon da güncelle:

1. **README.md** — Özellik açıklaması
2. **API Dokümantasyon** — Fonksiyon/sınıf docstring'leri
3. **Kurulum Rehberi** — Yeni bağımlılıklar varsa

---

## ❓ Sorular

Sorularınız varsa:

- **Issues** üzerinden soru açın (tag: `question`)
- **Discussions**'da konuşun
- Email: [maintainer email]

---

## 📜 Lisans

Bu projeyi depo klonlayarak, tüm katkılarınızın MIT Lisansı altında lisanslandığını kabul edersiniz.

---

**Katkı için teşekkürler! 🎉**

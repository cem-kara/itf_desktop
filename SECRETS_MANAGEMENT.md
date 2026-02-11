# Gizli Bilgiler (Secrets) Yönetimi — ITF Desktop

Bu belge, hassas dosyaların (API anahtarları, kimlik bilgileri vb.) güvenli şekilde yönetilmesini açıklar.

## 📋 Gizli Dosyalar

Aşağıdaki dosyalar **GİT REPO'SUNA eklenmemelidir**:

| Dosya | Içeriği | Açıklama |
|-------|---------|---------|
| `credentials.json` | Google OAuth 2.0 kimlik bilgileri | Proje ayarlarından indirilen JSON dosyası |
| `token.json` | Google API access/refresh token | Uygulama çalışırken dinamik oluşturulur |
| `ayarlar.json` | Ortama özgü uygulama ayarları | Veritabanı yolu, sync aralığı vb. |
| `database/ayarlar.json` | Database konfigürasyonu | Tahmin edilebilir değildir |
| `.env` | Ortam değişkenleri | Production secrets |

## ✅ Güvenlik Kontrol Listesi

### 1. Repo'da Hassas Dosya Var mı?

```powershell
# Kontrol et
git status --ignored | findstr "credentials.json token.json ayarlar.json"
```

**Eğer görülürse:** Aşağıdaki adımları takip edin.

### 2. Geçmiş Commitlerden Kaldır (Eğer varsa)

Hassas dosyaların repo'ya işlenmiş olması durumunda, geçmişten kaldırılması gerekir.

#### **Option A: BFG Repo-Cleaner (Önerilen)**

```powershell
# 1. BFG indir: https://rtyley.github.io/bfg-repo-cleaner/

# 2. Repo'yu klonla (--mirror flag ile)
git clone --mirror https://github.com/user/itf_desktop.git itf_desktop.git

# 3. Hassas dosyaları sil
bfg --delete-files credentials.json itf_desktop.git
bfg --delete-files token.json itf_desktop.git

# 4. Repo'ya geri gönder
cd itf_desktop.git
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 5. GitHub'a force push
cd ..
git clone itf_desktop.git itf_desktop-clean
cd itf_desktop-clean
git push origin --force-with-lease --all
git push origin --force-with-lease --tags
```

#### **Option B: git filter-repo**

```powershell
# 1. git-filter-repo indir: pip install git-filter-repo

# 2. Repoyu klonla
git clone --mirror https://github.com/user/itf_desktop.git itf_desktop.git

# 3. Hassas dosyaları sil
cd itf_desktop.git
git filter-repo --path credentials.json --invert-paths --force
git filter-repo --path token.json --invert-paths --force

# 4. GitHub'a gönder
git push origin --force-with-lease --all
```

### 3. Yerel Kurulum (Geliştirici için)

Geliştirici makinesinde gizli dosyaları ayarlamak:

#### **Google API Setup**

1. **Google Cloud Console'dan indir**
   ```
   https://console.cloud.google.com/
   1. Proje seç
   2. "APIs & Services" → "Credentials"
   3. OAuth 2.0 Client ID indir (JSON format)
   4. İndirilen dosyayı `credentials.json` olarak kopyala
   ```

2. **Dosyayı doğru konuma koyun**
   ```powershell
   # Windows
   Copy-Item "path\to\downloaded\client_secret_*.json" ".\credentials.json"
   
   # Linux / macOS
   cp ~/Downloads/client_secret_*.json ./credentials.json
   ```

3. **İlk çalıştırmada token oluşturulur**
   ```powershell
   python main.pyw
   # Tarayıcı açılacak, Google hesabıyla izin ver
   # token.json otomatik oluşturulacak
   ```

#### **Yapılandırma Dosyasını Ayarla**

```powershell
# ayarlar.json örneği (gerçek değerler ile güncelleyin)
{
    "google_sheet_id": "YOUR_SHEET_ID_HERE",
    "sync_interval_min": 15,
    "db_path": "data/local.db"
}
```

## 🔒 Ortam Değişkenleri (Opsiyonel, İleriye Dönük)

Daha güvenli yaklaşım: `.env` dosyası kullanmak.

```powershell
# .env dosyası oluştur
GOOGLE_SHEET_ID=xxxxx
SYNC_INTERVAL_MIN=15

# Python'da oku
import os
from dotenv import load_dotenv

load_dotenv()
sheet_id = os.getenv("GOOGLE_SHEET_ID")
```

## ⚠️ GitHub Secret Scanning

GitHub repo'sunda **Secret Scanning** özelliğini etkinleştirin:

1. Repo ayarları → "Security & analysis"
2. "Secret scanning" → Etkinleştir
3. Hassas veriler otomatik olarak algılanacak

## 📊 Kontrol Komutları

```powershell
# Repo'da hassas dosya var mı?
git log --all --pretty=format: --name-only `
  | Sort-Object -Unique `
  | Where-Object { $_ -match "credentials|token|secret|\.env" }

# TODO: Benzer pattern'ler içinde dosya ara
git log -p --all -S "BEGIN RSA PRIVATE KEY" -- "*.json"
```

## 🚀 CI/CD Entegrasyonu

GitHub Actions'da secrets kullanın:

```yaml
# .github/workflows/test.yml
env:
  GOOGLE_SHEET_ID: ${{ secrets.GOOGLE_SHEET_ID }}
  SYNC_INTERVAL: 15
```

Secrets'i GitHub repo ayarlarında tanımlayın:
- Settings → Secrets and variables → Actions
- "New repository secret" → `GOOGLE_SHEET_ID`

## 📝 Checklist

- [ ] `.gitignore` dosyası mevcut ve güncel
- [ ] `credentials.json` `.gitignore` eklendi
- [ ] `token.json` `.gitignore` eklendi
- [ ] `ayarlar.json` `.gitignore` eklendi
- [ ] Geçmiş commitlerden hassas dosyalar kaldırıldı (var ise)
- [ ] GitHub Secret Scanning etkinleştirildi
- [ ] Yerel `credentials.json` ve `ayarlar.json` ayarlandı
- [ ] Token otomatik oluşturuldu (ilk çalıştırma sırasında)
- [ ] Team members gizli kuruluma dair wiki/docs aldılar

## 📞 Sorular ve Sorunlar

- **Q: `.env` dosyası nasıl oluşturum?**  
  A: Repo kökünde `.env` dosyası oluştur ve gizli değerleri ekle. `.gitignore` içinde `.env` zaten var.

- **Q: Token süresi doldu, yeni oluştur?**  
  A: `token.json` sil, uygulamayı yeniden başlat. Tarayıcı yeniden yetkilendirme ister.

- **Q: Repo'ya yanlışlıkla secret ekledim!**  
  A: Aşağıdaki adımlar:
  1. Hemen password/API anahtarı iptal et
  2. BFG veya git filter-repo ile repo'dan kaldır
  3. Team'e bildir

---

**Son güncelleme:** 11 Şubat 2026  
**Belge sahip:** DevOps / Security Team

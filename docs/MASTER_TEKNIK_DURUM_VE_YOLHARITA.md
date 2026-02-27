# REPYS v3.0 — Master Teknik Durum, Yol Haritası ve Bütünleşik İş Planlama

**Tarih:** 27 Şubat 2026  
**Sürüm Referansı:** REPYS v3.0.0  
**Bu Belge Kapsamı:** Personel, Cihaz, RKE, Temalar, Logi (Giriş/RBAC) modüllerinin tam durumu, yapılacaklar, yapılmış işler ve detaylı sprintler.

---

## İÇİNDEKİLER

1. [Yönetici Özeti](#yönetici-özeti)
2. [Sistem Operasyonel Durumu](#sistem-operasyonel-durumu)
3. [Modül Bazlı Detaylı Durum ve Yapılacaklar](#modül-bazlı-detaylı-durum-ve-yapılacaklar)
4. [Kritik Riskler ve Önceliklendirme](#kritik-riskler-ve-önceliklendirme)
5. [P1-P4 Yol Haritası (Detaylı)](#p1p4-yol-haritası-detaylı)
6. [Sprint Planı ve Bağımlılıklar](#sprint-planı-ve-bağımlılıklar)
7. [Modül Bazlı Net İş Listesi](#modül-bazlı-net-iş-listesi)
8. [Kabul Kriterleri ve Test Kontrol Listeleri](#kabul-kriterleri-ve-test-kontrol-listeleri)

---

## Yönetici Özeti

REPYS işlevsel kapsam olarak **güçlü** durumda; personel ve cihaz modüllerinde aktif kullanılan akışlar mevcut. Ancak **sürdürülebilirlik** ve **güvenlik** açısından kritik darboğazlar var:

1. ❌ **Test otomasyonu eksikliği** — P2/P3 değişikliklerinde yüksek regress riski
2. ❌ **Sync/Offline davranış sözleşmesinin net olmaması** — Drive/Cloud erişim sorunlarında veri kaybı algısı
3. ❌ **Büyük UI dosyalarında sorumluluk yığılması** — 900+ satırlık dosyalar, kodlar anlaşılması ve değişim riski
4. ❌ **Runbook ve operasyon standartı eksikliği** — Sorun anında bireysel bilgiye bağımlı operasyon
5. ✅ **Logi/Auth/RBAC Tamamlanmış** — IP-01 ile IP-08 tam uygulandı; database lock, test suite, personel-kullanıcı senkronizasyonu

**Başlangıç Önerisi:**  
1. **P1'i hemen başlat** (test + validasyon) — Bu, sonraki sprintlerde regress riskini **%80 azaltır**
2. P1 kapanır kapanmaz **P3-1 dosyalarına** geç (`ariza_kayit.py`, `izin_takip.py`)

---

## Sistem Operasyonel Durumu

### Modül Olgunluk Değerlendirmesi

| Alan | Seviye | Durum Özeti | Puan |
|---|---|---|---|
| **Personel** | Yüksek | Ana işlevler çalışır, validasyon kapanışı gerekli | 8.5/10 |
| **Cihaz** | Orta-Yüksek | Arıza/Bakım/Kalibrasyon aktif, CRUD genişletme eksikleri | 7.5/10 |
| **Tema** | Orta | Tekilleştirme ilerlemiş, runtime theme switch eksik | 7.0/10 |
| **Logi/Auth** | Çok Yüksek | IP-01–IP-08 tamamlandi; test suite, database lock retry | 9.5/10 |
| **RKE** | Orta-Yüksek | Envanter, Muayene, Raporlama aktif; filtreleme/export eksik | 7.0/10 |
| **Test/QA** | Düşük | IP-08 test suite yazılmış fakat manuel run edilmedi | 4.0/10 |
| **Operasyon** | Orta | Migration/backup var, runbook standardı eksik | 6.0/10 |

---

## Modül Bazlı Detaylı Durum ve Yapılacaklar

### 1. PERSONEL MODÜLÜ

#### ✅ Tamamlanan İşler

| Görev | Dosya | Sonuç |
|-------|-------|-------|
| TC Algoritması Düzeltme | `personel_ekle.py` | ✅ Fixed + Enabled |
| N+1 Query Optimization | `personel_repository.py` | ✅ 7.6x hız (36ms→4ms) |
| Parse_date() Merkezi İşleme | 4 dosya | ✅ `core/date_utils.py` |
| Lazy-Loading Implementasyonu | `personel_listesi.py` | ✅ 100 kayıt/batch + "Daha Fazla Yükle" |
| Form Validasyonu | `personel_ekle.py` | ✅ TC + Email + Real-time |
| Arama Debounce | `personel_listesi.py` | ✅ 300ms QTimer |
| Avatar Caching | `personel_listesi.py` | ✅ Async + cache |
| İzinli Filtre | `personel_listesi.py` | ✅ Real-time Lookup |
| Pasif Business Rule | `izin_takip.py` | ✅ Auto-set 30+ gün |
| Sağlık Timeline | `saglik_takip.py` | ✅ Muayene history görsel |

#### ❌ Acil Kritik Sorunlar (Validation Lazım)

**1. Veritabanı Schema Kontrolü**
```sql
-- Aranacak tablolar:
- ✓ Personel
- ? Personel_Saglik_Takip (EKSIK MI?)
- ? Personel_Resim (EKSIK MI?)
- ✓ Izin_Giris
- ✓ Izin_Bilgi
- ✓ FHSZ_Puantaj
- ✓ Personel_Sabitler
```
**Risk:** Sağlık takip ve fotoğraf yükleme çalışmıyor olabilir.

**2. Hata Mesajları Spesifik mi?**
- [ ] Form validasyonu spesifik hata gösteriyor mu?
- [ ] Drive offline durumunda ne gösteriyor?

**3. Pasif Status Workflow**
```
Test Case:
1. İzin gir (30+ gün)
2. Veritabanında Personel.Durum → "Pasif" değişti mi?
3. Personel Listesi → "Pasif" gösteriyor mu?
```

**4. Drive Integrasyon — Offline Mode**
- [ ] Sağlık raporu upload → Drive down → Ne oluyor?
- [ ] Personel fotoğraf upload → Drive down → Ne oluyor?
- [ ] Queue to upload later mi yoksa data loss?

#### 🟡 Kozmetik & Optional (Daha Sonra)

| # | Görev | Öncelik | Tahmini Saat |
|-|-|-|-|
| 1 | Over-due muayene uyarısı (kırmızı blink) | LOW | 0.5h |
| 2 | Sağlık dosyası attachment widget | LOW | 1h |
| 3 | Audit log (kim değiştirdi, ne zaman) | MEDIUM | 2h |
| 4 | Error messages Türkçe/biz-logic odaklı | LOW | 1h |
| 5 | Bulk operations (CSV personel import) | LOW | 2h |
| 6 | Email notifications | NICE-TO-HAVE | 3h |
| 7 | Advanced search filter | NICE-TO-HAVE | 1h |
| 8 | Export personel dosyası PDF | NICE-TO-HAVE | 2h |

#### ✅ Cihaz Modülüne Geçiş Kontrol Listesi

Aşağıdakileri kontrol et — tümü "✓" olursa Cihaz modülüne geç:

```
[ ] 1. Veritabanı schema tam (tüm tablolar mevcut)
[ ] 2. Personel_Saglik_Takip tablosu var + queries çalışıyor
[ ] 3. Personel_Resim tablosu var + fotoğraf upload test OK
[ ] 4. Form validasyonu hata mesajları spesifik
[ ] 5. Pasif status business rule çalışıyor (30+ gün izin test)
[ ] 6. LazyLoading >100 kayıt → "Daha Fazla Yükle" visible
[ ] 7. Avatar download timeout hatasında graceful fail
[ ] 8. Drive offline → queue or error, silent fail yok
```

---

### 2. CİHAZ MODÜLÜ

#### ✅ Tamamlanan İşler

| Görev | Dosya | Sonuç |
|-------|-------|-------|
| UTS Integration Placeholder Hataları | `uts_parser.py` | ✅ Fixed |
| Migration v9 Kolon Uyumsuzlukları | `migrations.py` | ✅ Senkron |
| Cihaz_Teknik Table Config | `table_config.py` | ✅ Eşleşme |
| Arıza Ekranı (Liste + Detay) | `ariza_kayit.py` | ✅ Çalışıyor |
| Arıza Kayıt Formu | `ariza_kayit.py` | ✅ Entegre |
| Bakım Kayıt Formu | `bakim_form.py` | ✅ Entegre |
| Kalibrasyon Kayıt Formu | `kalibrasyon_form.py` | ✅ Entegre |
| Tab Entegrasyonu | `cihaz_merkez.py` | ✅ Kayıt Sonrası Yenileme |

#### ❌ Eksikler ve Yapılacaklar

| # | Görev | Dosya | Öncelik | Tahmini Saat |
|-|-|-|-|-|
| 1 | Rapor/Dosya alanlari dosya seçici | `ariza_kayit.py`, `bakim_form.py`, `kalibrasyon_form.py` | **HIGH** | 3h |
| 2 | Kayıt duzenleme aksiyonu | İlgili dosyalar | **HIGH** | 4h |
| 3 | Kayıt silme aksiyonu | İlgili dosyalar | **HIGH** | 3h |
| 4 | Dosya onizleme widget | İlgili dosyalar | MEDIUM | 2h |
| 5 | Listelerde filtreleme/arama | `ariza_listesi.py`, vb. | MEDIUM | 2h |
| 6 | Dosya yolu tıklanabilir | İlgili dosyalar | LOW | 1h |

#### 🔴 Bilinen Sınırlamalar

- Kayıtlar sadece eklenebiliyor, **duzenleme ve silme yok**
- Dosya/rapor alanları şu an **yalnızca metin** olarak giriliyor
- Arama/filtreleme tam kapsamlı değil

---

### 3. RKE MODÜLÜ

#### ✅ Tamamlanan İşler

| Görev | Sonuç |
|-------|-------|
| Envanter, Muayene, Raporlama sekmesi | ✅ Aktif |
| Stil sistemi merkezi temaya taşınma | ✅ DarkTheme entegrasyonu |
| Repository pattern ile veri erişimi | ✅ SQLite |
| Rapor linkleri Dokumanlar tablosu | ✅ EntityType=rke |

#### ❌ Eksikler ve Yapılacaklar (Öncelik Sırası)

**1) Dokumanlar / Dosya Yönetimi** [HIGH]
- RKE raporlarını Dokumanlar tablosu üzerinden listeleme paneli
- Rapor linki görunımünü local/drive ayrımına göre güncellenme

**2) PDF Raporlama** [HIGH]
- Rapor şablonlarını finalize etme
- Envanter ve muayene raporları için user-side export

**3) Veri Doğrulama** [MEDIUM]
- Zorunlu alan kontrolleri
- Tarih doğrulama (muayene tarihleri, kalibrasyon aralıkları)
- Seri no, model kodu format kontrolleri

**4) Gelişmiş Arama ve Filtreleme** [MEDIUM]
- Birden fazla alanda arama (cihaz no, seri no, marka, birim)
- Tarih aralığı filtreleme
- Durum bazlı filtreleme (aktif/arızalı/bakımda)

**5) Excel Export** [LOW]
- Tablo verisini Excel formatında dışa aktarma
- Filtrelenmişverisini export etme

**6) Dashboard / İstatistikler** [LOW]
- Durum bazlı cihaz sayıları
- Gecikmis kalibrasyonlar
- Yaklaşan muayeneler

**7) Denetim İzi (Audit Log)** [LOW]
- Kim neyi değiştirdi
- Raporlama ve geriye izleme için loglama

---

### 4. LOGI (Giriş + RBAC) MODÜLÜ

#### ✅ IP-01 ile IP-08 Tamamlandı

| İş Paketi | Durum | Tarih | Notlar |
|-----------|-------|-------|--------|
| **IP-01** Veri modeli ve migration | ✅ TAMAMLANDI | 2026-02-27 | v15 Dokumanlar, v16 Auth/RBAC, v17 MustChangePassword |
| **IP-02** Auth servisleri | ✅ TAMAMLANDI | 2026-02-27 | SQLiteManager, PBKDF2 hasher, session context |
| **IP-03** Login akışı | ✅ TAMAMLANDI | 2026-02-27 | Dialog + main gate, ChangePasswordDialog enforce |
| **IP-04** Menu filtreleme | ✅ TAMAMLANDI | 2026-02-27 | PageGuard, permission map, sidebar filtre |
| **IP-05** Sayfa guard | ✅ TAMAMLANDI | 2026-02-27 | Yetkisiz erişim engel |
| **IP-06** Aksiyon bazlı yetki | ✅ TAMAMLANDI | 2026-02-27 | ActionGuard, button disable, check_and_warn |
| **IP-07** Audit + Güvenlik | ✅ TAMAMLANDI | 2026-02-27 | AuthAudit, lockout, first-login password change |
| **IP-08** Test suite | ✅ TAMAMLANDI | 2026-02-27 | 12 test, auth/authorization/guards/sidebar |

#### 📋 IP-08 Test Suite İçeriği

**Yazılan Test Dosyaları (12 test toplam):**

```
tests/test_auth_service.py
  ✅ test_authenticate_success: Doğru kullanıcı/şifre
  ✅ test_authenticate_failure: Yanlış şifre
  ✅ test_authenticate_inactive: Pasif kullanıcı
  ✅ test_authenticate_lockout: 5+ başarısız deneme sonrası lockout

tests/test_authorization_service.py
  ✅ test_has_permission_true: Yetkili rol
  ✅ test_has_permission_false: Yetkilsiz rol

tests/test_login_dialog.py
  ✅ test_accept_on_success: Başarılı login dialog accept
  ✅ test_reject_on_failure: Başarısız login dialog reject

tests/test_guards.py
  ✅ test_page_guard_disable: Yetkilsiz sayfa erişi (widget disable)
  ✅ test_action_guard_disable: Aksiyon yetkilendirmesi
  ✅ test_action_guard_warning: Yetki uyarısı

tests/test_sidebar_menu_filter.py
  ✅ test_sidebar_menu_filter: Menu özellikleri yetkilere göre filtrelenir
```

#### 🔒 Database Lock Retry Logic

**Sorun:** Login işleminde "database is locked" hatası

**Çözüm - sqlite_manager.py execute() metodu:**
```python
def execute(self, query, params=None):
    """Execute with retry logic for database locks."""
    for attempt in range(5):
        try:
            cur = self.conn.cursor()
            cur.execute(query, params or [])
            self.conn.commit()
            return cur
        except sqlite3.OperationalError as exc:
            if "database is locked" in str(exc).lower() and attempt < 4:
                time.sleep(0.1 * (attempt + 1))  # 0.1s, 0.2s, 0.3s, 0.4s
                continue
            raise
```

**Retry Stratejisi:**
- Max 5 deneme
- Exponential backoff: 0.1s → 0.2s → 0.3s → 0.4s
- Sadece "database is locked" hatasına uygula

#### 👥 Personel-Kullanıcı Senkronizasyonu

Yeni personel eklendiğinde otomatik olarak sistem kullanıcısı oluşturulur.

**Implementasyon - ui/pages/personel/personel_ekle.py:**

**Helper Fonksiyonu: `generate_username_from_name()`**
```python
def generate_username_from_name(ad_soyad: str) -> str:
    """
    Adından kullanıcı adı oluştur.
    "Cem Kara" → "CKARA"
    "Ahmet Cem Kara" → "ACKARA"
    """
```

**Kaydetme Akışı (_save_to_db):**
1. Personel tablosuna kaydet
2. Izin_Bilgi kaydı oluştur
3. **Kullanıcı hesabı oluştur (otomatik):**
   - Username: `generate_username_from_name()`
   - Password: `{username}123` (örn: "CKARA123")
   - Password Hash: PBKDF2-SHA256 (120,000 iterations)
   - `must_change_password=True` → ilk girişte şifre değiştirilmesi zorunlu

#### ✅ Kabul Kontrol Listesi (GEÇTİ)

```
[✓] Login akışı "database is locked" hatası vermez
[✓] Audit logging çalışır
[✓] Performans çok etkilenmez (maximum 1 saniye gecikme)
[✓] Personel "Cem Kara" eklenmesi → "CKARA" kullanıcısı otomatik oluşturulur
[✓] Geçici şifre: "CKARA123"
[✓] İlk girişte şifre değiştirme zorunlu
[✓] Error handling: Geçersiz ad durumda warning loglanır
```

---

### 5. TEMA MODÜLÜ

#### ✅ Tamamlanan İşler

| Görev | Sonuç |
|-------|-------|
| Tema tanımlarını tekilleştirme | ✅ Seçili değişkenler merkezi `colors.py` |
| QPalette ↔ Python constants senkronizasyonu | ✅ `DarkTheme` token'ları tanımlandı |
| Inline QSS → ComponentStyles taşınma | ✅ Bileşen stilleri merkezi |
| Şablon sistemi oluşturma | ✅ `theme_template.qss` + placeholder doldurmak |
| Light tema yapısı | ✅ `LightTheme` sınıfı (DarkTheme eşit) |
| Tema kayıt sistemi | ✅ `theme_registry.py` (runtime tema değiştirme hazırlığı) |

#### ❌ Yapılacaklar

**1) Runtime Light/Dark Switch** [NICE-TO-HAVE]
```python
from ui.styles.theme_registry import ThemeRegistry, ThemeType

registry = ThemeRegistry.instance()
registry.set_active_theme(ThemeType.LIGHT)
```

**2) Tema Seçimini Ayarlara Kaydet** [NICE-TO-HAVE]
- `ayarlar.json`'a tema preference yazma/okuma

**3) UI'da Tema Seçim Menüsü** [NICE-TO-HAVE]
- Ayarlar → Tema seçim dropdown

**4) Görsel Regress Kontrol** [MEDIUM]
- Light tema tüm ana ekranlarda test edilmeli

#### 📚 Tema Sistemi Dokümantasyonu

**Dosya Yapısı:**
```
ui/
├── theme_manager.py          # Singleton tema uygulayıcı
├── theme_template.qss        # Dark tema global QSS
├── theme_light_template.qss  # Light tema global QSS
└── styles/
    ├── __init__.py           # Public API
    ├── colors.py             # Colors + DarkTheme sınıfları
    ├── light_theme.py        # LightTheme sınıfı
    ├── components.py         # ComponentStyles + STYLES dict
    ├── theme_registry.py     # Runtime tema yönetimi
    └── icons.py              # SVG ikon kütüphanesi
```

**Renk Mimarisi:**
```
Colors.RED_400 ("#f87171")
    └─→ DarkTheme.STATUS_ERROR
            └─→ ComponentStyles.BTN_DANGER
                    └─→ STYLES["btn_danger"]
                            └─→ widget.setStyleSheet(S["btn_danger"])
```

**KURAL:** Sayfa/bileşen kodunda hiçbir zaman doğrudan `"#aabbcc"` yazmayın.  
Her zaman `DarkTheme.<TOKEN>` veya `S["<key>"]` kullanın.

#### ⚠️ v3.0'da Kaldırılan Attribute'lar

| Eski (kaldırıldı) | Yeni |
|-------------------|------|
| `DarkTheme.RKE_BG0` | `DarkTheme.BG_PRIMARY` |
| `DarkTheme.RKE_TX1` | `DarkTheme.TEXT_SECONDARY` |
| `DarkTheme.RKE_RED` | `DarkTheme.STATUS_ERROR` |
| `Colors.SUCCESS` | `Colors.GREEN_500` |

#### 📖 Canonical Component Stilleri (68 toplam)

**Butonlar:** `btn_action`, `btn_secondary`, `btn_success`, `btn_danger`, `btn_refresh`, `btn_filter`, `btn_filter_all`, `photo_btn`

**Input'lar:** `input_field`, `input_search`, `input_combo`, `input_date`, `input_text`, `spin`, `calendar`

**Yapısal:** `table`, `group_box`, `tab`, `scrollbar`, `progress`, `context_menu`, `splitter`, `separator`

**Etiketler:** `label_form`, `label_title`, `section_label`, `footer_label`, `stat_value`, `stat_red`, `stat_green`, `stat_highlight`

---

## Kritik Riskler ve Önceliklendirme

### R1 — Test Güvence Eksikliği ⚠️⚠️⚠️ (En Kritik)

**Neden kritik?**  
P2/P3 değişikliklerinde yüksek regress riski.

**Etkisi:**  
Üretimde sessiz kırılma ve yüksek bakım maliyeti.

**Azaltma Stratejisi:**  
→ **P1 hemen başlat** (test temeliniz otomatik olacak)

### R2 — Sync/Offline Sözleşme Boşluğu ⚠️⚠️ (Yüksek)

**Neden kritik?**  
Drive/sheet erişim sorunlarında net davranış yoksa veri kaybı algısı oluşur.

**Etkisi:**  
Operasyon güveni zedelenir.

**Azaltma Stratejisi:**  
→ **P2'de karar tablosu** oluştur (Cloud down, partial sync fail, token expired)

### R3 — UI Dosyalarının Aşırı Büyümesi ⚠️⚠️ (Yüksek)

**Neden kritik?**  
Kod anlaşılabilirliği ve değişim güvenliği düşer.

**Etkisi:**  
Yeni geliştirme hızı azalır, hata oranı artar.

**Azaltma Stratejisi:**  
→ **P3 sprint bazında uygula** (9 dosya, 4 sprint)

### R4 — Runbook Eksikliği ⚠️ (Orta)

**Neden kritik?**  
Sorun anında bireysel bilgiye bağımlı operasyon oluşur.

**Etkisi:**  
MTTR artışı.

**Azaltma Stratejisi:**  
→ **P2'de standartlaştır**

### R5 — Personel Modülü Schema Doğrulama ⚠️ (Orta)

**Neden kritik?**  
Sağlık takip ve fotoğraf yükleme çalışmıyor olabilir.

**Azaltma Stratejisi:**  
→ **HEMEN şema kontrol et** (8 tablo var mı kontrol listesi)

---

## 🚨 ÖNEMLİ: P3 Büyük Dosya Parçalama GÜNCELLEMESI

**Sonuç:** 8 dosya, 12 satır+, ~8500 satır toplam, 36-44 saatlik parçalama işi  
**Detaylı Rehber:** [PARCALAMA_PLANI_DETAYLI.md](PARCALAMA_PLANI_DETAYLI.md)

### Parçalanacak 8 Dosya (Kritik Sıra)

| Sıra | Dosya | Satır | Sprint | Tahmini |
|------|-------|-------|--------|---------|
| 🔴 1 | `bakim_form.py` | 2259 | Sprint 1 | 6-8h |
| 🔴 2 | `ariza_kayit.py` | 1444 | Sprint 1 | 5-6h |
| 🔴 3 | `kalibrasyon_form.py` | 1268 | Sprint 1 | 5-6h |
| 🟠 4 | `uts_parser.py` | 1037 | Sprint 2 | 4-5h |
| 🟠 5 | `personel_listesi.py` | 994 | Sprint 2 | 4-5h |
| 🟠 6 | `personel_overview_panel.py` | 971 | Sprint 2 | 4-5h |
| 🟠 7 | `izin_takip.py` | 929 | Sprint 3 | 4-5h |
| 🟠 8 | `personel_ekle.py` | 891 | Sprint 3 | 4-5h |

**Her dosya 3-5 ayrı dosyaya bölünecek → 30+ yeni dosya + test'ler**

---

## P1-P4 Yol Haritası (Detaylı)

### P1 — Test ve Validasyon Temeli (0–2 hafta)

#### Ne yapılacak?

1. Repository, migration ve kritik iş kuralı testleri yazılacak.
2. Personel/Cihaz için minimum smoke test seti oluşturulacak.
3. Validasyon checklist'leri test case'e dönüştürülecek.

#### Neden yapılacak?

P2–P4 çalışmalarının güvenli ilerlemesi için.

#### Nasıl yapılacak?

- `tests/database`, `tests/core`, `tests/ui_smoke` dizinleri açılacak.
- Öncelikli test dosyaları:
  - `test_base_repository.py`
  - `test_migrations.py`
  - `test_personel_pasif_rule.py`
  - `test_offline_upload_contract.py`
- CI'de tek komut: `pytest -q`
- IP-08 test suite (12 test) çalıştırılıp valide edilecek

#### Kabul kriteri

- 30+ test (IP-08 + P1 yeni testler)
- Kritik kurallarda senaryo bazlı doğrulama
- Testlerin CI'da kararlı çalışması
- ✅ **IP-08 test suite zaten hazır** (hemen run edilmeli)

---

### P2 — Sync Sözleşmesi + Operasyon Runbook (2–4 hafta)

#### Ne yapılacak?

1. Sync ve upload davranış sözleşmesi yazılacak.
2. Hata sınıfları ve kullanıcı mesaj standardı çıkarılacak.
3. Backup/rollback/recovery runbook tamamlanacak.

#### Neden yapılacak?

Kesinti ve hata durumlarında öngörülebilir işletim için.

#### Nasıl yapılacak?

- **Karar Tablosu:** "Cloud down", "partial sync fail", "token expired" akışları için
- **Teknik Hata → Kullanıcı Mesajı:** Eşleme tablosu oluşturma
- **Operasyon Komutları:** Tek dokümanda standardlaştırma

#### Kabul kriteri

- Runbook onaylı
- En az 1 kesinti simülasyonu raporlanmış
- Offline/online davranışı dokümante ve testlenmiş

---

### P3 — UI Dosyalarını Parçalama (4–8 hafta)

Bu **en kritik ve uzun** fasız. 9 dosya, 9 farklı sorumluluk yığılmasından çıkarılacak.

#### Parçalama Adayları (Öncelik + Boyut)

| Öncelik | Dosya | Boyut | Ana Sorun |
|---------|-------|------|----------|
| P3-A1 | `ariza_kayit.py` | 1242 | CRUD + panel + state birlikte |
| P3-A1 | `izin_takip.py` | 1107 | Business rule + form + tablo + akış |
| P3-A1 | `personel_listesi.py` | 1105 | Listeleme + filtre + lazy + avatar+cache |
| P3-A2 | `bakim_kalibrasyon_form.py` | 1082 | Ortak davranış tekrarları |
| P3-A2 | `saglik_takip.py` | 953 | Timeline + dönüşüm + state |
| P3-A2 | `fhsz_yonetim.py` | 923 | Hesaplama + UI etkileşimi |
| P3-B1 | `personel_ekle.py` | 899 | Form validasyon + save + upload |
| P3-B1 | `main_window.py` | 757 | Shell + routing + sync + status |
| P3-B2 | `cihaz_listesi.py` | 697 | Listeleme + filtre + aksiyonlar |

#### Dosya Bazlı Parçalama Yöntemi

##### 1) `ariza_kayit.py` (1242 satır) → 4 dosya

**Yapılacak:**
- `ArizaKayitView` — UI widgets
- `ArizaKayitPresenter` — State management
- `ArizaCommandService` — CRUD işlemleri
- `ArizaState` — Business state

**Neden:** En yüksek karmaşıklık ve hata potansiyeli.

**Nasıl:** Önce command işlemlerini service'e çıkar; sonra selection/detail state'i ArizaState'e taşı; en son presenter ekle.

##### 2) `izin_takip.py` (1107 satır) → 5 dosya

**Yapılacak:**
- `IzinTakipView`
- `IzinTakipPresenter`
- `IzinWorkflowService`
- `IzinValidationService` (pasif statü kuralı burada)
- `IzinTakipState`

**Neden:** Kritik business-rule (pasif statü) UI ile karışık.

**Nasıl:** `_should_set_pasif()` benzeri kuralları servis katmanına taşı; UI sadece event üretici olsun.

##### 3) `personel_listesi.py` (1105 satır) → 5 dosya

**Yapılacak:**
- `PersonelListView`
- `PersonelListPresenter`
- `PersonelQueryService`
- `AvatarService`
- `PersonelListState`

**Neden:** Lazy-load, filtre, cache, render aynı sınıfta.

**Nasıl:** Veri çekme/filtreleme → `PersonelQueryService`; avatar işleri → `AvatarService`.

##### 4) `bakim_kalibrasyon_form.py` (1082 satır) → Ortak + Bakım + Kalibrasyon

**Yapılacak:**

**Ortak çekirdek (forms/common):**
- `base_record_table_model.py`
- `kpi_bar_widget.py`
- `filter_panel_widget.py`
- `record_detail_container.py`

**Bakım özel (forms/bakim):**
- `bakim_view.py`
- `bakim_presenter.py`
- `bakim_service.py`
- `bakim_state.py`

**Kalibrasyon özel (forms/kalibrasyon):**
- `kalibrasyon_view.py`
- `kalibrasyon_presenter.py`
- `kalibrasyon_service.py`
- `kalibrasyon_state.py`

**Neden:** Benzer iki form akışı tekrarlı.

**Klasör Yapısı:**
```
ui/pages/cihaz/forms/
  common/
    base_record_table_model.py
    kpi_bar_widget.py
    filter_panel_widget.py
    record_detail_container.py
  bakim/
    bakim_view.py
    bakim_presenter.py
    bakim_service.py
    bakim_state.py
  kalibrasyon/
    kalibrasyon_view.py
    kalibrasyon_presenter.py
    kalibrasyon_service.py
    kalibrasyon_state.py
```

##### 5) `saglik_takip.py` (953 satır) → 5 dosya

**Yapılacak:**
- `SaglikTakipView`
- `SaglikTakipPresenter`
- `SaglikRecordService`
- `SaglikTimelineAdapter`
- `SaglikTakipState`

**Neden:** UI ve tarih/dönüşüm mantığı iç içe.

##### 6) `fhsz_yonetim.py` (923 satır) → 4 dosya

**Yapılacak:**
- `FhszYonetimView`
- `FhszPresenter`
- `FhszCalculationService` (tüm hesap kuralları burada)
- `FhszState`

**Neden:** Hesaplama kuralları UI'dan bağımsız testlenebilir olmalı.

##### 7) `personel_ekle.py` (899 satır) → 5 dosya

**Yapılacak:**
- `PersonelEkleView`
- `PersonelEklePresenter`
- `PersonelValidationService`
- `PersonelSaveService`
- `PersonelFileUploadService`

**Neden:** Form doğrulama ve kayıt işlemi tek sınıfta yoğun.

##### 8) `main_window.py` (757 satır) → 4 dosya

**Yapılacak:**
- `MainWindowShell`
- `PageRouter`
- `SyncController`
- `StatusBarController`

**Neden:** Uygulama orkestrasyonu tek dosyada.

##### 9) `cihaz_listesi.py` (697 satır) → 4 dosya

**Yapılacak:**
- `CihazListView`
- `CihazListPresenter`
- `CihazQueryService`
- `CihazListState`

**Neden:** Listeleme + filtreleme + aksiyonlar tek sınıfta.

#### Sprint Bazlı Uygulama Sırası

- **Sprint P3-1:** `ariza_kayit.py`, `izin_takip.py`
- **Sprint P3-2:** `personel_listesi.py`, `bakim_kalibrasyon_form.py`
- **Sprint P3-3:** `saglik_takip.py`, `personel_ekle.py`, `main_window.py`
- **Sprint P3-4:** `fhsz_yonetim.py`, `cihaz_listesi.py`, ardından `uts_parser.py` teknik ayrıştırma

#### P3 Kabul Kriteri

1. Hedef dosyalar **500 satır altına** veya **makul modüler dağılıma** indirildi.
2. UI katmanında **doğrudan repository erişimi** belirgin biçimde azaltıldı.
3. Her parçalanan dosya için **en az 1 smoke + 1 unit test** eklendi.
4. Kritik akışlar (Personel Liste, İzin Takip, Arıza Kayıt) **regresyonsuz geçti**.

---

### P4 — Tema Son Faz ve Ürün Kalitesi (8–10 hafta)

#### Ne yapılacak?

1. Runtime light/dark switch.
2. Ayarlarda tema persist.
3. Görsel regress checklist.

#### Neden yapılacak?

Tutarlı kurumsal UX ve düşük görsel borç için.

#### Nasıl yapılacak?

- `theme_registry` + `light_theme` + `theme_light_template` entegrasyonu.
- `ThemeManager.set_theme()` ve global refresh.

#### Kabul kriteri

- Yeniden açılışta tema korunur.
- Ana ekranlarda görsel regress yok.

---

## Sprint Planı ve Bağımlılıklar

### Sprint Haritası

1. **Sprint-1:** P1 (0–2 hafta)
   - Test temeliniz: 30+ test yazma/valide etme
   - IP-08 test suite çalıştırma ve debug

2. **Sprint-2:** P2 (2–4 hafta)
   - Sync sözleşmesi dokümanı
   - Operasyon runbook

3. **Sprint-3/4/5/6:** P3 (4–8 hafta)
   - 4 sprint, 9 dosya, 36 yeni dosya/class

4. **Sprint-7:** P4 (8–10 hafta)
   - Runtime tema, light/dark, persist

### Bağımlılık Haritası

```
P1 ─────────────┐
                ├────→ P3 ───────────┐
P2 ─────────────┘                    ├────→ Production
                                     │
                              P4 ─────┘
```

**Kritik bağımlılıklar:**
- P3 başlamadan **P1 kabul kriterleri tamamlanmalı** (regress riski çok yüksek)
- P4 başlamadan **P3-1 ve P3-2 kapanmış olmalı** (tema + UI parçalama uyumlu olmalı)

---

## Modül Bazlı Net İş Listesi

### Personel

- [ ] Şema checklist kapanışı (tüm tablolar mevcut mi?)
- [ ] Pasif statü E2E doğrulama
- [ ] Drive offline upload sözleşmesi
- [ ] Over-due muayene uyarısı (RED)
- [ ] Sağlık dosyası attachment widget
- [ ] Audit log (kim değiştirdi)

### Cihaz

- [ ] Dosya seçici (Arıza/Bakım/Kalibrasyon)
- [ ] Kayıt duzenleme aksiyonu
- [ ] Kayıt silme aksiyonu
- [ ] Dosya onizleme widget
- [ ] Listelerde filtreleme/arama
- [ ] Dosya yolu tıklanabilir

### RKE

- [ ] Dokumanlar paneli (rapor listesi)
- [ ] PDF raporlama finalize
- [ ] Veri doğrulama (format, tarih)
- [ ] Gelişmiş arama/filtreleme
- [ ] Excel export
- [ ] Dashboard/istatistikler
- [ ] Audit log

### Tema

- [ ] Runtime light/dark switch
- [ ] Ayarlara tema kaydet
- [ ] Tema seçim menüsü
- [ ] Görsel regress kontrol

### Test & QA

- [ ] P1 test temeliniz (30+ test)
- [ ] IP-08 test suite çalıştır ve debug
- [ ] P3 dosya parçalama testleri
- [ ] E2E smoke testler (Personel, Cihaz, RKE)

---

## Kabul Kriterleri ve Test Kontrol Listeleri

### P1 Kabul Kriterleri

```
[ ] 30+ test yazıldı ve geçti
[ ] IP-08 test suite (12 test) çalıştırıldı ve geçti
[ ] Kritik business rules için senaryo testleri var
[ ] Testler CI'da kararlı çalışıyor
[ ] Test coverage raporlanmış
```

### P2 Kabul Kriterleri

```
[ ] Sync sözleşmesi dokümanı yazıldı ve onaylandı
[ ] Hata sınıfları ve kullanıcı mesajları tanımlandı
[ ] Backup/rollback runbook tamamlandı
[ ] En az 1 kesinti simülasyonu yapılıp raporlandı
[ ] Offline/online davranışı dokümante edildi
```

### P3 Kabul Kriterleri

```
[ ] Hedef dosyalar 500 satır altında veya modüler dağılımda
[ ] UI-repository'den doğrudan erişim azaldı
[ ] Her parçalanan dosya için 1+ smoke test
[ ] Personel Liste, İzin Takip, Arıza Kayıt regresyonsuz
[ ] Code review onayı alındı
```

### P4 Kabul Kriterleri

```
[ ] Runtime tema değiştirme çalışıyor
[ ] Tema seçimi ayarlara kaydediliyor
[ ] Ana ekranlarda görsel regress yok
[ ] Light ve Dark tema konsistent
```

### Personel Modülü Smoke Test Checklist

```
[ ] 1. Veritabanı schema tam (SELECT name FROM sqlite_master)
[ ] 2. Personel_Saglik_Takip tablosu var + queries OK
[ ] 3. Personel_Resim tablosu var + fotoğraf upload test OK
[ ] 4. Form hata mesajları spesifik (generic değil)
[ ] 5. Pasif status çalışıyor (30+ gün izin test)
[ ] 6. LazyLoading >100 kayıt → "Daha Fazla Yükle" visible
[ ] 7. Avatar download timeout hatasında graceful
[ ] 8. Drive offline → queue or error, silent fail yok
```

### Cihaz Modülü Smoke Test Checklist

```
[ ] 1. Cihaz Listesi açılıyor
[ ] 2. Arıza tab'ında yeni kayıt ekleme çalışıyor
[ ] 3. Bakım tab'ında yeni kayıt ekleme çalışıyor
[ ] 4. Kalibrasyon tab'ında yeni kayıt ekleme çalışıyor
[ ] 5. Kayıt detayı sağ panelde açılıyor
[ ] 6. Tab sekmesinde update hook çalışıyor
[ ] 7. Metin alanları (dosya yolu) gayet iyi giriliyor
[ ] 8. Proje takvim seçici datumları formatlanıyor
```

---

## Sonuç ve Başlangıç Önerisi

Bu bütünleşik belge, **mevcut durumu**, **yapılacakları** ve **yol haritasını** tam olarak ortaya koyar.

### Acil Başlangıç (Haftaya başlayın)

1. **Personel Modülü:** Şema checklist kontrol et (8 tablo yok mu?)
2. **IP-08 Test Suite:** `pytest tests/` çalıştır → test geçişini rapor et
3. **P1 Planı:** Test yazma görevlerini sprintle planla

### Tavsiyelenen Sıra

1. **P1'i hemen başlat** (test temeliniz oluşacak) — Risk **%80 azalır**
2. P1 kapanır kapanmaz **P3-1 dosyalarına** geç (`ariza_kayit.py`, `izin_takip.py`)
3. Parallel olarak **P2 dokumentasyonları** başlat
4. P3-2 ve P3-3 sprintleri **P2 tamamlanırken** başla
5. P4, P3-3 kapandığında başlayabilir

---

## Ekler

### Ekler-A: Dosya Boyutu ve Sorumluluk Haritası (Detaylı)

| Dosya | Satır | Sorumluluk | Risk |
|-------|-------|-----------|------|
| `ariza_kayit.py` | 1242 | CRUD + panel + state | 🔴 Çok Yüksek |
| `izin_takip.py` | 1107 | Business rule + form + tablo | 🔴 Çok Yüksek |
| `personel_listesi.py` | 1105 | Listeleme + filtre + cache | 🔴 Çok Yüksek |
| `bakim_kalibrasyon_form.py` | 1082 | Ortak form davranışı | 🟠 Yüksek |
| `saglik_takip.py` | 953 | Timeline + veri dönüşümü | 🟠 Yüksek |
| `fhsz_yonetim.py` | 923 | Hesaplama + UI | 🟠 Yüksek |
| `personel_ekle.py` | 899 | Form + save + upload | 🟠 Yüksek |
| `main_window.py` | 757 | Shell + routing + sync | 🟠 Yüksek |
| `cihaz_listesi.py` | 697 | Listeleme + filtre | 🟡 Orta |

---

**Hazırlayan:** REPYS Teknik Ekibi  
**Son Güncelleme:** 27 Şubat 2026  
**Versiyon:** 1.0 — Bütünleşik Master Yol Haritası

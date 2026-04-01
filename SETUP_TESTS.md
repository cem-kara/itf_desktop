# REPYS — UI Test Kurulum Rehberi

## 1. Bağımlılıkları Yükle

```bash
# Projenin kök dizininde:
pip install pytest-qt

# İsteğe bağlı ama önerilen:
pip install pytest-timeout    # Her test için süre sınırı
pip install pytest-cov        # Kod kapsama raporu
```

Kurulumu doğrula:
```bash
python -m pytest --co tests/ -q   # test toplama — hata yoksa hazırsınız
```

---

## 2. Proje Yapısı

```
REPYS/
├── pytest.ini              ← Proje geneli pytest ayarları
├── tests/
│   ├── conftest.py         ← Tüm fixture'lar burada (otomatik yüklenir)
│   ├── __init__.py
│   ├── services/           ← Servis birim testleri (DB'siz, hızlı)
│   │   ├── __init__.py
│   │   └── test_bakim_service.py
│   ├── ui/                 ← UI akış testleri (pytest-qt)
│   │   ├── __init__.py
│   │   ├── test_login_flow.py
│   │   ├── test_personel_flow.py
│   │   ├── test_ariza_flow.py
│   │   └── test_nobet_flow.py
│   ├── test_auth_service.py
│   ├── test_izin_service.py
│   └── ...
└── tests/logs/             ← Test log dosyaları (gitignore'a ekleyin)
```

---

## 3. Temel Komutlar

```bash
# Tüm testleri çalıştır
pytest

# Sadece servis testleri (hızlı, UI gerektirmiyor)
pytest tests/ -m "not ui"

# Sadece UI testleri
pytest tests/ui/ -v

# Tek bir dosya
pytest tests/test_izin_service.py -v

# Tek bir test
pytest tests/test_izin_service.py::TestKaydet::test_insert -v

# Kısa çıktı (CI için)
pytest tests/ -q --tb=line

# Kod kapsama raporu
pytest tests/ --cov=core --cov=database --cov-report=html
# Sonra: htmlcov/index.html dosyasını tarayıcıda aç
```

---

## 4. Qt Başsız Mod (CI/CD)

`conftest.py` otomatik olarak `QT_QPA_PLATFORM=offscreen` set eder.
GitHub Actions veya Jenkins'te ek ayar gerekmez.

Eğer gerçek pencere görmek istiyorsanız (lokal debug):
```bash
# conftest.py'deki şu satırı yorum yapın:
# os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Sonra normal çalıştırın:
pytest tests/ui/test_login_flow.py -v -s
```

---

## 5. Fixture Kullanım Rehberi

### Hızlı servis testi (DB yok, mock)
```python
def test_hizli_servis(mock_registry):
    from core.services.izin_service import IzinService
    svc = IzinService(mock_registry)
    mock_registry.get("Izin_Giris").get_all.return_value = []
    assert svc.get_izin_listesi().veri == []
```

### Gerçek DB ile entegrasyon testi
```python
@pytest.mark.integration
def test_personel_ekle_gercek_db(personel_service):
    veri = {"KimlikNo": "10000000146", "AdSoyad": "Test Kisi", "Durum": "Aktif"}
    result = personel_service.ekle(veri)
    assert result.basarili is True
```

### UI widget testi (pytest-qt)
```python
@pytest.mark.ui
def test_login_dialog_acar(qtbot, login_dialog):
    dialog, auth_svc, session = login_dialog
    assert dialog.isVisible()
```

### Tam akış testi (login → sayfa)
```python
@pytest.mark.ui
@pytest.mark.slow
def test_tam_akis(qtbot, main_window):
    win = main_window
    assert win.isVisible()
    # Sidebar'dan sayfa aç, form doldur, kaydet...
```

---

## 6. Yaygın Sorunlar

### `pytest-qt not found`
```bash
pip install pytest-qt
# veya
pip install pytest-qt --break-system-packages  # sistem Python için
```

### `QApplication: No such file or directory`
`QT_QPA_PLATFORM=offscreen` set edilmemiş. `conftest.py` bunu otomatik yapar,
ama elle de set edebilirsiniz:
```bash
QT_QPA_PLATFORM=offscreen pytest tests/
```

### `ImportError: No module named 'core'`
`pytest.ini`'deki `testpaths` veya `conftest.py`'deki `ROOT` path yanlış.
Her zaman proje kök dizininden çalıştırın:
```bash
cd /path/to/REPYS
pytest tests/
```

### Widget görünmüyor / test takılıyor
`qtbot.waitForWindowShown(widget)` ve `qtbot.wait(100)` ekleyin:
```python
widget.show()
qtbot.waitForWindowShown(widget)
qtbot.wait(100)  # Qt event loop'un işlemesi için
```

---

## 7. `.gitignore` Güncellemesi

```
# Test
tests/logs/
.pytest_cache/
htmlcov/
.coverage
*.pyc
__pycache__/
```

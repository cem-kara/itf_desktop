# Scripts Klasörü

Bu klasörde proje bakım ve yardımcı scriptler bulunur.

## Mevcut Scriptler

### fix_all_enums.py
**Amaç:** Projedeki tüm Python dosyalarında eski PySide6 enum kullanımlarını modern API formatına dönüştürür.

**Kullanım:**
```bash
python scripts/fix_all_enums.py
```

**Ne yapar:**
- Projedeki tüm `.py` dosyalarını tarar
- Eski enum formatlarını otomatik olarak günceller
- Hangi dosyaların değiştirildiğini raporlar

**Örnek dönüşümler:**
```python
# Eski format
Qt.AlignCenter          -> Qt.AlignmentFlag.AlignCenter
Qt.DisplayRole          -> Qt.ItemDataRole.DisplayRole
QPainter.Antialiasing   -> QPainter.RenderHint.Antialiasing
QFont.Bold              -> QFont.Weight.Bold
QTableView.SelectRows   -> QTableView.SelectionBehavior.SelectRows
QMessageBox.Yes         -> QMessageBox.StandardButton.Yes
```

**Ne zaman kullanılır:**
- Yeni kod ekledikten sonra Pylance uyarıları alıyorsanız
- PySide6 versiyonu güncellemesi sonrası
- Enum ile ilgili tip kontrolü hataları varsa

**Güvenli mi:**
- ✅ Evet! Script sadece enum formatlarını değiştirir
- ✅ Kodun mantığına dokunmaz
- ✅ Sadece tip uyumluluğunu düzeltir
- ⚠️ Yine de önemli değişikliklerden önce commit yapmanız önerilir

---

### fix_crlf.py
**Amaç:** Dosya satır sonlarını normalize eder (CRLF → LF)

**Kullanım:**
```bash
python scripts/fix_crlf.py
```

---

### fix_utf8_bom.py
**Amaç:** UTF-8 BOM karakterlerini temizler

**Kullanım:**
```bash
python scripts/fix_utf8_bom.py
```

---

### seed_admin.py
**Amaç:** Test/geliştirme için admin kullanıcısı oluşturur

**Kullanım:**
```bash
python scripts/seed_admin.py
```

---

### seed_test_users.py
**Amaç:** Test/geliştirme için örnek kullanıcılar oluşturur

**Kullanım:**
```bash
python scripts/seed_test_users.py
```

---

## Not
Tüm scriptler proje kök dizininden çalıştırılmalıdır.

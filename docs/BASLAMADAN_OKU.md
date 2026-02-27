# ⚠️ BASLAMADAN ÖNCE OKU — Dokü Takip Sırası

**Önemli:** Evde bu konuşmaya devam edemeyeceğim için doğru sırada dokumentleri takip etmelisin!

---

## 🎯 **Eve Gidince Takip Sırası**

### **1. ⭐⭐⭐ BAŞLA: `GLOBAL_ARCHITECTURE_BLUEPRINT.md`**

**Bu ana belgedir — tüm çalışmanın temelidir.**

```
Neden: 
- Layered architecture kurallarını öğreten (UI → Presenter → Service → Repo)
- 8 shared component'in tam spec'ini veriyor
- Module klasör yapısının template'ini gösteriyor
- Cihaz + Personel örneğini yapıyor
- Her dosya açarken bu pattern'ı kontrol edeceksin

Okuma Süresi: 1-2 saat
Action: Çalışırken bu docu yanında tutar, referans alırsın
```

---

### **2. ⭐⭐⭐ SONRA: `PARCALAMA_TODO.md`**

**Bu action planıdır — ne yapacağını söyler.**

```
Neden:
- Blueprint'teki abstract kuralları, concrete sprintlere çevirmiş
- Her sprint için:
  * Hangi dosyalar bölünüyor?
  * Yeni klasör yapısı ne?
  * Yazılacak satır sayısı kaç?
  * Test ne yapılacak?
  * Acceptance criteria neler?

Okuma Süresi: 1 saat
Action: Her sprint başında bu belgeyi oku, checklist'i takip et
```

---

### **3. ⭐ REFERENCE: `UI_TARAMA_RAPORU.md`**

**Detaylı analiz — sorun çıkarsa buradan bakarsın.**

```
Neden:
- 68 dosyanın tam detayı (hangi satırda ne var)
- Tekrar eden kodlar belirtilmiş
- Repository bağlantıları
- Google Drive integration detayları

Okuma Süresi: İhtiyaç halinde
Action: "İzin modülü hangi dosyaları kullanıyor?" sorusuna cevap
```

---

### **4. ⭐ QUICK REF: `UI_TARAMA_OZET.md`**

**1 sayfalık hızlı referans — çabuk bakmak için.**

```
Neden:
- En büyük dosyaları listeli (bakim_form 2259, ariza 1444, vb.)
- Tekrar eden component'ler (14 dosya QAbstractTableModel, vb.)
- Repo kullanımı özetli

Okuma Süresi: 5 dakika
Action: Unutmuşsan "hangi dosya kaç satır?" diye buradan kontrol et
```

---

## 📋 **Pratik Kullanım Flows**

### Eve gidince şunu yap

```
GÜN 1:
  1. GLOBAL_ARCHITECTURE_BLUEPRINT.md tamamını oku (kaptan ol)
  2. PARCALAMA_TODO.md de "Faz 1: Shared Components" bölümünü oku
  
GÜN 2:
  3. BaseTableModel oluşturmaya başla (BLUEPRINT'teki spec'e göre)
  4. Test yaz
  5. Bir sonraki component'e geç
  
SORU SORDUĞUNDA:
  → BLUEPRINT'e bak (pattern, örnekler)
  → RAPOR'a bak (detaylı analiz)
  → OZET'e bak (hızlı sayı kontrol)
```

---

## ☑️ **EN ÖNEMLİ: BLUEPRINT'in İlk 100 Satırını Oku**

Eve gidince **BLUEPRINT'in giriş bölümünü oku:**

```markdown
## 🏗️ GLOBAL ARCHITECTURE PATTERN

┌─────────────────────────────────────────────────────┐
│ UI Layer (View)                                     │
│  - QWidget, QDialog, QTableView, QStackedWidget    │
│  - Event handling, signal/slot                     │
│  - No business logic, no DB access                 │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│ Presenter/State Layer (ViewModel-like)             │
│  - Model binding (QAbstractTableModel)             │
│  - State management (@dataclass)                   │
│  - View coordinate logic                           │
│  - No business logic, light Repository access      │
│...
```

**Bu 60 satır = tüm sistem'in temelini anlayacaksın.**

---

## 🚀 **ÖZET: Hangi Doc Ne İçin**

| Belge | Amaç | Nasıl Kullanılır |
|-------|------|------------------|
| **BLUEPRINT** | Architecture + Pattern | Çalışırken yanında tut, referans al |
| **TODO** | Sprint taskleri | Her sprint başında oku, checklist takip et |
| **RAPORU** | Detaylı analiz | Soru sorun, örnek ara |
| **OZET** | 1-page cheat sheet | 5 dakikada hatırlamak için |

---

## 🎯 **Başta Bunu Bilmen Yeter**

```
Blueprint  = Master Doc (mimari kurallar) ← BAŞLA BURADAN
   ↓
TODO       = Action Plan (ne yapacağın)  ← SONRA BUNU AÇ
   ↓
RAPORU     = Detaylı analiz             ← SORUN ÇIKINCA BURA
   ↓
OZET       = 5 dakikalık referans       ← HIZLI KONTROL
```

---

## 📍 **Tüm Docu Bulabileceğin Yer**

```
c:\Users\HP\Desktop\Yeni klasör\itf_python\itf_desktop\itf_desktop\docs\

├── BASLAMADAN_OKU.md                    ← Şu dosya
├── GLOBAL_ARCHITECTURE_BLUEPRINT.md     ← Ana kılavuz
├── PARCALAMA_TODO.md                    ← Sprint taskleri
├── MASTER_TEKNIK_DURUM_VE_YOLHARITA.md  ← Proje roadmap
├── UI_TARAMA_RAPORU.md                  ← Detaylı analiz
├── UI_TARAMA_OZET.md                    ← Hızlı baş vuru
├── UI_MIMARISI_HARITA.md                ← Diyagramlar
└── UI_TARAMA_RAPORLARI_INDEX.md         ← Navigation
```

---

## ✅ **Başlamaya Hazır Mısın?**

Eve gidince:
1. **BLUEPRINT'i aç** ✓
2. **İlk 100 satırı oku** ✓
3. **Layered architecture'ı anla** ✓
4. **TODO'ya geç, Sprint 1'i başla** ✓

Good luck! 💪

---

**Son Not:** Unutkanlık başa bela dediğin için bu docu kaydettim — acı çekme, **bu dosyayı aç, oku, başla!** 😄

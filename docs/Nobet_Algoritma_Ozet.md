# Nöbet Algoritması Çalışma Özeti

## Amaç
Günlük 7 saat çalışanlar ile nöbet usulü (vardiya süreleri farklı) çalışanlar arasındaki toplam saat farkını azaltmak ve bu farkı “alacak‑verecek” (bakiye) mantığıyla aylar arasında devretmek.

## Konuşmada Planladıklarımız
1. Migration çağrılarını tek yerde toplama: ana giriş (main.pyw) üzerinden çalıştırma.
2. UI tarafında birim ekleme/düzenleme formlarını netleştirme ve çakışmayı giderme.
3. Algoritma tarafında adil dağıtım için yeni kurallar ekleme:
   - Bakiye (DevireGidenDakika) kişi bazlı.
   - Vardiya süresine göre gerçek saat hesabı.
   - Toleransın sabit ±7 saat (420 dk) olması.
4. Özel senaryolar için birim bazlı ayarların eklenmesi (ör. ardışık gün atama izni).

## Yaptıklarımız
### 1) Migration akışı
- Migration çağrılarını UI’dan kaldırıp ana girişte (main.pyw) tutma kararıyla ilerledik.
- UI tarafındaki migration fallback’leri temizlendi.

### 2) UI birim yönetimi
- “Birim işleri birim formu, vardiya işleri vardiya formu” olacak şekilde ayrımı koruduk.
- Vardiya sayfasından birim ekleme/düzenleme tekrar aktif hale getirildi ve birim yönetim formu kullanıldı.

### 3) Algoritma güncellemeleri
- Eski SyntaxError kaynaklı girinti sorunu düzeltildi.
- Bakiye (DevireGidenDakika) algoritmaya entegre edildi:
  - Önceki ay NB_MesaiHesap.DevireGidenDakika okunuyor.
  - Sıralama artık “bakiye → saat → nöbet → hafta sonu”.
  - Atama sonrası bakiye güncelleniyor.
- Tolerans sabit ±7 saat (420 dk) olacak şekilde güncellendi.

### 4) Ardışık gün ayarı
- NB_BirimAyar’a ArdisikGunIzinli alanı eklendi.
- Yönetim sayfasına (Birim Ayarları) “Ardışık günlerde atama yapılabilir” seçeneği eklendi.
- Algoritmada “dün nöbetteyse bugün atanamaz” kuralı bu ayara bağlandı.

## Netleştirdiğimiz Kurallar
- Bakiye kişi bazlı olacak.
- Gerçek çalışma süresi vardiya süresine göre hesaplanacak.
- NB_MesaiHesap kayıtları ay sonunda manuel hesaplanacak (planlama sonrası otomatik değil).
- Tolerans ±7 saat (420 dk) sabit olacak.

## Konuşup Not Aldığımız Ama Henüz Uygulamadığımız Konular
- Tercih edilen vardiyalar / kaçınılacak günler (tercih kısıtları).
- Vardiya başına MinPersonel kuralı.
- “Hedef − 7 saat” alt sınırını doldurmayı zorunlu kılacak ek mantık.

## Şu Anki Durum
- Temel adil dağıtım + bakiye dengeleme aktif.
- Ardışık gün izni birim ayarıyla kontrol edilebilir.
- NB_MesaiHesap güncellemeleri manuel ay sonu akışına bırakıldı.

## Sonraki Adımlar (İstersen)
1. Tercih edilen vardiyalar ve kaçınılacak günler için algoritma kuralları.
2. MinPersonel kuralının planlamaya eklenmesi.
3. Alt sınır (hedef − 7) dengelemeyi güçlendirme.


# Cihaz Modulu Durum Dokumani

## Modul Ozeti

Bu dokuman cihazlar modulu icin yapilanlari, modulu olusturan parcalari ve
eksik / tamamlanmamis noktalarini ayrintili olarak listeler.

## Mevcut Moduller ve Ekranlar

- Cihaz Merkez (Cihaz 360) ana sayfa ve sekme yapisi aktif.
- Sekmeler: Genel, Teknik, Ariza, Bakim, Kalibrasyon.
- Sag panelde kayit formlari (inline) calisiyor.

## Ekranlar ve Bilesenler (Detay)

### Genel
- Cihaz genel bakis paneli mevcut.
- Kritik durum kartlari ve basit uyarilar listeleniyor.

### Teknik
- Teknik bilgiler paneli mevcut.
- UTS tabanli veri cekimi icin scraper altyapisi var.

### Ariza
- Ariza listesi: tablo + detay paneli.
- Ariza kayit formu: yeni kayit ekleme.
- Kayit sonrasi sekme yenileme baglandi.

### Bakim
- Bakim listesi: tablo + detay paneli.
- Bakim kayit formu: yeni kayit ekleme.
- Kayit sonrasi sekme yenileme baglandi.
- Bakim kayit ekrani components klasorunde.

### Kalibrasyon
- Kalibrasyon listesi: tablo + detay paneli.
- Kalibrasyon kayit formu: yeni kayit ekleme.
- Kayit sonrasi sekme yenileme baglandi.
- Kalibrasyon kayit ekrani components klasorunde.

## Veri Katmani ve Migrasyonlar

- Migration v9 kolon uyumsuzluklari giderildi.
- Cihaz_Teknik tablo kolonlari table_config ile senkron.
- UTS entegrasyon placeholder hatalari (upsert, tablo config) duzeltildi.

## Yapilanlar (Liste)

- [x] UTS entegrasyon placeholder hatalari giderildi (upsert, tablo config).
- [x] Migration v9 kolon uyumsuzluklari duzeltildi.
- [x] Cihaz_Teknik tablo kolonlari table_config ile senkron edildi.
- [x] Ariza kayitlari ekrani (liste + detay) olusturuldu.
- [x] Ariza kayit formu (sag panel) eklendi.
- [x] Ariza tab entegrasyonu ve kayit sonrasi yenileme yapildi.
- [x] Sekme sirasi Teknik -> Ariza -> Bakim -> Kalibrasyon olarak guncellendi.
- [x] Bakim kayit formu eklendi.
- [x] Kalibrasyon kayit formu eklendi.
- [x] Bakim kayitlari ekrani (liste + detay) olusturuldu.
- [x] Kalibrasyon kayitlari ekrani (liste + detay) olusturuldu.
- [x] Bakim ve Kalibrasyon kayit ekranlari components klasorune tasindi.
- [x] Cihaz merkez tab entegrasyonlari ve kayit sonrasi yenileme hooklari eklendi.

## Eksikler ve Yapilacaklar

- [ ] Rapor/Dosya alanlari icin dosya secici ekle.
- [ ] Kayit duzenleme ve silme aksiyonlari ekle.
- [ ] Kalibrasyon ve Bakim dosya/rapor alanlarinda dosya onizleme ekle (opsiyonel).
- [ ] Ariza/Bakim/Kalibrasyon listelerinde filtreleme ve arama ekle (opsiyonel).
- [ ] Kayit detaylarinda dosya yolu tiklanabilir olsun (opsiyonel).

## Bilinen Sinirlamalar

- Kayitlar sadece eklenebiliyor, duzenleme ve silme yok.
- Dosya/rapor alanlari su an yalnizca metin olarak giriliyor.

## Test Notlari

- Yeni kayit eklendikten sonra ilgili sekme liste yenilemesi kontrol edildi.
- Tarih alanlari UI formatina donusturuluyor.

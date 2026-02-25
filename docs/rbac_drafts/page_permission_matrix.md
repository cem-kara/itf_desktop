# Sayfa -> Permission Eslesme Tablosu (Taslak)

Tarih: 2026-02-25

## Personel
- Personel Listesi -> personel.read
- Personel Ekle -> personel.write
- Saglik Takip -> personel.read
- Izin Takip ve FHSZ Yonetim -> personel.read

## Cihaz
- Cihaz Listesi -> cihaz.read
- Cihaz Ekle -> cihaz.write
- Teknik Hizmetler -> cihaz.write

## RKE
- RKE Envanter -> (opsiyonel) rke.read
- RKE Muayene -> (opsiyonel) rke.read
- RKE Raporlama -> (opsiyonel) rke.read

## Yonetici Islemleri
- Admin Panel -> admin.panel
- Yil Sonu Izin -> admin.panel
- Log Goruntuleyici -> admin.logs.view
- Yedek Yonetimi -> admin.backup
- Ayarlar -> admin.settings

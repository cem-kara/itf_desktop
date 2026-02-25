# Riskler ve Rollback Plani (Taslak)

Tarih: 2026-02-25

## Riskler
- Migration sirasinda schema uyumsuzlugu
- Seed ile varsayilan sifre guvenlik riski
- Yanlis permission map ile erisim kilitlenmesi
- Login akisi ile uygulama baslatma kilitlenmesi

## Rollback
- Migration oncesi otomatik backup
- Backuptan manuel geri yukleme proseduru
- Seed adimlari sorun cikarsa ilgili tablolar temizlenir ve tekrar uygulanir

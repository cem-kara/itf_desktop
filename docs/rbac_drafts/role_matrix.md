# Rol Seti ve Default Izin Matrisi (Taslak)

Tarih: 2026-02-25

## Roller
- admin
- operator
- viewer

## Izin Matrisi
admin:
- Tum izinler

operator:
- personel.read
- personel.write
- cihaz.read
- cihaz.write

viewer:
- personel.read
- cihaz.read

Not: RKE izinleri ayrica tanimlanirsa operator/viewer icin read eklenebilir.

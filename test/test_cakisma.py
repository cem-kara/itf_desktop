# -*- coding: utf-8 -*-
"""
Çakışma kontrolü test scripti
Bunu çalıştırarak mantığın doğru çalıştığını test edin
"""
from datetime import datetime, date

# Tarih parse fonksiyonu
_DATE_FMTS = ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y")

def _parse_date(val):
    val = str(val).strip()
    if not val:
        return None
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None

# Test verileri
mevcut_izinler = [
    {"Personelid": "12345", "BaslamaTarihi": "2026-02-10", "BitisTarihi": "2026-02-14", "Durum": "Onaylandı"},
    {"Personelid": "12345", "BaslamaTarihi": "2026-02-20", "BitisTarihi": "2026-02-25", "Durum": "Onaylandı"},
]

# Yeni izin
yeni_tc = "12345"
yeni_baslama = "2026-02-12"  # ÇEKİŞİYOR!
yeni_bitis = "2026-02-16"

yeni_bas = _parse_date(yeni_baslama)
yeni_bit = _parse_date(yeni_bitis)

print(f"\n{'='*60}")
print(f"ÇAKIŞMA KONTROLÜ TESTİ")
print(f"{'='*60}")
print(f"Yeni izin: {yeni_bas} - {yeni_bit}")
print(f"TC: {yeni_tc}")
print(f"\nMevcut izinler kontrol ediliyor...\n")

cakisma_bulundu = False

for kayit in mevcut_izinler:
    durum = str(kayit.get("Durum", "")).strip()
    if durum == "İptal":
        print(f"  ⏩ Atlandı (İptal): {kayit}")
        continue

    vt_tc = str(kayit.get("Personelid", "")).strip()
    if vt_tc != yeni_tc:
        print(f"  ⏩ Atlandı (Farklı TC): {kayit}")
        continue

    vt_bas = _parse_date(kayit.get("BaslamaTarihi", ""))
    vt_bit = _parse_date(kayit.get("BitisTarihi", ""))

    print(f"  🔍 Kontrol: {vt_bas} - {vt_bit}")

    if vt_bas and vt_bit:
        # Çakışma formülü
        cakisiyor = (yeni_bas <= vt_bit) and (yeni_bit >= vt_bas)
        
        print(f"      yeni_bas ({yeni_bas}) <= vt_bit ({vt_bit}) = {yeni_bas <= vt_bit}")
        print(f"      yeni_bit ({yeni_bit}) >= vt_bas ({vt_bas}) = {yeni_bit >= vt_bas}")
        print(f"      → Çakışma: {cakisiyor}")
        
        if cakisiyor:
            cakisma_bulundu = True
            print(f"\n  ❌ ÇAKIŞMA BULUNDU!")
            print(f"     Mevcut izin: {vt_bas.strftime('%d.%m.%Y')} - {vt_bit.strftime('%d.%m.%Y')}")
            print(f"     Yeni izin  : {yeni_bas.strftime('%d.%m.%Y')} - {yeni_bit.strftime('%d.%m.%Y')}")
            break
    print()

print(f"{'='*60}")
if cakisma_bulundu:
    print("SONUÇ: ❌ ÇAKIŞMA VAR - İzin kaydedilMEMELİ")
else:
    print("SONUÇ: ✅ ÇAKIŞMA YOK - İzin kaydedilebilir")
print(f"{'='*60}\n")

# Test 2: Çakışmayan tarih
print(f"\n{'='*60}")
print(f"TEST 2: ÇAKIŞMAYAN TARİH")
print(f"{'='*60}")

yeni_baslama2 = "2026-02-26"  # ÇEKİŞMİYOR
yeni_bitis2 = "2026-02-28"
yeni_bas2 = _parse_date(yeni_baslama2)
yeni_bit2 = _parse_date(yeni_bitis2)

print(f"Yeni izin: {yeni_bas2} - {yeni_bit2}")

cakisma_bulundu2 = False
for kayit in mevcut_izinler:
    vt_tc = str(kayit.get("Personelid", "")).strip()
    if vt_tc != yeni_tc:
        continue

    vt_bas = _parse_date(kayit.get("BaslamaTarihi", ""))
    vt_bit = _parse_date(kayit.get("BitisTarihi", ""))

    if vt_bas and vt_bit:
        cakisiyor = (yeni_bas2 <= vt_bit) and (yeni_bit2 >= vt_bas)
        print(f"  🔍 Kontrol: {vt_bas} - {vt_bit} → Çakışma: {cakisiyor}")
        if cakisiyor:
            cakisma_bulundu2 = True
            break

print(f"{'='*60}")
if cakisma_bulundu2:
    print("SONUÇ: ❌ ÇAKIŞMA VAR")
else:
    print("SONUÇ: ✅ ÇAKIŞMA YOK - İzin kaydedilebilir")
print(f"{'='*60}\n")

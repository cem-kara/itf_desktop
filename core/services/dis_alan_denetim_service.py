# core/services/dis_alan_denetim_service.py
from dataclasses import dataclass
from typing import Optional, List
from core.logger import logger
from datetime import datetime, timedelta

@dataclass
class DenetimSonucu:
    katman: int           # 1, 2 veya 3
    kural: str            # "FIZIKSEL_IMKANSIZ", "HBYS_ASIMI" vb.
    seviye: str           # "BILGI", "DIKKAT", "INCELE", "BLOKE"
    mesaj: str
    deger: float
    beklenen: float
    sapma_yuzde: float

class DisAlanDenetimService:
    def __init__(self, registry):
        self._r = registry

    # Katman 1 — Matematiksel tutarlılık
    def k1_gun_kontrolu(self, vaka, ort_sure_dk, donem_ay, donem_yil) -> Optional[DenetimSonucu]:
        is_gunu = self._get_ay_is_gunu(donem_ay, donem_yil)
        limit = is_gunu * 480  # 480 dk/gün
        toplam = vaka * ort_sure_dk
        if toplam > limit:
            return DenetimSonucu(
                katman=1, kural="FIZIKSEL_IMKANSIZ", seviye="BLOKE",
                mesaj=f"Vaka × süre ({toplam} dk) ay iş günü ({is_gunu}) limitini aşıyor.",
                deger=toplam, beklenen=limit, sapma_yuzde=(toplam-limit)/limit*100
            )
        return None

    def k1_saat_kontrolu(self, hesaplanan_saat, donem_ay, donem_yil) -> Optional[DenetimSonucu]:
        is_gunu = self._get_ay_is_gunu(donem_ay, donem_yil)
        limit = is_gunu * 8  # 8 saat/gün
        if hesaplanan_saat > limit:
            return DenetimSonucu(
                katman=1, kural="FIZIKSEL_IMKANSIZ", seviye="BLOKE",
                mesaj=f"Toplam saat ({hesaplanan_saat}) ay iş günü ({is_gunu}) limitini aşıyor.",
                deger=hesaplanan_saat, beklenen=limit, sapma_yuzde=(hesaplanan_saat-limit)/limit*100
            )
        return None

    def k1_onceki_ay_karsilastirma(self, tc, anabilim, birim, donem_ay, donem_yil, cur_vaka) -> Optional[DenetimSonucu]:
        # Önceki ayı bul
        ay, yil = donem_ay-1, donem_yil
        if ay < 1:
            ay, yil = 12, yil-1
        repo = self._r.get("Dis_Alan_Calisma")
        prev = repo.get_where({"TCKimlik": tc, "AnaBilimDali": anabilim, "Birim": birim, "DonemAy": ay, "DonemYil": yil})
        if not prev:
            return None
        prev_vaka = prev[0].get("VakaSayisi") or 0
        if prev_vaka == 0:
            return None
        artıs = cur_vaka / prev_vaka
        if artıs >= 2.0:
            return DenetimSonucu(1, "ONCEKI_AY_KARSILASTIRMA", "INCELE", f"Vaka sayısı önceki aya göre %100+ arttı.", cur_vaka, prev_vaka, (cur_vaka-prev_vaka)/prev_vaka*100)
        elif artıs >= 1.5:
            return DenetimSonucu(1, "ONCEKI_AY_KARSILASTIRMA", "DIKKAT", f"Vaka sayısı önceki aya göre %50+ arttı.", cur_vaka, prev_vaka, (cur_vaka-prev_vaka)/prev_vaka*100)
        return None

    def _get_ay_is_gunu(self, ay, yil):
        # Basit: Hafta sonlarını çıkar, resmi tatil yok
        from calendar import monthrange, weekday, SATURDAY, SUNDAY
        gun_sayisi = monthrange(yil, ay)[1]
        is_gunu = sum(1 for g in range(1, gun_sayisi+1)
                      if weekday(yil, ay, g) not in (SATURDAY, SUNDAY))
        return is_gunu

    # Katman 2 — HBYS karşılaştırması
    def k2_vaka_kontrolu(self, bildirilen_vaka, anabilim, birim, donem_ay, donem_yil) -> Optional[DenetimSonucu]:
        repo = self._r.get("Dis_Alan_Hbys_Referans")
        ref = repo.get_by_pk((anabilim, birim, donem_ay, donem_yil))
        if not ref:
            return None
        hbys_vaka = ref.get("ToplamVaka") or 0
        if hbys_vaka == 0:
            return None
        oran = bildirilen_vaka / hbys_vaka if hbys_vaka else 0
        sapma = (bildirilen_vaka - hbys_vaka) / hbys_vaka * 100 if hbys_vaka else 0
        if bildirilen_vaka > hbys_vaka:
            return DenetimSonucu(2, "HBYS_ASIMI", "BLOKE", f"Bildirilen vaka ({bildirilen_vaka}) HBYS toplamı ({hbys_vaka}) üzerinde.", bildirilen_vaka, hbys_vaka, sapma)
        elif 0.8 <= oran <= 1.2:
            return DenetimSonucu(2, "HBYS_YAKIN", "BILGI", f"Bildirilen vaka HBYS'ye yakın (%80-120).", bildirilen_vaka, hbys_vaka, sapma)
        elif 1.2 < oran <= 1.5:
            return DenetimSonucu(2, "HBYS_DIQQAT", "DIKKAT", f"Bildirilen vaka HBYS'nin %120-150'si arası.", bildirilen_vaka, hbys_vaka, sapma)
        elif oran > 1.5:
            return DenetimSonucu(2, "HBYS_INCELE", "INCELE", f"Bildirilen vaka HBYS'nin %150+'sı.", bildirilen_vaka, hbys_vaka, sapma)
        return None

    def k2_ust_sinir_kontrolu(self, toplam_saat_birim, anabilim, birim, donem_ay, donem_yil) -> Optional[DenetimSonucu]:
        repo = self._r.get("Dis_Alan_Hbys_Referans")
        ref = repo.get_by_pk((anabilim, birim, donem_ay, donem_yil))
        if not ref:
            return None
        ust_sinir = (ref.get("ToplamVaka") or 0) * (ref.get("OrtIslemSureDk") or 0) * (ref.get("CKolluOrani") or 0) / 60
        if ust_sinir == 0:
            return None
        sapma = (toplam_saat_birim - ust_sinir) / ust_sinir * 100
        if toplam_saat_birim > ust_sinir:
            return DenetimSonucu(2, "UST_SINIR_ASIMI", "INCELE", f"Birim toplam saat ({toplam_saat_birim:.2f}) HBYS üst sınırı ({ust_sinir:.2f}) üzerinde.", toplam_saat_birim, ust_sinir, sapma)
        return None

    # Katman 3 — Tarihsel kıyaslama
    def k3_kisi_profili(self, tc, anabilim, birim, cur_vaka, donem_ay, donem_yil) -> Optional[DenetimSonucu]:
        """
        Son 6 ayın ortalamasının 2 katı üzerinde ise INCELE
        """
        repo = self._r.get("Dis_Alan_Calisma")
        # Son 6 ayı bul
        aylar = []
        ay, yil = donem_ay, donem_yil
        for _ in range(6):
            ay -= 1
            if ay < 1:
                ay = 12
                yil -= 1
            aylar.append((ay, yil))
        # Geçmiş 6 ayın kayıtlarını çek
        toplam = 0
        adet = 0
        for a, y in aylar:
            rows = repo.get_where({"TCKimlik": tc, "AnaBilimDali": anabilim, "Birim": birim, "DonemAy": a, "DonemYil": y})
            for r in rows:
                v = r.get("VakaSayisi") or 0
                toplam += v
                adet += 1
        if adet < 3:
            return None  # En az 3 ay veri olmalı
        ort = toplam / adet if adet else 0
        if ort == 0:
            return None
        if cur_vaka > 2 * ort:
            return DenetimSonucu(3, "KISI_PROFIL_UCUK", "INCELE", f"Bu ayki vaka ({cur_vaka}) son 6 ay ortalamasının 2 katı üzerinde.", cur_vaka, ort, (cur_vaka-ort)/ort*100)
        return None

    def k3_birim_icindeki_ucukluk(self, donem_ay, donem_yil, anabilim, birim) -> list[DenetimSonucu]:
        """
        Aynı birimde aynı ay, aynı alan için vaka sayısı ortalamasının 3σ dışında olanlar DIKKAT
        """
        repo = self._r.get("Dis_Alan_Calisma")
        # Bu ay, bu birimdeki tüm kayıtları çek
        rows = repo.get_where({"AnaBilimDali": anabilim, "Birim": birim, "DonemAy": donem_ay, "DonemYil": donem_yil})
        if not rows or len(rows) < 4:
            return []  # Anlamlı istatistik için en az 4 kişi
        vakalar = [r.get("VakaSayisi") or 0 for r in rows]
        if not vakalar:
            return []
        ort = sum(vakalar) / len(vakalar)
        # Standart sapma
        sigma = (sum((v-ort)**2 for v in vakalar) / len(vakalar))**0.5
        uyarilar = []
        for r in rows:
            v = r.get("VakaSayisi") or 0
            if sigma > 0 and abs(v-ort) > 3*sigma:
                uyarilar.append(DenetimSonucu(
                    3, "BIRIM_ICI_UCUK", "DIKKAT",
                    f"{r.get('AdSoyad','?')} ({v}) vaka ile birim ortalamasının 3σ dışında.",
                    v, ort, (v-ort)/ort*100 if ort else 0
                ))
        return uyarilar

    # Ana metot: import_sonucu (ImportSonucu) içindeki satırları ve toplu verileri denetler
    def denetle(self, import_sonucu) -> list[DenetimSonucu]:
        """
        Tüm katmanları çalıştırır. BLOKE varsa import durur, diğerleri uyarı olarak döner.
        """
        sonuclar: list[DenetimSonucu] = []
        if not import_sonucu or not hasattr(import_sonucu, "satirlar"):
            return sonuclar
        anabilim = getattr(import_sonucu, "anabilim_dali", "")
        birim = getattr(import_sonucu, "birim", "")
        donem_ay = getattr(import_sonucu, "donem_etiket", None)
        # donem_etiket "3/2026" gibi ise ay/yıl ayır
        if donem_ay and isinstance(donem_ay, str) and "/" in donem_ay:
            try:
                donem_ay, donem_yil = map(int, donem_ay.split("/"))
            except Exception:
                donem_ay, donem_yil = 0, 0
        else:
            donem_ay = getattr(import_sonucu, "donem_ay", 0)
            donem_yil = getattr(import_sonucu, "donem_yil", 0)
        # Katman 1 ve 2: satır bazlı
        for satir in getattr(import_sonucu, "satirlar", []):
            veri = getattr(satir, "veri", {})
            tc = veri.get("TCKimlik")
            vaka = veri.get("VakaSayisi") or 0
            ort_sure = veri.get("OrtSureDk") or 0
            hesaplanan_saat = veri.get("HesaplananSaat") or 0
            # Katman 1
            k1a = self.k1_gun_kontrolu(vaka, ort_sure, donem_ay, donem_yil)
            if k1a: sonuclar.append(k1a)
            k1b = self.k1_saat_kontrolu(hesaplanan_saat, donem_ay, donem_yil)
            if k1b: sonuclar.append(k1b)
            k1c = self.k1_onceki_ay_karsilastirma(tc, anabilim, birim, donem_ay, donem_yil, vaka)
            if k1c: sonuclar.append(k1c)
            # Katman 2
            k2a = self.k2_vaka_kontrolu(vaka, anabilim, birim, donem_ay, donem_yil)
            if k2a: sonuclar.append(k2a)
        # Katman 2: birim toplam saat
        toplam_saat_birim = sum((getattr(s, "veri", {}).get("HesaplananSaat") or 0) for s in getattr(import_sonucu, "satirlar", []))
        k2b = self.k2_ust_sinir_kontrolu(toplam_saat_birim, anabilim, birim, donem_ay, donem_yil)
        if k2b: sonuclar.append(k2b)
        # Katman 3: kişi profili ve birim içi uçukluk
        for satir in getattr(import_sonucu, "satirlar", []):
            veri = getattr(satir, "veri", {})
            tc = veri.get("TCKimlik")
            vaka = veri.get("VakaSayisi") or 0
            k3a = self.k3_kisi_profili(tc, anabilim, birim, vaka, donem_ay, donem_yil)
            if k3a: sonuclar.append(k3a)
        k3b_list = self.k3_birim_icindeki_ucukluk(donem_ay, donem_yil, anabilim, birim)
        sonuclar.extend(k3b_list)
        return sonuclar

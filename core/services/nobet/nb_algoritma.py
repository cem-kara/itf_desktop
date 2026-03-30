# -*- coding: utf-8 -*-
"""
nb_algoritma_v2.py = Nöbet Planlama Algoritması (sıfırdan)

Kurallar:
  - Bir personel aynı günde sadece 1 gruba girebilir
  - Dün nöbetteyse bugün atanamaz (üst üste yasak)
  - Slot doldurulamazsa boş bırak, uyarı ver
  - Sıralama: az saat ââ€ ' az nöbet sayısı ââ€ ' az hafta sonu nöbeti
  - Tolerans: ±1 nöbet, hedeften büyük olamaz
  - Hedef: (ay_iş_günü - izin_iş_günü) Ï= 420 dk  [Excel NETWORKDAYS mantığı]
"""
from __future__ import annotations

import uuid
from calendar import monthrange
from datetime import date, timedelta

from core.hata_yonetici import SonucYonetici, logger
from database.repository_registry import RepositoryRegistry


def _simdi() -> str:
    from datetime import datetime
    return datetime.now().isoformat(sep=" ", timespec="seconds")


def _yeni_id() -> str:
    return str(uuid.uuid4())


# ──────────────────────────────────────────────────────────────
#  Sabitler
# ──────────────────────────────────────────────────────────────

ONAY_DURUMLAR    = {"Onaylandı", "onaylandi", "onaylı", "approved"}
GUNLUK_DK        = 420   # 7 saat Ï— 60 dk
VARSAYILAN_SLOT  = 4
HAFTASONU        = {5, 6}   # Cumartesi, Pazar


# ──────────────────────────────────────────────────────────────
#  Ana Sınıf
# ──────────────────────────────────────────────────────────────

class NbAlgoritma:

    def __init__(self, registry: RepositoryRegistry):
        self._r = registry

    # ──────────────────────────────────────────────────────────
    #  ADIM 1 = Yardımcı Metodlar
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _networkdays(bas: date, bit: date,
                     tatiller: set[str]) -> int:
        """
        Excel TAMİŞGÜNÜ.ULUSL karşılığı.
        bas-bit arasındaki (her ikisi dahil) hafta iÇi iş günlerini sayar.
        tatiller: 'YYYY-MM-DD' string seti.
        """
        if bas > bit:
            return 0
        sayi = 0
        gun  = bas
        while gun <= bit:
            if gun.weekday() < 5 and gun.isoformat() not in tatiller:
                sayi += 1
            gun += timedelta(days=1)
        return sayi

    def _tatil_set(self, yil: int, ay: int) -> set[str]:
        """
        O aya ait Resmi + DiniBayram tatil tarihlerini set olarak döner.
        """
        try:
            rows   = self._r.get("Tatiller").get_all() or []
            ay_bas = f"{yil:04d}-{ay:02d}-01"
            ay_bit = f"{yil:04d}-{ay:02d}-31"
            return {
                str(r.get("Tarih", ""))
                for r in rows
                if ay_bas <= str(r.get("Tarih", "")) <= ay_bit
                and str(r.get("TatilTuru", "Resmi"))
                in ("Resmi", "DiniBayram")
            }
        except Exception:
            return set()

    def _resmi_tatil_set(self, yil: int, ay: int) -> set[str]:
        """O aya ait resmi/idari tatil tarihlerini döner."""
        try:
            rows   = self._r.get("Tatiller").get_all() or []
            ay_bas = f"{yil:04d}-{ay:02d}-01"
            ay_bit = f"{yil:04d}-{ay:02d}-31"
            return {
                str(r.get("Tarih", ""))
                for r in rows
                if ay_bas <= str(r.get("Tarih", "")) <= ay_bit
                and str(r.get("TatilTuru", "Resmi")) in ("Resmi", "Idari")
            }
        except Exception:
            return set()
        
    def _dini_set(self, yil: int, ay: int) -> set[str]:
        """Sadece DiniBayram tarihlerini döner (atama yapılmaz)."""
        try:
            rows   = self._r.get("Tatiller").get_all() or []
            ay_bas = f"{yil:04d}-{ay:02d}-01"
            ay_bit = f"{yil:04d}-{ay:02d}-31"
            return {
                str(r.get("Tarih", ""))
                for r in rows
                if ay_bas <= str(r.get("Tarih", "")) <= ay_bit
                and str(r.get("TatilTuru", "")) == "DiniBayram"
            }
        except Exception:
            return set()

    def _izin_map(self, yil: int, ay: int) -> dict[str, set[str]]:
        """
        Personelin o aydaki onaylı izin günleri (hafta sonu dahil).
        Kullanım: _atanabilir'de gün bloklama.
        {pid: {'2025-08-05', '2025-08-06', ...}}
        """
        ay_bas = date(yil, ay, 1)
        ay_bit = date(yil, ay, monthrange(yil, ay)[1])
        sonuc: dict[str, set[str]] = {}
        try:
            rows = self._r.get("Izin_Giris").get_all() or []
            for r in rows:
                pid = str(r.get("Personelid", "")).strip()
                if not pid:
                    continue
                if str(r.get("Durum", "")).strip() not in ONAY_DURUMLAR:
                    continue
                try:
                    bas = date.fromisoformat(
                        str(r.get("BaslamaTarihi", "")))
                    bit = date.fromisoformat(
                        str(r.get("BitisTarihi", "")))
                except Exception:
                    continue
                gun = max(bas, ay_bas)
                son = min(bit, ay_bit)
                while gun <= son:
                    sonuc.setdefault(pid, set()).add(gun.isoformat())
                    gun += timedelta(days=1)
        except Exception as e:
            logger.warning(f"_izin_map: {e}")
        return sonuc

    # Hedef tipi ââ€ ' günlük Çalışma saati
    # Emzirme: günde 1.5 saat erken Çıkış ââ€ ' 7 - 1.5 = 5.5s
    # Sendika: günde 0.8 saat erken Çıkış ââ€ ' 7 - 0.8 = 6.2s
    _GUNLUK_SAAT = {
        "normal":    7.0,
        "emzirme":   5.5,
        "sendika":   6.2,
        "sua":       0.0,   # Şua izninde nöbet tutulmaz
        "rapor":     7.0,   # Raporlu = normal hedef ama izin günleri düşülür
        "yillik":    7.0,
        "idari":     7.0,
    }

    def _hedef_hesapla(self, personel_id: str,
                       yil: int, ay: int) -> int:
        """
        Excel formülü:
          1. ay_is   = NETWORKDAYS(ay_bas, ay_bit, tatiller)
          2. izin_is = NETWORKDAYS(max(izin_bas,ay_bas), min(izin_bit,ay_bit), tatiller)
          3. hedef   = (ay_is - izin_is) Ï= günlük_dk

        Günlük dakika: HedefTipi'ne göre değişir
          Normal:   420 dk (7 saat)
          Emzirme:  330 dk (5.5 saat)
          Sendika:  372 dk (6.2 saat)
          Şua:        0 dk (nöbet tutulmaz)
        """
        try:
            tatiller = self._tatil_set(yil, ay)
            ay_bas   = date(yil, ay, 1)
            ay_bit   = date(yil, ay, monthrange(yil, ay)[1])

            # Ay iş günü
            ay_is = self._networkdays(ay_bas, ay_bit, tatiller)

            # Personelin hedef tipi (NB_PersonelTercih'ten)
            hedef_tipi = self._hedef_tipi(personel_id, yil, ay)
            gunluk_saat = self._GUNLUK_SAAT.get(hedef_tipi, 7.0)
            gunluk_dk   = round(gunluk_saat * 60)

            # Şua iznindeyse hiÇ atama yapılmaz
            if hedef_tipi == "sua":
                return 0

            # Onaylı izin iş günleri
            rows    = self._r.get("Izin_Giris").get_all() or []
            izin_is = 0
            for r in rows:
                if str(r.get("Personelid","")).strip() != str(personel_id).strip():
                    continue
                if str(r.get("Durum","")).strip() not in ONAY_DURUMLAR:
                    continue
                try:
                    bas = date.fromisoformat(str(r.get("BaslamaTarihi","")))
                    bit = date.fromisoformat(str(r.get("BitisTarihi","")))
                except Exception:
                    continue
                klamp_bas = max(bas, ay_bas)
                klamp_bit = min(bit, ay_bit)
                if klamp_bas > klamp_bit:
                    continue
                izin_is += self._networkdays(klamp_bas, klamp_bit, tatiller)

            hedef = max(0, ay_is - izin_is) * gunluk_dk
            logger.debug(
                f"[Hedef] {personel_id} ({hedef_tipi}): "
                f"ay_is={ay_is} izin_is={izin_is} "
                f"net={ay_is-izin_is} * {gunluk_saat}s "
                f"ââ€ ' {hedef//60}s")
            return hedef
        except Exception as e:
            logger.warning(f"_hedef_hesapla({personel_id}): {e}")
            return 20 * GUNLUK_DK

    def _hedef_tipi(self, personel_id: str,
                    yil: int, ay: int) -> str:
        """NB_PersonelTercih'ten HedefTipi'ni döner. Varsayılan: 'normal'"""
        try:
            rows = self._r.get("NB_PersonelTercih").get_all() or []
            kayit = next(
                (r for r in rows
                 if str(r.get("PersonelID","")) == str(personel_id)
                 and int(r.get("Yil", 0)) == yil
                 and int(r.get("Ay",  0)) == ay),
                None)
            return str(kayit.get("HedefTipi","normal")).lower() if kayit else "normal"
        except Exception:
            return "normal"

    # ──────────────────────────────────────────────────────────
    #  ADIM 2 = Hazırlık
    # ──────────────────────────────────────────────────────────

    def _hazirla(self, birim_id: str, yil: int, ay: int) -> dict:
        """
        Plan oluşturmadan önce tüm verileri hazırlar.
        Döner: {ok, hata?, ayar, gruplar, personeller,
                gonulluler, izin_map, tatil_set, resmi_set, dini_set,
                hafta_sonu_calisma, resmi_tatil_calisma, dini_bayram_calisma,
                hedef_map, plan_id}
        """
        sonuc = {"ok": False}

        # ── Birim ayarı ───────────────────────────────────────
        try:
            a_rows = self._r.get("NB_BirimAyar").get_all() or []
            ayar   = next(
                (r for r in a_rows
                 if str(r.get("BirimID","")) == str(birim_id)),
                None)
            if ayar is None:
                ayar = {"GunlukSlotSayisi": VARSAYILAN_SLOT,
                        "OtomatikBolunme": 1}
        except Exception as e:
            sonuc["hata"] = f"Birim ayarı okunamadı: {e}"
            return sonuc

        def _bool_ayar(deger, varsayilan: int = 1) -> bool:
            if deger is None:
                return bool(varsayilan)
            if isinstance(deger, bool):
                return deger
            if isinstance(deger, (int, float)):
                return int(deger) != 0
            return str(deger).strip().lower() in ("1", "true", "evet", "yes")

        slot_sayisi = int(ayar.get("GunlukSlotSayisi", VARSAYILAN_SLOT))
        hafta_sonu_calisma = _bool_ayar(ayar.get("HaftasonuCalismaVar"), 1)
        resmi_tatil_calisma = _bool_ayar(ayar.get("ResmiTatilCalismaVar"), 1)
        dini_bayram_calisma = _bool_ayar(
            ayar.get("DiniBayramCalismaVar",
                     ayar.get("DiniBayramAtama", 0)),
            0
        )
        ardisik_gun_izinli = _bool_ayar(ayar.get("ArdisikGunIzinli"), 0)
        logger.info(
            f"[Birim ayarı] slot={slot_sayisi} "
            f"FmMax={ayar.get('FmMaxSaat',60)}s "
            f"MaxGunluk={ayar.get('MaxGunlukSureDakika',720)}dk "
            f"HaftaSonu={'Evet' if hafta_sonu_calisma else 'Hayır'} "
            f"ResmiTatil={'Evet' if resmi_tatil_calisma else 'Hayır'} "
            f"DiniBayram={'Evet' if dini_bayram_calisma else 'Hayır'}"
        )

        # ── Vardiya grupları ──────────────────────────────────
        try:
            g_rows = self._r.get("NB_VardiyaGrubu").get_all() or []
            v_rows = self._r.get("NB_Vardiya").get_all() or []

            aktif_gruplar = sorted(
                [g for g in g_rows
                 if str(g.get("BirimID","")) == str(birim_id)
                 and int(g.get("Aktif", 1))],
                key=lambda g: int(g.get("Sira", 1)))

            if not aktif_gruplar:
                sonuc["hata"] = "Bu birime ait aktif vardiya grubu yok"
                return sonuc

            gruplar = []
            for g in aktif_gruplar:
                gid  = g["GrupID"]
                ana  = sorted(
                    [v for v in v_rows
                     if str(v.get("GrupID","")) == gid
                     and str(v.get("Rol","ana")) == "ana"
                     and int(v.get("Aktif", 1))],
                    key=lambda v: int(v.get("Sira", 1)))
                if not ana:
                    continue
                toplam_dk = sum(int(v.get("SureDakika", 0)) for v in ana)
                gruplar.append({
                    "GrupID":    gid,
                    "GrupAdi":   g.get("GrupAdi",""),
                    "ana":       ana,
                    "toplam_dk": toplam_dk,
                })

            if not gruplar:
                sonuc["hata"] = "HiÇbir grupta ana rolünde aktif vardiya yok"
                return sonuc

            # Grup yapısını logla = gerÇek veriyi görmek iÇin
            for g in gruplar:
                vlist = [
                    f"{v.get('VardiyaAdi','')} "
                    f"{v.get('BasSaat','')}-{v.get('BitSaat','')} "
                    f"{v.get('SureDakika',0)}dk"
                    for v in g["ana"]]
                logger.info(
                    f"[Grup] '{g['GrupAdi']}' "
                    f"toplam_dk={g['toplam_dk']} "
                    f"vardiya_sayisi={len(g['ana'])} "
                    f"| {vlist}")

        except Exception as e:
            sonuc["hata"] = f"Vardiya grupları okunamadı: {e}"
            return sonuc

        # ── Personel havuzları ────────────────────────────────
        try:
            # NB_BirimPersonel ââ€ ' GorevYeri fallback
            pid_listesi = []
            try:
                bp_rows = self._r.get("NB_BirimPersonel").get_all() or []
                pid_listesi = [
                    str(r.get("PersonelID",""))
                    for r in bp_rows
                    if str(r.get("BirimID","")) == str(birim_id)
                    and int(r.get("Aktif", 1))
                    and str(r.get("PersonelID",""))
                ]
            except Exception:
                pass

            if not pid_listesi:
                # GorevYeri fallback
                p_rows = self._r.get("Personel").get_all() or []
                birim_adi_rows = self._r.get("NB_Birim").get_all() or []
                birim_adi = next(
                    (r.get("BirimAdi","") for r in birim_adi_rows
                     if str(r.get("BirimID","")) == str(birim_id)),
                    "")
                pid_listesi = [
                    str(p["KimlikNo"]) for p in p_rows
                    if str(p.get("GorevYeri","")).strip() == birim_adi
                ]

            if not pid_listesi:
                sonuc["hata"] = "Bu birime atanmış personel bulunamadı"
                return sonuc

            # Tercih haritası = sadece "fazla_mesai_gonullu" işaretlenir
            # Herkes nöbet tutar; FM Gönüllü manuel ekleme iÇin işaretlenir
            t_rows = self._r.get("NB_PersonelTercih").get_all() or []
            fm_gonullu_set: set[str] = set()
            for r in t_rows:
                if (str(r.get("BirimID","")) == str(birim_id)
                        and int(r.get("Yil", 0)) == yil
                        and int(r.get("Ay",  0)) == ay
                        and str(r.get("NobetTercihi","")) == "fazla_mesai_gonullu"):
                    fm_gonullu_set.add(str(r.get("PersonelID","")))

            # Tüm personel zorunlu nöbet tutar
            personeller = [pid for pid in pid_listesi if pid]
            gonulluler  = [pid for pid in pid_listesi if pid in fm_gonullu_set]

            if not personeller:
                sonuc["hata"] = "Birime atanmış aktif personel yok"
                return sonuc

        except Exception as e:
            sonuc["hata"] = f"Personel listesi okunamadı: {e}"
            return sonuc

        # ── Hedef haritası (izin düşülmüş, kişiye özel) ──────
        hedef_map: dict[str, int] = {}
        for pid in personeller + gonulluler:
            hedef_map[pid] = self._hedef_hesapla(pid, yil, ay)
            logger.info(
                f"[Hedef] {pid} ââ€ ' {hedef_map[pid]}dk "
                f"= {hedef_map[pid]//60}s")

        # ── İzin, tatil setleri ───────────────────────────────
        tatil_set       = self._tatil_set(yil, ay)  # hedef hesabı iÇin
        resmi_tatil_set = self._resmi_tatil_set(yil, ay)
        dini_set        = self._dini_set(yil, ay)
        izin_map        = self._izin_map(yil, ay)

        # ── Plan başlığı (mevcut taslak temizle) ─────────────
        try:
            pl_rows = self._r.get("NB_Plan").get_all() or []
            ilgili = [
                r for r in pl_rows
                if str(r.get("BirimID", "")) == str(birim_id)
                and int(r.get("Yil", 0)) == yil
                and int(r.get("Ay", 0)) == ay
            ]
            mevcut = max(ilgili, key=lambda r: int(r.get("Versiyon", 1))) if ilgili else None

            if mevcut:
                durum = str(mevcut.get("Durum",""))
                if durum in ("onaylandi","yururlukte"):
                    sonuc["hata"] = (
                        f"Plan '{durum}' durumunda, değiştirilemez")
                    return sonuc
                # Mevcut tüm satırları fiziksel sil (DB şişmesini önle)
                s_rows = self._r.get("NB_PlanSatir").get_all() or []
                silinen = 0
                for s in s_rows:
                    if str(s.get("PlanID","")) == str(mevcut["PlanID"]):
                        try:
                            self._r.get("NB_PlanSatir").delete(s["SatirID"])
                            silinen += 1
                        except Exception:
                            pass
                if silinen:
                    logger.info(f"Eski taslak silindi: {silinen} satır")
                plan_id = str(mevcut["PlanID"])

                # Otomatik plan, revizyon modunu sonlandıran yeni bir taslak üretir.
                # Bu nedenle önceki onay izi alanlarını temizle.
                self._r.get("NB_Plan").update(plan_id, {
                    "Durum": "taslak",
                    "OnaylayanID": None,
                    "OnayTarihi": None,
                    "Notlar": "",
                    "updated_at": _simdi(),
                })
            else:
                plan_id = _yeni_id()
                self._r.get("NB_Plan").insert({
                    "PlanID":    plan_id,
                    "BirimID":   birim_id,
                    "Yil":       yil,
                    "Ay":        ay,
                    "Durum":     "taslak",
                    "created_at": _simdi(),
                    "updated_at": _simdi(),
                })

        except Exception as e:
            sonuc["hata"] = f"Plan başlığı oluşturulamadı: {e}"
            return sonuc

        sonuc.update({
            "ok":          True,
            "ayar":        ayar,
            "slot_sayisi": slot_sayisi,
            "gruplar":     gruplar,
            "personeller": personeller,
            "gonulluler":  gonulluler,
            "fm_gonullu":  gonulluler,
            "hedef_map":   hedef_map,
            "izin_map":    izin_map,
            "tatil_set":   tatil_set,
            "resmi_set":   resmi_tatil_set,
            "dini_set":    dini_set,
            "hafta_sonu_calisma": hafta_sonu_calisma,
            "resmi_tatil_calisma": resmi_tatil_calisma,
            "dini_bayram_calisma": dini_bayram_calisma,
            "ardisik_gun_izinli": ardisik_gun_izinli,
            "plan_id":     plan_id,
        })
        return sonuc

    # ──────────────────────────────────────────────────────────
    #  ADIM 3 = Atama Döngüsü
    # ──────────────────────────────────────────────────────────

    def plan_olustur(self, birim_id: str, yil: int,
                     ay: int) -> SonucYonetici:
        """
        Ana giriş noktası.
        1. Hazırlık (_hazirla)
        2. SayaÇlar
        3. Gün döngüsü ââ€ ' slot döngüsü ââ€ ' grup döngüsü ââ€ ' kişi seÇ
        """
        try:
            h = self._hazirla(birim_id, yil, ay)
            if not h["ok"]:
                return SonucYonetici.hata(
                    ValueError(h.get("hata","Hazırlık başarısız")))

            slot_sayisi = h["slot_sayisi"]
            gruplar     = h["gruplar"]
            personeller = h["personeller"]
            gonulluler  = h["gonulluler"]
            hedef_map   = h["hedef_map"]
            izin_map    = h["izin_map"]
            resmi_set   = h["resmi_set"]
            dini_set    = h["dini_set"]
            plan_id     = h["plan_id"]
            ayar        = h["ayar"]
            hafta_sonu_calisma = h["hafta_sonu_calisma"]
            resmi_tatil_calisma = h["resmi_tatil_calisma"]
            dini_bayram_calisma = h["dini_bayram_calisma"]
            ardisik_gun_izinli = h["ardisik_gun_izinli"]
            plan_id     = h["plan_id"]
            ayar        = h["ayar"]

            # ── SayaÇlar ──────────────────────────────────────
            # Sıralama: az saat ââ€ ' az nöbet ââ€ ' az hafta sonu
            saat_sayac: dict[str, int] = {p: 0 for p in personeller + gonulluler}
            nobet_sayac: dict[str, int] = {p: 0 for p in personeller + gonulluler}
            hs_sayac:   dict[str, int] = {p: 0 for p in personeller + gonulluler}
            # Son nöbet takibi: {pid: (tarih_str, grup_id)}
            # Aynı gün farklı gruba girebilir, aynı gruba giremez
            son_nobet:  dict[str, tuple] = {}
            # Günlük toplam süre: {pid: {tarih_str: toplam_dk}}
            gun_sure_sayac: dict[str, dict] = {p: {} for p in personeller + gonulluler}

            eklenen:  list[dict] = []
            uyarilar: list[str]  = []
            # FM Gönüllülerin fazla mesai saati (hedef üstü kısım)
            fm_saat_sayac: dict[str, int] = {p: 0 for p in gonulluler}

            # Önceki ay bakiyesi (alacak/verecek) — NB_MesaiHesap.DevireGidenDakika
            prev_yil = yil - 1 if ay == 1 else yil
            prev_ay  = 12      if ay == 1 else ay - 1
            try:
                mh_rows = self._r.get("NB_MesaiHesap").get_all() or []
                devir_map: dict[str, int] = {
                    str(r.get("PersonelID", "")): int(r.get("DevireGidenDakika", 0))
                    for r in mh_rows
                    if str(r.get("BirimID", "")) == str(birim_id)
                    and int(r.get("Yil", 0)) == prev_yil
                    and int(r.get("Ay",  0)) == prev_ay
                }
            except Exception:
                devir_map = {}

            # Bakiye sayacı (negatif = eksik, pozitif = fazla)
            bakiye_sayac: dict[str, int] = {
                p: int(devir_map.get(p, 0)) for p in (personeller + gonulluler)
            }

            # Birim bazlı günlük max süre = NB_BirimAyar.MaxGunlukSureDakika
            # 720dk = 12s ââ€ ' personel günde sadece 1 vardiya (gündüz VEYA gece)
            # 1440dk = 24s ââ€ ' personel aynı günde 2 vardiya tutabilir (gündüz + gece)
            BIRIM_MAX_GUN_DK = int(ayar.get("MaxGunlukSureDakika", 720))
            logger.info(
                f"[Birim] MaxGunlukSureDakika={BIRIM_MAX_GUN_DK}dk "
                f"({'24 saat = gündüz+gece izinli' if BIRIM_MAX_GUN_DK >= 1440 else '12 saat = tek vardiya'})"
            )

            # Tolerans: ±7 saat (420 dk) — hedefi Çok aşmamak iÇin sabit
            _tolerans_dk = 7 * 60

            def _tolerans(pid: str) -> int:
                """Kişiye özel tolerans = ±7 saat, hedeften büyük olamaz."""
                return min(_tolerans_dk, hedef_map.get(pid, 0))

            # Sıralama: az saat ââ€ ' az nöbet sayısı ââ€ ' az hafta sonu
            def _sirala(pid_listesi: list[str]) -> list[str]:
                return sorted(pid_listesi, key=lambda p: (
                    bakiye_sayac[p],
                    saat_sayac[p],
                    nobet_sayac[p],
                    hs_sayac[p],
                ))

            # Atanabilirlik kontrolü = zorunlu personel
            def _atanabilir(pid: str, tarih_str: str,
                            gun: date, grup_id: str = "",
                            eklenecek_dk: int = 0,
                            gunluk_limit_dk: int | None = None) -> bool:
                # İzin günü
                if tarih_str in izin_map.get(pid, set()):
                    return False
                son = son_nobet.get(pid)
                if son:
                    son_tarih, son_grup = son
                    if son_tarih == tarih_str and son_grup == grup_id:
                        return False
                    if not ardisik_gun_izinli:
                        dun = (gun - timedelta(days=1)).isoformat()
                        if son_tarih == dun:
                            return False
                hedef = hedef_map.get(pid, 0)
                if hedef == 0:
                    return False
                ust     = hedef + _tolerans(pid)
                sonraki = saat_sayac[pid] + eklenecek_dk
                if saat_sayac[pid] == 0:
                    pass  # İlk atama = günlük limit kontrolünü yine de yap
                elif sonraki > ust:
                    return False
                # ── Birim bazlı günlük max süre kontrolü ─────
                gun_toplam = gun_sure_sayac[pid].get(tarih_str, 0)
                limit_dk = gunluk_limit_dk or BIRIM_MAX_GUN_DK
                if gun_toplam + eklenecek_dk > limit_dk:
                    return False
                return True

            # FM Gönüllü max saat = NB_BirimAyar'dan oku, varsayılan 60s
            try:
                a_rows = self._r.get("NB_BirimAyar").get_all() or []
                ayar_r = next((r for r in a_rows
                               if str(r.get("BirimID","")) == str(birim_id)), None)
                FM_MAX_DK = int((ayar_r or {}).get("FmMaxSaat", 60)) * 60
            except Exception:
                FM_MAX_DK = 3600  # 60 saat

            def _atanabilir_fm(pid: str, tarih_str: str,
                               gun: date, grup_id: str = "") -> bool:
                # İzin günü
                if tarih_str in izin_map.get(pid, set()):
                    return False
                son = son_nobet.get(pid)
                if son:
                    son_tarih, son_grup = son
                    if son_tarih == tarih_str and son_grup == grup_id:
                        return False
                    if not ardisik_gun_izinli:
                        dun = (gun - timedelta(days=1)).isoformat()
                        if son_tarih == dun:
                            return False
                # FM toplam saati max 60s'i geÇemez
                # fm_saat_sayac: sadece FM gönüllü olarak eklenen saatler
                if fm_saat_sayac.get(pid, 0) >= FM_MAX_DK:
                    return False
                return True

            # Kayıt ekleme
            def _ekle(pid: str, vardiya: dict,
                      tarih_str: str, is_hw: bool, grup_id: str = ""):
                self._r.get("NB_PlanSatir").insert({
                    "SatirID":     _yeni_id(),
                    "PlanID":      plan_id,
                    "PersonelID":  pid,
                    "VardiyaID":   vardiya["VardiyaID"],
                    "NobetTarihi": tarih_str,
                    "Kaynak":      "algoritma",
                    "NobetTuru":   "normal",
                    "Durum":       "aktif",
                    "created_at":  _simdi(),
                })
                dk = int(vardiya.get("SureDakika", 0))
                saat_sayac[pid]  += dk
                nobet_sayac[pid] += 1
                bakiye_sayac[pid] += dk
                # Günlük toplam süre sayacını güncelle
                gun_sure_sayac[pid][tarih_str] = (
                    gun_sure_sayac[pid].get(tarih_str, 0) + dk)
                if is_hw:
                    hs_sayac[pid] += 1
                # son_nobet: (tarih, grup_id) = dün yasağı + aynı grup yasağı
                son_nobet[pid] = (tarih_str, grup_id)
                eklenen.append(pid)

            vardiya_meta: dict[str, tuple[int, str]] = {}
            for grup in gruplar:
                g_id = str(grup.get("GrupID", ""))
                for v in (grup.get("ana") or []):
                    v_id = str(v.get("VardiyaID", ""))
                    if not v_id:
                        continue
                    vardiya_meta[v_id] = (int(v.get("SureDakika", 0)), g_id)

            def _minimum_atama_dengele() -> None:
                """Hedefi olan zorunlu personelin sıfır nöbet kalmasını önlemeye çalış."""
                satirlar = [
                    r for r in (self._r.get("NB_PlanSatir").get_all() or [])
                    if str(r.get("PlanID", "")) == str(plan_id)
                    and str(r.get("Durum", "aktif")) == "aktif"
                ]
                if not satirlar:
                    return

                tasinmis_satirlar: set[str] = set()

                def _eksik_pidler() -> list[str]:
                    return [
                        pid for pid in personeller
                        if hedef_map.get(pid, 0) > 0 and nobet_sayac.get(pid, 0) == 0
                    ]

                # 1. faz: donor en az 2 nöbetli olsun.
                # 2. faz: hâlâ eksik varsa donor 1 nöbetli de olabilir.
                for donor_min_nobet in (2, 1):
                    while True:
                        eksik_pidler = _eksik_pidler()
                        if not eksik_pidler:
                            return

                        degisim_oldu = False
                        for hedef_pid in eksik_pidler:
                            adaylar = sorted(
                                satirlar,
                                key=lambda r: (
                                    nobet_sayac.get(str(r.get("PersonelID", "")), 0),
                                    saat_sayac.get(str(r.get("PersonelID", "")), 0),
                                ),
                                reverse=True,
                            )
                            for satir in adaylar:
                                donor_pid = str(satir.get("PersonelID", ""))
                                vardiya_id = str(satir.get("VardiyaID", ""))
                                tarih_str = str(satir.get("NobetTarihi", ""))
                                satir_id = str(satir.get("SatirID", ""))

                                if not donor_pid or donor_pid == hedef_pid:
                                    continue
                                if not vardiya_id or not tarih_str or not satir_id:
                                    continue
                                if satir_id in tasinmis_satirlar:
                                    continue
                                if nobet_sayac.get(donor_pid, 0) < donor_min_nobet:
                                    continue

                                meta = vardiya_meta.get(vardiya_id)
                                if not meta:
                                    continue
                                v_dk, grup_id = meta

                                try:
                                    gun = date.fromisoformat(tarih_str)
                                except Exception:
                                    continue

                                donor_alt_limit = max(
                                    0,
                                    hedef_map.get(donor_pid, 0) - _tolerans(donor_pid),
                                )
                                donor_sonrasi = saat_sayac.get(donor_pid, 0) - v_dk
                                if donor_sonrasi < donor_alt_limit:
                                    # 2. fazda (donor_min_nobet=1),
                                    # sıfır nöbetliyi kurtarmak için bir vardiya esneme izni ver.
                                    if donor_min_nobet >= 2:
                                        continue
                                    relax_limit = max(0, donor_alt_limit - v_dk)
                                    if donor_sonrasi < relax_limit:
                                        continue
                                    logger.info(
                                        f"[Dengeleme/Esneme] donor={donor_pid} "
                                        f"alt_limit={donor_alt_limit}dk -> {relax_limit}dk"
                                    )

                                if not _atanabilir(
                                    hedef_pid,
                                    tarih_str,
                                    gun,
                                    grup_id=f"{grup_id}_{vardiya_id}",
                                    eklenecek_dk=v_dk,
                                ):
                                    continue

                                self._r.get("NB_PlanSatir").update(satir_id, {
                                    "PersonelID": hedef_pid,
                                    "Kaynak": "algoritma_dengeleme",
                                    "updated_at": _simdi(),
                                })

                                saat_sayac[donor_pid] = max(0, saat_sayac.get(donor_pid, 0) - v_dk)
                                nobet_sayac[donor_pid] = max(0, nobet_sayac.get(donor_pid, 0) - 1)
                                bakiye_sayac[donor_pid] = bakiye_sayac.get(donor_pid, 0) - v_dk
                                gun_sure_sayac[donor_pid][tarih_str] = max(
                                    0,
                                    gun_sure_sayac[donor_pid].get(tarih_str, 0) - v_dk,
                                )

                                saat_sayac[hedef_pid] = saat_sayac.get(hedef_pid, 0) + v_dk
                                nobet_sayac[hedef_pid] = nobet_sayac.get(hedef_pid, 0) + 1
                                bakiye_sayac[hedef_pid] = bakiye_sayac.get(hedef_pid, 0) + v_dk
                                gun_sure_sayac[hedef_pid][tarih_str] = (
                                    gun_sure_sayac[hedef_pid].get(tarih_str, 0) + v_dk
                                )

                                if gun.weekday() in HAFTASONU:
                                    hs_sayac[donor_pid] = max(0, hs_sayac.get(donor_pid, 0) - 1)
                                    hs_sayac[hedef_pid] = hs_sayac.get(hedef_pid, 0) + 1

                                son_nobet[hedef_pid] = (tarih_str, f"{grup_id}_{vardiya_id}")
                                satir["PersonelID"] = hedef_pid
                                tasinmis_satirlar.add(satir_id)
                                degisim_oldu = True
                                logger.info(
                                    f"[Dengeleme] {hedef_pid} için {tarih_str} {vardiya_id} "
                                    f"ataması {donor_pid} personelinden devralındı."
                                )
                                break

                        if not degisim_oldu:
                            break

                for pid in _eksik_pidler():
                    uyarilar.append(
                        f"{pid} için minimum 1 nöbet dengelemesi yapılamadı"
                    )

            # ── Gün döngüsü ───────────────────────────────────
            # Her slot iÇin slot_sayisi kadar atama yapılır.
            # Her grup iÇindeki her vardiya ayrı bağımsız slot.
            # Yani: slot_sayisi Ï= grup_vardiya_sayisi kadar kişi atanır.
            #
            # Excel mantığı:
            #   08:00-20:00 ââ€ ' 4 slot ââ€ ' 4 farklı kişi
            #   20:00-08:00 ââ€ ' 4 slot ââ€ ' 4 farklı kişi
            # Bu yapıda "grup" sadece görsel başlık, her vardiya kendi slotu.
            ay_son = monthrange(yil, ay)[1]
            gunler = [date(yil, ay, g) for g in range(1, ay_son + 1)]

            for gun in gunler:
                tarih_str = gun.isoformat()

                # Birim tatil/hafta sonu Çalışma politikası
                if tarih_str in dini_set and not dini_bayram_calisma:
                    continue
                if tarih_str in resmi_set and not resmi_tatil_calisma:
                    continue

                is_hw = gun.weekday() in HAFTASONU
                if is_hw and not hafta_sonu_calisma:
                    continue

                is_hw = gun.weekday() in HAFTASONU

                # Her slot iÇin, her grup iÇindeki her vardiyaya kişi ata
                for slot_no in range(slot_sayisi):
                    for grup in gruplar:
                        grup_id = grup["GrupID"]
                        vardiyalar = grup["ana"]
                        toplam_grup_dk = sum(
                            int(v.get("SureDakika", 0)) for v in vardiyalar)
                        grup_adi = str(grup.get("GrupAdi", "")).strip().lower()
                        grup_24s_mod = (
                            len(vardiyalar) > 1
                            and toplam_grup_dk >= 1440
                            and (
                                BIRIM_MAX_GUN_DK >= 1440
                                or "24 saat" in grup_adi
                            )
                        )

                        # ── 24s mod: aynı kişiyi grubun tüm vardiyalarına ata ──
                        if grup_24s_mod:
                            atandi_24 = False

                            # Zorunlu personelden 24s tutabilecek biri var mı?
                            for pid in _sirala(personeller):
                                hedef = hedef_map.get(pid, 0)
                                ust = hedef + _tolerans(pid)
                                kalan_ust = ust - saat_sayac[pid]
                                # 24 saat izinli olmak, 24 saat zorunlu demek değil.
                                # Kalan üst limit 24s paketi taşımıyorsa tek vardiya moduna düş.
                                if kalan_ust < toplam_grup_dk:
                                    continue
                                ek_dk = 0
                                uygun = True
                                for v in vardiyalar:
                                    v_dk = int(v.get("SureDakika", 0))
                                    if not _atanabilir(
                                        pid, tarih_str, gun,
                                        grup_id=f"{grup_id}_{v['VardiyaID']}",
                                        eklenecek_dk=ek_dk + v_dk,
                                        gunluk_limit_dk=max(
                                            BIRIM_MAX_GUN_DK,
                                            toplam_grup_dk,
                                        ),
                                    ):
                                        uygun = False
                                        break
                                    ek_dk += v_dk
                                if uygun:
                                    for v in vardiyalar:
                                        _ekle(pid, v, tarih_str, is_hw,
                                              f"{grup_id}_{v['VardiyaID']}")
                                    atandi_24 = True
                                    break

                            # FM Gönüllü de dene
                            if not atandi_24:
                                for pid in _sirala(gonulluler):
                                    ust = hedef_map.get(pid, 0) + _tolerans(pid)
                                    kalan_ust = ust - saat_sayac[pid]
                                    if kalan_ust < toplam_grup_dk:
                                        continue
                                    if fm_saat_sayac.get(pid, 0) + toplam_grup_dk > FM_MAX_DK:
                                        continue
                                    ek_dk = 0
                                    uygun = True
                                    for v in vardiyalar:
                                        v_dk = int(v.get("SureDakika", 0))
                                        if not _atanabilir_fm(
                                            pid, tarih_str, gun,
                                            grup_id=f"{grup_id}_{v['VardiyaID']}",
                                        ):
                                            uygun = False
                                            break
                                        if fm_saat_sayac.get(pid, 0) + ek_dk + v_dk > FM_MAX_DK:
                                            uygun = False
                                            break
                                        ek_dk += v_dk
                                    if uygun:
                                        for v in vardiyalar:
                                            v_dk = int(v.get("SureDakika", 0))
                                            _ekle(pid, v, tarih_str, is_hw,
                                                  f"{grup_id}_{v['VardiyaID']}")
                                            fm_saat_sayac[pid] = \
                                                fm_saat_sayac.get(pid, 0) + v_dk
                                        atandi_24 = True
                                        break

                            if atandi_24:
                                continue  # Bu slot doldu, sıradaki slot'a geÇ

                            # 24s atanamadı ââ€ ' tek tek ata (aşağı düş)

                        # ── Tek vardiya modu (12s veya 24s bulunamadıysa) ──
                        for vardiya in vardiyalar:
                            v_dk = int(vardiya.get("SureDakika", 0))
                            v_slot_id = f"{grup_id}_{vardiya['VardiyaID']}"

                            atandi = False

                            # 1. Zorunlu personel
                            for pid in _sirala(personeller):
                                if not _atanabilir(pid, tarih_str, gun,
                                                   grup_id=v_slot_id,
                                                   eklenecek_dk=v_dk):
                                    continue
                                _ekle(pid, vardiya, tarih_str, is_hw, v_slot_id)
                                atandi = True
                                break

                            # 2. FM Gönüllüler
                            if not atandi:
                                for pid in _sirala(gonulluler):
                                    if not _atanabilir_fm(pid, tarih_str, gun,
                                                          grup_id=v_slot_id):
                                        continue
                                    _ekle(pid, vardiya, tarih_str, is_hw, v_slot_id)
                                    fm_saat_sayac[pid] = \
                                        fm_saat_sayac.get(pid, 0) + v_dk
                                    atandi = True
                                    break

                            # 3. Boş bırak
                            if not atandi:
                                uyarilar.append(
                                    f"{tarih_str} | slot {slot_no+1} | "
                                    f"'{vardiya.get('VardiyaAdi','')}' "
                                    f"doldurulamadı = boş")

            _minimum_atama_dengele()

            # ── Ï–zet ──────────────────────────────────────────
            for pid in personeller + gonulluler:
                dk  = saat_sayac[pid]
                hdf = hedef_map[pid]
                tol = _tolerans(pid)
                fm  = fm_saat_sayac.get(pid, 0)
                logger.info(
                    f"[Atama] {pid}: {dk}dk={dk//60}s "
                    f"/ hedef={hdf//60}s tol={tol//60}s "
                    f"/ üst={(hdf+tol)//60}s "
                    f"/ nöbet={nobet_sayac[pid]}"
                    + (f" / FM={fm//60}s" if fm else ""))

            ozet = (
                f"{len(eklenen)} nöbet ataması yapıldı"
                + (f"  |  {len(uyarilar)} uyarı" if uyarilar else ""))
            logger.info(
                f"Algoritma: {birim_id} {yil}/{ay:02d} = {ozet}")

            return SonucYonetici.tamam(
                mesaj=ozet,
                veri={"uyarilar": uyarilar, "PlanID": plan_id})

        except Exception as e:
            logger.error(f"plan_olustur: {e}", exc_info=True)
            return SonucYonetici.hata(e, "NbAlgoritma.plan_olustur")


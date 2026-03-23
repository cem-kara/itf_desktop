# -*- coding: utf-8 -*-
"""
NobetService — Nöbet Yönetimi İş Mantığı
═══════════════════════════════════════════════════════════
Sorumluluklar:
  - Birim / Vardiya CRUD
  - Nöbet planı oluşturma (otomatik + manuel)
  - Kısıt motoru (üst üste yasak, izin günü, aylık saat limiti)
  - Onay işlemleri
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Optional

from core.hata_yonetici import SonucYonetici
from core.logger import logger
from database.repository_registry import RepositoryRegistry


# ── Sabitler ──────────────────────────────────────────────
GUNLUK_HEDEF_SAAT  = 7.0    # iş günü başına hedef mesai (radyoloji standardı)
MAX_AYLIK_SAAT     = 225.0  # varsayılan üst limit (hesaplanmadığında fallback)
NOBET_SAAT         = 7.0    # geriye dönük uyumluluk için korundu


def _yeni_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12].upper()}"


class NobetService:
    """Nöbet modülü iş mantığı servisi."""

    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("RepositoryRegistry boş olamaz")
        self._r = registry

    # ═══════════════════════════════════════════════════
    #  BİRİM (Sabitler tablosundan okur — CRUD yok)
    # ═══════════════════════════════════════════════════

    def get_birimler(self) -> SonucYonetici:
        """Sabitler tablosundan Kod='Birim' olan kayıtları döner."""
        try:
            rows = self._r.get("Sabitler").get_all() or []
            birimler = sorted({
                str(r.get("MenuEleman", "")).strip()
                for r in rows
                if str(r.get("Kod", "")).strip() == "Birim"
                and str(r.get("MenuEleman", "")).strip()
            })
            return SonucYonetici.tamam(veri=birimler)
        except Exception as e:
            return SonucYonetici.hata(e, "NobetService.get_birimler")

    # ═══════════════════════════════════════════════════
    #  VARDİYA
    # ═══════════════════════════════════════════════════

    def get_birim_ayar(self, birim_adi: str) -> dict:
        """
        Birim ayarını döner. Yoksa varsayılan üretir.
        Slot süresi: GunlukSlotSaat || Σ ana vardiya SaatSuresi
        """
        try:
            rows = self._r.get("Nobet_BirimAyar").get_all() or []
            kayit = next((r for r in rows
                          if r.get("BirimAdi") == birim_adi), None)
            if kayit:
                return dict(kayit)
        except Exception:
            pass

        # Varsayılan: ana vardiyaların saatini topla
        slot_saat = None
        try:
            v_rows = self._r.get("Nobet_Vardiya").get_all() or []
            ana_saatler = [
                float(v.get("SaatSuresi", GUNLUK_HEDEF_SAAT))
                for v in v_rows
                if v.get("BirimAdi") == birim_adi
                and (v.get("VardiyaRolu") or "ana") == "ana"
                and int(v.get("Aktif", 1))
            ]
            if ana_saatler:
                slot_saat = sum(ana_saatler)
        except Exception:
            pass

        return {
            "BirimAdi":         birim_adi,
            "GunlukSlotSaat":   slot_saat or 24.0,
            "SlotBasiPersonel": 4,
            "CalismaModu":      "tam_gun",
            "OtomatikBolunme":  1,
        }

    def birim_ayar_kaydet(self, birim_adi: str, slot_saat: Optional[float],
                          slot_personel: int, calisma_modu: str,
                          otomatik_bolunme: bool = True,
                          aciklama: str = "") -> SonucYonetici:
        try:
            rows = self._r.get("Nobet_BirimAyar").get_all() or []
            mevcut = next((r for r in rows
                           if r.get("BirimAdi") == birim_adi), None)
            veri = {
                "BirimAdi":        birim_adi,
                "GunlukSlotSaat":  slot_saat,
                "SlotBasiPersonel": slot_personel,
                "CalismaModu":     calisma_modu,
                "OtomatikBolunme": 1 if otomatik_bolunme else 0,
                "Aciklama":        aciklama,
            }
            if mevcut:
                self._r.get("Nobet_BirimAyar").update(mevcut["AyarID"], veri)
            else:
                veri["AyarID"] = _yeni_id("BA-")
                self._r.get("Nobet_BirimAyar").insert(veri)
            return SonucYonetici.tamam(f"{birim_adi} birim ayarı kaydedildi")
        except Exception as e:
            return SonucYonetici.hata(e, "NobetService.birim_ayar_kaydet")

    def get_vardiyalar(self, birim_adi: Optional[str] = None) -> SonucYonetici:
        try:
            rows = self._r.get("Nobet_Vardiya").get_all() or []
            if birim_adi:
                rows = [r for r in rows if r.get("BirimAdi") == birim_adi]
            rows = [r for r in rows if r.get("Aktif", 1)]
            return SonucYonetici.tamam(veri=rows)
        except Exception as e:
            return SonucYonetici.hata(e, "NobetService.get_vardiyalar")

    def vardiya_ekle(self, veri: dict) -> SonucYonetici:
        try:
            if not veri.get("BirimAdi") or not veri.get("VardiyaAdi"):
                return SonucYonetici.hata(ValueError("BirimAdi ve VardiyaAdi zorunlu"))
            veri.setdefault("VardiyaID", _yeni_id("VAR-"))
            veri.setdefault("MinPersonel", 1)
            veri.setdefault("Aktif", 1)
            self._r.get("Nobet_Vardiya").insert(veri)
            return SonucYonetici.tamam(f"Vardiya eklendi: {veri['VardiyaAdi']}")
        except Exception as e:
            return SonucYonetici.hata(e, "NobetService.vardiya_ekle")

    def vardiya_guncelle(self, vardiya_id: str, veri: dict) -> SonucYonetici:
        try:
            self._r.get("Nobet_Vardiya").update(vardiya_id, veri)
            return SonucYonetici.tamam(f"Vardiya güncellendi: {vardiya_id}")
        except Exception as e:
            return SonucYonetici.hata(e, "NobetService.vardiya_guncelle")

    def vardiya_sil(self, vardiya_id: str) -> SonucYonetici:
        try:
            self._r.get("Nobet_Vardiya").update(vardiya_id, {"Aktif": 0})
            return SonucYonetici.tamam(f"Vardiya pasife alındı: {vardiya_id}")
        except Exception as e:
            return SonucYonetici.hata(e, "NobetService.vardiya_sil")

    # ═══════════════════════════════════════════════════
    #  NÖBET PLANI
    # ═══════════════════════════════════════════════════

    def get_plan(self, yil: int, ay: int,
                 birim_adi: Optional[str] = None) -> SonucYonetici:
        try:
            rows = self._r.get("Nobet_Plan").get_all() or []
            ay_bas = f"{yil:04d}-{ay:02d}-01"
            ay_bit = f"{yil:04d}-{ay:02d}-31"
            rows = [r for r in rows
                    if ay_bas <= str(r.get("NobetTarihi", "")) <= ay_bit
                    and r.get("Durum") != "iptal"]
            if birim_adi:
                rows = [r for r in rows if r.get("BirimAdi") == birim_adi]
            return SonucYonetici.tamam(veri=rows)
        except Exception as e:
            return SonucYonetici.hata(e, "NobetService.get_plan")

    def plan_ekle(self, veri: dict) -> SonucYonetici:
        try:
            personel_id = str(veri.get("PersonelID", "")).strip()
            tarih       = str(veri.get("NobetTarihi", "")).strip()
            birim_adi   = str(veri.get("BirimAdi", "")).strip()
            vardiya_id  = str(veri.get("VardiyaID", "")).strip()

            if not all([personel_id, tarih, birim_adi, vardiya_id]):
                return SonucYonetici.hata(
                    ValueError("PersonelID, NobetTarihi, BirimAdi, VardiyaID zorunlu")
                )

            kisit = self._kisit_kontrol(personel_id, tarih,
                                        birim_adi, vardiya_id,
                                        veri.get("NobetTuru", "normal"))
            if kisit:
                return SonucYonetici.hata(ValueError(kisit))

            veri.setdefault("PlanID", _yeni_id("NB-"))
            veri.setdefault("Durum", "taslak")
            veri.setdefault("NobetTuru", "normal")
            self._r.get("Nobet_Plan").insert(veri)
            return SonucYonetici.tamam(f"Nöbet eklendi: {personel_id} / {tarih}")
        except Exception as e:
            return SonucYonetici.hata(e, "NobetService.plan_ekle")

    def plan_guncelle(self, plan_id: str, veri: dict) -> SonucYonetici:
        try:
            self._r.get("Nobet_Plan").update(plan_id, veri)
            return SonucYonetici.tamam(f"Nöbet güncellendi: {plan_id}")
        except Exception as e:
            return SonucYonetici.hata(e, "NobetService.plan_guncelle")

    def plan_iptal(self, plan_id: str) -> SonucYonetici:
        try:
            self._r.get("Nobet_Plan").update(plan_id, {"Durum": "iptal"})
            return SonucYonetici.tamam(f"Nöbet iptal: {plan_id}")
        except Exception as e:
            return SonucYonetici.hata(e, "NobetService.plan_iptal")

    # ═══════════════════════════════════════════════════
    #  OTOMATİK PLANLAMA
    # ═══════════════════════════════════════════════════

    def otomatik_plan_olustur(
        self,
        yil: int,
        ay: int,
        birim_adi: str,
        max_aylik_saat: float = MAX_AYLIK_SAAT,
    ) -> SonucYonetici:
        """
        Slot tabanlı nöbet planlama algoritması.

        Her gün SlotBasiPersonel kadar "slot" doldurulur.
        Her slot normalde 1 kişiye tam atanır (SlotSuresi kadar saat).
        Kişinin aylık hedef saati dolmuşsa → OtomatikBolunme=1 ise slot
        "ana" vardiyaları arasında bölünür (farklı kişiler, aynı pozisyon).

        Adalet ölçüsü: SAAT TOPLAMI eşitlenir.
        Sıralama: az saat → az hafta sonu → bu vardiyaya az girmiş
        """
        try:
            # ── Birim ayarı ───────────────────────────────────
            ayar = self.get_birim_ayar(birim_adi)
            slot_basi    = int(ayar.get("SlotBasiPersonel", 4))
            slot_saat    = float(ayar.get("GunlukSlotSaat", 24.0))
            oto_bolunme  = bool(int(ayar.get("OtomatikBolunme", 1)))

            # Ana vardiyalar (algoritma bunları doldurur, sıralı)
            v_sonuc = self.get_vardiyalar(birim_adi)
            if not v_sonuc.basarili or not v_sonuc.veri:
                return SonucYonetici.hata(
                    ValueError(f"'{birim_adi}' için vardiya tanımı yok"))

            tum_vardiyalar = v_sonuc.veri
            ana_vardiyalar = [
                v for v in tum_vardiyalar
                if (v.get("VardiyaRolu") or "ana") == "ana"
                and int(v.get("Aktif",1))
            ]
            if not ana_vardiyalar:
                return SonucYonetici.hata(
                    ValueError(f"'{birim_adi}' için 'ana' rolünde vardiya yok"))

            # ── Personel havuzu ───────────────────────────────
            personel_rows = self._r.get("Personel").get_all() or []
            personeller   = [
                p for p in personel_rows
                if str(p.get("GorevYeri","")).strip() == birim_adi
            ]
            if not personeller:
                return SonucYonetici.hata(
                    ValueError(f"'{birim_adi}' biriminde kayıtlı personel yok"))

            tercih_map  = self._tercih_map_getir(yil, ay)
            personeller = [
                p for p in personeller
                if tercih_map.get(str(p["KimlikNo"]),"zorunlu") == "zorunlu"
            ]
            # Fazla mesai gönüllüleri — zorunlu personel dolduramadığında devreye girer
            gonullu_fm = [
                p for p in [q for q in (self._r.get("Personel").get_all() or [])
                             if str(q.get("GorevYeri","")).strip() == birim_adi]
                if tercih_map.get(str(p["KimlikNo"]),"zorunlu") == "fazla_mesai_gonullu"
            ]
            if not personeller:
                return SonucYonetici.hata(
                    ValueError("Zorunlu nöbet tutacak personel yok"))

            izin_map = self._izin_map_getir(yil, ay)

            # Dini bayram günleri — otomatik atama yapılmaz
            # Manuel 'Fazla Mesai' ile eklenebilir
            dini_bayram_set: set[str] = set(
                self._tatil_listesi_getir(yil, ay,
                                          idari_dahil=False,
                                          sadece_dini=True)
            )

            # Kişiye özgü aylık hedef saat (zorunlu + gönüllü)
            hedef_map: dict[str, float] = {}
            for p in personeller + gonullu_fm:
                pid = str(p["KimlikNo"])
                if pid in hedef_map:
                    continue
                h   = self._kisi_hedef_saat(pid, yil, ay, otomatik=True)
                hedef_map[pid] = h if h is not None else max_aylik_saat

            # ── Ay günleri ────────────────────────────────────
            ay_bas  = date(yil, ay, 1)
            ay_bit  = (date(yil+1,1,1)-timedelta(days=1) if ay==12
                       else date(yil,ay+1,1)-timedelta(days=1))
            gunler  = [ay_bas+timedelta(days=i)
                       for i in range((ay_bit-ay_bas).days+1)]

            # ── Sayaçlar ──────────────────────────────────────
            saat_sayac:    dict[str,float]         = {str(p["KimlikNo"]):0.0 for p in personeller}
            hs_sayac:      dict[str,int]           = {str(p["KimlikNo"]):0   for p in personeller}
            vardiya_sayac: dict[str,dict[str,int]] = {str(p["KimlikNo"]):{} for p in personeller}
            son_nobet:     dict[str,str]           = {}
            eklenen:       list[dict]              = []
            uyarilar:      list[str]               = []

            HAFTASONU = {5, 6}

            def _sirala(pid_listesi: list[str]) -> list[str]:
                return sorted(
                    pid_listesi,
                    key=lambda pid: (
                        saat_sayac.get(pid, 0.0),
                        hs_sayac.get(pid, 0),
                        sum(vardiya_sayac.get(pid,{}).values()),
                    )
                )

            def _atanabilir(pid: str, tarih_str: str, gun: date,
                            v_saat: float, hedef: float,
                            fm_gonullu: bool = False) -> bool:
                if tarih_str in izin_map.get(pid, set()):
                    return False
                dun = (gun - timedelta(days=1)).isoformat()
                if son_nobet.get(pid) == dun:
                    return False
                # FM gönüllüsünde saat limiti yok — isteyen kişi
                if not fm_gonullu and saat_sayac.get(pid, 0.0) >= hedef:
                    return False
                return True

            def _ekle(pid: str, v: dict, tarih_str: str, is_hw: bool):
                plan = {
                    "PlanID":      _yeni_id("NB-"),
                    "PersonelID":  pid,
                    "BirimAdi":    birim_adi,
                    "VardiyaID":   v["VardiyaID"],
                    "NobetTarihi": tarih_str,
                    "NobetTuru":   "normal",
                    "Durum":       "taslak",
                }
                self._r.get("Nobet_Plan").insert(plan)
                eklenen.append(plan)
                vsaat = float(v.get("SaatSuresi", GUNLUK_HEDEF_SAAT))
                saat_sayac[pid] = saat_sayac.get(pid, 0.0) + vsaat
                if is_hw:
                    hs_sayac[pid] = hs_sayac.get(pid, 0) + 1
                vs = vardiya_sayac.setdefault(pid, {})
                vs[v["VardiyaID"]] = vs.get(v["VardiyaID"], 0) + 1
                son_nobet[pid] = tarih_str
                return plan

            # ── Ana döngü ─────────────────────────────────────
            for gun in gunler:
                tarih_str = gun.isoformat()

                # Dini bayram → otomatik atama yok
                if tarih_str in dini_bayram_set:
                    continue

                is_hw     = gun.weekday() in HAFTASONU
                pid_listesi = [str(p["KimlikNo"]) for p in personeller]

                for slot_no in range(slot_basi):

                    # Tam slot: tek kişi tüm ana vardiyalara girer
                    # Önce zorunlu, dolmazsa FM gönüllüsü (saat limiti yok)
                    tam_atandi = False
                    fm_pid_listesi = [str(p["KimlikNo"]) for p in gonullu_fm]
                    for pid in _sirala(pid_listesi):
                        hedef = hedef_map.get(pid, max_aylik_saat)
                        kalan = hedef - saat_sayac.get(pid, 0.0)
                        if kalan < slot_saat * 0.5:
                            continue
                        if not _atanabilir(pid, tarih_str, gun, slot_saat, hedef):
                            continue
                        for v in ana_vardiyalar:
                            _ekle(pid, v, tarih_str, is_hw)
                        tam_atandi = True
                        break

                    if not tam_atandi:
                        for pid in _sirala(fm_pid_listesi):
                            hedef = hedef_map.get(pid, max_aylik_saat)
                            if not _atanabilir(pid, tarih_str, gun,
                                               slot_saat, hedef, fm_gonullu=True):
                                continue
                            for v in ana_vardiyalar:
                                _ekle(pid, v, tarih_str, is_hw)
                            tam_atandi = True
                            break

                    if tam_atandi:
                        continue

                    # Tam slot dolmadı — oto_bolunme açıksa her ana vardiyaya ayrı kişi
                    if oto_bolunme:
                        slot_tamam = True
                        for v in ana_vardiyalar:
                            v_saat = float(v.get("SaatSuresi", GUNLUK_HEDEF_SAAT))
                            atandi = False
                            # Önce zorunlu, dolmazsa FM gönüllüsü
                            for pid in _sirala(pid_listesi):
                                hedef = hedef_map.get(pid, max_aylik_saat)
                                if not _atanabilir(pid, tarih_str, gun,
                                                   v_saat, hedef):
                                    continue
                                _ekle(pid, v, tarih_str, is_hw)
                                atandi = True
                                break
                            if not atandi:
                                for pid in _sirala(fm_pid_listesi):
                                    hedef = hedef_map.get(pid, max_aylik_saat)
                                    if not _atanabilir(pid, tarih_str, gun,
                                                       v_saat, hedef,
                                                       fm_gonullu=True):
                                        continue
                                    _ekle(pid, v, tarih_str, is_hw)
                                    atandi = True
                                    break
                            if not atandi:
                                slot_tamam = False
                                uyarilar.append(
                                    f"{tarih_str} slot {slot_no+1} "
                                    f"'{v.get('VardiyaAdi','')}' doldurulamadı"
                                )
                        if not slot_tamam:
                            pass  # uyarı zaten eklendi
                    else:
                        uyarilar.append(
                            f"{tarih_str} slot {slot_no+1} — "
                            "hedef dolmuş personel, bölünme kapalı"
                        )

            ozet = (f"{len(eklenen)} nöbet ataması yapıldı"
                    + (f" | {len(uyarilar)} uyarı" if uyarilar else ""))
            return SonucYonetici.tamam(
                mesaj=ozet,
                veri={"eklenen": eklenen, "uyarilar": uyarilar}
            )
        except Exception as e:
            logger.error(f"Otomatik plan (slot): {e}")
            return SonucYonetici.hata(e, "NobetService.otomatik_plan_olustur")

    def taslak_temizle(self, yil: int, ay: int,
                       birim_adi: Optional[str] = None) -> SonucYonetici:
        """Onaylanmamış taslak nöbetleri direkt SQL ile siler."""
        try:
            ay_bas = f"{yil:04d}-{ay:02d}-01"
            ay_bit = f"{yil:04d}-{ay:02d}-31"

            repo = self._r.get("Nobet_Plan")
            if birim_adi:
                cur = repo.db.execute(
                    "DELETE FROM Nobet_Plan "
                    "WHERE NobetTarihi BETWEEN ? AND ? "
                    "AND Durum = 'taslak' AND BirimAdi = ?",
                    (ay_bas, ay_bit, birim_adi)
                )
            else:
                cur = repo.db.execute(
                    "DELETE FROM Nobet_Plan "
                    "WHERE NobetTarihi BETWEEN ? AND ? "
                    "AND Durum = 'taslak'",
                    (ay_bas, ay_bit)
                )
            silinen = cur.rowcount
            return SonucYonetici.tamam(f"{silinen} taslak silindi")
        except Exception as e:
            return SonucYonetici.hata(e, "NobetService.taslak_temizle")

    def onay_getir(self, yil: int, ay: int,
                   birim_adi: Optional[str] = None) -> SonucYonetici:
        try:
            rows = self._r.get("Nobet_Onay").get_all() or []
            rows = [r for r in rows
                    if r.get("Yil") == yil and r.get("Ay") == ay
                    and (not birim_adi or r.get("BirimAdi") == birim_adi)]
            return SonucYonetici.tamam(veri=rows)
        except Exception as e:
            return SonucYonetici.hata(e, "NobetService.onay_getir")

    def onayla(self, yil: int, ay: int, birim_adi: str,
               onaylayan_id: str) -> SonucYonetici:
        try:
            from datetime import datetime as _dt
            rows = self._r.get("Nobet_Plan").get_all() or []
            ay_bas = f"{yil:04d}-{ay:02d}-01"
            ay_bit = f"{yil:04d}-{ay:02d}-31"
            onaylanan = 0
            for r in rows:
                if (ay_bas <= str(r.get("NobetTarihi","")) <= ay_bit
                        and r.get("BirimAdi") == birim_adi
                        and r.get("Durum") == "taslak"):
                    self._r.get("Nobet_Plan").update(
                        r["PlanID"], {"Durum": "onaylandi"}
                    )
                    onaylanan += 1

            onay_rows = self._r.get("Nobet_Onay").get_all() or []
            mevcut = next(
                (o for o in onay_rows
                 if o.get("Yil") == yil and o.get("Ay") == ay
                 and o.get("BirimAdi") == birim_adi),
                None
            )
            onay_veri = {
                "Durum":       "onaylandi",
                "OnaylayanID": onaylayan_id,
                "OnayTarihi":  _dt.now().isoformat(),
            }
            if mevcut:
                self._r.get("Nobet_Onay").update(mevcut["OnayID"], onay_veri)
            else:
                onay_veri.update({
                    "OnayID":   _yeni_id("ONY-"),
                    "Yil":      yil,
                    "Ay":       ay,
                    "BirimAdi": birim_adi,
                })
                self._r.get("Nobet_Onay").insert(onay_veri)

            return SonucYonetici.tamam(
                f"{onaylanan} nöbet onaylandı ({yil}/{ay:02d} - {birim_adi})"
            )
        except Exception as e:
            return SonucYonetici.hata(e, "NobetService.onayla")

    # ═══════════════════════════════════════════════════
    #  İSTATİSTİK
    # ═══════════════════════════════════════════════════

    def personel_nobet_ozeti(self, yil: int, ay: int,
                              birim_adi: Optional[str] = None) -> SonucYonetici:
        try:
            plan = self.get_plan(yil, ay, birim_adi)
            if not plan.basarili:
                return plan
            rows = plan.veri or []

            # Vardiya saat haritası
            v_rows = self._r.get("Nobet_Vardiya").get_all() or []
            v_saat = {v["VardiyaID"]: float(v.get("SaatSuresi", GUNLUK_HEDEF_SAAT))
                      for v in v_rows}

            # Personel adları
            p_rows = self._r.get("Personel").get_all() or []
            p_ad   = {str(p["KimlikNo"]): p.get("AdSoyad", "") for p in p_rows}

            ozet: dict[str, dict] = {}
            for r in rows:
                pid = r.get("PersonelID", "")
                if pid not in ozet:
                    ozet[pid] = {
                        "PersonelID":  pid,
                        "AdSoyad":     p_ad.get(pid, pid),
                        "NobetSayisi": 0,
                        "ToplamSaat":  0.0,
                        "FazlaMesai":  0,
                    }
                ozet[pid]["NobetSayisi"] += 1
                ozet[pid]["ToplamSaat"]  += v_saat.get(r.get("VardiyaID",""), GUNLUK_HEDEF_SAAT)
                if r.get("NobetTuru") == "fazla_mesai":
                    ozet[pid]["FazlaMesai"] += 1

            return SonucYonetici.tamam(
                veri=sorted(ozet.values(),
                            key=lambda x: x["ToplamSaat"], reverse=True)
            )
        except Exception as e:
            return SonucYonetici.hata(e, "NobetService.personel_nobet_ozeti")

    # ═══════════════════════════════════════════════════
    #  İÇ YARDIMCILAR
    # ═══════════════════════════════════════════════════

    def _kisit_kontrol(self, personel_id: str, tarih: str,
                       birim_adi: str, vardiya_id: str,
                       nobet_turu: str = "normal") -> Optional[str]:
        """
        Kısıt kontrolü yapar. Sorun varsa mesaj döner, yoksa None.
        fazla_mesai türü için izin ve üst üste kontrolü atlanır.
        """
        if nobet_turu == "fazla_mesai":
            return None  # Fazla mesaiye kısıt uygulanmaz

        tarih_obj = date.fromisoformat(tarih)

        # İzin / rapor kontrolü
        izin_rows = self._r.get("Izin_Giris").get_all() or []
        for izin in izin_rows:
            if str(izin.get("Personelid","")) != personel_id:
                continue
            if izin.get("Durum", "") in ("İptal", "Reddedildi"):
                continue
            try:
                bas = date.fromisoformat(str(izin.get("BaslamaTarihi","")))
                bit = date.fromisoformat(str(izin.get("BitisTarihi","")))
                if bas <= tarih_obj <= bit:
                    return f"Personel {personel_id} bu tarihte izinli ({izin.get('IzinTipi','')})"
            except Exception:
                continue

        # Üst üste nöbet kontrolü
        dun = (tarih_obj - timedelta(days=1)).isoformat()
        plan_rows = self._r.get("Nobet_Plan").get_all() or []
        for r in plan_rows:
            if (str(r.get("PersonelID","")) == personel_id
                    and str(r.get("NobetTarihi","")) == dun
                    and r.get("Durum") != "iptal"):
                return f"Personel {personel_id} dün de nöbet tuttu (üst üste yasak)"

        # NOT: Aylık saat limiti burada kontrol edilmez.
        # Saat, mesai hesabı için izlenir; atama kısıtı gün sayısı üzerinden yapılır.

        return None

    def _izin_map_getir(self, yil: int, ay: int) -> dict[str, set[str]]:
        """Personel başına o ay geçerli izin günlerini döner."""
        ay_bas = date(yil, ay, 1)
        ay_bit = date(yil, ay + 1, 1) - timedelta(days=1) if ay < 12 \
                 else date(yil, 12, 31)
        izin_map: dict[str, set[str]] = {}
        try:
            for izin in (self._r.get("Izin_Giris").get_all() or []):
                pid = str(izin.get("Personelid", ""))
                if izin.get("Durum","") in ("İptal","Reddedildi"):
                    continue
                try:
                    bas = date.fromisoformat(str(izin.get("BaslamaTarihi","")))
                    bit = date.fromisoformat(str(izin.get("BitisTarihi","")))
                except Exception:
                    continue
                gun = max(bas, ay_bas)
                while gun <= min(bit, ay_bit):
                    izin_map.setdefault(pid, set()).add(gun.isoformat())
                    gun += timedelta(days=1)
        except Exception as e:
            logger.warning(f"İzin map hatası: {e}")
        return izin_map

    # ═══════════════════════════════════════════════════
    #  MESAİ HEDEF
    # ═══════════════════════════════════════════════════

    def _kisi_hedef_saat(self, personel_id: str,
                         yil: int, ay: int,
                         otomatik: bool = False) -> Optional[float]:
        """
        Kişiye özgü hedef saati döner.

        Nobet_MesaiHedef tablosunda kayıt varsa → o değeri kullanır.
        Kayıt yoksa:
          - otomatik=False → None döner (çağıran fallback uygular)
          - otomatik=True  → (iş_günü - izin_günü) × GUNLUK_HEDEF_SAAT hesaplar
        """
        try:
            rows = self._r.get("Nobet_MesaiHedef").get_all() or []
            for r in rows:
                if (str(r.get("PersonelID","")) == personel_id
                        and r.get("Yil") == yil and r.get("Ay") == ay):
                    return float(r.get("HedefSaat", 0.0))
        except Exception:
            pass

        if not otomatik:
            return None

        # Tabloda kayıt yok → izin günleri düşülmüş iş günü hesapla
        try:
            sonuc = self.personel_max_nobet_gunu(personel_id, yil, ay)
            if sonuc.basarili:
                veri = sonuc.veri
                net_gun = veri["IsGunu"] - veri["IzinGunu"]
                return max(0.0, net_gun * GUNLUK_HEDEF_SAAT)
        except Exception:
            pass
        return None

    def birim_ayar_kaydet(self, birim_adi: str,
                          gunluk_slot_saat: Optional[float],
                          slot_basi_personel: int = 4,
                          calisma_modu: str = "tam_gun",
                          aciklama: str = "") -> SonucYonetici:
        """Birim nöbet ayarlarını kaydeder."""
        try:
            rows = self._r.get("Nobet_BirimAyar").get_all() or []
            mevcut = next((r for r in rows
                           if r.get("BirimAdi") == birim_adi), None)
            veri = {
                "BirimAdi":         birim_adi,
                "GunlukSlotSaat":   gunluk_slot_saat,
                "SlotBasiPersonel": slot_basi_personel,
                "CalismaModu":      calisma_modu,
                "Aciklama":         aciklama,
            }
            if mevcut:
                self._r.get("Nobet_BirimAyar").update(mevcut["AyarID"], veri)
            else:
                veri["AyarID"] = _yeni_id("BA-")
                self._r.get("Nobet_BirimAyar").insert(veri)
            return SonucYonetici.tamam(
                f"{birim_adi} ayarları kaydedildi "
                f"({calisma_modu}, {gunluk_slot_saat or 'oto'}h/slot, "
                f"{slot_basi_personel} personel)"
            )
        except Exception as e:
            return SonucYonetici.hata(e, "NobetService.birim_ayar_kaydet")

    def birim_ayar_kaydet(self, birim_adi: str,
                          slot_saat: Optional[float],
                          slot_personel: int = 4,
                          calisma_modu: str = "tam_gun",
                          otomatik_bolunme: bool = True,
                          aciklama: str = "") -> SonucYonetici:
        """Birim nöbet ayarlarını kaydeder/günceller."""
        try:
            rows = self._r.get("Nobet_BirimAyar").get_all() or []
            mevcut = next((r for r in rows
                           if r.get("BirimAdi") == birim_adi), None)
            veri = {
                "BirimAdi":        birim_adi,
                "GunlukSlotSaat":  slot_saat,
                "SlotBasiPersonel": slot_personel,
                "CalismaModu":     calisma_modu,
                "OtomatikBolunme": 1 if otomatik_bolunme else 0,
                "Aciklama":        aciklama,
            }
            if mevcut:
                self._r.get("Nobet_BirimAyar").update(mevcut["AyarID"], veri)
            else:
                veri["AyarID"] = _yeni_id("BA-")
                self._r.get("Nobet_BirimAyar").insert(veri)
            return SonucYonetici.tamam(
                f"{birim_adi} ayarları kaydedildi "
                f"({calisma_modu}, "
                f"{slot_saat or 'oto'}h/slot, "
                f"{slot_personel} personel)"
            )
        except Exception as e:
            return SonucYonetici.hata(e, "NobetService.birim_ayar_kaydet")

    def birim_ayar_getir(self, birim_adi: str) -> Optional[dict]:
        """Birim ayarını döner. Kayıt yoksa None."""
        try:
            rows = self._r.get("Nobet_BirimAyar").get_all() or []
            return next((r for r in rows if r.get("BirimAdi") == birim_adi), None)
        except Exception:
            return None

    def _slot_saat_hesapla(self, birim_adi: str,
                           vardiyalar: list[dict],
                           ayar: Optional[dict]) -> float:
        """
        Bir slotun kaç saat süreceğini hesaplar.
        Öncelik: BirimAyar.GunlukSlotSaat → Σ vardiya.SaatSuresi
        """
        if ayar and ayar.get("GunlukSlotSaat"):
            return float(ayar["GunlukSlotSaat"])
        return sum(float(v.get("SaatSuresi", 0)) for v in vardiyalar)

    def _tercih_map_getir(self, yil: int, ay: int) -> dict[str, str]:
        """Personel bazlı NobetTercihi haritası döner. {pid: tercih}"""
        try:
            rows = self._r.get("Nobet_MesaiHedef").get_all() or []
            return {
                str(r.get("PersonelID","")): str(r.get("NobetTercihi","zorunlu"))
                for r in rows
                if r.get("Yil") == yil and r.get("Ay") == ay
            }
        except Exception:
            return {}

    def mesai_hedef_kaydet(self, personel_id: str, yil: int, ay: int,
                           hedef_saat: float, hedef_tipi: str = "normal",
                           birim_adi: str = "", aciklama: str = "",
                           nobet_tercihi: str = "zorunlu") -> SonucYonetici:
        """
        Kişiye özgü aylık hedef saati ve nöbet tercihini kaydeder.
        nobet_tercihi: zorunlu | gonullu_disi | nobet_yok
        """
        try:
            rows = self._r.get("Nobet_MesaiHedef").get_all() or []
            mevcut = next(
                (r for r in rows
                 if str(r.get("PersonelID","")) == personel_id
                 and r.get("Yil") == yil and r.get("Ay") == ay),
                None
            )
            veri = {
                "PersonelID":    personel_id,
                "Yil":           yil,
                "Ay":            ay,
                "BirimAdi":      birim_adi,
                "HedefSaat":     hedef_saat,
                "HedefTipi":     hedef_tipi,
                "Aciklama":      aciklama,
                "NobetTercihi":  nobet_tercihi,
            }
            if mevcut:
                self._r.get("Nobet_MesaiHedef").update(mevcut["HedefID"], veri)
            else:
                veri["HedefID"] = _yeni_id("HDF-")
                self._r.get("Nobet_MesaiHedef").insert(veri)
            return SonucYonetici.tamam(
                f"{personel_id} — {yil}/{ay:02d} hedef: {hedef_saat} saat "
                f"({hedef_tipi} / {nobet_tercihi})"
            )
        except Exception as e:
            return SonucYonetici.hata(e, "NobetService.mesai_hedef_kaydet")

    def mesai_hedef_getir(self, yil: int, ay: int,
                          birim_adi: Optional[str] = None) -> SonucYonetici:
        """O ay + birim için tüm hedef kayıtlarını döner."""
        try:
            rows = self._r.get("Nobet_MesaiHedef").get_all() or []
            rows = [r for r in rows
                    if r.get("Yil") == yil and r.get("Ay") == ay
                    and (not birim_adi or r.get("BirimAdi") == birim_adi)]
            return SonucYonetici.tamam(veri=rows)
        except Exception as e:
            return SonucYonetici.hata(e, "NobetService.mesai_hedef_getir")

    # ═══════════════════════════════════════════════════
    #  FAZLA MESAİ
    # ═══════════════════════════════════════════════════

    def fazla_mesai_hesapla(self, yil: int, ay: int,
                            birim_adi: Optional[str] = None) -> SonucYonetici:
        """
        Onaylanmış plan üzerinden kişi bazlı fazla mesai hesaplar ve kaydeder.

        Algoritma:
          Çalışılan Saat  = Σ vardiya.SaatSuresi (onaylı nöbetler)
          Hedef Saat      = Nobet_MesaiHedef'ten || iş_günü × 7
          Bu Ay Fazla     = Çalışılan − Hedef  (negatif olabilir = eksik)
          Önceki Devir    = önceki ayın DevireGiden değeri
          Toplam Fazla    = Bu Ay Fazla + Önceki Devir

          Ödeme kuralı (7 saat blok):
            Toplam Fazla ≥ 7  → Ödenen    = floor(Toplam / 7) × 7
                                 DevireGiden = Toplam % 7
            Toplam Fazla < 7  → Ödenen    = 0
                                 DevireGiden = Toplam  (< 7, + alacaklı / - verecekli)
        """
        try:
            plan = self.get_plan(yil, ay, birim_adi)
            plan_rows = [r for r in (plan.veri or [])
                         if r.get("Durum") == "onaylandi"]

            # Vardiya saat haritası
            v_rows = self._r.get("Nobet_Vardiya").get_all() or []
            v_saat = {v["VardiyaID"]: float(v.get("SaatSuresi", GUNLUK_HEDEF_SAAT))
                      for v in v_rows}

            # Personel bazlı çalışılan saat
            calisan: dict[str, float] = {}
            for r in plan_rows:
                pid  = r.get("PersonelID", "")
                vsid = r.get("VardiyaID", "")
                calisan[pid] = calisan.get(pid, 0.0) + v_saat.get(vsid, GUNLUK_HEDEF_SAAT)

            tatiller   = self._tatil_listesi_getir(yil, ay)
            from core.hesaplamalar import ay_is_gunu
            is_gunu_ay = ay_is_gunu(yil, ay, tatil_listesi=tatiller)

            # Önceki aydan DevireGiden
            prev_yil, prev_ay = (yil - 1, 12) if ay == 1 else (yil, ay - 1)
            prev_rows  = self._r.get("Nobet_FazlaMesai").get_all() or []
            devir_map: dict[str, float] = {
                str(r.get("PersonelID","")): float(r.get("DevireGiden", 0.0))
                for r in prev_rows
                if r.get("Yil") == prev_yil and r.get("Ay") == prev_ay
                and (not birim_adi or r.get("BirimAdi") == birim_adi)
            }

            mevcut_rows = self._r.get("Nobet_FazlaMesai").get_all() or []
            sonuclar    = []
            tum_pid     = set(calisan.keys()) | set(devir_map.keys())

            for pid in tum_pid:
                calisan_saat = calisan.get(pid, 0.0)
                hedef = self._kisi_hedef_saat(pid, yil, ay, otomatik=True)
                if hedef is None:
                    hedef = is_gunu_ay * GUNLUK_HEDEF_SAAT

                bu_ay_fazla  = calisan_saat - hedef
                devir        = devir_map.get(pid, 0.0)
                toplam       = bu_ay_fazla + devir

                # OdenenSaat kullanıcı tarafından girilir — burada 0 bırakılır
                # DevireGiden = ToplamFazla - OdenenSaat (güncelle_odenen ile set edilir)
                mevcut = next(
                    (r for r in mevcut_rows
                     if str(r.get("PersonelID","")) == pid
                     and r.get("Yil") == yil and r.get("Ay") == ay),
                    None
                )
                # Mevcut kayıtta OdenenSaat varsa koru (kullanıcı girmişse sıfırlama)
                odenen_mevcut = float(mevcut.get("OdenenSaat", 0.0)) if mevcut else 0.0
                devire_giden  = toplam - odenen_mevcut

                veri = {
                    "PersonelID":     pid,
                    "Yil":            yil,
                    "Ay":             ay,
                    "BirimAdi":       birim_adi or "",
                    "CalisanSaat":    calisan_saat,
                    "HedefSaat":      hedef,
                    "FazlaMesaiSaat": bu_ay_fazla,
                    "DevirSaat":      devir,
                    "ToplamFazla":    toplam,
                    "OdenenSaat":     odenen_mevcut,   # kullanıcı girdisi korunur
                    "DevireGiden":    devire_giden,
                }
                if mevcut:
                    self._r.get("Nobet_FazlaMesai").update(mevcut["FazlaID"], veri)
                else:
                    veri["FazlaID"] = _yeni_id("FZ-")
                    self._r.get("Nobet_FazlaMesai").insert(veri)

                sonuclar.append(veri)

            odenen_toplam = sum(r["OdenenSaat"] for r in sonuclar)
            return SonucYonetici.tamam(
                mesaj=(f"{len(sonuclar)} personel hesaplandı | "
                       f"Ödenen toplam: {odenen_toplam:.0f} saat"),
                veri=sonuclar
            )
        except Exception as e:
            return SonucYonetici.hata(e, "NobetService.fazla_mesai_hesapla")

    def odenen_guncelle(self, personel_id: str, yil: int, ay: int,
                        odenen_saat: float) -> SonucYonetici:
        """
        Kullanıcı tarafından girilen ödenen saati kaydeder.
        DevireGiden = ToplamFazla - OdenenSaat otomatik güncellenir.
        """
        try:
            rows = self._r.get("Nobet_FazlaMesai").get_all() or []
            kayit = next(
                (r for r in rows
                 if str(r.get("PersonelID","")) == personel_id
                 and r.get("Yil") == yil and r.get("Ay") == ay),
                None
            )
            if not kayit:
                return SonucYonetici.hata(
                    ValueError("Fazla mesai kaydı bulunamadı — önce hesaplayın")
                )
            toplam      = float(kayit.get("ToplamFazla", 0.0))
            devire_giden = toplam - odenen_saat
            self._r.get("Nobet_FazlaMesai").update(kayit["FazlaID"], {
                "OdenenSaat":  odenen_saat,
                "DevireGiden": devire_giden,
            })
            return SonucYonetici.tamam(
                mesaj=f"Ödenen: {odenen_saat:.1f} saat | Devire giden: {devire_giden:.1f} saat",
                veri={"OdenenSaat": odenen_saat, "DevireGiden": devire_giden}
            )
        except Exception as e:
            return SonucYonetici.hata(e, "NobetService.odenen_guncelle")

    def fazla_mesai_getir(self, yil: int, ay: int,
                          birim_adi: Optional[str] = None) -> SonucYonetici:
        """O ay fazla mesai kayıtlarını personel adı ile döner."""
        try:
            rows = self._r.get("Nobet_FazlaMesai").get_all() or []
            rows = [r for r in rows
                    if r.get("Yil") == yil and r.get("Ay") == ay
                    and (not birim_adi or r.get("BirimAdi") == birim_adi)]
            p_rows = self._r.get("Personel").get_all() or []
            p_ad   = {str(p["KimlikNo"]): p.get("AdSoyad","") for p in p_rows}
            for r in rows:
                r["AdSoyad"] = p_ad.get(str(r.get("PersonelID","")), "")
                # Geriye dönük uyumluluk: eski kayıtlarda DevireGiden yoksa
                if "DevireGiden" not in r or r["DevireGiden"] is None:
                    r["DevireGiden"] = r.get("ToplamFazla", 0.0)
                if "OdenenSaat" not in r or r["OdenenSaat"] is None:
                    r["OdenenSaat"] = 0.0
            return SonucYonetici.tamam(
                veri=sorted(rows, key=lambda r: r.get("AdSoyad",""))
            )
        except Exception as e:
            return SonucYonetici.hata(e, "NobetService.fazla_mesai_getir")

    def _tatil_listesi_getir(self, yil: int, ay: int,
                             idari_dahil: bool = True,
                             sadece_dini: bool = False) -> list[str]:
        """
        Tatiller tablosundan o aya ait tatil tarihlerini döner.

        TatilTuru değerleri:
          Resmi      → Devlet tatili (iş günü hesabına girer)
          Idari      → Kurum izni (iş günü hesabına girer)
          DiniBayram → Dini bayram (iş günü hesabına girer AMA
                       otomatik nöbet ataması yapılmaz)

        idari_dahil=True  → Resmi + Idari + DiniBayram
        idari_dahil=False → sadece Resmi + DiniBayram
        sadece_dini=True  → sadece DiniBayram
        """
        try:
            rows   = self._r.get("Tatiller").get_all() or []
            ay_bas = f"{yil:04d}-{ay:02d}-01"
            ay_bit = f"{yil:04d}-{ay:02d}-31"
            result = []
            for r in rows:
                t    = str(r.get("Tarih", "") or r.get("tarih", "")).strip()
                turu = str(r.get("TatilTuru", "Resmi")).strip()
                if not (ay_bas <= t <= ay_bit):
                    continue
                if sadece_dini:
                    if turu == "DiniBayram":
                        result.append(t)
                elif turu == "Resmi":
                    result.append(t)
                elif turu == "DiniBayram":
                    result.append(t)   # iş günü hesabında düşülür
                elif turu == "Idari" and idari_dahil:
                    result.append(t)
            return result
        except Exception as e:
            logger.debug(f"Tatil listesi: {e}")
            return []

    def personel_max_nobet_gunu(
        self, personel_id: str, yil: int, ay: int
    ) -> SonucYonetici:
        """
        Bir personelin o ayda tutabileceği maksimum nöbet gün sayısını hesaplar.

        Hesaplama:
          Ay toplam günleri
          - Hafta sonları (Cumartesi + Pazar)
          - Resmi tatiller (Tatiller tablosu)
          - Personelin onaylı izin günleri (Izin_Giris tablosu)
          = Çalışılabilir gün sayısı (= max nöbet gün sayısı üst sınırı)
        """
        try:
            from core.hesaplamalar import ay_is_gunu

            # Tatil listesi
            tatiller = self._tatil_listesi_getir(yil, ay)

            # Temel iş günü sayısı (hafta sonları + tatiller düşülmüş)
            is_gunu = ay_is_gunu(yil, ay, tatil_listesi=tatiller)

            # Personelin izin günlerini düş
            izin_map  = self._izin_map_getir(yil, ay)
            izin_gunleri = izin_map.get(personel_id, set())

            # İzin günlerinden hafta sonu ve tatil olmayanları say
            # (hafta sonu ve tatiller zaten is_gunu'ndan düşüldü)
            import calendar
            izin_is_gunu = 0
            for t_str in izin_gunleri:
                try:
                    t = date.fromisoformat(t_str)
                    if t.weekday() < 5 and t_str not in tatiller:
                        izin_is_gunu += 1
                except Exception:
                    pass

            max_gun = max(0, is_gunu - izin_is_gunu)
            return SonucYonetici.tamam(veri={
                "PersonelID":  personel_id,
                "Yil":         yil,
                "Ay":          ay,
                "IsGunu":      is_gunu,
                "IzinGunu":    izin_is_gunu,
                "TatilGunu":   len(tatiller),
                "MaxNobetGun": max_gun,
            })
        except Exception as e:
            return SonucYonetici.hata(e, "NobetService.personel_max_nobet_gunu")

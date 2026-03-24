"""
nobet_adapter.py — Geçiş dönemi uyumluluk katmanı

UI sayfaları get_nobet_service() çağrısını kullanmaya devam eder.
Bu adapter NB_ servislerini (birim, tercih, vardiya, plan, mesai)
tek bir nesnede toplar ve eski arayüzü karşılar.

Geçiş tamamlanınca UI sayfaları doğrudan NB_ servislerini çağıracak.
"""
from __future__ import annotations

from typing import Optional

from core.hata_yonetici import SonucYonetici, logger
from core.services.nobet.nb_birim_service   import NbBirimService
from core.services.nobet.nb_tercih_service  import NbTercihService
from core.services.nobet.nb_vardiya_service import NbVardiyaService
from core.services.nobet.nb_plan_service    import NbPlanService
from core.services.nobet.nb_mesai_service   import NbMesaiService
from database.repository_registry import RepositoryRegistry


class NobetAdapter:
    """
    Tüm NB_ servislerini tek nesnede toplar.
    UI sayfaları bu nesneyi `svc` olarak kullanır.

    Mevcut `svc._r.get(...)` çağrıları doğrudan çalışır —
    adapter aynı registry'yi paylaşır.
    """

    def __init__(self, registry: RepositoryRegistry):
        self._r       = registry   # UI'daki svc._r.get(...) için
        self.birim    = NbBirimService(registry)
        self.tercih   = NbTercihService(registry)
        self.vardiya  = NbVardiyaService(registry)
        self.plan     = NbPlanService(registry)
        self.mesai    = NbMesaiService(registry)

    # ──────────────────────────────────────────────────────────
    #  Birim
    # ──────────────────────────────────────────────────────────

    def get_birimler(self) -> SonucYonetici:
        return self.birim.get_birimler()

    # ──────────────────────────────────────────────────────────
    #  Vardiya
    # ──────────────────────────────────────────────────────────

    def get_vardiyalar(self, birim_id: Optional[str] = None) -> SonucYonetici:
        """
        birim_id: NB_Birim.BirimID veya eski BirimAdi (geçiş dönemi).
        BirimAdi gelirse BirimID'ye çevirir.
        """
        if not birim_id:
            return SonucYonetici.tamam(veri=[])
        bid = self._birim_id_coz(birim_id)
        if not bid:
            return SonucYonetici.tamam(veri=[])
        return self.vardiya.get_vardiyalar(bid)

    def get_gruplar(self, birim_id: str) -> SonucYonetici:
        bid = self._birim_id_coz(birim_id)
        if not bid:
            return SonucYonetici.tamam(veri=[])
        return self.vardiya.get_gruplar(bid)

    # ──────────────────────────────────────────────────────────
    #  Plan
    # ──────────────────────────────────────────────────────────

    def get_plan(self, yil: int, ay: int,
                 birim: Optional[str] = None) -> SonucYonetici:
        """
        birim: BirimID veya BirimAdi.
        Plan satırlarını döner (NB_PlanSatir + NB_Vardiya bilgisi join).
        """
        try:
            if not birim:
                return SonucYonetici.tamam(veri=[])
            bid     = self._birim_id_coz(birim)
            if not bid:
                return SonucYonetici.tamam(veri=[])
            plan    = self.plan.get_plan(bid, yil, ay)
            if not plan:
                return SonucYonetici.tamam(veri=[])
            sonuc = self.plan.get_satirlar(plan["PlanID"])
            # Vardiya bilgisi ekle (UI VardiyaAdi / BasSaat kullanıyor)
            v_rows = self._r.get("NB_Vardiya").get_all() or []
            v_map  = {v["VardiyaID"]: dict(v) for v in v_rows}
            satirlar = []
            for s in (sonuc.veri or []):
                v = v_map.get(s.get("VardiyaID"), {})
                satirlar.append({
                    **s,
                    "BirimID":   bid,
                    "VardiyaAdi": v.get("VardiyaAdi", ""),
                    "BasSaat":   v.get("BasSaat", ""),
                    "BitSaat":   v.get("BitSaat", ""),
                    "SureDakika": v.get("SureDakika", 0),
                    "VardiyaRolu": v.get("Rol", "ana"),
                    # Eski alan adlarını da ekle (UI uyumu)
                    "NobetTarihi": s.get("NobetTarihi", ""),
                    "PersonelID":  s.get("PersonelID", ""),
                })
            return SonucYonetici.tamam(veri=satirlar)
        except Exception as e:
            return SonucYonetici.hata(e, "NobetAdapter.get_plan")

    def plan_ekle(self, veri: dict) -> SonucYonetici:
        """Manuel nöbet ekleme — UI'dan gelen veri."""
        try:
            birim   = str(veri.get("BirimID") or veri.get("BirimAdi", ""))
            bid     = self._birim_id_coz(birim)
            yil     = int(str(veri.get("NobetTarihi", ""))[:4] or 0)
            ay      = int(str(veri.get("NobetTarihi", ""))[5:7] or 0)
            plan_s  = self.plan.plan_al_veya_olustur(bid, yil, ay)
            if not plan_s.basarili:
                return plan_s
            plan_id = plan_s.veri["PlanID"]
            return self.plan.satir_ekle(
                plan_id      = plan_id,
                personel_id  = str(veri.get("PersonelID", "")),
                vardiya_id   = str(veri.get("VardiyaID", "")),
                nobet_tarihi = str(veri.get("NobetTarihi", "")),
                kaynak       = "manuel",
                nobet_turu   = str(veri.get("NobetTuru", "normal")),
                notlar       = str(veri.get("Notlar", "")),
            )
        except Exception as e:
            return SonucYonetici.hata(e, "NobetAdapter.plan_ekle")

    def plan_iptal(self, satir_id: str) -> SonucYonetici:
        return self.plan.satir_iptal(satir_id)

    def taslak_temizle(self, yil: int, ay: int,
                       birim: Optional[str] = None) -> SonucYonetici:
        if not birim:
            return SonucYonetici.tamam("Birim belirtilmedi")
        bid = self._birim_id_coz(birim)
        if not bid:
            return SonucYonetici.tamam("Birim bulunamadı")
        return self.plan.taslak_temizle(bid, yil, ay)

    def onay_getir(self, yil: int, ay: int,
                   birim: Optional[str] = None) -> SonucYonetici:
        try:
            if not birim:
                return SonucYonetici.tamam(veri=[])
            bid    = self._birim_id_coz(birim)
            durum  = self.plan.onay_durumu(bid, yil, ay)
            return SonucYonetici.tamam(veri=[{"Durum": durum}])
        except Exception as e:
            return SonucYonetici.hata(e, "NobetAdapter.onay_getir")

    def onayla(self, yil: int, ay: int, birim: str,
               onaylayan_id: str) -> SonucYonetici:
        bid = self._birim_id_coz(birim)
        if not bid:
            return SonucYonetici.hata(ValueError(f"Birim bulunamadı: {birim}"))
        return self.plan.onayla(bid, yil, ay, onaylayan_id)

    # ──────────────────────────────────────────────────────────
    #  Personel Tercih / Mesai Hedef
    # ──────────────────────────────────────────────────────────

    def _tercih_map_getir(self, yil: int, ay: int,
                          birim: Optional[str] = None) -> dict[str, str]:
        if not birim:
            return {}
        bid = self._birim_id_coz(birim)
        if not bid:
            return {}
        return self.tercih.tercih_map_getir(bid, yil, ay)

    def sadece_tercih_guncelle(self, personel_id: str, yil: int, ay: int,
                                nobet_tercihi: str,
                                birim: str = "") -> SonucYonetici:
        """
        Sadece NobetTercihi alanını günceller.
        Kayıt yoksa otomatik hedef hesaplayarak oluşturur.
        """
        bid = self._birim_id_coz(birim) if birim else \
              self._personelin_birim_id(personel_id)
        if not bid:
            return SonucYonetici.hata(ValueError("Birim bulunamadı"))
        return self.tercih.sadece_tercih_guncelle(
            personel_id, bid, yil, ay, nobet_tercihi)

    def mesai_hedef_kaydet(self, personel_id: str, yil: int, ay: int,
                           hedef_saat: float = 0.0,
                           hedef_tipi: str = "normal",
                           birim_adi: str = "",
                           nobet_tercihi: str = "zorunlu",
                           aciklama: str = "") -> SonucYonetici:
        """Eski arayüz — saat → dakikaya çevirip NB_PersonelTercih'e yazar."""
        bid = self._birim_id_coz(birim_adi) if birim_adi else ""
        if not bid:
            return SonucYonetici.hata(ValueError(f"Birim bulunamadı: {birim_adi}"))
        hedef_dk = int(hedef_saat * 60) if hedef_saat else None
        return self.tercih.tercih_kaydet(
            personel_id   = personel_id,
            birim_id      = bid,
            yil           = yil,
            ay            = ay,
            nobet_tercihi = nobet_tercihi,
            hedef_dakika  = hedef_dk,
            hedef_tipi    = hedef_tipi,
            notlar        = aciklama,
        )

    def mesai_hedef_getir(self, yil: int, ay: int,
                          birim_adi: Optional[str] = None) -> SonucYonetici:
        """NB_PersonelTercih kayıtlarını eski MesaiHedef formatında döner."""
        try:
            bid = self._birim_id_coz(birim_adi) if birim_adi else ""
            rows = self._r.get("NB_PersonelTercih").get_all() or []
            ilgili = [r for r in rows
                      if int(r.get("Yil", 0)) == yil
                      and int(r.get("Ay",  0)) == ay
                      and (not bid or str(r.get("BirimID","")) == bid)]
            # Eski format: HedefSaat (saat cinsinden)
            sonuc = []
            for r in ilgili:
                dk = int(r.get("HedefDakika") or 0)
                sonuc.append({
                    "HedefID":      r.get("TercihID",""),
                    "PersonelID":   r.get("PersonelID",""),
                    "Yil":          r.get("Yil"),
                    "Ay":           r.get("Ay"),
                    "BirimAdi":     self._birim_adi_bul(str(r.get("BirimID",""))),
                    "HedefSaat":    round(dk / 60, 2),
                    "HedefTipi":    r.get("HedefTipi","normal"),
                    "NobetTercihi": r.get("NobetTercihi","zorunlu"),
                    "Aciklama":     r.get("Notlar",""),
                })
            return SonucYonetici.tamam(veri=sonuc)
        except Exception as e:
            return SonucYonetici.hata(e, "NobetAdapter.mesai_hedef_getir")

    def _kisi_hedef_saat(self, personel_id: str, yil: int,
                         ay: int, otomatik: bool = False,
                         birim_id: str = "") -> Optional[float]:
        """
        Personelin hedef saatini döner.

        otomatik=False → NB_PersonelTercih'ten (elle girilmiş değer)
        otomatik=True  → İzin günleri düşülerek HESAPLA (tabloyu atla)
                         Özet ve mesai sayfaları için doğru değer bu.
        """
        if otomatik:
            # Tabloyu atla — her zaman güncel izin verisinden hesapla
            try:
                from core.hesaplamalar import ay_is_gunu
                tatiller = self.tercih._tatil_listesi_getir(yil, ay)
                is_gunu  = ay_is_gunu(yil, ay, tatil_listesi=tatiller)
                izin_gun = self.tercih._izin_is_gunu(
                    personel_id, yil, ay, tatiller)
                net_gun  = max(0, is_gunu - izin_gun)
                return round(net_gun * 7.0, 2)
            except Exception:
                return None

        # otomatik=False → tablodaki elle girilmiş değer
        bid = birim_id or self._personelin_birim_id(personel_id)
        if not bid:
            return None
        dk = self.tercih.hedef_dakika_getir(
            personel_id, bid, yil, ay, otomatik=False)
        return round(dk / 60, 2) if dk is not None else None

    # ──────────────────────────────────────────────────────────
    #  Otomatik Plan
    # ──────────────────────────────────────────────────────────

    def otomatik_plan_olustur(self, yil: int, ay: int,
                               birim: str,
                               max_aylik_saat: float = 200.0) -> SonucYonetici:
        """NbAlgoritma'yı çağırır."""
        try:
            from core.services.nobet.nb_algoritma import NbAlgoritma
            bid = self._birim_id_coz(birim)
            if not bid:
                return SonucYonetici.hata(
                    ValueError(f"Birim bulunamadı: {birim}"))
            return NbAlgoritma(self._r).plan_olustur(bid, yil, ay)
        except Exception as e:
            return SonucYonetici.hata(e, "NobetAdapter.otomatik_plan_olustur")

    # ──────────────────────────────────────────────────────────
    #  Fazla Mesai
    # ──────────────────────────────────────────────────────────

    def personel_nobet_ozeti(self, yil: int, ay: int,
                             birim: Optional[str] = None) -> SonucYonetici:
        """
        O aydaki tüm personelin nöbet istatistiklerini döner.
        [{PersonelID, AdSoyad, NobetSayisi, ToplamSaat,
          HaftasonuSayisi, GunduzSayisi, GeceSayisi}]
        """
        try:
            bid     = self._birim_id_coz(birim) if birim else ""
            birim_adi = self._birim_adi_bul(bid) if bid else ""

            ay_bas  = f"{yil:04d}-{ay:02d}-01"
            ay_bit  = f"{yil:04d}-{ay:02d}-31"

            # Plan satırları
            ps_rows = self._r.get("NB_PlanSatir").get_all() or []
            # Onaylı planları bul (taslak satırlar özete girmez)
            pl_rows = self._r.get("NB_Plan").get_all() or []
            plan_ids = {
                r["PlanID"] for r in pl_rows
                if int(r.get("Yil", 0)) == yil
                and int(r.get("Ay",  0)) == ay
                and (not bid or str(r.get("BirimID","")) == bid)
                and r.get("Durum") in ("onaylandi", "yururlukte", "taslak")
            }
            # Taslak planlar dahil ama sadece aktif satırlar
            ilgili = [
                r for r in ps_rows
                if r.get("PlanID") in plan_ids
                and r.get("Durum") == "aktif"
            ]

            # Vardiya süre haritası
            v_rows = self._r.get("NB_Vardiya").get_all() or []
            v_sure = {
                str(v["VardiyaID"]): int(v.get("SureDakika", 0))
                for v in v_rows
            }
            v_bas = {
                str(v["VardiyaID"]): str(v.get("BasSaat","08:00"))
                for v in v_rows
            }

            # Personel adları
            p_rows = self._r.get("Personel").get_all() or []
            p_ad   = {str(p["KimlikNo"]): p.get("AdSoyad","") for p in p_rows}

            # Hafta sonu set
            from datetime import date
            HAFTASONU = {5, 6}

            # Personel bazlı istatistik
            ozet: dict[str, dict] = {}
            for s in ilgili:
                pid = str(s.get("PersonelID",""))
                vid = str(s.get("VardiyaID",""))
                tarih_str = str(s.get("NobetTarihi",""))
                dk  = v_sure.get(vid, 0)
                bas = v_bas.get(vid, "08:00")

                if pid not in ozet:
                    ozet[pid] = {
                        "PersonelID":     pid,
                        "AdSoyad":        p_ad.get(pid, ""),
                        "NobetSayisi":    0,
                        "ToplamSaat":     0.0,
                        "ToplamDakika":   0,
                        "HaftasonuSayisi":0,
                        "GunduzSayisi":   0,
                        "GeceSayisi":     0,
                    }
                try:
                    gun = date.fromisoformat(tarih_str)
                    if gun.weekday() in HAFTASONU:
                        ozet[pid]["HaftasonuSayisi"] += 1
                except Exception:
                    pass

                try:
                    saat = int(bas.split(":")[0])
                    if saat >= 20 or saat < 6:
                        ozet[pid]["GeceSayisi"] += 1
                    else:
                        ozet[pid]["GunduzSayisi"] += 1
                except Exception:
                    pass

                ozet[pid]["NobetSayisi"]  += 1
                ozet[pid]["ToplamDakika"] += dk
                ozet[pid]["ToplamSaat"]   = round(
                    ozet[pid]["ToplamDakika"] / 60, 2)

            return SonucYonetici.tamam(
                veri=sorted(ozet.values(),
                            key=lambda r: r.get("AdSoyad","")))
        except Exception as e:
            return SonucYonetici.hata(e, "NobetAdapter.personel_nobet_ozeti")

    def fazla_mesai_getir(self, yil: int, ay: int,
                          birim: Optional[str] = None) -> SonucYonetici:
        """NB_MesaiHesap'tan eski format döner."""
        try:
            bid   = self._birim_id_coz(birim) if birim else ""
            rows  = self._r.get("NB_MesaiHesap").get_all() or []
            ilgili = [
                r for r in rows
                if int(r.get("Yil", 0)) == yil
                and int(r.get("Ay",  0)) == ay
                and (not bid or str(r.get("BirimID","")) == bid)
            ]
            sonuc = []
            for r in ilgili:
                sonuc.append({
                    "FazlaID":       r.get("HesapID",""),
                    "PersonelID":    r.get("PersonelID",""),
                    "Yil":           r.get("Yil"),
                    "Ay":            r.get("Ay"),
                    "BirimAdi":      self._birim_adi_bul(
                                         str(r.get("BirimID",""))),
                    "CalisanSaat":   round(
                        int(r.get("CalisDakika",0))/60, 2),
                    "HedefSaat":     round(
                        int(r.get("HedefDakika",0))/60, 2),
                    "FazlaMesaiSaat":round(
                        int(r.get("FazlaDakika",0))/60, 2),
                    "DevirSaat":     round(
                        int(r.get("DevirDakika",0))/60, 2),
                    "ToplamFazla":   round(
                        int(r.get("ToplamFazlaDakika",0))/60, 2),
                    "OdenenSaat":    round(
                        int(r.get("OdenenDakika",0))/60, 2),
                    "DevireGiden":   round(
                        int(r.get("DevireGidenDakika",0))/60, 2),
                })
            return SonucYonetici.tamam(veri=sonuc)
        except Exception as e:
            return SonucYonetici.hata(e, "NobetAdapter.fazla_mesai_getir")

    def fazla_mesai_hesapla(self, yil: int, ay: int,
                            birim: Optional[str] = None) -> SonucYonetici:
        try:
            bid  = self._birim_id_coz(birim) if birim else ""
            plan = self.plan.get_plan(bid, yil, ay) if bid else None
            if not plan:
                return SonucYonetici.hata(ValueError("Plan bulunamadı"))
            sonuc = self.mesai.mesai_hesapla(bid, plan["PlanID"], yil, ay)
            if not sonuc.basarili:
                return sonuc
            # Eski format dönüşümü
            eski_fmt = []
            for r in (sonuc.veri or []):
                eski_fmt.append({
                    "FazlaID":       r.get("HesapID",""),
                    "PersonelID":    r.get("PersonelID",""),
                    "Yil":           r.get("Yil"),
                    "Ay":            r.get("Ay"),
                    "BirimAdi":      birim,
                    "CalisanSaat":   round(r.get("CalisDakika",0)/60, 2),
                    "HedefSaat":     round(r.get("HedefDakika",0)/60, 2),
                    "FazlaMesaiSaat":round(r.get("FazlaDakika",0)/60, 2),
                    "DevirSaat":     round(r.get("DevirDakika",0)/60, 2),
                    "ToplamFazla":   round(r.get("ToplamFazlaDakika",0)/60, 2),
                    "OdenenSaat":    round(r.get("OdenenDakika",0)/60, 2),
                    "DevireGiden":   round(r.get("DevireGidenDakika",0)/60, 2),
                })
            return SonucYonetici.tamam(veri=eski_fmt)
        except Exception as e:
            return SonucYonetici.hata(e, "NobetAdapter.fazla_mesai_hesapla")

    def odenen_guncelle(self, fazla_id: str,
                        odenen_saat: float) -> SonucYonetici:
        """Eski arayüz — saat → dakika çevirisi."""
        return self.mesai.odenen_guncelle(fazla_id, int(odenen_saat * 60))

    # ──────────────────────────────────────────────────────────
    #  Tatil / İzin (UI doğrudan kullanır)
    # ──────────────────────────────────────────────────────────

    def _tatil_listesi_getir(self, yil: int, ay: int,
                              idari_dahil: bool = True,
                              sadece_dini: bool = False) -> list[str]:
        """Tatil tarihlerini döner — UI plan sayfası için."""
        try:
            rows   = self._r.get("Tatiller").get_all() or []
            ay_bas = f"{yil:04d}-{ay:02d}-01"
            ay_bit = f"{yil:04d}-{ay:02d}-31"
            sonuc  = []
            for r in rows:
                t    = str(r.get("Tarih", "")).strip()
                turu = str(r.get("TatilTuru", "Resmi")).strip()
                if not (ay_bas <= t <= ay_bit):
                    continue
                if sadece_dini:
                    if turu == "DiniBayram":
                        sonuc.append(t)
                elif turu == "Resmi":
                    sonuc.append(t)
                elif turu == "DiniBayram":
                    sonuc.append(t)
                elif turu == "Idari" and idari_dahil:
                    sonuc.append(t)
            return sonuc
        except Exception:
            return []

    def _izin_map_getir(self, yil: int, ay: int) -> dict[str, set[str]]:
        """Plan algoritması için izin haritası."""
        return self.plan._izin_map_getir(yil, ay)

    def _dini_bayram_set_getir(self, yil: int, ay: int) -> set[str]:
        return self.plan._dini_bayram_set_getir(yil, ay)

    def personel_max_nobet_gunu(self, personel_id: str,
                                yil: int, ay: int) -> SonucYonetici:
        """İş günü hesabı — UI özet sayfası için."""
        try:
            from core.hesaplamalar import ay_is_gunu
            tatiller = self._tatil_listesi_getir(yil, ay)
            is_gunu  = ay_is_gunu(yil, ay, tatil_listesi=tatiller)
            izin_map = self._izin_map_getir(yil, ay)
            from datetime import date
            izin_is_gunu = sum(
                1 for t_str in izin_map.get(personel_id, set())
                if date.fromisoformat(t_str).weekday() < 5
                and t_str not in tatiller
            )
            return SonucYonetici.tamam(veri={
                "PersonelID":  personel_id,
                "Yil":         yil,
                "Ay":          ay,
                "IsGunu":      is_gunu,
                "IzinGunu":    izin_is_gunu,
                "TatilGunu":   len(tatiller),
                "MaxNobetGun": max(0, is_gunu - izin_is_gunu),
            })
        except Exception as e:
            return SonucYonetici.hata(e, "NobetAdapter.personel_max_nobet_gunu")

    # ──────────────────────────────────────────────────────────
    #  Yardımcılar
    # ──────────────────────────────────────────────────────────

    def _birim_id_coz(self, birim: str) -> str:
        """
        BirimID veya BirimAdi → BirimID.
        UUID formatındaysa doğrudan döner.
        """
        if not birim:
            return ""
        # UUID formatı kontrolü
        if len(birim) == 36 and birim.count("-") == 4:
            return birim
        # BirimAdi → BirimID
        return self.birim.birim_id_bul(birim) or ""

    def _birim_adi_bul(self, birim_id: str) -> str:
        try:
            rows = self._r.get("NB_Birim").get_all() or []
            kayit = next((r for r in rows
                          if r.get("BirimID") == birim_id), None)
            return kayit["BirimAdi"] if kayit else birim_id
        except Exception:
            return birim_id

    def _personelin_birim_id(self, personel_id: str) -> str:
        """Personelin GorevYeri'nden BirimID bul (geçiş dönemi)."""
        try:
            p_rows = self._r.get("Personel").get_all() or []
            p = next((r for r in p_rows
                      if str(r.get("KimlikNo","")) == str(personel_id)), None)
            if not p:
                return ""
            gorev_yeri = str(p.get("GorevYeri","")).strip()
            return self.birim.birim_id_bul(gorev_yeri) or ""
        except Exception:
            return ""

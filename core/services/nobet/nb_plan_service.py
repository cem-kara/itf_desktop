"""
nb_plan_service.py — NB_Plan + NB_PlanSatir yönetimi

Tasarım ilkeleri:
  - NB_PlanSatir kayıtları SİLİNMEZ — Durum='iptal' yapılır
  - Değişim zinciri: OncekiSatirID ile tam denetim izi
  - Plan versiyonlama: aynı ay/birim için birden fazla versiyon olabilir
  - Onay akışı: taslak → onaylandi → yururlukte
  - Kısıt katmanları: izin, üst üste, hedef dakika, max nöbet gün
"""
from __future__ import annotations

import uuid
from calendar import monthrange
from datetime import date, timedelta
from typing import Optional

from core.hata_yonetici import SonucYonetici, logger
from database.repository_registry import RepositoryRegistry


def _yeni_id() -> str:
    return str(uuid.uuid4())


def _simdi() -> str:
    return date.today().isoformat()


class NbPlanService:
    """
    NB_Plan + NB_PlanSatir CRUD, onay akışı ve kısıt kontrolü.

    Kullanım:
        svc = NbPlanService(registry)
        plan = svc.plan_al_veya_olustur(birim_id, 2026, 3)
        svc.satir_ekle(plan["PlanID"], personel_id, vardiya_id, tarih)
        svc.onayla(plan["PlanID"], onaylayan_id)
    """

    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("RepositoryRegistry boş olamaz")
        self._r = registry

    # ──────────────────────────────────────────────────────────
    #  Plan Okuma
    # ──────────────────────────────────────────────────────────

    def get_plan(self, birim_id: str, yil: int,
                 ay: int) -> Optional[dict]:
        """
        Birimin en güncel (en yüksek versiyonlu) planını döner.
        Yoksa None.
        """
        try:
            rows = self._r.get("NB_Plan").get_all() or []
            ilgili = [
                r for r in rows
                if str(r.get("BirimID", "")) == str(birim_id)
                and int(r.get("Yil", 0)) == yil
                and int(r.get("Ay",  0)) == ay
            ]
            if not ilgili:
                return None
            return dict(max(ilgili, key=lambda r: int(r.get("Versiyon", 1))))
        except Exception as e:
            logger.error(f"get_plan: {e}")
            return None

    def get_satirlar(self, plan_id: str,
                     sadece_aktif: bool = True) -> SonucYonetici:
        """
        Plan satırlarını döner.
        sadece_aktif=True → Durum='aktif' olanlar (iptal edilmişler hariç)
        """
        try:
            rows = self._r.get("NB_PlanSatir").get_all() or []
            rows = [r for r in rows
                    if str(r.get("PlanID", "")) == str(plan_id)]
            if sadece_aktif:
                rows = [r for r in rows if r.get("Durum") == "aktif"]
            return SonucYonetici.tamam(veri=[dict(r) for r in rows])
        except Exception as e:
            return SonucYonetici.hata(e, "NbPlanService.get_satirlar")

    def get_gun_satirlari(self, plan_id: str,
                          tarih: str) -> SonucYonetici:
        """Belirli bir günün aktif satırlarını döner."""
        try:
            sonuc = self.get_satirlar(plan_id)
            if not sonuc.basarili:
                return sonuc
            gunun = [r for r in (sonuc.veri or [])
                     if str(r.get("NobetTarihi", "")) == tarih]
            return SonucYonetici.tamam(veri=gunun)
        except Exception as e:
            return SonucYonetici.hata(e, "NbPlanService.get_gun_satirlari")

    def onay_durumu(self, birim_id: str,
                    yil: int, ay: int) -> str:
        """
        Plan onay durumunu döner.
        'yok' | 'taslak' | 'onaylandi' | 'yururlukte'
        """
        plan = self.get_plan(birim_id, yil, ay)
        if not plan:
            return "yok"
        return str(plan.get("Durum", "taslak"))

    # ──────────────────────────────────────────────────────────
    #  Plan Yazma
    # ──────────────────────────────────────────────────────────

    def plan_al_veya_olustur(self, birim_id: str, yil: int,
                              ay: int,
                              algoritma_versiyon: str = "v1",
                              olusturan_id: str = "",
                              temizle: bool = False) -> SonucYonetici:
        """
        Mevcut taslak plan varsa PlanID'sini döner.
        Yoksa yeni plan kaydı oluşturur.
        Onaylı plan varsa hata döner.

        temizle=True  → Otomatik plan öncesi aktif satırları iptal et.
        temizle=False → Sadece PlanID al/oluştur, satırlara dokunma (manuel ekleme).
        """
        try:
            mevcut = self.get_plan(birim_id, yil, ay)
            if mevcut:
                durum = mevcut.get("Durum", "taslak")
                if durum in ("onaylandi", "yururlukte"):
                    return SonucYonetici.hata(
                        ValueError(
                            f"Plan zaten {durum}. "
                            "Değişiklik için önce onayı geri alın."))
                # temizle=True ise mevcut aktif satırları iptal et
                if temizle:
                    ps_rows = self._r.get("NB_PlanSatir").get_all() or []
                    iptal_n = 0
                    for s in ps_rows:
                        if (str(s.get("PlanID", "")) == mevcut["PlanID"]
                                and s.get("Durum") == "aktif"):
                            self._r.get("NB_PlanSatir").update(
                                s["SatirID"],
                                {"Durum": "iptal", "updated_at": _simdi()})
                            iptal_n += 1
                    if iptal_n:
                        logger.info(f"Eski taslak temizlendi: {iptal_n} satır iptal")
                return SonucYonetici.tamam(
                    "Mevcut plan döndürüldü", veri=mevcut)

            plan = {
                "PlanID":               _yeni_id(),
                "BirimID":              str(birim_id),
                "Yil":                  int(yil),
                "Ay":                   int(ay),
                "Versiyon":             1,
                "Durum":                "taslak",
                "AlgoritmaVersiyon":    algoritma_versiyon,
                "created_at":           _simdi(),
                "created_by":           olusturan_id,
            }
            self._r.get("NB_Plan").insert(plan)
            logger.info(f"Yeni plan oluşturuldu: {birim_id} {yil}/{ay:02d}")
            return SonucYonetici.tamam("Yeni plan oluşturuldu", veri=plan)
        except Exception as e:
            return SonucYonetici.hata(e, "NbPlanService.plan_al_veya_olustur")

    def taslak_temizle(self, birim_id: str,
                       yil: int, ay: int) -> SonucYonetici:
        """
        Taslak planın aktif satırlarını fiziksel olarak siler.
        Onaylı satırlar dokunulmaz.
        """
        try:
            plan = self.get_plan(birim_id, yil, ay)
            if not plan:
                return SonucYonetici.tamam("Temizlenecek plan yok", veri={"silinen": 0})

            if plan.get("Durum") in ("onaylandi", "yururlukte"):
                return SonucYonetici.hata(
                    ValueError("Onaylı plan silinemez."))

            plan_id = plan["PlanID"]
            rows = self._r.get("NB_PlanSatir").get_all() or []
            silinen = 0
            for r in rows:
                if str(r.get("PlanID","")) == plan_id:
                    try:
                        self._r.get("NB_PlanSatir").delete(r["SatirID"])
                        silinen += 1
                    except Exception:
                        pass

            logger.info(f"Taslak temizlendi: {silinen} satır silindi")
            return SonucYonetici.tamam(
                f"{silinen} satır silindi",
                veri={"silinen": silinen, "PlanID": plan_id})
        except Exception as e:
            return SonucYonetici.hata(e, "NbPlanService.taslak_temizle")

    # ──────────────────────────────────────────────────────────
    #  Satır İşlemleri
    # ──────────────────────────────────────────────────────────

    def satir_ekle(self, plan_id: str,
                   personel_id: str,
                   vardiya_id: str,
                   nobet_tarihi: str,
                   kaynak: str = "algoritma",
                   nobet_turu: str = "normal",
                   notlar: str = "",
                   olusturan_id: str = "",
                   kisit_atla: bool = False) -> SonucYonetici:
        """
        Tek nöbet satırı ekler.
        kisit_atla=True → kısıt kontrolü yapılmaz (manuel override).
        """
        try:
            personel_id  = str(personel_id).strip()
            nobet_tarihi = str(nobet_tarihi).strip()
            vardiya_id   = str(vardiya_id).strip()

            if not all([plan_id, personel_id, vardiya_id, nobet_tarihi]):
                return SonucYonetici.hata(
                    ValueError("plan_id, personel_id, vardiya_id, "
                               "nobet_tarihi zorunlu"))

            # Plan durumu kontrolü
            plan_rows = self._r.get("NB_Plan").get_all() or []
            plan = next((r for r in plan_rows
                         if r.get("PlanID") == plan_id), None)
            if not plan:
                return SonucYonetici.hata(
                    ValueError(f"Plan bulunamadı: {plan_id}"))
            if plan.get("Durum") in ("onaylandi", "yururlukte"):
                if nobet_turu != "fazla_mesai":
                    return SonucYonetici.hata(
                        ValueError(
                            "Onaylı plana sadece 'fazla_mesai' türünde "
                            "satır eklenebilir."))

            # Kısıt kontrolü — kisit_atla=True ise atla
            if not kisit_atla:
                kisit = self._kisit_kontrol(
                    personel_id, nobet_tarihi, vardiya_id, nobet_turu)
                if kisit:
                    return SonucYonetici.uyari(kisit, "NbPlanService.satir_ekle")
            elif kisit_atla:
                logger.warning(
                    f"[Override] Kısıt atlandı: {personel_id} "
                    f"/ {nobet_tarihi} / {kaynak}")

            satir = {
                "SatirID":      _yeni_id(),
                "PlanID":       plan_id,
                "PersonelID":   personel_id,
                "VardiyaID":    vardiya_id,
                "NobetTarihi":  nobet_tarihi,
                "Kaynak":       kaynak,
                "NobetTuru":    nobet_turu,
                "Durum":        "aktif",
                "Notlar":       notlar,
                "created_at":   _simdi(),
                "created_by":   olusturan_id,
            }
            self._r.get("NB_PlanSatir").insert(satir)
            return SonucYonetici.tamam(
                f"Satır eklendi: {personel_id} / {nobet_tarihi}",
                veri=satir)
        except Exception as e:
            return SonucYonetici.hata(e, "NbPlanService.satir_ekle")

    def satir_iptal(self, satir_id: str,
                    neden: str = "") -> SonucYonetici:
        """
        Satırı iptal eder. Silmez — Durum='iptal' yapar.
        Denetim izi korunur.
        """
        try:
            self._r.get("NB_PlanSatir").update(satir_id, {
                "Durum":      "iptal",
                "Notlar":     neden,
                "updated_at": _simdi(),
            })
            return SonucYonetici.tamam("Satır iptal edildi")
        except Exception as e:
            return SonucYonetici.hata(e, "NbPlanService.satir_iptal")

    def satir_degistir(self, eski_satir_id: str,
                       yeni_personel_id: str,
                       neden: str = "",
                       olusturan_id: str = "") -> SonucYonetici:
        """
        Nöbet değişimi: eski satır iptal, yeni satır oluşturulur.
        OncekiSatirID zinciri korunur — tam denetim izi.
        """
        try:
            rows = self._r.get("NB_PlanSatir").get_all() or []
            eski = next(
                (r for r in rows if r.get("SatirID") == eski_satir_id), None)
            if not eski:
                return SonucYonetici.hata(
                    ValueError(f"Satır bulunamadı: {eski_satir_id}"))

            # Eski satırı iptal et
            self._r.get("NB_PlanSatir").update(eski_satir_id, {
                "Durum":      "degistirildi",
                "Notlar":     neden,
                "updated_at": _simdi(),
            })

            # Yeni satır — OncekiSatirID ile zincir
            yeni = {
                "SatirID":      _yeni_id(),
                "PlanID":       eski["PlanID"],
                "PersonelID":   yeni_personel_id,
                "VardiyaID":    eski["VardiyaID"],
                "NobetTarihi":  eski["NobetTarihi"],
                "Kaynak":       "degisim",
                "NobetTuru":    eski.get("NobetTuru", "normal"),
                "Durum":        "aktif",
                "OncekiSatirID": eski_satir_id,
                "Notlar":       neden,
                "created_at":   _simdi(),
                "created_by":   olusturan_id,
            }
            self._r.get("NB_PlanSatir").insert(yeni)
            logger.info(f"Nöbet değişimi: {eski_satir_id} → {yeni['SatirID']}")
            return SonucYonetici.tamam(
                "Nöbet değişimi yapıldı", veri=yeni)
        except Exception as e:
            return SonucYonetici.hata(e, "NbPlanService.satir_degistir")

    # ──────────────────────────────────────────────────────────
    #  Onay Akışı
    # ──────────────────────────────────────────────────────────

    def onayla(self, birim_id: str, yil: int, ay: int,
               onaylayan_id: str) -> SonucYonetici:
        """
        Planı onaylar: Durum taslak → onaylandi.
        Onay anında iptal satırlar fiziksel olarak silinir (DB şişmesini önler).
        """
        try:
            plan = self.get_plan(birim_id, yil, ay)
            if not plan:
                return SonucYonetici.hata(
                    ValueError("Onaylanacak plan bulunamadı"))
            if plan.get("Durum") != "taslak":
                return SonucYonetici.hata(
                    ValueError(
                        f"Plan zaten '{plan['Durum']}' durumunda."))

            plan_id = plan["PlanID"]

            # İptal satırları fiziksel sil
            tum_satirlar = self._r.get("NB_PlanSatir").get_all() or []
            silinen = 0
            for s in tum_satirlar:
                if (str(s.get("PlanID","")) == plan_id
                        and str(s.get("Durum","")) == "iptal"):
                    try:
                        self._r.get("NB_PlanSatir").delete(s["SatirID"])
                        silinen += 1
                    except Exception:
                        pass
            if silinen:
                logger.info(f"Onay öncesi {silinen} iptal satır silindi: {plan_id}")

            # Planı onayla
            self._r.get("NB_Plan").update(plan_id, {
                "Durum":       "onaylandi",
                "OnaylayanID": onaylayan_id,
                "OnayTarihi":  _simdi(),
                "updated_at":  _simdi(),
            })

            # Aktif satır sayısı
            satirlar = self.get_satirlar(plan_id)
            adet = len(satirlar.veri or [])

            logger.info(f"Plan onaylandı: {birim_id} {yil}/{ay:02d} "
                        f"({adet} aktif satır, {silinen} iptal silindi)")
            return SonucYonetici.tamam(
                f"Plan onaylandı — {adet} nöbet kaydı",
                veri={"PlanID": plan_id, "satirSayisi": adet,
                      "silinenIptal": silinen})
        except Exception as e:
            return SonucYonetici.hata(e, "NbPlanService.onayla")

    def onay_geri_al(self, birim_id: str, yil: int,
                     ay: int) -> SonucYonetici:
        """
        Onayı geri alır: onaylandi → taslak.
        Mevcut plan satırları korunur, plan taslak olarak düzenlenebilir.
        """
        try:
            plan = self.get_plan(birim_id, yil, ay)
            if not plan:
                return SonucYonetici.hata(
                    ValueError("Plan bulunamadı"))
            if plan.get("Durum") not in ("onaylandi", "yururlukte"):
                return SonucYonetici.hata(
                    ValueError("Onaylanmamış plan için geri alma yapılamaz"))

            # Sadece durum değişir — satırlar aynen korunur
            self._r.get("NB_Plan").update(plan["PlanID"], {
                "Durum":      "taslak",
                "updated_at": _simdi(),
            })

            satirlar = self.get_satirlar(plan["PlanID"])
            adet = len(satirlar.veri or [])

            logger.info(
                f"Plan onayı geri alındı: {birim_id} {yil}/{ay:02d} "
                f"→ taslak ({adet} satır korundu)")
            return SonucYonetici.tamam(
                f"Plan taslak durumuna alındı — {adet} nöbet kaydı korundu",
                veri={"PlanID": plan["PlanID"], "satirSayisi": adet})
        except Exception as e:
            return SonucYonetici.hata(e, "NbPlanService.onay_geri_al")

    # ──────────────────────────────────────────────────────────
    #  Kısıt Kontrolü
    # ──────────────────────────────────────────────────────────

    def _kisit_kontrol(self, personel_id: str, tarih: str,
                       vardiya_id: str,
                       nobet_turu: str = "normal") -> Optional[str]:
        """
        Kısıt kontrolü. Sorun varsa mesaj döner, yoksa None.
        fazla_mesai türü tüm kısıtları atlar.
        """
        if nobet_turu == "fazla_mesai":
            return None

        try:
            tarih_obj = date.fromisoformat(tarih)
        except ValueError:
            return f"Geçersiz tarih: {tarih}"

        # 1. İzin/rapor kontrolü
        izin_rows = self._r.get("Izin_Giris").get_all() or []
        for izin in izin_rows:
            if str(izin.get("Personelid", "")) != str(personel_id):
                continue
            if str(izin.get("Durum", "")).lower() in ("iptal", "reddedildi"):
                continue
            try:
                bas = date.fromisoformat(
                    str(izin.get("BaslamaTarihi", "")))
                bit = date.fromisoformat(
                    str(izin.get("BitisTarihi", "")))
                if bas <= tarih_obj <= bit:
                    return (f"{personel_id} bu tarihte izinli "
                            f"({izin.get('IzinTipi', '')})")
            except Exception:
                continue

        # 2. Üst üste nöbet kontrolü
        dun = (tarih_obj - timedelta(days=1)).isoformat()
        ps_rows = self._r.get("NB_PlanSatir").get_all() or []
        if any(str(r.get("PersonelID", "")) == str(personel_id)
               and str(r.get("NobetTarihi", "")) == dun
               and r.get("Durum") == "aktif"
               for r in ps_rows):
            return f"{personel_id} dün de nöbet tuttu (üst üste yasak)"

        return None

    def _izin_map_getir(self, yil: int, ay: int) -> dict[str, set[str]]:
        """Algoritma için personel bazlı izin günleri haritası."""
        ay_bas = date(yil, ay, 1)
        ay_bit = (date(yil, ay + 1, 1) - timedelta(days=1)
                  if ay < 12 else date(yil, 12, 31))
        izin_map: dict[str, set[str]] = {}
        try:
            for izin in (self._r.get("Izin_Giris").get_all() or []):
                pid = str(izin.get("Personelid", ""))
                if str(izin.get("Durum", "")).lower() in (
                        "iptal", "reddedildi"):
                    continue
                try:
                    bas = date.fromisoformat(
                        str(izin.get("BaslamaTarihi", "")))
                    bit = date.fromisoformat(
                        str(izin.get("BitisTarihi", "")))
                except Exception:
                    continue
                gun = max(bas, ay_bas)
                while gun <= min(bit, ay_bit):
                    izin_map.setdefault(pid, set()).add(gun.isoformat())
                    gun += timedelta(days=1)
        except Exception as e:
            logger.warning(f"İzin map hatası: {e}")
        return izin_map

    def _dini_bayram_set_getir(self, yil: int, ay: int) -> set[str]:
        """O aya ait dini bayram tarihlerini döner."""
        try:
            rows   = self._r.get("Tatiller").get_all() or []
            ay_bas = f"{yil:04d}-{ay:02d}-01"
            ay_bit = f"{yil:04d}-{ay:02d}-31"
            return {
                str(r.get("Tarih", ""))
                for r in rows
                if str(r.get("TatilTuru", "")) == "DiniBayram"
                and ay_bas <= str(r.get("Tarih", "")) <= ay_bit
            }
        except Exception:
            return set()

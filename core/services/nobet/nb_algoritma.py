"""
nb_algoritma.py — NB_ tabloları üzerinde çalışan slot motoru

Tasarım:
  - Saf fonksiyon: veritabanından okur, NB_PlanSatir'a yazar
  - Her birim için: birim ayarı → vardiya grupları → personel tercih →
    günlük slot doldur → uyarıları döndür
  - Adalet ölçüsü: dakika toplamı eşitliği (gün sayısı değil)
  - Sıralama: az dakika → az hafta sonu → bu vardiyaya az girmiş

Slot kavramı:
  Bir VardiyaGrubu = bir slot pozisyonu.
  Normal akış: tek kişi grubun tüm ana vardiyalarını alır (24h).
  İstisna: hedef dolmuşsa her ana vardiyaya ayrı kişi (slot bölünür).
  İkincil havuz (gonullu): hedef aşılabilir — saat limiti uygulanmaz.
"""
from __future__ import annotations

import uuid
from calendar import monthrange
from datetime import date, timedelta
from typing import Optional

from core.hata_yonetici import SonucYonetici, logger
from database.repository_registry import RepositoryRegistry

ALGORITMA_VERSIYON = "nb-v1"


def _yeni_id() -> str:
    return str(uuid.uuid4())


def _simdi() -> str:
    return date.today().isoformat()


class NbAlgoritma:
    """
    NB_ tabloları üzerinde çalışan nöbet planlama algoritması.

    Kullanım:
        alg = NbAlgoritma(registry)
        sonuc = alg.plan_olustur(birim_id, 2026, 3)
    """

    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("RepositoryRegistry boş olamaz")
        self._r = registry

    # ══════════════════════════════════════════════════════════
    #  ANA GİRİŞ NOKTASI
    # ══════════════════════════════════════════════════════════

    def plan_olustur(self, birim_id: str, yil: int,
                     ay: int) -> SonucYonetici:
        """
        Birim için aylık nöbet taslağı oluşturur.

        1. Mevcut taslak varsa silinir (onaylı planlar korunur).
        2. Plan başlığı (NB_Plan) oluşturulur ya da mevcut kullanılır.
        3. Her gün için slotlar doldurulur.
        4. Sonuç: eklenen satır sayısı + uyarı listesi.
        """
        try:
            # ── 1. Hazırlık ──────────────────────────────────
            hazirlik = self._hazirlik(birim_id, yil, ay)
            if not hazirlik["ok"]:
                return SonucYonetici.hata(
                    ValueError(hazirlik["hata"]))

            ayar        = hazirlik["ayar"]
            gruplar     = hazirlik["gruplar"]
            personeller = hazirlik["personeller"]
            gonulluler  = hazirlik["gonulluler"]
            izin_map    = hazirlik["izin_map"]
            dini_set    = hazirlik["dini_set"]
            tatil_set   = hazirlik["tatil_set"]
            hedef_map   = hazirlik["hedef_map"]
            plan_id     = hazirlik["plan_id"]

            slot_sayisi     = int(ayar.get("GunlukSlotSayisi", 4))
            oto_bolunme     = bool(int(ayar.get("OtomatikBolunme", 1)))

            # ── 2. Sayaçlar ───────────────────────────────────
            # {pid: dakika}
            saat_sayac:    dict[str, int]            = {p: 0 for p in personeller + gonulluler}
            # {pid: hafta sonu nöbet sayısı}
            hs_sayac:      dict[str, int]            = {p: 0 for p in personeller + gonulluler}
            # {pid: {vardiya_id: kaç kez girildi}}
            v_sayac:       dict[str, dict[str, int]] = {p: {} for p in personeller + gonulluler}
            # {pid: son nöbet tarihi str}
            son_nobet:     dict[str, str]            = {}
            eklenen:       list[dict]                = []
            uyarilar:      list[str]                 = []

            HAFTASONU = {5, 6}

            def _sirala(pid_listesi: list[str]) -> list[str]:
                return sorted(
                    pid_listesi,
                    key=lambda pid: (
                        saat_sayac.get(pid, 0),
                        hs_sayac.get(pid, 0),
                        sum(v_sayac.get(pid, {}).values()),
                    )
                )

            def _atanabilir(pid: str, tarih_str: str,
                            gun: date, gonullu: bool = False) -> bool:
                # İzin günü
                if tarih_str in izin_map.get(pid, set()):
                    return False
                # Üst üste yasak
                dun = (gun - timedelta(days=1)).isoformat()
                if son_nobet.get(pid) == dun:
                    return False
                # Hedef doldu mu? Gönüllüye uygulanmaz
                if not gonullu and saat_sayac.get(pid, 0) >= hedef_map.get(pid, 999999):
                    return False
                return True

            def _ekle(pid: str, vardiya: dict,
                      tarih_str: str, is_hw: bool):
                satir = {
                    "SatirID":     _yeni_id(),
                    "PlanID":      plan_id,
                    "PersonelID":  pid,
                    "VardiyaID":   vardiya["VardiyaID"],
                    "NobetTarihi": tarih_str,
                    "Kaynak":      "algoritma",
                    "NobetTuru":   "normal",
                    "Durum":       "aktif",
                    "created_at":  _simdi(),
                }
                self._r.get("NB_PlanSatir").insert(satir)
                eklenen.append(satir)
                dk = int(vardiya.get("SureDakika", 0))
                saat_sayac[pid] = saat_sayac.get(pid, 0) + dk
                if is_hw:
                    hs_sayac[pid] = hs_sayac.get(pid, 0) + 1
                vs = v_sayac.setdefault(pid, {})
                vid = vardiya["VardiyaID"]
                vs[vid] = vs.get(vid, 0) + 1
                son_nobet[pid] = tarih_str

            # ── 3. Ay günleri ─────────────────────────────────
            ay_son = monthrange(yil, ay)[1]
            gunler = [date(yil, ay, g) for g in range(1, ay_son + 1)]

            # ── 4. Ana döngü ──────────────────────────────────
            for gun in gunler:
                tarih_str = gun.isoformat()

                # Dini bayram → otomatik atama yok
                if tarih_str in dini_set:
                    continue

                is_hw = gun.weekday() in HAFTASONU

                for slot_no in range(slot_sayisi):

                    for grup in gruplar:
                        ana_vardiyalar = grup["ana"]
                        grup_dk        = grup["toplam_dk"]

                        if not ana_vardiyalar:
                            continue

                        # — Tam slot: tek kişi tüm ana vardiyas —
                        tam_atandi = False
                        for pid in _sirala(personeller):
                            kalan = hedef_map.get(pid, 0) - saat_sayac.get(pid, 0)
                            if kalan < grup_dk * 0.5:
                                continue
                            if not _atanabilir(pid, tarih_str, gun):
                                continue
                            for v in ana_vardiyalar:
                                _ekle(pid, v, tarih_str, is_hw)
                            tam_atandi = True
                            break

                        # Zorunlu personel dolduramadı → gönüllüler
                        if not tam_atandi:
                            for pid in _sirala(gonulluler):
                                if not _atanabilir(pid, tarih_str, gun,
                                                   gonullu=True):
                                    continue
                                for v in ana_vardiyalar:
                                    _ekle(pid, v, tarih_str, is_hw)
                                tam_atandi = True
                                break

                        if tam_atandi:
                            continue

                        # — Slot bölünmesi: her vardiyaya farklı kişi —
                        if not oto_bolunme:
                            uyarilar.append(
                                f"{tarih_str} slot {slot_no+1} grup "
                                f"'{grup['GrupAdi']}' doldurulamadı "
                                f"(otomatik bölünme kapalı)")
                            continue

                        for v in ana_vardiyalar:
                            atandi = False
                            for pid in _sirala(personeller):
                                if not _atanabilir(pid, tarih_str, gun):
                                    continue
                                _ekle(pid, v, tarih_str, is_hw)
                                atandi = True
                                break
                            if not atandi:
                                for pid in _sirala(gonulluler):
                                    if not _atanabilir(pid, tarih_str, gun,
                                                       gonullu=True):
                                        continue
                                    _ekle(pid, v, tarih_str, is_hw)
                                    atandi = True
                                    break
                            if not atandi:
                                uyarilar.append(
                                    f"{tarih_str} slot {slot_no+1} "
                                    f"'{v.get('VardiyaAdi','')}' doldurulamadı")

            ozet = (f"{len(eklenen)} nöbet ataması yapıldı"
                    + (f"  |  {len(uyarilar)} uyarı" if uyarilar else ""))
            logger.info(f"Algoritma tamamlandı: {birim_id} {yil}/{ay:02d} — {ozet}")
            return SonucYonetici.tamam(
                mesaj=ozet,
                veri={"eklenen": len(eklenen), "uyarilar": uyarilar,
                      "plan_id": plan_id})

        except Exception as e:
            logger.error(f"NbAlgoritma.plan_olustur: {e}")
            return SonucYonetici.hata(e, "NbAlgoritma.plan_olustur")

    # ══════════════════════════════════════════════════════════
    #  HAZIRLIK
    # ══════════════════════════════════════════════════════════

    def _hazirlik(self, birim_id: str, yil: int, ay: int) -> dict:
        """
        Plan öncesi tüm veriyi çeker ve doğrular.
        Sorun varsa ok=False, hata mesajı döner.
        """
        sonuc = {"ok": False}

        # ── Birim ayarı ───────────────────────────────────────
        ayar = self._birim_ayar(birim_id)

        # ── Vardiya grupları ──────────────────────────────────
        v_rows  = self._r.get("NB_Vardiya").get_all() or []
        g_rows  = self._r.get("NB_VardiyaGrubu").get_all() or []

        aktif_gruplar = [
            g for g in g_rows
            if str(g.get("BirimID", "")) == str(birim_id)
            and int(g.get("Aktif", 1))
        ]
        if not aktif_gruplar:
            sonuc["hata"] = f"'{birim_id}' birimine ait aktif vardiya grubu yok"
            return sonuc

        gruplar = []
        for g in sorted(aktif_gruplar, key=lambda x: int(x.get("Sira", 1))):
            gid = g["GrupID"]
            ana = [
                v for v in v_rows
                if str(v.get("GrupID", "")) == gid
                and (v.get("Rol") or "ana") == "ana"
                and int(v.get("Aktif", 1))
            ]
            toplam_dk = sum(int(v.get("SureDakika", 0)) for v in ana)
            gruplar.append({
                **dict(g),
                "ana":       sorted(ana, key=lambda x: int(x.get("Sira", 1))),
                "toplam_dk": toplam_dk,
            })

        if not any(g["ana"] for g in gruplar):
            sonuc["hata"] = "Hiçbir grupta 'ana' rolünde aktif vardiya yok"
            return sonuc

        # ── Personel havuzları ────────────────────────────────
        p_rows = self._r.get("Personel").get_all() or []
        t_rows = self._r.get("NB_PersonelTercih").get_all() or []

        # Önce NB_BirimPersonel tablosunu dene (yeni mimari)
        try:
            bp_rows = self._r.get("NB_BirimPersonel").get_all() or []
            tum_p   = [
                str(r.get("PersonelID",""))
                for r in bp_rows
                if str(r.get("BirimID","")) == str(birim_id)
                and int(r.get("Aktif", 1))
                and (not r.get("GorevBitis") or r.get("GorevBitis") >= _simdi())
            ]
        except Exception:
            tum_p = []

        # Fallback: GorevYeri (geçiş dönemi — FHSZ korunur, dokunulmaz)
        if not tum_p:
            birim_adi = self._birim_adi(birim_id)
            tum_p = [
                str(p["KimlikNo"]) for p in p_rows
                if str(p.get("GorevYeri","")).strip() == birim_adi
            ]

        if not tum_p:
            sonuc["hata"] = f"'{birim_id}' biriminde kayıtlı personel yok"
            return sonuc

        # Tercih haritası
        tercih_map: dict[str, str] = {
            str(r.get("PersonelID", "")): str(r.get("NobetTercihi", "zorunlu"))
            for r in t_rows
            if str(r.get("BirimID", "")) == str(birim_id)
            and int(r.get("Yil", 0)) == yil
            and int(r.get("Ay",  0)) == ay
        }
        personeller = [
            pid for pid in tum_p
            if tercih_map.get(pid, "zorunlu") == "zorunlu"
        ]
        gonulluler = [
            pid for pid in tum_p
            if tercih_map.get(pid, "zorunlu") == "fazla_mesai_gonullu"
        ]
        if not personeller:
            sonuc["hata"] = "Zorunlu nöbet tutacak personel yok"
            return sonuc

        # ── Hedef dakika haritası ─────────────────────────────
        hedef_map: dict[str, int] = {}
        for pid in personeller + gonulluler:
            t = next(
                (r for r in t_rows
                 if str(r.get("PersonelID", "")) == pid
                 and str(r.get("BirimID", "")) == str(birim_id)
                 and int(r.get("Yil", 0)) == yil
                 and int(r.get("Ay",  0)) == ay),
                None
            )
            if t and t.get("HedefDakika") is not None:
                hedef_map[pid] = int(t["HedefDakika"])
            else:
                hedef_map[pid] = self._otomatik_hedef(pid, yil, ay)

        # ── İzin ve tatil ─────────────────────────────────────
        izin_map  = self._izin_map(yil, ay)
        dini_set  = self._dini_bayram_set(yil, ay)
        tatil_set = self._tatil_set(yil, ay)

        # ── Plan başlığı ──────────────────────────────────────
        # Önce mevcut taslak satırları iptal et
        pl_rows = self._r.get("NB_Plan").get_all() or []
        mevcut_plan = next(
            (r for r in pl_rows
             if str(r.get("BirimID", "")) == str(birim_id)
             and int(r.get("Yil", 0)) == yil
             and int(r.get("Ay",  0)) == ay),
            None
        )
        if mevcut_plan:
            if mevcut_plan.get("Durum") in ("onaylandi", "yururlukte"):
                sonuc["hata"] = (
                    f"Plan zaten '{mevcut_plan['Durum']}' durumunda. "
                    "Değişiklik için önce onayı geri alın.")
                return sonuc
            # Taslak satırları iptal et
            ps_rows = self._r.get("NB_PlanSatir").get_all() or []
            for s in ps_rows:
                if (str(s.get("PlanID", "")) == mevcut_plan["PlanID"]
                        and s.get("Durum") == "aktif"):
                    self._r.get("NB_PlanSatir").update(
                        s["SatirID"],
                        {"Durum": "iptal", "updated_at": _simdi()})
            plan_id = mevcut_plan["PlanID"]
        else:
            plan_id = _yeni_id()
            self._r.get("NB_Plan").insert({
                "PlanID":            plan_id,
                "BirimID":           str(birim_id),
                "Yil":               yil,
                "Ay":                ay,
                "Versiyon":          1,
                "Durum":             "taslak",
                "AlgoritmaVersiyon": ALGORITMA_VERSIYON,
                "created_at":        _simdi(),
            })

        return {
            "ok":         True,
            "ayar":       ayar,
            "gruplar":    gruplar,
            "personeller": personeller,
            "gonulluler": gonulluler,
            "izin_map":   izin_map,
            "dini_set":   dini_set,
            "tatil_set":  tatil_set,
            "hedef_map":  hedef_map,
            "plan_id":    plan_id,
        }

    # ══════════════════════════════════════════════════════════
    #  YARDIMCILAR
    # ══════════════════════════════════════════════════════════

    def _birim_ayar(self, birim_id: str) -> dict:
        """NB_BirimAyar kaydı — yoksa varsayılan döner."""
        try:
            rows = self._r.get("NB_BirimAyar").get_all() or []
            kayit = next(
                (r for r in rows
                 if str(r.get("BirimID", "")) == str(birim_id)),
                None
            )
            if kayit:
                return dict(kayit)
        except Exception:
            pass
        return {
            "GunlukSlotSayisi": 4,
            "OtomatikBolunme":  1,
            "CalismaModu":      "tam_gun",
            "DiniBayramAtama":  0,
        }

    def _birim_adi(self, birim_id: str) -> str:
        try:
            rows = self._r.get("NB_Birim").get_all() or []
            kayit = next(
                (r for r in rows if r.get("BirimID") == birim_id), None)
            return kayit["BirimAdi"] if kayit else ""
        except Exception:
            return ""

    def _otomatik_hedef(self, personel_id: str,
                        yil: int, ay: int) -> int:
        """(İş günü - izin günü) × 420 dakika."""
        try:
            from core.hesaplamalar import ay_is_gunu
            tatiller = self._tatil_listesi(yil, ay)
            is_gunu  = ay_is_gunu(yil, ay, tatil_listesi=tatiller)
            izin_gun = self._izin_is_gunu(personel_id, yil, ay, tatiller)
            return max(0, is_gunu - izin_gun) * 420
        except Exception:
            return 20 * 420  # Varsayılan: 20 iş günü

    def _izin_map(self, yil: int, ay: int) -> dict[str, set[str]]:
        """Personel bazlı izin günleri: {pid: {tarih_str, ...}}"""
        ay_bas = date(yil, ay, 1)
        ay_bit = (date(yil, ay + 1, 1) - timedelta(days=1)
                  if ay < 12 else date(yil, 12, 31))
        sonuc: dict[str, set[str]] = {}
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
                    sonuc.setdefault(pid, set()).add(gun.isoformat())
                    gun += timedelta(days=1)
        except Exception as e:
            logger.warning(f"İzin map: {e}")
        return sonuc

    def _izin_is_gunu(self, personel_id: str, yil: int,
                      ay: int, tatiller: list[str]) -> int:
        izin_map = self._izin_map(yil, ay)
        return sum(
            1 for t_str in izin_map.get(personel_id, set())
            if date.fromisoformat(t_str).weekday() < 5
            and t_str not in tatiller
        )

    def _tatil_listesi(self, yil: int, ay: int) -> list[str]:
        """Resmi + DiniBayram tatil tarihleri."""
        try:
            rows   = self._r.get("Tatiller").get_all() or []
            ay_bas = f"{yil:04d}-{ay:02d}-01"
            ay_bit = f"{yil:04d}-{ay:02d}-31"
            return [
                str(r.get("Tarih", ""))
                for r in rows
                if ay_bas <= str(r.get("Tarih", "")) <= ay_bit
                and str(r.get("TatilTuru", "Resmi")) in ("Resmi", "DiniBayram")
            ]
        except Exception:
            return []

    def _tatil_set(self, yil: int, ay: int) -> set[str]:
        return set(self._tatil_listesi(yil, ay))

    def _dini_bayram_set(self, yil: int, ay: int) -> set[str]:
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

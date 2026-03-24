"""
nb_mesai_service.py — NB_MesaiHesap + NB_MesaiKural yönetimi

Mevcut Nobet_FazlaMesai tablosunun NB_ mimarisi karşılığı.

Temel farklar:
  - Dakika birimi (saat değil) — bölme hatası yok
  - Birim bazlı hesap — çoklu birimde çalışan personel doğru hesaplanır
  - NB_MesaiKural — ödeme kuralı tabloda, hardcode değil
  - NB_Plan FK — hangi plana göre hesaplandığı belli
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from core.hata_yonetici import SonucYonetici, logger
from database.repository_registry import RepositoryRegistry

GUNLUK_HEDEF_DAKIKA = 420   # 7 saat × 60


def _yeni_id() -> str:
    return str(uuid.uuid4())


def _simdi() -> str:
    return date.today().isoformat()


class NbMesaiService:
    """
    NB_MesaiHesap CRUD ve fazla mesai hesaplama.
    NB_MesaiKural — ödeme kuralı yönetimi.

    Kullanım:
        svc = NbMesaiService(registry)
        svc.mesai_hesapla(birim_id, plan_id, yil, ay)
        svc.odenen_guncelle(hesap_id, odenen_dakika)
    """

    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("RepositoryRegistry boş olamaz")
        self._r = registry

    # ──────────────────────────────────────────────────────────
    #  Kural Okuma
    # ──────────────────────────────────────────────────────────

    def gecerli_kural(self, tarih: Optional[str] = None) -> Optional[dict]:
        """
        Verilen tarihte geçerli mesai kuralını döner.
        tarih=None → bugün.
        Birden fazla kural çakışırsa en yenisi (GeserlilikBaslangic büyük olanı).
        """
        try:
            hedef_tarih = tarih or _simdi()
            rows = self._r.get("NB_MesaiKural").get_all() or []
            gecerli = [
                r for r in rows
                if str(r.get("GeserlilikBaslangic", "")) <= hedef_tarih
                and (not r.get("GeserlilikBitis")
                     or str(r.get("GeserlilikBitis", "")) >= hedef_tarih)
            ]
            if not gecerli:
                return None
            return dict(max(gecerli,
                            key=lambda r: str(r.get("GeserlilikBaslangic", ""))))
        except Exception as e:
            logger.error(f"gecerli_kural: {e}")
            return None

    def kural_ekle(self, kural_adi: str, kural_turu: str,
                   parametre: dict,
                   gecerlilik_baslangic: str,
                   gecerlilik_bitis: Optional[str] = None,
                   aciklama: str = "") -> SonucYonetici:
        """
        Yeni mesai kuralı ekler.
        Parametre örnekleri:
          odeme_esigi: {"esik_dakika": 420, "blok_dakika": 420}
          devir_limiti: {"max_devir_dakika": 840}
        """
        import json
        try:
            veri = {
                "KuralID":              _yeni_id(),
                "KuralAdi":             kural_adi.strip(),
                "KuralTuru":            kural_turu,
                "Parametre":            json.dumps(parametre, ensure_ascii=False),
                "GeserlilikBaslangic":  gecerlilik_baslangic,
                "GeserlilikBitis":      gecerlilik_bitis,
                "Aciklama":             aciklama,
                "created_at":           _simdi(),
            }
            self._r.get("NB_MesaiKural").insert(veri)
            return SonucYonetici.tamam(f"Kural eklendi: {kural_adi}")
        except Exception as e:
            return SonucYonetici.hata(e, "NbMesaiService.kural_ekle")

    def varsayilan_kural_yukle(self) -> SonucYonetici:
        """
        Standart radyoloji mesai kuralını yükler.
        7 saat bloğu: 420 dakika birikince bir blok ödenir.
        """
        return self.kural_ekle(
            kural_adi="Standart Radyoloji Mesai Kuralı",
            kural_turu="odeme_esigi",
            parametre={"blok_dakika": 420},
            gecerlilik_baslangic="2020-01-01",
            aciklama="7 saat (420 dakika) birikmesi halinde 1 blok ödenir. "
                     "Kalan devir sonraki aya geçer."
        )

    # ──────────────────────────────────────────────────────────
    #  Mesai Hesabı
    # ──────────────────────────────────────────────────────────

    def mesai_hesapla(self, birim_id: str, plan_id: str,
                      yil: int, ay: int) -> SonucYonetici:
        """
        Onaylı plan üzerinden tüm personel için mesai hesaplar.

        Formül:
          CalisDakika    = Σ vardiya.SureDakika (aktif satırlar)
          HedefDakika    = NB_PersonelTercih.HedefDakika || otomatik
          FazlaDakika    = CalisDakika − HedefDakika
          DevirDakika    = önceki ayın DevireGidenDakika
          ToplamFazla    = FazlaDakika + DevirDakika
          OdenenDakika   = kullanıcı girer (mevcut korunur)
          DevireGiden    = ToplamFazla − OdenenDakika
        """
        try:
            # Plan satırları (sadece Durum='aktif' — iptal edilmişler hariç)
            ps_rows = self._r.get("NB_PlanSatir").get_all() or []
            aktif_satirlar = [
                r for r in ps_rows
                if str(r.get("PlanID", "")) == str(plan_id)
                and r.get("Durum") == "aktif"
            ]

            # Vardiya süre haritası
            v_rows = self._r.get("NB_Vardiya").get_all() or []
            v_sure = {
                str(v["VardiyaID"]): int(v.get("SureDakika", GUNLUK_HEDEF_DAKIKA))
                for v in v_rows
            }

            # Personel bazlı çalışılan dakika
            calisan: dict[str, int] = {}
            for r in aktif_satirlar:
                pid  = str(r.get("PersonelID", ""))
                vsid = str(r.get("VardiyaID", ""))
                calisan[pid] = (calisan.get(pid, 0)
                                + v_sure.get(vsid, GUNLUK_HEDEF_DAKIKA))

            # Önceki ayın devir haritası
            prev_yil = yil - 1 if ay == 1 else yil
            prev_ay  = 12      if ay == 1 else ay - 1
            prev_rows = self._r.get("NB_MesaiHesap").get_all() or []
            devir_map: dict[str, int] = {
                str(r.get("PersonelID", "")): int(r.get("DevireGidenDakika", 0))
                for r in prev_rows
                if str(r.get("BirimID", "")) == str(birim_id)
                and int(r.get("Yil", 0)) == prev_yil
                and int(r.get("Ay",  0)) == prev_ay
            }

            # Personel tercih/hedef haritası
            t_rows  = self._r.get("NB_PersonelTercih").get_all() or []
            hedef_map: dict[str, int] = {
                str(r.get("PersonelID", "")): int(r.get("HedefDakika", 0))
                for r in t_rows
                if str(r.get("BirimID", "")) == str(birim_id)
                and int(r.get("Yil", 0)) == yil
                and int(r.get("Ay",  0)) == ay
                and r.get("HedefDakika") is not None
            }

            # Mevcut hesap kayıtları (OdenenDakika korumak için)
            mevcut_rows = self._r.get("NB_MesaiHesap").get_all() or []
            mevcut_map  = {
                str(r.get("PersonelID", "")): dict(r)
                for r in mevcut_rows
                if str(r.get("BirimID", "")) == str(birim_id)
                and int(r.get("Yil", 0)) == yil
                and int(r.get("Ay",  0)) == ay
                and str(r.get("PlanID", "")) == str(plan_id)
            }

            # Ödeme kuralı
            kural = self.gecerli_kural(f"{yil:04d}-{ay:02d}-01")

            tum_pid = set(calisan.keys()) | set(devir_map.keys())
            sonuclar: list[dict] = []

            for pid in tum_pid:
                calisan_dk = calisan.get(pid, 0)

                # Hedef: NB_PersonelTercih'te elle girilmiş kayıt varsa
                # onu kullan; yoksa izin düşülmüş otomatik hesap yap.
                # NOT: tablodaki kayıt da izin düşülmüş olmalı.
                # Güvenlik için her durumda _otomatik_hedef ile karşılaştır
                # ve küçük olanı al (izin olan personel aleyhine olmasın).
                hedef_otomatik = self._otomatik_hedef(pid, yil, ay)
                hedef_tercih   = hedef_map.get(pid)
                if hedef_tercih is not None:
                    # Tabloda kayıt var: izin düşülmüş otomatikten
                    # büyükse otomatik kullan (izin dikkate alınmamışsa)
                    hedef_dk = min(hedef_tercih, hedef_otomatik) \
                               if hedef_otomatik > 0 else hedef_tercih
                else:
                    hedef_dk = hedef_otomatik

                fazla_dk  = calisan_dk - hedef_dk
                devir_dk  = devir_map.get(pid, 0)
                toplam_dk = fazla_dk + devir_dk

                # Mevcut OdenenDakika'yı koru
                mevcut = mevcut_map.get(pid)
                odenen_dk = int(mevcut.get("OdenenDakika", 0)) if mevcut else 0
                devire_dk = toplam_dk - odenen_dk

                veri = {
                    "PersonelID":         pid,
                    "BirimID":            str(birim_id),
                    "PlanID":             str(plan_id),
                    "Yil":                yil,
                    "Ay":                 ay,
                    "CalisDakika":        calisan_dk,
                    "HedefDakika":        hedef_dk,
                    "FazlaDakika":        fazla_dk,
                    "DevirDakika":        devir_dk,
                    "ToplamFazlaDakika":  toplam_dk,
                    "OdenenDakika":       odenen_dk,
                    "DevireGidenDakika":  devire_dk,
                    "HesapDurumu":        "hesaplandi",
                    "HesapTarihi":        _simdi(),
                    "updated_at":         _simdi(),
                }

                if mevcut:
                    self._r.get("NB_MesaiHesap").update(
                        mevcut["HesapID"], veri)
                else:
                    veri["HesapID"]    = _yeni_id()
                    veri["created_at"] = _simdi()
                    self._r.get("NB_MesaiHesap").insert(veri)

                sonuclar.append(veri)

            toplam_calisan = sum(r["CalisDakika"]       for r in sonuclar)
            toplam_fazla   = sum(r["ToplamFazlaDakika"] for r in sonuclar)
            toplam_odenen  = sum(r["OdenenDakika"]      for r in sonuclar)

            return SonucYonetici.tamam(
                mesaj=(f"{len(sonuclar)} personel hesaplandı | "
                       f"Toplam çalışılan: {toplam_calisan // 60}s "
                       f"{toplam_calisan % 60}dk | "
                       f"Fazla: {toplam_fazla // 60}s | "
                       f"Ödenen: {toplam_odenen // 60}s"),
                veri=sonuclar)
        except Exception as e:
            return SonucYonetici.hata(e, "NbMesaiService.mesai_hesapla")

    # ──────────────────────────────────────────────────────────
    #  Ödenen Güncelleme
    # ──────────────────────────────────────────────────────────

    def odenen_guncelle(self, hesap_id: str,
                        odenen_dakika: int) -> SonucYonetici:
        """
        Kullanıcı tarafından ödenen dakika girilir.
        DevireGidenDakika otomatik yeniden hesaplanır.
        """
        try:
            rows  = self._r.get("NB_MesaiHesap").get_all() or []
            kayit = next(
                (r for r in rows if r.get("HesapID") == hesap_id), None)
            if not kayit:
                return SonucYonetici.hata(
                    ValueError(f"Hesap bulunamadı: {hesap_id}"))

            toplam     = int(kayit.get("ToplamFazlaDakika", 0))
            devire_dk  = toplam - odenen_dakika

            self._r.get("NB_MesaiHesap").update(hesap_id, {
                "OdenenDakika":      odenen_dakika,
                "DevireGidenDakika": toplam - odenen_dakika,
                "updated_at":        _simdi(),
            })
            return SonucYonetici.tamam(
                f"Ödenen güncellendi: {odenen_dakika} dk "
                f"(devir: {toplam - odenen_dakika} dk)")
        except Exception as e:
            return SonucYonetici.hata(e, "NbMesaiService.odenen_guncelle")

    def toplu_odenen_guncelle(self, birim_id: str, yil: int, ay: int,
                              plan_id: str,
                              odenen_map: dict[str, int]) -> SonucYonetici:
        """
        Birden fazla personel için ödenen dakikayı günceller.
        odenen_map: {personel_id: odenen_dakika}
        """
        try:
            rows = self._r.get("NB_MesaiHesap").get_all() or []
            guncellenen = 0
            for r in rows:
                if (str(r.get("BirimID", "")) != str(birim_id)
                        or int(r.get("Yil", 0)) != yil
                        or int(r.get("Ay",  0)) != ay
                        or str(r.get("PlanID", "")) != str(plan_id)):
                    continue
                pid = str(r.get("PersonelID", ""))
                if pid not in odenen_map:
                    continue
                odenen  = odenen_map[pid]
                toplam  = int(r.get("ToplamFazlaDakika", 0))
                self._r.get("NB_MesaiHesap").update(r["HesapID"], {
                    "OdenenDakika":      odenen,
                    "DevireGidenDakika": toplam - odenen,
                    "updated_at":        _simdi(),
                })
                guncellenen += 1
            return SonucYonetici.tamam(
                f"{guncellenen} kayıt güncellendi",
                veri={"guncellenen": guncellenen})
        except Exception as e:
            return SonucYonetici.hata(e, "NbMesaiService.toplu_odenen_guncelle")

    # ──────────────────────────────────────────────────────────
    #  Okuma
    # ──────────────────────────────────────────────────────────

    def get_hesaplar(self, birim_id: str, plan_id: str,
                     yil: int, ay: int) -> SonucYonetici:
        """Birim/plan bazlı tüm mesai hesaplarını döner."""
        try:
            rows = self._r.get("NB_MesaiHesap").get_all() or []
            ilgili = [
                dict(r) for r in rows
                if str(r.get("BirimID", "")) == str(birim_id)
                and str(r.get("PlanID", ""))  == str(plan_id)
                and int(r.get("Yil", 0)) == yil
                and int(r.get("Ay",  0)) == ay
            ]
            return SonucYonetici.tamam(veri=ilgili)
        except Exception as e:
            return SonucYonetici.hata(e, "NbMesaiService.get_hesaplar")

    def get_personel_hesap(self, personel_id: str, birim_id: str,
                           plan_id: str,
                           yil: int, ay: int) -> Optional[dict]:
        """Tek personelin mesai kaydını döner. Yoksa None."""
        try:
            rows = self._r.get("NB_MesaiHesap").get_all() or []
            kayit = next(
                (r for r in rows
                 if str(r.get("PersonelID", "")) == str(personel_id)
                 and str(r.get("BirimID", ""))   == str(birim_id)
                 and str(r.get("PlanID", ""))     == str(plan_id)
                 and int(r.get("Yil", 0)) == yil
                 and int(r.get("Ay",  0)) == ay),
                None
            )
            return dict(kayit) if kayit else None
        except Exception as e:
            logger.error(f"get_personel_hesap: {e}")
            return None

    def ozet_dakika_to_saat(self, veri: dict) -> dict:
        """
        Mesai hesap kaydındaki dakika değerlerini
        saat + dakika çiftine dönüştürür. UI gösterimi için.
        """
        def _dk(k: str) -> int:
            return int(veri.get(k, 0))

        def _fmt(dk: int) -> str:
            sgn = "-" if dk < 0 else ""
            dk  = abs(dk)
            return f"{sgn}{dk // 60}s {dk % 60:02d}dk"

        return {
            "PersonelID":        veri.get("PersonelID"),
            "CalisanSaat":       _fmt(_dk("CalisDakika")),
            "HedefSaat":         _fmt(_dk("HedefDakika")),
            "FazlaMesai":        _fmt(_dk("FazlaDakika")),
            "Devir":             _fmt(_dk("DevirDakika")),
            "ToplamFazla":       _fmt(_dk("ToplamFazlaDakika")),
            "OdenenSaat":        _fmt(_dk("OdenenDakika")),
            "DevireGiden":       _fmt(_dk("DevireGidenDakika")),
            # Ham değerler (tablo sıralama için)
            "_calis_dk":         _dk("CalisDakika"),
            "_fazla_dk":         _dk("FazlaDakika"),
            "_devire_dk":        _dk("DevireGidenDakika"),
        }

    # ──────────────────────────────────────────────────────────
    #  Yardımcılar
    # ──────────────────────────────────────────────────────────

    def _otomatik_hedef(self, personel_id: str,
                        yil: int, ay: int) -> int:
        """
        (İş Günü − İzin İş Günü) × 420 dakika.
        İzin günleri düşülerek kişiye özel hedef hesaplanır.
        """
        try:
            from core.hesaplamalar import ay_is_gunu
            tatiller = self._tatil_listesi_getir(yil, ay)
            is_gunu  = ay_is_gunu(yil, ay, tatil_listesi=tatiller)
            izin_gun = self._izin_is_gunu(personel_id, yil, ay, tatiller)
            net_gun  = max(0, is_gunu - izin_gun)
            return net_gun * GUNLUK_HEDEF_DAKIKA
        except Exception:
            return 20 * GUNLUK_HEDEF_DAKIKA  # Varsayılan: 20 iş günü

    def _izin_is_gunu(self, personel_id: str, yil: int,
                      ay: int, tatiller: list[str]) -> int:
        """Personelin o aydaki onaylı izin iş günü sayısı."""
        from calendar import monthrange
        from datetime import date, timedelta
        try:
            rows   = self._r.get("Izin_Giris").get_all() or []
            ay_bas = f"{yil:04d}-{ay:02d}-01"
            ay_bit = f"{yil:04d}-{ay:02d}-{monthrange(yil, ay)[1]:02d}"
            sayi   = 0
            for r in rows:
                if (str(r.get("Personelid", "")) != str(personel_id)
                        or str(r.get("Durum", "")).lower() not in
                        ("Onaylandı", "onaylandi", "onaylı", "approved")):
                    continue
                bas = str(r.get("BaslamaTarihi", "") or "")
                bit = str(r.get("BitisTarihi",   "") or "")
                if not bas or not bit:
                    continue
                bas = max(bas, ay_bas)
                bit = min(bit, ay_bit)
                if bas > bit:
                    continue
                cur = date.fromisoformat(bas)
                son = date.fromisoformat(bit)
                while cur <= son:
                    if cur.weekday() < 5 and cur.isoformat() not in tatiller:
                        sayi += 1
                    cur += timedelta(days=1)
            return sayi
        except Exception:
            return 0

    def _tatil_listesi_getir(self, yil: int, ay: int) -> list[str]:
        """O aya ait tatil tarihlerini döner."""
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

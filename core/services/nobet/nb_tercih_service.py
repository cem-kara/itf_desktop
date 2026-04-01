"""
nb_tercih_service.py — NB_PersonelTercih yönetimi

Aylık personel nöbet talebi, hedef saat ve kısıt yönetimi.
Mevcut Nobet_MesaiHedef tablosunun NB_ mimarisi karşılığı.

Farklar:
  - BirimID FK (BirimAdi TEXT değil)
  - HedefDakika (HedefSaat değil — dakika birimi)
  - Onay akışı (Durum: taslak | onaylandi)
  - MaxNobetGun kısıtı
  - KacinilacakGunler / TercihVardiyalar JSON kısıtları
"""
from __future__ import annotations

import json
import uuid
from calendar import monthrange
from datetime import date, timedelta
from typing import Optional

from core.hata_yonetici import SonucYonetici, logger
from database.repository_registry import RepositoryRegistry

GUNLUK_HEDEF_DAKIKA = 420   # 7 saat × 60 dakika
HEDEF_TIPLER = [
    ("normal",    "Normal"),
    ("sua",       "Şua İzni"),
    ("yillik",    "Yıllık İzin"),
    ("rapor",     "Raporlu"),
    ("emzirme",   "Emzirme İzni"),
    ("idari",     "İdari İzin"),
    ("dini_izin", "Dini İzin"),
]
NOBET_TERCIHLER = [
    ("zorunlu",             "Zorunlu"),
    ("fazla_mesai_gonullu", "Fazla Mesai Gönüllüsü"),
    ("gonullu_disi",        "Gönüllü Dışı"),
    ("nobet_yok",           "Nöbet Yok"),
]


def _yeni_id() -> str:
    return str(uuid.uuid4())


def _simdi() -> str:
    return date.today().isoformat()


class NbTercihService:
    """
    NB_PersonelTercih CRUD ve hedef hesaplama.

    Kullanım:
        svc = NbTercihService(registry)
        tercih = svc.get_tercih(pid, birim_id, 2026, 3)
        svc.tercih_kaydet(pid, birim_id, 2026, 3, nobet_tercihi="fazla_mesai_gonullu")
    """

    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("RepositoryRegistry boş olamaz")
        self._r = registry

    # ──────────────────────────────────────────────────────────
    #  Okuma
    # ──────────────────────────────────────────────────────────

    def get_tercih(self, personel_id: str, birim_id: str,
                   yil: int, ay: int) -> SonucYonetici:
        """
        Tek personelin aylık tercih kaydını döner.
        Kayıt yoksa None — çağıran otomatik hesaba geçer.
        """
        try:
            rows = self._r.get("NB_PersonelTercih").get_all() or []
            kayit = next(
                (dict(r) for r in rows
                 if str(r.get("PersonelID", "")) == str(personel_id)
                 and str(r.get("BirimID", ""))    == str(birim_id)
                 and int(r.get("Yil", 0)) == yil
                 and int(r.get("Ay",  0)) == ay),
                None
            )
            return SonucYonetici.tamam(veri=kayit)
        except Exception as e:
            return SonucYonetici.hata(e, "NbTercihService.get_tercih")

    def get_birim_tercihler(self, birim_id: str,
                            yil: int, ay: int) -> SonucYonetici:
        """
        Bir birimin tüm personel tercihlerini döner.
        Kayıt olmayan personel için otomatik hedef hesaplanır.
        """
        try:
            rows = self._r.get("NB_PersonelTercih").get_all() or []
            kayitlar = [
                dict(r) for r in rows
                if str(r.get("BirimID", "")) == str(birim_id)
                and int(r.get("Yil", 0)) == yil
                and int(r.get("Ay",  0)) == ay
            ]
            return SonucYonetici.tamam(veri=kayitlar)
        except Exception as e:
            return SonucYonetici.hata(e, "NbTercihService.get_birim_tercihler")

    def tercih_map_getir(self, birim_id: str,
                         yil: int, ay: int) -> SonucYonetici:
        """
        Algoritma için hızlı erişim haritası döner.
        {personel_id: nobet_tercihi}
        Kayıt olmayan personel → "zorunlu" varsayılan.
        """
        try:
            rows = self._r.get("NB_PersonelTercih").get_all() or []
            tercih_map = {
                str(r.get("PersonelID", "")): str(r.get("NobetTercihi", "zorunlu"))
                for r in rows
                if str(r.get("BirimID", "")) == str(birim_id)
                and int(r.get("Yil", 0)) == yil
                and int(r.get("Ay",  0)) == ay
            }
            return SonucYonetici.tamam(veri=tercih_map)
        except Exception as e:
            return SonucYonetici.hata(e, "NbTercihService.tercih_map_getir")

    def hedef_dakika_getir(self, personel_id: str, birim_id: str,
                           yil: int, ay: int,
                           otomatik: bool = True) -> SonucYonetici:
        """
        Kişinin aylık hedef dakikasını döner.

        NB_PersonelTercih kayıtlıysa → HedefDakika
        Yoksa otomatik=True ise → (iş_günü - izin_günü) × 420 dakika
        Yoksa otomatik=False ise → None
        """
        kayit_sonuc = self.get_tercih(personel_id, birim_id, yil, ay)
        if not kayit_sonuc.basarili:
            return kayit_sonuc
        kayit = kayit_sonuc.veri
        if kayit and kayit.get("HedefDakika") is not None:
            return SonucYonetici.tamam(veri=int(kayit["HedefDakika"]))

        if not otomatik:
            return SonucYonetici.tamam(veri=None)

        return SonucYonetici.tamam(veri=self._hesapla_hedef_dakika(personel_id, yil, ay))

    def ayar_var_mi(self, personel_id: str, birim_id: str,
                    yil: int, ay: int) -> SonucYonetici:
        """Bu ay için kayıt var mı?"""
        tercih_sonuc = self.get_tercih(personel_id, birim_id, yil, ay)
        if not tercih_sonuc.basarili:
            return tercih_sonuc
        return SonucYonetici.tamam(veri=tercih_sonuc.veri is not None)

    def eksik_personel_listesi(self, birim_id: str, yil: int,
                               ay: int) -> SonucYonetici:
        """
        Birimde kayıtlı olup bu ay tercih/hedef girişi olmayan
        personellerin ID listesini döner.
        Plan öncesi uyarı paneli için kullanılır.
        """
        try:
            # Birime bağlı personeller
            p_rows = self._r.get("Personel").get_all() or []

            # NB_Birim üzerinden BirimAdi bul (fallback: GorevYeri)
            birim_adi = self._birim_adi_bul(birim_id)
            personeller = [
                str(p["KimlikNo"]) for p in p_rows
                if str(p.get("GorevYeri", "")).strip() == birim_adi
            ] if birim_adi else []

            # Bu ay kaydı olanlar
            kayitli = {
                str(r.get("PersonelID", ""))
                for r in (self._r.get("NB_PersonelTercih").get_all() or [])
                if str(r.get("BirimID", "")) == birim_id
                and int(r.get("Yil", 0)) == yil
                and int(r.get("Ay",  0)) == ay
            }
            return SonucYonetici.tamam(veri=[pid for pid in personeller if pid not in kayitli])
        except Exception as e:
            return SonucYonetici.hata(e, "NbTercihService.eksik_personel_listesi")

    # ──────────────────────────────────────────────────────────
    #  Yazma
    # ──────────────────────────────────────────────────────────

    def tercih_kaydet(self,
                      personel_id:    str,
                      birim_id:       str,
                      yil:            int,
                      ay:             int,
                      nobet_tercihi:  str = "zorunlu",
                      hedef_dakika:   Optional[int] = None,
                      hedef_tipi:     str = "normal",
                      max_nobet_gun:  Optional[int] = None,
                      tercih_vardiyalar:   Optional[list] = None,
                      kacinilacak_gunler:  Optional[list] = None,
                      notlar:         str = "") -> SonucYonetici:
        """
        Personel aylık tercihini oluşturur veya günceller.
        hedef_dakika=None → otomatik hesapla (iş günü × 420 dk).
        """
        try:
            if nobet_tercihi not in [k for k, _ in NOBET_TERCIHLER]:
                return SonucYonetici.hata(
                    ValueError(f"Geçersiz nöbet tercihi: {nobet_tercihi}"))
            if hedef_tipi not in [k for k, _ in HEDEF_TIPLER]:
                return SonucYonetici.hata(
                    ValueError(f"Geçersiz hedef tipi: {hedef_tipi}"))

            # Hedef dakika boşsa otomatik hesapla
            if hedef_dakika is None:
                hedef_dakika = self._hesapla_hedef_dakika(
                    personel_id, yil, ay, hedef_tipi)

            veri = {
                "PersonelID":        str(personel_id),
                "BirimID":           str(birim_id),
                "Yil":               int(yil),
                "Ay":                int(ay),
                "NobetTercihi":      nobet_tercihi,
                "HedefDakika":       hedef_dakika,
                "HedefTipi":         hedef_tipi,
                "MaxNobetGun":       max_nobet_gun,
                "TercihVardiyalar":  json.dumps(tercih_vardiyalar or []),
                "KacinilacakGunler": json.dumps(kacinilacak_gunler or []),
                "Notlar":            notlar,
                "Durum":             "taslak",
                "updated_at":        _simdi(),
            }

            mevcut_sonuc = self.get_tercih(personel_id, birim_id, yil, ay)
            if not mevcut_sonuc.basarili:
                return mevcut_sonuc
            mevcut = mevcut_sonuc.veri
            if mevcut:
                self._r.get("NB_PersonelTercih").update(
                    mevcut["TercihID"], veri)
                msg = "Tercih güncellendi"
            else:
                veri["TercihID"]   = _yeni_id()
                veri["created_at"] = _simdi()
                self._r.get("NB_PersonelTercih").insert(veri)
                msg = "Tercih kaydedildi"

            return SonucYonetici.tamam(msg, veri=veri)

        except Exception as e:
            return SonucYonetici.hata(e, "NbTercihService.tercih_kaydet")

    def sadece_tercih_guncelle(self, personel_id: str, birim_id: str,
                               yil: int, ay: int,
                               nobet_tercihi: str) -> SonucYonetici:
        """
        Sadece NobetTercihi alanını değiştirir.
        Kayıt yoksa yeni oluşturur (hedef otomatik hesaplanır).
        Plan sayfası tıklama menüsü için.
        """
        if nobet_tercihi not in [k for k, _ in NOBET_TERCIHLER]:
            return SonucYonetici.hata(
                ValueError(f"Geçersiz tercih: {nobet_tercihi}"))

        mevcut_sonuc = self.get_tercih(personel_id, birim_id, yil, ay)
        if not mevcut_sonuc.basarili:
            return mevcut_sonuc
        mevcut = mevcut_sonuc.veri
        if mevcut:
            self._r.get("NB_PersonelTercih").update(
                mevcut["TercihID"],
                {"NobetTercihi": nobet_tercihi, "updated_at": _simdi()}
            )
            return SonucYonetici.tamam("Tercih güncellendi")
        else:
            return self.tercih_kaydet(
                personel_id, birim_id, yil, ay,
                nobet_tercihi=nobet_tercihi)

    def toplu_hedef_hesapla(self, birim_id: str,
                            yil: int, ay: int) -> SonucYonetici:
        """
        Birimin tüm personeli için hedef dakikayı hesaplar ve kaydeder.
        Mevcut kaydı varsa HedefDakika'yı günceller (tercih korunur).
        Plan oluşturmadan önce çalıştırılır.
        """
        try:
            birim_adi   = self._birim_adi_bul(birim_id)
            p_rows      = self._r.get("Personel").get_all() or []
            personeller = [
                p for p in p_rows
                if str(p.get("GorevYeri", "")).strip() == birim_adi
            ] if birim_adi else []

            guncellenen = 0
            for p in personeller:
                pid    = str(p["KimlikNo"])
                hedef  = self._hesapla_hedef_dakika(pid, yil, ay)
                mevcut_sonuc = self.get_tercih(pid, birim_id, yil, ay)
                if not mevcut_sonuc.basarili:
                    return mevcut_sonuc
                mevcut = mevcut_sonuc.veri
                if mevcut:
                    self._r.get("NB_PersonelTercih").update(
                        mevcut["TercihID"],
                        {"HedefDakika": hedef, "updated_at": _simdi()}
                    )
                else:
                    self.tercih_kaydet(pid, birim_id, yil, ay,
                                       hedef_dakika=hedef)
                guncellenen += 1

            return SonucYonetici.tamam(
                f"{guncellenen} personel hedefi hesaplandı",
                veri={"guncellenen": guncellenen})
        except Exception as e:
            return SonucYonetici.hata(e, "NbTercihService.toplu_hedef_hesapla")

    # ──────────────────────────────────────────────────────────
    #  Hedef Dakika Hesabı
    # ──────────────────────────────────────────────────────────

    def _hesapla_hedef_dakika(self, personel_id: str,
                              yil: int, ay: int,
                              hedef_tipi: str = "normal") -> int:
        """
        (İş Günü − İzin Günü) × 420 dakika formülü.
        Emzirme izninde günlük 90 dakika düşülür.
        """
        try:
            from core.hesaplamalar import ay_is_gunu

            tatiller = self._tatil_listesi_getir(yil, ay)
            is_gunu  = ay_is_gunu(yil, ay, tatil_listesi=tatiller)
            izin_gun = self._izin_is_gunu(personel_id, yil, ay, tatiller)
            net_gun  = max(0, is_gunu - izin_gun)

            hedef = net_gun * GUNLUK_HEDEF_DAKIKA

            if hedef_tipi == "emzirme":
                # Günde 1.5 saat (90 dakika) izinli — iş günü başına düşülür
                hedef = max(0, hedef - net_gun * 90)
            elif hedef_tipi in ("sua", "yillik", "rapor", "idari", "dini_izin"):
                # İzin günleri zaten düşüldü
                pass

            return hedef
        except Exception as e:
            logger.debug(f"Hedef hesaplama: {e}")
            return GUNLUK_HEDEF_DAKIKA * 20  # Varsayılan: 20 iş günü

    def _izin_is_gunu(self, personel_id: str, yil: int,
                      ay: int, tatiller: list[str]) -> int:
        """Personelin o aydaki izin iş günü sayısı."""
        try:
            rows    = self._r.get("Izin_Giris").get_all() or []
            ay_bas  = f"{yil:04d}-{ay:02d}-01"
            ay_bit  = f"{yil:04d}-{ay:02d}-{monthrange(yil, ay)[1]:02d}"
            sayi    = 0
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
                # İzin aralığındaki iş günlerini say
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

    def _birim_adi_bul(self, birim_id: str) -> Optional[str]:
        """BirimID → BirimAdi dönüşümü."""
        try:
            rows = self._r.get("NB_Birim").get_all() or []
            kayit = next(
                (r for r in rows if r.get("BirimID") == birim_id), None)
            return kayit["BirimAdi"] if kayit else None
        except Exception:
            return None

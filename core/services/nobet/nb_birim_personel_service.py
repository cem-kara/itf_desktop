"""
nb_birim_personel_service.py — NB_BirimPersonel yönetimi

Personel ↔ Birim çoktan-çoğa ilişki.

NOT: Personel.GorevYeri FHSZ kapsamında korunur, dokunulmaz.
     Bu tablo nöbet modülü için ek/ikincil birim atamasını sağlar.
     Algoritma ve tercih servisleri önce bu tabloyu dener,
     bulamazsa GorevYeri fallback ile devam eder.

Kullanım senaryoları:
  - Bir teknisyen hem Acil hem MR'da nöbet tutabilir
  - Rotasyon: geçici süre başka birimde görev
  - AnabirimMi=0 ile ikincil birim
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from core.hata_yonetici import SonucYonetici, logger
from database.repository_registry import RepositoryRegistry


def _yeni_id() -> str:
    return str(uuid.uuid4())


def _simdi() -> str:
    return date.today().isoformat()


ROLLER = ["teknisyen", "uzman", "sorumlu", "asistan"]


class NbBirimPersonelService:
    """
    NB_BirimPersonel CRUD.

    Kullanım:
        svc = NbBirimPersonelService(registry)
        svc.personel_ata(birim_id, personel_id)
        personeller = svc.birim_personelleri(birim_id)
    """

    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("RepositoryRegistry boş olamaz")
        self._r = registry

    # ──────────────────────────────────────────────────────────
    #  Okuma
    # ──────────────────────────────────────────────────────────

    def birim_personelleri(self, birim_id: str,
                           sadece_aktif: bool = True) -> SonucYonetici:
        """
        Birime atanmış personel listesi.
        Personel adı join edilmiş olarak döner.
        """
        try:
            rows = self._r.get("NB_BirimPersonel").get_all() or []
            ilgili = [
                r for r in rows
                if str(r.get("BirimID", "")) == str(birim_id)
                and (not sadece_aktif or int(r.get("Aktif", 1)))
                and (not sadece_aktif or not r.get("GorevBitis")
                     or r.get("GorevBitis") >= _simdi())
            ]

            # Personel adlarını join et
            p_rows = self._r.get("Personel").get_all() or []
            p_map  = {str(p["KimlikNo"]): p for p in p_rows}

            sonuc = []
            for r in sorted(ilgili,
                             key=lambda x: p_map.get(
                                 str(x.get("PersonelID","")),{}
                             ).get("AdSoyad","")):
                pid  = str(r.get("PersonelID",""))
                p    = p_map.get(pid, {})
                sonuc.append({
                    **dict(r),
                    "AdSoyad":      p.get("AdSoyad",""),
                    "HizmetSinifi": p.get("HizmetSinifi",""),
                    "GorevYeri":    p.get("GorevYeri",""),
                })
            return SonucYonetici.tamam(veri=sonuc)
        except Exception as e:
            return SonucYonetici.hata(e, "NbBirimPersonelService.birim_personelleri")

    def personel_birimleri(self, personel_id: str,
                           sadece_aktif: bool = True) -> SonucYonetici:
        """
        Personelin atandığı tüm birimleri döner.
        Çoklu birimde çalışanlar için.
        """
        try:
            rows = self._r.get("NB_BirimPersonel").get_all() or []
            ilgili = [
                r for r in rows
                if str(r.get("PersonelID","")) == str(personel_id)
                and (not sadece_aktif or int(r.get("Aktif", 1)))
                and (not sadece_aktif or not r.get("GorevBitis")
                     or r.get("GorevBitis") >= _simdi())
            ]

            # Birim adlarını join et
            b_rows = self._r.get("NB_Birim").get_all() or []
            b_map  = {str(b["BirimID"]): b for b in b_rows}

            sonuc = []
            for r in sorted(ilgili,
                             key=lambda x: int(x.get("AnabirimMi", 1)),
                             reverse=True):
                bid = str(r.get("BirimID",""))
                b   = b_map.get(bid, {})
                sonuc.append({
                    **dict(r),
                    "BirimAdi":  b.get("BirimAdi",""),
                    "BirimKodu": b.get("BirimKodu",""),
                })
            return SonucYonetici.tamam(veri=sonuc)
        except Exception as e:
            return SonucYonetici.hata(e, "NbBirimPersonelService.personel_birimleri")

    def _atama_var_mi(self, birim_id: str, personel_id: str) -> bool:
        """Aktif atama kaydı var mı?"""
        try:
            rows = self._r.get("NB_BirimPersonel").get_all() or []
            return any(
                str(r.get("BirimID","")) == str(birim_id)
                and str(r.get("PersonelID","")) == str(personel_id)
                and int(r.get("Aktif", 1))
                and (not r.get("GorevBitis") or r.get("GorevBitis") >= _simdi())
                for r in rows
            )
        except Exception:
            return False

    def atama_var_mi(self, birim_id: str, personel_id: str) -> SonucYonetici:
        """Aktif atama kaydı var mı?"""
        try:
            return SonucYonetici.tamam(veri=self._atama_var_mi(birim_id, personel_id))
        except Exception as e:
            return SonucYonetici.hata(e, "NbBirimPersonelService.atama_var_mi")

    def _personel_pid_listesi(self, birim_id: str) -> list[str]:
        """
        Birime atanmış aktif personel ID listesi.
        Algoritma ve tercih servisi için hızlı erişim.
        GorevYeri fallback için: boş dönerse GorevYeri kullanılır.
        """
        try:
            rows = self._r.get("NB_BirimPersonel").get_all() or []
            return [
                str(r.get("PersonelID",""))
                for r in rows
                if str(r.get("BirimID","")) == str(birim_id)
                and int(r.get("Aktif", 1))
                and (not r.get("GorevBitis") or r.get("GorevBitis") >= _simdi())
            ]
        except Exception:
            return []

    def personel_pid_listesi(self, birim_id: str) -> SonucYonetici:
        """Birime atanmış aktif personel ID listesini döner."""
        try:
            return SonucYonetici.tamam(veri=self._personel_pid_listesi(birim_id))
        except Exception as e:
            return SonucYonetici.hata(e, "NbBirimPersonelService.personel_pid_listesi")

    # ──────────────────────────────────────────────────────────
    #  Yazma
    # ──────────────────────────────────────────────────────────

    def personel_ata(self, birim_id: str, personel_id: str,
                     rol: str = "teknisyen",
                     ana_birim: bool = True,
                     gorev_baslangic: Optional[str] = None,
                     notlar: str = "") -> SonucYonetici:
        """
        Personeli birime atar.
        Zaten aktif atama varsa hata döner.
        """
        try:
            if rol not in ROLLER:
                return SonucYonetici.hata(
                    ValueError(f"Geçersiz rol: {rol}. Geçerli: {ROLLER}"))

            if self._atama_var_mi(birim_id, personel_id):
                return SonucYonetici.hata(
                    ValueError("Bu personelin bu birimde zaten aktif ataması var."))

            veri = {
                "ID":             _yeni_id(),
                "BirimID":        str(birim_id),
                "PersonelID":     str(personel_id),
                "Rol":            rol,
                "GorevBaslangic": gorev_baslangic or _simdi(),
                "GorevBitis":     None,
                "AnabirimMi":     1 if ana_birim else 0,
                "Aktif":          1,
                "Notlar":         notlar,
                "created_at":     _simdi(),
            }
            self._r.get("NB_BirimPersonel").insert(veri)
            logger.info(f"Personel atandı: {personel_id} → {birim_id} ({rol})")
            return SonucYonetici.tamam("Personel birime atandı", veri=veri)
        except Exception as e:
            return SonucYonetici.hata(e, "NbBirimPersonelService.personel_ata")

    def atama_guncelle(self, atama_id: str,
                       rol: Optional[str] = None,
                       ana_birim: Optional[bool] = None,
                       gorev_bitis: Optional[str] = None,
                       notlar: Optional[str] = None) -> SonucYonetici:
        """Atama kaydını günceller."""
        try:
            guncelleme = {"updated_at": _simdi()}
            if rol is not None:
                if rol not in ROLLER:
                    return SonucYonetici.hata(
                        ValueError(f"Geçersiz rol: {rol}"))
                guncelleme["Rol"] = rol
            if ana_birim is not None:
                guncelleme["AnabirimMi"] = 1 if ana_birim else 0
            if gorev_bitis is not None:
                guncelleme["GorevBitis"] = gorev_bitis
                guncelleme["Aktif"]      = 0
            if notlar is not None:
                guncelleme["Notlar"] = notlar

            self._r.get("NB_BirimPersonel").update(atama_id, guncelleme)
            return SonucYonetici.tamam("Atama güncellendi")
        except Exception as e:
            return SonucYonetici.hata(e, "NbBirimPersonelService.atama_guncelle")

    def gorevden_al(self, birim_id: str, personel_id: str,
                    bitis_tarihi: Optional[str] = None) -> SonucYonetici:
        """
        Personelin birim atamasını sonlandırır.
        GorevBitis set edilir, Aktif=0 yapılır.
        Kayıt silinmez — tarihsel veri korunur.
        """
        try:
            rows = self._r.get("NB_BirimPersonel").get_all() or []
            atama = next(
                (r for r in rows
                 if str(r.get("BirimID","")) == str(birim_id)
                 and str(r.get("PersonelID","")) == str(personel_id)
                 and int(r.get("Aktif", 1))),
                None
            )
            if not atama:
                return SonucYonetici.hata(
                    ValueError("Aktif atama kaydı bulunamadı."))

            self._r.get("NB_BirimPersonel").update(atama["ID"], {
                "GorevBitis": bitis_tarihi or _simdi(),
                "Aktif":      0,
                "updated_at": _simdi(),
            })
            logger.info(f"Atama sonlandırıldı: {personel_id} ← {birim_id}")
            return SonucYonetici.tamam("Görevden alındı")
        except Exception as e:
            return SonucYonetici.hata(e, "NbBirimPersonelService.gorevden_al")

    def toplu_gorev_yeri_migrate(self, birim_id: str) -> SonucYonetici:
        """
        GorevYeri → NB_BirimPersonel geçiş yardımcısı.

        Birime ait GorevYeri'ni NB_Birim.BirimAdi ile eşleştirip
        NB_BirimPersonel'e kayıt oluşturur.
        Zaten kaydı olanlar atlanır (idempotent).

        NOT: Personel.GorevYeri FHSZ kapsamında değiştirilmez.
        """
        try:
            # BirimAdi'ni bul
            b_rows = self._r.get("NB_Birim").get_all() or []
            birim  = next(
                (b for b in b_rows if b.get("BirimID") == birim_id), None)
            if not birim:
                return SonucYonetici.hata(
                    ValueError(f"Birim bulunamadı: {birim_id}"))
            birim_adi = birim["BirimAdi"]

            # GorevYeri bu birime eşit olan personeller
            p_rows = self._r.get("Personel").get_all() or []
            hedefler = [
                p for p in p_rows
                if str(p.get("GorevYeri","")).strip() == birim_adi
            ]

            eklenen = 0
            atlanan = 0
            for p in hedefler:
                pid = str(p["KimlikNo"])
                if self._atama_var_mi(birim_id, pid):
                    atlanan += 1
                    continue
                self.personel_ata(birim_id, pid, rol="teknisyen",
                                  ana_birim=True)
                eklenen += 1

            return SonucYonetici.tamam(
                f"Migrasyon tamamlandı: {eklenen} eklendi, {atlanan} atlandı",
                veri={"eklenen": eklenen, "atlanan": atlanan})
        except Exception as e:
            return SonucYonetici.hata(
                e, "NbBirimPersonelService.toplu_gorev_yeri_migrate")

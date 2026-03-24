"""
nb_vardiya_service.py — NB_VardiyaGrubu + NB_Vardiya yönetimi

Slot kavramı:
  Bir VardiyaGrubu = bir slot.
  Grup içindeki Vardiyalar = o slotun zaman dilimleri.
  Örnek: "24 Saat" grubu → Gündüz(08-20) + Gece(20-08)
  Algoritma bir personeli bir gruba (tüm vardiyas) atar.
  Slot bölününce her vardiyaya ayrı personel atanır.

Rol:
  ana       → algoritma bu vardiyayı slot için doldurur
  yardimci  → sadece manuel ekleme veya slot bölünmesinde kullanılır
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from core.hata_yonetici import SonucYonetici, logger
from database.repository_registry import RepositoryRegistry


def _yeni_id() -> str:
    return str(uuid.uuid4())


def _simdi() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _sure_dakika(bas: str, bit: str) -> int:
    """
    '08:00', '20:00' → 720 dakika.
    Gece geçişini destekler: '20:00', '08:00' → 720 dakika.
    """
    try:
        bh, bm = map(int, bas.split(":"))
        eh, em = map(int, bit.split(":"))
        toplam = (eh * 60 + em) - (bh * 60 + bm)
        if toplam <= 0:
            toplam += 24 * 60
        return toplam
    except Exception:
        return 0


class NbVardiyaService:
    """
    NB_VardiyaGrubu ve NB_Vardiya CRUD + algoritma yardımcıları.

    Kullanım:
        svc = NbVardiyaService(registry)
        gruplar = svc.get_gruplar(birim_id)
        svc.grup_ekle(birim_id, "24 Saat Nöbet", vardiyalar=[...])
    """

    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("RepositoryRegistry boş olamaz")
        self._r = registry

    # ──────────────────────────────────────────────────────────
    #  Grup Okuma
    # ──────────────────────────────────────────────────────────

    def get_gruplar(self, birim_id: str,
                    sadece_aktif: bool = True) -> SonucYonetici:
        """
        Birime ait vardiya gruplarını döner.
        Her gruba bağlı vardiyalar 'vardiyalar' alanında liste olarak gelir.
        """
        try:
            g_rows = self._r.get("NB_VardiyaGrubu").get_all() or []
            v_rows = self._r.get("NB_Vardiya").get_all() or []

            gruplar = [r for r in g_rows
                       if str(r.get("BirimID", "")) == str(birim_id)]
            if sadece_aktif:
                gruplar = [r for r in gruplar if int(r.get("Aktif", 1))]
            gruplar = sorted(gruplar, key=lambda r: int(r.get("Sira", 1)))

            sonuc = []
            for g in gruplar:
                gid = g["GrupID"]
                vardiyalar = sorted(
                    [v for v in v_rows
                     if str(v.get("GrupID", "")) == gid
                     and (not sadece_aktif or int(v.get("Aktif", 1)))],
                    key=lambda v: int(v.get("Sira", 1))
                )
                sonuc.append({**dict(g), "vardiyalar": vardiyalar})

            return SonucYonetici.tamam(veri=sonuc)
        except Exception as e:
            return SonucYonetici.hata(e, "NbVardiyaService.get_gruplar")

    def get_vardiyalar(self, birim_id: str,
                       sadece_aktif: bool = True,
                       sadece_ana: bool = False) -> SonucYonetici:
        """
        Birime ait tüm vardiyas — düz liste.
        sadece_ana=True → Rol='ana' olanlar (algoritma için).
        """
        try:
            rows = self._r.get("NB_Vardiya").get_all() or []
            rows = [r for r in rows
                    if str(r.get("BirimID", "")) == str(birim_id)]
            if sadece_aktif:
                rows = [r for r in rows if int(r.get("Aktif", 1))]
            if sadece_ana:
                rows = [r for r in rows
                        if (r.get("Rol") or "ana") == "ana"]
            rows = sorted(rows, key=lambda r: (
                int(r.get("Sira", 1)),
                str(r.get("BasSaat", ""))
            ))
            return SonucYonetici.tamam(veri=rows)
        except Exception as e:
            return SonucYonetici.hata(e, "NbVardiyaService.get_vardiyalar")

    def get_vardiya(self, vardiya_id: str) -> Optional[dict]:
        """Tek vardiya kaydı — yok ise None."""
        try:
            rows = self._r.get("NB_Vardiya").get_all() or []
            kayit = next(
                (r for r in rows if r.get("VardiyaID") == vardiya_id), None)
            return dict(kayit) if kayit else None
        except Exception:
            return None

    def slot_suresi_getir(self, birim_id: str) -> int:
        """
        Bir slotun toplam süresi (dakika).
        Önce NB_BirimAyar.GunlukSlotDakika — yoksa Σ ana vardiya süresi.
        Algoritma bu değeri hedef saat karşılaştırmasında kullanır.
        """
        try:
            # BirimAyar'da elle girilmiş değer var mı?
            a_rows = self._r.get("NB_BirimAyar").get_all() or []
            ayar   = next(
                (r for r in a_rows
                 if str(r.get("BirimID", "")) == str(birim_id)
                 and int(r.get("Aktif", 1) if "Aktif" in (r or {}) else 1)),
                None
            )
            if ayar and ayar.get("GunlukSlotDakika"):
                return int(ayar["GunlukSlotDakika"])

            # Yoksa ana vardiyas toplamı
            v_sonuc = self.get_vardiyalar(birim_id, sadece_ana=True)
            if v_sonuc.basarili and v_sonuc.veri:
                return sum(int(v.get("SureDakika", 0))
                           for v in v_sonuc.veri)
        except Exception as e:
            logger.debug(f"slot_suresi_getir: {e}")

        return 24 * 60  # Fallback: 24 saat

    # ──────────────────────────────────────────────────────────
    #  Grup Yazma
    # ──────────────────────────────────────────────────────────

    def grup_ekle(self, birim_id: str, grup_adi: str,
                  grup_turu: str = "zorunlu",
                  sira: int = 1,
                  vardiyalar: Optional[list[dict]] = None) -> SonucYonetici:
        """
        Vardiya grubu oluşturur ve isteğe bağlı vardiyas ekler.

        vardiyalar: [{"VardiyaAdi", "BasSaat", "BitSaat",
                      "Rol", "MinPersonel", "Sira"}, ...]
        """
        try:
            grup_adi = grup_adi.strip()
            if not grup_adi:
                return SonucYonetici.hata(ValueError("Grup adı boş olamaz"))

            # Aynı birimde aynı isimde aktif grup var mı?
            g_rows = self._r.get("NB_VardiyaGrubu").get_all() or []
            if any(str(r.get("BirimID", "")) == str(birim_id)
                   and r.get("GrupAdi", "").strip() == grup_adi
                   and int(r.get("Aktif", 1))
                   for r in g_rows):
                return SonucYonetici.hata(
                    ValueError(f"'{grup_adi}' adında grup zaten mevcut"))

            grup_id = _yeni_id()
            self._r.get("NB_VardiyaGrubu").insert({
                "GrupID":    grup_id,
                "BirimID":   str(birim_id),
                "GrupAdi":   grup_adi,
                "GrupTuru":  grup_turu,
                "Sira":      sira,
                "Aktif":     1,
                "created_at": _simdi(),
            })

            eklenen_v = []
            for i, v in enumerate(vardiyalar or [], start=1):
                v_sonuc = self.vardiya_ekle(
                    grup_id=grup_id,
                    birim_id=birim_id,
                    vardiya_adi=v.get("VardiyaAdi", f"Vardiya {i}"),
                    bas_saat=v.get("BasSaat", "08:00"),
                    bit_saat=v.get("BitSaat", "20:00"),
                    rol=v.get("Rol", "ana"),
                    min_personel=int(v.get("MinPersonel", 1)),
                    sira=int(v.get("Sira", i)),
                )
                if v_sonuc.basarili:
                    eklenen_v.append(v_sonuc.veri)

            logger.info(f"Grup eklendi: {grup_adi} "
                        f"({len(eklenen_v)} vardiya)")
            return SonucYonetici.tamam(
                f"'{grup_adi}' grubu eklendi",
                veri={"GrupID": grup_id, "vardiyalar": eklenen_v})

        except Exception as e:
            return SonucYonetici.hata(e, "NbVardiyaService.grup_ekle")

    def grup_guncelle(self, grup_id: str,
                      grup_adi: str = "",
                      sira: int = -1,
                      aktif: Optional[bool] = None) -> SonucYonetici:
        """Grup bilgilerini günceller."""
        try:
            guncelleme = {"updated_at": _simdi()}
            if grup_adi:
                guncelleme["GrupAdi"] = grup_adi.strip()
            if sira >= 0:
                guncelleme["Sira"] = sira
            if aktif is not None:
                guncelleme["Aktif"] = 1 if aktif else 0
            self._r.get("NB_VardiyaGrubu").update(grup_id, guncelleme)
            return SonucYonetici.tamam("Grup güncellendi")
        except Exception as e:
            return SonucYonetici.hata(e, "NbVardiyaService.grup_guncelle")

    def grup_sil(self, grup_id: str) -> SonucYonetici:
        """
        Grubu ve bağlı vardiyaları pasife alır.
        Aktif plan satırı varsa reddeder.
        """
        try:
            # Aktif plan satırı var mı?
            try:
                ps_rows = self._r.get("NB_PlanSatir").get_all() or []
                v_ids   = {
                    v["VardiyaID"]
                    for v in (self._r.get("NB_Vardiya").get_all() or [])
                    if str(v.get("GrupID", "")) == grup_id
                }
                aktif_plan = any(
                    r.get("VardiyaID") in v_ids
                    and r.get("Durum") == "aktif"
                    for r in ps_rows
                )
                if aktif_plan:
                    return SonucYonetici.hata(
                        ValueError(
                            "Bu gruba ait aktif nöbet planı var. "
                            "Önce ilgili planları iptal edin."))
            except Exception:
                pass

            # Vardiyas pasife al
            v_rows = self._r.get("NB_Vardiya").get_all() or []
            for v in v_rows:
                if str(v.get("GrupID", "")) == grup_id:
                    self._r.get("NB_Vardiya").update(
                        v["VardiyaID"],
                        {"Aktif": 0, "updated_at": _simdi()})

            # Grubu pasife al
            self._r.get("NB_VardiyaGrubu").update(
                grup_id, {"Aktif": 0, "updated_at": _simdi()})

            logger.info(f"Grup silindi (pasif): {grup_id}")
            return SonucYonetici.tamam("Grup ve vardiyaları pasife alındı")
        except Exception as e:
            return SonucYonetici.hata(e, "NbVardiyaService.grup_sil")

    # ──────────────────────────────────────────────────────────
    #  Vardiya Yazma
    # ──────────────────────────────────────────────────────────

    def vardiya_ekle(self, grup_id: str, birim_id: str,
                     vardiya_adi: str,
                     bas_saat: str, bit_saat: str,
                     rol: str = "ana",
                     min_personel: int = 1,
                     sira: int = 1) -> SonucYonetici:
        """Gruba yeni vardiya zaman dilimi ekler."""
        try:
            vardiya_adi = vardiya_adi.strip()
            if not vardiya_adi:
                return SonucYonetici.hata(
                    ValueError("Vardiya adı boş olamaz"))
            if rol not in ("ana", "yardimci"):
                return SonucYonetici.hata(
                    ValueError(f"Geçersiz rol: {rol} — 'ana' veya 'yardimci' olmalı"))

            sure = _sure_dakika(bas_saat, bit_saat)
            if sure <= 0:
                return SonucYonetici.hata(
                    ValueError(f"Geçersiz saat: {bas_saat}–{bit_saat}"))

            veri = {
                "VardiyaID":  _yeni_id(),
                "GrupID":     grup_id,
                "BirimID":    str(birim_id),
                "VardiyaAdi": vardiya_adi,
                "BasSaat":    bas_saat,
                "BitSaat":    bit_saat,
                "SureDakika": sure,
                "Rol":        rol,
                "MinPersonel": min_personel,
                "Sira":       sira,
                "Aktif":      1,
                "created_at": _simdi(),
            }
            self._r.get("NB_Vardiya").insert(veri)
            logger.info(f"Vardiya eklendi: {vardiya_adi} "
                        f"({bas_saat}–{bit_saat}, {sure} dk, rol={rol})")
            return SonucYonetici.tamam(
                f"'{vardiya_adi}' vardiyası eklendi", veri=veri)
        except Exception as e:
            return SonucYonetici.hata(e, "NbVardiyaService.vardiya_ekle")

    def vardiya_guncelle(self, vardiya_id: str,
                         vardiya_adi: str = "",
                         bas_saat: str = "",
                         bit_saat: str = "",
                         rol: str = "",
                         min_personel: int = -1,
                         sira: int = -1) -> SonucYonetici:
        """Vardiya bilgilerini günceller. SureDakika otomatik hesaplanır."""
        try:
            guncelleme = {"updated_at": _simdi()}
            if vardiya_adi:
                guncelleme["VardiyaAdi"] = vardiya_adi.strip()
            if rol in ("ana", "yardimci"):
                guncelleme["Rol"] = rol
            if min_personel >= 0:
                guncelleme["MinPersonel"] = min_personel
            if sira >= 0:
                guncelleme["Sira"] = sira

            if bas_saat or bit_saat:
                mevcut = self.get_vardiya(vardiya_id)
                yeni_bas = bas_saat or (mevcut or {}).get("BasSaat", "08:00")
                yeni_bit = bit_saat or (mevcut or {}).get("BitSaat", "20:00")
                guncelleme["BasSaat"]    = yeni_bas
                guncelleme["BitSaat"]    = yeni_bit
                guncelleme["SureDakika"] = _sure_dakika(yeni_bas, yeni_bit)

            self._r.get("NB_Vardiya").update(vardiya_id, guncelleme)
            return SonucYonetici.tamam("Vardiya güncellendi")
        except Exception as e:
            return SonucYonetici.hata(e, "NbVardiyaService.vardiya_guncelle")

    def vardiya_pasif_al(self, vardiya_id: str) -> SonucYonetici:
        """Vardiyayı pasife alır (soft delete)."""
        try:
            self._r.get("NB_Vardiya").update(
                vardiya_id, {"Aktif": 0, "updated_at": _simdi()})
            return SonucYonetici.tamam("Vardiya pasife alındı")
        except Exception as e:
            return SonucYonetici.hata(e, "NbVardiyaService.vardiya_pasif_al")

    # ──────────────────────────────────────────────────────────
    #  Hazır Şablonlar
    # ──────────────────────────────────────────────────────────

    def sablon_yukle(self, birim_id: str,
                     sablon: str) -> SonucYonetici:
        """
        Yaygın nöbet modellerini tek komutla yükler.

        Şablonlar:
          tam_gun_24h      → Gündüz(08-20) + Gece(20-08), 1 grup
          sadece_gunduz_12h→ Gündüz(08-20), 1 grup
          uzatilmis_gunduz → Gündüz(08-20) + Hafif Gece(20-00), 2 vardiya
          uc_vardiya_8h    → Sabah(08-16) + Akşam(16-24) + Gece(00-08)
        """
        SABLONLAR = {
            "tam_gun_24h": {
                "GrupAdi": "24 Saat Nöbet",
                "GrupTuru": "zorunlu",
                "vardiyalar": [
                    {"VardiyaAdi": "Gündüz", "BasSaat": "08:00",
                     "BitSaat": "20:00", "Rol": "ana", "MinPersonel": 1, "Sira": 1},
                    {"VardiyaAdi": "Gece",   "BasSaat": "20:00",
                     "BitSaat": "08:00", "Rol": "ana", "MinPersonel": 1, "Sira": 2},
                ],
            },
            "sadece_gunduz_12h": {
                "GrupAdi": "Gündüz Nöbet",
                "GrupTuru": "zorunlu",
                "vardiyalar": [
                    {"VardiyaAdi": "Gündüz", "BasSaat": "08:00",
                     "BitSaat": "20:00", "Rol": "ana", "MinPersonel": 1, "Sira": 1},
                ],
            },
            "uzatilmis_gunduz": {
                "GrupAdi": "Uzatılmış Gündüz",
                "GrupTuru": "zorunlu",
                "vardiyalar": [
                    {"VardiyaAdi": "Gündüz",      "BasSaat": "08:00",
                     "BitSaat": "20:00", "Rol": "ana",      "MinPersonel": 1, "Sira": 1},
                    {"VardiyaAdi": "Akşam/Gece",  "BasSaat": "20:00",
                     "BitSaat": "00:00", "Rol": "yardimci", "MinPersonel": 0, "Sira": 2},
                ],
            },
            "uc_vardiya_8h": {
                "GrupAdi": "3 Vardiya",
                "GrupTuru": "zorunlu",
                "vardiyalar": [
                    {"VardiyaAdi": "Sabah",  "BasSaat": "08:00",
                     "BitSaat": "16:00", "Rol": "ana", "MinPersonel": 1, "Sira": 1},
                    {"VardiyaAdi": "Akşam",  "BasSaat": "16:00",
                     "BitSaat": "00:00", "Rol": "ana", "MinPersonel": 1, "Sira": 2},
                    {"VardiyaAdi": "Gece",   "BasSaat": "00:00",
                     "BitSaat": "08:00", "Rol": "ana", "MinPersonel": 1, "Sira": 3},
                ],
            },
        }

        if sablon not in SABLONLAR:
            return SonucYonetici.hata(
                ValueError(
                    f"Bilinmeyen şablon: '{sablon}'. "
                    f"Geçerli: {', '.join(SABLONLAR)}"))

        s = SABLONLAR[sablon]
        return self.grup_ekle(
            birim_id=birim_id,
            grup_adi=s["GrupAdi"],
            grup_turu=s["GrupTuru"],
            vardiyalar=s["vardiyalar"],
        )

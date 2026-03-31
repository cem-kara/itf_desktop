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

import json
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

    def gecerli_kural(self, tarih: Optional[str] = None) -> SonucYonetici:
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
                return SonucYonetici.tamam(veri=None)
            kurum_genel = [
                r for r in gecerli
                if str(r.get("KuralTuru", "")).strip().lower() == "kurum_genel"
            ]
            adaylar = kurum_genel or gecerli
            return SonucYonetici.tamam(veri=dict(max(
                adaylar,
                key=lambda r: (
                    str(r.get("GeserlilikBaslangic", "")),
                    str(r.get("created_at", "")),
                    str(r.get("KuralID", "")),
                ),
            )))
        except Exception as e:
            return SonucYonetici.hata(e, "NbMesaiService.gecerli_kural")

    def get_kurum_genel_kural(self, tarih: Optional[str] = None) -> SonucYonetici:
        """Aktif kurum-genel kuralı çözümlenmiş parametreleriyle döner."""
        try:
            kural_sonuc = self.gecerli_kural(tarih)
            if not kural_sonuc.basarili:
                return kural_sonuc
            kural = kural_sonuc.veri
            param = self._kural_parametreleri(kural)
            return SonucYonetici.tamam(veri={
                "KuralID": (kural or {}).get("KuralID", ""),
                "KuralAdi": (kural or {}).get("KuralAdi", "Kurum Genel Mesai Kuralı"),
                "KuralTuru": (kural or {}).get("KuralTuru", "kurum_genel"),
                "GeserlilikBaslangic": (kural or {}).get("GeserlilikBaslangic", ""),
                "GeserlilikBitis": (kural or {}).get("GeserlilikBitis", ""),
                "Aciklama": (kural or {}).get("Aciklama", ""),
                **param,
            })
        except Exception as e:
            return SonucYonetici.hata(e, "NbMesaiService.get_kurum_genel_kural")

    @staticmethod
    def _to_int(value, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _to_bool(value, default: bool = False) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("1", "true", "evet", "yes")

    def _kural_parametreleri(self, kural: Optional[dict]) -> dict:
        """
        NB_MesaiKural.Parametre JSON'unu çözer ve kurum-genel varsayılanları döner.

        Desteklenen parametreler:
          sabit_hedef_dakika: int (örn. 144 saat = 8640)
          bildirim_esik_dakika: int (örn. 12 saat = 720)
          bildirim_temeli: 'donem_farki' | 'net_bakiye'
          kapanis_politikasi: 'devret' | 'tam_odeme_sifirla' | 'izinle_sifirla'
          negatif_devir_izinli: bool
        """
        default = {
            "sabit_hedef_dakika": 0,
            "bildirim_esik_dakika": 0,
            "bildirim_temeli": "donem_farki",
            "kapanis_politikasi": "devret",
            "negatif_devir_izinli": True,
        }
        if not kural:
            return default

        raw = kural.get("Parametre", "{}")
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else dict(raw or {})
        except Exception:
            parsed = {}

        temel = str(parsed.get("bildirim_temeli", default["bildirim_temeli"]))
        if temel not in ("donem_farki", "net_bakiye"):
            temel = default["bildirim_temeli"]

        kapanis = str(parsed.get("kapanis_politikasi", default["kapanis_politikasi"]))
        if kapanis not in ("devret", "tam_odeme_sifirla", "izinle_sifirla"):
            kapanis = default["kapanis_politikasi"]

        return {
            "sabit_hedef_dakika": max(0, self._to_int(parsed.get("sabit_hedef_dakika", 0), 0)),
            "bildirim_esik_dakika": max(0, self._to_int(parsed.get("bildirim_esik_dakika", 0), 0)),
            "bildirim_temeli": temel,
            "kapanis_politikasi": kapanis,
            "negatif_devir_izinli": self._to_bool(
                parsed.get("negatif_devir_izinli", default["negatif_devir_izinli"]),
                default=True,
            ),
        }

    def _kural_bildirim_dakika(self, fazla_dk: int, toplam_dk: int, param: dict) -> int:
        temel = param.get("bildirim_temeli", "donem_farki")
        esik = int(param.get("bildirim_esik_dakika", 0) or 0)
        aday = toplam_dk if temel == "net_bakiye" else fazla_dk
        if aday <= 0:
            return 0
        if aday <= esik:
            return 0
        return aday

    def _kural_kapanis_hesapla(self, toplam_dk: int, mevcut_odenen: int, param: dict) -> tuple[int, int]:
        """(odenen_dakika, devire_giden_dakika) döner."""
        kapanis = param.get("kapanis_politikasi", "devret")
        negatif_izinli = bool(param.get("negatif_devir_izinli", True))

        if kapanis in ("tam_odeme_sifirla", "izinle_sifirla") and toplam_dk > 0:
            odenen = toplam_dk
            devir = 0
        else:
            odenen = max(0, mevcut_odenen)
            devir = toplam_dk - odenen

        if not negatif_izinli and devir < 0:
            devir = 0
        return odenen, devir

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

    def kurum_genel_kural_kaydet(self,
                                 aylik_hedef_saat: int = 144,
                                 bildirim_esik_saat: int = 12,
                                 bildirim_temeli: str = "donem_farki",
                                 kapanis_politikasi: str = "devret",
                                 negatif_devir_izinli: bool = True,
                                 gecerlilik_baslangic: str = "2020-01-01") -> SonucYonetici:
        """
        Kurum-genel fazla mesai/bildirim kuralı oluşturur.

        Not: Bu yapı ücret hesaplamaz, sadece bildirim ve devir davranışını belirler.
        """
        return self.kural_ekle(
            kural_adi="Kurum Genel Mesai Kuralı",
            kural_turu="kurum_genel",
            parametre={
                "sabit_hedef_dakika": max(0, int(aylik_hedef_saat)) * 60,
                "bildirim_esik_dakika": max(0, int(bildirim_esik_saat)) * 60,
                "bildirim_temeli": str(bildirim_temeli),
                "kapanis_politikasi": str(kapanis_politikasi),
                "negatif_devir_izinli": bool(negatif_devir_izinli),
            },
            gecerlilik_baslangic=gecerlilik_baslangic,
            aciklama=(
                "Kurum geneli sabit hedef + bildirim eşiği. "
                "Ücret hesaplanmaz, sadece bildirim/devir yönetilir."
            ),
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
                    HedefDakika    = NB_PersonelTercih.HedefDakika (varsa, direkt)
                                                     yoksa otomatik
                    BayramDakika   = resmi/dini bayram günlerinde çalışılan toplam dakika
                    FazlaDakika    = (CalisDakika − HedefDakika) + BayramDakika
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

            # Resmi + dini bayram günleri hedef dışı ekstra mesaiye yazılır.
            bayram_tarihleri = set(self._tatil_listesi_getir(yil, ay))

            # Personel bazlı çalışılan dakika
            calisan: dict[str, int] = {}
            bayram_ekstra: dict[str, int] = {}
            for r in aktif_satirlar:
                pid  = str(r.get("PersonelID", ""))
                vsid = str(r.get("VardiyaID", ""))
                sure_dk = v_sure.get(vsid, GUNLUK_HEDEF_DAKIKA)
                calisan[pid] = calisan.get(pid, 0) + sure_dk

                tarih = str(r.get("NobetTarihi", "") or "")[:10]
                if tarih in bayram_tarihleri:
                    bayram_ekstra[pid] = bayram_ekstra.get(pid, 0) + sure_dk

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

            # Personel tercih/hedef haritası (aynı aydaki en güncel kayıt baz alınır)
            t_rows = self._r.get("NB_PersonelTercih").get_all() or []
            tercih_rows = [
                r for r in t_rows
                if str(r.get("BirimID", "")) == str(birim_id)
                and int(r.get("Yil", 0)) == yil
                and int(r.get("Ay", 0)) == ay
            ]
            tercih_rows.sort(
                key=lambda r: (
                    str(r.get("updated_at", "")),
                    str(r.get("created_at", "")),
                    str(r.get("TercihID", "")),
                )
            )

            hedef_map: dict[str, int] = {}
            for r in tercih_rows:
                pid = str(r.get("PersonelID", ""))
                if not pid:
                    continue
                hedef_raw = r.get("HedefDakika")
                if hedef_raw is None:
                    continue
                try:
                    hedef_map[pid] = int(hedef_raw)
                except (TypeError, ValueError):
                    continue

            # Birime aktif bağlı personeller (çalışma/tercih/devir kaydı olmasa da)
            bp_rows = self._r.get("NB_BirimPersonel").get_all() or []
            aktif_birim_pid = {
                str(r.get("PersonelID", ""))
                for r in bp_rows
                if str(r.get("BirimID", "")) == str(birim_id)
                and str(r.get("Aktif", 1)).strip() not in ("0", "False", "false")
                and str(r.get("PersonelID", "")).strip()
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

            # Kurum-genel kural parametreleri
            kural_sonuc = self.gecerli_kural(f"{yil:04d}-{ay:02d}-01")
            if not kural_sonuc.basarili:
                return kural_sonuc
            kural = kural_sonuc.veri
            kural_param = self._kural_parametreleri(kural)
            sabit_hedef_dk = int(kural_param.get("sabit_hedef_dakika", 0) or 0)

            # Hedefi tanımlı veya birime aktif bağlı olup bu ay çalışması/deviri
            # olmayan personel de fazla mesai listesinde görünmeli.
            tum_pid = (
                set(calisan.keys())
                | set(devir_map.keys())
                | set(hedef_map.keys())
                | aktif_birim_pid
            )
            sonuclar: list[dict] = []

            for pid in tum_pid:
                calisan_dk = calisan.get(pid, 0)

                hedef_tercih = hedef_map.get(pid)
                if sabit_hedef_dk > 0:
                    hedef_dk = sabit_hedef_dk
                elif hedef_tercih is not None:
                    # Kişiye ait ay hedefi açıkça girildiyse doğrudan kullan.
                    hedef_dk = int(hedef_tercih)
                else:
                    hedef_dk = self._otomatik_hedef(pid, yil, ay, birim_id)

                bayram_dk = bayram_ekstra.get(pid, 0)
                fazla_dk  = (calisan_dk - hedef_dk) + bayram_dk
                devir_dk  = devir_map.get(pid, 0)
                toplam_dk = fazla_dk + devir_dk

                # Mevcut OdenenDakika'yı koru veya politika gereği otomatik kapat.
                mevcut = mevcut_map.get(pid)
                odenen_dk = int(mevcut.get("OdenenDakika", 0)) if mevcut else 0
                odenen_dk, devire_dk = self._kural_kapanis_hesapla(
                    toplam_dk=toplam_dk,
                    mevcut_odenen=odenen_dk,
                    param=kural_param,
                )
                bildirim_dk = self._kural_bildirim_dakika(
                    fazla_dk=fazla_dk,
                    toplam_dk=toplam_dk,
                    param=kural_param,
                )

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

                sonuclar.append({
                    **veri,
                    "BildirimDakika": bildirim_dk,
                    "KuralKapanis": str(kural_param.get("kapanis_politikasi", "devret")),
                    "KuralTemel": str(kural_param.get("bildirim_temeli", "donem_farki")),
                })

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
            kural_sonuc = self.gecerli_kural()
            if not kural_sonuc.basarili:
                return kural_sonuc
            param = self._kural_parametreleri(kural_sonuc.veri)
            odenen_dk, devire_dk = self._kural_kapanis_hesapla(
                toplam_dk=toplam,
                mevcut_odenen=int(odenen_dakika),
                param={**param, "kapanis_politikasi": "devret"},
            )

            self._r.get("NB_MesaiHesap").update(hesap_id, {
                "OdenenDakika":      odenen_dk,
                "DevireGidenDakika": devire_dk,
                "updated_at":        _simdi(),
            })
            return SonucYonetici.tamam(
                f"Ödenen güncellendi: {odenen_dk} dk "
                f"(devir: {devire_dk} dk)")
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
            kural_sonuc = self.gecerli_kural()
            if not kural_sonuc.basarili:
                return kural_sonuc
            param = self._kural_parametreleri(kural_sonuc.veri)
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
                odenen_dk, devire_dk = self._kural_kapanis_hesapla(
                    toplam_dk=toplam,
                    mevcut_odenen=int(odenen),
                    param={**param, "kapanis_politikasi": "devret"},
                )
                self._r.get("NB_MesaiHesap").update(r["HesapID"], {
                    "OdenenDakika":      odenen_dk,
                    "DevireGidenDakika": devire_dk,
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

    def muhasebe_bildirim_listesi(self, birim_id: str, plan_id: str,
                                  yil: int, ay: int) -> SonucYonetici:
        """
        Ücret hesaplamadan, yalnızca fazla mesai bildirimi için liste üretir.
        """
        try:
            hesap_sonuc = self.get_hesaplar(birim_id, plan_id, yil, ay)
            if not hesap_sonuc.basarili:
                return hesap_sonuc

            kural_sonuc = self.gecerli_kural(f"{yil:04d}-{ay:02d}-01")
            if not kural_sonuc.basarili:
                return kural_sonuc
            kural = kural_sonuc.veri
            param = self._kural_parametreleri(kural)

            bildirimler = []
            for r in (hesap_sonuc.veri or []):
                fazla = int(r.get("FazlaDakika", 0))
                toplam = int(r.get("ToplamFazlaDakika", 0))
                bildirim_dk = self._kural_bildirim_dakika(fazla, toplam, param)
                if bildirim_dk <= 0:
                    continue
                bildirimler.append({
                    "PersonelID": str(r.get("PersonelID", "")),
                    "Yil": yil,
                    "Ay": ay,
                    "BirimID": str(birim_id),
                    "BildirimDakika": bildirim_dk,
                    "BildirimSaat": round(bildirim_dk / 60, 2),
                    "Kural": {
                        "Temel": param.get("bildirim_temeli", "donem_farki"),
                        "EsikDakika": int(param.get("bildirim_esik_dakika", 0) or 0),
                    },
                })

            return SonucYonetici.tamam(
                mesaj=f"{len(bildirimler)} personel için muhasebe bildirimi hazır.",
                veri=bildirimler,
            )
        except Exception as e:
            return SonucYonetici.hata(e, "NbMesaiService.muhasebe_bildirim_listesi")

    def get_personel_hesap(self, personel_id: str, birim_id: str,
                           plan_id: str,
                           yil: int, ay: int) -> SonucYonetici:
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
            return SonucYonetici.tamam(veri=dict(kayit) if kayit else None)
        except Exception as e:
            return SonucYonetici.hata(e, "NbMesaiService.get_personel_hesap")

    def ozet_dakika_to_saat(self, veri: dict) -> SonucYonetici:
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

        return SonucYonetici.tamam(veri={
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
        })

    # ──────────────────────────────────────────────────────────
    #  Yardımcılar
    # ──────────────────────────────────────────────────────────

    def _otomatik_hedef(self, personel_id: str,
                        yil: int, ay: int,
                        birim_id: str = "") -> int:
        """
        (İş Günü − İzin İş Günü) × günlük_dakika.
        HedefTipi'ne göre günlük dakika değişir:
          normal/rapor/yillik/idari → 420dk
          emzirme  → 330dk
          sendika  → 372dk
          sua      → 0dk
        """
        HEDEF_TIPI_DK = {
            "normal": 420, "rapor": 420, "yillik": 420, "idari": 420,
            "emzirme": 330, "sendika": 372, "sua": 0,
        }
        try:
            from core.hesaplamalar import ay_is_gunu
            tatiller  = self._tatil_listesi_getir(yil, ay)
            is_gunu   = ay_is_gunu(yil, ay, tatil_listesi=tatiller)
            izin_gun  = self._izin_is_gunu(personel_id, yil, ay, tatiller)
            net_gun   = max(0, is_gunu - izin_gun)
            # HedefTipi oku
            hedef_tipi = "normal"
            if birim_id:
                try:
                    t_rows = self._r.get("NB_PersonelTercih").get_all() or []
                    k = next(
                        (r for r in t_rows
                         if str(r.get("PersonelID","")) == str(personel_id)
                         and str(r.get("BirimID","")) == str(birim_id)
                         and int(r.get("Yil",0)) == yil
                         and int(r.get("Ay",0)) == ay),
                        None)
                    if k:
                        hedef_tipi = str(k.get("HedefTipi","normal")).lower()
                except Exception:
                    pass
            gun_dk = HEDEF_TIPI_DK.get(hedef_tipi, 420)
            return net_gun * gun_dk
        except Exception:
            return 20 * GUNLUK_HEDEF_DAKIKA

    def _izin_is_gunu(self, personel_id: str, yil: int,
                      ay: int, tatiller: list[str]) -> int:
        """Personelin o aydaki onaylı izin iş günü sayısı."""
        from calendar import monthrange
        from datetime import date, timedelta
        try:
            onay_durumlari = {
                "onaylandı", "onaylandi", "onaylı", "approved"
            }
            rows   = self._r.get("Izin_Giris").get_all() or []
            ay_bas = f"{yil:04d}-{ay:02d}-01"
            ay_bit = f"{yil:04d}-{ay:02d}-{monthrange(yil, ay)[1]:02d}"
            sayi   = 0
            for r in rows:
                durum = str(r.get("Durum", "")).strip().lower()
                if (str(r.get("Personelid", "")) != str(personel_id)
                        or durum not in onay_durumlari):
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

# -*- coding: utf-8 -*-
"""
dozimetre_service.py — Dozimetre Ölçüm Servisi

RepositoryRegistry tabanlı servis katmanı.
Tüm DB erişimleri registry üzerinden yapılır; ham sqlite3 bypass yok.

Dozimetre_Olcum tablosu sync=False olduğundan dirty/clean mekanizması
kullanılmaz — sadece yerel SQLite okuma/yazma.
"""

from __future__ import annotations

import uuid
from typing import Optional
from collections import defaultdict

from core.hata_yonetici import SonucYonetici, logger
from database.repository_registry import RepositoryRegistry


class DozimetreService:
    """
    Dozimetre_Olcum tablosu için servis katmanı.

    Kullanım:
        from core.di import get_dozimetre_service
        svc = get_dozimetre_service(db)
        sonuc = svc.get_tum_olcumler()
    """

    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("RepositoryRegistry boş olamaz")
        self._r = registry

    # ──────────────────────────────────────────────────────────
    #  Repository accessor
    # ──────────────────────────────────────────────────────────

    def _repo(self):
        return self._r.get("Dozimetre_Olcum")

    def _personel_repo(self):
        return self._r.get("Personel")

    # ──────────────────────────────────────────────────────────
    #  Sorgular
    # ──────────────────────────────────────────────────────────

    def get_tum_olcumler(self) -> SonucYonetici:
        """
        Tüm ölçüm kayıtlarını döner.
        Personel JOIN için Personel tablosundan adı zenginleştirir.
        """
        try:
            olcumler = self._repo().get_all() or []
            # Personel adlarını cache'le — gereksiz tekrar sorgu engeli
            personel_map: dict[str, dict] = {}
            for p in (self._personel_repo().get_all() or []):
                k = str(p.get("KimlikNo", "")).strip()
                if k:
                    personel_map[k] = p

            for r in olcumler:
                pid = str(r.get("PersonelID", "")).strip()
                p = personel_map.get(pid, {})
                # JOIN alanlarını ekle — yoksa boş bırak
                if "AdSoyad" not in r or not r.get("AdSoyad"):
                    r["AdSoyad"] = p.get("AdSoyad", "")
                r["_GorevYeri"] = p.get("GorevYeri", "")

            return SonucYonetici.tamam(veri=olcumler)
        except Exception as exc:
            return SonucYonetici.hata(exc, "DozimetreService.get_tum_olcumler")

    def get_olcumler_by_personel(self, personel_id: str) -> SonucYonetici:
        """
        Tek personelin ölçümlerini yıl/periyot sıralamasıyla döner.
        """
        try:
            pid = str(personel_id).strip()
            rows = self._repo().get_where({"PersonelID": pid}) or []
            rows.sort(key=lambda r: (
                int(r.get("Yil") or 0),
                int(r.get("Periyot") or 0),
            ))
            return SonucYonetici.tamam(veri=rows)
        except Exception as exc:
            return SonucYonetici.hata(exc, "DozimetreService.get_olcumler_by_personel")

    def get_istatistikler(
        self,
        rows: Optional[list] = None,
        hp10_uyari: float = 2.0,
        hp10_tehlike: float = 5.0,
        anomali_katsayi: float = 3.0,
    ) -> SonucYonetici:
        """
        Ölçüm listesi için istatistik ve anomali hesaplar.

        Args:
            rows: Hesaplanacak kayıt listesi. None ise get_tum_olcumler() kullanılır.
            hp10_uyari: Uyarı eşiği (mSv)
            hp10_tehlike: Tehlike eşiği (mSv)
            anomali_katsayi: Kişisel ortalamanın kaç katı anomali sayılır

        Returns:
            SonucYonetici.veri: dict — toplam, personel, rapor, max_hp10,
                                       uyari_say, tehlike_say, anomali_say
        """
        try:
            if rows is None:
                sonuc = self.get_tum_olcumler()
                if not sonuc.basarili:
                    return sonuc
                rows = sonuc.veri or []

            stats: dict = {
                "toplam": len(rows),
                "personel": len({r.get("PersonelID", "") for r in rows if r.get("PersonelID")}),
                "rapor": len({r.get("RaporNo", "") for r in rows if r.get("RaporNo")}),
                "max_hp10": None,
                "uyari_say": 0,
                "tehlike_say": 0,
                "anomali_say": 0,
            }

            if not rows:
                return SonucYonetici.tamam(veri=stats)

            hp10_vals = [self._float(r.get("Hp10")) for r in rows]
            hp10_vals = [v for v in hp10_vals if v is not None]

            if hp10_vals:
                stats["max_hp10"] = round(max(hp10_vals), 4)
                stats["uyari_say"]   = sum(1 for v in hp10_vals if v >= hp10_uyari)
                stats["tehlike_say"] = sum(1 for v in hp10_vals if v >= hp10_tehlike)

            # Anomali tespiti — kişi ortalamasının anomali_katsayi katı üstü
            kisi_hp10: dict[str, list[float]] = defaultdict(list)
            for r in rows:
                v = self._float(r.get("Hp10"))
                pid = r.get("PersonelID", "")
                if v is not None and v > 0 and pid:
                    kisi_hp10[pid].append(v)

            kisi_ort: dict[str, float] = {
                pid: sum(vals) / len(vals)
                for pid, vals in kisi_hp10.items() if vals
            }

            anomali_say = 0
            for r in rows:
                v   = self._float(r.get("Hp10"))
                pid = r.get("PersonelID", "")
                ort = kisi_ort.get(pid, 0.0)
                if v is not None and ort > 0 and v >= ort * anomali_katsayi:
                    r["_anomali"] = True
                    r["kisi_ort"] = round(ort, 4)
                    r["kat"]      = round(v / ort, 2)
                    anomali_say += 1
                else:
                    r["_anomali"] = False
                    r["kisi_ort"] = round(ort, 4) if ort else None
                    r["kat"]      = None

            stats["anomali_say"] = anomali_say
            return SonucYonetici.tamam(veri=stats)

        except Exception as exc:
            return SonucYonetici.hata(exc, "DozimetreService.get_istatistikler")

    # ──────────────────────────────────────────────────────────
    #  Yazma
    # ──────────────────────────────────────────────────────────

    def olcum_ekle(self, kayit: dict) -> SonucYonetici:
        """
        Bir kayıt satırını Dozimetre_Olcum tablosuna ekler.
        Excel import, PDF import ve tekil eklemeler için kullanılır.

        Excel alan adları → DB sütun adları eşlemesi:
            DerinDoz / Hp10    → Hp10
            YuzeyselDoz / Hp007 → Hp007
            Aciklama / Durum   → Durum
        """
        try:
            kayit_no = kayit.get("KayitNo") or uuid.uuid4().hex[:12].upper()

            hp10  = self._float(kayit.get("DerinDoz",    kayit.get("Hp10",  "")))
            hp007 = self._float(kayit.get("YuzeyselDoz", kayit.get("Hp007", "")))
            durum = kayit.get("Aciklama") or kayit.get("Durum") or "Excel İçe Aktarma"

            veri = {
                "KayitNo":       kayit_no,
                "RaporNo":       kayit.get("RaporNo", ""),
                "Periyot":       self._int(kayit.get("Periyot", "")),
                "PeriyotAdi":    kayit.get("PeriyotAdi", ""),
                "Yil":           self._int(kayit.get("Yil", "")),
                "DozimetriTipi": kayit.get("DozimetriTipi", "Excel"),
                "AdSoyad":       kayit.get("AdSoyad", ""),
                "CalistiBirim":  kayit.get("CalistiBirim", ""),
                "PersonelID":    kayit.get("PersonelID", kayit.get("TCKimlikNo", "")),
                "DozimetreNo":   kayit.get("DozimetreNo", ""),
                "VucutBolgesi":  kayit.get("VucutBolgesi", ""),
                "Hp10":          hp10,
                "Hp007":         hp007,
                "Durum":         durum,
                "OlusturmaTarihi": kayit.get("OlusturmaTarihi", ""),
            }

            self._repo().insert(veri)
            return SonucYonetici.tamam("Ölçüm kaydedildi.")

        except Exception as exc:
            # UNIQUE ihlali kontrolü
            if "UNIQUE" in str(exc).upper() or "unique" in str(exc).lower():
                return SonucYonetici.hata(
                    exc, "DozimetreService.olcum_ekle",
                    kullanici_mesaji="Bu kayıt zaten mevcut (UNIQUE ihlali)"
                )
            return SonucYonetici.hata(exc, "DozimetreService.olcum_ekle")

    # ──────────────────────────────────────────────────────────
    #  Yardımcı dönüşümler
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _float(val) -> float | None:
        if val is None or str(val).strip() == "":
            return None
        try:
            return float(str(val).replace(",", "."))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _int(val) -> int | None:
        if val is None or str(val).strip() == "":
            return None
        try:
            return int(float(str(val)))
        except (ValueError, TypeError):
            return None

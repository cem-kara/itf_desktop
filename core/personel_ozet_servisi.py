# -*- coding: utf-8 -*-
"""Personel merkez ekrani icin ozet veri servisleri."""

from __future__ import annotations

from datetime import date

from core.date_utils import parse_date, to_ui_date
from core.logger import logger


def personel_ozet_getir(db, personel_id: str) -> dict:
    """
    Personel bazli temel ozet metrikleri dondurur.

    Donus:
    {
        "izin_kayit_sayisi": int,
        "aktif_izin_var": bool,
        "aktif_izin_metin": str,
        "yaklasan_saglik": str,
        "fhsz_kayit_sayisi": int,
        "kritikler": list[str],
    }
    """
    ozet = {
        "izin_kayit_sayisi": 0,
        "aktif_izin_var": False,
        "aktif_izin_metin": "Aktif izin yok",
        "yaklasan_saglik": "Kayit bulunamadi",
        "fhsz_kayit_sayisi": 0,
        "kritikler": [],
        "personel": None,
    }

    tc = str(personel_id or "").strip()
    if not db or not tc:
        return ozet

    try:
        from core.di import get_registry

        registry = get_registry(db)
        bugun = date.today()

        # Personel Temel Bilgisi
        p_repo = registry.get("Personel")
        p_kayit = p_repo.get_by_id(tc)
        ozet["personel"] = p_kayit

        # Izin ozetleri
        izinler = [
            r
            for r in registry.get("Izin_Giris").get_all()
            if str(r.get("Personelid", "")).strip() == tc
        ]
        ozet["izin_kayit_sayisi"] = len(izinler)

        aktif_izin = None
        for kayit in izinler:
            baslama = parse_date(kayit.get("BaslamaTarihi"))
            bitis = parse_date(kayit.get("BitisTarihi")) or baslama
            if not baslama or not bitis:
                continue
            if baslama <= bugun <= bitis:
                aktif_izin = kayit
                break

        if aktif_izin:
            ozet["aktif_izin_var"] = True
            ozet["aktif_izin_metin"] = (
                f"{aktif_izin.get('IzinTipi', 'Izin')} - "
                f"{to_ui_date(aktif_izin.get('BitisTarihi'), '-')}"
            )
            ozet["kritikler"].append("Personel su an izinli.")

        # Saglik takip ozeti
        saglik_kayitlari = [
            r
            for r in registry.get("Personel_Saglik_Takip").get_all()
            if str(r.get("Personelid", "")).strip() == tc
        ]
        en_yakin = None
        for kayit in saglik_kayitlari:
            durum = str(kayit.get("Durum", "")).strip()
            if durum == "Pasif":
                continue
            kontrol_tarihi = parse_date(kayit.get("SonrakiKontrolTarihi"))
            if not kontrol_tarihi:
                continue
            if en_yakin is None or kontrol_tarihi < en_yakin:
                en_yakin = kontrol_tarihi

        if en_yakin:
            ozet["yaklasan_saglik"] = to_ui_date(en_yakin)
            kalan = (en_yakin - bugun).days
            if kalan < 0:
                ozet["kritikler"].append("Saglik kontrol tarihi gecmis.")
            elif kalan <= 30:
                ozet["kritikler"].append("Saglik kontrol tarihi yaklasiyor.")

        # FHSZ kayit adedi
        fhsz_kayitlari = [
            r
            for r in registry.get("FHSZ_Puantaj").get_all()
            if str(r.get("Personelid", "")).strip() == tc
        ]
        ozet["fhsz_kayit_sayisi"] = len(fhsz_kayitlari)

    except Exception as exc:
        logger.error(f"Personel ozet servis hatasi: {exc}")

    return ozet

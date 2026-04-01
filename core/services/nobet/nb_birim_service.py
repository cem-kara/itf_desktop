"""
nb_birim_service.py — NB_Birim yönetimi

Sabitler tablosundan bağımsız birim tanımları.
Nöbet modülünün tüm birim referansları bu servis üzerinden gider.

NOT: Personel.GorevYeri alanı FHSZ kapsamında korunur, bu servis
     o alana dokunmaz.
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


class NbBirimService:
    """
    NB_Birim CRUD ve yardımcı metodlar.

    Kullanım:
        svc = NbBirimService(registry)
        birimler = svc.get_birimler()
    """

    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("RepositoryRegistry boş olamaz")
        self._r = registry

    # ──────────────────────────────────────────────────────────
    #  Okuma
    # ──────────────────────────────────────────────────────────

    def get_birimler(self, sadece_aktif: bool = True) -> SonucYonetici:
        """
        Tüm birimleri döner.

        NB_Birim tablosu boşsa Sabitler.Birim fallback devreye girer
        — geçiş döneminde veri kaybı olmaz.

        Dönüş: [{"BirimID", "BirimKodu", "BirimAdi", "Sira", "Aktif"}, ...]
        """
        try:
            self._sync_missing_sabit_birimler()
            rows = self._r.get("NB_Birim").get_all() or []

            if rows:
                if sadece_aktif:
                    rows = [r for r in rows
                            if int(r.get("Aktif", 1)) == 1
                            and not int(r.get("is_deleted", 0))]
                rows = sorted(rows,
                              key=lambda r: (int(r.get("Sira", 99)),
                                             str(r.get("BirimAdi", ""))))
                return SonucYonetici.tamam(veri=[
                    {
                        "BirimID":   r["BirimID"],
                        "BirimKodu": r.get("BirimKodu", ""),
                        "BirimAdi":  r["BirimAdi"],
                        "BirimTipi": r.get("BirimTipi", "radyoloji"),
                        "Sira":      int(r.get("Sira", 99)),
                        "Aktif":     int(r.get("Aktif", 1)),
                        "Aciklama":  r.get("Aciklama", ""),
                    }
                    for r in rows
                ])

            # Fallback: Sabitler tablosu (geçiş dönemi)
            logger.debug("NB_Birim boş — Sabitler fallback")
            return self._get_birimler_sabitler()

        except Exception as e:
            logger.error(f"NbBirimService.get_birimler: {e}")
            return self._get_birimler_sabitler()

    def get_birim(self, birim_id: str) -> SonucYonetici:
        """Tek birim kaydını döner."""
        try:
            self._sync_missing_sabit_birimler()
            rows = self._r.get("NB_Birim").get_all() or []
            kayit = next(
                (r for r in rows if r.get("BirimID") == birim_id), None
            )
            if not kayit:
                return SonucYonetici.hata(
                    ValueError(f"Birim bulunamadı: {birim_id}"))
            return SonucYonetici.tamam(veri=dict(kayit))
        except Exception as e:
            return SonucYonetici.hata(e, "NbBirimService.get_birim")

    def birim_id_bul(self, birim_adi: str) -> SonucYonetici:
        """
        BirimAdi'nden BirimID döner.
        Bulamazsa veri alanında None taşır.
        """
        try:
            self._sync_missing_sabit_birimler()
            rows = self._r.get("NB_Birim").get_all() or []
            kayit = next(
                (r for r in rows
                 if r.get("BirimAdi", "").strip() == birim_adi.strip()
                 and not int(r.get("is_deleted", 0))),
                None
            )
            return SonucYonetici.tamam(veri=kayit["BirimID"] if kayit else None)
        except Exception as e:
            return SonucYonetici.hata(e, "NbBirimService.birim_id_bul")

    # ──────────────────────────────────────────────────────────
    #  Yazma
    # ──────────────────────────────────────────────────────────

    def birim_ekle(self, birim_adi: str, birim_kodu: str = "",
                   birim_tipi: str = "radyoloji",
                   sira: int = 99,
                   aciklama: str = "") -> SonucYonetici:
        """Yeni birim oluşturur."""
        try:
            birim_adi  = birim_adi.strip()
            birim_kodu = birim_kodu.strip() or self._adi_to_kod(birim_adi)

            if not birim_adi:
                return SonucYonetici.hata(
                    ValueError("Birim adı boş olamaz"))

            # Aynı ada sahip aktif birim var mı?
            rows = self._r.get("NB_Birim").get_all() or []
            if any(r.get("BirimAdi", "").strip() == birim_adi
                   and not int(r.get("is_deleted", 0))
                   for r in rows):
                return SonucYonetici.hata(
                    ValueError(f"'{birim_adi}' adında birim zaten mevcut"))

            veri = {
                "BirimID":   _yeni_id(),
                "BirimKodu": birim_kodu,
                "BirimAdi":  birim_adi,
                "BirimTipi": birim_tipi,
                "Aktif":     1,
                "Sira":      sira,
                "Aciklama":  aciklama,
                "is_deleted": 0,
                "created_at": _simdi(),
            }
            self._r.get("NB_Birim").insert(veri)
            logger.info(f"Birim eklendi: {birim_adi} ({birim_kodu})")
            return SonucYonetici.tamam(
                f"'{birim_adi}' birimi eklendi", veri=veri)

        except Exception as e:
            return SonucYonetici.hata(e, "NbBirimService.birim_ekle")

    def birim_guncelle(self, birim_id: str,
                       birim_adi: str = "",
                       birim_kodu: str = "",
                       birim_tipi: str = "",
                       sira: int = -1,
                       aciklama: str = None) -> SonucYonetici:
        """Mevcut birim bilgilerini günceller."""
        try:
            rows  = self._r.get("NB_Birim").get_all() or []
            kayit = next(
                (r for r in rows if r.get("BirimID") == birim_id), None)
            if not kayit:
                return SonucYonetici.hata(
                    ValueError(f"Birim bulunamadı: {birim_id}"))

            guncelleme = {"updated_at": _simdi()}
            if birim_adi:
                guncelleme["BirimAdi"]  = birim_adi.strip()
            if birim_kodu:
                guncelleme["BirimKodu"] = birim_kodu.strip()
            if birim_tipi:
                guncelleme["BirimTipi"] = birim_tipi
            if sira >= 0:
                guncelleme["Sira"]      = sira
            if aciklama is not None:
                guncelleme["Aciklama"]  = aciklama

            self._r.get("NB_Birim").update(birim_id, guncelleme)
            logger.info(f"Birim güncellendi: {birim_id}")
            return SonucYonetici.tamam("Birim güncellendi")

        except Exception as e:
            return SonucYonetici.hata(e, "NbBirimService.birim_guncelle")

    def birim_sil(self, birim_id: str) -> SonucYonetici:
        """
        Soft delete — birim is_deleted=1 yapılır.
        Bağlı vardiya/plan varsa reddeder.
        """
        try:
            # Bağlı aktif vardiya grubu var mı?
            try:
                g_rows = self._r.get("NB_VardiyaGrubu").get_all() or []
                if any(r.get("BirimID") == birim_id
                       and int(r.get("Aktif", 1)) for r in g_rows):
                    return SonucYonetici.hata(
                        ValueError(
                            "Bu birime bağlı aktif vardiya grubu var. "
                            "Önce vardiyaları pasife alın."))
            except Exception:
                pass

            self._r.get("NB_Birim").update(birim_id, {
                "is_deleted": 1,
                "Aktif":      0,
                "updated_at": _simdi(),
            })
            logger.info(f"Birim silindi (soft): {birim_id}")
            return SonucYonetici.tamam("Birim silindi")

        except Exception as e:
            return SonucYonetici.hata(e, "NbBirimService.birim_sil")

    def birim_aktif_toggle(self, birim_id: str) -> SonucYonetici:
        """Birimi aktif/pasif yapar."""
        try:
            rows  = self._r.get("NB_Birim").get_all() or []
            kayit = next(
                (r for r in rows if r.get("BirimID") == birim_id), None)
            if not kayit:
                return SonucYonetici.hata(
                    ValueError(f"Birim bulunamadı: {birim_id}"))
            yeni_aktif = 0 if int(kayit.get("Aktif", 1)) else 1
            self._r.get("NB_Birim").update(birim_id, {
                "Aktif":      yeni_aktif,
                "updated_at": _simdi(),
            })
            durum = "aktif" if yeni_aktif else "pasif"
            return SonucYonetici.tamam(f"Birim {durum} yapıldı")
        except Exception as e:
            return SonucYonetici.hata(e, "NbBirimService.birim_aktif_toggle")

    # ──────────────────────────────────────────────────────────
    #  Yardımcılar
    # ──────────────────────────────────────────────────────────

    def _adi_to_kod(self, adi: str) -> str:
        """Birim adından otomatik kod üretir: 'Acil Radyoloji' → 'ACL_RAD'"""
        karakter_map = str.maketrans(
            "çğıöşüÇĞİÖŞÜ", "cgiosoCGIOSU")
        temiz = adi.translate(karakter_map).upper()
        kelimeler = temiz.split()
        if len(kelimeler) == 1:
            return kelimeler[0][:6]
        return "_".join(k[:3] for k in kelimeler[:3])

    def _sync_missing_sabit_birimler(self) -> None:
        """Sabitler.Birim içinde olup NB_Birim'de olmayan kayıtları ekler."""
        try:
            nb_rows = self._r.get("NB_Birim").get_all() or []
            mevcut_adlar = {
                str(r.get("BirimAdi", "")).strip()
                for r in nb_rows
                if str(r.get("BirimAdi", "")).strip()
            }
            sabit_rows = self._r.get("Sabitler").get_all() or []
            eksikler = []
            for row in sabit_rows:
                if str(row.get("Kod", "")).strip() != "Birim":
                    continue
                birim_adi = str(row.get("MenuEleman", "")).strip()
                if not birim_adi or birim_adi in mevcut_adlar:
                    continue
                eksikler.append(birim_adi)

            if not eksikler:
                return

            sira = max((int(r.get("Sira", 99) or 99) for r in nb_rows), default=98)
            for birim_adi in sorted(set(eksikler)):
                sira += 1
                self._r.get("NB_Birim").insert({
                    "BirimID": _yeni_id(),
                    "BirimKodu": self._adi_to_kod(birim_adi),
                    "BirimAdi": birim_adi,
                    "BirimTipi": "radyoloji",
                    "Aktif": 1,
                    "Sira": sira,
                    "Aciklama": "Sabitler.Birim senkronizasyonu",
                    "is_deleted": 0,
                    "created_at": _simdi(),
                })
                mevcut_adlar.add(birim_adi)
            logger.info(f"NB_Birim senkronize edildi: {len(eksikler)} yeni birim")
        except Exception as e:
            logger.error(f"NbBirimService._sync_missing_sabit_birimler: {e}")

    def _get_birimler_sabitler(self) -> SonucYonetici:
        """Geçiş dönemi fallback — Sabitler tablosundan birim listesi."""
        try:
            rows     = self._r.get("Sabitler").get_all() or []
            birimler = sorted({
                str(r.get("MenuEleman", "")).strip()
                for r in rows
                if str(r.get("Kod", "")).strip() == "Birim"
                and str(r.get("MenuEleman", "")).strip()
            })
            return SonucYonetici.tamam(veri=[
                {
                    "BirimID":   "",
                    "BirimKodu": "",
                    "BirimAdi":  b,
                    "BirimTipi": "radyoloji",
                    "Sira":      99,
                    "Aktif":     1,
                    "Aciklama":  "",
                }
                for b in birimler
            ])
        except Exception as e:
            return SonucYonetici.hata(e, "NbBirimService._get_birimler_sabitler")

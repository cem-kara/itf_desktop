"""
SaglikService — Personel Sağlık Takip işlemleri için service katmanı

Sorumluluklar:
- Sağlık takip kayıtları (muayene, sonuç, doküman)
- Personel + Sağlık verisi birleşik sorgular
- Yeni kayıt ekleme / güncelleme
"""
import os
from typing import Optional
from core.hata_yonetici import SonucYonetici
from core.paths import DATA_DIR

from database.repository_registry import RepositoryRegistry


class SaglikService:
    """Personel sağlık takip işlemleri hizmeti."""

    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("RepositoryRegistry boş olamaz")
        self._r = registry

    # ───────────────────────────────────────────────────────────
    #  Repository Accessors
    # ───────────────────────────────────────────────────────────

    # ───────────────────────────────────────────────────────────
    #  Sağlık Kayıtları
    # ───────────────────────────────────────────────────────────

    def get_saglik_kayitlari(self, personel_id: Optional[str] = None) -> SonucYonetici:
        """
        Sağlık takip kayıtlarını getir.

        Args:
            personel_id: Belirtilirse sadece o personelin kayıtları döner.
        """
        try:
            tum = self._r.get("Personel_Saglik_Takip").get_all() or []
            if personel_id is not None:
                tum = [
                    r for r in tum
                    if str(r.get("Personelid", "")).strip() == str(personel_id).strip()
                ]
            return SonucYonetici.tamam(veri=tum)
        except Exception as e:
            return SonucYonetici.hata(e, "SaglikService.get_saglik_kayitlari")

    def get_saglik_kaydi(self, kayit_no: str) -> SonucYonetici:
        """Tek sağlık kaydını getir."""
        try:
            data = self._r.get("Personel_Saglik_Takip").get_by_pk(kayit_no)
            return SonucYonetici.tamam(veri=data)
        except Exception as e:
            return SonucYonetici.hata(e, f"SaglikService.get_saglik_kaydi({kayit_no})")

    def saglik_kaydi_ekle(self, veri: dict) -> SonucYonetici:
        """Yeni sağlık takip kaydı ekle."""
        try:
            self._r.get("Personel_Saglik_Takip").insert(veri)
            return SonucYonetici.tamam(f"Sağlık kaydı eklendi: {veri.get('KayitNo', '?')}")
        except Exception as e:
            return SonucYonetici.hata(e, "SaglikService.saglik_kaydi_ekle")

    def saglik_kaydi_guncelle(self, kayit_no: str, veri: dict) -> SonucYonetici:
        """Sağlık kaydını güncelle."""
        try:
            self._r.get("Personel_Saglik_Takip").update(kayit_no, veri)
            return SonucYonetici.tamam(f"Sağlık kaydı güncellendi: {kayit_no}")
        except Exception as e:
            return SonucYonetici.hata(e, "SaglikService.saglik_kaydi_guncelle")

    def saglik_kaydi_sil(self, kayit_no: str) -> SonucYonetici:
        """Sağlık kaydını sil."""
        try:
            self._r.get("Personel_Saglik_Takip").delete(kayit_no)
            return SonucYonetici.tamam(f"Sağlık kaydı silindi: {kayit_no}")
        except Exception as e:
            return SonucYonetici.hata(e, "SaglikService.saglik_kaydi_sil")

    # ───────────────────────────────────────────────────────────
    #  Personel + Sağlık Birleşik Sorgu
    # ───────────────────────────────────────────────────────────

    def get_personel_saglik_ozeti(self, personel_id: str) -> SonucYonetici:
        """
        Bir personelin son sağlık durumunu özetle.

        Returns:
            {
                "personel": {...},
                "son_kayit": {...} | None,
                "toplam_kayit": int
            }
        """
        try:
            personel = self._r.get("Personel").get_by_pk(personel_id)
            kayitlar_sonuc = self.get_saglik_kayitlari(personel_id)
            if not kayitlar_sonuc.basarili:
                return kayitlar_sonuc
            kayitlar = kayitlar_sonuc.veri or []

            son_kayit = None
            if kayitlar:
                son_kayit = sorted(
                    kayitlar,
                    key=lambda r: str(r.get("MuayeneTarihi", "")),
                    reverse=True
                )[0]

            data = {
                "personel": personel or {},
                "son_kayit": son_kayit,
                "toplam_kayit": len(kayitlar),
            }
            return SonucYonetici.tamam(veri=data)
        except Exception as e:
            return SonucYonetici.hata(e, f"SaglikService.get_personel_saglik_ozeti({personel_id})")

    def get_personel_listesi(self, aktif_only: bool = True) -> SonucYonetici:
        """
        Sağlık paneli için personel listesi.
        Sağlık takip sayfasında personel seçici olarak kullanılır.
        """
        try:
            rows = self._r.get("Personel").get_all() or []
            if aktif_only:
                rows = [r for r in rows if str(r.get("Durum", "")).strip().lower() != "pasif"]
            return SonucYonetici.tamam(veri=rows)
        except Exception as e:
            return SonucYonetici.hata(e, "SaglikService.get_personel_listesi")

    def get_dokumanlar(self, personel_id: str, belge_turu: Optional[str] = None) -> SonucYonetici:
        """
        Personele ait sağlık belgelerini getir.

        Args:
            personel_id: Personel TC/ID
            belge_turu: Opsiyonel filtre ("RaporDosya" vb.)
        """
        try:
            tum = self._r.get("Dokumanlar").get_all() or []
            result = [
                r for r in tum
                if str(r.get("EntityId", "")).strip() == str(personel_id).strip()
                   and str(r.get("EntityType", "")).strip() == "Personel_Saglik"
            ]
            if belge_turu:
                result = [r for r in result if str(r.get("BelgeTuru", "")) == belge_turu]
            return SonucYonetici.tamam(veri=result)
        except Exception as e:
            return SonucYonetici.hata(e, f"SaglikService.get_dokumanlar({personel_id})")

    def get_personel(self, personel_id: str) -> SonucYonetici:
        try:
            data = self._r.get("Personel").get_by_pk(personel_id)
            return SonucYonetici.tamam(veri=data or {})
        except Exception as e:
            return SonucYonetici.hata(e, f"SaglikService.get_personel({personel_id})")

    def get_ekran_yukleme_verisi(self) -> SonucYonetici:
        try:
            all_personel = self._r.get("Personel").get_all() or []
            personel_rows = [
                p for p in all_personel
                if str(p.get("Durum", "")).strip().lower() != "pasif"
            ]
            takip_rows = self._r.get("Personel_Saglik_Takip").get_all() or []
            docs = self._r.get("Dokumanlar").get_where({"EntityType": "personel"}) or []

            rapor_map: dict[tuple[str, str], dict] = {}
            for doc in docs:
                if str(doc.get("IliskiliBelgeTipi", "")).strip() != "Personel_Saglik_Takip":
                    continue
                entity_id = str(doc.get("EntityId", "")).strip()
                rel_id = str(doc.get("IliskiliBelgeID", "")).strip()
                if entity_id and rel_id:
                    rapor_map[(entity_id, rel_id)] = doc

            for takip in takip_rows:
                personelid = str(takip.get("Personelid", "")).strip()
                kayit_no = str(takip.get("KayitNo", "")).strip()
                doc = rapor_map.get((personelid, kayit_no))
                rapor_path = ""
                if doc:
                    local_path = str(doc.get("LocalPath", "")).strip()
                    drive_path = str(doc.get("DrivePath", "")).strip()
                    belge_adi = str(doc.get("Belge", "")).strip()
                    tc_no = str(doc.get("EntityId", "")).strip() or personelid
                    if local_path and os.path.isfile(local_path):
                        rapor_path = local_path
                    elif drive_path:
                        rapor_path = drive_path
                    else:
                        rapor_path = local_path
                    canonical_path = ""
                    if belge_adi and tc_no:
                        canonical_path = os.path.join(
                            DATA_DIR, "offline_uploads", "personel", tc_no, belge_adi
                        )
                    if canonical_path and os.path.isfile(canonical_path):
                        rapor_path = canonical_path
                    elif local_path and os.path.isdir(local_path) and belge_adi:
                        joined = os.path.join(local_path, belge_adi)
                        if os.path.isfile(joined):
                            rapor_path = joined
                if not rapor_path:
                    rapor_dosya = str(takip.get("RaporDosya", "")).strip()
                    if rapor_dosya:
                        if not os.path.isabs(rapor_dosya) and not rapor_dosya.startswith(("http://", "https://")):
                            basename = os.path.basename(rapor_dosya)
                            canonical = os.path.join(
                                DATA_DIR, "offline_uploads", "personel", personelid, basename
                            )
                            rapor_path = canonical if os.path.isfile(canonical) else rapor_dosya
                        else:
                            rapor_path = rapor_dosya
                takip["_RaporPath"] = rapor_path

            return SonucYonetici.tamam(veri={
                "all_personel": all_personel,
                "personel_rows": personel_rows,
                "takip_rows": takip_rows,
            })
        except Exception as e:
            return SonucYonetici.hata(e, "SaglikService.get_ekran_yukleme_verisi")

    def get_personel_saglik_kayitlari_detay(self, personel_id: str) -> SonucYonetici:
        try:
            all_rows = self._r.get("Personel_Saglik_Takip").get_all() or []
            records = [
                r for r in all_rows
                if str(r.get("Personelid", "")).strip() == str(personel_id).strip()
            ]
            records.sort(key=lambda x: str(x.get("MuayeneTarihi", "")), reverse=True)
            docs = self._r.get("Dokumanlar").get_where({
                "EntityType": "personel",
                "EntityId": str(personel_id).strip(),
            }) or []
            rapor_map: dict[str, dict] = {}
            kayit_nolari = {str(r.get("KayitNo", "")).strip() for r in records}
            for doc in docs:
                if str(doc.get("IliskiliBelgeTipi", "")).strip() != "Personel_Saglik_Takip":
                    continue
                rel = str(doc.get("IliskiliBelgeID", "")).strip()
                if rel in kayit_nolari and rel not in rapor_map:
                    rapor_map[rel] = doc
            for row in records:
                row["_RaporDoc"] = rapor_map.get(str(row.get("KayitNo", "")).strip())
            return SonucYonetici.tamam(veri=records)
        except Exception as e:
            return SonucYonetici.hata(e, "SaglikService.get_personel_saglik_kayitlari_detay")

    def kaydet_rapor_dosya(self, kayit_no: str, rapor_dosya: str) -> SonucYonetici:
        try:
            self._r.get("Personel_Saglik_Takip").update(
                str(kayit_no),
                {"RaporDosya": str(rapor_dosya or "")},
            )
            return SonucYonetici.tamam("Rapor dosya yolu güncellendi.")
        except Exception as e:
            return SonucYonetici.hata(e, "SaglikService.kaydet_rapor_dosya")

    def upsert_saglik_kaydi(self, payload: dict) -> SonucYonetici:
        try:
            kayit_no = str(payload.get("KayitNo", "")).strip()
            personel_id = str(payload.get("Personelid", "")).strip()
            if not kayit_no or not personel_id:
                return SonucYonetici.hata("KayitNo ve Personelid zorunludur.", "SaglikService.upsert_saglik_kaydi")

            personel_repo = self._r.get("Personel")
            takip_repo = self._r.get("Personel_Saglik_Takip")
            mevcut = takip_repo.get_by_id(kayit_no)
            personel = personel_repo.get_by_id(personel_id) or {}

            veri = dict(payload)
            veri.setdefault("AdSoyad", personel.get("AdSoyad", ""))
            veri.setdefault("Birim", personel.get("GorevYeri", ""))

            if mevcut:
                takip_repo.update(kayit_no, veri)
            else:
                takip_repo.insert(veri)

            muayene_db = veri.get("MuayeneTarihi", "")
            if muayene_db:
                from core.date_utils import parse_date as _pd
                mevcut_p = personel_repo.get_by_id(personel_id) or {}
                mevcut_t = _pd(mevcut_p.get("MuayeneTarihi"))
                yeni_t = _pd(muayene_db)
                if yeni_t and (not mevcut_t or yeni_t >= mevcut_t):
                    personel_repo.update(personel_id, {
                        "MuayeneTarihi": muayene_db,
                        "Sonuc": veri.get("Sonuc", ""),
                    })

            return SonucYonetici.tamam(veri={"kayit_no": kayit_no, "guncellendi": bool(mevcut)})
        except Exception as e:
            return SonucYonetici.hata(e, "SaglikService.upsert_saglik_kaydi")

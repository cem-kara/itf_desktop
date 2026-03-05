"""
CihazService — Cihaz, Arıza, Bakım, Kalibrasyon işlemleri için service katmanı

Sorumluluklar:
- Cihaz listesi, CRUD, filtreleme, sayfalama
- Arıza kaydı ve işlem logları
- Periyodik bakım planı ve kayıtları
- Kalibrasyon kayıtları
- Sabitler (combo verileri)
"""
from typing import Optional
from core.logger import logger
from database.repository_registry import RepositoryRegistry


class CihazService:
    """Cihaz modülü işlemleri hizmeti."""

    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("RepositoryRegistry boş olamaz")
        self._r = registry

    # ───────────────────────────────────────────────────────────
    #  Cihaz
    # ───────────────────────────────────────────────────────────

    def get_cihaz_listesi(self) -> list[dict]:
        """Tüm cihaz kayıtlarını döndür."""
        try:
            return self._r.get("Cihazlar").get_all() or []
        except Exception as e:
            logger.error(f"Cihaz listesi yükleme hatası: {e}")
            return []

    def get_cihaz_paginated(self, page: int, page_size: int) -> tuple[list[dict], int]:
        """
        Sayfalama ile cihaz listesi döndür.

        Returns:
            (kayıtlar, toplam_sayı)
        """
        try:
            return self._r.get("Cihazlar").get_paginated(page=page, page_size=page_size)
        except Exception as e:
            logger.error(f"Cihaz sayfalama hatası: {e}")
            return [], 0

    def get_cihaz(self, cihaz_id: str) -> Optional[dict]:
        """Tek cihazı ID'ye göre getir."""
        try:
            rows = self._r.get("Cihazlar").get_by_kod(cihaz_id, "Cihazid")
            return rows[0] if rows else None
        except Exception as e:
            logger.error(f"Cihaz '{cihaz_id}' yükleme hatası: {e}")
            return None

    def cihaz_ekle(self, veri: dict) -> bool:
        """Yeni cihaz ekle."""
        try:
            self._r.get("Cihazlar").insert(veri)
            logger.info(f"Cihaz eklendi: {veri.get('Cihazid', '?')}")
            return True
        except Exception as e:
            logger.error(f"Cihaz ekleme hatası: {e}")
            return False

    def cihaz_guncelle(self, cihaz_id: str, veri: dict) -> bool:
        """Cihaz bilgilerini güncelle."""
        try:
            self._r.get("Cihazlar").update(cihaz_id, veri)
            logger.info(f"Cihaz güncellendi: {cihaz_id}")
            return True
        except Exception as e:
            logger.error(f"Cihaz güncelleme hatası: {e}")
            return False

    def get_next_cihaz_sequence(self) -> int:
        """Sıradaki cihaz sıra numarasını hesapla."""
        try:
            import re
            cihazlar = self._r.get("Cihazlar").get_all() or []
            max_id = 0
            for row in cihazlar:
                cid = str(row.get("Cihazid", "")).strip()
                digits = re.sub(r"\D", "", cid)
                if digits:
                    num = int(digits)
                    if 0 < num < 900000 and num > max_id:
                        max_id = num
            return max_id + 1 if max_id else 1
        except Exception as e:
            logger.debug(f"Cihaz ID hesaplama hatası: {e}")
            return 1

    # ───────────────────────────────────────────────────────────
    #  Arıza
    # ───────────────────────────────────────────────────────────

    def get_ariza_listesi(self, cihaz_id: str) -> list[dict]:
        """Bir cihaza ait arızaları getir."""
        try:
            tum = self._r.get("Cihaz_Ariza").get_all() or []
            return [r for r in tum if str(r.get("Cihazid", "")).strip() == str(cihaz_id).strip()]
        except Exception as e:
            logger.error(f"Arıza listesi hatası ({cihaz_id}): {e}")
            return []

    def get_ariza(self, ariza_id: str) -> Optional[dict]:
        """Tek arıza kaydını getir."""
        try:
            return self._r.get("Cihaz_Ariza").get_by_pk(ariza_id)
        except Exception as e:
            logger.error(f"Arıza '{ariza_id}' yükleme hatası: {e}")
            return None

    def ariza_ekle(self, veri: dict) -> bool:
        """Yeni arıza kaydı ekle."""
        try:
            self._r.get("Cihaz_Ariza").insert(veri)
            logger.info(f"Arıza kaydedildi: {veri.get('Arizaid', '?')}")
            return True
        except Exception as e:
            logger.error(f"Arıza ekleme hatası: {e}")
            return False

    def ariza_guncelle(self, ariza_id: str, veri: dict) -> bool:
        """Arıza kaydını güncelle."""
        try:
            self._r.get("Cihaz_Ariza").update(ariza_id, veri)
            logger.info(f"Arıza güncellendi: {ariza_id}")
            return True
        except Exception as e:
            logger.error(f"Arıza güncelleme hatası: {e}")
            return False

    def get_ariza_islemler(self, ariza_id: str) -> list[dict]:
        """Bir arızaya ait işlem loglarını getir."""
        try:
            tum = self._r.get("Ariza_Islem").get_all() or []
            return [r for r in tum if str(r.get("Arizaid", "")).strip() == str(ariza_id).strip()]
        except Exception as e:
            logger.error(f"Arıza işlemler hatası ({ariza_id}): {e}")
            return []

    def ariza_islem_ekle(self, veri: dict) -> bool:
        """Arıza işlem logu ekle."""
        try:
            self._r.get("Ariza_Islem").insert(veri)
            logger.info(f"Arıza işlem eklendi: {veri.get('Arizaid', '?')}")
            return True
        except Exception as e:
            logger.error(f"Arıza işlem ekleme hatası: {e}")
            return False

    def ariza_islem_guncelle(self, islem_id: str, veri: dict) -> bool:
        """Arıza işlem kaydını güncelle."""
        try:
            self._r.get("Ariza_Islem").update(islem_id, veri)
            return True
        except Exception as e:
            logger.error(f"Arıza işlem güncelleme hatası: {e}")
            return False

    # ───────────────────────────────────────────────────────────
    #  Bakım
    # ───────────────────────────────────────────────────────────

    def get_bakim_listesi(self, cihaz_id: str) -> list[dict]:
        """Bir cihaza ait bakım planlarını getir."""
        try:
            tum = self._r.get("Periyodik_Bakim").get_all() or []
            return [r for r in tum if str(r.get("Cihazid", "")).strip() == str(cihaz_id).strip()]
        except Exception as e:
            logger.error(f"Bakım listesi hatası ({cihaz_id}): {e}")
            return []

    def get_tum_bakimlar(self) -> list[dict]:
        """Tüm bakım kayıtlarını döndür."""
        try:
            return self._r.get("Periyodik_Bakim").get_all() or []
        except Exception as e:
            logger.error(f"Bakım listesi genel hatası: {e}")
            return []

    def bakim_ekle(self, veri: dict) -> bool:
        """Yeni bakım kaydı ekle."""
        try:
            self._r.get("Periyodik_Bakim").insert(veri)
            logger.info(f"Bakım eklendi: {veri.get('Planid', '?')}")
            return True
        except Exception as e:
            logger.error(f"Bakım ekleme hatası: {e}")
            return False

    def bakim_guncelle(self, plan_id: str, veri: dict) -> bool:
        """Bakım kaydını güncelle."""
        try:
            self._r.get("Periyodik_Bakim").update(plan_id, veri)
            logger.info(f"Bakım güncellendi: {plan_id}")
            return True
        except Exception as e:
            logger.error(f"Bakım güncelleme hatası: {e}")
            return False

    # ───────────────────────────────────────────────────────────
    #  Kalibrasyon
    # ───────────────────────────────────────────────────────────

    def get_kalibrasyon_listesi(self, cihaz_id: str) -> list[dict]:
        """Bir cihaza ait kalibrasyon kayıtlarını getir."""
        try:
            tum = self._r.get("Kalibrasyon").get_all() or []
            return [r for r in tum if str(r.get("Cihazid", "")).strip() == str(cihaz_id).strip()]
        except Exception as e:
            logger.error(f"Kalibrasyon listesi hatası ({cihaz_id}): {e}")
            return []

    def kalibrasyon_ekle(self, veri: dict) -> bool:
        """Yeni kalibrasyon kaydı ekle."""
        try:
            self._r.get("Kalibrasyon").insert(veri)
            logger.info(f"Kalibrasyon eklendi: {veri.get('Kalid', '?')}")
            return True
        except Exception as e:
            logger.error(f"Kalibrasyon ekleme hatası: {e}")
            return False

    def kalibrasyon_guncelle(self, kal_id: str, veri: dict) -> bool:
        """Kalibrasyon kaydını güncelle."""
        try:
            self._r.get("Kalibrasyon").update(kal_id, veri)
            logger.info(f"Kalibrasyon güncellendi: {kal_id}")
            return True
        except Exception as e:
            logger.error(f"Kalibrasyon güncelleme hatası: {e}")
            return False

    # ───────────────────────────────────────────────────────────
    #  Sabitler (combo verileri)
    # ───────────────────────────────────────────────────────────

    def get_sabitler(self) -> list[dict]:
        """Tüm sabit kayıtlarını döndür."""
        try:
            return self._r.get("Sabitler").get_all() or []
        except Exception as e:
            logger.error(f"Sabitler yükleme hatası: {e}")
            return []

    def get_sabitler_by_kod(self, kod: str) -> list[str]:
        """
        Belirli bir Kod'a ait MenuEleman değerlerini döndür.
        Örnek: get_sabitler_by_kod("AnaBilimDali")
        """
        try:
            sabitler = self._r.get("Sabitler").get_all() or []
            return sorted({
                str(s.get("MenuEleman", "")).strip()
                for s in sabitler
                if str(s.get("Kod", "")).strip() == kod
                   and str(s.get("MenuEleman", "")).strip()
            })
        except Exception as e:
            logger.error(f"Sabitler [{kod}] yükleme hatası: {e}")
            return []

    def get_sabitler_grouped(self) -> dict[str, list[str]]:
        """
        Tüm sabit kayıtlarını Kod → MenuEleman listesi şeklinde döndür.
        cihaz_ekle.py combo doldurma için kullanılır.
        """
        try:
            sabitler = self._r.get("Sabitler").get_all() or []
            grouped: dict[str, list[str]] = {}
            for row in sabitler:
                kod = str(row.get("Kod", "")).strip()
                eleman = str(row.get("MenuEleman", "")).strip()
                if kod and eleman:
                    grouped.setdefault(kod, []).append(eleman)
            return grouped
        except Exception as e:
            logger.error(f"Sabitler grouped yükleme hatası: {e}")
            return {}

    # ───────────────────────────────────────────────────────────
    #  Repository Accessor Methods (Anti-Pattern 1 Bypass Eliminasyonu)
    # ───────────────────────────────────────────────────────────

    def insert_ariza_islem(self, data: dict) -> None:
        """Arıza işlem kaydı ekle."""
        try:
            self._r.get("Ariza_Islem").insert(data)
        except Exception as e:
            logger.error(f"Arıza işlem kaydı hatası: {e}")
            raise

    def update_cihaz_ariza(self, ariza_id: str, data: dict) -> None:
        """Cihaz arızasını güncelle."""
        try:
            self._r.get("Cihaz_Ariza").update(ariza_id, data)
        except Exception as e:
            logger.error(f"Cihaz arızası güncelleme hatası: {e}")
            raise

    def insert_cihaz_belge(self, data: dict) -> None:
        """Cihaz belgesi kaydet."""
        try:
            self._r.get("Cihaz_Belgeler").insert(data)
        except Exception as e:
            logger.error(f"Cihaz belgesi kaydı hatası: {e}")
            raise

    def get_periyodik_bakim_listesi(self, cihaz_id: str) -> list[dict]:
        """Cihaz için periyodik bakım listesi."""
        try:
            repo = self._r.get("Periyodik_Bakim")
            if hasattr(repo, 'filter'):
                return repo.filter({"Cihazid": cihaz_id}) or []
            return []
        except Exception as e:
            logger.error(f"Periyodik bakım listesi hatası: {e}")
            return []

    def get_cihaz_teknik_listesi(self) -> list[dict]:
        """Cihaz teknik tablosundan tüm kayıtları al."""
        try:
            return self._r.get("Cihaz_Teknik").get_all() or []
        except Exception as e:
            logger.error(f"Cihaz teknik listesi hatası: {e}")
            return []

    def insert_periyodik_bakim(self, data: dict) -> None:
        """Periyodik bakım kaydı ekle."""
        try:
            self._r.get("Periyodik_Bakim").insert(data)
        except Exception as e:
            logger.error(f"Periyodik bakım kaydı hatası: {e}")
            raise

    def update_periyodik_bakim(self, data: dict) -> None:
        """Periyodik bakım kaydını güncelle."""
        try:
            self._r.get("Periyodik_Bakim").update(data)
        except Exception as e:
            logger.error(f"Periyodik bakım güncelleme hatası: {e}")
            raise

    def get_cihaz_teknik(self, cihaz_id: str) -> Optional[dict]:
        """Cihaz teknik kaydını getir."""
        try:
            repo = self._r.get("Cihaz_Teknik")
            if hasattr(repo, 'get_by_cihaz_id'):
                return repo.get_by_cihaz_id(cihaz_id)
            return None
        except Exception as e:
            logger.error(f"Cihaz teknik getirme hatası: {e}")
            return None

    def insert_cihaz_teknik(self, data: dict) -> None:
        """Cihaz teknik kaydı ekle."""
        try:
            self._r.get("Cihaz_Teknik").insert(data)
        except Exception as e:
            logger.error(f"Cihaz teknik kaydı hatası: {e}")
            raise

    def update_cihaz_teknik(self, cihaz_id: str, data: dict) -> None:
        """Cihaz teknik kaydını güncelle."""
        try:
            self._r.get("Cihaz_Teknik").update(cihaz_id, data)
        except Exception as e:
            logger.error(f"Cihaz teknik güncelleme hatası: {e}")
            raise

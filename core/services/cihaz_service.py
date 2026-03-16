"""
CihazService — Cihaz, Arıza, Bakım, Kalibrasyon işlemleri için service katmanı

Sorumluluklar:
- Cihaz listesi, CRUD, filtreleme, sayfalama
- Arıza kaydı ve işlem logları
- Periyodik bakım planı ve kayıtları
- Kalibrasyon kayıtları
- Sabitler (combo verileri)
"""
from typing import Optional, List, Dict
from core.hata_yonetici import SonucYonetici, logger
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

    def get_cihaz_listesi(self) -> SonucYonetici:
        """Tüm cihaz kayıtlarını döndür."""
        try:
            rows = self._r.get("Cihazlar").get_all() or []
            return SonucYonetici.tamam(veri=rows)
        except Exception as e:
            return SonucYonetici.hata(e, "CihazService.get_cihaz_listesi")

    def get_cihaz_paginated(self, page: int, page_size: int) -> SonucYonetici:
        """
        Sayfalama ile cihaz listesi döndür.

        Returns:
            SonucYonetici
        """
        try:
            data = self._r.get("Cihazlar").get_paginated(page=page, page_size=page_size)
            return SonucYonetici.tamam(veri=data)
        except Exception as e:
            return SonucYonetici.hata(e, "CihazService.get_cihaz_paginated")

    def get_cihaz(self, cihaz_id: str) -> SonucYonetici:
        """Tek cihazı ID'ye göre getir."""
        try:
            rows = self._r.get("Cihazlar").get_by_kod(cihaz_id, "Cihazid")
            row = rows[0] if rows else None
            return SonucYonetici.tamam(veri=row)
        except Exception as e:
            return SonucYonetici.hata(e, "CihazService.get_cihaz")

    def cihaz_ekle(self, veri: dict) -> SonucYonetici:
        """Yeni cihaz ekle."""
        try:
            self._r.get("Cihazlar").insert(veri)
            return SonucYonetici.tamam(f"Cihaz eklendi: {veri.get('Cihazid', '?')}")
        except Exception as e:
            return SonucYonetici.hata(e, "CihazService.cihaz_ekle")

    def cihaz_guncelle(self, cihaz_id: str, veri: dict) -> SonucYonetici:
        """Cihaz bilgilerini güncelle."""
        try:
            self._r.get("Cihazlar").update(cihaz_id, veri)
            return SonucYonetici.tamam(f"Cihaz güncellendi: {cihaz_id}")
        except Exception as e:
            return SonucYonetici.hata(e, "CihazService.cihaz_guncelle")

    def get_next_cihaz_sequence(self) -> SonucYonetici:
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
            next_seq = max_id + 1 if max_id else 1
            return SonucYonetici.tamam(veri=next_seq)
        except Exception as e:
            return SonucYonetici.hata(e, "CihazService.get_next_cihaz_sequence")

    # ───────────────────────────────────────────────────────────
    #  Arıza
    # ───────────────────────────────────────────────────────────

    def get_ariza_listesi(self, cihaz_id: str) -> SonucYonetici:
        """Bir cihaza ait arızaları getir."""
        try:
            tum = self._r.get("Cihaz_Ariza").get_all() or []
            data = [r for r in tum if str(r.get("Cihazid", "")).strip() == str(cihaz_id).strip()]
            return SonucYonetici.tamam(veri=data)
        except Exception as e:
            return SonucYonetici.hata(e, f"CihazService.get_ariza_listesi({cihaz_id})")

    def get_ariza(self, ariza_id: str) -> SonucYonetici:
        """Tek arıza kaydını getir."""
        try:
            data = self._r.get("Cihaz_Ariza").get_by_pk(ariza_id)
            return SonucYonetici.tamam(veri=data)
        except Exception as e:
            return SonucYonetici.hata(e, f"CihazService.get_ariza({ariza_id})")

    def ariza_ekle(self, veri: dict) -> SonucYonetici:
        """Yeni arıza kaydı ekle."""
        try:
            self._r.get("Cihaz_Ariza").insert(veri)
            return SonucYonetici.tamam(f"Arıza kaydedildi: {veri.get('Arizaid', '?')}")
        except Exception as e:
            return SonucYonetici.hata(e, "CihazService.ariza_ekle")

    def ariza_guncelle(self, ariza_id: str, veri: dict) -> SonucYonetici:
        """Arıza kaydını güncelle."""
        try:
            self._r.get("Cihaz_Ariza").update(ariza_id, veri)
            return SonucYonetici.tamam(f"Arıza güncellendi: {ariza_id}")
        except Exception as e:
            return SonucYonetici.hata(e, f"CihazService.ariza_guncelle({ariza_id})")

    def get_ariza_islemler(self, ariza_id: str) -> SonucYonetici:
        """Bir arızaya ait işlem loglarını getir."""
        try:
            tum = self._r.get("Ariza_Islem").get_all() or []
            data = [r for r in tum if str(r.get("Arizaid", "")).strip() == str(ariza_id).strip()]
            return SonucYonetici.tamam(veri=data)
        except Exception as e:
            return SonucYonetici.hata(e, f"CihazService.get_ariza_islemler({ariza_id})")

    def ariza_islem_ekle(self, veri: dict) -> SonucYonetici:
        """Arıza işlem logu ekle."""
        try:
            self._r.get("Ariza_Islem").insert(veri)
            return SonucYonetici.tamam(f"Arıza işlem eklendi: {veri.get('Arizaid', '?')}")
        except Exception as e:
            return SonucYonetici.hata(e, "CihazService.ariza_islem_ekle")

    def ariza_islem_guncelle(self, islem_id: str, veri: dict) -> SonucYonetici:
        """Arıza işlem kaydını güncelle."""
        try:
            self._r.get("Ariza_Islem").update(islem_id, veri)
            return SonucYonetici.tamam(f"Arıza işlemi güncellendi: {islem_id}")
        except Exception as e:
            return SonucYonetici.hata(e, f"CihazService.ariza_islem_guncelle({islem_id})")

    # ───────────────────────────────────────────────────────────
    #  Bakım
    # ───────────────────────────────────────────────────────────

    def get_bakim_listesi(self, cihaz_id: str) -> SonucYonetici:
        """Bir cihaza ait bakım planlarını getir."""
        try:
            tum = self._r.get("Periyodik_Bakim").get_all() or []
            data = [r for r in tum if str(r.get("Cihazid", "")).strip() == str(cihaz_id).strip()]
            return SonucYonetici.tamam(veri=data)
        except Exception as e:
            return SonucYonetici.hata(e, f"CihazService.get_bakim_listesi({cihaz_id})")

    def get_tum_bakimlar(self) -> SonucYonetici:
        """Tüm bakım kayıtlarını döndür."""
        try:
            data = self._r.get("Periyodik_Bakim").get_all() or []
            return SonucYonetici.tamam(veri=data)
        except Exception as e:
            return SonucYonetici.hata(e, "CihazService.get_tum_bakimlar")

    def bakim_ekle(self, veri: dict) -> SonucYonetici:
        """Yeni bakım kaydı ekle."""
        try:
            self._r.get("Periyodik_Bakim").insert(veri)
            return SonucYonetici.tamam(f"Bakım eklendi: {veri.get('Planid', '?')}")
        except Exception as e:
            return SonucYonetici.hata(e, "CihazService.bakim_ekle")

    def bakim_guncelle(self, plan_id: str, veri: dict) -> SonucYonetici:
        """Bakım kaydını güncelle."""
        try:
            self._r.get("Periyodik_Bakim").update(plan_id, veri)
            return SonucYonetici.tamam(f"Bakım güncellendi: {plan_id}")
        except Exception as e:
            return SonucYonetici.hata(e, f"CihazService.bakim_guncelle({plan_id})")

    # ───────────────────────────────────────────────────────────
    #  Kalibrasyon
    # ───────────────────────────────────────────────────────────

    def get_kalibrasyon_listesi(self, cihaz_id: str) -> SonucYonetici:
        """Bir cihaza ait kalibrasyon kayıtlarını getir."""
        try:
            tum = self._r.get("Kalibrasyon").get_all() or []
            data = [r for r in tum if str(r.get("Cihazid", "")).strip() == str(cihaz_id).strip()]
            return SonucYonetici.tamam(veri=data)
        except Exception as e:
            return SonucYonetici.hata(e, f"CihazService.get_kalibrasyon_listesi({cihaz_id})")

    def kalibrasyon_ekle(self, veri: dict) -> SonucYonetici:
        """Yeni kalibrasyon kaydı ekle."""
        try:
            self._r.get("Kalibrasyon").insert(veri)
            return SonucYonetici.tamam(f"Kalibrasyon eklendi: {veri.get('Kalid', '?')}")
        except Exception as e:
            return SonucYonetici.hata(e, "CihazService.kalibrasyon_ekle")

    def kalibrasyon_guncelle(self, kal_id: str, veri: dict) -> SonucYonetici:
        """Kalibrasyon kaydını güncelle."""
        try:
            self._r.get("Kalibrasyon").update(kal_id, veri)
            return SonucYonetici.tamam(f"Kalibrasyon güncellendi: {kal_id}")
        except Exception as e:
            return SonucYonetici.hata(e, f"CihazService.kalibrasyon_guncelle({kal_id})")

    # ───────────────────────────────────────────────────────────
    #  Sabitler (combo verileri)
    # ───────────────────────────────────────────────────────────

    def get_sabitler(self) -> SonucYonetici:
        """Tüm sabit kayıtlarını döndür."""
        try:
            data = self._r.get("Sabitler").get_all() or []
            return SonucYonetici.tamam(veri=data)
        except Exception as e:
            return SonucYonetici.hata(e, "CihazService.get_sabitler")

    def get_sabitler_by_kod(self, kod: str) -> SonucYonetici:
        """
        Belirli bir Kod'a ait MenuEleman değerlerini döndür.
        Örnek: get_sabitler_by_kod("AnaBilimDali")
        """
        try:
            sabitler = self._r.get("Sabitler").get_all() or []
            data = sorted({
                str(s.get("MenuEleman", "")).strip()
                for s in sabitler
                if str(s.get("Kod", "")).strip() == kod
                   and str(s.get("MenuEleman", "")).strip()
            })
            return SonucYonetici.tamam(veri=data)
        except Exception as e:
            return SonucYonetici.hata(e, f"CihazService.get_sabitler_by_kod({kod})")

    def get_sabitler_grouped(self) -> SonucYonetici:
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
            return SonucYonetici.tamam(veri=grouped)
        except Exception as e:
            return SonucYonetici.hata(e, "CihazService.get_sabitler_grouped")

    # ───────────────────────────────────────────────────────────
    #  Repository Accessor Methods (Anti-Pattern 1 Bypass Eliminasyonu)
    # ───────────────────────────────────────────────────────────

    def insert_ariza_islem(self, data: dict) -> SonucYonetici:
        """Arıza işlem kaydı ekle."""
        try:
            self._r.get("Ariza_Islem").insert(data)
            return SonucYonetici.tamam("Arıza işlem kaydı eklendi.")
        except Exception as e:
            return SonucYonetici.hata(e, "CihazService.insert_ariza_islem")

    def update_cihaz_ariza(self, ariza_id: str, data: dict) -> SonucYonetici:
        """Cihaz arızasını güncelle."""
        try:
            self._r.get("Cihaz_Ariza").update(ariza_id, data)
            return SonucYonetici.tamam(f"Cihaz arızası güncellendi: {ariza_id}")
        except Exception as e:
            return SonucYonetici.hata(e, f"CihazService.update_cihaz_ariza({ariza_id})")

    def insert_cihaz_belge(self, data: dict) -> SonucYonetici:
        """Cihaz belgesi kaydet."""
        try:
            self._r.get("Cihaz_Belgeler").insert(data)
            return SonucYonetici.tamam("Cihaz belgesi kaydedildi.")
        except Exception as e:
            return SonucYonetici.hata(e, "CihazService.insert_cihaz_belge")

    def get_periyodik_bakim_listesi(self, cihaz_id: str) -> SonucYonetici:
        """Cihaz için periyodik bakım listesi."""
        try:
            repo = self._r.get("Periyodik_Bakim")
            data = []
            if hasattr(repo, 'filter'):
                data = repo.filter({"Cihazid": cihaz_id}) or []
            return SonucYonetici.tamam(veri=data)
        except Exception as e:
            return SonucYonetici.hata(e, f"CihazService.get_periyodik_bakim_listesi({cihaz_id})")

    def get_cihaz_teknik_listesi(self) -> SonucYonetici:
        """Cihaz teknik tablosundan tüm kayıtları al."""
        try:
            data = self._r.get("Cihaz_Teknik").get_all() or []
            return SonucYonetici.tamam(veri=data)
        except Exception as e:
            return SonucYonetici.hata(e, "CihazService.get_cihaz_teknik_listesi")

    def insert_periyodik_bakim(self, data: dict) -> SonucYonetici:
        """Periyodik bakım kaydı ekle."""
        try:
            self._r.get("Periyodik_Bakim").insert(data)
            return SonucYonetici.tamam("Periyodik bakım kaydı eklendi.")
        except Exception as e:
            return SonucYonetici.hata(e, "CihazService.insert_periyodik_bakim")

    def update_periyodik_bakim(self, data: dict) -> SonucYonetici:
        """Periyodik bakım kaydını güncelle."""
        try:
            pk = data.get("Planid")
            if not pk:
                return SonucYonetici.hata(Exception("Planid eksik"), "CihazService.update_periyodik_bakim")
            self._r.get("Periyodik_Bakim").update(pk, data)
            return SonucYonetici.tamam("Periyodik bakım güncellendi.")
        except Exception as e:
            return SonucYonetici.hata(e, "CihazService.update_periyodik_bakim")

    def get_cihaz_teknik(self, cihaz_id: str) -> SonucYonetici:
        """Cihaz teknik kaydını getir."""
        try:
            repo = self._r.get("Cihaz_Teknik")
            data = None
            if hasattr(repo, 'get_by_cihaz_id'):
                data = repo.get_by_cihaz_id(cihaz_id)
            return SonucYonetici.tamam(veri=data)
        except Exception as e:
            return SonucYonetici.hata(e, f"CihazService.get_cihaz_teknik({cihaz_id})")

    def insert_cihaz_teknik(self, data: dict) -> SonucYonetici:
        """Cihaz teknik kaydı ekle."""
        try:
            self._r.get("Cihaz_Teknik").insert(data)
            return SonucYonetici.tamam("Cihaz teknik kaydı eklendi.")
        except Exception as e:
            return SonucYonetici.hata(e, "CihazService.insert_cihaz_teknik")

    def update_cihaz_teknik(self, cihaz_id: str, data: dict) -> SonucYonetici:
        """Cihaz teknik kaydını güncelle."""
        try:
            self._r.get("Cihaz_Teknik").update(cihaz_id, data)
            return SonucYonetici.tamam(f"Cihaz teknik kaydı güncellendi: {cihaz_id}")
        except Exception as e:
            return SonucYonetici.hata(e, f"CihazService.update_cihaz_teknik({cihaz_id})")

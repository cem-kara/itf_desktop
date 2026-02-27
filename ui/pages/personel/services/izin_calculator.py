"""
İzin Hesaplamaları - Bakiye, Bitiş Tarihi, Pasif Durumu
=======================================================

Sorumluluklar:
- Bitiş tarihi hesaplama (tatil + cumartesi günü atla)
- Pasif durumu belirleme (30+ gün veya aylıksız izin)
- Bakiye kontrolü ve düşümü (Yıllık/Şua/Rapor-Mazeret)
"""

from datetime import date, datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from core.log_manager import get_logger

logger = get_logger(__name__)


class IzinCalculator:
    """İzin müdürü - Bakiye, tarih, durum hesaplamaları"""

    # Pasif dur statüsü için minimum gün
    PASIF_MIN_GUN = 30

    # Aylıksız izin anahtar sözcükleri
    UCUNSUZ_KEYWORDS = ["aylıksız", "ücretsiz", "ücret siz", "ucretsiz"]

    def __init__(self, tatil_listesi: Optional[list] = None):
        """
        Args:
            tatil_listesi: ISO format tarihlerin listesi [202412-25, 2024-01-01, ...]
        """
        self.tatil_listesi = set(tatil_listesi or [])

    def add_tatil(self, tarih_iso: str) -> None:
        """Tatil listesine tarih ekle."""
        if tarih_iso:
            self.tatil_listesi.add(tarih_iso)

    def add_tatiller(self, tarifler: list) -> None:
        """Tatil listesine birden fazla tarih ekle."""
        for t in tarifler:
            if t:
                self.tatil_listesi.add(t)

    def calculate_bitis_tarihi(
        self, baslama: date, gun: int
    ) -> Optional[date]:
        """
        Bitiş tarihi hesapla (tatil + hafta sonu atla).

        Args:
            baslama: İzinin başladığı tarih
            gun: İzin süresi (gün cinsinden, hafta sonu/tatil HARİÇ)

        Returns:
            İşe dönüş tarihi (bitiş tarihi sonrası ilk çalışma günü)

        Örnek:
            Cuma 29'dan başlayan 1 günlük izin → Pazartesi 2'ye dön
        """
        if not baslama or gun <= 0:
            return None

        kalan = gun
        current = baslama
        baslama_iso = baslama.isoformat()

        # Başlama günü hariç tutmalı mıyız?
        # Genelde izin başlama günü de sayılır, o yüzden 1 gün öncesinden başla
        # Ama hesaplama tarafında genelde başlama günü öncesi kontrol edilir
        # Burada increment ile kontrol ediyoruz

        while kalan > 0:
            current += timedelta(days=1)
            # Hafta sonu veya tatil ise atla
            if current.isoformat() == baslama_iso:
                # İzin başlama günü zaten başlamış, sayma
                continue
            if current.weekday() in (5, 6):  # Cumartesi (5), Pazar (6)
                continue
            if current.isoformat() in self.tatil_listesi:
                continue
            kalan -= 1

        return current

    def should_set_pasif(self, izin_tipi: str, gun: int) -> bool:
        """
        Personel pasif yapılmalı mı?

        Pasif durumu gerekçeleri:
        - 30+ gün sürekli izin
        - Aylıksız/ücretsiz izin

        Args:
            izin_tipi: "Yıllık İzin", "Aylıksız İzin", vb.
            gun: İzin süresi

        Returns:
            True → personel Pasif yapılmalı
        """
        # Gün kontrolü
        if gun > self.PASIF_MIN_GUN:
            logger.debug(
                f"Pasif gerekçesi: {gun} gün > {self.PASIF_MIN_GUN} minimum"
            )
            return True

        # Aylıksız/ücretsiz kontrol
        tip_lower = str(izin_tipi or "").strip().lower()
        for keyword in self.UCUNSUZ_KEYWORDS:
            if keyword in tip_lower:
                logger.debug(f"Pasif gerekçesi: '{keyword}' içeren izin tipi = {izin_tipi}")
                return True

        return False

    def get_balance_deduction(self, izin_tipi: str) -> Tuple[str, bool]:
        """
        Bakiyeden düşülecek alan belirleme.

        Args:
            izin_tipi: "Yıllık İzin", "Şua İzni", "Mazeret İzni", vb.

        Returns:
            (field_name, should_deduct)
            - field_name: "YillikKalan", "SuaKalan", "RaporMazeretTop"
            - should_deduct: Bakiyeden düşülmesi gerekli mi?

        Örnek:
            "Yıllık İzin" → ("YillikKalan", True)
            "Doğum İzni" → ("", False)
        """
        tip_norm = str(izin_tipi or "").strip().lower()

        if "yıllık" in tip_norm or "annual" in tip_norm:
            return "YillikKalan", True
        elif "şua" in tip_norm or "sua" in tip_norm:
            return "SuaKalan", True
        elif "rapor" in tip_norm or "mazeret" in tip_norm:
            return "RaporMazeretTop", False  # Bu durumda artırma yapılır
        else:
            # Doğum, Babalık, Ölüm, vb. → bakiye kontrolü yok
            return "", False

    def validate_balance(
        self,
        izin_tipi: str,
        gun: int,
        bakiye_dict: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Bakiye yeterliliği kontrolü.

        Args:
            izin_tipi: İzin tipi adı
            gun: İstenen gün sayısı
            bakiye_dict: Izin_Bilgi tablosundan gelen dict
                        {"YillikKalan": 5, "SuaKalan": 10, ...}

        Returns:
            (is_valid, warning_msg)
            - is_valid: Bakiye yeterli mi?
            - warning_msg: Uyarı mesajı (yetersiz ise)

        Örnek:
            validate_balance("Yıllık İzin", 15, {"YillikKalan": 10}) 
            → (False, "Bakiye: 10 gün, İstenmiş: 15 gün, Eksik: 5 gün")
        """
        field_name, should_deduct = self.get_balance_deduction(izin_tipi)

        # Bakiye kontrolü yapılmayan izin tipleri
        if not should_deduct or not field_name:
            return True, None

        kalan = float(bakiye_dict.get(field_name, 0))
        if gun <= kalan:
            return True, None

        eksik = gun - kalan
        msg = (
            f"Bakiye yetersiz:\n"
            f"• Mevcut Bakiye: {kalan} gün\n"
            f"• İstenen: {gun} gün\n"
            f"• Eksik: {eksik} gün"
        )
        return False, msg

    def check_tarih_cakismasi(
        self,
        yeni_bas: date,
        yeni_bit: date,
        mevcut_kayitlar: list
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Yeni izin tarihleri mevcut izinlerle çakışıyor mu?

        Çakışma formülü: (yeni_bas <= vt_bit) AND (yeni_bit >= vt_bas)

        Args:
            yeni_bas: Yeni izinin başlama tarihi
            yeni_bit: Yeni izinin bitiş tarihi
            mevcut_kayitlar: DB'deki İzin_Giris tablosundan gelen kayıtlar

        Returns:
            (has_conflict, conflict_info)
            - has_conflict: Çakışma var mı?
            - conflict_info: Çakışan kaydın detayları (varsa)
        """
        for kayit in mevcut_kayitlar:
            # İptal edilen kayıtları atla
            if str(kayit.get("Durum", "")).strip() == "İptal":
                continue

            # İzin tarihlerini parse et
            bas_str = kayit.get("BaslamaTarihi")
            bit_str = kayit.get("BitisTarihi")

            if not bas_str or not bit_str:
                continue

            try:
                vt_bas = self._parse_date(bas_str)
                vt_bit = self._parse_date(bit_str)
            except Exception:
                continue

            if not vt_bas or not vt_bit:
                continue

            # Çakışma kontrolü
            if (yeni_bas <= vt_bit) and (yeni_bit >= vt_bas):
                return True, {
                    "BaslamaTarihi": vt_bas.isoformat(),
                    "BitisTarihi": vt_bit.isoformat(),
                    "IzinTipi": kayit.get("IzinTipi", ""),
                    "Durum": kayit.get("Durum", ""),
                    "AdSoyad": kayit.get("AdSoyad", ""),
                }

        return False, None

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[date]:
        """Tarih string'ini parse et (çoklu format desteği)."""
        if not date_str:
            return None

        date_str = str(date_str).strip()

        # ISO format: 2024-12-25
        if len(date_str) == 10 and date_str[4] == "-":
            try:
                return datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        # TR format: 25.12.2024
        if len(date_str) == 10 and date_str[2] == ".":
            try:
                return datetime.strptime(date_str, "%d.%m.%Y").date()
            except ValueError:
                pass

        # Diğer format denemeleri
        for fmt in ["%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"]:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        return None

    def get_izin_duration(
        self, baslama: date, bitis: date, exclude_weekends: bool = True
    ) -> int:
        """
        İzin süresi hesapla (iş günü cinsinden).

        Args:
            baslama: Başlama tarihi
            bitis: Bitiş tarihi
            exclude_weekends: Hafta sonu hariç tutulacak mı?

        Returns:
            İş günü sayısı
        """
        if baslama > bitis:
            return 0

        gun_sayisi = 0
        current = baslama

        while current <= bitis:
            if exclude_weekends:
                if current.weekday() not in (5, 6):  # Tatil kontrolü yok, sadece W.S.
                    if current.isoformat() not in self.tatil_listesi:
                        gun_sayisi += 1
            else:
                if current.isoformat() not in self.tatil_listesi:
                    gun_sayisi += 1
            current += timedelta(days=1)

        return gun_sayisi

"""
DashboardService — Dashboard istatistikleri için service katmanı

Sorumluluklar:
- Cihaz / arıza / bakım / kalibrasyon sayıları
- RKE ve sağlık takip özetleri
- Aylık izinli personel istatistikleri
- Tüm sorgular tek noktadan, UI'a hazır dict döndürür
"""
import calendar, math
from datetime import datetime, timedelta
from typing import Optional
from core.hata_yonetici import SonucYonetici
from core.logger import logger
from database.repository_registry import RepositoryRegistry


def _parse_date(val: Optional[str]):
    """Esnek tarih parse — None veya boş string → None."""
    if not val:
        return None
    val = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            pass
    return None


class DashboardService:
    """Dashboard özet verilerini toplayan service."""

    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("RepositoryRegistry boş olamaz")
        self._r = registry

    # ───────────────────────────────────────────────────────────
    #  Ana Metod
    # ───────────────────────────────────────────────────────────

    def get_dashboard_data(self) -> SonucYonetici:
        """
        Tüm dashboard istatistiklerini toplu olarak döndür.

        Returns:
            {
                "yaklasan_ndk": int,
                "aylik_bakim": int,
                "aylik_kalibrasyon": int,
                "yeni_arizalar": int,
                "aktif_personel": int,
                "yaklasan_rke": int,
                "yaklasan_saglik": int,
                "gecmis_saglik": int,
                "acik_arizalar": int,
                "gecmis_kalibrasyon": int,
                "aylik_izinli_personel_toplam": int,
                "aylik_izinli_yillik": int,
                "aylik_izinli_sua": int,
                "aylik_izinli_rapor": int,
                "aylik_izinli_diger": int,
            }
        """
        today = datetime.now()
        today_str = today.strftime("%Y-%m-%d")
        data: dict = {}
        try:
            data["yaklasan_ndk"] = self._yaklasan_ndk(today, today_str).data or 0
            data["aylik_bakim"] = self._aylik_bakim(today).data or 0
            data["aylik_kalibrasyon"] = self._aylik_kalibrasyon(today).data or 0
            data["yeni_arizalar"] = self._yeni_arizalar(today, today_str).data or 0
            data["aktif_personel"] = self._aktif_personel().data or 0
            data["yaklasan_rke"] = self._yaklasan_rke(today, today_str).data or 0
            data["yaklasan_saglik"] = self._yaklasan_saglik(today, today_str).data or 0
            data["gecmis_saglik"] = self._gecmis_saglik(today_str).data or 0
            data["acik_arizalar"] = self._acik_arizalar().data or 0
            data["gecmis_kalibrasyon"] = self._gecmis_kalibrasyon(today_str).data or 0
            izin_stats_sonuc = self._aylik_izin_stats(today)
            if izin_stats_sonuc.basarili and izin_stats_sonuc.data is not None:
                data.update(izin_stats_sonuc.data) # Ensure it's a dict, not None
            else:
                logger.warning(f"Aylık izin istatistikleri alınamadı: {izin_stats_sonuc.mesaj}")
            return SonucYonetici.tamam(veri=data)
        except Exception as e:
            return SonucYonetici.hata(e, "DashboardService.get_dashboard_data")

    # ───────────────────────────────────────────────────────────
    #  Bireysel istatistikler
    # ───────────────────────────────────────────────────────────

    def _yaklasan_ndk(self, today: datetime, today_str: str) -> SonucYonetici:
        """6 ay içinde NDK lisansı sona erecek cihazlar."""
        try:
            six_months = (today + timedelta(days=180)).strftime("%Y-%m-%d")
            count = self._count_where(
                "Cihazlar",
                lambda r: today_str <= str(r.get("BitisTarihi", "")) <= six_months
            ).data or 0
            return SonucYonetici.tamam(veri=count)
        except Exception as e:
            return SonucYonetici.hata(e, "DashboardService._yaklasan_ndk")

    def _aylik_bakim(self, today: datetime) -> SonucYonetici:
        """Bu ay planlı bakım sayısı."""
        try:
            m_start, m_end = self._month_range(today)
            count = self._count_where(
                "Periyodik_Bakim",
                lambda r: (
                    m_start <= str(r.get("PlanlananTarih", "")) <= m_end
                    and str(r.get("Durum", "")).strip() == "Planlandı"
                )
            ).data or 0
            return SonucYonetici.tamam(veri=count)
        except Exception as e:
            return SonucYonetici.hata(e, "DashboardService._aylik_bakim")

    def _aylik_kalibrasyon(self, today: datetime) -> SonucYonetici:
        """Bu ay tamamlanan kalibrasyon sayısı."""
        try:
            m_start, m_end = self._month_range(today)
            count = self._count_where(
                "Kalibrasyon",
                lambda r: (
                    m_start <= str(r.get("BitisTarihi", "")) <= m_end
                    and str(r.get("Durum", "")).strip() == "Tamamlandı"
                )
            ).data or 0
            return SonucYonetici.tamam(veri=count)
        except Exception as e:
            return SonucYonetici.hata(e, "DashboardService._aylik_kalibrasyon")

    def _yeni_arizalar(self, today: datetime, today_str: str) -> SonucYonetici:
        """Son 7 günde açılan ve hâlâ açık arızalar."""
        try:
            one_week_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")
            count = self._count_where(
                "Cihaz_Ariza",
                lambda r: (
                    str(r.get("BaslangicTarihi", "")) >= one_week_ago
                    and str(r.get("Durum", "")).strip() != "Kapatıldı"
                )
            ).data or 0
            return SonucYonetici.tamam(veri=count)
        except Exception as e:
            return SonucYonetici.hata(e, "DashboardService._yeni_arizalar")

    def _aktif_personel(self) -> SonucYonetici:
        """Aktif personel sayısı."""
        try:
            count = self._count_where(
                "Personel",
                lambda r: str(r.get("Durum", "")).strip() == "Aktif"
            ).data or 0
            return SonucYonetici.tamam(veri=count)
        except Exception as e:
            return SonucYonetici.hata(e, "DashboardService._aktif_personel")

    def _yaklasan_rke(self, today: datetime, today_str: str) -> SonucYonetici:
        """1 ay içinde kontrol tarihi gelecek RKE ekipmanlar."""
        try:
            one_month = (today + timedelta(days=30)).strftime("%Y-%m-%d")
            count = self._count_where(
                "RKE_List",
                lambda r: (
                    today_str <= str(r.get("KontrolTarihi", "")) <= one_month
                    and str(r.get("Durum", "")).strip() == "Planlandı"
                )
            ).data or 0
            return SonucYonetici.tamam(veri=count)
        except Exception as e:
            return SonucYonetici.hata(e, "DashboardService._yaklasan_rke")

    def _yaklasan_saglik(self, today: datetime, today_str: str) -> SonucYonetici:
        """3 ay içinde sağlık kontrolü gelecek personel."""
        try:
            three_months = (today + timedelta(days=90)).strftime("%Y-%m-%d")
            count = self._count_where(
                "Personel_Saglik_Takip",
                lambda r: (
                    today_str <= str(r.get("SonrakiKontrolTarihi", "")) <= three_months
                    and str(r.get("Durum", "")).strip() != "Pasif"
                )
            ).data or 0
            return SonucYonetici.tamam(veri=count)
        except Exception as e:
            return SonucYonetici.hata(e, "DashboardService._yaklasan_saglik")

    def _gecmis_saglik(self, today_str: str) -> SonucYonetici:
        """Sağlık kontrol tarihi geçmiş personel."""
        try:
            count = self._count_where(
                "Personel_Saglik_Takip",
                lambda r: (
                    str(r.get("SonrakiKontrolTarihi", "")).strip() != ""
                    and str(r.get("SonrakiKontrolTarihi", "")) < today_str
                    and str(r.get("Durum", "")).strip() != "Pasif"
                )
            ).data or 0
            return SonucYonetici.tamam(veri=count)
        except Exception as e:
            return SonucYonetici.hata(e, "DashboardService._gecmis_saglik")

    def _acik_arizalar(self) -> SonucYonetici:
        """Açık arıza sayısı."""
        try:
            count = self._count_where(
                "Cihaz_Ariza",
                lambda r: str(r.get("Durum", "")).strip() == "Açık"
            ).data or 0
            return SonucYonetici.tamam(veri=count)
        except Exception as e:
            return SonucYonetici.hata(e, "DashboardService._acik_arizalar")

    def _gecmis_kalibrasyon(self, today_str: str) -> SonucYonetici:
        """Geçerlilik tarihi geçmiş kalibrasyon sayısı."""
        try:
            count = self._count_where(
                "Kalibrasyon",
                lambda r: (
                    str(r.get("BitisTarihi", "")).strip() != ""
                    and str(r.get("BitisTarihi", "")) < today_str
                    and str(r.get("Durum", "")).strip() == "Tamamlandı"
                )
            ).data or 0
            return SonucYonetici.tamam(veri=count)
        except Exception as e:
            return SonucYonetici.hata(e, "DashboardService._gecmis_kalibrasyon")

    def _aylik_izin_stats(self, today: datetime) -> SonucYonetici:
        """Bu ay izinli personel sayısı (tip bazlı)."""
        stats = {
            "aylik_izinli_personel_toplam": 0,
            "aylik_izinli_yillik": 0,
            "aylik_izinli_sua": 0,
            "aylik_izinli_rapor": 0,
            "aylik_izinli_diger": 0,
        }
        try:
            m_start, m_end = self._month_range(today)
            records = self._r.get("Izin_Giris").get_all() or []
            by_type: dict[str, set] = {"yillik": set(), "sua": set(), "rapor": set(), "diger": set()}
            all_personnel: set = set()

            for row in records:
                if str(row.get("Durum", "")).strip().lower() == "iptal":
                    continue
                pid = str(row.get("Personelid", "")).strip()
                start = _parse_date(row.get("BaslamaTarihi"))
                end   = _parse_date(row.get("BitisTarihi"))
                if not pid or not start:
                    continue
                if end is None:
                    end = start
                if start < datetime.strptime(m_end, "%Y-%m-%d") and end >= datetime.strptime(m_start, "%Y-%m-%d"):
                    ltype = self._classify_leave(str(row.get("IzinTipi", "")))
                    by_type[ltype].add(pid)
                    all_personnel.add(pid)

            stats["aylik_izinli_personel_toplam"] = len(all_personnel)
            stats["aylik_izinli_yillik"] = len(by_type["yillik"])
            stats["aylik_izinli_sua"]    = len(by_type["sua"])
            stats["aylik_izinli_rapor"]  = len(by_type["rapor"])
            stats["aylik_izinli_diger"]  = len(by_type["diger"])
            return SonucYonetici.tamam(veri=stats)
        except Exception as e:
            return SonucYonetici.hata(e, "DashboardService._aylik_izin_stats")

    # ───────────────────────────────────────────────────────────
    #  Yardımcılar
    # ───────────────────────────────────────────────────────────

    def _count_where(self, table: str, predicate) -> SonucYonetici:
        """Bir tablodaki kayıtları filtre fonksiyonu ile say."""
        rows = self._r.get(table).get_all() or []
        return SonucYonetici.tamam(veri=sum(1 for r in rows if predicate(r)))

    def _month_range(self, today: datetime) -> tuple[str, str]:
        """Ayın ilk ve son günü string olarak döndür."""
        m_start = today.replace(day=1).strftime("%Y-%m-%d")
        _, last_day = calendar.monthrange(today.year, today.month)
        m_end = today.replace(day=last_day).strftime("%Y-%m-%d")
        return m_start, m_end

    @staticmethod
    def _classify_leave(leave_type: str) -> str:
        lt = leave_type.strip().lower()
        if "yıllık" in lt or "yillik" in lt:
            return "yillik"
        if "şua" in lt or "sua" in lt:
            return "sua"
        if "rapor" in lt or "sağlık" in lt or "saglik" in lt:
            return "rapor"
        return "diger"

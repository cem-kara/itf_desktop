"""
DashboardService — Dashboard istatistikleri için service katmanı

Sorumluluklar:
- Cihaz / arıza / bakım / kalibrasyon sayıları
- RKE ve sağlık takip özetleri
- Aylık izinli personel istatistikleri
- Tüm sorgular tek noktadan, UI'a hazır dict döndürür
"""
import calendar
from datetime import datetime, timedelta
from typing import Optional
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

    def get_dashboard_data(self) -> dict:
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
            data["yaklasan_ndk"]        = self._yaklasan_ndk(today, today_str)
            data["aylik_bakim"]          = self._aylik_bakim(today)
            data["aylik_kalibrasyon"]    = self._aylik_kalibrasyon(today)
            data["yeni_arizalar"]        = self._yeni_arizalar(today, today_str)
            data["aktif_personel"]       = self._aktif_personel()
            data["yaklasan_rke"]         = self._yaklasan_rke(today, today_str)
            data["yaklasan_saglik"]      = self._yaklasan_saglik(today, today_str)
            data["gecmis_saglik"]        = self._gecmis_saglik(today_str)
            data["acik_arizalar"]        = self._acik_arizalar()
            data["gecmis_kalibrasyon"]   = self._gecmis_kalibrasyon(today_str)
            data.update(self._aylik_izin_stats(today))
        except Exception as e:
            logger.error(f"Dashboard data toplama hatası: {e}", exc_info=True)

        return data

    # ───────────────────────────────────────────────────────────
    #  Bireysel istatistikler
    # ───────────────────────────────────────────────────────────

    def _yaklasan_ndk(self, today: datetime, today_str: str) -> int:
        """6 ay içinde NDK lisansı sona erecek cihazlar."""
        try:
            six_months = (today + timedelta(days=180)).strftime("%Y-%m-%d")
            return self._count_where(
                "Cihazlar",
                lambda r: today_str <= str(r.get("BitisTarihi", "")) <= six_months
            )
        except Exception as e:
            logger.warning(f"Yaklaşan NDK sayımı hatası: {e}")
            return -1

    def _aylik_bakim(self, today: datetime) -> int:
        """Bu ay planlı bakım sayısı."""
        try:
            m_start, m_end = self._month_range(today)
            return self._count_where(
                "Periyodik_Bakim",
                lambda r: (
                    m_start <= str(r.get("PlanlananTarih", "")) <= m_end
                    and str(r.get("Durum", "")).strip() == "Planlandı"
                )
            )
        except Exception as e:
            logger.warning(f"Aylık bakım sayımı hatası: {e}")
            return -1

    def _aylik_kalibrasyon(self, today: datetime) -> int:
        """Bu ay tamamlanan kalibrasyon sayısı."""
        try:
            m_start, m_end = self._month_range(today)
            return self._count_where(
                "Kalibrasyon",
                lambda r: (
                    m_start <= str(r.get("BitisTarihi", "")) <= m_end
                    and str(r.get("Durum", "")).strip() == "Tamamlandı"
                )
            )
        except Exception as e:
            logger.warning(f"Aylık kalibrasyon sayımı hatası: {e}")
            return -1

    def _yeni_arizalar(self, today: datetime, today_str: str) -> int:
        """Son 7 günde açılan ve hâlâ açık arızalar."""
        try:
            one_week_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")
            return self._count_where(
                "Cihaz_Ariza",
                lambda r: (
                    str(r.get("BaslangicTarihi", "")) >= one_week_ago
                    and str(r.get("Durum", "")).strip() != "Kapatıldı"
                )
            )
        except Exception as e:
            logger.warning(f"Yeni arıza sayımı hatası: {e}")
            return -1

    def _aktif_personel(self) -> int:
        """Aktif personel sayısı."""
        try:
            return self._count_where(
                "Personel",
                lambda r: str(r.get("Durum", "")).strip() == "Aktif"
            )
        except Exception as e:
            logger.warning(f"Aktif personel sayımı hatası: {e}")
            return -1

    def _yaklasan_rke(self, today: datetime, today_str: str) -> int:
        """1 ay içinde kontrol tarihi gelecek RKE ekipmanlar."""
        try:
            one_month = (today + timedelta(days=30)).strftime("%Y-%m-%d")
            return self._count_where(
                "RKE_List",
                lambda r: (
                    today_str <= str(r.get("KontrolTarihi", "")) <= one_month
                    and str(r.get("Durum", "")).strip() == "Planlandı"
                )
            )
        except Exception as e:
            logger.warning(f"Yaklaşan RKE sayımı hatası: {e}")
            return -1

    def _yaklasan_saglik(self, today: datetime, today_str: str) -> int:
        """3 ay içinde sağlık kontrolü gelecek personel."""
        try:
            three_months = (today + timedelta(days=90)).strftime("%Y-%m-%d")
            return self._count_where(
                "Personel_Saglik_Takip",
                lambda r: (
                    today_str <= str(r.get("SonrakiKontrolTarihi", "")) <= three_months
                    and str(r.get("Durum", "")).strip() != "Pasif"
                )
            )
        except Exception as e:
            logger.warning(f"Yaklaşan sağlık sayımı hatası: {e}")
            return -1

    def _gecmis_saglik(self, today_str: str) -> int:
        """Sağlık kontrol tarihi geçmiş personel."""
        try:
            return self._count_where(
                "Personel_Saglik_Takip",
                lambda r: (
                    str(r.get("SonrakiKontrolTarihi", "")).strip() != ""
                    and str(r.get("SonrakiKontrolTarihi", "")) < today_str
                    and str(r.get("Durum", "")).strip() != "Pasif"
                )
            )
        except Exception as e:
            logger.warning(f"Geçmiş sağlık sayımı hatası: {e}")
            return -1

    def _acik_arizalar(self) -> int:
        """Açık arıza sayısı."""
        try:
            return self._count_where(
                "Cihaz_Ariza",
                lambda r: str(r.get("Durum", "")).strip() == "Açık"
            )
        except Exception as e:
            logger.warning(f"Açık arıza sayımı hatası: {e}")
            return -1

    def _gecmis_kalibrasyon(self, today_str: str) -> int:
        """Geçerlilik tarihi geçmiş kalibrasyon sayısı."""
        try:
            return self._count_where(
                "Kalibrasyon",
                lambda r: (
                    str(r.get("BitisTarihi", "")).strip() != ""
                    and str(r.get("BitisTarihi", "")) < today_str
                    and str(r.get("Durum", "")).strip() == "Tamamlandı"
                )
            )
        except Exception as e:
            logger.warning(f"Geçmiş kalibrasyon sayımı hatası: {e}")
            return -1

    def _aylik_izin_stats(self, today: datetime) -> dict:
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
                end   = _parse_date(row.get("BitisTarihi")) or start
                if not pid or not start:
                    continue
                if start < datetime.strptime(m_end, "%Y-%m-%d") and end >= datetime.strptime(m_start, "%Y-%m-%d"):
                    ltype = self._classify_leave(str(row.get("IzinTipi", "")))
                    by_type[ltype].add(pid)
                    all_personnel.add(pid)

            stats["aylik_izinli_personel_toplam"] = len(all_personnel)
            stats["aylik_izinli_yillik"] = len(by_type["yillik"])
            stats["aylik_izinli_sua"]    = len(by_type["sua"])
            stats["aylik_izinli_rapor"]  = len(by_type["rapor"])
            stats["aylik_izinli_diger"]  = len(by_type["diger"])
        except Exception as e:
            logger.warning(f"Aylık izin istatistik hatası: {e}")
        return stats

    # ───────────────────────────────────────────────────────────
    #  Yardımcılar
    # ───────────────────────────────────────────────────────────

    def _count_where(self, table: str, predicate) -> int:
        """Bir tablodaki kayıtları filtre fonksiyonu ile say."""
        rows = self._r.get(table).get_all() or []
        return sum(1 for r in rows if predicate(r))

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

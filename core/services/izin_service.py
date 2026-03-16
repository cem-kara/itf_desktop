"""
IzinService — Personel izin takibi işlemleri için service katmanı
Sorumluluklar:
- İzin verisi yükleme ve filtreleme
- İzin türleri listesi
- Pasif personel kuralı (30+ gün veya ücretsiz/aylıksız izin)
- İzin kaydı (INSERT/UPDATE/DELETE)
- Bugünkü izinli personel listesi
"""
from typing import Optional, List, Dict, Tuple
from datetime import date
import re
from core.hata_yonetici import SonucYonetici
from core.logger import logger
from core.date_utils import parse_date, to_ui_date
from database.repository_registry import RepositoryRegistry


class IzinService:
    """İzin ve izin takibi hizmeti"""
    
    def __init__(self, registry: RepositoryRegistry):
        """
        Servis oluştur.
        
        Args:
            registry: RepositoryRegistry örneği
        """
        if not registry:
            raise ValueError("RepositoryRegistry boş olamaz")
        self._r = registry
    
    # ───────────────────────────────────────────────────────────
    #  Repository Accessors
    # ───────────────────────────────────────────────────────────

    def get_izin_bilgi_repo(self) -> SonucYonetici:
        """İzin Bilgi repository'sine eriş."""
        return SonucYonetici.tamam(data=self._r.get("Izin_Bilgi"))

    def get_izin_giris_repo(self) -> SonucYonetici:
        """İzin Giriş repository'sine eriş."""
        return SonucYonetici.tamam(data=self._r.get("Izin_Giris"))

    def insert_izin_giris(self, data: dict) -> SonucYonetici:
        """İzin giriş kaydı ekle."""
        try:
            tc = str(data.get("Personelid", "")).strip()
            izin_tipi = str(data.get("IzinTipi", "")).strip()
            try:
                gun = int(data.get("Gun", 0))
            except (TypeError, ValueError):
                gun = 0

            if tc and izin_tipi and gun > 0:
                validation_sonuc = self.validate_izin_sure_limit(tc=tc, izin_tipi=izin_tipi, gun=gun)
                if not validation_sonuc.basarili:
                    return validation_sonuc

            self._r.get("Izin_Giris").insert(data)
            return SonucYonetici.tamam("İzin giriş kaydı eklendi.")
        except Exception as e:
            return SonucYonetici.hata(e, "IzinService.insert_izin_giris")

    def update_izin_giris(self, izin_id: str, data: dict) -> SonucYonetici:
        """İzin giriş kaydını güncelle."""
        try:
            self._r.get("Izin_Giris").update(izin_id, data)
            return SonucYonetici.tamam(f"İzin giriş kaydı güncellendi: {izin_id}")
        except Exception as e:
            logger.error(f"İzin giriş güncelleme hatası: {e}")
            return SonucYonetici.hata(e, "IzinService.update_izin_giris")

    # ───────────────────────────────────────────────────────────
    #  İş Kuralları
    # ───────────────────────────────────────────────────────────
    
    def should_set_pasif(self, izin_tipi: str, gun: int) -> bool:
        """
        Personeli pasif yapıp yapmayacağını belirle.
        
        İzin süresi 30+ gün VEYA ücretsiz/aylıksız izin → pasif olur.
        
        Args:
            izin_tipi: İzin türü (örn: "Yıllık İzin", "Ücretsiz İzin")
            gun: İzin süresi gün cinsinden
        
        Returns:
            Pasif yapılmalı ise True
        """
        # Gün kontrolü
        if gun > 30:
            return True
        
        # İzin türü kontrolü
        tip_lower = str(izin_tipi or "").strip().lower()
        if "aylıksız" in tip_lower or "ücretsiz" in tip_lower or "ucretsiz" in tip_lower:
            return True
        
        return False

    def _to_float(self, value, default: float = 0.0) -> float:
        """None/boş/string değerleri güvenli şekilde float'a çevir."""
        try:
            if value is None:
                return default
            if isinstance(value, str):
                s = value.strip().replace(",", ".")
                if not s:
                    return default
                return float(s)
            return float(value)
        except (TypeError, ValueError):
            return default

    def _normalize_izin_bilgi_payload(self, payload: Dict) -> Dict:
        """Izin_Bilgi sayısal alanlarında None değerleri 0.0'a normalize eder."""
        numeric_fields = (
            "YillikDevir",
            "YillikHakedis",
            "YillikToplamHak",
            "YillikKullanilan",
            "YillikKalan",
            "SuaKullanilabilirHak",
            "SuaKullanilan",
            "SuaKalan",
            "SuaCariYilKazanim",
            "RaporMazeretTop",
        )
        normalized = dict(payload)
        for key in numeric_fields:
            normalized[key] = self._to_float(normalized.get(key), 0.0)
        return normalized

    def _parse_max_from_aciklama(self, aciklama: str) -> Optional[int]:
        """Sabitler.Aciklama içinden sayısal max gün değerini çıkar."""
        text = str(aciklama or "").strip()
        if not text:
            return None

        # "10", "10 gün", "max: 15" gibi formatları destekle
        m = re.search(r"\d+(?:[.,]\d+)?", text)
        if not m:
            return None

        try:
            return max(0, int(float(m.group(0).replace(",", "."))))
        except (TypeError, ValueError):
            return None

    def get_izin_max_gun(self, tc: str, izin_tipi: str) -> Optional[int]:
        """
        İzin tipi + personel bazlı max gün sınırını döndürür.

        Returns:
            int: max gün sınırı
            None: limitsiz
        """
        tip = str(izin_tipi or "").strip()
        tc_str = str(tc or "").strip()
        if not tip:
            return None

        try:
            izin_bilgi = self._r.get("Izin_Bilgi").get_by_id(tc_str) if tc_str else None

            if tip == "Yıllık İzin":
                # 657 SK md.102: Birbirini izleyen iki yılın izni bir arada verilebilir.
                # Tek seferde max 60 gün (2 yıl), ayrıca toplamda YillikKalan'ı geçemez.
                kalan = self._to_float((izin_bilgi or {}).get("YillikKalan"), 0.0)
                return max(0, min(60, int(kalan)))

            if tip == "Şua İzni":
                # Şua sınırı SuaKullanilabilirHak alanından gelir.
                sua_hak = self._to_float((izin_bilgi or {}).get("SuaKullanilabilirHak"), 0.0)
                return max(0, int(sua_hak))

            # Diğer izinler: Sabitler.Aciklama sayısal ise limit, boşsa limitsiz.
            sabitler = self._r.get("Sabitler").get_all() or []
            for row in sabitler:
                if str(row.get("Kod", "")).strip() != "İzin_Tipi":
                    continue
                if str(row.get("MenuEleman", "")).strip() != tip:
                    continue
                return self._parse_max_from_aciklama(str(row.get("Aciklama", "")))

            return None
        except Exception as e:
            logger.error(f"Max izin gün hesaplama hatası: {e}")
            return None

    def validate_izin_sure_limit(self, tc: str, izin_tipi: str, gun: int) -> SonucYonetici:
        """İzin süresi limitini doğrular; limit aşımı varsa kaydı engeller."""
        try:
            if gun <= 0:
                return SonucYonetici.hata(Exception("İzin gün sayısı 0'dan büyük olmalıdır."), "IzinService.validate_izin_sure_limit")

            max_gun = self.get_izin_max_gun(tc=tc, izin_tipi=izin_tipi)
            if max_gun is None:
                return SonucYonetici.tamam()

            if gun > max_gun:
                return SonucYonetici.hata(Exception(f"{izin_tipi} için maksimum {max_gun} gün girilebilir."), "IzinService.validate_izin_sure_limit")

            return SonucYonetici.tamam()
        except Exception as e:
            logger.error(f"İzin limit doğrulama hatası: {e}")
            return SonucYonetici.hata(e, "IzinService.validate_izin_sure_limit")

    def hesapla_yillik_hak(self, baslama_tarihi: str) -> float:
        """
        Memuriyete başlama tarihine göre yıllık izin hakkını hesapla.

        Kural:
        - 1 yıldan az hizmet: 0 gün
        - 1-10 yıl (10 dahil): 20 gün
        - 10 yıldan fazla: 30 gün
        """
        try:
            baslama = parse_date(baslama_tarihi or "")
            if not baslama:
                return 0.0

            bugun = date.today()
            hizmet_yili = bugun.year - baslama.year
            if (bugun.month, bugun.day) < (baslama.month, baslama.day):
                hizmet_yili -= 1

            if hizmet_yili < 1:
                return 0.0
            if hizmet_yili <= 10:
                return 20.0
            return 30.0
        except Exception as e:
            logger.error(f"Yıllık hak hesaplama hatası: {e}")
            return 0.0

    def create_or_update_izin_bilgi(self, tc: str, ad_soyad: str, baslama_tarihi: str) -> SonucYonetici:
        """
        Personel için Izin_Bilgi kaydını oluşturur/günceller.
        Yıllık hak ve kalan alanlarını hizmet süresine göre set eder.
        """
        try:
            tc = str(tc or "").strip()
            if not tc:
                return SonucYonetici.hata(Exception("TC Kimlik No boş olamaz."), "IzinService.create_or_update_izin_bilgi")

            yillik_hak = self._to_float(self.hesapla_yillik_hak(baslama_tarihi), 0.0)
            payload = {
                "TCKimlik": tc,
                "AdSoyad": str(ad_soyad or "").strip(),
                "YillikDevir": 0.0,
                "YillikHakedis": yillik_hak,
                "YillikToplamHak": yillik_hak,
                "YillikKullanilan": 0.0,
                "YillikKalan": yillik_hak,
                "SuaKullanilabilirHak": 0.0,
                "SuaKullanilan": 0.0,
                "SuaKalan": 0.0,
                "SuaCariYilKazanim": 0.0,
                "RaporMazeretTop": 0.0,
            }
            payload = self._normalize_izin_bilgi_payload(payload)

            repo = self._r.get("Izin_Bilgi")
            mevcut = repo.get_by_id(tc)
            if mevcut:
                repo.update(tc, payload)
                logger.info(f"Izin_Bilgi güncellendi: {tc} (Yıllık Hak: {yillik_hak})")
                return SonucYonetici.tamam(f"Izin_Bilgi güncellendi: {tc}")
            else:
                repo.insert(payload)
                logger.info(f"Izin_Bilgi oluşturuldu: {tc} (Yıllık Hak: {yillik_hak})")
                return SonucYonetici.tamam(f"Izin_Bilgi oluşturuldu: {tc}")
        except Exception as e:
            return SonucYonetici.hata(e, "IzinService.create_or_update_izin_bilgi")

    # ───────────────────────────────────────────────────────────
    #  Veri Yükleme
    # ───────────────────────────────────────────────────────────

    def get_izin_listesi(self, ay: Optional[int] = None, yil: Optional[int] = None, tc: Optional[str] = None) -> SonucYonetici:
        """
        İzin listesini getir.
        
        Args:
            ay: Filtreleme için ay (isteğe bağlı)
            yil: Filtreleme için yıl (isteğe bağlı)
            tc: Filtreleme için TC Kimlik No (isteğe bağlı)
        
        Returns:
            İzin kayıtları
        """
        try:
            rows = self._r.get("Izin_Giris").get_all() or []
            
            if tc:
                rows = [r for r in rows if str(r.get("TC", "")).strip() == str(tc).strip()]
            
            if ay and yil:
                rows = [
                    r for r in rows
                    if str(r.get("Ay", "")).strip() == str(ay).strip()
                    and str(r.get("Yil", "")).strip() == str(yil).strip()
                ]
            elif ay:
                rows = [r for r in rows if str(r.get("Ay", "")).strip() == str(ay).strip()]
            elif yil:
                rows = [r for r in rows if str(r.get("Yil", "")).strip() == str(yil).strip()]
            
            return SonucYonetici.tamam(data=rows)
        except Exception as e:
            return SonucYonetici.hata(e, "IzinService.get_izin_listesi")

    def get_izin_tipleri(self) -> SonucYonetici:
        """
        İzin türlerini getir.
        
        Returns:
            İzin türleri listesi
        """
        try:
            sabitler = self._r.get("Sabitler").get_all() or []
            tipleri = [
                str(s.get("MenuEleman", "")).strip()
                for s in sabitler
                if str(s.get("Kod", "")).strip() == "IzinTipi"
                and str(s.get("MenuEleman", "")).strip()
            ]
            return SonucYonetici.tamam(data=sorted(list(set(tipleri))))
        except Exception as e:
            return SonucYonetici.hata(e, "IzinService.get_izin_tipleri")

    def get_personel_listesi(self) -> SonucYonetici:
        """
        Personel listesini getir.
        
        Returns:
            Tüm personeller
        """
        try:
            data = self._r.get("Personel").get_all() or []
            return SonucYonetici.tamam(data=data)
        except Exception as e:
            return SonucYonetici.hata(e, "IzinService.get_personel_listesi")

    def get_izinli_personeller_bugun(self) -> SonucYonetici:
        """
        Bugün izinli olan personellerin detaylı listesini getir.
        
        Returns:
            Dict[TC, List[(başlangıç_str, bitiş_str)]]
            Örnek: {"12345678901": [("01.03.2026", "05.03.2026")]}
        """
        try:
            today = date.today()
            izin_kayitlari = self._r.get("Izin_Giris").get_all() or []
            
            izinli_map: Dict[str, List[Tuple[str, str]]] = {}
            
            for kayit in izin_kayitlari:
                tc = str(kayit.get("Personelid", "")).strip()
                bas_tarih = parse_date(kayit.get("BaslamaTarihi", ""))
                bit_tarih = parse_date(kayit.get("BitisTarihi", ""))
                
                if not tc or not bas_tarih:
                    continue
                
                # Bitiş tarihi yoksa başlangıç tarihiyle aynı kabul et
                if not bit_tarih:
                    bit_tarih = bas_tarih
                
                # Bugün izin aralığında mı?
                if bas_tarih <= today <= bit_tarih:
                    bas_str = to_ui_date(kayit.get("BaslamaTarihi", ""), "")
                    bit_str = to_ui_date(kayit.get("BitisTarihi", ""), bas_str)
                    
                    if tc not in izinli_map:
                        izinli_map[tc] = []
                    izinli_map[tc].append((bas_str, bit_str))
            
            # Her TC için tarihleri sırala
            for tc in izinli_map:
                izinli_map[tc].sort(key=lambda x: x[0])
            
            return SonucYonetici.tamam(data=izinli_map)
        except Exception as e:
            return SonucYonetici.hata(e, "IzinService.get_izinli_personeller_bugun")

    # ───────────────────────────────────────────────────────────
    #  CRUD İşlemleri
    # ───────────────────────────────────────────────────────────

    def kaydet(self, veri: Dict, guncelle: bool = False) -> SonucYonetici:
        """
        İzin kaydı ekle veya güncelle.
        
        Args:
            veri: İzin verisi
            guncelle: True ise UPDATE, False ise INSERT
        
        Returns:
            Başarılı ise True
        """
        try:
            repo = self._r.get("Izin_Giris")
            if guncelle:
                izin_id = veri.get("Izinid")
                if not izin_id:
                    return SonucYonetici.hata(Exception("UPDATE için Izinid gerekli"), "IzinService.kaydet")
                repo.update(izin_id, veri)
                return SonucYonetici.tamam(f"İzin #{izin_id} güncellendi")
            else:
                repo.insert(veri)
                return SonucYonetici.tamam("Yeni izin kaydı oluşturuldu")
        except Exception as e:
            return SonucYonetici.hata(e, "IzinService.kaydet")

    def iptal_et(self, izin_id: str) -> SonucYonetici:
        """
        İzin kaydını iptal et (sil).
        
        Args:
            izin_id: İzin ID'si
        
        Returns:
            Başarılı ise True
        """
        try:
            self._r.get("Izin_Giris").delete(izin_id)
            return SonucYonetici.tamam(f"İzin #{izin_id} iptal edildi")
        except Exception as e:
            return SonucYonetici.hata(e, "IzinService.iptal_et")

    def get_sabitler_raw(self) -> SonucYonetici:
        """Tüm sabitler kayıtlarını döner (ham liste)."""
        try:
            data = self._r.get("Sabitler").get_all() or []
            return SonucYonetici.tamam(data=data)
        except Exception as e:
            return SonucYonetici.hata(e, "IzinService.get_sabitler_raw")

    def get_tatiller_raw(self) -> SonucYonetici:
        """Tüm tatil kayıtlarını döner (ham liste)."""
        try:
            data = self._r.get("Tatiller").get_all() or []
            return SonucYonetici.tamam(data=data)
        except Exception as e:
            return SonucYonetici.hata(e, "IzinService.get_tatiller_raw")

    def get_tum_izin_giris(self) -> SonucYonetici:
        """Tüm izin giriş kayıtlarını döner."""
        try:
            data = self._r.get("Izin_Giris").get_all() or []
            return SonucYonetici.tamam(data=data)
        except Exception as e:
            return SonucYonetici.hata(e, "IzinService.get_tum_izin_giris")

    def has_izin_cakisma(
        self,
        tc: str,
        baslama_tarihi: str,
        bitis_tarihi: str,
        ignore_izin_id: Optional[str] = None,
    ) -> SonucYonetici:
        """
        Verilen tarih aralığı için personelde izin çakışması var mı?

        Kural:
        - Durum "İptal" olanlar dikkate alınmaz.
        - Farklı personel kayıtları dikkate alınmaz.
        - Çakışma formülü: (yeni_bas <= vt_bit) and (yeni_bit >= vt_bas)
        - vt_bit boşsa vt_bas ile aynı kabul edilir.
        """
        try:
            tc_str = str(tc or "").strip()
            if not tc_str:
                return SonucYonetici.tamam(data=False)

            yeni_bas = parse_date(baslama_tarihi or "")
            yeni_bit = parse_date(bitis_tarihi or "")
            if not yeni_bas or not yeni_bit:
                return SonucYonetici.tamam(data=False)

            all_izin = self._r.get("Izin_Giris").get_all() or []
            for kayit in all_izin:
                if str(kayit.get("Durum", "")).strip() == "İptal":
                    continue

                if str(kayit.get("Personelid", "")).strip() != tc_str:
                    continue

                if ignore_izin_id and str(kayit.get("Izinid", "")).strip() == str(ignore_izin_id).strip():
                    continue

                vt_bas = parse_date(kayit.get("BaslamaTarihi", ""))
                vt_bit = parse_date(kayit.get("BitisTarihi", ""))
                if not vt_bas:
                    continue
                if not vt_bit:
                    vt_bit = vt_bas

                if (yeni_bas <= vt_bit) and (yeni_bit >= vt_bas):
                    return SonucYonetici.tamam(data=True)

            return SonucYonetici.tamam(data=False)
        except Exception as e:
            return SonucYonetici.hata(e, "IzinService.has_izin_cakisma")

    def calculate_carryover(self, mevcut_kalan: float, yillik_hakedis: float) -> float:
        """
        657 SK md.102 devir hesaplaması.
        
        Yıl sonu devir: Önceki yıllardaki kalan izinler ilk günleri (2 yıl limiti) kadar devredilebilir.
        Hesaplama: min(mevcut_kalan, yillik_hakedis, yillik_hakedis × 2)
        
        Args:
            mevcut_kalan: Bu yıl başındaki toplam kalan izin (gün)
            yillik_hakedis: Bu yıl için hak edilen izin (gün) — veya önceki yıl hakediş
        
        Returns:
            Devrine uygun izin miktarı (gün)
        
        Örnekler:
            • (35 gün kalan, 20 gün hakediş) → min(35, 20, 40) = 20 gün devir
            • (65 gün kalan, 20 gün hakediş) → min(65, 20, 40) = 20 gün devir (45 gün sona eriyor)
            • (55 gün kalan, 30 gün hakediş) → min(55, 30, 60) = 30 gün devir
        """
        try:
            kalan = float(mevcut_kalan or 0)
            hakediş = float(yillik_hakedis or 0)
            
            if kalan < 0 or hakediş < 0:
                return 0.0
            
            # 2 yıllık zamanaşımı limiti
            max_devir = hakediş * 2
            
            # Devir miktarı hesapla
            devir = min(kalan, hakediş, max_devir)
            
            return max(0.0, devir)
        except (ValueError, TypeError) as e:
            logger.error(f"IzinService.calculate_carryover: {e}")
            return 0.0

    def bakiye_dus(self, tc: str, izin_tipi: str, gun: int) -> SonucYonetici:
        """
        İzin kaydedilince bakiyeden otomatik düş.
        Yıllık İzin, Şua İzni, Rapor/Mazeret için çalışır.
        """
        try:
            izin_bilgi = self._r.get("Izin_Bilgi").get_by_id(tc)
            if not izin_bilgi:
                return SonucYonetici.hata(Exception("İzin bilgisi bulunamadı."), "IzinService.bakiye_dus")

            if izin_tipi == "Yıllık İzin":
                yeni_kul = float(izin_bilgi.get("YillikKullanilan", 0)) + gun
                yeni_kal = float(izin_bilgi.get("YillikKalan", 0)) - gun
                self._r.get("Izin_Bilgi").update(tc, {
                    "YillikKullanilan": yeni_kul,
                    "YillikKalan": yeni_kal,
                })
                return SonucYonetici.tamam(f"Yıllık izin bakiye düştü: {tc} → {gun} gün (Kalan: {yeni_kal})")

            elif izin_tipi == "Şua İzni":
                yeni_kul = float(izin_bilgi.get("SuaKullanilan", 0)) + gun
                yeni_kal = float(izin_bilgi.get("SuaKalan", 0)) - gun
                self._r.get("Izin_Bilgi").update(tc, {
                    "SuaKullanilan": yeni_kul,
                    "SuaKalan": yeni_kal,
                })
                return SonucYonetici.tamam(f"Şua izin bakiye düştü: {tc} → {gun} gün (Kalan: {yeni_kal})")

            elif izin_tipi in ("Rapor", "Mazeret İzni"):
                yeni_top = float(izin_bilgi.get("RaporMazeretTop", 0)) + gun
                self._r.get("Izin_Bilgi").update(tc, {"RaporMazeretTop": yeni_top})
                return SonucYonetici.tamam(f"Rapor/Mazeret toplam arttı: {tc} → +{gun} gün (Toplam: {yeni_top})")
            return SonucYonetici.tamam("Bakiye düşme işlemi tamamlandı.")
        except Exception as e:
            return SonucYonetici.hata(e, "IzinService.bakiye_dus")

    def set_personel_pasif(self, tc: str, izin_tipi: str, gun: int) -> SonucYonetici:
        """
        Uzun/ücretsiz izin kaydedilince personeli pasif yap.
        should_set_pasif() koşulunu kontrol eder.
        """
        if not tc or not self.should_set_pasif(izin_tipi, gun):
            return SonucYonetici.tamam("Personel pasif yapılmadı (koşul sağlanmadı).")
        try:
            self._r.get("Personel").update(tc, {"Durum": "Pasif"})
            return SonucYonetici.tamam(f"Personel pasif yapıldı: {tc} — {izin_tipi} — {gun} gün")
        except Exception as e:
            return SonucYonetici.hata(e, "IzinService.set_personel_pasif")

"""
Excel Import Modülü — Motor ve Veri Modelleri
=============================================
Kullanım:
    svc = ExcelImportService()
    df         = svc.excel_oku(dosya_yolu)          # pd.DataFrame
    harita     = svc.otomatik_eslestir(df.columns.tolist(), konfig)
    satirlar   = svc.donustur(df, harita, konfig)
    satirlar   = svc.duplicate_kontrol(satirlar, konfig, db)
    sonuc      = svc.yukle(satirlar, konfig, db, kaydeden="kullanici")
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Callable, Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Yardımcı: string normalize (otomatik eşleştirme için)
# ---------------------------------------------------------------------------

def _norm(text: str) -> str:
    """Küçük harf, aksansız, sadece alfanümerik."""
    text = unicodedata.normalize("NFKD", str(text))
    text = text.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", text.lower())


# ---------------------------------------------------------------------------
# Yardımcı: tip dönüşümleri
# ---------------------------------------------------------------------------

def _to_tc(val: str) -> str:
    """TC Kimlik — sayısal, 11 haneye sıfır doldur."""
    val = val.strip()
    if not val:
        return ""
    digits = re.sub(r"\D", "", val)
    return digits.zfill(11) if digits else ""


def _to_date(val: str) -> str:
    """Çeşitli formatları YYYY-MM-DD'ye çevirir; hatalıysa boş döner."""
    val = val.strip()
    if not val:
        return ""
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return pd.to_datetime(val, format=fmt).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            pass
    try:
        return pd.to_datetime(val, dayfirst=True, format="mixed").strftime("%Y-%m-%d")
    except Exception:
        return ""


def _to_int(val: str) -> str:
    val = val.strip()
    if not val:
        return ""
    try:
        return str(int(float(val)))
    except (ValueError, TypeError):
        return ""


def _to_float(val: str) -> str:
    val = val.strip()
    if not val:
        return ""
    try:
        return str(float(val.replace(",", ".")))
    except (ValueError, TypeError):
        return ""


def _to_str(val: str) -> str:
    return unicodedata.normalize("NFC", str(val)).strip()


_TIP_DONUSTUR: dict[str, Callable[[str], str]] = {
    "tc":    _to_tc,
    "date":  _to_date,
    "int":   _to_int,
    "float": _to_float,
    "str":   _to_str,
}


# ---------------------------------------------------------------------------
# Veri Modelleri
# ---------------------------------------------------------------------------

@dataclass
class AlanTanimi:
    """Tek bir DB kolonunu tanımlar."""
    alan: str                               # DB kolon adı  → "KimlikNo"
    goruntu: str                            # Ekran etiketi → "TC Kimlik No *"
    tip: str                                # "str" | "tc" | "date" | "int" | "float"
    zorunlu: bool = False
    varsayilan: str = ""                    # Boş gelirse kullanılacak değer (elle giriş default)
    anahtar_kelimeler: list[str] = field(default_factory=list)
    validator: Optional[Callable[[str], tuple[bool, str]]] = None
    # None → validasyon yok.
    # Fn   → (gecerli_mi, hata_mesaji) döner.
    # Örnek: lambda v: (validate_tc_kimlik_no(v), "Geçersiz TC Kimlik No")
    elle_girilebilir: bool = True
    # False → sadece Excel sütununa eşleştirilebilir, elle giriş yapılamaz.


@dataclass
class DuplicateKontrol:
    """Bir tablo için duplicate algılama ve çakışma stratejisi."""

    pk_alanlar: list[str]
    # DB'de zaten var mı kontrolü — import bağlamında anlamlı PK.
    #   Personel         → ["KimlikNo"]
    #   Cihazlar         → ["Cihazid"]
    #   RKE_List         → ["EkipmanNo"]
    #   RKE_Muayene      → ["EkipmanNo", "FMuayeneTarihi"]
    #   Dozimetre_Olcum  → ["TCKimlikNo", "Periyot", "Yil"]
    #   Dis_Alan_Calisma → ["TCKimlik", "DonemAy", "DonemYil", "TutanakNo"]
    #   Izin_Giris       → ["Personelid", "BaslamaTarihi", "IzinTipi"]
    #   Izin_Bilgi       → ["TCKimlik"]

    yumusak_alanlar: list[str] = field(default_factory=list)
    # PK farklı ama mantıksal duplicate — uyarı için.
    #   Izin_Giris   → ["Personelid", "BaslamaTarihi", "BitisTarihi"]
    #   RKE_Muayene  → ["EkipmanNo", "SMuayeneTarihi"]

    pk_cakisma: str = "raporla"
    # "raporla"    → hata listesine ekle, ekleme yapma
    # "atla"       → sessizce geç
    # "ustune_yaz" → mevcut kaydın üzerine yaz

    yumusak_cakisma: str = "uyar"
    # "uyar"    → ekle ama sonuçta uyarı göster
    # "atla"    → ekleme
    # "raporla" → hata listesine ekle


@dataclass
class ImportKonfig:
    """Bir tablo import işleminin tam yapılandırması."""
    baslik: str                              # "Toplu Personel İçe Aktarma"
    servis_fabrika: Callable                 # get_personel_service
    servis_metod: str                        # "ekle" | "cihaz_ekle" | ...
    tablo_adi: str                           # DB tablo adı — duplicate sorgusu için
    alanlar: list[AlanTanimi]
    duplicate: DuplicateKontrol
    normalize_fn: Optional[Callable[[dict], dict]] = None
    # None → yalnızca standart tip dönüşümleri uygulanır.
    # Fn   → standart dönüşüm SONRASINDA çağrılır; tablo özel ek mantık içerir.
    #        def normalize(kayit: dict) -> dict: ...


# ---------------------------------------------------------------------------
# table_config birleştirici
# ---------------------------------------------------------------------------

def alanlar_tam_listesi(konfig: "ImportKonfig") -> list[AlanTanimi]:
    """
    table_config.py'deki gerçek kolon listesini esas alarak tam AlanTanimi
    listesi döndürür.

    Öncelik kuralı:
    1. konfig.alanlar'da tanımlı alan → validator, zorunlu, anahtar_kelimeler
       gibi özel tanımlar korunur.
    2. table_config'de olup konfig.alanlar'da olmayan alan → otomatik AlanTanimi
       oluşturulur: tip date_fields'dan tespit edilir, geri kalanlar "str".
    3. table_config'de OLMAYAN ama konfig.alanlar'da olan alan → olduğu gibi eklenir
       (tabloya özel hesaplanmış alan olabilir).
    4. Sıra: table_config sütun sırası korunur, sonra ekstra konfig alanları.

    Atlanacak kolonlar: PK olmayan ama sistem tarafından doldurulan kolonlar
    (Resim, Diploma1, Diploma2, OzlukDosyasi, Img vb. binary/dosya kolonlar).
    """
    try:
        from database.table_config import TABLES
    except ImportError:
        return konfig.alanlar   # table_config yoksa konfig alanlarını kullan

    tablo = TABLES.get(konfig.tablo_adi)
    if not tablo:
        return konfig.alanlar

    # Dosya/binary kolonlar atlanır — import için anlamsız
    _ATLA = frozenset({
        "Resim", "Diploma1", "Diploma2", "OzlukDosyasi", "Img",
        "NDKLisansBelgesi", "Dosya", "Rapor",
        "KayitTarihi", "OlusturmaTarihi",   # otomatik doldurulan
    })

    tablo_kolonlar: list[str] = tablo.get("columns", [])
    date_fields: set[str]     = set(tablo.get("date_fields", []))

    # Konfig alanlarını hızlı erişim için indeksle
    konfig_idx: dict[str, AlanTanimi] = {a.alan: a for a in konfig.alanlar}

    sonuc: list[AlanTanimi] = []
    eklenen: set[str] = set()

    for kolon in tablo_kolonlar:
        if kolon in _ATLA:
            continue
        if kolon in konfig_idx:
            # Konfig tanımı var → aynen kullan
            sonuc.append(konfig_idx[kolon])
        else:
            # Otomatik oluştur
            tip = "date" if kolon in date_fields else "str"
            goruntu = _kolon_goruntu(kolon)
            sonuc.append(AlanTanimi(
                alan=kolon,
                goruntu=goruntu,
                tip=tip,
            ))
        eklenen.add(kolon)

    # Konfig'de olup table_config'de olmayan alanlar sona eklenir
    for at in konfig.alanlar:
        if at.alan not in eklenen:
            sonuc.append(at)

    return sonuc


def _kolon_goruntu(kolon: str) -> str:
    """
    CamelCase kolon adını okunabilir etikete çevirir.
    Örnek: "MemuriyeteBaslamaTarihi" → "Memuriyete Baslama Tarihi"
    """
    import re
    # CamelCase → boşluklu
    goster = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", kolon)
    goster = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", goster)
    return goster.strip()


@dataclass
class SatirSonucu:
    """Tek bir Excel satırının dönüştürme + yükleme sonucu."""
    satir_no: int
    veri: dict                               # Normalize edilmiş kayıt
    durum: str = ""
    # ""                 → henüz işlenmedi
    # "basarili"         → DB'ye eklendi
    # "hatali"           → servis hata döndürdü
    # "pk_duplicate"     → DB'de aynı PK zaten var
    # "yumusak_duplicate"→ yumuşak çakışma (yine de eklendi)
    # "zorunlu_eksik"    → zorunlu alan boş
    hata_mesaji: str = ""
    duzeltilmis_veri: Optional[dict] = None
    # Kullanıcı hata düzeltme ekranında güncellerse buraya yazılır.
    # None → orijinal veri kullanılır.


@dataclass
class ImportSonucu:
    """Tüm import işleminin özeti."""
    toplam: int
    basarili: int
    hatali: int
    pk_duplicate: int
    yumusak_duplicate: int
    zorunlu_eksik: int
    satirlar: list[SatirSonucu]

    @property
    def duzeltilecekler(self) -> list[SatirSonucu]:
        """Hatalı veya zorunlu alanı eksik satırlar — düzeltme ekranı için."""
        return [s for s in self.satirlar if s.durum in ("hatali", "zorunlu_eksik")]

    @property
    def uyarilar(self) -> list[SatirSonucu]:
        """Yumuşak duplicate olan satırlar."""
        return [s for s in self.satirlar if s.durum == "yumusak_duplicate"]


# ---------------------------------------------------------------------------
# Motor
# ---------------------------------------------------------------------------

class ExcelImportService:
    """
    Excel dosyasını okuyup DB'ye yükleyen merkezi motor.
    Durum bilgisi taşımaz — her metod bağımsız çağrılabilir.
    """

    # ------------------------------------------------------------------
    # 1) Dosya okuma
    # ------------------------------------------------------------------

    def excel_oku(self, dosya_yolu: str) -> pd.DataFrame:
        """
        Excel dosyasını okur; tüm sütunlar str olarak gelir, NaN → "".
        Döner: pd.DataFrame
        Fırlatır: ValueError (dosya okunamazsa)
        """
        try:
            df = pd.read_excel(dosya_yolu, dtype=str)
            df = df.fillna("").astype(str)
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except Exception as exc:
            raise ValueError(f"Excel dosyası okunamadı: {exc}") from exc

    # ------------------------------------------------------------------
    # 2) Otomatik sütun eşleştirme
    # ------------------------------------------------------------------

    def otomatik_eslestir(
        self,
        sutunlar: list[str],
        konfig: ImportKonfig,
    ) -> dict[str, str]:
        """
        Excel sütun adlarını DB alan adlarıyla eşleştirir.

        Algoritma:
          1. Sütun adını normalize et (_norm).
          2. Her AlanTanimi.anahtar_kelimeler listesini tara.
          3. Normalize sütun adı, normalize anahtar kelimeyi içeriyorsa eşleştir.
          4. Birden fazla alan eşleşirse en uzun anahtarı tercih et
             (daha spesifik eşleşme öncelikli).
          5. Aynı DB alanına iki farklı sütun eşleşmesin — ilk gelene öncelik.

        Döner: {"Excel Başlığı": "db_alan_adi", ...}
                — eşleşmeyen sütunlar haritaya dahil edilmez.
        """
        harita: dict[str, str] = {}

        for sutun in sutunlar:
            norm_sutun = _norm(sutun)
            en_iyi: Optional[tuple[int, str]] = None  # (eşleşme_uzunluğu, db_alan)

            for alan_tanimi in konfig.alanlar:
                for anahtar in alan_tanimi.anahtar_kelimeler:
                    norm_anahtar = _norm(anahtar)
                    if norm_anahtar and norm_anahtar in norm_sutun:
                        uzunluk = len(norm_anahtar)
                        if en_iyi is None or uzunluk > en_iyi[0]:
                            en_iyi = (uzunluk, alan_tanimi.alan)

            if en_iyi:
                db_alan = en_iyi[1]
                # Aynı DB alanına ikinci bir sütun eşleşmesin
                if db_alan not in harita.values():
                    harita[sutun] = db_alan

        return harita

    # ------------------------------------------------------------------
    # 3) Dönüştürme (normalizasyon + zorunlu alan kontrolü)
    # ------------------------------------------------------------------

    def donustur(
        self,
        df: pd.DataFrame,
        harita: dict[str, str],                    # {"Excel Sutun": "db_alan"}
        konfig: ImportKonfig,
        manuel_degerler: Optional[dict[str, str]] = None,  # {"db_alan": "sabit_deger"}
    ) -> list[SatirSonucu]:
        """
        DataFrame'i SatirSonucu listesine çevirir.
        DB'ye henüz yazılmaz — sadece dönüşüm ve validasyon yapılır.

        manuel_degerler: Adım 2'de "Elle Gir" ile girilen sabit değerler.
        Her satıra aynı değer uygulanır. Excel sütununa eşleştirilmiş
        alanlar için manuel_degerler göz ardı edilir.
        """
        # Ters harita: db_alan → excel_sutun
        ters_harita: dict[str, str] = {v: k for k, v in harita.items()}
        manuel = manuel_degerler or {}

        sonuclar: list[SatirSonucu] = []

        for idx, row in df.iterrows():
            satir_no = int(idx) + 2
            kayit: dict = {}
            hata_mesajlari: list[str] = []
            durum = ""

            for alan_tanimi in konfig.alanlar:
                db_alan = alan_tanimi.alan
                excel_sutun = ters_harita.get(db_alan)

                # Değer önceliği: Excel sütunu > manuel giriş > varsayılan
                if excel_sutun and excel_sutun in row.index:
                    ham = str(row[excel_sutun]).strip()
                elif db_alan in manuel and manuel[db_alan]:
                    ham = manuel[db_alan]
                elif alan_tanimi.varsayilan:
                    ham = alan_tanimi.varsayilan
                else:
                    ham = ""

                # Tip dönüşümü
                donustur_fn = _TIP_DONUSTUR.get(alan_tanimi.tip, _to_str)
                donusturulmus = donustur_fn(ham)

                # Zorunlu alan kontrolü
                if alan_tanimi.zorunlu and not donusturulmus:
                    hata_mesajlari.append(f"'{alan_tanimi.goruntu}' zorunlu")
                    durum = "zorunlu_eksik"

                # Validator kontrolü (değer doluysa)
                elif donusturulmus and alan_tanimi.validator:
                    try:
                        gecerli, hata_msg = alan_tanimi.validator(donusturulmus)
                        if not gecerli:
                            hata_mesajlari.append(f"'{alan_tanimi.goruntu}': {hata_msg}")
                            if durum == "":
                                durum = "hatali"
                    except Exception as exc:
                        hata_mesajlari.append(f"'{alan_tanimi.goruntu}' validasyon hatası: {exc}")
                        if durum == "":
                            durum = "hatali"

                kayit[db_alan] = donusturulmus

            # Tablo özel normalize_fn (standart dönüşüm SONRASINDA)
            if konfig.normalize_fn and durum not in ("zorunlu_eksik", "hatali"):
                try:
                    kayit = konfig.normalize_fn(kayit)
                except Exception as exc:
                    hata_mesajlari.append(f"Normalize hatası: {exc}")
                    durum = "hatali"

            sonuclar.append(SatirSonucu(
                satir_no=satir_no,
                veri=kayit,
                durum=durum,
                hata_mesaji="; ".join(hata_mesajlari),
            ))

        return sonuclar

    # ------------------------------------------------------------------
    # 4) Duplicate kontrolü (toplu sorgu — satır başına DB çağrısı YOK)
    # ------------------------------------------------------------------

    def duplicate_kontrol(
        self,
        satirlar: list[SatirSonucu],
        konfig: ImportKonfig,
        db,
    ) -> list[SatirSonucu]:
        """
        Mevcut DB kayıtlarıyla karşılaştırır.
        Yalnızca durum=="" olan (henüz temiz) satırlar kontrol edilir.
        pk_duplicate / yumusak_duplicate olarak işaretler.
        """
        dup = konfig.duplicate
        temiz = [s for s in satirlar if s.durum == ""]
        if not temiz:
            return satirlar

        # --- PK duplicate ---
        if dup.pk_alanlar:
            mevcut_pkler = self._mevcut_pk_seti(konfig.tablo_adi, dup.pk_alanlar, db)
            for satir in temiz:
                anahtar = tuple(satir.veri.get(a, "") for a in dup.pk_alanlar)
                if anahtar in mevcut_pkler:
                    satir.durum = "pk_duplicate"
                    satir.hata_mesaji = (
                        "Zaten mevcut: "
                        + ", ".join(f"{k}={v}" for k, v in zip(dup.pk_alanlar, anahtar))
                    )

        # --- Yumuşak duplicate ---
        if dup.yumusak_alanlar:
            mevcut_yumusak = self._mevcut_pk_seti(
                konfig.tablo_adi, dup.yumusak_alanlar, db
            )
            for satir in temiz:
                if satir.durum != "":
                    continue
                anahtar = tuple(satir.veri.get(a, "") for a in dup.yumusak_alanlar)
                if anahtar in mevcut_yumusak:
                    if dup.yumusak_cakisma == "uyar":
                        satir.durum = "yumusak_duplicate"
                        satir.hata_mesaji = (
                            "Mantıksal çakışma: "
                            + ", ".join(f"{k}={v}" for k, v in zip(dup.yumusak_alanlar, anahtar))
                        )
                    elif dup.yumusak_cakisma == "atla":
                        satir.durum = "pk_duplicate"
                        satir.hata_mesaji = "Yumuşak çakışma — atlandı"
                    elif dup.yumusak_cakisma == "raporla":
                        satir.durum = "hatali"
                        satir.hata_mesaji = "Yumuşak çakışma — hata olarak raporlandı"

        return satirlar

    def _mevcut_pk_seti(
        self,
        tablo: str,
        alanlar: list[str],
        db,
    ) -> set[tuple]:
        """
        Tek SQL sorgusunda mevcut PK kombinasyonlarını çeker.
        db parametresi sqlite3 uyumlu cursor() metoduna sahip olmalıdır.
        """
        if not alanlar:
            return set()
        alan_listesi = ", ".join(alanlar)
        try:
            cur = db.cursor()
            cur.execute(f"SELECT {alan_listesi} FROM {tablo}")
            return {
                tuple(str(v) if v is not None else "" for v in row)
                for row in cur.fetchall()
            }
        except Exception:
            # Tablo henüz yoksa veya farklı DB arayüzü kullanılıyorsa boş dön
            return set()

    # ------------------------------------------------------------------
    # 5) Yükleme
    # ------------------------------------------------------------------

    def yukle(
        self,
        satirlar: list[SatirSonucu],
        konfig: ImportKonfig,
        db,
        kaydeden: str = "",
    ) -> ImportSonucu:
        """
        Uygun satırları DB'ye yazar.

        Hangi satırlar yüklenir:
          - durum == ""                              → temiz satır
          - durum == "pk_duplicate" + "ustune_yaz"  → üzerine yaz
          - durum == "yumusak_duplicate"             → ekle (uyarı zaten var)

        Servis metodunu konfig üzerinden çağırır:
          svc = konfig.servis_fabrika(db)
          metod = getattr(svc, konfig.servis_metod)
          sonuc = metod(veri_dict)
        """
        svc = konfig.servis_fabrika(db)
        metod = getattr(svc, konfig.servis_metod)
        dup = konfig.duplicate

        for satir in satirlar:
            if satir.durum == "":
                pass  # temiz
            elif satir.durum == "pk_duplicate" and dup.pk_cakisma == "ustune_yaz":
                pass  # üzerine yaz
            elif satir.durum == "yumusak_duplicate":
                pass  # uyar ama yine de ekle
            else:
                continue  # diğerleri → atla

            veri = dict(satir.veri)
            if kaydeden:
                veri["kaydeden"] = kaydeden

            try:
                sonuc = metod(veri)
                # SonucYonetici uyumluluğu:
                #   .basarili_mi  (yeni standart)
                #   .basarili     (mevcut servisler — personel, cihaz vb.)
                #   .hata / .mesaj  hata açıklaması için
                if hasattr(sonuc, "basarili_mi"):
                    ok = sonuc.basarili_mi
                elif hasattr(sonuc, "basarili"):
                    ok = sonuc.basarili
                else:
                    ok = True   # dönüş değeri belirsizse başarılı say

                if ok:
                    satir.durum = "basarili"
                else:
                    satir.durum = "hatali"
                    satir.hata_mesaji = str(
                        getattr(sonuc, "hata", None)
                        or getattr(sonuc, "mesaj", None)
                        or sonuc
                    )
            except Exception as exc:
                satir.durum = "hatali"
                satir.hata_mesaji = str(exc)

        return self._ozet_olustur(satirlar)

    # ------------------------------------------------------------------
    # 6) Yeniden yükleme (hata düzeltme ekranından)
    # ------------------------------------------------------------------

    def yeniden_yukle(
        self,
        satirlar: list[SatirSonucu],
        konfig: ImportKonfig,
        db,
        kaydeden: str = "",
    ) -> ImportSonucu:
        """
        Hata düzeltme ekranından gelen satırları tekrar dener.
        satir.duzeltilmis_veri varsa onu kullanır, yoksa orijinal veriyi.
        Sadece "hatali" ve "zorunlu_eksik" satırlar yeniden denenir.
        """
        for satir in satirlar:
            if satir.durum not in ("hatali", "zorunlu_eksik"):
                continue
            if satir.duzeltilmis_veri is not None:
                satir.veri = satir.duzeltilmis_veri
                satir.duzeltilmis_veri = None
            # Durumu sıfırla ki yukle() işleyebilsin
            satir.durum = ""
            satir.hata_mesaji = ""

        return self.yukle(satirlar, konfig, db, kaydeden)

    # ------------------------------------------------------------------
    # Yardımcı: özet oluştur
    # ------------------------------------------------------------------

    def _ozet_olustur(self, satirlar: list[SatirSonucu]) -> ImportSonucu:
        sayac: dict[str, int] = {
            "basarili": 0,
            "hatali": 0,
            "pk_duplicate": 0,
            "yumusak_duplicate": 0,
            "zorunlu_eksik": 0,
        }
        for s in satirlar:
            if s.durum in sayac:
                sayac[s.durum] += 1

        return ImportSonucu(
            toplam=len(satirlar),
            basarili=sayac["basarili"],
            hatali=sayac["hatali"],
            pk_duplicate=sayac["pk_duplicate"],
            yumusak_duplicate=sayac["yumusak_duplicate"],
            zorunlu_eksik=sayac["zorunlu_eksik"],
            satirlar=satirlar,
        )

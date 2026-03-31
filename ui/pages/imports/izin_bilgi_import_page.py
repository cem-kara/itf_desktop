# -*- coding: utf-8 -*-
"""
izin_bilgi_import_page.py — Toplu İzin Bakiye Excel İçe Aktarma

create_or_update_izin_bilgi() yıllık hakkı baslama_tarihi'nden HESAPLİYOR,
Excel'deki değerleri görmezden geliyor. Bu sayfa ise Excel'deki bakiye
değerlerini olduğu gibi DB'ye yazar.

Strateji: get_izin_bilgi_repo() üzerinden doğrudan insert/update.
"""

from core.services.excel_import_service import AlanTanimi, DuplicateKontrol, ImportKonfig

from core.validators import validate_tc_kimlik_no
from core.text_utils import turkish_title_case
from ui.pages.imports.components.base_import_page import BaseImportPage
from core.di import get_izin_service


def _tc_v(v): return validate_tc_kimlik_no(v), "Geçersiz TC Kimlik No (hane algoritması)"


def _normalize(kayit: dict) -> dict:
    if kayit.get("AdSoyad"):
        kayit["AdSoyad"] = turkish_title_case(kayit["AdSoyad"])
    return kayit


class _IzinBilgiDirectAdapter:
    """
    Excel bakiye değerlerini doğrudan Izin_Bilgi tablosuna yazar.
    create_or_update_izin_bilgi() atlanır — o metod değerleri yeniden
    hesaplar ve Excel verisi kaybolur.
    """

    _SAYISAL = (
        "YillikDevir", "YillikHakedis", "YillikToplamHak",
        "YillikKullanilan", "YillikKalan",
        "SuaKullanilabilirHak", "SuaKullanilan", "SuaKalan",
        "SuaCariYilKazanim", "RaporMazeretTop",
    )

    def __init__(self, svc):
        self._svc = svc

    @staticmethod
    def _to_float(val) -> float:
        try:
            return float(str(val).replace(",", "."))
        except (TypeError, ValueError):
            return 0.0

    def _normalize_payload(self, kayit: dict) -> dict:
        payload = dict(kayit)
        for alan in self._SAYISAL:
            payload[alan] = self._to_float(payload.get(alan))
        return payload

    def izin_bilgi_kaydet(self, kayit: dict):
        """
        TCKimlik PK'sına göre mevcut kaydı günceller, yoksa ekler.
        Tüm sayısal alanları float'a normalize eder.
        """
        try:
            tc = str(kayit.get("TCKimlik", "")).strip()
            if not tc:
                class _Err:
                    basarili = False
                    mesaj = "TCKimlik boş olamaz"
                return _Err()

            repo_sonuc = self._svc.get_izin_bilgi_repo()
            repo = repo_sonuc.veri

            payload = self._normalize_payload(kayit)

            mevcut = repo.get_by_id(tc)
            if mevcut:
                repo.update(tc, payload)
            else:
                repo.insert(payload)

            class _Ok:
                basarili = True
                mesaj = ""
            return _Ok()

        except Exception as exc:
            class _Err:
                basarili = False
            _Err.mesaj = str(exc)
            return _Err()


def _get_adapter(db):
    return _IzinBilgiDirectAdapter(get_izin_service(db))


KONFIG = ImportKonfig(
    baslik="Toplu İzin Bakiye İçe Aktarma",
    servis_fabrika=_get_adapter,
    servis_metod="izin_bilgi_kaydet",
    tablo_adi="Izin_Bilgi",
    normalize_fn=_normalize,

    duplicate=DuplicateKontrol(
        pk_alanlar=["TCKimlik"],
        pk_cakisma="ustune_yaz",
    ),

    alanlar=[
        # ── Zorunlu ─────────────────────────────────────────────────────
        AlanTanimi(
            "TCKimlik", "TC Kimlik No *", "tc",
            zorunlu=True,
            validator=_tc_v,
            anahtar_kelimeler=["tckimlik", "kimlik", "tc", "tcno", "kimlikno"],
        ),
        AlanTanimi(
            "AdSoyad", "Ad Soyad", "str",
            anahtar_kelimeler=["adsoyad", "ad", "isim", "name"],
        ),

        # ── Yıllık Bakiye — Excel sütun adlarıyla eşleşen anahtar kelimeler
        AlanTanimi(
            "YillikHakedis", "Yıllık Hakediş", "float",
            anahtar_kelimeler=["yillikhakedis", "hakedis", "hakedilen",
                               "hak", "hakedisgunu"],
        ),
        AlanTanimi(
            "YillikDevir", "Yıllık Devir", "float",
            anahtar_kelimeler=["yillikdevir", "devir", "carriedover"],
        ),
        AlanTanimi(
            "YillikToplamHak", "Yıllık Toplam Hak", "float",
            anahtar_kelimeler=["yilliktoplamhak", "toplamhak", "toplam"],
        ),
        AlanTanimi(
            "YillikKullanilan", "Yıllık Kullanılan", "float",
            anahtar_kelimeler=["yillikkullanilan", "kullanilan"],
        ),
        AlanTanimi(
            "YillikKalan", "Yıllık Kalan", "float",
            anahtar_kelimeler=["yillikkalan", "kalan", "bakiye"],
        ),

        # ── SUA Bakiyesi ─────────────────────────────────────────────────
        AlanTanimi(
            "SuaKullanilabilirHak", "SUA Kullanılabilir Hak", "float",
            anahtar_kelimeler=["suakullanilabilir", "suahak"],
        ),
        AlanTanimi(
            "SuaKullanilan", "SUA Kullanılan", "float",
            anahtar_kelimeler=["suakullanilan"],
        ),
        AlanTanimi(
            "SuaKalan", "SUA Kalan", "float",
            anahtar_kelimeler=["suakalan"],
        ),
        AlanTanimi(
            "SuaCariYilKazanim", "SUA Cari Yıl Kazanım", "float",
            anahtar_kelimeler=["suacariyil", "suakazanim"],
        ),
        AlanTanimi(
            "RaporMazeretTop", "Rapor/Mazeret Toplam", "float",
            anahtar_kelimeler=["rapormazeret", "mazeret", "rapor"],
        ),
    ],
)


class IzinBilgiImportPage(BaseImportPage):
    def _konfig(self) -> ImportKonfig:
        return KONFIG

# core/hata_yonetici.py
# -*- coding: utf-8 -*-
"""
Merkezi Hata Yönetimi
═══════════════════════════════════════════════════════════════

KATMANLAR
─────────
1. qmessagebox_yakala()
   Tüm QMessageBox.critical/warning/information çağrılarını
   otomatik olarak log'a yazar. Sayfalara dokunmadan çalışır.

2. global_exception_hook_kur()
   Ana iş parçacığındaki yakalanmayan istisnaları loglar.

3. threading_exception_hook_kur()
   QThread / threading.Thread içindeki istisnaları loglar.

4. SonucYonetici — Servis katmanı için standart sonuç nesnesi
   ┌──────────────────────────────────────────────────────────┐
   │  svc = get_cihaz_service(db)                             │
   │  sonuc = svc.cihaz_ekle(veri)          # SonucYonetici  │
   │  if sonuc.basarili:                                      │
   │      bilgi_goster(self, sonuc.mesaj)                     │
   │  else:                                                   │
   │      hata_goster(self, sonuc.mesaj)                      │
   └──────────────────────────────────────────────────────────┘

5. Açık API — UI sayfaları için:
   exc_logla(konum, exc)
   hata_goster(parent, msg)
   uyari_goster(parent, msg)
   bilgi_goster(parent, msg)
   hata_logla_goster(parent, konum, exc)

6. servis_calistir() — UI'daki try/except bloklarını tek satıra indirir:
   ┌──────────────────────────────────────────────────────────┐
   │  sonuc = servis_calistir(                                │
   │      self,                                               │
   │      "PersonelEkle._kaydet",                             │
   │      lambda: self._svc.ekle(veri),                       │
   │      basari_msg="Personel eklendi.",                     │
   │  )                                                       │
   └──────────────────────────────────────────────────────────┘

KULLANIM (main.pyw):
    from core.hata_yonetici import (
        qmessagebox_yakala,
        global_exception_hook_kur,
        threading_exception_hook_kur,
    )
    app = QApplication(sys.argv)
    qmessagebox_yakala()          # sayfa importlarından önce
    global_exception_hook_kur()
    threading_exception_hook_kur()
"""
from __future__ import annotations

import sys
import traceback
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, TypeVar

from core.logger import logger

T = TypeVar("T")


# ══════════════════════════════════════════════════════════════
# 1. QMessageBox LOG YAKALAYICI
# ══════════════════════════════════════════════════════════════

def qmessagebox_yakala() -> None:
    """
    QMessageBox.critical / .warning / .information çağrılarını
    otomatik olarak log dosyasına da yazar.
    """
    try:
        import PySide6.QtWidgets as _qw

        _Orj = _qw.QMessageBox

        class _LoggedQMessageBox(_Orj):
            @staticmethod
            def critical(parent, title, msg, *args, **kwargs):
                logger.error(f"[UI ❌] {title}: {msg}")
                return _msgbox_critical(parent, title, msg)

            @staticmethod
            def warning(parent, title, msg, *args, **kwargs):
                logger.warning(f"[UI ⚠️] {title}: {msg}")
                return _msgbox_warning(parent, title, msg)

            @staticmethod
            def information(parent, title, msg, *args, **kwargs):
                logger.info(f"[UI ℹ️] {title}: {msg}")
                return _msgbox_bilgi(parent, title, msg)

        _qw.QMessageBox = _LoggedQMessageBox
        logger.info("QMessageBox log yakalayıcısı aktif edildi.")

    except Exception as exc:
        logger.error(f"qmessagebox_yakala başarısız: {exc}")


# ══════════════════════════════════════════════════════════════
# 2. ANA İŞ PARÇACIĞI — sys.excepthook
# ══════════════════════════════════════════════════════════════

def global_exception_hook_kur() -> None:
    """Ana iş parçacığındaki yakalanmayan her istisna loglanır."""

    def _hook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logger.critical(
            f"[YAKALANMAYAN İSTİSNA]\n"
            f"Tür  : {exc_type.__name__}\n"
            f"Mesaj: {exc_value}\n"
            f"{tb_str}"
        )
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook
    logger.info("Global exception hook kuruldu.")


# ══════════════════════════════════════════════════════════════
# 3. THREAD İSTİSNALARI
# ══════════════════════════════════════════════════════════════

def threading_exception_hook_kur() -> None:
    """threading.Thread ve QThread içindeki yakalanmayan istisnaları loglar."""

    def _thread_hook(args: threading.ExceptHookArgs) -> None:
        if args.exc_type is SystemExit:
            return
        tb_str = "".join(
            traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)
        )
        thread_adi = getattr(args.thread, "name", "Bilinmeyen Thread")
        logger.error(
            f"[THREAD İSTİSNASI — {thread_adi}]\n"
            f"Tür  : {args.exc_type.__name__}\n"
            f"Mesaj: {args.exc_value}\n"
            f"{tb_str}"
        )

    threading.excepthook = _thread_hook
    logger.info("Threading exception hook kuruldu.")


# ══════════════════════════════════════════════════════════════
# 4. SonucYonetici — Servis katmanı için standart sonuç nesnesi
# ══════════════════════════════════════════════════════════════

@dataclass
class SonucYonetici:
    """
    Servis metodlarından dönen standart sonuç nesnesi.

    Kullanım (servis tarafı):
        def kaydet(self, veri: dict) -> SonucYonetici:
            try:
                self._r.get("Tablo").insert(veri)
                return SonucYonetici.tamam("Kayıt eklendi.")
            except Exception as e:
                return SonucYonetici.hata(e, "Kayit._kaydet")

    Kullanım (UI tarafı):
        sonuc = svc.kaydet(veri)
        if sonuc.basarili:
            bilgi_goster(self, sonuc.mesaj)
        else:
            hata_goster(self, sonuc.mesaj)
    """
    basarili: bool
    mesaj: str = ""
    veri: Any = None
    hata_turu: str = ""
    _tb: str = field(default="", repr=False)

    # ── Fabrika metodları ─────────────────────────────────────

    @classmethod
    def tamam(cls, mesaj: str = "", veri: Any = None) -> "SonucYonetici":
        """Başarılı sonuç üretir."""
        return cls(basarili=True, mesaj=mesaj, veri=veri)

    @classmethod
    def hata(
        cls,
        exc_veya_mesaj,
        konum: str = "",
        kullanici_mesaji: Optional[str] = None,
    ) -> "SonucYonetici":
        """
        Hatalı sonuç üretir, otomatik log yazar.

        exc_veya_mesaj: Exception veya string
        konum: "ServisAdi.metod" formatında — log'a yazılır
        kullanici_mesaji: Kullanıcıya gösterilecek mesaj (None → exc mesajı)
        """
        if isinstance(exc_veya_mesaj, Exception):
            exc = exc_veya_mesaj
            tb = traceback.format_exc()
            hata_turu = type(exc).__name__
            log_msg = str(exc)
            gosterilecek = kullanici_mesaji or str(exc)
        else:
            exc = None
            tb = ""
            hata_turu = "Hata"
            log_msg = str(exc_veya_mesaj)
            gosterilecek = kullanici_mesaji or str(exc_veya_mesaj)

        if konum:
            logger.error(f"[{konum}] {hata_turu}: {log_msg}\n{tb}".rstrip())
        else:
            logger.error(f"{hata_turu}: {log_msg}\n{tb}".rstrip())

        return cls(
            basarili=False,
            mesaj=gosterilecek,
            hata_turu=hata_turu,
            _tb=tb,
        )

    @classmethod
    def uyari(cls, mesaj: str, konum: str = "") -> "SonucYonetici":
        """Uyarı sonucu — kullanıcıya gösterilmeli ama kritik değil."""
        if konum:
            logger.warning(f"[{konum}] {mesaj}")
        else:
            logger.warning(mesaj)
        return cls(basarili=False, mesaj=mesaj, hata_turu="Uyarı")

    # ── Yardımcı özellikler ───────────────────────────────────

    @property
    def basarisiz(self) -> bool:
        return not self.basarili

    def __bool__(self) -> bool:
        return self.basarili


# ══════════════════════════════════════════════════════════════
# 5. AÇIK API — UI sayfaları için
# ══════════════════════════════════════════════════════════════

def exc_logla(konum: str, exc: Exception) -> None:
    """
    Exception'ı tam traceback ile log'a yazar (dialog göstermez).

        except Exception as e:
            exc_logla("SayfaAdi._metod", e)
            hata_goster(self, str(e))
    """
    tb = traceback.format_exc()
    logger.error(f"[{konum}] {type(exc).__name__}: {exc}\n{tb}")


def hata_goster(parent, mesaj: str, baslik: str = "Hata") -> None:
    """ERROR log + QMessageBox.critical."""
    logger.error(f"[UI Hata] {baslik}: {mesaj}")
    _msgbox_critical(parent, baslik, mesaj)


def uyari_goster(parent, mesaj: str, baslik: str = "Uyarı") -> None:
    """WARNING log + MesajKutusu.uyari."""
    logger.warning(f"[UI Uyarı] {baslik}: {mesaj}")
    _msgbox_warning(parent, baslik, mesaj)


def bilgi_goster(parent, mesaj: str, baslik: str = "Bilgi") -> None:
    """INFO log + MesajKutusu.bilgi."""
    logger.info(f"[UI Bilgi] {baslik}: {mesaj}")
    _msgbox_bilgi(parent, baslik, mesaj)


def hata_logla_goster(
    parent,
    konum: str,
    exc: Exception,
    baslik: str = "Hata",
    kullanici_mesaji: Optional[str] = None,
) -> None:
    """
    exc_logla (tam traceback) + hata_goster kombosu — tek satır:

        except Exception as e:
            hata_logla_goster(self, "SayfaAdi._metod", e)
    """
    exc_logla(konum, exc)
    gosterilecek = kullanici_mesaji or str(exc)
    _msgbox_critical(parent, baslik, gosterilecek)


# ══════════════════════════════════════════════════════════════
# 6. servis_calistir() — UI'da try/except bloğunu tek satıra indirir
# ══════════════════════════════════════════════════════════════


def soru_sor(parent, mesaj: str, baslik: str = "Onay") -> bool:
    """
    Evet/Hayır onay diyalogu gösterir. Evet → True döner.

    Kullanım:
        if soru_sor(self, "Silmek istiyor musunuz?"):
            ...
    """
    try:
        from PySide6.QtWidgets import QMessageBox
        cevap = QMessageBox.question(
            parent, baslik, mesaj,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return cevap == QMessageBox.StandardButton.Yes
    except Exception:
        return False


def servis_calistir(
    parent,
    konum: str,
    islem: Callable[[], T],
    basari_msg: str = "",
    hata_baslik: str = "Hata",
    basari_goster: bool = True,
    hata_goster_ui: bool = True,
) -> Optional[T]:
    """
    UI'daki tekrarlayan try/except/QMessageBox kalıbını tek satıra indirger.

    Parametreler:
        parent       : QWidget — mesaj kutularının ebeveyni
        konum        : "SayfaAdi._metod" — log için
        islem        : Çalıştırılacak lambda veya callable
        basari_msg   : Başarı durumunda gösterilecek mesaj (boşsa dialog yok)
        hata_baslik  : Hata dialog başlığı
        basari_goster: True → başarıda bilgi_goster() çağırır
        hata_goster_ui: True → hata durumunda hata_goster() çağırır

    Dönüş:
        İşlem başarılıysa sonucu, hata durumunda None döner.

    Kullanım:
        # Eski kalıp (7 satır):
        try:
            sonuc = svc.personel_ekle(veri)
            if sonuc:
                QMessageBox.information(self, "Bilgi", "Eklendi.")
            else:
                QMessageBox.critical(self, "Hata", "Eklenemedi.")
        except Exception as e:
            logger.error(f"PersonelEkle._kaydet: {e}")
            QMessageBox.critical(self, "Hata", str(e))

        # Yeni kalıp (3 satır):
        sonuc = servis_calistir(
            self, "PersonelEkle._kaydet",
            lambda: svc.personel_ekle(veri),
            basari_msg="Personel eklendi.",
        )
    """
    try:
        sonuc = islem()
        if basari_msg and basari_goster:
            bilgi_goster(parent, basari_msg)
        return sonuc
    except Exception as exc:
        exc_logla(konum, exc)
        if hata_goster_ui:
            _msgbox_critical(parent, hata_baslik, str(exc))
        return None


# ══════════════════════════════════════════════════════════════
# DAHİLİ YARDIMCILAR
# ══════════════════════════════════════════════════════════════

def _msgbox_critical(parent, baslik: str, mesaj: str) -> None:
    try:
        from ui.dialogs.mesaj_kutusu import MesajKutusu
        MesajKutusu.hata(parent, mesaj, baslik=baslik)
    except Exception:
        try:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(parent, baslik, mesaj)
        except Exception:
            pass


def _msgbox_warning(parent, baslik: str, mesaj: str) -> None:
    try:
        from ui.dialogs.mesaj_kutusu import MesajKutusu
        MesajKutusu.uyari(parent, mesaj, baslik=baslik)
    except Exception:
        try:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(parent, baslik, mesaj)
        except Exception:
            pass


def _msgbox_bilgi(parent, baslik: str, mesaj: str) -> None:
    try:
        from ui.dialogs.mesaj_kutusu import MesajKutusu
        MesajKutusu.bilgi(parent, mesaj, baslik=baslik)
    except Exception:
        try:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(parent, baslik, mesaj)
        except Exception:
            pass

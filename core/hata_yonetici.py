# -*- coding: utf-8 -*-
"""
core/hata_yonetici.py
══════════════════════════════════════════════════════════════
Merkezi hata yönetimi — 4 katman:

  1. qmessagebox_yakala()
     ─────────────────────
     PySide6.QtWidgets modülünde QMessageBox'ı log yazan bir
     alt sınıfla değiştirir. Sayfaların HİÇBİRİNİ değiştirmeden
     tüm .critical / .warning çağrıları loglara yansır.

     Sayfa modülleri lazy-import ile yüklendiğinden (main_window
     içindeki _create_page()), bu fonksiyon onlardan ÖNCE
     çağrılmalı — yani app oluşturulur oluşturulmaz.

  2. global_exception_hook_kur()
     ─────────────────────────────
     Ana iş parçacığındaki yakalanmayan Python istisnalarını
     sys.excepthook üzerinden loglar.

  3. threading_exception_hook_kur()
     ──────────────────────────────
     QThread / threading.Thread içindeki yakalanmayan istisnaları
     threading.excepthook üzerinden loglar.

  4. Açık API — yeni sayfalar için:
       exc_logla(konum, exc)
       hata_goster(parent, msg)
       uyari_goster(parent, msg)
       hata_logla_goster(parent, konum, exc)
       servis_calistir(parent, konum, lambda: ..., "Başarılı")
       soru_sor(parent, "Emin misiniz?")

Kullanım (main.pyw veya main.py):

    from core.hata_yonetici import (
        qmessagebox_yakala,
        global_exception_hook_kur,
        threading_exception_hook_kur,
    )

    app = QApplication(sys.argv)
    qmessagebox_yakala()            # <-- sayfa importlarından önce
    global_exception_hook_kur()
    threading_exception_hook_kur()
"""
import sys
import traceback
import threading
from typing import Any, Optional

from core.logger import logger


# ══════════════════════════════════════════════════════════════
#  1. QMessageBox LOG YAKALAYICI
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
                try:
                    from ui.dialogs.mesaj_kutusu import MesajKutusu
                    MesajKutusu.hata(parent, msg, baslik=title)
                except Exception:
                    pass
                return _Orj.critical(parent, title, msg, *args, **kwargs)

            @staticmethod
            def warning(parent, title, msg, *args, **kwargs):
                logger.warning(f"[UI ⚠️] {title}: {msg}")
                try:
                    from ui.dialogs.mesaj_kutusu import MesajKutusu
                    MesajKutusu.uyari(parent, msg, baslik=title)
                except Exception:
                    pass
                return _Orj.warning(parent, title, msg, *args, **kwargs)

            @staticmethod
            def information(parent, title, msg, *args, **kwargs):
                logger.info(f"[UI ℹ️] {title}: {msg}")
                try:
                    from ui.dialogs.mesaj_kutusu import MesajKutusu
                    MesajKutusu.bilgi(parent, msg, baslik=title)
                except Exception:
                    pass
                return _Orj.information(parent, title, msg, *args, **kwargs)

        _qw.QMessageBox = _LoggedQMessageBox
        logger.info("QMessageBox log yakalayıcısı aktif edildi.")

    except Exception as exc:
        logger.error(f"qmessagebox_yakala başarısız: {exc}")


# ══════════════════════════════════════════════════════════════
#  2. ANA İŞ PARÇACIĞI — sys.excepthook
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
#  3. THREAD İSTİSNALARI
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
#  4. AÇIK API
# ══════════════════════════════════════════════════════════════

def exc_logla(konum: str, exc: Exception) -> None:
    """
    Exception'ı tam traceback ile log'a yazar (dialog göstermez).

    Kullanım:
        except Exception as e:
            exc_logla("SayfaAdi._metod", e)
            hata_goster(self, str(e))
    """
    tb = traceback.format_exc()
    logger.error(f"[{konum}] {type(exc).__name__}: {exc}\n{tb}")


def hata_goster(parent, mesaj: str, baslik: str = "Hata") -> None:
    """
    ERROR seviyesinde log yaz + QMessageBox.critical göster.
    logger.error her koşulda çağrılır; qmessagebox_yakala() aktifse
    QMessageBox içinden de ayrıca log yazılır (INFO seviyesinde önce
    sıkıştırmak için buradan sadece bir kez logluyoruz).
    """
    logger.error(f"[UI Hata] {baslik}: {mesaj}")
    _msgbox_critical(parent, baslik, mesaj)


def uyari_goster(parent, mesaj: str, baslik: str = "Uyarı") -> None:
    """
    WARNING seviyesinde log yaz + MesajKutusu.uyari göster.
    """
    logger.warning(f"[UI Uyarı] {baslik}: {mesaj}")
    _msgbox_warning(parent, baslik, mesaj)


def bilgi_goster(parent, mesaj: str, baslik: str = "Bilgi") -> None:
    """
    INFO seviyesinde log yaz + MesajKutusu.bilgi göster.

    Kullanım:
        from core.hata_yonetici import bilgi_goster
        bilgi_goster(self, "Kayıt başarıyla eklendi.")
    """
    logger.info(f"[UI Bilgi] {baslik}: {mesaj}")
    try:
        from ui.dialogs.mesaj_kutusu import MesajKutusu
        MesajKutusu.bilgi(parent, mesaj, baslik=baslik)
    except Exception as _e:
        logger.debug(f"MesajKutusu gösterilemedi — {baslik}: {_e}")
        try:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(parent, baslik, mesaj)
        except Exception:
            pass


def hata_logla_goster(parent, konum: str, exc: Exception,
                       baslik: str = "Hata") -> None:
    """
    exc_logla (tam traceback) + hata_goster kombosu — tek satır:

        except Exception as e:
            hata_logla_goster(self, "SayfaAdi._metod", e)
    """
    exc_logla(konum, exc)
    _msgbox_critical(parent, baslik, str(exc))

def servis_calistir(parent, konum: str, service_call, basari_msg: str = ""):
    """
    Servis metodunu çalıştırır, başarı/hata durumlarını yönetir.
    UI'daki try/except bloklarını azaltır.

    Args:
        parent: QWidget ebeveyni (dialoglar için)
        konum: Hata loglaması için konum (örn: "SayfaAdi._metod")
        service_call: Çalıştırılacak servis fonksiyonu (lambda)
        basari_msg: Başarı durumunda gösterilecek mesaj. Boş ise gösterilmez.
    """
    try:
        sonuc = service_call()
        # Servis SonucYonetici döndürüyorsa
        if isinstance(sonuc, SonucYonetici):
            if sonuc.basarili:
                if basari_msg:
                    bilgi_goster(parent, basari_msg)
            else:
                hata_goster(parent, sonuc.mesaj)
        # Servis bool döndürüyorsa
        elif isinstance(sonuc, bool):
            if sonuc and basari_msg:
                bilgi_goster(parent, basari_msg)
            elif not sonuc:
                hata_goster(parent, f"{konum} işlemi başarısız oldu.")
        # Servis bir şey döndürmüyorsa (sadece exception fırlatır)
        else:
            if basari_msg:
                bilgi_goster(parent, basari_msg)
    except Exception as e:
        hata_logla_goster(parent, konum, e)

def soru_sor(parent, mesaj: str, baslik: str = "Onay") -> bool:
    """
    Kullanıcıya onay sorusu sorar (MesajKutusu.soru).

    Returns:
        bool: Evet ise True, Hayır ise False
    """
    try:
        from ui.dialogs.mesaj_kutusu import MesajKutusu
        return MesajKutusu.soru(parent, mesaj, baslik=baslik)
    except Exception as _e:
        logger.debug(f"MesajKutusu.soru gösterilemedi — {baslik}: {_e}")
        try:
            from PySide6.QtWidgets import QMessageBox
            yanit = QMessageBox.question(parent, baslik, mesaj, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            return yanit == QMessageBox.StandardButton.Yes
        except Exception:
            return False

# ── Dahili yardımcılar ────────────────────────────────────────

def _msgbox_critical(parent, baslik: str, mesaj: str) -> None:
    try:
        from ui.dialogs.mesaj_kutusu import MesajKutusu
        MesajKutusu.hata(parent, mesaj, baslik=baslik)
    except Exception as _e:
        logger.debug(f"MesajKutusu gösterilemedi — {baslik}: {_e}")
        try:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(parent, baslik, mesaj)
        except Exception:
            pass


def _msgbox_warning(parent, baslik: str, mesaj: str) -> None:
    try:
        from ui.dialogs.mesaj_kutusu import MesajKutusu
        MesajKutusu.uyari(parent, mesaj, baslik=baslik)
    except Exception as _e:
        logger.debug(f"MesajKutusu gösterilemedi — {baslik}: {_e}")
        try:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(parent, baslik, mesaj)
        except Exception:
            pass
class SonucYonetici:
    def __init__(self, basarili: bool, mesaj: str = "", data: Optional[Any] = None):
        self.basarili = basarili
        self.mesaj = mesaj
        self.data = data

    @staticmethod
    def tamam(mesaj: str = "", data: Optional[Any] = None):
        return SonucYonetici(True, mesaj, data)

    @staticmethod
    def hata(exc: Exception | str, konum: str = ""):
        import traceback
        msg = str(exc)
        if konum:
            msg = f"{konum}: {msg}"
        # Otomatik log
        logger.error(msg)
        logger.debug(traceback.format_exc())
        return SonucYonetici(False, msg)
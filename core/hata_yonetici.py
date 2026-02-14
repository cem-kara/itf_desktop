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
                return _Orj.critical(parent, title, msg, *args, **kwargs)

            @staticmethod
            def warning(parent, title, msg, *args, **kwargs):
                logger.warning(f"[UI ⚠️] {title}: {msg}")
                return _Orj.warning(parent, title, msg, *args, **kwargs)

            @staticmethod
            def information(parent, title, msg, *args, **kwargs):
                logger.info(f"[UI ℹ️] {title}: {msg}")
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
            traceback.format_exception(args.exc_type, args.exc_value, args.exc_tb)
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
    WARNING seviyesinde log yaz + QMessageBox.warning göster.
    """
    logger.warning(f"[UI Uyarı] {baslik}: {mesaj}")
    _msgbox_warning(parent, baslik, mesaj)


def hata_logla_goster(parent, konum: str, exc: Exception,
                       baslik: str = "Hata") -> None:
    """
    exc_logla (tam traceback) + hata_goster kombosu — tek satır:

        except Exception as e:
            hata_logla_goster(self, "SayfaAdi._metod", e)
    """
    exc_logla(konum, exc)
    _msgbox_critical(parent, baslik, str(exc))


# ── Dahili yardımcılar ────────────────────────────────────────

def _msgbox_critical(parent, baslik: str, mesaj: str) -> None:
    try:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(parent, baslik, mesaj)
    except Exception as _e:
        logger.debug(f"QMessageBox gösterilemedi — {baslik}: {_e}")


def _msgbox_warning(parent, baslik: str, mesaj: str) -> None:
    try:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(parent, baslik, mesaj)
    except Exception as _e:
        logger.debug(f"QMessageBox gösterilemedi — {baslik}: {_e}")

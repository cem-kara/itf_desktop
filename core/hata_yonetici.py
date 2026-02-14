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
#     PySide6'da sınıf attribute'una statik atama çalışmaz;
#     bunun yerine PySide6.QtWidgets.QMessageBox'ı log yazan bir
#     alt sınıfla DEĞİŞTİRİYORUZ.  Sayfalar lazy-import ile
#     'from PySide6.QtWidgets import QMessageBox' dediğinde
#     artık bu alt sınıfı alırlar.
# ══════════════════════════════════════════════════════════════

def qmessagebox_yakala() -> None:
    """
    QMessageBox.critical / .warning / .information çağrılarını
    otomatik olarak log dosyasına da yazar.

    Çalışma prensibi:
      • PySide6.QtWidgets modülündeki 'QMessageBox' adını,
        orijinalden türetilmiş _LoggedQMessageBox ile değiştiririz.
      • Sayfalar lazy-import ile 'from PySide6.QtWidgets import
        QMessageBox' dediğinde bu yeni sınıfı alırlar.
      • Orijinal sınıfı _critical_orijinal vs. olarak saklarız;
        böylece sonsuz döngü olmaz.
    """
    try:
        import PySide6.QtWidgets as _qw

        _Orj = _qw.QMessageBox   # Orijinal sınıfı koru

        class _LoggedQMessageBox(_Orj):
            """
            QMessageBox'ı saran log-aware sürüm.
            Tüm static metod çağrıları log yazdıktan sonra
            orijinal davranışa devredilir.
            """

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

        # Modül namespace'ini güncelle — lazy import'lar artık
        # _LoggedQMessageBox'ı alır.
        _qw.QMessageBox = _LoggedQMessageBox

        logger.info("QMessageBox log yakalayıcısı aktif edildi.")

    except Exception as exc:
        # Yakalayıcı kurulamazsa uygulama çalışmaya devam etmeli
        logger.error(f"qmessagebox_yakala başarısız: {exc}")


# ══════════════════════════════════════════════════════════════
#  2. ANA İŞ PARÇACIĞI — sys.excepthook
# ══════════════════════════════════════════════════════════════

def global_exception_hook_kur() -> None:
    """
    Ana iş parçacığındaki yakalanmayan her Python istisnasını
    CRITICAL seviyesinde log dosyasına yazar.
    """

    def _hook(exc_type, exc_value, exc_tb):
        # KeyboardInterrupt'ı normal çıkış olarak işle — loglamaya gerek yok
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
        # Konsola da yazdır
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook
    logger.info("Global exception hook kuruldu.")


# ══════════════════════════════════════════════════════════════
#  3. THREAD İSTİSNALARI — threading.excepthook + QThread
# ══════════════════════════════════════════════════════════════

def threading_exception_hook_kur() -> None:
    """
    threading.Thread ve QThread içindeki yakalanmayan istisnaları
    ERROR seviyesinde loglar.

    Python 3.8+ threading.excepthook:
      QThread.run() içindeki try/except bloğu dışına çıkan
      her istisna buraya düşer.
    """

    def _thread_hook(args: threading.ExceptHookArgs) -> None:
        # SystemExit'i loglamaya gerek yok
        if args.exc_type is SystemExit:
            return

        tb_str = "".join(
            traceback.format_exception(
                args.exc_type, args.exc_value, args.exc_tb
            )
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
#  4. AÇIK API — Yeni sayfalar için önerilen kullanım
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
    qmessagebox_yakala() aktifken çift loglama olmaz çünkü
    _LoggedQMessageBox.critical zaten log yazar; burada ek log eklenmez.
    """
    # Loglama: qmessagebox_yakala aktif değilse manuel logla
    _msgbox_critical(parent, baslik, mesaj)


def uyari_goster(parent, mesaj: str, baslik: str = "Uyarı") -> None:
    """
    WARNING seviyesinde log yaz + QMessageBox.warning göster.
    """
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
    except Exception:
        logger.error(f"QMessageBox gösterilemedi — {baslik}: {mesaj}")


def _msgbox_warning(parent, baslik: str, mesaj: str) -> None:
    try:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(parent, baslik, mesaj)
    except Exception:
        logger.warning(f"QMessageBox gösterilemedi — {baslik}: {mesaj}")

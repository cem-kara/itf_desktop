# -*- coding: utf-8 -*-
"""
ui/dialogs/mesaj_kutusu.py
══════════════════════════════════════════════════════════════
Merkezi mesaj kutusu — native QMessageBox yerine kullanılır.

NEDEN:
  QMessageBox Windows sistem temasını kullanır. Sistem teması
  light olan bilgisayarlarda dark uygulamamızın içinde buton
  yazıları arka planla aynı renk olabiliyor (okunaksız).
  Bu sınıf tamamen kendi stilimizle çalışır — temadan bağımsız.

KULLANIM:
from ui.dialogs.mesaj_kutusu import MesajKutusu

  MesajKutusu.bilgi(parent, "Kayıt başarıyla eklendi.")
  MesajKutusu.uyari(parent, "Bu alan boş olamaz.")
  MesajKutusu.hata(parent, "Bağlantı kurulamadı.")
  onay = MesajKutusu.soru(parent, "Kaydı silmek istiyor musunuz?")
  if onay:
      ...

  # Başlık özelleştirme:
  MesajKutusu.bilgi(parent, "İşlem tamamlandı.", baslik="Sync")

qmessagebox_yakala() bu sınıfı otomatik olarak QMessageBox yerine
bağlar — mevcut QMessageBox.information/warning/critical çağrıları
değiştirilmeden bu dialogu açar.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QSizePolicy, QMessageBox,
    QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from ui.styles.icons import Icons, IconColors


# ══════════════════════════════════════════════════════════════
#  Tema sabitleri — DarkTheme import kalmadan yazıldı
#  Böylece tema yüklenemese bile dialog çalışır.
# ══════════════════════════════════════════════════════════════

def _theme_colors() -> dict:
    """Aktif tema renklerini döner; hata olursa dark fallback kullanır."""
    # Tema yüklenemese bile çalışacak şekilde sabit hex kodları döndürülüyor
    return {
        "bg":        "#0d1117",
        "bg2":       "#161b22",
        "border":    "#1e2d3d",
        "text":      "#e8edf5",
        "text_muted": "#8b8fa3",
        "success":   "#2ec98e",
        "warning":   "#e8a030",
        "error":     "#e85555",
        "accent":    "#3d8ef5",
    }


# ══════════════════════════════════════════════════════════════
#  Dialog türleri
# ══════════════════════════════════════════════════════════════

class _Tur:
    BILGI  = "bilgi"
    UYARI  = "uyari"
    HATA   = "hata"
    SORU   = "soru"


_TUR_META = {
    _Tur.BILGI: {
        "ikon":       "check_circle",
        "ikon_renk":  IconColors.SUCCESS,
        "sol_renk":   "#2ec98e",
        "baslik":     "Bilgi",
    },
    _Tur.UYARI: {
        "ikon":       "alert_triangle",
        "ikon_renk":  IconColors.WARNING,
        "sol_renk":   "#e8a030",
        "baslik":     "Uyarı",
    },
    _Tur.HATA: {
        "ikon":       "x_circle",
        "ikon_renk":  IconColors.DANGER,
        "sol_renk":   "#e85555",
        "baslik":     "Hata",
    },
    _Tur.SORU: {
        "ikon":       "info",
        "ikon_renk":  IconColors.PRIMARY,
        "sol_renk":   "#3d8ef5",
        "baslik":     "Onay",
    },
}


# ══════════════════════════════════════════════════════════════
#  _MesajDialog — tek iç sınıf, tüm türler buradan
# ══════════════════════════════════════════════════════════════

class _MesajDialog(QDialog):

    def __init__(
        self,
        parent,
        tur: str,
        mesaj: str,
        baslik: str | None = None,
    ):
        super().__init__(parent)
        self._tur   = tur
        self._mesaj = mesaj
        self._meta  = _TUR_META[tur]
        self._baslik = baslik or self._meta["baslik"]
        self._c     = _theme_colors()
        self._onaylandi = False

        self.setWindowTitle(self._baslik)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setMinimumWidth(380)
        self.setMaximumWidth(560)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        self._build_ui()
        self._apply_style()

    # ── İnşa ───────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(0)

        card = QFrame()
        card.setObjectName("mk_card")
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 190))
        card.setGraphicsEffect(shadow)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # Üst şerit: renkli sol bar + ikon + başlık
        header = QFrame()
        header.setObjectName("mk_header")
        header.setFixedHeight(60)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 18, 0)
        h_layout.setSpacing(10)

        # Renkli sol bar
        sol_bar = QFrame()
        sol_bar.setObjectName("mk_sol_bar")
        sol_bar.setFixedWidth(5)
        h_layout.addWidget(sol_bar)

        # İkon
        ikon_lbl = QLabel()
        ikon_lbl.setObjectName("mk_ikon")
        ikon_lbl.setFixedSize(34, 34)
        ikon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        try:
            pm = Icons.pixmap(
                self._meta["ikon"],
                size=22,
                color=self._meta["ikon_renk"],
            )
            ikon_lbl.setPixmap(pm)
        except Exception:
            pass
        h_layout.addWidget(ikon_lbl)

        # Başlık
        baslik_lbl = QLabel(self._baslik)
        baslik_lbl.setObjectName("mk_baslik")
        h_layout.addWidget(baslik_lbl, 1)

        card_layout.addWidget(header)

        # Mesaj alanı
        icerik = QFrame()
        icerik.setObjectName("mk_icerik")
        i_layout = QVBoxLayout(icerik)
        i_layout.setContentsMargins(22, 18, 22, 18)

        mesaj_lbl = QLabel(self._mesaj)
        mesaj_lbl.setObjectName("mk_mesaj")
        mesaj_lbl.setWordWrap(True)
        mesaj_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        i_layout.addWidget(mesaj_lbl)
        card_layout.addWidget(icerik)

        # Buton alanı
        buton_frame = QFrame()
        buton_frame.setObjectName("mk_buton_frame")
        b_layout = QHBoxLayout(buton_frame)
        b_layout.setContentsMargins(16, 12, 16, 14)
        b_layout.setSpacing(10)
        b_layout.addStretch()

        if self._tur == _Tur.SORU:
            btn_hayir = QPushButton("Hayır")
            btn_hayir.setObjectName("mk_btn_secondary")
            btn_hayir.setFixedHeight(36)
            btn_hayir.setMinimumWidth(86)
            btn_hayir.clicked.connect(self.reject)
            b_layout.addWidget(btn_hayir)

            btn_evet = QPushButton("Evet")
            btn_evet.setObjectName("mk_btn_primary")
            btn_evet.setFixedHeight(36)
            btn_evet.setMinimumWidth(86)
            btn_evet.clicked.connect(self._on_evet)
            btn_evet.setDefault(True)
            b_layout.addWidget(btn_evet)
        else:
            btn_tamam = QPushButton("Tamam")
            btn_tamam.setObjectName("mk_btn_primary")
            btn_tamam.setFixedHeight(36)
            btn_tamam.setMinimumWidth(86)
            btn_tamam.clicked.connect(self.accept)
            btn_tamam.setDefault(True)
            b_layout.addWidget(btn_tamam)

        card_layout.addWidget(buton_frame)
        root.addWidget(card)

    def _on_evet(self):
        self._onaylandi = True
        self.accept()

    # ── Stil ───────────────────────────────────────────────────

    def _apply_style(self):
        c     = self._c
        sol   = self._meta["sol_renk"]
        ikon  = self._meta["ikon_renk"]

        self.setStyleSheet("""
            QDialog {{
                background-color: rgba(5, 10, 18, 190);
            }}

            QFrame#mk_card {{
                background-color: {};
                border: 2px solid {};
                border-radius: 16px;
            }}

            /* Başlık şeridi */
            QFrame#mk_header {{
                background-color: {};
                border-bottom: 1px solid {};
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
            }}
            QFrame#mk_sol_bar {{
                background-color: {};
                border: none;
            }}
            QLabel#mk_ikon {{
                background-color: {};
                border: 1px solid {};
                border-radius: 17px;
                padding: 0px;
            }}
            QLabel#mk_baslik {{
                font-size: 14px;
                font-weight: 700;
                color: {};
                background: transparent;
                padding-left: 2px;
            }}

            /* Mesaj alanı */
            QFrame#mk_icerik {{
                background-color: transparent;
            }}
            QLabel#mk_mesaj {{
                font-size: 13px;
                color: {};
                background: transparent;
            }}

            /* Buton alanı */
            QFrame#mk_buton_frame {{
                background-color: {};
                border-top: 1px solid {};
                border-bottom-left-radius: 16px;
                border-bottom-right-radius: 16px;
            }}

            /* Tamam / Evet butonu */
            QPushButton#mk_btn_primary {{
                background-color: {};
                color: #ffffff;
                border: none;
                border-radius: 7px;
                font-size: 13px;
                font-weight: 600;
                padding: 0 20px;
            }}
            QPushButton#mk_btn_primary:hover {{
                background-color: {}cc;
            }}
            QPushButton#mk_btn_primary:pressed {{
                background-color: {}99;
            }}

            /* Hayır / İptal butonu */
            QPushButton#mk_btn_secondary {{
                background-color: transparent;
                color: {};
                border: 1px solid {};
                border-radius: 7px;
                font-size: 13px;
                font-weight: 500;
                padding: 0 20px;
            }}
            QPushButton#mk_btn_secondary:hover {{
                background-color: {};
                color: {};
            }}
            QPushButton#mk_btn_secondary:pressed {{
                background-color: {};
            }}
        """.format(
            c['bg2'], c['border'],
            c['bg2'], c['border'],
            sol,
            c['bg'], ikon,
            c['text'],
            c['text'],
            c['bg2'], c['border'],
            sol, sol, sol,
            c['text_muted'], c['border'],
            c['border'], c['text'],
            c['bg']
        ))

    # ── Sonuç ──────────────────────────────────────────────────

    @property
    def onaylandi(self) -> bool:
        return self._onaylandi


# ══════════════════════════════════════════════════════════════
#  Dışa açık API
# ══════════════════════════════════════════════════════════════

class MesajKutusu:
    """
    Statik yardımcı — doğrudan örnekleme gerekmez.

    MesajKutusu.bilgi(parent, "Kayıt eklendi.")
    MesajKutusu.uyari(parent, "Alan boş!")
    MesajKutusu.hata(parent, "Bağlantı hatası.")
    if MesajKutusu.soru(parent, "Silmek istiyor musunuz?"):
        ...
    """

    @staticmethod
    def bilgi(parent, mesaj: str, baslik: str = "Bilgi") -> None:
        d = _MesajDialog(parent, _Tur.BILGI, mesaj, baslik)
        d.exec()

    @staticmethod
    def uyari(parent, mesaj: str, baslik: str = "Uyarı") -> None:
        d = _MesajDialog(parent, _Tur.UYARI, mesaj, baslik)
        d.exec()

    @staticmethod
    def hata(parent, mesaj: str, baslik: str = "Hata") -> None:
        d = _MesajDialog(parent, _Tur.HATA, mesaj, baslik)
        d.exec()

    @staticmethod
    def soru(parent, mesaj: str, baslik: str = "Onay") -> bool:
        """True → Evet, False → Hayır / kapatma"""
        d = _MesajDialog(parent, _Tur.SORU, mesaj, baslik)
        d.exec()
        return d.onaylandi


_QMESSAGEBOX_PATCHED = False


def qmessagebox_yakala() -> None:
    """QMessageBox çağrılarını MesajKutusu'na yönlendirir."""
    global _QMESSAGEBOX_PATCHED
    if _QMESSAGEBOX_PATCHED:
        return

    def _information(parent, title, text, *args, **kwargs):
        MesajKutusu.bilgi(parent, str(text), baslik=str(title) if title else "Bilgi")
        return QMessageBox.StandardButton.Ok

    def _warning(parent, title, text, *args, **kwargs):
        MesajKutusu.uyari(parent, str(text), baslik=str(title) if title else "Uyarı")
        return QMessageBox.StandardButton.Ok

    def _critical(parent, title, text, *args, **kwargs):
        MesajKutusu.hata(parent, str(text), baslik=str(title) if title else "Hata")
        return QMessageBox.StandardButton.Ok

    def _question(
        parent,
        title,
        text,
        buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        defaultButton=QMessageBox.StandardButton.No,
        *args,
        **kwargs,
    ):
        del buttons, defaultButton, args, kwargs
        onay = MesajKutusu.soru(parent, str(text), baslik=str(title) if title else "Onay")
        return QMessageBox.StandardButton.Yes if onay else QMessageBox.StandardButton.No

    QMessageBox.information = staticmethod(_information)
    QMessageBox.warning = staticmethod(_warning)
    QMessageBox.critical = staticmethod(_critical)
    QMessageBox.question = staticmethod(_question)
    _QMESSAGEBOX_PATCHED = True

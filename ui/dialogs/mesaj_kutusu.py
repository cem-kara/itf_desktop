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
    QLabel, QPushButton, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ui.styles.icons import Icons, IconColors


# ══════════════════════════════════════════════════════════════
#  Tema sabitleri — DarkTheme import kalmadan yazıldı
#  Böylece tema yüklenemese bile dialog çalışır.
# ══════════════════════════════════════════════════════════════

def _theme_colors() -> dict:
    """Aktif tema renklerini döner; hata olursa dark fallback kullanır."""
    try:
        from ui.styles.colors import DarkTheme as C
        return {
            "bg":        C.BG_PRIMARY,
            "bg2":       C.BG_SECONDARY,
            "border":    C.BORDER_PRIMARY,
            "text":      C.TEXT_PRIMARY,
            "text_muted": C.TEXT_MUTED,
            "success":   C.STATUS_SUCCESS,
            "warning":   C.STATUS_WARNING,
            "error":     C.STATUS_ERROR,
            "accent":    C.ACCENT,
        }
    except Exception:
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
            Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumWidth(380)
        self.setMaximumWidth(560)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        self._build_ui()
        self._apply_style()

    # ── İnşa ───────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Üst şerit: renkli sol bar + ikon + başlık
        header = QFrame()
        header.setObjectName("mk_header")
        header.setFixedHeight(56)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 16, 0)
        h_layout.setSpacing(0)

        # Renkli sol bar
        sol_bar = QFrame()
        sol_bar.setObjectName("mk_sol_bar")
        sol_bar.setFixedWidth(5)
        h_layout.addWidget(sol_bar)

        # İkon
        ikon_lbl = QLabel()
        ikon_lbl.setObjectName("mk_ikon")
        ikon_lbl.setFixedSize(44, 44)
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

        root.addWidget(header)

        # Mesaj alanı
        icerik = QFrame()
        icerik.setObjectName("mk_icerik")
        i_layout = QVBoxLayout(icerik)
        i_layout.setContentsMargins(20, 16, 20, 16)

        mesaj_lbl = QLabel(self._mesaj)
        mesaj_lbl.setObjectName("mk_mesaj")
        mesaj_lbl.setWordWrap(True)
        mesaj_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        i_layout.addWidget(mesaj_lbl)
        root.addWidget(icerik)

        # Buton alanı
        buton_frame = QFrame()
        buton_frame.setObjectName("mk_buton_frame")
        b_layout = QHBoxLayout(buton_frame)
        b_layout.setContentsMargins(16, 10, 16, 14)
        b_layout.setSpacing(8)
        b_layout.addStretch()

        if self._tur == _Tur.SORU:
            btn_hayir = QPushButton("Hayır")
            btn_hayir.setObjectName("mk_btn_secondary")
            btn_hayir.setFixedHeight(34)
            btn_hayir.setMinimumWidth(80)
            btn_hayir.clicked.connect(self.reject)
            b_layout.addWidget(btn_hayir)

            btn_evet = QPushButton("Evet")
            btn_evet.setObjectName("mk_btn_primary")
            btn_evet.setFixedHeight(34)
            btn_evet.setMinimumWidth(80)
            btn_evet.clicked.connect(self._on_evet)
            btn_evet.setDefault(True)
            b_layout.addWidget(btn_evet)
        else:
            btn_tamam = QPushButton("Tamam")
            btn_tamam.setObjectName("mk_btn_primary")
            btn_tamam.setFixedHeight(34)
            btn_tamam.setMinimumWidth(80)
            btn_tamam.clicked.connect(self.accept)
            btn_tamam.setDefault(True)
            b_layout.addWidget(btn_tamam)

        root.addWidget(buton_frame)

    def _on_evet(self):
        self._onaylandi = True
        self.accept()

    # ── Stil ───────────────────────────────────────────────────

    def _apply_style(self):
        c     = self._c
        sol   = self._meta["sol_renk"]
        ikon  = self._meta["ikon_renk"]

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {c['bg']};
            }}

            /* Başlık şeridi */
            QFrame#mk_header {{
                background-color: {c['bg2']};
                border-bottom: 1px solid {c['border']};
            }}
            QFrame#mk_sol_bar {{
                background-color: {sol};
                border: none;
            }}
            QLabel#mk_ikon {{
                background: transparent;
                padding: 0px;
            }}
            QLabel#mk_baslik {{
                font-size: 13px;
                font-weight: 700;
                color: {c['text']};
                background: transparent;
                padding-left: 4px;
            }}

            /* Mesaj alanı */
            QFrame#mk_icerik {{
                background-color: {c['bg']};
            }}
            QLabel#mk_mesaj {{
                font-size: 13px;
                color: {c['text']};
                background: transparent;
                line-height: 1.5;
            }}

            /* Buton alanı */
            QFrame#mk_buton_frame {{
                background-color: {c['bg2']};
                border-top: 1px solid {c['border']};
            }}

            /* Tamam / Evet butonu */
            QPushButton#mk_btn_primary {{
                background-color: {sol};
                color: #ffffff;
                border: none;
                border-radius: 5px;
                font-size: 13px;
                font-weight: 600;
                padding: 0 18px;
            }}
            QPushButton#mk_btn_primary:hover {{
                background-color: {sol}cc;
            }}
            QPushButton#mk_btn_primary:pressed {{
                background-color: {sol}99;
            }}

            /* Hayır / İptal butonu */
            QPushButton#mk_btn_secondary {{
                background-color: transparent;
                color: {c['text_muted']};
                border: 1px solid {c['border']};
                border-radius: 5px;
                font-size: 13px;
                font-weight: 500;
                padding: 0 18px;
            }}
            QPushButton#mk_btn_secondary:hover {{
                background-color: {c['border']};
                color: {c['text']};
            }}
            QPushButton#mk_btn_secondary:pressed {{
                background-color: {c['bg']};
            }}
        """)

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

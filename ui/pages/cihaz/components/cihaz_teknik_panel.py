# -*- coding: utf-8 -*-
"""
Cihaz Teknik Panel
─────────────────────────────────────
Teknik Bilgiler sekmesi icin cihaz teknik verilerini gosterir.
v2 tablo temasi + 2-cift-per-row duzeni, duzgun hizalama.
"""
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QSizePolicy, QGridLayout
)
from PySide6.QtCore import Qt, Signal

from ui.styles import DarkTheme
from ui.styles.components import STYLES as S
from core.logger import logger
from database.repository_registry import RepositoryRegistry

C = DarkTheme

# ── Renk sabitleri ─────────────────────────────────────────────────────────────
_ACCENT     = getattr(C, "ACCENT",         "#4d9de0")
_BORDER     = getattr(C, "BORDER_PRIMARY", "#2d3f55")
_TEXT_PRI   = getattr(C, "TEXT_PRIMARY",   "#dce8f5")
_TEXT_SEC   = getattr(C, "TEXT_SECONDARY", "#7a93ad")
_BG_SECT    = "rgba(255,255,255,0.03)"
_BG_HDR     = "rgba(77,157,224,0.18)"
_BG_SUBHDR  = "rgba(77,157,224,0.09)"
_BG_EVEN    = "transparent"
_BG_ODD     = "rgba(255,255,255,0.04)"
_BORDER_CSS = f"1px solid {_BORDER}"

# ── Stil sabitler ──────────────────────────────────────────────────────────────
_HDR_CSS = (
    f"background: {_BG_HDR};"
    f" color: {_ACCENT};"
    " font-size: 12px; font-weight: 700; letter-spacing: 0.5px;"
    f" border-bottom: {_BORDER_CSS};"
    " padding: 7px 14px;"
)
_SUBHDR_CSS = (
    f"background: {_BG_SUBHDR};"
    f" color: {_ACCENT};"
    " font-size: 11px; font-weight: 600; font-style: italic;"
    f" border-top: {_BORDER_CSS}; border-bottom: {_BORDER_CSS};"
    " padding: 4px 14px;"
)
_LBL_CSS = (
    f"color: {_TEXT_SEC};"
    " font-size: 11px; font-weight: 600;"
    " padding: 7px 14px 2px 14px;"
)
_VAL_CSS = (
    f"color: {_TEXT_PRI};"
    " font-size: 12px; font-weight: 400;"
    " padding: 2px 14px 7px 14px;"
)
_VAL_LINK_CSS = (
    f"color: {_ACCENT};"
    " font-size: 12px; font-weight: 400;"
    " padding: 2px 14px 7px 14px;"
)


def _make_pair_widget(lbl_text: str, val_widget: QLabel, bg: str) -> QWidget:
    """
    Bir etiket-deger cifti icin dikey widget olusturur.
    Ust: kucuk etiket | Alt: deger.
    """
    w = QWidget()
    w.setStyleSheet(f"background: {bg};")
    w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

    vbox = QVBoxLayout(w)
    vbox.setContentsMargins(0, 0, 0, 0)
    vbox.setSpacing(0)

    lbl = QLabel(lbl_text)
    lbl.setStyleSheet(_LBL_CSS + f" background: {bg};")
    lbl.setWordWrap(True)
    lbl.setAlignment(Qt.AlignLeft | Qt.AlignBottom)

    val_widget.setStyleSheet(val_widget.styleSheet() + f" background: {bg};")
    val_widget.setWordWrap(True)
    val_widget.setAlignment(Qt.AlignLeft | Qt.AlignTop)

    vbox.addWidget(lbl)
    vbox.addWidget(val_widget)
    return w


class _TableSection(QWidget):
    """
    Tam genislikte, kenarlıklı bolum widget'i.

    Her mantiksal satir:
        [ sol-cift ] | dikey ayirici | [ sag-cift ]

    Hizalama: 3 sutunlu QGridLayout (sol | sep | sag).
    Zebra: cift/tek satir arkaplan.
    """

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self._logical_row = 0   # mevcut mantiksal satir (zebra icin)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Dis cerceve
        self._frame = QFrame()
        self._frame.setStyleSheet(
            f"QFrame {{ border: {_BORDER_CSS}; border-radius: 4px;"
            f" background: {_BG_SECT}; }}"
        )
        self._vbox = QVBoxLayout(self._frame)
        self._vbox.setContentsMargins(0, 0, 0, 0)
        self._vbox.setSpacing(0)

        # Bolum baslik satiri
        hdr = QLabel(title)
        hdr.setStyleSheet(_HDR_CSS)
        hdr.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._vbox.addWidget(hdr)

        outer.addWidget(self._frame)

    # ── Yardimcilar ───────────────────────────────────────────────────────────

    def add_subheader(self, title: str):
        """Alt-bolum baslik (Sterilite Bilgisi, Raf Omru vb.)."""
        sub = QLabel(title)
        sub.setStyleSheet(_SUBHDR_CSS)
        sub.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._vbox.addWidget(sub)
        self._logical_row = 0   # zebra sifirla

    def add_row(self,
                lbl1: str, val1: QLabel,
                lbl2: str = "", val2: QLabel = None):
        """
        Bir mantiksal satir ekler.
        Sol: lbl1/val1   Sag: lbl2/val2 (opsiyonel).
        Zebra arkaplan otomatik uygulanir.
        """
        bg = _BG_ODD if (self._logical_row % 2 != 0) else _BG_EVEN
        self._logical_row += 1

        # Satir container
        row_w = QWidget()
        row_w.setStyleSheet(
            f"background: {bg}; border-bottom: {_BORDER_CSS};"
        )
        row_w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        row_h = QHBoxLayout(row_w)
        row_h.setContentsMargins(0, 0, 0, 0)
        row_h.setSpacing(0)

        # Sol cift
        left_w = _make_pair_widget(lbl1, val1, bg)
        row_h.addWidget(left_w, stretch=1)

        # Dikey ayirici
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFixedWidth(1)
        sep.setStyleSheet(f"background: {_BORDER}; border: none;")
        row_h.addWidget(sep)

        # Sag cift
        if lbl2 and val2 is not None:
            right_w = _make_pair_widget(lbl2, val2, bg)
        else:
            # Bos sag taraf — simetri icin
            right_w = QWidget()
            right_w.setStyleSheet(f"background: {bg};")
            right_w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        row_h.addWidget(right_w, stretch=1)

        self._vbox.addWidget(row_w)


# ──────────────────────────────────────────────────────────────────────────────

class CihazTeknikPanel(QWidget):
    """
    Cihaz Merkez ekranindaki 'Teknik Bilgiler' sekmesi icerigi.
    """
    saved = Signal()

    def __init__(self, cihaz_id, db=None, parent=None):
        super().__init__(parent)
        self.db           = db
        self.cihaz_id     = str(cihaz_id) if cihaz_id is not None else ""
        self.teknik_data  = {}
        self._widgets     = {}
        self._link_fields = set()

        self._setup_ui()
        self._load_data()

    # ──────────────────────────────────────────────────────────────────────────
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(S.get("scroll", ""))

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        root = QVBoxLayout(content)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # ── 1. Tanimlayici Bilgiler ───────────────────────────────────────────
        s1 = _TableSection("Tanimlayici Bilgiler")
        s1.add_row("Cihaz ID",            self._w("Cihazid"),
                   "Urun Tanimi",         self._w("UrunTanimi"))
        s1.add_row("Birincil Urun No",    self._w("BirincilUrunNumarasi"),
                   "Firma",               self._w("Firma"))
        s1.add_row("Marka",               self._w("Marka"),
                   "Urun Adi",            self._w("UrunAdi"))
        s1.add_row("Urun Kunyesi",        self._w("UrunKunye"),
                   "Turkce Etiket",       self._w("TurkceEtiket"))
        s1.add_row("Orijinal Etiket",     self._w("OrijinalEtiket"),
                   "Versiyon/Model",      self._w("VersiyonModel"))
        s1.add_row("Referans/Katalog No", self._w("ReferansKatalogNo"),
                   "Urun Sayisi",         self._w("UrunSayisi"))
        s1.add_row("Urun Aciklamasi",     self._w("UrunAciklamasi"))
        root.addWidget(s1)

        # ── 2. Ithal/Imal Bilgileri ───────────────────────────────────────────
        s2 = _TableSection("Ithal/Imal Bilgileri")
        s2.add_row("Ithal/Imal Bilgisi",        self._w("IthalImalBilgisi"),
                   "Mensei Ulke",               self._w("MenseiUlke"))
        s2.add_row("Ithal Edilen Ulke",         self._w("IthalEdilenUlke"),
                   "Yerli Mali Belgesi Var mi", self._w("YerliMaliBelgesiVarMi"))
        root.addWidget(s2)

        # ── 3. Ozellikler ─────────────────────────────────────────────────────
        s3 = _TableSection("Ozellikler")

        s3.add_subheader("Sterilite Bilgisi")
        s3.add_row("Steril Paketlendi mi",
                   self._w("SterilPaketlendiMi"),
                   "Kullanim Oncesi Sterilizasyon Gerekli mi",
                   self._w("KullanimOncesiSterilizasyonGerekliMi"))

        s3.add_subheader("Kullanimlik Bilgisi")
        s3.add_row("Tek Kullanimlik mi",             self._w("TekKullanimlikMi"),
                   "Sinirli Kullanim Sayisi Var mi", self._w("SinirliKullanimSayisiVarMi"))
        s3.add_row("Tek Hasta Kullanim mi",          self._w("TekHastaKullanimMi"))

        s3.add_subheader("Raf Omru Bilgisi")
        s3.add_row("Raf Omru Var mi", self._w("RafOmruVarMi"))

        s3.add_subheader("Kalibrasyon ve Bakim")
        s3.add_row("Kalibrasyona Tabi mi",      self._w("KalibrasyonaTabiMi"),
                   "Kalibrasyon Periyodu (Ay)", self._w("KalibrasyonPeriyoduAy"))
        s3.add_row("Bakima Tabi mi",            self._w("BakimaTabiMi"),
                   "Bakim Periyodu (Ay)",       self._w("BakimPeriyoduAy"))

        s3.add_subheader("Diger Urun Ozellikleri")
        s3.add_row("MRG Guvenlik Bilgisi",         self._w("MRGGuvenlikBilgisi"),
                   "Lateks Iceriyor mu",            self._w("LateksIceriyorMu"))
        s3.add_row("Ftalat/DEHP Iceriyor mu",      self._w("FtalatDEHPIceriyorMu"),
                   "Iyonize Radyasyon Icerir mi",   self._w("IyonizeRadyasyonIcerirMi"))
        s3.add_row("Nanomateryal Iceriyor mu",      self._w("NanomateryalIceriyorMu"),
                   "Vucuda Implante Edilebilir mi",  self._w("ImplanteEdilebilirMi"))
        s3.add_row("Bilesen/Aksesuar mi",           self._w("BilesenAksesuarMi"),
                   "Ek-3 Kapsaminda mi",            self._w("Ek3KapsamindaMi"))
        s3.add_row("Ekstra Bilgi Linki",            self._w("EkstraBilgiLinki", is_link=True))
        root.addWidget(s3)

        # ── 4. Urun Belgeleri ve Gorseller ───────────────────────────────────
        s4 = _TableSection("Urun Belgeleri ve Gorseller")
        s4.add_row("Urun Belgeleri",      self._w("UrunBelgeleri",     is_link=True))
        s4.add_row("Urun Gorsel Dosyasi", self._w("UrunGorselDosyasi", is_link=True))
        root.addWidget(s4)

        root.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    # ──────────────────────────────────────────────────────────────────────────
    def _w(self, key: str, is_link=False) -> QLabel:
        """Deger QLabel olustur ve kaydet."""
        val = QLabel("")
        val.setTextInteractionFlags(Qt.TextSelectableByMouse)
        val.setWordWrap(True)
        val.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        if is_link:
            val.setOpenExternalLinks(True)
            val.setTextFormat(Qt.RichText)
            val.setStyleSheet(_VAL_LINK_CSS)
            self._link_fields.add(key)
        else:
            val.setStyleSheet(_VAL_CSS)
        self._widgets[key] = val
        return val

    # ──────────────────────────────────────────────────────────────────────────
    def _load_data(self):
        if self.db and self.cihaz_id:
            try:
                registry    = RepositoryRegistry(self.db)
                teknik_repo = registry.get("Cihaz_Teknik")
                teknik      = teknik_repo.get_by_id(self.cihaz_id)
                self.teknik_data = teknik if teknik else {"Cihazid": self.cihaz_id}
            except Exception as e:
                logger.error(f"Teknik veri yukleme hatasi: {e}")
                self.teknik_data = {"Cihazid": self.cihaz_id}

        for key, widget in self._widgets.items():
            raw = self.teknik_data.get(key, "")
            if key in self._link_fields and raw:
                try:
                    uri = Path(str(raw)).expanduser().resolve().as_uri()
                    widget.setText(
                        f'<a href="{uri}" style="color:{_ACCENT};">{raw}</a>'
                    )
                except Exception:
                    widget.setText(str(raw))
            else:
                widget.setText(str(raw) if raw else "—")

    def load_data(self):
        self._load_data()

    def set_embedded_mode(self, embedded: bool):
        pass

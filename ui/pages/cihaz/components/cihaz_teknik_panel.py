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

    Hizalama: 4-sutunlu QGridLayout (Label1 | Value1 | Label2 | Value2).
    Zebra: cift/tek satir arkaplan.
    """

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self._physical_row = 0   # Fiziksel satir sayisi

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
        self._physical_row = 0   # Sifirla

    def add_row(self,
                lbl1: str, val1: QLabel,
                lbl2: str = "", val2: QLabel = None):
        """
        4-sutunlu bir satir ekler: Label1 | Value1 | Label2 | Value2.
        Zebra arkaplan otomatik uygulanir.
        """
        bg = _BG_ODD if (self._physical_row % 2 != 0) else _BG_EVEN
        self._physical_row += 1

        # Satir container ve grid layout
        row_w = QWidget()
        row_w.setStyleSheet(
            f"background: {bg}; border-bottom: {_BORDER_CSS};"
        )
        row_w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        grid = QGridLayout(row_w)
        grid.setContentsMargins(8, 6, 8, 6)  # Iç padding
        grid.setSpacing(12)  # Label-Value arası
        grid.setColumnStretch(0, 0)  # Label1 — sabit
        grid.setColumnStretch(1, 1)  # Value1 — genişlesin
        grid.setColumnStretch(2, 0)  # Label2 — sabit
        grid.setColumnStretch(3, 1)  # Value2 — genişlesin

        # Birinci çift: Label1 | Value1
        lbl1_w = QLabel(lbl1)
        lbl1_w.setStyleSheet(_LBL_CSS)
        lbl1_w.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl1_w.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        grid.addWidget(lbl1_w, 0, 0, Qt.AlignRight | Qt.AlignVCenter)
        grid.addWidget(val1, 0, 1, Qt.AlignLeft | Qt.AlignVCenter)

        # İkinci çift: Label2 | Value2 (eğer varsa)
        if lbl2 and val2 is not None:
            lbl2_w = QLabel(lbl2)
            lbl2_w.setStyleSheet(_LBL_CSS)
            lbl2_w.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lbl2_w.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
            grid.addWidget(lbl2_w, 0, 2, Qt.AlignRight | Qt.AlignVCenter)
            grid.addWidget(val2, 0, 3, Qt.AlignLeft | Qt.AlignVCenter)

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
                   "Kurum Unvan",         self._w("KurumUnvan"))
        s1.add_row("Marka",               self._w("MarkaAdi"),
                   "Urun Tipi",           self._w("UrunTipi"))
        s1.add_row("Temel UDI DI",        self._w("TemelUdiDi"),
                   "Etiket",              self._w("EtiketAdi"))
        s1.add_row("Versiyon/Model",      self._w("VersiyonModel"),
                   "Katalog No",          self._w("KatalogNo"))
        s1.add_row("Aciklama",            self._w("Aciklama"))
        root.addWidget(s1)

        # ── 2. Ithal/Imal Bilgileri ───────────────────────────────────────────
        s2 = _TableSection("Ithal/Imal Bilgileri")
        s2.add_row("Ithal/Imal Bilgisi",        self._w("IthalImalBilgisi"),
                   "Mensei Ulke",               self._w("MenseiUlkeSet"))
        s2.add_row("Ithal Edilen Ulke",         self._w("IthalEdilenUlkeSet"),
                   "Sinif",                     self._w("Sinif"))
        root.addWidget(s2)

        # ── 3. Kurum Bilgileri ───────────────────────────────────────────────
        s22 = _TableSection("Kurum/Firma Bilgileri")
        s22.add_row("Kurum Gorunu Adi",   self._w("KurumGorunenAd"),
                    "Kurum No",            self._w("KurumNo"))
        s22.add_row("Kurum Telefon",      self._w("KurumTelefon"),
                    "Kurum Eposta",        self._w("KurumEposta"))
        root.addWidget(s22)

        # ── 4. Ozellikler ─────────────────────────────────────────────────────
        s3 = _TableSection("Teknik Ozellikler")

        s3.add_subheader("Durum ve Kayit Bilgileri")
        s3.add_row("Durum",                      self._w("Durum"),
                   "Cihaz Kayit Tipi",          self._w("CihazKayitTipi"))
        s3.add_row("UTS Baslangic Tarihi",      self._w("UtsBaslangicTarihi"),
                   "Kontrol Gonderildigi Tarih", self._w("KontroleGonderildigiTarih"))

        s3.add_subheader("Kalibrasyon ve Bakim")
        s3.add_row("Kalibrasyona Tabi mi",      self._w("KalibrasyonaTabiMi"),
                   "Kalibrasyon Periyodu (Ay)", self._w("KalibrasyonPeriyodu"))
        s3.add_row("Bakima Tabi mi",            self._w("BakimaTabiMi"),
                   "Bakim Periyodu (Ay)",       self._w("BakimPeriyodu"))

        s3.add_subheader("Guvenlik ve Uyum")
        s3.add_row("MRG Uyumlu",                       self._w("MrgUyumlu"),
                   "Iyonize Radyasyon Icerir mi",     self._w("IyonizeRadyasyonIcerir"))
        s3.add_row("Tek Hasta Kullanilabilir mi",     self._w("TekHastayaKullanilabilir"),
                   "Sinirli Kullanim Sayisi Var",     self._w("SinirliKullanimSayisiVar"))
        s3.add_row("Sinirli Kullanim Sayisi",         self._w("SinirliKullanimSayisi"),
                   "Baska Imalatyici Yap Edildi",     self._w("BaskaImalatciyaUrettirildiMi"))
        s3.add_row("GMDN Kodu",                        self._w("GmdnTerimKod"),
                   "GMDN Tanimi",                      self._w("GmdnTerimTurkceAd"))
        s3.add_row("GMDN Aciklama",                    self._w("GmdnTerimTurkceAciklama"),
                   "Sut Eslesmesi",                    self._w("SutEslesmesiSet"))
        root.addWidget(s3)

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

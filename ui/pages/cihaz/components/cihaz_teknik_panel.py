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
    QScrollArea, QSizePolicy, QGridLayout, QLineEdit, QPushButton
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
        4-sütünlü bir satır ekler: Label1 | Value1 | Label2 | Value2.
        Zebra arkaplanı otomatik uygulanır.
        """
        bg = _BG_ODD if (self._physical_row % 2 != 0) else _BG_EVEN
        self._physical_row += 1

        # Satır container ve grid layout
        row_w = QWidget()
        row_w.setStyleSheet(
            f"background: {bg}; border-bottom: {_BORDER_CSS};"
        )
        row_w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        hbox = QHBoxLayout(row_w)
        hbox.setContentsMargins(12, 8, 12, 8)
        hbox.setSpacing(20)

        # Birinci çift: Label1 | Value1
        col1 = QWidget()
        col1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        col1_lay = QVBoxLayout(col1)
        col1_lay.setContentsMargins(0, 0, 0, 0)
        col1_lay.setSpacing(2)

        lbl1_w = QLabel(lbl1)
        lbl1_w.setStyleSheet(_LBL_CSS.replace("padding: 7px 14px 2px 14px;", "padding: 0;"))
        lbl1_w.setAlignment(Qt.AlignLeft)
        lbl1_w.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        col1_lay.addWidget(lbl1_w)

        val1.setStyleSheet(val1.styleSheet().replace("padding: 2px 14px 7px 14px;", "padding: 0;"))
        val1.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        col1_lay.addWidget(val1)
        hbox.addWidget(col1, 1)

        # İkinci çift: Label2 | Value2 (eğer varsa)
        if lbl2 and val2 is not None:
            col2 = QWidget()
            col2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            col2_lay = QVBoxLayout(col2)
            col2_lay.setContentsMargins(0, 0, 0, 0)
            col2_lay.setSpacing(2)

            lbl2_w = QLabel(lbl2)
            lbl2_w.setStyleSheet(_LBL_CSS.replace("padding: 7px 14px 2px 14px;", "padding: 0;"))
            lbl2_w.setAlignment(Qt.AlignLeft)
            lbl2_w.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
            col2_lay.addWidget(lbl2_w)

            val2.setStyleSheet(val2.styleSheet().replace("padding: 2px 14px 7px 14px;", "padding: 0;"))
            val2.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            col2_lay.addWidget(val2)
            hbox.addWidget(col2, 1)
        else:
            hbox.addStretch()

        self._vbox.addWidget(row_w)


# ──────────────────────────────────────────────────────────────────────────────

class CihazTeknikPanel(QWidget):
    """
    Cihaz Merkez ekranindaki 'Teknik Bilgiler' sekmesi icerigi.
    """
    searched = Signal(str)  # Sorgula butonuna basilinca, ürün no ile emit
    search_complete = Signal(dict, bool, str)  # data, success, message
    saved = Signal()

    def __init__(self, cihaz_id, db=None, parent=None):
        super().__init__(parent)
        self.db           = db
        self.cihaz_id     = str(cihaz_id) if cihaz_id is not None else ""
        self.teknik_data  = {}
        self._widgets     = {}
        self._link_fields = set()
        self._search_box  = None  # UTS sorgusu textbox'ı

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

        # ── 0. UTS Sorgulama Action Bar ────────────────────────────────────────
        action_bar = QWidget()
        action_bar.setStyleSheet(
            f"background: {_BG_SECT}; border-bottom: {_BORDER_CSS};"
        )
        action_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        action_lay = QHBoxLayout(action_bar)
        action_lay.setContentsMargins(14, 10, 14, 10)
        action_lay.setSpacing(10)

        # TextBox
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("UTS Ürün Numarası...")
        self._search_box.setStyleSheet(
            f"QLineEdit {{"
            f" background: rgba(255,255,255,0.06);"
            f" color: {_TEXT_PRI};"
            f" border: 1px solid {_BORDER};"
            f" border-radius: 4px;"
            f" padding: 6px 10px;"
            f" font-size: 11px;"
            f"}} QLineEdit:focus {{"
            f" border: 1px solid {_ACCENT};"
            f"}}"
        )
        self._search_box.setMinimumHeight(32)
        action_lay.addWidget(self._search_box, 1)

        # Sorgula butonu
        btn_search = QPushButton("Sorgula")
        btn_search.setMinimumWidth(80)
        btn_search.setMinimumHeight(32)
        btn_search.setStyleSheet(S.get("btn_primary", ""))
        btn_search.clicked.connect(self._on_search)
        action_lay.addWidget(btn_search)

        # Temizle butonu
        btn_clear = QPushButton("Temizle")
        btn_clear.setMinimumWidth(80)
        btn_clear.setMinimumHeight(32)
        btn_clear.setStyleSheet(S.get("btn_secondary", ""))
        btn_clear.clicked.connect(self._on_clear)
        action_lay.addWidget(btn_clear)

        # Kaydet butonu
        btn_save = QPushButton("Kaydet")
        btn_save.setMinimumWidth(80)
        btn_save.setMinimumHeight(32)
        btn_save.setStyleSheet(S.get("btn_primary", ""))
        btn_save.clicked.connect(self.saved.emit)
        action_lay.addWidget(btn_save)

        root.addWidget(action_bar)

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

    # ──────────────────────────────────────────────────────────────────────────
    # UTS Action Bar Handlers
    # ──────────────────────────────────────────────────────────────────────────
    def _on_search(self):
        """Sorgula butonuna basilinca."""
        if self._search_box:
            urun_no = self._search_box.text().strip()
            if urun_no:
                self.searched.emit(urun_no)
            else:
                logger.warning("UTS sorgulama: Boş ürün numarası")

    def _on_clear(self):
        """Temizle butonuna basilinca."""
        if self._search_box:
            self._search_box.clear()
            self._search_box.setFocus()

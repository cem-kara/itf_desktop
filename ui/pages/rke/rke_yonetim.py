# -*- coding: utf-8 -*-
"""RKE Envanter Yönetimi — liste + sağ animasyonlu kayıt paneli."""
from typing import Optional

from PySide6.QtCore import (
    Qt, QSortFilterProxyModel, Signal, QTimer, QSize,
    QPropertyAnimation, QEasingCurve,
)
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QLineEdit, QComboBox, QTableView,
    QAbstractItemView, QDateEdit, QTextEdit, QScrollArea,
    QFormLayout,
)

from core.logger import logger
from core.di import get_rke_service
from core.hata_yonetici import bilgi_goster, hata_goster, soru_sor
from ui.components.base_table_model import BaseTableModel
from ui.styles.icons import IconRenderer, IconColors

# ─── Sabitler ──────────────────────────────────────────────
_PANEL_W = 512

_DURUM_SECENEKLER = ["Uygun", "Uygun Değil", "Kontrolde", "Kullanım Dışı"]
_CINS_SECENEKLER  = ["Önlük", "Boyunluk", "Gözlük", "Eldiven", "Bere", "Etek", "Diğer"]
_BEDEN_SECENEKLER = ["XS", "S", "M", "L", "XL", "XXL", "Standart"]
_PB_SECENEKLER    = ["0.25", "0.35", "0.50"]

_DURUM_RENK = {
    "Uygun":         (46,  201, 142),
    "Uygun Değil":   (232,  85,  85),
    "Kontrolde":     (232, 160,  48),
    "Kullanım Dışı": (143, 163, 184),
}

def _durum_stil(r: int, g: int, b: int) -> str:
    return (
        f"QPushButton {{background:rgba({r},{g},{b},38);"
        f"color:rgb({r},{g},{b});"
        f"border:1px solid rgba({r},{g},{b},100);"
        f"border-radius:4px;padding:4px 12px;"
        f"font-size:11px;font-weight:500;}}"
        f"QPushButton:checked {{background:rgba({r},{g},{b},80);"
        f"border:1px solid rgb({r},{g},{b});font-weight:600;}}"
        f"QPushButton:hover {{background:rgba({r},{g},{b},60);}}"
    )


# ═══════════════════════════════════════════════════════════
#  MODEL
# ═══════════════════════════════════════════════════════════

_COLS = [
    ("EkipmanNo",        "Ekipman No",      120),
    ("KoruyucuNumarasi", "Koruyucu No",     130),
    ("AnaBilimDali",     "Ana Bilim Dalı",  160),
    ("Birim",            "Birim",           140),
    ("KoruyucuCinsi",    "Cins",            110),
    ("KursunEsdegeri",   "Pb",               55),
    ("HizmetYili",       "Yıl",              55),
    ("Bedeni",           "Beden",            65),
    ("KontrolTarihi",    "Kontrol Tarihi",  110),
    ("Durum",            "Durum",           110),
]


class _RKEModel(BaseTableModel):
    def __init__(self, parent=None):
        super().__init__(_COLS, parent=parent)

    def _display(self, key: str, row: dict) -> str:
        val = row.get(key, "")
        return str(val) if val is not None else ""

    def _fg(self, key: str, row: dict):
        if key == "Durum":
            return self.status_fg(str(row.get("Durum", "")))
        return None


# ═══════════════════════════════════════════════════════════
#  KAYIT PANELİ
# ═══════════════════════════════════════════════════════════

class _KayitPanel(QFrame):
    """Yeni ekle / düzenle formu — sağdan animasyonlu açılır kapanır."""

    kaydet_istendi = Signal(dict)
    sil_istendi    = Signal(str)
    kapat_istendi  = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("bg-role", "panel")
        self.setMinimumWidth(0)
        self.setMaximumWidth(0)
        self._mod: str = "yeni"
        self._ekipman_no: str = ""
        self._anim_min: Optional[QPropertyAnimation] = None
        self._anim_max: Optional[QPropertyAnimation] = None
        # Dışarıdan load_data tarafından doldurulur
        self.sabitler:   dict[str, dict[str, str]] = {}
        self.rke_listesi: list[dict] = []
        self._build_ui()
        # Combo değişimlerinde otomatik no hesapla
        self.cmb_abd.currentIndexChanged.connect(self.kod_hesapla)
        self.cmb_birim_panel.currentIndexChanged.connect(self.kod_hesapla)
        self.cmb_cins.currentIndexChanged.connect(self.kod_hesapla)

    # ─── UI ──────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Başlık
        header = QFrame()
        header.setFixedHeight(48)
        header.setProperty("bg-role", "elevated")
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(16, 0, 8, 0)
        self.lbl_baslik = QLabel("Yeni Kayıt")
        self.lbl_baslik.setProperty("style-role", "section-title")
        self.lbl_baslik.setProperty("color-role", "primary")
        hlay.addWidget(self.lbl_baslik)
        hlay.addStretch()
        btn_kapat = QPushButton()
        btn_kapat.setFixedSize(28, 28)
        btn_kapat.setProperty("style-role", "close")
        btn_kapat.setToolTip("Kapat")
        btn_kapat.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(btn_kapat, "x", color=IconColors.MUTED, size=14)
        btn_kapat.clicked.connect(self.kapat_istendi.emit)
        hlay.addWidget(btn_kapat)
        root.addWidget(header)

        # Form içeriği (scroll)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setProperty("style-role", "plain")

        icerik = QWidget()
        form = QFormLayout(icerik)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        def _lbl(t: str, zorunlu: bool = False) -> QLabel:
            l = QLabel(("★ " if zorunlu else "") + t)
            l.setProperty("color-role", "muted")
            return l

        self.inp_ekipman_no  = QLineEdit(); self.inp_ekipman_no.setPlaceholderText("Ekipman no")
        self.inp_koruyucu_no = QLineEdit(); self.inp_koruyucu_no.setPlaceholderText("Koruyucu numarası")
        self.cmb_abd         = QComboBox()
        self.cmb_birim_panel = QComboBox()
        self.inp_yil         = QLineEdit(); self.inp_yil.setPlaceholderText("YYYY"); self.inp_yil.setMaxLength(4)
        self.inp_demirba     = QLineEdit(); self.inp_demirba.setPlaceholderText("Demirbaş no (opsiyonel)")

        self.cmb_cins  = QComboBox(); self.cmb_cins.addItems(_CINS_SECENEKLER)
        self.cmb_pb    = QComboBox(); self.cmb_pb.addItems(_PB_SECENEKLER);      self.cmb_pb.setEditable(True)
        self.cmb_beden = QComboBox(); self.cmb_beden.addItems(_BEDEN_SECENEKLER)

        # Gizli — formda yok, _veri_topla'da otomatik atanır
        self.dt_kontrol = QDateEdit(); self.dt_kontrol.setDate(self.dt_kontrol.minimumDate())
        self.cmb_durum  = QComboBox(); self.cmb_durum.addItems(_DURUM_SECENEKLER)

        self.txt_aciklama = QTextEdit()
        self.txt_aciklama.setPlaceholderText("Açıklama...")
        self.txt_aciklama.setFixedHeight(70)

        for lbl_t, widget, zorunlu in [
            ("Ekipman No",      self.inp_ekipman_no,  True),
            ("Koruyucu No",     self.inp_koruyucu_no, False),
            ("Ana Bilim Dalı",  self.cmb_abd,         False),
            ("Birim",           self.cmb_birim_panel, False),
            ("Koruyucu Cinsi",  self.cmb_cins,        False),
            ("Pb",              self.cmb_pb,          False),
            ("Hizmet Yılı",     self.inp_yil,         False),
            ("Beden",           self.cmb_beden,       False),
            ("Demirbaş No",     self.inp_demirba,     False),
            ("Açıklama",        self.txt_aciklama,    False),
        ]:
            form.addRow(_lbl(lbl_t, zorunlu), widget)

        scroll.setWidget(icerik)
        root.addWidget(scroll, 1)

        # Alt butonlar
        alt = QFrame()
        alt.setFixedHeight(56)
        alt.setProperty("bg-role", "elevated")
        alay = QHBoxLayout(alt)
        alay.setContentsMargins(16, 8, 16, 8)
        alay.setSpacing(8)

        self.btn_sil = QPushButton("Sil")
        self.btn_sil.setProperty("style-role", "danger")
        self.btn_sil.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_sil.setVisible(False)
        IconRenderer.set_button_icon(self.btn_sil, "trash", color=IconColors.MUTED, size=14)
        self.btn_sil.clicked.connect(self._on_sil)
        alay.addWidget(self.btn_sil)
        alay.addStretch()

        self.btn_kaydet = QPushButton("Kaydet")
        self.btn_kaydet.setProperty("style-role", "action")
        self.btn_kaydet.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_kaydet, "save", color=IconColors.PRIMARY, size=14)
        self.btn_kaydet.clicked.connect(self._on_kaydet)
        alay.addWidget(self.btn_kaydet)

        root.addWidget(alt)

    # ─── Animasyon ───────────────────────────────────────

    def _animate(self, hedef: int):
        for anim, prop in [(self._anim_min, b"minimumWidth"),
                           (self._anim_max, b"maximumWidth")]:
            if anim and anim.state() == QPropertyAnimation.State.Running:
                anim.stop()

        cur = self.width()
        for prop in (b"minimumWidth", b"maximumWidth"):
            a = QPropertyAnimation(self, prop)
            a.setDuration(220)
            a.setStartValue(cur)
            a.setEndValue(hedef)
            a.setEasingCurve(QEasingCurve.Type.OutCubic)
            a.start()
            if prop == b"minimumWidth":
                self._anim_min = a
            else:
                self._anim_max = a

    def ac(self):
        self._animate(_PANEL_W)

    def kapat(self):
        self._animate(0)

    # ─── Mod ─────────────────────────────────────────────

    def yeni_mod(self):
        self._mod = "yeni"
        self._ekipman_no = ""
        self.lbl_baslik.setText("Yeni Kayıt")
        self.btn_sil.setVisible(False)
        self.inp_ekipman_no.setReadOnly(False)
        self._temizle()
        self.ac()

    def duzenle_mod(self, row: dict):
        self._mod = "duzenle"
        self._ekipman_no = str(row.get("EkipmanNo", ""))
        self.lbl_baslik.setText(f"Düzenle — {self._ekipman_no}")
        self.btn_sil.setVisible(True)
        self.inp_ekipman_no.setReadOnly(True)

        self.inp_ekipman_no.setText(str(row.get("EkipmanNo", "")))
        self.inp_koruyucu_no.setText(str(row.get("KoruyucuNumarasi", "") or ""))
        self._set_cmb(self.cmb_abd,         str(row.get("AnaBilimDali", "") or ""))
        self._set_cmb(self.cmb_birim_panel,  str(row.get("Birim", "") or ""))
        self._set_cmb(self.cmb_cins,        str(row.get("KoruyucuCinsi", "") or ""))
        self._set_cmb(self.cmb_pb,    str(row.get("KursunEsdegeri", "") or ""))
        self.inp_yil.setText(str(row.get("HizmetYili", "") or ""))
        self._set_cmb(self.cmb_beden, str(row.get("Bedeni", "") or ""))
        self._set_cmb(self.cmb_durum, str(row.get("Durum", "") or "Uygun"))
        self.inp_demirba.setText(str(row.get("VarsaDemirbasNo", "") or ""))
        self.txt_aciklama.setPlainText(str(row.get("Aciklama", "") or ""))

        kt = row.get("KontrolTarihi", "")
        if kt:
            try:
                from core.date_utils import parse_date
                from PySide6.QtCore import QDate
                d = parse_date(str(kt))
                if d:
                    self.dt_kontrol.setDate(QDate(d.year, d.month, d.day))
            except Exception:
                pass
        self.ac()

    # ─── Yardımcı ────────────────────────────────────────

    @staticmethod
    def _set_cmb(cmb: QComboBox, val: str):
        idx = cmb.findText(val)
        if idx >= 0:
            cmb.setCurrentIndex(idx)
        elif cmb.isEditable():
            cmb.setCurrentText(val)

    def _temizle(self):
        for w in (self.inp_ekipman_no, self.inp_koruyucu_no,
                  self.inp_yil, self.inp_demirba):
            w.clear()
        self.txt_aciklama.clear()
        for cmb in (self.cmb_abd, self.cmb_birim_panel, self.cmb_cins, self.cmb_pb):
            cmb.setCurrentIndex(0)
        self.cmb_beden.setCurrentIndex(0)
        self.dt_kontrol.setDate(self.dt_kontrol.minimumDate())

    def _veri_topla(self) -> Optional[dict]:
        ekipman_no = self.inp_ekipman_no.text().strip()
        if not ekipman_no:
            return None

        from datetime import date as _date
        bugun = _date.today().strftime("%Y-%m-%d")

        # Yeni kayıt → kontrol tarihi=bugün, durum=Uygun
        # Düzenleme → mevcut değerleri koru (tabloda zaten var)
        kt    = bugun if self._mod == "yeni" else self.dt_kontrol.date().toString("yyyy-MM-dd")
        durum = "Uygun" if self._mod == "yeni" else self.cmb_durum.currentText()

        return {
            "EkipmanNo":        ekipman_no,
            "KoruyucuNumarasi": self.inp_koruyucu_no.text().strip(),
            "AnaBilimDali":     self.cmb_abd.currentText(),
            "Birim":            self.cmb_birim_panel.currentText(),
            "KoruyucuCinsi":    self.cmb_cins.currentText().strip(),
            "KursunEsdegeri":   self.cmb_pb.currentText().strip(),
            "HizmetYili":       self.inp_yil.text().strip(),
            "Bedeni":           self.cmb_beden.currentText(),
            "KontrolTarihi":    kt,
            "Durum":            durum,
            "VarsaDemirbasNo":  self.inp_demirba.text().strip(),
            "Aciklama":         self.txt_aciklama.toPlainText().strip(),
        }

    def kod_hesapla(self):
        """
        ABD / Birim / Cins seçimi değişince EkipmanNo ve
        KoruyucuNumarasi alanlarını otomatik doldur.
        Sadece yeni kayıt modunda çalışır.
        """
        if self._mod != "yeni":
            return

        abd  = self.cmb_abd.currentText().strip()
        birim = self.cmb_birim_panel.currentText().strip()
        cins  = self.cmb_cins.currentText().strip()

        def short(grup: str, val: str) -> str:
            m = self.sabitler.get(grup, {})
            return m.get(val, "UNK") if m else "UNK"

        k_abd  = short("AnaBilimDali",  abd)
        k_cins = short("KoruyucuCinsi", cins)

        # EkipmanNo — aynı cinsten kaç ekipman varsa +1
        if cins:
            sayac = 1 + sum(
                1 for r in self.rke_listesi
                if r.get("KoruyucuCinsi", "").strip() == cins
            )
            self.inp_ekipman_no.setText(f"RKE-{k_cins}-{sayac}")
        else:
            self.inp_ekipman_no.clear()

        # KoruyucuNumarasi
        if birim == "Radyoloji Depo":
            self.inp_koruyucu_no.clear()
        elif abd and birim and cins:
            sayac = 1 + sum(
                1 for r in self.rke_listesi
                if r.get("AnaBilimDali", "").strip()   == abd
                and r.get("Birim", "").strip()          == birim
                and r.get("KoruyucuCinsi", "").strip()  == cins
            )
            k_b = short("Birim", birim)
            self.inp_koruyucu_no.setText(f"{k_abd}-{k_b}-{k_cins}-{sayac}")
        else:
            self.inp_koruyucu_no.clear()

    def _on_kaydet(self):
        veri = self._veri_topla()
        if not veri:
            hata_goster(self, "Ekipman No zorunludur.")
            return
        self.kaydet_istendi.emit(veri)

    def _on_sil(self):
        if self._ekipman_no:
            self.sil_istendi.emit(self._ekipman_no)


# ═══════════════════════════════════════════════════════════
#  SAYFA
# ═══════════════════════════════════════════════════════════

class RKEYonetimPage(QWidget):

    detay_requested = Signal(dict)

    def __init__(self, db=None, action_guard=None, parent=None):
        super().__init__(parent)
        self.setProperty("bg-role", "page")
        self._db           = db
        self._action_guard = action_guard
        self._all_data: list[dict] = []

        self._search_timer = QTimer(self)
        self._search_timer.setInterval(250)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._apply_filters)

        # Sabit listeler (load_data'da doldurulur)
        self._sabit_abd:   list[str] = []
        self._sabit_birim: list[str] = []
        self._sabit_cins:  list[str] = []
        self._sabit_beden: list[str] = _BEDEN_SECENEKLER

        self._setup_ui()
        self._connect_signals()
        if db:
            self.load_data()

    # ─── UI ──────────────────────────────────────────────

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)
        main.addWidget(self._build_toolbar())
        main.addWidget(self._build_subtoolbar())

        # İçerik: tablo sol + panel sağ
        self._icerik = QHBoxLayout()
        self._icerik.setContentsMargins(0, 0, 0, 0)
        self._icerik.setSpacing(0)

        sol = QWidget()
        sol_lay = QVBoxLayout(sol)
        sol_lay.setContentsMargins(0, 0, 0, 0)
        sol_lay.setSpacing(0)
        sol_lay.addWidget(self._build_table(), 1)
        sol_lay.addWidget(self._build_footer())
        self._icerik.addWidget(sol, 1)

        self._panel = _KayitPanel()
        self._icerik.addWidget(self._panel)

        wrap = QWidget()
        wrap.setLayout(self._icerik)
        main.addWidget(wrap, 1)

    def _build_toolbar(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(60)
        frame.setProperty("bg-role", "panel")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(8)

        title = QLabel("RKE Envanter")
        title.setProperty("style-role", "title")
        title.setProperty("color-role", "primary")
        lay.addWidget(title)
        lay.addWidget(self._sep())

        self._durum_btns: dict[str, QPushButton] = {}
        for lbl in ("Tümü", "Uygun", "Uygun Değil", "Kontrolde"):
            btn = QPushButton(lbl)
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setFixedHeight(28)
            btn.setMinimumWidth(80)
            if lbl == "Tümü":
                btn.setProperty("style-role", "secondary")
                btn.setChecked(True)
            else:
                r, g, b = _DURUM_RENK[lbl]
                btn.setStyleSheet(_durum_stil(r, g, b))
            self._durum_btns[lbl] = btn
            lay.addWidget(btn)

        lay.addWidget(self._sep())

        self.inp_arama = QLineEdit()
        self.inp_arama.setPlaceholderText("Ekipman no, birim, cins ara…")
        self.inp_arama.setClearButtonEnabled(True)
        self.inp_arama.setFixedWidth(220)
        lay.addWidget(self.inp_arama)

        lay.addStretch()

        self.btn_yenile = QPushButton()
        self.btn_yenile.setToolTip("Yenile")
        self.btn_yenile.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_yenile.setFixedSize(32, 28)
        self.btn_yenile.setProperty("style-role", "refresh")
        IconRenderer.set_button_icon(self.btn_yenile, "refresh", color=IconColors.MUTED, size=16)
        lay.addWidget(self.btn_yenile)

        self.btn_yeni = QPushButton(" Yeni Ekipman")
        self.btn_yeni.setProperty("style-role", "action")
        self.btn_yeni.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_yeni, "plus", color=IconColors.PRIMARY, size=14)
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self.btn_yeni, "rke.write")
        lay.addWidget(self.btn_yeni)

        return frame

    def _build_subtoolbar(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(36)
        frame.setProperty("bg-role", "page")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(8)

        lbl = QLabel("FİLTRE:")
        lbl.setProperty("color-role", "disabled")
        lay.addWidget(lbl)

        for attr, placeholder, width in [
            ("cmb_abd",   "Ana Bilim Dalı", 160),
            ("cmb_birim", "Birim",          140),
            ("cmb_cins",  "Cins",           130),
        ]:
            lbl_f = QLabel(placeholder + ":")
            lbl_f.setProperty("color-role", "disabled")
            lay.addWidget(lbl_f)
            cmb = QComboBox()
            cmb.addItem("Tümü")
            cmb.setFixedWidth(width)
            setattr(self, attr, cmb)
            lay.addWidget(cmb)

        lay.addStretch()
        return frame

    def _build_table(self) -> QTableView:
        self._model = _RKEModel()
        self._proxy = QSortFilterProxyModel(self)
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._proxy.setFilterKeyColumn(-1)

        self.table = QTableView()
        self.table.setModel(self._proxy)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setDefaultSectionSize(38)

        self._model.setup_columns(self.table, stretch_keys=["AnaBilimDali", "Birim"])
        return self.table

    def _build_footer(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(36)
        frame.setProperty("bg-role", "panel")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 0, 16, 0)
        self.lbl_info = QLabel("0 kayıt")
        self.lbl_info.setProperty("style-role", "footer")
        lay.addWidget(self.lbl_info)
        lay.addStretch()
        return frame

    # ─── Sinyaller ───────────────────────────────────────

    def _connect_signals(self):
        for lbl, btn in self._durum_btns.items():
            btn.clicked.connect(lambda _, t=lbl: self._on_durum_click(t))
        self.inp_arama.textChanged.connect(lambda _: self._search_timer.start())
        self.cmb_abd.currentIndexChanged.connect(lambda _: self._apply_filters())
        self.cmb_birim.currentIndexChanged.connect(lambda _: self._apply_filters())
        self.cmb_cins.currentIndexChanged.connect(lambda _: self._apply_filters())
        self.btn_yenile.clicked.connect(self.load_data)
        self.btn_yeni.clicked.connect(self._on_yeni)
        self.table.doubleClicked.connect(self._on_double_click)
        self._panel.kaydet_istendi.connect(self._on_panel_kaydet)
        self._panel.sil_istendi.connect(self._on_panel_sil)
        self._panel.kapat_istendi.connect(self._panel.kapat)

    # ─── Veri ────────────────────────────────────────────

    def load_data(self):
        if not self._db:
            return
        try:
            svc = get_rke_service(self._db)
            sonuc = svc.get_rke_listesi()
            self._all_data = (sonuc.veri or []) if sonuc.basarili else []

            # Sabitler tablosundan combo listeleri ve kısa kodları yükle
            try:
                sabitler = svc._r.get("Sabitler").get_all() or []
                def _sabit_liste(kod: str) -> list[str]:
                    return sorted({
                        str(r.get("MenuEleman", "")).strip()
                        for r in sabitler
                        if str(r.get("Kod", "")).strip() == kod
                        and str(r.get("MenuEleman", "")).strip()
                    })
                def _kisa_kod_map(kod: str) -> dict[str, str]:
                    """MenuEleman → Aciklama (kısa kod) eşlemesi."""
                    return {
                        str(r.get("MenuEleman", "")).strip(): str(r.get("Aciklama", "")).strip()
                        for r in sabitler
                        if str(r.get("Kod", "")).strip() == kod
                        and str(r.get("MenuEleman", "")).strip()
                    }
                self._sabit_abd   = _sabit_liste("AnaBilimDali")
                self._sabit_birim = _sabit_liste("Birim")
                self._sabit_cins  = _sabit_liste("Koruyucu_Cinsi")
                self._sabit_beden = _sabit_liste("Beden") or _BEDEN_SECENEKLER
                # Kısa kod haritaları
                self._panel.sabitler = {
                    "AnaBilimDali":   _kisa_kod_map("AnaBilimDali"),
                    "Birim":          _kisa_kod_map("Birim"),
                    "KoruyucuCinsi":  _kisa_kod_map("Koruyucu_Cinsi"),
                }
            except Exception as e:
                logger.debug(f"RKE sabitler yüklenemedi: {e}")
                self._sabit_abd = self._sabit_birim = self._sabit_cins = []
                self._sabit_beden = _BEDEN_SECENEKLER
                self._panel.sabitler = {}

            # Paneli güncelle
            self._panel.rke_listesi = self._all_data
            self._panel_combolarini_doldur()

        except Exception as e:
            logger.error(f"RKE liste yükleme: {e}")
            self._all_data = []
        self._fill_combos()
        self._apply_filters()

    def _panel_combolarini_doldur(self):
        """Kayıt panelindeki combo'ları Sabitler tablosundan doldur."""
        p = self._panel

        def _doldur(cmb: QComboBox, secenekler: list[str], mevcut: str = ""):
            cmb.blockSignals(True)
            cmb.clear()
            cmb.addItem("")          # boş seçenek
            cmb.addItems(secenekler)
            idx = cmb.findText(mevcut)
            if idx >= 0:
                cmb.setCurrentIndex(idx)
            cmb.blockSignals(False)

        _doldur(p.cmb_abd,         self._sabit_abd)
        _doldur(p.cmb_birim_panel, self._sabit_birim)
        _doldur(p.cmb_cins,        self._sabit_cins)
        _doldur(p.cmb_beden,       self._sabit_beden)

    def _fill_combos(self):
        def uniq(key):
            return sorted({str(r.get(key, "")) for r in self._all_data if r.get(key, "")})

        for cmb, key in [
            (self.cmb_abd,   "AnaBilimDali"),
            (self.cmb_birim, "Birim"),
            (self.cmb_cins,  "KoruyucuCinsi"),
        ]:
            cur = cmb.currentText()
            cmb.blockSignals(True)
            cmb.clear()
            cmb.addItem("Tümü")
            cmb.addItems(uniq(key))
            idx = cmb.findText(cur)
            if idx >= 0:
                cmb.setCurrentIndex(idx)
            cmb.blockSignals(False)

    # ─── Filtreleme ──────────────────────────────────────

    def _on_durum_click(self, lbl: str):
        for t, btn in self._durum_btns.items():
            btn.setChecked(t == lbl)
        self._apply_filters()

    def _apply_filters(self):
        filtered = self._all_data
        aktif = next((t for t, b in self._durum_btns.items() if b.isChecked()), "Tümü")
        if aktif != "Tümü":
            filtered = [r for r in filtered if str(r.get("Durum", "")).strip() == aktif]
        for cmb, key in [
            (self.cmb_abd,   "AnaBilimDali"),
            (self.cmb_birim, "Birim"),
            (self.cmb_cins,  "KoruyucuCinsi"),
        ]:
            val = cmb.currentText()
            if val and val != "Tümü":
                filtered = [r for r in filtered if str(r.get(key, "")).strip() == val]
        self._model.set_data(filtered)
        self._proxy.setFilterFixedString(self.inp_arama.text().strip())
        self.lbl_info.setText(f"{self._proxy.rowCount()} kayıt")

    # ─── Panel işlemleri ─────────────────────────────────

    def _on_yeni(self):
        self._panel.yeni_mod()

    def _on_double_click(self, idx):
        if not idx.isValid():
            return
        src = self._proxy.mapToSource(idx)
        row = self._model.get_row(src.row())
        if row:
            self._panel.duzenle_mod(row)
            self.detay_requested.emit(row)

    def _on_panel_kaydet(self, veri: dict):
        if not self._db:
            return
        try:
            svc = get_rke_service(self._db)
            if self._panel._mod == "yeni":
                sonuc = svc.rke_ekle(veri)
            else:
                sonuc = svc.rke_guncelle(veri["EkipmanNo"], veri)
            if sonuc.basarili:
                bilgi_goster(self, sonuc.mesaj)
                self._panel.kapat()
                self.load_data()
            else:
                hata_goster(self, sonuc.mesaj)
        except Exception as e:
            logger.error(f"RKE kaydet: {e}")
            hata_goster(self, str(e))

    def _on_panel_sil(self, ekipman_no: str):
        if not soru_sor(self, f"<b>{ekipman_no}</b> kaydı silinsin mi?"):
            return
        try:
            svc = get_rke_service(self._db)
            sonuc = svc.rke_sil(ekipman_no)
            if sonuc.basarili:
                bilgi_goster(self, sonuc.mesaj)
                self._panel.kapat()
                self.load_data()
            else:
                hata_goster(self, sonuc.mesaj)
        except Exception as e:
            hata_goster(self, str(e))

    # ─── Yardımcı ────────────────────────────────────────

    @staticmethod
    def _sep() -> QFrame:
        f = QFrame()
        f.setFixedSize(1, 22)
        f.setProperty("bg-role", "separator")
        return f


# Geriye dönük uyumluluk
RKEYonetimPenceresi = RKEYonetimPage

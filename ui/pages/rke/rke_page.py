# -*- coding: utf-8 -*-
"""
rke_page.py — Birleşik RKE Yönetim Sayfası

Tek tablo, tek DB sorgusu.
Sağ panel context-sensitive:
  • Satır seç → "Ekipmanı Düzenle" veya "Muayene Ekle" butonuna göre açılır.
  • Çift tıklama → Ekipman düzenleme paneli.
  • Toplu seçim → "Toplu Muayene" aktifleşir.
"""
import uuid
from typing import Optional

from PySide6.QtCore import (
    Qt, QSortFilterProxyModel, Signal, QTimer,
    QPropertyAnimation, QEasingCurve, QDate,
)
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QLineEdit, QComboBox, QTableView,
    QAbstractItemView, QDateEdit, QTextEdit, QScrollArea,
    QFormLayout, QStackedWidget,
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
_FIZIKSEL_SEÇ     = ["Kullanıma Uygun", "Kullanıma Uygun Değil"]
_SKOPI_SEÇ        = ["Kullanıma Uygun", "Kullanıma Uygun Değil", "Yapılmadı"]

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
        return str(row.get(key, "") or "")

    def _fg(self, key: str, row: dict):
        if key == "Durum":
            return self.status_fg(str(row.get("Durum", "")))
        return None


# ═══════════════════════════════════════════════════════════
#  PANEL YARDIMCILARI
# ═══════════════════════════════════════════════════════════

def _panel_header(baslik_widget: QLabel, parent: QFrame,
                  kapat_cb) -> QFrame:
    """Ortak panel başlık çubuğu."""
    header = QFrame()
    header.setFixedHeight(48)
    header.setProperty("bg-role", "elevated")
    hlay = QHBoxLayout(header)
    hlay.setContentsMargins(16, 0, 8, 0)
    hlay.addWidget(baslik_widget)
    hlay.addStretch()
    btn_k = QPushButton()
    btn_k.setFixedSize(28, 28)
    btn_k.setProperty("style-role", "close")
    btn_k.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    IconRenderer.set_button_icon(btn_k, "x", color=IconColors.MUTED, size=14)
    btn_k.clicked.connect(kapat_cb)
    hlay.addWidget(btn_k)
    return header


def _scroll_form() -> tuple[QScrollArea, QWidget, QFormLayout]:
    """Scroll + form içeriği döndür."""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setProperty("style-role", "plain")
    icerik = QWidget()
    form = QFormLayout(icerik)
    form.setContentsMargins(16, 12, 16, 16)
    form.setSpacing(10)
    form.setLabelAlignment(
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
    )
    scroll.setWidget(icerik)
    return scroll, icerik, form


def _form_lbl(t: str, zorunlu: bool = False) -> QLabel:
    l = QLabel(("★ " if zorunlu else "") + t)
    l.setProperty("color-role", "muted")
    return l


def _panel_alt(sil_cb, kaydet_cb) -> tuple[QFrame, QPushButton]:
    """Alt buton çubuğu; sil butonu döner (görünürlük dışarıdan)."""
    alt = QFrame()
    alt.setFixedHeight(56)
    alt.setProperty("bg-role", "elevated")
    alay = QHBoxLayout(alt)
    alay.setContentsMargins(16, 8, 16, 8)
    alay.setSpacing(8)
    btn_sil = QPushButton("Sil")
    btn_sil.setProperty("style-role", "danger")
    btn_sil.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    btn_sil.setVisible(False)
    IconRenderer.set_button_icon(btn_sil, "trash", color=IconColors.MUTED, size=14)
    btn_sil.clicked.connect(sil_cb)
    alay.addWidget(btn_sil)
    alay.addStretch()
    btn_kd = QPushButton("Kaydet")
    btn_kd.setProperty("style-role", "action")
    btn_kd.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    IconRenderer.set_button_icon(btn_kd, "save", color=IconColors.PRIMARY, size=14)
    btn_kd.clicked.connect(kaydet_cb)
    alay.addWidget(btn_kd)
    return alt, btn_sil


# ═══════════════════════════════════════════════════════════
#  BİRLEŞİK SAĞ PANEL
# ═══════════════════════════════════════════════════════════

class _SagPanel(QFrame):
    """
    Tek panel, iki mod:
      'ekipman' → Ekipman ekleme / düzenleme formu
      'muayene' → Muayene kayıt formu
    """

    ekipman_kaydet  = Signal(dict)
    ekipman_sil     = Signal(str)   # EkipmanNo
    muayene_kaydet  = Signal(dict)
    muayene_sil     = Signal(str)   # KayitNo
    kapat_istendi   = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("bg-role", "panel")
        self.setMinimumWidth(0)
        self.setMaximumWidth(0)

        # Durum
        self._mod: str = ""          # 'ekipman' | 'muayene'
        self._ekipman_no: str = ""
        self._kayit_no: str = ""
        self._anim: list[QPropertyAnimation] = []

        # Paylaşılan veriler (load_data'dan doldurulur)
        self.sabitler:          dict[str, dict[str, str]] = {}
        self.rke_listesi:       list[dict] = []
        self.kontrol_listesi:   list[str] = []
        self.sorumlu_listesi:   list[str] = []
        self.aciklama_listesi:  list[str] = []

        self._build_ui()

    # ─── UI ──────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Başlık (mod'a göre değişir)
        self.lbl_baslik = QLabel("")
        self.lbl_baslik.setProperty("style-role", "section-title")
        self.lbl_baslik.setProperty("color-role", "primary")
        root.addWidget(_panel_header(self.lbl_baslik, self, self.kapat_istendi.emit))

        # Bilgi etiketi (muayene modunda ekipman adı gösterir)
        self.lbl_bilgi = QLabel("")
        self.lbl_bilgi.setProperty("color-role", "accent")
        self.lbl_bilgi.setProperty("style-role", "stat-label")
        self.lbl_bilgi.setContentsMargins(16, 4, 16, 0)
        root.addWidget(self.lbl_bilgi)

        # Stacked: 0=ekipman, 1=muayene
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_ekipman_form())
        self._stack.addWidget(self._build_muayene_form())
        root.addWidget(self._stack, 1)

        # Alt butonlar — her form kendi setini kullanır
        root.addWidget(self._alt_ekipman)
        root.addWidget(self._alt_muayene)

    def _build_ekipman_form(self) -> QScrollArea:
        from PySide6.QtWidgets import QGroupBox, QGridLayout

        # Widget tanımları
        self.inp_ekipman_no  = QLineEdit(); self.inp_ekipman_no.setPlaceholderText("Otomatik hesaplanır")
        self.inp_koruyucu_no = QLineEdit(); self.inp_koruyucu_no.setPlaceholderText("Otomatik hesaplanır")
        self.cmb_abd         = QComboBox()
        self.cmb_birim_panel = QComboBox()
        self.cmb_cins        = QComboBox(); self.cmb_cins.addItems(_CINS_SECENEKLER)
        self.cmb_pb          = QComboBox(); self.cmb_pb.addItems(_PB_SECENEKLER); self.cmb_pb.setEditable(True)
        self.inp_yil         = QLineEdit(); self.inp_yil.setPlaceholderText("YYYY"); self.inp_yil.setMaxLength(4)
        self.cmb_beden       = QComboBox(); self.cmb_beden.addItems(_BEDEN_SECENEKLER)
        self.inp_demirba     = QLineEdit(); self.inp_demirba.setPlaceholderText("Opsiyonel")
        self.txt_aciklama    = QTextEdit(); self.txt_aciklama.setPlaceholderText("Açıklama..."); self.txt_aciklama.setFixedHeight(64)
        # Gizli (otomatik atanır)
        self.dt_kontrol    = QDateEdit(); self.dt_kontrol.setDate(self.dt_kontrol.minimumDate())
        self.cmb_durum_ekp = QComboBox(); self.cmb_durum_ekp.addItems(_DURUM_SECENEKLER)

        def _lbl(t): l = QLabel(t); l.setProperty("style-role","stat-label"); l.setProperty("color-role","muted"); return l
        def _lbl_r(t): l = QLabel(t); l.setProperty("style-role","stat-label"); l.setProperty("color-role","err"); return l

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setProperty("style-role", "plain")

        icerik = QWidget()
        vlay = QVBoxLayout(icerik)
        vlay.setContentsMargins(12, 10, 12, 12)
        vlay.setSpacing(8)

        # ── Tanımlama ──
        grp_id = QGroupBox("Tanımlama")
        grp_id.setProperty("style-role", "group")
        gi = QGridLayout(grp_id)
        gi.setContentsMargins(10, 6, 10, 10)
        gi.setSpacing(6)

        gi.addWidget(_lbl_r("• Ekipman No"), 0, 0)
        gi.addWidget(self.inp_ekipman_no, 1, 0)
        gi.addWidget(_lbl("Koruyucu No"), 0, 1)
        gi.addWidget(self.inp_koruyucu_no, 1, 1)
        vlay.addWidget(grp_id)

        # ── Konum ──
        grp_konum = QGroupBox("Konum")
        grp_konum.setProperty("style-role", "group")
        gk = QGridLayout(grp_konum)
        gk.setContentsMargins(10, 6, 10, 10)
        gk.setSpacing(6)

        gk.addWidget(_lbl("Ana Bilim Dalı"), 0, 0, 1, 2)
        gk.addWidget(self.cmb_abd, 1, 0, 1, 2)
        gk.addWidget(_lbl("Birim"), 2, 0, 1, 2)
        gk.addWidget(self.cmb_birim_panel, 3, 0, 1, 2)
        vlay.addWidget(grp_konum)

        # ── Ekipman Özellikleri ──
        grp_ozellik = QGroupBox("Ekipman Özellikleri")
        grp_ozellik.setProperty("style-role", "group")
        go = QGridLayout(grp_ozellik)
        go.setContentsMargins(10, 6, 10, 10)
        go.setSpacing(6)

        go.addWidget(_lbl("Koruyucu Cinsi"), 0, 0, 1, 2)
        go.addWidget(self.cmb_cins, 1, 0, 1, 2)

        go.addWidget(_lbl("Pb"), 2, 0)
        go.addWidget(self.cmb_pb, 3, 0)
        go.addWidget(_lbl("Hizmet Yılı"), 2, 1)
        go.addWidget(self.inp_yil, 3, 1)
        go.setColumnStretch(0, 1)
        go.setColumnStretch(1, 1)

        go.addWidget(_lbl("Beden"), 4, 0, 1, 2)
        go.addWidget(self.cmb_beden, 5, 0, 1, 2)
        vlay.addWidget(grp_ozellik)

        # ── Ek Bilgiler ──
        grp_ek = QGroupBox("Ek Bilgiler")
        grp_ek.setProperty("style-role", "group")
        ge = QVBoxLayout(grp_ek)
        ge.setContentsMargins(10, 6, 10, 10)
        ge.setSpacing(6)
        ge.addWidget(_lbl("Demirbaş No"))
        ge.addWidget(self.inp_demirba)
        ge.addWidget(_lbl("Açıklama"))
        ge.addWidget(self.txt_aciklama)
        vlay.addWidget(grp_ek)

        vlay.addStretch()
        scroll.setWidget(icerik)

        self._alt_ekipman, self.btn_ekipman_sil = _panel_alt(
            self._on_ekipman_sil, self._on_ekipman_kaydet
        )
        # Combo sinyalleri
        self.cmb_abd.currentIndexChanged.connect(self.kod_hesapla)
        self.cmb_birim_panel.currentIndexChanged.connect(self.kod_hesapla)
        self.cmb_cins.currentIndexChanged.connect(self.kod_hesapla)
        return scroll

    def _build_muayene_form(self) -> QScrollArea:
        from PySide6.QtWidgets import QGroupBox, QGridLayout

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setProperty("style-role", "plain")

        icerik = QWidget()
        vlay = QVBoxLayout(icerik)
        vlay.setContentsMargins(12, 10, 12, 12)
        vlay.setSpacing(8)

        def _grp_lbl(t: str) -> QLabel:
            l = QLabel(t)
            l.setProperty("style-role", "stat-label")
            l.setProperty("color-role", "muted")
            return l

        def _req_lbl(t: str) -> QLabel:
            """Zorunlu alan etiketi — küçük kırmızı nokta prefix."""
            l = QLabel(f"• {t}")
            l.setProperty("style-role", "stat-label")
            l.setProperty("color-role", "err")
            return l

        # ── Fiziksel Muayene ──
        grp_fiz = QGroupBox("Fiziksel Muayene")
        grp_fiz.setProperty("style-role", "group")
        gf = QGridLayout(grp_fiz)
        gf.setContentsMargins(10, 6, 10, 10)
        gf.setSpacing(6)
        gf.addWidget(_grp_lbl("Tarih"), 0, 0)
        self.dt_fiziksel = QDateEdit(QDate.currentDate())
        self.dt_fiziksel.setCalendarPopup(True)
        self.dt_fiziksel.setDisplayFormat("dd.MM.yyyy")
        gf.addWidget(self.dt_fiziksel, 1, 0)
        gf.addWidget(_req_lbl("Durum"), 0, 1)
        self.cmb_fiziksel = QComboBox()
        self.cmb_fiziksel.addItems(_FIZIKSEL_SEÇ)
        gf.addWidget(self.cmb_fiziksel, 1, 1)
        vlay.addWidget(grp_fiz)

        # ── Skopi Muayene ──
        grp_sko = QGroupBox("Skopi Muayene")
        grp_sko.setProperty("style-role", "group")
        gs = QGridLayout(grp_sko)
        gs.setContentsMargins(10, 6, 10, 10)
        gs.setSpacing(6)
        gs.addWidget(_grp_lbl("Tarih"), 0, 0)
        self.dt_skopi = QDateEdit(QDate.currentDate())
        self.dt_skopi.setCalendarPopup(True)
        self.dt_skopi.setDisplayFormat("dd.MM.yyyy")
        gs.addWidget(self.dt_skopi, 1, 0)
        gs.addWidget(_req_lbl("Durum"), 0, 1)
        self.cmb_skopi = QComboBox()
        self.cmb_skopi.addItems(_SKOPI_SEÇ)
        self.cmb_skopi.setCurrentIndex(2)
        gs.addWidget(self.cmb_skopi, 1, 1)
        vlay.addWidget(grp_sko)

        # ── Sonuç ──
        grp_sonuc = QGroupBox("Sonuç Bilgileri")
        grp_sonuc.setProperty("style-role", "group")
        go = QVBoxLayout(grp_sonuc)
        go.setContentsMargins(10, 6, 10, 10)
        go.setSpacing(6)

        go.addWidget(_grp_lbl("Kontrol Eden"))
        self.cmb_kontrol = QComboBox()
        self.cmb_kontrol.setEditable(True)
        if le := self.cmb_kontrol.lineEdit():
            le.setPlaceholderText("Kontrol eden unvan...")
        go.addWidget(self.cmb_kontrol)

        go.addWidget(_grp_lbl("Birim Sorumlusu"))
        self.cmb_sorumlu = QComboBox()
        self.cmb_sorumlu.setEditable(True)
        if le := self.cmb_sorumlu.lineEdit():
            le.setPlaceholderText("Birim sorumlusu unvan...")
        go.addWidget(self.cmb_sorumlu)

        go.addWidget(_grp_lbl("Teknik Açıklama"))
        self.cmb_aciklama_panel = QComboBox()
        self.cmb_aciklama_panel.setEditable(True)
        if le := self.cmb_aciklama_panel.lineEdit():
            le.setPlaceholderText("Açıklama seçin veya yazın...")
        go.addWidget(self.cmb_aciklama_panel)

        go.addWidget(_grp_lbl("Notlar"))
        self.txt_notlar = QTextEdit()
        self.txt_notlar.setPlaceholderText("Not...")
        self.txt_notlar.setFixedHeight(64)
        go.addWidget(self.txt_notlar)
        vlay.addWidget(grp_sonuc)

        vlay.addStretch()
        scroll.setWidget(icerik)

        self._alt_muayene, self.btn_muayene_sil = _panel_alt(
            self._on_muayene_sil, self._on_muayene_kaydet
        )
        return scroll

    # ─── Animasyon ───────────────────────────────────────

    def _animate(self, hedef: int):
        cur = self.width()
        self._anim.clear()
        for prop in (b"minimumWidth", b"maximumWidth"):
            a = QPropertyAnimation(self, prop)
            a.setDuration(220)
            a.setStartValue(cur)
            a.setEndValue(hedef)
            a.setEasingCurve(QEasingCurve.Type.OutCubic)
            a.start()
            self._anim.append(a)

    def ac(self):
        self._animate(_PANEL_W)

    def kapat(self):
        self._animate(0)

    # ─── Mod geçişleri ───────────────────────────────────

    def _goster_mod(self, mod: str):
        """Doğru form ve alt butonları göster."""
        self._mod = mod
        if mod == "ekipman":
            self._stack.setCurrentIndex(0)
            self._alt_ekipman.setVisible(True)
            self._alt_muayene.setVisible(False)
        else:
            self._stack.setCurrentIndex(1)
            self._alt_ekipman.setVisible(False)
            self._alt_muayene.setVisible(True)

    def yeni_ekipman(self):
        self._ekipman_no = ""
        self.lbl_baslik.setText("Yeni Ekipman")
        self.lbl_bilgi.setText("")
        self.btn_ekipman_sil.setVisible(False)
        self.inp_ekipman_no.setReadOnly(False)
        self._temizle_ekipman()
        self._goster_mod("ekipman")
        self.ac()

    def duzenle_ekipman(self, row: dict):
        self._ekipman_no = str(row.get("EkipmanNo", ""))
        self.lbl_baslik.setText(f"Düzenle — {self._ekipman_no}")
        self.lbl_bilgi.setText("")
        self.btn_ekipman_sil.setVisible(True)
        self.inp_ekipman_no.setReadOnly(True)

        self.inp_ekipman_no.setText(str(row.get("EkipmanNo", "")))
        self.inp_koruyucu_no.setText(str(row.get("KoruyucuNumarasi", "") or ""))
        self._set_cmb(self.cmb_abd,         str(row.get("AnaBilimDali", "") or ""))
        self._set_cmb(self.cmb_birim_panel,  str(row.get("Birim", "") or ""))
        self._set_cmb(self.cmb_cins,        str(row.get("KoruyucuCinsi", "") or ""))
        self._set_cmb(self.cmb_pb,          str(row.get("KursunEsdegeri", "") or ""))
        self.inp_yil.setText(str(row.get("HizmetYili", "") or ""))
        self._set_cmb(self.cmb_beden,       str(row.get("Bedeni", "") or ""))
        self._set_cmb(self.cmb_durum_ekp,   str(row.get("Durum", "") or "Uygun"))
        self.inp_demirba.setText(str(row.get("VarsaDemirbasNo", "") or ""))
        self.txt_aciklama.setPlainText(str(row.get("Aciklama", "") or ""))

        kt = row.get("KontrolTarihi", "")
        if kt:
            try:
                from core.date_utils import parse_date
                d = parse_date(str(kt))
                if d:
                    from PySide6.QtCore import QDate
                    self.dt_kontrol.setDate(QDate(d.year, d.month, d.day))
            except Exception:
                pass

        self._goster_mod("ekipman")
        self.ac()

    def yeni_muayene(self, ekipman_no: str, bilgi: str = ""):
        self._kayit_no = ""
        self._ekipman_no = ekipman_no
        self.lbl_baslik.setText("Yeni Muayene")
        self.lbl_bilgi.setText(bilgi or ekipman_no)
        self.btn_muayene_sil.setVisible(False)
        self._temizle_muayene()
        self._goster_mod("muayene")
        self.ac()

    # ─── Yardımcı ────────────────────────────────────────

    @staticmethod
    def _set_cmb(cmb: QComboBox, val: str):
        idx = cmb.findText(val)
        if idx >= 0:
            cmb.setCurrentIndex(idx)
        elif cmb.isEditable():
            cmb.setCurrentText(val)

    def _temizle_ekipman(self):
        for w in (self.inp_ekipman_no, self.inp_koruyucu_no,
                  self.inp_yil, self.inp_demirba):
            w.clear()
        self.txt_aciklama.clear()
        for cmb in (self.cmb_abd, self.cmb_birim_panel, self.cmb_cins, self.cmb_pb):
            if cmb.count(): cmb.setCurrentIndex(0)
        self.cmb_beden.setCurrentIndex(0)
        self.dt_kontrol.setDate(self.dt_kontrol.minimumDate())

    def _temizle_muayene(self):
        self.dt_fiziksel.setDate(QDate.currentDate())
        self.cmb_fiziksel.setCurrentIndex(0)
        self.dt_skopi.setDate(QDate.currentDate())
        self.cmb_skopi.setCurrentIndex(2)
        if self.cmb_kontrol.count():  self.cmb_kontrol.setCurrentIndex(0)
        if self.cmb_sorumlu.count():  self.cmb_sorumlu.setCurrentIndex(0)
        if self.cmb_aciklama_panel.count(): self.cmb_aciklama_panel.setCurrentIndex(0)
        self.txt_notlar.clear()

    # ─── Sabitlerden doldur ──────────────────────────────

    def panel_combolarini_doldur(self):
        def _doldur(cmb, items, mevcut=""):
            cmb.blockSignals(True)
            cmb.clear()
            cmb.addItem("")
            cmb.addItems(items)
            idx = cmb.findText(mevcut)
            if idx >= 0: cmb.setCurrentIndex(idx)
            cmb.blockSignals(False)

        _doldur(self.cmb_abd,          self.sabitler.get("_liste_abd", []))
        _doldur(self.cmb_birim_panel,  self.sabitler.get("_liste_birim", []))
        _doldur(self.cmb_cins,         self.sabitler.get("_liste_cins", []))
        beden = self.sabitler.get("_liste_beden", _BEDEN_SECENEKLER)
        _doldur(self.cmb_beden, beden)
        if self.kontrol_listesi:
            _doldur(self.cmb_kontrol, self.kontrol_listesi)
        sorumlu = self.sorumlu_listesi or self.kontrol_listesi
        if sorumlu:
            _doldur(self.cmb_sorumlu, sorumlu)
        if self.aciklama_listesi:
            _doldur(self.cmb_aciklama_panel, self.aciklama_listesi)

    # ─── Otomatik no hesapla ─────────────────────────────

    def kod_hesapla(self):
        if self._mod != "ekipman" or self.inp_ekipman_no.isReadOnly():
            return
        abd   = self.cmb_abd.currentText().strip()
        birim = self.cmb_birim_panel.currentText().strip()
        cins  = self.cmb_cins.currentText().strip()

        def short(grup: str, val: str) -> str:
            m = self.sabitler.get(grup, {})
            return m.get(val, "UNK") if isinstance(m, dict) else "UNK"

        k_abd  = short("AnaBilimDali",  abd)
        k_cins = short("KoruyucuCinsi", cins)

        if cins:
            sayac = 1 + sum(1 for r in self.rke_listesi
                            if r.get("KoruyucuCinsi", "").strip() == cins)
            self.inp_ekipman_no.setText(f"RKE-{k_cins}-{sayac}")
        else:
            self.inp_ekipman_no.clear()

        if birim == "Radyoloji Depo":
            self.inp_koruyucu_no.clear()
        elif abd and birim and cins:
            sayac = 1 + sum(1 for r in self.rke_listesi
                            if r.get("AnaBilimDali","").strip() == abd
                            and r.get("Birim","").strip() == birim
                            and r.get("KoruyucuCinsi","").strip() == cins)
            k_b = short("Birim", birim)
            self.inp_koruyucu_no.setText(f"{k_abd}-{k_b}-{k_cins}-{sayac}")
        else:
            self.inp_koruyucu_no.clear()

    # ─── Veri toplama ────────────────────────────────────

    def _veri_ekipman(self) -> Optional[dict]:
        ekipman_no = self.inp_ekipman_no.text().strip()
        if not ekipman_no:
            return None
        from datetime import date as _date
        bugun = _date.today().strftime("%Y-%m-%d")
        kt = bugun if not self.inp_ekipman_no.isReadOnly() \
             else self.dt_kontrol.date().toString("yyyy-MM-dd")
        durum = "Uygun" if not self.inp_ekipman_no.isReadOnly() \
                else self.cmb_durum_ekp.currentText()
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

    def _veri_muayene(self) -> dict:
        return {
            "KayitNo":              self._kayit_no or f"M-{uuid.uuid4().hex[:10].upper()}",
            "EkipmanNo":            self._ekipman_no,
            "FMuayeneTarihi":       self.dt_fiziksel.date().toString("yyyy-MM-dd"),
            "FizikselDurum":        self.cmb_fiziksel.currentText(),
            "SMuayeneTarihi":       self.dt_skopi.date().toString("yyyy-MM-dd"),
            "SkopiDurum":           self.cmb_skopi.currentText(),
            "Aciklamalar":          self.cmb_aciklama_panel.currentText().strip(),
            "KontrolEdenUnvani":    self.cmb_kontrol.currentText().strip(),
            "BirimSorumlusuUnvani": self.cmb_sorumlu.currentText().strip(),
            "Notlar":               self.txt_notlar.toPlainText().strip(),
            "Rapor":                "",
        }

    # ─── Sinyal işleyiciler ──────────────────────────────

    def _on_ekipman_kaydet(self):
        veri = self._veri_ekipman()
        if not veri:
            hata_goster(self, "Ekipman No zorunludur.")
            return
        self.ekipman_kaydet.emit(veri)

    def _on_ekipman_sil(self):
        if self._ekipman_no:
            self.ekipman_sil.emit(self._ekipman_no)

    def _on_muayene_kaydet(self):
        self.muayene_kaydet.emit(self._veri_muayene())

    def _on_muayene_sil(self):
        if self._kayit_no:
            self.muayene_sil.emit(self._kayit_no)


# ═══════════════════════════════════════════════════════════
#  ANA SAYFA
# ═══════════════════════════════════════════════════════════

class RKEPage(QWidget):
    """
    Birleşik RKE sayfası.
    rke_merkez.py'de ENVANTER sekmesi yerine kullanılır.
    """

    def __init__(self, db=None, action_guard=None, parent=None,
                 kullanici_adi: Optional[str] = None):
        super().__init__(parent)
        self.setProperty("bg-role", "page")
        self._db            = db
        self._action_guard  = action_guard
        self._kullanici_adi = kullanici_adi
        self._all_data: list[dict] = []

        self._search_timer = QTimer(self)
        self._search_timer.setInterval(250)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._apply_filters)

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

        icerik = QHBoxLayout()
        icerik.setContentsMargins(0, 0, 0, 0)
        icerik.setSpacing(0)

        sol = QWidget()
        sol_lay = QVBoxLayout(sol)
        sol_lay.setContentsMargins(0, 0, 0, 0)
        sol_lay.setSpacing(0)
        sol_lay.addWidget(self._build_table(), 1)
        sol_lay.addWidget(self._build_footer())
        icerik.addWidget(sol, 1)

        self._panel = _SagPanel()
        icerik.addWidget(self._panel)

        wrap = QWidget()
        wrap.setLayout(icerik)
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

        # Durum filtre butonları
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

        self.btn_yeni_ekipman = QPushButton(" Yeni Ekipman")
        self.btn_yeni_ekipman.setProperty("style-role", "action")
        self.btn_yeni_ekipman.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_yeni_ekipman, "plus", color=IconColors.PRIMARY, size=14)
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self.btn_yeni_ekipman, "rke.write")
        lay.addWidget(self.btn_yeni_ekipman)

        self.btn_muayene = QPushButton(" Muayene Ekle")
        self.btn_muayene.setProperty("style-role", "secondary")
        self.btn_muayene.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_muayene.setEnabled(False)
        IconRenderer.set_button_icon(self.btn_muayene, "clipboard", color=IconColors.MUTED, size=14)
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self.btn_muayene, "rke.write")
        lay.addWidget(self.btn_muayene)

        self.btn_toplu = QPushButton(" Toplu Muayene")
        self.btn_toplu.setProperty("style-role", "secondary")
        self.btn_toplu.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_toplu.setEnabled(False)
        IconRenderer.set_button_icon(self.btn_toplu, "users", color=IconColors.MUTED, size=14)
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self.btn_toplu, "rke.write")
        lay.addWidget(self.btn_toplu)

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
            ("cmb_abd",   "Ana Bilim Dalı", 300),
            ("cmb_birim", "Birim",          250),
            ("cmb_cins",  "Cins",           200),
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
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
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
        for cmb in (self.cmb_abd, self.cmb_birim, self.cmb_cins):
            cmb.currentIndexChanged.connect(lambda _: self._apply_filters())
        self.btn_yenile.clicked.connect(self.load_data)
        self.btn_yeni_ekipman.clicked.connect(self._on_yeni_ekipman)
        self.btn_muayene.clicked.connect(self._on_muayene_ekle)
        self.btn_toplu.clicked.connect(self._on_toplu_muayene)
        self.table.doubleClicked.connect(self._on_double_click)
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self._panel.ekipman_kaydet.connect(self._on_ekipman_kaydet)
        self._panel.ekipman_sil.connect(self._on_ekipman_sil)
        self._panel.muayene_kaydet.connect(self._on_muayene_kaydet)
        self._panel.muayene_sil.connect(self._on_muayene_sil)
        self._panel.kapat_istendi.connect(self._panel.kapat)

    # ─── Veri ────────────────────────────────────────────

    def load_data(self):
        if not self._db:
            return
        try:
            svc = get_rke_service(self._db)
            sonuc = svc.get_rke_listesi()
            self._all_data = (sonuc.veri or []) if sonuc.basarili else []

            try:
                sabitler = svc._r.get("Sabitler").get_all() or []

                def liste(kod): return sorted({
                    str(r.get("MenuEleman","")).strip()
                    for r in sabitler
                    if str(r.get("Kod","")).strip() == kod
                    and str(r.get("MenuEleman","")).strip()
                })
                def kisa(kod): return {
                    str(r.get("MenuEleman","")).strip():
                    str(r.get("Aciklama","")).strip()
                    for r in sabitler
                    if str(r.get("Kod","")).strip() == kod
                }
                self._panel.sabitler = {
                    "_liste_abd":   liste("AnaBilimDali"),
                    "_liste_birim": liste("Birim"),
                    "_liste_cins":  liste("Koruyucu_Cinsi"),
                    "_liste_beden": liste("Beden") or _BEDEN_SECENEKLER,
                    "AnaBilimDali":  kisa("AnaBilimDali"),
                    "Birim":         kisa("Birim"),
                    "KoruyucuCinsi": kisa("Koruyucu_Cinsi"),
                }
                kontrol = liste("KontrolEden")
                sorumlu = liste("BirimSorumlusu") or kontrol
                aciklama = liste("RKE_Teknik")
                if self._kullanici_adi and self._kullanici_adi not in kontrol:
                    kontrol.insert(0, self._kullanici_adi)
                self._panel.kontrol_listesi   = kontrol
                self._panel.sorumlu_listesi   = sorumlu
                self._panel.aciklama_listesi  = aciklama
                self._panel.rke_listesi       = self._all_data
                self._panel.panel_combolarini_doldur()
                if self._kullanici_adi:
                    self._panel._set_cmb(
                        self._panel.cmb_kontrol, self._kullanici_adi
                    )
            except Exception as e:
                logger.debug(f"RKE sabitler: {e}")

        except Exception as e:
            logger.error(f"RKE load_data: {e}")
            self._all_data = []

        self._fill_combos()
        self._apply_filters()

    def _fill_combos(self):
        def uniq(key):
            return sorted({str(r.get(key,"")) for r in self._all_data if r.get(key,"")})
        for cmb, key in [(self.cmb_abd,"AnaBilimDali"),
                         (self.cmb_birim,"Birim"),
                         (self.cmb_cins,"KoruyucuCinsi")]:
            cur = cmb.currentText()
            cmb.blockSignals(True)
            cmb.clear(); cmb.addItem("Tümü"); cmb.addItems(uniq(key))
            idx = cmb.findText(cur)
            if idx >= 0: cmb.setCurrentIndex(idx)
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
            filtered = [r for r in filtered if str(r.get("Durum","")).strip() == aktif]
        for cmb, key in [(self.cmb_abd,"AnaBilimDali"),
                         (self.cmb_birim,"Birim"),
                         (self.cmb_cins,"KoruyucuCinsi")]:
            val = cmb.currentText()
            if val and val != "Tümü":
                filtered = [r for r in filtered if str(r.get(key,"")).strip() == val]
        self._model.set_data(filtered)
        self._proxy.setFilterFixedString(self.inp_arama.text().strip())
        self.lbl_info.setText(f"{self._proxy.rowCount()} kayıt")

    # ─── Seçim yönetimi ──────────────────────────────────

    def _on_selection_changed(self, *_):
        sel = self.table.selectionModel().selectedRows()
        n = len(sel)
        self.btn_muayene.setEnabled(n == 1)
        self.btn_toplu.setEnabled(n >= 2)

    def _secili_row(self) -> Optional[dict]:
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            return None
        src = self._proxy.mapToSource(sel[0])
        return self._model.get_row(src.row())

    def _secili_ekipman_nolari(self) -> list[str]:
        ekipmanlar = []
        for idx in self.table.selectionModel().selectedRows():
            src = self._proxy.mapToSource(idx)
            row = self._model.get_row(src.row())
            if row:
                ekipmanlar.append(str(row.get("EkipmanNo", "")))
        return sorted(set(ekipmanlar))

    # ─── Buton işleyiciler ───────────────────────────────

    def _on_yeni_ekipman(self):
        self._panel.yeni_ekipman()

    def _on_double_click(self, idx):
        if not idx.isValid():
            return
        src = self._proxy.mapToSource(idx)
        row = self._model.get_row(src.row())
        if row:
            self._panel.duzenle_ekipman(row)

    def _on_muayene_ekle(self):
        row = self._secili_row()
        if not row:
            return
        no = str(row.get("EkipmanNo", ""))
        bilgi = f"{no}  |  {row.get('KoruyucuCinsi','')}  {row.get('Birim','')}".strip(" |")
        self._panel.yeni_muayene(no, bilgi)

    def _on_toplu_muayene(self):
        ekipmanlar = self._secili_ekipman_nolari()
        if len(ekipmanlar) < 2:
            return
        from ui.pages.rke.components.toplu_muayene_dialog import TopluMuayeneDialog
        dlg = TopluMuayeneDialog(
            db=self._db,
            ekipmanlar=ekipmanlar,
            kontrol_listesi=self._panel.kontrol_listesi,
            aciklama_listesi=self._panel.aciklama_listesi,
            kullanici_adi=self._kullanici_adi,
            parent=self,
        )
        if dlg.exec() == dlg.DialogCode.Accepted:
            self.load_data()

    # ─── Panel kaydet / sil ──────────────────────────────

    def _on_ekipman_kaydet(self, veri: dict):
        if not self._db:
            return
        try:
            svc = get_rke_service(self._db)
            if self._panel.inp_ekipman_no.isReadOnly():
                sonuc = svc.rke_guncelle(veri["EkipmanNo"], veri)
            else:
                sonuc = svc.rke_ekle(veri)
            if sonuc.basarili:
                bilgi_goster(self, sonuc.mesaj)
                self._panel.kapat()
                self.load_data()
            else:
                hata_goster(self, sonuc.mesaj)
        except Exception as e:
            hata_goster(self, str(e))

    def _on_ekipman_sil(self, ekipman_no: str):
        if not soru_sor(self, f"<b>{ekipman_no}</b> silinsin mi?"):
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

    def _on_muayene_kaydet(self, veri: dict):
        if not self._db:
            return
        try:
            svc = get_rke_service(self._db)
            if self._panel._kayit_no:
                sonuc = svc.muayene_guncelle(veri["KayitNo"], veri)
            else:
                sonuc = svc.muayene_ekle(veri)
            if sonuc.basarili:
                bilgi_goster(self, sonuc.mesaj)
                self._panel.kapat()
                self.load_data()
            else:
                hata_goster(self, sonuc.mesaj)
        except Exception as e:
            hata_goster(self, str(e))

    def _on_muayene_sil(self, kayit_no: str):
        if not soru_sor(self, f"<b>{kayit_no}</b> muayene kaydı silinsin mi?"):
            return
        try:
            svc = get_rke_service(self._db)
            sonuc = svc.muayene_sil(kayit_no)
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

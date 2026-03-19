# -*- coding: utf-8 -*-
"""RKE Envanter Yönetimi — merkezi temaya göre tasarım."""
import sys
import time
from typing import Any, List, Dict, Optional
from datetime import datetime

from PySide6.QtCore  import Qt, QDate, QThread, Signal, QAbstractTableModel, QModelIndex
from PySide6.QtWidgets import (
    QGroupBox,
    QWidget, QVBoxLayout, QHBoxLayout, QAbstractItemView,
    QTableView, QHeaderView, QLabel, QPushButton, QComboBox,
    QDateEdit, QLineEdit, QTextEdit, QProgressBar, QScrollArea,
    QFrame, QGridLayout, QSizePolicy, QApplication, QMessageBox,
)
from PySide6.QtGui import QColor, QCursor

from core.di import get_rke_service as _get_rke_service
from core.hata_yonetici import hata_goster, bilgi_goster, uyari_goster
from ui.components.base_table_model import BaseTableModel
from ui.styles.colors import DarkTheme
from ui.styles.icons import IconRenderer, IconColors


# ── ORTAK STİL STRİNGLERİ ────────────────────────────────────────
# _S_PAGE kaldırıldı — global QSS kuralı geçerli
# _S_INPUT kaldırıldı — global QSS kuralı geçerli
# _S_DATE kaldırıldı — global QSS kuralı geçerli
# _S_COMBO kaldırıldı — global QSS kuralı geçerli
# _S_TEXTEDIT kaldırıldı — global QSS kuralı geçerli
# _S_TABLE kaldırıldı — global QSS kuralı geçerli
# _S_SCROLL kaldırıldı — global QSS kuralı geçerli
# _S_PBAR kaldırıldı — global QSS kuralı geçerli


# ══════════════════════════════════════════════════════════════════
#  FieldGroup — mockup'ın fgroup bileşeni
# ══════════════════════════════════════════════════════════════════
class FieldGroup(QGroupBox):
    """
    QGroupBox tabanlı grup kutusu — tema sistemiyle uyumlu.
    color parametresi başlık aksan rengini belirler.
    Arka plan ve kenarlık tema QSS tarafından otomatik uygulanır.
    """
    def __init__(self, title: str, color: str = "", parent=None):
        super().__init__(title, parent)
        # Başlık rengini sadece color özelliğiyle override et
        if color:
            self.setStyleSheet(f"QGroupBox::title {{ color: {color}; }}")
        self._bl = QVBoxLayout(self)
        self._bl.setContentsMargins(10, 10, 10, 12)
        self._bl.setSpacing(8)

    def add_widget(self, w): self._bl.addWidget(w)
    def add_layout(self, l): self._bl.addLayout(l)
    def body_layout(self) -> QVBoxLayout: return self._bl



# ══════════════════════════════════════════════════════════════════
#  YARDIMCIlar - Sabitler
# ══════════════════════════════════════════════════════════════════
def _load_sabitler_from_db(db) -> Dict:
    """Sabitler tablosundan verileri registry üzerinden oku ve kısaltma map'ini döndür."""
    if not db:
        return {}
    try:
        from core.di import get_registry
        sabitler = get_registry(db).get("Sabitler").get_all() or []

        maps = {"AnaBilimDali": {}, "Birim": {}, "Koruyucu_Cinsi": {}, "Beden": {}}

        for row in sabitler:
            kod    = str(row.get("Kod") or "").strip()
            eleman = str(row.get("MenuEleman") or "").strip()
            kis    = str(row.get("Aciklama") or "").strip()

            if kod and eleman and kis and kod in maps:
                maps[kod][eleman] = kis

        return maps
    except Exception as e:
        from core.logger import logger
        logger.error(f"Sabitler yüklenirken hata: {e}")
        return {}


# ══════════════════════════════════════════════════════════════════
#  TABLO MODELİ
# ══════════════════════════════════════════════════════════════════
_COLS = [
    ("EkipmanNo",        "EKİPMAN NO",  120),
    ("KoruyucuNumarasi", "KORUYUCU NO", 140),
    ("AnaBilimDali",     "ABD",         110),
    ("Birim",            "BİRİM",       110),
    ("KoruyucuCinsi",    "CİNS",        110),
    ("KursunEsdegeri",   "Pb",           70),
    ("HizmetYili",       "YIL",          60),
    ("Bedeni",           "BEDEN",        70),
    ("KontrolTarihi",    "KONTROL T.",  100),
    ("Durum",            "DURUM",       120),
   
]
_CK = [c[0] for c in _COLS]
_CH = [c[1] for c in _COLS]
_CW = [c[2] for c in _COLS]

VT_COLS = [
    "KayitNo","EkipmanNo","KoruyucuNumarasi","AnaBilimDali","Birim",
    "KoruyucuCinsi","KursunEsdegeri","HizmetYili","Bedeni","KontrolTarihi",
    "Durum","Açiklama","Varsa_Demirbaş_No","KayitTarih"
]


class RKETableModel(BaseTableModel):
    def __init__(self, rows=None, parent=None):
        super().__init__(_COLS, rows, parent)

    def _display(self, key, row):
        return str(row.get(key, ""))

    def _fg(self, key, row):
        if key == "Durum":
            v = row.get(key, "")
            if "Değil" in v or "Hurda" in v:
                return QColor(DarkTheme.STATUS_ERROR)
            if "Uygun" in v:
                return QColor(DarkTheme.STATUS_SUCCESS)
            if "Tamirde" in v:
                return QColor(DarkTheme.STATUS_WARNING)
        return None

    def _align(self, key):
        if key in ("KontrolTarihi", "HizmetYili", "Durum", "KursunEsdegeri", "Bedeni"):
            return Qt.AlignmentFlag.AlignCenter
        return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft

    def set_rows(self, rows):
        self.set_data(rows)

    def get_row(self, idx) -> Optional[Dict]:
        return self._data[idx] if 0 <= idx < len(self._data) else None


class _GecmisModel(BaseTableModel):
    _K = ["Tarih","Sonuç","Açıklama"]
    _H = ["TARİH","SONUÇ","AÇIKLAMA"]
    _COLS = [("Tarih", "TARİH"), ("Sonuç", "SONUÇ"), ("Açıklama", "AÇIKLAMA")]

    def __init__(self, parent=None):
        super().__init__(self._COLS, [], parent)

    def _display(self, key, row):
        return str(row.get(key, ""))

    def _fg(self, key, row):
        if key == "Sonuç":
            v = row.get("Sonuç", "")
            if "Değil" in v:
                return QColor(DarkTheme.STATUS_ERROR)
            if "Uygun" in v:
                return QColor(DarkTheme.STATUS_SUCCESS)
        return None

    def set_rows(self, rows):
        self.set_data(rows)


# ══════════════════════════════════════════════════════════════════
#  ANA PENCERE
# ══════════════════════════════════════════════════════════════════
class RKEYonetimPenceresi(QWidget):
    def __init__(self, db=None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._action_guard = action_guard
        self.setWindowTitle("RKE Envanter Yönetimi")
        self.resize(1280, 840)
        # setStyleSheet kaldırıldı (_S_PAGE) — global QSS

        self.sabitler: Dict          = {}
        self.rke_listesi: List[Dict] = []
        self.muayene_listesi: List[Dict] = []
        self.secili_ekipman_no       = None
        self.inputs: Dict[str, Any] = {}
        self._kpi: Dict[str, QLabel]    = {}
        
        # Servis katmanı
        self._rke_svc = _get_rke_service(self._db) if self._db else None
        self._sabitler_cache = {}

        self._setup_ui()
        # YetkiYoneticisi.uygula(self, "rke_yonetim")  # TODO: Yetki sistemi entegrasyonu

    # ─────────────────────────────────────────────────────────────
    #  ANA LAYOUT
    # ─────────────────────────────────────────────────────────────
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._mk_kpi_bar())
        root.addWidget(self._mk_body(), 1)

    # ─────────────────────────────────────────────────────────────
    #  KPI ŞERIDI
    # ─────────────────────────────────────────────────────────────
    def _mk_kpi_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(68)
        bar.setProperty("bg-role", "page")
        hl = QHBoxLayout(bar)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(1)

        specs = [
            ("toplam",  "TOPLAM EKİPMAN", "0", DarkTheme.ACCENT),
            ("uygun",   "KULLANIMA UYGUN","0", DarkTheme.STATUS_SUCCESS),
            ("uygun_d", "UYGUN DEĞİL",    "0", DarkTheme.STATUS_ERROR),
            ("hurda",   "HURDA",          "0", DarkTheme.STATUS_WARNING),
            ("tamirde", "TAMİRDE",        "0", DarkTheme.TEXT_MUTED),
        ]
        for key, title, val, color in specs:
            hl.addWidget(self._mk_kpi_card(key, title, val, color), 1)
        return bar

    def _mk_kpi_card(self, key, title, val, color) -> QWidget:
        w = QWidget()
        w.setProperty("bg-role", "page")
        hl = QHBoxLayout(w)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)

        accent = QFrame()
        accent.setFixedWidth(3)
        # tema otomatik — accent
        hl.addWidget(accent)

        content = QWidget()
        content.setProperty("bg-role", "page")
        vl = QVBoxLayout(content)
        vl.setContentsMargins(14, 8, 14, 8)
        vl.setSpacing(2)

        lt = QLabel(title)
        lt.setProperty("color-role", "muted")
        lv = QLabel(val)
        lv.setStyleSheet(f"color:{color};background:transparent;font-size:20px;font-weight:700;")
        vl.addWidget(lt)
        vl.addWidget(lv)
        hl.addWidget(content, 1)
        self._kpi[key] = lv
        return w

    # ─────────────────────────────────────────────────────────────
    #  GÖVDE (liste | form)
    # ─────────────────────────────────────────────────────────────
    def _mk_body(self) -> QWidget:
        w = QWidget(); w.setProperty("bg-role", "page");
        hl = QHBoxLayout(w); hl.setContentsMargins(0,0,0,0); hl.setSpacing(0)
        hl.addWidget(self._mk_list_panel(), 1)
        sep = QFrame(); sep.setFixedWidth(1)
        sep.setProperty("bg-role", "separator")
        hl.addWidget(sep)
        self._form_panel = self._mk_form_panel()
        self._form_panel.setFixedWidth(390)
        hl.addWidget(self._form_panel)
        return w

    # ─────────────────────────────────────────────────────────────
    #  FORM PANELİ
    # ─────────────────────────────────────────────────────────────
    def _mk_form_panel(self) -> QWidget:
        panel = QWidget()
        panel.setProperty("bg-role", "page")
        vl = QVBoxLayout(panel); vl.setContentsMargins(0,0,0,0); vl.setSpacing(0)

        # Panel başlık çubuğu
        hdr = QWidget(); hdr.setFixedHeight(36)
        hdr.setProperty("bg-role", "page")
        hh = QHBoxLayout(hdr); hh.setContentsMargins(14,0,14,0)
        t1 = QLabel("EKİPMAN FORMU")
        t1.setProperty("color-role", "muted")
        t1.setProperty("color-role", "muted")  # monospace tema QSS ile
        self._lbl_mode = QLabel("YENİ KAYIT")
        self._lbl_mode.setProperty("style-role", "warning")
        hh.addWidget(t1); hh.addStretch(); hh.addWidget(self._lbl_mode)
        vl.addWidget(hdr)

        # Scroll form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        # setStyleSheet kaldırıldı (_S_SCROLL) — global QSS

        inner = QWidget()
        il = QVBoxLayout(inner)
        il.setContentsMargins(12, 12, 12, 20)
        il.setSpacing(10)

        # ── Kimlik Bilgileri ─────────────────────────────────────
        grp_id = FieldGroup("Kimlik Bilgileri", DarkTheme.STATUS_WARNING)
        g = QGridLayout(); g.setContentsMargins(0,0,0,0)
        g.setHorizontalSpacing(10); g.setVerticalSpacing(6)
        
        # Hidden KayitNo (arka planda kullanılacak)
        hidden_kayitno = self._input(ro=True)
        hidden_kayitno.setVisible(False)
        self.inputs["KayitNo"] = hidden_kayitno
        
        self._add_row(g, 0, "EKİPMAN NO", "EkipmanNo",        ro=True)
        self._add_row(g, 1, "KORUYUCU NO","KoruyucuNumarasi",  ro=True)
        self._add_row(g, 2, "DEMİRBAŞ NO","Varsa_Demirbaş_No")
        grp_id.add_layout(g); il.addWidget(grp_id)

        # ── Ekipman Özellikleri ──────────────────────────────────
        grp_oz = FieldGroup("Ekipman Özellikleri", DarkTheme.STATUS_SUCCESS)
        g2 = QGridLayout(); g2.setContentsMargins(0,0,0,0)
        g2.setHorizontalSpacing(10); g2.setVerticalSpacing(6)
        self._add_combo_row(g2, 0, "ANA BİLİM DALI", "AnaBilimDali")
        self.inputs["AnaBilimDali"].currentIndexChanged.connect(self.kod_hesapla)
        self._add_combo_row(g2, 1, "BİRİM", "Birim")
        self.inputs["Birim"].currentIndexChanged.connect(self.kod_hesapla)
        self._add_combo_row(g2, 2, "KORUYUCU CİNSİ", "KoruyucuCinsi")
        self.inputs["KoruyucuCinsi"].currentIndexChanged.connect(self.kod_hesapla)

        g2.addWidget(self._lbl("KURŞUN EŞDEĞERİ"),  6, 0)
        g2.addWidget(self._lbl("BEDEN"),             6, 1)
        cmb_pb = self._combo(); cmb_pb.setEditable(True)
        cmb_pb.addItems(["0.25 mmPb","0.35 mmPb","0.50 mmPb","1.0 mmPb"])
        cmb_bd = self._combo()
        g2.addWidget(cmb_pb, 7, 0); g2.addWidget(cmb_bd, 7, 1)
        self.inputs["KursunEsdegeri"] = cmb_pb
        self.inputs["Beden"]          = cmb_bd

        g2.addWidget(self._lbl("HİZMET YILI"), 8, 0, 1, 2)
        dt_yil = self._date(); dt_yil.setDisplayFormat("yyyy")
        g2.addWidget(dt_yil, 9, 0, 1, 2)
        self.inputs["HizmetYili"] = dt_yil

        grp_oz.add_layout(g2); il.addWidget(grp_oz)

        # ── Durum ve Geçmiş ──────────────────────────────────────
        grp_dur = FieldGroup("Durum ve Geçmiş", DarkTheme.STATUS_ERROR)
        g3 = QGridLayout(); g3.setContentsMargins(0,0,0,0)
        g3.setHorizontalSpacing(10); g3.setVerticalSpacing(6)
        
        # KAYIT TARİHİ (salt okunur)
        g3.addWidget(self._lbl("KAYIT TARİHİ"), 0, 0)
        lbl_kayit = self._value_label()
        g3.addWidget(lbl_kayit, 1, 0)
        self.inputs["KayitTarih"] = lbl_kayit
        
        # SON KONTROL (salt okunur)
        g3.addWidget(self._lbl("SON KONTROL"), 0, 1)
        lbl_kontrol = self._value_label()
        g3.addWidget(lbl_kontrol, 1, 1)
        self.inputs["KontrolTarihi"] = lbl_kontrol
        
        # GÜNCEL DURUM (salt okunur)
        g3.addWidget(self._lbl("GÜNCEL DURUM"), 2, 0, 1, 2)
        lbl_durum = self._value_label()
        g3.addWidget(lbl_durum, 3, 0, 1, 2)
        self.inputs["Durum"] = lbl_durum
        
        # AÇIKLAMA (salt okunur)
        g3.addWidget(self._lbl("AÇIKLAMA"), 4, 0, 1, 2)
        lbl_aciklama = self._value_label()
        lbl_aciklama.setFixedHeight(70)
        lbl_aciklama.setWordWrap(True)
        lbl_aciklama.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        lbl_aciklama.setProperty("bg-role", "input")
        g3.addWidget(lbl_aciklama, 5, 0, 1, 2)
        self.inputs["Açiklama"] = lbl_aciklama
        
        grp_dur.add_layout(g3); il.addWidget(grp_dur)

        # ── Muayene Geçmişi ───────────────────────────────────────
        grp_gec = FieldGroup("Muayene Geçmişi", DarkTheme.RKE_PURP)
        self._gecmis_model = _GecmisModel()
        tbl = QTableView()
        tbl.setModel(self._gecmis_model)
        # setStyleSheet kaldırıldı (_S_TABLE) — global QSS
        tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.verticalHeader().setVisible(False)
        tbl.setShowGrid(False); tbl.setAlternatingRowColors(True)
        tbl.setFixedHeight(120)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        grp_gec.add_widget(tbl); il.addWidget(grp_gec)
        il.addStretch()

        scroll.setWidget(inner); vl.addWidget(scroll, 1)

        # Progress bar
        self.pbar = QProgressBar()
        self.pbar.setVisible(False); self.pbar.setFixedHeight(2)
        # setStyleSheet kaldırıldı (_S_PBAR) — global QSS
        vl.addWidget(self.pbar)

        # Butonlar
        br = QHBoxLayout(); br.setContentsMargins(12,8,12,12); br.setSpacing(8)
        self.btn_temizle = self._btn("↺  TEMİZLE / YENİ", "secondary")
        self.btn_temizle.clicked.connect(self.temizle)
        self.btn_kaydet  = self._btn("KAYDET", "primary")
        self.btn_kaydet.clicked.connect(self.kaydet)
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self.btn_kaydet, "cihaz.write")
        br.addWidget(self.btn_temizle); br.addWidget(self.btn_kaydet)
        vl.addLayout(br)
        return panel

    # ─────────────────────────────────────────────────────────────
    #  LİSTE PANELİ
    # ─────────────────────────────────────────────────────────────
    def _mk_list_panel(self) -> QWidget:
        panel = QWidget(); panel.setProperty("bg-role", "page");
        vl = QVBoxLayout(panel); vl.setContentsMargins(0,0,0,0); vl.setSpacing(0)

        # Filtre çubuğu
        fbar = QWidget(); fbar.setFixedHeight(46)
        fbar.setProperty("bg-role", "page")
        fl = QHBoxLayout(fbar); fl.setContentsMargins(12,0,12,0); fl.setSpacing(8)

        self.cmb_filtre_abd = self._combo(width=170)
        self.cmb_filtre_abd.addItem("Tüm ABD")
        self.cmb_filtre_abd.currentIndexChanged.connect(self.tabloyu_filtrele)

        self.cmb_filtre_dur = self._combo(width=160)
        self.cmb_filtre_dur.addItems(["Tüm Durumlar","Kullanıma Uygun","Kullanıma Uygun Değil","Hurda","Tamirde"])
        self.cmb_filtre_dur.currentIndexChanged.connect(self.tabloyu_filtrele)

        self.txt_ara = QLineEdit()
        self.txt_ara.setFixedHeight(28); self.txt_ara.setPlaceholderText("⌕  Ara...")
        self.txt_ara.textChanged.connect(self.tabloyu_filtrele)

        btn_yenile = QPushButton("")
        btn_yenile.setFixedSize(28,28)
        btn_yenile.setProperty("style-role", "refresh")
        btn_yenile.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(btn_yenile, "refresh", color=IconColors.MUTED, size=14)
        btn_yenile.clicked.connect(self.load_data)

        fl.addWidget(self.cmb_filtre_abd); fl.addWidget(self.cmb_filtre_dur)
        fl.addWidget(self.txt_ara, 1); fl.addWidget(btn_yenile)
        vl.addWidget(fbar)

        # Tablo
        self._model = RKETableModel()
        self.tablo = QTableView()
        self.tablo.setModel(self._model)
        # setStyleSheet kaldırıldı (_S_TABLE) — global QSS
        self.tablo.setAlternatingRowColors(True)
        self.tablo.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tablo.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tablo.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.setShowGrid(False)
        self.tablo.setSortingEnabled(True)
        hdr = self.tablo.horizontalHeader()
        for i, w in enumerate(_CW):
            hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch if i == 2 else QHeaderView.ResizeMode.Interactive)
            if i != 2: hdr.resizeSection(i, w)
        self.tablo.doubleClicked.connect(self._on_double_click)
        vl.addWidget(self.tablo, 1)

        # Footer
        foot = QWidget(); foot.setFixedHeight(30)
        foot.setProperty("bg-role", "page")
        foot.setProperty("border-role", "top")
        fl2 = QHBoxLayout(foot); fl2.setContentsMargins(12,0,12,0)
        self.lbl_sayi = QLabel("0 kayıt")
        self.lbl_sayi.setProperty("color-role", "muted")
        self.lbl_sayi.setProperty("color-role", "muted")  # monospace tema QSS ile
        fl2.addStretch(); fl2.addWidget(self.lbl_sayi)
        vl.addWidget(foot)
        return panel

    # ─────────────────────────────────────────────────────────────
    #  UI YARDIMCILARI
    # ─────────────────────────────────────────────────────────────
    def _lbl(self, text) -> QLabel:
        l = QLabel(text)
        l.setProperty("color-role", "muted")
        l.setProperty("color-role", "muted")  # monospace tema QSS ile
        return l

    def _value_label(self, text="—") -> QLabel:
        """Salt okunur veri gösterimi için label."""
        l = QLabel(text)
        l.setFixedHeight(28)
        l.setProperty("bg-role", "panel")
        return l

    def _input(self, ro=False) -> QLineEdit:
        w = QLineEdit(); w.setFixedHeight(28)
        if ro: w.setReadOnly(True)
        return w

    def _combo(self, width=None) -> QComboBox:
        w = QComboBox(); w.setFixedHeight(28)
        if width: w.setMinimumWidth(width)
        return w

    def _date(self) -> QDateEdit:
        w = QDateEdit(); w.setCalendarPopup(True)
        w.setDisplayFormat("yyyy-MM-dd"); w.setDate(QDate.currentDate())
        w.setFixedHeight(28)
        return w

    def _btn(self, text, style="secondary") -> QPushButton:
        b = QPushButton(text); b.setFixedHeight(34)
        b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        if style == "primary":
            b.setProperty("style-role", "success-filled")
        else:
            b.setProperty("style-role", "secondary")
        return b

    def _add_row(self, grid, row, label, key, ro=False):
        grid.addWidget(self._lbl(label), row*2, 0, 1, 2)
        w = self._input(ro)
        grid.addWidget(w, row*2+1, 0, 1, 2)
        self.inputs[key] = w

    def _add_row2(self, grid, row, label1, key1, label2=None, key2=None,
                  _date=False, _date2=False):
        grid.addWidget(self._lbl(label1), row*2,   0)
        w1 = self._date() if _date  else self._input()
        grid.addWidget(w1, row*2+1, 0)
        self.inputs[key1] = w1
        if label2:
            grid.addWidget(self._lbl(label2), row*2, 1)
            w2 = self._date() if _date2 else self._input()
            grid.addWidget(w2, row*2+1, 1)
            if key2:
                self.inputs[key2] = w2

    def _add_combo_row(self, grid, row, label, key):
        grid.addWidget(self._lbl(label), row*2, 0, 1, 2)
        w = self._combo(); grid.addWidget(w, row*2+1, 0, 1, 2)
        self.inputs[key] = w

    # ─────────────────────────────────────────────────────────────
    #  KPI GÜNCELLEME
    # ─────────────────────────────────────────────────────────────
    def _update_kpi(self, rows: List[Dict]):
        c = {"toplam":len(rows),"uygun":0,"uygun_d":0,"hurda":0,"tamirde":0}
        for r in rows:
            d = r.get("Durum","")
            if "Değil" in d: c["uygun_d"] += 1
            elif "Uygun" in d: c["uygun"] += 1
            elif "Hurda" in d: c["hurda"] += 1
            elif "Tamirde" in d: c["tamirde"] += 1
        for k, v in c.items():
            if k in self._kpi: self._kpi[k].setText(str(v))

    # ─────────────────────────────────────────────────────────────
    #  MANTIK
    # ─────────────────────────────────────────────────────────────
    def load_data(self):
        """Ana pencereden çağrılan public veri yükleme metodu."""
        if not self._rke_svc:
            uyari_goster(self, "Veritabanı bağlantısı kurulamadı.")
            return

        try:
            # Sabitler yükle
            self.sabitler = _load_sabitler_from_db(self._db)

            # RKE listesi
            sonuc = self._rke_svc.get_rke_listesi()
            if not sonuc.basarili:
                hata_goster(self, sonuc.mesaj)
                return
            self.rke_listesi = sonuc.veri or []

            # Muayene listesi
            m_sonuc = self._rke_svc.get_muayene_listesi()
            if m_sonuc.basarili:
                self.muayene_listesi = m_sonuc.veri or []

            # Combo'ları doldur
            self._populate_combos()

            # Tabloyu filtrele
            self.tabloyu_filtrele()

        except Exception as e:
            from core.logger import logger
            logger.error(f"Veri yükleme hatası: {e}")
            hata_goster(self, f"Veri yüklenirken hata: {e}")
    
    def _populate_combos(self):
        """Combo kutularını sabitlerden doldur."""
        def fill(ui_key, db_key):
            w = self.inputs.get(ui_key)
            if not isinstance(w, QComboBox): return
            w.blockSignals(True); w.clear(); w.addItem("")
            d = self.sabitler.get(db_key, {})
            items = sorted(d.keys() if isinstance(d, dict) else d)
            w.addItems(items); w.blockSignals(False)

        fill("AnaBilimDali","AnaBilimDali")
        fill("Birim","Birim")
        fill("KoruyucuCinsi","Koruyucu_Cinsi")
        fill("Beden","Beden")

        # Filtre combo'ları
        self.cmb_filtre_abd.blockSignals(True)
        self.cmb_filtre_abd.clear(); self.cmb_filtre_abd.addItem("Tüm ABD")
        abd_d = self.sabitler.get("AnaBilimDali", {})
        self.cmb_filtre_abd.addItems(sorted(abd_d.keys() if isinstance(abd_d, dict) else abd_d))
        self.cmb_filtre_abd.blockSignals(False)

    def tabloyu_filtrele(self):
        """Filtrelere göre RKE listesini süzgecinden geçir."""
        f_abd  = self.cmb_filtre_abd.currentText()
        f_dur  = self.cmb_filtre_dur.currentText()
        ara    = self.txt_ara.text().lower()

        result = []
        for row in self.rke_listesi:
            # Filtreler
            if f_abd != "Tüm ABD" and row.get("AnaBilimDali", "") != f_abd:
                continue
            if f_dur != "Tüm Durumlar" and row.get("Durum", "") != f_dur:
                continue
            
            # Arama
            if ara:
                searchable = " ".join(str(v) for v in row.values()).lower()
                if ara not in searchable:
                    continue
            
            result.append(row)

        self._model.set_rows(result)
        self.lbl_sayi.setText(f"{len(result)} kayıt")
        self._update_kpi(result)

    def _on_double_click(self, index: QModelIndex):
        row = self._model.get_row(index.row())
        if not row: return
        self.secili_ekipman_no = row.get("EkipmanNo","")

        for key, w in self.inputs.items():
            val = row.get(key,"")
            if isinstance(w, QLineEdit): 
                w.setText(str(val) if val else "")
            elif isinstance(w, QTextEdit): 
                w.setPlainText(str(val) if val else "")
            elif isinstance(w, QComboBox): 
                w.setCurrentText(str(val) if val else "")
            elif isinstance(w, QDateEdit):
                if val:
                    try: 
                        w.setDate(QDate.fromString(str(val)[:10],"yyyy-MM-dd"))
                    except: 
                        pass
            elif isinstance(w, QLabel):  # Salt okunur label alanları
                w.setText(str(val) if val else "—")

        try:
            yil = str(row.get("HizmetYili","")).strip()
            if yil and yil.isdigit(): 
                self.inputs["HizmetYili"].setDate(QDate(int(yil),1,1))
        except: 
            pass

        # Durum ve KontrolTarihi artık label, setEnabled gereksiz
        self.btn_kaydet.setText("↑  GÜNCELLE")
        self.btn_kaydet.setProperty("style-role", "warning")
        self._lbl_mode.setText("DÜZENLEME")
        self.gecmisi_yukle(row.get("EkipmanNo",""))

    def gecmisi_yukle(self, ekipman_no: str):
        """Ekipman numarasına göre muayene geçmişini yükle."""
        if not ekipman_no or not self.muayene_listesi:
            self._gecmis_model.set_rows([])
            return
        
        rows = []
        for muayene in self.muayene_listesi:
            if str(muayene.get("EkipmanNo", "")).strip() == str(ekipman_no).strip():
                rows.append({
                    "Tarih": muayene.get("FMuayeneTarihi", ""),
                    "Sonuç": muayene.get("FizikselDurum", ""),
                    "Açıklama": muayene.get("Aciklamalar", "")
                })
        self._gecmis_model.set_rows(rows)

    def kod_hesapla(self):
        """Ekipman ve koruyucu numaralarını otomatik hesapla."""
        abd  = self.inputs["AnaBilimDali"].currentText()
        birim= self.inputs["Birim"].currentText()
        cins = self.inputs["KoruyucuCinsi"].currentText()

        def short(grp, val):
            m = self.sabitler.get(grp,{})
            return m.get(val,"UNK") if isinstance(m,dict) else "UNK"

        k_abd = short("AnaBilimDali",abd)
        k_cins= short("Koruyucu_Cinsi",cins)

        # Yeni kayıt ise ekipman no oluştur
        if not self.secili_ekipman_no and cins:
            sayac = 1 + sum(1 for r in self.rke_listesi if r.get("KoruyucuCinsi") == cins)
            self.inputs["EkipmanNo"].setText(f"RKE-{k_cins}-{sayac}")

        # Koruyucu numarası
        if birim == "Radyoloji Depo":
            self.inputs["KoruyucuNumarasi"].setText("")
        elif abd and birim and cins:
            sayac = 1 + sum(
                1 for r in self.rke_listesi
                if r.get("AnaBilimDali") == abd 
                and r.get("Birim") == birim 
                and r.get("KoruyucuCinsi") == cins
            )
            k_b = short("Birim",birim)
            self.inputs["KoruyucuNumarasi"].setText(f"{k_abd}-{k_b}-{k_cins}-{sayac}")

    def temizle(self):
        """Formu temizle ve yeni kayıt moduna geç."""
        self.secili_ekipman_no = None
        for w in self.inputs.values():
            if isinstance(w, QLineEdit):  w.clear()
            elif isinstance(w, QTextEdit): w.clear()
            elif isinstance(w, QComboBox): w.setCurrentIndex(0)
            elif isinstance(w, QDateEdit): w.setDate(QDate.currentDate())
            elif isinstance(w, QLabel): w.setText("—")
        self.inputs["KayitNo"].setText("Otomatik")
        # Durum ve KontrolTarihi artık label, setEnabled gereksiz
        self._gecmis_model.set_rows([])
        self.btn_kaydet.setText("KAYDET")
        self.btn_kaydet.setProperty("style-role", "success-filled")
        self._lbl_mode.setText("YENİ KAYIT")

    def kaydet(self):
        """RKE kaydını veritabanına kaydet (insert veya update)."""
        if self._action_guard and not self._action_guard.check_and_warn(
            self, "cihaz.write", "RKE Kaydetme"
        ):
            return
        if not self._rke_svc:
            uyari_goster(self, "Veritabanı bağlantısı kurulamadı.")
            return
        
        ekipman_no = self.inputs["EkipmanNo"].text().strip()
        if not ekipman_no:
            uyari_goster(self, "Ekipman No zorunludur.")
            return

        try:
            # Form verilerini topla
            data = {
                "EkipmanNo": ekipman_no,
                "KoruyucuNumarasi": self.inputs["KoruyucuNumarasi"].text().strip(),
                "AnaBilimDali": self.inputs["AnaBilimDali"].currentText(),
                "Birim": self.inputs["Birim"].currentText(),
                "KoruyucuCinsi": self.inputs["KoruyucuCinsi"].currentText(),
                "KursunEsdegeri": self.inputs["KursunEsdegeri"].currentText(),
                "HizmetYili": self.inputs["HizmetYili"].text(),
                "Bedeni": self.inputs["Beden"].currentText(),
                "KontrolTarihi": self.inputs["KontrolTarihi"].text(),
                "Durum": self.inputs["Durum"].text(),
                "Aciklama": self.inputs["Açiklama"].text(),
                "VarsaDemirbasNo": self.inputs.get("Varsa_Demirbaş_No", self.inputs.get("VarsaDemirbasNo", QLineEdit())).text().strip(),
                "KayitTarih": self.inputs.get("KayitTarih", QLineEdit()).text(),
                "Barkod": self.inputs.get("Barkod", QLineEdit()).text().strip(),
            }

            # Güncelleme mi, yeni kayıt mı?
            if self.secili_ekipman_no:
                sonuc = self._rke_svc.rke_guncelle(self.secili_ekipman_no, data)
            else:
                sonuc = self._rke_svc.rke_ekle(data)

            if sonuc.basarili:
                bilgi_goster(self, sonuc.mesaj)
                self.temizle()
                self.load_data()
            else:
                hata_goster(self, sonuc.mesaj)

        except Exception as e:
            from core.logger import logger
            logger.error(f"RKE kayıt hatası: {e}")
            hata_goster(self, f"Kayıt sırasında hata: {e}")







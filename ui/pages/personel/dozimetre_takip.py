# -*- coding: utf-8 -*-
"""
dozimetre_takip.py
──────────────────
Dozimetre_Olcum tablosunu görüntüleyen ve yorumlayan ana sayfa.

Özellikler
----------
• Özet kartlar     : Toplam ölçüm, benzersiz personel, rapor sayısı,
                     max Hp10, uyarı/tehlike sayısı
• Filtre çubuğu   : Yıl · Periyot · Birim · Durum · Ad/TC arama
• Ana tablo        : Tüm ölçüm kayıtları (renk kodlu Hp değerleri)
• Alt panel        : Seçili personelin geçmişi + Hp10/Hp007 trend +
                     yıllık kümülatif doz + 5 yıllık limit + periyot doluluk
• QThread loader   : UI donmaz

NDK Doz Limitleri (Radyasyon Güvenliği Yönetmeliği)
----------------------------------------------------
  Yıllık Hp(10)     : 20 mSv (5 yıl ortalaması) / max 50 mSv tek yılda
  5 yıllık toplam   : 100 mSv
  Çalışma Koşulu A  : 6 mSv/yıl eşiği
  İnceleme düzeyi   : 2 mSv/periyot (yıllık limitin 1/10'u)
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal as _Signal
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QTableView, QLineEdit, QDialog,
    QComboBox, QAbstractItemView, QSizePolicy, QSplitter,
    QTabWidget, QFormLayout, QDialogButtonBox, QMessageBox,
    QDoubleSpinBox,
)

from core.logger import logger
from ui.components.base_table_model import BaseTableModel
from ui.styles import DarkTheme
from ui.styles.icons import IconRenderer, IconColors

# ─────────────────────────────────────────────────────────────
# NDK Doz Limitleri
# ─────────────────────────────────────────────────────────────
YILLIK_LIMIT   = 20.0    # mSv — 5 yıl ortalaması üst sınırı
YILLIK_MAX     = 50.0    # mSv — tek yılda mutlak max
BES_YILLIK     = 100.0   # mSv — ardışık 5 yıl toplamı
CALISMA_A      =  6.0    # mSv — Çalışma Koşulu A eşiği
HP10_UYARI     =  2.0    # mSv — periyot inceleme düzeyi
HP10_TEHLIKE   =  5.0    # mSv — tehlike eşiği
PERIYOT_SAYISI =  4      # RADAT yılda 4 periyot
ANOMALI_KATSAYI = 3.0   # Kişisel ortalamanın kaç katı → anomali

# ─────────────────────────────────────────────────────────────
# Sütunlar
# ─────────────────────────────────────────────────────────────
MAIN_COLS = [
    ("Yil",          "Yıl",        60),
    ("Periyot",      "Per.",       40),
    ("PeriyotAdi",   "Dönem",     150),
    ("AdSoyad",      "Ad Soyad",  150),
    ("PersonelID",   "TC / ID",   110),
    ("CalistiBirim", "Birim",     130),
    ("DozimetreNo",  "Dzm. No",    75),
    ("VucutBolgesi", "Bölge",     100),
    ("Hp10",         "Hp(10)",     65),
    ("Hp007",        "Hp(0,07)",   65),
    ("Durum",        "Durum",     115),
    ("_anomali",     "⚠",          28),   # anomali bayrağı
]

GECMIS_COLS = [
    ("Yil",        "Yıl",      60),
    ("Periyot",    "Per.",     40),
    ("PeriyotAdi", "Dönem",   110),
    ("DozimetreNo","Dzm.",     90),
    ("Hp10",       "Hp(10)",   65),
    ("Hp007",      "Hp(0,07)", 65),
    ("Durum",      "Durum",   115),
]

KARS_COLS = [
    ("AdSoyad",      "Ad Soyad",     160),
    ("PersonelID",   "TC / ID",      110),
    ("CalistiBirim", "Birim",        130),
    ("hp10_p1",      "Per.1 Hp(10)",  80),
    ("hp10_p2",      "Per.2 Hp(10)",  80),
    ("fark",         "Fark",          70),
    ("degisim",      "Değişim %",     80),
]

BIRIM_COLS = [
    ("CalistiBirim", "Birim",        160),
    ("kayit_say",    "Kayıt Sayısı",  90),
    ("ort_hp10",     "Ort. Hp(10)",   80),
    ("max_hp10",     "Maks. Hp(10)",  80),
    ("oran",         "Genel Ort. Katı", 100),
    ("uyari_say",    f"≥{HP10_UYARI} mSv", 80),
    ("tehlike_say",  f"≥{HP10_TEHLIKE} mSv", 80),
]

ANOMALI_COLS = [
    ("Yil",          "Yıl",          60),
    ("Periyot",      "Per.",          40),
    ("AdSoyad",      "Ad Soyad",     160),
    ("PersonelID",   "TC / ID",      110),
    ("CalistiBirim", "Birim",        130),
    ("Hp10",         "Hp(10)",        65),
    ("kisi_ort",     "Kişi Ort.",     70),
    ("kat",          "× Ortalama",    80),
]


# ─────────────────────────────────────────────────────────────
# Yardımcı
# ─────────────────────────────────────────────────────────────
def _hp(val) -> Optional[float]:
    try:
        return float(val) if val is not None else None
    except (ValueError, TypeError):
        return None


def _hp_renk(v: float) -> QColor:
    if v >= HP10_TEHLIKE: return QColor("#f87171")
    if v >= HP10_UYARI:   return QColor("#facc15")
    return QColor("#4ade80")


# ─────────────────────────────────────────────────────────────
# Modeller
# ─────────────────────────────────────────────────────────────
class _MainModel(BaseTableModel):
    ALIGN_CENTER = frozenset({"Yil","Periyot","Hp10","Hp007","DozimetreNo","_anomali"})

    def _display(self, key: str, row: dict) -> str:
        val = row.get(key)
        if val is None: return ""
        if key == "_anomali":
            return "⚠" if row.get("_anomali") else ""
        if key in ("Hp10","Hp007"):
            v = _hp(val)
            return f"{v:.3f}" if v is not None else str(val)
        return str(val)

    def _fg(self, key: str, row: dict):
        if key == "_anomali":
            return QColor("#f97316") if row.get("_anomali") else None
        if key in ("Hp10","Hp007"):
            v = _hp(row.get(key))
            return _hp_renk(v) if v is not None else None
        if key == "PersonelID":
            pid = str(row.get("PersonelID", ""))
            return QColor("#4ade80") if pid.isdigit() else QColor("#facc15")
        if key == "Durum":
            return QColor("#f87171") if "Aşım" in str(row.get("Durum","")) else QColor("#4ade80")
        return None

    def _bg(self, key: str, row: dict):
        # Anomali satırı — hafif turuncu arka plan
        if row.get("_anomali"):
            return QColor("#f9731615")
        return None


class _GecmisModel(BaseTableModel):
    ALIGN_CENTER = frozenset({"Yil","Periyot","Hp10","Hp007","DozimetreNo"})

    def _display(self, key: str, row: dict) -> str:
        val = row.get(key)
        if val is None: return ""
        if key in ("Hp10","Hp007"):
            v = _hp(val)
            return f"{v:.3f}" if v is not None else str(val)
        return str(val)

    def _fg(self, key: str, row: dict):
        if key in ("Hp10","Hp007"):
            v = _hp(row.get(key))
            return _hp_renk(v) if v is not None else None
        if key == "Durum":
            return QColor("#f87171") if "Aşım" in str(row.get("Durum","")) else QColor("#4ade80")
        return None


class _KarsModel(BaseTableModel):
    ALIGN_CENTER = frozenset({"hp10_p1","hp10_p2","fark","degisim"})

    def _display(self, key: str, row: dict) -> str:
        val = row.get(key)
        if val is None: return "—"
        if key in ("hp10_p1","hp10_p2"):
            v = _hp(val)
            return f"{v:.3f}" if v is not None else "—"
        if key == "fark":
            v = _hp(val)
            if v is None: return "—"
            return f"{'+' if v > 0 else ''}{v:.3f}"
        if key == "degisim":
            v = _hp(val)
            if v is None: return "—"
            return f"{'+' if v > 0 else ''}{v:.1f}%"
        return str(val)

    def _fg(self, key: str, row: dict):
        if key in ("fark","degisim"):
            v = _hp(row.get(key))
            if v is None: return None
            return QColor("#f87171") if v > 0 else QColor("#4ade80")
        if key in ("hp10_p1","hp10_p2"):
            v = _hp(row.get(key))
            return _hp_renk(v) if v is not None else None
        return None


class _BirimModel(BaseTableModel):
    ALIGN_CENTER = frozenset({"kayit_say","ort_hp10","max_hp10","oran","uyari_say","tehlike_say"})

    def _display(self, key: str, row: dict) -> str:
        val = row.get(key)
        if val is None: return "—"
        if key in ("ort_hp10","max_hp10"):
            return f"{float(val):.3f}"
        if key == "oran":
            return f"{float(val):.2f}×"
        return str(val)

    def _fg(self, key: str, row: dict):
        if key == "oran":
            v = _hp(row.get("oran"))
            if v is None: return None
            if v >= 2.0: return QColor("#f87171")
            if v >= 1.5: return QColor("#facc15")
            return QColor("#4ade80")
        if key in ("ort_hp10","max_hp10"):
            v = _hp(row.get(key))
            return _hp_renk(v) if v is not None else None
        return None


class _AnomaliModel(BaseTableModel):
    ALIGN_CENTER = frozenset({"Yil","Periyot","Hp10","kisi_ort","kat"})

    def _display(self, key: str, row: dict) -> str:
        val = row.get(key)
        if val is None: return "—"
        if key in ("Hp10","kisi_ort"):
            v = _hp(val)
            return f"{v:.3f}" if v is not None else "—"
        if key == "kat":
            return f"{float(val):.1f}×"
        return str(val)

    def _fg(self, key: str, row: dict):
        if key == "kat":
            v = _hp(row.get("kat"))
            if v is None: return None
            if v >= 5.0: return QColor("#f87171")
            if v >= 3.0: return QColor("#f97316")
            return None
        if key == "Hp10":
            v = _hp(row.get("Hp10"))
            return _hp_renk(v) if v is not None else None
        return None


# ─────────────────────────────────────────────────────────────
# Trend Widget — Hp10 + Hp007 çift çizgi
# ─────────────────────────────────────────────────────────────
class _TrendWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[dict] = []
        self.setMinimumHeight(80)
        self.setMaximumHeight(100)

    def set_data(self, rows: list[dict]):
        self._rows = rows
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setFont(QFont("", 7))

        rows   = self._rows
        hp10s  = [(_hp(r.get("Hp10"))  or 0.0) for r in rows]
        hp007s = [(_hp(r.get("Hp007")) or 0.0) for r in rows]
        labels = [f"{r.get('Yil','')}-{r.get('Periyot','')}" for r in rows]

        if len(hp10s) < 2:
            p.setPen(QColor("muted"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "Trend için en az 2 periyot gerekli")
            return

        w, h = self.width(), self.height()
        pl, pr, pt, pb = 8, 8, 8, 20
        cw = w - pl - pr
        ch = h - pt - pb
        n  = len(hp10s)
        mx = max(max(hp10s), max(hp007s), HP10_UYARI + 0.1, 0.1)

        def px(i): return int(pl + i * cw / (n - 1))
        def py(v): return int(pt + ch - v / mx * ch)

        # İnceleme düzeyi eşik çizgisi
        if HP10_UYARI < mx:
            p.setPen(QPen(QColor("#facc1540"), 1, Qt.PenStyle.DashLine))
            p.drawLine(pl, py(HP10_UYARI), w - pr, py(HP10_UYARI))

        # Hp(10) — mavi, kalın
        p.setPen(QPen(QColor("accent"), 2))
        for i in range(n - 1):
            p.drawLine(px(i), py(hp10s[i]), px(i+1), py(hp10s[i+1]))
        for i, v in enumerate(hp10s):
            p.setBrush(_hp_renk(v)); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(px(i)-3, py(v)-3, 6, 6)

        # Hp(0,07) — turuncu, kesik
        p.setPen(QPen(QColor("#fb923c"), 1, Qt.PenStyle.DashLine))
        for i in range(n - 1):
            p.drawLine(px(i), py(hp007s[i]), px(i+1), py(hp007s[i+1]))
        for i, v in enumerate(hp007s):
            p.setBrush(QColor("#fb923c")); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(px(i)-2, py(v)-2, 5, 5)

        # X ekseni etiketleri
        p.setPen(QColor("muted"))
        if labels:
            p.drawText(pl, h - 4, labels[0])
            p.drawText(w - pr - 40, h - 4, labels[-1])

        # Legend
        p.setPen(QColor("accent"))
        p.drawText(w - pr - 90, pt + 10, "— Hp(10)")
        p.setPen(QColor("#fb923c"))
        p.drawText(w - pr - 90, pt + 20, "-- Hp(0,07)")


# ─────────────────────────────────────────────────────────────
# Kümülatif Doz Gauge
# ─────────────────────────────────────────────────────────────
class _GaugeWidget(QWidget):
    def __init__(self, baslik: str, limit: float,
                 esik_sari: float = 0.5, esik_kirmizi: float = 0.75,
                 parent=None):
        super().__init__(parent)
        self._baslik = baslik
        self._limit  = limit
        self._esik1  = esik_sari
        self._esik2  = esik_kirmizi
        self._deger  = 0.0
        self.setFixedHeight(46)
        self.setMinimumWidth(160)

    def set_deger(self, deger: float):
        self._deger = deger
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        oran = min(self._deger / self._limit, 1.0) if self._limit else 0.0
        w, h = self.width(), self.height()

        # Başlık
        p.setPen(QColor("muted"))
        p.setFont(QFont("", 8))
        p.drawText(0, 12, self._baslik)

        # Arka plan
        bar_y, bar_h = 18, 10
        p.setBrush(QColor(DarkTheme.BG_TERTIARY))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, bar_y, w, bar_h, 4, 4)

        # Doluluk
        if oran > 0:
            if oran >= self._esik2:   renk = QColor("#f87171")
            elif oran >= self._esik1: renk = QColor("#facc15")
            else:                     renk = QColor("#4ade80")
            p.setBrush(renk)
            p.drawRoundedRect(0, bar_y, int(w * oran), bar_h, 4, 4)

        # Değer
        p.setPen(QColor("primary"))
        p.setFont(QFont("", 8, QFont.Weight.Bold))
        metin = f"{self._deger:.2f} / {self._limit:.0f} mSv  (%{oran*100:.0f})"
        p.drawText(0, bar_y + bar_h + 14, metin)


# ─────────────────────────────────────────────────────────────
# QThread Worker
# ─────────────────────────────────────────────────────────────
class _Loader(QThread):
    finished = _Signal(list, dict)
    error    = _Signal(str)

    def __init__(self, db):
        super().__init__()
        self._db = db

    def run(self):
        try:
            from database.sqlite_manager import SQLiteManager
            from core.di import get_dozimetre_service
            from core.paths import DB_PATH

            db_path = getattr(self._db, "db_path", None) or str(self._db) if self._db else DB_PATH
            db = SQLiteManager(db_path=db_path, check_same_thread=False)
            svc = get_dozimetre_service(db)

            sonuc = svc.get_tum_olcumler()
            rows = sonuc.veri or []

            # Yıl DESC, Periyot DESC, AdSoyad sıralaması
            rows.sort(key=lambda r: (
                -(int(r.get("Yil") or 0)),
                -(int(r.get("Periyot") or 0)),
                str(r.get("AdSoyad") or ""),
            ))

            stats_sonuc = svc.get_istatistikler(
                rows,
                hp10_uyari=HP10_UYARI,
                hp10_tehlike=HP10_TEHLIKE,
                anomali_katsayi=ANOMALI_KATSAYI,
            )
            stats = stats_sonuc.veri or {}

            db.close()
            self.finished.emit(rows, stats)
        except Exception as exc:
            self.error.emit(str(exc))


# ─────────────────────────────────────────────────────────────
# Ana Sayfa
# ─────────────────────────────────────────────────────────────
class DozimetreTakipPage(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db      = db
        self._rows:   list[dict] = []
        self._filter: list[dict] = []
        self._loader: Optional[_Loader] = None
        self._build_ui()
        if db:
            self.load_data()

    # ─── UI İnşası ──────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 12)
        root.setSpacing(14)

        # Başlık
        top = QHBoxLayout()
        lbl = QLabel("Dozimetre Ölçüm Takibi")
        lbl.setProperty("style-role", "title")
        lbl.setProperty("color-role", "primary")
        self.btn_yenile = QPushButton("Yenile")
        self.btn_yenile.setProperty("style-role", "refresh")
        IconRenderer.set_button_icon(self.btn_yenile, "refresh", color=IconColors.MUTED, size=14)
        self.btn_yenile.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_yenile.clicked.connect(self.load_data)
        self.btn_import = QPushButton("Yeni Dönem Raporu")
        self.btn_import.setProperty("style-role", "action")
        IconRenderer.set_button_icon(self.btn_import, "upload", color=IconColors.PRIMARY, size=14)
        self.btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_import.clicked.connect(self._open_import)
        top.addWidget(lbl); top.addStretch()
        top.addWidget(self.btn_import); top.addWidget(self.btn_yenile)
        root.addLayout(top)

        # Özet kartlar
        stat_row = QHBoxLayout(); stat_row.setSpacing(10)
        self._s_toplam   = self._stat("Toplam Ölçüm",        "—", "accent")
        self._s_personel = self._stat("Personel",              "—", "#60a5fa")
        self._s_rapor    = self._stat("Rapor",                 "—", "#a78bfa")
        self._s_max_hp10 = self._stat("Maks. Hp(10)",         "—", "#fb923c")
        self._s_uyari    = self._stat(f"≥{HP10_UYARI} mSv",   "—", "#facc15")
        self._s_tehlike  = self._stat(f"≥{HP10_TEHLIKE} mSv", "—", "#f87171")
        self._s_anomali  = self._stat(f"⚠ Anomali (×{ANOMALI_KATSAYI:.0f})", "—", "#f97316")
        for w in (self._s_toplam, self._s_personel, self._s_rapor,
                  self._s_max_hp10, self._s_uyari, self._s_tehlike, self._s_anomali):
            stat_row.addWidget(w)
        root.addLayout(stat_row)

        # Filtre çubuğu
        ff = QFrame(); ff.setProperty("style-role", "form")
        fb = QHBoxLayout(ff); fb.setContentsMargins(12, 8, 12, 8); fb.setSpacing(8)
        self.cmb_yil     = self._cmb("Yıl")
        self.cmb_periyot = self._cmb("Periyot")
        self.cmb_birim   = self._cmb("Birim")
        self.cmb_durum   = self._cmb("Durum")
        self.inp_arama   = QLineEdit()
        self.inp_arama.setPlaceholderText("Ad / TC / ID ara...")
        self.inp_arama.setProperty("style-role", "search")
        self.inp_arama.setFixedWidth(200)
        for lbl_t, w in (("Yıl", self.cmb_yil), ("Per.", self.cmb_periyot),
                          ("Birim", self.cmb_birim), ("Durum", self.cmb_durum)):
            fb.addWidget(QLabel(lbl_t)); fb.addWidget(w)
        fb.addWidget(self.inp_arama)
        self.lbl_sonuc = QLabel("— kayıt")
        self.lbl_sonuc.setProperty("color-role", "muted")
        fb.addStretch(); fb.addWidget(self.lbl_sonuc)
        root.addWidget(ff)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(6)

        # Ana tablo
        self.table = QTableView()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setProperty("style-role", "table")
        self._main_model = _MainModel(MAIN_COLS)
        self.table.setModel(self._main_model)
        self._main_model.setup_columns(self.table, stretch_keys=["AdSoyad", "VucutBolgesi"])
        self.table.selectionModel().selectionChanged.connect(self._on_select)
        splitter.addWidget(self.table)

        # Alt panel — sekmeli
        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_gecmis_tab(),    "📊  Periyot Geçmişi & Limitler")
        self._tabs.addTab(self._build_kars_tab(),      "⚖️  Periyot Karşılaştırma")
        self._tabs.addTab(self._build_birim_tab(),     "🏗️  Birim Risk Haritası")
        self._tabs.addTab(self._build_anomali_tab(),   "⚠️  Anomali Listesi")
        self._tabs.addTab(self._build_duzelt_tab(),    "✏️  Kayıt Düzelt")
        splitter.addWidget(self._tabs)
        splitter.setSizes([420, 250])
        root.addWidget(splitter, 1)

        self.lbl_footer = QLabel("")
        self.lbl_footer.setProperty("style-role", "footer")
        root.addWidget(self.lbl_footer)

        for w in (self.cmb_yil, self.cmb_periyot, self.cmb_birim, self.cmb_durum):
            w.currentIndexChanged.connect(self._apply_filter)
        self.inp_arama.textChanged.connect(self._apply_filter)

    def _build_gecmis_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 8, 12, 8); lay.setSpacing(8)

        self.lbl_alt_baslik = QLabel("← Tabloda bir satır seçin")
        self.lbl_alt_baslik.setProperty("style-role", "section-title")
        self.lbl_alt_baslik.setProperty("color-role", "muted")
        lay.addWidget(self.lbl_alt_baslik)

        icerik = QHBoxLayout(); icerik.setSpacing(14)

        # Geçmiş tablo
        self.tbl_gecmis = QTableView()
        self.tbl_gecmis.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_gecmis.verticalHeader().setVisible(False)
        self.tbl_gecmis.setAlternatingRowColors(True)
        self.tbl_gecmis.setMaximumHeight(190)
        self.tbl_gecmis.setProperty("style-role", "table")
        self._gecmis_model = _GecmisModel(GECMIS_COLS)
        self.tbl_gecmis.setModel(self._gecmis_model)
        self._gecmis_model.setup_columns(self.tbl_gecmis, stretch_keys=["PeriyotAdi"])
        icerik.addWidget(self.tbl_gecmis, 3)

        # Sağ panel
        sag = QVBoxLayout(); sag.setSpacing(6)

        # Mini istatistik + çalışma koşulu
        self.lbl_mini_stat = QLabel("")
        self.lbl_mini_stat.setProperty("color-role", "muted")
        self.lbl_mini_stat.setWordWrap(True)
        self.lbl_mini_stat.setTextFormat(Qt.TextFormat.RichText)
        sag.addWidget(self.lbl_mini_stat)

        # Periyot doluluk uyarısı
        self.lbl_periyot_doluluk = QLabel("")
        self.lbl_periyot_doluluk.setWordWrap(True)
        sag.addWidget(self.lbl_periyot_doluluk)

        # Yıllık kümülatif gauge
        self._gauge_yillik = _GaugeWidget(
            f"Yıllık Kümülatif Hp(10)  [NDK: {YILLIK_LIMIT:.0f} mSv]",
            YILLIK_LIMIT, 0.5, 0.75
        )
        sag.addWidget(self._gauge_yillik)

        # 5 yıllık kümülatif gauge
        self._gauge_5yil = _GaugeWidget(
            f"5 Yıllık Kümülatif Hp(10)  [NDK: {BES_YILLIK:.0f} mSv]",
            BES_YILLIK, 0.5, 0.75
        )
        sag.addWidget(self._gauge_5yil)

        # Trend
        lbl_trend = QLabel("  ── Hp(10)   -- Hp(0,07)")
        lbl_trend.setProperty("color-role", "muted")
        sag.addWidget(lbl_trend)
        self._trend = _TrendWidget()
        sag.addWidget(self._trend)
        sag.addStretch()

        icerik.addLayout(sag, 2)
        lay.addLayout(icerik)
        return w

    def _cmb(self, placeholder: str) -> QComboBox:
        c = QComboBox()
        c.setProperty("style-role", "combo")
        c.addItem(f"Tümü ({placeholder})")
        c.setMinimumWidth(120)
        return c

    def _stat(self, title: str, value: str, color: str) -> QFrame:
        card = QFrame()
        card.setProperty("bg-role", "panel")
        card.setProperty("style-role", "stat-card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 8, 12, 8); lay.setSpacing(2)
        lbl_t = QLabel(title)
        lbl_t.setProperty("color-role", "muted")
        lbl_t.setProperty("style-role", "stat-label")
        lbl_v = QLabel(value)
        lbl_v.setProperty("color-role", color)
        lbl_v.setProperty("style-role", "stat-value")
        lbl_v.setObjectName("val")
        lay.addWidget(lbl_t); lay.addWidget(lbl_v)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return card

    @staticmethod
    def _set_stat(card: QFrame, value: str):
        lbl = card.findChild(QLabel, "val")
        if lbl: lbl.setText(value)

    # ─── Yükleme ────────────────────────────────────────────
    def load_data(self):
        if self._loader and self._loader.isRunning():
            return
        self.btn_yenile.setEnabled(False)
        self.lbl_footer.setText("Yükleniyor...")
        self._loader = _Loader(self._db)
        self._loader.finished.connect(self._on_load_finished)
        self._loader.error.connect(self._on_load_error)
        self._loader.start()

    def _on_load_finished(self, rows: list, stats: dict):
        self.btn_yenile.setEnabled(True)
        self._rows = rows
        self._set_stat(self._s_toplam,   str(stats.get("toplam", 0)))
        self._set_stat(self._s_personel, str(stats.get("personel", 0)))
        self._set_stat(self._s_rapor,    str(stats.get("rapor", 0)))
        mx = stats.get("max_hp10")
        self._set_stat(self._s_max_hp10, f"{mx:.3f}" if mx else "—")
        self._set_stat(self._s_uyari,    str(stats.get("uyari_say", 0)))
        self._set_stat(self._s_tehlike,  str(stats.get("tehlike_say", 0)))
        self._set_stat(self._s_anomali,  str(stats.get("anomali_say", 0)))
        self._fill_filter_combos()
        self._apply_filter()
        self._update_birim_haritasi()
        self._update_anomali_listesi()
        self.lbl_footer.setText(f"{len(rows)} ölçüm kaydı yüklendi.")
        if stats.get("anomali_say", 0):
            self._tabs.setTabText(4, f"⚠️  Anomali ({stats['anomali_say']})")

    def _on_load_error(self, msg: str):
        self.btn_yenile.setEnabled(True)
        logger.error(f"Dozimetre takip yükleme hatası: {msg}")
        self.lbl_footer.setText(f"Hata: {msg}")

    # ─── Filtre ─────────────────────────────────────────────
    # ─── Periyot Karşılaştırma sekmesi ─────────────────────
    def _build_kars_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 8, 12, 8); lay.setSpacing(8)

        # Seçici
        ust = QHBoxLayout(); ust.setSpacing(10)
        ust.addWidget(QLabel("Periyot 1:"))
        self.cmb_kars_p1 = QComboBox()
        self.cmb_kars_p1.setMinimumWidth(140)
        ust.addWidget(self.cmb_kars_p1)
        ust.addWidget(QLabel("  →  Periyot 2:"))
        self.cmb_kars_p2 = QComboBox()
        self.cmb_kars_p2.setMinimumWidth(140)
        ust.addWidget(self.cmb_kars_p2)
        btn_kars = QPushButton("Karşılaştır")
        btn_kars.clicked.connect(self._hesapla_karsilastirma)
        btn_kars.setCursor(Qt.CursorShape.PointingHandCursor)
        ust.addWidget(btn_kars)
        self.lbl_kars_info = QLabel("")
        self.lbl_kars_info.setProperty("color-role","muted")
        ust.addWidget(self.lbl_kars_info)
        ust.addStretch()
        lay.addLayout(ust)

        self.tbl_kars = QTableView()
        self.tbl_kars.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_kars.verticalHeader().setVisible(False)
        self.tbl_kars.setAlternatingRowColors(True)
        self.tbl_kars.setSortingEnabled(True)
        self.tbl_kars.setProperty("style-role","table")
        self._kars_model = _KarsModel(KARS_COLS)
        self.tbl_kars.setModel(self._kars_model)
        self._kars_model.setup_columns(self.tbl_kars, stretch_keys=["AdSoyad"])
        lay.addWidget(self.tbl_kars)
        return w

    def _build_birim_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 8, 12, 8); lay.setSpacing(8)
        lbl = QLabel("Her birimin Hp(10) ortalaması ve genel ortalamaya oranı")
        lbl.setProperty("color-role","muted")
        lay.addWidget(lbl)
        self.tbl_birim = QTableView()
        self.tbl_birim.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_birim.verticalHeader().setVisible(False)
        self.tbl_birim.setAlternatingRowColors(True)
        self.tbl_birim.setSortingEnabled(True)
        self.tbl_birim.setProperty("style-role","table")
        self._birim_model = _BirimModel(BIRIM_COLS)
        self.tbl_birim.setModel(self._birim_model)
        self._birim_model.setup_columns(self.tbl_birim, stretch_keys=["CalistiBirim"])
        lay.addWidget(self.tbl_birim)
        return w

    def _build_anomali_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 8, 12, 8); lay.setSpacing(8)
        lbl = QLabel(
            f"Kişisel Hp(10) ortalamasının {ANOMALI_KATSAYI:.0f} katını aşan ölçümler — "
            f"ölçüm hatası, dozimetre değişimi veya gerçek maruziyet artışı olabilir."
        )
        lbl.setWordWrap(True)
        lbl.setProperty("color-role","muted")
        lay.addWidget(lbl)
        self.tbl_anomali = QTableView()
        self.tbl_anomali.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_anomali.verticalHeader().setVisible(False)
        self.tbl_anomali.setAlternatingRowColors(True)
        self.tbl_anomali.setSortingEnabled(True)
        self.tbl_anomali.setProperty("style-role","table")
        self._anomali_model = _AnomaliModel(ANOMALI_COLS)
        self.tbl_anomali.setModel(self._anomali_model)
        self._anomali_model.setup_columns(self.tbl_anomali, stretch_keys=["AdSoyad"])
        lay.addWidget(self.tbl_anomali)
        return w

    def _build_duzelt_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 8, 12, 8); lay.setSpacing(8)

        lbl = QLabel("Ana tablodan bir satır seçin, ardından aşağıdaki formu düzenleyip kaydedin.")
        lbl.setProperty("color-role","muted")
        lay.addWidget(lbl)

        # Seçili kayıt bilgisi
        self.lbl_duzelt_secili = QLabel("— Kayıt seçilmedi —")
        self.lbl_duzelt_secili.setProperty("style-role","section-title")
        lay.addWidget(self.lbl_duzelt_secili)

        # Form
        form = QFormLayout(); form.setSpacing(8)
        self._duzelt_hp10  = QDoubleSpinBox()
        self._duzelt_hp10.setRange(0.0, 500.0)
        self._duzelt_hp10.setDecimals(4); self._duzelt_hp10.setSuffix(" mSv")
        self._duzelt_hp007 = QDoubleSpinBox()
        self._duzelt_hp007.setRange(0.0, 500.0)
        self._duzelt_hp007.setDecimals(4); self._duzelt_hp007.setSuffix(" mSv")
        self._duzelt_durum = QLineEdit()
        self._duzelt_dzm   = QLineEdit()
        form.addRow("Hp(10) mSv:", self._duzelt_hp10)
        form.addRow("Hp(0,07) mSv:", self._duzelt_hp007)
        form.addRow("Durum:", self._duzelt_durum)
        form.addRow("Dozimetre No:", self._duzelt_dzm)
        lay.addLayout(form)

        btn_row = QHBoxLayout()
        self.btn_duzelt_kaydet = QPushButton("💾  Kaydet")
        self.btn_duzelt_kaydet.setProperty("style-role","action")
        self.btn_duzelt_kaydet.setEnabled(False)
        self.btn_duzelt_kaydet.clicked.connect(self._duzelt_kaydet)
        btn_row.addStretch(); btn_row.addWidget(self.btn_duzelt_kaydet)
        lay.addLayout(btn_row)
        lay.addStretch()

        self._duzelt_kayit_no: Optional[str] = None
        return w

    # ─── Yeni sekme iş mantığı ──────────────────────────────
    def _fill_kars_combos(self):
        """Periyot seçicilerini doldur — format: 'YYYY-P'"""
        periyotlar = sorted(
            {f"{r.get('Yil','')}-{r.get('Periyot','')}" for r in self._rows
             if r.get("Yil") and r.get("Periyot")},
            reverse=True
        )
        for cmb in (self.cmb_kars_p1, self.cmb_kars_p2):
            cur = cmb.currentText()
            cmb.blockSignals(True); cmb.clear()
            for p in periyotlar: cmb.addItem(p)
            idx = cmb.findText(cur)
            if idx >= 0: cmb.setCurrentIndex(idx)
            cmb.blockSignals(False)
        # Varsayılan: p1 = ikinci, p2 = birinci (en yeni)
        if self.cmb_kars_p1.count() >= 2:
            self.cmb_kars_p1.setCurrentIndex(1)
            self.cmb_kars_p2.setCurrentIndex(0)

    def _hesapla_karsilastirma(self):
        p1 = self.cmb_kars_p1.currentText()
        p2 = self.cmb_kars_p2.currentText()
        if not p1 or not p2 or p1 == p2:
            self.lbl_kars_info.setText("İki farklı periyot seçin.")
            return

        def parse(s):
            parts = s.split("-")
            return (int(parts[0]), int(parts[1])) if len(parts) == 2 else (0, 0)

        y1, per1 = parse(p1)
        y2, per2 = parse(p2)

        idx_p1 = {r.get("PersonelID"): r for r in self._rows
                  if r.get("Yil") == y1 and r.get("Periyot") == per1}
        idx_p2 = {r.get("PersonelID"): r for r in self._rows
                  if r.get("Yil") == y2 and r.get("Periyot") == per2}

        tum_pid = set(idx_p1) | set(idx_p2)
        sonuclar = []
        artan = azalan = 0
        for pid in tum_pid:
            r1 = idx_p1.get(pid)
            r2 = idx_p2.get(pid)
            hp1 = _hp(r1.get("Hp10")) if r1 else None
            hp2 = _hp(r2.get("Hp10")) if r2 else None
            fark = round(hp2 - hp1, 4) if hp1 is not None and hp2 is not None else None
            degisim = round((fark / hp1) * 100, 1) if fark is not None and hp1 and hp1 > 0 else None
            kaynak = r2 or r1
            if fark and fark > 0: artan += 1
            if fark and fark < 0: azalan += 1
            sonuclar.append({
                "AdSoyad":      kaynak.get("AdSoyad",""),
                "PersonelID":   pid,
                "CalistiBirim": kaynak.get("CalistiBirim",""),
                "hp10_p1":      hp1,
                "hp10_p2":      hp2,
                "fark":         fark,
                "degisim":      degisim,
            })
        sonuclar.sort(key=lambda x: (x.get("fark") or 0), reverse=True)
        self._kars_model.set_data(sonuclar)
        self.lbl_kars_info.setText(
            f"{len(sonuclar)} personel  |  "
            f"🔴 {artan} artış  🟢 {azalan} azalış"
        )

    def _update_birim_haritasi(self):
        from collections import defaultdict
        birim_data: dict[str, list] = defaultdict(list)
        for r in self._rows:
            v = _hp(r.get("Hp10"))
            b = r.get("CalistiBirim","")
            if v is not None and b:
                birim_data[b].append(v)

        if not birim_data:
            self._birim_model.set_data([])
            return

        genel_ort = (sum(v for vals in birim_data.values() for v in vals) /
                     sum(len(vals) for vals in birim_data.values()))

        sonuclar = []
        for birim, vals in birim_data.items():
            ort = sum(vals) / len(vals)
            uyari_say   = sum(1 for v in vals if v >= HP10_UYARI)
            tehlike_say = sum(1 for v in vals if v >= HP10_TEHLIKE)
            sonuclar.append({
                "CalistiBirim": birim,
                "kayit_say":    len(vals),
                "ort_hp10":     round(ort, 4),
                "max_hp10":     round(max(vals), 4),
                "oran":         round(ort / genel_ort, 2) if genel_ort > 0 else 0,
                "uyari_say":    uyari_say,
                "tehlike_say":  tehlike_say,
            })
        sonuclar.sort(key=lambda x: x["oran"], reverse=True)
        self._birim_model.set_data(sonuclar)

    def _update_anomali_listesi(self):
        anomaliler = [r for r in self._rows if r.get("_anomali")]
        anomaliler.sort(key=lambda x: (x.get("kat") or 0), reverse=True)
        self._anomali_model.set_data(anomaliler)

    def _fill_filter_combos(self):
        """Filtre combo'larını mevcut veriyle doldur."""
        def _unique_vals(key):
            vals = [str(r.get(key, "")).strip() for r in self._rows if str(r.get(key, "")).strip()]
            try:
                return sorted(set(vals), key=lambda v: int(v), reverse=(key == "Yil"))
            except Exception:
                return sorted(set(vals))

        combo_specs = [
            (self.cmb_yil, "Yıl", _unique_vals("Yil")),
            (self.cmb_periyot, "Periyot", _unique_vals("Periyot")),
            (self.cmb_birim, "Birim", _unique_vals("CalistiBirim")),
            (self.cmb_durum, "Durum", _unique_vals("Durum")),
        ]

        for cmb, label, values in combo_specs:
            cur = cmb.currentText()
            cmb.blockSignals(True)
            cmb.clear()
            cmb.addItem(f"Tümü ({label})")
            for v in values:
                cmb.addItem(v)
            if cur:
                idx = cmb.findText(cur)
                if idx >= 0:
                    cmb.setCurrentIndex(idx)
            cmb.blockSignals(False)

    # ─── Karşılaştırma combo doldur (filtre sonrası) ────────
    def _apply_filter(self):
        yil   = self.cmb_yil.currentText()
        per   = self.cmb_periyot.currentText()
        birim = self.cmb_birim.currentText()
        durum = self.cmb_durum.currentText()
        arama = self.inp_arama.text().strip().lower()

        def _ok(r):
            if "Tümü" not in yil   and str(r.get("Yil", ""))          != yil:   return False
            if "Tümü" not in per   and str(r.get("Periyot", ""))       != per:   return False
            if "Tümü" not in birim and str(r.get("CalistiBirim", "")) != birim: return False
            if "Tümü" not in durum and str(r.get("Durum", ""))         != durum: return False
            if arama:
                hay = (str(r.get("AdSoyad","")) + str(r.get("PersonelID",""))).lower()
                if arama not in hay: return False
            return True

        self._filter = [r for r in self._rows if _ok(r)]
        self._main_model.set_data(self._filter)
        self.lbl_sonuc.setText(f"{len(self._filter)} kayıt")
        self._fill_kars_combos()

    # ─── Kayıt düzeltme ─────────────────────────────────────
    def _on_select(self, selected, deselected):
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return
        row = self._main_model.get_row(indexes[0].row())
        if not row:
            return

        pid = row.get("PersonelID", "")
        ad  = row.get("AdSoyad", "")
        yil = row.get("Yil", "")

        # Düzelt sekmesini doldur
        kayit_no = row.get("KayitNo","")
        self._duzelt_kayit_no = kayit_no
        self.lbl_duzelt_secili.setText(
            f"{ad}  —  {pid}  |  {yil}/{row.get('Periyot','')}  |  KayitNo: {kayit_no}"
        )
        self._duzelt_hp10.setValue(_hp(row.get("Hp10")) or 0.0)
        self._duzelt_hp007.setValue(_hp(row.get("Hp007")) or 0.0)
        self._duzelt_durum.setText(str(row.get("Durum","") or ""))
        self._duzelt_dzm.setText(str(row.get("DozimetreNo","") or ""))
        self.btn_duzelt_kaydet.setEnabled(bool(kayit_no))

        # Geçmiş panel
        gecmis = sorted(
            [r for r in self._rows if r.get("PersonelID") == pid],
            key=lambda r: (r.get("Yil", 0), r.get("Periyot", 0))
        )
        self.lbl_alt_baslik.setText(
            f"{ad}  —  {pid}  |  {len(gecmis)} periyot ölçümü"
        )
        self.lbl_alt_baslik.setStyleSheet(
            f"font-size:13px;font-weight:600;color:{"primary"};"
        )
        self._gecmis_model.set_data(gecmis)
        self._trend.set_data(gecmis)

        yil_veriler = [r for r in gecmis if str(r.get("Yil","")) == str(yil)]
        yillik_hp10 = sum(_hp(r.get("Hp10")) or 0.0 for r in yil_veriler)
        self._gauge_yillik.set_deger(yillik_hp10)

        try:
            yil_int    = int(yil)
            yil_aralik = set(range(yil_int - 4, yil_int + 1))
            bes_hp10   = sum(
                _hp(r.get("Hp10")) or 0.0
                for r in gecmis if r.get("Yil") in yil_aralik
            )
        except (ValueError, TypeError):
            bes_hp10 = sum(_hp(r.get("Hp10")) or 0.0 for r in gecmis)
        self._gauge_5yil.set_deger(bes_hp10)

        kayitli = {r.get("Periyot") for r in yil_veriler}
        eksik   = [i for i in range(1, PERIYOT_SAYISI + 1) if i not in kayitli]
        if not eksik:
            doluluk_metin = f"✔ {yil} yılı — {PERIYOT_SAYISI}/{PERIYOT_SAYISI} periyot kayıtlı"
            doluluk_renk  = "#4ade80"
        else:
            doluluk_metin = (
                f"⚠ {yil} yılı — {len(kayitli)}/{PERIYOT_SAYISI} periyot  |  "
                f"Eksik: {', '.join(str(e) for e in eksik)}. periyot"
            )
            doluluk_renk = "#facc15"
        self.lbl_periyot_doluluk.setText(doluluk_metin)
        self.lbl_periyot_doluluk.setProperty("color-role", "primary")

        hp10s = [_hp(r.get("Hp10")) for r in gecmis if _hp(r.get("Hp10")) is not None]
        if hp10s:
            ort = sum(hp10s) / len(hp10s)
            mx  = max(hp10s)
            trend_ok   = hp10s[-1] <= hp10s[0] if len(hp10s) >= 2 else True
            trend_ikon = "↓ Azalıyor" if trend_ok else "↑ Artıyor"
            trend_renk = "#4ade80" if trend_ok else "#f87171"
            kos        = "A (>6 mSv/yıl)" if yillik_hp10 >= CALISMA_A else "B (≤6 mSv/yıl)"
            kos_renk   = "#facc15" if yillik_hp10 >= CALISMA_A else "#4ade80"
            self.lbl_mini_stat.setText(
                f"Ort. Hp(10): <b>{ort:.3f}</b> mSv &nbsp;|&nbsp; "
                f"Maks: <b>{mx:.3f}</b> mSv<br>"
                f"Trend: <span style='color:{trend_renk}'><b>{trend_ikon}</b></span>"
                f"&nbsp;&nbsp;&nbsp;"
                f"Doz Bazlı Koşul: <span style='color:{kos_renk}'><b>{kos}</b></span>"
            )

        dzm_no = row.get("DozimetreNo", "")
        if dzm_no:
            self._tabs.setCurrentIndex(0)

    def _duzelt_kaydet(self):
        kayit_no = self._duzelt_kayit_no
        if not kayit_no or not self._db:
            return

        yeni_hp10  = self._duzelt_hp10.value()
        yeni_hp007 = self._duzelt_hp007.value()
        yeni_durum = self._duzelt_durum.text().strip()
        yeni_dzm   = self._duzelt_dzm.text().strip()

        cevap = QMessageBox.question(
            self, "Kayıt Düzelt",
            f"<b>KayitNo: {kayit_no}</b><br><br>"
            f"Hp(10): <b>{yeni_hp10:.4f}</b> mSv<br>"
            f"Hp(0,07): <b>{yeni_hp007:.4f}</b> mSv<br>"
            f"Durum: <b>{yeni_durum}</b><br>"
            f"Dozimetre No: <b>{yeni_dzm}</b><br><br>"
            f"Kayıt güncellensin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if cevap != QMessageBox.StandardButton.Yes:
            return

        try:
            loader = _Loader.__new__(_Loader)
            loader._db = self._db
            conn, kapat = loader._conn()
            conn.execute(
                """UPDATE Dozimetre_Olcum
                   SET Hp10=?, Hp007=?, Durum=?, DozimetreNo=?
                   WHERE KayitNo=?""",
                (yeni_hp10, yeni_hp007, yeni_durum, yeni_dzm, kayit_no)
            )
            conn.commit()
            if kapat: conn.close()
            QMessageBox.information(self, "Başarılı", "Kayıt güncellendi.")
            self.load_data()
        except Exception as exc:
            QMessageBox.critical(self, "Hata", f"Güncelleme başarısız:\n{exc}")
            logger.error(f"Kayıt düzeltme hatası: {exc}")

    # ─── Import dialog ───────────────────────────────────────
    def _open_import(self):
        from PySide6.QtWidgets import QDialog, QVBoxLayout
        ImportClass = None
        for mod in ("ui.pages.imports.dozimetre_pdf_import_page",
                    "ui.pages.import_.dozimetre_pdf_import_page"):
            try:
                m = __import__(mod, fromlist=["DozimetrePdfImportPage"])
                ImportClass = m.DozimetrePdfImportPage
                break
            except ImportError:
                continue
        if not ImportClass:
            logger.error("DozimetrePdfImportPage bulunamadı")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Dozimetre Raporu İçe Aktar")
        dlg.resize(1100, 700)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(ImportClass(db=self._db, parent=dlg))
        dlg.finished.connect(self.load_data)
        dlg.exec()

    def set_db(self, db):
        self._db = db
        self.load_data()

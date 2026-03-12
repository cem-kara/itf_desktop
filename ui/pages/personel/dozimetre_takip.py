# -*- coding: utf-8 -*-
"""
dozimetre_takip.py
──────────────────
Dozimetre_Olcum tablosunu görüntüleyen ve yorumlayan ana sayfa.

Özellikler
----------
• Özet kartlar   : Toplam ölçüm, benzersiz personel, rapor sayısı,
                   max Hp10, Durum dağılımı
• Filtre çubuğu  : Yıl · Periyot · Birim · Durum · Ad/TC arama
• Ana tablo      : Tüm ölçüm kayıtları (renk kodlu Hp değerleri)
• Alt panel      : Seçili personelin tüm periyot geçmişi + mini trend
• QThread loader : UI donmaz
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal as _Signal, QSortFilterProxyModel
from PySide6.QtGui import QColor, QPainter, QPen, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QTableView, QHeaderView, QLineEdit,
    QComboBox, QAbstractItemView, QSizePolicy, QScrollArea,
    QSplitter,
)

from core.logger import logger
from ui.components.base_table_model import BaseTableModel
from ui.styles import DarkTheme
from ui.styles.components import STYLES as S
from ui.styles.icons import IconRenderer, IconColors

# ─────────────────────────────────────────────────────────────
# Sütunlar
# ─────────────────────────────────────────────────────────────
MAIN_COLS = [
    ("Yil",          "Yıl",        100),
    ("Periyot",      "Per.",       40),
    ("PeriyotAdi",   "Dönem",     110),
    ("AdSoyad",      "Ad Soyad",  150),
    ("TCKimlikNo",   "TC",        105),
    ("CalistiBirim", "Birim",     130),
    ("DozimetreNo",  "Dzm. No",    75),
    ("VucutBolgesi", "Bölge",     100),
    ("Hp10",         "Hp(10)",     65),
    ("Hp007",        "Hp(0,07)",   65),
    ("Durum",        "Durum",     115),
]

GECMIS_COLS = [
    ("Yil",        "Yıl",    100),
    ("Periyot",    "Per.",   40),
    ("PeriyotAdi", "Dönem",  110),
    ("DozimetreNo","Dzm.",    90),
    ("Hp10",       "Hp(10)", 65),
    ("Hp007",      "Hp(0,07)",65),
    ("Durum",      "Durum",  115),
]

# Hp10 için renk eşiği (mSv) — TAEK limitine göre
HP10_UYARI  = 2.0    # sarı
HP10_TEHLIKE = 5.0   # kırmızı


# ─────────────────────────────────────────────────────────────
# Modeller
# ─────────────────────────────────────────────────────────────
class _MainModel(BaseTableModel):
    ALIGN_CENTER = frozenset({"Yil","Periyot","Hp10","Hp007","DozimetreNo"})

    def _display(self, key: str, row: dict) -> str:
        val = row.get(key)
        if val is None: return ""
        if key in ("Hp10","Hp007"):
            return f"{float(val):.3f}" if str(val).replace(".","").isdigit() else str(val)
        return str(val)

    def _fg(self, key: str, row: dict):
        if key == "Hp10":
            try:
                v = float(row.get("Hp10") or 0)
                if v >= HP10_TEHLIKE: return QColor("#f87171")
                if v >= HP10_UYARI:   return QColor("#facc15")
                return QColor("#4ade80")
            except: pass
        if key == "Hp007":
            try:
                v = float(row.get("Hp007") or 0)
                if v >= HP10_TEHLIKE: return QColor("#f87171")
                if v >= HP10_UYARI:   return QColor("#facc15")
                return QColor("#4ade80")
            except: pass
        if key == "Durum":
            d = str(row.get("Durum",""))
            if "Aşım" in d: return QColor("#f87171")
            return QColor("#4ade80")
        return None


class _GecmisModel(BaseTableModel):
    ALIGN_CENTER = frozenset({"Yil","Periyot","Hp10","Hp007","DozimetreNo"})

    def _display(self, key: str, row: dict) -> str:
        val = row.get(key)
        if val is None: return ""
        if key in ("Hp10","Hp007"):
            return f"{float(val):.3f}" if str(val).replace(".","").isdigit() else str(val)
        return str(val)

    def _fg(self, key: str, row: dict):
        if key == "Hp10":
            try:
                v = float(row.get("Hp10") or 0)
                if v >= HP10_TEHLIKE: return QColor("#f87171")
                if v >= HP10_UYARI:   return QColor("#facc15")
                return QColor("#4ade80")
            except: pass
        if key == "Durum":
            if "Aşım" in str(row.get("Durum","")): return QColor("#f87171")
            return QColor("#4ade80")
        return None


# ─────────────────────────────────────────────────────────────
# Mini Trend Widget — personelin Hp10 geçmişi
# ─────────────────────────────────────────────────────────────
class _TrendWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._points: list[float] = []
        self._labels: list[str]   = []
        self.setMinimumHeight(70)
        self.setMaximumHeight(90)
        self.setProperty("bg-role", "transparent")

    def set_data(self, rows: list[dict]):
        self._points = []
        self._labels = []
        for r in rows:
            try:
                v = float(r.get("Hp10") or 0)
                self._points.append(v)
                self._labels.append(f"{r.get('Yil','')}-{r.get('Periyot','')}")
            except: pass
        self.update()

    def paintEvent(self, event):
        if len(self._points) < 2:
            p = QPainter(self)
            p.setPen(QColor(DarkTheme.TEXT_MUTED))
            p.setFont(QFont("", 9))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Trend için en az 2 periyot gerekli")
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        mx = max(self._points) if max(self._points) > 0 else 1
        w, h = self.width(), self.height()
        pad_l, pad_r, pad_t, pad_b = 8, 8, 8, 20
        cw = w - pad_l - pad_r
        ch = h - pad_t - pad_b
        n  = len(self._points)

        def px(i): return int(pad_l + i * cw / (n - 1))
        def py(v): return int(pad_t + ch - v / mx * ch)

        # Eşik çizgileri
        p.setPen(QPen(QColor("#facc1540"), 1, Qt.PenStyle.DashLine))
        y_uyari = py(HP10_UYARI / mx * mx)
        if 0 < HP10_UYARI < mx:
            p.drawLine(pad_l, py(HP10_UYARI), w - pad_r, py(HP10_UYARI))

        # Çizgi
        p.setPen(QPen(QColor(DarkTheme.ACCENT), 2))
        for i in range(n - 1):
            p.drawLine(px(i), py(self._points[i]), px(i+1), py(self._points[i+1]))

        # Noktalar
        for i, v in enumerate(self._points):
            if v >= HP10_TEHLIKE:   c = QColor("#f87171")
            elif v >= HP10_UYARI:   c = QColor("#facc15")
            else:                   c = QColor("#4ade80")
            p.setBrush(c); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(px(i)-4, py(v)-4, 8, 8)

        # X ekseni etiketleri (sadece ilk ve son)
        p.setPen(QColor(DarkTheme.TEXT_MUTED))
        p.setFont(QFont("", 7))
        if self._labels:
            p.drawText(pad_l, h-4, self._labels[0])
            p.drawText(w - pad_r - 40, h-4, self._labels[-1])


# ─────────────────────────────────────────────────────────────
# QThread Worker
# ─────────────────────────────────────────────────────────────
class _Loader(QThread):
    finished = _Signal(list, dict)   # rows, stats
    error    = _Signal(str)

    def __init__(self, db: str):
        super().__init__()
        self._db = db

    def run(self):
        try:
            conn = sqlite3.connect(self._db)
            conn.row_factory = sqlite3.Row
            try:
                rows = [dict(r) for r in conn.execute(
                    "SELECT * FROM Dozimetre_Olcum ORDER BY Yil DESC, Periyot DESC, AdSoyad"
                ).fetchall()]
            except sqlite3.OperationalError:
                rows = []

            stats = {}
            if rows:
                try:
                    s = conn.execute("""
                        SELECT
                            COUNT(*)                        as toplam,
                            COUNT(DISTINCT TCKimlikNo)      as personel,
                            COUNT(DISTINCT RaporNo)         as rapor,
                            ROUND(AVG(Hp10),4)              as ort_hp10,
                            ROUND(MAX(Hp10),4)              as max_hp10,
                            SUM(CASE WHEN Hp10 >= 2 THEN 1 ELSE 0 END) as uyari_say,
                            SUM(CASE WHEN Hp10 >= 5 THEN 1 ELSE 0 END) as tehlike_say
                        FROM Dozimetre_Olcum
                    """).fetchone()
                    stats = dict(s)
                except: pass
            conn.close()
            self.finished.emit(rows, stats)
        except Exception as exc:
            self.error.emit(str(exc))


# ─────────────────────────────────────────────────────────────
# Ana Sayfa
# ─────────────────────────────────────────────────────────────
class DozimetreTakipPage(QWidget):
    def __init__(self, db: str = "", parent=None):
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

        # Başlık + yenile
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

        top.addWidget(lbl)
        top.addStretch()
        top.addWidget(self.btn_import)
        top.addWidget(self.btn_yenile)
        root.addLayout(top)

        # Özet kartlar
        self._stat_row = QHBoxLayout()
        self._stat_row.setSpacing(10)
        self._s_toplam   = self._make_stat("Toplam Ölçüm",   "—", DarkTheme.ACCENT)
        self._s_personel = self._make_stat("Personel",        "—", "#60a5fa")
        self._s_rapor    = self._make_stat("Rapor Sayısı",    "—", "#a78bfa")
        self._s_max_hp10 = self._make_stat("Maks. Hp(10)",   "—", "#fb923c")
        self._s_uyari    = self._make_stat("≥2 mSv Uyarı",   "—", "#facc15")
        self._s_tehlike  = self._make_stat("≥5 mSv Tehlike", "—", "#f87171")
        for w in (self._s_toplam, self._s_personel, self._s_rapor,
                  self._s_max_hp10, self._s_uyari, self._s_tehlike):
            self._stat_row.addWidget(w)
        root.addLayout(self._stat_row)

        # Filtre çubuğu
        filter_frame = QFrame()
        filter_frame.setProperty("style-role", "form")
        fb = QHBoxLayout(filter_frame)
        fb.setContentsMargins(12, 8, 12, 8)
        fb.setSpacing(8)

        self.cmb_yil    = self._cmb("Yıl")
        self.cmb_periyot = self._cmb("Periyot")
        self.cmb_birim  = self._cmb("Birim")
        self.cmb_durum  = self._cmb("Durum")
        self.inp_arama  = QLineEdit()
        self.inp_arama.setPlaceholderText("Ad / TC ara...")
        self.inp_arama.setProperty("style-role", "search")
        self.inp_arama.setFixedWidth(200)

        for lbl_text, w in (("Yıl", self.cmb_yil), ("Periyot", self.cmb_periyot),
                             ("Birim", self.cmb_birim), ("Durum", self.cmb_durum)):
            fb.addWidget(QLabel(lbl_text))
            fb.addWidget(w)
        fb.addWidget(self.inp_arama)

        self.lbl_sonuc = QLabel("— kayıt")
        self.lbl_sonuc.setProperty("color-role", "muted")
        self.lbl_sonuc.setProperty("style-role", "footer")
        fb.addStretch()
        fb.addWidget(self.lbl_sonuc)
        root.addWidget(filter_frame)

        # Splitter: üst tablo / alt panel
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(6)
        splitter.setProperty("bg-role", "panel")

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
        self._main_model.setup_columns(self.table, stretch_keys=["AdSoyad","VucutBolgesi"])
        self.table.selectionModel().selectionChanged.connect(self._on_select)
        splitter.addWidget(self.table)

        # Alt panel — seçili personel geçmişi
        bottom = QFrame()
        bottom.setProperty("bg-role", "panel")
        bottom_lay = QVBoxLayout(bottom)
        bottom_lay.setContentsMargins(16,10,16,10)
        bottom_lay.setSpacing(8)

        self.lbl_alt_baslik = QLabel("← Tabloda bir satır seçin")
        self.lbl_alt_baslik.setProperty("style-role", "section-title")
        self.lbl_alt_baslik.setProperty("color-role", "muted")
        bottom_lay.addWidget(self.lbl_alt_baslik)

        alt_icerik = QHBoxLayout()
        alt_icerik.setSpacing(16)

        # Geçmiş tablo
        self.tbl_gecmis = QTableView()
        self.tbl_gecmis.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_gecmis.verticalHeader().setVisible(False)
        self.tbl_gecmis.setAlternatingRowColors(True)
        self.tbl_gecmis.setMaximumHeight(200)
        self.tbl_gecmis.setProperty("style-role", "table")
        self._gecmis_model = _GecmisModel(GECMIS_COLS)
        self.tbl_gecmis.setModel(self._gecmis_model)
        self._gecmis_model.setup_columns(self.tbl_gecmis, stretch_keys=["PeriyotAdi"])
        alt_icerik.addWidget(self.tbl_gecmis, 3)

        # Trend + mini istatistik
        right_panel = QVBoxLayout()
        right_panel.setSpacing(6)

        self.lbl_mini_stat = QLabel("")
        self.lbl_mini_stat.setProperty("color-role", "muted")
        self.lbl_mini_stat.setProperty("style-role", "info")
        self.lbl_mini_stat.setWordWrap(True)
        right_panel.addWidget(self.lbl_mini_stat)

        lbl_trend = QLabel("Hp(10) Trend")
        lbl_trend.setProperty("color-role", "muted")
        lbl_trend.setProperty("style-role", "stat-label")
        right_panel.addWidget(lbl_trend)

        self._trend = _TrendWidget()
        right_panel.addWidget(self._trend)
        right_panel.addStretch()
        alt_icerik.addLayout(right_panel, 2)
        bottom_lay.addLayout(alt_icerik)

        splitter.addWidget(bottom)
        splitter.setSizes([450, 200])
        root.addWidget(splitter, 1)

        # Footer
        self.lbl_footer = QLabel("")
        self.lbl_footer.setProperty("style-role", "footer")
        root.addWidget(self.lbl_footer)

        # Bağlantılar
        for w in (self.cmb_yil, self.cmb_periyot, self.cmb_birim, self.cmb_durum):
            w.currentIndexChanged.connect(self._apply_filter)
        self.inp_arama.textChanged.connect(self._apply_filter)

    def _cmb(self, placeholder: str) -> QComboBox:
        c = QComboBox()
        c.setProperty("style-role", "combo")
        c.addItem(f"Tümü ({placeholder})")
        c.setMinimumWidth(130)
        return c

    def _make_stat(self, title: str, value: str, color: str) -> QFrame:
        card = QFrame()
        card.setProperty("bg-role", "panel")
        card.setProperty("style-role", "stat-card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setProperty("color-role", "muted")
        lbl_t.setProperty("style-role", "stat-label")

        lbl_v = QLabel(value)
        lbl_v.setProperty("color-role", color)
        lbl_v.setProperty("style-role", "stat-value")
        lbl_v.setObjectName("val")

        lay.addWidget(lbl_t)
        lay.addWidget(lbl_v)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return card

    @staticmethod
    def _set_stat(card: QFrame, value: str):
        lbl = card.findChild(QLabel, "val")
        if lbl is not None:
            lbl.setText(value)

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

        # Özet kartlar
        self._set_stat(self._s_toplam,   str(stats.get("toplam",0)))
        self._set_stat(self._s_personel, str(stats.get("personel",0)))
        self._set_stat(self._s_rapor,    str(stats.get("rapor",0)))
        self._set_stat(self._s_max_hp10, f"{stats.get('max_hp10',0):.3f}")
        self._set_stat(self._s_uyari,    str(stats.get("uyari_say",0)))
        self._set_stat(self._s_tehlike,  str(stats.get("tehlike_say",0)))

        self._fill_filter_combos()
        self._apply_filter()
        self.lbl_footer.setText(f"{len(rows)} ölçüm kaydı yüklendi.")

    def _on_load_error(self, msg: str):
        self.btn_yenile.setEnabled(True)
        logger.error(f"Dozimetre takip yükleme hatası: {msg}")
        self.lbl_footer.setText(f"Hata: {msg}")

    # ─── Filtre ─────────────────────────────────────────────
    def _fill_filter_combos(self):
        def _fill(cmb, key, label):
            vals = sorted({str(r.get(key,"")) for r in self._rows if r.get(key)})
            cmb.blockSignals(True)
            cur = cmb.currentText()
            cmb.clear()
            cmb.addItem(f"Tümü ({label})")
            for v in vals:
                cmb.addItem(v)
            idx = cmb.findText(cur)
            if idx >= 0: cmb.setCurrentIndex(idx)
            cmb.blockSignals(False)

        _fill(self.cmb_yil,     "Yil",          "Yıl")
        _fill(self.cmb_periyot, "Periyot",       "Periyot")
        _fill(self.cmb_birim,   "CalistiBirim",  "Birim")
        _fill(self.cmb_durum,   "Durum",         "Durum")

    def _apply_filter(self):
        yil    = self.cmb_yil.currentText()
        per    = self.cmb_periyot.currentText()
        birim  = self.cmb_birim.currentText()
        durum  = self.cmb_durum.currentText()
        arama  = self.inp_arama.text().strip().lower()

        def _ok(r):
            if "Tümü" not in yil   and str(r.get("Yil",""))         != yil:   return False
            if "Tümü" not in per   and str(r.get("Periyot",""))      != per:   return False
            if "Tümü" not in birim and str(r.get("CalistiBirim","")) != birim: return False
            if "Tümü" not in durum and str(r.get("Durum",""))        != durum: return False
            if arama:
                hay = (str(r.get("AdSoyad","")) + str(r.get("TCKimlikNo",""))).lower()
                if arama not in hay: return False
            return True

        self._filter = [r for r in self._rows if _ok(r)]
        self._main_model.set_data(self._filter)
        self.lbl_sonuc.setText(f"{len(self._filter)} kayıt")

    # ─── Satır seçimi → geçmiş panel ────────────────────────
    def _on_select(self, selected, deselected):
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return
        row = self._main_model.get_row(indexes[0].row())
        if not row:
            return

        ad     = row.get("AdSoyad","")
        tc     = row.get("TCKimlikNo","")
        pid    = row.get("PersonelID","") or tc

        # Aynı personelin tüm ölçümleri (TC veya PersonelID üzerinden)
        gecmis = sorted(
            [r for r in self._rows
             if r.get("TCKimlikNo") == tc or r.get("PersonelID") == pid],
            key=lambda r: (r.get("Yil",0), r.get("Periyot",0))
        )

        self.lbl_alt_baslik.setText(
            f"{ad}  —  {tc}  |  {len(gecmis)} periyot ölçümü")
        self.lbl_alt_baslik.setStyleSheet(
            f"font-size:13px;font-weight:600;color:{DarkTheme.TEXT_PRIMARY};")

        self._gecmis_model.set_data(gecmis)
        self._trend.set_data(gecmis)

        # Mini istatistik
        if gecmis:
            hp10s = [float(r["Hp10"]) for r in gecmis if r.get("Hp10") is not None]
            if hp10s:
                ort = sum(hp10s)/len(hp10s)
                mx  = max(hp10s)
                trend_ok = hp10s[-1] <= hp10s[0] if len(hp10s) >= 2 else True
                trend_icon = "↓ Azalıyor" if trend_ok else "↑ Artıyor"
                trend_color = "#4ade80" if trend_ok else "#f87171"
                self.lbl_mini_stat.setText(
                    f"Ort. Hp(10): <b>{ort:.3f}</b> mSv<br>"
                    f"Maks. Hp(10): <b>{mx:.3f}</b> mSv<br>"
                    f"Trend: <span style='color:{trend_color}'><b>{trend_icon}</b></span>"
                )
                self.lbl_mini_stat.setTextFormat(Qt.TextFormat.RichText)

    def _open_import(self):
        from PySide6.QtWidgets import QDialog, QVBoxLayout
        from ui.pages.personel.dozimetre_import import DozimetreImportPage

        dlg = QDialog(self)
        dlg.setWindowTitle("Dozimetre Raporu İçe Aktar")
        dlg.resize(1100, 700)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(0, 0, 0, 0)

        import_page = DozimetreImportPage(db=self._db, parent=dlg)
        lay.addWidget(import_page)

        # Dialog kapanınca tabloyu yenile
        dlg.finished.connect(self.load_data)
        dlg.exec()

    def set_db(self, db: str):
        self._db = db
        self.load_data()

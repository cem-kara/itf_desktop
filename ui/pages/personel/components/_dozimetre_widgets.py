# -*- coding: utf-8 -*-
"""
ui/pages/personel/components/_dozimetre_widgets.py
─────────────────────────────────────────────────
Dozimetre panelinde kullanılan küçük widget'lar:
  _DozModel    — QTableView modeli
  _TrendWidget — Hp(10)/Hp(0,07) mini trend grafiği
  _GaugeWidget — NDK limit doluluk çubuğu
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen, QFont
from PySide6.QtWidgets import QWidget

from ui.components.base_table_model import BaseTableModel

# NDK Doz Limitleri
HP10_UYARI   = 2.0
HP10_TEHLIKE = 5.0
YILLIK_LIMIT = 20.0
BES_YILLIK   = 100.0
CALISMA_A    = 6.0
PERIYOT_SAYISI = 4

GECMIS_COLS = [
    ("Yil",          "Yıl",        100),
    ("Periyot",      "Per.",        40),
    ("PeriyotAdi",   "Dönem",      110),
    ("DozimetreNo",  "Dzm. No",     75),
    ("VucutBolgesi", "Bölge",      100),
    ("Hp10",         "Hp(10)",      65),
    ("Hp007",        "Hp(0,07)",    65),
    ("Durum",        "Durum",      115),
]


class _DozModel(BaseTableModel):
    ALIGN_CENTER = frozenset({"Yil", "Periyot", "Hp10", "Hp007", "DozimetreNo"})

    def _display(self, key: str, row: dict) -> str:
        val = row.get(key)
        if val is None:
            return ""
        if key in ("Hp10", "Hp007"):
            try:
                return f"{float(val):.3f}"
            except (ValueError, TypeError):
                return str(val)
        return str(val)

    def _fg(self, key: str, row: dict):
        if key == "Hp10":
            try:
                v = float(row.get("Hp10") or 0)
                if v >= HP10_TEHLIKE: return QColor("#f87171")
                if v >= HP10_UYARI:   return QColor("#facc15")
                return QColor("#4ade80")
            except (ValueError, TypeError):
                pass
        if key == "Hp007":
            try:
                v = float(row.get("Hp007") or 0)
                if v >= HP10_TEHLIKE: return QColor("#f87171")
                if v >= HP10_UYARI:   return QColor("#facc15")
                return QColor("#4ade80")
            except (ValueError, TypeError):
                pass
        if key == "Durum":
            return QColor("#f87171") if "Aşım" in str(row.get("Durum", "")) \
                   else QColor("#4ade80")
        return None


class _TrendWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[dict] = []
        self.setMinimumHeight(80)
        self.setMaximumHeight(100)
        self.setProperty("bg-role", "transparent")

    def set_data(self, rows: list[dict]):
        self._rows = rows
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setFont(QFont("", 7))

        rows   = self._rows
        hp10s, hp007s, labels = [], [], []
        for r in rows:
            try:
                hp10s.append(float(r.get("Hp10")  or 0))
                hp007s.append(float(r.get("Hp007") or 0))
                labels.append(f"{r.get('Yil','')}-{r.get('Periyot','')}")
            except (ValueError, TypeError):
                pass

        if len(hp10s) < 2:
            p.setPen(QColor("#4d6070"))
            p.setFont(QFont("", 9))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "Trend için en az 2 periyot gerekli")
            return

        mx  = max(max(hp10s), max(hp007s), HP10_UYARI + 0.1, 0.1)
        w, h = self.width(), self.height()
        pl, pr, pt, pb = 10, 10, 10, 22
        cw, ch = w - pl - pr, h - pt - pb
        n = len(hp10s)

        def px(i): return int(pl + i * cw / (n - 1))
        def py(v): return int(pt + ch - v / mx * ch)

        if 0 < HP10_UYARI <= mx:
            p.setPen(QPen(QColor("#facc1550"), 1, Qt.PenStyle.DashLine))
            p.drawLine(pl, py(HP10_UYARI), w - pr, py(HP10_UYARI))

        p.setPen(QPen(QColor("#3d8ef5"), 2))
        for i in range(n - 1):
            p.drawLine(px(i), py(hp10s[i]), px(i + 1), py(hp10s[i + 1]))
        for i, v in enumerate(hp10s):
            c = ("#f87171" if v >= HP10_TEHLIKE else
                 "#facc15" if v >= HP10_UYARI   else "#4ade80")
            p.setBrush(QColor(c)); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(px(i) - 4, py(v) - 4, 8, 8)

        p.setPen(QPen(QColor("#fb923c"), 1, Qt.PenStyle.DashLine))
        for i in range(n - 1):
            p.drawLine(px(i), py(hp007s[i]), px(i + 1), py(hp007s[i + 1]))
        for i, v in enumerate(hp007s):
            p.setBrush(QColor("#fb923c")); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(px(i) - 2, py(v) - 2, 5, 5)

        p.setPen(QColor("#4d6070"))
        if labels:
            p.drawText(pl, h - 5, labels[0])
            p.drawText(w - pr - 45, h - 5, labels[-1])
        p.setPen(QColor("#3d8ef5"))
        p.drawText(w - pr - 90, pt + 10, "— Hp(10)")
        p.setPen(QColor("#fb923c"))
        p.drawText(w - pr - 90, pt + 20, "-- Hp(0,07)")


class _GaugeWidget(QWidget):
    """Yıllık / 5 yıllık doz limitine göre doluluk çubuğu."""

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
        self.setMinimumWidth(140)

    def set_deger(self, deger: float):
        self._deger = deger
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        oran = min(self._deger / self._limit, 1.0) if self._limit else 0.0
        w = self.width()

        p.setPen(QColor("#4d6070"))
        p.setFont(QFont("", 8))
        p.drawText(0, 12, self._baslik)

        bar_y, bar_h = 18, 10
        p.setBrush(QColor("#232a3a")); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, bar_y, w, bar_h, 4, 4)

        if oran > 0:
            renk = (QColor("#f87171") if oran >= self._esik2 else
                    QColor("#facc15") if oran >= self._esik1 else
                    QColor("#4ade80"))
            p.setBrush(renk)
            p.drawRoundedRect(0, bar_y, int(w * oran), bar_h, 4, 4)

        p.setPen(QColor("#e8edf5"))
        p.setFont(QFont("", 8, QFont.Weight.Bold))
        p.drawText(0, bar_y + bar_h + 14,
                   f"{self._deger:.2f} / {self._limit:.0f} mSv  (%{oran*100:.0f})")

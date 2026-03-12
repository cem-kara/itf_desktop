# -*- coding: utf-8 -*-
"""
personel_dozimetre_panel.py
──────────────────────────
PersonelMerkezPage içinde kullanılmak üzere tek bir personelin
Dozimetre_Olcum geçmişini gösteren panel.

Kullanım
--------
    from ui.pages.personel.components.personel_dozimetre_panel import PersonelDozimetrePanel

    panel = PersonelDozimetrePanel(db=self.db, personel_id=self.personel_id)
    # personel_id → Personel.KimlikNo (TC kimlik no)
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal as _Signal
from PySide6.QtGui import QColor, QPainter, QPen, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGroupBox, QTableView, QHeaderView, QAbstractItemView,
    QPushButton, QSizePolicy,
)

from core.logger import logger
from ui.components.base_table_model import BaseTableModel
from ui.styles.colors import DarkTheme as C
from ui.styles.components import STYLES as S
from ui.styles.icons import IconRenderer, IconColors

# Hp eşikleri (mSv)
HP10_UYARI   = 2.0
HP10_TEHLIKE = 5.0

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


# ─── Model ──────────────────────────────────────────────────
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
            return QColor("#f87171") if "Aşım" in str(row.get("Durum", "")) else QColor("#4ade80")
        return None


# ─── Trend Widget ────────────────────────────────────────────
class _TrendWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._points: list[float] = []
        self._labels: list[str]   = []
        self.setMinimumHeight(80)
        self.setMaximumHeight(100)
        self.setProperty("bg-role", "transparent")

    def set_data(self, rows: list[dict]):
        self._points = []
        self._labels = []
        for r in rows:
            try:
                self._points.append(float(r.get("Hp10") or 0))
                self._labels.append(f"{r.get('Yil','')}-{r.get('Periyot','')}")
            except (ValueError, TypeError):
                pass
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        if len(self._points) < 2:
            p.setPen(QColor(C.TEXT_MUTED))
            p.setFont(QFont("", 9))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "Trend için en az 2 periyot gerekli")
            return

        mx  = max(self._points) if max(self._points) > 0 else 1
        w, h = self.width(), self.height()
        pl, pr, pt, pb = 10, 10, 10, 22
        cw, ch = w - pl - pr, h - pt - pb
        n = len(self._points)

        def px(i): return int(pl + i * cw / (n - 1))
        def py(v): return int(pt + ch - v / mx * ch)

        # Uyarı eşiği çizgisi
        if 0 < HP10_UYARI <= mx:
            p.setPen(QPen(QColor("#facc1550"), 1, Qt.PenStyle.DashLine))
            p.drawLine(pl, py(HP10_UYARI), w - pr, py(HP10_UYARI))

        # Trend çizgisi
        p.setPen(QPen(QColor(C.ACCENT), 2))
        for i in range(n - 1):
            p.drawLine(px(i), py(self._points[i]), px(i + 1), py(self._points[i + 1]))

        # Noktalar
        for i, v in enumerate(self._points):
            c = ("#f87171" if v >= HP10_TEHLIKE else
                 "#facc15" if v >= HP10_UYARI else "#4ade80")
            p.setBrush(QColor(c))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(px(i) - 4, py(v) - 4, 8, 8)

        # Etiketler (ilk / son)
        p.setPen(QColor(C.TEXT_MUTED))
        p.setFont(QFont("", 7))
        if self._labels:
            p.drawText(pl, h - 5, self._labels[0])
            p.drawText(w - pr - 45, h - 5, self._labels[-1])


# ─── Worker ─────────────────────────────────────────────────
class _Loader(QThread):
    finished = _Signal(list)
    error    = _Signal(str)

    def __init__(self, db: str, personel_id: str):
        super().__init__()
        self._db          = db
        self._personel_id = personel_id

    def run(self):
        try:
            db_path = getattr(self._db, "db_path", None) or str(self._db)
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                rows = [dict(r) for r in conn.execute(
                    """
                    SELECT * FROM Dozimetre_Olcum
                    WHERE PersonelID = ? OR TCKimlikNo = ?
                    ORDER BY Yil ASC, Periyot ASC
                    """,
                    (self._personel_id, self._personel_id),
                ).fetchall()]
            except sqlite3.OperationalError:
                rows = []
            conn.close()
            self.finished.emit(rows)
        except Exception as exc:
            self.error.emit(str(exc))


# ─── Panel ──────────────────────────────────────────────────
class PersonelDozimetrePanel(QWidget):
    """
    Tek personelin dozimetre geçmişini gösteren panel.

    Parameters
    ----------
    db          : str  — SQLite dosya yolu
    personel_id : str  — Personel.KimlikNo  (TC kimlik no)
    """

    def __init__(self, db: str = "", personel_id: str = "", parent=None):
        super().__init__(parent)
        self._db          = db
        self._personel_id = str(personel_id).strip()
        self._rows:  list[dict]      = []
        self._loader: Optional[_Loader] = None
        self._build_ui()
        if db and personel_id:
            self.load_data()

    # ─── UI ─────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        # ── Özet grup ──
        ozet_group = QGroupBox("Dozimetre Özeti")
        ozet_group.setProperty("style-role", "group")
        ozet_lay = QHBoxLayout(ozet_group)
        ozet_lay.setContentsMargins(16, 12, 16, 12)
        ozet_lay.setSpacing(32)

        self._s_periyot  = self._stat_lbl("Ölçüm Sayısı")
        self._s_son_yil  = self._stat_lbl("Son Yıl / Periyot")
        self._s_ort_hp10 = self._stat_lbl("Ort. Hp(10)")
        self._s_max_hp10 = self._stat_lbl("Maks. Hp(10)")
        self._s_durum    = self._stat_lbl("Genel Durum")

        for w in (self._s_periyot, self._s_son_yil,
                  self._s_ort_hp10, self._s_max_hp10, self._s_durum):
            ozet_lay.addWidget(w)

        ozet_lay.addStretch()

        self.btn_yenile = QPushButton("")
        self.btn_yenile.setToolTip("Yenile")
        self.btn_yenile.setFixedSize(32, 32)
        self.btn_yenile.setProperty("style-role", "refresh")
        self.btn_yenile.setCursor(Qt.CursorShape.PointingHandCursor)
        IconRenderer.set_button_icon(self.btn_yenile, "refresh", color=IconColors.MUTED, size=14)
        self.btn_yenile.clicked.connect(self.load_data)
        ozet_lay.addWidget(self.btn_yenile, alignment=Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(ozet_group)

        # ── Trend ──
        trend_group = QGroupBox("Hp(10) Trendi")
        trend_group.setProperty("style-role", "group")
        trend_lay = QVBoxLayout(trend_group)
        trend_lay.setContentsMargins(12, 8, 12, 8)
        self._trend = _TrendWidget()
        trend_lay.addWidget(self._trend)
        root.addWidget(trend_group)

        # ── Geçmiş tablo ──
        tablo_group = QGroupBox("Periyot Geçmişi")
        tablo_group.setProperty("style-role", "group")
        tablo_lay = QVBoxLayout(tablo_group)
        tablo_lay.setContentsMargins(8, 8, 8, 8)

        self._table = QTableView()
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setProperty("style-role", "table")
        self._model = _DozModel(GECMIS_COLS)
        self._table.setModel(self._model)
        self._model.setup_columns(self._table, stretch_keys=["VucutBolgesi"])
        tablo_lay.addWidget(self._table)
        root.addWidget(tablo_group, 1)

        # ── Durum / boş mesaj ──
        self.lbl_bos = QLabel("Bu personel için dozimetre kaydı bulunamadı.")
        self.lbl_bos.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_bos.setStyleSheet(f"color:{C.TEXT_MUTED};font-size:12px;")
        self.lbl_bos.hide()
        root.addWidget(self.lbl_bos)

    def _stat_lbl(self, title: str) -> QFrame:
        f = QFrame()
        f.setProperty("bg-role", "transparent")
        lay = QVBoxLayout(f)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        t = QLabel(title)
        t.setProperty("color-role", "muted")
        t.setProperty("style-role", "stat-label")
        v = QLabel("—")
        v.setProperty("color-role", "primary")
        v.setProperty("style-role", "stat-value")
        v.setObjectName("val")
        lay.addWidget(t)
        lay.addWidget(v)
        f.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        return f

    @staticmethod
    def _set_stat(card: QFrame, text: str, color: str = ""):
        lbl = card.findChild(QLabel, "val")
        if lbl:
            lbl.setText(text)
            if color:
                lbl.setStyleSheet(
                    f"color:{color};font-size:14px;font-weight:600;")

    # ─── Yükleme ────────────────────────────────────────────
    def load_data(self):
        if not self._db or not self._personel_id:
            return
        if self._loader and self._loader.isRunning():
            return
        self.btn_yenile.setEnabled(False)
        self._loader = _Loader(self._db, self._personel_id)
        self._loader.finished.connect(self._on_load_finished)
        self._loader.error.connect(self._on_load_error)
        self._loader.start()

    def _on_load_finished(self, rows: list):
        self.btn_yenile.setEnabled(True)
        self._rows = rows
        self._model.set_data(rows)
        self._trend.set_data(rows)
        self._update_ozet()

        bos = len(rows) == 0
        self.lbl_bos.setVisible(bos)
        self._table.setVisible(not bos)

    def _on_load_error(self, msg: str):
        self.btn_yenile.setEnabled(True)
        logger.error(f"PersonelDozimetrePanel yükleme hatası ({self._personel_id}): {msg}")

    def _update_ozet(self):
        rows = self._rows
        if not rows:
            for card in (self._s_periyot, self._s_son_yil,
                         self._s_ort_hp10, self._s_max_hp10, self._s_durum):
                self._set_stat(card, "—")
            return

        # Ölçüm sayısı
        self._set_stat(self._s_periyot, str(len(rows)), C.ACCENT)

        # Son yıl / periyot
        son = rows[-1]
        self._set_stat(self._s_son_yil,
                       f"{son.get('Yil','')} / {son.get('Periyot','')} ({son.get('PeriyotAdi','')})")

        # Hp10 istatistikleri
        hp10s = []
        for r in rows:
            try: hp10s.append(float(r.get("Hp10") or 0))
            except (ValueError, TypeError): pass

        if hp10s:
            ort = sum(hp10s) / len(hp10s)
            mx  = max(hp10s)
            ort_renk = ("#f87171" if ort >= HP10_TEHLIKE else
                        "#facc15" if ort >= HP10_UYARI else "#4ade80")
            mx_renk  = ("#f87171" if mx  >= HP10_TEHLIKE else
                        "#facc15" if mx  >= HP10_UYARI else "#4ade80")
            self._set_stat(self._s_ort_hp10, f"{ort:.3f} mSv", ort_renk)
            self._set_stat(self._s_max_hp10, f"{mx:.3f} mSv",  mx_renk)
        else:
            self._set_stat(self._s_ort_hp10, "—")
            self._set_stat(self._s_max_hp10, "—")

        # Genel durum — son periyot Durum alanına göre
        son_durum = str(son.get("Durum", "")).strip()
        if "Aşım" in son_durum:
            self._set_stat(self._s_durum, "Doz Aşımı", "#f87171")
        else:
            # Trend: son değer ≤ ilk değer → azalıyor
            if len(hp10s) >= 2:
                trend = "↓ Azalıyor" if hp10s[-1] <= hp10s[0] else "↑ Artıyor"
                renk  = "#4ade80" if hp10s[-1] <= hp10s[0] else "#facc15"
            else:
                trend = "Sınırın Altında"
                renk  = "#4ade80"
            self._set_stat(self._s_durum, trend, renk)

    # ─── Dışarıdan ayarlama ─────────────────────────────────
    def set_personel(self, db: str, personel_id: str):
        """Farklı personel için paneli yeniden yükler."""
        self._db          = db
        self._personel_id = str(personel_id).strip()
        self.load_data()

    # PersonelMerkez ile uyumlu interface
    def set_embedded_mode(self, mode):
        pass

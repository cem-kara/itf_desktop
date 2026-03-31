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

from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal as _Signal
from PySide6.QtGui import QColor, QPainter, QPen, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGroupBox, QTableView, QAbstractItemView, QPushButton,
    QSizePolicy,
)

from core.logger import logger
from ui.components.base_table_model import BaseTableModel
from ui.styles.icons import IconRenderer, IconColors

# NDK Doz Limitleri (Radyasyon Güvenliği Yönetmeliği)
HP10_UYARI     = 2.0    # mSv — periyot inceleme düzeyi
HP10_TEHLIKE   = 5.0    # mSv — tehlike eşiği
YILLIK_LIMIT   = 20.0   # mSv — 5 yıl ortalaması
YILLIK_MAX     = 50.0   # mSv — tek yılda mutlak max
BES_YILLIK     = 100.0  # mSv — ardışık 5 yıl toplamı
CALISMA_A      = 6.0    # mSv — Çalışma Koşulu A eşiği
PERIYOT_SAYISI = 4      # RADAT yılda 4 periyot

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
        hp10s  = []
        hp007s = []
        labels = []
        for r in rows:
            try:
                hp10s.append(float(r.get("Hp10") or 0))
                hp007s.append(float(r.get("Hp007") or 0))
                labels.append(f"{r.get('Yil','')}-{r.get('Periyot','')}")
            except (ValueError, TypeError):
                pass

        if len(hp10s) < 2:
            p.setPen(QColor("#4d6070"))  # TEXT_MUTED
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

        # İnceleme eşiği çizgisi
        if 0 < HP10_UYARI <= mx:
            p.setPen(QPen(QColor("#facc1550"), 1, Qt.PenStyle.DashLine))
            p.drawLine(pl, py(HP10_UYARI), w - pr, py(HP10_UYARI))

        # Hp(10) — mavi, kalın
        p.setPen(QPen(QColor("#3d8ef5"), 2))  # ACCENT
        for i in range(n - 1):
            p.drawLine(px(i), py(hp10s[i]), px(i + 1), py(hp10s[i + 1]))
        for i, v in enumerate(hp10s):
            c = ("#f87171" if v >= HP10_TEHLIKE else
                 "#facc15" if v >= HP10_UYARI else "#4ade80")
            p.setBrush(QColor(c)); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(px(i) - 4, py(v) - 4, 8, 8)

        # Hp(0,07) — turuncu, kesik
        p.setPen(QPen(QColor("#fb923c"), 1, Qt.PenStyle.DashLine))
        for i in range(n - 1):
            p.drawLine(px(i), py(hp007s[i]), px(i + 1), py(hp007s[i + 1]))
        for i, v in enumerate(hp007s):
            p.setBrush(QColor("#fb923c")); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(px(i) - 2, py(v) - 2, 5, 5)

        # Etiketler
        p.setPen(QColor("#4d6070"))  # TEXT_MUTED
        if labels:
            p.drawText(pl, h - 5, labels[0])
            p.drawText(w - pr - 45, h - 5, labels[-1])

        # Legend
        p.setPen(QColor("#3d8ef5"))  # ACCENT
        p.drawText(w - pr - 90, pt + 10, "— Hp(10)")
        p.setPen(QColor("#fb923c"))
        p.drawText(w - pr - 90, pt + 20, "-- Hp(0,07)")


# ─── Gauge Widget ────────────────────────────────────────────
class _GaugeWidget(QWidget):
    """Yıllık veya 5 yıllık doz limitine göre doluluk çubuğu."""

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
        w, h = self.width(), self.height()

        p.setPen(QColor("#4d6070"))  # TEXT_MUTED
        p.setFont(QFont("", 8))
        p.drawText(0, 12, self._baslik)

        bar_y, bar_h = 18, 10
        p.setBrush(QColor("#232a3a")); p.setPen(Qt.PenStyle.NoPen)  # BG_TERTIARY
        p.drawRoundedRect(0, bar_y, w, bar_h, 4, 4)

        if oran > 0:
            renk = (QColor("#f87171") if oran >= self._esik2 else
                    QColor("#facc15") if oran >= self._esik1 else
                    QColor("#4ade80"))
            p.setBrush(renk)
            p.drawRoundedRect(0, bar_y, int(w * oran), bar_h, 4, 4)

        p.setPen(QColor("#e8edf5"))  # TEXT_PRIMARY
        p.setFont(QFont("", 8, QFont.Weight.Bold))
        p.drawText(0, bar_y + bar_h + 14,
                   f"{self._deger:.2f} / {self._limit:.0f} mSv  (%{oran*100:.0f})")


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
            from database.sqlite_manager import SQLiteManager
            from core.di import get_dozimetre_service
            from core.paths import DB_PATH

            db_path = getattr(self._db, "db_path", None) or str(self._db) if self._db else DB_PATH
            db = SQLiteManager(db_path=db_path, check_same_thread=False)
            svc = get_dozimetre_service(db)

            rows = svc.get_olcumler_by_personel(self._personel_id).veri or []
            db.close()
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
        trend_group = QGroupBox("Hp(10) ── Hp(0,07) --  Trend")
        trend_group.setProperty("style-role", "group")
        trend_lay = QVBoxLayout(trend_group)
        trend_lay.setContentsMargins(12, 8, 12, 8)
        self._trend = _TrendWidget()
        trend_lay.addWidget(self._trend)
        root.addWidget(trend_group)

        # ── NDK Limit Gauge'ları ──
        limit_group = QGroupBox("NDK Doz Limitleri")
        limit_group.setProperty("style-role", "group")
        limit_lay = QHBoxLayout(limit_group)
        limit_lay.setContentsMargins(16, 12, 16, 12)
        limit_lay.setSpacing(24)

        self._gauge_yillik = _GaugeWidget(
            f"Yıllık Kümülatif Hp(10)  [NDK: {YILLIK_LIMIT:.0f} mSv]",
            YILLIK_LIMIT, 0.5, 0.75
        )
        self._gauge_5yil = _GaugeWidget(
            f"5 Yıllık Kümülatif Hp(10)  [NDK: {BES_YILLIK:.0f} mSv]",
            BES_YILLIK, 0.5, 0.75
        )
        self.lbl_periyot_doluluk = QLabel("")
        self.lbl_periyot_doluluk.setWordWrap(True)
        self.lbl_periyot_doluluk.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        limit_lay.addWidget(self._gauge_yillik, 2)
        limit_lay.addWidget(self._gauge_5yil, 2)
        limit_lay.addWidget(self.lbl_periyot_doluluk, 1)
        root.addWidget(limit_group)

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
        self.lbl_bos.setProperty("color-role", "primary")
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
            self._gauge_yillik.set_deger(0.0)
            self._gauge_5yil.set_deger(0.0)
            self.lbl_periyot_doluluk.setText("")
            return

        # Ölçüm sayısı
        self._set_stat(self._s_periyot, str(len(rows)), "#3d8ef5")  # ACCENT

        # Son yıl / periyot
        son = rows[-1]
        son_yil = son.get("Yil", "")
        self._set_stat(self._s_son_yil,
                       f"{son_yil} / {son.get('Periyot','')} ({son.get('PeriyotAdi','')})")

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

        # Genel durum — Çalışma Koşulu + trend
        son_durum = str(son.get("Durum", "")).strip()
        yil_veriler = [r for r in rows if str(r.get("Yil","")) == str(son_yil)]
        yillik_hp10 = sum(float(r.get("Hp10") or 0) for r in yil_veriler
                          if r.get("Hp10") is not None)
        if "Aşım" in son_durum:
            self._set_stat(self._s_durum, "⚠ Doz Aşımı", "#f87171")
        elif yillik_hp10 >= CALISMA_A:
            self._set_stat(self._s_durum, "Doz Bazlı Koşul A (>6 mSv)", "#facc15")
        elif len(hp10s) >= 2:
            trend = "↓ Azalıyor" if hp10s[-1] <= hp10s[0] else "↑ Artıyor"
            renk  = "#4ade80" if hp10s[-1] <= hp10s[0] else "#facc15"
            self._set_stat(self._s_durum, trend, renk)
        else:
            self._set_stat(self._s_durum, "Sınırın Altında", "#4ade80")

        # Yıllık gauge (son yıl)
        self._gauge_yillik.set_deger(yillik_hp10)

        # 5 yıllık gauge
        try:
            yil_int    = int(son_yil)
            yil_aralik = set(range(yil_int - 4, yil_int + 1))
            bes_hp10   = sum(float(r.get("Hp10") or 0) for r in rows
                             if r.get("Yil") in yil_aralik and r.get("Hp10") is not None)
        except (ValueError, TypeError):
            bes_hp10 = sum(hp10s)
        self._gauge_5yil.set_deger(bes_hp10)

        # Periyot doluluk (son yıl)
        kayitli = {r.get("Periyot") for r in yil_veriler}
        eksik   = [i for i in range(1, PERIYOT_SAYISI + 1) if i not in kayitli]
        if not eksik:
            doluluk_metin = f"✔ {son_yil} yılı\n{PERIYOT_SAYISI}/{PERIYOT_SAYISI} periyot kayıtlı"
            doluluk_renk  = "#4ade80"
        else:
            doluluk_metin = (f"⚠ {son_yil} yılı\n{len(kayitli)}/{PERIYOT_SAYISI} periyot  |  "
                             f"Eksik: {', '.join(str(e) for e in eksik)}. periyot")
            doluluk_renk = "#facc15"
        self.lbl_periyot_doluluk.setText(doluluk_metin)
        self.lbl_periyot_doluluk.setProperty("color-role", "primary")

    # ─── Dışarıdan ayarlama ─────────────────────────────────
    def set_personel(self, db: str, personel_id: str):
        """Farklı personel için paneli yeniden yükler."""
        self._db          = db
        self._personel_id = str(personel_id).strip()
        self.load_data()

    # PersonelMerkez ile uyumlu interface
    def set_embedded_mode(self, mode):
        pass

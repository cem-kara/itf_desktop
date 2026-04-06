# -*- coding: utf-8 -*-
# REPYS v0.4.0 — 2026-04-06  (yeniden yapılandırılmış)
"""
ui/pages/personel/components/personel_dozimetre_panel.py
─────────────────────────────────────────────────────────
PersonelMerkezPage içinde kullanılmak üzere tek bir personelin
dozimetre geçmişini gösteren ana panel.

Bağımlı modüller (aynı klasörde):
    _dozimetre_widgets.py   → _DozModel, _TrendWidget, _GaugeWidget
    _yuksek_doz_panel.py    → _YuksekDozBildirimPanel

Kullanım:
    from ui.pages.personel.components.personel_dozimetre_panel import PersonelDozimetrePanel
    panel = PersonelDozimetrePanel(db=self.db, personel_id=self.personel_id)
"""
from __future__ import annotations

import os
import sys
import subprocess
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal as _Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGroupBox, QTableView, QAbstractItemView, QPushButton,
    QSizePolicy,
)

from core.logger import logger

from ._dozimetre_widgets import (
    _DozModel, _TrendWidget, _GaugeWidget,
    GECMIS_COLS, HP10_UYARI, HP10_TEHLIKE,
    YILLIK_LIMIT, BES_YILLIK, CALISMA_A, PERIYOT_SAYISI,
)
from ._yuksek_doz_panel import _YuksekDozBildirimPanel
from ui.styles.icons import IconRenderer, IconColors


# ─── Arka plan veri yükleyici ────────────────────────────────

class _Loader(QThread):
    finished = _Signal(list)
    error    = _Signal(str)

    def __init__(self, db, personel_id: str):
        super().__init__()
        self._db          = db
        self._personel_id = personel_id

    def run(self):
        try:
            from database.sqlite_manager import SQLiteManager
            from core.di import get_dozimetre_service
            from core.paths import DB_PATH

            db_path = (
                getattr(self._db, "db_path", None)
                or str(self._db)
                if self._db else DB_PATH
            )
            db   = SQLiteManager(db_path=db_path, check_same_thread=False)
            svc  = get_dozimetre_service(db)
            rows = svc.get_olcumler_by_personel(self._personel_id).veri or []
            db.close()
            self.finished.emit(rows)
        except Exception as exc:
            self.error.emit(str(exc))


# ─── Ana Panel ───────────────────────────────────────────────

class PersonelDozimetrePanel(QWidget):
    """
    Tek personelin dozimetre geçmişini gösteren panel.

    Parameters
    ----------
    db          : SQLiteManager veya db_path string
    personel_id : Personel.KimlikNo (TC kimlik no)
    """

    def __init__(self, db=None, personel_id: str = "", parent=None):
        super().__init__(parent)
        self._db          = db
        self._personel_id = str(personel_id).strip()
        self._rows:  list[dict]         = []
        self._loader: Optional[_Loader] = None
        self._build_ui()
        if db and personel_id:
            self.load_data()

    # ─── UI ──────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # ── Özet kartı ──────────────────────────────────────
        ozet_group = QGroupBox("Dozimetre Özeti")
        ozet_group.setProperty("style-role", "group")
        ozet_lay = QHBoxLayout(ozet_group)
        ozet_lay.setContentsMargins(16, 10, 16, 10)
        ozet_lay.setSpacing(28)

        self._s_periyot  = self._stat_card("Ölçüm Sayısı")
        self._s_son_yil  = self._stat_card("Son Yıl / Periyot")
        self._s_ort_hp10 = self._stat_card("Ort. Hp(10)")
        self._s_max_hp10 = self._stat_card("Maks. Hp(10)")
        self._s_durum    = self._stat_card("Genel Durum")

        for w in (self._s_periyot, self._s_son_yil,
                  self._s_ort_hp10, self._s_max_hp10, self._s_durum):
            ozet_lay.addWidget(w)

        ozet_lay.addStretch()

        self.btn_yenile = QPushButton("")
        self.btn_yenile.setToolTip("Yenile")
        self.btn_yenile.setFixedSize(32, 32)
        self.btn_yenile.setProperty("style-role", "refresh")
        self.btn_yenile.setCursor(Qt.CursorShape.PointingHandCursor)
        IconRenderer.set_button_icon(
            self.btn_yenile, "refresh", color=IconColors.MUTED, size=14
        )
        self.btn_yenile.clicked.connect(self.load_data)
        ozet_lay.addWidget(self.btn_yenile, alignment=Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(ozet_group)

        # ── Trend grafiği ─────────────────────────────────────
        trend_group = QGroupBox("Hp(10) \u2500\u2500 Hp(0,07) --  Trend")
        trend_group.setProperty("style-role", "group")
        trend_lay = QVBoxLayout(trend_group)
        trend_lay.setContentsMargins(12, 8, 12, 8)
        self._trend = _TrendWidget()
        trend_lay.addWidget(self._trend)
        root.addWidget(trend_group)

        # ── NDK Limit Gauge'ları ──────────────────────────────
        limit_group = QGroupBox("NDK Doz Limitleri")
        limit_group.setProperty("style-role", "group")
        limit_lay = QHBoxLayout(limit_group)
        limit_lay.setContentsMargins(16, 10, 16, 10)
        limit_lay.setSpacing(24)

        self._gauge_yillik = _GaugeWidget(
            f"Y\u0131ll\u0131k K\u00fcm\u00fclatif Hp(10)  [NDK: {YILLIK_LIMIT:.0f} mSv]",
            YILLIK_LIMIT, 0.5, 0.75,
        )
        self._gauge_5yil = _GaugeWidget(
            f"5 Y\u0131ll\u0131k K\u00fcm\u00fclatif Hp(10)  [NDK: {BES_YILLIK:.0f} mSv]",
            BES_YILLIK, 0.5, 0.75,
        )
        self.lbl_periyot_doluluk = QLabel("")
        self.lbl_periyot_doluluk.setWordWrap(True)
        self.lbl_periyot_doluluk.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        limit_lay.addWidget(self._gauge_yillik, 2)
        limit_lay.addWidget(self._gauge_5yil, 2)
        limit_lay.addWidget(self.lbl_periyot_doluluk, 1)
        root.addWidget(limit_group)

        # ── Y\u00fcksek Doz Bildirimleri ───────────────────────────
        self._yuksek_doz_panel = _YuksekDozBildirimPanel()
        root.addWidget(self._yuksek_doz_panel)

        # ── Ge\u00e7mi\u015f tablo ──────────────────────────────────────
        tablo_group = QGroupBox("Periyot Ge\u00e7mi\u015fi")
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

        self.lbl_bos = QLabel("Bu personel i\u00e7in dozimetre kayd\u0131 bulunamad\u0131.")
        self.lbl_bos.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_bos.setProperty("color-role", "primary")
        self.lbl_bos.hide()
        root.addWidget(self.lbl_bos)

    def _stat_card(self, baslik: str) -> QFrame:
        f = QFrame()
        f.setProperty("bg-role", "transparent")
        lay = QVBoxLayout(f)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        t = QLabel(baslik)
        t.setProperty("color-role", "muted")
        t.setProperty("style-role", "stat-label")
        v = QLabel("\u2014")
        v.setProperty("color-role", "primary")
        v.setProperty("style-role", "stat-value")
        v.setObjectName("val")
        lay.addWidget(t)
        lay.addWidget(v)
        f.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        return f

    @staticmethod
    def _set_stat(card: QFrame, metin: str, renk: str = ""):
        lbl = card.findChild(QLabel, "val")
        if lbl:
            lbl.setText(metin)
            if renk:
                lbl.setStyleSheet(f"color:{renk};font-size:14px;font-weight:600;")

    # ─── Y\u00fckleme ─────────────────────────────────────────────

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
        self._yuksek_doz_panel.guncelle(rows)
        self._bagla_form_butonu(rows)
        bos = not rows
        self.lbl_bos.setVisible(bos)
        self._table.setVisible(not bos)

    def _on_load_error(self, msg: str):
        self.btn_yenile.setEnabled(True)
        logger.error(f"PersonelDozimetrePanel y\u00fckleme hatas\u0131 ({self._personel_id}): {msg}")

    # ─── Form butonu y\u00f6netimi ─────────────────────────────────

    def _bagla_form_butonu(self, rows: list):
        asim_rows = [r for r in rows if float(r.get("Hp10") or 0) >= HP10_UYARI]
        if not asim_rows:
            self._yuksek_doz_panel.bagla_form_butonu(None)
            return

        hedef  = max(asim_rows, key=lambda r: float(r.get("Hp10") or 0))
        mevcut = self._form_kayit_getir(hedef)

        if mevcut:
            pdf = mevcut["PdfYolu"]
            self._yuksek_doz_panel.bagla_form_butonu(
                lambda checked=False, p=pdf: self._pdf_ac(p),
                buton_metni="\U0001f4c4  Formu G\u00f6r\u00fcnt\u00fcle",
            )
        else:
            self._yuksek_doz_panel.bagla_form_butonu(
                lambda checked=False, r=hedef: self._form_doldur(r),
                buton_metni="\U0001f4cb  Doz Ara\u015ft\u0131rma Formu A\u00e7",
            )

    def _form_kayit_getir(self, row: dict) -> dict | None:
        if not self._db:
            return None
        try:
            from core.di import get_dozimetre_service
            svc = get_dozimetre_service(self._db)
            return svc.form_var_mi(
                self._personel_id,
                int(row.get("Yil") or 0),
                int(row.get("Periyot") or 0),
            )
        except Exception as exc:
            logger.warning(f"Form kayit sorgu hatas\u0131: {exc}")
            return None

    def _pdf_ac(self, pdf_yolu: str):
        if not os.path.exists(pdf_yolu):
            logger.warning(f"PDF bulunamad\u0131: {pdf_yolu}")
            return
        try:
            if sys.platform == "win32":
                os.startfile(pdf_yolu)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", pdf_yolu])
            else:
                subprocess.Popen(["xdg-open", pdf_yolu])
        except Exception as exc:
            logger.error(f"PDF a\u00e7ma hatas\u0131: {exc}")

    def _form_doldur(self, row: dict):
        try:
            from ui.dialogs.doz_arastirma_formu_dialog import DozArastirmaFormuDialog
            kayit = dict(row)
            kayit.setdefault("KimlikNo", self._personel_id)
            dlg = DozArastirmaFormuDialog(
                olcum_kaydi=kayit,
                db=self._db,
                personel_id=self._personel_id,
                parent=self,
            )
            if dlg.exec():
                pdf_yolu = dlg.get_saved_pdf_path()
                if pdf_yolu and self._db:
                    self._form_meta_kaydet(row, pdf_yolu)
                if pdf_yolu:
                    self._yuksek_doz_panel.bagla_form_butonu(
                        lambda checked=False, p=pdf_yolu: self._pdf_ac(p),
                        buton_metni="\U0001f4c4  Formu G\u00f6r\u00fcnt\u00fcle",
                    )
                logger.info(f"Doz Ara\u015ft\u0131rma Formu olu\u015fturuldu: {pdf_yolu}")
        except Exception as exc:
            logger.error(f"Form doldurma hatas\u0131: {exc}")

    def _form_meta_kaydet(self, row: dict, pdf_yolu: str):
        try:
            from core.di import get_dozimetre_service
            svc = get_dozimetre_service(self._db)
            svc.form_kaydet(
                personel_id    = self._personel_id,
                yil            = int(row.get("Yil") or 0),
                periyot        = int(row.get("Periyot") or 0),
                olculen_doz    = float(row.get("Hp10") or 0),
                pdf_yolu       = pdf_yolu,
                olcum_kayit_no = str(row.get("KayitNo") or ""),
            )
        except Exception as exc:
            logger.error(f"Form meta kayit hatas\u0131: {exc}")

    # ─── \u00d6zet g\u00fcncelleme ─────────────────────────────────────

    def _update_ozet(self):
        rows = self._rows
        if not rows:
            for card in (self._s_periyot, self._s_son_yil,
                         self._s_ort_hp10, self._s_max_hp10, self._s_durum):
                self._set_stat(card, "\u2014")
            self._gauge_yillik.set_deger(0.0)
            self._gauge_5yil.set_deger(0.0)
            self.lbl_periyot_doluluk.setText("")
            return

        self._set_stat(self._s_periyot, str(len(rows)), "#3d8ef5")

        son     = rows[-1]
        son_yil = son.get("Yil", "")
        self._set_stat(
            self._s_son_yil,
            f"{son_yil} / {son.get('Periyot','')} ({son.get('PeriyotAdi','')})",
        )

        hp10s = []
        for r in rows:
            try:
                hp10s.append(float(r.get("Hp10") or 0))
            except (ValueError, TypeError):
                pass

        if hp10s:
            ort = sum(hp10s) / len(hp10s)
            mx  = max(hp10s)
            def _renk(v):
                return ("#f87171" if v >= HP10_TEHLIKE else
                        "#facc15" if v >= HP10_UYARI   else "#4ade80")
            self._set_stat(self._s_ort_hp10, f"{ort:.3f} mSv", _renk(ort))
            self._set_stat(self._s_max_hp10, f"{mx:.3f} mSv",  _renk(mx))
        else:
            self._set_stat(self._s_ort_hp10, "\u2014")
            self._set_stat(self._s_max_hp10, "\u2014")

        son_durum   = str(son.get("Durum", "")).strip()
        yil_veriler = [r for r in rows if str(r.get("Yil", "")) == str(son_yil)]
        yillik_hp10 = sum(
            float(r.get("Hp10") or 0) for r in yil_veriler
            if r.get("Hp10") is not None
        )

        if "A\u015f\u0131m" in son_durum:
            self._set_stat(self._s_durum, "\u26a0 Doz A\u015f\u0131m\u0131", "#f87171")
        elif yillik_hp10 >= CALISMA_A:
            self._set_stat(self._s_durum, "Ko\u015ful A (>6 mSv)", "#facc15")
        elif len(hp10s) >= 2:
            trend = "\u2193 Azal\u0131yor" if hp10s[-1] <= hp10s[0] else "\u2191 Art\u0131yor"
            renk  = "#4ade80"            if hp10s[-1] <= hp10s[0] else "#facc15"
            self._set_stat(self._s_durum, trend, renk)
        else:
            self._set_stat(self._s_durum, "S\u0131n\u0131r\u0131n Alt\u0131nda", "#4ade80")

        self._gauge_yillik.set_deger(yillik_hp10)
        try:
            yil_int    = int(son_yil)
            yil_aralik = set(range(yil_int - 4, yil_int + 1))
            bes_hp10   = sum(
                float(r.get("Hp10") or 0) for r in rows
                if r.get("Yil") in yil_aralik and r.get("Hp10") is not None
            )
        except (ValueError, TypeError):
            bes_hp10 = sum(hp10s)
        self._gauge_5yil.set_deger(bes_hp10)

        kayitli = {r.get("Periyot") for r in yil_veriler}
        eksik   = [i for i in range(1, PERIYOT_SAYISI + 1) if i not in kayitli]
        if not eksik:
            metin = f"\u2714 {son_yil} y\u0131l\u0131\n{PERIYOT_SAYISI}/{PERIYOT_SAYISI} periyot kay\u0131tl\u0131"
        else:
            metin = (
                f"\u26a0 {son_yil} y\u0131l\u0131\n"
                f"{len(kayitli)}/{PERIYOT_SAYISI} periyot  |  "
                f"Eksik: {', '.join(str(e) for e in eksik)}. periyot"
            )
        self.lbl_periyot_doluluk.setText(metin)
        self.lbl_periyot_doluluk.setProperty("color-role", "primary")

    # ─── Harici aray\u00fcz ──────────────────────────────────────────

    def set_personel(self, db, personel_id: str):
        self._db          = db
        self._personel_id = str(personel_id).strip()
        self.load_data()

    def set_embedded_mode(self, mode):
        pass

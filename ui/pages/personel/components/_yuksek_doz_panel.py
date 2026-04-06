# -*- coding: utf-8 -*-
"""
ui/pages/personel/components/_yuksek_doz_panel.py
──────────────────────────────────────────────────
Yüksek doz aşımı bildirimleri için panel bileşenleri:
  _YuksekDozKartWidget    — Tek aşım periyodunu gösteren kart
  _YuksekDozBildirimPanel — Tüm aşımların listelendiği GroupBox
"""
from __future__ import annotations

import os
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QGroupBox, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from core.logger import logger
from ._dozimetre_widgets import HP10_UYARI, HP10_TEHLIKE

# Kısa önlem etiketleri (bullet'sız)
_ONLEM = {
    "tehlike": "⛔  Acil Değerlendirme Gerekli",
    "uyari":   "⚠  İnceleme Başlatılmalı",
}


class _YuksekDozKartWidget(QFrame):
    """Tek bir yüksek doz periyodunu gösteren kompakt kart."""

    def __init__(self, row: dict, limit_tipi: str, parent=None):
        super().__init__(parent)
        self.setProperty("bg-role", "panel")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._build(row, limit_tipi)

    def _build(self, row: dict, limit_tipi: str):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 7, 10, 7)
        lay.setSpacing(10)

        # İkon + seviye
        ikon_col = QVBoxLayout()
        ikon_col.setAlignment(Qt.AlignmentFlag.AlignTop)
        ikon_lbl = QLabel("⛔" if limit_tipi == "tehlike" else "⚠")
        ikon_lbl.setProperty("color-role",
            "danger" if limit_tipi == "tehlike" else "warning")
        ikon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sev_lbl = QLabel("TEHLİKE" if limit_tipi == "tehlike" else "UYARI")
        sev_lbl.setProperty("color-role",
            "danger" if limit_tipi == "tehlike" else "warning")
        sev_lbl.setProperty("style-role", "badge")
        sev_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ikon_col.addWidget(ikon_lbl)
        ikon_col.addWidget(sev_lbl)
        lay.addLayout(ikon_col)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setProperty("color-role", "muted")
        lay.addWidget(sep)

        # Bilgi kolonu
        bilgi = QVBoxLayout()
        bilgi.setSpacing(2)

        yil   = str(row.get("Yil", "—"))
        per   = str(row.get("Periyot", "—"))
        peradi = str(row.get("PeriyotAdi", ""))

        # Başlık
        bas_lay = QHBoxLayout()
        per_lbl = QLabel(f"📅 {yil} yılı — {per}. Periyot")
        per_lbl.setProperty("color-role", "primary")
        per_lbl.setProperty("style-role", "bold")
        bas_lay.addWidget(per_lbl)
        if peradi:
            adi_lbl = QLabel(f"({peradi})")
            adi_lbl.setProperty("color-role", "muted")
            bas_lay.addWidget(adi_lbl)
        bas_lay.addStretch()
        bilgi.addLayout(bas_lay)

        # Doz değerleri
        doz_lay = QHBoxLayout()
        doz_lay.setSpacing(12)
        try:
            hp10  = float(row.get("Hp10")  or 0)
            hp007 = float(row.get("Hp007") or 0)
        except (ValueError, TypeError):
            hp10, hp007 = 0.0, 0.0

        hp10_renk = ("danger"  if hp10 >= HP10_TEHLIKE else
                     "warning" if hp10 >= HP10_UYARI   else "success")
        hp10_lbl = QLabel(f"Hp(10) = {hp10:.3f} mSv")
        hp10_lbl.setProperty("color-role", hp10_renk)
        hp10_lbl.setProperty("style-role", "mono")
        doz_lay.addWidget(hp10_lbl)

        if hp007 > 0:
            hp007_lbl = QLabel(f"Hp(0,07) = {hp007:.3f} mSv")
            hp007_lbl.setProperty("color-role", "muted")
            hp007_lbl.setProperty("style-role", "mono")
            doz_lay.addWidget(hp007_lbl)

        esik  = HP10_TEHLIKE if limit_tipi == "tehlike" else HP10_UYARI
        asim  = hp10 - esik
        if asim > 0:
            asim_lbl = QLabel(f"(+{asim:.3f} mSv eşik üstü)")
            asim_lbl.setProperty("color-role",
                "danger" if limit_tipi == "tehlike" else "warning")
            doz_lay.addWidget(asim_lbl)
        doz_lay.addStretch()
        bilgi.addLayout(doz_lay)

        # Alt bilgi
        alt_lay = QHBoxLayout()
        alt_lay.setSpacing(12)
        for etiket, deger_key in [
            ("Dzm. No:", "DozimetreNo"),
            ("Bölge:", "VucutBolgesi"),
            ("Kayıt:", "Durum"),
        ]:
            val = str(row.get(deger_key, "")).strip()
            if val:
                lbl = QLabel(f"{etiket} {val}")
                lbl.setProperty("color-role",
                    "danger" if "Aşım" in val and deger_key == "Durum" else "muted")
                alt_lay.addWidget(lbl)
        alt_lay.addStretch()
        bilgi.addLayout(alt_lay)

        lay.addLayout(bilgi, 1)


class _YuksekDozBildirimPanel(QGroupBox):
    """
    Tüm doz aşımı periyotlarını listeleyen bildirim paneli.

    Kullanım:
        panel = _YuksekDozBildirimPanel()
        panel.guncelle(rows)                        # dozimetre kayıtları
        panel.bagla_form_butonu(slot_fonksiyon)     # buton bağlantısı
    """

    def __init__(self, parent=None):
        super().__init__("🔔 Yüksek Doz Bildirimleri", parent)
        self.setProperty("style-role", "group")
        self._slot_form_ac: Optional[object] = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(5)

        # ── Özet + buton satırı ──────────────────────────────
        ozet_bar = QHBoxLayout()
        ozet_bar.setSpacing(14)

        self._lbl_tehlike = self._chip("danger")
        self._lbl_uyari   = self._chip("warning")
        self._lbl_son     = self._chip("muted")
        self._lbl_son.setMinimumWidth(180)

        self._btn_form_ac = QPushButton("📋  Doz Araştırma Formu Aç")
        self._btn_form_ac.setProperty("style-role", "action")
        self._btn_form_ac.setFixedHeight(26)
        self._btn_form_ac.hide()

        ozet_bar.addWidget(self._lbl_tehlike)
        ozet_bar.addWidget(self._lbl_uyari)
        ozet_bar.addWidget(self._lbl_son)
        ozet_bar.addStretch()
        ozet_bar.addWidget(self._btn_form_ac)
        root.addLayout(ozet_bar)

        # ── Ayraç ────────────────────────────────────────────
        self._sep = QFrame()
        self._sep.setFrameShape(QFrame.Shape.HLine)
        self._sep.setProperty("color-role", "muted")
        root.addWidget(self._sep)

        # ── Kart listesi ──────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setProperty("bg-role", "transparent")
        scroll.setMinimumHeight(100)
        scroll.setMaximumHeight(300)

        self._kartlar_widget = QWidget()
        self._kartlar_widget.setProperty("bg-role", "transparent")
        self._kartlar_lay = QVBoxLayout(self._kartlar_widget)
        self._kartlar_lay.setContentsMargins(0, 0, 0, 0)
        self._kartlar_lay.setSpacing(5)

        self._lbl_temiz = QLabel(
            "✅  İncelenen periyotlarda doz limiti aşımı tespit edilmedi."
        )
        self._lbl_temiz.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_temiz.setProperty("color-role", "success")
        self._kartlar_lay.addWidget(self._lbl_temiz)
        self._kartlar_lay.addStretch()

        scroll.setWidget(self._kartlar_widget)
        root.addWidget(scroll, 1)

        # ── Kısa önlem notu ───────────────────────────────────
        self._onlem_lbl = QLabel("")
        self._onlem_lbl.setProperty("color-role", "muted")
        self._onlem_lbl.setProperty("style-role", "caption")
        self._onlem_lbl.hide()
        root.addWidget(self._onlem_lbl)

    @staticmethod
    def _chip(color_role: str) -> QLabel:
        lbl = QLabel("—")
        lbl.setProperty("style-role", "stat-chip")
        lbl.setProperty("color-role", color_role)
        return lbl

    # ── Güncelleme ────────────────────────────────────────────

    def guncelle(self, rows: list[dict]):
        """Dozimetre kayıt listesinden aşım periyotlarını çizer."""
        # Eski kartları temizle
        while self._kartlar_lay.count() > 2:
            item = self._kartlar_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tehlike_rows, uyari_rows = [], []
        for r in rows:
            try:
                hp10 = float(r.get("Hp10") or 0)
            except (ValueError, TypeError):
                continue
            if hp10 >= HP10_TEHLIKE:
                tehlike_rows.append(r)
            elif hp10 >= HP10_UYARI:
                uyari_rows.append(r)

        bos = not tehlike_rows and not uyari_rows

        # Özet chip'leri
        self._lbl_tehlike.setText(f"⛔ Tehlike: {len(tehlike_rows)} periyot")
        self._lbl_uyari.setText(f"⚠ Uyarı: {len(uyari_rows)} periyot")

        tum = sorted(
            tehlike_rows + uyari_rows,
            key=lambda r: (int(r.get("Yil") or 0), int(r.get("Periyot") or 0)),
        )
        if tum:
            son = tum[-1]
            self._lbl_son.setText(
                f"Son Aşım: {son.get('Yil','?')}/{son.get('Periyot','?')}. Periyot"
            )
        else:
            self._lbl_son.setText("Son Aşım: —")

        # Kartlar (en yeni üstte)
        self._lbl_temiz.setVisible(bos)
        self._sep.setVisible(not bos)

        if not bos:
            siralananlar = sorted(
                [(r, "tehlike") for r in tehlike_rows] +
                [(r, "uyari")   for r in uyari_rows],
                key=lambda x: (
                    -int(x[0].get("Yil")     or 0),
                    -int(x[0].get("Periyot") or 0),
                ),
            )
            for r, tip in siralananlar:
                kart = _YuksekDozKartWidget(r, tip, self._kartlar_widget)
                self._kartlar_lay.insertWidget(
                    self._kartlar_lay.count() - 1, kart
                )

        # Önlem notu (sadece etiket)
        if tehlike_rows:
            self._onlem_lbl.setText(_ONLEM["tehlike"])
            self._onlem_lbl.setProperty("color-role", "danger")
            self._onlem_lbl.show()
        elif uyari_rows:
            self._onlem_lbl.setText(_ONLEM["uyari"])
            self._onlem_lbl.setProperty("color-role", "warning")
            self._onlem_lbl.show()
        else:
            self._onlem_lbl.hide()

        # Buton görünürlüğü
        self._btn_form_ac.setVisible(not bos)

        self.style().unpolish(self)
        self.style().polish(self)

    def bagla_form_butonu(self, slot, buton_metni: str = "📋  Doz Araştırma Formu Aç"):
        """
        Form açma butonunu verilen slot'a bağlar.
        Önceki bağlantı argümanlı disconnect ile koparılır → RuntimeWarning yok.
        """
        if self._slot_form_ac is not None:
            try:
                self._btn_form_ac.clicked.disconnect(self._slot_form_ac)
            except (RuntimeError, TypeError):
                pass
        self._slot_form_ac = slot
        if slot is not None:
            self._btn_form_ac.clicked.connect(slot)
        self._btn_form_ac.setText(buton_metni)

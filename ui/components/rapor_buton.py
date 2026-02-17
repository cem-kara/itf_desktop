# -*- coding: utf-8 -*-
"""
Rapor Dışa Aktarma Widget'ı  —  ui/components/rapor_buton.py
══════════════════════════════════════════════════════════════
Her liste/rapor sayfasına tek satırda "Excel" ve/veya "PDF" butonu ekler.

─── KULLANIM ────────────────────────────────────────────────────────────────

  from ui.components.rapor_buton import RaporButon

  # 1) Hem Excel hem PDF butonu
  self.rapor_buton = RaporButon(
      parent          = self,
      sablon          = "kalibrasyon_listesi",
      context_fn      = self._rapor_context,   # context dict döndüren callable
      tablo_fn        = self._rapor_tablo,      # list[dict] döndüren callable
      varsayilan_isim = "kalibrasyon_raporu",
  )
  btn_satiri.addWidget(self.rapor_buton)

  # 2) Sadece Excel
  RaporButon(self, "kalibrasyon_listesi", context_fn, tablo_fn, mod="excel")

  # 3) Sadece PDF
  RaporButon(self, "kalibrasyon_listesi", context_fn, tablo_fn, mod="pdf")

─── context_fn ve tablo_fn ──────────────────────────────────────────────────

  def _rapor_context(self) -> dict:
      return {
          "baslik"     : "Kalibrasyon Raporu",
          "tarih"      : datetime.date.today().strftime("%d.%m.%Y"),
          "toplam"     : self.tablo.rowCount(),
          "birim"      : self._secili_birim or "Tümü",
          "hazirlayan" : "—",
      }

  def _rapor_tablo(self) -> list[dict]:
      satirlar = []
      for satir in range(self.tablo.rowCount()):
          satirlar.append({
              "CihazAdi"    : self.tablo.item(satir, 0).text(),
              "BitisTarihi" : self.tablo.item(satir, 1).text(),
              "Durum"       : self.tablo.item(satir, 2).text(),
              "Aciklama"    : self.tablo.item(satir, 3).text(),
          })
      return satirlar

─── Gelişmiş: özel dosya adı ────────────────────────────────────────────────

  RaporButon(
      self, "kalibrasyon_listesi", ctx_fn, tbl_fn,
      isim_fn = lambda: f"kal_{datetime.date.today():%Y%m%d}",
  )

══════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import datetime
from typing import Callable

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor

from core.logger import logger
from core.rapor_servisi import RaporServisi
from ui.theme_manager import ThemeManager
from ui.styles import Colors, DarkTheme
from ui.styles.icons import IconRenderer

S = ThemeManager.get_all_component_styles()


class RaporButon(QWidget):
    """
    Sayfaya yerleştirilen Excel + PDF dışa aktarma butonu çifti.

    Parameters
    ----------
    parent          : QWidget — üst widget
    sablon          : data/templates/excel|pdf/<sablon>.xlsx|html
    context_fn      : Callable[[], dict] — anlık context üretici
    tablo_fn        : Callable[[], list[dict]] — anlık tablo verisi üretici
    mod             : "her_ikisi" | "excel" | "pdf"
    varsayilan_isim : Dosya kaydetme diyaloğundaki önerilen isim (uzantısız)
    isim_fn         : Callable[[], str] — dinamik dosya adı üretici (opsiyonel)
    """

    def __init__(
        self,
        parent: QWidget,
        sablon: str,
        context_fn: Callable[[], dict],
        tablo_fn: Callable[[], list],
        mod: str = "her_ikisi",
        varsayilan_isim: str | None = None,
        isim_fn: Callable[[], str] | None = None,
    ):
        super().__init__(parent)
        self._sablon          = sablon
        self._context_fn      = context_fn
        self._tablo_fn        = tablo_fn
        self._mod             = mod
        self._varsayilan_isim = varsayilan_isim or sablon
        self._isim_fn         = isim_fn

        self._build_ui()

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        if self._mod in ("her_ikisi", "excel"):
            self._btn_excel = self._buton(
                "Excel", "export_excel_btn",
                Colors.GREEN_700, Colors.GREEN_600, self._excel_al, "file_excel"
            )
            lay.addWidget(self._btn_excel)

        if self._mod in ("her_ikisi", "pdf"):
            self._btn_pdf = self._buton(
                "PDF", "export_pdf_btn",
                Colors.RED_700, Colors.RED_600, self._pdf_al, "file_pdf"
            )
            lay.addWidget(self._btn_pdf)

    @staticmethod
    def _buton(
        metin: str,
        obj_name: str,
        renk1: str,
        renk2: str,
        slot: Callable,
        icon_name: str,
    ) -> QPushButton:
        btn = QPushButton(metin)
        btn.setObjectName(obj_name)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(btn, icon_name, color=DarkTheme.TEXT_PRIMARY, size=14)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {renk1};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover  {{ background: {renk2}; }}
            QPushButton:pressed{{ background: {renk1}; opacity: 0.85; }}
            QPushButton:disabled {{ background: {DarkTheme.BG_TERTIARY}; color: {DarkTheme.TEXT_DISABLED}; }}
        """)
        btn.clicked.connect(slot)
        return btn

    # ── Eylemler ─────────────────────────────────────────────────────────────

    def _excel_al(self) -> None:
        self._disa_aktar("excel")

    def _pdf_al(self) -> None:
        self._disa_aktar("pdf")

    def _disa_aktar(self, tur: str) -> None:
        # 1) Kayıt yolu seç
        isim = self._isim_fn() if self._isim_fn else self._varsayilan_isim
        kayit_yolu = RaporServisi.kaydet_diyalogu(self, isim, tur=tur)
        if not kayit_yolu:
            return   # kullanıcı iptal etti

        # 2) Veri üret
        try:
            context = self._context_fn()
            tablo   = self._tablo_fn()
        except Exception as e:
            logger.error(f"Rapor verisi üretilirken hata: {e}")
            QMessageBox.warning(self, "Hata", f"Rapor verisi alınamadı:\n{e}")
            return

        # 3) Raporu üret
        if tur == "excel":
            yol = RaporServisi.excel(self._sablon, context, tablo, kayit_yolu)
        else:
            yol = RaporServisi.pdf(self._sablon, context, tablo, kayit_yolu)

        if not yol:
            QMessageBox.critical(
                self, "Hata",
                f"Rapor oluşturulamadı.\n"
                f"Şablon mevcut mu? data/templates/{tur}/{self._sablon}"
                f"{'xlsx' if tur == 'excel' else 'html'}"
            )
            return

        # 4) Başarı → aç mı?
        cevap = QMessageBox.question(
            self, "Rapor Hazır",
            f"{'Excel' if tur == 'excel' else 'PDF'} raporu kaydedildi.\n\n"
            f"{yol}\n\nDosya açılsın mı?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if cevap == QMessageBox.Yes:
            RaporServisi.ac(yol)

    # ── Durum kontrolü ───────────────────────────────────────────────────────

    def excel_aktif(self, aktif: bool) -> None:
        """Excel butonunu etkinleştir / devre dışı bırak."""
        if hasattr(self, "_btn_excel"):
            self._btn_excel.setEnabled(aktif)

    def pdf_aktif(self, aktif: bool) -> None:
        if hasattr(self, "_btn_pdf"):
            self._btn_pdf.setEnabled(aktif)

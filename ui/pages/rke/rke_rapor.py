# -*- coding: utf-8 -*-
"""
RKE Raporlama â€“ Ana Sayfa (KoordinatÃ¶r)
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Bu dosya mevcut import path'ini korur; iÅŸ mantÄ±ÄŸÄ± alt modÃ¼llere taÅŸÄ±nmÄ±ÅŸtÄ±r:

  rke/rapor/rke_pdf_builder.py   â†’ HTML ÅŸablonlarÄ±, pdf_olustur()
  rke/rapor/rke_rapor_models.py  â†’ RaporTableModel
  rke/rapor/rke_rapor_workers.py â†’ VeriYukleyiciThread, RaporOlusturucuThread
"""
from PySide6.QtCore import Qt, QSortFilterProxyModel
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QComboBox, QLineEdit,
    QGroupBox, QMessageBox, QTableView, QHeaderView,
    QAbstractItemView, QRadioButton, QButtonGroup, QSizePolicy,
)
from PySide6.QtGui import QCursor

from core.logger import logger
from ui.theme_manager import ThemeManager
from ui.styles import DarkTheme
from ui.styles.icons import IconRenderer

from ui.pages.rke.rapor.rke_rapor_models import RaporTableModel, COLUMNS
from ui.pages.rke.rapor.rke_rapor_workers import VeriYukleyiciThread, RaporOlusturucuThread, _parse_date

S = ThemeManager.get_all_component_styles()


class RKERaporPage(QWidget):
    """RKE Raporlama ve Analiz sayfasÄ±."""

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(S.get("page", "background-color: transparent;"))
        self._db            = db
        self._ham_veriler   = []
        self._filtreli_veri = []

        self._setup_ui()
        self._connect_signals()
        self.load_data()

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    #  UI KURULUMU
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(16, 12, 16, 12)
        main.setSpacing(12)

        # â”€â”€ KONTROL PANELÄ° â”€â”€
        panel = QGroupBox("Rapor AyarlarÄ± ve Filtreler")
        panel.setStyleSheet(S.get("group", ""))
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        h_panel = QHBoxLayout(panel)
        h_panel.setSpacing(20)

        # Sol: Rapor TÃ¼rÃ¼
        v_left = QVBoxLayout()
        v_left.setSpacing(8)
        lbl_tur = QLabel("RAPOR TÃœRÃœ")
        lbl_tur.setStyleSheet(S.get("section_title", ""))
        v_left.addWidget(lbl_tur)

        radio_ss = f"""
            QRadioButton {{ color:{DarkTheme.TEXT_SECONDARY}; font-size:13px; padding:4px; background:transparent; }}
            QRadioButton::indicator {{ width:16px; height:16px; border-radius:9px; border:2px solid {DarkTheme.BORDER_PRIMARY}; background:{DarkTheme.BG_SECONDARY}; }}
            QRadioButton::indicator:checked {{ background-color:{DarkTheme.INPUT_BORDER_FOCUS}; border-color:{DarkTheme.INPUT_BORDER_FOCUS}; }}
            QRadioButton:hover {{ color:{DarkTheme.TEXT_PRIMARY}; }}
        """
        self._rb_genel = QRadioButton("A.  Kontrol Raporu (Genel)")
        self._rb_genel.setChecked(True)
        self._rb_genel.setStyleSheet(radio_ss)
        self._rb_hurda = QRadioButton("B.  Hurda (HEK) Raporu")
        self._rb_hurda.setStyleSheet(radio_ss)
        self._rb_kisi  = QRadioButton("C.  Personel BazlÄ± Raporlar")
        self._rb_kisi.setStyleSheet(radio_ss)

        self._btn_group = QButtonGroup(self)
        for rb in (self._rb_genel, self._rb_hurda, self._rb_kisi):
            v_left.addWidget(rb)
            self._btn_group.addButton(rb)
        v_left.addStretch()
        h_panel.addLayout(v_left)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(S.get("separator", ""))
        h_panel.addWidget(sep)

        # SaÄŸ: Filtreler + Butonlar
        v_right = QVBoxLayout()
        v_right.setSpacing(12)

        h_filters = QHBoxLayout()
        h_filters.setSpacing(12)
        self._cmb_abd   = self._make_labeled_combo("Ana Bilim DalÄ±", "TÃ¼m BÃ¶lÃ¼mler")
        self._cmb_birim = self._make_labeled_combo("Birim",          "TÃ¼m Birimler")
        self._cmb_tarih = self._make_labeled_combo("Ä°ÅŸlem Tarihi",   "TÃ¼m Tarihler")
        for w in (self._cmb_abd, self._cmb_birim, self._cmb_tarih):
            h_filters.addWidget(w["container"])

        txt_wrap = QWidget()
        txt_wrap.setStyleSheet("background: transparent;")
        tw = QVBoxLayout(txt_wrap)
        tw.setContentsMargins(0, 0, 0, 0)
        tw.setSpacing(4)
        tw.addWidget(QLabel("Ara"))
        self._txt_ara = QLineEdit()
        self._txt_ara.setPlaceholderText("Ekipman / Cins / Birim...")
        self._txt_ara.setClearButtonEnabled(True)
        self._txt_ara.setStyleSheet(S.get("search", ""))
        tw.addWidget(self._txt_ara)
        h_filters.addWidget(txt_wrap)
        v_right.addLayout(h_filters)

        h_btn = QHBoxLayout()
        h_btn.setSpacing(10)
        self._btn_yenile = QPushButton("VERÄ°LERÄ° YENÄ°LE")
        self._btn_yenile.setStyleSheet(S.get("refresh_btn", ""))
        self._btn_yenile.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self._btn_yenile, "sync", color=DarkTheme.TEXT_PRIMARY, size=14)

        self._btn_olustur = QPushButton("PDF RAPOR OLUÅTUR")
        self._btn_olustur.setStyleSheet(S.get("pdf_btn", ""))
        self._btn_olustur.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self._btn_olustur, "save", color=DarkTheme.TEXT_PRIMARY, size=14)

        h_btn.addWidget(self._btn_yenile)
        h_btn.addWidget(self._btn_olustur)
        h_btn.addStretch()

        _sep_k = QFrame()
        _sep_k.setFrameShape(QFrame.VLine)
        _sep_k.setFixedHeight(28)
        _sep_k.setStyleSheet(S.get("separator", ""))
        h_btn.addWidget(_sep_k)

        self.btn_kapat = QPushButton("KAPAT")
        self.btn_kapat.setToolTip("Pencereyi Kapat")
        self.btn_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kapat.setStyleSheet(S.get("close_btn", ""))
        IconRenderer.set_button_icon(self.btn_kapat, "x", color=DarkTheme.TEXT_PRIMARY, size=14)
        h_btn.addWidget(self.btn_kapat)

        v_right.addLayout(h_btn)
        v_right.addStretch()
        h_panel.addLayout(v_right)
        main.addWidget(panel)

        # â”€â”€ PROGRESS â”€â”€
        self._pbar = QProgressBar()
        self._pbar.setFixedHeight(4)
        self._pbar.setTextVisible(False)
        self._pbar.setStyleSheet(S.get("progress", ""))
        self._pbar.setVisible(False)
        main.addWidget(self._pbar)

        # â”€â”€ TABLO â”€â”€
        self._model = RaporTableModel()
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self._proxy.setFilterKeyColumn(-1)

        self._table = QTableView()
        self._table.setModel(self._proxy)
        self._table.setStyleSheet(S.get("table", ""))
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSortingEnabled(True)

        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Tarih
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Pb
        main.addWidget(self._table, 1)

        # â”€â”€ FOOTER â”€â”€
        footer = QHBoxLayout()
        self._lbl_sayi = QLabel("0 kayÄ±t")
        self._lbl_sayi.setStyleSheet(
            S.get("footer_label", f"color:{DarkTheme.TEXT_MUTED}; font-size:11px;")
        )
        footer.addWidget(self._lbl_sayi)
        footer.addStretch()
        main.addLayout(footer)

    def _make_labeled_combo(self, label_text: str, default_item: str) -> dict:
        c = QWidget()
        c.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(c)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl = QLabel(label_text)
        lbl.setStyleSheet(S.get("label", ""))
        cmb = QComboBox()
        cmb.setStyleSheet(S.get("combo", ""))
        cmb.setMinimumWidth(160)
        cmb.addItem(default_item)
        lay.addWidget(lbl)
        lay.addWidget(cmb)
        return {"container": c, "combo": cmb}

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    #  SÄ°NYALLER
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def _connect_signals(self):
        self._btn_yenile.clicked.connect(self.load_data)
        self._btn_olustur.clicked.connect(self._on_rapor_olustur)
        self._txt_ara.textChanged.connect(self._proxy.setFilterFixedString)
        self._cmb_abd["combo"].currentTextChanged.connect(self._on_abd_birim_degisti)
        self._cmb_birim["combo"].currentTextChanged.connect(self._on_abd_birim_degisti)
        self._cmb_tarih["combo"].currentTextChanged.connect(self._filtrele)
        self._btn_group.buttonClicked.connect(lambda _: self._filtrele())

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    #  VERÄ° YÃœKLEME
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def load_data(self):
        if hasattr(self, "_loader") and self._loader.isRunning():
            return
        self._pbar.setVisible(True)
        self._pbar.setRange(0, 0)
        self._btn_olustur.setEnabled(False)
        self._btn_yenile.setText("YÃ¼kleniyorâ€¦")

        self._loader = VeriYukleyiciThread()
        self._loader.veri_hazir.connect(self._on_data_ready)
        self._loader.hata_olustu.connect(self._on_error)
        self._loader.finished.connect(self._on_loader_finished)
        self._loader.start()

    def _on_loader_finished(self):
        self._pbar.setVisible(False)
        self._btn_olustur.setEnabled(True)
        self._btn_yenile.setText("VERÄ°LERÄ° YENÄ°LE")

    def _on_data_ready(self, data, abd_listesi, birim_listesi, tarih_listesi):
        self._ham_veriler = data
        self._fill_combo(self._cmb_abd,   abd_listesi,   "TÃ¼m BÃ¶lÃ¼mler")
        self._fill_combo(self._cmb_birim, birim_listesi, "TÃ¼m Birimler")
        self._fill_combo(self._cmb_tarih, tarih_listesi, "TÃ¼m Tarihler")
        self._on_abd_birim_degisti()

    @staticmethod
    def _fill_combo(widget_dict: dict, items: list, default: str):
        cmb = widget_dict["combo"]
        cmb.blockSignals(True)
        curr = cmb.currentText()
        cmb.clear()
        cmb.addItem(default)
        cmb.addItems(items)
        idx = cmb.findText(curr)
        cmb.setCurrentIndex(idx if idx >= 0 else 0)
        cmb.blockSignals(False)

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    #  FÄ°LTRELEME
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def _on_abd_birim_degisti(self):
        f_abd   = self._cmb_abd["combo"].currentText()
        f_birim = self._cmb_birim["combo"].currentText()

        mevcut_tarihler = {
            row["Tarih"]
            for row in self._ham_veriler
            if row.get("Tarih")
            and ("TÃ¼m" in f_abd   or row.get("ABD",   "") == f_abd)
            and ("TÃ¼m" in f_birim or row.get("Birim", "") == f_birim)
        }
        sirali = sorted(mevcut_tarihler, key=_parse_date, reverse=True)

        cmb = self._cmb_tarih["combo"]
        cmb.blockSignals(True)
        cmb.clear()
        cmb.addItem("TÃ¼m Tarihler")
        cmb.addItems(sirali)
        cmb.blockSignals(False)

        self._filtrele()

    def _filtrele(self):
        f_abd   = self._cmb_abd["combo"].currentText()
        f_birim = self._cmb_birim["combo"].currentText()
        f_tarih = self._cmb_tarih["combo"].currentText()

        filtered = [
            row for row in self._ham_veriler
            if ("TÃ¼m" in f_abd   or row.get("ABD",   "") == f_abd)
            and ("TÃ¼m" in f_birim or row.get("Birim", "") == f_birim)
            and ("TÃ¼m" in f_tarih or row.get("Tarih", "") == f_tarih)
            and (not self._rb_hurda.isChecked() or "DeÄŸil" in row.get("Sonuc", ""))
        ]
        self._filtreli_veri = filtered
        self._model.set_data(filtered)
        self._lbl_sayi.setText(f"{len(filtered)} kayÄ±t")

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    #  RAPOR OLUÅTURMA
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def _on_rapor_olustur(self):
        if not self._filtreli_veri:
            QMessageBox.warning(self, "UyarÄ±", "Rapor oluÅŸturmak iÃ§in tabloda veri olmalÄ±dÄ±r.")
            return
        if hasattr(self, "_worker") and self._worker.isRunning():
            QMessageBox.warning(self, "UyarÄ±", "Ã–nceki rapor iÅŸlemi henÃ¼z tamamlanmadÄ±.")
            return

        mod = 1
        if self._rb_hurda.isChecked():   mod = 2
        elif self._rb_kisi.isChecked():  mod = 3

        ozet = f"{self._cmb_abd['combo'].currentText()} â€” {self._cmb_birim['combo'].currentText()}"

        self._btn_olustur.setEnabled(False)
        self._btn_olustur.setText("Ä°ÅŸleniyorâ€¦")
        self._pbar.setVisible(True)
        self._pbar.setRange(0, 0)

        self._worker = RaporOlusturucuThread(mod, self._filtreli_veri, ozet)
        self._worker.log_mesaji.connect(self._on_log)
        self._worker.islem_bitti.connect(self._on_rapor_bitti)
        self._worker.start()

    def _on_rapor_bitti(self):
        self._pbar.setVisible(False)
        self._btn_olustur.setEnabled(True)
        self._btn_olustur.setText("PDF RAPOR OLUÅTUR")
        QMessageBox.information(
            self, "TamamlandÄ±",
            "Rapor iÅŸlemi tamamlandÄ±. PDF oluÅŸturulduysa Drive'a veya yerel klasÃ¶re kaydedilmiÅŸtir."
        )

    def _on_log(self, msg: str):
        logger.info(f"[RKERapor] {msg}")
        if "HATA" in msg:
            QMessageBox.warning(self, "UyarÄ±", msg)

    def _on_error(self, msg: str):
        self._pbar.setVisible(False)
        self._btn_olustur.setEnabled(True)
        self._btn_yenile.setText("VERÄ°LERÄ° YENÄ°LE")
        logger.error(f"RKERapor hatasÄ±: {msg}")
        QMessageBox.critical(self, "Hata", msg)

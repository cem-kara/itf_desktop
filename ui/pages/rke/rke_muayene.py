# -*- coding: utf-8 -*-
"""RKE Muayene GiriÅi Ã¢â‚¬â€ rke_yonetim tasarÄ±mÄ±yla uyumlu."""
import sys
import os
import time
import datetime
from typing import List, Dict, Optional

from PySide6.QtCore import (Qt, QDate, QThread, Signal, QAbstractTableModel,
                             QModelIndex, QTimer, QUrl)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QAbstractItemView,
    QTableView, QHeaderView, QLabel, QPushButton, QComboBox,
    QDateEdit, QLineEdit, QTextEdit, QProgressBar, QScrollArea,
    QFrame, QGroupBox, QGridLayout, QFileDialog, QMessageBox,
    QDialog, QListWidget, QCheckBox, QApplication,
)
from PySide6.QtGui import QColor, QCursor, QDesktopServices, QStandardItemModel, QStandardItem, QPalette

from ui.styles.colors import DarkTheme, C as _C
from ui.styles.components import STYLES
from ui.components.base_table_model import BaseTableModel
from ui.pages.rke.components.toplu_muayene_dialog import TopluMuayeneDialog
from core.paths import DB_PATH
from core.storage.storage_service import StorageService

# --- YOL AYARLARI ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir  = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from dateutil.relativedelta import relativedelta
    from core.logger import logger
    from database.google import GoogleDriveService, veritabani_getir

    def show_info(title, message, parent):
        if "Uyar" in str(title):
            QMessageBox.warning(parent, title, message)
        else:
            QMessageBox.information(parent, title, message)

    def show_error(title, message, parent):
        QMessageBox.critical(parent, title, message)

except ImportError:
    import logging
    logger = logging.getLogger("RKEMuayene")
    def veritabani_getir(vt, sayfa): return None
    def show_info(t, m, p): print(m)
    def show_error(t, m, p): print(m)
    class GoogleDriveService:
        def upload_file(self, a, b): return None
    class relativedelta:
        def __init__(self, **kw): self.years = kw.get("years", 0)
        def __radd__(self, dt): return dt.replace(year=dt.year + self.years)
    class YetkiYoneticisi:
        @staticmethod
        def uygula(w, key): pass
    class DarkTheme:
        BG_PRIMARY = "#0f1117"; BG_SECONDARY = "#13161d"; SURFACE = "#13161d"
        PANEL = "#191d26"; BORDER_PRIMARY = "#242938"
        TEXT_PRIMARY = "#eef0f5"; TEXT_SECONDARY = "#8b90a0"; TEXT_MUTED = "#5a6278"
        ACCENT = "#4f8ef7"; DANGER = "#f75f5f"; WARNING = "#f5a623"; SUCCESS = "#3ecf8e"
    class _S(dict):
        def __missing__(self, k): return ""
    S = _S({
        "page":         f"background:{DarkTheme.BG_PRIMARY};color:{DarkTheme.TEXT_PRIMARY};",
        "group":        f"QGroupBox{{background:{DarkTheme.PANEL};border:1px solid {DarkTheme.BORDER_PRIMARY};border-radius:6px;color:{DarkTheme.ACCENT};font-weight:600;padding-top:4px;margin-top:12px;}}QGroupBox::title{{subcontrol-origin:margin;left:10px;padding:0 4px;}}",
        "table":        f"QTableView{{background:{DarkTheme.PANEL};alternate-background-color:{DarkTheme.BG_SECONDARY};border:none;gridline-color:{DarkTheme.BORDER_PRIMARY};}}QHeaderView::section{{background:{DarkTheme.BG_SECONDARY};color:{DarkTheme.TEXT_SECONDARY};padding:6px;border:none;font-weight:600;}}",
        "input":        f"QLineEdit,QDateEdit{{background:{DarkTheme.BG_SECONDARY};border:1px solid {DarkTheme.BORDER_PRIMARY};border-radius:4px;padding:0 8px;color:{DarkTheme.TEXT_PRIMARY};}}",
        "combo":        f"QComboBox{{background:{DarkTheme.BG_SECONDARY};border:1px solid {DarkTheme.BORDER_PRIMARY};border-radius:4px;padding:0 8px;color:{DarkTheme.TEXT_PRIMARY};}}",
        "label":        f"color:{DarkTheme.TEXT_SECONDARY};font-size:11px;font-weight:600;",
        "footer_label": f"color:{DarkTheme.TEXT_MUTED};font-size:11px;",
        "refresh_btn":  f"QPushButton{{background:{DarkTheme.PANEL};border:1px solid {DarkTheme.BORDER_PRIMARY};border-radius:4px;color:{DarkTheme.TEXT_SECONDARY};padding:0 12px;}}QPushButton:hover{{color:{DarkTheme.TEXT_PRIMARY};}}",
        "success_btn":  f"QPushButton{{background:{DarkTheme.SUCCESS};border:none;border-radius:4px;color:#0f1117;font-weight:700;}}",
        "cancel_btn":   f"QPushButton{{background:transparent;border:1px solid {DarkTheme.BORDER_PRIMARY};border-radius:4px;color:{DarkTheme.TEXT_SECONDARY};}}",
        "info_label":   f"color:{DarkTheme.TEXT_MUTED};font-size:11px;",
    })

# 
_S_PAGE = STYLES["page"]
_S_INPUT = STYLES["input"]
_S_DATE = STYLES["input_date"]
_S_COMBO = STYLES["input_combo"]
_S_TEXTEDIT = STYLES["input_text"]
_S_TABLE = STYLES["table"]
_S_SCROLL = STYLES["scrollbar"]
_S_PBAR = STYLES["progress"]


# RKE envanter tablo kolonlarÄ±
_RKE_COLS = [
    ("EkipmanNo",        "EKIPMAN NO",  120),
    ("KoruyucuNumarasi", "KORUYUCU NO", 140),
    ("AnaBilimDali",     "ABD",         110),
    ("Birim",            "BIRIM",       110),
    ("KoruyucuCinsi",    "CINS",        110),
    ("KursunEsdegeri",   "Pb",           70),
    ("HizmetYili",       "YIL",          60),
    ("Bedeni",           "BEDEN",        70),
    ("KontrolTarihi",    "KONTROL T.",  100),
    ("Durum",            "DURUM",       120),
]
_RKE_KEYS = [c[0] for c in _RKE_COLS]
_RKE_HEADERS = [c[1] for c in _RKE_COLS]
_RKE_WIDTHS = [c[2] for c in _RKE_COLS]


# ==================================================================
#  FieldGroup Ã¢â‚¬â€ mockup'Ä±n fgroup bileÅeni
# ==================================================================
class FieldGroup(QWidget):
    """Renkli sol Åerit + monospace baÅlÄ±k + iÃ§erik kartÄ±."""
    def __init__(self, title: str, color: str, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(
            f"FieldGroup{{background:{DarkTheme.BG_SECONDARY};border:1px solid {DarkTheme.BORDER_PRIMARY};border-radius:6px;}}"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Ã¢â€â‚¬Ã¢â€â‚¬ header Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
        hdr = QWidget()
        hdr.setFixedHeight(30)
        hdr.setAttribute(Qt.WA_StyledBackground, True)
        hdr.setStyleSheet(
            f"QWidget{{background:rgba(255,255,255,12);border-bottom:1px solid {DarkTheme.BORDER_PRIMARY};"
            f"border-top-left-radius:6px;border-top-right-radius:6px;}}"
        )
        hh = QHBoxLayout(hdr)
        hh.setContentsMargins(10, 0, 10, 0)
        hh.setSpacing(8)

        bar = QFrame()
        bar.setFixedSize(3, 14)
        bar.setStyleSheet("border: none;")

        lbl = QLabel(title.upper())
        lbl.setStyleSheet(
            f"color:{color};background:transparent;font-size:9px;font-weight:700;"
            f"letter-spacing:2px;font-family:{DarkTheme.MONOSPACE};"
        )
        hh.addWidget(bar)
        hh.addWidget(lbl)
        hh.addStretch()
        root.addWidget(hdr)

        # Ã¢â€â‚¬Ã¢â€â‚¬ body Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
        self._body = QWidget()
        self._body.setStyleSheet("background:transparent;")
        self._bl = QVBoxLayout(self._body)
        self._bl.setContentsMargins(10, 10, 10, 12)
        self._bl.setSpacing(8)
        root.addWidget(self._body)

    def add_widget(self, w): self._bl.addWidget(w)
    def add_layout(self, l): self._bl.addLayout(l)
    def body_layout(self) -> QVBoxLayout: return self._bl


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
#  YARDIMCI FONKSÄ°YONLAR
# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

def envanter_durumunu_belirle(fiziksel: str, skopi: str) -> str:
    fiz_ok = (fiziksel == "KullanÄ±ma Uygun")
    sko_ok = (skopi in ("KullanÄ±ma Uygun", "YapÄ±lmadÄ±"))
    return "KullanÄ±ma Uygun" if fiz_ok and sko_ok else "KullanÄ±ma Uygun DeÄŸil"


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
#  CHECKABLE COMBOBOX (deÄŸiÅmedi)
# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

class CheckableComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view().pressed.connect(self.handleItemPressed)
        self.setModel(QStandardItemModel(self))
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)

    def handleItemPressed(self, index):
        item = self.model().itemFromIndex(index)
        item.setCheckState(Qt.CheckState.Unchecked if item.checkState() == Qt.CheckState.Checked else Qt.CheckState.Checked)
        QTimer.singleShot(10, self.updateText)

    def updateText(self):
        items = [self.model().item(i).text()
                 for i in range(self.count())
                 if self.model().item(i).checkState() == Qt.CheckState.Checked]
        self.lineEdit().setText(", ".join(items))

    def setCheckedItems(self, text_list):
        if isinstance(text_list, str):
            text_list = [x.strip() for x in text_list.split(',')] if text_list else []
        elif not text_list:
            text_list = []
        for i in range(self.count()):
            item = self.model().item(i)
            item.setCheckState(Qt.CheckState.Checked if item.text() in text_list else Qt.CheckState.Unchecked)
        self.updateText()

    def getCheckedItems(self): return self.lineEdit().text()

    def addItem(self, text, data=None):
        item = QStandardItem(text)
        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        item.setData(Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
        self.model().appendRow(item)

    def addItems(self, texts):
        for t in texts: self.addItem(t)


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
#  WORKER THREADS (deÄŸiÅmedi)
# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

class VeriYukleyici(QThread):
    veri_hazir  = Signal(list, list, dict, list, list, list, list, list)
    hata_olustu = Signal(str)

    def __init__(self, db_path=None, use_sheets=True):
        super().__init__()
        self._db_path = db_path or DB_PATH
        self._use_sheets = use_sheets

    @staticmethod
    def _repo_muayene_to_table(rows: List[Dict]):
        if not rows:
            return [], []
        headers = [
            "KayitNo", "EkipmanNo", "F_MuayeneTarihi", "FizikselDurum",
            "S_MuayeneTarihi", "SkopiDurum", "Aciklamalar",
            "KontrolEden/Unvani", "BirimSorumlusu/Unvani", "Not", "Rapor"
        ]
        data = []
        for r in rows:
            data.append([
                r.get("KayitNo", ""),
                r.get("EkipmanNo", ""),
                r.get("FMuayeneTarihi", ""),
                r.get("FizikselDurum", ""),
                r.get("SMuayeneTarihi", ""),
                r.get("SkopiDurum", ""),
                r.get("Aciklamalar", ""),
                r.get("KontrolEdenUnvani", ""),
                r.get("BirimSorumlusuUnvani", ""),
                r.get("Notlar", ""),
                r.get("Rapor", ""),
            ])
        return headers, data

    @staticmethod
    def _find_header_index(headers: List[str], *candidates: str) -> int:
        for name in candidates:
            if name in headers:
                return headers.index(name)
        return -1

    def run(self):
        try:
            rke_data, rke_combo, rke_dict = [], [], {}
            muayene_listesi, headers = [], []
            teknik_aciklamalar = []
            kontrol_edenler, birim_sorumlulari = set(), set()

            db = None
            rke_repo = None
            muayene_repo = None
            if not self._use_sheets:
                from database.sqlite_manager import SQLiteManager
                from core.di import get_registry
                db = SQLiteManager(db_path=self._db_path, check_same_thread=True)
                registry = get_registry(db)
                rke_repo = registry.get("RKE_List")
                muayene_repo = registry.get("RKE_Muayene")

            ws_rke = None
            ws_muayene = None
            ws_sabit = None
            if self._use_sheets:
                try:
                    ws_rke = veritabani_getir('rke', 'rke_list')
                except Exception:
                    ws_rke = None
                try:
                    ws_muayene = veritabani_getir('rke', 'rke_muayene')
                except Exception:
                    ws_muayene = None
                try:
                    ws_sabit = veritabani_getir('sabit', 'Sabitler')
                except Exception:
                    ws_sabit = None

            if ws_rke:
                rke_data = ws_rke.get_all_records()
            elif rke_repo:
                rke_data = rke_repo.get_all()

            for row in rke_data:
                ekipman_no = str(row.get('EkipmanNo', '')).strip()
                cins       = str(row.get('KoruyucuCinsi', '')).strip()
                if ekipman_no:
                    display = f"{ekipman_no} | {cins}"
                    rke_combo.append(display)
                    rke_dict[display] = ekipman_no

            if ws_muayene:
                raw = ws_muayene.get_all_values()
                if raw:
                    headers = [str(h).strip() for h in raw[0]]
                    muayene_listesi = raw[1:]
            elif muayene_repo:
                headers, muayene_listesi = self._repo_muayene_to_table(muayene_repo.get_all())

            if headers and muayene_listesi:
                idx_k = self._find_header_index(headers, "KontrolEden/Unvani", "KontrolEden")
                idx_s = self._find_header_index(headers, "BirimSorumlusu/Unvani", "BirimSorumlusu")
                for row in muayene_listesi:
                    if idx_k != -1 and len(row) > idx_k:
                        val = str(row[idx_k]).strip()
                        if val: kontrol_edenler.add(val)
                    if idx_s != -1 and len(row) > idx_s:
                        val = str(row[idx_s]).strip()
                        if val: birim_sorumlulari.add(val)

            if ws_sabit:
                for s in ws_sabit.get_all_records():
                    if str(s.get('Kod', '')).strip() == "RKE_Teknik":
                        eleman = str(s.get('MenuEleman', '')).strip()
                        if eleman: teknik_aciklamalar.append(eleman)
            elif db:
                try:
                    rows = db.execute("SELECT Kod, MenuEleman FROM Sabitler").fetchall()
                    for s in rows:
                        if str(s["Kod"]).strip() == "RKE_Teknik":
                            eleman = str(s["MenuEleman"]).strip()
                            if eleman: teknik_aciklamalar.append(eleman)
                except Exception:
                    pass

            if not teknik_aciklamalar:
                teknik_aciklamalar = ["YÄ±rtÄ±k Yok", "KurÅun BÃ¼tÃ¼nlÃ¼ÄŸÃ¼ Tam", "AskÄ±lar SaÄŸlam", "Temiz"]

            self.veri_hazir.emit(
                rke_data, sorted(rke_combo), rke_dict,
                muayene_listesi, headers, sorted(teknik_aciklamalar),
                sorted(kontrol_edenler), sorted(birim_sorumlulari)
            )
            if db:
                db.close()
        except Exception as e:
            self.hata_olustu.emit(str(e))


class KayitWorker(QThread):
    finished = Signal(str)
    error    = Signal(str)

    def __init__(self, veri_dict, dosya_yolu, db_path=None, use_sheets=True):
        super().__init__()
        self.veri       = veri_dict
        self.dosya_yolu = dosya_yolu
        self._db_path = db_path or DB_PATH
        self._use_sheets = use_sheets

    def run(self):
        try:
            drive_link = "-"
            upload_result = {"mode": "none", "drive_link": "", "local_path": "", "error": ""}

            # Local DB (Dokumanlar iÃ§in) her zaman aÃ§Ä±lÄ±r
            from database.sqlite_manager import SQLiteManager
            from core.di import get_registry
            db = SQLiteManager(db_path=self._db_path, check_same_thread=True)
            registry = get_registry(db)

            if self.dosya_yolu and os.path.exists(self.dosya_yolu):
                storage = StorageService(db)
                upload_result = storage.upload(
                    file_path=self.dosya_yolu,
                    folder_name="RKE_Rapor",
                    custom_name=os.path.basename(self.dosya_yolu)
                )
                drive_link = upload_result.get("drive_link") or upload_result.get("local_path") or "-"

                # Dokumanlar tablosuna kaydet
                if upload_result.get("mode") != "none":
                    try:
                        repo_doc = registry.get("Dokumanlar")
                        repo_doc.insert({
                            "EntityType": "rke",
                            "EntityId": str(self.veri.get("EkipmanNo", "")),
                            "BelgeTuru": "Rapor",
                            "Belge": os.path.basename(self.dosya_yolu),
                            "DocType": "RKE_Rapor",
                            "DisplayName": os.path.basename(self.dosya_yolu),
                            "LocalPath": upload_result.get("local_path") or "",
                            "DrivePath": upload_result.get("drive_link") or "",
                            "BelgeAciklama": "",
                            "YuklenmeTarihi": datetime.datetime.now().isoformat(),
                            "IliskiliBelgeID": self.veri.get("KayitNo"),
                            "IliskiliBelgeTipi": "RKE_Muayene",
                        })
                    except Exception as e:
                        logger.warning(f"Dokumanlar kaydÄ± eklenemedi: {e}")

            rke_repo = None
            muayene_repo = None
            if not self._use_sheets:
                rke_repo = registry.get("RKE_List")
                muayene_repo = registry.get("RKE_Muayene")

            if self._use_sheets:
                ws_muayene = veritabani_getir('rke', 'rke_muayene')
                if not ws_muayene: raise Exception("VeritabanÄ± baÄŸlantÄ±sÄ± yok.")

                satir = [
                    self.veri['KayitNo'], self.veri['EkipmanNo'],
                    self.veri['F_MuayeneTarihi'], self.veri['FizikselDurum'],
                    self.veri['S_MuayeneTarihi'], self.veri['SkopiDurum'],
                    self.veri['Aciklamalar'], self.veri['KontrolEden'],
                    self.veri['BirimSorumlusu'], self.veri['Not'], drive_link
                ]
                ws_muayene.append_row(satir)

                ws_list = veritabani_getir('rke', 'rke_list')
                if ws_list:
                    cell = ws_list.find(self.veri['EkipmanNo'])
                    if cell:
                        yeni_durum = envanter_durumunu_belirle(
                            self.veri['FizikselDurum'], self.veri['SkopiDurum'])
                        gelecek = ""
                        skopi_str = self.veri['S_MuayeneTarihi']
                        if skopi_str:
                            try:
                                dt_obj = datetime.datetime.strptime(skopi_str, "%Y-%m-%d")
                                gelecek = (dt_obj + relativedelta(years=1)).strftime("%Y-%m-%d")
                            except: gelecek = skopi_str

                        hdrs = ws_list.row_values(1)
                        def ci(name):
                            try: return hdrs.index(name) + 1
                            except: return -1
                        if (c := ci("KontrolTarihi")) > 0 and gelecek:
                            ws_list.update_cell(cell.row, c, gelecek)
                        if (c := ci("Durum")) > 0:
                            ws_list.update_cell(cell.row, c, yeni_durum)
                        if (c := ci("AÃ§iklama")) > 0:
                            ws_list.update_cell(cell.row, c, self.veri['Aciklamalar'])
            else:
                if not muayene_repo:
                    raise Exception("VeritabanÄ± baÄŸlantÄ±sÄ± yok.")
                muayene_data = {
                    "KayitNo": self.veri.get("KayitNo"),
                    "EkipmanNo": self.veri.get("EkipmanNo"),
                    "FMuayeneTarihi": self.veri.get("F_MuayeneTarihi"),
                    "FizikselDurum": self.veri.get("FizikselDurum"),
                    "SMuayeneTarihi": self.veri.get("S_MuayeneTarihi"),
                    "SkopiDurum": self.veri.get("SkopiDurum"),
                    "Aciklamalar": self.veri.get("Aciklamalar"),
                    "KontrolEdenUnvani": self.veri.get("KontrolEden"),
                    "BirimSorumlusuUnvani": self.veri.get("BirimSorumlusu"),
                    "Notlar": self.veri.get("Not"),
                    "Rapor": drive_link,
                }
                muayene_repo.insert(muayene_data)

                if rke_repo:
                    yeni_durum = envanter_durumunu_belirle(
                        self.veri['FizikselDurum'], self.veri['SkopiDurum'])
                    gelecek = ""
                    skopi_str = self.veri['S_MuayeneTarihi']
                    if skopi_str:
                        try:
                            dt_obj = datetime.datetime.strptime(skopi_str, "%Y-%m-%d")
                            gelecek = (dt_obj + relativedelta(years=1)).strftime("%Y-%m-%d")
                        except: gelecek = skopi_str
                    update_data = {"Durum": yeni_durum, "Aciklama": self.veri.get("Aciklamalar", "")}
                    if gelecek:
                        update_data["KontrolTarihi"] = gelecek
                    rke_repo.update(self.veri["EkipmanNo"], update_data)

            self.finished.emit("KayÄ±t ve gÃ¼ncelleme baÅŸarÄ±lÄ±.")
            if db:
                db.close()
        except Exception as e:
            self.error.emit(str(e))

class TopluKayitWorker(QThread):
    progress = Signal(int, int)
    finished = Signal()
    error    = Signal(str)

    def __init__(self, ekipman_listesi, ortak_veri, dosya_yolu, fiziksel_aktif, skopi_aktif, db_path=None, use_sheets=True):
        super().__init__()
        self.ekipman_listesi = ekipman_listesi
        self.ortak_veri      = ortak_veri
        self.dosya_yolu      = dosya_yolu
        self.fiziksel_aktif  = fiziksel_aktif
        self.skopi_aktif     = skopi_aktif
        self._db_path = db_path or DB_PATH
        self._use_sheets = use_sheets

    def run(self):
        try:
            drive_link = "-"
            upload_result = {"mode": "none", "drive_link": "", "local_path": "", "error": ""}

            from database.sqlite_manager import SQLiteManager
            from core.di import get_registry
            db = SQLiteManager(db_path=self._db_path, check_same_thread=True)
            registry = get_registry(db)

            if self.dosya_yolu and os.path.exists(self.dosya_yolu):
                storage = StorageService(db)
                upload_result = storage.upload(
                    file_path=self.dosya_yolu,
                    folder_name="RKE_Rapor",
                    custom_name=os.path.basename(self.dosya_yolu)
                )
                drive_link = upload_result.get("drive_link") or upload_result.get("local_path") or "-"

            rke_repo = None
            muayene_repo = None
            if not self._use_sheets:
                rke_repo = registry.get("RKE_List")
                muayene_repo = registry.get("RKE_Muayene")

            if self._use_sheets:
                ws_muayene = veritabani_getir('rke', 'rke_muayene')
                ws_list    = veritabani_getir('rke', 'rke_list')
                if not ws_muayene or not ws_list:
                    raise Exception("VeritabanÄ± baÄŸlantÄ±sÄ± yok.")

                hdrs = ws_list.row_values(1)
                def ci(name):
                    try: return hdrs.index(name) + 1
                    except: return -1
                col_tarih   = ci("KontrolTarihi")
                col_durum   = ci("Durum")
                col_aciklama = ci("AÃ§iklama")
                try: col_ekipman = hdrs.index("EkipmanNo") + 1
                except: col_ekipman = 2
                all_ekipman = ws_list.col_values(col_ekipman)

                rows_to_add, batch_updates = [], []
                base_time = int(time.time())

                for idx, ekipman_no in enumerate(self.ekipman_listesi):
                    unique_id = f"M-{base_time}-{idx}"
                    f_tarih = self.ortak_veri['F_MuayeneTarihi'] if self.fiziksel_aktif else ""
                    f_durum = self.ortak_veri['FizikselDurum']   if self.fiziksel_aktif else ""
                    s_tarih = self.ortak_veri['S_MuayeneTarihi'] if self.skopi_aktif    else ""
                    s_durum = self.ortak_veri['SkopiDurum']      if self.skopi_aktif    else ""

                    rows_to_add.append([
                        unique_id, ekipman_no, f_tarih, f_durum, s_tarih, s_durum,
                        self.ortak_veri['Aciklamalar'], self.ortak_veri['KontrolEden'],
                        self.ortak_veri['BirimSorumlusu'], self.ortak_veri['Not'], drive_link
                    ])

                    try:
                        row_num = all_ekipman.index(ekipman_no) + 1
                        yeni_genel = envanter_durumunu_belirle(f_durum, s_durum)
                        gelecek = ""
                        if s_tarih:
                            try:
                                dt_obj = datetime.datetime.strptime(s_tarih, "%Y-%m-%d")
                                gelecek = (dt_obj + relativedelta(years=1)).strftime("%Y-%m-%d")
                            except: gelecek = s_tarih
                        if col_tarih > 0 and gelecek:
                            batch_updates.append({'range': f"{chr(64+col_tarih)}{row_num}", 'values': [[gelecek]]})
                        if col_durum > 0:
                            batch_updates.append({'range': f"{chr(64+col_durum)}{row_num}", 'values': [[yeni_genel]]})
                        if col_aciklama > 0:
                            batch_updates.append({'range': f"{chr(64+col_aciklama)}{row_num}", 'values': [[self.ortak_veri['Aciklamalar']]]})
                    except ValueError: pass

                    self.progress.emit(idx + 1, len(self.ekipman_listesi))

                ws_muayene.append_rows(rows_to_add)
                if batch_updates: ws_list.batch_update(batch_updates)
                self.finished.emit()
            else:
                if not muayene_repo:
                    raise Exception("VeritabanÄ± baÄŸlantÄ±sÄ± yok.")
                base_time = int(time.time())
                for idx, ekipman_no in enumerate(self.ekipman_listesi):
                    unique_id = f"M-{base_time}-{idx}"
                    f_tarih = self.ortak_veri['F_MuayeneTarihi'] if self.fiziksel_aktif else ""
                    f_durum = self.ortak_veri['FizikselDurum']   if self.fiziksel_aktif else ""
                    s_tarih = self.ortak_veri['S_MuayeneTarihi'] if self.skopi_aktif    else ""
                    s_durum = self.ortak_veri['SkopiDurum']      if self.skopi_aktif    else ""

                    muayene_data = {
                        "KayitNo": unique_id,
                        "EkipmanNo": ekipman_no,
                        "FMuayeneTarihi": f_tarih,
                        "FizikselDurum": f_durum,
                        "SMuayeneTarihi": s_tarih,
                        "SkopiDurum": s_durum,
                        "Aciklamalar": self.ortak_veri['Aciklamalar'],
                        "KontrolEdenUnvani": self.ortak_veri['KontrolEden'],
                        "BirimSorumlusuUnvani": self.ortak_veri['BirimSorumlusu'],
                        "Notlar": self.ortak_veri['Not'],
                        "Rapor": drive_link,
                    }
                    muayene_repo.insert(muayene_data)

                    if rke_repo:
                        yeni_genel = envanter_durumunu_belirle(f_durum, s_durum)
                        gelecek = ""
                        if s_tarih:
                            try:
                                dt_obj = datetime.datetime.strptime(s_tarih, "%Y-%m-%d")
                                gelecek = (dt_obj + relativedelta(years=1)).strftime("%Y-%m-%d")
                            except: gelecek = s_tarih
                        update_data = {"Durum": yeni_genel, "Aciklama": self.ortak_veri.get("Aciklamalar", "")}
                        if gelecek:
                            update_data["KontrolTarihi"] = gelecek
                        rke_repo.update(ekipman_no, update_data)

                    if upload_result.get("mode") != "none":
                        try:
                            repo_doc = registry.get("Dokumanlar")
                            repo_doc.insert({
                                "EntityType": "rke",
                                "EntityId": str(ekipman_no),
                                "BelgeTuru": "Rapor",
                                "Belge": os.path.basename(self.dosya_yolu),
                                "DocType": "RKE_Rapor",
                                "DisplayName": os.path.basename(self.dosya_yolu),
                                "LocalPath": upload_result.get("local_path") or "",
                                "DrivePath": upload_result.get("drive_link") or "",
                                "BelgeAciklama": "",
                                "YuklenmeTarihi": datetime.datetime.now().isoformat(),
                                "IliskiliBelgeID": unique_id,
                                "IliskiliBelgeTipi": "RKE_Muayene",
                            })
                        except Exception as e:
                            logger.warning(f"Dokumanlar kaydÄ± eklenemedi: {e}")

                self.finished.emit()
            if db:
                db.close()
        except Exception as e:
            self.error.emit(str(e))

class RKEEnvanterModel(BaseTableModel):
    def __init__(self, rows=None, parent=None):
        super().__init__(_RKE_COLS, rows, parent)

    def _display(self, key, row):
        return str(row.get(key, ""))

    def _fg(self, key, row):
        if key == "Durum":
            v = row.get(key, "")
            if "DeÄŸil" in v or "Hurda" in v:
                return QColor(_C["red"])
            if "Uygun" in v:
                return QColor(_C["green"])
        return None

    def _align(self, key):
        if key in ("KontrolTarihi", "Durum"):
            return Qt.AlignmentFlag.AlignCenter
        return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft

    def set_rows(self, rows):
        self.set_data(rows)

    def get_row(self, idx):
        return self._data[idx] if 0 <= idx < len(self._data) else None


_GECMIS_COLS = [
    ("F_MuayeneTarihi", "Fiz. Tarih"),
    ("S_MuayeneTarihi", "Skopi Tarih"),
    ("Aciklamalar",     "AÃ§Ä±klama"),
    ("Rapor",           "Rapor"),
]

class GecmisModel(BaseTableModel):
    def __init__(self, parent=None):
        super().__init__(_GECMIS_COLS, [], parent)

    def _display(self, key, row):
        val = str(row.get(key, ""))
        if key == "Rapor":
            return "Link" if "http" in val else "Ã¢â‚¬â€"
        return val

    def _fg(self, key, row):
        if key == "Rapor" and "http" in str(row.get(key, "")):
            return QColor(_C["accent"])
        return None

    def set_rows(self, rows):
        self.set_data(rows)

    def get_row(self, idx):
        return self._data[idx] if 0 <= idx < len(self._data) else None


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
#  TOPLU MUAYENE DÄ°ALOG
# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

class RKEMuayenePage(QWidget):
    def __init__(self, db=None, action_guard=None, parent=None, yetki="viewer", kullanici_adi=None):
        super().__init__(parent)
        self._db = db
        self._action_guard = action_guard
        self._db_path = DB_PATH
        self._use_sheets = False if self._db else True
        self.yetki         = yetki
        self.kullanici_adi = kullanici_adi
        self.setWindowTitle("RKE Muayene GiriÅi")
        self.resize(1200, 820)
        self.setStyleSheet(_S_PAGE)

        self.rke_data: List[Dict]   = []
        self.rke_dict: Dict         = {}
        self.tum_muayeneler         = []
        self.teknik_aciklamalar     = []
        self.kontrol_listesi        = []
        self.sorumlu_listesi        = []
        self.secilen_dosya          = None
        self.header_map: Dict       = {}
        self._kpi_labels: Dict[str, QLabel] = {}
        self.btn_kapat = None  # KapÄ±yÄ± kapat dÃ¼ÄŸmesi iÃ§in yer tutucu


        self._setup_ui()
        # YetkiYoneticisi.uygula(self, "rke_muayene")  # TODO: Yetki sistemi entegrasyonu

    # Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    #  UI KURULUM
    # Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_kpi_bar())
        root.addWidget(self._build_body(), 1)

    def _build_kpi_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(68)
        bar.setProperty("bg-role", "page")
        bar.style().unpolish(bar)
        bar.style().polish(bar)
        hl = QHBoxLayout(bar)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(1)
        
        specs = [
            ("toplam",  "TOPLAM EKÄ°PMAN",  "0", DarkTheme.ACCENT),
            ("uygun",   "KULLANIMA UYGUN", "0", DarkTheme.STATUS_SUCCESS),
            ("uygun_d", "UYGUN DEÄÄ°L",     "0", DarkTheme.STATUS_ERROR),
            ("bekleyen","KONTROL BEKLEYEN","0", DarkTheme.STATUS_WARNING),
        ]
        for key, title, val, color in specs:
            hl.addWidget(self._mk_kpi_card(key, title, val, color), 1)
        return bar
    
    def _mk_kpi_card(self, key, title, val, color) -> QWidget:
        w = QWidget()
        w.setProperty("bg-role", "page")
        w.style().unpolish(w)
        w.style().polish(w)
        hl = QHBoxLayout(w)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)

        accent = QFrame()
        accent.setFixedWidth(3)
        accent.setStyleSheet("border: none;")
        hl.addWidget(accent)

        content = QWidget()
        content.setProperty("bg-role", "page")
        content.style().unpolish(content)
        content.style().polish(content)
        vl = QVBoxLayout(content)
        vl.setContentsMargins(14, 8, 14, 8)
        vl.setSpacing(2)

        lt = QLabel(title)
        lt.setStyleSheet(
            f"color:{DarkTheme.TEXT_MUTED};background:transparent;font-family:{DarkTheme.MONOSPACE};"
            f"font-size:8px;font-weight:700;letter-spacing:2px;"
        )
        lv = QLabel(val)
        lv.setStyleSheet(
            f"color:{color};background:transparent;font-family:{DarkTheme.MONOSPACE};"
            f"font-size:20px;font-weight:700;"
        )
        vl.addWidget(lt)
        vl.addWidget(lv)
        hl.addWidget(content, 1)
        self._kpi_labels[key] = lv
        return w

    def _build_body(self) -> QWidget:
        body = QWidget()
        body.setProperty("bg-role", "page")
        body.style().unpolish(body)
        body.style().polish(body)
        hl = QHBoxLayout(body)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)

        self._form_panel = self._build_form_panel()
        self._form_panel.setFixedWidth(390)
        hl.addWidget(self._form_panel)

        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setProperty("bg-role", "separator")
        sep.style().unpolish(sep)
        sep.style().polish(sep)
        hl.addWidget(sep)

        hl.addWidget(self._build_list_panel(), 1)
        return body

    def _build_form_panel(self) -> QWidget:
        panel = QWidget()
        panel.setProperty("bg-role", "page")
        panel.style().unpolish(panel)
        panel.style().polish(panel)
        vl = QVBoxLayout(panel)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        # Panel baÅlÄ±k
        hdr = QWidget()
        hdr.setFixedHeight(36)
        hdr.setProperty("bg-role", "page")
        hdr.style().unpolish(hdr)
        hdr.style().polish(hdr)
        hh = QHBoxLayout(hdr)
        hh.setContentsMargins(14, 0, 14, 0)
        t1 = QLabel("MUAYENE FORMU")
        t1.setProperty("color-role", "muted")
        t1.setStyleSheet("font-family: {DarkTheme.MONOSPACE}; font-size: 9px; font-weight: 700; letter-spacing: 2px;")
        t1.style().unpolish(t1)
        t1.style().polish(t1)
        hh.addWidget(t1)
        hh.addStretch()
        vl.addWidget(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(_S_SCROLL)

        inner = QWidget()
        inner.setStyleSheet("background:transparent;")
        il = QVBoxLayout(inner)
        il.setContentsMargins(12, 12, 12, 16)
        il.setSpacing(10)

        # 1. Ekipman SeÃ§imi
        grp_ekipman = FieldGroup("Ekipman SeÃ§imi", DarkTheme.STATUS_WARNING)
        g = QGridLayout()
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(6)
        g.addWidget(self._lbl("EKÄ°PMAN NO"), 0, 0, 1, 2)
        self.cmb_rke = QComboBox()
        self.cmb_rke.setEditable(True)
        self.cmb_rke.setStyleSheet(_S_COMBO)
        self.cmb_rke.setFixedHeight(28)
        self.cmb_rke.setPlaceholderText("Ara veya seÃ§in...")
        self.cmb_rke.currentIndexChanged.connect(self.ekipman_secildi)
        g.addWidget(self.cmb_rke, 1, 0, 1, 2)
        grp_ekipman.add_layout(g)
        il.addWidget(grp_ekipman)

        # 2. Fiziksel Muayene
        grp_fiz = FieldGroup("Fiziksel Muayene", DarkTheme.STATUS_SUCCESS)
        gf = QGridLayout()
        gf.setContentsMargins(0, 0, 0, 0)
        gf.setHorizontalSpacing(10)
        gf.setVerticalSpacing(6)
        gf.addWidget(self._lbl("MUAYENE TARÄ°HÄ°"), 0, 0)
        gf.addWidget(self._lbl("DURUM"), 0, 1)
        self.dt_fiziksel = QDateEdit(QDate.currentDate())
        self.dt_fiziksel.setCalendarPopup(True)
        self.dt_fiziksel.setStyleSheet(_S_DATE)
        self.dt_fiziksel.setFixedHeight(28)
        self.cmb_fiziksel = QComboBox()
        self.cmb_fiziksel.setStyleSheet(_S_COMBO)
        self.cmb_fiziksel.setFixedHeight(28)
        self.cmb_fiziksel.addItems(["KullanÄ±ma Uygun", "KullanÄ±ma Uygun DeÄŸil"])
        gf.addWidget(self.dt_fiziksel, 1, 0)
        gf.addWidget(self.cmb_fiziksel, 1, 1)
        grp_fiz.add_layout(gf)
        il.addWidget(grp_fiz)

        # 3. Skopi Muayene
        grp_sko = FieldGroup("Skopi Muayene", DarkTheme.ACCENT2)
        gs = QGridLayout()
        gs.setContentsMargins(0, 0, 0, 0)
        gs.setHorizontalSpacing(10)
        gs.setVerticalSpacing(6)
        gs.addWidget(self._lbl("MUAYENE TARÄ°HÄ°"), 0, 0)
        gs.addWidget(self._lbl("DURUM"), 0, 1)
        self.dt_skopi = QDateEdit(QDate.currentDate())
        self.dt_skopi.setCalendarPopup(True)
        self.dt_skopi.setStyleSheet(_S_DATE)
        self.dt_skopi.setFixedHeight(28)
        self.cmb_skopi = QComboBox()
        self.cmb_skopi.setStyleSheet(_S_COMBO)
        self.cmb_skopi.setFixedHeight(28)
        self.cmb_skopi.addItems(["KullanÄ±ma Uygun", "KullanÄ±ma Uygun DeÄŸil", "YapÄ±lmadÄ±"])
        gs.addWidget(self.dt_skopi, 1, 0)
        gs.addWidget(self.cmb_skopi, 1, 1)
        grp_sko.add_layout(gs)
        il.addWidget(grp_sko)

        # 4. SonuÃ§ ve Raporlama
        grp_sonuc = FieldGroup("SonuÃ§ ve Raporlama", DarkTheme.ACCENT)
        go = QGridLayout()
        go.setContentsMargins(0, 0, 0, 0)
        go.setHorizontalSpacing(10)
        go.setVerticalSpacing(6)
        go.addWidget(self._lbl("KONTROL EDEN"), 0, 0)
        go.addWidget(self._lbl("BÄ°RÄ°M SORUMLUSU"), 0, 1)
        self.cmb_kontrol = QComboBox()
        self.cmb_kontrol.setEditable(True)
        self.cmb_kontrol.setStyleSheet(_S_COMBO)
        self.cmb_kontrol.setFixedHeight(28)
        if self.kullanici_adi:
            self.cmb_kontrol.setCurrentText(str(self.kullanici_adi))
        self.cmb_sorumlu = QComboBox()
        self.cmb_sorumlu.setEditable(True)
        self.cmb_sorumlu.setStyleSheet(_S_COMBO)
        self.cmb_sorumlu.setFixedHeight(28)
        go.addWidget(self.cmb_kontrol, 1, 0)
        go.addWidget(self.cmb_sorumlu, 1, 1)
        go.addWidget(self._lbl("TEKNÄ°K AÃƒâ€¡IKLAMA (Ãƒâ€¡oklu SeÃ§im)"), 2, 0, 1, 2)
        self.cmb_aciklama = CheckableComboBox()
        self.cmb_aciklama.setStyleSheet(_S_COMBO)
        self.cmb_aciklama.setFixedHeight(28)
        go.addWidget(self.cmb_aciklama, 3, 0, 1, 2)

        # Dosya satÄ±rÄ±
        file_row = QHBoxLayout()
        self.lbl_dosya = QLabel("Rapor seÃ§ilmedi")
        self.lbl_dosya.setProperty("color-role", "muted")
        self.lbl_dosya.setStyleSheet("font-size: 10px;")
        self.lbl_dosya.style().unpolish(self.lbl_dosya)
        self.lbl_dosya.style().polish(self.lbl_dosya)
        btn_dosya = QPushButton("ÄŸÅ¸â€œâ€š Rapor YÃ¼kle")
        btn_dosya.setStyleSheet(
            f"QPushButton{{background:{DarkTheme.BG_SECONDARY};border:1px solid {DarkTheme.BORDER_PRIMARY};border-radius:4px;"
            f"color:{DarkTheme.TEXT_SECONDARY};padding:0 12px;}}QPushButton:hover{{color:{DarkTheme.TEXT_PRIMARY};}}"
        )
        btn_dosya.setFixedHeight(28)
        btn_dosya.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_dosya.clicked.connect(self.dosya_sec)
        file_row.addWidget(self.lbl_dosya, 1)
        file_row.addWidget(btn_dosya)
        go.addLayout(file_row, 4, 0, 1, 2)
        grp_sonuc.add_layout(go)
        il.addWidget(grp_sonuc)

        # 5. GeÃ§miÅ
        grp_gecmis = FieldGroup("SeÃ§ili EkipmanÄ±n GeÃ§miÅi", DarkTheme.RKE_PURP)
        self._gecmis_model = GecmisModel()
        self.tbl_gecmis = QTableView()
        self.tbl_gecmis.setModel(self._gecmis_model)
        self.tbl_gecmis.setStyleSheet(_S_TABLE)
        self.tbl_gecmis.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_gecmis.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_gecmis.verticalHeader().setVisible(False)
        self.tbl_gecmis.setShowGrid(False)
        self.tbl_gecmis.setAlternatingRowColors(True)
        self.tbl_gecmis.setFixedHeight(140)
        self.tbl_gecmis.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_gecmis.doubleClicked.connect(self._gecmis_satir_tiklandi)
        grp_gecmis.add_widget(self.tbl_gecmis)
        il.addWidget(grp_gecmis)

        il.addStretch()
        scroll.setWidget(inner)
        vl.addWidget(scroll, 1)

        # Progress
        self.pbar = QProgressBar()
        self.pbar.setVisible(False)
        self.pbar.setFixedHeight(3)
        self.pbar.setStyleSheet(_S_PBAR)
        vl.addWidget(self.pbar)

        # Butonlar
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(12, 8, 12, 12)
        btn_row.setSpacing(8)
        self.btn_temizle = QPushButton("Ã¢â€ Âº  TEMÄ°ZLE")
        self.btn_temizle.setFixedHeight(34)
        self.btn_temizle.setStyleSheet(
            f"QPushButton{{background:transparent;border:1px solid {DarkTheme.BORDER_PRIMARY};"
            f"border-radius:5px;color:{DarkTheme.TEXT_MUTED};font-family:{DarkTheme.MONOSPACE};"
            f"font-size:10px;letter-spacing:1px;}}"
            f"QPushButton:hover{{color:{DarkTheme.TEXT_PRIMARY};border-color:{DarkTheme.TEXT_SECONDARY};}}"
        )
        self.btn_temizle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_temizle.clicked.connect(self.temizle)
        self.btn_kaydet = QPushButton("Ã¢Å“â€œ  KAYDET")
        self.btn_kaydet.setFixedHeight(34)
        self.btn_kaydet.setStyleSheet(
            f"QPushButton{{background:{DarkTheme.STATUS_SUCCESS};border:none;border-radius:5px;"
            f"color:#051a10;font-family:{DarkTheme.MONOSPACE};font-size:10px;font-weight:800;"
            f"letter-spacing:1px;}}"
        )
        self.btn_kaydet.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_kaydet.clicked.connect(self.kaydet)
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self.btn_kaydet, "cihaz.write")
        btn_row.addWidget(self.btn_temizle)
        btn_row.addWidget(self.btn_kaydet)
        vl.addLayout(btn_row)
        return panel

    def _build_list_panel(self) -> QWidget:
        panel = QWidget()
        panel.setProperty("bg-role", "page")
        panel.style().unpolish(panel)
        panel.style().polish(panel)
        vl = QVBoxLayout(panel)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        # Filtre Ã§ubuÄŸu
        fbar = QWidget()
        fbar.setFixedHeight(52)
        fbar.setProperty("bg-role", "page")
        fbar.style().unpolish(fbar)
        fbar.style().polish(fbar)
        fl = QHBoxLayout(fbar)
        fl.setContentsMargins(12, 10, 12, 10)
        fl.setSpacing(8)

        self.cmb_filtre_abd = QComboBox()
        self.cmb_filtre_abd.setStyleSheet(_S_COMBO)
        self.cmb_filtre_abd.setFixedHeight(28)
        self.cmb_filtre_abd.setMinimumWidth(160)
        self.cmb_filtre_abd.addItem("TÃ¼m ABD")
        self.cmb_filtre_abd.currentIndexChanged.connect(self.tabloyu_filtrele)

        self.txt_ara = QLineEdit()
        self.txt_ara.setStyleSheet(_S_INPUT)
        self.txt_ara.setFixedHeight(28)
        self.txt_ara.setPlaceholderText("Ara...")
        self.txt_ara.textChanged.connect(self.tabloyu_filtrele)

        btn_yenile = QPushButton("Ã¢Å¸Â³")
        btn_yenile.setFixedSize(28, 28)
        btn_yenile.setStyleSheet(
            f"QPushButton{{background:{DarkTheme.BG_SECONDARY};border:1px solid {DarkTheme.BORDER_PRIMARY};border-radius:4px;"
            f"color:{DarkTheme.TEXT_SECONDARY};}}QPushButton:hover{{color:{DarkTheme.TEXT_PRIMARY};}}"
        )
        btn_yenile.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_yenile.clicked.connect(self.verileri_yukle)

        btn_toplu = QPushButton("Ã¢â€“Â¶ Toplu Muayene")
        btn_toplu.setFixedHeight(28)
        btn_toplu.setStyleSheet(
            f"QPushButton{{background:{DarkTheme.ACCENT};border:none;border-radius:4px;"
            f"color:#0a1420;font-family:{DarkTheme.MONOSPACE};font-size:9px;font-weight:700;padding:0 12px;}}"
        )
        btn_toplu.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_toplu.clicked.connect(self.ac_toplu_dialog)

        fl.addWidget(self.cmb_filtre_abd)
        fl.addWidget(self.txt_ara, 1)
        fl.addWidget(btn_yenile)
        fl.addWidget(btn_toplu)
        vl.addWidget(fbar)

        # Tablo
        self._model = RKEEnvanterModel()
        self.tablo = QTableView()
        self.tablo.setModel(self._model)
        self.tablo.setStyleSheet(_S_TABLE)
        self.tablo.setAlternatingRowColors(True)
        self.tablo.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tablo.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tablo.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.setShowGrid(False)
        hdr = self.tablo.horizontalHeader()
        for i, w in enumerate(_RKE_WIDTHS):
            if i == len(_RKE_COLS) - 1:
                hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            else:
                hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                hdr.resizeSection(i, w)
        self.tablo.clicked.connect(self._sag_tablo_tiklandi)
        vl.addWidget(self.tablo, 1)

        # Footer
        footer = QWidget()
        footer.setFixedHeight(44)
        footer.setProperty("bg-role", "panel")
        footer.setProperty("border-role", "top")
        footer.style().unpolish(footer)
        footer.style().polish(footer)
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(12, 8, 12, 8)
        fl.setSpacing(8)
        
        self.lbl_sayi = QLabel("0 kayÄ±t")
        self.lbl_sayi.setStyleSheet(
            f"color:{DarkTheme.TEXT_MUTED};font-family:{DarkTheme.MONOSPACE};font-size:10px;font-weight:500;"
        )
        fl.addStretch()
        fl.addWidget(self.lbl_sayi)
        vl.addWidget(footer)
        return panel

    # Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    #  YARDIMCI UI
    # Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

    @staticmethod
    def _lbl(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color:{DarkTheme.TEXT_MUTED};font-family:{DarkTheme.MONOSPACE};"
            f"font-size:10px;font-weight:500;letter-spacing:0.3px;"
        )
        return lbl

    # Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    #  KPI
    # Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

    def _update_kpi(self, rows: List[Dict]):
        toplam, uygun, uygun_d, bekleyen = len(rows), 0, 0, 0
        today = datetime.date.today()
        for r in rows:
            d = str(r.get("Durum", ""))
            if "DeÄŸil" in d: uygun_d += 1
            elif "Uygun" in d: uygun  += 1
            kt = str(r.get("KontrolTarihi", ""))
            if kt and len(kt) >= 10:
                try:
                    dt_obj = datetime.datetime.strptime(kt[:10], "%Y-%m-%d").date()
                    if dt_obj <= today: bekleyen += 1
                except: pass
        for k, v in [("toplam", toplam), ("uygun", uygun),
                     ("uygun_d", uygun_d), ("bekleyen", bekleyen)]:
            if k in self._kpi_labels:
                self._kpi_labels[k].setText(str(v))

    # Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    #  MANTIK
    # Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

    def dosya_sec(self):
        yol, _ = QFileDialog.getOpenFileName(self, "Rapor", "", "PDF/Resim (*.pdf *.jpg)")
        if yol:
            self.secilen_dosya = yol
            self.lbl_dosya.setText(os.path.basename(yol))

    def verileri_yukle(self):
        self.pbar.setVisible(True)
        self.pbar.setRange(0, 0)
        self.loader = VeriYukleyici(self._db_path, use_sheets=self._use_sheets)
        self.loader.veri_hazir.connect(self.veriler_geldi)
        self.loader.hata_olustu.connect(lambda e: QMessageBox.critical(self, "Hata", e))
        self.loader.finished.connect(lambda: self.pbar.setVisible(False))
        self.loader.start()

    def veriler_geldi(self, rke_data, rke_combo, rke_dict, muayene_list,
                      headers, teknik_aciklamalar, kontrol_edenler, birim_sorumlulari):
        self.rke_data           = rke_data
        self.rke_dict           = rke_dict
        self.tum_muayeneler     = muayene_list
        self.header_map         = {h.strip(): i for i, h in enumerate(headers)}
        self.teknik_aciklamalar = teknik_aciklamalar
        self.kontrol_listesi    = kontrol_edenler
        self.sorumlu_listesi    = birim_sorumlulari

        self.cmb_rke.blockSignals(True)
        self.cmb_rke.clear()
        self.cmb_rke.addItems(rke_combo)
        self.cmb_rke.blockSignals(False)

        self.cmb_aciklama.clear()
        self.cmb_aciklama.addItems(teknik_aciklamalar)

        self.cmb_kontrol.clear()
        self.cmb_kontrol.addItems(kontrol_edenler)
        if self.kullanici_adi: self.cmb_kontrol.setCurrentText(str(self.kullanici_adi))

        self.cmb_sorumlu.clear()
        self.cmb_sorumlu.addItems(birim_sorumlulari)

        abd = sorted({str(r.get("AnaBilimDali", "")).strip() for r in rke_data
                      if str(r.get("AnaBilimDali", "")).strip()})
        self.cmb_filtre_abd.blockSignals(True)
        self.cmb_filtre_abd.clear()
        self.cmb_filtre_abd.addItem("TÃ¼m ABD")
        self.cmb_filtre_abd.addItems(abd)
        self.cmb_filtre_abd.blockSignals(False)

        self.tabloyu_filtrele()

    def tabloyu_filtrele(self):
        secilen_abd = self.cmb_filtre_abd.currentText()
        ara         = self.txt_ara.text().lower()
        filtered    = []
        for row in self.rke_data:
            abd = str(row.get("AnaBilimDali", "")).strip()
            if secilen_abd != "TÃ¼m ABD" and abd != secilen_abd: continue
            if ara and ara not in " ".join([str(v) for v in row.values()]).lower(): continue
            filtered.append(row)
        self._model.set_rows(filtered)
        self.lbl_sayi.setText(f"{len(filtered)} kayÄ±t")
        self._update_kpi(filtered)

    def _sag_tablo_tiklandi(self, index: QModelIndex):
        row_data = self._model.get_row(index.row())
        if not row_data: return
        ekipman_no = str(row_data.get("EkipmanNo", ""))
        idx = self.cmb_rke.findText(ekipman_no, Qt.MatchContains)
        if idx >= 0: self.cmb_rke.setCurrentIndex(idx)

    def ekipman_secildi(self):
        secilen_text = self.cmb_rke.currentText()
        if not secilen_text: return
        ekipman_no = self.rke_dict.get(secilen_text, secilen_text.split('|')[0].strip())
        rows = []
        idx_ekipman = self.header_map.get("EkipmanNo", -1)
        if idx_ekipman == -1: return
        for row in self.tum_muayeneler:
            if len(row) > idx_ekipman and row[idx_ekipman] == ekipman_no:
                def get_v(key):
                    i = self.header_map.get(key, -1)
                    return row[i] if i != -1 and len(row) > i else ""
                rows.append({
                    "F_MuayeneTarihi": get_v("F_MuayeneTarihi"),
                    "S_MuayeneTarihi": get_v("S_MuayeneTarihi"),
                    "Aciklamalar":     get_v("Aciklamalar"),
                    "Rapor":           get_v("Rapor"),
                })
        self._gecmis_model.set_rows(rows)

    def _gecmis_satir_tiklandi(self, index: QModelIndex):
        if index.column() == 3:
            row_data = self._gecmis_model.get_row(index.row())
            if row_data:
                link = str(row_data.get("Rapor", ""))
                if "http" in link:
                    QDesktopServices.openUrl(QUrl(link))

    def temizle(self):
        self.cmb_rke.setCurrentIndex(-1)
        self.dt_fiziksel.setDate(QDate.currentDate())
        self.dt_skopi.setDate(QDate.currentDate())
        self.cmb_kontrol.setCurrentText(str(self.kullanici_adi) if self.kullanici_adi else "")
        self.cmb_sorumlu.setCurrentText("")
        self.cmb_fiziksel.setCurrentIndex(0)
        self.cmb_skopi.setCurrentIndex(0)
        self.cmb_aciklama.setCheckedItems([])
        self.lbl_dosya.setText("Rapor seÃ§ilmedi")
        self.secilen_dosya = None
        self._gecmis_model.set_rows([])

    def kaydet(self):
        if self._action_guard and not self._action_guard.check_and_warn(
            self, "cihaz.write", "RKE Muayene Kaydetme"
        ):
            return
        rke_text = self.cmb_rke.currentText()
        if not rke_text:
            QMessageBox.warning(self, "UyarÄ±", "Ekipman seÃ§in."); return
        ekipman_no = self.rke_dict.get(rke_text, rke_text.split('|')[0].strip())
        unique_id  = f"M-{int(time.time())}"
        veri = {
            'KayitNo':          unique_id,
            'EkipmanNo':        ekipman_no,
            'F_MuayeneTarihi':  self.dt_fiziksel.date().toString("yyyy-MM-dd"),
            'FizikselDurum':    self.cmb_fiziksel.currentText(),
            'S_MuayeneTarihi':  self.dt_skopi.date().toString("yyyy-MM-dd"),
            'SkopiDurum':       self.cmb_skopi.currentText(),
            'Aciklamalar':      self.cmb_aciklama.getCheckedItems(),
            'KontrolEden':      self.cmb_kontrol.currentText(),
            'BirimSorumlusu':   self.cmb_sorumlu.currentText(),
            'Not':              "",
        }
        self.pbar.setVisible(True)
        self.pbar.setRange(0, 0)
        self.btn_kaydet.setEnabled(False)
        self.saver = KayitWorker(veri, self.secilen_dosya, db_path=self._db_path, use_sheets=self._use_sheets)
        self.saver.finished.connect(self.islem_basarili)
        self.saver.error.connect(lambda e: QMessageBox.critical(self, "Hata", e))
        self.saver.start()

    def islem_basarili(self, msg: str):
        self.pbar.setVisible(False)
        self.btn_kaydet.setEnabled(True)
        QMessageBox.information(self, "BaÅarÄ±lÄ±", msg)
        self.temizle()
        self.verileri_yukle()

    def ac_toplu_dialog(self):
        secili = self.tablo.selectionModel().selectedRows()
        if not secili:
            QMessageBox.warning(self, "UyarÄ±", "Tabloda satÄ±r seÃ§in."); return
        ekipmanlar = sorted({
            str(self._model.get_row(i.row()).get("EkipmanNo", ""))
            for i in secili
            if self._model.get_row(i.row())
        })
        dlg = TopluMuayeneDialog(
            ekipmanlar,
            self.teknik_aciklamalar,
            self.kontrol_listesi,
            self.sorumlu_listesi,
            self.kullanici_adi,
            self,
            db_path=self._db_path,
            use_sheets=self._use_sheets,
            checkable_combo_cls=CheckableComboBox,
            worker_cls=TopluKayitWorker,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            QMessageBox.information(self, "Bilgi", "Toplu kayÄ±t baÅarÄ±lÄ±.")
            self.verileri_yukle()

    def load_data(self):
        """main_window.py'den Ã§aÄŸrÄ±lan yÃ¼kleme metodu."""
        self.verileri_yukle()

    def closeEvent(self, event):
        for attr in ("loader", "saver"):
            t = getattr(self, attr, None)
            if t and t.isRunning(): t.quit(); t.wait(500)
        event.accept()








# -*- coding: utf-8 -*-
"""
Checkable ComboBox

oklu seim yaplabilen QComboBox bileeni.
RKE Muayene formunda teknik aklama seimi iin kullanlr,
ancak baka sayfalarda da yeniden kullanlabilir.
"""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QComboBox
from PySide6.QtGui import QColor, QPalette, QStandardItemModel, QStandardItem

from ui.styles import DarkTheme


class CheckableComboBox(QComboBox):
    """
    Her enin yannda onay kutusu bulunan QComboBox.

    Kullanm:
        cmb = CheckableComboBox()
        cmb.addItems(["Seçenek A", "Seçenek B"])
        cmb.set_checked_items(["Seçenek A"])
        secili = cmb.get_checked_items()   # "Seçenek A"
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view().pressed.connect(self._handle_pressed)
        self.setModel(QStandardItemModel(self))
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)

        p = self.lineEdit().palette()
        p.setColor(QPalette.Base, QColor(DarkTheme.INPUT_BG))
        p.setColor(QPalette.Text, QColor(DarkTheme.TEXT_PRIMARY))
        self.lineEdit().setPalette(p)

    #  zel addItem / addItems 

    def addItem(self, text, data=None):
        item = QStandardItem(text)
        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        item.setData(Qt.Unchecked, Qt.CheckStateRole)
        self.model().appendRow(item)

    def addItems(self, texts):
        for t in texts:
            self.addItem(t)

    #  Seim ynetimi 

    def _handle_pressed(self, index):
        item = self.model().itemFromIndex(index)
        item.setCheckState(
            Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked
        )
        QTimer.singleShot(10, self._update_text)

    def _update_text(self):
        checked = [
            self.model().item(i).text()
            for i in range(self.count())
            if self.model().item(i).checkState() == Qt.Checked
        ]
        self.lineEdit().setText(", ".join(checked))

    #  D Arayz 

    def set_checked_items(self, text_list):
        """
        Verilen liste elemanlarn iaretler, geri kalanlar temizler.
        text_list: list[str] ya da virglle ayrlm str kabul eder.
        """
        if isinstance(text_list, str):
            text_list = [x.strip() for x in text_list.split(",") if x.strip()] if text_list else []
        text_list = text_list or []
        for i in range(self.count()):
            item = self.model().item(i)
            item.setCheckState(
                Qt.Checked if item.text() in text_list else Qt.Unchecked
            )
        self._update_text()

    def get_checked_items(self) -> str:
        """aretli eleri virglle ayrlm string olarak dndrr."""
        return self.lineEdit().text()

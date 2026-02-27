# -*- coding: utf-8 -*-
"""RKE Checkable ComboBox component."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QComboBox


class CheckableComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view().pressed.connect(self.handleItemPressed)
        self.setModel(QStandardItemModel(self))
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)

    def handleItemPressed(self, index):
        item = self.model().itemFromIndex(index)
        item.setCheckState(Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked)
        QTimer.singleShot(10, self.updateText)

    def updateText(self):
        items = [
            self.model().item(i).text()
            for i in range(self.count())
            if self.model().item(i).checkState() == Qt.Checked
        ]
        self.lineEdit().setText(", ".join(items))

    def setCheckedItems(self, text_list):
        if isinstance(text_list, str):
            text_list = [x.strip() for x in text_list.split(',')] if text_list else []
        elif not text_list:
            text_list = []
        for i in range(self.count()):
            item = self.model().item(i)
            item.setCheckState(Qt.Checked if item.text() in text_list else Qt.Unchecked)
        self.updateText()

    def getCheckedItems(self):
        return self.lineEdit().text()

    def addItem(self, text, data=None):
        item = QStandardItem(text)
        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        item.setData(Qt.Unchecked, Qt.CheckStateRole)
        self.model().appendRow(item)

    def addItems(self, texts):
        for t in texts:
            self.addItem(t)

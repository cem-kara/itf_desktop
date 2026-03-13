from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from .fhsz.dis_alan_katsayi_page import DisAlanKatsayiPage

class DisAlanMerkezPage(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.addTab(DisAlanKatsayiPage(self._db), "Katsayı Protokolleri")
        # Diğer sekmeler buraya eklenecek
        layout.addWidget(self.tabs)
        self.setLayout(layout)

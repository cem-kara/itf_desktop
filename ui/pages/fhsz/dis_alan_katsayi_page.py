from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QTableView, QHBoxLayout
from core.di import get_dis_alan_katsayi_service
from core.logger import logger

class DisAlanKatsayiPage(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._svc = get_dis_alan_katsayi_service(db) if db else None
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        self.lbl_title = QLabel("Katsayı Protokolleri")
        self.lbl_title.setProperty("style-role", "title")
        layout.addWidget(self.lbl_title)

        self.table = QTableView()
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.btn_yeni = QPushButton("Yeni Protokol Ekle")
        self.btn_yeni.setProperty("style-role", "action")
        btn_layout.addWidget(self.btn_yeni)
        self.btn_pasife_al = QPushButton("Pasife Al")
        self.btn_pasife_al.setProperty("style-role", "danger")
        btn_layout.addWidget(self.btn_pasife_al)
        self.btn_tarihce = QPushButton("Tarihçe Göster")
        self.btn_tarihce.setProperty("style-role", "secondary")
        btn_layout.addWidget(self.btn_tarihce)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _load_data(self):
        if not self._svc:
            return
        try:
            # TODO: Model ve veri bağlama eklenecek
            pass
        except Exception as e:
            logger.error(f"DisAlanKatsayiPage yükleme: {e}")

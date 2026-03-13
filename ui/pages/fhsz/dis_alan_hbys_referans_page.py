# ui/pages/fhsz/dis_alan_hbys_referans_page.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QTableView
from core.di import get_dis_alan_hbys_referans_service
from core.logger import logger
from ui.pages.fhsz.dis_alan_hbys_referans_model import DisAlanHbysReferansModel
from ui.dialogs.mesaj_kutusu import MesajKutusu

class DisAlanHbysReferansPage(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db  = db
        self._svc = get_dis_alan_hbys_referans_service(db) if db else None
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.table = QTableView(self)
        self.model = DisAlanHbysReferansModel()
        self.table.setModel(self.model)
        self.model.setup_columns(self.table)
        self.layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.btn_yenile = QPushButton("Yenile")
        self.btn_yenile.setProperty("style-role", "refresh")
        self.btn_yenile.clicked.connect(self._load_data)
        btn_layout.addWidget(self.btn_yenile)
        btn_layout.addStretch()
        self.layout.addLayout(btn_layout)

    def _load_data(self):
        if not self._svc:
            return
        try:
            rows = self._svc.get_referans_listesi()
            self.model.set_data(rows)
        except Exception as e:
            logger.error(f"DisAlanHbysReferansPage yükleme: {e}")
            MesajKutusu.hata(self, "Veriler yüklenemedi.")

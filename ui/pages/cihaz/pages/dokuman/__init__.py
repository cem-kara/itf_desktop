from PySide6.QtWidgets import QWidget, QVBoxLayout
from ui.pages.cihaz.components.cihaz_dokuman_panel import CihazDokumanPanel


class CihazDokumanView(QWidget):
    def __init__(self, db=None, cihaz_data=None, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(CihazDokumanPanel(db=db, cihaz_data=cihaz_data or {}))


__all__ = ["CihazDokumanView"]

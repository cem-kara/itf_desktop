from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class RolesView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Roles view placeholder"))
        self.setLayout(layout)

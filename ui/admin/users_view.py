from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class UsersView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Users view placeholder"))
        self.setLayout(layout)

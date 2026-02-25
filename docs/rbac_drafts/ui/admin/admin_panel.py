from __future__ import annotations

from PySide6.QtWidgets import QLabel, QTabWidget, QVBoxLayout, QWidget


class AdminPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Admin Panel")

        self._tabs = QTabWidget()
        self._tabs.addTab(self._placeholder("Users"), "Users")
        self._tabs.addTab(self._placeholder("Roles"), "Roles")
        self._tabs.addTab(self._placeholder("Permissions"), "Permissions")
        self._tabs.addTab(self._placeholder("Audit"), "Audit")

        layout = QVBoxLayout()
        layout.addWidget(self._tabs)
        self.setLayout(layout)

    def _placeholder(self, name: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"{name} screen placeholder"))
        widget.setLayout(layout)
        return widget

from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.logger import logger
from database.auth_repository import AuthRepository


class AuditView(QWidget):
    def __init__(self, db, action_guard=None, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._action_guard = action_guard
        self._auth_repo = AuthRepository(db)
        self._build_ui()
        self.load_logs()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QHBoxLayout()
        title = QLabel("Audit Log")
        header.addWidget(title)
        header.addStretch()

        self._filter_username = QLineEdit()
        self._filter_username.setPlaceholderText("Username filter")
        header.addWidget(self._filter_username)

        self._filter_success = QComboBox()
        self._filter_success.addItem("All", None)
        self._filter_success.addItem("Success", 1)
        self._filter_success.addItem("Failure", 0)
        header.addWidget(self._filter_success)

        self._limit = QSpinBox()
        self._limit.setRange(10, 5000)
        self._limit.setValue(200)
        self._limit.setSingleStep(50)
        header.addWidget(QLabel("Limit"))
        header.addWidget(self._limit)

        self._btn_refresh = QPushButton("Refresh")
        self._btn_refresh.clicked.connect(self.load_logs)
        header.addWidget(self._btn_refresh)

        layout.addLayout(header)

        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(
            ["Created At", "Username", "Result", "Reason"]
        )
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._table)

        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self._btn_refresh, "admin.critical")

    def load_logs(self) -> None:
        username_filter = self._filter_username.text().strip()
        success_filter = self._filter_success.currentData()
        limit = int(self._limit.value())
        try:
            rows = self._auth_repo.get_auth_audit_logs(
                limit=limit,
                username_filter=username_filter if username_filter else None,
                success_filter=success_filter,
            )
            self._table.setRowCount(0)
            for row in rows:
                idx = self._table.rowCount()
                self._table.insertRow(idx)
                self._table.setItem(idx, 0, QTableWidgetItem(row["created_at"]))
                self._table.setItem(idx, 1, QTableWidgetItem(row["username"] or ""))
                self._table.setItem(
                    idx,
                    2,
                    QTableWidgetItem("Success" if row["success"] else "Failure"),
                )
                self._table.setItem(idx, 3, QTableWidgetItem(row["reason"] or ""))
            logger.info(f"Audit log loaded: {len(rows)} rows")
        except Exception as exc:
            logger.error(f"Audit log load failed: {exc}")

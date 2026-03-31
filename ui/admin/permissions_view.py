from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QFont

from core.logger import logger
from core.hata_yonetici import hata_goster, uyari_goster
from database.permission_repository import PermissionRepository

from ui.styles.icons import IconRenderer


class PermissionDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Yeni Yetki")
        self.setMinimumWidth(360)

        self._key = QLineEdit()
        # setStyleSheet kaldırıldı: input_field — global QSS kuralı geçerli
        self._desc = QLineEdit()
        # setStyleSheet kaldırıldı: input_field — global QSS kuralı geçerli

        form = QFormLayout()
        form.addRow("Permission Key:", self._key)
        form.addRow("Açıklama:", self._desc)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def get_data(self):
        return {
            "key": self._key.text().strip(),
            "description": self._desc.text().strip(),
        }


class PermissionsView(QWidget):
    def __init__(self, db, action_guard=None, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._action_guard = action_guard
        self._perm_repo = PermissionRepository(db)
        self._build_ui()
        self.load_permissions()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QHBoxLayout()
        title = QLabel("Yetki Yönetimi")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        header.addWidget(title)
        header.addStretch()

        self.btn_add = QPushButton("+ Yeni Yetki")
        self.btn_add.clicked.connect(self._add_permission)
        header.addWidget(self.btn_add)

        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Permission Key", "Açıklama"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        actions = QHBoxLayout()
        self.btn_refresh = QPushButton("Yenile")
        IconRenderer.set_button_icon(self.btn_refresh, "refresh", size=14)
        self.btn_refresh.clicked.connect(self.load_permissions)
        actions.addStretch()
        actions.addWidget(self.btn_refresh)
        layout.addLayout(actions)

        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self.btn_add, "admin.critical")

    def load_permissions(self) -> None:
        try:
            rows = self._perm_repo.get_permissions()
            self.table.setRowCount(0)
            for row in rows:
                idx = self.table.rowCount()
                self.table.insertRow(idx)
                self.table.setItem(idx, 0, QTableWidgetItem(row["key"]))
                self.table.setItem(idx, 1, QTableWidgetItem(row.get("description") or ""))
            logger.info(f"{len(rows)} yetki yüklendi")
        except Exception as e:
            logger.error(f"Yetkiler yüklenirken hata: {e}")
            hata_goster(self, f"Yetkiler yüklenirken hata oluştu:\n{e}", "Hata")

    def _add_permission(self) -> None:
        if self._action_guard and not self._action_guard.check_and_warn(
            self, "admin.critical", "Yetki Ekleme"
        ):
            return
        dialog = PermissionDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.get_data()
        if not data["key"]:
            uyari_goster(self, "Permission key boş olamaz!", "Uyarı")
            return
        try:
            self._perm_repo.create_permission(data["key"], data["description"])
            logger.info(f"Yeni yetki oluşturuldu: {data['key']}")
            self.load_permissions()
        except Exception as e:
            logger.error(f"Yetki oluşturulurken hata: {e}")
            hata_goster(self, f"Yetki oluşturulamadı:\n{e}", "Hata")

from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.logger import logger
from database.permission_repository import PermissionRepository
from ui.styles.colors import DarkTheme as C
from ui.styles.components import STYLES
from ui.styles.icons import Icons, IconRenderer


class RoleDialog(QDialog):
    def __init__(self, title: str, name: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(360)

        self._name = QLineEdit()
        # setStyleSheet kaldırıldı: input_field — global QSS kuralı geçerli
        self._name.setText(name)

        form = QFormLayout()
        form.addRow("Rol Adı:", self._name)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def get_name(self) -> str:
        return self._name.text().strip()


class RolePermissionsDialog(QDialog):
    def __init__(self, permissions, selected_ids, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Yetki Yönetimi")
        self.setMinimumWidth(520)

        self._permissions = permissions
        self._selected_ids = set(selected_ids)

        layout = QVBoxLayout(self)

        self._table = QTableWidget()
        self._table.setColumnCount(2)
        self._table.setHorizontalHeaderLabels(["Yetki", "Açıklama"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

        self._load_rows()

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_rows(self) -> None:
        self._table.setRowCount(0)
        for perm in self._permissions:
            row = self._table.rowCount()
            self._table.insertRow(row)

            key_item = QTableWidgetItem(perm["key"])
            key_item.setFlags(key_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            key_item.setCheckState(
                Qt.CheckState.Checked if perm["id"] in self._selected_ids else Qt.CheckState.Unchecked
            )
            self._table.setItem(row, 0, key_item)

            desc_item = QTableWidgetItem(perm.get("description") or "")
            self._table.setItem(row, 1, desc_item)

    def get_selected_permission_ids(self) -> list[int]:
        selected = []
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                selected.append(self._permissions[row]["id"])
        return selected


class RolesView(QWidget):
    def __init__(self, db, action_guard=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._action_guard = action_guard
        self._perm_repo = PermissionRepository(db)
        
        self._build_ui()
        self.load_roles()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Header
        header = QHBoxLayout()
        
        title = QLabel("Rol Yönetimi")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        header.addWidget(title)
        
        header.addStretch()
        
        self.btn_add = QPushButton("+ Yeni Rol")
        self.btn_add.clicked.connect(self._add_role)
        header.addWidget(self.btn_add)
        
        layout.addLayout(header)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Rol Adı", "Yetki Sayısı"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)
        
        # Actions
        actions = QHBoxLayout()
        
        self.btn_permissions = QPushButton("Yetkileri Düzenle")
        self.btn_permissions.clicked.connect(self._edit_permissions)
        actions.addWidget(self.btn_permissions)

        self.btn_edit = QPushButton("Düzenle")
        self.btn_edit.clicked.connect(self._edit_role)
        actions.addWidget(self.btn_edit)
        
        self.btn_delete = QPushButton("Sil")
        self.btn_delete.clicked.connect(self._delete_role)
        actions.addWidget(self.btn_delete)
        
        actions.addStretch()
        
        self.btn_refresh = QPushButton("Yenile")
        IconRenderer.set_button_icon(self.btn_refresh, "refresh", size=14)
        self.btn_refresh.clicked.connect(self.load_roles)
        actions.addWidget(self.btn_refresh)
        
        # IP-06: Admin aksiyonlari icin yetki kontrolu
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self.btn_add, "admin.critical")
            self._action_guard.disable_if_unauthorized(self.btn_permissions, "admin.critical")
            self._action_guard.disable_if_unauthorized(self.btn_edit, "admin.critical")
            self._action_guard.disable_if_unauthorized(self.btn_delete, "admin.critical")
        
        layout.addLayout(actions)
    
    def load_roles(self):
        """Rolleri yükle"""
        try:
            self.table.setRowCount(0)
            for row in self._perm_repo.get_roles_with_permission_count():
                table_row = self.table.rowCount()
                self.table.insertRow(table_row)
                
                self.table.setItem(table_row, 0, QTableWidgetItem(str(row["id"])))
                self.table.setItem(table_row, 1, QTableWidgetItem(row["name"]))
                self.table.setItem(table_row, 2, QTableWidgetItem(str(row["perm_count"])))
            
            logger.info(f"{self.table.rowCount()} rol yüklendi")
        except Exception as e:
            logger.error(f"Roller yüklenirken hata: {e}")
            QMessageBox.critical(self, "Hata", f"Roller yüklenirken hata oluştu:\n{e}")
    
    def _add_role(self):
        """Yeni rol ekle"""
        if self._action_guard and not self._action_guard.check_and_warn(
            self, "admin.critical", "Rol Ekleme"
        ):
            return
        dialog = RoleDialog("Yeni Rol", parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        name = dialog.get_name()
        if not name:
            QMessageBox.warning(self, "Uyarı", "Rol adı boş olamaz!")
            return
        try:
            role_id = self._perm_repo.create_role(name)
            logger.info(f"Yeni rol oluşturuldu: {name} (ID: {role_id})")
            self.load_roles()
        except Exception as e:
            logger.error(f"Rol oluşturulurken hata: {e}")
            QMessageBox.critical(self, "Hata", f"Rol oluşturulamadı:\n{e}")
    
    def _edit_permissions(self):
        """Rol yetkilerini düzenle"""
        if self._action_guard and not self._action_guard.check_and_warn(
            self, "admin.critical", "Rol Yetki Düzenleme"
        ):
            return
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir rol seçin!")
            return

        item = self.table.item(row, 0)
        if not item:
            return
        role_id = int(item.text())
        permissions = self._perm_repo.get_permissions()
        selected = self._perm_repo.get_role_permissions(role_id)

        dialog = RolePermissionsDialog(permissions, selected, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            selected_ids = dialog.get_selected_permission_ids()
            self._perm_repo.set_role_permissions(role_id, selected_ids)
            logger.info(f"Rol yetkileri güncellendi: role_id={role_id}")
            self.load_roles()
        except Exception as e:
            logger.error(f"Rol yetkileri güncellenirken hata: {e}")
            QMessageBox.critical(self, "Hata", f"Yetkiler güncellenemedi:\n{e}")

    def _edit_role(self):
        if self._action_guard and not self._action_guard.check_and_warn(
            self, "admin.critical", "Rol Düzenleme"
        ):
            return
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir rol seçin!")
            return

        id_item = self.table.item(row, 0)
        name_item = self.table.item(row, 1)
        if not id_item or not name_item:
            return
        role_id = int(id_item.text())
        current_name = name_item.text()
        dialog = RoleDialog("Rol Düzenle", name=current_name, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        new_name = dialog.get_name()
        if not new_name:
            QMessageBox.warning(self, "Uyarı", "Rol adı boş olamaz!")
            return
        try:
            self._perm_repo.update_role(role_id, new_name)
            logger.info(f"Rol güncellendi: {role_id} -> {new_name}")
            self.load_roles()
        except Exception as e:
            logger.error(f"Rol güncellenirken hata: {e}")
            QMessageBox.critical(self, "Hata", f"Rol güncellenemedi:\n{e}")
    
    def _delete_role(self):
        """Rolü sil"""
        if self._action_guard and not self._action_guard.check_and_warn(
            self, "admin.critical", "Rol Silme"
        ):
            return
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir rol seçin!")
            return

        id_item = self.table.item(row, 0)
        name_item = self.table.item(row, 1)
        if not id_item or not name_item:
            return
        role_id = int(id_item.text())
        role_name = name_item.text()

        try:
            user_count = self._perm_repo.get_role_user_count(role_id)
            if user_count > 0:
                QMessageBox.warning(
                    self,
                    "Uyarı",
                    f"Rol silinemedi. Bu role bağlı {user_count} kullanıcı var.",
                )
                return
        except Exception as e:
            logger.error(f"Rol kullanım kontrolü hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Rol silinemedi:\n{e}")
            return

        if QMessageBox.question(
            self,
            "Onay",
            f"'{role_name}' rolünü silmek istediğinizden emin misiniz?",
        ) != QMessageBox.StandardButton.Yes:
            return

        try:
            self._perm_repo.delete_role(role_id)
            logger.info(f"Rol silindi: {role_name} (ID: {role_id})")
            self.load_roles()
        except Exception as e:
            logger.error(f"Rol silinirken hata: {e}")
            QMessageBox.critical(self, "Hata", f"Rol silinemedi:\n{e}")


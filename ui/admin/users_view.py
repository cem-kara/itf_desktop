from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QDialog, QFormLayout,
    QLineEdit, QDialogButtonBox, QCheckBox, QLabel
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from core.logger import logger
from database.auth_repository import AuthRepository
from database.permission_repository import PermissionRepository
from core.auth.password_hasher import PasswordHasher

from ui.styles.icons import Icons, IconRenderer


class UserDialog(QDialog):
    """Kullanıcı ekleme/düzenleme dialogu"""
    def __init__(self, db, user_data=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._user_data = user_data
        self._is_edit = user_data is not None
        
        self.setWindowTitle("Kullanıcı Düzenle" if self._is_edit else "Yeni Kullanıcı")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Form
        form = QFormLayout()
        
        self.username_edit = QLineEdit()
        # setStyleSheet kaldırıldı: input_field — global QSS kuralı geçerli
        self.username_edit.setPlaceholderText("İnsan kullanıcı adı")
        if self._is_edit and user_data:
            self.username_edit.setText(user_data.username)
            self.username_edit.setEnabled(False)  # Username değiştirilmez
        
        self.password_edit = QLineEdit()
        # setStyleSheet kaldırıldı: input_field — global QSS kuralı geçerli
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("Şifre" if not self._is_edit else "Boş bırakılırsa değişmez")
        
        self.is_active_check = QCheckBox("Aktif")
        self.is_active_check.setChecked(True if not self._is_edit or not user_data else user_data.is_active)
        
        form.addRow("Kullanıcı Adı:", self.username_edit)
        form.addRow("Şifre:", self.password_edit)
        form.addRow("Durum:", self.is_active_check)
        
        layout.addLayout(form)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_data(self):
        return {
            "username": self.username_edit.text().strip(),
            "password": self.password_edit.text(),
            "is_active": self.is_active_check.isChecked()
        }


class UsersView(QWidget):
    user_changed = Signal()
    
    def __init__(self, db, action_guard=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._action_guard = action_guard
        self._auth_repo = AuthRepository(db)
        self._perm_repo = PermissionRepository(db)
        self._hasher = PasswordHasher()
        
        self._build_ui()
        self.load_users()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Header
        header = QHBoxLayout()
        
        title = QLabel("Kullanıcı Yönetimi")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        header.addWidget(title)
        
        header.addStretch()
        
        self.btn_add = QPushButton("Yeni Kullanıcı")
        IconRenderer.set_button_icon(self.btn_add, "user_add", size=14)
        self.btn_add.clicked.connect(self._add_user)
        header.addWidget(self.btn_add)
        
        layout.addLayout(header)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Kullanıcı Adı", "Durum", "Roller"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        from PySide6.QtWidgets import QAbstractItemView
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)
        
        # Actions
        actions = QHBoxLayout()
        
        self.btn_edit = QPushButton("Düzenle")
        IconRenderer.set_button_icon(self.btn_edit, "edit", size=14)
        self.btn_edit.clicked.connect(self._edit_user)
        actions.addWidget(self.btn_edit)
        
        self.btn_roles = QPushButton("Rolleri Yönet")
        IconRenderer.set_button_icon(self.btn_roles, "shield", size=14)
        self.btn_roles.clicked.connect(self._manage_roles)
        actions.addWidget(self.btn_roles)
        
        self.btn_delete = QPushButton("Sil")
        IconRenderer.set_button_icon(self.btn_delete, "trash", size=14)
        self.btn_delete.clicked.connect(self._delete_user)
        actions.addWidget(self.btn_delete)
        
        actions.addStretch()
        
        self.btn_refresh = QPushButton("Yenile")
        IconRenderer.set_button_icon(self.btn_refresh, "refresh", size=14)
        self.btn_refresh.clicked.connect(self.load_users)
        actions.addWidget(self.btn_refresh)
        
        # IP-06: Admin aksiyonlari icin yetki kontrolu
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self.btn_add, "admin.critical")
            self._action_guard.disable_if_unauthorized(self.btn_edit, "admin.critical")
            self._action_guard.disable_if_unauthorized(self.btn_roles, "admin.critical")
            self._action_guard.disable_if_unauthorized(self.btn_delete, "admin.critical")
        
        layout.addLayout(actions)

    @staticmethod
    def _validate_password(password: str) -> list[str]:
        errors = []
        if len(password) < 8:
            errors.append("Sifre en az 8 karakter olmali")
        if not any(c.isalpha() for c in password):
            errors.append("Sifre en az bir harf icermeli")
        if not any(c.isdigit() for c in password):
            errors.append("Sifre en az bir rakam icermeli")
        return errors
    
    def load_users(self):
        """Kullanıcıları yükle"""
        try:
            users = self._auth_repo.get_all_users()
            self.table.setRowCount(0)
            
            for user in users:
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                self.table.setItem(row, 0, QTableWidgetItem(str(user.id)))
                self.table.setItem(row, 1, QTableWidgetItem(user.username))
                self.table.setItem(row, 2, QTableWidgetItem("Aktif" if user.is_active else "Pasif"))
                
                # Rolleri getir
                roles = self._auth_repo.get_user_roles(user.id)
                role_names = ", ".join([r.name for r in roles]) if roles else "-"
                self.table.setItem(row, 3, QTableWidgetItem(role_names))
            
            logger.info(f"{len(users)} kullanıcı yüklendi")
        except Exception as e:
            logger.error(f"Kullanıcılar yüklenirken hata: {e}")
            QMessageBox.critical(self, "Hata", f"Kullanıcılar yüklenirken hata oluştu:\n{e}")
    
    def _add_user(self):
        """Yeni kullanıcı ekle"""
        if self._action_guard and not self._action_guard.check_and_warn(
            self, "admin.critical", "Kullanıcı Ekleme"
        ):
            return
        dialog = UserDialog(self._db, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            
            if not data["username"]:
                QMessageBox.warning(self, "Uyarı", "Kullanıcı adı boş olamaz!")
                return
            
            if not data["password"]:
                QMessageBox.warning(self, "Uyarı", "Şifre boş olamaz!")
                return

            pw_errors = self._validate_password(data["password"])
            if pw_errors:
                QMessageBox.warning(self, "Uyarı", "\n".join(pw_errors))
                return
            
            try:
                password_hash = self._hasher.hash(data["password"])
                user_id = self._auth_repo.create_user(
                    username=data["username"],
                    password_hash=password_hash,
                    is_active=data["is_active"],
                    must_change_password=True
                )
                logger.info(f"Yeni kullanıcı oluşturuldu: {data['username']} (ID: {user_id})")
                QMessageBox.information(self, "Başarılı", "Kullanıcı başarıyla oluşturuldu!")
                self.load_users()
                self.user_changed.emit()
            except Exception as e:
                logger.error(f"Kullanıcı oluşturulurken hata: {e}")
                QMessageBox.critical(self, "Hata", f"Kullanıcı oluşturulamadı:\n{e}")
    
    def _edit_user(self):
        """Kullanıcıyı düzenle"""
        if self._action_guard and not self._action_guard.check_and_warn(
            self, "admin.critical", "Kullanıcı Düzenleme"
        ):
            return
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir kullanıcı seçin!")
            return
        
        item_0 = self.table.item(row, 0)
        if not item_0:
            return
        user_id = int(item_0.text())
        user = self._auth_repo.get_user_by_id(user_id)
        if not user:
            return
        
        dialog = UserDialog(self._db, user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            
            try:
                # Şifre değiştirilecekse
                if data["password"]:
                    pw_errors = self._validate_password(data["password"])
                    if pw_errors:
                        QMessageBox.warning(self, "Uyarı", "\n".join(pw_errors))
                        return
                    password_hash = self._hasher.hash(data["password"])
                    self._auth_repo.update_user_password(user_id, password_hash)
                
                # Aktiflik durumunu güncelle
                self._auth_repo.update_user_status(user_id, data["is_active"])
                
                if user:
                    logger.info(f"Kullanıcı güncellendi: {user.username}")
                QMessageBox.information(self, "Başarılı", "Kullanıcı başarıyla güncellendi!")
                self.load_users()
                self.user_changed.emit()
            except Exception as e:
                logger.error(f"Kullanıcı güncellenirken hata: {e}")
                QMessageBox.critical(self, "Hata", f"Kullanıcı güncellenemedi:\n{e}")
    
    def _delete_user(self):
        """Kullanıcıyı sil"""
        if self._action_guard and not self._action_guard.check_and_warn(
            self, "admin.critical", "Kullanıcı Silme"
        ):
            return
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir kullanıcı seçin!")
            return
        
        item_0 = self.table.item(row, 0)
        item_1 = self.table.item(row, 1)
        if not item_0 or not item_1:
            return
        user_id = int(item_0.text())
        username = item_1.text()
        
        reply = QMessageBox.question(
            self,
            "Onay",
            f"'{username}' kullanıcısını silmek istediğinizden emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self._auth_repo.delete_user(user_id)
                logger.info(f"Kullanıcı silindi: {username}")
                QMessageBox.information(self, "Başarılı", "Kullanıcı başarıyla silindi!")
                self.load_users()
                self.user_changed.emit()
            except Exception as e:
                logger.error(f"Kullanıcı silinirken hata: {e}")
                QMessageBox.critical(self, "Hata", f"Kullanıcı silinemedi:\n{e}")
    
    def _manage_roles(self):
        """Kullanıcının rollerini yönet"""
        if self._action_guard and not self._action_guard.check_and_warn(
            self, "admin.critical", "Kullanıcı Rol Yönetimi"
        ):
            return
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir kullanıcı seçin!")
            return

        item_0 = self.table.item(row, 0)
        item_1 = self.table.item(row, 1)
        if not item_0 or not item_1:
            return
        user_id = int(item_0.text())
        username = item_1.text()

        roles = self._auth_repo.get_roles()
        selected_roles = {r.id for r in self._auth_repo.get_user_roles(user_id)}

        dialog = RoleSelectDialog(roles, selected_roles, username=username, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            selected_ids = dialog.get_selected_role_ids()
            self._auth_repo.set_user_roles(user_id, selected_ids)
            logger.info(f"Kullanıcı rolleri güncellendi: {username}")
            self.load_users()
            self.user_changed.emit()
        except Exception as e:
            logger.error(f"Kullanıcı rol güncelleme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Roller güncellenemedi:\n{e}")


class RoleSelectDialog(QDialog):
    def __init__(self, roles, selected_ids, username: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Roller - {username}")
        self.setMinimumWidth(400)
        self._roles = roles
        self._selected = set(selected_ids)

        layout = QVBoxLayout(self)

        self._table = QTableWidget()
        self._table.setColumnCount(1)
        self._table.setHorizontalHeaderLabels(["Roller"])
        self._table.horizontalHeader().setStretchLastSection(True)
        from PySide6.QtWidgets import QAbstractItemView
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

        self._load_rows()

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_rows(self):
        self._table.setRowCount(0)
        for role in self._roles:
            row = self._table.rowCount()
            self._table.insertRow(row)
            item = QTableWidgetItem(role["name"])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if role["id"] in self._selected else Qt.CheckState.Unchecked)
            self._table.setItem(row, 0, item)

    def get_selected_role_ids(self) -> list[int]:
        selected = []
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                selected.append(self._roles[row]["id"])
        return selected


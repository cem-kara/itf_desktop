from __future__ import annotations

from typing import Optional

from core.auth.authorization_service import AuthorizationService

from core.auth.session_context import SessionContext
from core.logger import logger


class ActionGuard:
    """
    Aksiyon bazlı yetki kontrolü için helper sınıf.
    
    Kullanım:
        action_guard = ActionGuard(authorization_service, session_context)
        
        # Butonu disable et
        if not action_guard.can_perform("personel.write"):
            btn_ekle.setEnabled(False)
        
        # İşlem öncesi kontrol
        if action_guard.check_and_warn(self, "personel.write", "Personel Ekleme"):
            # İşlem yapılabilir
            pass
    """
    
    def __init__(self, authorization_service: AuthorizationService, session_context: SessionContext):
        self._authz = authorization_service
        self._session = session_context
    
    def can_perform(self, permission_key: str) -> bool:
        """
        Kullanıcının belirtilen aksiyonu yapma yetkisi var mı?
        
        Args:
            permission_key: Kontrol edilecek yetki anahtarı (örn: "personel.write")
        
        Returns:
            True: Yetkili, False: Yetkisiz
        """
        user = self._session.get_user()
        if not user:
            return False
        return self._authz.has_permission(user.user_id, permission_key)
    
    def check_and_warn(self, parent_widget, permission_key: str, action_name: str) -> bool:
        """
        Yetki kontrolü yap, yetkisiz ise uyarı göster.
        
        Args:
            parent_widget: QWidget - Uyarı dialogunun parent'ı
            permission_key: Kontrol edilecek yetki anahtarı
            action_name: İşlemin adı (uyarı mesajında gösterilir)
        
        Returns:
            True: İşlem yapılabilir, False: İşlem engellendi
        """
        if self.can_perform(permission_key):
            return True
        
        from PySide6.QtWidgets import QMessageBox
        
        user = self._session.get_user()
        username = user.username if user else "Bilinmeyen"
        
        QMessageBox.warning(
            parent_widget,
            "Yetki Hatası",
            f"'{action_name}' işlemi için yetkiniz bulunmamaktadır.\n\n"
            f"Gerekli yetki: {permission_key}\n"
            f"Kullanıcı: {username}"
        )
        
        logger.warning(
            f"Yetkisiz aksiyon denemesi: {action_name} "
            f"(yetki: {permission_key}, kullanıcı: {username})"
        )
        
        return False
    
    def disable_if_unauthorized(self, widget, permission_key: str) -> None:
        """
        Widget'ı yetki yoksa disable et.
        
        Args:
            widget: QWidget - Disable edilecek widget (QPushButton, QAction, vb.)
            permission_key: Kontrol edilecek yetki anahtarı
        """
        if not self.can_perform(permission_key):
            widget.setEnabled(False)
            if hasattr(widget, 'setToolTip'):
                widget.setToolTip(f"Bu işlem için '{permission_key}' yetkisi gereklidir")
    
    def hide_if_unauthorized(self, widget, permission_key: str) -> None:
        """
        Widget'ı yetki yoksa gizle.
        
        Args:
            widget: QWidget - Gizlenecek widget
            permission_key: Kontrol edilecek yetki anahtarı
        """
        if not self.can_perform(permission_key):
            widget.setVisible(False)

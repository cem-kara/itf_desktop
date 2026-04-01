import os

from PySide6.QtWidgets import QApplication

from ui.sidebar import Sidebar


def _get_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class FakePageGuard:
    def __init__(self, allowed):
        self._allowed = set(allowed)

    def can_open(self, permission_key):
        return permission_key in self._allowed


def test_sidebar_filters_menu_items():
    _get_app()
    # Personel Listesi icin dis_alan.read izni gerekir.
    page_guard = FakePageGuard({"dis_alan.read"})
    sidebar = Sidebar(page_guard=page_guard)

    # Known items from ayarlar.json
    assert "Personel Listesi" in sidebar._all_buttons
    assert "Admin Panel" not in sidebar._all_buttons

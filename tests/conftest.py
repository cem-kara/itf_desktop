"""
REPYS Test Suite — Ortak Fixture'lar

Tüm test dosyaları tarafından otomatik yüklenir.
"""
import os
import sys
import pytest

# Proje kökünü sys.path'e ekle
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# ─────────────────────────────────────────────────────────────
#  Qt — headless mod (UI testleri için)
# ─────────────────────────────────────────────────────────────

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qt_app():
    """Oturum boyunca tek bir QApplication örneği."""
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        yield app
    except ImportError:
        pytest.skip("PySide6 kurulu değil")


# ─────────────────────────────────────────────────────────────
#  Genel mock registry
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def mock_registry():
    """Basit MagicMock registry — servis testlerinde kullanılır."""
    from unittest.mock import MagicMock
    return MagicMock()

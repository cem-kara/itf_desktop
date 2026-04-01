"""
REPYS UI Test Suite — conftest.py
==================================
pytest-qt tabanlı UI test altyapısı.

Kurulum (projenin kök dizininde):
    pip install pytest-qt

Çalıştırma:
    pytest tests/ -v                    # tüm testler
    pytest tests/ -v -m ui              # sadece UI testleri
    pytest tests/ -v -m "not ui"        # UI testleri hariç
    pytest tests/ui/ -v -s              # UI + print çıktısı
    pytest tests/ --tb=short            # kısa hata izleri
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock

import pytest

# ─── Path ────────────────────────────────────────────────────

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ─── Qt başsız mod ───────────────────────────────────────────
# CI ortamında DISPLAY olmasa bile çalışır.
# Lokal geliştirmede gerçek pencere açmak istiyorsanız
# bu satırı yorum yapın.

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_LOGGING_RULES", "*.debug=false;qt.qpa.*=false")


# ─── Marker tanımları ─────────────────────────────────────────

def pytest_configure(config):
    config.addinivalue_line("markers", "ui: PySide6 widget gerektiren testler")
    config.addinivalue_line("markers", "integration: Gerçek DB ile entegrasyon")
    config.addinivalue_line("markers", "slow: Yavaş testler (>1s)")
    config.addinivalue_line("markers", "smoke: Temel sağlık kontrolleri")


# ─── QApplication ────────────────────────────────────────────

@pytest.fixture(scope="session")
def qapp():
    """
    Oturum boyunca tek QApplication.
    pytest-qt zaten 'qapp' adında bir fixture sağlar —
    biz burada davranışını özelleştiriyoruz.
    """
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv[:1])
            app.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeDialogs, True)

        yield app
    except ImportError:
        pytest.skip("PySide6 kurulu değil — pip install PySide6")


# ─── SQLite ──────────────────────────────────────────────────

@pytest.fixture
def test_db_path(tmp_path) -> Path:
    """
    Her test için ayrı geçici DB dosyası.
    Test bittikten sonra tmp_path ile birlikte silinir.
    :memory: yerine dosya kullanıyoruz çünkü SQLiteManager
    birden fazla bağlantı açabiliyor.
    """
    return tmp_path / "repys_test.db"


@pytest.fixture
def migrated_db(test_db_path) -> Generator:
    """
    Migration çalıştırılmış + seed verileri eklenmiş temiz DB.
    Döner: SQLiteManager örneği.
    """
    from database.migrations import MigrationManager
    from database.sqlite_manager import SQLiteManager

    mgr = MigrationManager(str(test_db_path))
    mgr.run_migrations()

    db = SQLiteManager(str(test_db_path))
    yield db

    try:
        db.close()
    except Exception:
        pass


# ─── Auth & Oturum ───────────────────────────────────────────

@pytest.fixture
def test_credentials() -> dict:
    """Test kullanıcı bilgileri. Diğer fixture'larda override edilebilir."""
    return {"username": "test_admin", "password": "Test1234!"}


@pytest.fixture
def seeded_db(migrated_db, test_credentials) -> "SQLiteManager":
    """
    Admin kullanıcısı eklenmiş DB.
    AuthService'in create_user metodu olmadığından doğrudan SQL kullanıyoruz.
    """
    from datetime import datetime
    from core.auth.password_hasher import PasswordHasher

    pw_hash = PasswordHasher().hash(test_credentials["password"])

    migrated_db.execute(
        "INSERT OR IGNORE INTO Users "
        "(Username, PasswordHash, IsActive, MustChangePassword, CreatedAt) "
        "VALUES (?, ?, 1, 0, ?)",
        (test_credentials["username"], pw_hash, datetime.now().isoformat()),
    )
    # Admin rolü ata
    migrated_db.execute(
        "INSERT OR IGNORE INTO UserRoles (UserId, RoleId) "
        "SELECT u.UserId, r.RoleId FROM Users u, Roles r "
        "WHERE u.Username = ? AND r.RoleName = 'admin'",
        (test_credentials["username"],),
    )
    return migrated_db


@pytest.fixture
def session_ctx():
    """Temiz SessionContext."""
    from core.auth.session_context import SessionContext
    return SessionContext()


@pytest.fixture
def auth_service(seeded_db, session_ctx):
    """Gerçek DB üzerinde AuthService."""
    from database.auth_repository import AuthRepository
    from core.auth.auth_service import AuthService
    from core.auth.password_hasher import PasswordHasher

    repo = AuthRepository(seeded_db)
    return AuthService(repo=repo, hasher=PasswordHasher(), session=session_ctx)


@pytest.fixture
def logged_in(auth_service, session_ctx, test_credentials):
    """
    Giriş yapılmış durum.
    Döner: (auth_service, session_ctx) çifti.
    session_ctx.get_user() ile aktif kullanıcıya erişilebilir.
    """
    user = auth_service.authenticate(
        test_credentials["username"],
        test_credentials["password"],
    )
    assert user is not None, (
        "Test kullanıcısı giriş yapamadı. "
        "seeded_db fixture'ını veya PasswordHasher'ı kontrol edin."
    )
    return auth_service, session_ctx


@pytest.fixture
def authz_service(seeded_db):
    """Gerçek DB üzerinde AuthorizationService."""
    from database.auth_repository import AuthRepository
    from core.auth.authorization_service import AuthorizationService
    return AuthorizationService(AuthRepository(seeded_db))


# ─── Mock'lar ────────────────────────────────────────────────

@pytest.fixture
def mock_registry():
    """Hızlı servis testleri için MagicMock registry."""
    return MagicMock()


@pytest.fixture
def mock_db():
    """Hızlı UI testleri için MagicMock SQLiteManager."""
    return MagicMock()


@pytest.fixture
def mock_auth_service():
    """
    Mock AuthService — gerçek şifre hash'i olmadan giriş simüle eder.

    Kullanım:
        mock_auth_service.authenticate.return_value = SessionUser(1, "admin", True, False)
    """
    return MagicMock()


@pytest.fixture
def mock_authz_service():
    """
    Mock AuthorizationService — tüm izinlere True döner.
    Sayfa yetki filtrelerini bypass etmek için kullanın.
    """
    svc = MagicMock()
    svc.has_permission.return_value = True
    return svc


# ─── Servis fixture'ları (gerçek DB) ─────────────────────────

@pytest.fixture
def personel_service(migrated_db):
    from database.repository_registry import RepositoryRegistry
    from core.services.personel_service import PersonelService
    return PersonelService(RepositoryRegistry(migrated_db))


@pytest.fixture
def izin_service(migrated_db):
    from database.repository_registry import RepositoryRegistry
    from core.services.izin_service import IzinService
    return IzinService(RepositoryRegistry(migrated_db))


@pytest.fixture
def cihaz_service(migrated_db):
    from database.repository_registry import RepositoryRegistry
    from core.services.cihaz_service import CihazService
    return CihazService(RepositoryRegistry(migrated_db))


@pytest.fixture
def nobet_service(migrated_db):
    from database.repository_registry import RepositoryRegistry
    from core.services.nobet.nobet_adapter import NobetAdapter
    return NobetAdapter(RepositoryRegistry(migrated_db))


# ─── UI Widget fixture'ları ───────────────────────────────────

@pytest.fixture
def login_dialog(qtbot, migrated_db, session_ctx):
    """
    Açık LoginDialog.
    qtbot: pytest-qt tarafından otomatik inject edilir.

    Örnek:
        def test_login(login_dialog):
            dialog, auth_svc, session = login_dialog
            dialog._username.setText("admin")
            dialog._password.setText("sifre")
    """
    from ui.auth.login_dialog import LoginDialog
    from database.auth_repository import AuthRepository
    from core.auth.auth_service import AuthService
    from core.auth.password_hasher import PasswordHasher

    repo    = AuthRepository(migrated_db)
    service = AuthService(repo=repo, hasher=PasswordHasher(), session=session_ctx)

    dialog = LoginDialog(auth_service=service)
    qtbot.addWidget(dialog)
    dialog.show()

    yield dialog, service, session_ctx

    dialog.close()


@pytest.fixture
def main_window(qtbot, seeded_db, logged_in):
    """
    Tam MainWindow — login yapılmış, tüm sayfalar erişilebilir.

    Örnek:
        def test_sidebar(main_window):
            win = main_window
            assert win.isVisible()
    """
    from ui.main_window import MainWindow
    from database.auth_repository import AuthRepository
    from core.auth.authorization_service import AuthorizationService

    _, session = logged_in
    authz = AuthorizationService(AuthRepository(seeded_db))

    window = MainWindow(
        db=seeded_db,
        authorization_service=authz,
        session_context=session,
    )
    qtbot.addWidget(window)
    window.show()
    qtbot.waitForWindowShown(window)

    yield window

    window.close()


# ─── Yardımcı fonksiyonlar ───────────────────────────────────

def wait_signal(qtbot, signal, timeout_ms: int = 2000):
    """
    Bir sinyalin tetiklenmesini bekler.
    Timeout aşılırsa test FAIL olur.

    Kullanım:
        with wait_signal(qtbot, widget.data_loaded):
            widget.load_data()
    """
    return qtbot.waitSignal(signal, timeout=timeout_ms)


def click(qtbot, widget):
    """Sol tıklama kısayolu."""
    from PySide6.QtCore import Qt
    qtbot.mouseClick(widget, Qt.MouseButton.LeftButton)


def fill(widget, text: str):
    """QLineEdit veya QTextEdit'e metin yaz."""
    widget.clear()
    widget.setText(text)

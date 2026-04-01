"""
UI Akış Testleri — Giriş (Login) Senaryoları
=============================================
pytest-qt kullanır. Çalıştırmak için:
    pytest tests/ui/test_login_flow.py -v

Fixture'lar conftest.py'den otomatik gelir:
    qtbot       → pytest-qt sağlar
    login_dialog → conftest.py'den
    seeded_db   → conftest.py'den
"""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog


# ─────────────────────────────────────────────────────────────
#  1. Dialog açılıyor mu?
# ─────────────────────────────────────────────────────────────

@pytest.mark.ui
@pytest.mark.smoke
def test_login_dialog_gorunur(qtbot, login_dialog):
    """LoginDialog açıldığında ekranda görünmeli."""
    dialog, _, _ = login_dialog
    assert dialog.isVisible()


@pytest.mark.ui
def test_login_dialog_username_alani_var(qtbot, login_dialog):
    """Kullanıcı adı ve şifre alanları mevcut olmalı."""
    dialog, _, _ = login_dialog
    assert hasattr(dialog, "_username"), "Kullanıcı adı alanı (_username) bulunamadı"
    assert hasattr(dialog, "_password"), "Şifre alanı (_password) bulunamadı"


# ─────────────────────────────────────────────────────────────
#  2. Başarılı giriş
# ─────────────────────────────────────────────────────────────

@pytest.mark.ui
@pytest.mark.integration
def test_basarili_giris_dialog_kabul_eder(qtbot, login_dialog, test_credentials):
    """
    Doğru bilgilerle giriş yapıldığında dialog Accepted durumuna geçmeli.
    """
    dialog, _, session = login_dialog

    # Form doldur
    dialog._username.setText(test_credentials["username"])
    dialog._password.setText(test_credentials["password"])

    # Giriş yap
    dialog._on_accept()

    # Dialog kapanmalı ve Accepted dönmeli
    assert dialog.result() == QDialog.DialogCode.Accepted

    # Oturum açılmış olmalı
    assert session.get_user() is not None
    assert session.get_user().username == test_credentials["username"]


# ─────────────────────────────────────────────────────────────
#  3. Başarısız giriş
# ─────────────────────────────────────────────────────────────

@pytest.mark.ui
def test_yanlis_sifre_dialog_acik_kalir(qtbot, login_dialog, test_credentials):
    """
    Yanlış şifre girildiğinde dialog kapanmamalı.
    """
    dialog, _, session = login_dialog

    dialog._username.setText(test_credentials["username"])
    dialog._password.setText("YANLIS_SIFRE")

    dialog._on_accept()

    # Rejected veya hâlâ açık olmalı
    assert dialog.result() != QDialog.DialogCode.Accepted
    assert session.get_user() is None


@pytest.mark.ui
def test_bos_kullanici_adi_reddedilir(qtbot, login_dialog):
    """Kullanıcı adı boş bırakılırsa giriş reddedilmeli."""
    dialog, _, session = login_dialog

    dialog._username.setText("")
    dialog._password.setText("herhangi_sifre")

    dialog._on_accept()

    assert dialog.result() != QDialog.DialogCode.Accepted
    assert session.get_user() is None


@pytest.mark.ui
def test_bos_sifre_reddedilir(qtbot, login_dialog, test_credentials):
    """Şifre boş bırakılırsa giriş reddedilmeli."""
    dialog, _, session = login_dialog

    dialog._username.setText(test_credentials["username"])
    dialog._password.setText("")

    dialog._on_accept()

    assert dialog.result() != QDialog.DialogCode.Accepted


# ─────────────────────────────────────────────────────────────
#  4. Lockout (5 başarısız deneme)
# ─────────────────────────────────────────────────────────────

@pytest.mark.ui
@pytest.mark.integration
def test_lockout_5_basarisiz_denemede(qtbot, login_dialog, test_credentials):
    """
    5 kez yanlış şifre girildiğinde hesap kilitlenmeli.
    Doğru şifre ile de giriş yapılamamalı.
    """
    dialog, auth_svc, session = login_dialog

    # 5 kez yanlış şifre
    for _ in range(5):
        auth_svc.authenticate(test_credentials["username"], "YANLIS")

    # Doğru şifre ile dene — lockout nedeniyle reddedilmeli
    result = auth_svc.authenticate(
        test_credentials["username"],
        test_credentials["password"],
    )
    assert result is None, "Lockout sonrası doğru şifre ile giriş yapılabildi — lockout çalışmıyor"

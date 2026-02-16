import os
import sys
import types

# Proje kökünü Python path'e ekler; pytest hangi dizinden çalıştırılırsa çalıştırılsın modüller bulunur.
sys.path.insert(0, os.path.dirname(__file__))


def _install_qt_stub_if_needed() -> None:
    """
    PySide6 yoksa minimal fallback stub kur.
    Bu stub sadece import-time hatalarını önlemek içindir.
    """
    if "PySide6.QtWidgets" in sys.modules:
        return

    fake_pyside6 = types.ModuleType("PySide6")
    fake_qtcore = types.ModuleType("PySide6.QtCore")
    fake_qtwidgets = types.ModuleType("PySide6.QtWidgets")
    fake_qtgui = types.ModuleType("PySide6.QtGui")

    class _Dummy:
        def __init__(self, *args, **kwargs):
            pass

        def __call__(self, *args, **kwargs):
            return None

        def __getattr__(self, _name):
            return _Dummy()

        def setEnabled(self, *args, **kwargs):
            return None

        def setText(self, *args, **kwargs):
            return None

        def setStyleSheet(self, *args, **kwargs):
            return None

        def isRunning(self):
            return False

        def start(self):
            return None

        def stop(self):
            return None

    class _DummyApp(_Dummy):
        _inst = None

        @classmethod
        def instance(cls):
            return cls._inst

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            _DummyApp._inst = self

        def exec(self):
            return 0

    class _DummySignal:
        def __init__(self, *args, **kwargs):
            self._subs = []

        def connect(self, fn):
            self._subs.append(fn)

        def emit(self, *args, **kwargs):
            for fn in list(self._subs):
                fn(*args, **kwargs)

    # QtCore
    fake_qtcore.QThread = _Dummy
    fake_qtcore.Signal = _DummySignal

    class _QtNamespace:
        def __getattr__(self, _name):
            return 0

    fake_qtcore.Qt = _QtNamespace()

    def _qtcore_getattr(name):
        if name == "Signal":
            return _DummySignal
        if name == "Qt":
            return fake_qtcore.Qt
        return _Dummy

    fake_qtcore.__getattr__ = _qtcore_getattr

    # QtWidgets
    fake_qtwidgets.QApplication = _DummyApp
    fake_qtwidgets.QWidget = _Dummy
    fake_qtwidgets.QMainWindow = _Dummy
    fake_qtwidgets.QMessageBox = _Dummy

    def _qtwidgets_getattr(name):
        if name == "QApplication":
            return _DummyApp
        return _Dummy

    fake_qtwidgets.__getattr__ = _qtwidgets_getattr

    # QtGui
    fake_qtgui.QColor = _Dummy
    fake_qtgui.QCursor = _Dummy
    fake_qtgui.QIcon = _Dummy

    def _qtgui_getattr(_name):
        return _Dummy

    fake_qtgui.__getattr__ = _qtgui_getattr

    fake_pyside6.QtCore = fake_qtcore
    fake_pyside6.QtWidgets = fake_qtwidgets
    fake_pyside6.QtGui = fake_qtgui

    sys.modules.setdefault("PySide6", fake_pyside6)
    sys.modules.setdefault("PySide6.QtCore", fake_qtcore)
    sys.modules.setdefault("PySide6.QtWidgets", fake_qtwidgets)
    sys.modules.setdefault("PySide6.QtGui", fake_qtgui)


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    # PySide6 varsa gerçek modülleri erkenden yükle:
    # test dosyalarındaki koşullu stub blokları real modüllerin üstüne yazamasın.
    from PySide6 import QtCore  # noqa: F401
    from PySide6 import QtGui  # noqa: F401
    from PySide6 import QtWidgets  # noqa: F401
except Exception:
    _install_qt_stub_if_needed()

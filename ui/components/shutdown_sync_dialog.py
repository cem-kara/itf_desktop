from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt, QTimer, Slot


class ShutdownSyncDialog(QDialog):
    """Kapatma sırasında senkronizasyon devam ediyorsa gösterilen modal dialog.

    Basit bir animasyon (nokta ilerlemesi) ve iptal butonu sağlar. Worker
    `finished` veya `error` sinyali gelince otomatik kapanır.
    """

    def __init__(self, parent=None, sync_worker=None):
        super().__init__(parent)
        self.setWindowTitle("Senkronizasyon devam ediyor")
        self.setModal(True)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.sync_worker = sync_worker

        self._label = QLabel("Senkronizasyon uygulanıyor. Lütfen bekleyin")
        self._label.setWordWrap(True)

        self._dots = 0
        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._tick)

        self._cancel_btn = QPushButton("İptal Et ve Kapat")
        self._cancel_btn.clicked.connect(self._on_cancel)

        h = QHBoxLayout()
        h.addStretch(1)
        h.addWidget(self._cancel_btn)

        v = QVBoxLayout(self)
        v.addWidget(self._label)
        v.addLayout(h)

        # Bağlantılar
        if self.sync_worker is not None:
            try:
                self.sync_worker.finished.connect(self._on_finished)
                self.sync_worker.error.connect(self._on_finished)
            except Exception:
                pass

        self._canceled = False

        self._timer.start()

    @Slot()
    def _tick(self):
        self._dots = (self._dots + 1) % 4
        self._label.setText("Senkronizasyon uygulanıyor. Lütfen bekleyin" + "." * self._dots)

    @Slot()
    def _on_finished(self, *args, **kwargs):
        # Senkronizasyon tamamlandı veya hata geldi; dialogu kapat
        self._timer.stop()
        self.accept()

    @Slot()
    def _on_cancel(self):
        # Kullanıcı iptal etmek istiyor: worker durdur ve bekle
        if self.sync_worker is not None:
            try:
                self._label.setText("Senkronizasyon iptal ediliyor... Lütfen bekleyin")
                self._cancel_btn.setEnabled(False)
                self.sync_worker.stop()
            except Exception:
                pass

        # Kısa süre sonra kapat (worker.stop() bekleyen thread'ler için)
        QTimer.singleShot(800, self.accept)
